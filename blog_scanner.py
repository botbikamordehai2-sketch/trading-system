"""
Blog RSS Scanner — סורק חדשות אמיתיות מהבלוגים
מחזיר BULLISH / BEARISH / NEUTRAL לכל מקור
"""

import feedparser
import re
import sys
from datetime import datetime, timezone

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# מילות מפתח לניתוח סנטימנט
BULLISH_WORDS = [
    "rally", "surge", "bullish", "gains", "recovery", "upside", "beat",
    "strong", "growth", "optimism", "risk-on", "buy", "breakout", "momentum",
    "record", "high", "boost", "rebound", "soft landing", "dovish"
]
BEARISH_WORDS = [
    "crash", "sell", "bearish", "decline", "recession", "risk-off", "fear",
    "drop", "fall", "concern", "warning", "downside", "miss", "weak",
    "tariff", "inflation", "hawkish", "default", "crisis", "collapse", "dump"
]

RSS_FEEDS = {
    "ZeroHedge":           "https://feeds.feedburner.com/zerohedge/feed",
    "MarketWatch":         "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "ForexLive":           "https://www.forexlive.com/feed/news",
    "FXEmpire":            "https://www.fxempire.com/api/v1/en/articles/rss.xml",
    "Investing.com":       "https://www.investing.com/rss/news.rss",
    "Reuters Markets":     "https://feeds.reuters.com/reuters/businessNews",
}


def _score_text(text: str) -> tuple[str, int, int]:
    text_lower = text.lower()
    bull = sum(1 for w in BULLISH_WORDS if w in text_lower)
    bear = sum(1 for w in BEARISH_WORDS if w in text_lower)
    if bull > bear:
        return "BULLISH", bull, bear
    elif bear > bull:
        return "BEARISH", bull, bear
    return "NEUTRAL", bull, bear


def _is_recent(entry, hours: int = 24) -> bool:
    """בודק אם הכתבה מ-24 השעות האחרונות"""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            pub = datetime(*t[:6], tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
            return age <= hours
    return True   # אם אין תאריך — כולל


def scan_blogs(hours: int = 24) -> dict:
    """
    מחזיר dict: {source: {bias, headlines, bull, bear}}
    """
    results = {}

    for name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            recent = [e for e in feed.entries if _is_recent(e, hours)][:10]

            if not recent:
                results[name] = {"bias": "NEUTRAL", "headlines": [], "bull": 0, "bear": 0}
                continue

            total_bull = total_bear = 0
            headlines = []

            for entry in recent:
                title   = getattr(entry, "title",   "")
                summary = getattr(entry, "summary", "")
                text    = f"{title} {summary}"
                bias, b, br = _score_text(text)
                total_bull += b
                total_bear += br
                headlines.append({"title": title[:80], "bias": bias})

            if total_bull > total_bear:
                overall = "BULLISH"
            elif total_bear > total_bull:
                overall = "BEARISH"
            else:
                overall = "NEUTRAL"

            results[name] = {
                "bias":      overall,
                "headlines": headlines[:3],
                "bull":      total_bull,
                "bear":      total_bear,
            }

        except Exception as e:
            results[name] = {"bias": "NEUTRAL", "headlines": [], "error": str(e)}

    return results


if __name__ == "__main__":
    print("סורק בלוגים...")
    data = scan_blogs()
    for name, d in data.items():
        print(f"\n{'='*40}")
        print(f"{name}: {d['bias']} (🟢{d.get('bull',0)} 🔴{d.get('bear',0)})")
        for h in d.get("headlines", []):
            print(f"  [{h['bias']}] {h['title']}")
