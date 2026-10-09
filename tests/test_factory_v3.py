import unittest
from owl_factory_v3.runtime import manifest
from owl_factory_v3.recovery import reconcile
class FactoryV3Tests(unittest.TestCase):
 def test_registry(self):
  self.assertEqual(manifest("sum","1.0.0")["operation"],"sum")
  with self.assertRaises(ValueError):manifest("sum","9.0.0")
 def test_recovery(self):
  events=[{"event_id":1,"operation_id":"a","event_type":"STAGED","artifact_sha256":"a"*64},{"event_id":2,"operation_id":"a","event_type":"PROMOTED","artifact_sha256":"a"*64}]
  self.assertEqual(reconcile(events)["a"]["action"],"VERIFY_AND_RECONCILE")
 def test_mismatch(self):
  events=[{"event_id":1,"operation_id":"a","event_type":"STAGED","artifact_sha256":"a"*64},{"event_id":2,"operation_id":"a","event_type":"PROMOTED","artifact_sha256":"b"*64}]
  with self.assertRaises(ValueError):reconcile(events)
if __name__=="__main__":unittest.main()
