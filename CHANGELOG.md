# CHANGELOG — Trading System

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
