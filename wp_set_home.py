"""Set WordPress homepage to static page via REST API"""
import sys
import requests
import json
import base64

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WP_URL = "https://commotiai.com"
USERNAME = "mbotbika9@gmail.com"
APP_PASSWORD = "3PjH wVtJ Arkw 3QsE letA crcU"

# Auth header
auth = base64.b64encode(f"{USERNAME}:{APP_PASSWORD}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

# Step 1: List pages to find Home page
print(">> Listing pages...")
r = requests.get(f"{WP_URL}/wp-json/wp/v2/pages?per_page=20", headers=headers)
pages = r.json()
print(f"  Found {len(pages)} pages:")
home_id = None
for p in pages:
    title = p['title']['rendered']
    print(f"  ID:{p['id']} | {title} | {p['status']}")
    if 'Home' in title or 'home' in title.lower():
        home_id = p['id']

# Step 2: If no "Home" page, use first published page
if not home_id and pages:
    for p in pages:
        if p['status'] == 'publish':
            home_id = p['id']
            print(f"\n  WARNING: No 'Home' page found. Using: ID:{home_id} ({p['title']['rendered']})")
            break

# Step 3: Set homepage
if home_id:
    print(f"\n>> Setting homepage to page ID {home_id}...")
    data = {
        "show_on_front": "page",
        "page_on_front": home_id,
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/settings", headers=headers, json=data)
    if r.status_code == 200:
        result = r.json()
        print(f"  DONE! Homepage: {result.get('page_on_front')}, Show: {result.get('show_on_front')}")
    else:
        print(f"  FAILED: {r.status_code}")
        print(f"  Response: {r.text[:200]}")
else:
    print("\n  FAILED: No pages found. Create a 'Home' page first in WordPress admin.")