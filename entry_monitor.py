"""
Entry Monitor — מנטר הזדמנויות כניסה ושולח התראת טלגרם
רץ כל 15 דקות, שולח רק כשיש סיגנל אמיתי
"""
import sys, asyncio, os, time
from datetime import datetime
from pathlib import Path
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(Path.home() / "tv_webhook" / ".env")

ASSETS = {
    "NAS100":  {"symbol": "^NDX",    "group": "Indices"},
    "S&P500":  {"symbol": "^GSPC",    "group": "Indices"},
    "DOW":     {"symbol": "^DJI",     "group": "Indices"},
    "Nikkei":  {"symbol": "^N225",    "group": "Indices"},
    "XAUUSD":  {"symbol": "GC=F",     "group": "Commodities"},
    "XAGUSD":  {"symbol": "SI=F",     "group": "Commodities"},
    "WTI":     {"symbol": "CL=F",     "group": "Commodities"},
    "EURUSD":  {"symbol": "EURUSD=X", "group": "Forex"},
    "GBPUSD":  {"symbol": "GBPUSD=X", "group": "Forex"},
    "USDJPY":  {"symbol": "JPY=X",    "group": "Forex"},
    "AUDUSD":  {"symbol": "AUDUSD=X", "group": "Forex"},
    "BTCUSD":  {"symbol": "BTC-USD",  "group": "Crypto"},
}

INTERVAL   = 15 * 60   # 15 דקות
CHAT_ID    = os.getenv("ALL_CHAT_ID", os.getenv("NASDAQ_CHAT_ID", "1246833993"))
TOKEN      = os.getenv("TELEGRAM_TOKEN")

alerted = {}   # מניעת כפילויות: {asset: last_signal}


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    return round(100 - 100 / (1 + rs.iloc[-1]), 1)


def check_entry(name: str, info: dict) -> dict | None:
    try:
        h    = yf.Ticker(info["symbol"]).history(period="5d", interval="15m")
        if h.empty or len(h) < 20:
            return None

        close = h["Close"]
        high  = h["High"]
        low   = h["Low"]

        price = round(close.iloc[-1], 4)
        rsi   = compute_rsi(close)
        ma20  = round(close.rolling(20).mean().iloc[-1], 4)

        signals = []
        direction = None

        # ── LONG signals ──────────────────────────────────────
        if 50 < rsi < 65 and price > ma20:
            signals.append(f"RSI {rsi} + מעל MA20")
            direction = "LONG"

        if rsi < 32:
            signals.append(f"RSI {rsi} Oversold — ריבאונד?")
            direction = "LONG"

        # מחיר חצה MA20 מלמטה (2 נרות אישור)
        prev_below = close.iloc[-3] < close.rolling(20).mean().iloc[-3]
        now_above  = price > ma20
        if prev_below and now_above and rsi < 65:
            signals.append("Cross above MA20")
            direction = "LONG"

        # ── SHORT signals ─────────────────────────────────────
        if rsi > 72 and price < ma20:
            signals.append(f"RSI {rsi} Overbought + מתחת MA20")
            direction = "SHORT"

        if rsi > 78:
            signals.append(f"RSI {rsi} Extreme Overbought")
            direction = "SHORT"

        # מחיר חצה MA20 מלמעלה
        prev_above = close.iloc[-3] > close.rolling(20).mean().iloc[-3]
        now_below  = price < ma20
        if prev_above and now_below and rsi > 35:
            signals.append("Cross below MA20")
            direction = "SHORT"

        if not signals or not direction:
            return None

        # מניעת כפילות — אותו סיגנל לא ישלח פעמיים ב-2 שעות
        key = f"{name}_{direction}"
        last = alerted.get(key, 0)
        if time.time() - last < 7200:
            return None

        alerted[key] = time.time()

        return {
            "name":      name,
            "group":     info["group"],
            "direction": direction,
            "price":     price,
            "rsi":       rsi,
            "ma20":      ma20,
            "signals":   signals,
        }

    except Exception as e:
        return None


async def send_alert(entries: list):
    import telegram
    bot = telegram.Bot(token=TOKEN)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    msg = f"*ENTRY ALERT — {now}*\n"
    msg += f"_{len(entries)} הזדמנות{'ות' if len(entries)>1 else ''} נמצאה_\n\n"

    for e in entries:
        arrow = "BUY" if e["direction"] == "LONG" else "SELL"
        emoji = "" if e["direction"] == "LONG" else ""
        msg += f"{emoji} *{e['name']}* — {arrow}\n"
        msg += f"   Price: {e['price']} | RSI: {e['rsi']}\n"
        for s in e["signals"]:
            msg += f"   • {s}\n"
        msg += "\n"

    msg += "_DYOR — Not financial advice_"

    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    print(f"[ALERT] נשלח! {[e['name'] for e in entries]}")


def run_once():
    print(f"\n[{datetime.now().strftime('%H:%M')}] סורק כניסות...")
    entries = []
    for name, info in ASSETS.items():
        result = check_entry(name, info)
        if result:
            entries.append(result)
            print(f"  SIGNAL: {name} {result['direction']} | RSI:{result['rsi']}")
        else:
            print(f"  {name:10} — אין סיגנל")

    if entries:
        asyncio.run(send_alert(entries))
    else:
        print(f"  -> אין כניסות כרגע. הבא: {INTERVAL//60} דקות")


if __name__ == "__main__":
    print("="*50)
    print(f"Entry Monitor פעיל — כל {INTERVAL//60} דקות")
    print(f"נכסים: {len(ASSETS)} | Chat: {CHAT_ID}")
    print("="*50)
    while True:
        run_once()
        time.sleep(INTERVAL)
