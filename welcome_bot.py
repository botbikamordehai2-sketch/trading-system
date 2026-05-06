"""
Welcome Bot — רצף קבלת פנים אוטומטי
משתמש לוחץ t.me/BOT?start=darkweb → מקבל 3 הודעות ב-3 ימים.
Run: python welcome_bot.py
"""
import json
import os
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import requests

# ── Config ──────────────────────────────────────────────────
TOKENS_FILE    = Path("C:/Users/gfdh5555/tokens.txt")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
FREE_CHAT_ID   = "-1003901040094"
VIP_CHAT_ID    = "-1003984881621"
DB_FILE        = Path(__file__).parent / "welcome_bot.db"
POLL_INTERVAL  = 3   # שניות בין בדיקות

if not TELEGRAM_TOKEN:
    if TOKENS_FILE.exists():
        for line in TOKENS_FILE.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip() == "TELEGRAM_TOKEN":
                    TELEGRAM_TOKEN = v.strip()

BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ── רצף ההודעות ──────────────────────────────────────────────
SEQUENCE = [
    {
        "delay_days": 0,
        "message": """\
👋 *ברוך הבא ל-Commoti AI!*

קיבלתי את הבקשה שלך לבדיקת הדארק-ווב.
אבדוק את המייל שלך ואחזור אליך תוך 24 שעות עם דוח מלא.

בינתיים — הצטרף לערוץ החינמי שלנו לקבל:
📊 ניתוח שוק יומי
⚡ איתותי מסחר
🔐 טיפי אבטחה לסוחרים

👉 [Commoti AI Free](t.me/commotiai)""",
    },
    {
        "delay_days": 3,
        "message": """\
🔍 *עדכון — Dark Web Watch*

בדקתי את המייל שלך.
אשלח לך את הדוח המלא בקרוב.

💡 *טיפ לסוחר השבוע:*
הפעל 2FA על חשבון הבורסה שלך עכשיו.
זה 2 דקות שיכולות לחסוך לך הכל.

רוצה ניטור שבועי קבוע? → שאל אותי על ה-VIP 🔒""",
    },
    {
        "delay_days": 7,
        "message": """\
📊 *שבוע עבר — איך אתה מגן על עצמך?*

חברי VIP שלנו מקבלים:
✅ ניטור דארק-ווב שבועי
✅ התראות מיידיות על דליפות
✅ דוח חודשי + המלצות פעולה
✅ גישה לאיתותי מסחר יומיים

💰 רק $10/חודש — פחות מ-קפה אחד בשבוע.

👉 הצטרף עכשיו: t.me/commotiai""",
    },
]


# ── Database ─────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        joined_at TEXT,
        source TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS scheduled (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message TEXT,
        send_at TEXT,
        sent INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()


def add_user(chat_id: int, username: str, source: str):
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)",
              (chat_id, username, datetime.now().isoformat(), source))
    if c.rowcount > 0:
        # תזמן את רצף ההודעות
        for step in SEQUENCE:
            send_at = (datetime.now() + timedelta(days=step["delay_days"])).isoformat()
            c.execute("INSERT INTO scheduled (chat_id, message, send_at) VALUES (?,?,?)",
                      (chat_id, step["message"], send_at))
        print(f"  ✅ משתמש חדש: {username} ({chat_id}) — {len(SEQUENCE)} הודעות מתוזמנות")
    conn.commit()
    conn.close()


def get_pending() -> list:
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("SELECT id, chat_id, message FROM scheduled WHERE sent=0 AND send_at <= ?",
              (datetime.now().isoformat(),))
    rows = c.fetchall()
    conn.close()
    return rows


def mark_sent(row_id: int):
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("UPDATE scheduled SET sent=1 WHERE id=?", (row_id,))
    conn.commit()
    conn.close()


# ── Telegram API ─────────────────────────────────────────────
def send_msg(chat_id: int, text: str):
    try:
        r = requests.post(f"{BASE}/sendMessage",
                          json={"chat_id": chat_id, "text": text,
                                "parse_mode": "Markdown", "disable_web_page_preview": True},
                          timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  ❌ {e}")
        return False


def get_updates(offset: int = 0) -> list:
    try:
        r = requests.get(f"{BASE}/getUpdates",
                         params={"offset": offset, "timeout": 2},
                         timeout=10)
        if r.status_code == 200:
            return r.json().get("result", [])
    except:
        pass
    return []


# ── Main Loop ─────────────────────────────────────────────────
def main():
    init_db()
    print(f"🤖 Welcome Bot פעיל — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("לחץ Ctrl+C לעצירה\n")

    offset = 0
    while True:
        # בדוק הודעות נכנסות
        updates = get_updates(offset)
        for upd in updates:
            offset = upd["update_id"] + 1
            msg = upd.get("message", {})
            if not msg:
                continue

            chat_id  = msg["chat"]["id"]
            username = msg["chat"].get("username", msg["chat"].get("first_name", ""))
            text     = msg.get("text", "")

            # /start darkweb או /start רגיל
            if text.startswith("/start"):
                source = text.replace("/start", "").strip() or "direct"
                add_user(chat_id, username, source)

        # שלח הודעות מתוזמנות
        for row_id, chat_id, message in get_pending():
            if send_msg(chat_id, message):
                mark_sent(row_id)
                print(f"  📨 נשלח ל-{chat_id}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
