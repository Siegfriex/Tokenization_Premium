# NB03 — Representation Features Precontract — v1

**Status: SEMANTICS-READY, PENDING P2 v002 (2026-08-16).** This is preparation ahead of Phase 3.
G1 (Data Integrity) is still OPEN — this notebook cannot execute until `02_normalize_and_qc`
produces a QC'd registry and G1 passes. This document exists so that once that artifact lands,
`03_representation_features.ipynb` can be implemented against a frozen contract with zero new
research-semantics decisions in the loop. Machine-readable freeze: `configs/representation_v1.yaml`.
SSOT refs: §12.2 (D-02 schema), §13.3-13.5 (feature formulas), §16.1-16.2 (baseline distributions
and required visualizations), §21 (collinearity/compositional handling), §37 Phase 3.

## 1. Preconditions before this notebook may run

- G1 Data Integrity PASS on the pair registry it consumes (pair IDs unique, null/duplicate
  disposition resolved, source/license metadata complete — SSOT §31 G1).
- Input is `*_text_analysis` (NFC + BOM-stripped + outer-trim, internal whitespace preserved) per
  the normalization contract (`configs/normalization_v1.yaml`) — **never** `*_text_raw` or a
  further-normalized variant. Using the wrong text column here would silently contaminate every
  downstream byte/codepoint/whitespace count.

## 2. Grain, keys, row-count expectation

One row per `pair_id`, 1:1 join to D-01. Row count at population time must equal the accepted-cohort
row count of the D-01 registry it was built from (no fan-out, no silent drops) — any discrepancy is
a fail-fast condition (Notebook Constitution §9), not a warning.

## 3. What this notebook computes (no more, no less — no new feature zoo)

Exactly the variable groups in `configs/representation_v1.yaml`: unicode length (`codepoint_count`,
`grapheme_count` — DN-01, never a combined/ambiguous `char_count`), lexical length
(`ko_eojeol_count`, `en_word_count` — plain whitespace-split counts, independent of Kiwi), byte
(`utf8_bytes`, `bytes_per_codepoint`, `bytes_per_grapheme`), whitespace (`whitespace_count`,
`whitespace_density`, `space_run_count`), script composition and mixing, special-expression flags,
`LengthRatio_i = log(C_{i,KO}/C_{i,EN})` (§13.5, no `+1` smoothing — accepted pairs are never empty),
and provenance (`feature_extractor_version`, `unicode_library_version`).

**Explicitly out of scope for this notebook**: any morpheme/particle/ending/affix column. See §4.

## 4. The 03/04 boundary (the ordering problem this precontract resolves)

SSOT §12.2's D-02 table nominally lists a "morphology" variable group, but §37 runs
`03_representation_features` *before* `04_morphology_features` — so 03 cannot possibly compute
Kiwi-derived ratios that don't exist yet. This is the same shape of problem G1_PAIR_REGISTRY_PRECONTRACT_v1.md
§16.B already solved for the 01/02 boundary (nullable columns, backfilled by the later phase).

**Recommendation (engineering call, not yet Director-ratified — flag for confirmation, not a
silent decision)**: do not replicate that nullable-column pattern here. Instead, D-02
(`REP_FEATURES_v001.parquet`) simply never carries morphology columns; `morpheme_density`,
`particle_ratio`, `ending_ratio`, `deriv_affix_ratio` live only in D-03
(`MORPH_FEATURES_KIWI_v001.parquet`, produced by 04) and are joined on `pair_id` at analysis time
(07/08, per the RQ traceability matrix already in `configs/research_v1.yaml`). Reasons this is
preferred over the nullable-then-backfill pattern used for D-01: D-02 and D-03 are two genuinely
independent artifacts with independent versioning (`REP_FEATURES_v001` vs `MORPH_FEATURES_KIWI_v001`)
that never need to be the *same physical file* the way the D-01 registry does; forcing a
nullable-then-mutated D-02 would create a spurious coupling between two notebooks that otherwise
have zero dependency on each other's output. If the Research Director prefers the nullable pattern
for schema-literalism reasons, swap this section for the D-01 §16.B pattern verbatim — the rest of
this precontract is unaffected either way.

## 5. Compositional feature handling (§21, binding at model-build time, not here)

Script-share ratios (Hangul/Latin/digit/punctuation/symbol/other) sum to ~1 — a composition. This
notebook stores all shares as computed; it does **not** decide which reference category to drop —
that is `09_explanatory_models.ipynb`'s job when M1 is fit. Do not silently drop a category or
apply a compositional transform (e.g. ILR) inside this notebook — that would bake a modeling
decision into a feature-extraction artifact and make the artifact non-reusable across model
specifications.

## 6. Validation / fail-fast conditions (Notebook Constitution §9)

- `codepoint_count > 0` and `utf8_bytes > 0` for every accepted-cohort row (an accepted pair is
  never empty per §13.5's no-smoothing rationale — if either is 0, that pair should have failed
  §10.1 hard exclusion upstream; treat as a QC-boundary bug, not a silent zero).
- `bytes_per_codepoint >= 1.0` for every row (UTF-8 encodes every code point in >=1 byte) — a
  violation indicates an encoding/decoding bug in the extraction step itself.
- Script-share columns sum to 1 within floating-point tolerance per row.
- Row count reconciles exactly against the upstream G1-passed registry (§2).

## 7. Downstream consumers

`04_morphology_features.ipynb` (independent, joins later, no read dependency on this notebook's
output — see §4), `07_eda_and_decomposition.ipynb` (T02 overall statistics, F04 exact-decomposition
component distributions, F05 ByteDensityRatio vs CompressionPenalty), `09_explanatory_models.ipynb`
(M1 = M0 + byte/whitespace/script/surface features per `configs/research_v1.yaml` `model_blocks`).

## 8. File naming

`REP_FEATURES_v001.parquet` per SSOT §38, versioned on any schema or extraction-logic change, with
SHA-256 + row count + schema version + code commit recorded in the release manifest (Appendix B).
