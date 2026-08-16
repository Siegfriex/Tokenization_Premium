"""Phase-2 minimal-QC engineering primitives fixed by the v1.1 contract."""

from __future__ import annotations

import json
import os
import unicodedata
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from tokenization_premium.registry import provenance_pair_id, resolve_duckdb_memory_limit

P2_CONTRACT_COMMIT = "b9990afbf3fc0ed2a5e80fb4def1565e9ba3ebf4"
P2_CONTRACT_GIT_OBJECT = f"{P2_CONTRACT_COMMIT}:docs/contracts/P2_NORMALIZE_QC_PRECONTRACT_v1.md"
BLOCKED_BY_P2_CONTRACT = "BLOCKED_BY_P2_CONTRACT"
PAIR_REGISTRY_V001_RELATIVE_PATH = Path("data/registry/PAIR_REGISTRY_v001.parquet")
PAIR_REGISTRY_V002_RELATIVE_PATH = Path("data/registry/PAIR_REGISTRY_v002.parquet")
EXPECTED_D01_ROW_COUNT = 5_652_925
NORMALIZATION_RULE_VERSION = "p2_norm_v001"
NORMALIZATION_OPERATIONS = ("NFC", "BOM_STRIP", "OUTER_TRIM")
LANGUAGE_MIN_EVIDENCE = 5
LANGUAGE_SUBSTANTIAL_EVIDENCE = 5
EXACT_DUPLICATE_IDENTITY_SCOPE = "EXACT_RAW_KO_EN_ONLY_NOT_NEAR_DUPLICATE_OR_PARAPHRASE"

type QCFlags = Mapping[str, pa.Array | pa.ChunkedArray]
type ArtifactValidator = Callable[[Path], None]
type LanguageSide = Literal["KO", "EN"]
type LanguageSideReason = Literal[
    "KO_NO_HANGUL_LATIN_DOMINANT",
    "EN_NO_LATIN_HANGUL_DOMINANT",
    "INSUFFICIENT_LINGUISTIC_EVIDENCE",
    "NONE",
]


@dataclass(frozen=True)
class NormalizationResult:
    """SSOT raw→NFC→analysis result plus raw-based anomaly visibility."""

    nfc_text: str
    analysis_text: str
    operations: tuple[str, ...]
    unicode_anomaly_flag: bool
    unicode_anomaly_reasons: tuple[str, ...]


@dataclass(frozen=True)
class LanguageSideReview:
    """Model-free advisory result; this type cannot encode a rejection."""

    lang_side_anomaly_review_flag: bool
    lang_side_anomaly_reason: LanguageSideReason
    hangul_count: int
    latin_count: int
    alphabetic_evidence: int


@dataclass(frozen=True)
class D01HandoffSummary:
    """Safe manifest/oracle assertions without a population rescan."""

    status: Literal["PASS"]
    row_count: int
    pair_id_distinct: int
    canonical_input_count: int


@dataclass(frozen=True)
class D01RowLinkage:
    """Synthetic/batch-level D-01 lineage assertions without retaining text."""

    pair_id_integrity: bool
    raw_locator_present: bool
    canonical_ingest_linked: bool
    raw_sha_linked: bool


@dataclass(frozen=True)
class AtomicParquetWriteResult:
    """Validated partial artifact promoted to its final path."""

    path: Path
    row_count: int
    batch_count: int


class QCFlagComputer(Protocol):
    """Batch-to-flags extension point for the future authorized full run."""

    def compute(self, batch: pa.RecordBatch) -> QCFlags: ...


class StatusDeriver(Protocol):
    """Flags-to-status extension point for the future authorized full run."""

    def derive(self, flags: QCFlags) -> pa.Array: ...


class AuditSummaryBuilder(Protocol):
    """Raw-text-free numeric audit summary extension point."""

    def summarize(self, *, processed: int, metrics: Mapping[str, int | float]) -> Mapping[str, int | float]: ...


def manual_audit_import_schema() -> pa.Schema:
    """Return the nullable manual-only interface without fabricating labels."""
    return pa.schema(
        [
            pa.field("pair_id", pa.string(), nullable=False),
            pa.field("manual_semantic_score", pa.int8(), nullable=True),
            pa.field("manual_language_side_status", pa.string(), nullable=True),
            pa.field("manual_audit_status", pa.string(), nullable=True),
        ]
    )


def named_entity_deferred_fields() -> Mapping[str, bool | str | None]:
    """Expose the contract-required nullable NER fields without a heuristic or model."""
    return {"named_entity_heavy_flag": None, "named_entity_evaluation_status": "DEFERRED"}


def _unicode_anomaly_reasons(raw_text: str) -> tuple[str, ...]:
    reasons: list[str] = []
    edge_bom_stripped = raw_text.strip("\ufeff")
    if any(character in edge_bom_stripped for character in ("\u200b", "\u200c", "\u200d", "\ufeff")):
        reasons.append("INTERNAL_ZERO_WIDTH")
    if any(unicodedata.category(character) == "Cc" and character not in "\t\n" for character in raw_text):
        reasons.append("CONTROL_CHARACTER")
    previous_is_base = False
    for character in raw_text:
        if unicodedata.combining(character):
            if not previous_is_base:
                reasons.append("ORPHAN_COMBINING_MARK")
                break
        else:
            previous_is_base = not character.isspace()
    return tuple(reasons)


def normalize_ssot_text(text: str) -> NormalizationResult:
    """Apply NFC, edge-only U+FEFF stripping, then outer whitespace trim."""
    if not isinstance(text, str):
        raise TypeError("normalization input must be str")
    nfc_text = unicodedata.normalize("NFC", text)
    without_edge_bom = nfc_text.strip("\ufeff")
    analysis_text = without_edge_bom.strip()
    anomaly_reasons = _unicode_anomaly_reasons(text)
    return NormalizationResult(
        nfc_text=nfc_text,
        analysis_text=analysis_text,
        operations=NORMALIZATION_OPERATIONS,
        unicode_anomaly_flag=bool(anomaly_reasons),
        unicode_anomaly_reasons=anomaly_reasons,
    )


def empty_text_flag(ko_text_raw: object, en_text_raw: object) -> bool:
    """Flag null/non-string input or either side empty after frozen normalization."""
    if not isinstance(ko_text_raw, str) or not isinstance(en_text_raw, str):
        return True
    return not normalize_ssot_text(ko_text_raw).analysis_text or not normalize_ssot_text(en_text_raw).analysis_text


def _script_counts(text: str) -> tuple[int, int]:
    hangul = sum("\uac00" <= character <= "\ud7a3" for character in text)
    latin = sum(("A" <= character <= "Z") or ("a" <= character <= "z") for character in text)
    return hangul, latin


def language_side_anomaly_review(text: str, *, expected_side: LanguageSide) -> LanguageSideReview:
    """Run the conservative Unicode-script wiring smoke check from P2 v1.1."""
    if not isinstance(text, str):
        raise TypeError("language-side input must be str")
    if expected_side not in {"KO", "EN"}:
        raise ValueError("expected_side must be 'KO' or 'EN'")
    hangul, latin = _script_counts(text)
    evidence = hangul + latin
    if evidence < LANGUAGE_MIN_EVIDENCE:
        reason: LanguageSideReason = "INSUFFICIENT_LINGUISTIC_EVIDENCE"
    elif expected_side == "KO" and hangul == 0 and latin >= LANGUAGE_SUBSTANTIAL_EVIDENCE:
        reason = "KO_NO_HANGUL_LATIN_DOMINANT"
    elif expected_side == "EN" and latin == 0 and hangul >= LANGUAGE_SUBSTANTIAL_EVIDENCE:
        reason = "EN_NO_LATIN_HANGUL_DOMINANT"
    else:
        reason = "NONE"
    return LanguageSideReview(
        lang_side_anomaly_review_flag=reason != "NONE",
        lang_side_anomaly_reason=reason,
        hangul_count=hangul,
        latin_count=latin,
        alphabetic_evidence=evidence,
    )


def derive_pair_quality_status(structural_flags: Mapping[str, bool]) -> Literal["accepted", "rejected"]:
    """Gate only on the five contract-frozen structural flags, never advisory review flags."""
    hard_flags = (
        "empty_text_flag",
        "decode_integrity_flag",
        "markup_dominant_flag",
        "control_char_excess_flag",
        "exact_duplicate_flag",
    )
    return "rejected" if any(bool(structural_flags.get(name, False)) for name in hard_flags) else "accepted"


def decode_integrity_ok(text: str) -> bool:
    """Check Unicode readability only; tokenizer roundtrip belongs to G3."""
    if "\ufffd" in text:
        return False
    return not any(0xD800 <= ord(character) <= 0xDFFF for character in text)


def select_analysis_representative_pair_id(candidates: Sequence[Mapping[str, object]]) -> str:
    """Choose primary-analysis-eligible first, then stable min(pair_id)."""
    if not candidates:
        raise ValueError("duplicate group candidates must not be empty")
    pair_ids = [candidate.get("pair_id") for candidate in candidates]
    if any(not isinstance(pair_id, str) or not pair_id for pair_id in pair_ids):
        raise ValueError("every candidate must have a non-empty string pair_id")
    if len(set(pair_ids)) != len(pair_ids):
        raise ValueError("candidate pair_id values must be unique")
    eligible = [
        str(candidate["pair_id"])
        for candidate in candidates
        if candidate.get("primary_analysis_eligible") is True
    ]
    return min(eligible) if eligible else min(str(pair_id) for pair_id in pair_ids)


def validate_d01_manifest_handoff(
    manifest: Mapping[str, object], ingest_contract: Mapping[str, object]
) -> D01HandoffSummary:
    """Assert the already-recorded D-01 manifest and canonical ingest oracle agree."""
    validation = manifest.get("validation")
    pair_registry = manifest.get("pair_registry")
    expected_counts = ingest_contract.get("expected_logical_record_counts")
    prevention = ingest_contract.get("double_ingest_prevention_contract")
    if not all(isinstance(item, Mapping) for item in (validation, pair_registry, expected_counts, prevention)):
        raise ValueError("D-01 manifest or ingest contract structure is invalid")
    assert isinstance(validation, Mapping)
    assert isinstance(pair_registry, Mapping)
    assert isinstance(expected_counts, Mapping)
    assert isinstance(prevention, Mapping)
    row_count = int(pair_registry["row_count"])
    expected_total = int(expected_counts["total"])
    pair_id_distinct = int(validation["pair_id_distinct"])
    if manifest.get("cross_agent_contract") != "PASS" or validation.get("status") != "PASS":
        raise ValueError("D-01 manifest is not PASS")
    if row_count != EXPECTED_D01_ROW_COUNT or expected_total != row_count:
        raise ValueError("D-01 row count does not match the canonical oracle")
    if pair_id_distinct != row_count:
        raise ValueError("D-01 pair_id integrity is not PASS")
    manifest_inputs = manifest.get("input_file_hashes")
    oracle_inputs = prevention.get("ingest_allowlist")
    if not isinstance(manifest_inputs, list) or not isinstance(oracle_inputs, list):
        raise ValueError("canonical input inventories are missing")
    manifest_links = {(item["relative_path"], item["sha256"]) for item in manifest_inputs}
    oracle_links = {(item["relative_path"], item["sha256"]) for item in oracle_inputs}
    if manifest_links != oracle_links:
        raise ValueError("D-01 raw SHA linkage differs from the canonical ingest oracle")
    return D01HandoffSummary("PASS", row_count, pair_id_distinct, len(oracle_links))


def validate_d01_row_linkage(row: Mapping[str, object], ingest_contract: Mapping[str, object]) -> D01RowLinkage:
    """Validate one row's pair identity, locator, allowlist role, and raw SHA linkage."""
    required_strings = (
        "pair_id",
        "source_id",
        "source_record_id",
        "raw_locator",
        "canonical_ingest_role",
        "raw_file_relative_path",
        "raw_file_sha256",
    )
    if any(not isinstance(row.get(name), str) or not row[name] for name in required_strings):
        raise ValueError("D-01 row is missing required provenance linkage")
    pair_id_valid = row["pair_id"] == provenance_pair_id(str(row["source_id"]), str(row["source_record_id"]))
    try:
        locator = json.loads(str(row["raw_locator"]))
    except json.JSONDecodeError as error:
        raise ValueError("raw_locator is not valid JSON") from error
    locator_present = isinstance(locator, Mapping) and bool(locator)
    prevention = ingest_contract.get("double_ingest_prevention_contract")
    if not isinstance(prevention, Mapping) or not isinstance(prevention.get("ingest_allowlist"), list):
        raise ValueError("canonical ingest allowlist is missing")
    matching = [
        item
        for item in prevention["ingest_allowlist"]
        if item["relative_path"] == row["raw_file_relative_path"]
    ]
    canonical_linked = len(matching) == 1 and matching[0]["canonical_ingest_role"] == row["canonical_ingest_role"]
    raw_sha_linked = len(matching) == 1 and matching[0]["sha256"] == row["raw_file_sha256"]
    result = D01RowLinkage(pair_id_valid, locator_present, canonical_linked, raw_sha_linked)
    if not all((result.pair_id_integrity, result.raw_locator_present, result.canonical_ingest_linked, result.raw_sha_linked)):
        raise ValueError("D-01 row linkage validation failed")
    return result


def iter_parquet_batches(path: Path, *, batch_size: int = 25_000) -> Iterator[pa.RecordBatch]:
    """Iterate over Parquet with bounded record batches."""
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
    """Write bounded batches to partial, validate, then atomically promote."""
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
    """Open Phase-2 DuckDB with the 8GB default and mandatory spill directory."""
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
    "EXACT_DUPLICATE_IDENTITY_SCOPE",
    "EXPECTED_D01_ROW_COUNT",
    "LANGUAGE_MIN_EVIDENCE",
    "LANGUAGE_SUBSTANTIAL_EVIDENCE",
    "NORMALIZATION_OPERATIONS",
    "NORMALIZATION_RULE_VERSION",
    "P2_CONTRACT_COMMIT",
    "P2_CONTRACT_GIT_OBJECT",
    "PAIR_REGISTRY_V001_RELATIVE_PATH",
    "PAIR_REGISTRY_V002_RELATIVE_PATH",
    "AtomicParquetWriteResult",
    "AuditSummaryBuilder",
    "D01HandoffSummary",
    "D01RowLinkage",
    "LanguageSideReview",
    "NormalizationResult",
    "QCFlagComputer",
    "QCFlags",
    "StatusDeriver",
    "decode_integrity_ok",
    "derive_pair_quality_status",
    "empty_text_flag",
    "iter_parquet_batches",
    "language_side_anomaly_review",
    "manual_audit_import_schema",
    "named_entity_deferred_fields",
    "normalize_ssot_text",
    "open_phase2_duckdb",
    "select_analysis_representative_pair_id",
    "validate_d01_manifest_handoff",
    "validate_d01_row_linkage",
    "write_parquet_batches_atomic",
]
