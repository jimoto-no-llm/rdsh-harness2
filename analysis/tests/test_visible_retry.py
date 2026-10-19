import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("replay_visible_retry", Path(__file__).resolve().parents[1] / "visible_retry.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def arm(public=True, hidden=True, *, native=True, wall=100):
    return {"state": "completed", "nativeTransportWallMs": wall,
        "score": {"passed": native and public and hidden, "nativeCompleted": native,
            "sourceChanged": True, "allowedChanges": True, "visibleTestsUnchanged": True,
            "nativeActions": {"edit": 1, "test": 1, "read": 1}, "visible": {"ok": public},
            "hidden": {"passed": 8 if hidden else 7, "tests": 8},
            "hiddenTestsComplete": hidden, "artifactSha256": "source-digest"}}


def report():
    return {"suiteSha256": "frozen", "training": [{"transportWallMs": 1000}],
        "rows": [{"round": r, "taskId": task, "expectedHiddenTests": 8,
                  "baseline": arm(), "improved": arm(wall=200)}
                 for r in (1, 2, 3) for task in ("a", "layered-config-merge")]}


class ReplayTests(unittest.TestCase):
    def test_first_public_success_with_hidden_failure_is_retained_without_oracle(self):
        value = report()
        value["rows"][0]["baseline"] = arm(hidden=False)
        result = MODULE.replay(value)
        first = result["trajectories"]["ordinaryObservableRetryUpTo3"][0]
        self.assertEqual(first["selectedRound"], 1)
        self.assertEqual(first["attemptsConsumed"], 1)
        self.assertFalse(first["quality"]["passed"])
        self.assertEqual(first["hostSessionMs"], 100)
        self.assertEqual(result["summaries"]["ordinaryObservableRetryUpTo3"]["passed"], 1)
        # Hidden failure in a later attempt cannot alter observable selection.
        mutated = copy.deepcopy(value)
        mutated["rows"][2]["baseline"]["score"]["hidden"] = {"passed": 0, "tests": 8}
        self.assertEqual(MODULE.replay(mutated)["trajectories"]["ordinaryObservableRetryUpTo3"][0], first)

    def test_observable_failure_triggers_next_attempt_and_costs_sum_consumed_only(self):
        value = report()
        value["rows"][0]["baseline"] = arm(public=False, wall=300)
        value["rows"][2]["baseline"] = arm(wall=400)
        result = MODULE.replay(value)
        first = result["trajectories"]["ordinaryObservableRetryUpTo3"][0]
        self.assertEqual(first["selectedRound"], 2)
        self.assertEqual(first["attemptsConsumed"], 2)
        self.assertEqual(first["hostSessionMs"], 700)
        self.assertEqual(first["attempts"][0]["observableDecision"]["failureReasons"], ["publicTestsPass"])
        self.assertEqual(result["summaries"]["ordinaryObservableRetryUpTo3"]["totalHostSessionMs"], 800)
        self.assertEqual(result["summaries"]["improvedRound1WithFullTraining"]["totalHostSessionMs"], 1400)

    def test_no_observable_success_means_no_selected_output(self):
        value = report()
        for row in value["rows"]:
            if row["taskId"] == "a":
                row["baseline"] = {"state": "unavailable", "score": None}
        result = MODULE.replay(value)
        first = result["trajectories"]["ordinaryObservableRetryUpTo3"][0]
        self.assertIsNone(first["selectedRound"])
        self.assertFalse(first["quality"]["passed"])
        self.assertFalse(first["quality"]["outputAvailable"])
        self.assertEqual(first["attemptsConsumed"], 3)
        self.assertEqual(first["hostSessionMs"], 0)

    def test_hidden_grading_error_does_not_trigger_retry_if_public_passed(self):
        value = report()
        score = value["rows"][0]["baseline"]["score"]
        score["externalGradingError"] = "hidden-grader-error"
        score["hiddenTestsComplete"] = False
        score["passed"] = False
        result = MODULE.replay(value)
        first = result["trajectories"]["ordinaryObservableRetryUpTo3"][0]
        self.assertEqual(first["selectedRound"], 1)
        self.assertEqual(first["attemptsConsumed"], 1)
        self.assertTrue(first["quality"]["externalGradingError"])
        self.assertFalse(first["quality"]["passed"])

    def test_fixed_round_one_improved_is_not_best_of_three_and_sensitivity_filters(self):
        value = report()
        value["rows"][0]["improved"] = arm(hidden=False)
        result = MODULE.replay(value, exclude_tasks=["layered-config-merge"])
        self.assertEqual(result["summaries"]["improvedRound1WithFullTraining"]["tasks"], 1)
        self.assertEqual(result["summaries"]["improvedRound1WithFullTraining"]["passed"], 0)
        self.assertEqual(result["summaries"]["improvedRound1WithFullTraining"]["totalHostSessionMs"], 1100)
        self.assertEqual(result["excludedTasks"], ["layered-config-merge"])
        with self.assertRaises(ValueError):
            MODULE.replay(value, exclude_tasks=["typo"])

    def test_missing_host_time_nulls_comparison_instead_of_filling_zero(self):
        value = report()
        value["rows"][0]["baseline"]["nativeTransportWallMs"] = None
        result = MODULE.replay(value)
        self.assertIsNone(result["summaries"]["ordinaryObservableRetryUpTo3"]["totalHostSessionMs"])
        self.assertIsNone(result["comparisons"]["ordinaryObservableRetryUpTo3"]["additionalHostSessionMsWithImproved"])
        value["training"][0]["transportWallMs"] = None
        self.assertIsNone(MODULE.replay(value)["summaries"]["improvedRound1WithFullTraining"]["totalHostSessionMs"])


if __name__ == "__main__":
    unittest.main()
