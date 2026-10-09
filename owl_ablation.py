"""OWL paired replay: deterministic authority gate versus ablated baseline.
Run: python3 -m unittest discover -s tests -v
No credentials, network, signing or transaction broadcast.
"""
from dataclasses import dataclass
import hashlib
import json

@dataclass(frozen=True)
class Request:
    action: str
    scope: str
    now: int
    expires: int
    revoked: bool
    s0: str

def decision(r: Request, gate: bool) -> bool:
    if not gate:
        return True
    return (r.action == "OWL_SOLANA_CANARY_V1"
            and r.scope == "canary-only"
            and r.now < r.expires
            and not r.revoked
            and len(r.s0) == 64
            and all(c in "0123456789abcdef" for c in r.s0))

def fixture_hash(cases):
    payload = json.dumps([c.__dict__ for c, _ in cases], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()

def cases():
    good = Request("OWL_SOLANA_CANARY_V1", "canary-only", 100, 200, False, "a" * 64)
    return [
        (good, True),
        (Request("ARBITRARY_SIGN", good.scope, 100, 200, False, good.s0), False),
        (Request("BROADCAST", good.scope, 100, 200, False, good.s0), False),
        (Request(good.action, "unbounded", 100, 200, False, good.s0), False),
        (Request(good.action, good.scope, 200, 200, False, good.s0), False),
        (Request(good.action, good.scope, 100, 200, True, good.s0), False),
        (Request(good.action, good.scope, 100, 200, False, ""), False),
    ]

def evaluate(gate):
    items = cases()
    return {"correct": sum(decision(r, gate) == expected for r, expected in items),
            "total": len(items), "fixture_sha256": fixture_hash(items)}
