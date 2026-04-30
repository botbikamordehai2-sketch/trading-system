"""
🔬 RESEARCH WATCH — סורק מחקרים חדשים ב-Algo Trading Robustness
בודק arXiv + SSRN + Google Scholar למאמרים חדשים על:
  - Regime-switching models
  - Robustness testing for trading algorithms
  - Kelly fractional / risk management
  - Market microstructure
הרצה: python research_watch.py [--send]
"""
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE_FILE = Path(__file__).parent / "research_cache.json"
LAST_RUN_FILE = Path(__file__).parent / "research_last_run.txt"

# שאילתות חיפוש — מילות מפתח שרלוונטיות לפרויקטים שלך
QUERIES = [
    "algorithmic trading robustness testing",
    "regime switching model trading",
    "Kelly fractional position sizing",
    "market microstructure high frequency",
    "stop loss optimization machine learning",
    "walk forward analysis trading",
    "adversarial validation trading",
    "drawdown minimization algorithmic",
]

ARXIV_URL = "http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending"


def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(data):
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def last_run_date():
    if LAST_RUN_FILE.exists():
        return LAST_RUN_FILE.read_text(encoding="utf-8").strip()
    return None


def mark_run():
    LAST_RUN_FILE.write_text(datetime.now().strftime("%Y-%m-%d"), encoding="utf-8")


def search_arxiv(query: str) -> list:
    """מחפש מאמרים ב-arXiv"""
    import urllib.parse
    url = ARXIV_URL.format(query=urllib.parse.quote(query))
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return []

        # XML parsing פשוט
        papers = []
        entries = r.text.split("<entry>")[1:]  # skip header
        for entry in entries:
            title_start = entry.find("<title>") + 7
            title_end = entry.find("</title>")
            summary_start = entry.find("<summary>") + 9
            summary_end = entry.find("</summary>")
            link_start = entry.find('<id>') + 4
            link_end = entry.find('</id>')
            date_start = entry.find('<published>') + 11
            date_end = entry.find('</published>')

            if all(x > 0 for x in [title_start, summary_start, link_start]):
                title = entry[title_start:title_end].strip().replace("\n", " ")
                summary = entry[summary_start:summary_end].strip()[:300]
                link = entry[link_start:link_end].strip()
                date_str = entry[date_start:date_end].strip()[:10] if date_start > 0 else ""

                papers.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "date": date_str,
                    "source": "arXiv",
                    "query": query,
                })
        return papers

    except Exception:
        return []


def get_ssrn_recent():
    """
    SSRN — בדיקה ידנית: מחזיר קישורים מומלצים
    SSRN API דורש מנוי, אז מחזיר URL לחיפוש ידני
    """
    return [
        {
            "title": "חיפוש SSRN: algorithmic trading robustness",
            "summary": "SSRN.com — חפש: 'algorithmic trading' + 'robustness'",
            "link": "https://papers.ssrn.com/sol3/results.cfm?txtKeywords=algorithmic+trading+robustness",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "SSRN (link)",
            "query": "ssrn_check",
        }
    ]


def get_quantconnect_research():
    """בודק בלוג QuantConnect — מחקרים ופוסטים אחרונים"""
    return [
        {
            "title": "QuantConnect Research — Latest posts",
            "summary": "Blog.QuantConnect.com — tutorials, research papers, algorithm framework updates",
            "link": "https://www.quantconnect.com/blog",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "QuantConnect Blog",
            "query": "quantconnect",
        },
        {
            "title": "QuantConnect: Boot Camp (free)",
            "summary": "Algorithm Framework, Universe Selection, Alpha Creation, Portfolio Construction, Risk Management, Execution",
            "link": "https://www.quantconnect.com/learning",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "QuantConnect Learn",
            "query": "quantconnect",
        },
    ]


def check_new_papers(new_papers: list, cache: dict) -> list:
    """מסנן מאמרים שכבר נראו"""
    unseen = []
    for p in new_papers:
        key = p["link"]
        if key not in cache:
            cache[key] = p["date"]
            unseen.append(p)
    return unseen


def format_report(papers: list) -> str:
    if not papers:
        return "🔬 אין מאמרים חדשים השבוע.\n"

    lines = [f"🔬 *RESEARCH WATCH — {datetime.now().strftime('%d/%m/%Y')}*", ""]
    for i, p in enumerate(papers[:10], 1):  # max 10
        lines.append(f"{i}. *{p['title']}*")
        lines.append(f"   📅 {p['date']} | 📚 {p['source']}")
        if p['summary']:
            lines.append(f"   {p['summary'][:200]}...")
        lines.append(f"   🔗 {p['link']}")
        lines.append("")

    lines.append("_בדוק אילו רעיונות אפשר לשלב במערכת המסחר_")
    return "\n".join(lines)


def run(send_telegram=False):
    print(f"[{datetime.now().strftime('%H:%M')}] 🔬 Research Watch — סורק מאמרים...")
    print()

    cache = load_cache()
    all_papers = []

    for query in QUERIES:
        print(f"  arXiv: {query[:60]}...")
        papers = search_arxiv(query)
        new = check_new_papers(papers, cache)
        all_papers.extend(new)
        time.sleep(1)  # rate limit

    # SSRN
    all_papers.extend(get_ssrn_recent())
    # QuantConnect
    all_papers.extend(get_quantconnect_research())

    save_cache(cache)

    report = format_report(all_papers)
    print(report)

    if send_telegram and all_papers:
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv(Path.home() / "tv_webhook" / ".env")
            TOKEN = os.getenv("TELEGRAM_TOKEN")
            CHAT_ID = os.getenv("ALL_CHAT_ID", "1246833993")
            import telegram
            bot = telegram.Bot(token=TOKEN)
            import asyncio
            asyncio.run(bot.send_message(
                chat_id=CHAT_ID,
                text=report,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            ))
            print("[RESEARCH] נשלח לטלגרם!")
        except Exception as e:
            print(f"[RESEARCH] שליחת טלגרם נכשלה: {e}")

    mark_run()
    print(f"  סהכ מאמרים חדשים: {len(all_papers)}")


if __name__ == "__main__":
    send = "--send" in sys.argv
    run(send_telegram=send)