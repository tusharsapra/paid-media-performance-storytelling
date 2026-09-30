# Data contract

Inspect exports, plans, trackers, analytics, CRM summaries, mappings and change logs first. Capture objective, outcome definition, period, comparison, timezone, currency, spend basis, sources, approved targets and desired format. Ask only for material missing information; actuals-only reporting is valid when targets are absent.

Select a source per metric. Establish coverage rather than assuming a CRM or platform is complete. Preserve raw labels and provenance. Validate join cardinality and aggregate to a shared grain before combining sources. Never merge campaign spend onto multiple event or creative rows without preventing multiplication.

## Normalized CSV

Required columns: `row_id`, `source_file`, `source_row`, `scope_id`, `period_id`, `spend` and all declared grain dimensions. Use unique normalized row IDs and original source references such as `Export.csv` and `row 12`.

Optional numeric columns: `impressions`, `clicks`, `primary_outcomes`, `qualified_outcomes`, `revenue`. Blank, dash, `NA`, `N/A` and `null` represent missing. Use finite unformatted numbers. Normalize separators, percent strings and currency symbols before invoking the helper.

Grouping dimensions: `product`, `funnel`, `market`, `country`, `channel`, `campaign_id`, `audience`, `creative`, `date`. Declare the full actual grain, including ad/date dimensions if required. A date, when supplied, must be ISO formatted and fall within its period. Exclude total rows if detail is included. Rows must be mutually exclusive within scope/period; unique row IDs alone do not establish this.

## JSON configuration

Set `schema_version: 1`, `mutually_exclusive_rows: true` and a nonempty `grain` array. Declare `scopes` and `periods` maps; optionally include `targets` and `comparisons`. See `assets/sample-brief.json`.

Each scope declares `currency`, `spend_basis`, `timezone`, `date_basis`, `click_type`, and a `primary_outcome` object with `name`, `definition`, `source`, `counting` and `attribution`. Use explicit `unknown` for unresolved metadata. Such fields block comparative outcome claims.

Set `spend_outcome_compatible: true` only after confirming spend and primary outcomes support a derived cost ratio. Set `click_outcome_compatible: true` only after establishing a compatible click-to-outcome population. Defaults are false; the helper cannot establish these facts from headers.

Optional `qualified_outcome`: `name`, `definition`, `source`, `same_cohort`, `spend_compatible`. Require the same acquisition cohort and comparable maturity for qualification rate, and valid spend alignment for cost per qualified outcome. Lifecycle snapshots are not automatically acquisition cohorts.

Optional `revenue`: `kind` (`monetary` or `proxy`), `definition`, `source`, `currency`, `spend_compatible`. Define refunds/adjustment treatment. Monetary revenue in the same currency supports derived ROAS; proxy value supports a separately labelled value-to-cost ratio.

Set `allow_adjustments: true` only for documented negative spend, outcome or revenue adjustments. Negative impressions/clicks are always invalid.

Each period declares ISO `start`, `end`, `status` (`complete`, `provisional`, `unknown`), and optional `exported_at`. Status is declared, not verified by the helper.

Targets contain `scope_id`, `period_id`, `basis_confirmed: true`, and optional `budget`, `primary_outcomes`. Confirm the approved plan, outcome/source basis, spend basis, currency and period first. Targets apply to scope/period totals only. Do not repeat a monthly target on daily or market rows.

Comparisons contain `scope_id`, `current`, `previous`, `basis_confirmed: true`, optional `periods_comparable: true`. Unequal day counts are blocked unless comparability is explicitly confirmed. Equal day counts do not establish weekday, seasonality or maturity alignment. Provisional periods always carry a qualification.

Use distinct scopes when source, event or attribution definitions differ. Do not request a like-for-like comparison across such scopes. A descriptive spend bridge may still be possible outside the helper with explicit compatible definitions.

## Output

Read `groups`, their coverage, warnings, evidence and derived metrics; also read `comparisons` and `blocked_comparisons`. A total is null if any included row lacks that metric. No silent partial numerator with full spend is allowed.

The helper separates scopes and periods. It does not compute reach, unique people, impression share, significance, causal lift, margin, CAC/payback or future results. Review raw inputs and declarations before using its calculations.
