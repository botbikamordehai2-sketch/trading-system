"""
💎 DIAMOND SCANNER — מוצא את ההזדמנויות הטובות ביותר
סורק כל הצמדים, מדדים וסחורות ומדרג לפי Confluence Score
"""

import sys, asyncio, os
from datetime import datetime
from pathlib import Path
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(Path.home() / "tv_webhook" / ".env")

# ─────────────────────────────────────────────────────────────
# רשימת נכסים מלאה
# ─────────────────────────────────────────────────────────────
ASSETS = {
    # ── Indices ──────────────────────────────────────────────
    "NAS100":  {"symbol": "^IXIC",    "group": "📊 Indices",    "pip": 1},
    "S&P500":  {"symbol": "^GSPC",    "group": "📊 Indices",    "pip": 1},
    "DOW":     {"symbol": "^DJI",     "group": "📊 Indices",    "pip": 1},
    "DAX":     {"symbol": "^GDAXI",   "group": "📊 Indices",    "pip": 1},
    "FTSE100": {"symbol": "^FTSE",    "group": "📊 Indices",    "pip": 1},
    "Nikkei":  {"symbol": "^N225",    "group": "📊 Indices",    "pip": 1},

    # ── Commodities ───────────────────────────────────────────
    "XAUUSD":  {"symbol": "GC=F",     "group": "🥇 Commodities","pip": 0.1},
    "XAGUSD":  {"symbol": "SI=F",     "group": "🥇 Commodities","pip": 0.01},
    "WTI Oil": {"symbol": "CL=F",     "group": "🥇 Commodities","pip": 0.01},
    "Brent":   {"symbol": "BZ=F",     "group": "🥇 Commodities","pip": 0.01},
    "Nat Gas": {"symbol": "NG=F",     "group": "🥇 Commodities","pip": 0.01},
    "Copper":  {"symbol": "HG=F",     "group": "🥇 Commodities","pip": 0.01},

    # ── Forex Majors ──────────────────────────────────────────
    "EURUSD":  {"symbol": "EURUSD=X", "group": "💱 Forex",      "pip": 0.0001},
    "GBPUSD":  {"symbol": "GBPUSD=X", "group": "💱 Forex",      "pip": 0.0001},
    "USDJPY":  {"symbol": "JPY=X",    "group": "💱 Forex",      "pip": 0.01},
    "AUDUSD":  {"symbol": "AUDUSD=X", "group": "💱 Forex",      "pip": 0.0001},
    "USDCAD":  {"symbol": "CAD=X",    "group": "💱 Forex",      "pip": 0.0001},
    "NZDUSD":  {"symbol": "NZDUSD=X", "group": "💱 Forex",      "pip": 0.0001},
    "USDCHF":  {"symbol": "CHF=X",    "group": "💱 Forex",      "pip": 0.0001},
    "EURGBP":  {"symbol": "EURGBP=X", "group": "💱 Forex",      "pip": 0.0001},

    # ── Crypto ────────────────────────────────────────────────
    "BTCUSD":  {"symbol": "BTC-USD",  "group": "🪙 Crypto",     "pip": 1},
    "ETHUSD":  {"symbol": "ETH-USD",  "group": "🪙 Crypto",     "pip": 0.1},
}

MACRO = {
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "10Y": "^TNX",
}


# ─────────────────────────────────────────────────────────────
# חישובים טכניים
# ─────────────────────────────────────────────────────────────
def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    return round(100 - 100 / (1 + rs.iloc[-1]), 1)


def compute_atr(high, low, close, period: int = 14) -> float:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return round(tr.rolling(period).mean().iloc[-1], 4)


def fetch_asset(name: str, info: dict) -> dict | None:
    try:
        t    = yf.Ticker(info["symbol"])
        hist = t.history(period="60d", interval="1d")
        if hist.empty or len(hist) < 20:
            return None

        close = hist["Close"]
        high  = hist["High"]
        low   = hist["Low"]

        price   = round(close.iloc[-1], 4)
        prev    = round(close.iloc[-2], 4)
        chg_pct = round((price - prev) / prev * 100, 2)

        ma20 = round(close.rolling(20).mean().iloc[-1], 4)
        ma50 = round(close.rolling(50).mean().iloc[-1], 4) if len(close) >= 50 else ma20
        rsi  = compute_rsi(close)
        atr  = compute_atr(high, low, close)

        # ── Higher High / Lower Low (3 candles) ──────────────
        hh = close.iloc[-1] > close.iloc[-2] > close.iloc[-3]
        ll = close.iloc[-1] < close.iloc[-2] < close.iloc[-3]

        # ── Volatility breakout ───────────────────────────────
        avg_range = (high - low).rolling(10).mean().iloc[-1]
        today_range = high.iloc[-1] - low.iloc[-1]
        vol_break = today_range > avg_range * 1.5

        return {
            "name":      name,
            "group":     info["group"],
            "price":     price,
            "chg_pct":   chg_pct,
            "ma20":      ma20,
            "ma50":      ma50,
            "rsi":       rsi,
            "atr":       round(atr, 4),
            "hh":        hh,
            "ll":        ll,
            "vol_break": vol_break,
        }
    except Exception as e:
        return None


# ─────────────────────────────────────────────────────────────
# ציון יהלום — Confluence Score (0–8)
# ─────────────────────────────────────────────────────────────
def diamond_score(a: dict, macro: dict) -> tuple[int, str, list]:
    score  = 0
    bias   = "NEUTRAL"
    bull   = 0
    bear   = 0
    signals = []

    dxy_bull = macro.get("DXY", 0) < 0   # DXY ירד → bullish לרוב הנכסים
    vix_bull = macro.get("VIX", 0) < 0   # VIX ירד → risk-on
    y10_bull = macro.get("10Y", 0) < 0   # תשואות ירדו → bullish

    price = a["price"]
    is_usd_quoted = a["name"] not in ["USDJPY","USDCAD","USDCHF","DXY"]

    # ── Trend ────────────────────────────────────────────────
    if price > a["ma20"] > a["ma50"]:
        bull += 2; score += 2; signals.append("✅ Price>MA20>MA50 (Uptrend)")
    elif price < a["ma20"] < a["ma50"]:
        bear += 2; score += 2; signals.append("✅ Price<MA20<MA50 (Downtrend)")

    # ── Momentum RSI ─────────────────────────────────────────
    if 50 < a["rsi"] < 70:
        bull += 1; score += 1; signals.append(f"✅ RSI {a['rsi']} (Bull momentum)")
    elif 30 < a["rsi"] < 50:
        bear += 1; score += 1; signals.append(f"✅ RSI {a['rsi']} (Bear momentum)")
    elif a["rsi"] < 30:
        bull += 1; score += 1; signals.append(f"⚡ RSI {a['rsi']} (Oversold — reversal?)")
    elif a["rsi"] > 70:
        bear += 1; score += 1; signals.append(f"⚡ RSI {a['rsi']} (Overbought — reversal?)")

    # ── Higher High / Lower Low ───────────────────────────────
    if a["hh"]:
        bull += 1; score += 1; signals.append("✅ HH structure (3 candles)")
    elif a["ll"]:
        bear += 1; score += 1; signals.append("✅ LL structure (3 candles)")

    # ── Volatility breakout ───────────────────────────────────
    if a["vol_break"]:
        score += 1; signals.append("⚡ Volatility Breakout (ATR x1.5)")

    # ── Macro correlation ─────────────────────────────────────
    group = a["group"]
    if "Commodities" in group or "Crypto" in group:
        if dxy_bull and vix_bull:
            bull += 1; score += 1; signals.append("✅ DXY+VIX bullish for commodities")
        elif not dxy_bull and not vix_bull:
            bear += 1; score += 1; signals.append("✅ DXY+VIX bearish for commodities")
    elif "Indices" in group:
        if vix_bull and y10_bull:
            bull += 1; score += 1; signals.append("✅ VIX+10Y bullish for indices")
        elif not vix_bull:
            bear += 1; score += 1; signals.append("✅ VIX rising = risk-off for indices")
    elif "Forex" in group and is_usd_quoted:
        if not dxy_bull:
            bull += 1; score += 1; signals.append("✅ DXY up = USD strong")
        else:
            bear += 1; score += 1; signals.append("✅ DXY down = USD weak")

    bias = "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "NEUTRAL")
    return score, bias, signals


# ─────────────────────────────────────────────────────────────
# MAIN SCAN
# ─────────────────────────────────────────────────────────────
def run_scan():
    print("\n" + "="*60)
    print(f"💎 DIAMOND SCANNER — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*60)

    # Macro
    print("\n[1/3] Macro indicators...")
    macro_chg = {}
    for name, sym in MACRO.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            chg = round((h["Close"].iloc[-1] - h["Close"].iloc[-2]) /
                         h["Close"].iloc[-2] * 100, 2)
            macro_chg[name] = chg
            print(f"  {name}: {chg:+.2f}%")
        except:
            macro_chg[name] = 0

    # Assets
    print(f"\n[2/3] Scanning {len(ASSETS)} assets...")
    results = []
    for name, info in ASSETS.items():
        a = fetch_asset(name, info)
        if a:
            sc, bias, signals = diamond_score(a, macro_chg)
            a.update({"score": sc, "bias": bias, "signals": signals})
            results.append(a)
            print(f"  {name:10} | {bias:8} | Score: {sc} | RSI: {a['rsi']}")

    # מיון לפי ציון
    results.sort(key=lambda x: x["score"], reverse=True)

    # יהלומים — TOP 5
    diamonds = results[:5]

    print(f"\n[3/3] TOP DIAMONDS:")
    print("─"*60)
    for i, d in enumerate(diamonds, 1):
        emoji = ["💎","🥇","🥈","🥉","🏅"][i-1]
        print(f"\n{emoji} #{i} {d['name']} ({d['group']})")
        print(f"   Bias: {d['bias']} | Score: {d['score']}/8 | RSI: {d['rsi']}")
        print(f"   Price: {d['price']} | Change: {d['chg_pct']:+.2f}%")
        for s in d['signals'][:3]:
            print(f"   {s}")

    # שמירת דוח
    _save_report(results, diamonds, macro_chg)

    # שליחת Telegram
    _send_telegram(diamonds, macro_chg)

    return diamonds


def _save_report(results: list, diamonds: list, macro: dict):
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    path = Path(__file__).parent / "DIAMOND_REPORT.md"

    lines = [
        f"# 💎 Diamond Report — {now}\n",
        f"## Macro Context",
        f"| | Change |",
        f"|--|--|",
    ]
    for k, v in macro.items():
        arrow = "🟢" if (k == "DXY" and v < 0) or (k == "VIX" and v < 0) or (k == "10Y" and v < 0) else "🔴"
        lines.append(f"| {k} | {arrow} {v:+.2f}% |")

    lines += ["\n## 💎 Top Diamonds\n"]
    for i, d in enumerate(diamonds, 1):
        lines.append(f"### #{i} {d['name']} — {d['bias']} (Score: {d['score']}/8)")
        lines.append(f"- Price: {d['price']} | RSI: {d['rsi']} | ATR: {d['atr']}")
        lines.append(f"- Signals: {' | '.join(d['signals'][:3])}\n")

    lines += ["\n## All Assets\n", "| Asset | Group | Bias | Score | RSI | Change |",
              "|--|--|--|--|--|--|"]
    for r in results:
        lines.append(f"| {r['name']} | {r['group']} | {r['bias']} | {r['score']}/8 | {r['rsi']} | {r['chg_pct']:+.2f}% |")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n[OK] Report saved: {path}")


def _send_telegram(diamonds: list, macro: dict):
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("ALL_CHAT_ID") or os.getenv("NASDAQ_CHAT_ID")
    if not token or not chat_id:
        print("[SKIP] No Telegram credentials")
        return

    async def _send():
        import telegram
        bot  = telegram.Bot(token=token)
        now  = datetime.now().strftime("%d/%m/%Y %H:%M")

        dxy_arrow = "\U0001f7e2" if macro.get("DXY", 0) < 0 else "\U0001f534"
        vix_arrow = "\U0001f7e2" if macro.get("VIX", 0) < 0 else "\U0001f534"

        msg = f"\U0001f48e DIAMOND SCANNER — {now}\n\n"
        msg += f"Macro: DXY {dxy_arrow}{macro.get('DXY',0):+.1f}% | VIX {vix_arrow}{macro.get('VIX',0):+.1f}%\n\n"
        msg += "Top Diamonds:\n"

        emojis = ["\U0001f48e","\U0001f947","\U0001f948","\U0001f949","\U0001f3c5"]
        for i, d in enumerate(diamonds[:5], 1):
            bias_e = "\U0001f7e2" if d["bias"] == "BULLISH" else ("\U0001f534" if d["bias"] == "BEARISH" else "\U0001f7e1")
            msg += f"\n{emojis[i-1]} {d['name']} - {bias_e} {d['bias']}\n"
            msg += f"   Score: {d['score']}/8 | RSI: {d['rsi']} | {d['chg_pct']:+.2f}%\n"
            if d["signals"]:
                clean = d["signals"][0].replace("✅","").replace("⚡","").strip()
                msg += f"   {clean}\n"

        msg += "\nDYOR - Not financial advice"

        # ניסיון שליחה לכל chat_id
        chat_ids = [c for c in [os.getenv("ALL_CHAT_ID"), os.getenv("NASDAQ_CHAT_ID")] if c]
        sent = False
        for cid in chat_ids:
            try:
                await bot.send_message(chat_id=cid, text=msg)
                print(f"[OK] Telegram sent to {cid}")
                sent = True
                break
            except Exception as e:
                print(f"  [WARN] chat_id {cid}: {e}")

        if not sent:
            bot_info = await bot.get_me()
            print(f"\n[FIX NEEDED] Bot @{bot_info.username} לא שייך לאף צ'אט.")
            print("  1. פתח טלגרם")
            print(f"  2. חפש @{bot_info.username}")
            print("  3. שלח /start")
            print("  4. הרץ: python get_chat_id.py")

    try:
        asyncio.run(_send())
    except Exception as e:
        print(f"[WARN] Telegram error: {e}")


if __name__ == "__main__":
    run_scan()
