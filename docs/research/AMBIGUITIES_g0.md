# G0 Ambiguities & Decisions Required — SSOT v1.0

SSOT(KOEN-TP-RS-001 v1.0)를 `docs/contracts/RESEARCH_CONTRACT_v1.md`로 옮기는 과정에서, 스펙이 **원칙은 명시하지만 정확한 숫자/파라미터는 지정하지 않은** 항목들이다. 임의로 값을 만들어 채우지 않고 여기 기록한다 — Research Director 결정 후 `configs/research_v1.yaml`에 반영한다.

| ID | 항목 | SSOT 근거 | 스펙이 명시하지 않은 것 | 비고(비구속 제안) |
|---|---|---|---|---|
| AMB-01 | G2 exact-decomposition identity 허용오차 ε | §31 G2 | `\|logTP_i - (logCR+logBDR+logCP)\| < ε`에서 ε 수치 미지정 | float64 부동소수 오차 한계 고려 시 1e-9 ~ 1e-6 범위가 통상적 — Director 확정 필요 |
| AMB-02 | Bootstrap resample 횟수(B) | §17.2 | "pair-level bootstrap 95% CI"만 명시, B(반복횟수) 미지정 | 통상 B≥2000 (BCa 사용 시 더 크게) — 확정 필요 |
| AMB-03 | FDR alpha 수준 | §24, §29 | "Benjamini-Hochberg FDR 적용"만 명시, α(예: 0.05) 미지정 | — |
| AMB-04 | length_stratum 분위수 개수 | §9.2 | "영어 word/code point 또는 pair mean byte 기준 분위수"라고만 함 — tertile/quartile/quintile 여부 미지정 | — |
| AMB-05 | 표본 규모 목표치가 범위(range)로만 제시 | §9.1 | 최소 본분석 20,000–50,000, 권장 100,000+ 등 범위 — 실제 목표 N 확정 필요 (data-recon ingest 이후) | — |
| AMB-06 | 수동 semantic QC audit 표본 수 | §9.1, §10.3 | 300–500 범위, 정확한 N 미지정 | — |
| AMB-07 | Hold-out 비율 | §23.2 | 15–20% 범위, 정확한 비율 미지정 | — |
| AMB-08 | high_digit_ratio_flag / high_punctuation_ratio_flag 임계값 | §10.2 | flag 이름만 정의, 수치 threshold 없음 | — |
| AMB-09 | Random vs Fixed effects 판단 기준의 "충분한 level 수" | §20.1 | 정성적 서술("충분하고", "적으면")만 있고 수치 cutoff 없음 | — |
| AMB-10 | VIF/GVIF 임계값 | §20.2 | Identifiability Gate에서 VIF 확인을 요구하나 cutoff 값 없음 (게다가 "VIF만으로 자동 삭제 금지" 명시 — §21) | — |
| AMB-11 | Quantile regression 분석 분위수 | §22 | "상위 premium 분석"용 quantile regression만 언급, 구체적 분위(예: 0.9/0.95) 미지정 | — |
| AMB-12 | Source tier ↔ 실제 corpus 매핑 | §9.3 | Tier A/B/C 정의는 스펙에 있으나 실제 어떤 corpus가 어느 tier인지는 미정 | **AIHub 등 raw 데이터가 canonical ingest되지 않아 이 계약에서 의도적으로 미확정** — data-recon 완료 후 별도 CR |
| AMB-13 | `src/koen_tp/visualization.py` 소재 | Notebook Constitution 예시 vs SSOT §36 IA | Constitution은 `src/koen_tp/visualization.py`를 언급하지만 SSOT §36의 11개 모듈 목록(io, normalization, qc, unicode_features, morphology, tokenization, chunking, decomposition, statistics, modeling, serving)에는 `visualization.py`가 없음 | 이 문서 소유자가 아니므로(=`src/**`는 WRITE 금지) 여기서는 **불일치만 기록**하고 실제 모듈 생성은 제안하지 않음 |
| AMB-14 | 패키지 네임스페이스 | CR-001 | SSOT §36은 `src/koen_tp/`를 명시하나 CR-001로 `src/tokenization_premium/`이 승인된 예외로 확정됨 | 재논의하지 않음 — 참고로만 기록 |

각 항목은 개별적으로 CHANGE_REQUEST 절차(evidence → research impact → alternative → Director decision)를 거쳐야 `configs/research_v1.yaml`에 구체값으로 반영 가능하다.
