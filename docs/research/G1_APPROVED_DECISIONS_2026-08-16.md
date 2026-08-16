# G1 Approved Decisions — 2026-08-16

Research Director approved all four Vice Director recommendations below. **These apply SSOT taxonomy/contract to the current corpus — they do not change SSOT's research meaning, so no SSOT amendment or CHANGE_REQUEST is created for any of them.** `research/g0-claude@51147e3` remains frozen and untouched. `configs/research_v1.yaml` is **not** edited this round (see `docs/contracts/G1_PAIR_REGISTRY_PRECONTRACT_v1.md` §15 `PROPOSED_G1_CONFIG_DELTA` for the values to apply once Vice Director sequences G1 onto the canonical G0 base).

## D-RD-05 — Source Portfolio

| Corpus | `source_tier` | `research_role` | `primary_analysis_eligible` |
|---|---|---|---|
| 025 / D71265 | A | `PRIMARY_BACKBONE` | true |
| 026 / D71266 | A | `PRIMARY_DOMAIN_SUPPLEMENT` | true — condition: domain-specialized, `KO_TO_EN`-only, source/domain/direction structure kept explicit, **never pooled with 025 without a labeled stratum** |
| Legacy / D87 | `null` / **UNASSIGNED** (Tier B recommendation **withdrawn** — Tier B ≠ a fallback for weak provenance) | `SENSITIVITY_ONLY` | false |
| D71693 | — | `NOT_ACQUIRED` | `OUTSIDE_CURRENT_CORPUS` — no download proposed/started |

## D-RD-06 — Translation Direction

- 025: `KO_TO_EN` / `EN_TO_KO` per raw provenance (`ko_original`/`en_original` + `source_language`/`target_language` consistency)
- 026: `KO_TO_EN` (single direction, no reverse-direction file exists)
- Legacy: **`UNKNOWN`** — not `HUMAN_PARALLEL_UNKNOWN`; current evidence does not confirm human-parallel construction methodology. May upgrade to `HUMAN_PARALLEL_UNKNOWN` only if official construction documentation later confirms it.

## D-RD-07 — Canonical Domain Mapping

Top-level only; subdomains always stay `subdomain_raw`, never mapped:

- 025: 일상생활→`general`, 해외고객과의채팅→`dialogue`, 해외영업→`other`
- 026: 기술과학→`technology`, 세계→`other`, 경제→`other`, 정치→`other`, 기후→`other`
- Legacy: 구어체→`general`, 대화체→`dialogue`, 뉴스→`news`, 한국문화→`other`, 조례→`legal`, 지자체웹사이트→`administration`

Raw domain/subdomain labels are never overwritten — preserved verbatim in `domain_raw`/`subdomain_raw` alongside the canonical `domain` field.

## D-RD-08 — Primary Cohort Size Policy

AMB-05 is no longer "pick a target N." Primary analysis cohort = every 025+026 pair that is G1 ingest-valid, G2/QC-accepted, survives exact-duplicate policy, and is Tier-A eligible. **No arbitrary fixed cap, no pre-analysis 100k sampling, no 500k convenience cap.** SSOT's 100,000+ (§9.1) is a recommended floor, not a ceiling. Final numeric N is a realized value of the QC/dedup pipeline, not chosen in advance — and is not written anywhere yet.

## Still open (not resolved by the above)

- Duplicate Analysis-Representative selection rule — `WAIT_FOR_TARGETED_EDA_RECON` (other agents actively investigating 025 direction×split duplicate decomposition)
- AMB-13-adjacent: none remaining
- Full detail and rationale: `docs/research/G1_DECISION_QUEUE_v1.md`
