# Phase 2 QC — Open Decision Queue v1

이 문서는 `docs/contracts/P2_NORMALIZE_QC_PRECONTRACT_v1.md`가 **침묵하지 않고 명시적으로 이관**한 미해결 항목 목록이다. 각 항목은 Director 결정 전까지 어떤 값도 코드에 하드코딩하지 않는다.

## Q0 — [최우선] `accepted` 판정의 게이팅 방식 (§3c/§7 직결)

**질문**: SSOT §10.3의 500쌍 수동 semantic-QC audit은 (a) 전체 565만 행에 대한 rule-based(hard-exclusion 전무) `accepted` 판정의 **calibration/검증 통계**로만 기능하는가, 아니면 (b) 개별 row의 `accepted` 자체를 감사 대상 500쌍에 한정해 확정하는가?

**왜 중요한가**: 이 선택이 `FINAL_ANALYSIS_DENOMINATOR`(§6)와 `pair_quality_status` 컬럼 전체의 의미를 결정한다. (b)를 문자 그대로 적용하면 대부분의 row가 영구히 `review`로 남아 분석 표본이 사실상 500쌍으로 축소되는데, 이는 `primary_cohort_policy.mode=all_qc_accepted_tier_a`가 전제하는 100,000+ 규모(§9.1)와 정합하지 않는다.

**제안 (미승인)**: (a) 채택 — rule-based population-level accepted, 500쌍은 별도 calibration statistic.

**필요 결정**: Research Director의 명시적 확인 또는 제3안 지시.

## Q1 — `markup_dominant_flag` threshold

HTML/code/URL/table markup이 "텍스트 대부분을 차지"(§10.1)하는 정량 기준 미지정. 제안(미승인): 태그/URL 패턴 매치 문자 수 ÷ 전체 문자 수 `> 0.5`.

## Q2 — `control_char_excess_flag` threshold

제어문자/zero-width 문자가 "비정상적으로 과다"(§10.1)한 정량 기준 미지정. 제안(미승인): 해당 문자 수 ÷ 전체 codepoint 수 `> 0.05`.

## Q3 — `short_text_flag`/`long_text_flag` threshold

§10.2에 flag는 존재하나 절대/상대 threshold 없음. `length_stratum`(EN codepoint quintile, D-RD-01)을 재사용해 최하위/최상위 분위로 정의할지, 별도 절대 길이(codepoint 수) 기준을 둘지 미결정.

## Q4 — `script_mix_flag` 정의

Hangul+Latin 혼재를 어느 비율부터 "mix"로 볼지 미지정. D-02(Representation Features, Phase 3)의 정식 script 분해를 앞당겨 쓰지 않도록 QC-scope 전용 경량 정의가 필요 — 제안(미승인): 두 스크립트 모두 전체 alnum codepoint의 `10%` 이상.

## Q5 — `named_entity_heavy_flag` 정의

SSOT는 flag 존재만 요구, 방법 미지정. 개체명 인식 모델 도입은 LID(§5)와 동일한 과잉엔지니어링/재현성 부담 위험이 있음. Proxy heuristic 후보(미승인, 택1 또는 Director 대안 지시 필요):
- EN: 대문자 시작 단어 비율(연속 대문자 시퍽스는 제외)이 threshold 초과
- KO: 외래어/고유명사 표기 패턴(예: 알파벳-한글 혼용 토큰) 비율 초과
- 또는 이 flag를 이번 Phase 2 최초 버전에서 `false`로 placeholder 고정하고 Phase 3 이후 별도 CR로 정식 정의 (SSOT 위반 여부는 Director가 판단)

## Q6 — LID script-rule 정확한 threshold

`docs/contracts/P2_NORMALIZE_QC_PRECONTRACT_v1.md` §5는 방법(A: Unicode/script-rule)을 권고하나, "target script 비율이 얼마 미만이면 실패"의 정확한 숫자(제안 `<0.5`)는 Director 승인 대상. 이 숫자는 LID/QC pass rate의 실측값에 직접 영향을 주므로 estimand에 실질적 영향을 미치는 결정으로 분류.

## Q7 — Manual audit 로지스틱스

500쌍 감사를 (a) 프로젝트 1회 전체 표본으로 할지 (b) stratum별 최소 표본을 배정할지, 그리고 실제 채점자가 누구인지(Research Director 본인 또는 지정 rater) 미확정. 어떤 agent도 이 사람의 의미 판단을 대신하거나 결과를 발명하지 않는다.

## Q8 — CR-003 승인 여부 (선행 조건)

`research/g1-gate-claude@566f30b`의 CR-003 제안은 2026-08-16 17:32 KST 시점 기준 미승인. 이 Precontract는 CR-003 승인 여부와 무관하게 설계 자체는 유효하지만, formal Phase-2 **실행**(notebook 구현 착수, 565만 행 처리)은 위 Q0-Q7 해결과 별개로 Vice Director/Research Director의 착수 승인을 필요로 한다.

---

**이관 원칙**: 위 어느 항목도 이 세션에서 임의의 기본값을 코드/설정 파일에 기록하지 않았다. `configs/research_v1.yaml`에는 이 문서의 제안값 중 어느 것도 추가하지 않았다 — Director 승인 후에만 `d02_field_contract` 등의 신규 섹션으로 config에 반영되어야 한다.
