#!/usr/bin/env python3
"""Validate normalized paid-media evidence and calculate source-aware scorecards.

Standard library only. This does not ingest arbitrary platform exports or
establish whether metadata assertions are true. See references/data-contract.md.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

NUMERIC = ("spend", "impressions", "clicks", "primary_outcomes", "qualified_outcomes", "revenue")
DIMENSIONS = {"product", "funnel", "market", "country", "channel", "campaign_id", "audience", "creative", "date"}
REQUIRED = {"row_id", "source_file", "source_row", "scope_id", "period_id", "spend"}
MISSING = {"", "-", "na", "n/a", "null"}
HUNDRED = Decimal(100)


class DataError(ValueError):
    """Input cannot be safely analysed under the normalized data contract."""


def number(value, label):
    if value is None or str(value).strip().lower() in MISSING:
        return None
    if isinstance(value, bool):
        raise DataError(f"{label}: boolean is not a numeric value")
    try:
        result = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise DataError(f"{label}: expected an unformatted number") from exc
    if not result.is_finite():
        raise DataError(f"{label}: non-finite value")
    return result


def known(value):
    return isinstance(value, str) and value.strip().lower() not in {"", "unknown", "unspecified", "not supplied"}


def scope_known(scope):
    fields = ("currency", "spend_basis", "timezone", "date_basis", "click_type")
    outcome_fields = ("name", "definition", "source", "counting", "attribution")
    return all(known(scope.get(x)) for x in fields) and all(
        known(scope["primary_outcome"].get(x)) for x in outcome_fields
    )


def ratio(numerator, denominator, multiplier=Decimal(1)):
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator * multiplier


def validate_config(config):
    if not isinstance(config, dict):
        raise DataError("Configuration must be a JSON object")
    if config.get("schema_version") != 1 or config.get("mutually_exclusive_rows") is not True:
        raise DataError("Require schema_version 1 and confirmed mutually_exclusive_rows")
    grain = config.get("grain")
    if not isinstance(grain, list) or not grain or len(set(grain)) != len(grain) or any(x not in DIMENSIONS for x in grain):
        raise DataError("Require a nonempty unique grain using supported dimensions")
    for key in ("scopes", "periods"):
        if not isinstance(config.get(key), dict) or not config[key]:
            raise DataError(f"Require a nonempty {key} map")
    for sid, scope in config["scopes"].items():
        if not isinstance(scope, dict) or not isinstance(scope.get("primary_outcome"), dict):
            raise DataError(f"Scope {sid}: require primary_outcome metadata")
        for field in ("currency", "spend_basis", "timezone", "date_basis", "click_type"):
            if not isinstance(scope.get(field), str):
                raise DataError(f"Scope {sid}: require {field}; use explicit unknown when unresolved")
        for field in ("name", "definition", "source", "counting", "attribution"):
            if not isinstance(scope["primary_outcome"].get(field), str):
                raise DataError(f"Scope {sid}: require primary_outcome.{field}")
        for field in ("qualified_outcome", "revenue"):
            if field in scope and not isinstance(scope[field], dict):
                raise DataError(f"Scope {sid}: {field} must be an object")
        if "revenue" in scope and scope["revenue"].get("kind") not in {"monetary", "proxy"}:
            raise DataError(f"Scope {sid}: revenue kind must be monetary or proxy")
    for pid, period in config["periods"].items():
        if not isinstance(period, dict):
            raise DataError(f"Period {pid}: expected metadata object")
        try:
            start, end = date.fromisoformat(period["start"]), date.fromisoformat(period["end"])
        except (KeyError, ValueError, TypeError) as exc:
            raise DataError(f"Period {pid}: require ISO start and end") from exc
        if start > end or period.get("status") not in {"complete", "provisional", "unknown"}:
            raise DataError(f"Period {pid}: invalid interval or status")
    if not isinstance(config.get("targets", []), list):
        raise DataError("targets must be an array")
    seen = set()
    for target in config.get("targets", []):
        if not isinstance(target, dict):
            raise DataError("Each target must be an object")
        key = (target.get("scope_id"), target.get("period_id"))
        if key[0] not in config["scopes"] or key[1] not in config["periods"] or key in seen:
            raise DataError("Unknown or duplicate scope/period target")
        seen.add(key)
        if target.get("basis_confirmed") is not True:
            raise DataError("Confirm target basis before calculating attainment")
        for metric in ("budget", "primary_outcomes"):
            value = number(target.get(metric), f"Target {metric}")
            if value is not None and value < 0:
                raise DataError("Targets cannot be negative")
    if not isinstance(config.get("comparisons", []), list):
        raise DataError("comparisons must be an array")


def read_rows(path, config, group_by):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)):
            raise DataError("Duplicate column headers")
        needed = REQUIRED | set(config["grain"]) | set(group_by)
        if not needed.issubset(columns):
            raise DataError("Missing required columns: " + ", ".join(sorted(needed - set(columns))))
        rows, row_ids, keys = [], set(), set()
        for index, raw in enumerate(reader, 2):
            if None in raw:
                raise DataError(f"CSV row {index}: more values than headers")
            if not any((v or "").strip() for v in raw.values()):
                continue
            row = {k: (v or "").strip() for k, v in raw.items()}
            if any(not row.get(k) for k in needed - {"spend"}):
                raise DataError(f"CSV row {index}: missing identifier, dimension or source reference")
            sid, pid = row["scope_id"], row["period_id"]
            if sid not in config["scopes"] or pid not in config["periods"]:
                raise DataError(f"CSV row {index}: undeclared scope/period")
            key = (sid, pid, *(row[k] for k in config["grain"]))
            if row["row_id"] in row_ids or key in keys:
                raise DataError(f"CSV row {index}: duplicate row ID or declared-grain record")
            row_ids.add(row["row_id"])
            keys.add(key)
            if row.get("date"):
                try:
                    day = date.fromisoformat(row["date"])
                except ValueError as exc:
                    raise DataError(f"CSV row {index}: invalid date") from exc
                period = config["periods"][pid]
                if not date.fromisoformat(period["start"]) <= day <= date.fromisoformat(period["end"]):
                    raise DataError(f"CSV row {index}: date outside declared period")
            scope = config["scopes"][sid]
            for metric in NUMERIC:
                row[metric] = number(row.get(metric), f"CSV row {index} {metric}")
                if row[metric] is not None and row[metric] < 0:
                    if metric in {"impressions", "clicks"} or scope.get("allow_adjustments") is not True:
                        raise DataError(f"CSV row {index}: undocumented negative {metric}")
            qualified = scope.get("qualified_outcome", {})
            raw_count, qual_count = row["primary_outcomes"], row["qualified_outcomes"]
            if qualified.get("same_cohort") is True and raw_count is not None and qual_count is not None:
                if raw_count >= 0 and qual_count >= 0 and qual_count > raw_count:
                    raise DataError(f"CSV row {index}: same-cohort qualified outcomes exceed raw outcomes")
            rows.append(row)
    if not rows:
        raise DataError("No performance records")
    return rows


def calculate_group(rows, scope, period, target=None):
    totals, coverage, warnings = {}, {}, []
    for metric in NUMERIC:
        values = [r[metric] for r in rows if r[metric] is not None]
        coverage[metric] = {"present_rows": len(values), "total_rows": len(rows)}
        totals[metric] = sum(values, Decimal(0)) if len(values) == len(rows) else None
        if len(values) != len(rows):
            warnings.append(f"{metric}: incomplete; total and dependent ratios withheld")
    if not scope_known(scope):
        warnings.append("Unresolved scope metadata; comparative claims are blocked")
    if period["status"] != "complete":
        warnings.append("Period is provisional or maturity unknown; qualify results")
    if any(r[m] is not None and r[m] < 0 for r in rows for m in NUMERIC):
        warnings.append("Documented negative adjustments included; interpret net totals carefully")
    spend = totals["spend"]
    money_known = known(scope["currency"]) and known(scope["spend_basis"])
    nonnegative_spend = spend if money_known and spend is not None and spend >= 0 else None
    metrics = {
        "ctr_pct": ratio(totals["clicks"], totals["impressions"], HUNDRED),
        "cpc": ratio(nonnegative_spend, totals["clicks"]),
        "cpm": ratio(nonnegative_spend, totals["impressions"], Decimal(1000)),
        "cost_per_primary_outcome": None,
        "click_to_outcome_rate_pct": None,
        "qualification_rate_pct": None,
        "cost_per_qualified_outcome": None,
        "roas": None,
        "proxy_value_to_cost": None,
    }
    if not known(scope["click_type"]):
        metrics["ctr_pct"] = metrics["cpc"] = None
    if scope.get("spend_outcome_compatible") is True and scope_known(scope):
        metrics["cost_per_primary_outcome"] = ratio(nonnegative_spend, totals["primary_outcomes"])
    else:
        warnings.append("Primary cost ratio withheld: spend/outcome compatibility or definition unresolved")
    if scope.get("click_outcome_compatible") is True and scope_known(scope):
        metrics["click_to_outcome_rate_pct"] = ratio(totals["primary_outcomes"], totals["clicks"], HUNDRED)
    else:
        warnings.append("Click-to-outcome rate withheld: compatible denominator not confirmed")
    if totals["primary_outcomes"] == 0:
        warnings.append("No primary outcomes recorded; unit cost is undefined")
    qual = scope.get("qualified_outcome", {})
    qual_known = all(known(qual.get(k)) for k in ("name", "definition", "source"))
    if qual.get("same_cohort") is True and qual_known:
        metrics["qualification_rate_pct"] = ratio(totals["qualified_outcomes"], totals["primary_outcomes"], HUNDRED)
    if qual.get("spend_compatible") is True and qual_known:
        metrics["cost_per_qualified_outcome"] = ratio(nonnegative_spend, totals["qualified_outcomes"])
    if totals["qualified_outcomes"] is not None and not qual_known:
        warnings.append("Qualified outcome metadata unresolved; qualification ratios withheld")
    rev = scope.get("revenue", {})
    if rev.get("spend_compatible") is True and all(known(rev.get(k)) for k in ("definition", "source")):
        if rev.get("kind") == "monetary" and rev.get("currency") == scope["currency"] and money_known:
            metrics["roas"] = ratio(totals["revenue"], nonnegative_spend)
        elif rev.get("kind") == "proxy":
            metrics["proxy_value_to_cost"] = ratio(totals["revenue"], nonnegative_spend)
        else:
            warnings.append("Revenue ratio withheld: currency or value basis incompatible")
    if target is not None:
        budget = number(target.get("budget"), "target budget")
        outcomes = number(target.get("primary_outcomes"), "target primary_outcomes")
        metrics["budget_utilisation_pct"] = ratio(nonnegative_spend, budget, HUNDRED)
        metrics["target_attainment_pct"] = ratio(totals["primary_outcomes"], outcomes, HUNDRED) if scope_known(scope) else None
        metrics["planned_unit_cost"] = ratio(budget, outcomes) if scope_known(scope) and money_known else None
    return {"totals": totals, "coverage": coverage, "metrics": metrics, "warnings": warnings,
            "evidence": [{"row_id": r["row_id"], "source_file": r["source_file"], "source_row": r["source_row"]} for r in rows]}


def change(current, previous, percentage=False):
    if current is None or previous is None:
        return {"absolute": None, "relative_pct": None, "reason": "incomplete or withheld value"}
    result = {"absolute": current - previous,
              "relative_pct": (current - previous) / previous * HUNDRED if previous > 0 else None}
    if percentage:
        result["percentage_points"] = current - previous
    if previous <= 0:
        result["reason"] = "zero or negative baseline; relative change withheld"
    return result


def analyse(data_path, config, group_by=()):
    validate_config(config)
    if len(set(group_by)) != len(group_by) or any(d not in DIMENSIONS for d in group_by):
        raise DataError("Unsupported or duplicate grouping dimension")
    rows = read_rows(data_path, config, group_by)
    buckets = defaultdict(list)
    for row in rows:
        key = (row["scope_id"], row["period_id"], *(row[d] for d in group_by))
        buckets[key].append(row)
    targets = {(t["scope_id"], t["period_id"]): t for t in config.get("targets", [])}
    groups, by_key, warnings = [], {}, []
    if group_by and targets:
        warnings.append("Targets not applied to segments: supplied targets are scope/period totals")
    for key in sorted(buckets):
        sid, pid, *dims = key
        group = calculate_group(buckets[key], config["scopes"][sid], config["periods"][pid],
                                targets.get((sid, pid)) if not group_by else None)
        group.update(scope_id=sid, period_id=pid, dimensions=dict(zip(group_by, dims)),
                     scope=config["scopes"][sid], period=config["periods"][pid])
        groups.append(group)
        by_key[key] = group
    comparisons, blocked = [], []
    for comparison in config.get("comparisons", []):
        if not isinstance(comparison, dict):
            raise DataError("Each comparison must be an object")
        sid, current, previous = (comparison.get(x) for x in ("scope_id", "current", "previous"))
        reasons = []
        if sid not in config["scopes"] or current not in config["periods"] or previous not in config["periods"]:
            reasons.append("undeclared comparison scope or period")
        elif current == previous:
            reasons.append("identical periods")
        else:
            if comparison.get("basis_confirmed") is not True or not scope_known(config["scopes"][sid]):
                reasons.append("like-for-like outcome basis unresolved")
            p1, p0 = config["periods"][current], config["periods"][previous]
            s1, e1, s0, e0 = (date.fromisoformat(x) for x in (p1["start"], p1["end"], p0["start"], p0["end"]))
            if max(s1, s0) <= min(e1, e0):
                reasons.append("overlapping comparison intervals")
            if (e1 - s1).days != (e0 - s0).days and comparison.get("periods_comparable") is not True:
                reasons.append("unequal periods without explicit comparability confirmation")
        if reasons:
            blocked.append({"request": comparison, "reasons": reasons})
            continue
        dimensions = {key[2:] for key in by_key if key[0] == sid and key[1] in {current, previous}}
        if not dimensions:
            blocked.append({"request": comparison, "reasons": ["no records for comparison scope/periods"]})
        for dims in sorted(dimensions):
            g1, g0 = by_key.get((sid, current, *dims)), by_key.get((sid, previous, *dims))
            if g1 is None or g0 is None:
                blocked.append({"request": comparison, "dimensions": dict(zip(group_by, dims)),
                                "reasons": ["segment absent in one period; do not assume zero"]})
                continue
            result = {"scope_id": sid, "current": current, "previous": previous,
                      "dimensions": dict(zip(group_by, dims)), "changes": {}, "warnings": []}
            for section in ("totals", "metrics"):
                for metric in sorted(set(g1[section]) & set(g0[section])):
                    result["changes"][metric] = change(g1[section][metric], g0[section][metric], metric.endswith("_pct"))
            if g1["period"]["status"] != "complete" or g0["period"]["status"] != "complete":
                result["warnings"].append("Comparison includes provisional or maturity-unknown data")
            if comparison.get("periods_comparable") is not True:
                result["warnings"].append("Verify weekday mix, seasonality and conversion maturity")
            comparisons.append(result)
    return {"schema_version": 1, "groups": groups, "comparisons": comparisons,
            "blocked_comparisons": blocked, "warnings": warnings}


def serializable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serializable(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--group-by", default="")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        if args.output and Path(args.output).resolve() in {Path(args.data).resolve(), Path(args.config).resolve()}:
            raise DataError("Output cannot overwrite input data or configuration")
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = analyse(args.data, config, tuple(x.strip() for x in args.group_by.split(",") if x.strip()))
        output = json.dumps(serializable(result), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (DataError, OSError, json.JSONDecodeError, TypeError) as exc:
        sys.stderr.write(json.dumps({"error": str(exc)}) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
