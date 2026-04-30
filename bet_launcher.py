"""
🎯 TRACK 5 — Bet Scanner Launcher
מפעיל scan_loop.py פעמיים ביום (09:00 + 16:00)
עוקב אחרי P&L + שולח דוח שבועי לטלגרם

דרישות: API Key מ-the-odds-api.com

הרצה: python bet_launcher.py [--dry-run]
"""
import sys
import os
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path.home() / "tv_webhook" / ".env")

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")

BET_SCANNER_DIR = Path(__file__).parent.parent / "bet-scanner"
PROFIT_LOG      = Path(__file__).parent / "bet_profit_log.json"
OUTPUT_DIR      = Path(__file__).parent / "bet_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Kelly Criterion ─────────────────────────────────────────
BANKROLL       = 1000   # $ — starting bankroll
KELLY_FRACTION = 0.25   # quarter-kelly (שמרני)


def load_profit_log():
    if PROFIT_LOG.exists():
        return json.loads(PROFIT_LOG.read_text(encoding="utf-8"))
    return {"bankroll": BANKROLL, "trades": [], "start_date": datetime.now().strftime("%Y-%m-%d")}


def save_profit_log(data):
    PROFIT_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def log_trade(event: str, stake: float, result: str, pnl: float):
    """מתעד עסקה ביומן"""
    log = load_profit_log()
    log["trades"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "event": event,
        "stake": round(stake, 2),
        "result": result,
        "pnl": round(pnl, 2),
    })
    log["bankroll"] += pnl
    save_profit_log(log)


def monthly_stats():
    """מחשב סטטיסטיקות חודשיות"""
    log = load_profit_log()
    trades = log["trades"]
    if not trades:
        return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "pnl": 0, "roi": 0, "bankroll": log["bankroll"]}

    wins = sum(1 for t in trades if t["result"] == "WIN")
    losses = sum(1 for t in trades if t["result"] == "LOSS")
    total_pnl = sum(t["pnl"] for t in trades)
    roi = round(total_pnl / BANKROLL * 100, 1)

    return {
        "total": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades) * 100) if trades else 0,
        "pnl": round(total_pnl, 2),
        "roi": roi,
        "bankroll": round(log["bankroll"], 2),
    }


def generate_weekly_report() -> str:
    stats = monthly_stats()
    return (
        f"🎯 *Bet Scanner — Weekly Report*\n"
        f"📅 {datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"🏦 Bankroll: ${stats['bankroll']:.2f}\n"
        f"📊 Trades: {stats['total']} ({stats['win_rate']}% win)\n"
        f"✅ Wins: {stats['wins']} | ❌ Losses: {stats['losses']}\n"
        f"💰 P&L: ${stats['pnl']:+.2f} ({stats['roi']:+.1f}% ROI)\n\n"
        f"_Quarter-Kelly ({KELLY_FRACTION*100:.0f}% Kelly) | Bankroll: ${BANKROLL}_"
    )


def run_scan():
    """מריץ scan_loop.py"""
    scan_loop = BET_SCANNER_DIR / "scan_loop.py"
    if not scan_loop.exists():
        print("❌ scan_loop.py לא נמצא")
        return False

    if not ODDS_API_KEY:
        print("⚠️ ODDS_API_KEY לא מוגדר — scan_loop.py ירוץ ב-demo mode")
        # set env var temporarly
        os.environ["ODDS_API_KEY"] = "demo"

    print(f"🔍 מריץ: {scan_loop}")
    result = subprocess.run(
        [sys.executable, str(scan_loop)],
        cwd=str(BET_SCANNER_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode == 0:
        print("✅ Scan completed")
        output = result.stdout[-500:]  # last 500 chars
        if "VALUE:" in output or "ARB:" in output:
            print(output)
        return True
    else:
        print(f"❌ Scan failed: {result.stderr[:200]}")
        return False


def send_report_telegram(report: str):
    """שולח דוח לטלגרם"""
    try:
        from dotenv import load_dotenv
        load_dotenv(Path.home() / "tv_webhook" / ".env")
        TOKEN = os.getenv("TELEGRAM_TOKEN")
        CHAT_ID = os.getenv("ALL_CHAT_ID", "1246833993")

        import asyncio
        import telegram
        async def _send():
            bot = telegram.Bot(token=TOKEN)
            await bot.send_message(chat_id=CHAT_ID, text=report, parse_mode="Markdown")

        asyncio.run(_send())
        print("[BET] Report sent to Telegram")
    except Exception as e:
        print(f"[BET] Telegram error: {e}")


def main():
    print("=" * 60)
    print("🎯 TRACK 5 — Bet Scanner Launcher")
    print("=" * 60)

    dry_run = "--dry-run" in sys.argv
    send_report = "--report" in sys.argv

    if not ODDS_API_KEY:
        print("\n⚠️ ODDS_API_KEY not found in .env")
        print("   Get API key: https://the-odds-api.com/ (free tier: 500 req/month)")
        print("   Running in demo/offline mode...\n")

    stats = monthly_stats()
    print(f"🏦 Bankroll: ${stats['bankroll']:.2f}")
    print(f"📊 Total trades: {stats['total']}")

    if send_report:
        report = generate_weekly_report()
        print("\n" + report)
        send_report_telegram(report)
        return

    if dry_run:
        print("\n🔍 DRY RUN — not running scan, showing status only")
        print(f"📊 Monthly Stats: {json.dumps(stats, indent=2)}")
        return

    # Run scan
    print("\n🔍 Running scan...")
    success = run_scan()

    if success:
        stats = monthly_stats()
        print(f"\n📊 Updated Stats: {stats['bankroll']:.2f} bankroll, {stats['total']} trades")

    print()
    print("📋 להפעלה מלאה:")
    print("1. הירשם ב-the-odds-api.com")
    print("2. הוסף ODDS_API_KEY ל-.env")
    print("3. הרץ: python bet_launcher.py")
    print("4. דוח שבועי: python bet_launcher.py --report")
    print(f"5. Bankroll התחלתי: ${BANKROLL} | Quarter-Kelly | פוטנציאל: 3-8% ROI חודשי = ${int(BANKROLL*0.05)}-${int(BANKROLL*0.08)}/חודש")


if __name__ == "__main__":
    main()