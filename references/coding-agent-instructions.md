# Goal and coding-agent instructions

## Goal

Maintain a portable paid-media reporting skill that turns user-supplied evidence into accurate marketing narratives and executable recommendations across industries. Require no particular brand, agency, account structure or paid API. Validate evidence, calculate performance, identify material drivers, distinguish interpretation from hypothesis, and produce the requested report.

A polished report with invented data, bad arithmetic or unsupported causality fails.

## Architecture

- Use `SKILL.md` as the reporting agent's entry point and workflow.
- Load references as needed for definitions, diagnosis, measurement and narrative.
- Use `scripts/report_metrics.py` for validation and arithmetic on normalized CSV with explicit JSON scope metadata.
- Let the host agent read native uploads, normalize data, investigate and write the narrative.
- Keep examples and regression tests fictional. Do not imply the helper imports arbitrary exports or validates the truth of metadata declarations.

## Processing requirements

Preserve originals and source references. Validate grain and join cardinality. Separate different outcomes, currencies, spend bases, timezones and attribution settings. Keep targets separate from performance rows. Use decimal aggregation and compatible denominators. Keep missing values missing and undefined ratios null. Block misleading comparisons when scope or maturity is unresolved. Mark provisional data.

## Reporting requirements

Lead with the business outcome. Separate volume, efficiency, quality and target delivery. Inspect segment and mix effects. Give priority markets sufficient detail while preserving overall context. Distinguish observations, supported interpretations, hypotheses and unknowns. Include scope, roles, dependencies, review timing and success measures in actions. Never invent figures, benchmarks, dates, ownership, approvals or implemented changes.

## Development sequence

1. Read contracts and identify the precise extension or reporting failure.
2. Create a fictional task that exposes it.
3. Implement the narrowest correct change.
4. Add regression cases that test outcomes and failure paths.
5. Run all bundled tests and both sample CLI reports.
6. Forward-test a fresh reporting task with raw artifacts and minimal context; withhold expected answers.
7. Audit public files for private identifiers, original exports, source screenshots, URLs and commercial terms.
8. Validate metadata, reference links and CLI examples. Report changes, checks and limitations.

## Acceptance criteria

Require correct arithmetic, visible definitions, traceable claims, blocked incompatible comparisons, honest uncertainty, question coverage and justified actions. Treat invented numbers, double-counting, mixed-currency totals, zero-cost claims with no outcomes, privacy leakage and unsupported causal claims as hard failures.

## Sample commands

Run from the skill directory and place generated outputs outside it:

```bash
python3 scripts/test_report_metrics.py
python3 scripts/report_metrics.py --data assets/sample-performance.csv --config assets/sample-brief.json --output /tmp/paid-media-total.json
python3 scripts/report_metrics.py --data assets/sample-performance.csv --config assets/sample-brief.json --group-by market --output /tmp/paid-media-markets.json
```

Use a host-appropriate writable directory if `/tmp` is unavailable. Inspect warnings and blocked comparisons before writing.

## Boundaries

Keep native spreadsheet reading optional through the host; the CSV helper has no external dependency. Add adapters only with explicit mappings, provenance and meaningful tests. Treat identity reconciliation, tracking implementation, dashboards, finished decks and account execution as separate tasks. Preserve the file-first path if optional integrations are requested.

When preparing public distribution, keep repository-facing documentation outside the lean execution instructions. Do not publish to an external account or choose a public licence without the owner's instruction.
