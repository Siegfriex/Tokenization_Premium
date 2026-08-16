# P2 Schema Contract Field Matrix v001

Status: ENGINEERING REMEDIATION MAP — research semantics unchanged
Baseline: `impl/p2-canonical-run-codex@a4704fa40ee3a8cc85024e3f053f615d6e0174e8`
Research authority: `research/p2-qc-claude@b9990afbf3fc0ed2a5e80fb4def1565e9ba3ebf4`

This matrix is the implementation trace from the frozen research contract to executable evidence. It does not add a QC rule, threshold, model, or estimand.

## Contract chain

| Research contract rule | Python constant/helper | SQL expression/alias | Output field | Validation | Report field | Regression test |
|---|---|---|---|---|---|---|
| NFC → edge BOM strip → outer trim | `NORMALIZATION_OPERATIONS`, `normalize_ssot_text` | `nfc_normalize`, `trim(trim(..., chr(65279)))` | `ko_text_nfc`, `en_text_nfc`, `ko_text_analysis`, `en_text_analysis`, `normalization_rule_version`, `normalization_ops` | required schema; non-null; raw-column immutability | execution report `normalization` | normalization unit cases; synthetic execution E2E |
| Empty analysis text is a structural flag | `derive_pair_quality_status` | `__ko_analysis = '' OR __en_analysis = '' AS __empty` | `empty_text_flag` | required bool; non-null | `QC_FLOW_v001.csv:empty_text_flag` | unit flag cases; synthetic execution E2E |
| Decode integrity is Unicode-only | `decode_integrity_ok` | U+FFFD check as `__decode` | `decode_integrity_flag` | required bool; non-null | `QC_FLOW_v001.csv:decode_integrity_flag` | Unicode unit cases; synthetic execution E2E |
| Markup ratio `> 0.5` | frozen SQL parameter | markup match length ratio as `__markup` | `markup_dominant_flag` | required bool; non-null | `QC_FLOW_v001.csv:markup_dominant_flag` | synthetic execution E2E |
| Control/zero-width ratio `> 0.05` | frozen SQL parameter | control and zero-width ratio as `__control` | `control_char_excess_flag` | required bool; non-null | `QC_FLOW_v001.csv:control_char_excess_flag` | synthetic execution E2E |
| `exact_duplicate_flag = pair_id != analysis_representative_pair_id` | `EXACT_DUPLICATE_IDENTITY_SCOPE`, `select_analysis_representative_pair_id` | `pair_id <> __analysis_rep AS __exact_duplicate` | `exact_duplicate_flag` | required bool; non-null; full-population equality with `pair_id <> analysis_representative_pair_id` | `QC_FLOW_v001.csv:exact_duplicate_flag`; execution report duplicate disposition | survivor unit cases; schema/invariant/E2E tests |
| Advisory Unicode anomaly | `normalize_ssot_text` anomaly result | `__unicode_anomaly` | `unicode_anomaly_flag` | required bool; non-null | `QC_FLOW_v001.csv:unicode_anomaly_flag` | unit cases; synthetic execution E2E |
| Length quintile review only | frozen `ntile(5)` SQL | `__length_quintile` | `short_text_flag`, `long_text_flag`, `length_stratum` | required type; non-null | QC flag counts and sampling-frame stratum | synthetic execution E2E |
| Digit and punctuation ratio `> 0.20` | frozen SQL parameter | `__high_digit`, `__high_punct` | `high_digit_ratio_flag`, `high_punctuation_ratio_flag` | required bool; non-null | corresponding QC flow metrics | synthetic execution E2E |
| Script mix `>= 0.10` on both scripts | frozen SQL parameter | `__script_mix` | `script_mix_flag` | required bool; non-null | `QC_FLOW_v001.csv:script_mix_flag` | synthetic execution E2E |
| Language-side smoke is review-only | `LANGUAGE_MIN_EVIDENCE`, `LANGUAGE_SUBSTANTIAL_EVIDENCE`, `language_side_anomaly_review` | `__ko_side_reason`, `__en_side_reason` | `lang_side_anomaly_review_flag`, `lang_side_anomaly_reason`, `ko_lang_side_anomaly_reason`, `en_lang_side_anomaly_reason` | required field types; non-null for side reasons and flag | `QC_FLOW_v001.csv:lang_side_anomaly_review_flag`; `LID_QC_PASS_RATE_v001.csv` | language-side unit cases; synthetic execution E2E |
| Manual translation review is not fabricated | nullable manual-audit interface | `NULL::BOOLEAN` | `translation_quality_review_flag` | required nullable bool field | no automatic count gate | manual-interface unit test; schema E2E |
| NER is deferred | `named_entity_deferred_fields` | `NULL::BOOLEAN`, `'DEFERRED'` | `named_entity_heavy_flag`, `named_entity_evaluation_status` | nullable bool plus non-null status | execution/report metadata only | deferred-field unit test; schema E2E |
| Structural rejection priority is empty → decode → markup → control → exact duplicate | `derive_pair_quality_status` | `__primary_rejection_reason`, `__pair_quality_status` | `primary_rejection_reason`, `secondary_rejection_flags`, `pair_quality_status` | required types; status and JSON string invariants | QC accepted/rejected counts and execution report | unit status cases; synthetic execution E2E |
| D-01 provenance representative remains unchanged; P2 survivor is separate | `select_analysis_representative_pair_id` | cohort-aware window `__analysis_rep` | `representative_pair_id` unchanged; `analysis_representative_pair_id`, `duplicate_disposition`, `analysis_eligible_exact_dedup` | non-null and exact-duplicate equality invariant | exact-unique/final-analysis denominators; sampling frame | survivor unit cases; synthetic execution E2E |
| Successful completion manifest is the canonical-evidence gate | completion-manifest validator | not a QC SQL expression | canonical v002 plus `QC_MANIFEST_v001.json` | manifest status, artifact path/hash/rows/schema, report hashes | completion manifest and execution report | missing/invalid manifest rejection; full-path E2E |

## Single executable field contract

The remediation defines one Python field-spec collection from which all of the following are derived:

- complete ordered `P2_OUTPUT_SCHEMA` (the 44 D-01 fields plus P2 materialized fields);
- physical Parquet type and nullability checks;
- logically required non-null fields;
- aggregate boolean count fields used by `QC_FLOW_v001.csv`.

Physical Parquet nullability and logical null admissibility are distinct. DuckDB `COPY` records projected fields as physically nullable; contract-required non-null behavior is therefore enforced by full-population SQL invariants in addition to Arrow schema metadata checks.

## INC-004 baseline drift

| Link | Baseline observation | Required remediation |
|---|---|---|
| SQL → output | `__exact_duplicate` was computed but not projected | materialize `__exact_duplicate AS exact_duplicate_flag` |
| Output → validation | validation checked selected values but not the complete schema | validate ordered fields, Arrow types/nullability, required non-null fields, and duplicate equality |
| Output → report | report referenced an independently maintained literal `exact_duplicate_flag` | derive aggregate flag names from the field contract |
| Contract type → output type | `secondary_rejection_flags` was emitted as Arrow JSON extension although the contract says string | cast canonical JSON array to `VARCHAR` |
| Candidate → canonical | v002 was promoted before reports bound successfully | validate/hash/report against candidate and promote only after report validation |
| Canonical → evidence | canonical filename alone could be mistaken for completion | require a successful completion manifest and verify artifact/report hashes |
| Tests → executable chain | unit/static tests did not execute population SQL through reports and manifest | add a synthetic D-01 full-path regression test |

## Prohibited scope

This remediation does not add Lingua, fastText, semantic similarity, NER inference, morphology, tokenization, row-wise Python transformation, Polars, a separate SQL pipeline, or a framework/SQL-engine replacement. It does not change thresholds, cohort eligibility, duplicate identity, or survivor semantics.
