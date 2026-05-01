"""
Portfolio Backtester — simulates all 7 bots with FTMO rules
Uses real historical data from yfinance
"""
import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# -- FTMO / Account config --------------------------------------------------
ACCOUNT_SIZE     = 100_000.0
RISK_PER_TRADE   = 0.003          # 0.3% per lab bot
MAX_DAILY_LOSS   = 0.045          # 4.5%
MAX_DRAWDOWN     = 0.09           # 9%
MAX_POSITIONS    = 5
MAX_SAME_DIR     = 3
MAX_TRADES_DAY   = 2              # per bot

# -- Symbols ----------------------------------------------------------------
SYMBOLS = {
    "EURUSD=X": "EURUSD",
    "GC=F":     "XAUUSD",
    "GBPUSD=X": "GBPUSD",
}

# -- Data structures --------------------------------------------------------
@dataclass
class Trade:
    bot:        str
    symbol:     str
    direction:  str          # BUY / SELL
    entry:      float
    exit:       float
    pnl_pct:    float
    date:       datetime
    bars_held:  int

@dataclass
class DayStats:
    date:      str
    pnl:       float = 0.0
    trades:    int   = 0
    locked:    bool  = False

# -- Indicator helpers ------------------------------------------------------
def rsi(series: pd.Series, period=14) -> pd.Series:
    delta  = series.diff()
    gain   = delta.clip(lower=0).rolling(period).mean()
    loss   = (-delta.clip(upper=0)).rolling(period).mean()
    rs     = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period=14) -> pd.Series:
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"]  - df["Close"].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(period).mean()

def adx(df: pd.DataFrame, period=14) -> pd.Series:
    up   = df["High"].diff()
    down = -df["Low"].diff()
    pdm  = np.where((up > down) & (up > 0), up, 0)
    ndm  = np.where((down > up) & (down > 0), down, 0)
    tr   = atr(df, period)
    pdi  = 100 * pd.Series(pdm, index=df.index).rolling(period).mean() / tr
    ndi  = 100 * pd.Series(ndm, index=df.index).rolling(period).mean() / tr
    dx   = (100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)).rolling(period).mean()
    return dx

# -- Strategy signal functions (return +1 BUY, -1 SELL, 0 NONE) ----------
def sig_rsi_ma20(df):
    r   = rsi(df["Close"])
    ma  = df["Close"].rolling(20).mean()
    sig = pd.Series(0, index=df.index)
    sig[(r < 30) & (df["Close"] > ma)] = 1
    sig[(r > 70) & (df["Close"] < ma)] = -1
    return sig

def sig_bollinger_rsi(df):
    ma   = df["Close"].rolling(20).mean()
    std  = df["Close"].rolling(20).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    r    = rsi(df["Close"])
    sig  = pd.Series(0, index=df.index)
    sig[(df["Close"] < lower) & (r < 35)] = 1
    sig[(df["Close"] > upper) & (r > 65)] = -1
    return sig

def sig_trend_ema(df):
    ema20 = df["Close"].ewm(span=20).mean()
    ema50 = df["Close"].ewm(span=50).mean()
    adx_v = adx(df)
    sig   = pd.Series(0, index=df.index)
    sig[(ema20 > ema50) & (adx_v > 25)] = 1
    sig[(ema20 < ema50) & (adx_v > 25)] = -1
    return sig

def sig_ema_cross(df):
    ema9  = df["Close"].ewm(span=9).mean()
    ema21 = df["Close"].ewm(span=21).mean()
    sig   = pd.Series(0, index=df.index)
    cross_up   = (ema9 > ema21) & (ema9.shift() <= ema21.shift())
    cross_down = (ema9 < ema21) & (ema9.shift() >= ema21.shift())
    sig[cross_up]   = 1
    sig[cross_down] = -1
    return sig

def sig_macd(df):
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    macd  = ema12 - ema26
    signal= macd.ewm(span=9).mean()
    hist  = macd - signal
    ma200 = df["Close"].rolling(200).mean()
    sig   = pd.Series(0, index=df.index)
    sig[(hist > 0) & (hist.shift() <= 0) & (df["Close"] > ma200)] = 1
    sig[(hist < 0) & (hist.shift() >= 0) & (df["Close"] < ma200)] = -1
    return sig

def sig_stochastic(df):
    low14  = df["Low"].rolling(14).min()
    high14 = df["High"].rolling(14).max()
    k      = 100 * (df["Close"] - low14) / (high14 - low14).replace(0, np.nan)
    d      = k.rolling(3).mean()
    sig    = pd.Series(0, index=df.index)
    sig[(k < 20) & (d < 20) & (k > d)] = 1
    sig[(k > 80) & (d > 80) & (k < d)] = -1
    return sig

def sig_session_breakout(df):
    hour = pd.to_datetime(df.index).hour
    asian_high = df["High"].rolling(7 * 4).max().shift(1)  # approx 7h on H1
    asian_low  = df["Low"].rolling(7 * 4).min().shift(1)
    sig = pd.Series(0, index=df.index)
    london = (hour >= 8) & (hour <= 10)
    sig[london & (df["Close"] > asian_high)] = 1
    sig[london & (df["Close"] < asian_low)]  = -1
    return sig

# -- Bot definitions --------------------------------------------------------
BOTS = [
    {"name": "RSI_MA20",          "sym": "EURUSD=X", "signal": sig_rsi_ma20,        "hold": 4},
    {"name": "BollingerRSI",      "sym": "EURUSD=X", "signal": sig_bollinger_rsi,   "hold": 6},
    {"name": "Trend_EMA",         "sym": "GC=F",     "signal": sig_trend_ema,        "hold": 8},
    {"name": "EMA_Cross",         "sym": "GBPUSD=X", "signal": sig_ema_cross,        "hold": 5},
    {"name": "MACD_Lab",          "sym": "GC=F",     "signal": sig_macd,             "hold": 6},
    {"name": "Stoch_Lab",         "sym": "GBPUSD=X", "signal": sig_stochastic,       "hold": 4},
    {"name": "Session_Breakout",  "sym": "GBPUSD=X", "signal": sig_session_breakout, "hold": 3},
]

# -- Main simulation --------------------------------------------------------
def run_simulation(months=3):
    end   = datetime.today()
    start = end - timedelta(days=30 * months)
    print(f"Downloading {months} months of data ({start.date()} to {end.date()})...")

    data = {}
    for ticker, name in SYMBOLS.items():
        df = yf.download(ticker, start=start, end=end, interval="1h", progress=False, auto_adjust=True)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            data[ticker] = df
            print(f"  {name}: {len(df)} bars")

    all_trades:  List[Trade]            = []
    day_stats:   Dict[str, DayStats]   = {}
    equity       = ACCOUNT_SIZE
    peak_equity  = ACCOUNT_SIZE
    daily_start  = {}

    for bot in BOTS:
        df   = data.get(bot["sym"])
        if df is None or df.empty:
            continue
        sigs = bot["signal"](df)
        hold = bot["hold"]

        trades_today = {}
        i = 0
        while i < len(df) - hold:
            bar      = df.iloc[i]
            date_key = str(df.index[i].date())

            if date_key not in daily_start:
                daily_start[date_key] = equity

            # Portfolio lock checks
            daily_loss = (daily_start[date_key] - equity) / ACCOUNT_SIZE
            drawdown   = (peak_equity - equity) / ACCOUNT_SIZE
            locked     = daily_loss >= MAX_DAILY_LOSS or drawdown >= MAX_DRAWDOWN

            if date_key not in day_stats:
                day_stats[date_key] = DayStats(date_key)
            day_stats[date_key].locked = locked

            bot_trades = trades_today.get(date_key, 0)
            sig        = sigs.iloc[i]

            if not locked and sig != 0 and bot_trades < MAX_TRADES_DAY:
                entry      = float(bar["Close"])
                exit_price = float(df.iloc[i + hold]["Close"])
                direction  = "BUY" if sig == 1 else "SELL"

                raw_pnl = (exit_price - entry) / entry
                if direction == "SELL":
                    raw_pnl = -raw_pnl

                risk_amount = ACCOUNT_SIZE * RISK_PER_TRADE
                pnl_dollars = raw_pnl * risk_amount * 10  # leverage approx

                equity += pnl_dollars
                peak_equity = max(peak_equity, equity)

                trade = Trade(
                    bot       = bot["name"],
                    symbol    = SYMBOLS[bot["sym"]],
                    direction = direction,
                    entry     = entry,
                    exit      = exit_price,
                    pnl_pct   = pnl_dollars / ACCOUNT_SIZE * 100,
                    date      = df.index[i],
                    bars_held = hold,
                )
                all_trades.append(trade)

                day_stats[date_key].pnl    += pnl_dollars
                day_stats[date_key].trades += 1
                trades_today[date_key]      = bot_trades + 1
                i += hold
                continue
            i += 1

    return all_trades, day_stats, equity

# -- Report -----------------------------------------------------------------
def print_report(trades, day_stats, final_equity):
    print("\n" + "="*60)
    print("  PORTFOLIO SIMULATION REPORT")
    print("="*60)

    if not trades:
        print("No trades executed.")
        return

    df = pd.DataFrame([{
        "bot":    t.bot,
        "symbol": t.symbol,
        "dir":    t.direction,
        "pnl":    t.pnl_pct,
        "date":   t.date,
    } for t in trades])

    total_pnl   = df["pnl"].sum()
    win_rate    = (df["pnl"] > 0).mean() * 100
    total_trades= len(df)
    final_pct   = (final_equity - ACCOUNT_SIZE) / ACCOUNT_SIZE * 100

    print(f"\nAccount:      ${ACCOUNT_SIZE:,.0f} => ${final_equity:,.0f}")
    print(f"Total Return: {final_pct:+.2f}%")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate:     {win_rate:.1f}%")
    print(f"Avg P&L/Trade:{total_pnl/total_trades:.3f}%")

    print("\n-- Per Bot ----------------------------------------------")
    for bot_name, grp in df.groupby("bot"):
        wr  = (grp["pnl"] > 0).mean() * 100
        pnl = grp["pnl"].sum()
        print(f"  {bot_name:<20} {len(grp):>3} trades | WR {wr:5.1f}% | PnL {pnl:+.2f}%")

    locked_days = sum(1 for d in day_stats.values() if d.locked)
    print(f"\n-- Risk -------------------------------------------------")
    print(f"  Days locked by circuit breaker: {locked_days}")

    print("\n-- Best Days --------------------------------------------")
    sorted_days = sorted(day_stats.values(), key=lambda x: x.pnl, reverse=True)
    for d in sorted_days[:5]:
        print(f"  {d.date}  {d.pnl:+.2f}$  ({d.trades} trades)")

    print("\n-- Worst Days -------------------------------------------")
    for d in sorted_days[-5:]:
        print(f"  {d.date}  {d.pnl:+.2f}$  ({d.trades} trades)")
    print("="*60)

if __name__ == "__main__":
    trades, day_stats, final_equity = run_simulation(months=3)
    print_report(trades, day_stats, final_equity)
