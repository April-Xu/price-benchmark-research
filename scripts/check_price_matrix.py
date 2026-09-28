#!/usr/bin/env python3
"""Validate a JSONL price benchmark matrix.

Usage:
  python3 check_price_matrix.py records.jsonl [--strict]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

REQUIRED = [
    "provider",
    "target_region",
    "product",
    "target_spec",
    "billing_dimension",
    "payment_term",
    "currency",
    "status",
    "source_price_url",
    "source_spec_url",
    "queried_at",
]

STATUSES = {
    "exact",
    "approximate",
    "cross_generation",
    "regional_reference",
    "channel_required",
    "unavailable_public",
    "unavailable_service",
}
TERMS = {"on_demand", "monthly", "annual_commitment", "package", "free_tier", "other"}
NO_PUBLIC_PRICE = {"channel_required", "unavailable_public", "unavailable_service"}


def number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not a price")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and re.fullmatch(r"\s*-?\d+(?:\.\d+)?\s*", value):
        return float(value)
    raise ValueError("must be a number")


def url(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"https?://\S+", value) is not None


def date(value: str) -> bool:
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_record(row, seen):
    errors, warnings = [], []
    if not isinstance(row, dict):
        return ["Each line must be a JSON object"], warnings

    for key in REQUIRED:
        if key not in row or row[key] in (None, ""):
            errors.append(f"missing required field: {key}")
    if errors:
        return errors, warnings

    status = row.get("status")
    term = row.get("payment_term")
    if status not in STATUSES:
        errors.append(f"invalid status: {status}")
    if term not in TERMS:
        errors.append(f"invalid payment_term: {term}")
    if not isinstance(row.get("currency"), str) or not re.fullmatch(r"[A-Z]{3}", row["currency"]):
        errors.append("currency must be a 3-letter ISO code, e.g. USD")
    if not date(row.get("queried_at", "")):
        errors.append("queried_at must use YYYY-MM-DD")
    if not url(row.get("source_price_url", "")):
        errors.append("source_price_url must be an http(s) URL")
    if not url(row.get("source_spec_url", "")):
        errors.append("source_spec_url must be an http(s) URL")

    key = tuple(str(row.get(k, "")) for k in
                ("provider", "target_region", "product", "target_spec", "billing_dimension", "payment_term"))
    if key in seen:
        errors.append("duplicate price-cell key: provider/target_region/product/target_spec/billing_dimension/payment_term")
    seen.add(key)

    def num(field, required=False):
        if field not in row or row[field] is None:
            if required:
                errors.append(f"{field} is required")
            return None
        try:
            value = number(row[field])
            if value < 0:
                errors.append(f"{field} must not be negative")
            if value == 0 and term != "free_tier":
                errors.append(f"{field}=0 is only allowed for free_tier; missing prices must be null")
            return value
        except ValueError as exc:
            errors.append(f"{field} {exc}")
            return None

    list_price = num("list_price")
    promo_price = num("promo_price")
    sub_price = num("substitute_price")
    std_price = num("standardized_price")

    if std_price is not None:
        if not row.get("standardized_unit"):
            errors.append("standardized_price requires standardized_unit")
        if not row.get("formula"):
            errors.append("standardized_price requires formula")
    if promo_price is not None and not row.get("promo_conditions"):
        errors.append("promo_price requires promo_conditions")

    include = row.get("include_in_average")
    if include is not None and not isinstance(include, bool):
        errors.append("include_in_average must be true or false")

    if status == "exact":
        if list_price is None and std_price is None:
            errors.append("exact record requires list_price or standardized_price")
        if include is False and not row.get("average_exclusion_reason"):
            errors.append("exact price excluded from average requires average_exclusion_reason")
    else:
        if include is True:
            errors.append("only exact target-region prices may include_in_average=true")
        if not (row.get("difference_note") or row.get("issue_reason")):
            errors.append(f"{status} record requires difference_note or issue_reason")

    if status in {"approximate", "cross_generation"}:
        if list_price is None and sub_price is None:
            errors.append(f"{status} record requires a local list_price or substitute_price")
        if not row.get("difference_note"):
            errors.append(f"{status} record requires difference_note")

    if status == "regional_reference":
        if sub_price is None:
            errors.append("regional_reference requires substitute_price")
        if not row.get("actual_region") or row.get("actual_region") == row.get("target_region"):
            errors.append("regional_reference requires an actual_region different from target_region")
        for field in ("substitute_of", "substitute_reason"):
            if not row.get(field):
                errors.append(f"regional_reference requires {field}")

    if status in NO_PUBLIC_PRICE:
        if list_price is not None or sub_price is not None:
            warnings.append(f"{status} normally has no public/substitute price; move it to another status if one exists")
        if not row.get("issue_reason"):
            errors.append(f"{status} requires issue_reason")

    hours = row.get("monthly_equivalent_hours")
    if hours is not None:
        try:
            h = number(hours)
            if h <= 0:
                errors.append("monthly_equivalent_hours must be positive")
            if term != "on_demand":
                errors.append("monthly_equivalent_hours is only valid for an on_demand hourly equivalent")
            formula = str(row.get("formula", ""))
            if str(int(h)) not in formula:
                errors.append("formula must show the monthly equivalent hour basis")
        except ValueError:
            errors.append("monthly_equivalent_hours must be a positive number")

    if term == "annual_commitment" and row.get("billing_dimension") == "month":
        if row.get("annual_commitment_monthly_equivalent") is not True:
            errors.append("annual commitment divided into months requires annual_commitment_monthly_equivalent=true and must not be called a monthly subscription")

    if row.get("actual_region") and row.get("actual_region") != row.get("target_region") and status != "regional_reference":
        warnings.append("actual_region differs from target_region; consider status=regional_reference")

    return sorted(set(errors)), sorted(set(warnings))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    errors, warnings, seen, total = [], [], set(), 0
    counts = {}
    with args.input.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append({"line": line_no, "errors": [f"invalid JSON: {exc.msg}"]})
                continue
            row_errors, row_warnings = validate_record(row, seen)
            counts[row.get("status", "invalid")] = counts.get(row.get("status", "invalid"), 0) + 1
            if row_errors:
                errors.append({"line": line_no, "errors": row_errors})
            if row_warnings:
                warnings.append({"line": line_no, "warnings": row_warnings})

    result = {
        "ok": not errors and not (args.strict and warnings),
        "records": total,
        "status_counts": counts,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if not result["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
