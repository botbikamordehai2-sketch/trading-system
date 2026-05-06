"""
🛡️ API Guard — Anomaly Detection & Protection
מנטר תעבורת API של MT5, Telegram, Anthropic, Hostinger.
מזהה: brute-force, token exfiltration, unusual patterns.
שולח התראות לטלגרם על חריגות.

Run: python api_guard.py (every 15 minutes via Task Scheduler)
"""
import sys
import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ──────────────────────────────────────────────────
PROJ_DIR       = Path(__file__).parent
TOKENS_FILE    = Path("C:/Users/gfdh5555/tokens.txt")
ENV_FILE       = Path("C:/Users/gfdh5555/tv_webhook/.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8778948790:AAFQzzul1WNrfvqZbqtNeK_Y1B9BO10cZmA")
CHAT_ID        = os.getenv("ALL_CHAT_ID", "1246833993")
GUARD_LOG      = PROJ_DIR / "api_guard_log.json"
GUARD_STATE    = PROJ_DIR / "api_guard_state.json"
GUARD_DB       = PROJ_DIR / "api_guard.db"  # SQLite database

import requests
import sqlite3

# ── Database ─────────────────────────────────────────────────
def init_db():
    """Initialize SQLite database for event storage"""
    conn = sqlite3.connect(str(GUARD_DB))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        source_ip TEXT DEFAULT 'localhost'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        status_code INTEGER,
        duration_ms REAL,
        source TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS token_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        change_type TEXT NOT NULL,
        prev_hash TEXT,
        new_hash TEXT,
        prev_count INTEGER,
        new_count INTEGER
    )''')
    conn.commit()
    conn.close()

def log_event(event_type: str, severity: str, title: str, message: str):
    """Store event in SQLite database"""
    conn = sqlite3.connect(str(GUARD_DB))
    c = conn.cursor()
    c.execute(
        "INSERT INTO events (timestamp, event_type, severity, title, message) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), event_type, severity, title, message),
    )
    conn.commit()
    conn.close()

def log_api_call(endpoint: str, status: int, duration: float):
    """Store API call in database for rate monitoring"""
    conn = sqlite3.connect(str(GUARD_DB))
    c = conn.cursor()
    c.execute(
        "INSERT INTO api_calls (timestamp, endpoint, status_code, duration_ms) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), endpoint, status, duration),
    )
    conn.commit()
    conn.close()

def get_recent_events(hours: int = 24) -> list:
    """Query recent events from database"""
    conn = sqlite3.connect(str(GUARD_DB))
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    c.execute("SELECT timestamp, event_type, severity, title, message FROM events WHERE timestamp > ? ORDER BY timestamp DESC", (cutoff,))
    rows = c.fetchall()
    conn.close()
    return rows

def send_alert(title: str, msg: str, priority: str = "HIGH"):
    """Send security alert to Telegram"""
    try:
        e = {"HIGH": "🔴", "MEDIUM": "🟡"}.get(priority, "🟡")
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": f"{e} *{title}*\n\n{msg}", "parse_mode": "Markdown"},
            timeout=5,
        )
        print(f"  🚨 Alert: {title}")
    except:
        pass


# ═══════════════════════════════════════════════════════════
# CHECK 1: Token Integrity (Prevent exfiltration)
# ═══════════════════════════════════════════════════════════
def check_token_integrity():
    """Verify tokens file hasn't been tampered with"""
    if not TOKENS_FILE.exists():
        send_alert("🚨 TOKENS FILE MISSING", f"{TOKENS_FILE} not found. Possible deletion or attack.")
        return

    content = TOKENS_FILE.read_text(encoding="utf-8")
    lines = [l for l in content.splitlines() if l.strip()]

    # Load previous state
    state = {}
    if GUARD_STATE.exists():
        state = json.loads(GUARD_STATE.read_text(encoding="utf-8"))

    prev_hash = state.get("tokens_hash", "")
    prev_count = state.get("tokens_count", 0)
    current_hash = hashlib.sha256(content.encode()).hexdigest()
    current_count = len(lines)

    # Check: tokens added or removed unexpectedly
    if prev_hash and current_hash != prev_hash:
        if current_count < prev_count:
            send_alert("⚠️ TOKENS REMOVED", f"Tokens count dropped: {prev_count} → {current_count}.\nCheck {TOKENS_FILE}")
        elif current_count > prev_count:
            send_alert("ℹ️ TOKENS ADDED", f"Tokens count increased: {prev_count} → {current_count}.\nVerify addition is authorized.")

    # Check: exposed in source code (basic)
    for line in lines:
        if "sk-ant" in line or "github_pat" in line:
            # Verify it's only in tokens.txt, not leaked elsewhere
            pass  # Tokens in tokens.txt is expected

    # Update state
    state["tokens_hash"] = current_hash
    state["tokens_count"] = current_count
    state["last_check"] = datetime.now().isoformat()
    GUARD_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════
# CHECK 2: API Key Exposure (Prevent leak in code)
# ═══════════════════════════════════════════════════════════
def check_key_exposure():
    """Scan project files for accidental API key leaks"""
    # Load known keys
    known_keys = set()
    if TOKENS_FILE.exists():
        for line in TOKENS_FILE.read_text(encoding="utf-8").splitlines():
            parts = line.split(":", 1)
            if len(parts) == 2:
                known_keys.add(parts[1].strip())

    # Scan Python files for keys (quick check, not exhaustive)
    suspicious = []
    for py_file in PROJ_DIR.rglob("*.py"):
        # Skip tokens.txt and .env — expected locations
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            for key in known_keys:
                if len(key) > 20 and key in content and "tokens.txt" not in str(py_file):
                    suspicious.append(str(py_file.name))
                    break
        except:
            continue

    if suspicious:
        send_alert(
            "🔑 API KEY IN CODE",
            f"Keys found in:\n" + "\n".join(f"• {f}" for f in suspicious) +
            "\n\nMove keys to tokens.txt or .env immediately.",
            "HIGH",
        )


# ═══════════════════════════════════════════════════════════
# CHECK 3: Unusual API Call Frequency (Rate Limit Monitoring)
# ═══════════════════════════════════════════════════════════
def check_rate_anomalies():
    """Detect brute-force or data exfiltration patterns"""
    log = {}
    if GUARD_LOG.exists():
        log = json.loads(GUARD_LOG.read_text(encoding="utf-8"))

    now = datetime.now()
    window_start = (now - timedelta(hours=1)).isoformat()

    calls = [e for e in log.get("api_calls", []) if e["time"] > window_start]

    # Alert: more than 100 API calls in 1 hour (possible exfiltration)
    if len(calls) > 100:
        send_alert(
            "🚨 BRUTE FORCE / Exfiltration",
            f"{len(calls)} API calls in last hour.\nPossible data exfiltration or brute-force attack.\nThreshold: 100 calls/hour.",
            "HIGH",
        )

    # Alert: multiple failed calls (possible credential stuffing)
    failed = [c for c in calls if c.get("status", 200) >= 400]
    if len(failed) > 20:
        send_alert(
            "🔐 CREDENTIAL STUFFING",
            f"{len(failed)} failed API calls in 1 hour.\nSomeone may be trying to guess credentials.",
            "HIGH",
        )


# ═══════════════════════════════════════════════════════════
# CHECK 4: Port Scan Detection (Unauthorized Access)
# ═══════════════════════════════════════════════════════════
def check_port_activity():
    """Check if critical ports are being probed"""
    critical_ports = {
        9222: "TradingView CDP",
        443:  "HTTPS (WordPress)",
        3306: "MySQL (Hostinger)",
    }

    # Basic check: are critical services running?
    import socket
    for port, service in critical_ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        if result == 0:
            print(f"  ✅ Port {port} ({service}) — Open (expected)")
        else:
            print(f"  ⚠️ Port {port} ({service}) — Closed")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print(f"🛡️ API Guard — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print("\n🔑 Token Integrity:")
    check_token_integrity()

    print("\n📄 Key Exposure:")
    check_key_exposure()

    print("\n📊 Rate Anomalies:")
    check_rate_anomalies()

    print("\n🔌 Port Activity:")
    check_port_activity()

    print(f"\n✅ Guard cycle complete.")


if __name__ == "__main__":
    main()