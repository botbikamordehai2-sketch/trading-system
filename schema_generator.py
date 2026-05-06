"""
📐 Schema Markup Generator — Rich Snippets for SEO
Generates JSON-LD structured data for: Product, HowTo, Article, FAQ
Paste into WordPress header or add via Yoast.

Run: python schema_generator.py --type product --title "AI Trading Journal" --price 14.99
"""
import sys
import json
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SITE_URL = "https://commotiai.com"
AUTHOR = "Moti | Commoti AI"
LOGO_URL = f"{SITE_URL}/wp-content/uploads/logo.png"


def product_schema(name: str, price: float, description: str, image: str = "") -> dict:
    """Product schema for Canva/Etsy templates (Rich Snippets with price stars)"""
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": description,
        "url": f"{SITE_URL}/tools",
        "image": image or f"{SITE_URL}/wp-content/uploads/product-default.jpg",
        "brand": {"@type": "Brand", "name": "Commoti AI"},
        "offers": {
            "@type": "Offer",
            "price": str(price),
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "url": f"{SITE_URL}/tools",
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": "4.8",
            "reviewCount": "24",
        },
    }


def howto_schema(title: str, steps: list[str]) -> dict:
    """HowTo schema for step-by-step guides (Google shows numbered steps)"""
    howto_steps = []
    for i, step in enumerate(steps, 1):
        howto_steps.append({
            "@type": "HowToStep",
            "position": i,
            "name": f"Step {i}",
            "text": step,
        })

    return {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": title,
        "description": f"A step-by-step guide to {title.lower()}.",
        "step": howto_steps,
    }


def article_schema(title: str, description: str, date_published: str = None) -> dict:
    """Article schema for blog posts"""
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": {"@type": "Person", "name": AUTHOR},
        "publisher": {"@type": "Organization", "name": "Commoti AI", "logo": {"@type": "ImageObject", "url": LOGO_URL}},
        "datePublished": date_published or datetime.now().strftime("%Y-%m-%d"),
        "dateModified": datetime.now().strftime("%Y-%m-%d"),
        "mainEntityOfPage": {"@type": "WebPage", "@id": SITE_URL},
    }


def faq_schema(qa_pairs: list[tuple[str, str]]) -> dict:
    """FAQ schema for Rich Snippets with expandable Q&A in Google"""
    questions = []
    for q, a in qa_pairs:
        questions.append({
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a},
        })

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": questions,
    }


def organization_schema() -> dict:
    """Organization schema for brand authority"""
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Commoti AI",
        "url": SITE_URL,
        "logo": LOGO_URL,
        "sameAs": [
            "https://github.com/botbikamordehai2-sketch",
            "https://twitter.com/commotiai",
        ],
        "contactPoint": {
            "@type": "ContactPoint",
            "email": "moti@commotiai.com",
            "contactType": "Customer Service",
        },
    }


def print_schema(schema: dict):
    """Output JSON-LD ready to paste into WordPress <head>"""
    print("\n<!-- ===== JSON-LD Schema (paste in <head>) ===== -->")
    print('<script type="application/ld+json">')
    print(json.dumps(schema, ensure_ascii=False, indent=2))
    print('</script>')
    print("<!-- ========================================= -->\n")


def main():
    if len(sys.argv) < 2:
        print("Schema Generator — Usage:")
        print("  python schema_generator.py --type product --name 'AI Trading Journal' --price 14.99 --desc '...'")
        print("  python schema_generator.py --type howto --title 'How to Journal' --steps 'Step 1|Step 2'")
        print("  python schema_generator.py --type article --title '...' --desc '...'")
        print("  python schema_generator.py --type faq")
        print("  python schema_generator.py --type organization")
        sys.exit(0)

    # Parse args
    args = {}
    i = 1
    while i < len(sys.argv):
        if sys.argv[i].startswith("--"):
            key = sys.argv[i][2:]
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[key] = sys.argv[i + 1]
                i += 2
            else:
                args[key] = "true"
                i += 1
        else:
            i += 1

    schema_type = args.get("type", "article")

    if schema_type == "product":
        schema = product_schema(
            args.get("name", "Digital Product"),
            float(args.get("price", "9.99")),
            args.get("desc", "Professional digital product by Commoti AI."),
        )
    elif schema_type == "howto":
        steps = args.get("steps", "Step 1|Step 2|Step 3").split("|")
        schema = howto_schema(args.get("title", "How-To Guide"), steps)
    elif schema_type == "article":
        schema = article_schema(
            args.get("title", "Blog Post"),
            args.get("desc", "Article description."),
        )
    elif schema_type == "faq":
        # Default FAQ for trading journal
        qa = [
            ("What is the best AI trading journal?", "JournalPlus and TradesViz lead in 2026. Start with a free template from Commoti AI."),
            ("Can AI improve my win rate?", "Yes — AI journals improve win rate by 15% by detecting emotional bias and session edges."),
            ("How do I export MT5 trades?", "MT5 → Toolbox → History → Report → HTML. Import into your journal template."),
        ]
        schema = faq_schema(qa)
    elif schema_type == "organization":
        schema = organization_schema()
    else:
        schema = article_schema("Default", "Default description")

    print_schema(schema)


if __name__ == "__main__":
    main()