import requests
import re
import os
from pathlib import Path

WP_URL = "https://commotiai.com"
USERNAME = "mbotbika9@gmail.com"
APP_PASSWORD = "3PjH wVtJ Arkw 3QsE letA crcU"

POSTS_DIR = Path(r"C:\Users\gfdh5555\Desktop\projects\trading-system\wordpress_content")

# רק קבצי פוסטים (לא דפים/קטגוריות)
POST_FILES = [
    ("02_post_ict_silver_bullet.html", "ICT Silver Bullet Setup"),
    ("03_post_ai_trading_2026.html",   "How AI Is Changing Retail Trading in 2026"),
    # 11 כבר פורסם
    ("12_post_diamond_scanner.html",   "Diamond Scanner: How We Rank 50+ Assets Every Morning"),
    ("13_post_kelly_criterion.html",   "Kelly Criterion: The Math Behind Optimal Position Sizing"),
    ("14_post_dropship_guide.html",    "AI-Powered Dropshipping in 2026: How We Automated Product Research"),
]

def extract_html_content(filepath):
    content = filepath.read_text(encoding="utf-8")
    # הסרת שורות הקומנט בראש הקובץ
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    return content.strip()

def publish_post(title, html_content):
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    data = {
        "title":   title,
        "content": html_content,
        "status":  "publish",
    }
    resp = requests.post(
        endpoint,
        json=data,
        auth=(USERNAME, APP_PASSWORD),
        timeout=30
    )
    return resp

def main():
    print(f"Starting upload of {len(POST_FILES)} posts to {WP_URL}\n")
    for filename, title in POST_FILES:
        filepath = POSTS_DIR / filename
        if not filepath.exists():
            print(f"[SKIP] File not found: {filename}")
            continue

        html = extract_html_content(filepath)
        print(f"Uploading: {title} ...", end=" ", flush=True)
        resp = publish_post(title, html)

        if resp.status_code == 201:
            post_id  = resp.json().get("id")
            post_url = resp.json().get("link")
            print(f"OK - Published! ID={post_id} | {post_url}")
        else:
            print(f"ERROR {resp.status_code}: {resp.text[:200]}")

    print("\nDone!")

if __name__ == "__main__":
    main()
