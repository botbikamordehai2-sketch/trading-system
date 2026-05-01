"""
SMC Bot — Smart Money Concepts
Step 1: Liquidity Sweep on H1 Swing H/L
Step 2: MSS confirmation on M1
Step 3: Killzone (10:00-11:00 UTC) + FVG entry
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import requests

TELEGRAM_TOKEN = "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA"
CHAT_ID        = "1246833993"
ACCOUNT_SIZE   = 100_000.0
RISK_PCT       = 0.003

SYMBOLS = {
    "EURUSD=X": "EURUSD",
    "GC=F":     "XAUUSD",
    "GBPUSD=X": "GBPUSD",
}

# ── Telegram ────────────────────────────────────────────────────────────────
def send_telegram(msg: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=5,
        )
    except Exception:
        pass

# ── Data ────────────────────────────────────────────────────────────────────
def fetch(ticker: str, interval: str, period: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval,
                     progress=False, auto_adjust=True)
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# ── Step 1: Swing High / Low (5-bar fractal on H1) ──────────────────────────
def find_swings(df: pd.DataFrame, n: int = 2) -> pd.DataFrame:
    """
    Returns DataFrame with columns: swing_high, swing_low (price or NaN).
    n = half-window (default 2 → 5-bar fractal).
    """
    highs = df["High"].values
    lows  = df["Low"].values
    swing_h = np.full(len(df), np.nan)
    swing_l = np.full(len(df), np.nan)

    for i in range(n, len(df) - n):
        window_h = highs[i - n: i + n + 1]
        window_l = lows[i - n: i + n + 1]
        if highs[i] == window_h.max():
            swing_h[i] = highs[i]
        if lows[i] == window_l.min():
            swing_l[i] = lows[i]

    df = df.copy()
    df["swing_high"] = swing_h
    df["swing_low"]  = swing_l
    return df

# ── Step 1: Liquidity Sweep detection ───────────────────────────────────────
def detect_sweep(df_h1: pd.DataFrame) -> dict:
    """
    Checks last 3 candles for a sweep of a recent swing.
    Returns: {"type": "BULL"|"BEAR"|None, "level": float, "bar": int}
    """
    df = find_swings(df_h1)

    # Look back up to 20 bars for recent swings
    recent = df.iloc[-25:-3]
    last_swing_h = recent["swing_high"].dropna()
    last_swing_l = recent["swing_low"].dropna()

    if last_swing_h.empty and last_swing_l.empty:
        return {"type": None}

    # Last 3 candles (confirmed)
    candles = df.iloc[-4:-1]

    for _, candle in candles.iterrows():
        # BEARISH SWEEP: wick above swing high, candle closes BELOW it
        if not last_swing_h.empty:
            level_h = last_swing_h.iloc[-1]
            if candle["High"] > level_h and candle["Close"] < level_h:
                return {"type": "BEAR", "level": level_h, "candle": candle}

        # BULLISH SWEEP: wick below swing low, candle closes ABOVE it
        if not last_swing_l.empty:
            level_l = last_swing_l.iloc[-1]
            if candle["Low"] < level_l and candle["Close"] > level_l:
                return {"type": "BULL", "level": level_l, "candle": candle}

    return {"type": None}

# ── Step 2: Market Structure Shift on M1 ────────────────────────────────────
def detect_mss(df_m1: pd.DataFrame, sweep_type: str) -> bool:
    """
    BULL sweep → waiting for M1 to break above a recent lower high (BUY setup).
    BEAR sweep → waiting for M1 to break below a recent higher low (SELL setup).
    """
    if len(df_m1) < 20:
        return False

    recent = df_m1.iloc[-20:]

    if sweep_type == "BULL":
        # Find the most recent lower high in M1
        lower_high = recent["High"].rolling(3).max().iloc[-5]
        current_close = df_m1["Close"].iloc[-1]
        return current_close > lower_high

    if sweep_type == "BEAR":
        # Find the most recent higher low in M1
        higher_low = recent["Low"].rolling(3).min().iloc[-5]
        current_close = df_m1["Close"].iloc[-1]
        return current_close < higher_low

    return False

# ── Step 3a: Killzone filter ─────────────────────────────────────────────────
def in_killzone() -> bool:
    """London Silver Bullet: 10:00–11:00 UTC"""
    hour = datetime.utcnow().hour
    return hour in (10,)

# ── Step 3b: FVG + IFVG detection ───────────────────────────────────────────
def find_fvg(df: pd.DataFrame, sweep_type: str, lookback: int = 10) -> dict:
    """
    Detects regular FVG and IFVG (Implied/Hidden FVG).

    Regular FVG (wick-to-wick gap):
      Bullish: prev.High < next.Low  (gap up)
      Bearish: prev.Low  > next.High (gap down)

    IFVG (body-to-body gap — stronger, forms against the move):
      Bullish IFVG: prev.body_top < next.body_bottom + middle candle is BEARISH
      Bearish IFVG: prev.body_bot > next.body_top   + middle candle is BULLISH

    Returns {"found": bool, "type": "FVG"|"IFVG", "top", "bottom", "mid"}
    """
    bars = df.iloc[-lookback:]

    for i in range(1, len(bars) - 1):
        prev = bars.iloc[i - 1]
        mid  = bars.iloc[i]
        nxt  = bars.iloc[i + 1]

        mid_bullish = mid["Close"] > mid["Open"]
        mid_bearish = mid["Close"] < mid["Open"]

        # -- Regular FVG (wick gap) --
        if sweep_type == "BULL" and prev["High"] < nxt["Low"]:
            return {"found": True, "type": "FVG",
                    "top": nxt["Low"], "bottom": prev["High"],
                    "mid": (nxt["Low"] + prev["High"]) / 2}

        if sweep_type == "BEAR" and prev["Low"] > nxt["High"]:
            return {"found": True, "type": "FVG",
                    "top": prev["Low"], "bottom": nxt["High"],
                    "mid": (prev["Low"] + nxt["High"]) / 2}

        # -- IFVG (body gap, middle candle opposite direction) --
        prev_body_top = max(prev["Open"], prev["Close"])
        prev_body_bot = min(prev["Open"], prev["Close"])
        nxt_body_top  = max(nxt["Open"],  nxt["Close"])
        nxt_body_bot  = min(nxt["Open"],  nxt["Close"])

        if sweep_type == "BULL" and mid_bearish and prev_body_top < nxt_body_bot:
            return {"found": True, "type": "IFVG",
                    "top": nxt_body_bot, "bottom": prev_body_top,
                    "mid": (nxt_body_bot + prev_body_top) / 2}

        if sweep_type == "BEAR" and mid_bullish and prev_body_bot > nxt_body_top:
            return {"found": True, "type": "IFVG",
                    "top": prev_body_bot, "bottom": nxt_body_top,
                    "mid": (prev_body_bot + nxt_body_top) / 2}

    return {"found": False, "type": None}

# ── Daily bias ───────────────────────────────────────────────────────────────
def get_daily_bias(ticker: str) -> str:
    """BULL if price > yesterday's close, BEAR otherwise."""
    df = fetch(ticker, "1d", "5d")
    if df is None or len(df) < 2:
        return "NEUTRAL"
    return "BULL" if df["Close"].iloc[-1] > df["Close"].iloc[-2] else "BEAR"

# ── Main signal ──────────────────────────────────────────────────────────────
def signal_smc(ticker: str, symbol: str) -> dict:
    """
    Full SMC pipeline for one symbol.
    Returns signal dict or None.
    """
    # Step 0: Daily bias
    bias = get_daily_bias(ticker)

    # Step 1: Sweep on H1
    df_h1 = fetch(ticker, "1h", "5d")
    if df_h1 is None or len(df_h1) < 30:
        return None

    sweep = detect_sweep(df_h1)
    if sweep["type"] is None:
        return None

    # Bias filter: only take sweeps in direction of daily bias
    if bias != "NEUTRAL":
        if sweep["type"] == "BULL" and bias == "BEAR":
            return None
        if sweep["type"] == "BEAR" and bias == "BULL":
            return None

    # Step 2: MSS on M1
    df_m1 = fetch(ticker, "1m", "1d")
    if df_m1 is None or len(df_m1) < 20:
        return None

    mss = detect_mss(df_m1, sweep["type"])
    if not mss:
        return None

    # Step 3a: Killzone
    if not in_killzone():
        return None  # Outside London Silver Bullet window

    # Step 3b: FVG entry
    fvg = find_fvg(df_m1, sweep["type"])

    direction = "BUY" if sweep["type"] == "BULL" else "SELL"
    entry = fvg["mid"] if fvg["found"] else float(df_m1["Close"].iloc[-1])

    # SL: beyond the sweep level
    if direction == "BUY":
        sl = sweep["level"] * 0.9995   # just below sweep low
        tp = entry + (entry - sl) * 2  # 1:2 RR
    else:
        sl = sweep["level"] * 1.0005   # just above sweep high
        tp = entry - (sl - entry) * 2  # 1:2 RR

    return {
        "symbol":    symbol,
        "ticker":    ticker,
        "direction": direction,
        "entry":     entry,
        "sl":        sl,
        "tp":        tp,
        "sweep_lvl": sweep["level"],
        "fvg":       fvg["found"],
        "bias":      bias,
    }

# ── Scanner ──────────────────────────────────────────────────────────────────
def run_smc_scan():
    print(f"\n[SMC] {datetime.utcnow().strftime('%H:%M:%S UTC')} | Killzone: {in_killzone()}")
    signals = []

    for ticker, symbol in SYMBOLS.items():
        sig = signal_smc(ticker, symbol)
        if sig:
            signals.append(sig)
            msg = (
                f"<b>[SMC] {sig['direction']} {sig['symbol']}</b>\n"
                f"Sweep: {sig['sweep_lvl']:.5f} | Bias: {sig['bias']}\n"
                f"Entry: {sig['entry']:.5f}\n"
                f"SL: {sig['sl']:.5f} | TP: {sig['tp']:.5f}\n"
                f"FVG: {'YES' if sig['fvg'] else 'NO'} | RR: 1:2"
            )
            print(msg.replace("<b>", "").replace("</b>", ""))
            send_telegram(msg)

    if not signals:
        print("  No SMC signals.")

    return signals

# ── Backtest ─────────────────────────────────────────────────────────────────
def backtest_sweep_detection(ticker="EURUSD=X", symbol="EURUSD"):
    """Quick backtest: how many sweeps were detected in last 30 days."""
    print(f"\nBacktest: Sweep detection on {symbol} H1 (30 days)")
    df = fetch(ticker, "1h", "30d")
    if df is None or df.empty:
        print("No data.")
        return

    df = find_swings(df)
    sweeps = {"BULL": 0, "BEAR": 0}

    for i in range(5, len(df) - 1):
        window = df.iloc[:i]
        recent_h = window["swing_high"].dropna()
        recent_l = window["swing_low"].dropna()
        candle = df.iloc[i]

        if not recent_h.empty:
            lh = recent_h.iloc[-1]
            if candle["High"] > lh and candle["Close"] < lh:
                sweeps["BEAR"] += 1

        if not recent_l.empty:
            ll = recent_l.iloc[-1]
            if candle["Low"] < ll and candle["Close"] > ll:
                sweeps["BULL"] += 1

    total = sweeps["BULL"] + sweeps["BEAR"]
    print(f"  Bull sweeps: {sweeps['BULL']}")
    print(f"  Bear sweeps: {sweeps['BEAR']}")
    print(f"  Total: {total} ({total/30:.1f}/day avg)")
    print(f"  Swings found: {df['swing_high'].notna().sum()} highs, "
          f"{df['swing_low'].notna().sum()} lows")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Backtest first
    backtest_sweep_detection("EURUSD=X", "EURUSD")
    backtest_sweep_detection("GC=F",     "XAUUSD")

    # Run scan
    run_smc_scan()
