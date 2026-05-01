"""
🌍 Path 1 — Macro Sync: AI Daily Bias Generator
Reads NASDAQ scanner → Claude API → bias.json (readable by MQL5 bots)

Run: python daily_bias_ai.py
Auto: Task Scheduler 08:00 daily (after nasdaq_scanner.py at 07:55)
"""
import sys
import os
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────
OUTPUT_DIR   = Path(__file__).parent
BIAS_MD      = OUTPUT_DIR / "NASDAQ_DAILY_BIAS.md"
BIAS_JSON    = OUTPUT_DIR / "bias.json"

# ── Load Anthropic API Key ────────────────────────────────
# Try from env (set by .env), fallback to tokens.txt
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not API_KEY:
    try:
        tokens_file = Path("C:/Users/gfdh5555/tokens.txt")
        for line in tokens_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("Anthropic API:"):
                API_KEY = line.split(":", 1)[1].strip()
                break
    except:
        pass

if not API_KEY:
    print("❌ ANTHROPIC_API_KEY not found in env or tokens.txt")
    print("   Set environment variable or add to tokens.txt")
    sys.exit(1)

# ── FVG Detection (for bot context) ────────────────────────
def detect_fvg_from_scanner(md_text: str) -> str:
    """Extract indicator readings for FVG context"""
    indicators = {}
    for line in md_text.splitlines():
        for key in ["DXY", "VIX", "SPX", "NDX", "10Y"]:
            if key in line and "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 4:
                    indicators[key] = {"value": parts[1], "change": parts[2]}
    return json.dumps(indicators, indent=2)


# ── Build Prompt ───────────────────────────────────────────
def build_prompt(md_text: str) -> str:
    """Build Claude prompt from NASDAQ scanner output"""
    ind_data = detect_fvg_from_scanner(md_text)

    # Extract BIAS header if present
    bias_line = "NEUTRAL"
    for line in md_text.splitlines():
        if "**BIAS:**" in line:
            bias_line = line.split("**BIAS:**")[-1].strip()
            break

    return f"""You are Moti's Macro Sentinel — Portfolio & Strategy Architect for Commoti AI.

CONTEXT:
- 8 MQL5 bots running on FTMO Hedge $100K (Account 1513254752)
- Risk rules: 4% daily DD max, 0.3% per trade, 2 trades/day
- Bots use ICT/SMC: Liquidity Sweeps, MSS, Fair Value Gaps, Silver Bullet Killzone (10-11 AM NY)
- NASDAQ scanner provides daily macro data

SCANNER BIAS (mechanical): {bias_line}

INDICATOR DATA:
{ind_data}

YOUR TASK:
Analyze the macro data. Output a JSON response with:

1. **bias**: "BULLISH" / "BEARISH" / "NEUTRAL" — only one word
2. **confidence**: 0.0 to 1.0 — how confident you are
3. **reasoning**: 1-2 sentences in Hebrew explaining WHY
4. **risk_level**: "LOW" / "MEDIUM" / "HIGH" — based on VIX < 20 = LOW, VIX 20-30 = MEDIUM, VIX > 30 = HIGH
5. **killzone_advice**: "TRADE" / "CAUTION" / "SKIP" — whether to trade the 10-11 AM Silver Bullet today
6. **pairs_to_focus**: list of 1-3 pairs that look best today (choose from EURUSD, GBPUSD, XAUUSD)

OUTPUT FORMAT (ONLY this JSON, nothing else):
```json
{{
  "bias": "BULLISH",
  "confidence": 0.75,
  "reasoning": "DXY יורד, VIX נמוך, SPX עולה — שוק bull מובהק.",
  "risk_level": "LOW",
  "killzone_advice": "TRADE",
  "pairs_to_focus": ["EURUSD", "XAUUSD"]
}}
```"""


# ── Call Claude API ────────────────────────────────────────
def call_claude(prompt: str) -> str:
    """Send prompt to Claude API, return response text"""
    try:
        import anthropic
    except ImportError:
        print("⚠️ anthropic package not installed. Install: pip install anthropic")
        return '{"error": "anthropic package missing"}'

    client = anthropic.Anthropic(api_key=API_KEY)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            temperature=0.3,  # Low temp for consistency
            system="You are Moti's Macro Sentinel. Output only JSON. No explanations outside JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'


# ── Parse Response ─────────────────────────────────────────
def parse_response(response: str) -> dict:
    """Extract JSON from Claude's response"""
    # Try to find JSON block
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass

    # Fallback: return error
    return {
        "bias": "NEUTRAL",
        "confidence": 0.0,
        "reasoning": f"Failed to parse: {response[:100]}...",
        "risk_level": "MEDIUM",
        "killzone_advice": "CAUTION",
        "pairs_to_focus": ["EURUSD"],
        "error": "PARSE_FAILED",
        "raw_response": response[:200],
    }


# ── Save bias.json ─────────────────────────────────────────
def save_bias(bias_data: dict):
    """Save to bias.json — readable by MQL5 bots"""
    tz = timezone(timedelta(hours=3))  # Israel
    record = {
        "generated_at": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
        "generated_by": "Claude API (daily_bias_ai.py — Path 1 Macro Sync)",
        **bias_data,
    }

    BIAS_JSON.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 Saved: {BIAS_JSON}")


# ── Main ───────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🌍 Path 1 — Macro Sync: AI Daily Bias Generator")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Read scanner output
    if not BIAS_MD.exists():
        print(f"\n⚠️ BIAS file not found: {BIAS_MD}")
        print("   Run nasdaq_scanner.py first.")
        sys.exit(1)

    md_text = BIAS_MD.read_text(encoding="utf-8")
    print(f"\n📖 Read BIAS file: {BIAS_MD.name} ({len(md_text)} chars)")

    # 2. Build prompt
    print("\n🧠 Building Claude prompt...")
    prompt = build_prompt(md_text)

    # 3. Call Claude
    print("📡 Calling Claude API...")
    response = call_claude(prompt)
    print(f"   Response: {response[:150]}...")

    # 4. Parse
    bias_data = parse_response(response)

    # 5. Display result
    print(f"\n📊 Today's BIAS: **{bias_data.get('bias', 'NEUTRAL')}**")
    print(f"   Confidence: {bias_data.get('confidence', 0):.0%}")
    print(f"   Risk Level: {bias_data.get('risk_level', 'MEDIUM')}")
    print(f"   Killzone:   {bias_data.get('killzone_advice', 'CAUTION')}")
    print(f"   Pairs:      {', '.join(bias_data.get('pairs_to_focus', ['EURUSD']))}")
    print(f"   Reasoning:  {bias_data.get('reasoning', 'N/A')}")

    # 6. Save
    save_bias(bias_data)

    # 7. Final note
    print(f"\n✅ Path 1 complete. Next: MetaEditor → F7 Compile 8 bots")
    print(f"   The bots will read bias.json for direction filtering.\n")


if __name__ == "__main__":
    main()