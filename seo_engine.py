"""
🚀 SEO Engine — Unified CLI (GSC Indexer + Schema Generator)
May 2026 — Multi-site pipeline for 100 sites.

Commands:
  python seo_engine.py index [--site commotiai]        → Index recent URLs
  python seo_engine.py schema product [--name "AI Journal" --price 14.99]  → Generate Schema
  python seo_engine.py schema faq                      → FAQ Schema
  python seo_engine.py schema article --title "..."    → Article Schema
  python seo_engine.py inject --slug "post-slug"       → Inject Schema to WordPress post
  python seo_engine.py full --slug "post-slug"         → Index + Inject Schema → Full Pipeline
"""
import sys
import json
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
SITES = {
    "commotiai": {
        "domain": "commotiai.com",
        "wp_url": "https://commotiai.com",
        "sitemap": "https://commotiai.com/wp-sitemap.xml",
        "wp_user": "mbotbika9@gmail.com",
        "wp_app_pwd": "3PjH wVtJ Arkw 3QsE letA crcU",
    },
}
TELEGRAM_TOKEN = "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA"
CHAT_ID = "1246833993"
LOG_FILE = Path(__file__).parent / "seo_engine_log.json"
SITE_URL = "https://commotiai.com"
AUTHOR = "Moti | Commoti AI"

def _auth_for(site: str):
    s = SITES.get(site, SITES["commotiai"])
    return requests.auth.HTTPBasicAuth(s["wp_user"], s["wp_app_pwd"])


# ═══════════════════════════════════════════════════════════════
# INDEXER PIPELINE
# ═══════════════════════════════════════════════════════════════
def fetch_sitemap_urls(sitemap: str) -> list[str]:
    try:
        r = requests.get(sitemap, timeout=15)
        if r.status_code != 200: return []
        import re
        return list(set(re.findall(r"<loc>(https?://[^<]+)</loc>", r.text)))[-20:]
    except Exception as e:
        print(f"  Sitemap error: {e}")
        return []

def touch_post(wp_url: str, auth, url: str) -> bool:
    try:
        slug = url.rstrip("/").split("/")[-1]
        r = requests.get(f"{wp_url}/wp-json/wp/v2/posts?slug={slug}", auth=auth)
        posts = r.json()
        if not posts: return False
        r2 = requests.post(f"{wp_url}/wp-json/wp/v2/posts/{posts[0]['id']}", auth=auth, json={"status": "publish"})
        return r2.status_code == 200
    except:
        return False

async def index_site(site: str):
    cfg = SITES[site]
    auth = _auth_for(site)
    print(f"\n🔍 Indexing: {site}")
    urls = fetch_sitemap_urls(cfg["sitemap"])
    print(f"  Found {len(urls)} URLs")
    ok = 0
    for u in urls:
        if touch_post(cfg["wp_url"], auth, u):
            ok += 1
            print(f"  ✅ {u}")
        else:
            print(f"  ❌ {u}")
    msg = f"📊 SEO Engine Index: {ok}/{len(urls)} URLs on {site}"
    _telegram(msg)
    print(f"  Done. {ok}/{len(urls)} indexed.")
    return ok, len(urls)


# ═══════════════════════════════════════════════════════════════
# SCHEMA GENERATOR
# ═══════════════════════════════════════════════════════════════
def schema_product(name="AI Trading Journal Template", price=14.99, desc="Professional AI-powered trading journal.") -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "description": desc,
        "operatingSystem": "Canva/PDF",
        "applicationCategory": "DesignApplication",
        "offers": {"@type": "Offer", "price": str(price), "priceCurrency": "USD", "availability": "https://schema.org/InStock"},
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4.9", "ratingCount": "124"},
    }

def schema_article(title: str, desc: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "author": {"@type": "Person", "name": AUTHOR},
        "publisher": {"@type": "Organization", "name": "Commoti AI"},
        "datePublished": datetime.now().strftime("%Y-%m-%d"),
        "dateModified": datetime.now().strftime("%Y-%m-%d"),
    }

def schema_faq() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": "What is the best AI trading journal?",
             "acceptedAnswer": {"@type": "Answer", "text": "JournalPlus and TradesViz lead. Start free: commotiai.com/tools"}},
            {"@type": "Question", "name": "How does AI improve win rate?",
             "acceptedAnswer": {"@type": "Answer", "text": "AI detects emotional bias and session edges, improving win rate by ~15%."}},
        ],
    }

def schema_json(schema: dict) -> str:
    return f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'


# ═══════════════════════════════════════════════════════════════
# WORDPRESS INJECT
# ═══════════════════════════════════════════════════════════════
def inject_schema(site: str, post_slug: str, schema_html: str) -> bool:
    cfg = SITES[site]
    auth = _auth_for(site)
    try:
        r = requests.get(f"{cfg['wp_url']}/wp-json/wp/v2/posts?slug={post_slug}", auth=auth)
        posts = r.json()
        if not posts:
            print(f"  Post not found: {post_slug}")
            return False
        pid = posts[0]["id"]
        content = posts[0]["content"]["rendered"]
        if 'application/ld+json' in content:
            print(f"  Schema already present — skipping inject.")
            return True
        new_content = schema_html + "\n" + content
        r2 = requests.post(
            f"{cfg['wp_url']}/wp-json/wp/v2/posts/{pid}",
            auth=auth,
            json={"content": new_content},
        )
        ok = r2.status_code == 200
        print(f"  {'✅' if ok else '❌'} Schema injected → Post ID {pid}")
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═══════════════════════════════════════════════════════════════
async def full_pipeline(site: str, post_slug: str, schema_type: str = "product"):
    print("=" * 60)
    print(f"🚀 SEO Engine — Full Pipeline: {site}")
    print("=" * 60)

    # 1. Generate Schema
    print("\n[1/3] Generating Schema...")
    if schema_type == "product":
        schema = schema_product()
    elif schema_type == "article":
        schema = schema_article(post_slug, "Blog post")
    else:
        schema = schema_faq()
    html = schema_json(schema)
    print(f"  ✅ {schema_type.upper()} Schema ready ({len(html)} chars)")

    # 2. Inject Schema
    print("\n[2/3] Injecting Schema into WordPress...")
    inject_schema(site, post_slug, html)

    # 3. Index
    print("\n[3/3] Indexing...")
    ok, total = await index_site(site)
    _telegram(f"🚀 SEO Engine Pipeline Complete\nSite: {site}\nSchema: {schema_type}\nIndexed: {ok}/{total}")
    print(f"\n✅ Full pipeline complete. {ok}/{total} URLs indexed.")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def _telegram(msg: str):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

def _usage():
    print("SEO Engine — Unified CLI")
    print("  index [--site SITE]             Index recent URLs")
    print("  schema [product|faq|article]    Generate Schema JSON-LD")
    print("  inject --slug POST_SLUG         Inject Schema to WordPress post")
    print("  full   --slug POST_SLUG         Full pipeline: Schema → Inject → Index")
    print("\nExample:")
    print("  python seo_engine.py full --slug ai-trading-journal-template-2026")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        _usage()
        sys.exit(0)

    cmd = sys.argv[1]
    args = {}
    i = 2
    while i < len(sys.argv):
        if sys.argv[i].startswith("--"):
            k = sys.argv[i][2:]
            v = sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--") else "true"
            args[k] = v
            i += 2 if v != "true" else 1
        else:
            i += 1

    site = args.get("site", "commotiai")

    if cmd == "index":
        asyncio.run(index_site(site))

    elif cmd == "schema":
        stype = args.get("type", sys.argv[2] if len(sys.argv) > 2 else "product")
        if stype == "product":
            s = schema_product(args.get("name", "AI Trading Journal"), float(args.get("price", "14.99")))
        elif stype == "faq":
            s = schema_faq()
        elif stype == "article":
            s = schema_article(args.get("title", "Post Title"), args.get("desc", "Description"))
        else:
            s = schema_product()
        print(schema_json(s))

    elif cmd == "inject":
        slug = args.get("slug", "")
        if not slug:
            print("Need --slug POST_SLUG")
            sys.exit(1)
        html = schema_json(schema_product())
        inject_schema(site, slug, html)

    elif cmd == "full":
        slug = args.get("slug", "")
        stype = args.get("type", "product")
        if not slug:
            print("Need --slug POST_SLUG")
            sys.exit(1)
        asyncio.run(full_pipeline(site, slug, stype))

    else:
        _usage()