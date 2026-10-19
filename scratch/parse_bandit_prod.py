import json

with open("scratch/bandit_production.json", "r", encoding="utf-8") as f:
    data = json.load(f)

totals = data.get("metrics", {}).get("_totals", {})
print("Totals:", totals)

results = data.get("results", [])
print(f"Total findings: {len(results)}\n")
for i, r in enumerate(results, 1):
    sev = r.get("issue_severity")
    conf = r.get("issue_confidence")
    test_id = r.get("test_id")
    fname = r.get("filename")
    line = r.get("line_number")
    text = r.get("issue_text")
    print(f"{i}. [{sev} / {conf}] {test_id} @ {fname}:{line}")
    print(f"   {text}\n")
