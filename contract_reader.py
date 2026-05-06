"""
📄 AI Contract Reader — Post #16 Implementation
קורא PDF/DOCX/TXT של חוזה, מדגיש סעיפים בעייתיים

הרצה: python contract_reader.py "path/to/contract.pdf"
"""
import sys
import re
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════
# RULES — What to flag in contracts
# ═══════════════════════════════════════════════════════════
CONTRACT_RULES = {
    "⚠️ No Termination Clause": {
        "keywords": ["termination", "cancel", "terminate", "ביטול", "סיום"],
        "flag_if_missing": True,
        "severity": "HIGH",
    },
    "⚠️ Unlimited Liability": {
        "keywords": ["unlimited liability", "without limitation", "full liability", "אחריות בלתי מוגבלת"],
        "severity": "HIGH",
    },
    "⚠️ Auto-Renewal Trap": {
        "keywords": ["auto-renewal", "automatic renewal", "automatically renewed", "חידוש אוטומטי"],
        "severity": "MEDIUM",
    },
    "⚠️ Non-Compete (broad)": {
        "keywords": ["non-compete", "non compete", "not compete", "אי תחרות", "תחרות"],
        "severity": "MEDIUM",
    },
    "⚠️ IP Assignment": {
        "keywords": ["intellectual property", "all IP", "assigns all", "קניין רוחני", "כל זכויות"],
        "severity": "MEDIUM",
    },
    "⚠️ Venue/Law Clause": {
        "keywords": ["governed by", "venue", "jurisdiction", "בית משפט", "סמכות"],
        "severity": "LOW",
    },
    "⚠️ Payment Terms Vague": {
        "keywords": ["net 30", "net 60", "net 90", "payable within", "תשלום תוך"],
        "severity": "LOW",
    },
}


# ═══════════════════════════════════════════════════════════
# CONTRACT READER
# ═══════════════════════════════════════════════════════════
def read_contract(filepath: str) -> str:
    """קורא חוזה — TXT ישיר, PDF/DOCX בעתיד"""
    path = Path(filepath)
    if not path.exists():
        return f"❌ File not found: {filepath}"

    if path.suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    elif path.suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return " ".join(page.extract_text() for page in reader.pages if page.extract_text())
        except ImportError:
            return "⚠️ pypdf not installed. Run: pip install pypdf\n📋 Reading as text anyway...\n" + path.read_bytes().decode("utf-8", errors="replace")
    else:
        return path.read_text(encoding="utf-8", errors="replace")


def analyze_contract(text: str) -> list[dict]:
    """בודק חוזה לפי רשימת דגלים אדומים"""
    findings = []
    text_lower = text.lower()

    for title, rule in CONTRACT_RULES.items():
        if rule.get("flag_if_missing"):
            # Missing check
            found = any(kw.lower() in text_lower for kw in rule["keywords"])
            if not found:
                findings.append({
                    "title": title,
                    "severity": rule["severity"],
                    "detail": f"Contract doesn't mention: {rule['keywords'][0]}",
                    "found": False,
                })
        else:
            # Presence check
            for kw in rule["keywords"]:
                if kw.lower() in text_lower:
                    findings.append({
                        "title": title,
                        "severity": rule["severity"],
                        "detail": f"Found: '{kw}'"
                    })
                    break

    return findings


def print_report(filepath: str, text: str, findings: list[dict]):
    """מדפיס דו״ח"""
    print("=" * 60)
    print(f"📄 AI Contract Reader — Analysis Report")
    print(f"📁 File: {Path(filepath).name}")
    print(f"📏 Length: {len(text)} chars")
    print("=" * 60)

    if not findings:
        print("\n✅ No red flags found.")
        return

    severity_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 4))

    print(f"\n🚩 {len(findings)} Issues Found:\n")
    for i, f in enumerate(findings, 1):
        icon = "🔴" if f["severity"] == "HIGH" else "🟡" if f["severity"] == "MEDIUM" else "🔵"
        status = "MISSING" if not f.get("found", True) else "FOUND"
        print(f"  {icon} #{i} [{f['severity']}] {f['title']}")
        print(f"     {f['detail']} ({status})")

    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    med_count = sum(1 for f in findings if f["severity"] == "MEDIUM")
    low_count = sum(1 for f in findings if f["severity"] == "LOW")
    print(f"\n📊 Summary: 🔴{high_count} Critical  🟡{med_count} Warning  🔵{low_count} Info")
    print(f"\n💡 Recommendation: ", end="")
    if high_count > 0:
        print("⚠️ DO NOT SIGN — consult a lawyer.")
    elif med_count > 2:
        print("🟡 REVIEW carefully before signing.")
    else:
        print("✅ Looks reasonable — final review recommended.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python contract_reader.py <contract_file.txt>")
        print("Example: python contract_reader.py C:\\Users\\gfdh5555\\Desktop\\contract.txt")
        sys.exit(1)

    filepath = sys.argv[1]
    text = read_contract(filepath)
    if text.startswith("❌") or text.startswith("⚠️"):
        print(text)
        sys.exit(1)

    findings = analyze_contract(text)
    print_report(filepath, text, findings)