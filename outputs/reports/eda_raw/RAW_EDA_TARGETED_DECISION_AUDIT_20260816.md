# RAW EDA — Targeted Decision Audit Addendum

- Branch: `eda/g0-raw-notebooks`
- Accepted baseline: `a55b86dd50b3fadd46955accd73a60492b10c610`
- Scope: targeted full-population aggregate appendices only
- Claim boundary: PRE-G1 exploratory evidence; no tokenization, morphology, inference, QC acceptance, or canonical pair registry

## AIHub 025: new observations

- Full-population crosstabs cover 2,700,345 local label records without cross-dataset pooling.
- `SBS` occurs in 449,805 records. All observed SBS records are `KO_TO_EN × 일상생활`; counts outside that direction and raw domain are both zero.
- `크라우드 소싱` occurs only in `EN_TO_KO` in this snapshot and spans all three raw domains. `크라우드소싱` occurs in `KO_TO_EN` and spans `해외고객과의채팅` and `해외영업`; the `KO_TO_EN × 일상생활` cell uses `SBS`.
- These are distinct raw categorical strings coupled to different observed cells. Local EDA cannot decide whether they are spelling variants or different provenance.
- Exact raw KO+EN duplicate-after-first count is 214,252, matching the accepted baseline observation.
- Cross-direction 1:1-matchable identical-pair rows are 50,529, or 23.5839% of duplicate-after-first rows. This is a candidate structural explanation, not a causal or provenance attribution.
- Within-direction duplicate-after-first candidates are 26,525 for `EN_TO_KO` and 137,216 for `KO_TO_EN`. Within-split candidates are 164,170 for `TRAIN` and 24,844 for `VALID`; cross-split matchable rows are 36,089. These mechanisms overlap and must not be added as mutually exclusive parts.
- Duplicate-group multiplicity has a long tail: size 2 has 80,834 groups, size 3 has 5,528, size 4 has 2,200, and the maximum observed exact-pair group size is 5,508.
- Proposed count-only domain preview: `일상생활→general` 899,757; `해외고객과의채팅→dialogue` 540,221; `해외영업→other` 1,260,367. No canonical data was written.

## AIHub 026: new observations

- `특허정보원` source count is 359,910, `기술과학` raw-domain count is 359,910, and their row-level intersection is 359,910.
- `특허정보원` outside `기술과학` and `기술과학` outside `특허정보원` are both zero. This is a local categorical biconditional, not official provenance documentation.
- Proposed count-only domain preview: `기술과학→technology` 359,910; all remaining raw domains mapped to `other` total 990,252. No canonical data was written.

## Legacy 뉴스(2) ↔ 한국문화: new observation

- The reported overlap is reproduced exactly: 2,469 distinct raw KO+EN groups and 2,469 one-to-one-matchable rows.
- Every overlap group has multiplicity `뉴스(2)=1`, `한국문화=1`, combined size 2.
- Overlap-group rows are 1.2312% of 뉴스(2) (2,469 / 200,541) and 2.4532% of 한국문화 (2,469 / 100,646).
- The subset is concentrated: one date, one news institution, one `자동분류2`, and one `자동분류3` category each cover 100% of overlap rows. The leading `자동분류1` and culture keyword category covers 2,434 / 2,469 rows (98.5824%); the remaining 35 rows span five other observed category strings.
- Interpretation status is strictly `POTENTIAL CORPUS COMPOSITION OVERLAP`. This addendum does not label the overlap an error, contamination, invalid pair, or exclusion condition.

## Artifact index

- 025 aggregate tables: `outputs/eda_raw/targeted_decision_audit/aihub_025/`
- 026 aggregate tables: `outputs/eda_raw/targeted_decision_audit/aihub_026/`
- Legacy overlap tables: `outputs/eda_raw/targeted_decision_audit/legacy_news2_culture/`
- Targeted figures: `outputs/figures/eda_raw/targeted_decision_audit/`
- Notebook append helper: `outputs/eda_raw/support/append_targeted_decision_audit.py`

All targeted exports contain aggregate counts/rates/categories only. No raw KO/EN text or pair hashes are exported by the appendices.
