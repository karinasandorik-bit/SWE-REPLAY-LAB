"""Versioned trusted worker catalog, replay, audit and staging rollback."""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
CATALOG={
"sum@1":"import json,sys\nx=json.load(sys.stdin)\nassert x['op']=='sum' and isinstance(x['values'],list) and len(x['values'])<=100 and all(type(v)==int and abs(v)<=1000000 for v in x['values'])\nprint(json.dumps({'value':sum(x['values'])}))\n",
"count@1":"import json,sys\nx=json.load(sys.stdin)\nassert x['op']=='count' and isinstance(x['values'],list) and len(x['values'])<=100 and all(type(v)==int for v in x['values'])\nprint(json.dumps({'value':len(x['values'])}))\n"}
def oracle(kind,p):
 v=p["values"]
 if not isinstance(v,list) or len(v)>100 or any(type(x)!=int for x in v):raise ValueError("bad input")
 if kind=="sum@1" and p["op"]=="sum" and all(abs(x)<=1000000 for x in v):return {"value":sum(v)}
 if kind=="count@1" and p["op"]=="count":return {"value":len(v)}
 raise ValueError("bad operation")
def run(src,p):
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/"worker.py";path.write_text(src)
  r=subprocess.run([sys.executable,"-I","-S",str(path)],input=json.dumps(p),text=True,capture_output=True,cwd=td,env={"PATH":"/usr/bin:/bin"},timeout=5)
  if r.returncode:raise RuntimeError("worker failed")
  return json.loads(r.stdout)
def verify(kind,p):
 src=CATALOG[kind];expected=oracle(kind,p)
 if run(src,p)!=expected or run(src,p)!=expected:raise AssertionError("replay failed")
 return hashlib.sha256(src.encode()).hexdigest()
def audit(root,event):
 path=root/"audit.jsonl";prev="0"*64
 if path.exists() and path.stat().st_size:prev=json.loads(path.read_text().splitlines()[-1])["hash"]
 record={"prev":prev,"event":event};record["hash"]=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
 with path.open("a") as f:f.write(json.dumps(record,sort_keys=True)+"\n");f.flush();os.fsync(f.fileno())
def promote(root,kind,p,authorized=False,probe=None):
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 if not authorized:audit(root,{"action":"DENY","kind":kind});return "DENIED"
 digest=verify(kind,p);active=root/"active.json";old=active.read_bytes() if active.exists() else None
 def swap(data):
  with tempfile.NamedTemporaryFile(dir=root,delete=False) as f:f.write(data);tmp=f.name
  os.replace(tmp,active)
 swap(json.dumps({"kind":kind,"sha256":digest,"source":CATALOG[kind]}).encode())
 audit(root,{"action":"PROMOTE","kind":kind,"sha256":digest})
 try:
  if probe is not None and not probe():raise AssertionError("probe")
  if run(CATALOG[kind],p)!=oracle(kind,p):raise AssertionError("outcome")
 except Exception:
  if old is None:active.unlink(missing_ok=True)
  else:swap(old)
  audit(root,{"action":"ROLLBACK","kind":kind});return "ROLLED_BACK"
 audit(root,{"action":"CONFIRM","kind":kind});return "PROMOTED"
def verify_audit(root):
 previous="0"*64
 for line in (Path(root)/"audit.jsonl").read_text().splitlines():
  r=json.loads(line);digest=r.pop("hash")
  if r["prev"]!=previous or hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()!=digest:return False
  previous=digest
 return True
