"""
Entry Monitor — מנטר הזדמנויות כניסה ושולח התראת טלגרם
רץ כל 15 דקות, שולח רק כשיש סיגנל אמיתי
"""
import sys, asyncio, os, time, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(Path.home() / "tv_webhook" / ".env")

ASSETS = {
    # מדדים
    "US100":   {"symbol": "^NDX",     "group": "Indices"},
    "US500":   {"symbol": "^GSPC",    "group": "Indices"},
    # סחורות
    "XAUUSD":  {"symbol": "GC=F",     "group": "Commodities"},
    "XAGUSD":  {"symbol": "SI=F",     "group": "Commodities"},
    "USOIL":   {"symbol": "CL=F",     "group": "Commodities"},
    # פורקס — עיקריים
    "EURUSD":  {"symbol": "EURUSD=X", "group": "Forex"},
    "GBPUSD":  {"symbol": "GBPUSD=X", "group": "Forex"},
    "USDJPY":  {"symbol": "JPY=X",    "group": "Forex"},
    "USDCHF":  {"symbol": "USDCHF=X", "group": "Forex"},
    "USDCAD":  {"symbol": "USDCAD=X", "group": "Forex"},
    "AUDUSD":  {"symbol": "AUDUSD=X", "group": "Forex"},
    # פורקס — AUD crosses
    "AUDNZD":  {"symbol": "AUDNZD=X", "group": "Forex"},
    "AUDCAD":  {"symbol": "AUDCAD=X", "group": "Forex"},
    "AUDCHF":  {"symbol": "AUDCHF=X", "group": "Forex"},
    "AUDJPY":  {"symbol": "AUDJPY=X", "group": "Forex"},
}

INTERVAL   = 15 * 60   # 15 דקות
CHAT_ID    = os.getenv("ALL_CHAT_ID", os.getenv("NASDAQ_CHAT_ID", "1246833993"))
TOKEN      = os.getenv("TELEGRAM_TOKEN")

MT5_FILES  = r"C:\Users\gfdh5555\AppData\Roaming\MetaQuotes\Terminal\Common\Files"

MT5_SYMBOL_MAP = {
    "US100":  "US100.cash",
    "US500":  "US500.cash",
    "XAUUSD": "XAUUSD",
    "XAGUSD": "XAGUSD",
    "USOIL":  "USOIL.cash",
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "USDCHF": "USDCHF",
    "USDCAD": "USDCAD",
    "AUDUSD": "AUDUSD",
    "AUDNZD": "AUDNZD",
    "AUDCAD": "AUDCAD",
    "AUDCHF": "AUDCHF",
    "AUDJPY": "AUDJPY",
}

alerted = {}   # מניעת כפילויות: {asset: last_signal}
_news_cache = {"time": 0, "events": []}  # cache ל-15 דקות


def get_high_impact_news(within_hours: int = 2) -> str | None:
    """מחזיר שם האירוע אם יש HIGH impact event ב-N שעות הקרובות, אחרת None"""
    global _news_cache
    now_ts = time.time()

    # cache — מרענן כל 15 דקות
    if now_ts - _news_cache["time"] > 900:
        try:
            r = requests.get(
                "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                timeout=5
            )
            _news_cache = {"time": now_ts, "events": r.json()}
        except:
            return None  # אם API נכשל — לא חוסמים

    now_utc = datetime.now(timezone.utc)
    cutoff  = now_utc + timedelta(hours=within_hours)

    for ev in _news_cache["events"]:
        if ev.get("impact") != "High":
            continue
        try:
            ev_time = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            if now_utc <= ev_time <= cutoff:
                return ev.get("title", "HIGH NEWS")
        except:
            continue
    return None


def write_mt5_signal(name: str, direction: str):
    mt5_sym = MT5_SYMBOL_MAP.get(name)
    if not mt5_sym:
        return
    path = os.path.join(MT5_FILES, f"signal_{mt5_sym}.txt")
    with open(path, "w") as f:
        f.write(f"{direction},{int(time.time())}")
    print(f"  [MT5 BRIDGE] {mt5_sym} {direction} → {path}")


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    return round(100 - 100 / (1 + rs.iloc[-1]), 1)


def check_entry(name: str, info: dict) -> dict | None:
    try:
        h    = yf.Ticker(info["symbol"]).history(period="5d", interval="15m")
        if h.empty or len(h) < 50:
            return None

        close = h["Close"]
        price = round(close.iloc[-1], 4)
        rsi   = compute_rsi(close)
        ma20  = close.rolling(20).mean()
        ma50  = close.rolling(50).mean()
        ma20v = round(ma20.iloc[-1], 4)
        ma50v = round(ma50.iloc[-1], 4)

        # פילטר טרנד MA50
        trend_up   = price > ma50v
        trend_down = price < ma50v

        signals = []
        direction = None

        # ── LONG signals (רק עם טרנד עולה) ───────────────────
        if trend_up:
            if rsi < 30:
                signals.append(f"RSI {rsi} Oversold — ריבאונד?")
                direction = "LONG"
            if 50 < rsi < 65 and price > ma20v:
                signals.append(f"RSI {rsi} מומנטום + מעל MA20")
                direction = "LONG"
            prev_below = close.iloc[-3] < ma20.iloc[-3]
            if prev_below and price > ma20v and rsi < 65:
                signals.append("Cross above MA20")
                direction = "LONG"

        # ── SHORT signals (רק עם טרנד יורד) ──────────────────
        if trend_down:
            if rsi > 70:
                signals.append(f"RSI {rsi} Overbought")
                direction = "SHORT"
            if rsi > 35 and rsi < 52 and price < ma20v:
                signals.append(f"RSI {rsi} מומנטום שלילי + מתחת MA20")
                direction = "SHORT"
            prev_above = close.iloc[-3] > ma20.iloc[-3]
            if prev_above and price < ma20v and rsi > 35:
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

        # פילטר חדשות — HIGH impact event ב-2 שעות הקרובות → חסום לגמרי
        news_event = get_high_impact_news(within_hours=2)
        if news_event:
            print(f"  [NEWS BLOCK] {name} — חדשות HIGH: {news_event}")
            alerted.pop(key, None)  # מאפס כדי שיישלח אחרי החדשות
            return None

        # חישוב ATR לקביעת SL/TP
        high  = h["High"]
        low   = h["Low"]
        atr   = (high - low).rolling(14).mean().iloc[-1]
        atr   = round(atr, 4)

        if direction == "LONG":
            sl = round(price - atr * 1.5, 4)
            tp = round(price + atr * 3.0, 4)
        else:
            sl = round(price + atr * 1.5, 4)
            tp = round(price - atr * 3.0, 4)

        return {
            "name":      name,
            "group":     info["group"],
            "direction": direction,
            "price":     price,
            "rsi":       rsi,
            "sl":        sl,
            "tp":        tp,
            "atr":       atr,
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
        emoji = "🟢" if e["direction"] == "LONG" else "🔴"

        # סטטוס כניסה לפי RSI
        rsi = e["rsi"]
        if e["direction"] == "LONG":
            if rsi < 30:
                status = "✅ מוכן לכניסה עכשיו"
            elif rsi < 40:
                status = "⏳ המתן לאישור — RSI מתקרב"
            else:
                status = f"⏳ המתן למחיר {e['sl']} לפני כניסה"
        else:
            if rsi > 70:
                status = "✅ מוכן לכניסה עכשיו"
            elif rsi > 60:
                status = "⏳ המתן לאישור — RSI מתקרב"
            else:
                status = f"⏳ המתן למחיר {e['sl']} לפני כניסה"

        msg += f"{emoji} *{e['name']}* — {arrow}\n"
        msg += f"   {status}\n"
        msg += f"   💰 כניסה: `{e['price']}`\n"
        msg += f"   🛑 SL: `{e['sl']}`\n"
        msg += f"   🎯 TP: `{e['tp']}`\n"
        msg += f"   📊 RSI: {rsi}\n"
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
        for e in entries:
            write_mt5_signal(e["name"], e["direction"])
            # שמירה ליומן לצורך ועדת חקירה יומית
            try:
                from daily_review import log_signal
                log_signal(e["name"], e["direction"], e["price"], e["sl"], e["tp"])
            except:
                pass
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
