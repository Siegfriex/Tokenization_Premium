# G5 Identifiability Precheck — v1

**Status: PRE-REGISTERED CHECKLIST, NOT YET EXECUTED (2026-08-16).** This pre-registers the exact
diagnostics G5 (Analysis Readiness, SSOT §31: "identifiability check, collinearity report, analysis
cohort freeze, split manifest freeze") requires before `09_explanatory_models.ipynb` may produce a
coefficient table, per SSOT §20.2 Gate G-ID and `configs/research_v1.yaml`
`identifiability_gate_minimum_diagnostics`. No check below has been run against real data — G1 is
still OPEN and no corrected canonical P2 cohort exists yet. This document fixes *what* will be
checked and *how* a failure is disposed of, so that the moment a real cohort lands, G5 executes
immediately with zero re-derivation of semantics — same operating pattern as
`docs/research/NB07_NB08_ANALYSIS_TRIGGER_MATRIX_v1.md`. SSOT refs: §20.1-20.2 (Random vs Fixed,
Identifiability Gate), §21 (collinearity/compositional handling), §31 (G5 PASS conditions).

## 0. Scope boundary

This document pre-registers checks. It does **not** pre-decide which coefficients are estimable, does
not pre-select a model specification, and does not resolve the already-known 026 confound (below) —
per the mission instruction, unsupported coefficients are not pre-decided here; G-ID's actual verdict
is produced only when the checks are run against a real cohort.

## 1. Required diagnostics (SSOT §20.2, `configs/research_v1.yaml` `identifiability_gate_minimum_diagnostics`)

### 1.1 `source_id × domain` support

- **Check**: full contingency table, cell counts and cell proportions, `source_id` (fixed effect,
  `n_source` currently 3 candidates: `025`, `026`, `Legacy` — Legacy `primary_analysis_eligible=false`
  so the **main** cohort's effective `n_source=2`) × canonical `domain` (8-level taxonomy, §9.2).
- **Already-confirmed structural finding (not re-derived here, carried from
  `docs/contracts/G1_PAIR_REGISTRY_PRECONTRACT_v1.md` §14 and
  `docs/research/DIRECTION_AND_DOMAIN_MAPPING_PRECONTRACT_v1.md` Task 6 principle 4)**: 026's
  `domain=기술과학` (train 319,551 + valid 40,359) is numerically identical in count to
  `source_provenance_raw=특허정보원`, and the other four 026 domains (세계/경제/정치/기후) are
  correspondingly identical to `source_provenance_raw=한국연구재단`. Within 026 alone, `domain` and
  `source_provenance_raw` are **not separably estimable** — every row's domain value is fully
  determined by which of the two raw-source labels it carries, and vice versa.
- **What this means for the `source_id × domain` table specifically (not yet checked, since
  `source_id` is coarser than `source_provenance_raw`)**: 026 is a single `source_id` value, so the
  `source_id × domain` table's 026 row is simply "026 spans all 5 of its domains" — the confound is
  invisible at `source_id` granularity and only visible at `source_provenance_raw` granularity (§1.3
  below). **This is exactly why both tables (§1.1 canonical-source and §1.3 raw-source) are mandatory,
  not redundant** — checking only `source_id × domain` would miss the 026 confound entirely.
- **Disposition rule**: if any `source_id × domain` cell (at the coarse `source_id` grain) is zero or
  near-zero, that `domain` level's coefficient is not comparably estimable across sources and must be
  reported as such, not silently dropped or forced.

### 1.2 `source_id × translation_direction` support

- **Check**: contingency table, `source_id` × 4-level `translation_direction` taxonomy (post
  group-resolution, §16 duplicate-group rule).
- **Already-known asymmetries (not re-derived here)**: 026 is single-direction (`KO_TO_EN` only, no
  reverse-direction file exists, `translation_direction_defaults` in `configs/research_v1.yaml`) —
  `source_id=026` has **zero** support for `EN_TO_KO`/`UNKNOWN`. Legacy is 100% `UNKNOWN` (D-RD-06) —
  `source_id=Legacy` has **zero** support for `KO_TO_EN`/`EN_TO_KO`. Only `025` has within-source
  variation across `KO_TO_EN`/`EN_TO_KO` (`HUMAN_PARALLEL_UNKNOWN` is not currently used by any
  source). Practical consequence: a `source × translation_direction` interaction term is only
  estimable within `025`; for `026` and `Legacy`, direction is a constant, not a covariate, and any
  main-effect coefficient on `translation_direction` in a pooled M0-M3 fit is effectively identified
  by `025`'s internal variation alone, not by cross-source contrast.
- **Additional split-level finding (not a source×direction cell issue, but adjacent and must be
  checked alongside it)**: 025's `EN_TO_KO` **validation** split is 100% `domain=해외영업` (all
  150,038 rows) while `EN_TO_KO` **training** is mixed across all 3 of 025's domains — a
  direction×domain×split asymmetry (`DIRECTION_AND_DOMAIN_MAPPING_PRECONTRACT_v1.md`, "New finding").
  This must be checked as its own 3-way cross-tab (`source_id=025` subset, `translation_direction` ×
  `domain` × `is_validation_upstream`) before any claim that a held-out evaluation generalizes across
  domains within 025's `EN_TO_KO` direction.
- **Disposition rule**: report the zero-support cells explicitly in G5's identifiability report rather
  than fitting an interaction term that both zero-support sources would silently drop out of.

### 1.3 `source_provenance_raw × domain` and `source_provenance_raw × translation_direction`

- **Check**: same two contingency tables as §1.1/§1.2, but keyed on the finer-grained
  `source_provenance_raw` field (§6a of `G1_PAIR_REGISTRY_PRECONTRACT_v1.md` — the raw `source` JSON
  field, e.g. `특허정보원`, `한국연구재단`, `SBS`, `크라우드 소싱`/`크라우드소싱` preserved as
  distinct literal strings, publisher names for Legacy) — **not** a substitute for §1.1/§1.2, an
  additional pair of tables at a different granularity.
- **Purpose**: this is the table that actually surfaces the 026 domain confound (§1.1) — a coarse
  `source_id × domain` table cannot show it because 026 is one `source_id` value spanning multiple
  `source_provenance_raw` values, each of which maps 1:1 to one `domain` value.
- **Disposition rule**: any `source_provenance_raw` level with a single-`domain` (or single-direction)
  cell is flagged as **structurally confounded**, not estimable as an independent effect from that
  axis — per Gate G-ID (§20.2), no coefficient table is forced for a confounded pair; the fix (if one
  is later chosen) is a redesign — e.g. treating `domain` and `source_provenance_raw` as one composite
  factor for 026, or restricting domain-effect claims to 025 only — and that redesign choice is
  **explicitly deferred to whoever runs the actual M0-M3 fit**, not made here (same deferral as
  `G1_PAIR_REGISTRY_PRECONTRACT_v1.md` §14's own closing line).

## 2. Zero / near-zero variance features

- **Check**: for every categorical M0-M3 term (§`docs/contracts/NB09_EXPLANATORY_MODEL_MATRIX_v1.md`),
  compute the level-count distribution and flag any level below a to-be-set minimum count (this
  document does not set that minimum number — it is a G5-execution-time decision informed by the
  realized cohort size, not a value to guess now) and any feature with a single realized level across
  the **entire main cohort** (025+026, Legacy excluded per `primary_analysis_eligible=false`).
- **Already-known candidate**: `sentence_type` — on current evidence (§16.A of
  `G1_PAIR_REGISTRY_PRECONTRACT_v1.md`), none of 025/026/Legacy supply explicit sentence-type
  metadata, so canonical `sentence_type=other` for 100% of rows. If this holds at evidentiary-cohort
  time, `sentence_type` in M0 has **zero variance** and cannot be fit as a covariate at all (not "an
  insignificant coefficient" — a degenerate design-matrix column). G5 must report this explicitly
  rather than let a fitting library silently drop it (e.g. via automatic aliasing) without a paper
  trail.
- **Continuous features**: same check for D-02/D-03/D-05 numeric columns (e.g. a script-share column
  that is ~0 for every row in a given source, such as `hangul_ratio` for Legacy if Legacy's raw text
  is EN-only in some subset — not yet confirmed, to be checked against the real cohort, not assumed).

## 3. Correlation structure (pairwise Spearman/Pearson)

- **Check**: full pairwise correlation matrix across all M1-M3 continuous candidate regressors
  (D-02 byte/whitespace/script/surface fields, D-03 morphology primary-block fields, D-05 mechanism
  fields), reported once per model-block addition (i.e. an M1-scoped matrix, then an M1+M2-scoped
  matrix, then M1+M2+M3-scoped) so that a correlation newly introduced by adding a block is visible
  at the point it is introduced, not buried in one M3-scope matrix.
- **Known-in-advance structural correlations (T-06, not new findings, restated so G5's report doesn't
  need to rediscover them)**:
  - `bytes_per_codepoint_ko`/`bytes_per_codepoint_en` (D-02) are the two components of
    `ByteDensityRatio_i` (D-04) — expect these to correlate strongly with `ByteDensityRatio_i` and,
    transitively, with `token_premium`/`log_token_premium` if the latter is (mis)included in the same
    feature set as a regressor rather than only as the outcome (see NB09 §5's T-06 flag).
  - `LengthRatio_i` (D-02, §13.5) and `CodePointRatio_i` (D-04, §8.2) are both `log(C_ko/C_en)` from
    the same underlying counts — expect near-perfect correlation (effectively the same variable
    computed in two schemas) if both are ever entered together.
  - `particle_ratio`/`ending_ratio` (primary morphology block) are components of
    `function_morpheme_ratio` (alternative block) by POS-mapping construction (§15.3/§21) — expect
    strong correlation if both blocks are ever pooled into one design matrix, which is already
    forbidden by contract (`morphology_v1.yaml` `collinearity_rule`), not merely discouraged by this
    correlation check.
  - Script-share columns (`hangul_ratio`...`other_ratio`, and D-05's `chunk_type_share_*`) sum to ~1
    per language by construction — expect the standard compositional negative-correlation pattern
    among shares.

## 4. Condition number

- **Check**: condition number of the design matrix at each of M0, M1, M2, M3 (four numbers, not one —
  reported incrementally as blocks are added, same rationale as §3's incremental correlation
  matrices, so a jump in condition number is attributable to the specific block that introduced it).
- **Threshold**: SSOT does not specify a numeric condition-number threshold (unlike VIF, §5) — this
  document does not invent one. G5's report states the raw condition number at each block and flags
  it as a qualitative concern for Director/implementer review rather than asserting a pass/fail cutoff
  that SSOT never specified.

## 5. VIF / GVIF

- **Check**: VIF for continuous terms, generalized VIF (GVIF) for any categorical term with >2 levels,
  computed per model block (M1, M2, M3 — not meaningful for M0 alone beyond the categorical terms
  already covered by §1's contingency tables).
- **Thresholds (AMB-10 resolved, D-RD-01, already frozen in `configs/research_v1.yaml`
  `collinearity_diagnostics`)**: warning at VIF/GVIF ≥ 5, severe warning at ≥ 10.
- **Disposition rule (binding, restated from SSOT §21 and `morphology_v1.yaml`)**: **automatic feature
  deletion by VIF/GVIF alone is prohibited.** A severe-warning feature triggers a semantics review
  (does this feature carry independent meaning worth keeping despite overlap, per §21's "feature
  semantics를 먼저 검토한다"), not an automatic drop. Elastic Net's own feature-selection output
  (§22) is never substituted for the explanatory model's coefficient table (§21: "Elastic Net feature
  selection 결과를 설명모형의 '진실'로 대체하지 않는다").

## 6. Deterministic feature overlap

- **Check**: explicit enumeration of every field pair that is deterministically related by
  construction (not merely empirically correlated) — this is the T-06 threat, and it is a
  **superset** of what §3's correlation matrix would show empirically, because a deterministic
  relationship holds exactly (correlation ≈ 1.0 or an exact algebraic identity) regardless of sample.
- **Enumerated pairs (transcribed from NB09 §5, not re-derived — this is the same list, presented here
  as G5's own deterministic-overlap checklist rather than duplicated reasoning)**:
  1. `log_token_premium = logCodePointRatio_i + logByteDensityRatio_i + logCompressionPenalty_i`
     exactly (G2 identity, eps=1e-10) — the three right-hand terms must never all appear as
     regressors alongside `log_token_premium` as outcome in the same model; at most, this is a
     descriptive accounting relationship (T02/F04-F05 in `07`), not a regression input set.
  2. `LengthRatio_i` (D-02) and `CodePointRatio_i` (D-04) are the same quantity
     (`log(codepoint_count_ko/codepoint_count_en)`) computed in two different schemas — entering both
     is redundant, not merely correlated.
  3. `bytes_per_codepoint_ko`/`_en` (D-02) algebraically determine `ByteDensityRatio_i` (D-04) —
     same relationship as (1) one level down.
  4. `particle_ratio`+`ending_ratio` (primary morphology block) sum toward
     `function_morpheme_ratio` (alternative block) by POS-mapping construction (§15.3) — already a
     hard **contractual** prohibition (`morphology_v1.yaml`), not merely a G5 advisory.
  5. Script-share columns (D-02) and chunk-type-share columns (D-05) each sum to ~1 per language —
     compositional, not independent degrees of freedom; one reference category must be dropped or a
     compositional transform used (§21), decided at `09`'s model-build time, not at G5 itself (G5's
     job is to confirm the report exists, not to make the drop-category choice).
- **Disposition rule**: G5 PASS requires this enumeration to be present in the identifiability report
  as a named table — it is not satisfied merely by the VIF/GVIF numbers happening to be low, since a
  perfectly balanced dataset could still show low empirical VIF while the underlying relationship is
  exact and only "hidden" by how few of the identity's three terms were included in a given block.

## 7. What G5 does NOT do (scope fence)

- Does not pre-decide the 026 domain/source confound's resolution (composite factor vs 025-only
  domain claims) — that is deferred to whoever runs the M0-M3 fit, per
  `G1_PAIR_REGISTRY_PRECONTRACT_v1.md` §14's own closing line.
- Does not set a condition-number pass/fail threshold SSOT never specified.
- Does not decide which of the T-06 deterministic-overlap pairs' "safer" side (D-02 raw features vs
  D-04 ratio components) M1 should actually use — that is the same open flag as NB09 §5, carried here
  as a G5 precondition rather than resolved.
- Does not run any check against real data yet — every disposition rule above is conditional
  ("if X holds at evidentiary-cohort time"), not an assertion that it already holds.

## 8. G5 PASS condition mapping (§31, made concrete)

| SSOT §31 G5 condition | Satisfied by |
|---|---|
| identifiability check | §1 (four contingency tables) + Gate G-ID disposition |
| collinearity report | §3 (correlation matrices) + §4 (condition number) + §5 (VIF/GVIF) + §6 (deterministic overlap enumeration) |
| analysis cohort freeze | Not covered by this document — depends on G1 PASS (registry frozen + manual QC N=500 complete, still outstanding per `[[project_d01_independent_audit_v001]]`) and a recorded cohort hash for the exact row set `09` will fit against |
| split manifest freeze | Not covered by this document — depends on `cohort_and_split` (§23, LR-01) actually being executed and its resulting train/holdout manifest hashed and recorded |

The last two rows are listed for completeness of the G5 gate; this document's own scope (per the
mission that produced it) is §1-§6 (identifiability + collinearity) only.
