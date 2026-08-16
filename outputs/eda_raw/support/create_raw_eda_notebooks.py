"""Create the three supporting raw EDA notebooks deterministically."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

WORKTREE = Path(__file__).resolve().parents[3]
PROJECT_RAW = Path("/home/sieg/projects-wsl/Tokenization_Premium/data/raw/aigub")
NOTEBOOK_DIR = WORKTREE / "notebooks/exploratory/raw"

CONFIGS = [
    {
        "dataset_local_id": "AIHUB_025",
        "dataset_title": "AIHub 025 일상생활·구어체 한–영 병렬 말뭉치",
        "short_name": "daily_conversation_parallel",
        "artifact_prefix": "aihub_025",
        "raw_dir": str(PROJECT_RAW / "025.일상생활 및 구어체 한-영 번역 병렬 말뭉치 데이터"),
        "mapping": "Training/Validation × EN→KO and KO→EN JSON; byte-identical source/label aliases and one validation ZIP",
        "category_plot_dimensions": ["domain", "subdomain", "source", "source_language"],
    },
    {
        "dataset_local_id": "AIHUB_026",
        "dataset_title": "AIHub 026 기술과학 분야 한–영 병렬 말뭉치",
        "short_name": "tech_science_parallel",
        "artifact_prefix": "aihub_026",
        "raw_dir": str(PROJECT_RAW / "026.기술과학 분야 한-영 번역 병렬 말뭉치 데이터"),
        "mapping": "Training/Validation × KO→EN JSON; byte-identical source/label aliases",
        "category_plot_dimensions": ["domain", "subdomain", "source", "source_language"],
    },
    {
        "dataset_local_id": "LOCAL_KO_EN_PARALLEL_XLSX_V1",
        "dataset_title": "Local legacy 한국어–영어 번역 병렬 XLSX family",
        "short_name": "legacy_ko_en_parallel_xlsx",
        "artifact_prefix": "legacy_ko_en_xlsx",
        "raw_dir": str(PROJECT_RAW / "한국어-영어 번역(병렬) 말뭉치"),
        "mapping": "10 XLSX workbooks grouped as 구어체·대화체·뉴스·한국문화·조례·지자체웹; official AIHub ID UNKNOWN",
        "category_plot_dimensions": ["대분류", "언론사", "자동분류1", "지자체"],
    },
]


def markdown(text: str, cell_id: str):
    cell = nbf.v4.new_markdown_cell(text)
    cell["id"] = cell_id
    return cell


def code(text: str, cell_id: str):
    cell = nbf.v4.new_code_cell(text)
    cell["id"] = cell_id
    return cell


def make_notebook(config: dict[str, str]) -> nbf.NotebookNode:
    config_literal = repr(config)
    cells = [
        markdown(f"""# PRE-INGESTION EXPLORATORY EDA — {config['dataset_title']}

> **Notebook status:** `SUPPORTING / EXPLORATORY / PRE-INGESTION EDA / NOT G1 PASS`

| Traceability field | Value |
|---|---|
| Dataset local ID | `{config['dataset_local_id']}` |
| Inspected raw path | `{config['raw_dir']}` |
| File-family mapping | {config['mapping']} |
| File hashes / source manifest | 이 notebook 실행 시 모든 physical file SHA-256과 `RAW_FILE_MANIFEST_SHA`를 계산해 아래 inventory 및 output CSV/JSON에 기록 |
| Audit timestamp | 실행 cell에서 local timezone ISO-8601로 기록 |
| Population scope | SHA-256 고유 JSON/XLSX content의 **FULL POPULATION aggregate** |
| Visualization sample | `BLAKE2b(seed=20260816) mod 1000 < 10`, 약 1%; scatter/sample preview에만 사용 |
| Raw mutation | 없음; `data/raw/**` read-only |

이 notebook은 raw 구조와 관측 분포를 시각적으로 이해하기 위한 supporting artifact다. pair validity, primary corpus 적합성, Tokenization Premium, 또는 QC acceptance를 판단하지 않는다.
""", "raw-eda-00-title"),
        markdown("""## 1. 실행 환경과 snapshot contract

질문: **어떤 raw file에서 어떤 범위로 계산했는가?**

아래 cell은 worktree root를 자동 탐색하고 공용 streaming helper를 불러온다. 외부 다운로드는 없다.
""", "raw-eda-01-contract-md"),
        code(f"""from pathlib import Path
import json, sys
from IPython.display import Markdown, display

def find_worktree_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / 'pyproject.toml').exists() and (candidate / 'outputs/eda_raw/support/raw_eda_framework.py').exists():
            return candidate
    raise FileNotFoundError('worktree root not found')

WORKTREE_ROOT = find_worktree_root(Path.cwd().resolve())
sys.path.insert(0, str(WORKTREE_ROOT / 'outputs/eda_raw/support'))
from raw_eda_framework import (
    profile_dataset, save_artifacts, plot_overview, plot_lengths,
    plot_categories, plot_quality,
)

CONFIG = {config_literal}
OUTPUT_DIR = WORKTREE_ROOT / 'outputs/eda_raw' / CONFIG['artifact_prefix']
FIGURE_DIR = WORKTREE_ROOT / 'outputs/figures/eda_raw' / CONFIG['artifact_prefix']
print('WORKTREE_ROOT =', WORKTREE_ROOT)
print('Python =', sys.executable)
print('RAW =', CONFIG['raw_dir'])
""", "raw-eda-02-setup"),
        markdown("""## 2. Full-population streaming profile

질문: **전체 모집단의 규모·스키마·결측·길이·category·noise·중복 신호는 무엇인가?**

- JSON은 top-level `data[]`를 순차 파싱한다.
- XLSX는 `openpyxl(read_only=True)`로 행을 순차 처리한다.
- byte-identical source/label copies는 inventory에는 남기되 내용 집계는 SHA-256당 한 번만 한다.
- audit 중 size/mtime이 달라지면 결과 저장 전에 실행을 중단한다.
""", "raw-eda-03-profile-md"),
        code("""result = profile_dataset(CONFIG)
save_artifacts(result, OUTPUT_DIR)
display(Markdown('### Snapshot summary'))
display(result['summary'])
display(Markdown('### Physical file inventory and SHA-256'))
display(result['inventory'])
""", "raw-eda-04-profile"),
        markdown("""## 3. 구조·규모·coverage

질문: **어떤 file group이 corpus 규모를 구성하고, core text/metadata coverage는 어떤가?**
""", "raw-eda-05-overview-md"),
        code("""display(result['record_counts'].sort_values('records', ascending=False))
display(result['schema'].sort_values(['missing_or_empty_rate', 'group', 'field'], ascending=[False, True, True]).head(30))
plot_overview(result, FIGURE_DIR)
""", "raw-eda-06-overview"),
        markdown("""## 4. KO/EN raw length structure

질문: **raw codepoint/UTF-8 byte 길이의 중심·꼬리와 KO–EN 관계가 group별로 어떻게 다른가?**

위쪽 분포선과 p50/p95는 full population이다. hexbin만 deterministic 약 1% sample이다.
""", "raw-eda-07-length-md"),
        code("""display(result['length_summary'].sort_values(['metric', 'group', 'language']))
plot_lengths(result, FIGURE_DIR)
""", "raw-eda-08-length"),
        markdown("""## 5. Domain/source/category composition

질문: **어떤 source/domain/category가 실제 row volume을 구성하는가?**

범주 수가 큰 field는 top raw value만 시각화하며, 전체 count table은 CSV artifact로 남긴다.
""", "raw-eda-09-category-md"),
        code("""top_categories = (result['categories'].groupby(['dimension', 'value'], as_index=False)['count'].sum()
                  .sort_values(['dimension', 'count'], ascending=[True, False])
                  .groupby('dimension').head(10))
display(top_categories)
plot_categories(result, FIGURE_DIR)
""", "raw-eda-10-category"),
        markdown("""## 6. Potential QC signals — acceptance가 아님

질문: **missing metadata, whitespace/script/markup 신호, raw duplicate 후보는 어디에 집중되는가?**

모든 항목은 `OBSERVED RAW DISTRIBUTION` 또는 `POTENTIAL QC ISSUE`다. 자동 오류 판정이나 정규화 근거가 아니다.
""", "raw-eda-11-quality-md"),
        code("""display(result['duplicates'])
display(result['noise'].sort_values('rows_per_100k', ascending=False).head(30))
plot_quality(result, FIGURE_DIR)
""", "raw-eda-12-quality"),
        markdown("""## 7. Deterministic sample structure

질문: **집계표 뒤의 실제 row 구조가 어떤 모습인가?**

아래 preview는 scatter와 동일한 deterministic hash sample 중 일부다. `ko_preview`/`en_preview`는 표시 길이를 160 codepoint로 제한하며 원문을 수정하지 않는다.
""", "raw-eda-13-sample-md"),
        code("""sample_columns = [c for c in ['group','relative_path','row_number','pair_key','ko_preview','en_preview','ko_codepoints','en_codepoints','domain','subdomain','source','대분류','소분류','상황','언론사','키워드','지자체'] if c in result['samples'].columns]
display(result['samples'][sample_columns].head(12))
print(f"sample rows = {len(result['samples']):,}; full logical records = {result['summary']['logical_record_count']:,}")
""", "raw-eda-14-sample"),
        markdown("""## 8. Interpretation scaffold

**Target 설계:** 이 supporting EDA에는 modeling target이 없다. 관찰 단위는 raw KO–EN pair와 file/group metadata다.

**관찰:** 실행 결과의 full-population tables와 네 개 figure에서 규모, 길이, 범주, 결측/noise 위치를 확인한다.

**원인 가설:** source, domain, 번역 방향, 문체, file generation 방식이 분포 차이에 관련될 수 있으나 이 notebook은 원인을 검정하지 않는다.

**제한:** deterministic sample plot은 모집단 aggregate가 아니며, 64-bit hash duplicate count에는 collision 가능성이 있다. 외부 AIHub 문서와 공식 release completeness는 확인하지 않는다.

**결론:** `OBSERVED RAW DISTRIBUTION`, `STRUCTURAL DATA CHARACTERISTIC`, `POTENTIAL QC ISSUE`, `REQUIRES RECONCILIATION` 범위에서만 해석한다. **NOT G1 PASS.**
""", "raw-eda-15-interpretation"),
    ]
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Tokenization Premium", "language": "python", "name": "tokenization_premium"},
        "language_info": {"name": "python", "version": "3.12"},
        "raw_eda": {"dataset_local_id": config["dataset_local_id"], "status": "SUPPORTING_EXPLORATORY_NOT_G1_PASS", "sampling_seed": 20260816},
    }
    return notebook


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for config in CONFIGS:
        path = NOTEBOOK_DIR / f"EDA_RAW_{config['dataset_local_id']}_{config['short_name']}.ipynb"
        nbf.write(make_notebook(config), path)
        print(path.relative_to(WORKTREE))


if __name__ == "__main__":
    main()
