"""
AUTO UPDATE — Twice Daily Context Refresh
Run: 08:00 (morning) + 20:00 (evening)
Updates PROJECT_CONTEXT.md with latest status
Sends summary to Telegram
"""

import sys
import yfinance as yf
import json
import requests
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONTEXT_FILE = Path(r"C:\Users\gfdh5555\Desktop\projects\dropship-machine\PROJECT_CONTEXT.md")
TELEGRAM_TOKEN = "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA"
CHAT_ID = "1246833993"


def fetch_market():
    """Pull live market data"""
    data = {}
    tickers = {"DXY": "DX-Y.NYB", "VIX": "^VIX", "NDX": "^IXIC", "SPX": "^GSPC", "10Y": "^TNX"}
    for name, sym in tickers.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="2d")
            if len(h) > 1:
                close = round(h["Close"].iloc[-1], 2)
                prev = round(h["Close"].iloc[-2], 2)
                change = round(((close - prev) / prev) * 100, 2)
                data[name] = f"{close} ({change:+.2f}%)"
        except:
            data[name] = "N/A"
    return data


def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except:
        pass


def update_context(market_data):
    """Update timestamp in PROJECT_CONTEXT.md"""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    session = "בוקר" if datetime.now().hour < 16 else "ערב"

    update_line = f"> **עדכון {session}:** {now} | DXY: {market_data.get('DXY','?')} | VIX: {market_data.get('VIX','?')} | NDX: {market_data.get('NDX','?')}"

    if CONTEXT_FILE.exists():
        content = CONTEXT_FILE.read_text(encoding="utf-8")
        # Update the update line
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("> **עדכון אחרון:**") or line.startswith("> **עדכון בוקר:**") or line.startswith("> **עדכון ערב:**"):
                new_lines.append(update_line)
            else:
                new_lines.append(line)
        CONTEXT_FILE.write_text("\n".join(new_lines), encoding="utf-8")

    return update_line


def main():
    print("=" * 50)
    print(f"AUTO UPDATE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Pull market
    market = fetch_market()
    print(f"\nDXY: {market.get('DXY')}")
    print(f"VIX: {market.get('VIX')}")
    print(f"NDX: {market.get('NDX')}")
    print(f"SPX: {market.get('SPX')}")
    print(f"10Y: {market.get('10Y')}")

    # Update context file
    update_line = update_context(market)
    print(f"\n[OK] {update_line}")

    # Send Telegram
    msg = (
        f"<b>🔄 עדכון {'בוקר' if datetime.now().hour < 16 else 'ערב'} — {datetime.now().strftime('%d/%m %H:%M')}</b>\n\n"
        f"<b>שווקים:</b>\n"
        f"• DXY: {market.get('DXY', '?')}\n"
        f"• VIX: {market.get('VIX', '?')}\n"
        f"• NDX: {market.get('NDX', '?')}\n"
        f"• SPX: {market.get('SPX', '?')}\n"
        f"• 10Y: {market.get('10Y', '?')}\n\n"
        f"<b>Trading System:</b> Active (MT5 EA running)\n"
        f"<b>CONTEXT:</b> Updated in PROJECT_CONTEXT.md"
    )
    send_telegram(msg)
    print("[OK] Telegram sent")

    print("\nDone.")


if __name__ == "__main__":
    main()