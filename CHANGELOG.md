# CHANGELOG — Trading System

---

## [2026-04-30] — Claude Code (Bug Investigation + Blueberry Compliance)

### 🔴 Critical Bug Fixes — Circuit Breaker (גרם להפסד ב-USDJPY)

**שורש הבעיה:** 7 עסקאות LONG על USDJPY נפתחו ביום אחד במקום מקסימום 2.

| Bug | סיבה | תיקון |
|-----|------|--------|
| **Bug 1** | `increment_trade_counter()` הוגדרה אבל אף פעם לא נקראה ב-`run_once()` — מונה תמיד 0 | הוספת קריאה אחרי `write_mt5_signal()` |
| **Bug 2** | `_circuit["date"] = None` בכל startup גרם למחיקת lock + trades_today — circuit breaker מתאפס בכל הפעלה | בדיקת תאריך בתוכן הקובץ לפני מחיקה |
| **Bug 3** | אין PID lock — 5 instances רצו במקביל בין 18:12-18:20 | `ensure_single_instance()` עם psutil |
| **Bug 4** | `read_text()` / `write_text()` ללא `encoding="utf-8"` — קבצים נכתבו ב-cp1255 — מונה תמיד חזר 0 | `encoding="utf-8"` מפורש בכל קריאה/כתיבה |
| **Bug 5** | `time.sleep(INTERVAL)` כפול בשורות 443-444 — בוט ישן 30 דקות במקום 15 | הסרת השורה הכפולה |
| **Bug 6** | `write_mt5_signal()` פתח קובץ ללא encoding — קבצי signal לא נקראו ב-MT5 | `open(path, "w", encoding="utf-8")` |

### 🟡 Signal Logic Improvements

- **Anti-trend filter**: `last3_bearish` חוסם LONG / `last3_bullish` חוסם SHORT — מנע כניסות נגד מומנטום
- **RSI direction**: `rsi_rising` / `rsi_falling` — LONG רק כש-RSI עולה, SHORT רק כש-RSI יורד
- **close_signals_auto()** ב-`daily_review.py`: סגירה אוטומטית של signals שהגיעו ל-SL/TP
- **close_signals_auto() נקראת** ב-`run()` לפני `analyze_yesterday()`

### 🟢 Blueberry Funded Compliance

**`RSI_MA20_Bot.mq5`:**
- `InpMaxDailyLoss`: 4.5% → **3.8%** (Blueberry limit: 4%)
- `InpMinMarginPct = 150.0` — חדש: עוצר אם Margin Level < 150%
- כותרת עודכנה מ-"FTMO Demo Challenge" ל-"Blueberry Funded"
- `BLUEBERRY STOP` במקום `FTMO STOP` בלוגים

**`entry_monitor.py`:**
- `DAILY_DRAWDOWN_LIMIT = 4.0%` — drawdown check חדש
- `drawdown_check()`: קורא equity ישירות מ-MetaTrader5 Python API
- `DAILY_EQUITY_FILE` — שומר equity בתחילת יום לחישוב drawdown יומי

### 🧪 Test Suite — 31 בדיקות, הכל עובר

**`test_entry_monitor.py`** — `python test_entry_monitor.py` חייב לעבור לפני כל הפעלה

| Class | Tests | מכסה |
|-------|-------|-------|
| TestComputeRSI | 4 | oversold, overbought, סדרה קצרה, NaN |
| TestCircuitBreaker | 7 | כל תרחישי ה-CB המקוריים |
| TestCircuitBreakerExtra | 4 | restart, mid-day, full-day simulation |
| TestSignalLogic | 5 | last3, RSI direction |
| TestDailyReview | 1 | close_signals_auto import |
| TestAutoClose | 6 | LONG/SHORT × SL/TP, open, already-closed |
| TestMT5Bridge | 4 | UTF-8, format, unknown symbol, directions |

**`run_checks.bat`** — Tests + Ruff lint + Mypy type check

### Rules Updated

- ✅ **הרץ `run_checks.bat` לפני כל הפעלה על חשבון אמיתי**
- ✅ **Blueberry Funded:** max 1% risk/trade, 3.8% daily DD guard, margin >150%
- ❌ **לעולם לא** להריץ על חשבון Funded בלי 31/31 tests ירוק

---

## [2026-04-30] — Claude Code (Architect)

### Added
- `entry_monitor.py` — WhatsApp second channel via CallMeBot API
  - `send_whatsapp_alert()` — HTTP-only, no browser required
  - Config: `WHATSAPP_PHONE` + `WHATSAPP_APIKEY` in `.env`
  - Graceful fallback: silently skips if not configured
  - Setup: שלח "I allow callmebot to send me messages" ל-+34 644 65 21 91
  - Fires alongside Telegram after every signal batch

---

## [2026-04-30 00:30] — Claude Code (Architect)

### Added
- `scanner_to_blog.py` — Diamond Scanner output → ICT Blog daily post (08:35)
  - Parses DIAMOND_REPORT.md (macro + top 3 diamonds)
  - Generates Hebrew ICT analysis post with frontmatter
  - Saves to `ict-blog/content/posts/daily-analysis-YYYY-MM-DD.md`
  - Includes today's executed trades from signals_log.json
  - Task Scheduler: `ScannerToBlog` @ 08:35 daily

### Changed
- `entry_monitor.py` — Session Filter added
  - `BLOCKED_HOURS_UTC = (15, 16)` — חסום בימים 28-31 לחודש
  - Month-end Rebalancing: flows מוסדיים מייצרים תנועות מטעות
  - Reason: 30/4 = סוף חודש, VIX +5.5% — סביבת Risk-Off

- `entry_monitor.py` — Circuit Breaker added
  - `MAX_DAILY_TRADES = 2` — hard lock after 2 trades/day
  - Counts from `signals_log.json` — survives restarts
  - Sends [CIRCUIT BREAKER] log when locked
  - Reason: 3 trades were executed on 29/4 — prevent overtrading

### Security
- `dropship-machine/.gitignore` — blocks `.env`, `output/`, secrets from GitHub

---

## [2026-04-29] — Claude Code (Architect)

### Added
- `RSI_MA20_Bot.mq5` — MQL5 EA with File Bridge (reads signal_*.txt)
  - OnTimer (5s) + OnTick → CheckBridgeSignal()
  - Signal freshness: ignores signals older than 900s
  - FTMO guard: 4.5% daily loss / 9% drawdown
  - Magic: 202600

- `entry_monitor.py` — Python bridge
  - Scans 15 assets every 15 min (yfinance, RSI+MA20+MA50)
  - Writes `signal_SYMBOL.txt` to MT5 Common Files
  - News filter: HIGH impact events block trading (2h window)
  - Anti-duplicate: same signal blocked for 2 hours

- Task Scheduler: `TradingEntryMonitor` — auto-start at logon

### Infrastructure
- MT5 Profile "Trading" saved — all charts + EA load automatically
- Confirmed working: 3 trades executed via bridge (USDJPY, AUDCAD, USOIL)

### Rules (DO NOT VIOLATE)
- ❌ Never run `mt5_bot.py` — uses Python MT5 API, disables AutoTrading
- ✅ Only `entry_monitor.py` runs in background
- ✅ MQL5 only — no MQL4 code
- ✅ All EA changes tested in Strategy Tester before deploy
