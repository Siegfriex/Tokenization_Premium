"""Phase-2 contract 전에도 고정 가능한 normalization·streaming engineering primitive다."""

from __future__ import annotations

import os
import unicodedata
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from tokenization_premium.registry import resolve_duckdb_memory_limit

BLOCKED_BY_P2_CONTRACT = "BLOCKED_BY_P2_CONTRACT"
PAIR_REGISTRY_V001_RELATIVE_PATH = Path("data/registry/PAIR_REGISTRY_v001.parquet")
PAIR_REGISTRY_V002_RELATIVE_PATH = Path("data/registry/PAIR_REGISTRY_v002.parquet")

type QCFlags = Mapping[str, pa.Array | pa.ChunkedArray]
type ArtifactValidator = Callable[[Path], None]


@dataclass(frozen=True)
class NormalizationResult:
    """SSOT §11의 NFC와 analysis text를 원문 변경 없이 함께 전달한다."""

    nfc_text: str
    analysis_text: str
    operations: tuple[str, ...]


@dataclass(frozen=True)
class AtomicParquetWriteResult:
    """Validated partial artifact가 final path로 승격된 engineering 결과다."""

    path: Path
    row_count: int
    batch_count: int


class QCFlagComputer(Protocol):
    """Claude 계약 이후 구체화할 batch-to-flags extension point다."""

    def compute(self, batch: pa.RecordBatch) -> QCFlags: ...


class StatusDeriver(Protocol):
    """Claude 계약 이후 구체화할 flags-to-status extension point다."""

    def derive(self, flags: QCFlags) -> pa.Array: ...


class AuditSummaryBuilder(Protocol):
    """Raw text 없이 안전한 numeric audit summary만 만드는 extension point다."""

    def summarize(self, *, processed: int, metrics: Mapping[str, int | float]) -> Mapping[str, int | float]: ...


def normalize_ssot_text(text: str) -> NormalizationResult:
    """NFC 후 BOM을 제거하고 외곽 whitespace만 trim하며 내부 whitespace를 보존한다."""
    if not isinstance(text, str):
        raise TypeError("normalization input must be str")
    operations: list[str] = []
    nfc_text = unicodedata.normalize("NFC", text)
    if nfc_text != text:
        operations.append("NFC")
    without_bom = nfc_text.replace("\ufeff", "")
    if without_bom != nfc_text:
        operations.append("REMOVE_BOM")
    analysis_text = without_bom.strip()
    if analysis_text != without_bom:
        operations.append("OUTER_TRIM")
    return NormalizationResult(nfc_text=nfc_text, analysis_text=analysis_text, operations=tuple(operations))


def iter_parquet_batches(path: Path, *, batch_size: int = 25_000) -> Iterator[pa.RecordBatch]:
    """Parquet input을 전체 메모리에 적재하지 않고 bounded record batch로 순회한다."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    parquet_file = pq.ParquetFile(path)
    yield from parquet_file.iter_batches(batch_size=batch_size)


def write_parquet_batches_atomic(
    destination: Path,
    schema: pa.Schema,
    batches: Iterable[pa.RecordBatch],
    *,
    validate: ArtifactValidator,
) -> AtomicParquetWriteResult:
    """Bounded batches를 partial에 쓰고 validation 성공 후에만 final path로 atomic 승격한다."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    if partial.exists():
        partial.unlink()
    row_count = 0
    batch_count = 0
    writer = pq.ParquetWriter(partial, schema=schema, compression="zstd")
    try:
        for batch in batches:
            if batch.schema != schema:
                raise ValueError("record batch schema does not match declared output schema")
            writer.write_batch(batch)
            row_count += batch.num_rows
            batch_count += 1
    finally:
        writer.close()
    validate(partial)
    os.replace(partial, destination)
    return AtomicParquetWriteResult(path=destination, row_count=row_count, batch_count=batch_count)


def open_phase2_duckdb(runtime_dir: Path, environ: Mapping[str, str] | None = None) -> duckdb.DuckDBPyConnection:
    """기본 8GB memory cap과 mandatory spill directory를 적용한 Phase-2 DuckDB connection을 연다."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_literal = str(runtime_dir.resolve()).replace("'", "''")
    memory_limit = resolve_duckdb_memory_limit(environ)
    connection = duckdb.connect()
    try:
        connection.execute("SET preserve_insertion_order = false")
        connection.execute(f"SET memory_limit = '{memory_limit}'")
        connection.execute(f"SET temp_directory = '{runtime_literal}'")
    except Exception:
        connection.close()
        raise
    return connection


__all__ = [
    "BLOCKED_BY_P2_CONTRACT",
    "PAIR_REGISTRY_V001_RELATIVE_PATH",
    "PAIR_REGISTRY_V002_RELATIVE_PATH",
    "AtomicParquetWriteResult",
    "AuditSummaryBuilder",
    "NormalizationResult",
    "QCFlagComputer",
    "QCFlags",
    "StatusDeriver",
    "iter_parquet_batches",
    "normalize_ssot_text",
    "open_phase2_duckdb",
    "write_parquet_batches_atomic",
]
