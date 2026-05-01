"""
Live Paper Trading Simulation
Runs 7 strategies on real-time data every 60 seconds.
Sends Telegram alerts. No MT5 needed.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ── Config ─────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA"
CHAT_ID         = "1246833993"
ACCOUNT_SIZE    = 100_000.0
RISK_PCT        = 0.003
MAX_DAILY_LOSS  = 0.045
MAX_DRAWDOWN    = 0.09
MAX_POSITIONS   = 9
CHECK_INTERVAL  = 60          # seconds between checks

SYMBOLS = {
    "EURUSD=X": "EURUSD",
    "GC=F":     "XAUUSD",
    "GBPUSD=X": "GBPUSD",
}

# ── Telegram ────────────────────────────────────────────────────────────────
def send_telegram(msg: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception:
        pass

# ── Indicators ──────────────────────────────────────────────────────────────
def rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    return 100 - (100 / (1 + g / l.replace(0, np.nan)))

def ema(s, span): return s.ewm(span=span).mean()

def bb(s, p=20, k=2):
    ma = s.rolling(p).mean()
    std = s.rolling(p).std()
    return ma + k*std, ma - k*std

def macd_hist(s):
    return ema(s,12) - ema(s,26) - (ema(s,12) - ema(s,26)).ewm(span=9).mean()

def stoch(df, p=14):
    lo = df["Low"].rolling(p).min()
    hi = df["High"].rolling(p).max()
    return 100 * (df["Close"] - lo) / (hi - lo).replace(0, np.nan)

# ── Signal functions (return BUY / SELL / NONE on last bar) ────────────────
def signal_rsi_ma20(df):
    r, m = rsi(df["Close"]), df["Close"].rolling(20).mean()
    if r.iloc[-1] < 30 and df["Close"].iloc[-1] > m.iloc[-1]: return "BUY"
    if r.iloc[-1] > 70 and df["Close"].iloc[-1] < m.iloc[-1]: return "SELL"
    return "NONE"

def signal_bollinger(df):
    up, lo = bb(df["Close"])
    r = rsi(df["Close"])
    if df["Close"].iloc[-1] < lo.iloc[-1] and r.iloc[-1] < 35: return "BUY"
    if df["Close"].iloc[-1] > up.iloc[-1] and r.iloc[-1] > 65: return "SELL"
    return "NONE"

def signal_trend_ema(df):
    e20 = ema(df["Close"], 20); e50 = ema(df["Close"], 50)
    if e20.iloc[-1] > e50.iloc[-1] and e20.iloc[-2] <= e50.iloc[-2]: return "BUY"
    if e20.iloc[-1] < e50.iloc[-1] and e20.iloc[-2] >= e50.iloc[-2]: return "SELL"
    return "NONE"

def signal_ema_cross(df):
    e9 = ema(df["Close"], 9); e21 = ema(df["Close"], 21)
    if e9.iloc[-1] > e21.iloc[-1] and e9.iloc[-2] <= e21.iloc[-2]: return "BUY"
    if e9.iloc[-1] < e21.iloc[-1] and e9.iloc[-2] >= e21.iloc[-2]: return "SELL"
    return "NONE"

def signal_macd(df):
    h = macd_hist(df["Close"]); m200 = df["Close"].rolling(200).mean()
    if h.iloc[-1] > 0 and h.iloc[-2] <= 0 and df["Close"].iloc[-1] > m200.iloc[-1]: return "BUY"
    if h.iloc[-1] < 0 and h.iloc[-2] >= 0 and df["Close"].iloc[-1] < m200.iloc[-1]: return "SELL"
    return "NONE"

def signal_stoch(df):
    k = stoch(df); d = k.rolling(3).mean()
    if k.iloc[-1] < 20 and d.iloc[-1] < 20 and k.iloc[-1] > d.iloc[-1]: return "BUY"
    if k.iloc[-1] > 80 and d.iloc[-1] > 80 and k.iloc[-1] < d.iloc[-1]: return "SELL"
    return "NONE"

def signal_london(df):
    hour = datetime.utcnow().hour
    if hour not in range(8, 11): return "NONE"
    prev = df.iloc[-25:-1]
    hi = prev["High"].max(); lo = prev["Low"].min()
    if df["Close"].iloc[-1] > hi: return "BUY"
    if df["Close"].iloc[-1] < lo: return "SELL"
    return "NONE"

# ── Bot #8 — FVG Sentinel (SMC: Sweep → MSS → FVG/IFVG) ────────────────────
# Killzone: London Silver Bullet 10:00-11:00 UTC + NY AM 13:30-15:30 UTC

def _swings(df: pd.DataFrame, n: int = 2):
    """5-bar fractal swing highs and lows."""
    highs, lows = df["High"].values, df["Low"].values
    sh = np.full(len(df), np.nan)
    sl = np.full(len(df), np.nan)
    for i in range(n, len(df) - n):
        if highs[i] == highs[i-n:i+n+1].max(): sh[i] = highs[i]
        if lows[i]  == lows[i-n:i+n+1].min():  sl[i] = lows[i]
    df = df.copy()
    df["_sh"] = sh
    df["_sl"] = sl
    return df

def _in_killzone_sentinel() -> bool:
    """London SB 10:00-11:00 UTC  OR  NY AM 13:30-15:30 UTC."""
    h = datetime.utcnow().hour
    return h == 10 or h in (13, 14, 15)

def _detect_sweep(df: pd.DataFrame):
    """
    Checks the last 3 confirmed candles for a liquidity sweep
    of a swing from the prior 30 bars.
    Returns ("BULL"|"BEAR"|None, level)
    """
    df = _swings(df)
    window = df.iloc[-35:-3]
    recent_h = window["_sh"].dropna()
    recent_l = window["_sl"].dropna()

    for _, c in df.iloc[-4:-1].iterrows():
        if not recent_h.empty:
            lh = recent_h.iloc[-1]
            if c["High"] > lh and c["Close"] < lh:
                return "BEAR", lh
        if not recent_l.empty:
            ll = recent_l.iloc[-1]
            if c["Low"] < ll and c["Close"] > ll:
                return "BULL", ll
    return None, None

def _confirm_mss(df: pd.DataFrame, sweep: str) -> bool:
    """MSS on H1: last close breaks beyond the previous candle's range."""
    if len(df) < 3: return False
    cur  = df.iloc[-1]
    prev = df.iloc[-2]
    if sweep == "BULL": return float(cur["Close"]) > float(prev["High"])
    if sweep == "BEAR": return float(cur["Close"]) < float(prev["Low"])
    return False

def _has_fvg(df: pd.DataFrame, sweep: str, lookback: int = 8) -> bool:
    """Regular FVG (wick gap) or IFVG (body gap + opposite middle candle)."""
    bars = df.iloc[-lookback-2:-1]
    for i in range(1, len(bars) - 1):
        p = bars.iloc[i - 1]; m = bars.iloc[i]; n = bars.iloc[i + 1]
        if sweep == "BULL":
            if p["High"] < n["Low"]: return True                        # FVG
            if m["Close"] < m["Open"] and max(p["Open"],p["Close"]) < min(n["Open"],n["Close"]):
                return True                                               # IFVG
        if sweep == "BEAR":
            if p["Low"] > n["High"]: return True                        # FVG
            if m["Close"] > m["Open"] and min(p["Open"],p["Close"]) > max(n["Open"],n["Close"]):
                return True                                               # IFVG
    return False

def _daily_bias(df: pd.DataFrame) -> str:
    if len(df) < 50: return "NEUTRAL"
    ema50 = df["Close"].ewm(span=50).mean().iloc[-1]
    return "BULL" if df["Close"].iloc[-1] > ema50 else "BEAR"

def signal_fvg_sentinel(df):
    if not _in_killzone_sentinel():               return "NONE"
    if len(df) < 50:                              return "NONE"

    sweep, _ = _detect_sweep(df)
    if sweep is None:                             return "NONE"

    bias = _daily_bias(df)
    if bias != "NEUTRAL":
        if sweep == "BULL" and bias == "BEAR":    return "NONE"
        if sweep == "BEAR" and bias == "BULL":    return "NONE"

    if not _confirm_mss(df, sweep):               return "NONE"
    if not _has_fvg(df, sweep):                   return "NONE"

    return "BUY" if sweep == "BULL" else "SELL"

# ── Bot definitions ─────────────────────────────────────────────────────────
BOTS = [
    {"name": "RSI_MA20",         "ticker": "EURUSD=X", "signal": signal_rsi_ma20,     "hold_bars": 4},
    {"name": "BollingerRSI",     "ticker": "EURUSD=X", "signal": signal_bollinger,    "hold_bars": 6},
    {"name": "Trend_EMA",        "ticker": "GC=F",     "signal": signal_trend_ema,    "hold_bars": 8},
    {"name": "EMA_Cross",        "ticker": "GBPUSD=X", "signal": signal_ema_cross,    "hold_bars": 5},
    {"name": "MACD_Lab",         "ticker": "GC=F",     "signal": signal_macd,         "hold_bars": 6},
    {"name": "Stoch_Lab",        "ticker": "GBPUSD=X", "signal": signal_stoch,        "hold_bars": 4},
    {"name": "Session_Breakout", "ticker": "GBPUSD=X", "signal": signal_london,       "hold_bars": 3},
    # ── Bot #8 & #9: FVG Sentinel ──────────────────────────────────────────
    {"name": "FVG_XAUUSD",       "ticker": "GC=F",     "signal": signal_fvg_sentinel, "hold_bars": 8},
    {"name": "FVG_GBPUSD",       "ticker": "GBPUSD=X", "signal": signal_fvg_sentinel, "hold_bars": 8},
]

# ── Position tracker ─────────────────────────────────────────────────────────
@dataclass
class Position:
    bot:       str
    symbol:    str
    direction: str
    entry:     float
    open_time: datetime
    hold_bars: int
    size_usd:  float
    bars_open: int = 0

# ── Live Simulation Engine ───────────────────────────────────────────────────
class LiveSim:
    def __init__(self):
        self.equity      = ACCOUNT_SIZE
        self.peak_equity = ACCOUNT_SIZE
        self.positions:  List[Position] = []
        self.closed:     List[dict]     = []
        self.daily_start = ACCOUNT_SIZE
        self.last_date   = datetime.utcnow().date()
        self.bar_count   = 0
        self.data_cache: Dict[str, pd.DataFrame] = {}

    def fetch_data(self, ticker: str) -> Optional[pd.DataFrame]:
        try:
            df = yf.download(ticker, period="5d", interval="1h", progress=False, auto_adjust=True)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception:
            return None

    def daily_loss_pct(self):
        return (self.daily_start - self.equity) / ACCOUNT_SIZE

    def drawdown_pct(self):
        return (self.peak_equity - self.equity) / ACCOUNT_SIZE

    def is_locked(self):
        return self.daily_loss_pct() >= MAX_DAILY_LOSS or self.drawdown_pct() >= MAX_DRAWDOWN

    def reset_day(self):
        today = datetime.utcnow().date()
        if today != self.last_date:
            self.daily_start = self.equity
            self.last_date   = today

    def close_positions(self, data: Dict[str, pd.DataFrame]):
        for pos in list(self.positions):
            pos.bars_open += 1
            df = data.get(pos.symbol)
            if df is None: continue
            price = float(df["Close"].iloc[-1])
            if pos.bars_open >= pos.hold_bars:
                raw = (price - pos.entry) / pos.entry
                if pos.direction == "SELL": raw = -raw
                pnl = raw * pos.size_usd * 10
                self.equity += pnl
                self.peak_equity = max(self.peak_equity, self.equity)
                result = {
                    "bot": pos.bot, "symbol": SYMBOLS.get(pos.symbol, pos.symbol),
                    "dir": pos.direction, "entry": pos.entry, "exit": price,
                    "pnl": pnl, "pnl_pct": pnl / ACCOUNT_SIZE * 100,
                    "bars": pos.bars_open, "time": datetime.utcnow(),
                }
                self.closed.append(result)
                self.positions.remove(pos)
                icon = "+" if pnl > 0 else "-"
                send_telegram(
                    f"[{icon}] {pos.bot} {pos.direction} {SYMBOLS.get(pos.symbol,'')}\n"
                    f"Entry: {pos.entry:.5f} | Exit: {price:.5f}\n"
                    f"PnL: ${pnl:+.2f} ({pnl/ACCOUNT_SIZE*100:+.3f}%)\n"
                    f"Equity: ${self.equity:,.2f}"
                )

    def open_positions(self, data: Dict[str, pd.DataFrame]):
        if len(self.positions) >= MAX_POSITIONS: return
        active_bots = {p.bot for p in self.positions}
        for bot in BOTS:
            if bot["name"] in active_bots: continue
            df = data.get(bot["ticker"])
            if df is None or len(df) < 30: continue
            sig = bot["signal"](df)
            if sig == "NONE": continue
            price = float(df["Close"].iloc[-1])
            pos = Position(
                bot=bot["name"], symbol=bot["ticker"], direction=sig,
                entry=price, open_time=datetime.utcnow(),
                hold_bars=bot["hold_bars"],
                size_usd=ACCOUNT_SIZE * RISK_PCT,
            )
            self.positions.append(pos)
            send_telegram(
                f"[OPEN] {bot['name']} {sig} {SYMBOLS.get(bot['ticker'],'')}\n"
                f"Entry: {price:.5f} | Risk: ${pos.size_usd:.0f}\n"
                f"Hold: {bot['hold_bars']} bars"
            )

    def status_report(self):
        wins  = [t for t in self.closed if t["pnl"] > 0]
        total = len(self.closed)
        wr    = len(wins) / total * 100 if total else 0
        total_pnl = sum(t["pnl"] for t in self.closed)
        locked_str = " [LOCKED]" if self.is_locked() else ""

        lines = [
            f"LIVE SIM STATUS{locked_str}",
            f"Equity: ${self.equity:,.2f} ({(self.equity-ACCOUNT_SIZE)/ACCOUNT_SIZE*100:+.2f}%)",
            f"Open positions: {len(self.positions)}",
            f"Closed trades: {total} | WR: {wr:.1f}%",
            f"Total PnL: ${total_pnl:+.2f}",
            f"Daily loss: {self.daily_loss_pct()*100:.2f}% | DD: {self.drawdown_pct()*100:.2f}%",
        ]
        if self.positions:
            lines.append("Open:")
            for p in self.positions:
                lines.append(f"  {p.bot} {p.direction} {SYMBOLS.get(p.symbol,'')} bar {p.bars_open}/{p.hold_bars}")
        msg = "\n".join(lines)
        print(msg)
        return msg

    def run(self):
        print(f"Live Sim started | Account: ${ACCOUNT_SIZE:,.0f} | Checking every {CHECK_INTERVAL}s")
        send_telegram(f"LIVE SIM STARTED\nAccount: ${ACCOUNT_SIZE:,.0f}\n9 bots active | FVG Sentinel (XAUUSD+GBPUSD) | FTMO rules enabled")

        while True:
            self.bar_count += 1
            self.reset_day()
            now = datetime.utcnow().strftime("%H:%M:%S")

            print(f"\n[{now}] Bar #{self.bar_count} | Equity: ${self.equity:,.2f}", end=" ")

            data = {}
            for ticker in SYMBOLS:
                df = self.fetch_data(ticker)
                if df is not None:
                    data[ticker] = df

            self.close_positions(data)

            if self.is_locked():
                print("| PORTFOLIO LOCKED")
            else:
                self.open_positions(data)
                print(f"| Positions: {len(self.positions)}")

            if self.bar_count % 10 == 0:
                msg = self.status_report()
                send_telegram(msg)

            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    sim = LiveSim()
    sim.run()
