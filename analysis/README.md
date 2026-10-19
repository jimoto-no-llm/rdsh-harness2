# Reproduce the published analysis

These commands use stored observations and generated fixture sources. They make **zero model calls** and need no rdsh, DSH, provider authentication, Harness² checkout, or private workspace. Python 3.11+ is sufficient for statistics; cursor source replay additionally requires the installed Node dependencies and macOS `sandbox-exec`.

From the repository root:

```sh
python3 analysis/reaggregate.py --verify
python3 -m unittest discover -s analysis/tests -v
```

`reaggregate.py` reads only [`coding-expanded-comparison-2026-10-19.json`](../evaluation/coding-expanded-comparison-2026-10-19.json). It derives the primary comparison, per-task/per-round results, task-cluster bootstrap, semantic-eligible subset, repair-time scenarios, amortization, known/new task subgroups, ambiguous-config exclusion, clarified-config substitution, and observable-failure retry replay from the per-arm observations. `--verify` compares every derived statistic with the published summaries and exits nonzero on disagreement. It reproduces 9/24 versus 13/24 successes, 4/8 ordinary retry versus 4/8 fixed-round-1 improved successes, and 452.056 seconds of full-training additional host session time per net additional success.

Use `--input FILE` for a compatible document or `--output FILE` to save the full recomputation. Paths default relative to the script location, so invocation from another working directory also works. The saved input SHA records provenance without embedding an absolute path.

The primary 24 cells remain fixed. Config clarification substitutes three posthoc cells in a separate sensitivity calculation; it does not create another independent full replication. Retry selects the first ordinary attempt whose native call, allowed edits, unchanged public tests, edit/test actions, and public tests succeed. Hidden grades are inspected only after selection; a public success with hidden failure stops retry. The three candidates were observed in separate original rounds, so this is an observational replay rather than an executed online retry experiment.

## Replay the cursor counterexamples

```sh
npm ci --ignore-scripts
node analysis/replay-cursor.mjs
```

This verifies the original candidate/test-source hashes, materializes the six stored pagination sources in a fresh temporary directory, applies `pure-esm-fixture-v2`, and runs every test through the existing macOS sandbox. It refuses to run if the sandbox is unavailable and removes only its newly created temporary directory afterward. The source policy is a conservative fixture screen, **not a complete security boundary for arbitrary hostile JavaScript**.

The known five-string cursor case is the original ninth primary assertion, rerun only for its breakdown. The separately labeled source-derived posthoc challenge uses the same bounded union of 26 candidates against all six outputs. Round 1 baseline and round 2 improved pass 25/26; the other four outputs pass 26/26. All original candidate and assertion hashes match. These reruns add no primary scores or independent model samples. Native-failed round-3 outputs remain overall task failures even though their stored sources pass this isolated case.

## Published source artifacts

[`evaluation/artifacts/index.json`](../evaluation/artifacts/index.json) identifies 66 reviewed artifact JSONs: 12 training probes, 48 primary solvers, and 6 clarified-config solvers. Each contains only `files`, `changedPaths`, and `sha256`, unchanged from the original artifact. `files` includes the public fixture tests where the original artifact recorded them; it contains no hidden grader, conversation, native trace, session, model overlay, or credentials. The index records both raw-file and canonical source-map SHA-256. Unit tests verify every entry. Keeping the full source set permits independent audit of all published grades, including failures, instead of selecting successful outputs.

[`evaluation/harnesses/index.json`](../evaluation/harnesses/index.json) records the three adopted aggregate harnesses as synthetic Markdown, with individual file hashes and canonical tree hashes matching the experiment. Adoption succeeded, but not every adaptation stage succeeded. Neither source artifacts nor harnesses prove that the original provider run can be reproduced bit for bit; the model's sampling was not seeded.

Host session time is summed across sessions, includes failures/startup, and is not parallel experiment elapsed time. Human repair times and reuse counts are scenarios, not measured savings. The repeated task/harness dependencies and small hand-authored task set limit inference. No token or dollar cost is inferred.
