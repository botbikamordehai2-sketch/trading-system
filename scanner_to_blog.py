"""
Scanner → Blog
רץ ב-08:35 (5 דק' אחרי Diamond Scanner)
קורא DIAMOND_REPORT.md → מייצר טיוטת מאמר ICT → שומר ב-ict-blog/content/posts/
"""
import sys, json, re
from datetime import datetime, date
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIAMOND_REPORT = Path(r"C:\Users\gfdh5555\Desktop\projects\diamond-scanner\DIAMOND_REPORT.md")
BLOG_POSTS_DIR = Path(r"C:\Users\gfdh5555\ict-blog\content\posts")
SIGNALS_LOG    = Path(r"C:\Users\gfdh5555\Desktop\projects\trading-system\signals_log.json")

BIAS_MAP = {
    "BULLISH":  ("עולה",  "LONG",  "תמיכה"),
    "BEARISH":  ("יורד",  "SHORT", "התנגדות"),
    "NEUTRAL":  ("ניטרלי","WAIT",  "צפייה"),
}


def parse_report(path: Path) -> dict:
    """קורא DIAMOND_REPORT.md ומחלץ TOP diamonds + macro."""
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")
    data = {"diamonds": [], "macro": {}, "date": datetime.now().strftime("%Y-%m-%d")}

    # חלץ macro  — פורמט: | DXY | 🔴 +0.33% |
    for line in text.splitlines():
        m = re.search(r"\|\s*(DXY|VIX|10Y)\s*\|\s*([🟢🔴])\s*([+-]?\d+\.\d+)%", line)
        if m:
            data["macro"][m.group(1)] = {"arrow": m.group(2), "chg": abs(float(m.group(3)))}

    # חלץ diamonds — פורמט: ### #1 XAUUSD — BEARISH (Score: 6/8)
    current = {}
    for line in text.splitlines():
        # שורת כותרת: ### #1 XAUUSD — BEARISH (Score: 6/8)
        head = re.match(r"###\s+#\d+\s+([\w&. ]+?)\s+—\s+(\w+)\s+\(Score:\s*(\d+)/\d+\)", line)
        if head:
            if current.get("name"):
                data["diamonds"].append(current)
            current = {
                "name":    head.group(1).strip(),
                "bias":    head.group(2),
                "score":   int(head.group(3)),
                "signals": [],
            }
            continue

        # שורת מחיר: - Price: 4557.3 | RSI: 31.8 | ATR: 70.87
        price_m = re.search(r"Price:\s*([\d.]+)\s*\|\s*RSI:\s*([\d.]+)", line)
        if price_m and current:
            current["price"] = float(price_m.group(1))
            current["rsi"]   = float(price_m.group(2))

        # שורת change מ-All Assets table: | XAUUSD | ... | -0.74% |
        chg_m = re.search(r"\|\s*" + re.escape(current.get("name","___")) + r"\s*\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|\s*([+-][\d.]+)%", line)
        if chg_m and current:
            current["chg"] = float(chg_m.group(1))

        # Signals: ✅... | ⚡... (פסיק מפריד)
        if "Signals:" in line and current:
            sigs = re.sub(r".*Signals:\s*", "", line)
            current["signals"] = [s.strip() for s in sigs.split("|") if s.strip()]

    if current.get("name"):
        data["diamonds"].append(current)

    return data


def load_todays_entries() -> list:
    """טוען עסקאות שנשלחו היום מ-signals_log.json."""
    today = date.today().isoformat()
    if not SIGNALS_LOG.exists():
        return []
    try:
        logs = json.loads(SIGNALS_LOG.read_text(encoding="utf-8"))
        return [e for e in logs if e.get("date", "").startswith(today)]
    except Exception:
        return []


def macro_summary(macro: dict) -> str:
    vix = macro.get("VIX", {})
    dxy = macro.get("DXY", {})
    tny = macro.get("10Y", {})

    lines = []
    if vix:
        mood = "סביבה שקטה — Risk-On" if vix.get("chg", 0) < 0 else "עליית VIX — Risk-Off"
        lines.append(f"**VIX:** {vix.get('arrow','')} {abs(vix.get('chg',0)):.2f}% ({mood})")
    if dxy:
        mood = "דולר חלש — תומך בזהב ומדדים" if dxy.get("chg", 0) < 0 else "דולר חזק — לחץ על סחורות"
        lines.append(f"**DXY:** {dxy.get('arrow','')} {abs(dxy.get('chg',0)):.2f}% ({mood})")
    if tny:
        mood = "תשואות עולות — לחץ על צמיחה" if tny.get("chg", 0) > 0 else "תשואות יורדות — תמיכה במדדים"
        lines.append(f"**10Y:** {tny.get('arrow','')} {abs(tny.get('chg',0)):.2f}% ({mood})")
    return "\n".join(f"- {l}" for l in lines) if lines else "- נתונים לא זמינים"


def diamond_section(d: dict) -> str:
    name   = d.get("name", "")
    bias   = d.get("bias", "NEUTRAL")
    score  = d.get("score", 0)
    rsi    = d.get("rsi", 50)
    price  = d.get("price", 0)
    chg    = d.get("chg", 0)
    he_bias, direction, level_type = BIAS_MAP.get(bias, ("ניטרלי", "WAIT", "צפייה"))
    signals = d.get("signals", [])[:3]

    sig_text = "\n".join(f"- {s}" for s in signals) if signals else "- אין איתותים בולטים"
    chg_arrow = "▲" if chg > 0 else "▼"

    return f"""
### {name} — {he_bias} | Score: {score}/8

| פרמטר | ערך |
|--------|-----|
| **מחיר** | {price} ({chg_arrow}{abs(chg):.2f}%) |
| **RSI(14)** | {rsi} |
| **כיוון** | {direction} |
| **ניהול עסקה** | SL מתחת ל{level_type} הקרובה ביותר |

**איתותי Confluence:**
{sig_text}
"""


def generate_post(data: dict) -> str:
    today      = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    diamonds   = data.get("diamonds", [])[:3]
    macro      = data.get("macro", {})
    entries    = load_todays_entries()
    date_he    = datetime.now().strftime("%d/%m/%Y")

    top_name   = diamonds[0]["name"] if diamonds else "שוק"
    top_bias   = BIAS_MAP.get(diamonds[0].get("bias","NEUTRAL"), ("ניטרלי","WAIT",""))[0] if diamonds else "ניטרלי"

    keywords   = [d["name"] for d in diamonds] + ["ICT מסחר", "Diamond Scanner", "ניתוח יומי"]
    kw_str     = json.dumps(keywords, ensure_ascii=False)

    diamond_sections = "\n".join(diamond_section(d) for d in diamonds)

    entries_section = ""
    if entries:
        rows = "\n".join(
            f"| {e['name']} | {e['direction']} | {e['entry']} | {e['sl']} | {e['tp']} |"
            for e in entries
        )
        entries_section = f"""
## עסקאות שהופעלו היום

| נכס | כיוון | כניסה | SL | TP |
|-----|-------|-------|----|----|
{rows}

> העסקאות הופעלו אוטומטית דרך ה-MT5 Bridge לאחר אישור הסיגנל.
"""

    return f"""---
title: "ניתוח יומי {date_he} — {top_name} {top_bias} | Diamond Scanner"
description: "ניתוח ICT יומי אוטומטי: Top 3 הזדמנויות לפי Confluence Score, Macro Context, ו-RSI. מופעל מה-Diamond Scanner."
date: "{today}"
category: "Daily Analysis"
keywords: {kw_str}
readTime: 4
---

## הקשר מאקרו — {date_he}

{macro_summary(macro)}

---

## Top 3 הזדמנויות — Diamond Scanner

{diamond_sections}

---

## היררכיית ICT לכניסה

לפי המתודולוגיה:

1. **Structure** — זיהוי כיוון המגמה הראשי (MA20/MA50)
2. **POI** — Order Block או FVG בכיוון המגמה
3. **DOL** — Draw on Liquidity: היכן ה-Smart Money מכוון?
4. **Trigger** — RSI קיצוני + Price Action confirmation
5. **Entry** — כניסה עם SL מתחת ל-Low האחרון (LONG) או מעל ל-High (SHORT)
{entries_section}

---

> ניתוח זה נוצר אוטומטית ב-08:35 על ידי Diamond Scanner + ICT Blog Pipeline.
> [ICT Blog](https://ict-blog-bay.vercel.app) — לא המלצת השקעה.
"""


def run():
    print(f"[{datetime.now().strftime('%H:%M')}] Scanner → Blog")

    data = parse_report(DIAMOND_REPORT)
    if not data.get("diamonds"):
        print("  [SKIP] אין נתוני Diamond — הריץ את diamond_scanner.py קודם")
        return

    post = generate_post(data)
    today = date.today().isoformat()
    slug  = f"daily-analysis-{today}"
    out   = BLOG_POSTS_DIR / f"{slug}.md"

    out.write_text(post, encoding="utf-8")
    print(f"  [OK] נשמר: {out}")
    print(f"  TOP: {[d['name'] for d in data['diamonds'][:3]]}")
    return out


if __name__ == "__main__":
    run()
