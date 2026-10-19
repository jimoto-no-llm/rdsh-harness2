"""POSTHOC replay: retry ordinary outputs using observable failures only.

No model, grader, subprocess, network or source modification occurs here. Hidden
grades are accessed only after the selected attempt has been fixed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time


def known_ms(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def add_known(values):
    values = [known_ms(value) for value in values]
    return sum(values) if all(value is not None for value in values) else None


def arm_cost(arm):
    # An unavailable harness/attempt was not invoked and consumed no session time.
    return 0 if arm.get("state") == "unavailable" else known_ms(arm.get("nativeTransportWallMs"))


def observable(arm):
    score = arm.get("score") or {}
    actions = score.get("nativeActions") or {}
    checks = {"nativeCompleted": score.get("nativeCompleted") is True,
        "sourceChanged": score.get("sourceChanged") is True,
        "allowedChanges": score.get("allowedChanges") is True,
        "visibleTestsUnchanged": score.get("visibleTestsUnchanged") is True,
        "editToolCalled": type(actions.get("edit")) is int and actions["edit"] >= 1,
        "testToolCalled": type(actions.get("test")) is int and actions["test"] >= 1,
        "publicTestsPass": (score.get("visible") or {}).get("ok") is True}
    return {"passed": all(checks.values()), "checks": checks,
            "failureReasons": [name for name, ok in checks.items() if not ok]}


def assess_chosen(arm, expected):
    """Called only after observable selection. These fields never control retry."""
    if arm is None:
        return {"passed": False, "outputAvailable": False, "hiddenPassed": 0,
                "hiddenTests": 0, "expectedHiddenTests": expected, "hiddenComplete": False}
    score = arm.get("score") or {}
    hidden = score.get("hidden") or {}
    return {"passed": score.get("passed") is True,
            "outputAvailable": score.get("nativeCompleted") is True and score.get("sourceChanged") is True,
            "hiddenPassed": hidden.get("passed", 0), "hiddenTests": hidden.get("tests", 0),
            "expectedHiddenTests": expected, "hiddenComplete": score.get("hiddenTestsComplete") is True,
            "nativeCompleted": score.get("nativeCompleted") is True,
            "externalGradingError": bool(score.get("externalGradingError")),
            "artifactSha256": score.get("artifactSha256")}


def summarize(entries, training_ms=0):
    solve_ms = add_known(entry["hostSessionMs"] for entry in entries)
    total_ms = add_known([solve_ms, training_ms])
    count = len(entries)
    return {"tasks": count, "passed": sum(entry["quality"]["passed"] for entry in entries),
        "outputsAvailable": sum(entry["quality"]["outputAvailable"] for entry in entries),
        "hiddenPassed": sum(entry["quality"]["hiddenPassed"] for entry in entries),
        "hiddenTestsObserved": sum(entry["quality"]["hiddenTests"] for entry in entries),
        "hiddenTestsPlanned": sum(entry["quality"]["expectedHiddenTests"] for entry in entries),
        "successRate": sum(entry["quality"]["passed"] for entry in entries) / count if count else None,
        "solverHostSessionMs": solve_ms, "trainingHostSessionMs": training_ms,
        "totalHostSessionMs": total_ms, "timingComplete": total_ms is not None,
        "attemptsConsumed": sum(entry.get("attemptsConsumed", 1) for entry in entries)}


def replay(report, *, exclude_tasks=()):
    indexed = {}
    for row in report["rows"]:
        key = (row["round"], row["taskId"])
        if key in indexed:
            raise ValueError("duplicate task/round cell")
        indexed[key] = row
    all_tasks = sorted({row["taskId"] for row in report["rows"]})
    if set(exclude_tasks) - set(all_tasks):
        raise ValueError("excluded task absent from report")
    tasks = [task for task in all_tasks if task not in exclude_tasks]
    if not tasks or any((round_id, task) not in indexed for task in tasks for round_id in (1, 2, 3)):
        raise ValueError("replay requires nonempty tasks and all three observed round cells")
    retry, first, improved = [], [], []
    for task in tasks:
        expected = indexed[1, task]["expectedHiddenTests"]
        attempts, selected, selected_round = [], None, None
        for round_id in (1, 2, 3):
            arm = indexed[round_id, task]["baseline"]
            public_decision = observable(arm)
            attempts.append({"round": round_id, "state": arm["state"],
                "hostSessionMs": arm_cost(arm), "observableDecision": public_decision})
            if public_decision["passed"]:
                selected, selected_round = arm, round_id
                break
        retry.append({"taskId": task, "selectedRound": selected_round,
            "attemptsConsumed": len(attempts), "attempts": attempts,
            "hostSessionMs": add_known(attempt["hostSessionMs"] for attempt in attempts),
            "quality": assess_chosen(selected, expected)})
        for arm_name, destination in (("baseline", first), ("improved", improved)):
            arm = indexed[1, task][arm_name]
            destination.append({"taskId": task, "selectedRound": 1, "state": arm["state"],
                "hostSessionMs": arm_cost(arm), "observableDecision": observable(arm),
                "quality": assess_chosen(arm, expected)})
    first_training = (report.get("training") or [{}])[0]
    training_ms = known_ms(first_training.get("transportWallMs"))
    summaries = {"ordinaryRound1": summarize(first), "ordinaryObservableRetryUpTo3": summarize(retry),
                 "improvedRound1WithFullTraining": summarize(improved, training_ms)}
    comparisons = {}
    for name in ("ordinaryRound1", "ordinaryObservableRetryUpTo3"):
        baseline = summaries[name]
        enhanced = summaries["improvedRound1WithFullTraining"]
        delta_passed = enhanced["passed"] - baseline["passed"]
        delta_ms = (enhanced["totalHostSessionMs"] - baseline["totalHostSessionMs"]
                    if enhanced["totalHostSessionMs"] is not None and baseline["totalHostSessionMs"] is not None else None)
        comparisons[name] = {"netAdditionalSuccessesWithImproved": delta_passed,
            "additionalHostSessionMsWithImproved": delta_ms,
            "additionalSecondsPerNetSuccess": delta_ms / 1000 / delta_passed if delta_ms is not None and delta_passed > 0 else None,
            "repairTimeScenarios": [{"repairSeconds": repair,
                "netSecondsSavedWithImproved": delta_passed * repair - delta_ms / 1000 if delta_ms is not None else None}
                for repair in (60, 300, 900)]}
    return {"version": 1, "analysisKind": "POSTHOC observational replay, not a new online experiment",
        "inputSuiteSha256": report.get("suiteSha256"), "excludedTasks": sorted(exclude_tasks),
        "selectionRule": "Try ordinary baseline round 1, then 2, then 3; stop at first native-completed source change with allowed edits, unchanged public tests, edit/test tool calls, and publicTests.ok. Never inspect hidden grades to decide retries.",
        "roundOrder": [1, 2, 3], "improvedSelection": "Fixed round 1, including all of its measured training host session time; no best-of-three selection.",
        "summaries": summaries, "comparisons": comparisons,
        "trajectories": {"ordinaryRound1": first, "ordinaryObservableRetryUpTo3": retry,
                         "improvedRound1WithFullTraining": improved},
        "limitations": ["POSTHOC replay of existing samples, susceptible to temporal differences and shared-provider conditions.",
            "These trajectories are neither new independent samples nor part of the predeclared primary inference.",
            "Retry candidates were originally generated in separate independent harness rounds; a fresh online retry workflow was not executed.",
            "Public success can hide incorrect output: the first public success is retained even if its hidden grade fails.",
            "Host session milliseconds include startup and failures, sum session durations, and exclude grader time; they are not parallel experiment elapsed time.",
            "Only consumed ordinary attempts and fixed round-1 improved calls/training are charged in the counterfactual replay; the actual original study also paid for unused samples and other training rounds.",
            "Missing measured host session time makes corresponding cost comparisons unavailable; no token prices or money are inferred."]}
