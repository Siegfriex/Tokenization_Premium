# NB05 — o200k_base Token Measurement Precontract — v1

**Status: SEMANTICS-READY, PENDING P2 v002 (2026-08-16).** `configs/tokenizer_v1.yaml` already
freezes tokenizer identity, artifact hashes, and the roundtrip smoke-test samples — not restated
here. This document adds the D-04 field contract, the exact-decomposition computation sequence, and
the G2 identity-check procedure that turns the SSOT's math (§8) into an executable gate. SSOT refs:
§8 (Exact Decomposition), §12.4 (D-04 schema), §14 (tokenizer fixed rules), §25 (Track A), §31 (G2,
G3). Track B (§26, gpt-oss serving / D-06) is explicitly out of scope for this notebook — Track A
and Track B are never merged into the same columns (Decision D-03) and Track B is deferred
non-blocking per this project's prior scoping ([[project_hardware_track_b_constraint]]).

## 1. Preconditions

Same distinction as NB03 §1: G1 OPEN does not block implementing this notebook's tokenizer-
measurement code, its unit tests, or exercising it against synthetic/small-sample input — including
the exact-decomposition computation sequence in §4 and the G2 identity check in §5, all of which can
be validated on synthetic data now. G1 PASS (plus D-02 existing) is required only before a
full-population run is promoted as evidentiary D-04.

This notebook additionally consumes `codepoint_count`/`utf8_bytes` from D-02
(NB03's output) to compute the decomposition — **not** a re-derivation of those quantities. If D-02
is not yet built, this notebook can still measure raw token counts (`ko_token_count`,
`en_token_count`, `token_premium`, `log_token_premium`) independently, but `CodePointRatio` and
`ByteDensityRatio` (and therefore the G2 identity check) require D-02 to exist first. Recommendation:
sequence as 03 -> 05's decomposition step, even though 04 and 05's raw token-count step have no such
dependency and could run in parallel with 03/04.

## 2. Grain, keys, row-count expectation

One row per `pair_id` (`measurement_id` is the surrogate run key, analogous to
`morph_measurement_id` in NB04 §2 — re-running under a different `tiktoken`/artifact hash produces a
new `measurement_id`, same `pair_id`). Input is `*_text_analysis` for **both** KO and EN, encoded
independently per language with **no chat template, no system/user role, no special token** (§25.2)
— this is the Track A raw-text-efficiency measurement, structurally distinct from the Track B
Harmony-serialized measurement in D-06.

## 3. What this notebook computes (D-04 fields, §12.4 — no new feature zoo)

`tokenizer_id`, `tiktoken_version`, `encoding_file_sha256`, `mergeable_ranks_hash`, `pat_str_sha256`,
`special_tokens_hash` (all provenance, sourced from `configs/tokenizer_v1.yaml`'s
`artifact`/`hash_contract` block — this notebook records them per-run, it does not redefine them),
`ko_token_ids`/`en_token_ids`, `ko_token_count`/`en_token_count`, `token_premium`,
`log_token_premium`, `token_difference`, `compression_penalty`, `roundtrip_ok`.

## 4. Exact decomposition computation sequence (§8 — the load-bearing part of this notebook)

Compute in this order, each step a pure function of the previous:

1. **Token Premium**: `TP_i = T_{i,KO} / T_{i,EN}` (§8.1) — from this notebook's own token counts.
2. **Code Point Ratio**: `CodePointRatio_i = C_{i,KO} / C_{i,EN}` (§8.2) — from D-02's
   `codepoint_count`, joined on `pair_id`. This notebook does not recompute code point counts.
3. **Byte Density Ratio**: per-language `D^B_{i,l} = B_{i,l} / C_{i,l}` (from D-02's `utf8_bytes` /
   `codepoint_count`, i.e. D-02's own `bytes_per_codepoint` column), then
   `ByteDensityRatio_i = D^B_{i,KO} / D^B_{i,EN}` (§8.3).
4. **Tokenizer Compression Penalty**: per-language token-per-byte `E_{i,l} = T_{i,l} / B_{i,l}`
   (`T` from this notebook, `B` from D-02), then
   `CompressionPenalty_i = E_{i,KO} / E_{i,EN}` (§8.4).
5. **Identity check (this is G2, not a separate step)**: verify
   `TP_i = CodePointRatio_i * ByteDensityRatio_i * CompressionPenalty_i` exactly, equivalently in log
   space `|logTP_i - (logCodePointRatio_i + logByteDensityRatio_i + logCompressionPenalty_i)| < eps`
   with `eps = 1.0e-10` (already frozen in `configs/research_v1.yaml`
   `g2_decomposition_identity_epsilon`, AMB-01/D-RD-01 — this notebook consumes that constant, does
   not re-decide it).

Because steps 2-4 are algebraically forced by step 1's ratio and D-02's own byte/codepoint values,
the identity in step 5 is not a statistical check — it must hold to floating-point precision for
every single row. **Any row failing the epsilon bound is an implementation bug in this notebook
(wrong join, wrong ratio order, unit mismatch), not a data-quality finding** — per Notebook
Constitution §9 (fail-fast), a single failing row should halt the notebook, not get flagged and
carried forward.

## 5. G2/G3 gate mapping (§31, made concrete for this notebook)

- **G2 Representation Integrity PASS conditions**, satisfied by this notebook: Unicode
  normalization audit (delegated to NB03/normalization contract), codepoint/grapheme/byte unit
  tests (delegated to NB03), and **exact decomposition numerical identity** — §4 step 5 above is
  the direct, executable form of this condition.
- **G3 Tokenizer Integrity PASS conditions**, satisfied by this notebook: 100% roundtrip
  (`decode(encode(text)) == text` for every accepted-cohort row, not just the smoke-test samples in
  `tokenizer_v1.yaml`), `tiktoken` version/hash recorded (already frozen, this notebook stamps it
  per-run), `pat_str` hash recorded, and an audit-sample token-bytes inspection (§14.2 rule 4 —
  `decode_single_token_bytes`, not just token IDs, for a review sample).

## 6. Validation / fail-fast conditions

- `roundtrip_ok == true` for 100% of rows (§25.4, G3) — any failure blocks the gate, full stop.
- `ko_token_count > 0` and `en_token_count > 0` for every accepted-cohort row (§25.4).
- G2 identity check (§4 step 5) passes for 100% of rows at `eps = 1.0e-10`.
- Pilot-scale (100-pair) script/byte-decoding audit clean before scaling to the full cohort (§25.4)
  — do not run the full-cohort measurement before this pilot check passes once.

## 7. Downstream consumers

`06_regex_chunk_audit.ipynb` (D-05, FK to this notebook's `measurement_id`),
`07_eda_and_decomposition.ipynb` (T02/T03, F01-F05 — the decomposition components computed here are
the direct input to every one of those tables/figures), `08_primary_inference.ipynb` (RQ1 signed-rank
test on this notebook's `log_token_premium`), `09_explanatory_models.ipynb` (Outcome A/B = this
notebook's `log_token_premium`/`log_compression_penalty`).

## 8. File naming

`TOKEN_O200K_BASE_v001.parquet` per SSOT §38.
