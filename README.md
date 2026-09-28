# Price Benchmark Research Skill

A reusable Agent Skill for building auditable, like-for-like price comparisons from official vendor websites. It works for cloud products across providers and regions—compute, storage, networking, and databases—and for SaaS seats, plans, licenses, and usage packages.

The Skill helps an agent:

- define the decision scope, comparable unit, usage assumptions, and payment terms before collecting prices;
- keep on-demand, monthly, annual-commitment, promotional, free-tier, list, and substitute prices in separate fields;
- record source URLs, query date, selected parameters, formulas, availability status, and substitution rationale;
- handle missing local prices without treating them as zero or assuming the service cannot be purchased;
- calculate averages, differences, tiers, and unit conversions from one source-of-truth matrix;
- preserve user-owned content, comments, and formatting when updating an existing report.

## Repository layout

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Main trigger conditions and end-to-end workflow |
| `references/pricing-schema.md` | JSONL fields, statuses, and product-specific comparison dimensions |
| `references/calculations.md` | Payment terms, unit conversion, tiers, free allowances, averages, and percentage rules |
| `references/report-editing.md` | Report structure, interactive tables, evidence, and safe in-place document updates |
| `scripts/check_price_matrix.py` | Deterministic validator for price-matrix JSONL records |
| `evals/evaluations.md` | Trigger, non-trigger, and boundary evaluation scenarios |

## Install

Copy the complete folder into the skills directory supported by your agent runtime:

```bash
git clone https://github.com/April-Xu/price-benchmark-research.git
cp -R price-benchmark-research <your-skills-directory>/
```

The runtime entry point must be:

```text
<your-skills-directory>/price-benchmark-research/SKILL.md
```

Keep the `references/`, `scripts/`, and `evals/` subdirectories together with `SKILL.md`. Do not put temporary research records, screenshots, or customer documents inside the Skill folder.

## Validate a price matrix

Store one price record per JSONL row, then run:

```bash
python3 scripts/check_price_matrix.py records.jsonl
```

Minimal exact-price example:

```json
{"provider":"Example Cloud","target_region":"global","product":"example service","target_spec":"standard plan","billing_dimension":"seat_month","payment_term":"monthly","currency":"USD","status":"exact","list_price":10,"include_in_average":true,"source_price_url":"https://example.com/pricing","source_spec_url":"https://example.com/specs","queried_at":"2026-01-01"}
```

Common statuses are `exact`, `approximate`, `cross_generation`, `regional_reference`, `channel_required`, `unavailable_public`, and `unavailable_service`. Missing prices must be `null`, not zero. Regional-reference and non-comparable rows are excluded from local averages by default.

## Boundary

Official public prices are procurement and competitive benchmarks. They are not negotiated discounts, final tax-inclusive invoices, or a substitute for self-build TCO. Site selection or self-build conclusions require additional hardware, power, space, bandwidth, utilization, operations, and financing inputs.

## Evaluation

Run the scenarios in `evals/evaluations.md` in a fresh session after changing core rules. At minimum, verify that mixed payment terms, zero-filled gaps, cross-region prices in local averages, and unit-conversion errors are caught or clearly explained.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
