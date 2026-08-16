"""Append aggregate-only PRE-G1 decision-audit sections to AIHub 025/026 EDA notebooks."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import nbformat


ROOT = Path(__file__).resolve().parents[3]
NOTEBOOK_DIR = ROOT / "notebooks/exploratory/raw"
MARKER = "targeted-decision-audit-20260816"
SELECTED = {item.strip() for item in os.environ.get("TARGET_APPENDIX", "025,026,legacy").split(",") if item.strip()}


def markdown(source: str, suffix: str):
    cell = nbformat.v4.new_markdown_cell(source)
    cell["id"] = f"targeted-{suffix}"
    cell["metadata"]["tags"] = [MARKER]
    return cell


def code(source: str, suffix: str):
    cell = nbformat.v4.new_code_cell(source)
    cell["id"] = f"targeted-{suffix}"
    cell["metadata"]["tags"] = [MARKER]
    return cell


COMMON = r'''
from collections import Counter
import hashlib
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from raw_eda_framework import configure_plotting, iter_json_data, json_path_meta

TARGET_OUTPUT_ROOT = WORKTREE_ROOT / "outputs/eda_raw/targeted_decision_audit"
TARGET_FIGURE_ROOT = WORKTREE_ROOT / "outputs/figures/eda_raw/targeted_decision_audit"
TARGET_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
TARGET_FIGURE_ROOT.mkdir(parents=True, exist_ok=True)

def unique_label_jsons(raw_dir):
    paths=[]
    for path in sorted(Path(raw_dir).rglob("*.json")):
        relative=path.relative_to(raw_dir).as_posix()
        if "/라벨링데이터/" in f"/{relative}":
            paths.append(path)
    return paths

def exact_pair_digest(ko, en):
    digest=hashlib.blake2b(digest_size=16, key=b"RAW_EDA_TARGET_20260816")
    for text in (str(ko or ""), str(en or "")):
        encoded=text.encode("utf-8", errors="strict")
        digest.update(len(encoded).to_bytes(8,"big")); digest.update(encoded)
    return digest.digest()

def save_aggregate(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path,index=False,encoding="utf-8-sig")

def save_target_figure(fig, name):
    path=TARGET_FIGURE_ROOT/name
    fig.savefig(path,dpi=160,bbox_inches="tight")
    plt.show()
    return path
'''


CODE_025_PROFILE = COMMON + r'''
RAW_025=Path(CONFIG["raw_dir"])
OUT_025=TARGET_OUTPUT_ROOT/"aihub_025"
cross_direction_split_domain=Counter()
cross_direction_source_domain=Counter()
canonical_preview=Counter()
packed_pair_counts={}
direction_shift={"EN_TO_KO":0,"KO_TO_EN":16}
split_shift={"TRAIN":32,"VALID":48}
record_total=0

for path in unique_label_jsons(RAW_025):
    relative=path.relative_to(RAW_025).as_posix()
    split,_,direction=json_path_meta(relative)
    for row in iter_json_data(path):
        domain=str(row.get("domain") or "<MISSING>")
        source=str(row.get("source") or "<MISSING>")
        cross_direction_split_domain[(direction,split,domain)] += 1
        cross_direction_source_domain[(direction,source,domain)] += 1
        mapped={"일상생활":"general","해외고객과의채팅":"dialogue","해외영업":"other"}.get(domain,"UNMAPPED_PREVIEW")
        canonical_preview[(domain,mapped)] += 1
        pair_hash=exact_pair_digest(row.get("ko"),row.get("en"))
        packed=packed_pair_counts.get(pair_hash,0)
        packed += 1 << direction_shift[direction]
        packed += 1 << split_shift[split]
        packed_pair_counts[pair_hash]=packed
        record_total += 1

direction_split_domain_df=pd.DataFrame([
    {"direction":direction,"split":split,"raw_domain":domain,"record_count":count}
    for (direction,split,domain),count in cross_direction_split_domain.items()
]).sort_values(["direction","split","raw_domain"])
direction_source_domain_df=pd.DataFrame([
    {"direction":direction,"raw_source":source,"raw_domain":domain,"record_count":count}
    for (direction,source,domain),count in cross_direction_source_domain.items()
]).sort_values(["direction","raw_source","raw_domain"])
domain_preview_025_df=pd.DataFrame([
    {"raw_domain":raw,"proposed_canonical_domain":mapped,"record_count":count}
    for (raw,mapped),count in canonical_preview.items()
]).sort_values(["proposed_canonical_domain","raw_domain"])

def unpack_pair_counts(value):
    return tuple((value >> shift) & 0xFFFF for shift in (0,16,32,48))

multiplicity=Counter(); direction_cells=np.zeros((2,2),dtype=np.int64); split_cells=np.zeros((2,2),dtype=np.int64)
mirror_candidate_rows=0; split_overlap_candidate_rows=0; total_duplicate_rows=0
mirror_groups=0; split_overlap_groups=0
for packed in packed_pair_counts.values():
    enko,koen,train,valid=unpack_pair_counts(packed)
    total=enko+koen
    multiplicity[total] += 1
    total_duplicate_rows += max(total-1,0)
    direction_cells[0,0] += max(enko-1,0); direction_cells[1,1] += max(koen-1,0)
    split_cells[0,0] += max(train-1,0); split_cells[1,1] += max(valid-1,0)
    mirrored=min(enko,koen); split_overlap=min(train,valid)
    mirror_candidate_rows += mirrored; split_overlap_candidate_rows += split_overlap
    mirror_groups += int(enko>0 and koen>0); split_overlap_groups += int(train>0 and valid>0)
direction_cells[0,1]=direction_cells[1,0]=mirror_candidate_rows
split_cells[0,1]=split_cells[1,0]=split_overlap_candidate_rows

duplicate_mechanism_025_df=pd.DataFrame([
    {"mechanism":"within EN_TO_KO","candidate_row_count":int(direction_cells[0,0]),"candidate_group_count":sum(1 for v in packed_pair_counts.values() if (v&0xFFFF)>1),"definition":"sum(max(n-1,0)) within direction"},
    {"mechanism":"within KO_TO_EN","candidate_row_count":int(direction_cells[1,1]),"candidate_group_count":sum(1 for v in packed_pair_counts.values() if ((v>>16)&0xFFFF)>1),"definition":"sum(max(n-1,0)) within direction"},
    {"mechanism":"EN_TO_KO <-> KO_TO_EN","candidate_row_count":mirror_candidate_rows,"candidate_group_count":mirror_groups,"definition":"sum(min(n_EN_TO_KO,n_KO_TO_EN)); cross-direction matchable rows"},
    {"mechanism":"within TRAIN","candidate_row_count":int(split_cells[0,0]),"candidate_group_count":sum(1 for v in packed_pair_counts.values() if ((v>>32)&0xFFFF)>1),"definition":"sum(max(n-1,0)) within split"},
    {"mechanism":"within VALID","candidate_row_count":int(split_cells[1,1]),"candidate_group_count":sum(1 for v in packed_pair_counts.values() if ((v>>48)&0xFFFF)>1),"definition":"sum(max(n-1,0)) within split"},
    {"mechanism":"TRAIN <-> VALID","candidate_row_count":split_overlap_candidate_rows,"candidate_group_count":split_overlap_groups,"definition":"sum(min(n_TRAIN,n_VALID)); cross-split matchable rows"},
])
duplicate_multiplicity_025_df=pd.DataFrame([
    {"duplicate_group_size":size,"exact_pair_group_count":count,"rows_in_groups":size*count,"duplicate_rows_after_first":(size-1)*count}
    for size,count in sorted(multiplicity.items()) if size>=2
])
duplicate_explanation_025_df=pd.DataFrame([{
    "full_population_rows":record_total,
    "distinct_exact_pair_groups":len(packed_pair_counts),
    "duplicate_rows_after_first":total_duplicate_rows,
    "direction_mirror_matchable_rows":mirror_candidate_rows,
    "direction_mirror_share_of_duplicate_rows":mirror_candidate_rows/max(1,total_duplicate_rows),
    "cross_split_matchable_rows":split_overlap_candidate_rows,
    "interpretation":"candidate structural explanation only; not causal provenance or QC acceptance",
}])

sbs=direction_source_domain_df[direction_source_domain_df.raw_source.eq("SBS")]
sbs_check_025_df=pd.DataFrame([{
    "SBS_record_count":int(sbs.record_count.sum()),
    "SBS_outside_KO_TO_EN_count":int(sbs.loc[~sbs.direction.eq("KO_TO_EN"),"record_count"].sum()),
    "SBS_outside_daily_life_domain_count":int(sbs.loc[~sbs.raw_domain.eq("일상생활"),"record_count"].sum()),
    "observed_only_in_KO_TO_EN_and_daily_life":bool(len(sbs) and sbs.direction.eq("KO_TO_EN").all() and sbs.raw_domain.eq("일상생활").all()),
}])
crowd_variant_025_df=direction_source_domain_df[direction_source_domain_df.raw_source.isin(["크라우드 소싱","크라우드소싱"])].copy()
crowd_variant_025_df["eda_interpretation"]="distinct raw categorical strings; spelling/provenance equivalence requires documentation"

for frame,name in [
    (direction_split_domain_df,"direction_split_domain_full_population.csv"),
    (direction_source_domain_df,"direction_source_domain_full_population.csv"),
    (duplicate_mechanism_025_df,"duplicate_mechanism_decomposition.csv"),
    (duplicate_multiplicity_025_df,"duplicate_group_multiplicity.csv"),
    (duplicate_explanation_025_df,"duplicate_direction_mirroring_explanation.csv"),
    (sbs_check_025_df,"sbs_scope_check.csv"),
    (crowd_variant_025_df,"crowd_source_variant_observation.csv"),
    (domain_preview_025_df,"canonical_domain_mapping_preview.csv"),
]: save_aggregate(frame,OUT_025/name)

print(f"025 targeted full-population pass complete: {record_total:,} rows; no raw text exported")
'''


CODE_025_RENDER = r'''
display(Markdown("### 9.1 Full-population direction × split × raw domain"))
display(direction_split_domain_df.pivot_table(index=["direction","split"],columns="raw_domain",values="record_count",fill_value=0,aggfunc="sum"))
display(Markdown("### 9.2 Full-population direction × raw source × raw domain"))
display(direction_source_domain_df.pivot_table(index=["direction","raw_source"],columns="raw_domain",values="record_count",fill_value=0,aggfunc="sum"))
display(Markdown("### 9.3 SBS and crowd-source string observations"))
display(sbs_check_025_df); display(crowd_variant_025_df)
display(Markdown("`크라우드 소싱`과 `크라우드소싱`은 raw category상 서로 다른 정확 문자열이다. 이 notebook은 spelling variant인지 다른 provenance인지 결정하지 않는다."))
display(Markdown("### 9.4 Exact-pair duplicate mechanism decomposition"))
display(duplicate_mechanism_025_df); display(duplicate_explanation_025_df); display(duplicate_multiplicity_025_df)
display(Markdown("Direction mirroring 설명분은 양 방향에서 1:1로 매칭 가능한 동일 raw KO+EN 행 수이다. 중복 원인이나 provenance를 확정하지 않는다."))
display(Markdown("### 9.5 Proposed canonical-domain mapping — count-only preview"))
display(domain_preview_025_df)

configure_plotting()
fig,axes=plt.subplots(1,2,figsize=(15,5),constrained_layout=True)
for axis,matrix,labels,title in [
    (axes[0],direction_cells,["EN_TO_KO","KO_TO_EN"],"Direction: diagonal=within duplicate rows\noff-diagonal=cross-direction matchable rows"),
    (axes[1],split_cells,["TRAIN","VALID"],"Split: diagonal=within duplicate rows\noff-diagonal=cross-split matchable rows"),
]:
    image=axis.imshow(matrix,cmap="YlOrRd",aspect="auto")
    axis.set_xticks(range(2),labels); axis.set_yticks(range(2),labels); axis.set_title(title)
    for i in range(2):
        for j in range(2): axis.text(j,i,f"{matrix[i,j]:,}",ha="center",va="center")
    fig.colorbar(image,ax=axis,shrink=.75,label="candidate rows")
fig.suptitle("AIHub 025 — exact-pair duplicate mechanism candidates (full population)",fontsize=16,fontweight="bold")
save_target_figure(fig,"aihub_025_duplicate_mechanism_heatmap.png")

fig,axes=plt.subplots(1,2,figsize=(15,5),constrained_layout=True)
axes[0].scatter(duplicate_multiplicity_025_df.duplicate_group_size,duplicate_multiplicity_025_df.exact_pair_group_count,s=24,alpha=.75,color="#DC2626")
axes[0].set_xscale("log"); axes[0].set_yscale("log")
axes[0].set_title("Exact-pair duplicate group multiplicity\nall observed sizes; log-log scale"); axes[0].set_xlabel("group size"); axes[0].set_ylabel("groups")
preview=domain_preview_025_df.sort_values("record_count")
axes[1].barh(preview.raw_domain+" → "+preview.proposed_canonical_domain,preview.record_count,color="#2563EB")
axes[1].set_title("Proposed domain mapping: count-only EDA preview"); axes[1].set_xlabel("records")
fig.suptitle("AIHub 025 — PRE-G1 targeted distributions",fontsize=16,fontweight="bold")
save_target_figure(fig,"aihub_025_multiplicity_domain_preview.png")
'''


CODE_026_PROFILE = COMMON + r'''
RAW_026=Path(CONFIG["raw_dir"])
OUT_026=TARGET_OUTPUT_ROOT/"aihub_026"
source_domain=Counter(); canonical_preview=Counter(); record_total_026=0
for path in unique_label_jsons(RAW_026):
    for row in iter_json_data(path):
        source=str(row.get("source") or "<MISSING>")
        domain=str(row.get("domain") or "<MISSING>")
        source_domain[(source,domain)] += 1
        canonical_preview[(domain,"technology" if domain=="기술과학" else "other")] += 1
        record_total_026 += 1

source_domain_026_df=pd.DataFrame([
    {"raw_source":source,"raw_domain":domain,"record_count":count}
    for (source,domain),count in source_domain.items()
]).sort_values(["raw_source","raw_domain"])
domain_preview_026_df=pd.DataFrame([
    {"raw_domain":raw,"proposed_canonical_domain":mapped,"record_count":count}
    for (raw,mapped),count in canonical_preview.items()
]).sort_values(["proposed_canonical_domain","raw_domain"])
patent_source_count=sum(count for (source,_),count in source_domain.items() if source=="특허정보원")
technology_domain_count=sum(count for (_,domain),count in source_domain.items() if domain=="기술과학")
joint_count=source_domain.get(("특허정보원","기술과학"),0)
patent_technology_check_026_df=pd.DataFrame([{
    "patent_source_record_count":patent_source_count,
    "technology_domain_record_count":technology_domain_count,
    "joint_record_count":joint_count,
    "patent_source_outside_technology_count":patent_source_count-joint_count,
    "technology_domain_outside_patent_source_count":technology_domain_count-joint_count,
    "row_level_biconditional_exact":bool(patent_source_count==technology_domain_count==joint_count),
    "evidence_scope":"LOCAL_OBSERVED row-level categorical equality only",
}])
for frame,name in [
    (source_domain_026_df,"source_domain_full_population.csv"),
    (patent_technology_check_026_df,"patent_technology_row_level_check.csv"),
    (domain_preview_026_df,"canonical_domain_mapping_preview.csv"),
]: save_aggregate(frame,OUT_026/name)
print(f"026 targeted full-population pass complete: {record_total_026:,} rows; no raw text exported")
'''


CODE_026_RENDER = r'''
display(Markdown("### 9.1 Full-population raw source × raw domain"))
source_domain_matrix_026=source_domain_026_df.pivot_table(index="raw_source",columns="raw_domain",values="record_count",fill_value=0,aggfunc="sum")
display(source_domain_matrix_026)
display(Markdown("### 9.2 특허정보원 ↔ 기술과학 row-level exact check"))
display(patent_technology_check_026_df)
display(Markdown("이 결과는 local raw category의 필요충분 대응 여부만 관찰한다. 공식 provenance나 domain 정의를 확정하지 않는다."))
display(Markdown("### 9.3 Proposed canonical-domain mapping — count-only preview"))
display(domain_preview_026_df)

configure_plotting()
fig,axes=plt.subplots(1,2,figsize=(16,6),constrained_layout=True)
matrix=source_domain_matrix_026
image=axes[0].imshow(matrix.values,aspect="auto",cmap="Blues")
axes[0].set_xticks(range(len(matrix.columns)),matrix.columns,rotation=35,ha="right")
axes[0].set_yticks(range(len(matrix.index)),matrix.index)
axes[0].set_title("Raw source × raw domain (full population)")
fig.colorbar(image,ax=axes[0],shrink=.75,label="records")
preview=domain_preview_026_df.sort_values("record_count")
colors=np.where(preview.proposed_canonical_domain.eq("technology"),"#2563EB","#94A3B8")
axes[1].barh(preview.raw_domain+" → "+preview.proposed_canonical_domain,preview.record_count,color=colors)
axes[1].set_title("Proposed domain mapping: count-only EDA preview"); axes[1].set_xlabel("records")
fig.suptitle("AIHub 026 — PRE-G1 targeted source/domain audit",fontsize=16,fontweight="bold")
save_target_figure(fig,"aihub_026_source_domain_mapping_preview.png")
'''


CODE_LEGACY_PROFILE = COMMON + r'''
from raw_eda_framework import iter_xlsx_rows

RAW_LEGACY=Path(CONFIG["raw_dir"])
OUT_LEGACY=TARGET_OUTPUT_ROOT/"legacy_news2_culture"
NEWS2_PATH=RAW_LEGACY/"3_문어체_뉴스(2).xlsx"
CULTURE_PATH=RAW_LEGACY/"4_문어체_한국문화.xlsx"

def workbook_pair_counts(path):
    header,rows=iter_xlsx_rows(path); counts=Counter(); total=0
    for _,row in rows:
        counts[exact_pair_digest(row.get("원문"),row.get("번역문"))] += 1
        total += 1
    return counts,total

news_counts,news_total=workbook_pair_counts(NEWS2_PATH)
culture_counts,culture_total=workbook_pair_counts(CULTURE_PATH)
overlap_hashes=set(news_counts).intersection(culture_counts)
news_overlap_rows=sum(news_counts[key] for key in overlap_hashes)
culture_overlap_rows=sum(culture_counts[key] for key in overlap_hashes)
matchable_overlap_rows=sum(min(news_counts[key],culture_counts[key]) for key in overlap_hashes)

overlap_summary_legacy_df=pd.DataFrame([{
    "overlap_exact_pair_group_count":len(overlap_hashes),
    "one_to_one_matchable_overlap_count":matchable_overlap_rows,
    "news2_total_rows":news_total,
    "news2_rows_in_overlap_groups":news_overlap_rows,
    "news2_overlap_row_rate":news_overlap_rows/max(1,news_total),
    "culture_total_rows":culture_total,
    "culture_rows_in_overlap_groups":culture_overlap_rows,
    "culture_overlap_row_rate":culture_overlap_rows/max(1,culture_total),
    "status":"POTENTIAL CORPUS COMPOSITION OVERLAP",
    "interpretation":"exact raw KO+EN only; no error, provenance, or QC conclusion",
}])

overlap_multiplicity_legacy_df=pd.DataFrame([
    {
        "news2_group_multiplicity":news_n,
        "culture_group_multiplicity":culture_n,
        "combined_group_multiplicity":news_n+culture_n,
        "exact_pair_group_count":count,
        "status":"POTENTIAL CORPUS COMPOSITION OVERLAP",
    }
    for (news_n,culture_n),count in sorted(Counter((news_counts[key],culture_counts[key]) for key in overlap_hashes).items())
])

metadata_counts=Counter()
for corpus,path,fields in [
    ("NEWS2",NEWS2_PATH,["날짜","자동분류1","자동분류2","자동분류3","언론사"]),
    ("CULTURE",CULTURE_PATH,["키워드"]),
]:
    _,rows=iter_xlsx_rows(path)
    for _,row in rows:
        if exact_pair_digest(row.get("원문"),row.get("번역문")) not in overlap_hashes:
            continue
        for field in fields:
            value=str(row.get(field) if row.get(field) not in (None,"") else "<MISSING>")
            metadata_counts[(corpus,field,value)] += 1

overlap_metadata_legacy_df=pd.DataFrame([
    {"corpus":corpus,"metadata_field":field,"category":value,"overlap_row_count":count}
    for (corpus,field,value),count in metadata_counts.items()
]).sort_values(["corpus","metadata_field","overlap_row_count"],ascending=[True,True,False])
concentration_rows=[]
for (corpus,field),part in overlap_metadata_legacy_df.groupby(["corpus","metadata_field"]):
    counts=part.overlap_row_count.sort_values(ascending=False); denominator=int(counts.sum())
    concentration_rows.append({
        "corpus":corpus,"metadata_field":field,"overlap_rows_with_field":denominator,
        "unique_category_count":len(counts),"top1_share":counts.head(1).sum()/max(1,denominator),
        "top5_share":counts.head(5).sum()/max(1,denominator),"top10_share":counts.head(10).sum()/max(1,denominator),
        "status":"DESCRIPTIVE CONCENTRATION ONLY / POTENTIAL CORPUS COMPOSITION OVERLAP",
    })
overlap_concentration_legacy_df=pd.DataFrame(concentration_rows)

for frame,name in [
    (overlap_summary_legacy_df,"news2_culture_overlap_summary.csv"),
    (overlap_multiplicity_legacy_df,"news2_culture_overlap_multiplicity.csv"),
    (overlap_metadata_legacy_df,"news2_culture_overlap_metadata_distribution.csv"),
    (overlap_concentration_legacy_df,"news2_culture_overlap_concentration.csv"),
]: save_aggregate(frame,OUT_LEGACY/name)
print(f"Legacy overlap pass complete: matchable={matchable_overlap_rows:,}; no raw text or pair hashes exported")
'''


CODE_LEGACY_RENDER = r'''
display(Markdown("### 9.1 뉴스(2) ↔ 한국문화 exact raw KO/EN overlap"))
display(overlap_summary_legacy_df)
display(Markdown("### 9.2 Overlap duplicate-group multiplicity"))
display(overlap_multiplicity_legacy_df)
display(Markdown("### 9.3 Available metadata distributions within overlap rows"))
for (corpus,field),part in overlap_metadata_legacy_df.groupby(["corpus","metadata_field"]):
    display(Markdown(f"#### {corpus} · {field}")); display(part.head(20))
display(Markdown("### 9.4 Descriptive subset concentration"))
display(overlap_concentration_legacy_df)
display(Markdown("이 appendix는 exact raw pair의 구성 중첩만 관찰한다. 오류·오염·제외·provenance 동일성을 판정하지 않으며 상태는 **POTENTIAL CORPUS COMPOSITION OVERLAP**이다."))

configure_plotting()
fig,axes=plt.subplots(2,2,figsize=(16,11),constrained_layout=True)
summary=overlap_summary_legacy_df.iloc[0]
axes[0,0].bar(["뉴스(2)","한국문화"],[summary.news2_overlap_row_rate,summary.culture_overlap_row_rate],color=["#0F766E","#7C3AED"])
axes[0,0].set_title("Rows in cross-workbook overlap groups"); axes[0,0].set_ylabel("share of workbook rows"); axes[0,0].set_ylim(0,max(.03,summary.culture_overlap_row_rate*1.2))
for i,value in enumerate([summary.news2_overlap_row_rate,summary.culture_overlap_row_rate]): axes[0,0].text(i,value,f"{value:.3%}",ha="center",va="bottom")

mult=overlap_multiplicity_legacy_df.groupby("combined_group_multiplicity",as_index=False).exact_pair_group_count.sum()
axes[0,1].bar(mult.combined_group_multiplicity.astype(str),mult.exact_pair_group_count,color="#DC2626")
axes[0,1].set_title("Overlap exact-pair group multiplicity"); axes[0,1].set_xlabel("combined group size"); axes[0,1].set_ylabel("groups")

news_top=overlap_metadata_legacy_df[(overlap_metadata_legacy_df.corpus=="NEWS2") & (overlap_metadata_legacy_df.metadata_field=="자동분류1")].head(12).sort_values("overlap_row_count")
axes[1,0].barh(news_top.category.astype(str).str.slice(0,36),news_top.overlap_row_count,color="#2563EB")
axes[1,0].set_title("뉴스(2) overlap: 자동분류1 top categories"); axes[1,0].set_xlabel("overlap rows")

culture_top=overlap_metadata_legacy_df[(overlap_metadata_legacy_df.corpus=="CULTURE") & (overlap_metadata_legacy_df.metadata_field=="키워드")].head(12).sort_values("overlap_row_count")
axes[1,1].barh(culture_top.category.astype(str).str.slice(0,36),culture_top.overlap_row_count,color="#7C3AED")
axes[1,1].set_title("한국문화 overlap: 키워드 top categories"); axes[1,1].set_xlabel("overlap rows")
fig.suptitle("뉴스(2) ↔ 한국문화 — POTENTIAL CORPUS COMPOSITION OVERLAP",fontsize=16,fontweight="bold")
save_target_figure(fig,"legacy_news2_culture_overlap_composition.png")

concentration=overlap_concentration_legacy_df.set_index(["corpus","metadata_field"])[["top1_share","top5_share","top10_share"]]
fig,ax=plt.subplots(figsize=(11,6),constrained_layout=True)
image=ax.imshow(concentration.values,aspect="auto",cmap="YlGnBu",vmin=0,vmax=1)
ax.set_xticks(range(3),["top1 share","top5 share","top10 share"])
ax.set_yticks(range(len(concentration)),[" · ".join(idx) for idx in concentration.index])
for i in range(len(concentration)):
    for j in range(3): ax.text(j,i,f"{concentration.iloc[i,j]:.1%}",ha="center",va="center")
ax.set_title("Overlap subset concentration by available metadata\nDescriptive only; no inferential or QC claim")
fig.colorbar(image,ax=ax,label="share of overlap rows")
save_target_figure(fig,"legacy_news2_culture_overlap_concentration.png")
'''


def append_cells(path: Path, cells: list) -> None:
    notebook = nbformat.read(path, as_version=4)
    notebook.cells = [cell for cell in notebook.cells if MARKER not in cell.get("metadata", {}).get("tags", [])]
    notebook.cells.extend(cells)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)


if "025" in SELECTED:
    append_cells(
        NOTEBOOK_DIR / "EDA_RAW_AIHUB_025_daily_conversation_parallel.ipynb",
        [
        markdown(
            """## 9. Targeted PRE-G1 identifiability / duplicate decision audit

이 appendix만 추가한다. 기존 EDA baseline은 유지한다. Full-population aggregate만 저장하며
tokenization·morphology·inference·QC acceptance·canonical pair registry를 수행하지 않는다.
Proposed domain mapping은 count-only preview이며 canonical data를 저장하지 않는다.""",
            "025-md",
        ),
        code(CODE_025_PROFILE, "025-profile"),
        code(CODE_025_RENDER, "025-render"),
        ],
    )

if "026" in SELECTED:
    append_cells(
        NOTEBOOK_DIR / "EDA_RAW_AIHUB_026_tech_science_parallel.ipynb",
        [
        markdown(
            """## 9. Targeted PRE-G1 source/domain decision audit

이 appendix만 추가한다. 기존 EDA baseline은 유지한다. Full-population aggregate만 저장하며
tokenization·morphology·inference·QC acceptance·canonical pair registry를 수행하지 않는다.
Proposed domain mapping은 count-only preview이며 canonical data를 저장하지 않는다.""",
            "026-md",
        ),
        code(CODE_026_PROFILE, "026-profile"),
        code(CODE_026_RENDER, "026-render"),
        ],
    )

if "legacy" in SELECTED:
    append_cells(
        NOTEBOOK_DIR / "EDA_RAW_LOCAL_KO_EN_PARALLEL_XLSX_V1_legacy_ko_en_parallel_xlsx.ipynb",
        [
        markdown(
            """## 9. Targeted 뉴스(2) ↔ 한국문화 composition-overlap audit

Full-population exact raw KO/EN overlap을 재계산하고 양쪽 분모 비율·multiplicity·available metadata 집중도를 집계한다.
원문·pair hash는 저장하지 않는다. 이 관찰은 오류나 QC 판정이 아니며 상태는
**POTENTIAL CORPUS COMPOSITION OVERLAP**로만 기록한다.""",
            "legacy-md",
        ),
        code(CODE_LEGACY_PROFILE, "legacy-profile"),
        code(CODE_LEGACY_RENDER, "legacy-render"),
        ],
    )

print("targeted appendices installed")

if os.environ.get("RESTORE_BASELINE_FROM_GIT") == "1":
    for path in NOTEBOOK_DIR.glob("EDA_RAW_*.ipynb"):
        relative=path.relative_to(ROOT).as_posix()
        baseline_text=subprocess.check_output(["git","-C",str(ROOT),"show",f"HEAD:{relative}"],text=True)
        baseline=nbformat.reads(baseline_text,as_version=4)
        current=nbformat.read(path,as_version=4)
        current.cells[:len(baseline.cells)]=baseline.cells
        current.metadata=baseline.metadata
        nbformat.validate(current)
        nbformat.write(current,path)
    print("baseline cells and notebook metadata restored; targeted appendices preserved")
