"""Trusted manifest registry + Docker-isolated worker runtime; fail closed."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
REGISTRY=Path(__file__).with_name("manifests.json")
SCRIPT='''import json,sys
p=json.load(sys.stdin)
v=p["values"]
assert isinstance(v,list) and len(v)<=100 and all(type(x)==int and abs(x)<=1000000 for x in v)
op=p["op"]
assert op in ("sum","count")
print(json.dumps({"value":sum(v) if op=="sum" else len(v)}))
'''
def manifest(worker_id,version):
 catalog=json.loads(REGISTRY.read_text())
 matches=[w for w in catalog["workers"] if w["id"]==worker_id and w["version"]==version]
 if len(matches)!=1:raise ValueError("unknown worker/version")
 w=matches[0]
 if w["image"]!="python:3.11-alpine" or w["operation"] not in ("sum","count"):raise ValueError("untrusted manifest")
 return w
def run(worker_id,version,values):
 w=manifest(worker_id,version)
 if not isinstance(values,list) or len(values)>w["max_items"] or any(type(x)!=int or abs(x)>1000000 for x in values):raise ValueError("invalid values")
 payload={"op":w["operation"],"values":values}
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/"worker.py";path.write_text(SCRIPT)
  cmd=["docker","run","--rm","--network=none","--read-only","--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=32","--memory=128m","--cpus=0.5","--user=65534:65534","--mount",f"type=bind,src={path},dst=/worker.py,readonly",w["image"],"python","-I","-S","/worker.py"]
  result=subprocess.run(cmd,input=json.dumps(payload),text=True,capture_output=True,timeout=20)
  if result.returncode:raise RuntimeError("sandbox failed")
  actual=json.loads(result.stdout)
  expected={"value":sum(values) if w["operation"]=="sum" else len(values)}
  if actual!=expected:raise AssertionError("oracle mismatch")
  return {"worker":worker_id,"version":version,"result":actual,"artifact_sha256":hashlib.sha256(SCRIPT.encode()).hexdigest()}
