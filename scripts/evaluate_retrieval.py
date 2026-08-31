from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from copilot.index import FilingStore
root=Path(__file__).resolve().parents[1]; store=FilingStore(root/".copilot_data")
by_name={x["name"]:x["id"] for x in store.list()}; total=hit1=hit5=0
for line in (root/"practice-questions.jsonl").open(encoding="utf-8"):
 row=json.loads(line); fid=by_name.get(row["doc_name"])
 if not fid:continue
 _,hits=store.search(fid,row["question"],8); expected={e["evidence_page_num"]+1 for e in row["evidence"]}; pages=[p["page"] for _,p in hits]; total+=1; hit1+=bool(set(pages[:1])&expected); hit5+=bool(set(pages[:5])&expected)
print(json.dumps({"questions":total,"page_hit_at_1":round(hit1/max(total,1),3),"page_hit_at_5":round(hit5/max(total,1),3)},indent=2))
