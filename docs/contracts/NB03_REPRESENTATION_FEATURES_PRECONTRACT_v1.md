# NB03 — Representation Features Precontract — v1

**Status: SEMANTICS-READY, PENDING P2 v002 (2026-08-16).** This is preparation ahead of Phase 3.
G1 (Data Integrity) is still OPEN. **G1 OPEN does not block implementation, synthetic/unit-test
execution, or schema preparation for `03_representation_features.ipynb`** (Vice Director correction,
2026-08-16) — the extraction code, its unit tests, and the D-02 schema can be built and exercised
against synthetic or small-sample input now, with zero new research-semantics decisions in the
loop. What G1 OPEN blocks is promoting a full-population run against the current registry to
formal evidence: any `REP_FEATURES_v001.parquet` produced before a corrected canonical P2 cohort is
confirmed is a synthetic/dry-run artifact, not evidentiary D-02. Machine-readable freeze:
`configs/representation_v1.yaml`.
SSOT refs: §12.2 (D-02 schema), §13.3-13.5 (feature formulas), §16.1-16.2 (baseline distributions
and required visualizations), §21 (collinearity/compositional handling), §37 Phase 3.

## 1. Preconditions

**For implementation, unit tests, schema preparation, and synthetic/small-sample dry runs**: none
beyond the SSOT contract itself — this may proceed now, independent of G1 status.

**For a full-population run promoted as evidentiary D-02** (consumed by NB05/07/08/09 as such):
G1 Data Integrity PASS on the pair registry it consumes (pair IDs unique, null/duplicate
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

## 4. The 03/04 physical-schema question — status: SPEC_AMBIGUITY / PROPOSED_PHYSICAL_SCHEMA_CLARIFICATION

**Classification correction (Vice Director, 2026-08-16): this is not a resolved ambiguity.** The
previous revision of this section framed itself as "the ordering problem this precontract resolves"
— that overstated it. SSOT §12.2's D-02 table lists a "morphology" variable group; this document
does not reinterpret or delete that row, and does not treat the proposal below as an approved
semantic change to §12.2. It records an open physical-schema question and a non-binding proposed
direction, preserved so it can be raised as a `CHANGE_REQUEST` candidate later if the Research
Director wants it settled formally.

**Operational boundary (unchanged, not itself in question)**: `03_representation_features.ipynb`
does not compute morphology under either resolution of the question below —
`04_morphology_features.ipynb` (D-03) remains the sole execution site for morphology measurement.
§37 also runs `03` before `04`, so `03` cannot compute Kiwi-derived ratios that do not exist yet
regardless of how the schema question is resolved.

**Issue**: does §12.2's morphology group belong physically inside D-02
(`REP_FEATURES_v001.parquet`) — following the nullable-then-backfilled pattern
`G1_PAIR_REGISTRY_PRECONTRACT_v1.md` §16.B already used for the 01/02 boundary — or does it belong
only in the separate D-03 artifact (`MORPH_FEATURES_KIWI_v001.parquet`, produced by 04), joined on
`pair_id` at analysis time?

**Proposed direction (engineering opinion only — NOT Director-ratified, NOT a decision)**: D-02
never carries morphology columns; `morpheme_density`, `particle_ratio`, `ending_ratio`,
`deriv_affix_ratio` live only in D-03 and are joined on `pair_id` at analysis time (07/08/09, per the
RQ traceability matrix already in `configs/research_v1.yaml`).

**Impact if this direction were taken**: D-02 and D-03 become two genuinely independent artifacts
with independent versioning (`REP_FEATURES_v001` vs `MORPH_FEATURES_KIWI_v001`) that never need to
be the *same physical file* the way the D-01 registry does, avoiding a spurious coupling between two
notebooks that otherwise have zero dependency on each other's output.

**Alternative**: replicate the D-01 §16.B nullable-then-backfill pattern instead — add morphology
columns to D-02 as null until `04` backfills them. Keeps §12.2's grouping physically literal at the
cost of coupling D-02's schema to D-04's execution timing.

**Disposition**: unresolved. Neither option is adopted by this document. Implementers should treat
"D-02 does not carry morphology columns" as provisional only, and should not cite this section as
authority for a settled schema decision — that requires a `CHANGE_REQUEST` and Research Director
approval.

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
