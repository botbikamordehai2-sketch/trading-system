"""
Academic Research Scanner
Daily scan of 10 academic sources -> summaries -> diamonds -> Telegram.
Run via Task Scheduler or manually.
"""
import os
import re
import json
import time
import hashlib
import requests
import io
from datetime import datetime
from pathlib import Path

# -- Optional PDF backend (install one) -------------------------------------
try:
    import fitz          # pip install pymupdf
    PDF_BACKEND = "pymupdf"
except ImportError:
    try:
        import pypdf     # pip install pypdf
        PDF_BACKEND = "pypdf"
    except ImportError:
        PDF_BACKEND = None

# -- Optional HTML parser ---------------------------------------------------
try:
    from bs4 import BeautifulSoup   # pip install beautifulsoup4
    BS4 = True
except ImportError:
    BS4 = False

# -- Optional Claude AI summaries -------------------------------------------
try:
    import anthropic
    ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    AI_AVAILABLE = bool(os.environ.get("ANTHROPIC_API_KEY"))
except ImportError:
    AI_AVAILABLE = False

# -- Config -----------------------------------------------------------------
TELEGRAM_TOKEN = "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA"
CHAT_ID        = "1246833993"
CACHE_FILE     = Path(__file__).parent / "research_cache.json"
REPORT_FILE    = Path(__file__).parent / "RESEARCH_REPORT.md"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
}

# Trading system context for diamond extraction
SYSTEM_CONTEXT = """
We run 7 trading bots on EURUSD, XAUUSD, GBPUSD with these strategies:
1. RSI_MA20: RSI(14) + MA20, H1
2. BollingerRSI: Bollinger Bands + RSI, H1
3. Trend_EMA: EMA20/50 crossover + ADX>25, H1
4. EMA_Cross: EMA9 x EMA21, H1
5. MACD_Lab: MACD histogram cross + MA200 filter, H1
6. Stoch_Lab: Stochastic K/D, H1
7. Session_Breakout: London open range break, M15

Portfolio: $100K virtual, 0.3% risk/trade, FTMO rules (4.5% daily loss, 9% max DD).
3-month backtest: +0.12%, WR 46.9%, 399 trades.
"""

SOURCES = [
    {
        "name": "ML in Financial Markets (ResearchGate - Grilli)",
        "url": "https://www.researchgate.net/profile/Luca-Grilli/publication/358005792_Machine_learning_in_financial_markets/links/61ee9af44393577eca8a23e2/Machine-learning-in-financial-markets.pdf",
        "type": "pdf",
    },
    {
        "name": "Neural Networks for Trading (Academia.edu)",
        "url": "https://www.academia.edu/download/104983274/11296.pdf",
        "type": "pdf",
    },
    {
        "name": "Algorithmic Trading MSc Thesis (UniVe)",
        "url": "https://unitesi.unive.it/bitstream/20.500.14247/14114/1/870146-1273960.pdf",
        "type": "pdf",
    },
    {
        "name": "ML Trading Strategies Review (MECS Press)",
        "url": "https://www.mecs-press.org/ijeme/ijeme-v13-n6/IJEME-V13-N6-5.pdf",
        "type": "pdf",
    },
    {
        "name": "ML for Algorithmic Trading (Sciendo / REMAV)",
        "url": "https://sciendo.com/pdf/10.2478/remav-2022-0021",
        "type": "pdf",
    },
    {
        "name": "Systematic Review Algorithmic Trading (AIPress VSE)",
        "url": "http://aip.vse.cz/artkey/aip-202503-0013_systematic-review-on-algorithmic-trading.php",
        "type": "html",
    },
    {
        "name": "Deep RL Portfolio Management (arXiv 2106.00123)",
        "url": "https://arxiv.org/pdf/2106.00123",
        "type": "pdf",
    },
    {
        "name": "Hybrid ML Stock Prediction (MDPI Mathematics)",
        "url": "https://www.mdpi.com/2227-7390/10/18/3302",
        "type": "html",
    },
    {
        "name": "Automated Trading System Survey (IEEE 9350582)",
        "url": "https://ieeexplore.ieee.org/document/9350582",
        "type": "html",
    },
    {
        "name": "Algorithmic Trading with ML Survey (ResearchGate)",
        "url": "https://www.researchgate.net/publication/377990543_Algorithmic_trading_with_machine_learning_a_systematic_review",
        "type": "html",
    },
]

# -- Telegram ----------------------------------------------------------------
def send_telegram(msg: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"Telegram error: {e}")

def send_long_telegram(text: str):
    """Split message into 4000-char chunks and send sequentially."""
    limit = 4000
    chunks = [text[i:i+limit] for i in range(0, len(text), limit)]
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            chunk = f"[{i+1}/{len(chunks)}]\n" + chunk
        send_telegram(chunk)
        if i < len(chunks) - 1:
            time.sleep(1)

# -- Cache -------------------------------------------------------------------
def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

# -- Fetch -------------------------------------------------------------------
def fetch_pdf(url: str) -> str:
    if PDF_BACKEND is None:
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()
        content = resp.content
        if PDF_BACKEND == "pymupdf":
            doc = fitz.open(stream=content, filetype="pdf")
            pages = min(len(doc), 20)  # first 20 pages
            return "\n".join(doc[i].get_text() for i in range(pages))
        else:
            reader = pypdf.PdfReader(io.BytesIO(content))
            pages = min(len(reader.pages), 20)
            return "\n".join(reader.pages[i].extract_text() or "" for i in range(pages))
    except Exception as e:
        print(f"  PDF fetch error: {e}")
        return ""

def fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        if BS4:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        else:
            # Minimal HTML strip
            text = re.sub(r"<[^>]+>", " ", resp.text)
            return re.sub(r"\s+", " ", text).strip()
    except Exception as e:
        print(f"  HTML fetch error: {e}")
        return ""

def fetch_source(source: dict) -> str:
    if source["type"] == "pdf":
        return fetch_pdf(source["url"])
    return fetch_html(source["url"])

# -- Summarize (with Claude) ------------------------------------------------
def summarize_with_ai(text: str, source_name: str) -> dict:
    if not AI_AVAILABLE:
        return summarize_simple(text, source_name)

    snippet = text[:8000]
    prompt = f"""You are analyzing an academic paper on algorithmic trading and machine learning.

Paper: {source_name}

Text excerpt:
{snippet}

Our trading system context:
{SYSTEM_CONTEXT}

Tasks:
1. Write a 3-sentence summary of the paper's main contribution.
2. List up to 5 "diamonds" — specific, actionable findings that could improve our 7 bots.
   Format each diamond as: DIAMOND: [finding] -> [how to apply to our system]

Be concrete and specific. Ignore generic findings."""

    try:
        response = ANTHROPIC_CLIENT.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text
        return {"summary": content, "diamonds": extract_diamonds(content)}
    except Exception as e:
        print(f"  Claude API error: {e}")
        return summarize_simple(text, source_name)

# -- Summarize (no API) -----------------------------------------------------
TRADING_KEYWORDS = [
    "win rate", "sharpe", "drawdown", "rsi", "macd", "bollinger",
    "ema", "moving average", "stochastic", "momentum", "mean reversion",
    "stop loss", "take profit", "risk management", "position sizing",
    "kelly criterion", "volatility", "trend following", "breakout",
    "backtesting", "overfitting", "walk-forward", "regime", "lstm",
    "random forest", "gradient boost", "reinforcement learning",
    "neural network", "feature", "signal", "alpha", "return",
    "correlation", "portfolio", "diversification", "regime change",
]

def summarize_simple(text: str, source_name: str) -> dict:
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 60]
    # Score lines by keyword density
    scored = []
    text_lower = text.lower()
    for line in lines[:200]:
        line_lower = line.lower()
        score = sum(1 for kw in TRADING_KEYWORDS if kw in line_lower)
        if score > 0:
            scored.append((score, line))
    scored.sort(reverse=True)
    top_lines = [l for _, l in scored[:8]]

    summary_text = f"Key excerpts from {source_name}:\n"
    summary_text += "\n".join(f"- {l}" for l in top_lines[:5]) if top_lines else "(No extractable text)"
    diamonds = [l for _, l in scored[:3]] if scored else []

    return {"summary": summary_text, "diamonds": diamonds}

def extract_diamonds(text: str) -> list:
    diamonds = []
    for line in text.split("\n"):
        if "DIAMOND:" in line:
            diamonds.append(line.replace("DIAMOND:", "").strip())
    return diamonds

# -- Main report generator ---------------------------------------------------
def run_scanner():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache = load_cache()

    print(f"\nResearch Scanner | {today}")
    print(f"PDF backend: {PDF_BACKEND or 'NONE — install pymupdf or pypdf'}")
    print(f"HTML parser: {'beautifulsoup4' if BS4 else 'basic regex'}")
    print(f"AI summaries: {'Claude Haiku' if AI_AVAILABLE else 'keyword-based (set ANTHROPIC_API_KEY for AI)'}")
    print("="*60)

    send_telegram(f"RESEARCH SCANNER STARTED\nDate: {today}\nSources: {len(SOURCES)}")

    results = []
    all_diamonds = []

    for i, source in enumerate(SOURCES, 1):
        name = source["name"]
        url  = source["url"]
        key  = url_hash(url)

        print(f"\n[{i}/{len(SOURCES)}] {name}")

        # Use cached text if already fetched today
        cached = cache.get(key, {})
        if cached.get("date") == today and cached.get("text"):
            print("  Using cached text")
            text = cached["text"]
        else:
            print(f"  Fetching {source['type'].upper()}...")
            text = fetch_source(source)
            if text:
                cache[key] = {"date": today, "text": text[:50000], "name": name}
                save_cache(cache)
                print(f"  Fetched {len(text):,} chars")
            else:
                print("  FAILED — skipping")
                results.append({"name": name, "url": url, "status": "failed", "summary": "", "diamonds": []})
                continue

        result = summarize_with_ai(text, name)
        result["name"] = name
        result["url"] = url
        result["status"] = "ok"
        results.append(result)
        all_diamonds.extend(result.get("diamonds", []))

        print(f"  Done | {len(result.get('diamonds', []))} diamonds found")
        time.sleep(2)

    # -- Build report --------------------------------------------------------
    report_lines = [
        f"# Research Report — {today}",
        "",
        f"Sources scanned: {sum(1 for r in results if r['status'] == 'ok')}/{len(SOURCES)}",
        f"AI summaries: {'YES (Claude Haiku)' if AI_AVAILABLE else 'NO (keyword-based)'}",
        "",
        "---",
        "",
    ]

    for r in results:
        status_str = "OK" if r["status"] == "ok" else "FAILED"
        report_lines += [
            f"## [{status_str}] {r['name']}",
            f"URL: {r['url']}",
            "",
        ]
        if r["status"] == "ok":
            report_lines += [r.get("summary", ""), ""]
            for d in r.get("diamonds", []):
                report_lines.append(f"- DIAMOND: {d}")
            report_lines.append("")

    if all_diamonds:
        report_lines += [
            "---",
            "",
            "## All Diamonds",
            "",
        ]
        for d in all_diamonds:
            report_lines.append(f"- {d}")

    report_text = "\n".join(report_lines)
    REPORT_FILE.write_text(report_text, encoding="utf-8")
    print(f"\nReport saved: {REPORT_FILE}")

    # -- Send to Telegram ----------------------------------------------------
    ok_count   = sum(1 for r in results if r["status"] == "ok")
    fail_count = len(results) - ok_count

    header = (
        f"RESEARCH SCANNER COMPLETE — {today}\n"
        f"Scanned: {ok_count}/{len(SOURCES)} | Failed: {fail_count}\n\n"
    )

    # Diamonds summary
    if all_diamonds:
        diamond_block = "DIAMONDS (actionable insights):\n"
        for j, d in enumerate(all_diamonds[:10], 1):
            diamond_block += f"{j}. {d[:200]}\n"
    else:
        diamond_block = "No diamonds extracted. Check RESEARCH_REPORT.md for full text."

    # Per-source short summary
    sources_block = "\nPER SOURCE:\n"
    for r in results:
        icon = "OK" if r["status"] == "ok" else "FAIL"
        name_short = r["name"][:45]
        sources_block += f"[{icon}] {name_short}\n"

    full_msg = header + diamond_block + sources_block
    send_long_telegram(full_msg)

    print("\nScan complete. Telegram notification sent.")
    return results

# -- Entry point -------------------------------------------------------------
if __name__ == "__main__":
    # Check dependencies
    missing = []
    if PDF_BACKEND is None:
        missing.append("pymupdf (pip install pymupdf)")
    if not BS4:
        missing.append("beautifulsoup4 (pip install beautifulsoup4)")
    if missing:
        print("WARN: Missing optional packages:")
        for m in missing:
            print(f"  pip install {m.split(' ')[0]}")
        print()

    run_scanner()
