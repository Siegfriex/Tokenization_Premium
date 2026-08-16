# G1 Decision Queue — v1

Only items that genuinely require a Research Director decision are marked `DECISION_REQUIRED`. Everything else is classified so it does not need to be re-raised.

| Item | Classification | Rationale |
|---|---|---|
| AMB-05 — final analysis N | `WAIT_FOR_RAW_EDA` | Cannot be frozen before duplicate-representative policy (below) and Raw EDA's label distributions are known; local raw volume (~5.65M unique-content records across 025/026/Legacy) already far exceeds SSOT's 100k+ recommended floor, so this is not a *volume* blocker, only a *definition-of-final-N* blocker |
| AMB-12 — source tier ↔ corpus mapping | `DECISION_REQUIRED` | Recommendations are ready in `docs/research/AIHUB_LOCAL_WEB_RECONCILIATION_v1.md` Task 2 (025→Tier A/primary backbone, 026→Tier A/domain supplement, Legacy→Tier B(tentative)/sensitivity-only, D71693→not acquired). Needs approval, not further evidence, to move from recommendation to `configs/research_v1.yaml.corpus_tier_assignment` |
| Duplicate Analysis-Representative selection rule (which record wins within a `duplicate_group_id`) | `DECISION_REQUIRED` | Directly changes which ~214k+ records enter the accepted cohort for 025 alone; candidate rules (prefer non-validation split, prefer curated tier, prefer earliest `sn`) have different research consequences and none is dictated by SSOT text |
| Train/validation overlap handling (keep AIHub's upstream split vs rebuild via LR-01 grouping) | `DECISION_REQUIRED` | SSOT §23/LR-01 mandates group-based non-leakage but does not by itself tell us whether to trust AIHub's provided split label at all once 15.8% overlap is observed in 025 — this is a methodological choice with downstream statistical consequences |
| `pair_id` = provenance-derived (not content hash) design | `DECISION_REQUIRED` (recommend approval) | A real methodological choice, not a mechanical detail — determines what "duplicate" even means downstream; recommend approving as designed in `PAIR_IDENTITY_AND_DUPLICATE_CONTRACT_v1.md` |
| Legacy `source_record_id` mechanism (workbook+sheet+physical_row fallback) | `ENGINEERING_DETAIL` | Forced by evidence — no reliable natural key exists in any Legacy workbook (127,824 duplicate ID/SID rows), so there is no alternative to evaluate; implementation is Codex's |
| Direction-confidence handling rule (contradiction → `UNKNOWN`, insufficient signal → review flag, Legacy → `HUMAN_PARALLEL_UNKNOWN`) | `CAN_BE_RESOLVED_BY_SSOT` | Follows mechanically from the SSOT taxonomy's own four values (§9.2) and the observed field-consistency already confirmed by data-recon — no new judgment call beyond applying existing definitions |
| Domain mapping — 한국문화 (`general` vs `other`) | `DECISION_REQUIRED` | Genuine boundary case; SSOT taxonomy does not disambiguate "cultural content" and the raw signal (a keyword list, not a domain field) does not resolve it either |
| Domain mapping — 조례/ordinances (`legal` vs `administration`) | `DECISION_REQUIRED` | Same — ordinances are simultaneously statute text and government output; SSOT treats `legal` and `administration` as distinct values |
| Domain mapping — all other categories (025's unseen 3 domains/11 subdomains, 026's unseen 15 subdomains) | `WAIT_FOR_RAW_EDA` | Cannot map labels that have not yet been enumerated |
| Auxiliary D-01 fields (`source_record_id`, `raw_locator`, `duplicate_group_id`, `domain_raw`, `subdomain_raw`, `is_validation_upstream`, etc.) | `ENGINEERING_DETAIL` once the `pair_id` design above is approved | These are mechanical consequences of the identity design, not independent research choices |
| 025 duplicate-mechanism hypothesis (TL1/TL2 direction-mirroring vs accidental repetition) | `WAIT_FOR_RAW_EDA` | Requires a targeted check of whether duplicate pair-hashes cluster at the TL1↔TL2 boundary — a data question, not a policy question |
| 026 scale discrepancy (local 1.35M vs web "1.5M sentences") | *(not escalated)* | Logged in the reconciliation doc as a minor, non-blocking discrepancy; does not require a decision to proceed |

## Section 13 — Perplexity SSOT Amendment Review

**Proposed amendment** (from `origin/evidence/g0-perplexity`): add a clause stating "AI Hub KO-EN is not a single corpus identifier," requiring each result to report official dataset ID/title/URL/access date/archive SHA-256/selected fields/direction/normalization/filtering/final N/acquisition constraint, and treating datasets as separate strata absent a documented pooling justification.

**Verdict: `NO_SSOT_CHANGE_REQUIRED`** — this is operational/data-contract elaboration, not a change to SSOT's research meaning. Every element Perplexity asks for is already expressible inside the existing contract:
- "not a single corpus identifier" / "separate strata unless pooling is justified" ≈ SSOT §20.1 (source fixed/random effects), §20.2 (Identifiability Gate), T-04 (domain-source confounding) — already forbids silently pooling sources without identifiability checks, and this reconciliation's own Task 2 already assigns 025/026/Legacy as distinct roles rather than one pooled "AIHub" blob.
- official dataset ID/title/URL/access date/archive SHA-256/acquisition constraint ≈ D-01's `source_id`, `source_license_note` fields (§12.1) plus §30.2's lineage requirement (raw file hash, source registry snapshot, acquisition metadata) — already operationalized in `docs/contracts/G1_PAIR_REGISTRY_PRECONTRACT_v1.md` §1-2.
- selected KO/EN fields, translation direction, normalization/filtering policy, final paired N ≈ already covered by §11 (normalization), §9.2 (translation_direction), §10 (QC), and this decision queue's own open items above.

**Conclusion**: adopt Perplexity's request as **elaboration of how the existing source registry is documented and populated**, not as a new SSOT clause. No CR is proposed for this item.
