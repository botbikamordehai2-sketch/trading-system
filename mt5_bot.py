"""
MT5 Auto-Trading Bot — FTMO Demo Challenge
מבצע עסקאות אוטומטי ב-MT5 לפי איתותי RSI+MA20
שומר על חוקי FTMO: max daily loss 5%, max drawdown 10%
"""
import sys, time, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
import MetaTrader5 as mt5
import yfinance as yf
import pandas as pd

load_dotenv(Path.home() / "tv_webhook" / ".env")

# ─── הגדרות FTMO ──────────────────────────────────────────
ACCOUNT_SIZE    = 10_000   # גודל חשבון (שנה לפי FTMO שלך)
RISK_PER_TRADE  = 0.01     # 1% ריסק לעסקה
MAX_DAILY_LOSS  = 0.045    # 4.5% — עצור לפני שגיעים ל-5% של FTMO
MAX_DRAWDOWN    = 0.09     # 9% — עצור לפני 10% של FTMO
SCAN_INTERVAL   = 60 * 15  # סריקה כל 15 דקות

# ─── מיפוי יאהו → MT5 symbols ────────────────────────────
ASSETS = {
    "EURUSD":  {"yf": "EURUSD=X",  "mt5": "EURUSD",  "digits": 5, "sl_pips": 30},
    "GBPUSD":  {"yf": "GBPUSD=X",  "mt5": "GBPUSD",  "digits": 5, "sl_pips": 35},
    "USDJPY":  {"yf": "JPY=X",     "mt5": "USDJPY",  "digits": 3, "sl_pips": 30},
    "AUDUSD":  {"yf": "AUDUSD=X",  "mt5": "AUDUSD",  "digits": 5, "sl_pips": 30},
    "XAUUSD":  {"yf": "GC=F",      "mt5": "XAUUSD",  "digits": 2, "sl_pips": 200},
    "XAGUSD":  {"yf": "SI=F",      "mt5": "XAGUSD",  "digits": 3, "sl_pips": 50},
    "NAS100":  {"yf": "^NDX",      "mt5": "NAS100",  "digits": 1, "sl_pips": 150},
    "US500":   {"yf": "^GSPC",     "mt5": "US500",   "digits": 1, "sl_pips": 50},
    "BTCUSD":  {"yf": "BTC-USD",   "mt5": "BTCUSD",  "digits": 2, "sl_pips": 500},
}

# ─── מצב ─────────────────────────────────────────────────
open_trades  = set()   # {symbol} — מניעת כפילויות
daily_pnl    = 0.0
initial_balance = None


# ─── RSI ─────────────────────────────────────────────────
def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    return round(100 - 100 / (1 + rs.iloc[-1]), 1)


# ─── סיגנל ───────────────────────────────────────────────
def get_signal(name: str, yf_symbol: str) -> str | None:
    try:
        h     = yf.Ticker(yf_symbol).history(period="3d", interval="15m")
        if len(h) < 20:
            return None
        close = h["Close"]
        price = close.iloc[-1]
        rsi   = compute_rsi(close)
        ma20  = close.rolling(20).mean().iloc[-1]

        if rsi < 30:
            return "LONG"
        elif rsi < 35 and price <= close.rolling(20).min().iloc[-1] * 1.002:
            return "LONG"
        elif price > ma20 and 48 < rsi < 65:
            return "LONG"
        elif rsi > 70:
            return "SHORT"
        elif rsi > 65 and price >= close.rolling(20).max().iloc[-1] * 0.998:
            return "SHORT"
        elif price < ma20 and 35 < rsi < 52:
            return "SHORT"
        return None
    except Exception as e:
        print(f"  [signal error] {name}: {e}")
        return None


# ─── חישוב lot size ───────────────────────────────────────
def calc_lot(symbol: str, sl_pips: int) -> float:
    try:
        info    = mt5.symbol_info(symbol)
        if not info:
            return 0.01
        tick    = mt5.symbol_info_tick(symbol)
        price   = tick.ask
        pip_val = info.trade_tick_value  # ערך pip בדולר ל-0.01 lot

        risk_amount = ACCOUNT_SIZE * RISK_PER_TRADE
        lot = round(risk_amount / (sl_pips * pip_val * 100), 2)
        lot = max(info.volume_min, min(lot, info.volume_max))
        return lot
    except Exception:
        return 0.01


# ─── פתיחת עסקה ──────────────────────────────────────────
def open_trade(name: str, asset: dict, direction: str) -> bool:
    symbol  = asset["mt5"]
    sl_pips = asset["sl_pips"]
    digits  = asset["digits"]
    lot     = calc_lot(symbol, sl_pips)

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"  [no tick] {symbol}")
        return False

    if direction == "LONG":
        order_type = mt5.ORDER_TYPE_BUY
        price      = tick.ask
        sl         = round(price - sl_pips * 10 ** (-digits), digits)
        tp         = round(price + sl_pips * 2 * 10 ** (-digits), digits)
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price      = tick.bid
        sl         = round(price + sl_pips * 10 ** (-digits), digits)
        tp         = round(price - sl_pips * 2 * 10 ** (-digits), digits)

    request = {
        "action":      mt5.TRADE_ACTION_DEAL,
        "symbol":      symbol,
        "volume":      lot,
        "type":        order_type,
        "price":       price,
        "sl":          sl,
        "tp":          tp,
        "deviation":   20,
        "magic":       202600,
        "comment":     f"RSI-bot {direction}",
        "type_time":   mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"  [OPEN] {direction} {symbol} | lot:{lot} | price:{price} | SL:{sl} | TP:{tp}")
        open_trades.add(symbol)
        return True
    else:
        print(f"  [FAIL] {symbol} retcode:{result.retcode} — {result.comment}")
        return False


# ─── בדיקת חוקי FTMO ──────────────────────────────────────
def check_ftmo_rules() -> bool:
    global daily_pnl, initial_balance
    account = mt5.account_info()
    if not account:
        return False

    balance  = account.balance
    equity   = account.equity

    if initial_balance is None:
        initial_balance = balance

    # daily loss — אם הפסדנו יותר מ-4.5% היום → עצור
    if daily_pnl < -(ACCOUNT_SIZE * MAX_DAILY_LOSS):
        print(f"  [FTMO] Daily loss limit! PnL:{daily_pnl:.2f} — לא נפתח עסקאות היום")
        return False

    # max drawdown — אם equity ירד מ-9% מהבלנס ההתחלתי → עצור
    if equity < initial_balance * (1 - MAX_DRAWDOWN):
        print(f"  [FTMO] Max drawdown! Equity:{equity} Initial:{initial_balance} — עוצר הבוט")
        return False

    return True


# ─── עדכון PnL יומי ──────────────────────────────────────
def update_daily_pnl():
    global daily_pnl
    positions = mt5.positions_get()
    if positions:
        daily_pnl = sum(p.profit for p in positions)


# ─── סריקה ראשית ─────────────────────────────────────────
def run_once():
    if not check_ftmo_rules():
        return

    now = datetime.now().strftime("%H:%M")
    print(f"\n[{now}] סורק {len(ASSETS)} נכסים...")

    for name, asset in ASSETS.items():
        mt5_sym = asset["mt5"]

        # אם כבר יש עסקה פתוחה על הנכס — דלג
        existing = mt5.positions_get(symbol=mt5_sym)
        if existing:
            print(f"  [SKIP] {name} — עסקה פתוחה כבר")
            continue

        signal = get_signal(name, asset["yf"])
        if signal:
            print(f"  SIGNAL {signal} {name}")
            open_trade(name, asset, signal)
        else:
            print(f"  --- {name}")

    update_daily_pnl()


# ─── חיבור ל-MT5 ─────────────────────────────────────────
def connect_mt5() -> bool:
    if not mt5.initialize():
        print(f"[ERROR] MT5 לא אותחל: {mt5.last_error()}")
        print("וודא ש-MetaTrader5 פתוח ומחובר לחשבון FTMO Demo")
        return False

    account = mt5.account_info()
    print(f"[MT5] מחובר | חשבון: {account.login} | בלנס: {account.balance} | ברוקר: {account.company}")
    return True


# ─── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print(f"MT5 Bot — FTMO Demo Challenge")
    print(f"ריסק לעסקה: {RISK_PER_TRADE*100}% | סריקה כל {SCAN_INTERVAL//60} דקות")
    print(f"הגנת FTMO: daily {MAX_DAILY_LOSS*100}% | drawdown {MAX_DRAWDOWN*100}%")
    print("=" * 55)

    if not connect_mt5():
        sys.exit(1)

    try:
        while True:
            run_once()
            time.sleep(SCAN_INTERVAL)
    except KeyboardInterrupt:
        print("\n[STOP] הבוט הופסק ידנית")
    finally:
        mt5.shutdown()
