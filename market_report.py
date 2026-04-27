"""
Market Report — דוח שוק מלא לטלגרם
שולח את כל הנכסים עם RSI + כיוון, כל 15 דקות
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
CHAT_ID = os.getenv("ALL_CHAT_ID", "1246833993")

ASSETS = {
    # מדדים
    "NAS100":  {"symbol": "^NDX",      "group": "Indices"},
    "S&P500":  {"symbol": "^GSPC",     "group": "Indices"},
    "DOW":     {"symbol": "^DJI",      "group": "Indices"},
    "DAX":     {"symbol": "^GDAXI",    "group": "Indices"},
    "Nikkei":  {"symbol": "^N225",     "group": "Indices"},
    # סחורות
    "XAUUSD":  {"symbol": "GC=F",      "group": "Commodities"},
    "XAGUSD":  {"symbol": "SI=F",      "group": "Commodities"},
    "WTI":     {"symbol": "CL=F",      "group": "Commodities"},
    "Brent":   {"symbol": "BZ=F",      "group": "Commodities"},
    "NatGas":  {"symbol": "NG=F",      "group": "Commodities"},
    # פורקס
    "EURUSD":  {"symbol": "EURUSD=X",  "group": "Forex"},
    "GBPUSD":  {"symbol": "GBPUSD=X",  "group": "Forex"},
    "USDJPY":  {"symbol": "JPY=X",     "group": "Forex"},
    "AUDUSD":  {"symbol": "AUDUSD=X",  "group": "Forex"},
    "USDCAD":  {"symbol": "CAD=X",     "group": "Forex"},
    "USDCHF":  {"symbol": "CHF=X",     "group": "Forex"},
    "EURGBP":  {"symbol": "EURGBP=X",  "group": "Forex"},
    # קריפטו
    "BTCUSD":  {"symbol": "BTC-USD",   "group": "Crypto"},
    "ETHUSD":  {"symbol": "ETH-USD",   "group": "Crypto"},
}

INTERVAL = 15 * 60  # כל 15 דקות

GROUP_EMOJI = {
    "Indices":    "📊",
    "Commodities": "🛢",
    "Forex":      "💱",
    "Crypto":     "🔶",
}


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    return round(100 - 100 / (1 + rs.iloc[-1]), 1)


def scan_asset(name: str, info: dict) -> dict:
    try:
        h = yf.Ticker(info["symbol"]).history(period="3d", interval="15m")
        if len(h) < 20:
            return {"name": name, "group": info["group"], "error": True}

        close = h["Close"]
        price = round(close.iloc[-1], 4)
        rsi   = compute_rsi(close)
        ma20  = round(close.rolling(20).mean().iloc[-1], 4)

        if rsi < 30:
            signal = "LONG"
            label  = "Oversold"
        elif rsi < 35:
            signal = "LONG"
            label  = "Weak Long"
        elif rsi > 70:
            signal = "SHORT"
            label  = "Overbought"
        elif rsi > 65:
            signal = "SHORT"
            label  = "Weak Short"
        elif price > ma20 and 48 < rsi < 65:
            signal = "LONG"
            label  = "Momentum"
        elif price < ma20 and 35 < rsi < 52:
            signal = "SHORT"
            label  = "Neg. Momentum"
        else:
            signal = "WAIT"
            label  = "Neutral"

        return {
            "name":   name,
            "group":  info["group"],
            "price":  price,
            "rsi":    rsi,
            "signal": signal,
            "label":  label,
            "error":  False,
        }
    except Exception:
        return {"name": name, "group": info["group"], "error": True}


def signal_icon(signal: str) -> str:
    return {"LONG": "🟢", "SHORT": "🔴", "WAIT": "⚪"}.get(signal, "⚪")


async def send_report(results: list):
    import telegram
    bot = telegram.Bot(token=TOKEN)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ספירת סיגנלים
    longs  = [r for r in results if r.get("signal") == "LONG"]
    shorts = [r for r in results if r.get("signal") == "SHORT"]
    waits  = [r for r in results if r.get("signal") == "WAIT"]

    msg  = f"*דוח שוק — {now}*\n"
    msg += f"🟢 LONG: {len(longs)} | 🔴 SHORT: {len(shorts)} | ⚪ ממתין: {len(waits)}\n"
    msg += "─" * 28 + "\n\n"

    # קיבוץ לפי קבוצה
    groups = {}
    for r in results:
        g = r["group"]
        groups.setdefault(g, []).append(r)

    for group, items in groups.items():
        emoji = GROUP_EMOJI.get(group, "•")
        msg += f"{emoji} *{group}*\n"
        for r in items:
            if r.get("error"):
                msg += f"  • {r['name']:8} — שגיאה\n"
                continue
            icon = signal_icon(r["signal"])
            msg += f"  {icon} {r['name']:8} | {r['signal']:5} | RSI {r['rsi']:4} | {r['label']}\n"
            msg += f"      מחיר: {r['price']}\n"
        msg += "\n"

    msg += "_DYOR — Not financial advice_"

    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    print(f"[{now}] דוח נשלח — {len(results)} נכסים")


def run_once():
    now = datetime.now().strftime("%H:%M")
    print(f"\n[{now}] סורק {len(ASSETS)} נכסים...")
    results = []
    for name, info in ASSETS.items():
        r = scan_asset(name, info)
        results.append(r)
        if r.get("error"):
            print(f"  {name:10} — שגיאה")
        else:
            print(f"  {r['signal']:5} {name:10} | RSI {r['rsi']}")

    asyncio.run(send_report(results))


if __name__ == "__main__":
    print("=" * 50)
    print(f"Market Report — {len(ASSETS)} נכסים")
    print(f"שולח כל {INTERVAL // 60} דקות | Chat: {CHAT_ID}")
    print("=" * 50)
    while True:
        run_once()
        time.sleep(INTERVAL)
