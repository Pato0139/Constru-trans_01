import json
from pathlib import Path

base_path = Path("apps/ia/training")

with open(base_path / "ia_knowledge_base.json", "r", encoding="utf-8") as f:
    kb = json.load(f)

print("Proyecto:", kb["project"])
print("FAQs:", len(kb["faq_entries"]))
print("Intenciones:", len(kb["intent_examples"]))

for faq in kb["faq_entries"]:
    print(faq["id"], "->", faq["best_response"])
