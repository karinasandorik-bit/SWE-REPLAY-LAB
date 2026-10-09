import unittest
from owl_capability_bootstrap import Capability, Task, plan

class BootstrapPolicyTests(unittest.TestCase):
    def setUp(self):
        self.task = Task("postgres-recovery", "database-test-write", "owl_ablation_004", "isolated-schema")

    def test_no_grant_denied(self):
        self.assertEqual(plan(self.task, [], 100)["decision"], "NEEDS_AUTHORIZATION")

    def test_valid_grant_allows(self):
        g = Capability("database-test-write", "owl_ablation_004", "isolated-schema", 200, True)
        self.assertEqual(plan(self.task, [g], 100)["decision"], "EXECUTE_ALLOWED")

    def test_expired_grant_denied(self):
        g = Capability("database-test-write", "owl_ablation_004", "isolated-schema", 100, True)
        self.assertEqual(plan(self.task, [g], 100)["decision"], "NEEDS_AUTHORIZATION")

    def test_unapproved_grant_denied(self):
        g = Capability("database-test-write", "owl_ablation_004", "isolated-schema", 200, False)
        self.assertEqual(plan(self.task, [g], 100)["decision"], "NEEDS_AUTHORIZATION")

    def test_broad_scope_does_not_substitute(self):
        g = Capability("database-test-write", "owl_ablation_004", "all-schemas", 200, True)
        self.assertEqual(plan(self.task, [g], 100)["decision"], "NEEDS_AUTHORIZATION")

    def test_wrong_resource_denied(self):
        g = Capability("database-test-write", "production", "isolated-schema", 200, True)
        self.assertEqual(plan(self.task, [g], 100)["decision"], "NEEDS_AUTHORIZATION")

if __name__ == "__main__":
    unittest.main()
