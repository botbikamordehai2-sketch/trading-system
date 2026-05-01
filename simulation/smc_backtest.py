"""
SMC Full Backtest
Tests all H1 sweep events over 60 days:
- Killzone vs non-Killzone
- Bias-aligned vs counter-bias
- FVG entry vs direct entry
- RR 1:2 fixed | SL = sweep wick extreme
"""
import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timedelta

# ── Config ───────────────────────────────────────────────────────────────────
ACCOUNT_SIZE   = 100_000.0
RISK_PCT       = 0.003          # 0.3% per trade
RR             = 2.0            # Risk:Reward 1:2
MAX_HOLD_BARS  = 8              # Max H1 bars before flat exit
SWING_N        = 2              # Fractal half-window (5-bar)
KILLZONE_HOURS = {10}           # UTC hours (London Silver Bullet)

SYMBOLS = {
    "EURUSD=X": "EURUSD",
    "GC=F":     "XAUUSD",
    "GBPUSD=X": "GBPUSD",
}

# ── Data ─────────────────────────────────────────────────────────────────────
def fetch_h1(ticker: str, days: int = 60) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start, end=end, interval="1h",
                     progress=False, auto_adjust=True)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    return df

# ── Indicators ────────────────────────────────────────────────────────────────
def add_swings(df: pd.DataFrame, n: int = SWING_N) -> pd.DataFrame:
    highs = df["High"].values
    lows  = df["Low"].values
    sh = np.full(len(df), np.nan)
    sl = np.full(len(df), np.nan)
    for i in range(n, len(df) - n):
        if highs[i] == highs[i-n:i+n+1].max():
            sh[i] = highs[i]
        if lows[i] == lows[i-n:i+n+1].min():
            sl[i] = lows[i]
    df = df.copy()
    df["swing_h"] = sh
    df["swing_l"] = sl
    return df

def daily_bias(df: pd.DataFrame, i: int) -> str:
    """Bias based on EMA50 on H1 at bar i."""
    if i < 50:
        return "NEUTRAL"
    ema50 = df["Close"].iloc[:i].ewm(span=50).mean().iloc[-1]
    return "BULL" if df["Close"].iloc[i] > ema50 else "BEAR"

def has_fvg(df: pd.DataFrame, i: int, direction: str, lookback: int = 5) -> str:
    """
    Check for FVG or IFVG in next `lookback` bars after sweep bar i.
    Returns: "FVG" | "IFVG" | "NONE"
    """
    end = min(i + lookback, len(df) - 2)
    for j in range(i + 1, end):
        prev = df.iloc[j - 1]
        mid  = df.iloc[j]
        nxt  = df.iloc[j + 1]

        # Regular FVG
        if direction == "BULL" and prev["High"] < nxt["Low"]:
            return "FVG"
        if direction == "BEAR" and prev["Low"] > nxt["High"]:
            return "FVG"

        # IFVG (body gap, middle candle opposite)
        prev_top = max(prev["Open"], prev["Close"])
        prev_bot = min(prev["Open"], prev["Close"])
        nxt_top  = max(nxt["Open"],  nxt["Close"])
        nxt_bot  = min(nxt["Open"],  nxt["Close"])
        mid_bull = mid["Close"] > mid["Open"]
        mid_bear = mid["Close"] < mid["Open"]

        if direction == "BULL" and mid_bear and prev_top < nxt_bot:
            return "IFVG"
        if direction == "BEAR" and mid_bull and prev_bot > nxt_top:
            return "IFVG"

    return "NONE"

# ── Trade outcome simulation ──────────────────────────────────────────────────
def simulate_trade(df: pd.DataFrame, entry_i: int,
                   direction: str, sl: float, tp: float) -> str:
    """
    Walk forward bar by bar, return 'WIN' / 'LOSS' / 'FLAT'.
    """
    for j in range(entry_i + 1, min(entry_i + MAX_HOLD_BARS + 1, len(df))):
        high = df["High"].iloc[j]
        low  = df["Low"].iloc[j]
        if direction == "BUY":
            if high >= tp:  return "WIN"
            if low  <= sl:  return "LOSS"
        else:
            if low  <= tp:  return "WIN"
            if high >= sl:  return "LOSS"
    return "FLAT"

# ── Backtest engine ───────────────────────────────────────────────────────────
@dataclass
class Trade:
    date:      str
    symbol:    str
    direction: str
    entry:     float
    sl:        float
    tp:        float
    result:    str      # WIN / LOSS / FLAT
    pnl_pct:   float
    killzone:  bool
    bias_ok:   bool
    fvg:       bool
    sweep_lvl: float

def run_backtest(ticker: str, symbol: str, days: int = 60) -> List[Trade]:
    print(f"\n{'='*55}")
    print(f"  {symbol} — {days}-day SMC Backtest")
    print(f"{'='*55}")

    df = fetch_h1(ticker, days)
    if df is None or len(df) < 60:
        print("  Not enough data.")
        return []

    df = add_swings(df)
    trades: List[Trade] = []
    used_bars = set()   # avoid double-trading same sweep

    for i in range(10, len(df) - MAX_HOLD_BARS - 2):
        if i in used_bars:
            continue

        candle = df.iloc[i]
        hour   = candle.name.hour if hasattr(candle.name, "hour") else 0

        # Collect recent swings (last 30 bars before i)
        window = df.iloc[max(0, i-30):i]
        recent_h = window["swing_h"].dropna()
        recent_l = window["swing_l"].dropna()

        sweep_type = None
        level = None

        # Bearish sweep: wick above swing high, close below
        if not recent_h.empty:
            lh = recent_h.iloc[-1]
            if candle["High"] > lh and candle["Close"] < lh:
                sweep_type = "BEAR"
                level = lh

        # Bullish sweep: wick below swing low, close above
        if sweep_type is None and not recent_l.empty:
            ll = recent_l.iloc[-1]
            if candle["Low"] < ll and candle["Close"] > ll:
                sweep_type = "BULL"
                level = ll

        if sweep_type is None:
            continue

        # Metadata
        in_kz    = hour in KILLZONE_HOURS
        bias     = daily_bias(df, i)
        bias_ok  = (
            (sweep_type == "BULL" and bias == "BULL") or
            (sweep_type == "BEAR" and bias == "BEAR") or
            bias == "NEUTRAL"
        )
        fvg = has_fvg(df, i, sweep_type)   # "FVG" | "IFVG" | "NONE"

        # Entry: open of next bar
        entry_i = i + 1
        if entry_i >= len(df):
            continue
        entry = float(df["Open"].iloc[entry_i])

        # SL: beyond the sweep wick
        if sweep_type == "BULL":
            sl = level * 0.9990    # 10 pips below sweep low
            tp = entry + (entry - sl) * RR
            direction = "BUY"
        else:
            sl = level * 1.0010    # 10 pips above sweep high
            tp = entry - (sl - entry) * RR
            direction = "SELL"

        result = simulate_trade(df, entry_i, direction, sl, tp)

        risk_amt = ACCOUNT_SIZE * RISK_PCT
        if result == "WIN":
            pnl_pct = RISK_PCT * RR * 100
        elif result == "LOSS":
            pnl_pct = -RISK_PCT * 100
        else:
            pnl_pct = 0.0

        trades.append(Trade(
            date      = str(candle.name)[:10],
            symbol    = symbol,
            direction = direction,
            entry     = entry,
            sl        = sl,
            tp        = tp,
            result    = result,
            pnl_pct   = pnl_pct,
            killzone  = in_kz,
            bias_ok   = bias_ok,
            fvg       = fvg,
            sweep_lvl = level,
        ))
        used_bars.add(i)

    return trades

# ── Report ─────────────────────────────────────────────────────────────────
def print_report(trades: List[Trade], label: str = "ALL"):
    if not trades:
        print(f"  [{label}] No trades.")
        return
    wins  = sum(1 for t in trades if t.result == "WIN")
    loss  = sum(1 for t in trades if t.result == "LOSS")
    flat  = sum(1 for t in trades if t.result == "FLAT")
    total = len(trades)
    wr    = wins / total * 100
    pnl   = sum(t.pnl_pct for t in trades)
    print(f"  [{label}] Trades:{total:3d} | W:{wins} L:{loss} F:{flat} | "
          f"WR:{wr:5.1f}% | PnL:{pnl:+.2f}%")

def full_report(trades: List[Trade]):
    if not trades:
        return

    print(f"\n  Total sweeps found: {len(trades)}")
    print()

    # All
    print_report(trades, "ALL SWEEPS      ")

    # Killzone filter
    kz   = [t for t in trades if t.killzone]
    nokz = [t for t in trades if not t.killzone]
    print_report(kz,   "IN  KILLZONE    ")
    print_report(nokz, "OUT KILLZONE    ")

    # Bias filter
    bias_ok  = [t for t in trades if t.bias_ok]
    bias_bad = [t for t in trades if not t.bias_ok]
    print_report(bias_ok,  "BIAS ALIGNED    ")
    print_report(bias_bad, "COUNTER BIAS    ")

    # FVG / IFVG filter
    fvg_only  = [t for t in trades if t.fvg == "FVG"]
    ifvg_only = [t for t in trades if t.fvg == "IFVG"]
    any_gap   = [t for t in trades if t.fvg != "NONE"]
    no_gap    = [t for t in trades if t.fvg == "NONE"]
    print_report(fvg_only,  "REGULAR FVG     ")
    print_report(ifvg_only, "IFVG            ")
    print_report(any_gap,   "FVG or IFVG     ")
    print_report(no_gap,    "NO GAP          ")

    # Combined: Killzone + Bias + any gap
    best = [t for t in trades if t.killzone and t.bias_ok and t.fvg != "NONE"]
    print_report(best, "KZ + BIAS + GAP ")

    # Month breakdown
    months = {}
    for t in trades:
        m = t.date[:7]
        months.setdefault(m, []).append(t)
    print()
    for m, mt in sorted(months.items()):
        wins = sum(1 for t in mt if t.result == "WIN")
        pnl  = sum(t.pnl_pct for t in mt)
        print(f"  {m}: {len(mt):2d} trades | WR {wins/len(mt)*100:.0f}% | PnL {pnl:+.2f}%")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_trades = []
    for ticker, symbol in SYMBOLS.items():
        trades = run_backtest(ticker, symbol, days=60)
        full_report(trades)
        all_trades.extend(trades)

    print(f"\n{'='*55}")
    print("  PORTFOLIO COMBINED")
    print(f"{'='*55}")
    full_report(all_trades)

    # Best filter stats
    best = [t for t in all_trades if t.killzone and t.bias_ok and t.fvg]
    if best:
        eq = ACCOUNT_SIZE
        for t in best:
            eq *= 1 + t.pnl_pct / 100
        ret = (eq - ACCOUNT_SIZE) / ACCOUNT_SIZE * 100
        print(f"\n  Best filter equity: ${eq:,.2f} ({ret:+.2f}%)")
        print(f"  Trades per day (KZ+Bias+FVG): {len(best)/60:.2f}")
