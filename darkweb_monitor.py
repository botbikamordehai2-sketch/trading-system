"""
Dark Web Watch — VIP Monitor
קורא מיילים מ-CSV, בודק HIBP API, שולח דוח לטלגרם.
Run: python darkweb_monitor.py
Schedule: Task Scheduler — שבועי ביום ראשון 09:00
"""
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

# ── Config ──────────────────────────────────────────────────
TOKENS_FILE    = Path("C:/Users/gfdh5555/tokens.txt")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID        = os.getenv("ALL_CHAT_ID", "")          # ערוץ VIP
HIBP_API_KEY   = os.getenv("HIBP_API_KEY", "")         # https://haveibeenpwned.com/API/Key
MEMBERS_CSV    = Path(__file__).parent / "vip_members.csv"
RESULTS_LOG    = Path(__file__).parent / "darkweb_results.json"

# טוען tokens.txt אם env vars לא מוגדרים
if not TELEGRAM_TOKEN or not HIBP_API_KEY:
    if TOKENS_FILE.exists():
        for line in TOKENS_FILE.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key, val = key.strip(), val.strip()
                if key == "TELEGRAM_TOKEN" and not TELEGRAM_TOKEN:
                    TELEGRAM_TOKEN = val
                elif key == "ALL_CHAT_ID" and not CHAT_ID:
                    CHAT_ID = val
                elif key == "HIBP_API_KEY" and not HIBP_API_KEY:
                    HIBP_API_KEY = val

HIBP_HEADERS = {
    "hibp-api-key": HIBP_API_KEY,
    "user-agent":   "CommotiAI-DarkWebWatch/1.0",
}


# ── CSV Structure ─────────────────────────────────────────────
# vip_members.csv עמודות:
# name, email, plan, notes
# דוגמה:
# Avi Cohen,avi@gmail.com,VIP,trader
# Sara Levi,sara@work.co.il,VIP+,broker


def load_members() -> list[dict]:
    if not MEMBERS_CSV.exists():
        _create_sample_csv()
    members = []
    with open(MEMBERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("email", "").strip():
                members.append(row)
    return members


def _create_sample_csv():
    with open(MEMBERS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "email", "plan", "notes"])
        writer.writerow(["דוגמה", "example@gmail.com", "VIP", "trader"])
    print(f"נוצר קובץ לדוגמה: {MEMBERS_CSV}")
    print("ערוך אותו עם המיילים האמיתיים לפני הרצה.")


# ── HIBP API ─────────────────────────────────────────────────
def check_email(email: str) -> list[dict]:
    """מחזיר רשימת דליפות לאימייל. [] = נקי."""
    if not HIBP_API_KEY:
        print("  ⚠️  HIBP_API_KEY חסר — מדלג על בדיקה")
        return []
    try:
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false"
        r = requests.get(url, headers=HIBP_HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return []          # נקי
        elif r.status_code == 429:
            print("  ⏳ Rate limit — ממתין 6 שניות")
            time.sleep(6)
            return check_email(email)
        else:
            print(f"  ⚠️  HIBP שגיאה {r.status_code} עבור {email}")
            return []
    except Exception as e:
        print(f"  ❌ שגיאת רשת: {e}")
        return []


def classify_severity(breaches: list[dict]) -> str:
    """HIGH אם יש דליפה < 365 יום, MEDIUM אם ישנה, LOW אם נקי."""
    if not breaches:
        return "LOW"
    from datetime import timezone
    now = datetime.now(timezone.utc)
    for b in breaches:
        try:
            breach_date = datetime.fromisoformat(b["BreachDate"] + "T00:00:00+00:00")
            if (now - breach_date).days < 365:
                return "HIGH"
        except Exception:
            continue
    return "MEDIUM"


# ── Report ────────────────────────────────────────────────────
def build_report(results: list[dict]) -> str:
    now = datetime.now().strftime("%d/%m/%Y")
    total = len(results)
    clean = sum(1 for r in results if not r["breaches"])
    leaked = total - clean
    high   = sum(1 for r in results if r["severity"] == "HIGH")

    lines = [
        f"🛡️ *Dark Web Watch — {now}*",
        f"סה\"כ חברי VIP שנבדקו: {total}",
        f"✅ נקיים: {clean} | ⚠️ דליפות: {leaked} | 🔴 דחוף: {high}",
        "",
    ]

    for r in results:
        if not r["breaches"]:
            continue
        sev_icon = "🔴" if r["severity"] == "HIGH" else "🟡"
        lines.append(f"{sev_icon} *{r['name']}* — {len(r['breaches'])} דליפות")
        for b in r["breaches"][:3]:        # עד 3 ראשונות
            services = ", ".join(b.get("DataClasses", [])[:3])
            lines.append(f"  • {b['Name']} ({b['BreachDate']}) — {services}")
        if len(r["breaches"]) > 3:
            lines.append(f"  ... ועוד {len(r['breaches']) - 3}")
        lines.append("")

    if leaked == 0:
        lines.append("✨ אין דליפות חדשות השבוע. המשיכו לשמור על 2FA וסיסמאות חזקות.")
    else:
        lines.append("📋 *פעולות מומלצות:*")
        lines.append("1️⃣ החליפו סיסמה לכל שירות שדלף")
        lines.append("2️⃣ הפעילו 2FA / Passkey")
        lines.append("3️⃣ בדקו רוטציית API keys אם רלוונטי")

    return "\n".join(lines)


def send_telegram(msg: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️  Telegram לא מוגדר — מדפיס לקונסול:\n")
        print(msg)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
        print("  ✅ דוח נשלח לטלגרם")
    except Exception as e:
        print(f"  ❌ שגיאת טלגרם: {e}")


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print(f"🛡️  Dark Web Watch — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    members = load_members()
    if not members:
        print("❌ אין חברים ב-vip_members.csv")
        return

    print(f"\nבודק {len(members)} חברי VIP...\n")
    results = []

    for m in members:
        email = m["email"].strip()
        name  = m.get("name", email)
        print(f"  🔍 {name} <{email}>")
        breaches = check_email(email)
        sev      = classify_severity(breaches)
        results.append({"name": name, "email": email, "breaches": breaches, "severity": sev})
        icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "✅"}[sev]
        print(f"     {icon} {len(breaches)} דליפות ({sev})")
        time.sleep(1.6)     # HIBP rate limit: max 1 req/1.5s

    # שמור לוג
    RESULTS_LOG.write_text(
        json.dumps({"date": datetime.now().isoformat(), "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # שלח דוח
    report = build_report(results)
    print(f"\n{'='*55}\n{report}\n{'='*55}")
    send_telegram(report)
    print("\n✅ סיום.")


if __name__ == "__main__":
    main()
