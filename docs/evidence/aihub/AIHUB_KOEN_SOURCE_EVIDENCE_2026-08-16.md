# AI Hub KO-EN Source Evidence Audit

- Audit date: 2026-08-16 (KST)
- Status: WEB_CONFIRMED only; no local AI Hub archive, schema, or raw-record inspection was performed.
- Scope: official AI Hub dataset pages and official AI Hub access/use materials, with secondary materials excluded from core conclusions.

## Decision question

Which AI Hub KO-EN candidates can serve as a reproducible source for paired Tokenization Premium (TP = T_KO / T_EN), subject to hard gates?

Hard gates:

- H1: deterministic KO-EN pairability
- H2: raw or near-raw text availability
- H3: research-use/acquisition clarity
- H4: stable KO-EN mapping

A web assertion is not a local-data assertion. The required labels are:

- `WEB_CONFIRMED`: stated or directly evidenced by an official web source
- `LOCAL_INSPECTION_REQUIRED`: requires approved archive/schema/record inspection
- `CONFLICT_FOR_RECONCILIATION`: web claim and local report differ

## Official source register

| ID | Official title / document | Official URL | Web-confirmed evidence | Audit status |
|---|---|---|---|---|
| D71265 | AI Hub, `일상생활 및 구어체 한-영 번역 병렬 말뭉치 데이터` | https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71265 | Dataset page identifies Korean text data, a 2021 build / 2022-07 update, translation annotation, and a KO-EN everyday/spoken parallel corpus. The page is an official candidate record. | WEB_CONFIRMED |
| D71266 | AI Hub, `기술과학 분야 한-영 번역 병렬 말뭉치 데이터` | https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71266 | Dataset page states KO-EN 1.5 million sentences, technical/science domains (including AI, big data, IT), JSON labeling format, and neural machine translation as a use case. | WEB_CONFIRMED |
| D87 | AI Hub, `한국어-영어 번역(병렬) 말뭉치` | https://www.aihub.or.kr/aidata/87 | Official catalogue result describes 1.6 million KO-EN translation sentences: 1.1m written (news, government web content, ordinances, Korean culture) and 0.5m spoken. | WEB_CONFIRMED; schema/version unresolved |
| D71693 | AI Hub, `국제 학술대회용 전문분야 한영/영한 통번역 데이터` | https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71693 | Official page describes bidirectional KO-EN/EN-KO professional conference interpretation/translation data and reports 900,572 text sentences plus 2,017 hours of speech. | WEB_CONFIRMED; text schema/version unresolved |
| U1 | AI Hub, `데이터 이용정책` | https://aihub.or.kr/intrcn/guid/usagepolicy.do | AI Hub says downloading AI data requires a separate procedure. | WEB_CONFIRMED |
| U2 | AI Hub, `논문 작성시 주의해야 할 이용정책과 명시 사항` FAQ | https://aihub.or.kr/aihubnews/faq/list.do | Official FAQ says downloaded original files (e.g., JSON/JPG) may not be leaked externally; redistribution of reprocessed data is in principle disallowed absent prior consultation; attribution is required; trained models/services may be distributed and commercially used subject to attribution. It also describes login, application history, and download workflow. | WEB_CONFIRMED |
| U3 | AI Hub, `이용약관` | https://aihub.or.kr/useStplat.do?currMenu=110&topMenu=110 | Official terms identify NIA as the AI Hub operator and define service use conditions/procedures. | WEB_CONFIRMED |

All URLs above were checked on 2026-08-16. Access pages can change; record a download timestamp, archived terms text, archive filename, and SHA-256 when acquisition occurs.

## Gate assessment

### D71265 — everyday/spoken KO-EN parallel corpus

| Gate | Verdict | Evidence boundary |
|---|---|---|
| H1 deterministic pairability | CONDITIONAL PASS | Official title and description explicitly call it a KO-EN parallel translation corpus. Exact row key, one-to-one cardinality, and field names are LOCAL_INSPECTION_REQUIRED. |
| H2 raw/near-raw text | CONDITIONAL PASS | It is an official text/translation dataset with a download page; whether downloaded records expose the exact text fields without irreversible transformations is LOCAL_INSPECTION_REQUIRED. |
| H3 research-use/acquisition clarity | PASS WITH RESTRICTIONS | AI Hub documents application/download procedures and use constraints. This is reproducible acquisition only for eligible users who retain approval/time/version evidence; it is not frictionless public redistribution. |
| H4 stable KO-EN mapping | CONDITIONAL PASS | Parallel-corpus designation supports an intended mapping. Stable pair ID, duplicates, split/merge patterns, and language direction must be verified locally. |

Disposition: **eligible for a provisional scored shortlist**, not yet a frozen primary corpus.

### D71266 — technical/science KO-EN parallel corpus

| Gate | Verdict | Evidence boundary |
|---|---|---|
| H1 deterministic pairability | CONDITIONAL PASS | Official page identifies a KO-EN parallel translation corpus. JSON labeling format is web-confirmed; keys/cardinality are LOCAL_INSPECTION_REQUIRED. |
| H2 raw/near-raw text | CONDITIONAL PASS | Official page identifies text data and JSON labels. Exact source/target text columns and any cleaned variants are LOCAL_INSPECTION_REQUIRED. |
| H3 research-use/acquisition clarity | PASS WITH RESTRICTIONS | Same official AI Hub application/download and non-redistribution framework applies. |
| H4 stable KO-EN mapping | CONDITIONAL PASS | Intended parallel mapping is documented; row-level mapping stability remains LOCAL_INSPECTION_REQUIRED. |

Disposition: **eligible for a provisional scored shortlist**, not a stand-alone population estimate for generic KO-EN.

### D87 — legacy catalogue KO-EN parallel corpus

| Gate | Verdict | Evidence boundary |
|---|---|---|
| H1 | NOT YET PASSED | Aggregate catalogue description establishes a KO-EN resource but not a particular downloadable version/schema/pair key. |
| H2 | NOT YET PASSED | The indexed description does not establish exact raw/near-raw columns. |
| H3 | PASS WITH RESTRICTIONS | AI Hub policy gives general acquisition clarity. |
| H4 | NOT YET PASSED | Stable mapping cannot be asserted from aggregate topic/count description. |

Disposition: **sensitivity-only candidate pending a current official dataset record and local schema audit**. Do not assign a 100-point score yet.

### D71693 — professional conference interpretation/translation corpus

| Gate | Verdict | Evidence boundary |
|---|---|---|\n| H1 | NOT YET PASSED | Bidirectional language-pair existence is web-confirmed, but text-level KO-EN pairing and speech/text relation are unresolved. |
| H2 | NOT YET PASSED | Text scale is reported, but text fields/format are not yet verified. |
| H3 | PASS WITH RESTRICTIONS | AI Hub general acquisition policy applies. |
| H4 | NOT YET PASSED | Mapping stability and translation direction at row level are unresolved. |

Disposition: **sensitivity-only candidate pending schema audit**.

## Provisional 100-point scoring

Scoring is permitted only for D71265 and D71266 because they conditionally clear all four gates from web evidence. Scores are provisional and must be replaced after local inspection. `N/A` candidates did not clear the hard gate and are intentionally unscored.

| Criterion (weight) | D71265 everyday/spoken | D71266 technical/science | Reasoning confined to web evidence |
|---|---:|---:|---|
| M1 Pairability (20) | 16 | 16 | Both are explicitly KO-EN parallel translation corpora; exact keys/cardinality unverified. |
| M2 Translation/semantic provenance (15) | 11 | 11 | Translation annotation/use case is documented; translator workflow and MT/PE provenance unverified. |
| M3 License/reproducible acquisition (15) | 7 | 7 | Official acquisition and usage rules are clear but original-file external release/reprocessed-data redistribution are constrained. |
| M4 Source/domain metadata (15) | 11 | 13 | Everyday/spoken vs technical/science domains are documented; D71266 has explicit technical subdomains. |
| M5 Translation direction (10) | 5 | 5 | KO-EN identity is documented, but each-record source/target direction not verified. |
| M6 Raw-text fidelity (8) | 4 | 5 | Text/translation and D71266 JSON are documented; exact raw and cleaned fields unverified. |
| M7 QC/noise risk (7) | 3 | 3 | No official quality report was inspected in this audit; do not infer low noise. |
| M8 Usable scale (5) | 5 | 5 | D71265 is reported at multi-million total scale; D71266 at 1.5m KO-EN sentences. |
| M9 Domain/length diversity (3) | 3 | 2 | D71265 everyday/spoken scope is a stronger initial diversity complement; both need local length profiling. |
| M10 Version/documentation stability (2) | 1 | 1 | Dataset pages provide build/update context, but archive-version and immutable documentation evidence are absent. |
| **Total (100)** | **77** | **78** | Conditional, web-only scores; not Tier A certification. |

Tie rule outcome: D71266 nominally leads by metadata, but this does not override primary purpose. Pairability/provenance/license have no verified advantage.

## Recommended portfolio

| Portfolio role | Candidate | Rationale | Guardrail |
|---|---|---|---|
| Primary backbone | D71265, conditional on local gate confirmation | Its everyday/spoken scope is the least specialized of currently inspected candidates, so it is the better starting population for a general-language TP analysis. | Do not call it representative of all Korean/English; register domain and direction. |
| Quality anchor | NONE ASSIGNED | No official construction/quality manual was inspected and no local archive audit occurred. | Assign only after identifying a documented QA sample and validating pair mapping/noise. |
| Domain supplement | D71266, conditional on local gate confirmation | It adds technical/science terminology and explicit subdomains. | Analyze as a separate stratum; never pool it silently with D71265. |
| Sensitivity-only | D87 and D71693 | Official descriptions establish candidate relevance but not sufficient downloadable schema/mapping evidence. | Promote only after current official page/version and local schema audit. |

## Required local recon evidence

For every acquired archive, create a non-secret manifest containing: official dataset ID/title; official URL; access date; approval reference; dataset/version/update date; archive filename; byte size; SHA-256; local file list; schema dump; row count; unique pair-ID count; null counts; duplicate and reverse-duplicate counts; exact KO/EN field names; translation-direction distribution; source/domain metadata; text-cleaning variants; and exclusion counts.

Minimum H1/H4 test:

1. Identify a stable record or pair identifier, or construct one from raw source provenance plus fields.
2. Verify every retained row has exactly one selected KO and one selected EN string.
3. Report duplicate KO, duplicate EN, duplicate pair, and one-to-many/many-to-one rates.
4. Preserve source file and original row/record identity after filtering.

Minimum H2 test:

1. Preserve raw extracted strings before normalization.
2. Enumerate raw/cleaned/translated fields and choose one preregistered pair.
3. Measure control characters, Unicode normalization state, markup, PII placeholders, and language mixing.

## Research interpretation boundaries

- A KO-EN translation pair supports a paired token-count observation; it does not establish language-intrinsic AI efficiency.
- UTF-8 bytes, morphology, vocabulary coverage, translation direction, genre, entities, numerals, punctuation, and normalization can all co-vary with TP.
- No claim that higher byte density causes higher token count, or that morphology is the causal source of TP, is supported by this source audit.
- Do not equate output-token differences with reasoning quality.

## Reconciliation rule

If local evidence contradicts any `WEB_CONFIRMED` description, do not overwrite either account. Log `CONFLICT_FOR_RECONCILIATION` with: dataset ID; archive SHA-256; local path held outside Git if restricted; exact field/record evidence; official URL; access dates; and the decision to revise, stratify, or exclude.

## SSOT amendment proposed

Add the following data-source clause to KOEN-TP-RS-001:

> `AI Hub KO-EN` is not a single corpus identifier. Each result must report official dataset ID, title, official page URL, access date, archive SHA-256, selected KO/EN fields, translation direction, normalization policy, filtering rules, final paired N, and acquisition/redistribution constraint. Datasets are separate strata unless a documented composition analysis justifies pooling.

## Next audit actions

1. Obtain the official dataset-specific construction/quality manual for D71265 and D71266.
2. Acquire authorized archives and run the required local gate tests.
3. Freeze a versioned source registry before tokenizer experiments.
4. Assign a quality anchor only after a documented QA audit; do not infer Tier A from AI Hub branding.
