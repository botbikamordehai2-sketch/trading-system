"""
Price Alert Monitor — כל הנכסים
מחשב רמות כניסה אוטומטית ושולח התראה ברגע שמחיר מגיע
"""
import sys, asyncio, os, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import yfinance as yf
import pandas as pd

load_dotenv(Path.home() / "tv_webhook" / ".env")
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "1246833993"

ASSETS = {
    # מדדים
    "NAS100":   {"symbol": "^NDX",     "group": "מדד"},
    "S&P500":   {"symbol": "^GSPC",     "group": "מדד"},
    "DOW":      {"symbol": "^DJI",      "group": "מדד"},
    "DAX":      {"symbol": "^GDAXI",    "group": "מדד"},
    "Nikkei":   {"symbol": "^N225",     "group": "מדד"},
    # סחורות
    "XAUUSD":   {"symbol": "GC=F",      "group": "סחורה"},
    "XAGUSD":   {"symbol": "SI=F",      "group": "סחורה"},
    "WTI":      {"symbol": "CL=F",      "group": "סחורה"},
    "Brent":    {"symbol": "BZ=F",      "group": "סחורה"},
    "NatGas":   {"symbol": "NG=F",      "group": "סחורה"},
    "Copper":   {"symbol": "HG=F",      "group": "סחורה"},
    # פורקס
    "EURUSD":   {"symbol": "EURUSD=X",  "group": "פורקס"},
    "GBPUSD":   {"symbol": "GBPUSD=X",  "group": "פורקס"},
    "USDJPY":   {"symbol": "JPY=X",     "group": "פורקס"},
    "AUDUSD":   {"symbol": "AUDUSD=X",  "group": "פורקס"},
    "USDCAD":   {"symbol": "CAD=X",     "group": "פורקס"},
    "USDCHF":   {"symbol": "CHF=X",     "group": "פורקס"},
    "EURGBP":   {"symbol": "EURGBP=X",  "group": "פורקס"},
    # קריפטו
    "BTCUSD":   {"symbol": "BTC-USD",   "group": "קריפטו"},
    "ETHUSD":   {"symbol": "ETH-USD",   "group": "קריפטו"},
}

fired    = {}   # {key: timestamp} — מניעת כפילות ב-4 שעות
CHECK_INTERVAL = 60   # בדיקה כל דקה


def rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    return round(100 - 100 / (1 + gain / loss.replace(0, 1e-9)).iloc[-1], 1)


def get_entry_signal(name: str, symbol: str) -> dict | None:
    try:
        h = yf.Ticker(symbol).history(period="3d", interval="15m")
        if len(h) < 20:
            return None

        close  = h["Close"]
        high   = h["High"]
        low    = h["Low"]
        price  = round(close.iloc[-1], 5)
        r      = rsi(close)
        ma20   = round(close.rolling(20).mean().iloc[-1], 5)
        ma50   = round(close.rolling(50).mean().iloc[-1], 5) if len(close) >= 50 else ma20

        support    = round(low.rolling(20).min().iloc[-1], 5)
        resistance = round(high.rolling(20).max().iloc[-1], 5)

        direction = None
        reason    = ""
        level     = None

        # ── LONG ──────────────────────────────────────────────
        if r < 30:
            direction = "LONG"
            reason    = f"RSI {r} — Oversold קיצוני"
            level     = price
        elif r < 35 and price <= support * 1.002:
            direction = "LONG"
            reason    = f"RSI {r} + מחיר על Support {support}"
            level     = support
        elif 48 < r < 65 and price > ma20 > ma50:
            direction = "LONG"
            reason    = f"RSI {r} — מומנטום + מעל MA20/MA50"
            level     = round(ma20, 5)

        # ── SHORT ─────────────────────────────────────────────
        elif r > 70:
            direction = "SHORT"
            reason    = f"RSI {r} — Overbought קיצוני"
            level     = price
        elif r > 65 and price >= resistance * 0.998:
            direction = "SHORT"
            reason    = f"RSI {r} + מחיר על Resistance {resistance}"
            level     = resistance
        elif 35 < r < 52 and price < ma20 < ma50:
            direction = "SHORT"
            reason    = f"RSI {r} — מומנטום שלילי + מתחת MA20/MA50"
            level     = round(ma20, 5)

        if not direction:
            return None

        # מניעת כפילות ב-4 שעות
        key = f"{name}_{direction}"
        last = fired.get(key, 0)
        if time.time() - last < 14400:
            return None

        return {
            "name":      name,
            "direction": direction,
            "price":     price,
            "level":     level,
            "rsi":       r,
            "ma20":      ma20,
            "support":   support,
            "resistance": resistance,
            "reason":    reason,
        }
    except:
        return None


async def send_telegram(signals: list):
    import telegram
    bot = telegram.Bot(token=TOKEN)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    msg = f"התראת כניסה — {now}\n"
    msg += f"{len(signals)} סיגנלים פעילים\n"
    msg += "=" * 30 + "\n\n"

    for s in signals:
        action = "קנה" if s["direction"] == "LONG" else "מכור"
        msg += f"{s['direction']} {s['name']} — {action}\n"
        msg += f"מחיר: {s['price']} | RSI: {s['rsi']}\n"
        msg += f"סיבה: {s['reason']}\n"
        msg += f"כניסה: {s['level']}\n"
        msg += "-" * 25 + "\n"

    msg += "\nDYOR — לא המלצת השקעה"
    await bot.send_message(chat_id=CHAT_ID, text=msg)


def scan():
    now = datetime.now().strftime("%H:%M")
    print(f"\n[{now}] סורק {len(ASSETS)} נכסים...")
    signals = []

    for name, info in ASSETS.items():
        sig = get_entry_signal(name, info["symbol"])
        if sig:
            signals.append(sig)
            fired[f"{name}_{sig['direction']}"] = time.time()
            print(f"  SIGNAL: {sig['direction']:5} {name:10} | RSI:{sig['rsi']} | {sig['reason']}")
        else:
            print(f"  -----  {name:10} | ללא סיגנל")

    if signals:
        asyncio.run(send_telegram(signals))
        print(f"\n  [{now}] נשלחו {len(signals)} התראות לטלגרם!")
    else:
        print(f"\n  [{now}] אין סיגנלים — הבא בעוד {CHECK_INTERVAL} שניות")


if __name__ == "__main__":
    print("=" * 50)
    print(f"Price Alert Monitor — {len(ASSETS)} נכסים")
    print(f"בדיקה כל {CHECK_INTERVAL} שניות | Chat: {CHAT_ID}")
    print("=" * 50)
    while True:
        scan()
        time.sleep(CHECK_INTERVAL)
