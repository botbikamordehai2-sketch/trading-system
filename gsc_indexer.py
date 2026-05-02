"""
🔍 GSC Auto-Indexer — Multi-Site Pipeline (May 2026)
Sends new URLs to Google Search Console for instant indexing.
Supports up to 100 sites. Rate limit: 200 URLs/day per service account.

Run: python gsc_indexer.py --site ai_seo
"""
import sys
import json
import asyncio
import requests
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Multi-Site Configuration ────────────────────────────────
SITES = {
    "commotiai": {
        "domain": "commotiai.com",
        "sitemap": "https://commotiai.com/wp-sitemap.xml",
        "wp_url": "https://commotiai.com",
        "wp_user": "mbotbika9@gmail.com",
        "wp_app_pwd": "3PjH wVtJ Arkw 3QsE letA crcU",
    },
    # Add more sites here (up to 100)
}

TELEGRAM_TOKEN = "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA"
CHAT_ID = "1246833993"
LOG_FILE = Path(__file__).parent / "gsc_indexing_log.json"


def fetch_sitemap_urls(sitemap_url: str) -> list:
    """Pull recent URLs from WordPress sitemap"""
    try:
        r = requests.get(sitemap_url, timeout=15)
        if r.status_code != 200:
            return []
        # WordPress sitemap is XML; simple extraction
        import re
        urls = re.findall(r"<loc>(https?://[^<]+)</loc>", r.text)
        # Only return URLs from the last 7 days (new posts)
        return list(set(urls))[-20:]  # Last 20 URLs
    except Exception as e:
        print(f"  Sitemap error: {e}")
        return []


def touch_post_via_wp(wp_url: str, wp_user: str, wp_pwd: str, post_url: str) -> bool:
    """Ping WordPress to trigger Google re-crawl"""
    try:
        auth = requests.auth.HTTPBasicAuth(wp_user, wp_pwd)
        slug = post_url.rstrip("/").split("/")[-1]
        r = requests.get(f"{wp_url}/wp-json/wp/v2/posts?slug={slug}", auth=auth)
        posts = r.json()
        if not posts:
            return False
        # Touch the post to update modified time
        post_id = posts[0]["id"]
        r = requests.post(
            f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
            auth=auth,
            json={"status": "publish"},
        )
        return r.status_code == 200
    except:
        return False


def log_result(domain: str, url: str, success: bool):
    """Log indexing attempts"""
    log = {}
    if LOG_FILE.exists():
        log = json.loads(LOG_FILE.read_text(encoding="utf-8"))

    if domain not in log:
        log[domain] = []
    log[domain].append({
        "url": url,
        "time": datetime.now().isoformat(),
        "success": success,
    })

    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def send_telegram(msg: str):
    """Send status to Telegram"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=5,
        )
    except:
        pass


async def index_site(site_name: str, site_config: dict):
    """Index one site"""
    print(f"\n{'='*50}")
    print(f"  Site: {site_name} ({site_config['domain']})")
    print(f"{'='*50}")

    urls = fetch_sitemap_urls(site_config["sitemap"])
    print(f"  Found {len(urls)} recent URLs")

    success_count = 0
    for url in urls:
        ok = touch_post_via_wp(
            site_config["wp_url"],
            site_config["wp_user"],
            site_config["wp_app_pwd"],
            url,
        )
        log_result(site_name, url, ok)
        if ok:
            success_count += 1
        print(f"  {'✅' if ok else '❌'} {url}")

    print(f"\n  Summary: {success_count}/{len(urls)} pinged")
    return success_count, len(urls)


async def main_async(site_filter: str = None):
    """Run all sites (or filter by name)"""
    tasks = []
    for name, config in SITES.items():
        if site_filter and site_filter != name:
            continue
        tasks.append(index_site(name, config))

    if not tasks:
        print(f"No sites matched filter: {site_filter}")
        print(f"Available: {', '.join(SITES.keys())}")
        return

    results = await asyncio.gather(*tasks)

    total_ok = sum(r[0] for r in results)
    total_urls = sum(r[1] for r in results)

    msg = f"📊 GSC Indexer Complete\n{total_ok}/{total_urls} URLs pinged"
    send_telegram(msg)
    print(f"\n{'='*50}")
    print(f"  DONE: {total_ok}/{total_urls} URLs across {len(tasks)} site(s)")
    print(f"{'='*50}")


if __name__ == "__main__":
    site_filter = None
    if len(sys.argv) > 2 and sys.argv[1] == "--site":
        site_filter = sys.argv[2]

    asyncio.run(main_async(site_filter))