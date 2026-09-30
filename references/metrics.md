# Metric rules

Calculate from compatible unrounded totals. Name numerator, denominator, source, attribution and spend basis. Preserve native platform ratios separately if they use different denominators.

| Measure | Formula | Condition |
|---|---|---|
| CTR | Defined clicks / impressions × 100 | Name click type. |
| CPC | Spend / clicks | Same scope/currency. |
| CPM | Spend / impressions × 1,000 | Same spend basis. |
| Cost per outcome | Spend / defined outcomes | Compatible populations. |
| Click-to-outcome rate | Outcomes / clicks × 100 | Not automatically platform eligible-interaction CVR. |
| Qualification rate | Qualified / raw outcomes × 100 | Same mature acquisition cohort. |
| Cost per qualified outcome | Spend / qualified outcomes | Compatible spend/source coverage. |
| ROAS | Attributed monetary revenue / media spend | Same currency and compatible basis; not profit. |
| Proxy-value-to-cost | Assigned value / spend | Not monetary revenue or ROAS. |
| Target attainment | Actual outcomes / target × 100 | Same definition, period and grain. |
| Budget utilisation | Actual spend / budget × 100 | Same spend/currency/period basis. |
| Absolute change | Current − previous | Comparable definitions. |
| Relative change | (Current − previous) / previous × 100 | Nonzero base; qualify negative bases. |
| Percentage-point change | Current percentage − previous percentage | Distinct from relative change. |

Use null for missing data and undefined ratios. Spend with zero outcomes means no outcomes recorded, not efficient zero CPA. Aggregate rates from totals rather than averaging campaign ratios. Preserve fractional attribution credits without calling them unique people.

Do not sum reach or unique users across overlapping audiences/days. Do not average impression shares without valid denominators. Repeated-event rates can exceed 100%; investigate count rules rather than automatically rejecting them.

For compatible positive totals: actual unit cost / planned unit cost = budget utilisation / target attainment. This verifies arithmetic, not scalability. If a separately supplied efficiency target differs from budget/volume-derived cost, present both distinctly.

Explain segment contributions using absolute changes across complete mutually exclusive segments. Signed shares may exceed 100% when declines offset growth. Check whether allocation mix explains a blended improvement.

Use matching elapsed periods and planned phasing for month-to-date comparisons. A linear run-rate is a labelled scenario, not a reliable forecast. Do not build a cohort funnel from unrelated period totals.

Optional descriptive arithmetic bridge: `(current spend − previous spend)/previous CPA + current spend × (1/current CPA − 1/previous CPA)` equals outcome change when positive CPAs and scopes align. It is order-dependent and not causal; the bundled helper does not calculate it automatically.
