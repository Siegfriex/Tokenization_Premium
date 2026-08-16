"""Phase-2 v1.1 minimal-QC engineering contract tests; synthetic inputs only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import tokenization_premium.phase2 as phase2
from tokenization_premium.hashing import sha256_file
from tokenization_premium.paths import PROJECT_ROOT
from tokenization_premium.phase2 import (
    BLOCKED_BY_P2_CONTRACT,
    EXACT_DUPLICATE_IDENTITY_SCOPE,
    NORMALIZATION_OPERATIONS,
    P2_AGGREGATE_COUNT_FIELDS,
    P2_COMPLETION_STATUS,
    P2_CONTRACT_COMMIT,
    P2_OUTPUT_SCHEMA,
    decode_integrity_ok,
    derive_pair_quality_status,
    empty_text_flag,
    iter_parquet_batches,
    language_side_anomaly_review,
    manual_audit_import_schema,
    named_entity_deferred_fields,
    normalize_ssot_text,
    open_phase2_duckdb,
    require_phase2_canonical_evidence,
    select_analysis_representative_pair_id,
    validate_d01_manifest_handoff,
    validate_d01_row_linkage,
    validate_phase2_output_schema,
    write_parquet_batches_atomic,
)
from tokenization_premium.registry import duplicate_group_id, provenance_pair_id
from tokenization_premium.schemas import pair_registry_schema


def _synthetic_d01_row(
    pair_id: str,
    *,
    logical_corpus: str,
    duplicate_id: str,
    representative_pair_id: str,
    ko_text: str,
    en_text: str,
) -> dict[str, object]:
    return {
        "pair_id": pair_id,
        "source_id": f"source-{logical_corpus.lower()}",
        "source_tier": "A" if logical_corpus in {"025", "026"} else None,
        "domain": "일상생활",
        "sentence_type": "other",
        "translation_direction": "KO_TO_EN",
        "ko_text_raw": ko_text,
        "en_text_raw": en_text,
        "ko_text_nfc": None,
        "en_text_nfc": None,
        "ko_text_analysis": None,
        "en_text_analysis": None,
        "pair_quality_status": "review",
        "pair_quality_score": None,
        "pair_version": "v001",
        "source_license_note": "synthetic-test-only",
        "source_record_id": pair_id,
        "raw_locator": json.dumps({"pair_id": pair_id}, sort_keys=True),
        "duplicate_group_id": duplicate_id,
        "representative_pair_id": representative_pair_id,
        "domain_raw": None,
        "subdomain_raw": None,
        "source_provenance_raw": None,
        "is_validation_upstream": False,
        "translation_direction_raw": "KO_TO_EN",
        "translation_direction_review_flag": False,
        "mt_field_present": False,
        "sentence_type_raw": None,
        "sentence_type_provenance_status": "SYNTHETIC_TEST",
        "normalization_status": "PENDING_PHASE2",
        "qc_stage_status": "PENDING_PHASE2",
        "direction_conflict_flag": False,
        "domain_conflict_flag": False,
        "source_id_conflict_flag": False,
        "source_provenance_raw_conflict_flag": False,
        "logical_corpus": logical_corpus,
        "canonical_ingest_role": f"SYNTHETIC_{logical_corpus}",
        "raw_file_relative_path": f"synthetic/{logical_corpus}.json",
        "raw_file_sha256": "0" * 64,
        "raw_sheet_name": None,
        "raw_physical_row_number": None,
        "source_native_id": None,
        "source_native_sid": None,
        "raw_metadata_json": "{}",
    }


def _prepare_synthetic_phase2_project(tmp_path: Path) -> dict[str, Any]:
    project_root = tmp_path / "project"
    input_path = project_root / "data/registry/PAIR_REGISTRY_v001.parquet"
    output_path = project_root / "data/registry/PAIR_REGISTRY_v002.parquet"
    d01_manifest_path = project_root / "outputs/manifests/PAIR_REGISTRY_MANIFEST_v001.json"
    contract_path = project_root / "docs/contracts/P2_NORMALIZE_QC_PRECONTRACT_v1.md"
    runtime_dir = project_root / ".runtime/p2-e2e"
    rows = [
        _synthetic_d01_row(
            "pair_legacy_duplicate",
            logical_corpus="LEGACY",
            duplicate_id="dup-exact",
            representative_pair_id="pair_legacy_duplicate",
            ko_text="같은 문장입니다",
            en_text="This is the same sentence.",
        ),
        _synthetic_d01_row(
            "pair_tier_a_survivor",
            logical_corpus="025",
            duplicate_id="dup-exact",
            representative_pair_id="pair_legacy_duplicate",
            ko_text="같은 문장입니다",
            en_text="This is the same sentence.",
        ),
        _synthetic_d01_row(
            "pair_unique_026",
            logical_corpus="026",
            duplicate_id="dup-026",
            representative_pair_id="pair_unique_026",
            ko_text="기술 문장입니다",
            en_text="This is a technical sentence.",
        ),
        _synthetic_d01_row(
            "pair_unique_legacy",
            logical_corpus="LEGACY",
            duplicate_id="dup-legacy",
            representative_pair_id="pair_unique_legacy",
            ko_text="문화 문장입니다",
            en_text="This is a cultural sentence.",
        ),
    ]
    input_path.parent.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=pair_registry_schema()), input_path)
    d01_manifest_path.parent.mkdir(parents=True)
    d01_manifest_path.write_text(
        json.dumps(
            {"pair_registry": {"sha256": sha256_file(input_path), "row_count": len(rows)}},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("synthetic copy of frozen P2 contract\n", encoding="utf-8")
    return {
        "project_root": project_root,
        "input_path": input_path,
        "output_path": output_path,
        "d01_manifest_path": d01_manifest_path,
        "contract_path": contract_path,
        "runtime_dir": runtime_dir,
        "row_count": len(rows),
        "run_id": "P2_SYNTHETIC_E2E",
    }


@pytest.mark.parametrize(
    ("source", "expected_nfc", "expected_analysis"),
    [
        ("e\u0301", "é", "é"),
        ("\ufeff문장\ufeff", "\ufeff문장\ufeff", "문장"),
        ("  leading and trailing  ", "  leading and trailing  ", "leading and trailing"),
        ("내부  반복   공백", "내부  반복   공백", "내부  반복   공백"),
        (" \t첫째\n\t둘째\t ", " \t첫째\n\t둘째\t ", "첫째\n\t둘째"),
        ("ＡＢＣ", "ＡＢＣ", "ＡＢＣ"),
        ("MiXeD Case", "MiXeD Case", "MiXeD Case"),
    ],
)
def test_ssot_normalization_is_exact_and_non_destructive(source: str, expected_nfc: str, expected_analysis: str) -> None:
    result = normalize_ssot_text(source)
    assert result.nfc_text == expected_nfc
    assert result.analysis_text == expected_analysis
    assert result.operations == NORMALIZATION_OPERATIONS


def test_internal_bom_is_not_silently_deleted() -> None:
    result = normalize_ssot_text("텍스\ufeff트")
    assert result.analysis_text == "텍스\ufeff트"
    assert result.unicode_anomaly_flag is True
    assert "INTERNAL_ZERO_WIDTH" in result.unicode_anomaly_reasons


def test_edge_bom_only_is_removed_without_false_internal_signal() -> None:
    result = normalize_ssot_text("\ufeff문장\ufeff")
    assert result.analysis_text == "문장"
    assert result.unicode_anomaly_flag is False


def test_null_is_rejected_and_empty_is_observable_after_normalization() -> None:
    with pytest.raises(TypeError, match="must be str"):
        normalize_ssot_text(None)  # type: ignore[arg-type]
    assert normalize_ssot_text(" \ufeff ").analysis_text == "\ufeff"
    assert normalize_ssot_text("   ").analysis_text == ""
    assert empty_text_flag(None, "English") is True
    assert empty_text_flag("한국어", "   ") is True
    assert empty_text_flag("한국어", "English") is False


@pytest.mark.parametrize("value", ["OpenAI API 사용 방법", "Python GPU 모델"])
def test_language_smoke_technical_english_in_ko_is_not_anomaly(value: str) -> None:
    result = language_side_anomaly_review(value, expected_side="KO")
    assert result.lang_side_anomaly_review_flag is False
    assert result.lang_side_anomaly_reason == "NONE"


def test_language_smoke_korean_proper_noun_in_en_is_not_anomaly() -> None:
    result = language_side_anomaly_review("Korea 서울", expected_side="EN")
    assert result.lang_side_anomaly_review_flag is False
    assert result.lang_side_anomaly_reason == "NONE"


def test_language_smoke_clear_latin_only_ko_is_review() -> None:
    result = language_side_anomaly_review("This sentence is entirely English", expected_side="KO")
    assert result.lang_side_anomaly_review_flag is True
    assert result.lang_side_anomaly_reason == "KO_NO_HANGUL_LATIN_DOMINANT"


def test_language_smoke_clear_hangul_only_en_is_review() -> None:
    result = language_side_anomaly_review("이 문장은 전부 한글입니다", expected_side="EN")
    assert result.lang_side_anomaly_review_flag is True
    assert result.lang_side_anomaly_reason == "EN_NO_LATIN_HANGUL_DOMINANT"


@pytest.mark.parametrize("value", ["ID42", "https://openai.com/v1", "12345", "x = f(y);"])
def test_short_identifier_url_numbers_and_code_never_become_hard_failure(value: str) -> None:
    review = language_side_anomaly_review(value, expected_side="KO")
    status = derive_pair_quality_status(
        {"lang_side_anomaly_review_flag": review.lang_side_anomaly_review_flag}
    )
    assert status == "accepted"


def test_review_is_not_rejection() -> None:
    review = language_side_anomaly_review("This sentence is entirely English", expected_side="KO")
    assert review.lang_side_anomaly_review_flag is True
    assert derive_pair_quality_status({"lang_side_anomaly_review_flag": True}) == "accepted"
    assert derive_pair_quality_status({"empty_text_flag": True, "lang_side_anomaly_review_flag": False}) == "rejected"


def test_manual_audit_interface_is_nullable_and_does_not_fabricate_labels() -> None:
    schema = manual_audit_import_schema()
    assert schema.names == [
        "pair_id",
        "manual_semantic_score",
        "manual_language_side_status",
        "manual_audit_status",
    ]
    assert all(schema.field(name).nullable for name in schema.names[1:])


def test_named_entity_fields_are_explicitly_deferred_without_model_output() -> None:
    assert named_entity_deferred_fields() == {
        "named_entity_heavy_flag": None,
        "named_entity_evaluation_status": "DEFERRED",
    }


def test_cohort_aware_duplicate_survivor_keeps_tier_a_primary_row() -> None:
    candidates = [
        {"pair_id": "pair_000_legacy", "primary_analysis_eligible": False, "representative_pair_id": "pair_000_legacy"},
        {"pair_id": "pair_900_tier_a", "primary_analysis_eligible": True, "representative_pair_id": "pair_000_legacy"},
    ]
    assert select_analysis_representative_pair_id(candidates) == "pair_900_tier_a"
    assert {candidate["representative_pair_id"] for candidate in candidates} == {"pair_000_legacy"}


def test_duplicate_group_is_exact_not_near_duplicate_boundary() -> None:
    exact = duplicate_group_id("같은 문장", "same sentence")
    repeated = duplicate_group_id("같은 문장", "same sentence")
    near = duplicate_group_id("같은 문장!", "same sentence")
    paraphrase = duplicate_group_id("동일한 문장", "an equivalent sentence")
    assert exact == repeated
    assert exact != near != paraphrase
    assert EXACT_DUPLICATE_IDENTITY_SCOPE == "EXACT_RAW_KO_EN_ONLY_NOT_NEAR_DUPLICATE_OR_PARAPHRASE"


def test_decode_integrity_is_unicode_only() -> None:
    assert decode_integrity_ok("Unicode 읽기 OK") is True
    assert decode_integrity_ok("lossy \ufffd") is False
    assert decode_integrity_ok("unpaired \ud800") is False


def test_d01_manifest_handoff_uses_recorded_manifest_and_oracle_without_rescan() -> None:
    manifest = json.loads((PROJECT_ROOT / "outputs/manifests/PAIR_REGISTRY_MANIFEST_v001.json").read_text(encoding="utf-8"))
    oracle = json.loads((PROJECT_ROOT / "outputs/manifests/data_recon/G1_INGEST_EXPECTATIONS_v001.json").read_text(encoding="utf-8"))
    result = validate_d01_manifest_handoff(manifest, oracle)
    assert result.status == "PASS"
    assert result.row_count == result.pair_id_distinct == 5_652_925
    assert result.canonical_input_count == 16


def test_d01_row_pair_locator_ingest_role_and_raw_sha_linkage() -> None:
    oracle = json.loads((PROJECT_ROOT / "outputs/manifests/data_recon/G1_INGEST_EXPECTATIONS_v001.json").read_text(encoding="utf-8"))
    entry = oracle["double_ingest_prevention_contract"]["ingest_allowlist"][0]
    source_id = "synthetic-source"
    source_record_id = "synthetic-record"
    row = {
        "pair_id": provenance_pair_id(source_id, source_record_id),
        "source_id": source_id,
        "source_record_id": source_record_id,
        "raw_locator": json.dumps({"row": 1}),
        "canonical_ingest_role": entry["canonical_ingest_role"],
        "raw_file_relative_path": entry["relative_path"],
        "raw_file_sha256": entry["sha256"],
    }
    result = validate_d01_row_linkage(row, oracle)
    assert result.pair_id_integrity is True
    assert result.raw_locator_present is True
    assert result.canonical_ingest_linked is True
    assert result.raw_sha_linked is True


def test_bounded_parquet_iterator_and_validated_atomic_promotion(tmp_path: Path) -> None:
    schema = pa.schema([pa.field("row_id", pa.int64(), nullable=False), pa.field("value", pa.string(), nullable=False)])
    source = tmp_path / "PAIR_REGISTRY_v001.synthetic.parquet"
    destination = tmp_path / "PAIR_REGISTRY_v002.synthetic.parquet"
    table = pa.table({"row_id": list(range(5)), "value": ["a", "b", "c", "d", "e"]}, schema=schema)
    pq.write_table(table, source)
    batches = list(iter_parquet_batches(source, batch_size=2))
    assert [batch.num_rows for batch in batches] == [2, 2, 1]

    def validate(path: Path) -> None:
        assert pq.ParquetFile(path).metadata.num_rows == 5

    result = write_parquet_batches_atomic(destination, schema, iter(batches), validate=validate)
    assert result.path == destination
    assert result.row_count == 5
    assert result.batch_count == 3
    assert destination.is_file()
    assert not destination.with_suffix(destination.suffix + ".partial").exists()


def test_failed_validation_never_promotes_partial_artifact(tmp_path: Path) -> None:
    schema = pa.schema([pa.field("row_id", pa.int64(), nullable=False)])
    destination = tmp_path / "PAIR_REGISTRY_v002.synthetic.parquet"
    batch = pa.record_batch([pa.array([1, 2])], schema=schema)

    def reject(_: Path) -> None:
        raise ValueError("synthetic validation failure")

    with pytest.raises(ValueError, match="synthetic validation failure"):
        write_parquet_batches_atomic(destination, schema, [batch], validate=reject)
    assert not destination.exists()
    assert destination.with_suffix(destination.suffix + ".partial").is_file()


def test_phase2_duckdb_uses_spill_safe_synthetic_connection(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "duckdb-spill"
    connection = open_phase2_duckdb(runtime_dir, environ={})
    try:
        assert connection.execute("SELECT 1").fetchone() == (1,)
        memory_limit = connection.execute("SELECT current_setting('memory_limit')").fetchone()
        assert memory_limit is not None and str(memory_limit[0]).startswith("7.4 GiB")
        temp_directory = connection.execute("SELECT current_setting('temp_directory')").fetchone()
        assert temp_directory is not None and Path(str(temp_directory[0])).resolve() == runtime_dir.resolve()
    finally:
        connection.close()
    assert runtime_dir.is_dir()


def test_p2_output_schema_is_the_single_report_field_contract() -> None:
    assert len(P2_OUTPUT_SCHEMA) == 70
    assert len(P2_OUTPUT_SCHEMA.names) == len(set(P2_OUTPUT_SCHEMA.names))
    exact_duplicate = P2_OUTPUT_SCHEMA.field("exact_duplicate_flag")
    assert exact_duplicate.type == pa.bool_()
    assert exact_duplicate.nullable is True
    assert "exact_duplicate_flag" in P2_AGGREGATE_COUNT_FIELDS
    assert P2_OUTPUT_SCHEMA.field("secondary_rejection_flags").type == pa.string()


def test_synthetic_population_to_completion_manifest_e2e(tmp_path: Path) -> None:
    prepared = _prepare_synthetic_phase2_project(tmp_path)
    result = phase2._execute_phase2_population(
        project_root=prepared["project_root"],
        input_path=prepared["input_path"],
        output_path=prepared["output_path"],
        d01_manifest_path=prepared["d01_manifest_path"],
        contract_path=prepared["contract_path"],
        runtime_dir=prepared["runtime_dir"],
        run_id=prepared["run_id"],
        expected_row_count=prepared["row_count"],
        execution_code_commit_override="synthetic-code-commit",
    )
    output_path = prepared["output_path"]
    assert result.validation_status == "PASS"
    assert result.row_count == 4
    assert result.output_column_count == len(P2_OUTPUT_SCHEMA)
    assert output_path.is_file()
    assert not output_path.with_suffix(output_path.suffix + ".candidate").exists()
    assert validate_phase2_output_schema(output_path).equals(P2_OUTPUT_SCHEMA)
    duplicate_rows = {
        row["pair_id"]: row
        for row in pq.read_table(
            output_path,
            columns=[
                "pair_id",
                "analysis_representative_pair_id",
                "exact_duplicate_flag",
                "secondary_rejection_flags",
            ],
        ).to_pylist()
    }
    assert duplicate_rows["pair_tier_a_survivor"]["analysis_representative_pair_id"] == "pair_tier_a_survivor"
    assert duplicate_rows["pair_tier_a_survivor"]["exact_duplicate_flag"] is False
    assert duplicate_rows["pair_legacy_duplicate"]["analysis_representative_pair_id"] == "pair_tier_a_survivor"
    assert duplicate_rows["pair_legacy_duplicate"]["exact_duplicate_flag"] is True
    assert isinstance(duplicate_rows["pair_legacy_duplicate"]["secondary_rejection_flags"], str)

    report_paths = [
        prepared["project_root"] / "outputs/reports/QC_FLOW_v001.csv",
        prepared["project_root"] / "outputs/reports/LID_QC_PASS_RATE_v001.csv",
        prepared["project_root"] / "outputs/reports/MANUAL_QC_SAMPLING_FRAME_SUMMARY_v001.csv",
        prepared["project_root"] / "outputs/reports/P2_EXECUTION_REPORT_v001.json",
    ]
    assert all(path.is_file() for path in report_paths)
    manifest_path = prepared["project_root"] / "outputs/manifests/QC_MANIFEST_v001.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["completion_status"] == P2_COMPLETION_STATUS
    assert manifest["output"]["column_count"] == 70
    assert manifest["output"]["sha256"] == result.output_sha256
    assert len(manifest["reports"]) == 4
    evidence = require_phase2_canonical_evidence(prepared["project_root"])
    assert evidence.output_path == output_path.resolve()
    assert evidence.output_sha256 == result.output_sha256
    assert evidence.row_count == 4


def test_report_failure_never_promotes_candidate_or_completion_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_synthetic_phase2_project(tmp_path)

    def reject_reports(
        report_paths: dict[str, Path],
        *,
        expected_row_count: int,
        run_id: str,
        output_sha256: str,
    ) -> None:
        del report_paths, expected_row_count, run_id, output_sha256
        raise ValueError("synthetic report validation failure")

    monkeypatch.setattr(phase2, "_validate_candidate_reports", reject_reports)
    with pytest.raises(ValueError, match="synthetic report validation failure"):
        phase2._execute_phase2_population(
            project_root=prepared["project_root"],
            input_path=prepared["input_path"],
            output_path=prepared["output_path"],
            d01_manifest_path=prepared["d01_manifest_path"],
            contract_path=prepared["contract_path"],
            runtime_dir=prepared["runtime_dir"],
            run_id=prepared["run_id"],
            expected_row_count=prepared["row_count"],
            execution_code_commit_override="synthetic-code-commit",
        )
    output_path = prepared["output_path"]
    assert not output_path.exists()
    assert output_path.with_suffix(output_path.suffix + ".candidate").is_file()
    assert not (prepared["project_root"] / "outputs/manifests/QC_MANIFEST_v001.json").exists()
    assert not (prepared["project_root"] / "outputs/reports/QC_FLOW_v001.csv").exists()
    with pytest.raises(FileNotFoundError, match="completion manifest is required"):
        require_phase2_canonical_evidence(prepared["project_root"])


def test_canonical_notebook_consumes_v11_and_authorizes_only_population_qc() -> None:
    notebook_path = PROJECT_ROOT / "notebooks/02_normalize_and_qc.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    markdown = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown"]
    code = "\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    expected_sections = [
        "0 Contract / Scope",
        "1 Input lineage",
        "2 D-01 handoff verification",
        "3 Normalization",
        "4 Decode / Unicode integrity",
        "5 Structural QC",
        "6 Exact duplicate analysis disposition",
        "7 Language-side sanity review",
        "8 Population pair_quality_status",
        "9 QC aggregate flow",
        "10 v002 artifact validation",
        "11 Manifest / hashes / G1 evidence summary",
    ]
    for section in expected_sections:
        assert any(section in cell for cell in markdown)
    assert P2_CONTRACT_COMMIT in code
    assert "execute_phase2_population" in code
    assert "require_phase2_canonical_evidence" in code
    assert "FULL_RUN_AUTHORIZED = True" in code
    assert "MANUAL_AUDIT_SAMPLE_DRAW_AUTHORIZED = False" in code
    assert "analysis_representative_pair_id" in code
    assert "PAIR_REGISTRY_v002.parquet" not in code
    assert "lingua" not in code.lower().replace("'lingua'", "")
    assert "fasttext" not in code.lower().replace("'fasttext'", "")
    assert "lid_failure_flag" not in code
    assert BLOCKED_BY_P2_CONTRACT not in code
    assert all(cell.get("execution_count") is None for cell in notebook["cells"] if cell["cell_type"] == "code")
