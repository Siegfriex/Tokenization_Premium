# P2 v002 Bounded Audit Charter v1

**Role:** Independent Data Integrity / Oracle Auditor (event-driven, bounded scope).
**Branch:** `data/p2-v002-audit-recon` (based on `origin/integration/g1@774abdcff7f79d85f2b46901d9478c500943c63d`).
**Script:** `scripts/audit/p2_v002_bounded_audit.py`.

This charter is prepared *before* a valid canonical v002 exists. It does not
review or modify the P2 remediation/execution code
(`impl/p2-canonical-run-codex`, `src/tokenization_premium/phase2.py`).

## Trigger condition

The bounded audit fires **without separate Vice Director approval** the
moment BOTH of the following exist simultaneously:

1. `data/registry/PAIR_REGISTRY_v002.parquet`
2. `outputs/manifests/QC_MANIFEST_v001.json` (+ `outputs/reports/QC_FLOW_v001.csv`)

A parquet file alone is **not** a valid trigger. On 2026-08-16T21:16:24+09:00,
run `P2_CANONICAL_20260816T211028` produced a 2.95GB v002 parquet
(5,652,925 rows, SHA-256 verified at the `V002_SHA256` stage) but then
FAILED at `SAFE_AGGREGATE_REPORTS` before writing the manifest/report. That
state was correctly treated as **not triggering** this audit — see the
Integration Steward's report at that timestamp. `_require_trigger_evidence()`
in the script enforces this mechanically (verified 2026-08-16T21:56 dry-run:
`TRIGGER_NOT_MET`, exit 2, no scan performed).

No broad/exploratory EDA runs before the trigger. Preparing code and
contract-reading is the only permitted pre-trigger work.

## Independence boundary

Every invariant re-derives the rule from the frozen research contract text
(`research/p2-qc-claude@b9990af` SS3/SS4/SS7/SS9/SS11), not from importing
`phase2.py`'s disposition functions. Shared infrastructure utilities with no
QC judgment content (`hashing.sha256_file`, `registry.resolve_duckdb_memory_limit`)
are reused — those are I/O/runtime-safety plumbing, not the logic under audit.

## The 13 bounded items and the estimand each protects

| # | Item | Script check | Downstream estimand threatened if this fails |
|---|---|---|---|
| 1 | Artifact SHA | `check_01_artifact_sha` | All of Phase 2+ — an unverified artifact means every later stage (G3 tokenizer measurement, TP_i) may be computed on silently-corrupted or substituted data. |
| 2 | Row count | `check_02_row_count` | `RAW_RECORD_DENOMINATOR` (5,652,925) — any drift invalidates every pass-rate denominator in SS11 and the D-01↔P2 lineage claim that no row is added/dropped. |
| 3 | Distinct `pair_id` | `check_03_distinct_pair_id` | Primary-key integrity — a broken key silently double-counts or drops pairs in every later group-by (source/domain/direction), corrupting `TP_i` sample composition. |
| 4 | Required schema | `check_04_required_schema` | Reproducibility (SSOT contract conformance) — missing/extra columns break every downstream notebook that reads v002 by name and can silently null-fill or misalign a field used in QC gating. |
| 5 | `exact_duplicate_flag` invariant | `check_05_exact_duplicate_flag_invariant` | `EXACT_UNIQUE_CONTENT_DENOMINATOR` and `pair_quality_status` — this flag directly gates `accepted`/`rejected` (SS3c priority order), so a broken invariant silently shifts the accepted/rejected split. |
| 6 | `analysis_representative_pair_id` invariant | `check_06_analysis_representative_pair_id_invariant` | `FINAL_ANALYSIS_DENOMINATOR` — this is the field `analysis_eligible_exact_dedup` is defined against (SS4); a wrong representative silently changes which duplicate survives into the primary analysis cohort. |
| 7 | Accepted/rejected counts | `check_07_accepted_rejected_counts` | `FINAL_ANALYSIS_DENOMINATOR` and the entire G1 LID/QC pass-rate closure item (SS10) — this is the actual gate `TP_i` sample membership depends on. |
| 8 | Primary Tier-A realized N | `check_08_primary_tier_a_realized_n` | `PRIMARY_ELIGIBLE_DENOMINATOR` (4,050,507 = 2,700,345 + 1,350,162) — the base population for `primary_cohort_policy.mode: all_qc_accepted_tier_a`; drift here silently changes which corpus dominates the primary analysis. |
| 9 | Source composition | `_composition_diff("source_id"/"logical_corpus")` | Source-mix confound — Phase 2 must not silently rebalance which source rows survive; SS4 guarantees zero row deletion, so any drift is a transform bug, not a legitimate QC outcome. |
| 10 | Domain composition | `_composition_diff("domain")` | Domain-mix confound — same guarantee; a domain-composition shift would bias any later domain-stratified `log TP` estimate without being visible in aggregate N. |
| 11 | `translation_direction` composition | `_composition_diff("translation_direction")` | Direction-mix confound — `TP_i = T_KO/T_EN` is direction-sensitive; silent direction-composition drift would bias the primary inference (`Median(log TP) > 0`) without changing total N. |
| 12 | Anomaly/review aggregates | `check_12_anomaly_review_aggregates` | Non-gating by design (SS3b) — this check only confirms review-only flags never silently became hard-rejects; it does not itself threaten an estimand, it guards against gate-creep. |
| 13 | Catastrophic source/domain/direction loss | folded into 9-11 (`INVARIANT_COMPOSITION_COLUMNS` full-outer-diff vs v001) | Same as 9-11, framed as the "did an entire category silently disappear" catastrophic case — this is checked as an *exact* v001-vs-v002 identity, not a magnitude threshold, because SS4 makes it a zero-tolerance invariant. |

## Verdict contract

- **`P2_BOUNDED_AUDIT_PASS`**: all 13 items pass. Still **not** a G1 PASS —
  manual QC N=500 and the LID/QC pass-rate closure adjudication remain
  separate, human-owned decisions (see `docs/research/P2_QC_DECISION_QUEUE_v1.md`).
- **`P2_BOUNDED_AUDIT_MATERIAL_FINDING`**: one or more items fail. The report
  names the exact failing check and the estimand column above states
  precisely which downstream quantity is threatened — this auditor does not
  generalize beyond what the failing check actually measured.

## Explicit non-scope

- Does not review, fix, or rerun `impl/p2-canonical-run-codex` execution code.
- Does not perform the 500-pair manual semantic audit.
- Does not compute `o200k_base` tokenization or `TP_i`/`logTP_i` (G3 scope).
- Does not write to any other agent's worktree or branch.
