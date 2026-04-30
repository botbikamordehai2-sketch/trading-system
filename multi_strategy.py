"""
MULTI-STRATEGY RUNNER
מריץ כל האסטרטגיות במקביל, כותב signals לתיקיות נפרדות
כל חשבון MT5 קורא מתיקייה שלו בלבד.

Signal path: Common/Files/{strategy_id}/signal_{SYMBOL}.txt
EA config:   InpStrategyFolder = "s1_classic"  (לפי החשבון)

הרצה: python multi_strategy.py
"""
import sys
import time
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from entry_monitor import (
    ASSETS, MT5_FILES, alerted,
    get_high_impact_news, compute_rsi,
)

DUPLICATE_BLOCK_SECONDS = 7200  # 2 שעות
from strategies import STRATEGIES
import yfinance as yf
import pandas as pd

MT5_COMMON = Path(MT5_FILES).parent  # Common\Files

PERF_FILE = Path(__file__).parent / "strategy_performance.json"


# ── helpers ─────────────────────────────────────────────────
def load_perf():
    if PERF_FILE.exists():
        return json.loads(PERF_FILE.read_text(encoding="utf-8"))
    return {sid: {"signals": 0, "wins": 0, "losses": 0} for sid in STRATEGIES}


def save_perf(data):
    PERF_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_data(name: str, info: dict):
    try:
        sym = info.get("yf_symbol", info.get("symbol", name))
        h = yf.Ticker(sym).history(period="5d", interval="15m")
        if h.empty or len(h) < 20:
            return None
        return h
    except Exception:
        return None


def check_entry_strategy(name: str, info: dict, h, strat: dict) -> dict | None:
    """בדיקת כניסה לפי הגדרות האסטרטגיה"""
    close = h["Close"]
    if len(close) < 52:
        return None

    price = round(close.iloc[-1], 5)
    ma20  = close.rolling(20).mean().iloc[-1]
    ma50  = close.rolling(50).mean().iloc[-1]

    # RSI
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, 1e-9)
    rsi_series = (100 - 100 / (1 + rs)).dropna()
    rsi = round(rsi_series.iloc[-1], 1)

    # Trend filter
    if strat.get("require_trend"):
        trend_up   = price > ma50
        trend_down = price < ma50
    else:
        trend_up = trend_down = True

    # RSI direction
    rsi_rising  = len(rsi_series) >= 4 and rsi_series.iloc[-1] > rsi_series.iloc[-3]
    rsi_falling = len(rsi_series) >= 4 and rsi_series.iloc[-1] < rsi_series.iloc[-3]

    # Anti-trend (last 3 candles)
    last3 = close.iloc[-3:].values
    last3_bullish = all(last3[i] > last3[i-1] for i in range(1, 3))
    last3_bearish = all(last3[i] < last3[i-1] for i in range(1, 3))

    oversold  = strat.get("rsi_oversold",  30)
    overbought = strat.get("rsi_overbought", 70)

    # Momentum strategy variant
    if "rsi_bull_min" in strat:
        long_rsi  = strat["rsi_bull_min"] <= rsi <= 70
        short_rsi = 30 <= rsi <= strat["rsi_bear_max"]
    else:
        long_rsi  = rsi < oversold
        short_rsi = rsi > overbought

    direction = None

    if trend_up and long_rsi:
        if strat.get("rsi_direction") and not rsi_rising:
            pass
        elif strat.get("anti_trend") and last3_bearish:
            pass
        else:
            direction = "LONG"

    elif trend_down and short_rsi:
        if strat.get("rsi_direction") and not rsi_falling:
            pass
        elif strat.get("anti_trend") and last3_bullish:
            pass
        else:
            direction = "SHORT"

    if not direction:
        return None

    atr = float(pd.concat([
        h["High"] - h["Low"],
        (h["High"] - h["Close"].shift()).abs(),
        (h["Low"]  - h["Close"].shift()).abs(),
    ], axis=1).max(axis=1).rolling(14).mean().iloc[-1])

    sl = round(price - atr * 1.5, 5) if direction == "LONG" else round(price + atr * 1.5, 5)
    tp = round(price + atr * 3.0, 5) if direction == "LONG" else round(price - atr * 3.0, 5)

    return {"name": name, "direction": direction, "price": price,
            "rsi": rsi, "sl": sl, "tp": tp}


def write_signal(strategy_id: str, name: str, direction: str):
    """כותב signal לתיקיית האסטרטגיה"""
    strat_dir = MT5_COMMON / strategy_id
    strat_dir.mkdir(parents=True, exist_ok=True)

    from entry_monitor import MT5_SYMBOL_MAP
    mt5_name = MT5_SYMBOL_MAP.get(name)
    if not mt5_name:
        return

    path = strat_dir / f"signal_{mt5_name}.txt"
    ts = int(datetime.now(timezone.utc).timestamp())
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{direction},{ts}")
    print(f"  [{strategy_id}] {name} {direction} → {path.name}")


def run_all_strategies():
    print(f"\n[{datetime.now().strftime('%H:%M')}] Multi-Strategy scan...")

    # חדשות HIGH impact — בלוק גלובלי אם צריך
    news_events = get_high_impact_news()

    perf = load_perf()
    total_signals = 0

    for name, info in ASSETS.items():
        h = fetch_data(name, info)
        if h is None:
            continue

        for sid, strat in STRATEGIES.items():
            # בדיקת חדשות
            if strat.get("news_block") and news_events:
                for ev in news_events:
                    if ev.get("currency", "") in name:
                        continue  # skip this asset

            # בדיקת duplicate
            dup_key = f"{sid}_{name}"
            last_time = alerted.get(dup_key, 0)
            if time.time() - last_time < DUPLICATE_BLOCK_SECONDS:
                continue

            result = check_entry_strategy(name, info, h, strat)
            if result:
                write_signal(sid, name, result["direction"])
                alerted[dup_key] = time.time()
                perf.setdefault(sid, {"signals": 0, "wins": 0, "losses": 0})
                perf[sid]["signals"] += 1
                total_signals += 1

    save_perf(perf)
    print(f"  סה\"כ signals: {total_signals} על {len(STRATEGIES)} אסטרטגיות")

    # הדפס תוצאות
    _print_leaderboard(perf)


def _print_leaderboard(perf: dict):
    print(f"\n{'─'*55}")
    print(f"  {'Strategy':<20} {'Signals':>7} {'Wins':>5} {'Losses':>7} {'Rate':>6}")
    print(f"{'─'*55}")
    for sid, strat in STRATEGIES.items():
        p = perf.get(sid, {"signals": 0, "wins": 0, "losses": 0})
        closed = p["wins"] + p["losses"]
        rate = f"{p['wins']/closed*100:.0f}%" if closed else "—"
        print(f"  {sid:<20} {p['signals']:>7} {p['wins']:>5} {p['losses']:>7} {rate:>6}")
        print(f"  {'':2}{strat['description']}")
    print(f"{'─'*55}\n")


def run_loop():
    INTERVAL = 15 * 60  # 15 דקות
    print("=" * 55)
    print("MULTI-STRATEGY RUNNER — 5 strategies")
    for sid, s in STRATEGIES.items():
        print(f"  {sid}: {s['description']}")
    print(f"  Signal dirs: {MT5_COMMON}/{{strategy_id}}/signal_*.txt")
    print("=" * 55)

    while True:
        run_all_strategies()
        print(f"  הבא: {INTERVAL//60} דקות")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    run_loop()
