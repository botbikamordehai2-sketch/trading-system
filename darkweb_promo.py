"""
Dark Web Promo — פרסום אוטומטי לטלגרם FREE
שולח פוסט פרסומי לערוץ החינמי כל 3 ימים.
Schedule: Task Scheduler — כל יום 10:00 (הסקריפט בודק בעצמו אם צריך לשלוח)
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import requests

# ── Config ──────────────────────────────────────────────────
TOKENS_FILE  = Path("C:/Users/gfdh5555/tokens.txt")
STATE_FILE   = Path(__file__).parent / "darkweb_promo_state.json"
PROMO_INTERVAL_DAYS = 3   # כל כמה ימים לשלוח

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
FREE_CHAT_ID   = os.getenv("FREE_CHAT_ID", "-1003901040094")   # ערוץ חינמי

if not TELEGRAM_TOKEN:
    if TOKENS_FILE.exists():
        for line in TOKENS_FILE.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip() == "TELEGRAM_TOKEN":
                    TELEGRAM_TOKEN = v.strip()

# ── פוסטים לרוטציה ──────────────────────────────────────────
PROMO_POSTS = [
    """\
🔍 *האם המייל שלך דלף לדארק-ווב?*

סוחרים הם יעד מועדף להאקרים.
מייל אחד שדלף = סיסמאות, API keys, חשבונות בורסה בסיכון.

✅ בדיקה *חינמית* — פשוטה, מיידית.
👇 השאר מייל וקבל דוח תוך 24 שעות:

🌐 commotiai.com/dark-web-check

*Commoti AI — שומר על הסוחר*""",

    """\
⚠️ *ידעת? 23 מיליון סיסמאות של סוחרים דלפו ב-2025*

אם אתה מסחר בביטקוין, פורקס או מניות —
הפרטים שלך שווים כסף לפושעים.

🛡️ אנחנו בודקים בשבילך האם אתה בסיכון.
*בחינם. ללא כרטיס אשראי.*

👉 commotiai.com/dark-web-check""",

    """\
🕵️ *Dark Web Watch — השירות שכל סוחר צריך*

בכל שבוע אנחנו סורקים את הדארק-ווב
ומחפשים את המיילים של הקהילה שלנו.

📬 הצטרף לשירות החינמי:
commotiai.com/dark-web-check

אם נמצא משהו — תקבל התראה ישירות לכאן. 🔔""",

    """\
💡 *טיפ אבטחה לסוחר — שבוע זה:*

השלבים הכי חשובים להגנה על חשבון בורסה:
1️⃣ בדוק אם המייל שלך דלף
2️⃣ הפעל 2FA על *כל* הפלטפורמות
3️⃣ החלף סיסמה לפחות אחת לרבעון

🔗 התחל בשלב 1 — חינם:
commotiai.com/dark-web-check""",
]


# ── Logic ─────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_sent": None, "post_index": 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def should_send(state: dict) -> bool:
    if not state["last_sent"]:
        return True
    last = datetime.fromisoformat(state["last_sent"])
    return datetime.now() - last >= timedelta(days=PROMO_INTERVAL_DAYS)


def send_post(text: str):
    if not TELEGRAM_TOKEN:
        print("⚠️ TELEGRAM_TOKEN חסר")
        print(text)
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": FREE_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        if r.status_code == 200:
            print("✅ פוסט נשלח לערוץ החינמי")
            return True
        else:
            print(f"❌ שגיאה {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"❌ {e}")
        return False


def main():
    print(f"📣 Dark Web Promo — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    state = load_state()

    if not should_send(state):
        next_send = datetime.fromisoformat(state["last_sent"]) + timedelta(days=PROMO_INTERVAL_DAYS)
        print(f"⏳ הפוסט הבא: {next_send.strftime('%d/%m/%Y')}")
        return

    idx  = state["post_index"] % len(PROMO_POSTS)
    post = PROMO_POSTS[idx]

    if send_post(post):
        state["last_sent"]  = datetime.now().isoformat()
        state["post_index"] = (idx + 1) % len(PROMO_POSTS)
        save_state(state)


if __name__ == "__main__":
    main()
