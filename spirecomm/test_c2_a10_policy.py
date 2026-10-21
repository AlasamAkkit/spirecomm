"""Pure regression coverage for fixed Ascension-10 phase policy.

Importing the policy module is not equivalent to launching the game:
no agent instance or CommunicationMod loop is constructed in these tests.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import test_connection_c2_a10 as a10


class A10PolicyTests(unittest.TestCase):
    def _rebuild(self, prior):
        # Stub only the inherited event-to-progress calculation. No experiment
        # files are opened, seeds issued, or live progress sidecars written.
        obj = object.__new__(a10.ContinualC2A10Agent)
        with patch.object(
            a10.stable.ContinualC2StableAgent,
            "_rebuild_progress_from_events",
            return_value=prior,
        ):
            return obj._rebuild_progress_from_events()

    def test_cutover_after_run38_and_no_fabricated_clear(self):
        progress = self._rebuild({
            "processed_run_numbers": list(range(16, 39)),
            "current_ascension": 1,
            "highest_cleared_ascension": 0,
            "clearances": [{"run_number": 37, "ascension": 0}],
        })
        self.assertEqual(progress["current_ascension"], 10)
        self.assertEqual(progress["highest_cleared_ascension"], 0)
        self.assertEqual(progress["clearances"], [{"run_number": 37, "ascension": 0}])
        self.assertEqual(progress["difficulty_override_start_run"], 39)

    def test_no_early_cutover(self):
        progress = self._rebuild({
            "processed_run_numbers": list(range(16, 38)),
            "current_ascension": 1,
            "highest_cleared_ascension": 0,
            "clearances": [{"run_number": 37, "ascension": 0}],
        })
        self.assertEqual(progress["current_ascension"], 1)
        self.assertNotIn("difficulty_override_start_run", progress)

    def test_a10_remains_fixed_after_a10_win(self):
        progress = self._rebuild({
            "processed_run_numbers": list(range(16, 40)),
            "current_ascension": 11,
            "highest_cleared_ascension": 10,
            "clearances": [{"run_number": 37, "ascension": 0},
                           {"run_number": 39, "ascension": 10}],
        })
        self.assertEqual(progress["current_ascension"], 10)
        self.assertEqual(progress["highest_cleared_ascension"], 10)

    def test_active_controller_class_is_a10_policy_wrapper(self):
        self.assertIs(a10.base.STSAgent, a10.ContinualC2A10Agent)
        self.assertTrue(issubclass(
            a10.ContinualC2A10Agent,
            a10.stable.ContinualC2StableAgent,
        ))


if __name__ == "__main__":
    unittest.main()
