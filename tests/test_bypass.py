import unittest
from services.bypass import get_bypass_strategies


class TestBypassManager(unittest.TestCase):
    def test_registered_strategies_count(self):
        strategies = get_bypass_strategies()
        self.assertEqual(len(strategies), 4)

    def test_strategy_attributes_and_ids(self):
        strategies = get_bypass_strategies()
        strategy_ids = [s.id for s in strategies]

        self.assertIn("native_web", strategy_ids)
        self.assertIn("ssstik", strategy_ids)
        self.assertIn("tikwm", strategy_ids)
        self.assertIn("gallery_dl", strategy_ids)

        for s in strategies:
            self.assertTrue(s.is_active, f"Strategy {s.id} should be active")
            self.assertTrue(len(s.name) > 0, f"Strategy {s.id} missing name")
            self.assertTrue(len(s.description) > 0, f"Strategy {s.id} missing description")
            self.assertTrue(len(s.target) > 0, f"Strategy {s.id} missing target")


if __name__ == "__main__":
    unittest.main()
