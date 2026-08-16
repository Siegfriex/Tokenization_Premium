# Translation Direction & Domain Mapping — Pre-G1 Precontract (v1)

Draft only. Domain mapping is explicitly **not frozen** here — per directive, final mapping waits for Raw EDA Agent's label-distribution results. Direction mapping is closer to final because the provenance signals are already visible in the raw schema.

## Task 5 — Translation Direction Mapping Contract

SSOT taxonomy (fixed): `KO_TO_EN | EN_TO_KO | HUMAN_PARALLEL_UNKNOWN | UNKNOWN`

### Rule for JSON corpora (025, 026)

Provenance signals available per data-recon: `source_language`, `target_language`, `ko_original` (present only in 한→영 files), `en_original` (present only in 영→한 files). Data-recon confirmed `source_language`/`target_language` values are **consistent with file direction** in the observed data.

```text
IF en_original present AND source_language/target_language consistent with EN→KO:
    translation_direction = EN_TO_KO

IF ko_original present AND source_language/target_language consistent with KO→EN:
    translation_direction = KO_TO_EN

IF source_language/target_language present but neither ko_original nor en_original present:
    → fall back to filename/folder direction convention (영한/한영) as a WEAKER signal only
    → flag translation_direction_review_flag = true

IF source_language/target_language CONTRADICTS ko_original/en_original presence:
    translation_direction = UNKNOWN
    → route to manual review, do not silently pick one side
```

Applied to observed local data: 025 TL1/VL1 (영한 files) → `EN_TO_KO`; 025 TL2/VL1(한영) → `KO_TO_EN`; 026 (한영 only) → 100% `KO_TO_EN`, no reverse-direction subset exists.

### Rule for Legacy XLSX

No `source_language`/`target_language` column, no `ko_original`/`en_original` staging field exists in any of the 10 workbooks. Per directive instruction, filename convention alone (e.g., inferring direction from a workbook's topic name) must **not** be used to assert direction.

```text
Legacy 원문/번역문 rows → translation_direction = HUMAN_PARALLEL_UNKNOWN
```

This is a deliberate use of the SSOT's `HUMAN_PARALLEL_UNKNOWN` value rather than plain `UNKNOWN`: the data unambiguously *is* a human-produced parallel pair (원문=original text, 번역문=translated text, by column naming), it is only the source→target language direction that is not machine-recorded. `UNKNOWN` is reserved for cases where even parallel-pair status is in doubt.

## Task 6 — Domain Mapping Precontract (DRAFT, NOT FROZEN)

SSOT taxonomy (fixed): `general | administration | legal | news | technology | education | dialogue | other`

**Principles** (all four are binding regardless of which mapping is eventually chosen):
1. Preserve the source's raw label (`domain_raw`, `subdomain_raw`) unmodified alongside the canonical `domain` field — never overwrite raw labels, including literal-string variants like "크라우드 소싱" vs "크라우드소싱" in 025.
2. `domain` (canonical) is a separate, additional field — not a renaming of the raw label.
3. When mapping confidence is low, map to `other` rather than forcing a fit.
4. Never conflate `source_id` and `domain` — a single source can span domains and a domain can span sources; do not let one stand in for the other (this is exactly the confounding SSOT T-04 and the Identifiability Gate §20.2 are designed to catch).

### Draft mapping table

| Local family/workbook | Raw label evidence available | Draft canonical `domain` | Confidence | Why not frozen |
|---|---|---|---|---|
| 025 (전체) | 3 domains / 11 subdomains — **counts only, literal label strings not yet enumerated** by data-recon | *(pending)* | — | Cannot responsibly map a label we have not seen; requires Raw EDA's label enumeration |
| 026 (전체) | 5 domains / 15 subdomains, corpus-level title "기술과학"(tech-science), sources = 한국연구재단/특허정보원 | `technology` | MEDIUM-HIGH (corpus-level only) | Corpus-level label is unambiguous; 15 subdomain literal values still unseen, so subdomain-level mapping is pending |
| Legacy 구어체(1)/(2) | No domain column at all in this workbook's schema | `other` (with `domain_raw=null`) | LOW | No raw signal exists to map from |
| Legacy 대화체 | 대분류(5): 여행/쇼핑(46,524), 비즈니스(28,064), 일상대화(24,012), + 2 more unlisted-count categories | `dialogue` | HIGH | Category labels directly match SSOT's `dialogue` value |
| Legacy 뉴스(1-4) | 자동분류1/2/3 (3-tier, many empty), publisher names (국민일보/서울경제/한겨레 등) | `news` | HIGH | Direct match; publisher metadata corroborates |
| Legacy 한국문화 | 키워드 102종 (keyword list, not a domain/category field) | `general` or `other` — **judgment call, not resolved here** | LOW | "Korean culture" content doesn't cleanly fit any single SSOT value; keyword list ≠ domain category |
| Legacy 조례 (ordinances) | 지자체 54종 (municipality names only, no genre field) | `legal` (lean) vs `administration` (alternative) — **boundary case, not resolved here** | LOW-MEDIUM | Ordinances are municipal statute text (favors `legal`), but they are also administrative-government output (favors `administration`); SSOT treats these as distinct taxonomy values so a Director call is needed |
| Legacy 지자체웹사이트 (local gov website) | 지자체 4종 | `administration` | MEDIUM | Government website content fits administrative domain more directly than legal |

**Two explicit boundary cases flagged for Research Director** (not Raw-EDA-blocked, since the ambiguity is conceptual, not a missing-label problem): 한국문화 (general vs other) and 조례 (legal vs administration). See decision queue.

**Everything else in this table is DRAFT and explicitly not frozen** until Raw EDA Agent reports the actual enumerated label distributions for 025's 3 domains/11 subdomains and 026's 15 subdomains.
