"""
TELEGRAM ALERTS INTEGRATION
Sends NASDAQ BIAS, trading alerts, and system notifications
Usage: python telegram_alerts.py
Requires: pip install python-telegram-bot
"""

import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# CONFIGURATION — Fill these!
# ============================================================
# Get token from @BotFather on Telegram: https://t.me/BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Your Telegram Chat ID
# Send /start to your bot, then visit: https://api.telegram.org/bot<TOKEN>/getUpdates
CHAT_ID = "YOUR_CHAT_ID_HERE"

# ============================================================
# SIMPLE HTTP-BASED SENDER (no async deps needed for basic use)
# ============================================================
import urllib.request
import json


def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """Send a message to Telegram via Bot API"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("[ERROR] Please set BOT_TOKEN and CHAT_ID in telegram_alerts.py")
        print("1. Create bot: https://t.me/BotFather")
        print("2. Get token from BotFather")
        print("3. Get your chat ID: https://api.telegram.org/bot<TOKEN>/getUpdates")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"[OK] Message sent to Telegram")
                return True
            else:
                print(f"[ERR] Telegram API error: {result}")
                return False
    except Exception as e:
        print(f"[ERR] Failed to send: {e}")
        return False


# ============================================================
# ALERTS
# ============================================================
def send_daily_bias(bias_data: dict):
    """Send formatted NASDAQ BIAS report"""
    message = f"""<b>📊 NASDAQ DAILY BIAS</b>
📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}

<b>Live Indicators:</b>
• DXY: {bias_data.get('DXY', {}).get('value', 'N/A')} ({bias_data.get('DXY', {}).get('change_pct', 0):+.2f}%)
• VIX: {bias_data.get('VIX', {}).get('value', 'N/A')} ({bias_data.get('VIX', {}).get('change_pct', 0):+.2f}%)
• NDX: {bias_data.get('NDX', {}).get('value', 'N/A')} ({bias_data.get('NDX', {}).get('change_pct', 0):+.2f}%)
• SPX: {bias_data.get('SPX', {}).get('value', 'N/A')} ({bias_data.get('SPX', {}).get('change_pct', 0):+.2f}%)
• 10Y: {bias_data.get('10Y', {}).get('value', 'N/A')}% ({bias_data.get('10Y', {}).get('change_pct', 0):+.2f}%)

<b>🧠 BIAS: {bias_data.get('bias', 'N/A')}</b>
Score: {bias_data.get('score', '?')}/3
Details: {', '.join(bias_data.get('details', []))}

<code>{'🟢' if 'BULLISH' in str(bias_data.get('bias','')) else '🔴'}</code>
"""
    return send_telegram_message(message)


def send_simple_alert(text: str):
    """Send a simple text alert"""
    return send_telegram_message(f"⚠️ <b>Alert:</b> {text}")


def send_test_message():
    """Send a test message to verify bot works"""
    return send_telegram_message(
        f"✅ <b>Test Message</b>\n"
        f"Bot is working!\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


# ============================================================
# INTEGRATION WITH SCANNER
# ============================================================
def run_scanner_and_alert():
    """Run nasdaq_scanner.py and send results to Telegram"""
    sys.path.insert(0, str(Path(__file__).parent))
    from nasdaq_scanner import fetch_indicators, calculate_bias

    # Pull data
    indicators = fetch_indicators()
    bias, score, details = calculate_bias(indicators)

    # Package for Telegram
    bias_data = {
        "DXY": indicators.get("DXY", {}),
        "VIX": indicators.get("VIX", {}),
        "NDX": indicators.get("NDX", {}),
        "SPX": indicators.get("SPX", {}),
        "10Y": indicators.get("10Y", {}),
        "bias": bias,
        "score": score,
        "details": details,
    }

    # Send
    send_daily_bias(bias_data)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("TELEGRAM ALERTS -", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 60)

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n[!] First time setup required:")
        print("    1. Open https://t.me/BotFather in Telegram")
        print("    2. Send /newbot and create a bot")
        print("    3. Copy the token into BOT_TOKEN above")
        print("    4. Send /start to your bot")
        print("    5. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("    6. Copy the 'id' field into CHAT_ID above")
        print("\n    Then run again: python telegram_alerts.py")
    else:
        print("\n[1] Sending test message...")
        send_test_message()

        print("\n[2] Running scanner + sending BIAS...")
        run_scanner_and_alert()

        print("\n[DONE] Check Telegram!")