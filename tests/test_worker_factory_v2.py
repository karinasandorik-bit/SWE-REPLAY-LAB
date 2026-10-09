import tempfile,unittest
from pathlib import Path
from owl_worker_factory_v2 import verify,promote,verify_audit
class FactoryV2Tests(unittest.TestCase):
 def test_replay(self):
  self.assertEqual(len(verify("sum@1",{"op":"sum","values":[2,3]})),64)
  self.assertEqual(len(verify("count@1",{"op":"count","values":[2,3]})),64)
 def test_deny(self):
  with tempfile.TemporaryDirectory() as td:
   self.assertEqual(promote(td,"sum@1",{"op":"sum","values":[2]}),"DENIED")
   self.assertTrue(verify_audit(td))
 def test_rollback(self):
  with tempfile.TemporaryDirectory() as td:
   self.assertEqual(promote(td,"sum@1",{"op":"sum","values":[2]},True),"PROMOTED")
   before=(Path(td)/"active.json").read_bytes()
   self.assertEqual(promote(td,"count@1",{"op":"count","values":[2]},True,probe=lambda:False),"ROLLED_BACK")
   self.assertEqual((Path(td)/"active.json").read_bytes(),before)
   self.assertTrue(verify_audit(td))
if __name__=="__main__":unittest.main()
