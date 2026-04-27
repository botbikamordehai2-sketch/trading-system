"""
שולח דוח יומי של NASDAQ BIAS לטלגרם
"""

import asyncio, os, sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# טוען .env מהטלגרם webhook הקיים
env_path = Path.home() / "tv_webhook" / ".env"
load_dotenv(env_path)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID        = os.getenv("ALL_CHAT_ID", os.getenv("NASDAQ_CHAT_ID"))


def bias_emoji(bias: str) -> str:
    return {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}.get(bias, "⚪")


async def send_daily_report(indicators: dict, bias: str, score: int,
                             details: list, blogs: dict):
    import telegram
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    emoji = bias_emoji(bias)

    # בניית הודעה
    lines = [
        f"📊 *NASDAQ DAILY BIAS — {now}*",
        f"",
        f"{emoji} *{bias}* — Score: {score}/3",
        f"",
        f"*📈 Indicators:*",
    ]

    for name, d in indicators.items():
        if "error" not in d:
            chg   = d["change_pct"]
            arrow = "🟢" if (name == "DXY" and chg < 0) or \
                           (name in ("NDX","SPX") and chg > 0) or \
                           (name == "VIX" and chg < 0) or \
                           (name == "10Y" and chg < 0) else "🔴"
            lines.append(f"  {arrow} {name}: {d['value']} ({chg:+.2f}%)")

    # Blogs summary
    bull_blogs = [k for k, v in blogs.items() if v.get("bias") == "BULLISH"]
    bear_blogs = [k for k, v in blogs.items() if v.get("bias") == "BEARISH"]

    if bull_blogs or bear_blogs:
        lines += ["", "*🌐 Blog Sentiment:*"]
        if bull_blogs:
            lines.append(f"  🟢 Bullish: {', '.join(bull_blogs[:3])}")
        if bear_blogs:
            lines.append(f"  🔴 Bearish: {', '.join(bear_blogs[:3])}")

    lines += [
        "",
        f"*💡 Signal:*",
        f"  {' \\+ '.join(details[:2])}",
        "",
        "_DYOR — Not financial advice_",
    ]

    text = "\n".join(lines)

    await bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode="Markdown",
    )
    print(f"[OK] Telegram report sent to {CHAT_ID}")


def send_report(indicators, bias, score, details, blogs):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("[SKIP] No Telegram credentials")
        return
    asyncio.run(send_daily_report(indicators, bias, score, details, blogs))


if __name__ == "__main__":
    # בדיקה עם נתונים דמה
    test_ind = {
        "DXY": {"value": 98.3, "change_pct": -0.18},
        "VIX": {"value": 18.9, "change_pct": +1.3},
        "NDX": {"value": 24836, "change_pct": +1.6},
        "SPX": {"value": 5200, "change_pct": +0.8},
        "10Y": {"value": 4.31, "change_pct": -0.2},
    }
    send_report(test_ind, "BULLISH", 2,
                ["DXY down = Tailwind", "NDX up = Momentum"],
                {"ZeroHedge": {"bias": "BEARISH"}, "MarketWatch": {"bias": "BULLISH"}})
