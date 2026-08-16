"""Phase-2 semantic-neutral scaffold의 normalization·streaming·notebook contract를 검사한다."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tokenization_premium.paths import PROJECT_ROOT
from tokenization_premium.phase2 import (
    BLOCKED_BY_P2_CONTRACT,
    iter_parquet_batches,
    normalize_ssot_text,
    open_phase2_duckdb,
    write_parquet_batches_atomic,
)


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


def test_normalization_reports_only_operations_that_changed_text() -> None:
    assert normalize_ssot_text("plain").operations == ()
    assert normalize_ssot_text("e\u0301").operations == ("NFC",)
    assert normalize_ssot_text(" \ufeffvalue ").operations == ("REMOVE_BOM", "OUTER_TRIM")


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
        temp_directory = connection.execute("SELECT current_setting('temp_directory')").fetchone()
        assert temp_directory is not None and Path(str(temp_directory[0])).resolve() == runtime_dir.resolve()
    finally:
        connection.close()
    assert runtime_dir.is_dir()


def test_notebook_scaffold_has_all_sections_and_explicit_semantic_blocks() -> None:
    notebook_path = PROJECT_ROOT / "notebooks/02_normalize_and_qc.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    markdown = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown"]
    code = "\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    expected_sections = [
        "0 Contract / Scope",
        "1 Environment + Inputs",
        "2 D-01 Integrity Handoff",
        "3 Normalization",
        "4 QC Flag Computation",
        "5 Duplicate Disposition",
        "6 LID",
        "7 Semantic QC",
        "8 QC Flow",
        "9 Registry v002",
        "10 Artifact / Hash",
        "11 G1 Closure Evidence",
    ]
    for section in expected_sections:
        assert any(section in cell for cell in markdown)
    assert code.count(BLOCKED_BY_P2_CONTRACT) >= 8
    assert "ProgressHeartbeat" in code and "progress_tqdm" in code
    assert "SYNTHETIC_ONLY = True" in code
    assert "PROSPECTIVE_LONG_STAGES" in code
    assert "BLOCKED_SEMANTICS" in code
