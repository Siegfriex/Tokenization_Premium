# ruff: noqa: E501
"""Build bounded G1 duplicate/split/analysis-unit decision-support evidence.

This script reads canonical Phase-1 registry artifacts without mutating them.
It deliberately excludes all KO/EN text-bearing columns from every query and
does not perform normalization, QC disposition, tokenization, or model fitting.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from matplotlib import font_manager
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VERSION = "v001"
ARTIFACT_STEM = "EDA_G1"
ANALYSIS_BASE_COMMIT = "691a378d2047eb4e4d18c2c5060cd6c2498f77fe"
SAMPLE_SEED = 20260816
KST = ZoneInfo("Asia/Seoul")
MISSING = "<MISSING>"
PRIMARY_CORPORA = ("025", "026")
KNOWN_DIRECTIONS = ("KO_TO_EN", "EN_TO_KO", "HUMAN_PARALLEL_UNKNOWN")

REPORT_DIR = PROJECT_ROOT / "outputs/reports/eda_g1_decision_support"
MANIFEST_DIR = PROJECT_ROOT / "outputs/manifests/eda_g1_decision_support"
FIGURE_DIR = PROJECT_ROOT / "outputs/figures/eda_g1_decision_support"
RUNTIME_DIR = PROJECT_ROOT / ".runtime/eda_g1_decision_support"

REPORT_PATH = REPORT_DIR / "EDA_G1_DUPLICATE_DECISION_SUPPORT_v001.md"
SUMMARY_PATH = REPORT_DIR / "EDA_G1_DUPLICATE_DECISION_SUPPORT_v001.csv"
GROUP_PROFILE_PATH = REPORT_DIR / "EDA_G1_DUPLICATE_GROUP_PROFILE_v001.parquet"
SPLIT_MATRIX_PATH = REPORT_DIR / "EDA_G1_SPLIT_LEAKAGE_MATRIX_v001.csv"
IDENTIFIABILITY_PATH = REPORT_DIR / "EDA_G1_IDENTIFIABILITY_CROSSTABS_v001.parquet"
MANUAL_FRAME_PATH = REPORT_DIR / "EDA_G1_MANUAL_QC_SAMPLING_FRAME_v001.csv"
DECISION_REQUESTS_PATH = REPORT_DIR / "DECISION_REQUESTS_v001.md"
STRATUM_PROFILE_PATH = REPORT_DIR / "EDA_G1_DUPLICATE_STRATUM_PROFILE_v001.csv"
CROSS_DIRECTION_PATH = REPORT_DIR / "EDA_G1_CROSS_DIRECTION_PROFILE_v001.csv"
SCENARIO_PATH = REPORT_DIR / "EDA_G1_POLICY_SCENARIOS_v001.csv"
IDENTIFIABILITY_DIAGNOSTICS_PATH = REPORT_DIR / "EDA_G1_IDENTIFIABILITY_DIAGNOSTICS_v001.csv"
MANIFEST_PATH = MANIFEST_DIR / "EDA_G1_DECISION_SUPPORT_MANIFEST_v001.json"
MANIFEST_SHA_PATH = MANIFEST_DIR / "EDA_G1_DECISION_SUPPORT_MANIFEST_v001.sha256"

FIGURES = {
    "F01": FIGURE_DIR / "F01_DUPLICATE_GROUP_SIZE_DISTRIBUTION_v001",
    "F02": FIGURE_DIR / "F02_DUPLICATE_BURDEN_BY_CORPUS_SOURCE_v001",
    "F03": FIGURE_DIR / "F03_CROSS_DIRECTION_COMPOSITION_v001",
    "F04": FIGURE_DIR / "F04_UPSTREAM_SPLIT_LEAKAGE_MATRIX_v001",
    "F05": FIGURE_DIR / "F05_IDENTIFIABILITY_HEATMAPS_v001",
    "F06": FIGURE_DIR / "F06_SCENARIO_COMPOSITION_IMPACT_v001",
    "F07": FIGURE_DIR / "F07_MANUAL_QC_ALLOCATION_v001",
    "F08": FIGURE_DIR / "F08_DIRECTOR_DECISION_DASHBOARD_v001",
}


def log(message: str) -> None:
    timestamp = dt.datetime.now(tz=KST).isoformat(timespec="seconds")
    print(f"[{timestamp}] {message}", flush=True)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def quote_sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def as_int(value: Any) -> int:
    return int(value) if not pd.isna(value) else 0


def fmt_int(value: Any) -> str:
    return f"{as_int(value):,}"


def fmt_pct(value: Any, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value) * 100:.{digits}f}%"


def safe_label(value: Any, limit: int = 38) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def configure_plotting() -> dict[str, str | None]:
    font_path: str | None = None
    family: str | None = None
    priorities = ("Noto Sans CJK KR", "Noto Sans KR", "NanumGothic")
    for candidate in sorted(font_manager.findSystemFonts()):
        try:
            candidate_family = font_manager.FontProperties(fname=candidate).get_name()
        except (RuntimeError, OSError):
            continue
        if candidate_family in priorities:
            font_path = candidate
            family = candidate_family
            break
    if family:
        matplotlib.rcParams["font.family"] = family
    matplotlib.rcParams.update(
        {
            "axes.unicode_minus": False,
            "figure.facecolor": "#F7F7F2",
            "axes.facecolor": "#FCFCF8",
            "savefig.facecolor": "#F7F7F2",
            "svg.fonttype": "none",
            "svg.hashsalt": "eda-g1-decision-support-v001",
            "axes.titleweight": "bold",
            "axes.edgecolor": "#5B6472",
            "grid.color": "#DDE2E6",
            "grid.alpha": 0.75,
        }
    )
    return {"family": family, "path": font_path}


def save_figure(fig: plt.Figure, base: Path) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(base.with_suffix(".png"), dpi=180, bbox_inches="tight", metadata={"Software": "EDA G1 decision support v001"})
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight", metadata={"Date": "2026-08-16", "Creator": "EDA G1 decision support v001"})
    plt.close(fig)


def validate_png(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        gray = image.convert("L")
        extrema = gray.getextrema()
        shape = [image.height, image.width, len(image.getbands())]
    if path.stat().st_size < 10_000 or extrema[0] == extrema[1]:
        raise AssertionError(f"non-trivial PNG validation failed: {path}")
    return {"path": path.relative_to(PROJECT_ROOT).as_posix(), "bytes": path.stat().st_size, "shape_hwc": shape, "gray_extrema": list(extrema)}


def hamilton_allocation(populations: np.ndarray, total: int, priority: np.ndarray | None = None, minimums: np.ndarray | None = None) -> np.ndarray:
    populations = populations.astype(int)
    scores = populations.astype(float) if priority is None else populations.astype(float) * priority.astype(float)
    minimums = np.zeros_like(populations) if minimums is None else np.minimum(minimums.astype(int), populations)
    if int(minimums.sum()) > total:
        raise ValueError("minimum allocation exceeds requested total")
    allocation = minimums.copy()
    remaining = total - int(allocation.sum())
    capacity = populations - allocation
    if remaining == 0:
        return allocation
    active_scores = np.where(capacity > 0, scores, 0.0)
    if active_scores.sum() <= 0:
        raise ValueError("no capacity for remaining allocation")
    quotas = remaining * active_scores / active_scores.sum()
    floors = np.minimum(np.floor(quotas).astype(int), capacity)
    allocation += floors
    remaining = total - int(allocation.sum())
    remainders = quotas - floors
    while remaining > 0:
        candidates = np.where(allocation < populations)[0]
        if not len(candidates):
            raise ValueError("allocation capacity exhausted")
        order = candidates[np.argsort(-remainders[candidates], kind="stable")]
        progressed = False
        for index in order:
            if remaining == 0:
                break
            if allocation[index] < populations[index]:
                allocation[index] += 1
                remainders[index] = -1.0
                remaining -= 1
                progressed = True
        if not progressed:
            raise ValueError("unable to complete allocation")
    return allocation


def add_summary(
    records: list[dict[str, Any]],
    *,
    scenario: str,
    metric: str,
    numerator: int | float | None,
    denominator: int | float | None,
    stratum: str,
    boundary: str,
    label: str = "DERIVED DESCRIPTIVE",
    detail: str = "",
) -> None:
    rate = None
    if numerator is not None and denominator not in (None, 0) and not pd.isna(numerator) and not pd.isna(denominator):
        rate = float(numerator) / float(denominator)
    records.append(
        {
            "scenario": scenario,
            "metric": metric,
            "numerator": numerator,
            "denominator": denominator,
            "rate": rate,
            "stratum": stratum,
            "evidence_label": label,
            "interpretation_boundary": boundary,
            "detail": detail,
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-registry", type=Path, default=PROJECT_ROOT / "data/registry/PAIR_REGISTRY_v001.parquet")
    parser.add_argument("--source-registry", type=Path, default=PROJECT_ROOT / "data/registry/SOURCE_REGISTRY_v001.parquet")
    parser.add_argument("--input-manifest", type=Path, default=PROJECT_ROOT / "outputs/manifests/PAIR_REGISTRY_MANIFEST_v001.json")
    parser.add_argument("--memory-limit", default="6GB")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--temp-directory", type=Path, default=Path("/tmp/tokenization_premium_eda_g1_duckdb"))
    return parser.parse_args()


def create_group_profile(connection: duckdb.DuckDBPyConnection, pair_path: Path) -> None:
    output = quote_sql_path(GROUP_PROFILE_PATH)
    pair = quote_sql_path(pair_path)
    sql = f"""
    COPY (
      SELECT
        duplicate_group_id,
        count(*)::BIGINT AS group_size,
        min(representative_pair_id) AS representative_pair_id,
        count(DISTINCT representative_pair_id)::INTEGER AS representative_pointer_count,
        string_agg(DISTINCT coalesce(logical_corpus, '{MISSING}'), ' | ' ORDER BY coalesce(logical_corpus, '{MISSING}')) AS logical_corpus_composition,
        count(DISTINCT coalesce(logical_corpus, '{MISSING}'))::INTEGER AS logical_corpus_level_count,
        string_agg(DISTINCT coalesce(source_id, '{MISSING}'), ' | ' ORDER BY coalesce(source_id, '{MISSING}')) AS source_id_composition,
        count(DISTINCT coalesce(source_id, '{MISSING}'))::INTEGER AS source_id_level_count,
        string_agg(DISTINCT coalesce(source_provenance_raw, '{MISSING}'), ' | ' ORDER BY coalesce(source_provenance_raw, '{MISSING}')) AS source_provenance_raw_composition,
        count(DISTINCT coalesce(source_provenance_raw, '{MISSING}'))::INTEGER AS source_provenance_raw_level_count,
        string_agg(DISTINCT coalesce(domain, '{MISSING}'), ' | ' ORDER BY coalesce(domain, '{MISSING}')) AS domain_composition,
        count(DISTINCT coalesce(domain, '{MISSING}'))::INTEGER AS domain_level_count,
        string_agg(DISTINCT coalesce(domain_raw, '{MISSING}'), ' | ' ORDER BY coalesce(domain_raw, '{MISSING}')) AS domain_raw_composition,
        count(DISTINCT coalesce(domain_raw, '{MISSING}'))::INTEGER AS domain_raw_level_count,
        string_agg(DISTINCT coalesce(translation_direction, '{MISSING}'), ' | ' ORDER BY coalesce(translation_direction, '{MISSING}')) AS translation_direction_composition,
        string_agg(DISTINCT coalesce(translation_direction_raw, '{MISSING}'), ' | ' ORDER BY coalesce(translation_direction_raw, '{MISSING}')) AS translation_direction_raw_composition,
        count(DISTINCT translation_direction_raw) FILTER (WHERE translation_direction_raw IN {KNOWN_DIRECTIONS})::INTEGER AS known_direction_count,
        bool_or(translation_direction_raw = 'UNKNOWN') AS has_unknown_direction,
        bool_or(translation_direction_raw IS NULL OR translation_direction_raw NOT IN ('KO_TO_EN', 'EN_TO_KO', 'HUMAN_PARALLEL_UNKNOWN', 'UNKNOWN')) AS has_missing_or_other_direction,
        sum(CASE WHEN is_validation_upstream = false THEN 1 ELSE 0 END)::BIGINT AS train_rows,
        sum(CASE WHEN is_validation_upstream = true THEN 1 ELSE 0 END)::BIGINT AS validation_rows,
        sum(CASE WHEN is_validation_upstream IS NULL THEN 1 ELSE 0 END)::BIGINT AS missing_split_rows,
        bool_or(is_validation_upstream = false) AS has_train,
        bool_or(is_validation_upstream = true) AS has_validation,
        bool_or(is_validation_upstream IS NULL) AS has_missing_split,
        string_agg(DISTINCT coalesce(sentence_type, '{MISSING}'), ' | ' ORDER BY coalesce(sentence_type, '{MISSING}')) AS sentence_type_composition,
        string_agg(DISTINCT coalesce(raw_file_relative_path, '{MISSING}'), ' | ' ORDER BY coalesce(raw_file_relative_path, '{MISSING}')) AS raw_file_composition,
        bool_or(direction_conflict_flag) AS direction_conflict_flag,
        bool_or(domain_conflict_flag) AS domain_conflict_flag,
        bool_or(source_id_conflict_flag) AS source_id_conflict_flag,
        bool_or(source_provenance_raw_conflict_flag) AS source_provenance_raw_conflict_flag,
        CASE
          WHEN bool_or(translation_direction_raw IS NULL OR translation_direction_raw NOT IN ('KO_TO_EN', 'EN_TO_KO', 'HUMAN_PARALLEL_UNKNOWN', 'UNKNOWN')) THEN 'missing/other metadata state'
          WHEN count(DISTINCT translation_direction_raw) FILTER (WHERE translation_direction_raw IN {KNOWN_DIRECTIONS}) > 0
               AND bool_or(translation_direction_raw = 'UNKNOWN') THEN 'known + UNKNOWN'
          WHEN count(DISTINCT translation_direction_raw) FILTER (WHERE translation_direction_raw IN {KNOWN_DIRECTIONS}) > 1 THEN 'mixed known directions'
          WHEN count(DISTINCT translation_direction_raw) FILTER (WHERE translation_direction_raw IN {KNOWN_DIRECTIONS}) = 1 THEN 'single known direction'
          WHEN bool_and(translation_direction_raw = 'UNKNOWN') THEN 'all UNKNOWN'
          ELSE 'missing/other metadata state'
        END AS direction_composition_class,
        CASE
          WHEN count(*) = 1 THEN '1'
          WHEN count(*) = 2 THEN '2'
          WHEN count(*) = 3 THEN '3'
          WHEN count(*) BETWEEN 4 AND 5 THEN '4-5'
          WHEN count(*) BETWEEN 6 AND 10 THEN '6-10'
          ELSE '>10'
        END AS group_size_bucket,
        bool_or(is_validation_upstream = false) AND bool_or(is_validation_upstream = true) AS cross_split_flag
      FROM read_parquet('{pair}')
      GROUP BY duplicate_group_id
    ) TO '{output}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
    """
    connection.execute(sql)


def build_stratum_profile(connection: duckdb.DuckDBPyConnection, pair_path: Path) -> pd.DataFrame:
    pair = quote_sql_path(pair_path)
    group = quote_sql_path(GROUP_PROFILE_PATH)
    query = f"""
    WITH augmented AS (
      SELECT p.pair_id, p.duplicate_group_id, p.representative_pair_id, g.group_size,
             p.logical_corpus, p.source_id, p.source_provenance_raw, p.domain_raw, p.domain,
             p.translation_direction, p.translation_direction_raw, p.sentence_type,
             p.raw_file_relative_path,
             CASE WHEN p.is_validation_upstream THEN 'VALIDATION' WHEN p.is_validation_upstream = false THEN 'TRAIN' ELSE '{MISSING}' END AS upstream_split
      FROM read_parquet('{pair}') p
      JOIN read_parquet('{group}') g USING (duplicate_group_id)
    ), long AS (
      SELECT pair_id, duplicate_group_id, representative_pair_id, group_size, axis, stratum_value
      FROM augmented,
      LATERAL (VALUES
        ('logical_corpus', coalesce(logical_corpus, '{MISSING}')),
        ('source_id', coalesce(source_id, '{MISSING}')),
        ('source_provenance_raw', coalesce(source_provenance_raw, '{MISSING}')),
        ('domain_raw', coalesce(domain_raw, '{MISSING}')),
        ('canonical_domain', coalesce(domain, '{MISSING}')),
        ('translation_direction', coalesce(translation_direction, '{MISSING}')),
        ('translation_direction_raw', coalesce(translation_direction_raw, '{MISSING}')),
        ('upstream_split_provenance', upstream_split),
        ('sentence_type', coalesce(sentence_type, '{MISSING}')),
        ('raw_file_relative_path', coalesce(raw_file_relative_path, '{MISSING}'))
      ) AS strata(axis, stratum_value)
    ), aggregated AS (
      SELECT axis, stratum_value,
             count(*)::BIGINT AS row_count,
             count(DISTINCT pair_id)::BIGINT AS unique_pair_id_count,
             count(DISTINCT duplicate_group_id)::BIGINT AS duplicate_group_presence_count,
             count(*) FILTER (WHERE group_size > 1)::BIGINT AS rows_in_non_singleton_groups,
             count(DISTINCT duplicate_group_id) FILTER (WHERE group_size > 1)::BIGINT AS non_singleton_group_presence_count,
             count(*) FILTER (WHERE pair_id = representative_pair_id)::BIGINT AS representative_row_count
      FROM long GROUP BY axis, stratum_value
    )
    SELECT *,
           row_count / sum(row_count) OVER (PARTITION BY axis)::DOUBLE AS row_share,
           representative_row_count / nullif(sum(representative_row_count) OVER (PARTITION BY axis), 0)::DOUBLE AS representative_share,
           duplicate_group_presence_count / sum(duplicate_group_presence_count) OVER (PARTITION BY axis)::DOUBLE AS group_presence_share,
           rows_in_non_singleton_groups / row_count::DOUBLE AS duplicate_affected_row_rate,
           non_singleton_group_presence_count / duplicate_group_presence_count::DOUBLE AS duplicate_affected_group_rate,
           1.0 - representative_row_count / row_count::DOUBLE AS representative_collapse_change_rate,
           (representative_row_count / nullif(sum(representative_row_count) OVER (PARTITION BY axis), 0)::DOUBLE)
             - (row_count / sum(row_count) OVER (PARTITION BY axis)::DOUBLE) AS composition_share_change
    FROM aggregated ORDER BY axis, row_count DESC, stratum_value
    """
    return connection.execute(query).fetchdf()


def build_cross_direction_profile(connection: duckdb.DuckDBPyConnection, pair_path: Path) -> pd.DataFrame:
    pair = quote_sql_path(pair_path)
    group = quote_sql_path(GROUP_PROFILE_PATH)
    query = f"""
    WITH augmented AS (
      SELECT p.duplicate_group_id, g.direction_composition_class, g.group_size_bucket,
             p.logical_corpus, p.source_id, p.source_provenance_raw, p.domain,
             CASE WHEN p.is_validation_upstream THEN 'VALIDATION' WHEN p.is_validation_upstream = false THEN 'TRAIN' ELSE '{MISSING}' END AS upstream_split
      FROM read_parquet('{pair}') p JOIN read_parquet('{group}') g USING (duplicate_group_id)
    ), member_strata AS (
      SELECT direction_composition_class, duplicate_group_id, axis, stratum_value
      FROM augmented,
      LATERAL (VALUES
        ('logical_corpus', coalesce(logical_corpus, '{MISSING}')),
        ('source_id', coalesce(source_id, '{MISSING}')),
        ('source_provenance_raw', coalesce(source_provenance_raw, '{MISSING}')),
        ('canonical_domain', coalesce(domain, '{MISSING}')),
        ('upstream_split_provenance', upstream_split)
      ) AS strata(axis, stratum_value)
    ), member_summary AS (
      SELECT direction_composition_class, axis, stratum_value,
             count(DISTINCT duplicate_group_id)::BIGINT AS duplicate_group_count,
             count(*)::BIGINT AS affected_row_count
      FROM member_strata GROUP BY ALL
    ), size_summary AS (
      SELECT direction_composition_class, 'group_size_bucket' AS axis, group_size_bucket AS stratum_value,
             count(*)::BIGINT AS duplicate_group_count, sum(group_size)::BIGINT AS affected_row_count
      FROM read_parquet('{group}') GROUP BY ALL
    )
    SELECT * FROM member_summary UNION ALL SELECT * FROM size_summary
    ORDER BY direction_composition_class, axis, affected_row_count DESC
    """
    return connection.execute(query).fetchdf()


def build_split_matrix_and_simulation(connection: duckdb.DuckDBPyConnection, pair_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    pair = quote_sql_path(pair_path)
    group = quote_sql_path(GROUP_PROFILE_PATH)
    matrix_records: list[dict[str, Any]] = []
    level_map = {"TRAIN": "has_train", "VALIDATION": "has_validation", "MISSING": "has_missing_split"}
    for row_level, row_column in level_map.items():
        for column_level, column_column in level_map.items():
            row = connection.execute(
                f"""SELECT count(*)::BIGINT AS group_count, sum(group_size)::BIGINT AS affected_rows
                FROM read_parquet('{group}') WHERE {row_column} AND {column_column}"""
            ).fetchone()
            matrix_records.append(
                {
                    "record_type": "OVERLAP_MATRIX",
                    "row_split": row_level,
                    "column_split": column_level,
                    "metric": "duplicate_group_count",
                    "value": int(row[0] or 0),
                    "denominator_type": "all_duplicate_groups",
                    "denominator": None,
                    "rate": None,
                    "interpretation_boundary": "Upstream labels are provenance metadata, not project split assignments.",
                }
            )
            matrix_records.append(
                {
                    "record_type": "OVERLAP_MATRIX",
                    "row_split": row_level,
                    "column_split": column_level,
                    "metric": "affected_rows_in_overlapping_groups",
                    "value": int(row[1] or 0),
                    "denominator_type": "all_registry_rows",
                    "denominator": None,
                    "rate": None,
                    "interpretation_boundary": "Rows may be counted in more than one matrix cell; use the TRAIN x VALIDATION cell for exact cross-split exposure.",
                }
            )
    totals = connection.execute(
        f"""SELECT count(*)::BIGINT AS groups, sum(group_size)::BIGINT AS rows,
        count(*) FILTER (WHERE cross_split_flag)::BIGINT AS cross_groups,
        sum(group_size) FILTER (WHERE cross_split_flag)::BIGINT AS cross_rows,
        sum(train_rows) FILTER (WHERE cross_split_flag)::BIGINT AS cross_train_rows,
        sum(validation_rows) FILTER (WHERE cross_split_flag)::BIGINT AS cross_validation_rows
        FROM read_parquet('{group}')"""
    ).fetchdf().iloc[0]
    for metric, value, denominator_type, denominator in (
        ("cross_train_validation_group_count", totals.cross_groups, "all_duplicate_groups", totals.groups),
        ("rows_in_cross_train_validation_groups", totals.cross_rows, "all_registry_rows", totals.rows),
        ("train_rows_in_cross_train_validation_groups", totals.cross_train_rows, "all_registry_rows", totals.rows),
        ("validation_rows_in_cross_train_validation_groups", totals.cross_validation_rows, "all_registry_rows", totals.rows),
    ):
        matrix_records.append(
            {
                "record_type": "SUMMARY",
                "row_split": "TRAIN",
                "column_split": "VALIDATION",
                "metric": metric,
                "value": int(value),
                "denominator_type": denominator_type,
                "denominator": int(denominator),
                "rate": float(value) / float(denominator),
                "interpretation_boundary": "Exact-content overlap only; broader near-duplicate overlap is not measured here.",
            }
        )
    matrix = pd.DataFrame(matrix_records)

    simulation_query = f"""
    WITH assigned AS (
      SELECT duplicate_group_id,
             (hash(pair_id || '|{SAMPLE_SEED}') % 1000) < 800 AS row_train,
             (hash(duplicate_group_id || '|{SAMPLE_SEED}') % 1000) < 800 AS group_train
      FROM read_parquet('{pair}')
    ), group_assignment AS (
      SELECT duplicate_group_id, count(*)::BIGINT AS group_size,
             sum(row_train::INTEGER)::BIGINT AS row_split_train_rows,
             sum((NOT row_train)::INTEGER)::BIGINT AS row_split_holdout_rows,
             min(group_train)::BOOLEAN AS grouped_train
      FROM assigned GROUP BY duplicate_group_id
    )
    SELECT
      count(*)::BIGINT AS total_groups,
      sum(group_size)::BIGINT AS total_rows,
      sum(row_split_train_rows)::BIGINT AS row_split_train_rows,
      sum(row_split_holdout_rows)::BIGINT AS row_split_holdout_rows,
      count(*) FILTER (WHERE row_split_train_rows > 0 AND row_split_holdout_rows > 0)::BIGINT AS row_split_cross_groups,
      sum(group_size) FILTER (WHERE row_split_train_rows > 0 AND row_split_holdout_rows > 0)::BIGINT AS row_split_affected_rows,
      sum(row_split_holdout_rows) FILTER (WHERE row_split_train_rows > 0)::BIGINT AS row_split_holdout_rows_linked_to_train,
      sum(group_size) FILTER (WHERE grouped_train)::BIGINT AS grouped_train_rows,
      sum(group_size) FILTER (WHERE NOT grouped_train)::BIGINT AS grouped_holdout_rows
    FROM group_assignment
    """
    result = connection.execute(simulation_query).fetchdf().iloc[0]
    simulations: list[dict[str, Any]] = []
    for strategy in ("NAIVE_ROW_HASH_80_20", "PAIR_ID_HASH_80_20"):
        simulations.append(
            {
                "strategy": strategy,
                "seed": SAMPLE_SEED,
                "train_rows": int(result.row_split_train_rows),
                "holdout_rows": int(result.row_split_holdout_rows),
                "cross_partition_duplicate_groups": int(result.row_split_cross_groups),
                "rows_in_cross_partition_groups": int(result.row_split_affected_rows),
                "holdout_rows_with_group_member_in_train": int(result.row_split_holdout_rows_linked_to_train),
                "grouping_unit": "registry row" if strategy.startswith("NAIVE") else "pair_id",
                "interpretation_boundary": "pair_id is unique per row, so these two assignments are structurally identical for this registry.",
            }
        )
    simulations.append(
        {
            "strategy": "DUPLICATE_GROUP_ID_HASH_80_20",
            "seed": SAMPLE_SEED,
            "train_rows": int(result.grouped_train_rows),
            "holdout_rows": int(result.grouped_holdout_rows),
            "cross_partition_duplicate_groups": 0,
            "rows_in_cross_partition_groups": 0,
            "holdout_rows_with_group_member_in_train": 0,
            "grouping_unit": "duplicate_group_id",
            "interpretation_boundary": "Eliminates exact-content cross-partition overlap only; future near-duplicate clusters may require a broader key.",
        }
    )
    return matrix, pd.DataFrame(simulations)


def build_cross_split_composition(connection: duckdb.DuckDBPyConnection, pair_path: Path) -> pd.DataFrame:
    pair = quote_sql_path(pair_path)
    group = quote_sql_path(GROUP_PROFILE_PATH)
    query = f"""
    WITH affected AS (
      SELECT p.duplicate_group_id, g.group_size_bucket, p.logical_corpus, p.source_id,
             p.source_provenance_raw, p.domain, p.translation_direction_raw, p.raw_file_relative_path
      FROM read_parquet('{pair}') p JOIN read_parquet('{group}') g USING (duplicate_group_id)
      WHERE g.cross_split_flag
    ), long AS (
      SELECT duplicate_group_id, axis, stratum_value FROM affected,
      LATERAL (VALUES
        ('logical_corpus', coalesce(logical_corpus, '{MISSING}')),
        ('source_id', coalesce(source_id, '{MISSING}')),
        ('source_provenance_raw', coalesce(source_provenance_raw, '{MISSING}')),
        ('canonical_domain', coalesce(domain, '{MISSING}')),
        ('translation_direction_raw', coalesce(translation_direction_raw, '{MISSING}')),
        ('raw_file_relative_path', coalesce(raw_file_relative_path, '{MISSING}')),
        ('group_size_bucket', group_size_bucket)
      ) AS strata(axis, stratum_value)
    )
    SELECT axis, stratum_value, count(DISTINCT duplicate_group_id)::BIGINT AS duplicate_group_count,
           count(*)::BIGINT AS affected_row_count
    FROM long GROUP BY ALL ORDER BY axis, affected_row_count DESC
    """
    return connection.execute(query).fetchdf()


def crosstab_inputs(connection: duckdb.DuckDBPyConnection, pair_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    pair = quote_sql_path(pair_path)
    portfolio_sql = f"""
    WITH base AS (
      SELECT logical_corpus, source_id, coalesce(source_provenance_raw, '{MISSING}') AS source_provenance_raw,
             coalesce(domain, '{MISSING}') AS canonical_domain, coalesce(domain_raw, '{MISSING}') AS domain_raw,
             coalesce(translation_direction, '{MISSING}') AS translation_direction,
             coalesce(translation_direction_raw, '{MISSING}') AS translation_direction_raw
      FROM read_parquet('{pair}')
    ), portfolios AS (
      SELECT logical_corpus AS portfolio, * FROM base
      UNION ALL
      SELECT 'PRIMARY_025_026' AS portfolio, * FROM base WHERE logical_corpus IN ('025','026')
    )
    SELECT * FROM portfolios
    """
    definitions = (
        ("source_id_x_canonical_domain", "source_id", "canonical_domain"),
        ("source_provenance_raw_x_domain_raw", "source_provenance_raw", "domain_raw"),
        ("source_id_x_translation_direction", "source_id", "translation_direction"),
        ("source_provenance_raw_x_translation_direction_raw", "source_provenance_raw", "translation_direction_raw"),
    )
    frames: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []
    for table_name, x_axis, y_axis in definitions:
        observed = connection.execute(
            f"""WITH portfolios AS ({portfolio_sql})
            SELECT portfolio, {x_axis} AS x_level, {y_axis} AS y_level, count(*)::BIGINT AS row_count
            FROM portfolios GROUP BY ALL"""
        ).fetchdf()
        for portfolio, group in observed.groupby("portfolio", sort=True):
            x_levels = sorted(group.x_level.astype(str).unique())
            y_levels = sorted(group.y_level.astype(str).unique())
            grid = pd.MultiIndex.from_product([x_levels, y_levels], names=["x_level", "y_level"]).to_frame(index=False)
            cells = grid.merge(group[["x_level", "y_level", "row_count"]], how="left", on=["x_level", "y_level"])
            cells["row_count"] = cells["row_count"].fillna(0).astype("int64")
            total = int(cells.row_count.sum())
            cells.insert(0, "crosstab", table_name)
            cells.insert(0, "portfolio", portfolio)
            cells["denominator_type"] = "portfolio_registry_rows"
            cells["denominator"] = total
            cells["rate"] = cells.row_count / total if total else np.nan
            cells["evidence_label"] = "DERIVED DESCRIPTIVE"
            cells["interpretation_boundary"] = "Composition/identifiability diagnostic; no separate-effect or causal interpretation."
            frames.append(cells)

            nonzero = cells[cells.row_count > 0]
            x_nonzero_y = nonzero.groupby("x_level").y_level.nunique()
            y_nonzero_x = nonzero.groupby("y_level").x_level.nunique()
            x_deterministic = set(x_nonzero_y[x_nonzero_y == 1].index)
            y_deterministic = set(y_nonzero_x[y_nonzero_x == 1].index)
            x_det_rows = int(nonzero[nonzero.x_level.isin(x_deterministic)].row_count.sum())
            y_det_rows = int(nonzero[nonzero.y_level.isin(y_deterministic)].row_count.sum())
            diagnostics.append(
                {
                    "portfolio": portfolio,
                    "crosstab": table_name,
                    "x_axis": x_axis,
                    "y_axis": y_axis,
                    "x_level_count": len(x_levels),
                    "y_level_count": len(y_levels),
                    "possible_cell_count": len(cells),
                    "observed_cell_count": len(nonzero),
                    "zero_cell_count": len(cells) - len(nonzero),
                    "zero_cell_rate": (len(cells) - len(nonzero)) / len(cells) if len(cells) else np.nan,
                    "x_levels_mapping_to_one_y": len(x_deterministic),
                    "x_level_deterministic_rate": len(x_deterministic) / len(x_levels) if x_levels else np.nan,
                    "rows_in_x_deterministic_levels": x_det_rows,
                    "x_deterministic_row_rate": x_det_rows / total if total else np.nan,
                    "y_levels_mapping_to_one_x": len(y_deterministic),
                    "y_level_deterministic_rate": len(y_deterministic) / len(y_levels) if y_levels else np.nan,
                    "rows_in_y_deterministic_levels": y_det_rows,
                    "y_deterministic_row_rate": y_det_rows / total if total else np.nan,
                    "evidence_label": "NOT IDENTIFIABLE" if len(x_levels) <= 1 or len(y_levels) <= 1 or (x_det_rows == total and y_det_rows == total) else "DERIVED DESCRIPTIVE",
                    "interpretation_boundary": "Deterministic mapping or a constant factor blocks separate within-portfolio interpretation; this is not a fitted model.",
                }
            )
    return pd.concat(frames, ignore_index=True), pd.DataFrame(diagnostics)


def build_manual_frame(connection: duckdb.DuckDBPyConnection, pair_path: Path) -> pd.DataFrame:
    pair = quote_sql_path(pair_path)
    group = quote_sql_path(GROUP_PROFILE_PATH)
    query = f"""
    WITH candidates AS (
      SELECT p.logical_corpus, coalesce(p.domain, '{MISSING}') AS canonical_domain,
             g.direction_conflict_flag, g.cross_split_flag, g.group_size,
             CASE
               WHEN g.direction_conflict_flag AND g.cross_split_flag THEN 'CROSS_DIRECTION_AND_CROSS_SPLIT_DUPLICATE'
               WHEN g.direction_conflict_flag THEN 'CROSS_DIRECTION_DUPLICATE'
               WHEN g.cross_split_flag THEN 'CROSS_SPLIT_DUPLICATE'
               WHEN g.group_size > 1 THEN 'OTHER_EXACT_DUPLICATE'
               ELSE 'SINGLETON'
             END AS structural_risk_class
      FROM read_parquet('{pair}') p JOIN read_parquet('{group}') g USING (duplicate_group_id)
    )
    SELECT logical_corpus, canonical_domain, structural_risk_class, count(*)::BIGINT AS population_row_count,
           count(*) / sum(count(*)) OVER ()::DOUBLE AS population_row_share
    FROM candidates GROUP BY ALL ORDER BY logical_corpus, canonical_domain, structural_risk_class
    """
    frame = connection.execute(query).fetchdf()
    populations = frame.population_row_count.to_numpy(dtype=int)
    frame["proportional_allocation_n"] = hamilton_allocation(populations, 500)
    priority_map = {
        "CROSS_DIRECTION_AND_CROSS_SPLIT_DUPLICATE": 10.0,
        "CROSS_DIRECTION_DUPLICATE": 7.0,
        "CROSS_SPLIT_DUPLICATE": 6.0,
        "OTHER_EXACT_DUPLICATE": 2.5,
        "SINGLETON": 1.0,
    }
    minimum_map = {
        "CROSS_DIRECTION_AND_CROSS_SPLIT_DUPLICATE": 6,
        "CROSS_DIRECTION_DUPLICATE": 5,
        "CROSS_SPLIT_DUPLICATE": 5,
        "OTHER_EXACT_DUPLICATE": 3,
        "SINGLETON": 2,
    }
    frame["risk_priority_multiplier"] = frame.structural_risk_class.map(priority_map).astype(float)
    frame.loc[frame.logical_corpus == "LEGACY", "risk_priority_multiplier"] *= 1.5
    frame.loc[frame.population_row_share < 0.001, "risk_priority_multiplier"] *= 2.0
    minimums = frame.structural_risk_class.map(minimum_map).to_numpy(dtype=int)
    frame["risk_oversampled_allocation_n"] = hamilton_allocation(
        populations,
        500,
        priority=frame.risk_priority_multiplier.to_numpy(dtype=float),
        minimums=minimums,
    )
    for allocation in ("proportional", "risk_oversampled"):
        n_col = f"{allocation}_allocation_n"
        frame[f"{allocation}_inclusion_rate"] = frame[n_col] / frame.population_row_count
        frame[f"{allocation}_base_weight_N_over_n"] = np.where(frame[n_col] > 0, frame.population_row_count / frame[n_col], np.nan)
        weighted_mean = np.average(
            frame.loc[frame[n_col] > 0, f"{allocation}_base_weight_N_over_n"],
            weights=frame.loc[frame[n_col] > 0, n_col],
        )
        frame[f"{allocation}_normalized_weight"] = frame[f"{allocation}_base_weight_N_over_n"] / weighted_mean
    frame["minimum_per_cell_logic"] = frame.structural_risk_class.map(lambda value: f"minimum {minimum_map[value]} when populated")
    frame["rare_cell_flag"] = frame.population_row_share < 0.001
    frame["high_risk_flag"] = frame.structural_risk_class.isin(
        {"CROSS_DIRECTION_AND_CROSS_SPLIT_DUPLICATE", "CROSS_DIRECTION_DUPLICATE", "CROSS_SPLIT_DUPLICATE"}
    )
    frame["sample_draw_status"] = "NOT_DRAWN_REQUI_DISPOSITION"
    frame["evidence_label"] = "POLICY OPTION"
    frame["interpretation_boundary"] = "Allocation frame only; final allocation and any draw require Research Director approval."
    return frame


def scenario_tables(stratum: pd.DataFrame, identity: dict[str, int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    global_rows = []
    definitions = {
        "S0": (identity["row_count"], "all registry rows", "retains row multiplicity"),
        "S1": (identity["group_count"], "one representative pointer per exact duplicate group", "retains one provenance pointer; group conflicts remain explicit in group profile"),
        "S2": (identity["row_count"], "all rows with duplicate_group_id as future cluster", "retains multiplicity while requiring cluster-aware resampling/inference"),
        "S3-PROVENANCE": (identity["row_count"], "full rows for provenance descriptions", "dual-denominator policy option"),
        "S3-INDEPENDENT-PAIR": (identity["group_count"], "representatives for a hypothetical independent-pair estimate", "not an estimate and not a selected policy"),
    }
    for scenario, (rows, unit, boundary) in definitions.items():
        global_rows.append(
            {
                "scenario": scenario,
                "row_count": rows,
                "duplicate_group_count": identity["group_count"],
                "analysis_unit_description": unit,
                "information_boundary": boundary,
                "evidence_label": "POLICY OPTION",
            }
        )
    composition_rows: list[dict[str, Any]] = []
    for item in stratum.itertuples(index=False):
        base = {
            "axis": item.axis,
            "stratum_value": item.stratum_value,
            "raw_row_count": int(item.row_count),
            "representative_row_count": int(item.representative_row_count),
            "raw_row_share": float(item.row_share),
            "representative_row_share": float(item.representative_share),
            "composition_share_change": float(item.composition_share_change),
        }
        for scenario, count_key, share_key in (
            ("S0", "raw_row_count", "raw_row_share"),
            ("S1", "representative_row_count", "representative_row_share"),
            ("S2", "raw_row_count", "raw_row_share"),
            ("S3-PROVENANCE", "raw_row_count", "raw_row_share"),
            ("S3-INDEPENDENT-PAIR", "representative_row_count", "representative_row_share"),
        ):
            composition_rows.append(
                {
                    "scenario": scenario,
                    "axis": base["axis"],
                    "stratum_value": base["stratum_value"],
                    "count": base[count_key],
                    "share": base[share_key],
                    "s1_minus_s0_share_change": base["composition_share_change"],
                    "evidence_label": "POLICY OPTION",
                    "interpretation_boundary": "Scenario composition is descriptive; S1 representative metadata is a provenance pointer and does not resolve group-level conflicts.",
                }
            )
    return pd.DataFrame(global_rows), pd.DataFrame(composition_rows)


def build_figures(
    connection: duckdb.DuckDBPyConnection,
    stratum: pd.DataFrame,
    cross_direction: pd.DataFrame,
    split_matrix: pd.DataFrame,
    ident_cells: pd.DataFrame,
    scenario_composition: pd.DataFrame,
    manual_frame: pd.DataFrame,
    identity: dict[str, int],
) -> list[dict[str, Any]]:
    palette = {"navy": "#17324D", "blue": "#2678A5", "teal": "#2A9D8F", "amber": "#E9A23B", "red": "#C64B4B", "gray": "#8A94A3"}
    validation: list[dict[str, Any]] = []

    size = connection.execute(
        f"""SELECT group_size_bucket, count(*)::BIGINT AS group_count, sum(group_size)::BIGINT AS row_count
        FROM read_parquet('{quote_sql_path(GROUP_PROFILE_PATH)}') GROUP BY ALL"""
    ).fetchdf()
    order = ["1", "2", "3", "4-5", "6-10", ">10"]
    size["group_size_bucket"] = pd.Categorical(size.group_size_bucket, categories=order, ordered=True)
    size = size.sort_values("group_size_bucket")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), constrained_layout=True)
    axes[0].bar(size.group_size_bucket.astype(str), size.group_count, color=palette["blue"])
    axes[0].set_yscale("log")
    axes[0].set_title("How many exact-content groups have each size?")
    axes[0].set_xlabel("Group-size bucket")
    axes[0].set_ylabel("Duplicate groups (log scale)")
    axes[0].grid(axis="y")
    axes[1].bar(size.group_size_bucket.astype(str), size.row_count, color=palette["teal"])
    axes[1].set_yscale("log")
    axes[1].set_title("How many registry rows sit in each group-size bucket?")
    axes[1].set_xlabel("Group-size bucket")
    axes[1].set_ylabel("Registry rows (log scale)")
    axes[1].grid(axis="y")
    fig.suptitle("OBSERVED — exact duplicate-group size distribution\nDenominators: duplicate groups (left), registry rows (right)", fontsize=14)
    save_figure(fig, FIGURES["F01"])

    corpus = stratum[stratum.axis == "logical_corpus"].copy().sort_values("row_count", ascending=False)
    source = stratum[stratum.axis == "source_provenance_raw"].copy().nlargest(12, "row_count").sort_values("duplicate_affected_row_rate")
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.2), constrained_layout=True)
    x = np.arange(len(corpus))
    axes[0].bar(x - 0.2, corpus.row_count, width=0.4, label="all rows", color=palette["navy"])
    axes[0].bar(x + 0.2, corpus.representative_row_count, width=0.4, label="representative rows", color=palette["teal"])
    axes[0].set_xticks(x, corpus.stratum_value)
    axes[0].set_title("Corpus counts before/after representative collapse")
    axes[0].set_ylabel("Rows")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y")
    axes[1].barh([safe_label(v) for v in source.stratum_value], source.duplicate_affected_row_rate * 100, color=palette["amber"])
    axes[1].set_title("Top-volume raw-source labels: rows in non-singleton groups")
    axes[1].set_xlabel("Affected registry rows (%)")
    axes[1].grid(axis="x")
    fig.suptitle("DERIVED DESCRIPTIVE — duplicate burden by corpus and raw-source provenance", fontsize=14)
    save_figure(fig, FIGURES["F02"])

    direction_overall = cross_direction[cross_direction.axis == "group_size_bucket"].groupby("direction_composition_class", as_index=False).agg(
        duplicate_group_count=("duplicate_group_count", "sum"), affected_row_count=("affected_row_count", "sum")
    ).sort_values("affected_row_count")
    direction_025 = cross_direction[(cross_direction.axis == "logical_corpus") & (cross_direction.stratum_value == "025")].sort_values("affected_row_count")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), constrained_layout=True)
    axes[0].barh(direction_overall.direction_composition_class, direction_overall.duplicate_group_count, color=palette["blue"])
    axes[0].set_xscale("log")
    axes[0].set_title("All groups by raw-direction composition")
    axes[0].set_xlabel("Duplicate groups (log scale)")
    axes[0].grid(axis="x")
    axes[1].barh(direction_025.direction_composition_class, direction_025.affected_row_count, color=palette["red"])
    axes[1].set_xscale("log")
    axes[1].set_title("025 rows affected by each composition class")
    axes[1].set_xlabel("Registry rows (log scale)")
    axes[1].grid(axis="x")
    fig.suptitle("OBSERVED — cross-direction structure uses translation_direction_raw; ambiguity is retained", fontsize=14)
    save_figure(fig, FIGURES["F03"])

    overlap = split_matrix[(split_matrix.record_type == "OVERLAP_MATRIX") & (split_matrix.metric == "duplicate_group_count")]
    heat = overlap.pivot(index="row_split", columns="column_split", values="value").reindex(index=["TRAIN", "VALIDATION", "MISSING"], columns=["TRAIN", "VALIDATION", "MISSING"]).fillna(0)
    fig, ax = plt.subplots(figsize=(8.5, 7), constrained_layout=True)
    image = ax.imshow(np.log10(heat.to_numpy() + 1), cmap="YlOrRd")
    ax.set_xticks(range(len(heat.columns)), heat.columns)
    ax.set_yticks(range(len(heat.index)), heat.index)
    for i in range(len(heat.index)):
        for j in range(len(heat.columns)):
            ax.text(j, i, f"{int(heat.iloc[i, j]):,}", ha="center", va="center", color="black", fontsize=11)
    ax.set_title("OBSERVED — duplicate-group overlap among upstream split labels\nCell text = groups; color = log10(groups + 1)")
    ax.set_xlabel("Column split provenance")
    ax.set_ylabel("Row split provenance")
    fig.colorbar(image, ax=ax, label="log10(group count + 1)")
    save_figure(fig, FIGURES["F04"])

    panels = [
        ("026", "source_provenance_raw_x_domain_raw", "026 raw source × raw domain"),
        ("025", "source_provenance_raw_x_translation_direction_raw", "025 raw source × raw direction"),
        ("PRIMARY_025_026", "source_id_x_canonical_domain", "Primary portfolio source_id × canonical domain"),
        ("PRIMARY_025_026", "source_id_x_translation_direction", "Primary portfolio source_id × canonical direction"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(17, 13), constrained_layout=True)
    for ax, (portfolio, table_name, title) in zip(axes.flat, panels, strict=True):
        subset = ident_cells[(ident_cells.portfolio == portfolio) & (ident_cells.crosstab == table_name)]
        pivot = subset.pivot(index="x_level", columns="y_level", values="rate").fillna(0)
        matrix = pivot.to_numpy() * 100
        image = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=max(1.0, float(matrix.max())))
        ax.set_xticks(range(len(pivot.columns)), [safe_label(v, 20) for v in pivot.columns], rotation=35, ha="right")
        ax.set_yticks(range(len(pivot.index)), [safe_label(v, 27) for v in pivot.index])
        ax.set_title(title)
        ax.set_xlabel("Column factor")
        ax.set_ylabel("Row factor")
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                if matrix[i, j] >= 0.05:
                    ax.text(j, i, f"{matrix[i, j]:.1f}%", ha="center", va="center", fontsize=8)
        fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02, label="portfolio row share (%)")
    fig.suptitle("NOT IDENTIFIABLE diagnostics — zero cells and deterministic mappings constrain separate interpretation", fontsize=15)
    save_figure(fig, FIGURES["F05"])

    scenario_focus = scenario_composition[
        (scenario_composition.axis == "logical_corpus") & scenario_composition.scenario.isin(["S0", "S1"])
    ].copy()
    pivot = scenario_focus.pivot(index="stratum_value", columns="scenario", values="share").fillna(0) * 100
    sensitive = stratum.assign(abs_change=lambda d: d.composition_share_change.abs()).nlargest(12, "abs_change").sort_values("composition_share_change")
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), constrained_layout=True)
    pivot.plot(kind="bar", ax=axes[0], color=[palette["navy"], palette["teal"]])
    axes[0].set_title("Corpus share: all rows (S0) vs representatives (S1)")
    axes[0].set_ylabel("Composition share (%)")
    axes[0].set_xlabel("Logical corpus")
    axes[0].tick_params(axis="x", rotation=0)
    axes[0].legend(title="Scenario", frameon=False)
    axes[0].grid(axis="y")
    axes[1].barh([f"{r.axis}: {safe_label(r.stratum_value, 26)}" for r in sensitive.itertuples()], sensitive.composition_share_change * 100, color=np.where(sensitive.composition_share_change >= 0, palette["teal"], palette["red"]))
    axes[1].axvline(0, color="#333333", linewidth=0.8)
    axes[1].set_title("Largest representative-minus-row share changes")
    axes[1].set_xlabel("Percentage-point change")
    axes[1].grid(axis="x")
    fig.suptitle("POLICY OPTION — scenario impact on composition; no scenario is selected", fontsize=14)
    save_figure(fig, FIGURES["F06"])

    allocation = manual_frame.groupby("structural_risk_class", as_index=False).agg(
        population_row_count=("population_row_count", "sum"),
        proportional_allocation_n=("proportional_allocation_n", "sum"),
        risk_oversampled_allocation_n=("risk_oversampled_allocation_n", "sum"),
    ).sort_values("risk_oversampled_allocation_n")
    y = np.arange(len(allocation))
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)
    ax.barh(y - 0.18, allocation.proportional_allocation_n, height=0.36, label="proportional option", color=palette["blue"])
    ax.barh(y + 0.18, allocation.risk_oversampled_allocation_n, height=0.36, label="risk-oversampled option", color=palette["amber"])
    ax.set_yticks(y, [safe_label(v, 45) for v in allocation.structural_risk_class])
    ax.set_xlabel("Proposed records out of 500")
    ax.set_title("POLICY OPTION — manual-QC allocation alternatives (no records drawn)")
    ax.legend(frameon=False)
    ax.grid(axis="x")
    save_figure(fig, FIGURES["F07"])

    duplicate_excess = identity["row_count"] - identity["group_count"]
    cross_groups = int(connection.execute(f"SELECT count(*) FROM read_parquet('{quote_sql_path(GROUP_PROFILE_PATH)}') WHERE direction_conflict_flag").fetchone()[0])
    split_cross_groups = int(connection.execute(f"SELECT count(*) FROM read_parquet('{quote_sql_path(GROUP_PROFILE_PATH)}') WHERE cross_split_flag").fetchone()[0])
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    cards = [
        ("Registry rows removed under S1", duplicate_excess, identity["row_count"], palette["teal"]),
        ("Raw-direction-conflicted groups", cross_groups, identity["group_count"], palette["red"]),
        ("Upstream train-validation spanning groups", split_cross_groups, identity["group_count"], palette["amber"]),
        ("Representative pointers", identity["representative_row_count"], identity["group_count"], palette["blue"]),
    ]
    for ax, (title, numerator, denominator, color) in zip(axes.flat, cards, strict=True):
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0.03, 0.08), 0.94, 0.84, facecolor="white", edgecolor=color, linewidth=2, transform=ax.transAxes))
        ax.text(0.5, 0.70, title, ha="center", va="center", fontsize=12, transform=ax.transAxes)
        ax.text(0.5, 0.46, f"{numerator:,}", ha="center", va="center", fontsize=25, fontweight="bold", color=color, transform=ax.transAxes)
        ax.text(0.5, 0.27, f"{numerator / denominator * 100:.2f}% of denominator {denominator:,}", ha="center", va="center", fontsize=10, transform=ax.transAxes)
    fig.suptitle("NOT A PRIMARY RESULT — Director decision-support dashboard", fontsize=16)
    save_figure(fig, FIGURES["F08"])

    for base in FIGURES.values():
        png_path = base.with_suffix(".png")
        svg_path = base.with_suffix(".svg")
        validation.append(validate_png(png_path))
        if svg_path.stat().st_size < 5_000:
            raise AssertionError(f"non-trivial SVG validation failed: {svg_path}")
    return validation


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 30) -> str:
    subset = frame.loc[:, columns].head(max_rows).copy()
    return subset.to_markdown(index=False)


def build_reports(
    identity: dict[str, int],
    size_distribution: pd.DataFrame,
    largest_groups: pd.DataFrame,
    stratum: pd.DataFrame,
    cross_direction: pd.DataFrame,
    split_matrix: pd.DataFrame,
    simulations: pd.DataFrame,
    cross_split: pd.DataFrame,
    ident_diagnostics: pd.DataFrame,
    manual_frame: pd.DataFrame,
    scenarios: pd.DataFrame,
    source_registry: pd.DataFrame,
    summary_records: list[dict[str, Any]],
    execution_started: str,
    pair_path: Path,
    source_path: Path,
) -> None:
    total_rows = identity["row_count"]
    groups = identity["group_count"]
    excess = total_rows - groups
    non_singleton_groups = int(size_distribution.loc[size_distribution.group_size_bucket != "1", "group_count"].sum())
    non_singleton_rows = int(size_distribution.loc[size_distribution.group_size_bucket != "1", "row_count"].sum())
    singleton_groups = int(size_distribution.loc[size_distribution.group_size_bucket == "1", "group_count"].sum())
    cross_direction_groups = int(
        cross_direction[(cross_direction.axis == "group_size_bucket") & (cross_direction.direction_composition_class == "mixed known directions")].duplicate_group_count.sum()
    )
    cross_direction_rows = int(
        cross_direction[(cross_direction.axis == "group_size_bucket") & (cross_direction.direction_composition_class == "mixed known directions")].affected_row_count.sum()
    )
    split_summary = split_matrix[(split_matrix.record_type == "SUMMARY") & (split_matrix.metric == "cross_train_validation_group_count")].iloc[0]
    split_rows = split_matrix[(split_matrix.record_type == "SUMMARY") & (split_matrix.metric == "rows_in_cross_train_validation_groups")].iloc[0]
    corpus = stratum[stratum.axis == "logical_corpus"].copy()
    corpus["row_count"] = corpus.row_count.map(fmt_int)
    corpus["representative_row_count"] = corpus.representative_row_count.map(fmt_int)
    corpus["duplicate_affected_row_rate"] = corpus.duplicate_affected_row_rate.map(fmt_pct)
    corpus["composition_share_change"] = corpus.composition_share_change.map(lambda value: f"{value * 100:+.3f} pp")
    sensitive = stratum.assign(abs_change=lambda d: d.composition_share_change.abs()).nlargest(12, "abs_change").copy()
    sensitive["row_share"] = sensitive.row_share.map(fmt_pct)
    sensitive["representative_share"] = sensitive.representative_share.map(fmt_pct)
    sensitive["composition_share_change"] = sensitive.composition_share_change.map(lambda value: f"{value * 100:+.3f} pp")
    direction_classes = cross_direction[cross_direction.axis == "group_size_bucket"].groupby("direction_composition_class", as_index=False).agg(
        duplicate_group_count=("duplicate_group_count", "sum"), affected_row_count=("affected_row_count", "sum")
    )
    direction_classes["duplicate_group_count"] = direction_classes.duplicate_group_count.map(fmt_int)
    direction_classes["affected_row_count"] = direction_classes.affected_row_count.map(fmt_int)
    split_top = cross_split.groupby(["axis", "stratum_value"], as_index=False).agg(
        duplicate_group_count=("duplicate_group_count", "sum"), affected_row_count=("affected_row_count", "sum")
    ).sort_values(["axis", "affected_row_count"], ascending=[True, False]).groupby("axis", as_index=False).head(5)
    split_top["duplicate_group_count"] = split_top.duplicate_group_count.map(fmt_int)
    split_top["affected_row_count"] = split_top.affected_row_count.map(fmt_int)
    ident_display = ident_diagnostics.copy()
    for column in ("zero_cell_rate", "x_deterministic_row_rate", "y_deterministic_row_rate"):
        ident_display[column] = ident_display[column].map(fmt_pct)
    allocation_rollup = manual_frame.groupby("structural_risk_class", as_index=False).agg(
        population_row_count=("population_row_count", "sum"),
        proportional_allocation_n=("proportional_allocation_n", "sum"),
        risk_oversampled_allocation_n=("risk_oversampled_allocation_n", "sum"),
    )
    allocation_rollup["population_row_count"] = allocation_rollup.population_row_count.map(fmt_int)
    scenario_display = scenarios.copy()
    scenario_display["row_count"] = scenario_display.row_count.map(fmt_int)
    scenario_display["duplicate_group_count"] = scenario_display.duplicate_group_count.map(fmt_int)

    report = f"""# EDA G1 Duplicate Decision Support {VERSION}

**NOT A PRIMARY RESULT**  
**REQUI DISPOSITION**  
**Execution started:** {execution_started}  
**Analysis base:** `{ANALYSIS_BASE_COMMIT}`  
**Scope:** read-only, non-text-bearing, decision-support EDA. No policy is selected.

## Director dashboard

| Director question | Evidence answer | Boundary |
|---|---|---|
| How much changes under exact duplicate collapse? | {fmt_int(excess)} of {fmt_int(total_rows)} rows ({fmt_pct(excess / total_rows)}) are beyond one representative per group; S1 has {fmt_int(groups)} rows. | DERIVED DESCRIPTIVE; no primary unit selected. |
| Which composition claims are denominator-sensitive? | The largest absolute S1-minus-S0 share shifts are listed below and in `F06`; corpus-level shifts are small but several direction/source/file cells move more. | Representative metadata is a provenance pointer, not a group-level conflict resolver. |
| Is upstream validation reusable as a project holdout? | {fmt_int(split_summary.value)} groups span upstream train/validation, affecting {fmt_int(split_rows.value)} rows. | OBSERVED exact overlap only; reuse requires Director disposition and broader LR-01 work. |
| How large is cross-direction structure? | {fmt_int(cross_direction_groups)} groups / {fmt_int(cross_direction_rows)} rows contain multiple known raw directions. | OBSERVED from `translation_direction_raw`; no direction resolution is invented. |
| Which factors are confounded? | Within every individual corpus, `source_id` is constant. In 026, raw source and canonical domain form a deterministic 2×2 correspondence. | NOT IDENTIFIABLE for separate within-corpus effects where constant/deterministic. |
| Smallest exact grouping key visible now? | Raw provenance description: rows and groups side by side. Hypothetical independent-pair unit: `duplicate_group_id`. Predictive holdout: at least `duplicate_group_id`; broader future near-duplicate cluster remains required by LR-01 if established. | POLICY OPTION, not a selected policy. |

Figures: `F08_DIRECTOR_DECISION_DASHBOARD_v001`, then `F01`–`F07` in `outputs/figures/eda_g1_decision_support/`.

## A. Registry and identity map

**OBSERVED**

| Metric | Count | Denominator / meaning |
|---|---:|---|
| Registry rows | {fmt_int(total_rows)} | rows |
| Non-null `pair_id` | {fmt_int(identity['pair_nonnull'])} | rows |
| Distinct `pair_id` | {fmt_int(identity['pair_distinct'])} | unique observation identities |
| Exact-content groups | {fmt_int(groups)} | distinct `duplicate_group_id` |
| Singleton groups | {fmt_int(singleton_groups)} | duplicate groups |
| Multi-row groups | {fmt_int(non_singleton_groups)} | duplicate groups |
| Rows in multi-row groups | {fmt_int(non_singleton_rows)} ({fmt_pct(non_singleton_rows / total_rows)}) | registry rows |
| Groups affected by duplication | {fmt_int(non_singleton_groups)} ({fmt_pct(non_singleton_groups / groups)}) | duplicate groups |
| Representative rows | {fmt_int(identity['representative_row_count'])} | rows where `pair_id = representative_pair_id` |
| Distinct representative pointers | {fmt_int(identity['representative_pointer_count'])} | pointer identities |

`pair_id` is the row-level observation identity. `duplicate_group_id` is the exact-content identity. `representative_pair_id` is a deterministic provenance pointer. The observed one-to-one count between groups and representative pointers does not make these identifiers interchangeable.

### Group-size distribution

{markdown_table(size_distribution.assign(group_count=size_distribution.group_count.map(fmt_int), row_count=size_distribution.row_count.map(fmt_int)), ['group_size_bucket','group_count','row_count'])}

### Largest groups (no raw text)

{markdown_table(largest_groups, ['duplicate_group_id','group_size','representative_pair_id','logical_corpus_composition','translation_direction_raw_composition','raw_file_composition'], 12)}

## B. Duplicate concentration and composition

**DERIVED DESCRIPTIVE**

{markdown_table(corpus, ['stratum_value','row_count','representative_row_count','duplicate_affected_row_rate','composition_share_change'])}

Largest absolute composition shifts under representative collapse:

{markdown_table(sensitive, ['axis','stratum_value','row_share','representative_share','composition_share_change'], 12)}

The full row-level and group-presence denominators are in `{STRATUM_PROFILE_PATH.name}`. Metadata-defined length is **UNAVAILABLE** in the canonical schema; this EDA does not derive length from text. `sentence_type` is present but structurally `other`/source-unavailable and therefore does not support a reliable stratification conclusion.

## C. Cross-direction duplicate analysis

**OBSERVED** — classification is based on `translation_direction_raw`, because canonical direction may already preserve group ambiguity as `UNKNOWN`.

{markdown_table(direction_classes, ['direction_composition_class','duplicate_group_count','affected_row_count'])}

For corpus 025, the multiple-known-direction class contains **{fmt_int(cross_direction_groups)} groups**. This reproduces the observed 025 cross-direction structure. It is concentrated/described by corpus, source, domain, upstream split, and group size in `{CROSS_DIRECTION_PATH.name}`. The EDA does not assert a mechanism for why the pattern exists.

## D. Upstream split leakage analysis

**OBSERVED**

- Upstream train/validation spanning exact groups: **{fmt_int(split_summary.value)} / {fmt_int(split_summary.denominator)} groups ({fmt_pct(split_summary.rate)})**.
- Rows in those groups: **{fmt_int(split_rows.value)} / {fmt_int(split_rows.denominator)} rows ({fmt_pct(split_rows.rate)})**.
- Upstream labels remain provenance metadata.

Top affected composition cells by axis:

{markdown_table(split_top, ['axis','stratum_value','duplicate_group_count','affected_row_count'], 40)}

Simulation-style structural comparison (80/20 deterministic hash, seed `{SAMPLE_SEED}`):

{markdown_table(simulations, ['strategy','grouping_unit','train_rows','holdout_rows','cross_partition_duplicate_groups','holdout_rows_with_group_member_in_train'])}

`pair_id` is unique per registry row, so row-hash and pair-id-hash assignments are identical here. `duplicate_group_id` grouping removes exact-content overlap in the simulation. **NOT IDENTIFIABLE:** whether a broader near-duplicate cluster is necessary cannot be quantified until such a cluster artifact exists; LR-01 still requires that future check.

## E. Source/domain/direction identifiability

**NOT IDENTIFIABLE** where a factor is constant or a mapping is deterministic.

{markdown_table(ident_display, ['portfolio','crosstab','x_level_count','y_level_count','zero_cell_rate','x_deterministic_row_rate','y_deterministic_row_rate','evidence_label'], 30)}

- 025: `source_id` has no within-corpus variation. Direction varies, but source/domain/direction/split cells are sparse and asymmetric; use composite strata for description where the crosstabs show zero cells.
- 026: `source_id` and canonical direction are each constant within corpus. `source_provenance_raw=특허정보원` corresponds exactly to canonical `technology`, while `한국연구재단` corresponds exactly to canonical `other`; raw domain refines the latter into four labels. Separate raw-source and canonical-domain effects are not supported.
- LEGACY: `source_id` and canonical direction are constant. Raw-source and domain structure has many deterministic/near-deterministic cells; separate interpretation is not supported for those cells.
- Pooled 025+026: there is partial overlap through canonical `other`, but `technology` occurs only in 026. Pooled separate-factor interpretation remains constrained and requires an explicit design decision; no model is fitted here.

## F. Policy-impact scenarios

**POLICY OPTION** — trade-offs only.

{markdown_table(scenario_display, ['scenario','row_count','duplicate_group_count','analysis_unit_description','information_boundary'])}

| Scenario | Raw provenance description | Hypothetical paired primary estimate | Source/domain prevalence | Model training | Holdout evaluation | Robustness sensitivity |
|---|---|---|---|---|---|---|
| S0 | Preserves every provenance row | Repeated exact content violates an independent-pair assumption unless accounted for | Row-level prevalence only | Exact leakage unless grouped later | Not suitable without grouping | Useful multiplicity-sensitive view |
| S1 | Loses repeated-row multiplicity; retains one pointer | Supports one-row-per-exact-group framing, subject to other dependencies | Representative-pointer prevalence; conflicts require group profile | Exact duplicates collapsed | Still requires split grouping and near-duplicate review | Useful collapse-sensitive view |
| S2 | Preserves every provenance row | Can support cluster-aware inference if method is later approved | Show row and group denominators | Requires group-aware resampling | At least group-aware | Useful dependence-sensitive view |
| S3 | Uses full rows for provenance and representatives for hypothetical estimate | Separates descriptive and inferential denominators | Both denominators explicit | Same split constraints as S1/S2 | Same split constraints as S1/S2 | Useful denominator sensitivity |

No scenario is labeled as selected. S1/S3 composition uses representative-row provenance only; group-level conflicts remain in the group profile.

## G. Manual-QC sampling frame

**POLICY OPTION** — no sample was drawn.

{markdown_table(allocation_rollup, ['structural_risk_class','population_row_count','proportional_allocation_n','risk_oversampled_allocation_n'])}

Candidate stratification variables are logical corpus, canonical domain, singleton/non-singleton structure, raw-direction conflict, upstream cross-split status, source role (including Legacy sensitivity-only), sparse raw-source/domain cells, and missing/other direction metadata. The proposed frame uses mutually exclusive `logical_corpus × canonical_domain × structural_risk_class` cells. Risk allocation gives minimum representation to populated high-risk and rare cells. If later population descriptions use this sample, apply the recorded `N/n` weights (or normalized weights) and account for the approved design.

**REQUI DISPOSITION:** the final 500-record allocation and any draw require Research Director approval.

## H. Concrete choices requiring Director approval

See `{DECISION_REQUESTS_PATH.name}`. Required choices are D1 primary unit, D2/D3 reporting denominators, D4 holdout grouping and upstream-label disposition, D5 cross-direction sensitivity variants, D6 manual-QC allocation, and D7 composite versus separate identifiability factors.

## Reproducibility and boundaries

- Pair input: `{pair_path}`; rows `{fmt_int(total_rows)}`.
- Source input: `{source_path}`; rows `{fmt_int(len(source_registry))}`.
- Analysis base commit: `{ANALYSIS_BASE_COMMIT}`.
- Execution script was uncommitted at run time; its SHA-256 is recorded in the manifest. Artifact record commit is therefore `null` until separately committed.
- Query/config reference: `{Path(__file__).relative_to(PROJECT_ROOT)}` and its SHA-256 in the manifest.
- Runtime: DuckDB/Python versions, memory limit, thread count, temp spill path, sample seed, schema, row counts, and hashes are in `{MANIFEST_PATH.name}`.
- Every rate in CSV artifacts names its denominator. Public-facing outputs contain no KO/EN text columns.
- This EDA does not select a policy, change QC status, change normalization status, alter source tiers, create a canonical registry, draw the manual sample, measure tokenization/morphology, fit models, or authorize a gate transition.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")

    decision_requests = f"""# Decision Requests {VERSION}

**REQUI DISPOSITION**  
**NOT A PRIMARY RESULT**

## D1 — Primary TP estimation unit

- Options: A retain all rows; B one deterministic representative per exact group; C retain all rows with duplicate-group-aware inference/resampling; D alternative only if a broader dependency artifact later demonstrates necessity.
- Inspect: `{REPORT_PATH.name}` §A/§F; `{GROUP_PROFILE_PATH.name}`; `F01`, `F06`.
- Consequences: A preserves multiplicity but requires dependence handling; B changes denominator and loses row multiplicity; C preserves provenance and requires a future cluster-aware method; D needs new evidence.
- Not determined: the inferential policy and whether broader near-duplicate clusters are needed.

## D2 — Descriptive-statistics denominator

- Options: all rows only; representatives only; both row and group/representative views.
- Inspect: `{STRATUM_PROFILE_PATH.name}` columns `row_share`, `representative_share`, `composition_share_change`; `F02`, `F06`.
- Consequences: a single denominator hides sensitivity; dual reporting increases table size but preserves provenance and exact-content views.
- Not determined: which denominator is authoritative for each Director-facing table.

## D3 — Source/corpus prevalence denominator

- Options: row-level; duplicate-group presence; both with explicit denominator labels.
- Inspect: `{STRATUM_PROFILE_PATH.name}` for `logical_corpus`, `source_id`, `source_provenance_raw`, `canonical_domain`; report §B.
- Consequences: row-level prevalence weights repeated provenance; group presence counts a group in every stratum it spans; representative prevalence uses one pointer and does not resolve conflicts.
- Not determined: approved prevalence convention.

## D4 — Predictive split / holdout grouping

- Options: do not reuse upstream split; reuse only after explicit leakage remediation; create project split grouped by exact group and later broaden to near-duplicate cluster if established.
- Inspect: `{SPLIT_MATRIX_PATH.name}`; report §D; `F04`.
- Consequences: row/pair-id splitting permits exact-content cross-partition overlap; duplicate-group splitting removes that exact overlap; upstream reuse retains {fmt_int(split_summary.value)} cross-split groups.
- Not determined: upstream-label disposition and the future near-duplicate grouping artifact/method.

## D5 — Cross-direction duplicate treatment

- Options: preserve mixed groups with conflict-aware sensitivity; representative-only sensitivity with group conflicts reported; known-single-direction subset sensitivity only if explicitly approved.
- Inspect: `{CROSS_DIRECTION_PATH.name}`; `{GROUP_PROFILE_PATH.name}` direction fields; report §C; `F03`.
- Consequences: variants change direction denominators and may remove mixed-direction evidence from a sensitivity view.
- Not determined: which variants enter the analysis plan; no direction-resolution rule is proposed.

## D6 — Manual-QC allocation

- Options: 500-record proportional allocation; 500-record risk-oversampled allocation; Director-specified hybrid.
- Inspect: `{MANUAL_FRAME_PATH.name}`; report §G; `F07`.
- Consequences: proportional allocation follows volume but may allocate zero to rare cells; risk oversampling improves structural-risk coverage and requires the recorded weights for later population description.
- Not determined: final cell allocation, any sample draw, and downstream weighting estimator.

## D7 — Source/domain/direction analysis structure

- Options: composite strata where mappings are deterministic; restricted within-corpus descriptions; separately parameterized factors only in cells with support and a later approved design.
- Inspect: `{IDENTIFIABILITY_PATH.name}`; `{IDENTIFIABILITY_DIAGNOSTICS_PATH.name}`; report §E; `F05`.
- Consequences: composite strata preserve observed structure; separate-factor claims in constant/deterministic cells are not supported.
- Not determined: future model formula or causal interpretation; neither is part of this EDA.
"""
    DECISION_REQUESTS_PATH.write_text(decision_requests, encoding="utf-8")
    pd.DataFrame(summary_records).to_csv(SUMMARY_PATH, index=False)


def main() -> None:
    args = parse_args()
    execution_started_dt = dt.datetime.now(tz=KST)
    execution_started = execution_started_dt.isoformat(timespec="seconds")
    for directory in (REPORT_DIR, MANIFEST_DIR, FIGURE_DIR, RUNTIME_DIR, args.temp_directory):
        directory.mkdir(parents=True, exist_ok=True)
    if not args.pair_registry.is_file() or not args.source_registry.is_file() or not args.input_manifest.is_file():
        raise FileNotFoundError("pair registry, source registry, and input manifest must all exist")
    if git_value("rev-parse", "HEAD") != ANALYSIS_BASE_COMMIT:
        raise RuntimeError(f"analysis must execute from base {ANALYSIS_BASE_COMMIT}")

    input_manifest = json.loads(args.input_manifest.read_text(encoding="utf-8"))
    pair_hash = sha256_file(args.pair_registry)
    source_hash = sha256_file(args.source_registry)
    if pair_hash != input_manifest["pair_registry"]["sha256"] or source_hash != input_manifest["source_registry"]["sha256"]:
        raise AssertionError("canonical input SHA-256 does not match PAIR_REGISTRY_MANIFEST_v001")
    log("Input hashes verified against canonical manifest")

    pair_meta = pq.ParquetFile(args.pair_registry)
    source_meta = pq.ParquetFile(args.source_registry)
    forbidden_columns = {"ko_text_raw", "en_text_raw", "ko_text_nfc", "en_text_nfc", "ko_text_analysis", "en_text_analysis", "raw_metadata_json"}
    if not forbidden_columns.issubset(set(pair_meta.schema_arrow.names)):
        raise AssertionError("expected text-bearing columns are not present; schema drift requires review")

    connection = duckdb.connect()
    connection.execute(f"SET memory_limit='{args.memory_limit}'")
    connection.execute(f"SET threads={args.threads}")
    connection.execute(f"SET temp_directory='{quote_sql_path(args.temp_directory)}'")
    connection.execute("PRAGMA enable_progress_bar")

    log("Building non-text-bearing duplicate-group profile")
    create_group_profile(connection, args.pair_registry)
    group_meta = pq.ParquetFile(GROUP_PROFILE_PATH)
    identity_row = connection.execute(
        f"""
        SELECT count(*)::BIGINT AS row_count, count(pair_id)::BIGINT AS pair_nonnull,
               count(DISTINCT pair_id)::BIGINT AS pair_distinct,
               count(DISTINCT duplicate_group_id)::BIGINT AS group_count,
               count(DISTINCT representative_pair_id)::BIGINT AS representative_pointer_count,
               count(*) FILTER (WHERE pair_id = representative_pair_id)::BIGINT AS representative_row_count,
               count(*) FILTER (WHERE duplicate_group_id IS NULL)::BIGINT AS missing_group_rows,
               count(*) FILTER (WHERE representative_pair_id IS NULL)::BIGINT AS missing_representative_rows
        FROM read_parquet('{quote_sql_path(args.pair_registry)}')
        """
    ).fetchdf().iloc[0]
    identity = {key: int(value) for key, value in identity_row.to_dict().items()}
    pointer_violations = connection.execute(
        f"""SELECT count(*) FROM read_parquet('{quote_sql_path(GROUP_PROFILE_PATH)}')
        WHERE representative_pointer_count <> 1"""
    ).fetchone()[0]
    identity["representative_pointer_group_violations"] = int(pointer_violations)
    if identity["group_count"] != group_meta.metadata.num_rows or identity["representative_row_count"] != identity["group_count"] or pointer_violations:
        raise AssertionError("identity map invariant failed")
    log(f"Identity map verified: {identity['row_count']:,} rows / {identity['group_count']:,} groups")

    size_distribution = connection.execute(
        f"""SELECT group_size_bucket, count(*)::BIGINT AS group_count, sum(group_size)::BIGINT AS row_count
        FROM read_parquet('{quote_sql_path(GROUP_PROFILE_PATH)}') GROUP BY ALL
        ORDER BY CASE group_size_bucket WHEN '1' THEN 1 WHEN '2' THEN 2 WHEN '3' THEN 3 WHEN '4-5' THEN 4 WHEN '6-10' THEN 5 ELSE 6 END"""
    ).fetchdf()
    largest_groups = connection.execute(
        f"""SELECT duplicate_group_id, group_size, representative_pair_id, logical_corpus_composition,
             source_provenance_raw_composition, domain_composition, translation_direction_raw_composition,
             CASE WHEN length(raw_file_composition) > 160 THEN left(raw_file_composition, 157) || '...' ELSE raw_file_composition END AS raw_file_composition
        FROM read_parquet('{quote_sql_path(GROUP_PROFILE_PATH)}')
        ORDER BY group_size DESC, duplicate_group_id LIMIT 20"""
    ).fetchdf()

    log("Aggregating duplicate burden by metadata stratum")
    stratum = build_stratum_profile(connection, args.pair_registry)
    stratum.to_csv(STRATUM_PROFILE_PATH, index=False)
    cross_direction = build_cross_direction_profile(connection, args.pair_registry)
    cross_direction.to_csv(CROSS_DIRECTION_PATH, index=False)

    log("Quantifying upstream and simulated split leakage")
    split_matrix, simulations = build_split_matrix_and_simulation(connection, args.pair_registry)
    split_matrix.to_csv(SPLIT_MATRIX_PATH, index=False)
    cross_split = build_cross_split_composition(connection, args.pair_registry)
    cross_split.to_csv(REPORT_DIR / "EDA_G1_CROSS_SPLIT_COMPOSITION_v001.csv", index=False)

    log("Building source/domain/direction identifiability maps")
    ident_cells, ident_diagnostics = crosstab_inputs(connection, args.pair_registry)
    pq.write_table(pa.Table.from_pandas(ident_cells, preserve_index=False), IDENTIFIABILITY_PATH, compression="zstd")
    ident_diagnostics.to_csv(IDENTIFIABILITY_DIAGNOSTICS_PATH, index=False)

    log("Building policy scenarios and the 500-record allocation frame")
    scenarios, scenario_composition = scenario_tables(stratum, identity)
    scenario_export = pd.concat(
        [
            scenarios.assign(record_type="SCENARIO_DEFINITION"),
            scenario_composition.assign(record_type="COMPOSITION"),
        ],
        ignore_index=True,
        sort=False,
    )
    scenario_export.to_csv(SCENARIO_PATH, index=False)
    manual_frame = build_manual_frame(connection, args.pair_registry)
    if int(manual_frame.proportional_allocation_n.sum()) != 500 or int(manual_frame.risk_oversampled_allocation_n.sum()) != 500:
        raise AssertionError("manual allocation totals must each equal 500")
    manual_frame.to_csv(MANUAL_FRAME_PATH, index=False)

    source_registry = pq.read_table(args.source_registry).to_pandas()
    summary_records: list[dict[str, Any]] = []
    total_rows = identity["row_count"]
    total_groups = identity["group_count"]
    non_singleton_groups = int(size_distribution.loc[size_distribution.group_size_bucket != "1", "group_count"].sum())
    non_singleton_rows = int(size_distribution.loc[size_distribution.group_size_bucket != "1", "row_count"].sum())
    identity_metrics = (
        ("registry_rows", total_rows, total_rows, "rows"),
        ("distinct_pair_id", identity["pair_distinct"], total_rows, "unique pair_id / rows"),
        ("duplicate_groups", total_groups, total_groups, "distinct duplicate_group_id"),
        ("singleton_groups", int(size_distribution.loc[size_distribution.group_size_bucket == "1", "group_count"].sum()), total_groups, "duplicate groups"),
        ("multi_row_groups", non_singleton_groups, total_groups, "duplicate groups"),
        ("rows_in_multi_row_groups", non_singleton_rows, total_rows, "registry rows"),
        ("representative_rows", identity["representative_row_count"], total_rows, "registry rows"),
        ("duplicate_excess_rows_beyond_one_representative", total_rows - total_groups, total_rows, "registry rows"),
    )
    for metric, numerator, denominator, stratum_name in identity_metrics:
        add_summary(summary_records, scenario="IDENTITY", metric=metric, numerator=numerator, denominator=denominator, stratum=stratum_name, boundary="Identity counts are descriptive and do not select an analysis unit.")
    for row in size_distribution.itertuples(index=False):
        add_summary(summary_records, scenario="IDENTITY", metric="group_size_bucket_group_count", numerator=int(row.group_count), denominator=total_groups, stratum=str(row.group_size_bucket), boundary="Denominator is duplicate groups.")
        add_summary(summary_records, scenario="IDENTITY", metric="group_size_bucket_row_count", numerator=int(row.row_count), denominator=total_rows, stratum=str(row.group_size_bucket), boundary="Denominator is registry rows.")
    for row in stratum.itertuples(index=False):
        add_summary(summary_records, scenario="S0", metric="stratum_row_count", numerator=int(row.row_count), denominator=total_rows, stratum=f"{row.axis}={row.stratum_value}", boundary="Row-level composition; repeated exact content retains multiplicity.")
        add_summary(summary_records, scenario="S1", metric="stratum_representative_row_count", numerator=int(row.representative_row_count), denominator=total_groups, stratum=f"{row.axis}={row.stratum_value}", boundary="Representative provenance composition; does not resolve group conflicts.", label="POLICY OPTION")
        add_summary(summary_records, scenario="DUPLICATE_BURDEN", metric="rows_in_non_singleton_groups", numerator=int(row.rows_in_non_singleton_groups), denominator=int(row.row_count), stratum=f"{row.axis}={row.stratum_value}", boundary="Rate denominator is source/corpus-specific eligible registry rows in the named stratum.")
    split_group_row = split_matrix[(split_matrix.record_type == "SUMMARY") & (split_matrix.metric == "cross_train_validation_group_count")].iloc[0]
    split_affected_row = split_matrix[(split_matrix.record_type == "SUMMARY") & (split_matrix.metric == "rows_in_cross_train_validation_groups")].iloc[0]
    add_summary(summary_records, scenario="UPSTREAM_PROVENANCE", metric="cross_train_validation_groups", numerator=int(split_group_row.value), denominator=int(split_group_row.denominator), stratum="all duplicate groups", boundary="Upstream labels are provenance only; exact overlap does not quantify future near duplicates.")
    add_summary(summary_records, scenario="UPSTREAM_PROVENANCE", metric="rows_in_cross_train_validation_groups", numerator=int(split_affected_row.value), denominator=int(split_affected_row.denominator), stratum="all registry rows", boundary="Upstream labels are provenance only; exact overlap does not quantify future near duplicates.")
    for row in simulations.itertuples(index=False):
        add_summary(summary_records, scenario=row.strategy, metric="cross_partition_duplicate_groups", numerator=int(row.cross_partition_duplicate_groups), denominator=total_groups, stratum=row.grouping_unit, boundary=row.interpretation_boundary, label="POLICY OPTION")
        add_summary(summary_records, scenario=row.strategy, metric="holdout_rows_with_group_member_in_train", numerator=int(row.holdout_rows_with_group_member_in_train), denominator=int(row.holdout_rows), stratum=row.grouping_unit, boundary=row.interpretation_boundary, label="POLICY OPTION")
    for row in ident_diagnostics.itertuples(index=False):
        add_summary(summary_records, scenario="IDENTIFIABILITY", metric="zero_cells", numerator=int(row.zero_cell_count), denominator=int(row.possible_cell_count), stratum=f"{row.portfolio}:{row.crosstab}", boundary=row.interpretation_boundary, label=row.evidence_label)
        add_summary(summary_records, scenario="IDENTIFIABILITY", metric="rows_in_x_deterministic_levels", numerator=int(row.rows_in_x_deterministic_levels), denominator=int(row.rows_in_x_deterministic_levels / row.x_deterministic_row_rate) if row.x_deterministic_row_rate else None, stratum=f"{row.portfolio}:{row.crosstab}", boundary=row.interpretation_boundary, label=row.evidence_label)
    for row in manual_frame.itertuples(index=False):
        add_summary(summary_records, scenario="QC_PROPORTIONAL_500", metric="allocated_records", numerator=int(row.proportional_allocation_n), denominator=500, stratum=f"{row.logical_corpus}|{row.canonical_domain}|{row.structural_risk_class}", boundary="Allocation option only; no sample was drawn.", label="POLICY OPTION")
        add_summary(summary_records, scenario="QC_RISK_OVERSAMPLED_500", metric="allocated_records", numerator=int(row.risk_oversampled_allocation_n), denominator=500, stratum=f"{row.logical_corpus}|{row.canonical_domain}|{row.structural_risk_class}", boundary="Allocation option only; use recorded N/n weights for later population description.", label="POLICY OPTION")
    for row in scenarios.itertuples(index=False):
        add_summary(summary_records, scenario=row.scenario, metric="scenario_row_count", numerator=int(row.row_count), denominator=total_rows, stratum=row.analysis_unit_description, boundary=row.information_boundary, label="POLICY OPTION")

    log("Rendering seven evidence views plus the Director dashboard")
    font_info = configure_plotting()
    visual_validation = build_figures(connection, stratum, cross_direction, split_matrix, ident_cells, scenario_composition, manual_frame, identity)

    build_reports(
        identity,
        size_distribution,
        largest_groups,
        stratum,
        cross_direction,
        split_matrix,
        simulations,
        cross_split,
        ident_diagnostics,
        manual_frame,
        scenarios,
        source_registry,
        summary_records,
        execution_started,
        args.pair_registry.resolve(),
        args.source_registry.resolve(),
    )

    connection.close()
    log("Validating output schemas and assembling manifest")
    summary_columns = {"scenario", "metric", "numerator", "denominator", "rate", "stratum", "interpretation_boundary"}
    if not summary_columns.issubset(pd.read_csv(SUMMARY_PATH, nrows=1).columns):
        raise AssertionError("decision summary schema is incomplete")
    group_schema = pq.ParquetFile(GROUP_PROFILE_PATH).schema_arrow
    if forbidden_columns.intersection(group_schema.names):
        raise AssertionError("group profile contains a forbidden text-bearing column")
    required_group_columns = {"duplicate_group_id", "group_size", "representative_pair_id", "direction_composition_class", "cross_split_flag"}
    if not required_group_columns.issubset(group_schema.names):
        raise AssertionError("group profile schema is incomplete")

    execution_finished = dt.datetime.now(tz=KST)
    output_paths = sorted(
        [path for path in REPORT_DIR.glob("EDA_G1_*_v001.*")]
        + [DECISION_REQUESTS_PATH]
        + [path for path in FIGURE_DIR.glob("*_v001.png")]
        + [path for path in FIGURE_DIR.glob("*_v001.svg")]
    )
    script_path = Path(__file__).resolve()
    manifest = {
        "artifact_id": "EDA_G1_DECISION_SUPPORT_MANIFEST_v001",
        "artifact_class": "EXPLORATORY_DECISION_SUPPORT_NOT_A_PRIMARY_RESULT",
        "decision_status": "REQUI_DISPOSITION",
        "created_at": execution_finished.isoformat(timespec="seconds"),
        "analysis_base_commit": ANALYSIS_BASE_COMMIT,
        "execution_code_commit": None,
        "execution_code_status": "UNCOMMITTED_SCRIPT_AGAINST_ANALYSIS_BASE",
        "artifact_record_commit": None,
        "artifact_record_status": "UNCOMMITTED_EXPLORATORY_OUTPUTS",
        "execution_script": {"path": script_path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(script_path)},
        "input_artifacts": [
            {
                "role": "canonical_pair_registry_read_only",
                "path_used": args.pair_registry.resolve().as_posix(),
                "manifest_relative_path": input_manifest["pair_registry"]["path"],
                "sha256": pair_hash,
                "row_count": pair_meta.metadata.num_rows,
                "schema_version": input_manifest["pair_registry"]["schema_version"],
                "schema_sha256": input_manifest["pair_registry"]["schema_sha256"],
            },
            {
                "role": "canonical_source_registry_read_only",
                "path_used": args.source_registry.resolve().as_posix(),
                "manifest_relative_path": input_manifest["source_registry"]["path"],
                "sha256": source_hash,
                "row_count": source_meta.metadata.num_rows,
                "schema_version": input_manifest["source_registry"]["schema_version"],
                "schema_sha256": input_manifest["source_registry"]["schema_sha256"],
            },
            {
                "role": "canonical_input_manifest_read_only",
                "path_used": args.input_manifest.resolve().as_posix(),
                "sha256": sha256_file(args.input_manifest),
                "registry_build_code_commit": input_manifest.get("code_commit"),
            },
        ],
        "identity_counts": identity,
        "schemas": {
            "pair_registry_columns": pair_meta.schema_arrow.names,
            "group_profile_columns": group_schema.names,
            "public_output_text_column_policy": "KO_EN_TEXT_COLUMNS_EXCLUDED",
            "metadata_length_proxy": "UNAVAILABLE_NOT_DERIVED_FROM_TEXT",
        },
        "runtime_policy": {
            "python": sys.version,
            "platform": platform.platform(),
            "duckdb": duckdb.__version__,
            "pandas": pd.__version__,
            "pyarrow": pa.__version__,
            "matplotlib": matplotlib.__version__,
            "memory_limit": args.memory_limit,
            "threads": args.threads,
            "temp_spill_directory": args.temp_directory.resolve().as_posix(),
            "progress_observability": "timestamped stage log plus DuckDB progress bar",
            "execution_started": execution_started,
            "execution_finished": execution_finished.isoformat(timespec="seconds"),
            "elapsed_seconds": round((execution_finished - execution_started_dt).total_seconds(), 3),
            "sample_seed": SAMPLE_SEED,
            "sample_draw": "NOT_PERFORMED",
            "font": font_info,
        },
        "denominator_definitions": {
            "rows": "all registry rows in the named population/stratum",
            "unique_pair_id": "distinct observation identities; pair_id is unique per registry row",
            "duplicate_groups": "distinct exact-content duplicate_group_id values",
            "representative_rows": "rows where pair_id equals representative_pair_id",
            "group_presence": "distinct duplicate groups represented in a stratum; a conflicted group may appear in multiple strata",
            "source_corpus_specific_eligible_rows": "registry rows in the explicitly named source/corpus stratum; no Phase-2 eligibility decision is inferred",
        },
        "scenario_definitions": scenarios.to_dict(orient="records"),
        "visual_validation": visual_validation,
        "validation_status": "VERIFIED_BOUNDED_EDA_ARTIFACTS",
        "non_goals_confirmed": [
            "NO_POLICY_SELECTION",
            "NO_CANONICAL_MUTATION",
            "NO_QC_DISPOSITION",
            "NO_NORMALIZATION",
            "NO_TOKENIZATION_OR_MORPHOLOGY",
            "NO_MODEL_FITTING",
            "NO_SAMPLE_DRAW",
            "NO_GATE_CLAIM",
        ],
        "outputs": [
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in output_paths
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_SHA_PATH.write_text(f"{sha256_file(MANIFEST_PATH)}  {MANIFEST_PATH.name}\n", encoding="utf-8")
    log(f"Completed bounded EDA package with {len(output_paths)} hashed outputs")


if __name__ == "__main__":
    main()
