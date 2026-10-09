"""Independent seeded holdout: evaluate interaction effects and boundary cases."""
import hashlib
import json
import random
import unittest
from owl_ablation import Request, decision

class HiddenInteractions(unittest.TestCase):
    def test_seeded_holdout(self):
        rng = random.Random(20261009)
        seen = []
        for _ in range(512):
            action = rng.choice(["OWL_SOLANA_CANARY_V1", "ARBITRARY_SIGN", "BROADCAST", ""])
            scope = rng.choice(["canary-only", "unbounded", ""])
            now = rng.choice([0, 99, 100, 199, 200, 201])
            expires = rng.choice([0, 100, 200])
            revoked = rng.choice([False, True])
            s0 = rng.choice(["a"*64, "", "g"*64, "A"*64])
            req = Request(action, scope, now, expires, revoked, s0)
            expected = (action == "OWL_SOLANA_CANARY_V1" and scope == "canary-only"
                        and now < expires and not revoked and s0 == "a"*64)
            self.assertEqual(decision(req, True), expected)
            seen.append([action, scope, now, expires, revoked, s0, expected])
        digest = hashlib.sha256(json.dumps(seen, separators=(",", ":")).encode()).hexdigest()
        print("HOLDOUT_SEED=20261009 N=512 SHA256=" + digest)

    def test_boundary_time(self):
        for now, expiry, expected in [(99, 100, True), (100, 100, False), (101, 100, False)]:
            req = Request("OWL_SOLANA_CANARY_V1", "canary-only", now, expiry, False, "a"*64)
            self.assertEqual(decision(req, True), expected)

if __name__ == "__main__":
    unittest.main()
