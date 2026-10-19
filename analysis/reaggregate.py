#!/usr/bin/env python3
"""Recompute published comparisons offline from the source-only result JSON."""
import argparse
import hashlib
import json
from pathlib import Path
from bench_statistics import summarize
from visible_retry import replay

ROOT = Path(__file__).resolve().parent.parent
KNOWN = {'bounded-map-settled', 'dependency-schedule', 'paginated-records'}
CONFIG = 'layered-config-merge'


def calculate(document):
    primary = document['primary']
    rows, training = primary['rows'], primary['training']
    keys = [(r['round'], r['taskId']) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate task/round cell')
    def stats(selected, elapsed=None):
        return summarize(selected, training, seed=primary['seed'], total_wall_ms=elapsed)
    supplemental = document['supplement']['report']['rows']
    if {r['taskId'] for r in supplemental} != {CONFIG}:
        raise ValueError('unexpected supplemental task')
    primary_summary = stats(rows, primary['summary']['timing']['orchestratorElapsedWallMsIncludingPauses'])
    primary_summary['timing']['externalTrainingExcludedFromOrchestratorElapsed'] = True
    return {
        'classification': 'Offline recomputation; no new model calls or independent samples',
        'primary': primary_summary,
        'subgroupAndExclusionSensitivity': {
            'knownThreeTasks': stats([r for r in rows if r['taskId'] in KNOWN]),
            'newFiveTasks': stats([r for r in rows if r['taskId'] not in KNOWN]),
            'excludingAmbiguousConfig': stats([r for r in rows if r['taskId'] != CONFIG]),
        },
        'clarifiedSubstitutionSensitivity': {
            'classification': 'POSTHOC replacement sensitivity; 21 original cells plus 3 clarified-config cells, not a new full replication',
            'summary': stats([r for r in rows if r['taskId'] != CONFIG] + supplemental),
        },
        'observableRetryPosthocReplay': replay(primary),
        'observableRetryExcludingConfigPosthocReplay': replay(primary, exclude_tasks=[CONFIG]),
    }


def verify(document, result):
    checks = {
        'primary': result['primary'] == document['primary']['summary'],
        'subgroupAndExclusionSensitivity': result['subgroupAndExclusionSensitivity'] == document['subgroupAndExclusionSensitivity'],
        'clarifiedSubstitutionSensitivity': result['clarifiedSubstitutionSensitivity']['summary'] == document['clarifiedSubstitutionSensitivity']['summary'],
    }
    for key in ['observableRetryPosthocReplay', 'observableRetryExcludingConfigPosthocReplay']:
        # File provenance/timestamps were attached by the private CLI, not statistics.
        expected = {k: v for k, v in document[key].items() if k not in ['inputReport', 'generatedEpochSeconds']}
        checks[key] = result[key] == expected
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'evaluation/coding-expanded-comparison-2026-10-19.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', action='store_true', help='fail unless every published statistic matches')
    args = parser.parse_args()
    data = args.input.read_bytes()
    document = json.loads(data)
    result = calculate(document)
    checks = verify(document, result)
    if args.verify and not all(checks.values()):
        raise SystemExit('Published statistics mismatch: ' + ', '.join(k for k, v in checks.items() if not v))
    result['inputSha256'] = hashlib.sha256(data).hexdigest()
    result['publishedStatisticsMatch'] = checks
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'publishedStatisticsMatch': checks, 'primaryPassed': {a: result['primary'][a]['passed'] for a in ['baseline', 'improved']}, 'pairs': result['primary']['pairs'], 'retryPassed': result['observableRetryPosthocReplay']['summaries']['ordinaryObservableRetryUpTo3']['passed'], 'fixedImprovedRound1Passed': result['observableRetryPosthocReplay']['summaries']['improvedRound1WithFullTraining']['passed'], 'fullTrainingExtraSecondsPerNetSuccess': result['primary']['timing']['fullPipelineAdditionalTransportSecondsPerNetSuccess']}, indent=2))


if __name__ == '__main__':
    main()
