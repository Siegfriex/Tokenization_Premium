"""Independent bounded audit for PAIR_REGISTRY_v002 (Phase 2 minimal-QC output).

Role: Independent Data Integrity / Oracle Auditor (event-driven, bounded scope).
This script does NOT review or import the P2 remediation/execution logic
(`src/tokenization_premium/phase2.py`). Every invariant below is re-derived
directly from the frozen research contract text so the audit stays
independent of the implementation it is checking:

  - research/p2-qc-claude@b9990afbf3fc0ed2a5e80fb4def1565e9ba3ebf4
    docs/contracts/P2_NORMALIZE_QC_PRECONTRACT_v1.md (SS3, SS4, SS7, SS9, SS11)
  - impl/p2-scaffold-codex@2a65326583d51c53e1abe0caba04fb9b36cd2b23
    docs/contracts/P2_MINIMAL_QC_ENGINEERING_HANDOFF_v1.md

Shared, non-QC infrastructure (SHA-256 streaming, DuckDB memory-limit
resolution) is reused from `tokenization_premium.hashing` /
`tokenization_premium.registry` because those are generic utilities, not
the QC decision logic under audit.

TRIGGER PRECONDITION (enforced by `_require_trigger_evidence`):
this script refuses to run its bounded checks unless BOTH
`data/registry/PAIR_REGISTRY_v002.parquet` AND
`outputs/manifests/QC_MANIFEST_v001.json` exist. A parquet file produced by
a FAILED run with no accompanying manifest is not a valid trigger — do not
bypass this guard to "peek" at an orphaned artifact.

No broad/exploratory EDA is performed here. Every query below maps to one
of the 13 bounded-audit items in the Vice Director's audit charter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tokenization_premium.hashing import sha256_file  # noqa: E402  (pure I/O utility, not QC logic)
from tokenization_premium.registry import resolve_duckdb_memory_limit  # noqa: E402  (pure runtime-safety utility)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
V001_PATH = PROJECT_ROOT / "data/registry/PAIR_REGISTRY_v001.parquet"
V002_PATH = PROJECT_ROOT / "data/registry/PAIR_REGISTRY_v002.parquet"
QC_MANIFEST_PATH = PROJECT_ROOT / "outputs/manifests/QC_MANIFEST_v001.json"
QC_FLOW_PATH = PROJECT_ROOT / "outputs/reports/QC_FLOW_v001.csv"
RUNTIME_SPILL_DIR = PROJECT_ROOT / ".runtime/p2-v002-audit-recon/duckdb-spill"

RAW_RECORD_DENOMINATOR = 5_652_925
TIER_A_025_EXPECTED = 2_700_345
TIER_A_026_EXPECTED = 1_350_162
PRIMARY_ELIGIBLE_DENOMINATOR = TIER_A_025_EXPECTED + TIER_A_026_EXPECTED  # 4,050,507

# Precontract SS3a: the 5 structural hard-exclusion flags, in the exact
# `primary_rejection_reason` priority order defined in SS3c.
STRUCTURAL_FLAGS_IN_PRIORITY_ORDER = (
    "empty_text_flag",
    "decode_integrity_flag",
    "markup_dominant_flag",
    "control_char_excess_flag",
    "exact_duplicate_flag",
)

# Precontract SS9: 21 columns introduced by v002 on top of v001's 44, PLUS
# `exact_duplicate_flag` (self-test correction 2026-08-16 — SS9's own "v002
# 신규 컬럼" table lists only 4 of the 5 SS3a/SS3c structural hard-exclusion
# flags, omitting `exact_duplicate_flag`; that omission was faithfully
# transcribed here too. check_05/check_07 already read this column directly,
# so leaving it out of this expected-set would make check_04 report it as an
# "unexpected_new_column" on every real run — a false MATERIAL_FINDING on a
# perfectly valid artifact. Caught by tests/test_p2_v002_bounded_audit.py's
# synthetic-fixture self-test; the same omission in the precontract doc
# itself (docs/contracts/P2_NORMALIZE_QC_PRECONTRACT_v1.md SS9) is a
# different branch's file and is flagged upstream, not edited here.)
EXPECTED_V002_NEW_COLUMNS: dict[str, str] = {
    "normalization_rule_version": "VARCHAR",
    "normalization_ops": "VARCHAR",
    "unicode_anomaly_flag": "BOOLEAN",
    "empty_text_flag": "BOOLEAN",
    "markup_dominant_flag": "BOOLEAN",
    "control_char_excess_flag": "BOOLEAN",
    "decode_integrity_flag": "BOOLEAN",
    "exact_duplicate_flag": "BOOLEAN",
    "short_text_flag": "BOOLEAN",
    "long_text_flag": "BOOLEAN",
    "high_digit_ratio_flag": "BOOLEAN",
    "high_punctuation_ratio_flag": "BOOLEAN",
    "script_mix_flag": "BOOLEAN",
    "translation_quality_review_flag": "BOOLEAN",
    "lang_side_anomaly_review_flag": "BOOLEAN",
    "lang_side_anomaly_reason": "VARCHAR",
    "named_entity_heavy_flag": "BOOLEAN",
    "named_entity_evaluation_status": "VARCHAR",
    "primary_rejection_reason": "VARCHAR",
    "secondary_rejection_flags": "VARCHAR",
    "analysis_representative_pair_id": "VARCHAR",
    "duplicate_disposition": "VARCHAR",
    "analysis_eligible_exact_dedup": "BOOLEAN",
}

# Columns whose per-category row counts MUST be byte-for-byte identical
# between v001 and v002, because the precontract guarantees no row is
# ever deleted or re-keyed in Phase 2 (SS4: "row는 삭제하지 않는다").
# Any drift here is by definition a catastrophic transform bug, not a
# research judgment call.
INVARIANT_COMPOSITION_COLUMNS = ("source_id", "domain", "translation_direction", "logical_corpus")


class TriggerNotMetError(RuntimeError):
    """Raised when the event-driven precondition for a bounded audit is not satisfied."""


class MaterialFinding(dict):
    """A single audit item that threatens a specific downstream estimand."""


def _sql_literal(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def _scalar(connection: duckdb.DuckDBPyConnection, query: str) -> Any:
    row = connection.execute(query).fetchone()
    assert row is not None and len(row) == 1, f"expected 1x1 result, got {row!r} for query: {query}"
    return row[0]


def _rows(connection: duckdb.DuckDBPyConnection, query: str) -> list[tuple[Any, ...]]:
    return connection.execute(query).fetchall()


def _require_trigger_evidence() -> None:
    """Refuse to run unless a valid v002 artifact AND its manifest both exist.

    A `.parquet` written by a FAILED run (no manifest) is exactly the kind
    of orphaned artifact this guard exists to reject — see the Integration
    Steward's 2026-08-16T21:16 report: v002 existed with a verified SHA-256
    but the run failed before QC_MANIFEST_v001.json / QC_FLOW_v001.csv were
    written. That state is NOT a valid trigger.
    """
    missing = [str(p) for p in (V002_PATH, QC_MANIFEST_PATH, QC_FLOW_PATH) if not p.exists()]
    if missing:
        raise TriggerNotMetError(
            "Bounded audit trigger not met — missing required evidence: "
            + ", ".join(missing)
            + ". Per audit charter: do not run full bounded audit before a corrected "
            "canonical v002 AND its manifest both exist."
        )


def _open_connection() -> duckdb.DuckDBPyConnection:
    RUNTIME_SPILL_DIR.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    connection.execute("SET preserve_insertion_order = false")
    connection.execute(f"SET memory_limit = '{resolve_duckdb_memory_limit()}'")
    connection.execute(f"SET temp_directory = '{_sql_literal(RUNTIME_SPILL_DIR)}'")
    return connection


def check_01_artifact_sha(manifest: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute v002's file SHA-256 and compare vs the manifest's recorded value."""
    actual_sha256 = sha256_file(V002_PATH)
    candidates = _find_manifest_sha256_candidates(manifest)
    matched = [key for key, value in candidates.items() if value == actual_sha256]
    return {
        "check": "01_artifact_sha256",
        "actual_sha256": actual_sha256,
        "manifest_candidates": candidates,
        "pass": bool(matched),
        "matched_manifest_key": matched[0] if matched else None,
    }


def _find_manifest_sha256_candidates(manifest: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Best-effort recursive scan for any manifest key that looks like a v002 SHA-256 field.

    The manifest schema has never actually been produced by a successful run
    (every attempt so far has failed before this stage), so this cannot be
    hard-coded to one key path — it must discover whatever shape the first
    real manifest actually has and report it for human confirmation.
    """
    found: dict[str, str] = {}
    for key, value in manifest.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower()):
            found[path] = value
        elif isinstance(value, dict):
            found.update(_find_manifest_sha256_candidates(value, path))
    return found


def check_02_row_count(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    actual = int(_scalar(connection, f"SELECT count(*) FROM read_parquet('{_sql_literal(V002_PATH)}')"))
    return {"check": "02_row_count", "expected": RAW_RECORD_DENOMINATOR, "actual": actual, "pass": actual == RAW_RECORD_DENOMINATOR}


def check_03_distinct_pair_id(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    relation = f"read_parquet('{_sql_literal(V002_PATH)}')"
    total = int(_scalar(connection, f"SELECT count(*) FROM {relation}"))
    distinct = int(_scalar(connection, f"SELECT count(DISTINCT pair_id) FROM {relation}"))
    nulls = int(_scalar(connection, f"SELECT count(*) FROM {relation} WHERE pair_id IS NULL"))
    return {"check": "03_distinct_pair_id", "total": total, "distinct": distinct, "null": nulls, "pass": distinct == total and nulls == 0}


def check_04_required_schema() -> dict[str, Any]:
    actual_schema = pq.ParquetFile(V002_PATH).schema_arrow
    actual_names = set(actual_schema.names)
    v001_names = set(pq.ParquetFile(V001_PATH).schema_arrow.names)
    expected_names = v001_names | set(EXPECTED_V002_NEW_COLUMNS)
    missing = sorted(expected_names - actual_names)
    unexpected_new = sorted(actual_names - expected_names)
    return {
        "check": "04_required_schema",
        "expected_column_count": len(expected_names),
        "actual_column_count": len(actual_names),
        "missing_columns": missing,
        "unexpected_new_columns": unexpected_new,
        "pass": not missing and not unexpected_new,
    }


def check_05_exact_duplicate_flag_invariant(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """exact_duplicate_flag MUST equal (pair_id != analysis_representative_pair_id) — SS3a."""
    relation = f"read_parquet('{_sql_literal(V002_PATH)}')"
    violations = int(
        _scalar(
            connection,
            f"SELECT count(*) FROM {relation} "
            "WHERE exact_duplicate_flag <> (pair_id <> analysis_representative_pair_id)",
        )
    )
    return {"check": "05_exact_duplicate_flag_invariant", "violations": violations, "pass": violations == 0}


def check_06_analysis_representative_pair_id_invariant(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Re-derive analysis_representative_pair_id independently per SS4 and diff against stored value.

    Rule (precontract SS4): within a duplicate_group_id,
      eligible = candidates where logical_corpus IN ('025', '026')
      analysis_representative_pair_id = min(eligible) if eligible non-empty else min(candidates)
    """
    relation = f"read_parquet('{_sql_literal(V002_PATH)}')"
    query = f"""
        WITH group_eligible AS (
            SELECT duplicate_group_id, min(pair_id) AS eligible_min
            FROM {relation}
            WHERE logical_corpus IN ('025', '026')
            GROUP BY duplicate_group_id
        ),
        group_any AS (
            SELECT duplicate_group_id, min(pair_id) AS any_min
            FROM {relation}
            GROUP BY duplicate_group_id
        ),
        expected AS (
            SELECT a.duplicate_group_id, COALESCE(e.eligible_min, a.any_min) AS expected_rep
            FROM group_any a
            LEFT JOIN group_eligible e USING (duplicate_group_id)
        )
        SELECT count(*)
        FROM {relation} r
        JOIN expected x USING (duplicate_group_id)
        WHERE r.analysis_representative_pair_id <> x.expected_rep
    """
    violations = int(_scalar(connection, query))
    return {"check": "06_analysis_representative_pair_id_invariant", "violations": violations, "pass": violations == 0}


def check_07_accepted_rejected_counts(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """pair_quality_status disposition per SS3c: rejected iff >=1 of the 5 structural flags true."""
    relation = f"read_parquet('{_sql_literal(V002_PATH)}')"
    flags_or = " OR ".join(STRUCTURAL_FLAGS_IN_PRIORITY_ORDER)
    disposition_violations = int(
        _scalar(
            connection,
            f"SELECT count(*) FROM {relation} WHERE "
            f"(({flags_or}) AND pair_quality_status <> 'rejected') OR "
            f"(NOT ({flags_or}) AND pair_quality_status <> 'accepted')",
        )
    )
    other_status_values = _rows(connection, f"SELECT DISTINCT pair_quality_status FROM {relation} WHERE pair_quality_status NOT IN ('accepted', 'rejected')")
    accepted_n = int(_scalar(connection, f"SELECT count(*) FROM {relation} WHERE pair_quality_status = 'accepted'"))
    rejected_n = int(_scalar(connection, f"SELECT count(*) FROM {relation} WHERE pair_quality_status = 'rejected'"))
    return {
        "check": "07_accepted_rejected_counts",
        "accepted": accepted_n,
        "rejected": rejected_n,
        "disposition_rule_violations": disposition_violations,
        "unexpected_status_values": [row[0] for row in other_status_values],
        "pass": disposition_violations == 0 and not other_status_values,
    }


def check_08_primary_tier_a_realized_n(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    relation = f"read_parquet('{_sql_literal(V002_PATH)}')"
    tier_a_total = int(_scalar(connection, f"SELECT count(*) FROM {relation} WHERE source_tier = 'A'"))
    per_corpus = _rows(connection, f"SELECT logical_corpus, count(*) FROM {relation} WHERE source_tier = 'A' GROUP BY logical_corpus ORDER BY logical_corpus")
    return {
        "check": "08_primary_tier_a_realized_n",
        "expected_total": PRIMARY_ELIGIBLE_DENOMINATOR,
        "actual_total": tier_a_total,
        "per_corpus": {row[0]: row[1] for row in per_corpus},
        "expected_per_corpus": {"025": TIER_A_025_EXPECTED, "026": TIER_A_026_EXPECTED},
        "pass": tier_a_total == PRIMARY_ELIGIBLE_DENOMINATOR,
    }


def _composition_diff(connection: duckdb.DuckDBPyConnection, column: str) -> dict[str, Any]:
    v001_relation = f"read_parquet('{_sql_literal(V001_PATH)}')"
    v002_relation = f"read_parquet('{_sql_literal(V002_PATH)}')"
    query = f"""
        WITH v1 AS (SELECT {column} AS key, count(*) AS n FROM {v001_relation} GROUP BY {column}),
             v2 AS (SELECT {column} AS key, count(*) AS n FROM {v002_relation} GROUP BY {column})
        SELECT COALESCE(v1.key, v2.key) AS key, v1.n AS v001_n, v2.n AS v002_n
        FROM v1 FULL OUTER JOIN v2 USING (key)
        WHERE v1.n IS DISTINCT FROM v2.n
        ORDER BY key
    """
    drifted = _rows(connection, query)
    return {
        "column": column,
        "drifted_categories": [{"key": row[0], "v001_n": row[1], "v002_n": row[2]} for row in drifted],
        "pass": not drifted,
    }


def check_09_10_11_13_composition_and_catastrophic_loss(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Items 9 (source), 10 (domain), 11 (translation_direction) composition, plus the item-13
    catastrophic-loss framing: because Phase 2 never deletes or re-keys rows (SS4), per-category
    row counts must be IDENTICAL between v001 and v002. Any drift is catastrophic by definition,
    not a judgment call.
    """
    diffs = {column: _composition_diff(connection, column) for column in INVARIANT_COMPOSITION_COLUMNS}
    return {
        "check": "09_10_11_13_source_domain_direction_composition_and_catastrophic_loss",
        "per_column": diffs,
        "pass": all(d["pass"] for d in diffs.values()),
    }


def check_12_anomaly_review_aggregates(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Report-only: counts of review/advisory flags. These never gate pair_quality_status (SS3b)."""
    relation = f"read_parquet('{_sql_literal(V002_PATH)}')"
    review_flags = (
        "lang_side_anomaly_review_flag",
        "translation_quality_review_flag",
        "script_mix_flag",
        "short_text_flag",
        "long_text_flag",
        "high_digit_ratio_flag",
        "high_punctuation_ratio_flag",
        "unicode_anomaly_flag",
    )
    counts = {flag: int(_scalar(connection, f"SELECT count(*) FROM {relation} WHERE {flag}")) for flag in review_flags}
    non_gating_violations = int(
        _scalar(
            connection,
            f"SELECT count(*) FROM {relation} WHERE "
            "(lang_side_anomaly_review_flag OR translation_quality_review_flag) "
            "AND pair_quality_status = 'rejected' "
            "AND primary_rejection_reason IS NULL",
        )
    )
    return {
        "check": "12_anomaly_review_aggregates",
        "counts": counts,
        "review_only_gating_violations": non_gating_violations,
        "pass": non_gating_violations == 0,
    }


def run_bounded_audit() -> dict[str, Any]:
    _require_trigger_evidence()
    manifest = json.loads(QC_MANIFEST_PATH.read_text(encoding="utf-8"))
    connection = _open_connection()
    try:
        results = [
            check_01_artifact_sha(manifest),
            check_02_row_count(connection),
            check_03_distinct_pair_id(connection),
            check_04_required_schema(),
            check_05_exact_duplicate_flag_invariant(connection),
            check_06_analysis_representative_pair_id_invariant(connection),
            check_07_accepted_rejected_counts(connection),
            check_08_primary_tier_a_realized_n(connection),
            check_09_10_11_13_composition_and_catastrophic_loss(connection),
            check_12_anomaly_review_aggregates(connection),
        ]
    finally:
        connection.close()

    material_findings = [r for r in results if not r["pass"]]
    verdict = "P2_BOUNDED_AUDIT_PASS" if not material_findings else "P2_BOUNDED_AUDIT_MATERIAL_FINDING"
    return {"verdict": verdict, "checks": results, "material_findings": material_findings}


if __name__ == "__main__":
    try:
        report = run_bounded_audit()
    except TriggerNotMetError as exc:
        print(f"TRIGGER_NOT_MET: {exc}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0 if report["verdict"] == "P2_BOUNDED_AUDIT_PASS" else 1)
