# CR-003 — G1 Gate Sequence Clarification (PROPOSAL ONLY)

**Status: PROPOSAL — NOT APPROVED.** 이 문서는 Change Request 초안이다. SSOT PDF는 수정하지 않았으며, 어떤 승인도 이 문서 자체가 선언하지 않는다. 최종 승인 권한은 Research Director에게, Gate adjudication 권한은 Vice Director에게 있다.

**Author:** `research/g1-gate-claude` (Claude, Research/Data/Statistics Orchestrator)
**Depends on:** [[project-d01-independent-audit-v001]], `2026-08-16_1616_KOEN_TP_G1_ENTRY_MIDPOINT_DECISION_LOG.md` (L.647–761에서 이미 동일 gap을 선제 식별함 — 이 CR은 그 관찰을 공식 CR 형식으로 승격한 것이지 신규 발견이 아니다)

---

## 1. CHANGE_REQUEST

| 항목 | 값 |
|---|---|
| CR ID | CR-003 |
| 제목 | G1 Gate와 Phase 1/Phase 2 notebook 실행 순서 간 시퀀싱 모순 해소 |
| 분류 | Gate-text clarification (연구 내용 변경 아님, SSOT §31/§37의 문구·귀속 관계만 명확화) |
| 대상 문서 | `ssot/Korean_English_Tokenization_Premium_Research_Spec_v1.0-2.pdf` §31 (인쇄 p.27 / PDF p.28), §37 (인쇄 p.31 / PDF p.32) |
| 발의 근거 | D-01 엔지니어링 완료 시점에 "G1 PASS를 지금 선언할 수 있는가"라는 질문이 실제로 발생했고, SSOT 원문 자체가 이 질문에 문면상 즉답하지 않음을 확인함 |

## 2. 정확한 원문 (EXACT BEFORE WORDING)

### §31 연구 Gate — G1 — Data Integrity (인쇄 p.27 / PDF p.28)

```
G1 — Data Integrity
PASS 조건:
　・pair IDs unique
　・null/duplicate checks
　・LID/QC pass rate 보고
　・source/license metadata 완성
```

### §37 Notebook 실행 순서 (인쇄 p.31–32 / PDF p.32–33)

```
Phase 1 — Data Contract
01_build_pair_registry.ipynb
　・source ingest
　・stable pair ID
　・metadata schema
　・raw hash

Phase 2 — Normalization & QC
02_normalize_and_qc.ipynb
　・NFC/analysis text
　・anomaly flags
　・duplicate/LID/parallel quality
　・QC flow table
```

두 인용 모두 이번 세션에서 PDF p.26–33 range read로 직접 재확인했으며, Codex 오케스트레이터가 지정한 페이지 번호(및 PDF/인쇄 페이지 오프셋 1)와 정확히 일치한다.

## 3. PROBLEM

SSOT는 Gate를 "G0, G1, G2 …"로 명명하고(§31), notebook을 "Phase 0, Phase 1, Phase 2 …"로 명명한다(§37). 두 번호 체계 사이에 **1:1 대응이 명시적으로 선언되어 있지 않다.**

- G1의 PASS 조건 중 `LID/QC pass rate 보고`와 `source/license metadata 완성`은, §37의 정의에 따르면 **Phase 2 (`02_normalize_and_qc.ipynb`)**의 산출물이다 — `duplicate/LID/parallel quality`가 Phase 2 항목으로 명시되어 있다.
- 그런데 Phase 1 (`01_build_pair_registry.ipynb`)의 항목(`source ingest`, `stable pair ID`, `metadata schema`, `raw hash`)만으로는 G1의 4개 PASS 조건 중 `pair IDs unique`, `null/duplicate checks`(구조적 null/중복 checks만) 정도만 충족되고, `LID/QC pass rate`는 원천적으로 산출 불가능하다.
- 즉 **"G1"이라는 이름이 "Phase 1"과 숫자가 같다는 이유만으로 G1 = Phase 1 완료 시점에 판정 가능하다고 오독될 위험이 있으나, SSOT 문면 자체는 G1이 Phase 2 산출물을 요구한다고 명시하여 이 오독을 반박한다.** 문제는 SSOT가 틀렸다는 것이 아니라, 두 넘버링 체계의 관계를 명시적으로 진술하는 문장이 없어 매 실행마다 재해석 위험이 남는다는 것이다.

## 4. IMPACT

이 모호성을 방치하면 두 가지 잘못된 결과 중 하나가 나올 수 있다:

1. **조기 PASS 오판**: `01_build_pair_registry`만 완료한 상태에서 "Phase 1 = G1"이라는 이름 대응만 보고 G1 PASS를 선언 — LID/QC pass rate와 source/license metadata 완성 조건이 미충족인 채로 Gate를 통과시키는 오류.
2. **과도한 차단**: 반대로 "G1이 아직 OPEN이니 Phase 1 산출물(pair registry)조차 신뢰할 수 없다"는 과잉 해석으로, 이미 독립 감사([[project-d01-independent-audit-v001]])까지 마친 엔지니어링 완료 산출물의 통합·후속 작업(Phase 2 설계 등)을 불필요하게 차단.

현재 이 프로젝트는 실제로 (1)의 문턱까지 왔다 — Codex D-01 산출물이 25/25 reconciliation PASS, 독립 재검증까지 마쳤고, 그 직후 "G1 PASS인가"라는 질문이 제기되었기 때문이다. 다행히 사전에 Vice Director 결정로그(2026-08-16 16:16)가 이 정확한 함정을 이미 문서화해 두었으나, 그것은 결정로그 한 곳에만 존재하는 임시 해석이며 SSOT 자체의 CHANGELOG에는 아직 반영되지 않았다.

## 5. ALTERNATIVES CONSIDERED

- **(A) 아무것도 바꾸지 않는다.** SSOT 문면을 그대로 두고, 매번 결정로그에서 재해석한다. — 이번처럼 매 Gate마다 동일한 혼동이 재발할 위험이 있고, Vice Director/Research Director가 바뀌거나 시간이 지나면 결정로그의 임시 해석이 유실될 수 있다. **기각.**
- **(B) §37의 Phase 번호를 Gate 번호와 다르게 재명명한다** (예: Phase 1→"Data Contract Stage", Phase 2→"QC Stage", 숫자 제거). — SSOT 본문 구조를 광범위하게 변경해야 하고, 기존 notebook 파일명(`01_...`, `02_...`)과 CR 범위를 벗어나는 영향이 크다. **기각 (범위 초과).**
- **(C, 권장) §31 G1 항목에 "이 PASS 조건은 Phase 1과 Phase 2 notebook 산출물을 모두 요구하며, `01_build_pair_registry.ipynb` 단독 완료만으로 충족되지 않는다"는 명시적 각주/문장을 추가한다.** notebook 번호 체계는 그대로 두고, Gate 판정 시점과 필요 선행 notebook의 대응 관계만 명문화한다. 코드/notebook 이름 변경 없음, 연구 설계 값 변경 없음 — 순수 문서 명확화(clarification)로 최소 침습적이다. **권장.**

## 6. RECOMMENDED AFTER WORDING (제안 문구, 미승인)

### §31 G1 — Data Integrity (제안 삽입, 기존 4개 PASS 조건 하단에 추가)

```
G1 — Data Integrity
PASS 조건:
　・pair IDs unique
　・null/duplicate checks
　・LID/QC pass rate 보고
　・source/license metadata 완성

[신규 삽입, 제안]
비고: 이 PASS 조건은 §37 Phase 1(01_build_pair_registry.ipynb)과
Phase 2(02_normalize_and_qc.ipynb) 산출물을 모두 전제로 한다.
Phase 1 단독 완료(ingest/stable pair ID/metadata schema/raw hash)는
`pair IDs unique`와 구조적 null/duplicate 가시성만 충족하며,
`LID/QC pass rate 보고`는 Phase 2가 산출할 때까지 미충족 상태(OPEN)로
남는다. Gate 번호(G1)와 Phase 번호(Phase 1)의 일치는 우연이며 동일
완료 시점을 의미하지 않는다.
```

### §37 Phase 1 — Data Contract (제안 삽입, 기존 4개 항목 하단에 추가)

```
Phase 1 — Data Contract
01_build_pair_registry.ipynb
　・source ingest
　・stable pair ID
　・metadata schema
　・raw hash

[신규 삽입, 제안]
비고: 이 Phase의 완료는 §31 G1 Gate의 부분 충족일 뿐이다.
G1 전체 PASS 판정에는 Phase 2(02_normalize_and_qc.ipynb)의
duplicate/LID/parallel quality 산출물이 추가로 필요하다.
```

## 7. GATE IMPLICATIONS

- G1은 `01_build_pair_registry.ipynb` 완료만으로 PASS 선언될 수 **없다** — 이는 새 규칙이 아니라 §31 원문의 명시적 요구(`LID/QC pass rate 보고`)를 재확인하는 것뿐이다. 이 CR은 그 요구를 바꾸지 않는다.
- 이 CR이 승인되면, 향후 모든 Gate(G2–G6)에 대해서도 "Gate 번호 = Phase 번호"라는 암묵적 가정이 자동으로 성립하지 않는다는 선례가 명문화된다 — 예컨대 G2(Representation Integrity)가 Phase 3(Feature Layer, `03_representation_features.ipynb`) 산출물만으로 충족되는지, 아니면 다른 Phase의 산출물도 필요한지 역시 사전에 명시적으로 검토해야 한다는 실무 지침이 생긴다.
- 이 CR은 D-01 엔지니어링 산출물 자체의 정확성·완결성 판정에는 영향을 주지 않는다 — `D01_ENGINEERING_COMPLETE`는 이 CR과 독립적으로 이미 참이다.

## 8. DIRECTOR APPROVAL REQUIREMENT

이 CR은 **Research Director 승인 없이는 SSOT에 반영되지 않는다.** 승인 시에도 SSOT PDF 자체(`Korean_English_Tokenization_Premium_Research_Spec_v1.0-2.pdf`)는 이 세션에서 직접 편집하지 않았으며, 이 문서는 승인 이후 별도 절차(PDF 개정판 발행 또는 Appendix A 형태의 공식 CR 등재)를 위한 초안일 뿐이다. 본 문서의 존재 자체가 승인을 의미하지 않는다.

## 9. PROPOSED CHANGELOG ROW (Director 승인 시에만 실제 CHANGELOG.md에 등재할 초안)

```
## CR-003 — G1_GATE_PHASE_SEQUENCE_CLARIFICATION (PROPOSED, NOT YET APPROVED)

- **Evidence**: SSOT §31 G1 PASS 조건(`LID/QC pass rate 보고`, `source/license
  metadata 완성`)은 §37 Phase 2(`02_normalize_and_qc.ipynb`)의 산출물이며,
  §37 Phase 1(`01_build_pair_registry.ipynb`)만으로는 충족되지 않는다.
  Gate 번호와 Phase 번호가 우연히 같아(G1/Phase 1) 조기 PASS로 오독될
  위험이 있음을 D-01 엔지니어링 완료 직후 실제로 확인함.
- **Research impact**: 없음 — 연구 설계 값, notebook 순서, 코드는 변경하지
  않는다. Gate 판정 문서화만 명확화한다.
- **Alternative considered**: (A) 현행 유지 — 매번 재해석 위험, 기각.
  (B) Phase 번호 체계 전체 재명명 — 범위 초과, 기각. (C) §31/§37에 상호
  참조 각주 추가 — **제안(권장)**.
- **Decision**: PENDING — Research Director 승인 대기.
- **Impact**: 승인 시 §31 G1, §37 Phase 1 항목에 각주 추가. Notebook
  파일명/코드/연구값 변경 없음. G1 PASS는 여전히 Phase 2 산출물
  (LID/QC pass-rate artifact) 완성을 전제한다 — 이 CR은 그 요구조건을
  완화하지 않는다.
```

---

**요약**: 이 CR은 SSOT의 요구사항을 바꾸는 것이 아니라, 이미 원문에 존재하는 요구사항("G1은 LID/QC pass rate를 요구하고, 그것은 Phase 2 산출물이다")이 Gate 번호와 Phase 번호의 우연한 일치 때문에 매번 재해석되어야 하는 상황을 문서 차원에서 종결시키자는 제안이다. **PROPOSAL ONLY — AWAITING RESEARCH DIRECTOR DECISION.**
