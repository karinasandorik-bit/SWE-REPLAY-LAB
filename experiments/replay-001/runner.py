#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from openai import OpenAI

ROOT=Path("task")
TRACE=Path("artifacts/trajectory.jsonl")
def sha(b): return hashlib.sha256(b).hexdigest()
def ws_hash():
    rows=[]
    for p in sorted(ROOT.rglob("*")):
        if p.is_file():
            rows.append(f"{p.relative_to(ROOT)}\0{sha(p.read_bytes())}")
    return sha("\n".join(rows).encode())
def log(x):
    TRACE.parent.mkdir(exist_ok=True)
    with TRACE.open("a") as f:f.write(json.dumps(x,sort_keys=True)+"\n")

issue="""Remove the unnecessary `py.path.local` restriction from pytest's `tmpdir` fixture implementation so that an alternative path object supplied by the temporary-path factory remains usable. Preserve existing behavior and tests; make the smallest justified change."""
client=OpenAI()
before=ws_hash()
log({"event":"MODEL_CALL","step":1,"workspace_before":before,"observation_sha256":sha(issue.encode())})
r=client.responses.create(model=os.environ.get("MODEL","gpt-5.6"),input=[
 {"role":"system","content":"You are a coding agent. Return ONLY a unified diff against the supplied repository. Make the smallest justified fix. Do not use network."},
 {"role":"user","content":issue+"\nRepository is pytest at the frozen base revision. Relevant files must be inferred from the task."}
])
text=r.output_text
log({"event":"MODEL_RESPONSE","step":1,"raw_sha256":sha(text.encode()),"raw":text})
Path("artifacts/model-response.txt").write_text(text)
print("MODEL_CALL_1_COMPLETED")
