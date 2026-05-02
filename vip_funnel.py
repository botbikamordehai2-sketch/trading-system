"""
📢 VIP Sales Funnel — 10 Posts + WhatsApp Script
Converts free channel viewers → $29 VIP members

Run: python vip_funnel.py
"""
import sys
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════
# VIP Funnel Posts (copy-paste to Telegram)
# ═══════════════════════════════════════════════════════════
POSTS = [
    # Post 1 — Proof
    """🔥 SIGNAL HIT TP

EURUSD Long — +42 pips ✅
כניסה: 10:15 AM | יציאה: 10:33 AM
RSI+MA20 confluence + Silver Bullet Killzone

📊 VIP קיבל את הסיגנל ראשון — 30 דקות לפני הערוץ החינמי.

👉 רוצה את הבא בזמן אמת?
📩 שלח הודעה: VIP""",

    # Post 2 — Value
    """📊 BIAS יומי 02/05

DXY: חלש | VIX: נמוך | NDX: עולה
BIAS: BULLISH 🟢
Confidence: 72%

מיקוד היום: EURUSD + XAUUSD

VIP מקבל בנוסף:
• כניסה מדויקת + SL + TP
• עדכונים בזמן אמת
• 3-5 סיגנלים ביום

📩 שלח: VIP""",

    # Post 3 — FOMO
    """⚠️ 3 סוחרים הצטרפו ל-VIP היום

הם מקבלים:
✅ כניסות בזמן אמת (Telegram push)
✅ Exit alerts — לא מפספסים TP
✅ ניתוח יומי + Killzone focus

אתה עדיין בחינמי.

📩 שלח: VIP""",

    # Post 4 — Result
    """📊 סיכום יומי 02/05

סיגנלים: 4
✅ TP: 3
❌ SL: 1
Win Rate: 75%
Net: +86 pips

הסיגנל היחיד שהפסיד היה אחרי 13:00 — בדיוק ב-Chop שהסקריפט זיהה.

VIP לא נכנס שם — Circuit Breaker עבד.

📩 שלח: VIP — תתחיל מחר בבוקר""",

    # Post 5 — Teaching
    """🎓 Killzone 10-11 AM — איך לזהות Sweep אמיתי

1. חכה ל-10:00 NY
2. חפש Sweep מתחת Swing Low קודם
3. וודא MSS — סגירה מעל גובה הנר הקודם
4. כניסה ב-FVG

ב-VIP: אנחנו שולחים את ה-setup עם צילום מסך.

📩 שלח: VIP""",

    # Post 6 — Testimonial-style
    """💬 "הצטרפתי ל-VIP לפני שבוע. עד עכשיו +210 pips. לא הייתי מאמין שאפשר ככה."

— א', סוחר מישראל

📩 שלח: VIP — תתחיל מחר""",

    # Post 7 — Scarcity
    """🚫 נותרו 3 מקומות במחיר $29

ברגע שמתמלאים — המחיר עולה ל-$49.

מקבלים:
• 3-5 סיגנלים ביום
• כניסות + SL + TP מדויק
• BIAS יומי + Killzone focus
• תמיכה אישית בקבוצה קטנה

📩 שלח: VIP — לפני שהמחיר עולה""",

    # Post 8 — Free → VIP bridge
    """📊 Signal Free (delay 30min)

GBPUSD Short — כניסה 1.2640
SL: 1.2670 | TP: 1.2590

⚠️ שים לב: הסיגנל באיחור של 30 דקות.
VIP קיבל אותו ב-10:00 בדיוק.

רוצה לקבל בזמן אמת?
📩 שלח: VIP""",

    # Post 9 — Community
    """👥 קהילת VIP מונה 4 סוחרים פעילים.

אנחנו מדברים על:
• Setups יומיים
• ניתוח Killzone
• mistakes + תיקונים
• שיתוף צילומי מסך

לא עוד גרף לבד.

📩 שלח: VIP — נכנס היום""",

    # Post 10 — Direct close
    """⚡ $29 = חודש VIP

מה אתה מקבל:
✅ 3-5 סיגנלים ביום
✅ כניסה + SL + TP
✅ BIAS יומי (Claude AI)
✅ Killzone focus (10-11 AM)
✅ תמיכה אישית

השקעה: $29
פוטנציאל: $500-$1,500/חודש

📩 שלח הודעה: VIP
(או לחץ: @motitrades_vip)

נתראה בפנים 🤝""",
]

# ═══════════════════════════════════════════════════════════
# WhatsApp Invite Messages
# ═══════════════════════════════════════════════════════════
WHATSAPP_INVITES = [
    """אחי 🤙

אני מנהל ערוץ טלגרם חינמי — BIAS יומי + 1 סיגנל ביום.
150+ פיפס החודש, 75% Win Rate.

אם אתה סוחר — שווה להציץ:
t.me/commotiai_free

(יש גם VIP — אבל בוא תראה קודם)""",

    """היי 👋

שמתי לב שאתה בענייני טריידינג.
אני רץ על FTMO עם 8 בוטים + Claude AI לניתוח מאקרו.

משתף BIAS יומי + 1 סיגנל חופשי בערוץ:
t.me/commotiai_free

אם בא לך — תצטרף 🤝""",

    """שאלה קטנה — אתה סוחר?

אם כן:
אני מוציא 3-5 סיגנלים ביום בערוץ VIP.
EURUSD, GBPUSD, XAUUSD.
RSI+MA20 + Silver Bullet Killzone.

VIP = $29 לחודש.

תכלס — 1 סיגנל טוב מכסה את זה.

📩 רוצה לנסות?""",
]


if __name__ == "__main__":
    print("=" * 60)
    print("📢 VIP Sales Funnel — Posts + WhatsApp Script")
    print(f"   Date: {datetime.now().strftime('%d/%m/%Y')}")
    print("=" * 60)

    print(f"\n📊 {len(POSTS)} Telegram Posts Ready:")
    print("-" * 40)
    for i, post in enumerate(POSTS, 1):
        print(f"\n--- Post {i} ---")
        print(post)

    print(f"\n\n📱 {len(WHATSAPP_INVITES)} WhatsApp Messages Ready:")
    print("-" * 40)
    for i, msg in enumerate(WHATSAPP_INVITES, 1):
        print(f"\n--- WhatsApp {i} ---")
        print(msg)

    print("\n\n" + "=" * 60)
    print("🎯 Action Plan:")
    print("  1. Post 1-3 today (every 2-3 hours)")
    print("  2. Post 4-7 tomorrow")
    print("  3. Post 8-10 day 3")
    print("  4. Send WhatsApp to 3-5 contacts")
    print("  5. Track: how many said VIP?")
    print("=" * 60)