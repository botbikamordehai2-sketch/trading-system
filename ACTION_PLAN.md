# 📋 ACTION PLAN — 30/4/2026

## 🔴 NOW (5 min)

### 1. MT5 → Compile EA
```
פתח MT5 → MetaEditor → File → Open → RSI_MA20_Bot.mq5
F7 (Compile) → וודא 0 errors, 0 warnings
```
**למה:** EA עודכן ל-Blueberry compliance (drawdown guard, margin check) — חייב recompile.

### 2. Add ODDS_API_KEY to .env
```
ODDS_API_KEY=your_key_from_the-odds-api.com
```
**Get key:** https://the-odds-api.com/ (free tier: 500 req/month)

---

## 🟡 TODAY

### 3. GitHub — Create 3 repos
```bash
# diamond-scanner
git -C "C:\Users\gfdh5555\Desktop\projects\diamond-scanner" remote add origin https://github.com/botbikamordehai2-sketch/diamond-scanner.git
git -C "C:\Users\gfdh5555\Desktop\projects\diamond-scanner" push -u origin master

# bet-scanner
git -C "C:\Users\gfdh5555\Desktop\projects\bet-scanner" remote add origin https://github.com/botbikamordehai2-sketch/bet-scanner.git
git -C "C:\Users\gfdh5555\Desktop\projects\bet-scanner" push -u origin master

# dropship-machine (orphan — no history)
cd "C:\Users\gfdh5555\Desktop\projects\dropship-machine"
git checkout --orphan clean
git add -A
git commit -m "fresh start — no credentials in history"
git remote add origin https://github.com/botbikamordehai2-sketch/dropship-machine.git
git push -u origin clean
```

### 4. Etsy — Upload canva-assets
```bash
cd "C:\Users\gfdh5555\Desktop\projects\trading-system"
python etsy_uploader.py --dry-run   # view CSV first
# Then:
python etsy_uploader.py             # upload (needs ETSY_API_KEY)
```
**Cost:** $2.00 (10 listings × $0.20)

### 5. Portfolio → Vercel
```bash
# Create GitHub repo: botbikamordehai2-sketch/portfolio
# Push:
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" init
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" add -A
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" commit -m "initial"
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" remote add origin https://github.com/botbikamordehai2-sketch/portfolio.git
git -C "C:\Users\gfdh5555\Desktop\projects\portfolio" push -u origin master
# Vercel: Import → botbikamordehai2-sketch/portfolio → Deploy
```

---

## 🟢 WHEN READY

### 6. Anthropic API Key → Dropship Machine
```
ANTHROPIC_API_KEY=your_key
python "C:\Users\gfdh5555\Desktop\projects\dropship-machine\main.py"
```

### 7. Telegram VIP → Live
```
1. Create @freetrades Free channel → add bot as admin
2. Create @viptrades VIP channel → add bot as admin
3. Get chat IDs → add FREE_CHAT_ID + VIP_CHAT_ID to .env
4. Create Ko-fi account → update KO_FI_LINK in telegram_vip.py
5. Run: python telegram_vip.py
```

---

## ✅ DONE (no action needed)
- **trading-system** — 31 tests passing, GitHub updated, EA bridge active
- **diamond-scanner** — Task Scheduler 08:30 daily, Telegram alerts
- **ICT Blog + Publify** — LIVE on Vercel

---

## 📊 All 9 Projects Status

| # | Project | Status | Action |
|---|---------|--------|--------|
| 1 | trading-system | ✅ LIVE | — |
| 2 | ICT Blog | ✅ LIVE | — |
| 3 | Publify | ✅ LIVE | — |
| 4 | diamond-scanner | ✅ LIVE | Push to GitHub |
| 5 | bet-scanner | 🟡 | API key + GitHub |
| 6 | dropship-machine | 🟡 | API key + GitHub |
| 7 | canva-assets | 🟡 | Upload to Etsy |
| 8 | portfolio | 🟡 | GitHub + Vercel |
| 9 | tv_webhook | 🟡 | — |