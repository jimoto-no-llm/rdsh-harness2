#!/usr/bin/env node
// Replay stored source artifacts. No provider/SDK/rdsh or model call is used.
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, realpathSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runFixtureTests, supportedSandbox } from '../coding-tools.mjs';
import { validateGradingSources } from '../source-policy.mjs';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const digest = value => createHash('sha256').update(value).digest('hex');
const load = path => JSON.parse(readFileSync(path, 'utf8'));
if (process.argv.length !== 2) throw new Error('This replay takes no arguments');
if (!supportedSandbox().supported) throw new Error('macOS sandbox-exec is required; never run unsandboxed');
const study = load(join(root, 'evaluation/coding-expanded-comparison-2026-10-19.json'));
const index = load(join(root, 'evaluation/artifacts/index.json'));
const fixtures = join(root, 'analysis/fixtures');
const posthoc = readFileSync(join(fixtures, 'posthoc-cursor.test.mjs'), 'utf8');
const known = readFileSync(join(fixtures, 'known-cursor.test.mjs'), 'utf8');
const candidates = load(join(fixtures, 'posthoc-candidates.json')).candidates;
if (digest(JSON.stringify(candidates)) !== study.cursorPosthocFalsification.candidatesSha256 ||
    digest(posthoc) !== study.cursorPosthocFalsification.testcaseSha256 || candidates.length !== 26 ||
    candidates.some(c => Buffer.byteLength(c.value) > 256)) throw new Error('Posthoc fixture integrity mismatch');
const knownCase = known.slice(known.indexOf("test('initial null stays distinct"));
if (digest(knownCase) !== study.cursorFixedCaseBreakdown.caseSha256) throw new Error('Primary cursor assertion integrity mismatch');
const temporary = realpathSync(mkdtempSync(join(tmpdir(), 'rdsh-cursor-replay-')));
const results = [];
try {
  const graderRoot = join(temporary, 'tests'); mkdirSync(graderRoot);
  writeFileSync(join(graderRoot, 'known.test.mjs'), known);
  writeFileSync(join(graderRoot, 'posthoc.test.mjs'), posthoc);
  for (let round = 1; round <= 3; round++) for (const arm of ['baseline', 'improved']) {
    const id = `primary/round-${String(round).padStart(2, '0')}/paginated-records/${arm}`;
    const entry = index.entries.find(e => e.id === id);
    if (!entry) throw new Error('Missing cursor artifact');
    const bytes = readFileSync(join(root, 'evaluation/artifacts', entry.path));
    if (digest(bytes) !== entry.fileSha256) throw new Error('Source artifact hash mismatch');
    const artifact = JSON.parse(bytes);
    const files = Object.keys(artifact.files).filter(p => p.startsWith('src/')).sort();
    if (JSON.stringify(files) !== JSON.stringify(['src/collect-pages.mjs', 'src/merge-records.mjs'])) throw new Error('Unexpected artifact source layout');
    const canonical = JSON.stringify(artifact.files, Object.keys(artifact.files).sort());
    if (digest(canonical) !== artifact.sha256 || artifact.sha256 !== entry.declaredSourceSha256) throw new Error('Canonical source hash mismatch');
    const workspace = join(temporary, `round-${round}-${arm}`); mkdirSync(join(workspace, 'src'), { recursive: true });
    for (const file of files) writeFileSync(join(workspace, file), artifact.files[file]);
    const policy = validateGradingSources(workspace, files);
    if (policy.policy !== 'pure-esm-fixture-v2') throw new Error('Source policy mismatch');
    const scores = {};
    for (const [name, count] of [['known', 1], ['posthoc', 26]]) {
      const run = await runFixtureTests({ workspace, fixtureRoot: workspace, graderRoot, testFiles: [`${name}.test.mjs`], timeoutMs: 15000 });
      if (run.tests !== count || run.passed + run.failed !== count || run.timedOut || run.outputLimited || run.sandbox !== 'macos-sandbox-exec') throw new Error('Incomplete sandboxed test execution');
      const expected = name === 'known' ? study.cursorFixedCaseBreakdown.rows.find(r => r.round === round && r.arm === arm).cursorCase : study.cursorPosthocFalsification.results.find(r => r.round === round && r.arm === arm);
      if (run.passed !== expected.passed || run.failed !== expected.failed) throw new Error('Cursor result differs from published evidence');
      scores[name] = { tests: run.tests, passed: run.passed, failed: run.failed };
    }
    results.push({ round, arm, ...scores });
  }
  console.log(JSON.stringify({ additionalModelCalls: 0, primaryScoreContribution: 0, hostileCodeBoundary: false, sandbox: 'macos-sandbox-exec', verifiedOriginalFixtureHashes: true, results }, null, 2));
} finally { rmSync(temporary, { recursive: true, force: true }); }
