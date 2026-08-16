# G1 Pair Registry Precontract — v1

This is **not** an implementation spec for `01_build_pair_registry.ipynb` and contains no code. It fixes the research semantics that any implementation of that notebook must satisfy. It draws on `docs/research/PAIR_IDENTITY_AND_DUPLICATE_CONTRACT_v1.md`, `docs/research/DIRECTION_AND_DOMAIN_MAPPING_PRECONTRACT_v1.md`, `docs/research/AIHUB_LOCAL_WEB_RECONCILIATION_v1.md`, and SSOT §9-12.

## 0. The 01 / 02 boundary (do not confuse)

- **`01_build_pair_registry` (ingest)**: move raw source records into a reproducible registry with stable identity and full provenance. Exclusions here are **structural/parsing failures only** — a record could not be read into the schema at all (e.g., missing required field, undecodable encoding, malformed JSON/XLSX row).
- **`02_normalize_and_qc` (QC)**: apply SSOT §10.1 hard exclusions (empty text, exact duplicates, language-ID failure, markup-dominant text, control-character anomalies, tokenizer round-trip failure, semantic-QC failure) and §10.2 soft flags.

A record that ingests successfully but is a duplicate, or has anomalous-but-parseable text, is **not** excluded at step 01 — it enters the registry with its full identity and gets excluded/flagged at step 02. Conflating these two exclusion reasons would make it impossible to later ask "how many raw records existed at all" independent of "how many passed QC."

## 1. Source acquisition identity

Each of the 3 currently-known local dataset families (025, 026, Legacy) gets one `source_id`. `source_id` must carry: local family label, ingest snapshot reference (pointing to the `RAW_FILE_MANIFEST_SHA` data-recon already computed — `9a546bc9...c1f0c`), and a placeholder for the official AIHub `dataSetSn` (currently unconfirmed — AMB-12/OPEN, do not fabricate one). D71693 has no `source_id` yet — it is `NOT_ACQUIRED`.

## 2. Source registry & license note

Per D-01 schema (§12.1): `source_id`, `source_tier`, `source_license_note`. `source_tier` stays unpopulated (`null`) until AMB-12 resolves (see `configs/research_v1.yaml`). `source_license_note` must record the **self-asserted** raw `license` field value (`"open"` for 025/026 JSON) verbatim, plus an explicit annotation that this has not been checked against AIHub's official usage policy (application/approval requirement, redistribution restriction — per Perplexity's evidence audit U1-U3). Legacy has no license field at all — `source_license_note = "UNKNOWN — no license metadata in source"`.

## 3. Raw file hash linkage

Every `pair_id` must be traceable to the exact physical raw file(s) it came from via the already-computed per-file SHA-256 values in `AIHUB_RAW_RECON.md` §B. This is provenance linkage only — it does not imply re-verification of those hashes at registry-build time (though re-verification is cheap and recommended as a smoke test, that is Codex's implementation call).

## 4. Pair grain & stable pair identity

One registry row = one raw KO/EN record, per the identity design in `PAIR_IDENTITY_AND_DUPLICATE_CONTRACT_v1.md`: `pair_id` is provenance-derived (`source_id` + `source_record_id`), never a content hash. `duplicate_group_id` (content-based) is a proposed **auxiliary** field, not yet confirmed as required for G1 — see decision queue.

## 5. Raw provenance / raw field selection

For JSON corpora, the registry must retain `sn`, `data_set`, `domain` (raw), `subdomain` (raw), `ko`, `en`, `ko_original`/`en_original` (whichever present), `mt`, `source_language`, `target_language`, `source` (raw), `license` (raw), `style`, `file_name` — i.e. the full core field set data-recon already enumerated, not a pre-filtered subset. For XLSX, retain the full workbook row plus `raw_locator` (`relative_path`, `sheet_name`, `physical_row_number`).

## 6. Translation direction & source/domain mapping

Apply the rules in `DIRECTION_AND_DOMAIN_MAPPING_PRECONTRACT_v1.md` §Task 5 exactly (including the `HUMAN_PARALLEL_UNKNOWN` treatment for Legacy). Domain mapping is **not** applied at ingest time in final form — only `domain_raw`/`subdomain_raw` are captured at 01; the canonical `domain` field population is deferred until the mapping table is frozen (post-Raw-EDA), consistent with the 01/02 boundary above — mapping is not a structural-parse concern.

## 7. Duplicate group semantics & exact-duplicate handling candidates

Registry construction computes `duplicate_group_id` (if adopted) but does **not** perform Analysis Representative selection or hard-exclusion at step 01 — that is a `02_normalize_and_qc` decision per SSOT §10.1. Step 01's job is only to make duplicate membership *visible and queryable*, not to resolve it. See the 6 scenario policies in `PAIR_IDENTITY_AND_DUPLICATE_CONTRACT_v1.md` §4 — all remain candidates, none frozen.

## 8. Split provenance

Registry must preserve the **upstream** split label as ingested (`is_validation` boolean, matching data-recon's own manifest field) as raw provenance — this is not the same as the project's own train/hold-out split (§23), which is constructed later and independently, using `GroupKFold(source_id)` or near-duplicate cluster grouping per Leakage Rule LR-01. Do not let the AIHub-provided train/valid split silently become the project's analysis split without applying LR-01 first (given the 15.8% training/validation pair-hash overlap already observed in 025).

## 9. Missing text / schema violation / ingest exclusion vs QC-later

- **Ingest exclusion** (01): record could not be parsed into the D-01 schema at all — e.g. malformed JSON object, unreadable XLSX row, required field structurally absent. Data-recon observed **zero** empty/null/absent `ko`/`en`/`sn`/원문/번역문 across all 23 files, so on current evidence ingest-exclusion volume should be at or near zero — but the registry build must still implement the check, not assume it.
- **QC-later exclusion** (02): record parsed fine but fails a §10.1 hard-exclusion rule (duplicate, anomalous, language-ID failure, etc.) — these records **do** enter the D-01 registry with `pair_quality_status` reflecting their eventual disposition, they are not silently dropped at 01.

## 10. Required row-count reconciliation

At minimum, the registry build must reconcile and report: physical file record counts (from data-recon: 025=2,700,345 unique-content / 026=1,350,162 / Legacy=1,602,418) against registry row counts, and explain any discrepancy (e.g., byte-identical source/label file pairs must not be double-ingested — data-recon's Risk #1 flags exactly this: "원천/라벨링 JSON이 byte-identical이다... 재귀 ingest하면 D025와 D026이 정확히 2배 집계"). A registry build that silently double-counts these would produce a false sense of scale.

## 11. D-01 required fields (per SSOT §12.1, unchanged, restated for traceability)

`pair_id, source_id, source_tier, domain, sentence_type, translation_direction, ko_text_raw, en_text_raw, ko_text_nfc, en_text_nfc, ko_text_analysis, en_text_analysis, pair_quality_status, pair_quality_score, pair_version, source_license_note`

## 12. Proposed auxiliary fields (not in SSOT §12.1 verbatim — flagged as extensions)

`source_record_id`, `raw_locator`, `duplicate_group_id`, `domain_raw`, `subdomain_raw`, `source_raw` (uncoerced raw source label, e.g. preserving "크라우드 소싱" vs "크라우드소싱" distinctly), `is_validation_upstream` (AIHub-provided split flag, distinct from project split), `translation_direction_review_flag`, `mt_field_present` (whether an `mt` staging field existed in the source record, for provenance transparency about the source's own translation pipeline).

These auxiliary fields require Research Director confirmation before being treated as required — see decision queue. None are implemented yet.

## 13. Downstream linkage to D-02/D-03/D-04

`pair_id` is the join key into D-02 (Representation Features), D-03 (Morphology Measurement), D-04 (Token Measurement) — this registry precontract does not change that join-key design, it only fixes what `pair_id` itself means (§4 above, and `PAIR_IDENTITY_AND_DUPLICATE_CONTRACT_v1.md`).
