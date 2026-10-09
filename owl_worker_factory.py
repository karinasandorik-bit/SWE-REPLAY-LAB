"""OWL Worker Factory v1: template generation -> subprocess -> oracle -> gated promotion.

Isolation: disposable cwd, empty environment, CPU/memory limits on POSIX.
Not a container or hardened sandbox: only trusted built-in templates may execute.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from owl_capability_bootstrap import Capability, Task, plan

TEMPLATE = '''import json,sys
request=json.load(sys.stdin)
if request.get("operation")!="sum" or not isinstance(request.get("values"),list):
    raise SystemExit(2)
values=request["values"]
if len(values)>1000 or any(type(v) is not int or abs(v)>1000000 for v in values):
    raise SystemExit(2)
print(json.dumps({"result":sum(values)},sort_keys=True))
'''
TASK = Task("promote-worker", "worker-promote", "owl-worker-sum", "staging-only")

def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))

def build_and_verify(payload: dict, root: Path) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="owl-worker-") as tmp:
        work = Path(tmp)
        worker = work / "worker.py"
        worker.write_text(TEMPLATE, encoding="utf-8")
        digest = hashlib.sha256(worker.read_bytes()).hexdigest()
        try:
            run = subprocess.run(
                [sys.executable, "-I", "-S", str(worker)],
                input=json.dumps(payload), text=True, capture_output=True,
                cwd=work, env={"PATH": "/usr/bin:/bin"}, timeout=5,
                preexec_fn=limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return {"status": "REJECTED", "reason": "timeout", "sha256": digest}
        if run.returncode != 0:
            return {"status": "REJECTED", "reason": "worker_failed", "sha256": digest}
        try:
            observed = json.loads(run.stdout)
        except json.JSONDecodeError:
            return {"status": "REJECTED", "reason": "invalid_output", "sha256": digest}
        values = payload.get("values")
        if (payload.get("operation") != "sum" or not isinstance(values, list)
                or len(values) > 1000 or any(type(v) is not int or abs(v) > 1000000 for v in values)
                or observed != {"result": sum(values)}):
            return {"status": "REJECTED", "reason": "oracle_failed", "sha256": digest}
        staged = root / "staging" / digest
        staged.mkdir(parents=True, exist_ok=True)
        (staged / "worker.py").write_bytes(worker.read_bytes())
        manifest = {"status": "VERIFIED_STAGED", "sha256": digest, "oracle": "independent_python_sum",
                    "result": observed, "template": "sum-v1"}
        (staged / "manifest.json").write_text(json.dumps(manifest, sort_keys=True))
        return manifest

def promote(root: Path, manifest: dict, grants: list[Capability], now: int) -> dict:
    if manifest.get("status") != "VERIFIED_STAGED":
        return {"status": "DENIED", "reason": "not_verified"}
    if plan(TASK, grants, now)["decision"] != "EXECUTE_ALLOWED":
        return {"status": "DENIED", "reason": "missing_capability"}
    root = Path(root)
    digest = manifest["sha256"]
    source = root / "staging" / digest / "worker.py"
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        return {"status": "DENIED", "reason": "integrity_mismatch"}
    if source.read_text(encoding="utf-8") != TEMPLATE:
        return {"status": "DENIED", "reason": "untrusted_template"}
    active = root / "active"
    active.mkdir(parents=True, exist_ok=True)
    pending = active / (".worker." + digest + ".tmp")
    pending.write_bytes(source.read_bytes())
    os.replace(pending, active / "worker.py")
    return {"status": "PROMOTED_STAGING_ONLY", "sha256": digest}

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        report = build_and_verify({"operation": "sum", "values": [2, 3, 5]}, Path(tmp))
        print(json.dumps({"verification": report,
                          "promotion_without_grant": promote(Path(tmp), report, [], 100)}, sort_keys=True))
