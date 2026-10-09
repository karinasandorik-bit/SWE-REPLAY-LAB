import hashlib
import tempfile
import unittest
from pathlib import Path
from owl_capability_bootstrap import Capability
from owl_worker_factory import build_and_verify, promote

class FactoryTests(unittest.TestCase):
    def test_full_cycle_staging(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            report=build_and_verify({"operation":"sum","values":[2,3,5]},root)
            self.assertEqual(report["status"],"VERIFIED_STAGED")
            self.assertEqual(report["result"],{"result":10})
            self.assertEqual(promote(root,report,[],100)["status"],"DENIED")
            grant=Capability("worker-promote","owl-worker-sum","staging-only",200,True)
            self.assertEqual(promote(root,report,[grant],100)["status"],"PROMOTED_STAGING_ONLY")
            self.assertEqual(hashlib.sha256((root/"active"/"worker.py").read_bytes()).hexdigest(),report["sha256"])

    def test_invalid_payload_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            for values in (["1",2], [1000001], list(range(1001))):
                report=build_and_verify({"operation":"sum","values":values},Path(td))
                self.assertEqual(report["status"],"REJECTED")

    def test_tamper_prevents_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            report=build_and_verify({"operation":"sum","values":[4]},root)
            (root/"staging"/report["sha256"]/"worker.py").write_text("print('tampered')")
            grant=Capability("worker-promote","owl-worker-sum","staging-only",200,True)
            self.assertEqual(promote(root,report,[grant],100)["reason"],"integrity_mismatch")

    def test_expired_grant_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            report=build_and_verify({"operation":"sum","values":[1]},root)
            expired=Capability("worker-promote","owl-worker-sum","staging-only",100,True)
            self.assertEqual(promote(root,report,[expired],100)["status"],"DENIED")

if __name__=="__main__":
    unittest.main()
