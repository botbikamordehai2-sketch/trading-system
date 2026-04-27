# 📊 Trading System — ICT/SMC NASDAQ BIAS & Multi-Asset Scanner

> **Live system** — scans 20+ assets, calculates daily BIAS, sends Telegram alerts.

## 🧠 What It Does

| Module | File | Description |
|--------|------|-------------|
| **NASDAQ BIAS** | `nasdaq_scanner.py` | Pulls DXY, VIX, NDX, SPX, 10Y from Yahoo Finance. Calculates BULLISH/BEARISH/NEUTRAL |
| **NYSE Opening Scan** | `nyse_opening_scan.py` | Scans 18 assets (Forex, Indices, Commodities, Crypto) for pre-market setups |
| **Entry Monitor** | `entry_monitor.py` | Sends LONG/SHORT signals to Telegram every 15 min |
| **Price Alert** | `price_alert.py` | Tracks 20 assets every 60 seconds |
| **Telegram Alerts** | `telegram_alerts.py` | BIAS reports + signals → Telegram |
| **Diamond Scanner** | `diamond_scanner.py` | Multi-asset confluence scanner (runs 08:30 daily) |
| **Deep Analysis** | `silver_deep.py` | SILVER FVG/OB structure analysis |
| **Methodology** | `ICT_METHODOLOGY.md` | Full 5-step ICT/SMC framework |

## 🛠 Tech Stack

- **Python 3.12** — Core language
- **yfinance** — Live market data (DXY, VIX, NDX, SPX, 10Y, Forex, Commodities)
- **Telegram Bot API** — Alert delivery
- **ICT/SMC** — FVG, OB, BPR, SMT, Rejection Block, Liquidity analysis
- **Git** — Version control (6+ commits)

## 📊 Current BIAS (last run)

```
DXY: 98.33 (-0.18%) — Tailwind
VIX: 18.95 (+1.28%) — Fear Rising
NDX: 24,836 (+1.63%) — Momentum Up
→ BIAS: BULLISH (Score: 2/3)
```

## 🚀 Quick Start

```bash
pip install yfinance
python show_bias.py          # Display current BIAS
python nyse_opening_scan.py  # Scan 18 assets for NYSE open
```

## 📡 Telegram Integration

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Get `TOKEN` + `CHAT_ID`
3. Add to `telegram_alerts.py`
4. Run: `python telegram_alerts.py`

## 📚 Ecosystem

| Project | URL |
|---------|-----|
| ICT Blog | [ict-blog-bay.vercel.app](https://ict-blog-bay.vercel.app) |
| Publify | [publify-three.vercel.app](https://publify-three.vercel.app) |
| Dropship Machine | `../dropship-machine/` |

---

> **Built with ICT/SMC methodology.** DYOR — not financial advice.