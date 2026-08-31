import json,os,re
from urllib.request import Request,urlopen
ABSTAIN="Not found in this filing."
CALC_RE=re.compile(r'\b(calculat|divid|ratio|percent|turnover|margin|growth|averag|multiply|subtract|change|compar|difference|increase|decrease|between)\b',re.I)
RATIO_RE=re.compile(r'\b(calculat|divid|ratio|turnover|margin|averag|multiply)\b',re.I)

def _snippet(text,terms,limit=600):
 low=text.lower(); pos=[low.find(t) for t in terms if len(t)>3 and low.find(t)>=0]; at=min(pos) if pos else 0; start=max(0,at-200); return text[start:start+limit].strip()

def _clean(text):
 # Convert pipe-separated HTML table cells to readable prose
 parts=[p.strip() for p in text.split('|') if p.strip()]
 return ' '.join(parts)

def _norm(s):
 return ' '.join(re.sub(r'[$,]','',s).lower().split())

def _recompute(answer_text):
 # Parse explicit division from model answer: "X / Y" → recompute in Python
 m=re.search(r'([\d,]+(?:\.\d+)?)\s*[/÷]\s*([\d,]+(?:\.\d+)?)',answer_text)
 if m:
  num=float(m.group(1).replace(',',''));den=float(m.group(2).replace(',',''))
  if den:return round(num/den,2)
 return None

def _ollama(question,hits,terms,calc_mode,ratio_mode):
 n_pages=4 if calc_mode else 3
 snippets=[_clean(_snippet(p['text'],terms,600)) for _,p in hits[:n_pages]]
 evidence="\n\n".join(f"[PAGE {p['page']}] {s}" for (_,p),s in zip(hits[:n_pages],snippets))
 if ratio_mode:
  fmt='{"answer":"show arithmetic as numerator / denominator = result with units (e.g. $500,343M / $201,674M = 2.48)","page":integer_or_null,"quote":"short verbatim quote 4-6 words","confidence":number_0_to_1}'
  extra='Extract the exact raw numbers from the evidence. Show arithmetic explicitly as X / Y = Z in the answer field so the result can be verified. Round to two decimal places.'
 elif calc_mode:
  fmt='{"answer":"precise natural language answer showing both values and their difference/change with units","page":integer_or_null,"quote":"short verbatim quote 4-6 words","confidence":number_0_to_1}'
  extra='For comparisons, state both values and the change (e.g. "Increased from $481,317M in FY2017 to $495,761M in FY2018, a change of +$14,444M (+3.0%)").'
 else:
  fmt='{"answer":"precise natural language answer with units (e.g. $500,343 million) or Not found in this filing.","page":integer_or_null,"quote":"short verbatim quote 4-6 words","confidence":number_0_to_1}'
  extra='Express the answer with proper units and formatting (e.g. "$500,343 million" not "500343"). Quote must be under 8 words.'
 prompt=f'''You are a conservative financial filing analyst. Answer ONLY from the filing evidence below.
Return one JSON object: {fmt}
Resolve the requested year, table column, sign, and units carefully. {extra} If evidence is insufficient, answer exactly "Not found in this filing." Do not add markdown.

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
 terms=[x.lower() for x in re.findall(r"[A-Za-z]{4,}",question)]
 calc_mode=bool(CALC_RE.search(question))
 ratio_mode=bool(RATIO_RE.search(question))
 print(f"[RETRIEVAL] pages={[p['page'] for _,p in hits]} calc={calc_mode} ratio={ratio_mode}")
 result=None
 try:result=_ollama(question,hits,terms,calc_mode,ratio_mode)
 except Exception as exc:print("Answer model unavailable:",exc)
 if result:
  page=next((p for _,p in hits if p["page"]==result.get("page")),None)
  quote=(result.get("quote") or "").strip()
  page_clean=_clean(page["text"]) if page else ""
  valid=page and quote and set(_norm(quote).split()).issubset(set(_norm(page_clean).split()))
  answer=result.get("answer","")
  # Only recompute for ratio/division questions, not comparisons
  if ratio_mode and answer!=ABSTAIN:
   recomputed=_recompute(answer)
   if recomputed:answer=f"{recomputed} (verified)"
  print(f"[DEBUG] answer={answer!r} confidence={result.get('confidence')} page={result.get('page')} valid={valid}")
  if answer==ABSTAIN or (result.get("confidence") or 0)<.72 or not valid:
   return {"answer":ABSTAIN,"declined":True,"document":meta["name"],"evidence":[]}
  clean_quote=" ".join(re.sub(r"\s*\|\s*"," ",quote).split())
  return {"answer":answer,"declined":False,"document":meta["name"],"evidence":[{"page":page["page"],"quote":clean_quote}]}
 return {"answer":ABSTAIN,"declined":True,"document":meta["name"],"evidence":[{"page":p["page"],"quote":_snippet(p["text"],terms)} for _,p in hits[:3]],"note":"Local answer model unavailable; start Ollama and ensure the configured model is installed."}
