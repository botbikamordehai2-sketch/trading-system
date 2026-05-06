# COMMOTI AI — WordPress Setup Guide
# commotiai.com | Hostinger Business Hosting

## מבנה האתר — 9 קטגוריות

| קובץ | דף WordPress | Slug | נושא |
|------|-------------|------|------|
| 01_homepage_landing.html | Pages → Home | / | דף הבית |
| 04_category_trading.html | Pages → Trading | /trading | FTMO + EA |
| 05_category_scanner.html | Pages → Scanner | /scanner | Diamond Scanner |
| 06_category_betting.html | Pages → Betting | /betting | Value Betting |
| 07_category_templates.html | Pages → Templates | /templates | Canva + Etsy |
| 08_category_aitools.html | Pages → AI Tools | /ai-tools | Tool Reviews |
| 09_category_ict_smc.html | Pages → ICT/SMC | /ict-smc | ICT Education |

## סדר ההתקנה ב-WordPress

### שלב 1 — הגדרות בסיסיות
1. WordPress → Settings → General
   - Site Title: Commoti AI
   - Tagline: Algorithmic Trading • ICT/SMC • AI Tools
   - Timezone: Jerusalem

2. WordPress → Settings → Permalinks
   - בחר: Post name (/blog-post-title/)
   - Save Changes

### שלב 2 — צור דפים (Pages)
לכל קובץ HTML:
1. Pages → Add New
2. Title = שם הדף (לפי טבלה למעלה)
3. לחץ "Text" (לא Visual/Block)
4. הדבק את תוכן קובץ ה-HTML
5. Publish

### שלב 3 — הגדר Homepage
1. Settings → Reading
2. "Your homepage displays" → A static page
3. Homepage: בחר "Home"
4. Posts page: בחר "Blog"

### שלב 4 — התקן תוספים
- **Yoast SEO** — חובה לכל פוסט
- **WP Rocket** — מהירות (או W3 Total Cache)
- **WPForms Lite** — ניוזלטר/יצירת קשר
- **MonsterInsights** — Google Analytics

### שלב 5 — תפריט ניווט
Appearance → Menus → יצור תפריט ראשי:
- Home → /
- Trading → /trading
- Scanner → /scanner  
- ICT/SMC → /ict-smc
- AI Tools → /ai-tools
- Templates → /templates
- Blog → /blog

## Affiliate Links — עדכן לפני פרסום
החלף בכל הקבצים:
- `YOUR_ID` → ה-affiliate ID שלך ב-FTMO/TradingView/IC Markets
- `YOUR_CHANNEL` → ה-Telegram channel שלך
- `TradingTemplateHub` → שם חנות ה-Etsy שלך

## הצעד הבא
1. Hostinger → My Sites → commotiai.com → WordPress Admin
2. התקן את הדפים לפי הסדר
3. פרסם → שלח URL ל-Google Search Console
