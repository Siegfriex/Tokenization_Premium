# INC-004 Invalid v002 Quarantine Proposal

Status: EXECUTED / VERIFIED at `2026-08-16T22:06:29+09:00`

## Incident lineage

- Run ID: `P2_CANONICAL_20260816T211028`
- Execution branch: `impl/p2-canonical-run-codex`
- Execution SHA: `a4704fa40ee3a8cc85024e3f053f615d6e0174e8`
- Terminal stage: `SAFE_AGGREGATE_REPORTS`
- Terminal status: `FAILED`
- Failure: DuckDB BinderException because `exact_duplicate_flag` was not materialized

## Verified invalid artifact

- Canonical pathname before quarantine: `data/registry/PAIR_REGISTRY_v002.parquet`
- Rows: `5,652,925`
- Row groups: `57`
- Columns: `69`
- Bytes: `2,954,200,837`
- SHA-256: `4a36c8b94b6e05e35d16a980443620063a8b853b4d40539905f0db30ee50c312`
- Schema SHA-256: `41146122886f87defdb4cf7091e20be467bf678ee7c2667746e432bb06e4c1e4`
- Contract drift: missing `exact_duplicate_flag`; `secondary_rejection_flags` is Arrow JSON extension instead of contract string

The file is execution evidence, not a canonical P2 completion artifact. No successful `QC_MANIFEST_v001.json` exists for this run.

## Quarantine operation

Use a same-filesystem rename, never a copy-overwrite or deletion:

```text
from: data/registry/PAIR_REGISTRY_v002.parquet
to:   .runtime/quarantine/INC-004/P2_CANONICAL_20260816T211028/
      PAIR_REGISTRY_v002.INVALID.4a36c8b94b6e.parquet
```

Preconditions:

1. source is a regular file;
2. source SHA-256, bytes, rows, columns, and schema SHA-256 match the incident manifest;
3. destination does not exist;
4. no P2/DuckDB/Jupyter heavy worker is using the source;
5. execution worktree tracked state remains unchanged.

Postconditions:

1. canonical pathname is absent;
2. quarantine pathname is a regular file;
3. quarantined bytes and SHA-256 match the source evidence;
4. incident heartbeat remains under `.runtime/progress/P2_CANONICAL_20260816T211028/`;
5. no report or completion manifest is synthesized for the failed run.

This move changes publication status only. It does not change corpus bytes, QC rules, survivor semantics, or research estimands.

## Execution result

- Canonical pathname absent: PASS
- Quarantine pathname present: PASS
- SHA-256 unchanged: PASS
- Bytes unchanged: PASS
- Rows/row groups/columns unchanged: PASS
- Incident heartbeat retained: PASS
- Execution worktree tracked state clean: PASS
- Destructive deletion or overwrite: NOT PERFORMED
