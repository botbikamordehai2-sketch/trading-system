# 🎯 MASTER PLAN — Finish All 9 Projects

> **מצב נוכחי:** 4 LIVE, 5 צריכים 1-2 פעולות כל אחד
> **זמן כולל:** ~שעתיים

---

## ⚡ BLOCK 1 — 5 דקות (קריטי, עכשיו)

### 1. MT5 — Compile EA
```
פתח MT5 → MetaEditor (F4) → File → Open → RSI_MA20_Bot.mq5
לחץ F7 (Compile)
וודא: 0 errors, 0 warnings
```
**למה:** EA עודכן ל-Blueberry (drawdown 4%, margin 150%) — לא ירוץ בלי compile.

### 2. the-odds-api.com → API Key
```
https://the-odds-api.com/ → Sign Up (free)
העתק API key
הוסף לקובץ C:\Users\gfdh5555\tv_webhook\.env:
ODDS_API_KEY=המפתח_שקיבלת
```

---

## 🟡 BLOCK 2 — 15 דקות (GitHub + Portfolio)

### 3. צור 4 repos ב-GitHub
פתח https://github.com/botbikamordehai2-sketch → New repository:
- `diamond-scanner` (public)
- `bet-scanner` (public)
- `dropship-machine` (private — היו credentials)
- `portfolio` (public)

### 4. Push all 4 repos
פתח CMD והדבק:

```cmd
REM diamond-scanner
git -C "C:\Users\gfdh5555\Desktop\projects\diamond-scanner" remote add origin https://github.com/botbikamordehai2-sketch/diamond-scanner.git
git -C "C:\Users\gfdh5555\Desktop\projects\diamond-scanner" push -u origin master

REM bet-scanner
git -C "C:\Users\gfdh5555\Desktop\projects\bet-scanner" remote add origin https://github.com/botbikamordehai2-sketch/bet-scanner.git
git -C "C:\Users\gfdh5555\Desktop\projects\bet-scanner" push -u origin master

REM dropship-machine (orphan — no history, no secrets)
cd "C:\Users\gfdh5555\Desktop\projects\dropship-machine"
git checkout --orphan clean
git add -A
git commit -m "fresh start — no credentials in history"
git branch -M master
git remote add origin https://github.com/botbikamordehai2-sketch/dropship-machine.git
git push -u origin master

REM portfolio
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" init
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" add -A
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" commit -m "initial portfolio"
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" remote add origin https://github.com/botbikamordehai2-sketch/portfolio.git
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" push -u origin master
```

### 5. Portfolio → Vercel Deploy
```
https://vercel.com → Import → botbikamordehai2-sketch/portfolio → Deploy
(2 דקות, אוטומטי)
```

---

## 🟠 BLOCK 3 — 10 דקות (Etsy)

### 6. Etsy API Key
```
https://etsy.com/developers → Create App → קבל API Key
הוסף ל-.env: ETSY_API_KEY + ETSY_SHOP_ID
```

### 7. Canva Template Links
פתח Canva → כל 10 התבניות → Share → "Anyone with link can view" → העתק
עדכן ב-`etsy_uploader.py` שורות 46-55 (תחליף XXXXXXXXX)

### 8. Upload to Etsy
```cmd
cd "C:\Users\gfdh5555\Desktop\projects\trading-system"
python etsy_uploader.py
```
**עלות:** $2.00 | **פוטנציאל:** $300-$1,500/חודש

---

## 🟢 BLOCK 4 — 10 דקות (Ko-fi + Telegram VIP)

### 9. Ko-fi
```
https://ko-fi.com → Sign Up (free) → set username
עדכן telegram_vip.py שורה 34:
KO_FI_LINK = "https://ko-fi.com/your_username"
```

### 10. Telegram VIP — הפעלת הבוט
```
1. Telegram: Create Channel → @motitrades_free (ציבורי)
2. Create Channel → @motitrades_vip (פרטי)
3. הוסף @tradijfhng_alerts_2026_bot כשני הערוצים (Administrator)
4. שלח הודעה לשני הערוצים, ואז:
   https://api.telegram.org/bot8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA/getUpdates
5. העתק chat_id (מתחיל ב--100)
6. הוסף ל-.env:
   FREE_CHAT_ID=-100XXXXXXXXXX
   VIP_CHAT_ID=-100XXXXXXXXXX
```

### 11. הפעל VIP Bot
```cmd
cd "C:\Users\gfdh5555\Desktop\projects\trading-system"
python telegram_vip.py
```
**פוטנציאל:** $500-$1,500/חודש

---

## 🔵 BLOCK 5 — 10 דקות (Affiliate + Anthropic)

### 12. Affiliate Programs
```
FTMO:     https://ftmo.com/affiliates → Sign up → replace YOUR_ID
TradingView: https://tradingview.com/affiliate → Sign up → replace YOUR_ID
IC Markets:  https://icmarkets.com → IB Program → replace YOUR_ID
Amazon:   https://affiliate-program.amazon.com → replace YOUR_TAG

עדכן affiliate_engine.py (5 מקומות — חפש YOUR_ID/YOUR_TAG)
```

### 13. Anthropic API Key
```
https://console.anthropic.com → API Keys → Create
הוסף ל-.env: ANTHROPIC_API_KEY=your_key
```

### 14. הפעל Affiliate Engine
```cmd
python "C:\Users\gfdh5555\Desktop\projects\trading-system\affiliate_engine.py"
```
→ מעתיק affiliate_footer.html לבלוג ICT Blog

---

## 🟣 BLOCK 6 — 10 דקות (Dropship Machine + Bet Scanner)

### 15. Dropship Machine
```cmd
# וודא ANTHROPIC_API_KEY ב-.env
python "C:\Users\gfdh5555\Desktop\projects\dropship-machine\main.py"
```

### 16. Bet Scanner — LIVE
```cmd
# וודא ODDS_API_KEY ב-.env
python "C:\Users\gfdh5555\Desktop\projects\trading-system\bet_launcher.py"
# דוח שבועי:
python "C:\Users\gfdh5555\Desktop\projects\trading-system\bet_launcher.py" --report
```

---

## ✅ CHECKLIST סופי

| # | משימה | סטטוס |
|---|--------|--------|
| 1 | MT5 F7 Compile | ☐ |
| 2 | the-odds-api.com key | ☐ |
| 3 | GitHub: diamond-scanner | ☐ |
| 4 | GitHub: bet-scanner | ☐ |
| 5 | GitHub: dropship-machine | ☐ |
| 6 | GitHub: portfolio | ☐ |
| 7 | Vercel: portfolio | ☐ |
| 8 | Etsy API key | ☐ |
| 9 | Canva links update | ☐ |
| 10 | Etsy upload | ☐ |
| 11 | Ko-fi signup | ☐ |
| 12 | Telegram channels | ☐ |
| 13 | Telegram VIP bot live | ☐ |
| 14 | FTMO affiliate | ☐ |
| 15 | TradingView affiliate | ☐ |
| 16 | IC Markets affiliate | ☐ |
| 17 | Anthropic API key | ☐ |
| 18 | Bet scanner live | ☐ |
| 19 | Dropship machine live | ☐ |
| 20 | ICT Blog affiliate footer | ☐ |

---

## 💰 פוטנציאל סופי (כל המסלולים פעילים)

| Track | פוטנציאל חודשי |
|-------|-----------------|
| 1. Prop Firm | $1,000-$4,000 |
| 2. Telegram VIP | $500-$1,500 |
| 3. Etsy | $300-$1,500 |
| 4. Affiliate | $100-$500 |
| 5. Bet Scanner | $200-$1,000 |
| **סה"כ** | **$2,100-$8,500/חודש** |