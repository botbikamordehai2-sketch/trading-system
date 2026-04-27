"""
NASDAQ DAILY SCANNER
Pulls live indicators: DXY, VIX, SPX, NDX, 10Y
Calculates BIAS and updates NASDAQ_DAILY_BIAS.md
Usage: python nasdaq_scanner.py
"""

import sys
import yfinance as yf
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUTPUT_DIR = Path(__file__).parent
BIAS_FILE = OUTPUT_DIR / "NASDAQ_DAILY_BIAS.md"


# ============================================================
# 1. LIVE INDICATORS (yfinance)
# ============================================================
def fetch_indicators():
    """Pull DXY, VIX, SPX, NDX, 10Y from Yahoo Finance"""
    tickers = {
        "DXY": "DX-Y.NYB",
        "VIX": "^VIX",
        "SPX": "^GSPC",
        "NDX": "^IXIC",
        "10Y": "^TNX",
    }

    results = {}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if not hist.empty:
                close = round(hist["Close"].iloc[-1], 2)
                prev = round(hist["Close"].iloc[-2], 2) if len(hist) > 1 else close
                change = round(((close - prev) / prev) * 100, 2) if prev else 0
                results[name] = {"value": close, "change_pct": change}
            else:
                results[name] = {"error": "No data"}
        except Exception as e:
            results[name] = {"error": str(e)}

    return results


# ============================================================
# 2. BIAS CALCULATION
# ============================================================
def calculate_bias(indicators):
    """Calculate BIAS from DXY, VIX, NDX"""
    score = 0
    details = []

    dxy = indicators.get("DXY", {})
    vix = indicators.get("VIX", {})
    ndx = indicators.get("NDX", {})

    if dxy.get("change_pct", 0) < 0:
        score += 1
        details.append("DXY down = Tailwind")
    else:
        details.append("DXY up = Headwind")

    if vix.get("change_pct", 0) < 0:
        score += 1
        details.append("VIX down = Low Fear")
    else:
        details.append("VIX up = Fear Rising")

    if ndx.get("change_pct", 0) > 0:
        score += 1
        details.append("NDX up = Momentum")
    else:
        details.append("NDX down = Negative")

    if score >= 2:
        bias = "BULLISH"
    elif score <= 1:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return bias, score, details


# ============================================================
# 3. BLOG HEADLINES SCAN (RSS — LIVE)
# ============================================================
def scan_blogs():
    """Scan real RSS feeds and return bias per source"""
    try:
        from blog_scanner import scan_blogs as _scan
        data = _scan()
        # המרה לפורמט ישן {name: bias_str} + שמירת פרטים
        return data
    except Exception as e:
        print(f"  [WARN] blog_scanner error: {e}")
        return {}


# ============================================================
# 4. X (TWITTER) SCAN — חינמי דרך Nitter RSS
# ============================================================
def scan_x():
    """Scan X accounts via Nitter RSS (free, no API key needed)"""
    try:
        import feedparser
        accounts = {
            "@LizAnnSonders": "LizAnnSonders",
            "@alphatrends":   "alphatrends",
            "@ZeroHedge":     "zerohedge",
            "@ripster47":     "ripster47",
        }
        BULLISH = ["rally","bullish","buy","breakout","surge","long","risk-on"]
        BEARISH = ["crash","bearish","sell","drop","recession","risk-off","short"]

        results = {}
        for handle, user in accounts.items():
            try:
                # Nitter RSS — חלופה חינמית לTwitter
                url  = f"https://nitter.net/{user}/rss"
                feed = feedparser.parse(url)
                text = " ".join(
                    getattr(e, "title", "") for e in feed.entries[:5]
                ).lower()
                bull = sum(1 for w in BULLISH if w in text)
                bear = sum(1 for w in BEARISH if w in text)
                bias = "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "NEUTRAL")
                results[handle] = {"bias": bias, "bull": bull, "bear": bear}
            except Exception:
                results[handle] = {"bias": "NEUTRAL"}
        return results
    except Exception as e:
        print(f"  [WARN] X scan error: {e}")
        return {}


# ============================================================
# 5. UPDATE BIAS FILE
# ============================================================
def update_bias_file(indicators, bias, score, details, blogs, x_accounts):
    """Update NASDAQ_DAILY_BIAS.md with fresh data"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    # Build indicators table
    ind_table = ""
    for name, data in indicators.items():
        if "error" in data:
            ind_table += f"| {name} | N/A | N/A | ERR | {data['error']} |\n"
        else:
            if data["change_pct"] < 0:
                arrow = "[+]"
            elif data["change_pct"] > 0:
                arrow = "[-]"
            else:
                arrow = "[=]"

            if name == "DXY":
                note = "Weak USD = Bullish" if data["change_pct"] < 0 else "Strong USD = Bearish"
            elif name == "VIX":
                note = "Fear dropping" if data["change_pct"] < 0 else "Fear rising"
            elif name == "NDX":
                note = "*Momentum Up*" if data["change_pct"] > 0 else "*Momentum Down*"
            elif name == "SPX":
                note = "Correlated w/ NQ"
            elif name == "10Y":
                note = "Yields down = Bullish" if data["change_pct"] < 0 else "Yields up = Bearish"
            else:
                note = ""
            ind_table += f"| {name} | {data['value']} | {data['change_pct']:+.2f}% | {arrow} | {note} |\n"

    blog_rows = ""
    for name, b in blogs.items():
        blog_rows += f"| {name} | {b} | ____ |\n"

    x_rows = ""
    for name, b in x_accounts.items():
        x_rows += f"| {name} | {b} | ____ |\n"

    content = f"""# NASDAQ (NQ) -- BIAS Daily | Week {datetime.now().strftime('%d/%m/%Y')}

> **Updated:** {now}
> **BIAS:** {bias}
> **Timeframe:** Daily / 4H

---

## Global Overview

### Headlines (Blogs)
> *Fill manually or via RSS integration*

| # | Source | BIAS | Summary |
|---|------|------|-------|
{blog_rows.strip()}

### X (Twitter) Heads-Up
| # | Account | BIAS | Summary |
|---|-------|------|-------|
{x_rows.strip()}

---

### Live Indicators (yfinance)
| Indicator | Value | Change | BIAS | Note |
|-----|-----|-------|------|------|
{ind_table.strip()}
| **BIAS** | **{bias}** | **Score: {score}/3** | | {' + '.join(details)} |

> Data pulled automatically: {now}

---

## Step 1 -- Market Structure

### HTF Weekly
```
[ ] Fill -- Weekly structure: HH/HL/LL/LH
```

### Daily Structure
```
Last HH: ____
Last HL: ____
Last LL: ____
Last LH: ____
```

### Current State:
```
[ ] Accumulation / [ ] Manipulation / [ ] Distribution
```

---

## Step 2 -- Tools

```
Open FVG: ____
Active OB: ____
SMT: ____
```

---

## Step 3 -- Liquidity

```
BSL (Target Up): ____
SSL (Target Down): ____
```

---

## Step 4 -- BIAS

```
{bias} -- {datetime.now().strftime('%d/%m/%Y')}
Reason: {' + '.join(details)}
Score: {score}/3
```

---

## Step 5 -- Price Delivery

```
[ ] Consolidation -> [ ] Displacement -> [ ] Impulse
```

---

## Full Source Registry

> See previous NASDAQ_DAILY_BIAS.md (backed up in Git)

---

> **DYOR:** Sources for info only -- not investment advice.
> **Update daily, commit to Git after filling chart fields.**
"""

    with open(BIAS_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] BIAS FILE UPDATED: {BIAS_FILE}")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("NASDAQ DAILY SCANNER -", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 60)

    # Step 1: Live indicators
    print("\n[1/5] Fetching indicators...")
    indicators = fetch_indicators()
    for name, data in indicators.items():
        if "error" in data:
            print(f"  [ERR] {name}: {data['error']}")
        else:
            print(f"  [OK] {name}: {data['value']} ({data['change_pct']:+.2f}%)")

    # Step 2: Calculate BIAS
    print("\n[2/5] Calculating BIAS...")
    bias, score, details = calculate_bias(indicators)
    print(f"  -> {bias} (Score: {score}/3)")
    for d in details:
        print(f"    {d}")

    # Step 3: Blog scan (stub)
    print("\n[3/5] Scanning blogs...")
    blogs = scan_blogs()
    print(f"  -> {len(blogs)} blogs (stub)")

    # Step 4: X scan (stub)
    print("\n[4/5] Scanning X...")
    x_accounts = scan_x()
    print(f"  -> {len(x_accounts)} accounts (stub)")

    # Step 5: Update file
    print("\n[5/5] Updating BIAS FILE...")
    update_bias_file(indicators, bias, score, details, blogs, x_accounts)

    # Step 6: Send Telegram report
    print("\n[6/6] Sending Telegram report...")
    try:
        from telegram_daily import send_report
        send_report(indicators, bias, score, details, blogs)
    except Exception as e:
        print(f"  [WARN] Telegram skip: {e}")

    print("\n" + "=" * 60)
    print("[DONE] Scan complete!")
    print(f"File: {BIAS_FILE}")
    print("=" * 60)