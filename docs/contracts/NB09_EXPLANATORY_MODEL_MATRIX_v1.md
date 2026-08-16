# NB09 — Explanatory Model Matrix — v1

**Status: SEMANTICS-READY, PENDING D-02/D-03/D-04/D-05 evidentiary artifacts + G5 PASS (2026-08-16).**
This is a field-level mapping precontract for `09_explanatory_models.ipynb` — it contains no code and
does not itself fit any model. It maps every M0-M3 block term in `configs/research_v1.yaml`
`model_blocks` (SSOT §19.1) and both outcomes (SSOT §18.1-18.2) to the actual upstream artifact/field
that will supply it, using only fields already frozen in D-01/D-02/D-03/D-04/D-05 schemas
(`docs/contracts/G1_PAIR_REGISTRY_PRECONTRACT_v1.md`, `configs/representation_v1.yaml`,
`configs/morphology_v1.yaml`, `configs/tokenizer_v1.yaml`, SSOT §12.5). No new feature is introduced
anywhere in this document. SSOT refs: §12.1-12.5 (D-01-D-05 schemas), §13 (feature formulas), §18
(main model equations), §19 (staged M0-M3 blocks), §20-21 (identifiability/collinearity), MN-01
(no causal language), MN-02/§19.3 (M3 is mechanism audit, not stricter causal control), IR-02 (Outcome
A/B never merged), T-06 (deterministic feature overlap).

Fitting `09` requires **G5 Analysis Readiness PASS** (§31: identifiability check, collinearity
report, analysis cohort freeze, split manifest freeze — see the companion
`docs/research/G5_IDENTIFIABILITY_PRECHECK_v1.md`). This document may be written and reviewed now,
independent of G1/G5 status, per the same implementation-vs-evidentiary-promotion distinction already
used in NB03/NB04/NB05 (`docs/contracts/NB0{3,4,5}_*_PRECONTRACT_v1.md` §1).

## 0. Outcomes

### Outcome A — `log_token_premium` (primary, §18.1)

| Property | Value |
|---|---|
| Source artifact | D-04 (`TOKEN_O200K_BASE_v001.parquet`, `05_o200k_measurement.ipynb`) |
| Canonical field | `log_token_premium` |
| Transformation | None — D-04 stores this directly (`log(token_premium)`, itself `log(T_KO/T_EN)`) |
| Expected sign | Not specified by SSOT (no §16-19 text asserts a directional hypothesis on the outcome itself — RQ1's H1 is `Median(logTP) > 0`, which is a location-shift hypothesis on the outcome, not a regression-coefficient sign) |
| Interpretation boundary | Primary estimand for RQ1 (median, §17) and for M0-M3 (§19). Never reported in the same table/figure as Outcome B (IR-02). All M0-M3 coefficients on this outcome are conditional statistical associations only (MN-01) |
| Collinearity relationship | By construction, `log_token_premium = logCodePointRatio + logByteDensityRatio + logCompressionPenalty` exactly (G2 identity, eps=1e-10) — see §4 below for why this constrains what M1 may contain |
| Role | Explanatory (the modeled outcome itself, not a regressor) |

### Outcome B — `log_compression_penalty` (secondary, §18.2)

| Property | Value |
|---|---|
| Source artifact | D-04, field `compression_penalty` |
| Canonical field | `log_compression_penalty` |
| Transformation | `log(compression_penalty)` — D-04's schema (§12.4) stores `compression_penalty` itself; the log transform is taken at model-build time in `09`, same treatment as `log_token_premium`'s own relationship to `token_premium`. This is not a new feature, it is the log of an already-frozen D-04 decomposition component |
| Expected sign | Not specified by SSOT |
| Interpretation boundary | IR-02: isolates tokenizer-specific fragmentation/compression asymmetry **after** removing the byte-representation share of the premium (§18.2: "UTF-8 byte량의 총 차이를 분리한 뒤 tokenizer-specific fragmentation/compression 차이를 설명"). Never merged with Outcome A in one table/figure |
| Collinearity relationship | Is itself one of the three exact multiplicative components of Outcome A (T-06) — see §4 |
| Role | Explanatory (secondary outcome, mechanism-adjacent per its own definition, but not itself mechanism-only — §18.2 gives it a full M-equivalent model, `α1..α3`, distinct from M3) |

## 1. M0 — `Y ~ length + domain + sentence_type + translation_direction + source`

| Field | Source artifact | Canonical field | Transformation | Expected sign | Interpretation boundary | Collinearity | Role |
|---|---|---|---|---|---|---|---|
| `length` | **SPEC_AMBIGUITY** — SSOT §19.1 names this term but does not pin its exact operational field (§9.2's `length_stratum` is defined as a *stratification* variable, "영어 word/code point 또는 pair mean byte 기준 분위수," AMB-04-resolved to **EN codepoint count, quintile bins** in `configs/research_v1.yaml`). No D-01 field literally named `length` exists. | `length_stratum` (quintile of D-02's `codepoint_count_en`, per AMB-04/D-RD-01) — **candidate only, not Director-ratified as the M0 operationalization**, flagged here so `09`'s implementer does not silently invent a different one | Quintile bin (categorical) or the underlying continuous `codepoint_count_en`/`codepoint_count_ko` — **which of the two enters M0 is itself unresolved and must not be decided by this document** | Not specified | `length_stratum` is computed from a D-02 field (NB03's output), so M0 — nominally the "baseline, pre-representation" block — already has one term (`length`) that cannot be populated before D-02 exists. This is a real sequencing tension worth surfacing to whoever builds `09`, not resolved here | Directly derived from `codepoint_count_en`, which also feeds `LengthRatio_i` (§13.5) and `CodePointRatio_i` (§8.2, D-04) — using both `length_stratum` and `CodePointRatio`/`LengthRatio` in the same model risks the same class of overlap as T-06, even though `length_stratum` is EN-only (not a KO/EN ratio) | Explanatory (baseline control, §19.1) |
| `domain` | D-01 | `domain` (canonical, D-RD-07-mapped) | Categorical, one reference category | Not specified | Confounded with `source_provenance_raw`/`source_id` for 026 (near-perfect, §Identifiability Gate) — must clear G5 before independent interpretation | See G5 precheck | Explanatory |
| `sentence_type` | D-01 | `sentence_type` (canonical; `other` for all three current sources per §16.A — no source supplies explicit sentence-type metadata) | Categorical | Not specified | On current evidence this column has near-zero variance (single level `other` across 025/026/Legacy) — G5's zero/near-zero-variance check must confirm before treating it as an active term at all | None beyond its own single-level degeneracy | Explanatory |
| `translation_direction` | D-01 | `translation_direction` (canonical, group-resolved per duplicate-group rule) | Categorical (`KO_TO_EN`/`EN_TO_KO`/`UNKNOWN`; `HUMAN_PARALLEL_UNKNOWN` not currently used, D-RD-06) | Not specified | T-03 Translationese: direction is both a control and a stratification axis (§9.2, RQ6); 026 is single-direction only (`KO_TO_EN`), Legacy is 100% `UNKNOWN` — direction has no within-source variance for those two sources | Confounded with `domain` for 025's `EN_TO_KO` validation split (100% `domain=해외영업`, a direction×domain×split asymmetry, not yet a coefficient-level confound but a support-coverage one — see G5 precheck) | Explanatory |
| `source` | D-01 | `source_id` (canonical, corpus/acquisition-family granularity — **not** `source_provenance_raw`, §6a) | Categorical, fixed effect primary (D-RD-01/AMB-09; random-intercept only if `n_source>=10` + identifiable + converges + non-singular — currently `n_source=3`, so fixed effects is the only viable primary specification today) | Not specified | Never pooled 025+026 without an explicit stratum label per `source_portfolio.condition` (`configs/research_v1.yaml`); Legacy is `primary_analysis_eligible=false` (`SENSITIVITY_ONLY`) — Legacy rows should not enter the **main** M0-M3 fit at all, only sensitivity item 3 ("full accepted cohort vs curated-source-only cohort") | Near-perfectly confounded with `domain` for 026 (see `domain` row above) — this is the same confound viewed from the other axis | Explanatory |

## 2. M1 — `M0 + byte/whitespace/script/surface features`

All fields below are D-02 (`REP_FEATURES_v001.parquet`, `03_representation_features.ipynb`) columns,
per `configs/representation_v1.yaml` `variable_groups`. Per-language (`_ko`/`_en`) values are D-02's
own storage grain; any KO/EN ratio combination is this notebook's own model-build step, not a D-02
column.

| Field | Source artifact | Canonical field | Transformation | Expected sign | Interpretation boundary | Collinearity | Role |
|---|---|---|---|---|---|---|---|
| Byte density | D-02 | `bytes_per_codepoint_ko`, `bytes_per_codepoint_en` (D-02 stores per-language values only — see `representation_v1.yaml` `byte.note`) | As stored, or entered as the two per-language values rather than their ratio (see collinearity note) | Not specified | Per-language `bytes_per_codepoint` values are what M1 should use, **not** `ByteDensityRatio_i` (that ratio is a D-04 decomposition component of Outcome A itself, §8.3) | **T-06 direct hit**: `ByteDensityRatio_i = bytes_per_codepoint_ko / bytes_per_codepoint_en` is one of the three exact multiplicative factors of `token_premium`. Entering `ByteDensityRatio_i` (or its log) as an M1 regressor on Outcome A would partially re-introduce the decomposition identity into the regression rather than genuinely explaining it — SSOT §18.1's own illustrative equation includes `β2 log ByteDensityRatio_i` directly, which is in tension with T-06's "회귀에 동일 항등식 구성요소 무비판적 중복 투입 금지." **This document does not resolve that tension** — it flags it (SPEC_AMBIGUITY, §18.1-example vs §19.1-staged-blocks vs T-06) for whoever fits `09` to decide explicitly, with the decomposition (T02/F04-F05, `07`) always available as the descriptive-accounting fallback that does not require resolving it | Explanatory (or descriptive-only, per the unresolved tension) |
| Whitespace | D-02 | `whitespace_density_ko`, `whitespace_density_en` (paired as `ΔWhitespaceDensity_i` per §18.1/18.2's own notation, i.e. a KO-EN difference, not a ratio) | `ΔWhitespaceDensity_i = whitespace_density_ko - whitespace_density_en` (SSOT's own §18 notation — a difference, not a ratio, so it is not a decomposition-identity component and is safe from T-06) | Not specified | Appears in **both** Outcome A (§18.1, `β3`) and Outcome B (§18.2, `α1`) — a shared regressor across the two outcome models, which is by design (both outcomes are affected by whitespace-driven fragmentation differences) and not itself a violation of IR-02 (IR-02 forbids merging *reporting*, not sharing a regressor) | None with the decomposition identity (difference, not ratio) | Explanatory |
| Script composition | D-02 | `hangul_ratio`, `latin_ratio`, `digit_ratio`, `punctuation_ratio`, `symbol_ratio`, `other_ratio` (per-language, i.e. `_ko`/`_en` suffixed at storage, per D-02 grain note) | Drop one reference category at model-build time (§21) — **not** decided by D-02 itself (`representation_v1.yaml` explicitly defers this to `09`) | Not specified | This is `ScriptFeatures_i` in §18.1/18.2's notation | Compositional (sums to ~1 per language) — reference-category drop or compositional transform (ILR) as sensitivity only (§21, sensitivity item 7 territory is morphology-specific but the same principle applies here per §21's general rule) | Explanatory |
| Surface/mixing/special-expression | D-02 | `script_type_count`, `script_switch_count`, `url_flag`, `email_flag`, `emoji_flag`, `code_like_pattern_flag` | As stored | Not specified | These are accepted-cohort-internal technical flags (`representation_v1.yaml` `special_expression.note`), distinct from the §10.1 hard-exclusion markup-dominant test that already ran upstream in `02` | None known | Explanatory |
| Lexical length (surface, non-Kiwi) | D-02 | `ko_eojeol_count`, `en_word_count` | As stored | Not specified | Explicitly independent of Kiwi execution (`representation_v1.yaml` `lexical_length.note`) — safe to use in M1 even before D-03 exists | Potential overlap with `length`/`length_stratum` (M0) if both a length control and eojeol/word counts enter the same model — not adjudicated here, G5's VIF/condition-number check is where this surfaces empirically | Explanatory |
| Pair length ratio | D-02 | `LengthRatio_i = log(codepoint_count_ko / codepoint_count_en)` (§13.5) | Already log-transformed at D-02 build time, no smoothing (accepted pairs are never empty) | Not specified | Distinct from `CodePointRatio_i` (D-04, §8.2) even though both are KO/EN codepoint ratios — `LengthRatio_i` is D-02's own surface-length feature, `CodePointRatio_i` is D-04's decomposition component; SSOT keeps them as two named quantities in two different schemas. Using both in the same M1 spec would be redundant (same information, computed twice) — flag, do not silently pick one without noting the substitution | Near-identical in value to `log CodePointRatio_i` (both are `log(C_ko/C_en)`, same underlying counts) — effectively the same T-06 concern as byte density above, one level removed | Explanatory (or redundant with a decomposition component, per the flag) |

## 3. M2 — `M1 + morphology block`

All fields are D-03 (`MORPH_FEATURES_KIWI_v001.parquet`, `04_morphology_features.ipynb`), KO-side only
(§5 of SSOT — no `_en` morphology exists), per `configs/morphology_v1.yaml` `feature_blocks`. This is
the RQ4 test block (§19.2: M2-M1 incremental value via LR test/AIC/BIC/partial R², never a single
coefficient p-value).

| Field | Source artifact | Canonical field | Transformation | Expected sign | Interpretation boundary | Collinearity | Role |
|---|---|---|---|---|---|---|---|
| Primary block | D-03 | `morpheme_density`, `particle_ratio`, `ending_ratio`, `deriv_affix_ratio` | Ratios as stored (derived from D-03's `morpheme_count`/`particle_count`/`ending_count`/`deriv_affix_count`, computation is `04`'s job not `09`'s) | Not specified | This is the **only** morphology block that may enter the *main* M2 (`morphology_v1.yaml` `feature_blocks.usage_rule`) | `function_morpheme_ratio` (alternative block) and its components (`particle_ratio`, `ending_ratio`) must never appear together in one primary regression (§15.3/§21, restated in NB04 §3) — irrelevant here since alternative block is excluded from main M2 by construction, but the constraint still binds if a future implementer merges blocks "for convenience" | Explanatory (and the direct target of RQ4) |
| Alternative block | D-03 | `morpheme_density`, `function_morpheme_ratio`, `deriv_affix_ratio` | As stored | Not specified | Robustness-analysis input **only** (sensitivity item 7, `configs/research_v1.yaml` `sensitivity_analyses.minimum_set`) — never substituted into the primary M2 without a logged decision (NB04 §3) | Same collinearity rule as above, viewed from the other block | Explanatory, sensitivity-track only |
| Analyzer quality gate (not a model regressor) | D-03 | `analysis_warning_flag`, `morphology_status` | N/A | N/A | Rows with `COMPLETED_WITH_WARNING` stay in the primary cohort by default (NB04 §4) — this is a cohort-membership signal, not itself a regressor unless a future sensitivity spec deliberately conditions on it | None | Neither (data-quality metadata, out of scope for M0-M3 as a regressor) |

## 4. M3 — `M2 + regex-chunk/tokenizer mechanism features`

All fields are D-05 (`CHUNK_O200K_BASE_v001.parquet` — file-naming per SSOT §38 convention applied to
the D-05 schema table, §12.5; `06_regex_chunk_audit.ipynb`), joined via `tokenizer_measurement_id` FK
to D-04. **No `docs/contracts/*` precontract exists yet for `06_regex_chunk_audit.ipynb`** — the field
list below is transcribed directly from SSOT §12.5 since no machine-readable `configs/*.yaml` freeze
of D-05 exists at the time of this writing either; a future NB06 precontract should be the actual
freeze point, this document only maps M3 to what SSOT §12.5 already specifies.

| Field | Source artifact | Canonical field | Transformation | Expected sign | Interpretation boundary | Collinearity | Role |
|---|---|---|---|---|---|---|---|
| Chunk count | D-05 | `ko_chunk_count`, `en_chunk_count` | As stored, or a KO/EN ratio computed at model-build time (no SSOT-named ratio field exists for this one, unlike `token_premium`/`CodePointRatio`) | Not specified | §19.3: M3's role is mechanism audit, not a predictive win — a high M3 R² is *expected* and not itself evidence of anything beyond "chunk features are close to the outcome-generating process" | Structurally close to `ko_token_count`/`en_token_count` (D-04) by tokenizer construction (chunk boundaries are the regex pre-tokenization stage that BPE merges operate within) — MN-02: never treat M3's fit as a stricter causal control on M2's morphology coefficients | **Mechanism-only** (§19.3, MN-02) — never explanatory in the causal sense, never used to "control away" M2's morphology association |
| Chunk byte-length distribution | D-05 | `mean_chunk_bytes_*`, `p50_chunk_bytes_*`, `p90_chunk_bytes_*` (`*` = `_ko`/`_en`) | As stored | Not specified | Same §19.3 boundary as above | Same as chunk count | Mechanism-only |
| Tokens per chunk | D-05 | `tokens_per_chunk_*` | As stored | Not specified | This is the closest D-05 field to a direct outcome mechanism (token count normalized by chunk count) — precisely why §19.3 calls out that M3's high R² is expected and uninformative on its own | Mechanically related to `token_premium`/`compression_penalty` (D-04) by construction (chunk-level token yield is the proximate mechanism behind pair-level compression) | Mechanism-only |
| Chunk type composition | D-05 | `chunk_type_share_*` (letter/number/punctuation/whitespace shares) | As stored | Not specified | Parallels D-02's script-share composition (§2 above) one level closer to the tokenizer's own regex boundaries rather than raw Unicode script categories | Compositional (sums to ~1 per language) — same reference-category-drop principle as D-02 script shares (§21) | Mechanism-only |

## 5. Cross-cutting notes (binding on `09`, not new decisions)

- **MN-01** (all blocks): every coefficient above is a conditional statistical association. No field's
  "interpretation boundary" cell in this document may be read as asserting a causal claim, regardless
  of how the field is later found to correlate with the outcome.
- **MN-02** (M3 only): M3's mechanism features are never used to demote or "explain away" M2's
  morphology association as spurious. M3 answers RQ5, not a stricter version of RQ4.
- **IR-02** (Outcome A vs B): no table or figure in `09`'s output may present M0-M3 coefficients for
  both outcomes side by side as if they were one model family.
- **T-06 / §18-vs-§19 tension (this document's own primary open flag)**: SSOT §18.1's illustrative
  equation for Outcome A includes `log CodePointRatio_i` and `log ByteDensityRatio_i` directly as
  regressors, which are two of the three exact multiplicative factors of `log_token_premium` itself
  (G2 identity). SSOT §19.1's staged M0-M3 blocks instead describe M1 as "byte/whitespace/script/
  surface features" (plural, D-02's per-language raw columns), which is a different — and T-06-safer —
  operationalization. **This document does not resolve which reading `09` should implement.** Both
  readings are transcribed above (§2, byte density row) with the tension flagged, per the same
  SPEC_AMBIGUITY discipline as NB03 §4. Raise as a `CHANGE_REQUEST` if the Research Director wants a
  single authoritative M1 specification before `09` is implemented.
- **`length` in M0 (this document's second open flag)**: no D-01/D-02 field is literally named
  `length`; the only SSOT-anchored candidate is `length_stratum` (quintile of D-02's
  `codepoint_count_en`, AMB-04-resolved basis), which cannot be computed before D-02 exists — a minor
  sequencing note for whoever assembles M0's design matrix, not a semantic decision made here.

## 6. Downstream / precondition summary

Requires (evidentiary, not implementation): D-01 G1 PASS, D-02 (NB03), D-03 (NB04), D-04 G2+G3 PASS
(NB05), D-05 (NB06, not yet under contract) all promoted to evidentiary status, plus **G5 Analysis
Readiness PASS** (identifiability check, collinearity report, analysis cohort freeze, split manifest
freeze — `docs/research/G5_IDENTIFIABILITY_PRECHECK_v1.md`). Feeds `10_predictive_split_and_eval.ipynb`
(not yet under contract) and `11_robustness.ipynb` (sensitivity items 6-9 directly exercise this
document's M0-M3/block choices).
