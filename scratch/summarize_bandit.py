import json

with open('scratch/bandit_report.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

metrics = data.get('metrics', {}).get('_totals', {})
print('Bandit totals:', metrics)
results = data.get('results', [])
print(f'Total issues: {len(results)}')
high_medium = [r for r in results if r['issue_severity'] in ('HIGH', 'MEDIUM')]
print(f'HIGH/MEDIUM issues: {len(high_medium)}')
for r in high_medium:
    print(f"[{r['issue_severity']}] {r['test_name']} in {r['filename']}:{r['line_number']} - {r['issue_text']}")
