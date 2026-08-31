from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from copilot.index import FilingStore
root=Path(__file__).resolve().parents[1]; store=FilingStore(root/".copilot_data"); files=list((root/"filings").glob("*"))
for i,path in enumerate(files,1):
 job=store.begin(path.name); store.process(job,path.read_bytes()); status=store.status(job); print(f"[{i}/{len(files)}] {path.name}: {status['status']} ({status.get('pages',0)} pages)")
