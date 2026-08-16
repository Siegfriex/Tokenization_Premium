"""Synthetic-fixture self-test for scripts/audit/p2_v002_bounded_audit.py.

Independent Data Integrity / Oracle Auditor, event-driven bounded-audit script.
This test never touches real project data (`data/registry/*.parquet`,
`outputs/manifests/QC_MANIFEST_v001.json`) — every fixture is a tiny synthetic
parquet/JSON built in `tmp_path` and wired in via monkeypatching the module's
path constants. Per the Vice Director's pre-trigger directive: this is the
one allowed category of pre-trigger work (script self-test), not a scan of
the current (invalid, FAILED-run) v002 artifact.

Goal: prove the audit script's OWN logic — trigger guard, each of the 13
bounded-audit invariants, verdict aggregation, and idempotency — actually
catches violations rather than trivially returning "pass" regardless of input.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit" / "p2_v002_bounded_audit.py"


def _load_audit_module():
    """Load the audit script as a fresh module object per test (avoids cross-test path-const leakage)."""
    spec = importlib.util.spec_from_file_location("p2_v002_bounded_audit_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# A minimal, self-consistent v001 column set (small subset of the real 44 —
# this test validates the audit's SET-DIFF LOGIC, not literal production
# schema fidelity, which is Codex's engineering scope, not this auditor's).
# `pair_quality_status` is a D-01 field per SSOT §12.1 (present since v001,
# value `review` at Phase 1 per G1_PAIR_REGISTRY_PRECONTRACT_v1.md §16.C) —
# it belongs in the v001 base set, NOT in "v002-new" (see EXPECTED_V002_NEW_COLUMNS
# in the script under test, which correctly omits it for the same reason).
V001_BASE_COLUMNS = ("pair_id", "source_id", "source_tier", "domain", "translation_direction", "logical_corpus", "duplicate_group_id", "pair_quality_status")


def _v001_row(pair_id, source_id="025", source_tier="A", domain="general", direction="KO_TO_EN", corpus="025", dup_group=None):
    return {
        "pair_id": pair_id,
        "source_id": source_id,
        "source_tier": source_tier,
        "domain": domain,
        "translation_direction": direction,
        "logical_corpus": corpus,
        "duplicate_group_id": dup_group or pair_id,
        "pair_quality_status": "review",
    }


def _write_v001(path: Path, rows: list[dict]) -> None:
    pq.write_table(pa.table({col: [r[col] for r in rows] for col in V001_BASE_COLUMNS}), path)


def _v002_row(v001_row: dict, *, exact_duplicate_flag=False, analysis_representative_pair_id=None, pair_quality_status="accepted", primary_rejection_reason=None, **flag_overrides):
    row = dict(v001_row)
    row["analysis_representative_pair_id"] = analysis_representative_pair_id or v001_row["pair_id"]
    row["exact_duplicate_flag"] = exact_duplicate_flag
    row["pair_quality_status"] = pair_quality_status
    row["primary_rejection_reason"] = primary_rejection_reason
    for flag in ("empty_text_flag", "decode_integrity_flag", "markup_dominant_flag", "control_char_excess_flag"):
        row[flag] = flag_overrides.get(flag, False)
    for flag in ("short_text_flag", "long_text_flag", "high_digit_ratio_flag", "high_punctuation_ratio_flag", "script_mix_flag", "translation_quality_review_flag", "lang_side_anomaly_review_flag", "unicode_anomaly_flag", "named_entity_heavy_flag"):
        row[flag] = flag_overrides.get(flag, False)
    for str_flag in ("normalization_rule_version", "normalization_ops", "lang_side_anomaly_reason", "named_entity_evaluation_status", "secondary_rejection_flags", "duplicate_disposition"):
        row[str_flag] = flag_overrides.get(str_flag, "n/a")
    row["analysis_eligible_exact_dedup"] = flag_overrides.get("analysis_eligible_exact_dedup", not row["exact_duplicate_flag"])
    return row


V002_ALL_COLUMNS = V001_BASE_COLUMNS + (
    "analysis_representative_pair_id", "exact_duplicate_flag", "primary_rejection_reason",
    "empty_text_flag", "decode_integrity_flag", "markup_dominant_flag", "control_char_excess_flag",
    "short_text_flag", "long_text_flag", "high_digit_ratio_flag", "high_punctuation_ratio_flag", "script_mix_flag",
    "translation_quality_review_flag", "lang_side_anomaly_review_flag", "unicode_anomaly_flag", "named_entity_heavy_flag",
    "normalization_rule_version", "normalization_ops", "lang_side_anomaly_reason", "named_entity_evaluation_status",
    "secondary_rejection_flags", "duplicate_disposition", "analysis_eligible_exact_dedup",
)


def _write_v002(path: Path, rows: list[dict]) -> None:
    pq.write_table(pa.table({col: [r.get(col) for r in rows] for col in V002_ALL_COLUMNS}), path)


def _clean_pair(n: int) -> tuple[dict, dict]:
    v1 = _v001_row(f"p{n}")
    v2 = _v002_row(v1)
    return v1, v2


def _wire_paths(module, tmp_path: Path, v001_rows, v002_rows, manifest: dict | None, write_qc_flow: bool = True):
    v001_path = tmp_path / "PAIR_REGISTRY_v001.parquet"
    v002_path = tmp_path / "PAIR_REGISTRY_v002.parquet"
    manifest_path = tmp_path / "QC_MANIFEST_v001.json"
    qc_flow_path = tmp_path / "QC_FLOW_v001.csv"
    _write_v001(v001_path, v001_rows)
    _write_v002(v002_path, v002_rows)
    if manifest is not None:
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    if write_qc_flow:
        qc_flow_path.write_text("stage,count\nraw,1\n", encoding="utf-8")
    module.V001_PATH = v001_path
    module.V002_PATH = v002_path
    module.QC_MANIFEST_PATH = manifest_path
    module.QC_FLOW_PATH = qc_flow_path
    module.RUNTIME_SPILL_DIR = tmp_path / "duckdb-spill"
    module.RAW_RECORD_DENOMINATOR = len(v002_rows)
    module.PRIMARY_ELIGIBLE_DENOMINATOR = sum(1 for r in v002_rows if r["source_tier"] == "A")
    return v001_path, v002_path, manifest_path, qc_flow_path


# --- 1. Trigger guard --------------------------------------------------------

def test_trigger_guard_refuses_when_evidence_missing(tmp_path):
    module = _load_audit_module()
    module.V001_PATH = tmp_path / "missing_v001.parquet"
    module.V002_PATH = tmp_path / "missing_v002.parquet"
    module.QC_MANIFEST_PATH = tmp_path / "missing_manifest.json"
    module.QC_FLOW_PATH = tmp_path / "missing_flow.csv"
    with pytest.raises(module.TriggerNotMetError):
        module._require_trigger_evidence()


def test_trigger_guard_rejects_orphaned_parquet_without_manifest(tmp_path):
    """The exact real-world case observed 2026-08-16T21:16 — v002 exists, manifest does not."""
    module = _load_audit_module()
    v1, v2 = _clean_pair(1)
    _wire_paths(module, tmp_path, [v1], [v2], manifest=None, write_qc_flow=False)
    with pytest.raises(module.TriggerNotMetError):
        module._require_trigger_evidence()


def test_trigger_guard_passes_when_all_three_evidence_files_present(tmp_path):
    module = _load_audit_module()
    v1, v2 = _clean_pair(1)
    _wire_paths(module, tmp_path, [v1], [v2], manifest={"sha256": "0" * 64})
    module._require_trigger_evidence()  # must not raise


# --- 2. Individual invariants: prove each check catches its violation -------

def test_row_count_check_pass_and_fail(tmp_path):
    module = _load_audit_module()
    v1, v2 = _clean_pair(1)
    _wire_paths(module, tmp_path, [v1], [v2], manifest={})
    conn = module._open_connection()
    try:
        result = module.check_02_row_count(conn)
    finally:
        conn.close()
    assert result["pass"] is True

    module.RAW_RECORD_DENOMINATOR = 999  # force mismatch
    conn = module._open_connection()
    try:
        result = module.check_02_row_count(conn)
    finally:
        conn.close()
    assert result["pass"] is False


def test_distinct_pair_id_check_catches_duplicate_key(tmp_path):
    module = _load_audit_module()
    v1a, v2a = _clean_pair(1)
    v1b, v2b = _clean_pair(1)  # same pair_id twice -> broken primary key
    _wire_paths(module, tmp_path, [v1a, v1b], [v2a, v2b], manifest={})
    conn = module._open_connection()
    try:
        result = module.check_03_distinct_pair_id(conn)
    finally:
        conn.close()
    assert result["pass"] is False
    assert result["distinct"] < result["total"]


def test_required_schema_check_catches_missing_and_unexpected_columns(tmp_path):
    module = _load_audit_module()
    v1, v2 = _clean_pair(1)
    v001_path, v002_path, _, _ = _wire_paths(module, tmp_path, [v1], [v2], manifest={})
    result = module.check_04_required_schema()
    assert result["pass"] is True

    # Drop a required v002-new column and add an unexpected one.
    broken_row = dict(v2)
    del broken_row["exact_duplicate_flag"]
    broken_row["totally_unexpected_column"] = "x"
    columns = [c for c in V002_ALL_COLUMNS if c != "exact_duplicate_flag"] + ["totally_unexpected_column"]
    pq.write_table(pa.table({c: [broken_row.get(c)] for c in columns}), v002_path)
    result = module.check_04_required_schema()
    assert result["pass"] is False
    assert "exact_duplicate_flag" in result["missing_columns"]
    assert "totally_unexpected_column" in result["unexpected_new_columns"]


def test_exact_duplicate_flag_invariant_catches_violation(tmp_path):
    module = _load_audit_module()
    v1, v2 = _clean_pair(1)
    # Violate: flag says duplicate, but representative == self (should be non-duplicate).
    v2_broken = dict(v2)
    v2_broken["exact_duplicate_flag"] = True
    _wire_paths(module, tmp_path, [v1], [v2_broken], manifest={})
    conn = module._open_connection()
    try:
        result = module.check_05_exact_duplicate_flag_invariant(conn)
    finally:
        conn.close()
    assert result["pass"] is False
    assert result["violations"] == 1


def test_analysis_representative_invariant_catches_wrong_representative(tmp_path):
    module = _load_audit_module()
    v1a, v2a = _v001_row("p1", corpus="025", dup_group="g1"), None
    v1b, v2b = _v001_row("p2", corpus="025", dup_group="g1"), None
    v2a = _v002_row(v1a, exact_duplicate_flag=False, analysis_representative_pair_id="p1")
    # p2 is in the same duplicate group as p1; min(pair_id) within the group is "p1",
    # so p2's representative SHOULD be "p1" too -- but this fixture wrongly self-points.
    v2b = _v002_row(v1b, exact_duplicate_flag=True, analysis_representative_pair_id="p2")
    _wire_paths(module, tmp_path, [v1a, v1b], [v2a, v2b], manifest={})
    conn = module._open_connection()
    try:
        result = module.check_06_analysis_representative_pair_id_invariant(conn)
    finally:
        conn.close()
    assert result["pass"] is False
    assert result["violations"] == 1


def test_accepted_rejected_disposition_catches_mislabeled_row(tmp_path):
    module = _load_audit_module()
    v1, v2 = _clean_pair(1)
    # Structural flag true (empty_text_flag) but status wrongly left "accepted".
    v2_broken = dict(v2)
    v2_broken["empty_text_flag"] = True
    v2_broken["pair_quality_status"] = "accepted"
    _wire_paths(module, tmp_path, [v1], [v2_broken], manifest={})
    conn = module._open_connection()
    try:
        result = module.check_07_accepted_rejected_counts(conn)
    finally:
        conn.close()
    assert result["pass"] is False
    assert result["disposition_rule_violations"] == 1


def test_composition_diff_catches_category_count_drift(tmp_path):
    module = _load_audit_module()
    v1a = _v001_row("p1", source_id="025", domain="general", direction="KO_TO_EN", corpus="025")
    v1b = _v001_row("p2", source_id="026", domain="legal", direction="EN_TO_KO", corpus="026")
    v2a = _v002_row(v1a)
    v2b = _v002_row(v1b)
    # Silently flip p2's domain in v002 relative to v001 -- exactly the "row transform
    # changed composition" bug SS4's zero-row-deletion guarantee is meant to catch.
    v2b_drifted = dict(v2b)
    v2b_drifted["domain"] = "general"
    _wire_paths(module, tmp_path, [v1a, v1b], [v2a, v2b_drifted], manifest={})
    conn = module._open_connection()
    try:
        result = module.check_09_10_11_13_composition_and_catastrophic_loss(conn)
    finally:
        conn.close()
    assert result["pass"] is False
    assert result["per_column"]["domain"]["pass"] is False
    # source_id/translation_direction/logical_corpus were untouched -- must still pass.
    assert result["per_column"]["source_id"]["pass"] is True


def test_anomaly_review_aggregates_catches_review_flag_used_as_hard_gate(tmp_path):
    module = _load_audit_module()
    v1, v2 = _clean_pair(1)
    v2_broken = dict(v2)
    v2_broken["lang_side_anomaly_review_flag"] = True
    v2_broken["pair_quality_status"] = "rejected"
    v2_broken["primary_rejection_reason"] = None  # no structural reason recorded -> review flag silently gated
    _wire_paths(module, tmp_path, [v1], [v2_broken], manifest={})
    conn = module._open_connection()
    try:
        result = module.check_12_anomaly_review_aggregates(conn)
    finally:
        conn.close()
    assert result["pass"] is False
    assert result["review_only_gating_violations"] == 1


# --- 3. End-to-end verdict aggregation + report-schema + idempotency -------

def _build_clean_fixture(module, tmp_path):
    rows_v1 = [_v001_row(f"p{i}", corpus="025" if i % 2 == 0 else "026", source_id="025" if i % 2 == 0 else "026") for i in range(4)]
    rows_v2 = [_v002_row(r) for r in rows_v1]
    v001_path, v002_path, manifest_path, _ = _wire_paths(module, tmp_path, rows_v1, rows_v2, manifest={})
    # Manifest sha256 must match the actual written v002 file for check_01 to pass.
    actual_sha = module.sha256_file(v002_path)
    manifest_path.write_text(json.dumps({"artifact_sha256": actual_sha}), encoding="utf-8")
    return rows_v1, rows_v2


def test_run_bounded_audit_end_to_end_pass_verdict(tmp_path):
    module = _load_audit_module()
    _build_clean_fixture(module, tmp_path)
    report = module.run_bounded_audit()
    assert report["verdict"] == "P2_BOUNDED_AUDIT_PASS"
    assert report["material_findings"] == []
    # Output-schema check: every check result carries the two contract-required keys.
    assert all({"check", "pass"} <= set(c) for c in report["checks"])


def test_run_bounded_audit_end_to_end_material_finding_verdict(tmp_path):
    module = _load_audit_module()
    rows_v1, rows_v2 = _build_clean_fixture(module, tmp_path)
    rows_v2[0]["exact_duplicate_flag"] = True  # introduce exactly one violation
    _write_v002(module.V002_PATH, rows_v2)
    actual_sha = module.sha256_file(module.V002_PATH)
    module.QC_MANIFEST_PATH.write_text(json.dumps({"artifact_sha256": actual_sha}), encoding="utf-8")
    report = module.run_bounded_audit()
    assert report["verdict"] == "P2_BOUNDED_AUDIT_MATERIAL_FINDING"
    assert len(report["material_findings"]) >= 1
    assert any(f["check"] == "05_exact_duplicate_flag_invariant" for f in report["material_findings"])


def test_run_bounded_audit_is_idempotent(tmp_path):
    """Running twice against identical fixtures yields an identical report (read-only, no
    QC-judgment state is mutated on disk between runs)."""
    module = _load_audit_module()
    _build_clean_fixture(module, tmp_path)
    report_1 = module.run_bounded_audit()
    report_2 = module.run_bounded_audit()
    assert report_1 == report_2
