import json,os,re
from urllib.request import Request,urlopen
ABSTAIN="Not found in this filing."
def _snippet(text,terms,limit=1000):
 low=text.lower(); pos=[low.find(t) for t in terms if len(t)>3 and low.find(t)>=0]; at=min(pos) if pos else 0; start=max(0,at-220); return text[start:start+limit].strip()
def _ollama(question,hits):
 evidence="\n\n".join(f"[PAGE {p['page']}] {p['text'][:2000]}" for _,p in hits[:5])
 prompt=f'''You are a conservative financial filing analyst. Answer ONLY from the filing evidence below.
Return one JSON object with exactly these keys:
{{"answer":"short precise answer or Not found in this filing.","page":integer_or_null,"quote":"short verbatim proving quote","confidence":number_0_to_1}}
Resolve the requested year, table column, sign, and units carefully. For a calculation, include inputs and arithmetic in answer. The quote must be copied verbatim from one cited page. If evidence is insufficient or ambiguous, abstain. Do not add markdown.

QUESTION: {question}

EVIDENCE:
{evidence}'''
 body={"model":os.getenv("OLLAMA_MODEL","qwen2.5:3b"),"messages":[{"role":"user","content":prompt}],"format":"json","stream":False,"options":{"temperature":0}}
 req=Request(os.getenv("OLLAMA_URL","http://127.0.0.1:11434")+"/api/chat",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
 with urlopen(req,timeout=180) as r:data=json.load(r)
 return json.loads(data["message"]["content"])
def answer_question(store,filing_id,question):
 question=question.strip()
 if len(question)<4:raise ValueError("Enter a specific analyst question")
 meta,hits=store.search(filing_id,question)
 if not hits:return {"answer":ABSTAIN,"declined":True,"document":meta["name"],"evidence":[]}
 print(f"[RETRIEVAL] pages={[p['page'] for _,p in hits]}")
 result=None
 try:result=_ollama(question,hits)
 except Exception as exc:print("Answer model unavailable:",exc)
 if result:
  page=next((p for _,p in hits if p["page"]==result.get("page")),None); quote=result.get("quote","").strip(); normalized=lambda s:" ".join(re.sub(r"[|$,]"," ",s).lower().split()); valid=page and quote and normalized(quote) in normalized(page["text"])
  print(f"[DEBUG] answer={result.get('answer')!r} confidence={result.get('confidence')} page={result.get('page')} quote={quote!r} valid={valid}")
  if result.get("answer")==ABSTAIN or result.get("confidence",0)<.72 or not valid:return {"answer":ABSTAIN,"declined":True,"document":meta["name"],"evidence":[]}
  return {"answer":result["answer"],"declined":False,"document":meta["name"],"evidence":[{"page":page["page"],"quote":quote}]}
 terms=[x.lower() for x in re.findall(r"[A-Za-z]{4,}",question)]
 return {"answer":ABSTAIN,"declined":True,"document":meta["name"],"evidence":[{"page":p["page"],"quote":_snippet(p["text"],terms)} for _,p in hits[:3]],"note":"Local answer model unavailable; start Ollama and ensure the configured model is installed."}
