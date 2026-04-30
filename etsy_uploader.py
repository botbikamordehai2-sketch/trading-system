"""
🏪 TRACK 3 — Etsy Bulk Uploader
מעלה את 10 מוצרי Canva ל-Etsy (TradingTemplateHub)

דרישות:
  - ETSY_API_KEY ב-.env
  - ETSY_SHOP_ID ב-.env

הרצה: python etsy_uploader.py [--dry-run]
"""
import sys
import os
import json
import csv
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path.home() / "tv_webhook" / ".env")

ETSY_API_KEY = os.getenv("ETSY_API_KEY", "")
ETSY_SHOP_ID = os.getenv("ETSY_SHOP_ID", "")

# נתיבים
CATALOG_FILE = Path(__file__).parent.parent / "canva-assets" / "catalog.json"
OUTPUT_DIR   = Path(__file__).parent / "etsy_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Etsy category IDs (Trading niche)
CATEGORY_BUSINESS = 361   # Business & Industrial
DIGITAL_DOWNLOAD  = True

# Canva template link placeholder (עדכן אחרי יצירת template links אמיתיים)
CANVA_TEMPLATE_LINKS = {
    "TTH-001": "https://www.canva.com/design/XXXXXXXXX/trading-journal",
    "TTH-002": "https://www.canva.com/design/XXXXXXXXX/ict-planner",
    "TTH-003": "https://www.canva.com/design/XXXXXXXXX/forex-cheat-sheets",
    "TTH-004": "https://www.canva.com/design/XXXXXXXXX/dark-theme",
    "TTH-005": "https://www.canva.com/design/XXXXXXXXX/crypto-tracker",
    "TTH-006": "https://www.canva.com/design/XXXXXXXXX/social-media",
    "TTH-007": "https://www.canva.com/design/XXXXXXXXX/risk-calculator",
    "TTH-008": "https://www.canva.com/design/XXXXXXXXX/business-plan",
    "TTH-009": "https://www.canva.com/design/XXXXXXXXX/market-report",
    "TTH-010": "https://www.canva.com/design/XXXXXXXXX/ultimate-bundle",
}


def load_catalog():
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_csv(catalog: dict, dry_run: bool = True):
    """מייצר CSV מוכן ל-Etsy"""
    products = catalog.get("products", [])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_DIR / f"etsy_upload_{timestamp}.csv"

    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "title", "description", "price", "quantity", "tags",
            "who_made", "when_made", "is_digital", "canva_link",
        ])

        for p in products:
            product_id = p["id"]
            canva_link = CANVA_TEMPLATE_LINKS.get(product_id, "TBD")

            # Description with Canva link
            desc = (
                f"{p['description']}\n\n"
                f"📊 {p['pages']} pages | 🎨 Fully editable in Canva (free account works)\n"
                f"📥 Instant download — {p['format']}\n\n"
                f"🔗 Canva Template Link included in download\n"
                f"💬 Questions? Message me — I reply within 24h\n\n"
                f"Tags: {', '.join(p['tags'][:5])}"
            )

            writer.writerow([
                p["title"],
                desc,
                p["price_usd"],
                999,  # quantity (digital = unlimited)
                ", ".join(p["tags"][:13]),  # Etsy max 13 tags
                "i_did",       # who_made
                "2024_2026",   # when_made
                "TRUE",        # digital
                canva_link,
            ])

        # Summary row
        writer.writerow([])
        writer.writerow(["SUMMARY", "", f"${sum(p['price_usd'] for p in products):.2f} total", str(len(products)), "", "", "", "", ""])

    return filename


def generate_markdown(catalog: dict):
    """מייצר Markdown עם כל המוצרים — לשליחה לעצמך"""
    products = catalog.get("products", [])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_DIR / f"etsy_listings_{timestamp}.md"

    lines = [
        f"# 🏪 {catalog['shop_name']} — Etsy Listings",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> Niche: {catalog['niche']}",
        "",
    ]

    for p in products:
        product_id = p["id"]
        canva_link = CANVA_TEMPLATE_LINKS.get(product_id, "TBD")

        lines.append(f"## {p['title']}")
        lines.append(f"**Price:** ${p['price_usd']} | **Pages:** {p['pages']} | **Format:** {p['format']}")
        lines.append(f"**Category:** {p['category']}")
        lines.append(f"**Tags:** {', '.join(p['tags'][:8])}")
        lines.append("")
        lines.append(p["description"])
        lines.append("")
        lines.append(f"🔗 Canva Link: {canva_link}")
        lines.append("---")
        lines.append("")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filename


def main():
    print("=" * 60)
    print("🏪 TRACK 3 — Etsy Bulk Uploader")
    print("=" * 60)

    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("⚠️ DRY RUN — מייצר קבצים בלבד, לא מעלה")

    if not ETSY_API_KEY:
        print("❌ ETSY_API_KEY not found in .env")
        print("   CSV/Markdown יופקו אבל לא תהיה העלאה אוטומטית")
        print("   הוסף ETSY_API_KEY ב-.env להעלאה אוטומטית")

    catalog = load_catalog()
    products = catalog.get("products", [])
    print(f"\n📦 מוצרים בקטלוג: {len(products)}")
    total = sum(p["price_usd"] for p in products)
    print(f"💰 סה\"כ ערך: ${total:.2f}")
    print(f"🏷️  חנות: {catalog['shop_name']}")

    # Generate CSV
    csv_file = generate_csv(catalog, dry_run=dry_run)
    print(f"\n✅ CSV: {csv_file}")

    # Generate Markdown
    md_file = generate_markdown(catalog)
    print(f"✅ Markdown: {md_file}")

    print()
    print("📋 צעדים להעלאה:")
    print("1. עדכן CANVA_TEMPLATE_LINKS בסקריפט עם קישורים אמיתיים מקנבה")
    print("2. העלה CSV ל-Etsy דרך Seller Dashboard")
    print('   או: python -c "from etsy_uploader import upload_to_etsy; upload_to_etsy()"')
    print(f"3. עלות: ${len(products) * 0.20:.2f} ({len(products)} listings × $0.20)")
    print()

    if ETSY_API_KEY and not dry_run:
        print("🔌 ETSY API Key found — attempting upload...")
        upload_to_etsy(catalog)
    elif dry_run:
        print("🏁 DRY RUN complete — review CSV and Markdown then remove --dry-run")
    else:
        print("🏁 Ready for upload — add ETSY_API_KEY to .env and remove --dry-run")


def upload_to_etsy(catalog: dict):
    """מעלה מוצרים ל-Etsy דרך API"""
    import requests

    products = catalog.get("products", [])
    uploaded = 0
    failed = 0

    for p in products:
        product_id = p["id"]
        canva_link = CANVA_TEMPLATE_LINKS.get(product_id)

        payload = {
            "quantity": 999,
            "title": p["title"][:140],
            "description": (
                f"{p['description']}\n\n"
                f"📊 {p['pages']} pages | 🎨 Canva Editable\n"
                f"📥 {p['format']}\n"
                f"🔗 Template Link: {canva_link}"
            ),
            "price": p["price_usd"],
            "who_made": "i_did",
            "when_made": "2024_2026",
            "is_supply": False,
            "is_digital": True,
            "tags": p["tags"][:13],
            "type": "download",
        }

        try:
            r = requests.post(
                f"https://openapi.etsy.com/v3/application/shops/{ETSY_SHOP_ID}/listings",
                headers={
                    "x-api-key": ETSY_API_KEY,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )

            if r.status_code in (200, 201):
                print(f"  ✅ {product_id}: {p['title'][:50]}...")
                uploaded += 1
            else:
                print(f"  ❌ {product_id}: {r.status_code} — {r.text[:100]}")
                failed += 1

        except Exception as e:
            print(f"  ❌ {product_id}: Error — {e}")
            failed += 1

    print(f"\n📊 Upload Summary: {uploaded} success, {failed} failed")


if __name__ == "__main__":
    main()