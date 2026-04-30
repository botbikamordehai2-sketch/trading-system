# CLAUDE.md — Trading System Context

## Project Overview
Live MT5 trading bot for **Blueberry Funded** prop firm account.
Architecture: Python (entry_monitor.py) → signal files → MQL5 EA (RSI_MA20_Bot.mq5)

## Critical Rules
- NEVER run `mt5_bot.py` — uses Python MT5 API, disables AutoTrading in MT5
- ALWAYS run `python test_entry_monitor.py` before any change to entry_monitor.py or daily_review.py
- ALL 31 tests must pass before running on a live Funded account
- MAX_DAILY_TRADES = 2 — hard limit per Blueberry rules

## Blueberry Funded Limits (enforce in code)
| Rule | Value | Where enforced |
|------|-------|----------------|
| Daily Drawdown | 4% | drawdown_check() in entry_monitor.py + InpMaxDailyLoss=3.8% in EA |
| Risk per trade | max 1.5% | InpRisk=1.0% in EA |
| Margin Level | > 150% | FTMOGuard() in EA |
| News trading | forbidden 2min before/after HIGH | get_high_impact_news() blocks 2h |
| HFT / Arbitrage | forbidden | not implemented |

## Architecture
```
entry_monitor.py (runs every 15 min)
  -> yfinance: fetch RSI + MA20 + MA50
  -> circuit_breaker_check()   # max 2 trades/day
  -> drawdown_check()          # MT5 equity API, 4% limit
  -> session_filter_check()    # month-end block
  -> check_entry()             # RSI + anti-trend filter
  -> write_mt5_signal()        # writes signal_SYMBOL.txt (UTF-8)
  -> Telegram + WhatsApp alert

RSI_MA20_Bot.mq5 (OnTimer every 5s)
  -> CheckBridgeSignal()       # reads signal_*.txt
  -> FTMOGuard()               # daily DD + margin check
  -> CalcLot()                 # 1% risk based sizing
```

## Key Files
| File | Purpose |
|------|---------|
| `entry_monitor.py` | Main Python scanner + circuit breaker |
| `RSI_MA20_Bot.mq5` | MQL5 EA — reads signals, executes trades |
| `daily_review.py` | Daily P&L review + close_signals_auto() |
| `test_entry_monitor.py` | 31 unit tests — run before every deploy |
| `run_checks.bat` | Pre-flight: tests + lint + type check |
| `signals_log.json` | Trade log (all signals, closed/open status) |
| `circuit_breaker.lock` | Hard lock file — deleted at midnight |
| `trades_today.txt` | Format: "YYYY-MM-DD:N" — daily trade count |
| `daily_start_equity.txt` | Format: "YYYY-MM-DD:EQUITY" — for drawdown calc |

## Known Bugs Fixed (2026-04-30)
1. increment_trade_counter() was never called → circuit breaker never engaged
2. Lock file deleted on every restart → protection reset
3. No PID lock → 5 concurrent instances ran simultaneously
4. Missing encoding="utf-8" → files written in cp1255, counter always 0
5. Double time.sleep() → 30 min interval instead of 15
6. write_mt5_signal() no encoding → EA couldn't read signals

## Signal Logic (check_entry)
- LONG: trend_up (price > MA50) + RSI oversold/momentum + rsi_rising + NOT last3_bearish
- SHORT: trend_down (price < MA50) + RSI overbought/momentum + rsi_falling + NOT last3_bullish
- News block: HIGH impact events block ALL assets for 2 hours
- Duplicate block: same signal blocked for 2 hours

## MT5 Signal Bridge
- Python writes: `C:\Users\gfdh5555\AppData\Roaming\MetaQuotes\Terminal\Common\Files\signal_SYMBOL.txt`
- Format: `LONG,1234567890` (direction + unix timestamp)
- EA ignores signals older than 900 seconds
- EA deletes file after reading

## Environment
- .env location: `C:\Users\gfdh5555\tv_webhook\.env`
- Required keys: TELEGRAM_TOKEN, ALL_CHAT_ID, ODDS_API_KEY, WHATSAPP_PHONE, WHATSAPP_APIKEY
- psutil required: `pip install psutil` (for PID lock)
- MetaTrader5 required: `pip install MetaTrader5` (for drawdown check)

## Before Making Any Change
1. `python test_entry_monitor.py` — all 31 must pass
2. Make change
3. `python test_entry_monitor.py` — all 31 must still pass
4. Update CHANGELOG.md
