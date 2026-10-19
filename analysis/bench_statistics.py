"""Pure offline statistics, matching the frozen repeated evaluator. No model calls."""
import math
import random
import statistics

def binomial_p(wins, losses):
    n = wins + losses
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2 ** n) if n else 1.0

def passed(arm):
    return bool(arm.get("state") == "completed" and (arm.get("score") or {}).get("passed"))

def complete_sum(values):
    values = list(values)
    return sum(values) if all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in values) else None

def difference(left, right):
    return left - right if left is not None and right is not None else None

def summarize(rows, training, *, seed, total_wall_ms):
    n = len(rows)
    wins = sum(passed(row["improved"]) and not passed(row["baseline"]) for row in rows)
    losses = sum(passed(row["baseline"]) and not passed(row["improved"]) for row in rows)
    completed_pairs = [row for row in rows if all(row[a]["state"] == "completed" for a in ("baseline", "improved"))]
    semantic_pairs = [row for row in completed_pairs if row.get("expectedHiddenTests", 0) > 0
        and all(row[a]["score"].get("nativeCompleted")
                and not row[a]["score"].get("externalGradingError")
                and row[a]["score"].get("hidden", {}).get("tests") == row["expectedHiddenTests"]
                for a in ("baseline", "improved"))]
    observed_wins = sum(passed(r["improved"]) and not passed(r["baseline"]) for r in completed_pairs)
    observed_losses = sum(passed(r["baseline"]) and not passed(r["improved"]) for r in completed_pairs)
    arms = {}
    for arm in ("baseline", "improved"):
        entries = [row[arm] for row in rows]
        scores = [entry["score"] for entry in entries if entry.get("score")]
        model_ms = [score["modelWallMs"] for score in scores if isinstance(score.get("modelWallMs"), (int, float))]
        native_values = [0 if entry["state"] == "unavailable" else
            ((entry.get("score") or {}).get("modelWallMs") if entry["state"] == "completed"
             and ((entry.get("score") or {}).get("nativeCompleted")
                  or (entry.get("score") or {}).get("modelWallMs", 0) > 0) else None) for entry in entries]
        arms[arm] = {"passed": sum(passed(entry) for entry in entries), "planned": n,
            "completed": len(scores), "successRate": sum(passed(entry) for entry in entries) / n if n else None,
            "nativeFailures": sum(not score.get("nativeCompleted", False) for score in scores),
            "externalGradingFailures": sum(bool(score.get("externalGradingError")) for score in scores),
            "unavailableOrInterrupted": sum(entry.get("score") is None for entry in entries),
            "nativeWallMs": complete_sum(native_values), "observedNativeWallMsLowerBound": sum(model_ms),
            "nativeTimingComplete": all(value is not None for value in native_values),
            "nativeTransportWallMs": complete_sum(0 if e["state"] == "unavailable" else e.get("nativeTransportWallMs") for e in entries),
            "meanNativeWallMs": statistics.mean(model_ms) if model_ms else None,
            "gradingWallMs": sum(score.get("gradingWallMs", 0) for score in scores),
            "wallMs": sum(entry.get("wallMs") or 0 for entry in entries),
            "hiddenPassed": sum(score.get("hidden", {}).get("passed", 0) for score in scores),
            "hiddenTests": sum(score.get("hidden", {}).get("tests", 0) for score in scores)}
        expected = sum(row.get("expectedHiddenTests") or 0 for row in rows)
        arms[arm]["plannedHiddenTests"] = expected
        arms[arm]["hiddenFractionOfPlanned"] = arms[arm]["hiddenPassed"] / expected if expected else None
    groups = {}
    for key, values in (("byRound", sorted({row["round"] for row in rows})),
                        ("byTask", sorted({row["taskId"] for row in rows}))):
        field = "round" if key == "byRound" else "taskId"
        groups[key] = [{field: value, "pairs": sum(row[field] == value for row in rows),
            "baselinePassed": sum(passed(row["baseline"]) for row in rows if row[field] == value),
            "improvedPassed": sum(passed(row["improved"]) for row in rows if row[field] == value)} for value in values]
    oracle = {arm: sum(any(passed(row[arm]) for row in rows if row["taskId"] == task)
                       for task in sorted({row["taskId"] for row in rows})) for arm in ("baseline", "improved")}
    task_deltas = [(item["improvedPassed"] - item["baselinePassed"]) / item["pairs"] for item in groups["byTask"]]
    rng = random.Random(seed)
    boot = sorted(statistics.mean(rng.choices(task_deltas, k=len(task_deltas))) for _ in range(10000)) if task_deltas else []
    full_training = complete_sum(t.get("wallMs") for t in training)
    native_training = complete_sum(t.get("nativeWallMs") for t in training)
    incremental_training_native = complete_sum(t.get("additionalNativeOverTrainingBaselineMs") for t in training)
    training_transport = complete_sum(t.get("transportWallMs") for t in training)
    incremental_training_transport = complete_sum(t.get("additionalOverTrainingBaselineMs") for t in training)
    delta_native = difference(arms["improved"]["nativeWallMs"], arms["baseline"]["nativeWallMs"])
    delta_transport = difference(arms["improved"]["nativeTransportWallMs"], arms["baseline"]["nativeTransportWallMs"])
    full_additional = native_training + delta_native if native_training is not None and delta_native is not None else None
    additional = incremental_training_native + delta_native if incremental_training_native is not None and delta_native is not None else None
    full_additional_transport = training_transport + delta_transport if training_transport is not None and delta_transport is not None else None
    additional_transport = incremental_training_transport + delta_transport if incremental_training_transport is not None and delta_transport is not None else None
    net = wins - losses
    available_training = [t for t in training if t["state"] == "available"]
    mean_training_native = native_training / len(training) if training and native_training is not None else None
    mean_incremental_native = incremental_training_native / len(training) if training and incremental_training_native is not None else None
    mean_delta = delta_native / n if n and delta_native is not None else None
    mean_training_transport = training_transport / len(training) if training and training_transport is not None else None
    mean_incremental_transport = incremental_training_transport / len(training) if training and incremental_training_transport is not None else None
    mean_delta_transport = delta_transport / n if n and delta_transport is not None else None
    def amortized(count, full=False, transport=False):
        overhead = ((mean_training_transport if full else mean_incremental_transport) if transport
                    else (mean_training_native if full else mean_incremental_native))
        delta = mean_delta_transport if transport else mean_delta
        return (overhead / count + delta) / 1000 if overhead is not None and delta is not None else None
    def ratio(value):
        return value / 1000 / net if value is not None and net > 0 else None
    return {"pairs": n, "completedPairs": len(completed_pairs), **arms, **groups,
        "improvementPairs": wins, "regressionPairs": losses, "netAdditionalSuccesses": net,
        "pairedCompletedOnly": {"wins": observed_wins, "losses": observed_losses,
            "exactDiscordantBinomialTwoSidedP": binomial_p(observed_wins, observed_losses),
            "interpretation": "Exploratory only: the exact calculation assumes independent discordant cells; repeated tasks and shared harnesses violate that assumption."},
        "semanticEligiblePairs": {"pairs": len(semantic_pairs),
            "baselinePassed": sum(passed(row["baseline"]) for row in semantic_pairs),
            "improvedPassed": sum(passed(row["improved"]) for row in semantic_pairs),
            "wins": sum(passed(row["improved"]) and not passed(row["baseline"]) for row in semantic_pairs),
            "losses": sum(passed(row["baseline"]) and not passed(row["improved"]) for row in semantic_pairs),
            "definition": "Both native calls succeeded, no external grading error, and both hidden graders counted exactly the frozen expected number of tests (passes or legitimate failures)."},
        "oracleAnySuccessAcrossRounds": {"tasks": len(groups["byTask"]), **oracle,
            "interpretation": "Hidden-grade oracle upper bound across observed repeats, not a deployable selector or a measured cost-matched retry policy."},
        "taskClusterBootstrap": {"unit": "task; all rounds retained within each sampled task", "draws": 10000,
            "rateDifference95Percentile": [boot[249], boot[9749]] if boot else None,
            "interpretation": "Descriptive only: few hand-authored task clusters, not an independent population confidence guarantee."},
        "timing": {"orchestratorElapsedWallMsIncludingPauses": total_wall_ms,
            "trainingWallMsSummedAcrossRounds": full_training, "trainingNativeWallMs": native_training,
            "trainingTransportWallMs": training_transport,
            "additionalOverTrainingBaselineMs": incremental_training_transport,
            "additionalNativeOverTrainingBaselineMs": incremental_training_native,
            "holdoutNativeDeltaMs": delta_native, "holdoutTransportDeltaMs": delta_transport,
            "plannedIncrementalAdditionalNativeMs": additional,
            "fullPipelineAdditionalNativeMs": full_additional,
            "plannedIncrementalAdditionalTransportMs": additional_transport,
            "fullPipelineAdditionalTransportMs": full_additional_transport,
            "additionalSecondsPerNetSuccess": ratio(additional),
            "fullPipelineAdditionalSecondsPerNetSuccess": ratio(full_additional),
            "additionalTransportSecondsPerNetSuccess": ratio(additional_transport),
            "fullPipelineAdditionalTransportSecondsPerNetSuccess": ratio(full_additional_transport),
            "nativeCostTimingComplete": additional is not None and full_additional is not None,
            "transportCostTimingComplete": additional_transport is not None and full_additional_transport is not None,
            "transportTimingMeaning": "Sum of host-measured native session durations, including process startup and failed sessions; not concurrent experiment elapsed time or grader time.",
            "missingTrainingTransportTimings": sum(t.get("transportWallMs") is None
                or t.get("additionalOverTrainingBaselineMs") is None for t in training),
            "missingTrainingTimings": sum(t.get("nativeWallMs") is None for t in training)},
        "repairTimeScenarios": [{"repairSeconds": repair,
            "savedRepairSeconds": net * repair,
            "plannedIncrementalAdditionalNativeSeconds": additional / 1000 if additional is not None else None,
            "plannedIncrementalNetSecondsSaved": net * repair - additional / 1000 if additional is not None else None,
            "fromScratchAdditionalNativeSeconds": full_additional / 1000 if full_additional is not None else None,
            "fromScratchNetSecondsSaved": net * repair - full_additional / 1000 if full_additional is not None else None,
            "plannedIncrementalAdditionalTransportSeconds": additional_transport / 1000 if additional_transport is not None else None,
            "plannedIncrementalTransportNetSecondsSaved": net * repair - additional_transport / 1000 if additional_transport is not None else None,
            "fromScratchAdditionalTransportSeconds": full_additional_transport / 1000 if full_additional_transport is not None else None,
            "fromScratchTransportNetSecondsSaved": net * repair - full_additional_transport / 1000 if full_additional_transport is not None else None}
            for repair in (60, 300, 900)],
        "amortization": [{"tasksPerFreshHarness": count,
            "meanTrainingNativeSeconds": mean_training_native / 1000 if mean_training_native is not None else None,
            "meanTrainingIncrementalNativeSeconds": mean_incremental_native / 1000 if mean_incremental_native is not None else None,
            "additionalNativeSecondsPerTask": amortized(count),
            "fromScratchAdditionalNativeSecondsPerTask": amortized(count, full=True),
            "meanTrainingTransportSeconds": mean_training_transport / 1000 if mean_training_transport is not None else None,
            "meanTrainingIncrementalTransportSeconds": mean_incremental_transport / 1000 if mean_incremental_transport is not None else None,
            "additionalTransportSecondsPerTask": amortized(count, transport=True),
            "fromScratchAdditionalTransportSecondsPerTask": amortized(count, full=True, transport=True),
            "observedNetSuccessRateDifference": net / n if n else None,
            "breakEvenRepairSeconds": amortized(count) / (net / n) if n and net > 0 and amortized(count) is not None else None,
            "fromScratchBreakEvenRepairSeconds": amortized(count, full=True) / (net / n)
                if n and net > 0 and amortized(count, full=True) is not None else None,
            "breakEvenTransportRepairSeconds": amortized(count, transport=True) / (net / n)
                if n and net > 0 and amortized(count, transport=True) is not None else None,
            "fromScratchBreakEvenTransportRepairSeconds": amortized(count, full=True, transport=True) / (net / n)
                if n and net > 0 and amortized(count, full=True, transport=True) is not None else None}
            for count in (8, 24, 100)],
        "availableTrainingRounds": len(available_training), "costUsd": None,
        "roundReproducibility": {"positive": sum(r["improvedPassed"] > r["baselinePassed"] for r in groups["byRound"]),
            "negative": sum(r["improvedPassed"] < r["baselinePassed"] for r in groups["byRound"]),
            "tied": sum(r["improvedPassed"] == r["baselinePassed"] for r in groups["byRound"])},
        "limitations": ["Training and holdout samples are dependent within each frozen harness round.",
            "The cursor regression is now a known evaluation case; heldout means excluded from these training calls, not unknown to the experiment designer.",
            "Unavailable arms count as unsuccessful in planned-pipeline rates; semantic analysis is separately restricted to eligible successful native calls.",
            "Completed pairs means both scores were collected, including native/grading failures; semantic-eligible pairs exclude these failures and invalid hidden-test counts.",
            "Native milliseconds sum provider sessions; concurrent elapsed time and human repair time are different quantities.",
            "Planned incremental time excludes the ordinary training-task baseline; from-scratch time charges all training calls. Transport and native timings are reported separately.",
            "Missing or zero-duration failed native sessions make native cost ratios and break-even estimates unavailable; observed native sums are lower bounds only. Host transport timing is independent and may remain complete.",
            "Amortization at 24/100 tasks is a timing scenario holding the observed effect fixed, not evidence that the quality benefit generalizes beyond these tasks.",
            "No token or monetary price is inferred; source-screening is conservative and not a general hostile-JavaScript trust boundary."]}
