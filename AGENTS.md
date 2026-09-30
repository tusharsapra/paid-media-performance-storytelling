# Coding instructions

Read `references/coding-agent-instructions.md`, `SKILL.md` and the relevant data and metric contracts before changing this package.

Keep runtime data out of public resources. Use fictional fixtures. Do not add paid APIs, live account actions, credentials, hardcoded installation paths or required platform integrations.

Preserve CLI compatibility, provenance, null semantics, scope separation and fail-closed comparisons. Run `python3 scripts/test_report_metrics.py` and both sample reports after code changes. Add meaningful regression cases for changed calculations and validation; do not alter tests to accept incorrect results.

Keep the entry point concise and put details in references. Distinguish implemented features from proposed extensions. Do not silently broaden normalized input support into arbitrary platform ingestion.
