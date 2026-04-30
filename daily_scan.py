"""
DAILY SCAN — סורק פעמיים ביום
1. בודק תקינות: entry_monitor חי? Circuit Breaker לא נעול? EA באוויר?
2. סורק RSS של מקורות כלכליים — מביא כותרות אחרונות
3. שולח דוח לטלגרם
Usage: python daily_scan.py
Task Scheduler: 08:00 + 20:00
"""

import sys, os, json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA"
CHAT_ID = "1246833993"

MONITOR_DIR = Path(r"C:\Users\gfdh5555\Desktop\projects\trading-system")
LOCK_FILE = MONITOR_DIR / "circuit_breaker.lock"
PID_FILE = MONITOR_DIR / "entry_monitor.pid"
MT5_SIGNALS = Path(r"C:\Users\gfdh5555\AppData\Roaming\MetaQuotes\Terminal\Common\Files")

# RSS Feeds to scan
RSS_FEEDS = [
    ("ForexLive", "https://www.forexlive.com/feed/"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories"),
    ("Investing.com", "https://www.investing.com/rss/news.rss"),
]


def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"[ERR] Telegram: {e}")


def check_bot_health():
    """בדיקת תקינות: entry_monitor, Circuit Breaker, MT5 signals"""
    now = datetime.now().strftime("%d/%m %H:%M")
    health = []

    health.append(f"<b>Daily Scan — {now}</b>\n")

    # 1. entry_monitor pid
    if PID_FILE.exists():
        pid = PID_FILE.read_text().strip()
        health.append(f"[OK] entry_monitor PID: {pid}")
    else:
        health.append("[WARN] entry_monitor לא רץ — PID file חסר")

    # 2. Circuit Breaker
    if LOCK_FILE.exists():
        lock_content = LOCK_FILE.read_text().strip()
        health.append(f"[LOCK] Circuit Breaker: {lock_content}")
    else:
        health.append("[OK] Circuit Breaker: מותר לסחור (אין lock)")

    # 3. MT5 signals — check if bridge files exist
    signals = list(MT5_SIGNALS.glob("signal_*.txt"))
    if signals:
        recent = max(signals, key=lambda p: p.stat().st_mtime)
        age_sec = datetime.now().timestamp() - recent.stat().st_mtime
        health.append(f"[OK] MT5 bridge: {len(signals)} signal files, last: {recent.name} ({age_sec/60:.0f} min ago)")
    else:
        health.append("[INFO] MT5 bridge: no signal files yet")

    return "\n".join(health)


def scan_rss():
    """Scan RSS feeds for latest headlines"""
    headlines = []
    
    for source, url in RSS_FEEDS[:2]:  # Limit to 2 to avoid timeout
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:3]  # Top 3 per source

            for item in items:
                title = item.find("title")
                link = item.find("link")
                if title is not None and title.text:
                    headlines.append(f"<b>{source}:</b> {title.text[:120]}")
                if len(headlines) >= 5:
                    break
        except Exception as e:
            headlines.append(f"<i>{source}: RSS unavailable</i>")

    return "\n".join(headlines) if headlines else "No RSS updates available"


def main():
    print("=" * 50)
    print(f"DAILY SCAN — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Health check
    health = check_bot_health()
    print(health)

    # RSS scan
    rss = scan_rss()
    print(f"\n[RSS Headlines]\n{rss}")

    # Send to Telegram
    full_msg = f"{health}\n\n<b>Latest Headlines:</b>\n{rss}"
    send_telegram(full_msg)

    print("\n[OK] Report sent to Telegram")


if __name__ == "__main__":
    main()