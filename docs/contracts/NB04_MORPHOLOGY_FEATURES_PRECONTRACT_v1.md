# NB04 — Morphology Features Precontract — v1

**Status: SEMANTICS-READY, PENDING P2 v002 (2026-08-16).** `configs/morphology_v1.yaml` already
freezes the analyzer identity, prohibited actions, POS mapping, and the two feature blocks — that
file is the machine-readable source of truth and is **not restated in full here**. This document
adds the operational details `morphology_v1.yaml` does not cover: grain/keys, failure handling,
what "ready to implement" means, and the 03/04 physical-schema question, which remains open (see
`NB03_REPRESENTATION_FEATURES_PRECONTRACT_v1.md` §4 — status: SPEC_AMBIGUITY /
PROPOSED_PHYSICAL_SCHEMA_CLARIFICATION, not a resolution). SSOT refs: §12.3 (D-03 schema), §15
(analyzer freeze), §37 Phase 3.

## 1. Preconditions

Same distinction as NB03 §1: implementation, unit tests, schema preparation, and synthetic/
small-sample dry runs are not blocked by G1 OPEN. A full-population run promoted as evidentiary D-03
requires the same G1 PASS precondition as NB03's evidentiary-run precondition. Independent of
`03_representation_features.ipynb` — per NB03 §4, D-03 does not consume D-02 and D-02 does not
consume D-03. Both read `*_text_analysis` from the same registry (G1-passed, for the evidentiary
run); they can run in either order or in parallel.

## 2. Grain, keys, row-count expectation

One row per `pair_id` for the KO side only (`M_a(x_{i,KO})` per §5 of the SSOT — morphology analysis
is defined over the Korean text only, there is no `_en` counterpart; do not add English morphology
columns, that would be a new feature not in scope per §3.1 In Scope). `morph_measurement_id` is a
separate surrogate key for the measurement *run* (re-running Kiwi under a different
`analyzer_config_hash` produces a new `morph_measurement_id`, same `pair_id`) — do not conflate the
two. Row count must equal the G1-passed registry's accepted-cohort count.

## 3. What this notebook computes — primary block only by default, alternative block for sensitivity

Per `configs/morphology_v1.yaml` `feature_blocks`: primary = `morpheme_density`, `particle_ratio`,
`ending_ratio`, `deriv_affix_ratio`. Alternative = `morpheme_density`, `function_morpheme_ratio`,
`deriv_affix_ratio`. **Both blocks are computed and stored** (§15.3 requires the parallel comparison
to check collinearity impact), but only the primary block feeds M2 in the main explanatory model
(§19.1) — the alternative block is a robustness-analysis input (§24 item 7), never substituted into
the primary model without a logged decision.

Collinearity rule (already in `morphology_v1.yaml`, restated because it is easy to violate by
accident when wiring a regression): `function_morpheme_ratio` and its components (`particle_ratio`,
`ending_ratio`) must never appear together in the same primary regression — that is exactly what
"primary block" vs "alternative block" as two separate model variants is *for*. A future
implementer adding both blocks' columns to one design matrix "for convenience" would silently
re-introduce the collinearity SSOT §15.3/§21 explicitly designed the block split to avoid.

## 4. Analyzer failure handling (not fully specified in morphology_v1.yaml — filled in here)

`D-03.analysis_warning_flag` marks a failed/anomalous Kiwi run (§12.3). This precontract specifies
the disposition, since the SSOT schema table alone doesn't say what happens to the four ratio
columns when the flag is set:

- If Kiwi analysis fails entirely for a `pair_id` (exception, empty output where non-empty input
  was given): `morpheme_count`, `particle_count`, `ending_count`, `deriv_affix_count`, and all four
  derived ratios are `null` (not 0 — a 0 would misrepresent "analyzed, zero particles" as
  indistinguishable from "not analyzed"), `analysis_warning_flag = true`,
  `morphology_status = ANALYZER_FAILURE`.
- If Kiwi succeeds but returns a warning-level anomaly (e.g. OOV-heavy input, per T-05 Analyzer
  measurement error): counts/ratios are still stored as computed, `analysis_warning_flag = true`,
  `morphology_status = COMPLETED_WITH_WARNING`. These rows stay in the primary analysis cohort by
  default (T-05's mitigation is analyzer-version-freeze + sample audit + curated-source subset, not
  blanket exclusion) — G4's "sample manual inspection" PASS condition (§31) is where a human checks
  whether warning-flagged rows need reclassifying, not an automatic drop here.
- Clean rows: `morphology_status = OK`.

**Fail-fast condition (Notebook Constitution §9)**: an analyzer failure rate above whatever
threshold G4's "failure rate 보고" surfaces as anomalous should block a silent gate PASS — this
notebook must *report* the failure rate as a first-class output, not just log it, so G4 has
something concrete to gate on.

## 5. POS mapping — Sejong tag freeze (restated pointer only)

`J*` = particle, `E*` = ending, `{XSN, XSV, XSA}` = derivational affix, exactly as frozen in
`configs/morphology_v1.yaml` `pos_mapping`. This precontract adds no new mapping decisions — any
observed Kiwi tag outside this set that a future implementer is tempted to fold into one of these
buckets must instead surface as an unmapped-tag count in `morpheme_sequence` provenance, not be
silently absorbed.

## 6. What this notebook must NOT do (§15.2, restated because violations are easy to introduce silently)

Never feed Kiwi's morpheme-boundary output back into the tokenizer as input (§15.2 rule 1). Never
use an analyzer-corrected string as Track A tokenizer input (§15.2 rule 2). Never apply a
domain-specific custom dictionary and then compare across sources without an identical secondary
track (§15.2 rule 3). These three are analyzer-pipeline-contamination risks specific to morphology
work and are the most likely accidental violation if 04 and 05 (tokenizer measurement) end up
implemented by people who don't re-read §15 closely.

## 7. Downstream consumers

`07_eda_and_decomposition.ipynb` / `09_explanatory_models.ipynb` (M2 = M1 + morphology primary
block, the RQ4 test — incremental value judged by block-level LR test/AIC/BIC/partial R², never a
single coefficient p-value per §19.2), `11_robustness.ipynb` (primary vs alternative block
comparison, §24 item 7).

## 8. File naming

`MORPH_FEATURES_KIWI_v001.parquet` per SSOT §38.
