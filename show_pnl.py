import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from daily_review import close_signals_auto, load_log

print("Running close_signals_auto...")
close_signals_auto()

data = load_log()
closed = [s for s in data if s.get("closed")]
wins = sum(1 for s in closed if s.get("result") == "WIN")
losses = sum(1 for s in closed if s.get("result") == "LOSS")
net = sum(s.get("pct", 0) or 0 for s in closed)

print(f"\n=== PnL SUMMARY ===")
print(f"Total signals: {len(data)}")
print(f"Closed: {len(closed)}  ({wins} WINS / {losses} LOSSES)")
print(f"Net PnL: {net:+.2f}%")
print()

for s in sorted(closed, key=lambda x: x["date"]):
    icon = "OK" if s["result"] == "WIN" else "XX"
    print(f"{icon}  {s['date']}  |  {s['name']:8} {s['direction']:5}  |  {s.get('pct', 0):+.2f}%")