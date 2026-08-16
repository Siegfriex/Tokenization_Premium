# Phase 2 — `02_normalize_and_qc.ipynb` Precontract v1

**Status: CONTRACT DESIGN ONLY.** `CR-003`(`research/g1-gate-claude@566f30b`)는 **아직 승인되지 않았다**(2026-08-16 17:32 KST 시점 최신 결정로그 `2026-08-16_1732_KOEN_TP_ENG_OBS_001_PROGRESS_HEARTBEAT_CONTRACT.md` §15 확인: "CR-003 remains a Director decision before formal G1 closure"). 이 문서는 **계약 설계까지만** 수행하며, Phase 2의 **공식 실행 권한을 전제하지 않는다.** Notebook 구현 없음, 565만 행 전체 실행 없음.

**Branch:** `research/p2-qc-claude` (from `origin/integration/g1@526a14c`, Wave 3C — DuckDB runtime-safety까지 통합됨)
**Author:** Claude, Research/Data/Statistics Orchestrator
**Depends on:** [[project-d01-independent-audit-v001]], `docs/contracts/G1_PAIR_REGISTRY_PRECONTRACT_v1.md`, `configs/research_v1.yaml`, `docs/research/CR-003_G1_GATE_SEQUENCE_CLARIFICATION_PROPOSAL.md`, `2026-08-16_1701_KOEN_TP_PRINTED_SSOT_REDLINE_AND_G1_TRAFFIC_CONTROL.md`, `2026-08-16_1732_KOEN_TP_ENG_OBS_001_PROGRESS_HEARTBEAT_CONTRACT.md` (ENG-OBS-001)

---

## 0. Purpose and scope boundary

Canonical notebook: `02_normalize_and_qc.ipynb`.

```
D-01 raw registry (PAIR_REGISTRY_v001.parquet, 5,652,925 rows, 44 cols)
  → deterministic normalization (raw → nfc → analysis)
  → QC flag computation (hard-exclusion candidates + soft flags, all independent)
  → exact-dedup disposition (representative vs non-representative, no deletion)
  → LID scan
  → accepted/review/rejected disposition + primary_rejection_reason
  → aggregate LID/QC pass-rate reporting
  → G1 closure evidence (partial — see §10)
```

**Explicitly out of scope for this notebook** (belongs to later Phase per §37):
- Token-premium computation, `TP_i`/`logTP_i`, exact decomposition (D-04, Phase 4/5)
- Morphology measurement (D-03, Phase 4, Kiwi)
- Any explanatory/predictive model (M0-M3, Phase 5)
- Regex chunk measurement (D-05)

## 1. SSOT-first audit — classification

Every Phase-2 rule below is classified. `IMPLEMENTATION_CHOICE_REQUIRED` items are never silently resolved here — they are escalated in `docs/research/P2_QC_DECISION_QUEUE_v1.md`.

| Rule | SSOT ref | Classification |
|---|---|---|
| `*_text_raw` immutable, never overwritten | §11 (원문은 절대 덮어쓰지 않는다) | SSOT_EXPLICIT |
| `*_text_nfc` = NFC only | §11.1 | SSOT_EXPLICIT |
| `*_text_analysis` = NFC + BOM 제거 + 외곽 whitespace trim, 내부 whitespace 보존 | §11.1 | SSOT_EXPLICIT |
| Forbidden silent ops (NFKC, lowercasing, whitespace collapse, 치환, 조사/어미 분리 등) | §11.2 | SSOT_EXPLICIT |
| 7 hard-exclusion categories | §10.1 | SSOT_EXPLICIT (existence of the 7 categories); exact per-category **threshold/algorithm** = mostly IMPLEMENTATION_CHOICE_REQUIRED (see §3) |
| 8 soft flags (existence) | §10.2 | SSOT_EXPLICIT |
| `high_digit_ratio_flag`/`high_punctuation_ratio_flag` threshold = `>0.20` | D-RD-01 (AMB-08) | DIRECTOR_APPROVED_EXTENSION — frozen, do not reopen |
| `short_text_flag`/`long_text_flag` threshold | §10.2 (flag exists), no number given | IMPLEMENTATION_CHOICE_REQUIRED |
| `script_mix_flag` definition | §10.2 (flag exists), no rule given | IMPLEMENTATION_CHOICE_REQUIRED |
| `named_entity_heavy_flag` definition | §10.2 (flag exists), no rule given | IMPLEMENTATION_CHOICE_REQUIRED |
| `unicode_anomaly_flag` scope (제어문자·zero-width·비정상 결합문자) | §11.1 | SSOT_EXPLICIT scope; exact regex/threshold = IMPLEMENTATION_CHOICE_REQUIRED |
| Semantic QC 3-step (source metadata → auto similarity → manual audit) | §10.3 | SSOT_EXPLICIT |
| Manual audit N | §9.1 (300-500) → **500 고정** | DIRECTOR_APPROVED_EXTENSION (D-RD-01, AMB-06 resolved) — do not reopen |
| Audit rubric 2/1/0 | §10.3 | SSOT_EXPLICIT |
| Automated similarity score must not gate primary outcome (T-01) | §10.3, §32 T-01 | SSOT_EXPLICIT |
| **Whether manual-audit result gates individual-row `pair_quality_status`, or only validates the rule-based disposition's calibration** | §10.3 (실제로는 명시되지 않음 — `configs/research_v1.yaml`의 `pair_qc.semantic_qc`도 이 질문을 해결하지 않음, 직접 확인함) | **IMPLEMENTATION_CHOICE_REQUIRED — 이번 세션에서 발견한 가장 중요한 미해결 지점, §3/§7 참조** |
| LID method | §10.1 ("언어 식별이 명백히 잘못된") | IMPLEMENTATION_CHOICE_REQUIRED — method itself, see §5 |
| Duplicate representative = provenance pointer only, no semantic covariate inheritance | D-01 precontract §7 (Vice Director correction), already implemented in D-01 | SSOT_EXPLICIT (carried from G1 contract, not re-litigated) |
| domain/source_id/source_provenance_raw group-conflict **resolution to a value** | D-01 precontract §7 ("follow-on design question, not answered here") | Still **UNRESOLVED** — Phase 2 must not invent a resolution; conflict flags only |
| Leakage Rule LR-01 (text hash / near-dup cluster as split group key) | §23 | SSOT_EXPLICIT — **not implemented here** (split belongs to Phase 5); Phase 2 only guarantees `duplicate_group_id` remains the correct group key for later use |
| Tokenizer roundtrip existence check at QC gate | §10.1, §25.4 | SSOT_EXPLICIT (existence); scope kept minimal, see §8 |
| Reproducibility fields (`normalization_rule_version`, `normalization_ops`) | §11.1 | SSOT_EXPLICIT — **new columns, not present in `PAIR_REGISTRY_v001`'s 44-column schema**, must be added in v002 |
| `execution_code_commit`/`artifact_record_commit` manifest fields | Redline §30.2 (2026-08-16 17:01 log) | DIRECTOR_APPROVED_EXTENSION (operational clarification, already used by D-01 manifest) |
| ENG-OBS-001 heartbeat on all >30s stages | ENG-OBS-001 (2026-08-16 17:32 log) | DIRECTOR_APPROVED_EXTENSION — mandatory, applies prospectively |

## 2. Normalization contract (frozen)

Three columns per language, computed in this exact order, from `ko_text_raw`/`en_text_raw` (D-01, immutable):

```python
import unicodedata

def to_nfc(raw: str) -> str:
    return unicodedata.normalize("NFC", raw)

_BOM = "﻿"

def to_analysis(raw: str) -> str:
    step1 = unicodedata.normalize("NFC", raw)          # 1. NFC
    step2 = step1.strip(_BOM)                          # 2. BOM 제거 (edges only, repeats via str.strip's multi-char strip semantics)
    step3 = step2.strip()                               # 3. 외곽 whitespace trim (Python str.isspace() 기준, 내부는 미변경)
    return step3
```

- `ko_text_nfc`/`en_text_nfc` = `to_nfc(ko_text_raw)`/`to_nfc(en_text_raw)` — NFC 외 어떠한 변형도 없음.
- `ko_text_analysis`/`en_text_analysis` = `to_analysis(ko_text_raw)`/`to_analysis(en_text_raw)`.
- `normalization_rule_version` = 문자열 상수 (예: `"p2_norm_v001"`) — 규칙 자체가 바뀌면만 증가.
- `normalization_ops` = 실제 적용한 op 이름의 canonical JSON 배열, 예: `["NFC","BOM_STRIP","OUTER_TRIM"]` (모든 row 동일 — 이번 계약에서는 조건부 op 없음).
- `unicode_anomaly_flag` = `ko_text_raw` 또는 `en_text_raw`에 제어문자(`Cc` 카테고리, tab/newline 제외) 또는 비정상 zero-width(`​`,`‌`,`‍`,`﻿` 등 시각적으로 안 보이는 문자로 outer-trim 이후에도 텍스트 **내부**에 남아있는 경우) 또는 비정상 결합문자(orphan combining mark, 즉 앞에 결합 대상 base character가 없는 combining diacritic)가 존재하면 true.

**금지 (§11.2, primary analysis text에 적용 금지):**

| 금지 항목 | 비고 |
|---|---|
| 내부 whitespace collapse | `to_analysis`는 outer만 trim, 내부 whitespace run은 원문 그대로 |
| punctuation ASCII 치환 | 예: `、`→`,` 금지 |
| lowercasing | `.lower()` 호출 금지 |
| full-width/half-width 통합 | `Ａ`→`A` 변환 금지 (이는 사실 NFKC의 일부이므로 NFKC 금지와 사실상 동일 사항) |
| NFKC 변환 | `unicodedata.normalize("NFKC", ...)` 호출 금지 |
| 숫자 치환 | `１`→`1` 등 금지 |
| emoji 제거 | 필터링 금지 |
| 조사/어미 분리 | 형태소 분석 결과를 analysis text에 반영 금지 — 그것은 D-03/Phase 4의 일 |

NFKC/whitespace-collapse/raw-text 기준 결과는 **별도 sensitivity track에서만** 허용(§11.2, §24 항목 1-2) — 이번 계약이 만드는 컬럼이 아니라, 그 결과가 필요할 때 별도 파생 컬럼/아티팩트로 생성해야 하며 이번 v002 스키마에는 포함하지 않는다.

### Tests (unit, deterministic, no 5.65M row execution)

- `test_nfc_idempotent` — `to_nfc(to_nfc(x)) == to_nfc(x)`
- `test_analysis_preserves_internal_whitespace` — `to_analysis("a   b") == "a   b"` (3-space internal run intact)
- `test_analysis_strips_bom_and_outer_whitespace_only` — `to_analysis("﻿  텍스트  ﻿") == "텍스트"`, internal 문자는 불변
- `test_analysis_does_not_apply_nfkc` — fullwidth 입력(`"Ａ１"`)이 `to_analysis` 이후에도 fullwidth로 유지 (halfwidth `"A1"`로 변환되지 않음)
- `test_analysis_does_not_lowercase` — 대소문자 혼합 문자열이 그대로 보존
- `test_analysis_does_not_touch_josa_eomi` — 한국어 조사/어미가 포함된 문자열이 형태소 경계로 분리되지 않고 원문 그대로 (문자열 단위 비교만, 형태소 분석 호출 자체가 없음을 코드 경로로 확인)
- `test_raw_column_never_mutated` — `to_nfc`/`to_analysis` 실행 후에도 원본 `ko_text_raw`/`en_text_raw` 참조가 동일 객체/동일 값

## 3. QC flags — compute-first, dispose-second architecture

**모든 flag를 독립적으로 먼저 계산**하고, disposition은 그 다음 단계에서 유도한다 (flag 계산 순서가 count에 영향을 주지 않도록).

### 3a. Hard-exclusion candidate flags (7, §10.1 순서 그대로, 모두 boolean, 모두 독립 계산)

| Flag | 정의 | 분류 |
|---|---|---|
| `empty_text_flag` | `ko_text_analysis`/`en_text_analysis` 정규화 후 빈 문자열(`""`) — D-01 ingest 시점엔 비어있지 않았어도, BOM/outer-whitespace만으로 구성된 raw text는 analysis 단계에서 빈 문자열이 될 수 있음(실측 필요, 가정 금지) | SSOT_EXPLICIT existence, 재계산 필요성은 엔지니어링 판단 |
| `exact_duplicate_flag` | D-01 `duplicate_group_id` 기준, `pair_id != representative_pair_id`인 row = true | SSOT_EXPLICIT + 이미 D-01에 존재하는 컬럼을 재사용 |
| `lid_failure_flag` | §5 참조 | IMPLEMENTATION_CHOICE_REQUIRED |
| `markup_dominant_flag` | HTML 태그/URL/코드 패턴이 텍스트의 **다수**를 차지 — 정확한 비율 threshold 미지정 | IMPLEMENTATION_CHOICE_REQUIRED (제안: 태그/URL 패턴 문자 수 ÷ 전체 문자 수 `> 0.5`, Director 확인 필요 — §P2_QC_DECISION_QUEUE_v1 Q1) |
| `control_char_excess_flag` | 제어문자/zero-width 문자 비율이 "비정상적으로 과다" — 정확한 threshold 미지정 | IMPLEMENTATION_CHOICE_REQUIRED (제안: 해당 문자 수 ÷ 전체 codepoint 수 `> 0.05`, Director 확인 필요 — Decision Queue Q2) |
| `roundtrip_failure_flag` | §8 참조 | SSOT_EXPLICIT existence, minimal-scope 구현은 §8 |
| `semantic_qc_fail_flag` | §7 참조 — 자동/수동 audit에서 명백히 실패 | §3b/§7에서 상세 |

### 3b. Soft flags (8, §10.2)

| Flag | 정의/threshold | 상태 |
|---|---|---|
| `short_text_flag` | length_stratum 최하위 분위 또는 절대 threshold | IMPLEMENTATION_CHOICE_REQUIRED (Decision Queue Q3) |
| `long_text_flag` | 위와 대칭 | IMPLEMENTATION_CHOICE_REQUIRED (Decision Queue Q3) |
| `high_digit_ratio_flag` | 숫자 codepoint 비율 `> 0.20` | **DIRECTOR_APPROVED_EXTENSION, 이미 고정(D-RD-01) — 재논의 안 함** |
| `high_punctuation_ratio_flag` | 구두점 codepoint 비율 `> 0.20` | **DIRECTOR_APPROVED_EXTENSION, 이미 고정(D-RD-01) — 재논의 안 함** |
| `script_mix_flag` | 한 필드 내 Hangul+Latin이 모두 유의미 비율로 존재 | IMPLEMENTATION_CHOICE_REQUIRED (Decision Queue Q4) — D-02(§12.2 Representation Features)의 정식 script 분해와는 별개의 QC-scope-only 경량 boolean이어야 함(Phase 3 산출물을 조기 생성하지 않기 위함) |
| `unicode_anomaly_flag` | §2 정의 재사용 | SSOT_EXPLICIT (scope), threshold는 §2와 동일 규칙 |
| `translation_quality_review_flag` | 자동 유사도 score가 애매 구간(예: 사전 threshold 미만이지만 hard-fail은 아님) 이거나 수동 audit에서 review 판정 — D-01의 `translation_direction_review_flag`(방향 애매성)와는 **다른 필드**, 혼동 금지 | IMPLEMENTATION_CHOICE_REQUIRED, §7과 연동 |
| `named_entity_heavy_flag` | 고유명사/개체명 비율이 높음 | IMPLEMENTATION_CHOICE_REQUIRED (Decision Queue Q5) — NER 모델 도입은 LID와 동일한 과잉 엔지니어링 위험, proxy heuristic 제안 필요 |

### 3c. Disposition (두 번째 단계에서만 유도, flag 계산에 영향 없음)

```
primary_rejection_reason (deterministic priority, REPORTING ONLY — 다른 동시발생 flag를 숨기지 않음):
  1. empty_text_flag
  2. roundtrip_failure_flag
  3. lid_failure_flag
  4. markup_dominant_flag
  5. control_char_excess_flag
  6. semantic_qc_fail_flag
  7. exact_duplicate_flag   (마지막 — 중복은 구조적 오류보다 후순위로 보고)

secondary_rejection_flags = 위 7개 중 primary로 선택되지 않은 나머지 true flag 전체 (배열, 정보 손실 없음)

pair_quality_status:
  rejected  ⟺ 위 7개 hard-exclusion flag 중 하나 이상 true
  review    ⟺ hard-exclusion 없음, 그러나 §7 semantic QC의 최종 disposition 규칙이 아직 미확정 (아래 참조)
  accepted  ⟺ §7 참조 — **이 변환 규칙 자체가 Decision Queue의 최상위 항목**
```

**이 문서가 침묵하지 않는 지점**: SSOT §10.3은 수동 audit을 요구하지만 500쌍 표본으로는 565만 행 전체에 개별 disposition을 줄 수 없다. 두 가지 해석이 가능하며 **어느 쪽도 이 문서에서 결정하지 않는다** (§7, Decision Queue Q0 참조):
- **해석 (a) — 제안**: `accepted`는 순수 규칙 기반(hard-exclusion 전무)으로 전체 population에 부여하고, 500쌍 수동 audit은 이 규칙 기반 disposition이 방향적으로 타당한지 **검증(calibration)**하는 별도 population-level statistic으로만 사용한다. 자동 유사도 score는 `pair_quality_score`에 전량 저장하되 disposition을 gate하지 않는다(T-01 그대로 준수).
- **해석 (b)**: 수동 audit 대상 500쌍만 `accepted`/`rejected` 확정, 나머지는 `review`로 영구 유지(비실용적 — 대부분의 row가 영원히 `review`로 남음).

## 4. Exact duplicate disposition

- D-01이 이미 계산: `duplicate_group_id`(content identity, raw KO+EN), `representative_pair_id`(=min(pair_id) in group, provenance pointer only), `direction_conflict_flag`/`domain_conflict_flag`/`source_id_conflict_flag`/`source_provenance_raw_conflict_flag`.
- Phase 2는 **row를 삭제하지 않는다** — v002는 v001과 동일하게 5,652,925 rows.
- 신규 컬럼 `duplicate_disposition` ∈ `{REPRESENTATIVE, NON_REPRESENTATIVE_DUPLICATE}` (= `pair_id == representative_pair_id` 여부의 가독형 표현, `exact_duplicate_flag`의 역).
- 신규 컬럼 `analysis_eligible_exact_dedup` (boolean) = `duplicate_disposition == REPRESENTATIVE`. 이후 분석은 이 컬럼으로 필터링하되, **원본 row는 registry에 남는다.**
- Mixed-direction group: D-01이 이미 group-resolve했으므로 Phase 2는 **그대로 상속**한다 — 재계산 금지.
- Domain/source conflict flag: D-01 값 그대로 상속. **값으로 resolve하지 않는다** — D-01 precontract §7이 "follow-on design question, not answered here"라고 명시한 것을 이번에도 재확인하며, Phase 2 역시 이 질문에 답하지 않는다(향후 Phase 5 모델링 단계의 결정 사항으로 이월).
- Analysis-level semantic covariate: `translation_direction`은 D-01에서 이미 group-resolved 값 그대로 사용. `domain`/`source_id`/`source_provenance_raw`는 row-level raw 값 그대로 사용하며 conflict flag로만 경고.
- LR-01(§23) 연결: `duplicate_group_id`가 이미 "동일 원문에서 파생된 near-duplicate cluster"의 group key 역할을 하므로, Phase 5의 실제 train/test split은 이 컬럼을 group key로 재사용할 수 있다 — **split 자체는 Phase 2 범위 밖**이며 여기서 구현하지 않는다.

## 5. LID — option comparison and recommendation

**중요한 재구성**: SSOT §10.1의 요구는 "언어 식별이 **명백히** 잘못된 pair"다. 이는 open-set language identification이 아니라, **이미 스키마가 ko_text/en_text로 확정된 컬럼이 실제로 기대한 스크립트를 담고 있는지**를 검증하는 닫힌 집합(closed-set) 스키마 정합성 문제다 — 이 재구성이 아래 권고의 핵심 근거다.

| | A. Unicode/script-rule | B. 경량 통계 LID (예: py3langid) | C. Pretrained neural LID |
|---|---|---|---|
| 정의 | 문자 카테고리(Hangul U+AC00-D7A3 vs Latin) 비율 계산 | n-gram/문자빈도 통계 분류기 | transformer 기반 다국어 분류기 |
| False positive 위험 | 낮음(닫힌 집합 문제에 적합) — 단, 외래어/고유명사 원어 표기가 있는 정상 pair를 과다플래그할 위험 존재 | 중간 — 짧은 텍스트/코드스위칭/전문용어에서 오류 증가 | 낮음(개방형 문제 기준)이나 이 프로젝트엔 과잉스펙 |
| KO/EN 혼합 스크립트 처리 | 비율 기반이라 혼합 정도를 그대로 노출(투명) | 확률 점수로 애매함을 표현하나 불투명 | 가장 정교하나 여전히 근본적으로 애매한 case는 애매함 |
| 숫자/구두점 처리 | 분모에서 명시적으로 제외 가능(투명) | 모델 의존적, 불투명 | 모델 자체 tokenizer가 흡수, 불투명 |
| 565만 행 기준 runtime | O(n) codepoint 분류, 수 초~1분대 | 배치 처리 시 수 분~수십 분대 | CPU-bound 시 시간 단위, 이 프로젝트는 GPU 서빙이 Track B 제약으로 이미 비가용(메모리 기록: RTX 5070 12GB) |
| 재현성 | 완전 결정적, 모델 파일 없음 | 모델 hash 고정 필요(kiwipiepy 패턴 재사용 가능하나 추가 부담) | 모델 weight 고정+환경 고정 필요, 무거움 |
| 의존성 영향 | 0 (stdlib `unicodedata`만) | 신규 패키지 + 번들 모델 파일, license 확인 필요 | 신규 ML 스택, 대용량 weight, license/재배포 검토 — Track B와 동일한 과잉엔지니어링 위험 |

**권고: A(Unicode/script-rule)를 1차 규칙으로 채택.** 근거: (1) 문제 자체가 닫힌 집합 스키마 검증이지 개방형 LID가 아님, (2) 완전 결정적·의존성 0·감사 가능, (3) 프로젝트가 이미 Track B에서 동일한 논리로 무거운 모델 도입을 유보한 전례(D-RD-03/CR-002)와 일관됨.

**Sensitivity/audit 병행 (권고, 강제 아님)**: 500쌍 수동 semantic QC 표본과 동일하거나 겹치는 strata에서 경량 통계 LID(B)를 **감사 전용**으로 1회 실행해 rule-based flag의 false-negative rate를 교차검증. 전체 565만 행 게이팅에는 사용하지 않는다.

**Director 결정 필요 (estimand에 실질적 영향)**: 정확한 threshold(예: "target script 비율 < 0.5면 실패"의 "0.5") 자체는 SSOT 수치가 아니므로 Decision Queue Q6으로 이관. LID 방식 선택(A) 자체는 이 문서의 권고이나, threshold 숫자는 Director 승인 전까지 확정되지 않는다.

## 6. QC pass-rate denominators (4종, 절대 단일 "pass rate" 보고 금지)

```
RAW_RECORD_DENOMINATOR
  = 5,652,925   (D-01 전체 structurally-ingested rows, 025+026+LEGACY)

EXACT_UNIQUE_CONTENT_DENOMINATOR
  = count(DISTINCT duplicate_group_id)
  = RAW_RECORD_DENOMINATOR − Σ(corpus별 duplicate_pair_rows_after_first_occurrence)
  ≈ 5,652,925 − (214,252[025] + 44[026] + 2,494[LEGACY, D-01 manifest상 informational])
  ≈ 5,436,135  (** 참고치 — Phase 2 실행 시점에 정식 재계산 필요, 이 문서는 이 수를 확정치로 주장하지 않는다 **)

PRIMARY_ELIGIBLE_DENOMINATOR
  = source_tier == 'A' (025+026), Legacy(tier=null/UNASSIGNED) 제외
  = 2,700,345 + 1,350,162 = 4,050,507
  (`configs/research_v1.yaml`의 `primary_cohort_policy.mode: all_qc_accepted_tier_a`와 명명 일관성 유지;
   ENG-OBS-001 예시 heartbeat payload의 total=4,050,507과도 일치 — 우연이 아니라 동일 개념)

FINAL_ANALYSIS_DENOMINATOR
  = PRIMARY_ELIGIBLE_DENOMINATOR ∩ analysis_eligible_exact_dedup=true ∩ pair_quality_status='accepted'
  (실행 전 계산 불가 — 공식만 동결, §3c의 accepted 규칙이 Director 확정되기 전에는 이 수도 확정 불가)
```

`outputs/reports/LID_QC_PASS_RATE_v001.csv`는 이 4개 분모를 **별도 행**으로 명시하고, 어떤 단일 "pass rate"도 4개 중 하나로 뭉뚱그리지 않는다.

## 7. Semantic QC

- Audit N = **500** (고정, D-RD-01/AMB-06 — 재논의 안 함).
- Strata: `domain × sentence_type × translation_direction × source_id × length_stratum` (§9.2 표본설계와 동일 축 재사용, 새 strata 발명 안 함).
- Score rubric: 2(실질적 동등)/1(핵심 의미 대응, 경미한 누락·추가·의역)/0(다른 의미/심각한 누락/정렬 오류) — §10.3 그대로.
- Primary cohort target = score 2. Score 1 결과는 sensitivity analysis로 분리 가능(config에 이미 고정).
- 자동 유사도 score(`pair_quality_score`) 역할: **보조 QC 신호로만 저장, 어떤 row의 `pair_quality_status`도 gate하지 않는다**(T-01). 이는 SSOT 문언 그대로이며 이 계약이 새로 만드는 규칙이 아니다.
- Manual audit 역할: (해석 a 채택 시) population 전체의 rule-based accepted 판정이 방향적으로 타당한지 검증하는 통계(예: "500쌍 감사 표본 중 rule-based accepted였던 pair의 X%가 audit score=2") — 이 자체가 개별 row의 disposition을 바꾸지 않는다.
- **Research Director로부터 필요한 정확한 증거** (이 항목 자체가 §3c 미해결과 직결):
  1. 해석 (a)/(b) 중 공식 채택안 확인(또는 제3안 지시).
  2. 500쌍 감사를 프로젝트 전체 1회로 볼지, 아니면 stratum별로 세분해 각 stratum에 최소 표본을 배정할지.
  3. 실제 audit을 누가 수행하는지 — 이 SSOT 요구는 사람의 의미 판단이며, 어떤 agent도 "수동 audit"을 대신 수행하거나 그 결과를 발명할 수 없다. Research Director 본인 또는 지정된 rater가 고정 rubric으로 수행해야 하며, 이 문서는 그 결과를 가정하지 않는다.

## 8. Tokenizer roundtrip boundary (QC-only, minimal)

D-04(Phase 4, `05_o200k_measurement.ipynb`)의 전체 토큰 측정을 조기 생성하지 않는다. QC 게이트는 다음만 수행:

```python
import tiktoken
enc = tiktoken.get_encoding("o200k_base")

def roundtrip_ok(text: str) -> bool:
    ids = enc.encode(text)
    return len(ids) > 0 and enc.decode(ids) == text
```

- 저장 컬럼: `tokenizer_roundtrip_ok` (boolean) — `ko_text_analysis`/`en_text_analysis` 각각에 대해 `roundtrip_failure_flag = not (roundtrip_ok(ko) and roundtrip_ok(en))`.
- **저장하지 않음**: token IDs, token count, `TP_i`/`logTP_i`, `compression_penalty`, chunk 통계 — 이들은 D-04/D-05 스키마(§12.4, §12.5)이며 Phase 4/5의 몫이다. 이 게이트가 D-04 outcome을 몰래 생성하지 않도록 하는 것이 §25.4 "encode/decode roundtrip 100% PASS" 성공조건을 QC 레벨에서만 만족시키는 목적이다.

## 9. Output contract (naming frozen, Codex 구현 전 확정)

```
data/registry/PAIR_REGISTRY_v002.parquet      # v001과 동일하게 raw-text 보유 → .gitignore 유지, untracked
outputs/reports/QC_FLOW_v001.csv               # flag/disposition별 aggregate 카운트만, raw text 없음
outputs/reports/LID_QC_PASS_RATE_v001.csv      # §6의 4개 분모, aggregate only
outputs/manifests/QC_MANIFEST_v001.json        # SHA-256, row count, schema version,
                                                #   execution_code_commit + artifact_record_commit(redline §30.2),
                                                #   contract hashes(이 문서 + G1 precontract + research_v1.yaml)
```

명명 근거: v001 D-01 산출물의 기존 패턴(`PAIR_REGISTRY_MANIFEST_v001.json`, `PAIR_REGISTRY_RECONCILIATION_v001.csv`)과 zero-padded 버전 규칙(§38)을 그대로 계승. Raw-text 보유 아티팩트(`PAIR_REGISTRY_v002.parquet`)는 계속 untracked; 집계 전용 리포트(CSV/JSON, raw text 없음)만 Git에 안전하게 persist 가능.

### v002 신규 컬럼 (v001의 44개 컬럼에 추가, 삭제 없음)

| 컬럼 | 타입 | 근거 |
|---|---|---|
| `normalization_rule_version` | string | §11.1 |
| `normalization_ops` | string (canonical JSON array) | §11.1 |
| `unicode_anomaly_flag` | bool | §11.1, §10.2 |
| `empty_text_flag`, `lid_failure_flag`, `markup_dominant_flag`, `control_char_excess_flag`, `roundtrip_failure_flag`, `semantic_qc_fail_flag` | bool ×6 | §10.1 (exact_duplicate_flag는 기존 D-01 컬럼에서 유도, 신규 아님) |
| `short_text_flag`, `long_text_flag`, `script_mix_flag`, `translation_quality_review_flag`, `named_entity_heavy_flag` | bool ×5 | §10.2 |
| `primary_rejection_reason` | string, nullable | §3c |
| `secondary_rejection_flags` | string (canonical JSON array) | §3c |
| `duplicate_disposition` | string enum | §4 |
| `analysis_eligible_exact_dedup` | bool | §4 |
| `tokenizer_roundtrip_ok` | bool | §8 |
| `qc_stage_status` (기존 컬럼 값 갱신: `PENDING_PHASE2` → `PHASE2_COMPLETE`) | string | D-01 §16C 후속 |
| `pair_quality_status`/`pair_quality_score` (기존 컬럼, Phase 2에서 실제 값 채움) | string/float | §10.3, §3c |
| `ko_text_nfc`/`en_text_nfc`/`ko_text_analysis`/`en_text_analysis` (기존 nullable 컬럼, Phase 2에서 실제 값 채움) | string | §11.1 |

`high_digit_ratio_flag`/`high_punctuation_ratio_flag`도 신규 컬럼(bool ×2, threshold 이미 확정 `>0.20`) — 위 목록에서 누락 방지를 위해 명시.

## 10. G1 closure matrix

| 항목 | CURRENT | PHASE2 REQUIRED EVIDENCE | PASS RULE | OWNER ARTIFACT |
|---|---|---|---|---|
| pair ID uniqueness | PASS (D-01, 독립감사 재확인) | 없음 — 이미 충족 | `pair_id` distinct == total, null == 0 | `PAIR_REGISTRY_RECONCILIATION_v001.csv` |
| null/duplicate integrity | PASS (D-01, 구조적 수준) | 없음 — 이미 충족 | 구조적 null/dup 가시화 완료 | 위와 동일 |
| source/license metadata | **PASS** (Vice Director adjudication) | 없음 — Vice Director가 이미 판정 완료. `provenance_closure_status`(025/026 PENDING, Legacy PARTIAL)는 **OPEN NON-BLOCKING RISK**로 별도 분류하며 이 판정은 G1 PASS 조건 자체를 막지 않음 | 개별 row `source_license_note` self-asserted 기록 + non-verification 명시 완료 | `SOURCE_REGISTRY_v001.parquet` |
| LID/QC pass rate | **NOT CLOSED** (redline 2026-08-16 17:01 로그, margin 판정) | `QC_FLOW_v001.csv` + `LID_QC_PASS_RATE_v001.csv` 생성, §6의 4개 분모 모두 보고, §3c disposition 규칙 Director 확정 후 실행 | 4개 분모 각각 산출 + 자동 disposition 규칙이 문서화되고 실행 가능 | `outputs/reports/LID_QC_PASS_RATE_v001.csv`, `QC_MANIFEST_v001.json` |

`D-RD-05`(source tier 배정: 025=A, 026=A, Legacy=null/UNASSIGNED)는 **재논의하지 않는다** — 이 매트릭스는 그 결정을 전제로만 사용한다.

## 11. ENG-OBS-001 적용 (모든 >30초 단계)

| Stage | total 알려짐? | progress unit | checkpoint | 예상 memory class | restartability |
|---|---|---|---|---|---|
| v001 registry read (5,652,925 rows) | Yes | rows read | batch당(예: 25,000행) | 낮음(streaming read) | 무상태 재실행 가능(read-only) |
| Normalization pass (NFC/BOM/trim) | Yes | rows processed | batch당 | 낮음(문자열 연산, DuckDB 불필요) | idempotent, 재실행 안전 |
| LID scan (script-rule, §5-A) | Yes | rows scanned | batch당 | 낮음 | idempotent |
| Duplicate disposition join | Yes(group 수 사전 계산 가능) | groups resolved | DuckDB query 단위(단일 대형 SQL이면 INDETERMINATE 허용, ENG-OBS-001 §5) | 중간(8GB DuckDB 캡, runtime-safety 계약 준수) | 전체 재실행(atomic COPY, D-01 패턴 재사용) |
| Semantic QC 배치 채점(자동 유사도, all rows) | Yes | rows scored | batch당 | 중간(모델 있으면) | idempotent |
| Manual audit(500쌍) | Yes(고정 500) | audited pairs | 개별 audit 단위 | 해당 없음(사람 작업) | 해당 없음 |
| Tokenizer roundtrip 검사(§8) | Yes | pairs checked | batch당 | 낮음(tiktoken CPU) | idempotent |
| Manifest/report 저장 | Yes(고정 파일 수) | 파일 수 | 파일 단위 | 낮음 | atomic replace(D-01 패턴 재사용) |

모든 단계는 `ProgressHeartbeat(run_id="P2_QC_<timestamp>", phase="02_normalize_and_qc", stage=<stage>, total=<known>, interval_sec=10.0)` + `tqdm.auto`를 사용하며, heartbeat에는 raw KO/EN 텍스트를 절대 기록하지 않는다(ENG-OBS-001 §6 privacy boundary 그대로 적용). Duplicate disposition의 DuckDB 단계는 `memory_limit`을 D-01 runtime-safety 계약(8GB 기본, 6GB 권장 concurrent-safe)과 동일하게 적용한다.

---

**요약**: 이 문서는 Phase 2의 엔지니어링 계약을 동결하되, 최소 1개의 실질적 미해결 지점(§3c/§7 — accepted 판정이 rule-based population-level인지 manual-audit-gated인지)과 다수의 threshold류 IMPLEMENTATION_CHOICE_REQUIRED 항목을 **침묵 없이 Decision Queue로 이관**한다. CR-003 승인 여부와 무관하게 이 계약 설계 자체는 유효하지만, **Codex의 실제 notebook 구현·전체 실행은 이 문서만으로 착수하지 않는다** — Decision Queue 항목에 대한 Director 결정과, G1/CR-003에 대한 Vice Director 판정이 선행되어야 한다.
