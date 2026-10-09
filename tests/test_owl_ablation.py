import unittest
from owl_ablation import cases, decision, evaluate

class PairedReplay(unittest.TestCase):
    def test_identical_cases(self):
        self.assertEqual(evaluate(False)["fixture_sha256"], evaluate(True)["fixture_sha256"])
    def test_full_gate(self):
        self.assertEqual(evaluate(True)["correct"], 7)
    def test_ablation_detects_failures(self):
        self.assertEqual(evaluate(False)["correct"], 1)
    def test_expected_outputs(self):
        for req, expected in cases():
            self.assertEqual(decision(req, True), expected)
if __name__ == "__main__":
    unittest.main()
