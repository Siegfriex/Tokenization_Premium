# NB07/NB08 — Analysis Trigger Matrix — v1

**Purpose.** This is not a new analysis plan — `configs/research_v1.yaml`'s `traceability_matrix`
already fixes RQ -> data -> estimand -> method -> output for RQ1-RQ7. What's missing is the
*operational* question this document answers: **when a specific artifact lands, what exactly runs,
in what order, and what must already be true before it's allowed to run.** This closes the gap so
that the moment Codex's P2 v002 (and later phase artifacts) land, the research lane executes
immediately with zero re-derivation of semantics. SSOT refs: §16-17 (baseline analysis + RQ1
inference), §29 (multiple-testing/reporting), §31 (gates), §34 (traceability matrix), §35
(tables/figures), §37 Phase 5.

**Status: SEMANTICS-READY, PENDING artifacts.** Nothing in this document is executed yet — G1 is
still OPEN, no v002 population artifact exists as of this writing (2026-08-16 ~21:00 KST,
[[project_pair_duplicate_recon_v001]] / [[project_d01_independent_audit_v001]]).

## 1. Artifact -> trigger table

| Artifact (file, schema) | Produced by | Unlocks | Blocked without |
|---|---|---|---|
| `PAIR_REGISTRY_v00N.parquet` (D-01), QC'd + G1 PASS | `02_normalize_and_qc.ipynb` | `03`, `04`, `05` raw token-count step (parallel) | Manual QC N=500 (still NOT_PERFORMED) is part of G1 PASS per §31 — v002 landing is necessary but not sufficient for G1 |
| `REP_FEATURES_v001.parquet` (D-02) | `03_representation_features.ipynb` | `05`'s decomposition step (§4 in NB05 precontract), `07` T02/F04-F05 | — |
| `MORPH_FEATURES_KIWI_v001.parquet` (D-03) | `04_morphology_features.ipynb` | `09`'s M2 block (not `07`/`08` — RQ1 does not need morphology) | — |
| `TOKEN_O200K_BASE_v001.parquet` (D-04), G2+G3 PASS | `05_o200k_measurement.ipynb` | `07` (descriptive decomposition), `08` (RQ1 inference) | G2 identity check and G3 100% roundtrip — see §2, hard gate, not advisory |
| `CHUNK_O200K_BASE_v001.parquet` (D-05) | `06_regex_chunk_audit.ipynb` | `09`'s M3 mechanism audit only | Not required for `07`/`08` — RQ5 is a separate, later question |

**The one hard dependency for `07`/`08` to start at all**: D-04 with G2 (decomposition identity)
and G3 (tokenizer roundtrip/hash) both PASS. D-02 is required for the decomposition components
(`CodePointRatio`, `ByteDensityRatio`) inside D-04's own computation (per NB05 §4), but once D-04
exists and its gates pass, `07`/`08` need nothing else — they do **not** wait on D-03 or D-05.

## 2. Execution sequence once D-04 (G2+G3 PASS) lands

This is the concrete, ordered checklist — not a restatement of the traceability matrix, but the
step order within it:

1. **Verify gates, don't re-check them.** Confirm G2/G3 PASS artifacts exist (the identity-check
   log and roundtrip-audit log from NB05 §5/§6) — do not re-run the identity check inside `07`/`08`;
   that would duplicate NB05's job and risks silently masking a NB05 bug behind a second
   implementation.
2. **`07_eda_and_decomposition.ipynb` — descriptive first, always before inference:**
   - T01 Sample composition and QC flow (from D-01's QC disposition, already available at G1).
   - T02 Overall KO-EN tokenization statistics (mean/median/SD/IQR/quantiles of token counts,
     TP, logTP, ΔT, CodePointRatio, ByteDensityRatio, CompressionPenalty, tokens/codepoint,
     tokens/byte — §16.1, all descriptive, no test statistics yet).
   - F01-F05 (KO/EN token scatter, TP histogram+ECDF, domain TP violin/box, exact-decomposition
     component distribution, ByteDensityRatio vs CompressionPenalty).
   - Extreme-case audit (§16.3): auto-extract top/bottom 50-100 TP cases, do **not** pre-delete
     any as outliers — classify first (hard error vs valid extreme), exclude only confirmed hard
     errors, keep valid extremes in the analysis cohort.
   - This notebook produces T01-T02 and F01-F05 only. It does **not** run the RQ1 hypothesis test —
     that is `08`'s job. Keeping the boundary here matters because §29 requires distinguishing
     "post-hoc extreme-case exploration" from "confirmatory result," and mixing descriptive EDA
     with the primary test in one notebook makes that separation easy to blur by accident.
3. **`08_primary_inference.ipynb` — RQ1, and RQ1 only:**
   - Primary test: one-sample signed-rank test on `Median(logTP) = 0` vs `> 0` (§17.1).
   - Robustness companion, run alongside (not instead of): sign test, specifically because §17.1
     flags this as the check to run "if distributional symmetry is in doubt" — run it
     unconditionally as a robustness companion rather than gating its execution on a prior symmetry
     test, since a symmetry pretest itself has known size-distortion problems and isn't specified
     anywhere else in the SSOT as a required step.
   - CIs (§17.2): pair-level bootstrap 95% CI, `bootstrap_resamples = 5000` (already frozen in
     `configs/research_v1.yaml`), for median TP, geometric mean TP, median logTP, `P(TP>1)`, median
     absolute token difference. **Source-stratified bootstrap is the default** when source
     imbalance is large; source-cluster bootstrap is secondary, only when source-level counts are
     sufficient (§17.2) — check the source-count condition before choosing, don't default to
     cluster bootstrap for convenience.
   - Reporting rule (§17.3, binding): never report a p-value alone. Effect size + CI first; if N is
     very large, interpret practical premium magnitude over "statistically significant" language.
   - Produces T01/F01-F03 (per the traceability matrix's own RQ1 row) — some of T01/F01-F03 overlap
     with `07`'s descriptive output; where they do, `08` reuses `07`'s already-computed tables rather
     than recomputing them, to avoid two notebooks silently diverging on the same number.

## 3. What `07`/`08` explicitly do NOT do (scope fence, so neither notebook creeps into 09's job)

No M0-M3 regression fitting, no morphology block, no tokenizer-mechanism (chunk) features, no
identifiability-gate contingency tables. Those all belong to `09_explanatory_models.ipynb` and
require **G5 Analysis Readiness** (§31: identifiability check, collinearity report, analysis cohort
freeze, split manifest freeze) — a strictly later, separate gate that `07`/`08` do not need and must
not be blocked on. RQ1 is deliberately the one research question answerable from D-01+D-04 alone.

## 4. Multiple-testing scope for this stage (§29)

RQ1 is a single primary test — no FDR correction applies to it (§29: "단일 primary RQ1에는 불필요한
FDR 보정을 적용하지 않는다"). FDR correction only becomes relevant once `09`/`11` introduce the
morphology-coefficient family and domain-interaction family — out of scope for `07`/`08`.

## 5. Readiness checklist (§39, the subset relevant to `07`/`08` specifically)

- [ ] G1 PASS (registry frozen, QC N=500 complete — not yet done, see [[project_d01_independent_audit_v001]])
- [ ] G2 PASS (exact decomposition identity, eps=1e-10, 100% of rows)
- [ ] G3 PASS (tokenizer roundtrip 100%, hashes recorded)
- [ ] Analysis cohort hash frozen for the run `07`/`08` will execute against
- [ ] `bootstrap_resamples=5000` and `g2_decomposition_identity_epsilon=1e-10` confirmed unchanged
      from `configs/research_v1.yaml` (both already AMB-01/AMB-02 resolved — re-derive nothing)

None of these are checked yet as of this writing — this document is the pre-registered execution
plan waiting on them, not a claim that any box above is checked.
