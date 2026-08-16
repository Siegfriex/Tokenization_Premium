# Raw dataset EDA notebook index

Status: `SUPPORTING / EXPLORATORY / PRE-INGESTION EDA / NOT G1 PASS`

이 문서는 실행된 notebook을 찾기 위한 간결한 index다. 상세 표·sample·해석 경계는 각 notebook이 중심 산출물이다.

## A. Dataset notebooks created

| Dataset local ID | Executed notebook | Full-population logical records | Deterministic sample |
|---|---|---:|---:|
| `AIHUB_025` | `notebooks/exploratory/raw/EDA_RAW_AIHUB_025_daily_conversation_parallel.ipynb` | 2,700,345 | 27,115 |
| `AIHUB_026` | `notebooks/exploratory/raw/EDA_RAW_AIHUB_026_tech_science_parallel.ipynb` | 1,350,162 | 13,632 |
| `LOCAL_KO_EN_PARALLEL_XLSX_V1` | `notebooks/exploratory/raw/EDA_RAW_LOCAL_KO_EN_PARALLEL_XLSX_V1_legacy_ko_en_parallel_xlsx.ipynb` | 1,602,418 | 15,966 |

모든 notebook은 `nbformat.validate`를 통과했고 project `tokenization_premium` kernel로 fresh execution됐다. 각 notebook의 7개 code cell은 모두 실행됐고 error output은 0개다.

## B. Dataset/file mapping

| Dataset | Physical files | Unique SHA content | Logical grouping |
|---|---:|---:|---|
| AIHub 025 | 9 | 5 | Train/Valid × EN→KO/KO→EN JSON. Source/label byte aliases와 validation ZIP은 inventory에만 남기고 JSON 내용은 SHA당 한 번 집계 |
| AIHub 026 | 4 | 2 | Train/Valid × KO→EN JSON. Source/label byte aliases는 SHA당 한 번 집계 |
| Legacy XLSX | 10 | 10 | 구어체 2, 대화체 1, 뉴스 4, 한국문화 1, 조례 1, 지자체웹 1 workbook을 한 corpus family로 묶음 |

Dataset별 `*_inventory.csv`가 physical 상대경로, bytes, mtime, SHA-256, split, role, direction, duplicate alias를 보존한다. 세 notebook 모두 audit 중 size/mtime이 변하지 않은 file만 사용했다.

## C. Main raw-distribution findings

### AIHub 025

- 규모: train EN→KO 1,200,307, train KO→EN 1,200,000, valid EN→KO 150,038, valid KO→EN 150,000.
- raw codepoint p50: KO 25–29, EN 50–59. p95: KO 48–55, EN 101–117.
- domain: 해외영업 1,260,367, 일상생활 899,757, 해외고객과의채팅 540,221.
- source: `크라우드 소싱` 1,350,345, `크라우드소싱` 900,195, `SBS` 449,805. 공백 차이를 raw 별도 값으로 유지했다.
- `ner` null rate는 group별 약 95.96%–97.07%다. KO/EN core text의 null/empty는 관측되지 않았다.

### AIHub 026

- 규모: train 1,200,144, valid 150,018; 모두 KO→EN 구조다.
- raw codepoint p50은 KO 77, EN 173; p95는 KO 116, EN 279–280으로 025보다 길다.
- domain top: 세계 449,941, 기술과학 359,910, 경제 270,144.
- source: 한국연구재단 990,252, 특허정보원 359,910.
- `ner` null rate는 train 83.64%, valid 83.57%. KO/EN core text null/empty는 관측되지 않았다.

### Legacy XLSX

- 규모: 뉴스 801,387, 구어체 400,000, 한국문화 100,646, 조례 100,298, 지자체웹 100,087, 대화체 100,000.
- family별 길이 차이가 크다. EN p50은 구어체 51, 대화체 63, 뉴스 174, 한국문화 151, 조례 210, 지자체웹 195다.
- 대화체 대분류 top은 여행/쇼핑 46,524, 비즈니스 28,064, 일상대화 24,012.
- 뉴스 언론사 top은 국민일보 227,538, 서울경제 197,491, 한겨레 117,692.
- 뉴스 `자동분류2` missing/null/empty 31.78%, `자동분류3` 56.62%, URL 11.88%다.

## D. High-value visual findings

1. `aihub_025_02_raw_lengths.png`: direction별 KO/EN 중심과 꼬리 길이 차이, deterministic sample에서의 KO–EN raw-length 관계를 한 화면에서 보여준다.
2. `aihub_025_04_quality_signals.png`: 025의 raw duplicate 후보와 validation→training overlap 후보가 다른 noise signal보다 규모상 중요한 reconciliation 대상임을 보여준다.
3. `aihub_026_02_raw_lengths.png`: train/valid 길이 분포가 거의 겹치며, 025보다 긴 기술과학 문장 구조를 보여준다. 이는 구조 관찰이지 split 동질성 검정이 아니다.
4. `legacy_ko_en_xlsx_03_category_composition.png`: 대화체 대분류, 뉴스 언론사/자동분류, 조례·지자체 source 구성이 서로 다른 schema family임을 빠르게 보여준다.
5. `legacy_ko_en_xlsx_04_quality_signals.png`: 뉴스 metadata 결측과 family별 script/markup 후보 위치를 분리한다.

각 figure는 제목, 축 단위, full-population/sample 범위를 명시하며 2266–2268 × 1517 px PNG로 저장됐다.

## E. Data quality risks

- AIHub 025: raw KO+EN hash duplicate 후보 214,252행, validation row 중 training pair hash overlap 후보 47,385행.
- AIHub 026: duplicate 후보 44행, validation→training overlap 후보 9행.
- Legacy: corpus family 전체 pair duplicate 후보 2,494행.
- Hash 수치는 raw BLAKE2b-64 후보이며 collision 가능성이 있어 확정 duplicate 판정이 아니다.
- AIHub 026 EN에는 zero-width signal이 train 6,688행, valid 840행 관측됐다.
- Legacy 뉴스 `자동분류2/3`와 URL은 metadata coverage가 낮다.
- KO field의 Latin script, EN field의 Hangul, HTML-like pattern은 관측 신호다. 고유명사·인용·표현일 수 있으므로 자동 오류나 삭제 근거가 아니다.
- Legacy 대화체에는 `SID`/`ID`가 없다. deterministic ingest key 정책이 별도로 필요하다.

## F. Cross-dataset structural differences

| Axis | AIHub 025 | AIHub 026 | Legacy XLSX |
|---|---|---|---|
| Direction | EN→KO와 KO→EN 모두 | KO→EN | `원문`/`번역문` field pair; 공식 translation workflow UNKNOWN |
| Style/domain | 구어체, 3개 상위 domain | 문어체 기술과학, 5개 상위 domain | 구어·대화·뉴스·문화·조례·지자체 혼합 |
| Typical length | 짧은 문장 | 긴 기술/과학 문장 | family별 편차가 매우 큼 |
| Metadata | domain/subdomain/source/style/license/MT/original | 025와 유사 | workbook마다 category schema가 다름 |
| Split | train/validation | train/validation | local files에 canonical split 없음 |
| Main reconciliation | physical alias와 split overlap | zero-width와 소수 overlap | provenance, key namespace, metadata heterogeneity |

이 차이는 `STRUCTURAL DATA CHARACTERISTIC`이며 corpus 우열이나 primary 적합성 주장이 아니다.

## G. Things requiring AIHub Recon evidence

- 이 notebook별 SHA snapshot과 독립 Recon manifest의 file inventory/hash가 같은 raw snapshot인지 대조.
- AIHub 025 ZIP member와 extracted/label JSON의 byte equality 및 physical alias 처리 원칙 확인.
- 공식 dataset ID, release version, 배포 completeness, train/validation split provenance.
- `sn`, `SID`, `ID`의 공식 uniqueness scope와 legacy 대화체 key 정의.
- JSON `ner`, `mt`, original/final field의 공식 schema 의미.
- raw metadata `license=open`과 실제 라이선스 문서의 일치 여부.

## H. Things requiring Claude research decision

- 025, 026, legacy 중 어떤 corpus를 primary/candidate/excluded로 둘지.
- 025의 양방향 file을 별도 strata로 유지할지, 같은 KO–EN pair space에서 reconciliation할지.
- 025 validation→training overlap 후보를 split 정책상 어떻게 처리할지.
- Legacy family를 하나의 dataset으로 유지할지, 뉴스/조례/대화체 등으로 분리할지.
- Legacy 대화체 deterministic pair key와 workbook-scoped ID namespace 정책.
- zero-width/markup/script mixing에 대한 향후 normalization/QC 정책. 이 EDA는 저장·수정하지 않았다.

## I. Notebook artifact paths

```text
notebooks/exploratory/raw/EDA_RAW_AIHUB_025_daily_conversation_parallel.ipynb
notebooks/exploratory/raw/EDA_RAW_AIHUB_026_tech_science_parallel.ipynb
notebooks/exploratory/raw/EDA_RAW_LOCAL_KO_EN_PARALLEL_XLSX_V1_legacy_ko_en_parallel_xlsx.ipynb

outputs/eda_raw/aihub_025/**
outputs/eda_raw/aihub_026/**
outputs/eda_raw/legacy_ko_en_xlsx/**
outputs/figures/eda_raw/aihub_025/**
outputs/figures/eda_raw/aihub_026/**
outputs/figures/eda_raw/legacy_ko_en_xlsx/**
outputs/eda_raw/support/raw_eda_framework.py
outputs/eda_raw/support/create_raw_eda_notebooks.py
```

Dataset별 output에는 inventory, record counts, schema coverage, raw length summary, category counts, noise summary, duplicate signals, deterministic sample, profile summary JSON이 있다.

## J. Git commits / remote push evidence

| Dataset scope | Commit | Push observation |
|---|---|---|
| AIHub 025 + shared EDA framework | `9c67e80` | new `origin/eda/g0-raw-notebooks` branch created and upstream set |
| AIHub 026 | `bb15950` | `9c67e80..bb15950` pushed |
| Legacy XLSX | `46a6670` | `bb15950..46a6670` pushed |

각 commit 전에 cached path가 `notebooks/exploratory/raw/**`, `outputs/eda_raw/**`, `outputs/figures/eda_raw/**`, `outputs/reports/eda_raw/**`에만 속하는지 검사했다. `data/raw/**`는 stage하지 않았다.

## Claim boundary

수행하지 않은 작업: o200k tokenization, Tokenization Premium/logTP/CompressionPenalty, morphology, normalization 저장, pair registry/cohort 생성, signed-rank/bootstrap/M0–M3, causal explanation, final QC acceptance.
