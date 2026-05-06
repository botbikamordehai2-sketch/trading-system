"""
🚨 Alert Engine — Proactive Sense→Think→Act System
Checks conditions and sends Telegram alerts automatically.

Triggers:
  - Trading: Killzone approaching, high win rate, risk alerts
  - SEO: Post indexing status
  - Conversion: New affiliate clicks, VIP subscriptions

Run: python alert_engine.py (every 30 minutes via Task Scheduler)
"""
import sys
import json
import os
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ──────────────────────────────────────────────────
PROJ_DIR  = Path(__file__).parent
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA")
CHAT_ID   = os.getenv("ALL_CHAT_ID", "1246833993")
BIAS_FILE = PROJ_DIR / "bias.json"
VIP_FILE  = PROJ_DIR / "vip_subscribers.json"
ALERT_LOG = PROJ_DIR / "alerts_sent.json"

alerts_sent = {}
if ALERT_LOG.exists():
    alerts_sent = json.loads(ALERT_LOG.read_text(encoding="utf-8"))


def send_alert(title: str, message: str, priority: str = "MEDIUM"):
    """Send Telegram alert. Deduplicates same alert within 12 hours."""
    key = title.replace(" ", "_").lower()
    now = datetime.now()
    last = alerts_sent.get(key, "2000-01-01T00:00:00")
    if (now - datetime.fromisoformat(last)).total_seconds() < 43200:  # 12 hours
        return  # Already sent recently

    emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵", "INFO": "ℹ️"}
    e = emoji.get(priority, "ℹ️")
    msg = f"{e} *{title}*\n\n{message}"

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=5,
        )
        alerts_sent[key] = now.isoformat()
        ALERT_LOG.write_text(json.dumps(alerts_sent, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ Alert sent: {title}")
    except Exception as e:
        print(f"  ❌ Alert failed: {e}")


# ═══════════════════════════════════════════════════════════
# TRADING TRIGGERS
# ═══════════════════════════════════════════════════════════
def check_trading_triggers():
    """Check bias.json for actionable trading alerts"""
    if not BIAS_FILE.exists():
        return

    bias = json.loads(BIAS_FILE.read_text(encoding="utf-8"))
    risk = bias.get("risk_level", "MEDIUM")
    killzone = bias.get("killzone_advice", "CAUTION")
    confidence = bias.get("confidence", 0)

    # Trigger 1: Killzone is TRADE
    if killzone == "TRADE":
        send_alert(
            "⚡ Killzone Active — TRADE Today",
            f"BIAS: {bias.get('bias', 'NEUTRAL')}\n"
            f"Confidence: {confidence:.0%}\n"
            f"Risk: {risk}\n"
            f"Pairs: {', '.join(bias.get('pairs_to_focus', ['EURUSD']))}\n\n"
            f"🕙 Silver Bullet: 10:00-11:00 NY",
            "HIGH" if risk == "LOW" else "MEDIUM",
        )

    # Trigger 2: High risk — caution
    if risk == "HIGH":
        send_alert(
            "⚠️ High Risk Today — Consider Reducing Exposure",
            f"VIX elevated or market uncertainty.\n"
            f"BIAS: {bias.get('bias', 'NEUTRAL')}\n"
            f"Killzone Advice: {killzone}\n\n"
            f"Suggestion: Reduce position sizes or wait.",
            "HIGH",
        )


# ═══════════════════════════════════════════════════════════
# SEO TRIGGERS
# ═══════════════════════════════════════════════════════════
def check_seo_triggers():
    """Check if key posts need re-indexing"""
    key_posts = [
        "ai-trading-journal-template-2026",
        "ai-small-team-25x-multiplier",
    ]

    for slug in key_posts:
        url = f"https://commotiai.com/{slug}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                send_alert(
                    f"🔍 Post Not Reachable: {slug}",
                    f"URL: {url}\nHTTP: {r.status_code}\n\nCheck WordPress or re-index.",
                    "HIGH",
                )
        except:
            pass


# ═══════════════════════════════════════════════════════════
# CONVERSION TRIGGERS
# ═══════════════════════════════════════════════════════════
def check_conversion_triggers():
    """Check for new VIP subscribers or revenue events"""
    if not VIP_FILE.exists():
        return

    vips = json.loads(VIP_FILE.read_text(encoding="utf-8"))
    now = datetime.now().strftime("%Y-%m-%d")

    new_today = 0
    for user_id, data in vips.items():
        if data.get("joined") == now:
            new_today += 1

    if new_today > 0:
        send_alert(
            f"💎 {new_today} New VIP Today!",
            f"Total VIP subscribers: {len(vips)}\n"
            f"Revenue today: ${new_today * 29}\n\n"
            f"Keep posting. The funnel is working.",
            "HIGH",
        )


# ═══════════════════════════════════════════════════════════
# SYSTEM HEALTH
# ═══════════════════════════════════════════════════════════
def check_system_health():
    """Check if key files exist"""
    files = [
        BIAS_FILE,
        PROJ_DIR / "entry_monitor.pid",
    ]

    for f in files:
        if not f.exists():
            send_alert(
                f"⚠️ Missing File: {f.name}",
                f"Expected at: {f}\n\nCheck if the pipeline is running.",
                "HIGH",
            )


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print(f"🚨 Alert Engine — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n📊 Trading Triggers:")
    check_trading_triggers()

    print("\n🔍 SEO Triggers:")
    check_seo_triggers()

    print("\n💎 Conversion Triggers:")
    check_conversion_triggers()

    print("\n⚙️ System Health:")
    check_system_health()

    print(f"\n✅ Alert cycle complete.")


if __name__ == "__main__":
    main()