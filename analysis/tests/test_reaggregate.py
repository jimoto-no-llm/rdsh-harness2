import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'analysis'))
from reaggregate import calculate, verify


class ReaggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT / 'evaluation/coding-expanded-comparison-2026-10-19.json').read_text())
        cls.result = calculate(cls.document)

    def test_every_published_summary_recomputed_from_rows(self):
        self.assertTrue(all(verify(self.document, self.result).values()))
        summary = self.result['primary']
        self.assertEqual([summary[a]['passed'] for a in ['baseline', 'improved']], [9, 13])
        self.assertAlmostEqual(summary['timing']['fullPipelineAdditionalTransportSecondsPerNetSuccess'], 452.0561082390009)

    def test_published_summary_cannot_control_recomputed_scores(self):
        changed = copy.deepcopy(self.document)
        changed['primary']['summary']['baseline']['passed'] = 24
        result = calculate(changed)
        self.assertEqual(result['primary']['baseline']['passed'], 9)
        self.assertFalse(verify(changed, result)['primary'])

    def test_failed_native_retains_primary_failure_but_not_semantic_pair(self):
        summary = self.result['primary']
        self.assertEqual(summary['pairs'], 24)
        self.assertEqual(summary['semanticEligiblePairs']['pairs'], 12)
        self.assertEqual(summary['baseline']['nativeFailures'], 8)
        self.assertEqual(summary['improved']['nativeFailures'], 7)
        self.assertEqual(summary['roundReproducibility'], {'positive': 2, 'negative': 0, 'tied': 1})

    def test_config_sensitivity_never_adds_independent_primary_samples(self):
        self.assertEqual(self.result['subgroupAndExclusionSensitivity']['excludingAmbiguousConfig']['pairs'], 21)
        self.assertEqual(self.result['clarifiedSubstitutionSensitivity']['summary']['pairs'], 24)
        duplicate = copy.deepcopy(self.document)
        duplicate['primary']['rows'].append(duplicate['primary']['rows'][0])
        with self.assertRaises(ValueError):
            calculate(duplicate)

    def test_all_exported_source_bytes_and_source_hashes_match(self):
        index = json.loads((ROOT / 'evaluation/artifacts/index.json').read_text())
        self.assertEqual(index['artifactCount'], 66)
        self.assertEqual(len(index['entries']), 66)
        ids = set()
        for entry in index['entries']:
            self.assertNotIn(entry['id'], ids)
            ids.add(entry['id'])
            self.assertNotIn('..', Path(entry['path']).parts)
            self.assertFalse(Path(entry['path']).is_absolute())
            data = (ROOT / 'evaluation/artifacts' / entry['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry['fileSha256'])
            artifact = json.loads(data)
            self.assertEqual(set(artifact), {'files', 'changedPaths', 'sha256'})
            canonical = json.dumps(artifact['files'], sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
            self.assertEqual(hashlib.sha256(canonical).hexdigest(), artifact['sha256'])
            self.assertEqual(artifact['sha256'], entry['declaredSourceSha256'])
            self.assertTrue(entry['reviewedForTampering'])

    def test_published_arm_grades_reference_exact_exported_sources(self):
        index = json.loads((ROOT / 'evaluation/artifacts/index.json').read_text())
        entries = {e['id']: e for e in index['entries']}
        for phase, report in [('primary', self.document['primary']), ('supplement', self.document['supplement']['report'])]:
            for row in report['rows']:
                for arm in ['baseline', 'improved']:
                    key = f"{phase}/round-{row['round']:02d}/{row['taskId']}/{arm}"
                    self.assertEqual(entries[key]['declaredSourceSha256'], row[arm]['score']['artifactSha256'])

    def test_frozen_markdown_harnesses_match_published_provenance(self):
        index = json.loads((ROOT / 'evaluation/harnesses/index.json').read_text())
        for row in index['rounds']:
            files = {}
            for path, digest in row['files'].items():
                self.assertTrue(path.endswith('.md'))
                data = (ROOT / f'evaluation/harnesses/round-{row["round"]:02d}' / path).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                files[path] = data.decode()
            canonical = json.dumps(files, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
            self.assertEqual(hashlib.sha256(canonical).hexdigest(), row['sourceSha256'])
            self.assertEqual(row['sourceSha256'], self.document['primary']['training'][row['round'] - 1]['frozenHarnessSha256'])


if __name__ == '__main__':
    unittest.main()
