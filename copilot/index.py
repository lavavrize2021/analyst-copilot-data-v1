from __future__ import annotations
import hashlib, json, math, re, time, uuid
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
TOKEN=re.compile(r"[a-zA-Z][a-zA-Z0-9&.-]*|\d[\d,.]*")
BREAK=re.compile(r"page-break-(?:after|before)\s*:\s*always",re.I)
STOP=set("the a an of in to for and is was were what by as on from company following using answer".split())
def tokens(s): return [x.lower().strip(".,") for x in TOKEN.findall(s) if x.lower() not in STOP]
class PageParser(HTMLParser):
 def __init__(self): super().__init__(convert_charrefs=True); self.pages=[[]]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if BREAK.search(a.get("style","")) and self.pages[-1]: self.pages.append([])
  if tag in {"br","p","div","tr","li","h1","h2","h3"}: self.pages[-1].append("\n")
  if tag in {"td","th"}: self.pages[-1].append(" | ")
 def handle_data(self,data): self.pages[-1].append(data)
def parse_document(raw,suffix):
 text=raw.decode("utf-8","replace")
 if suffix in {".html",".htm"}:
  p=PageParser(); p.feed(text); pages=[" ".join("".join(x).split()) for x in p.pages]
 elif suffix in {".txt",".md"}: pages=[" ".join(x.split()) for x in text.split("\f")]
 else: raise ValueError("Supported filing formats: HTML, HTM, TXT")
 return [p for p in pages if len(p)>10]
class FilingStore:
 def __init__(self,root:Path):
  self.root=root; root.mkdir(exist_ok=True); self.jobs={}; self.catalog=root/"catalog.json"; self.docs={}
  if self.catalog.exists():
   try:self.docs=json.loads(self.catalog.read_text(encoding="utf-8"))
   except Exception:pass
 def begin(self,name):
  if Path(name).suffix.lower() not in {".htm",".html",".txt",".md"}:raise ValueError("Upload an HTML or text filing")
  jid=uuid.uuid4().hex; self.jobs[jid]={"job_id":jid,"status":"queued","name":Path(name).name,"progress":0}; return jid
 def process(self,jid,raw):
  try:
   self.jobs[jid].update(status="processing",progress=10); name=self.jobs[jid]["name"]; pages=parse_document(raw,Path(name).suffix.lower()); self.jobs[jid]["progress"]=65; fid=hashlib.sha256(raw).hexdigest()[:16]
   records=[{"page":i,"text":p,"tf":dict(Counter(tokens(p)))} for i,p in enumerate(pages,1)]; (self.root/f"{fid}.json").write_text(json.dumps(records,ensure_ascii=False),encoding="utf-8")
   self.docs[fid]={"id":fid,"name":Path(name).stem,"pages":len(records),"added":int(time.time())}; self.catalog.write_text(json.dumps(self.docs,indent=2),encoding="utf-8"); self.jobs[jid].update(status="ready",progress=100,filing_id=fid,pages=len(records))
  except Exception as e:self.jobs[jid].update(status="error",error=str(e),progress=0)
 def list(self):return sorted(self.docs.values(),key=lambda x:x["added"],reverse=True)
 def status(self,jid):return self.jobs.get(jid,{"status":"unknown","error":"Job not found"})
 def load(self,fid):
  if fid not in self.docs:raise ValueError("Choose a processed filing")
  return self.docs[fid],json.loads((self.root/f"{fid}.json").read_text(encoding="utf-8"))
 def search(self,fid,query,k=8):
  meta,pages=self.load(fid); q=tokens(query)
  low=query.lower()
  expansions={
   "capital expenditure":"purchases property plant equipment pp&e capex",
   "capex":"purchases property plant equipment",
   "net ppne":"property plant equipment net",
   "revenue":"net sales revenues",
   "free cash flow":"operating activities capital expenditures",
   "debt":"borrowings notes payable long-term debt",
   "inventory":"inventories",
   "asset turnover":"average total assets revenues turnover",
   "turnover":"average total assets revenues",
   "return on assets":"average total assets net income roa",
   "return on equity":"net income equity roe shareholders",
   "operating income":"operating selling general administrative expenses",
   "net income":"consolidated net income earnings attributable walmart",
   "operating income":"income operating selling general administrative expenses revenues costs",
   "gross margin":"net sales cost gross profit",
   "net sales":"revenues net sales membership income",
   "average total assets":"total assets average beginning ending",
  }
  for phrase,extra in expansions.items():
   if phrase in low:q.extend(tokens(extra))
  if not q:return meta,[]
  n=len(pages); df=Counter(t for p in pages for t in p["tf"]); avg=sum(sum(p["tf"].values()) for p in pages)/max(n,1); out=[]
  for p in pages:
   dl=sum(p["tf"].values()); score=0
   for t in q:
    f=p["tf"].get(t,0); idf=math.log(1+(n-df[t]+.5)/(df[t]+.5)); score+=idf*f*2.2/(f+1.2*(.25+.75*dl/max(avg,1)))
   if score:out.append((score,p))
  out.sort(key=lambda x:x[0],reverse=True); return meta,out[:k]
