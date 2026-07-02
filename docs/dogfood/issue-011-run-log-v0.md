# Run Log V0 Dogfood

Date: 2026-07-02

## Results

- Added append-only `state/runs/<issue-id>/run-log.md`.
- Added `go-ship-it append-log`.
- Added `go-ship-it show-run --logs`.
- Added run-log entries to trace and export.
- Kept source pointers as opaque strings.

## Example

```sh
go-ship-it append-log issue-001 --note "Agent recovered with --root." --author codex --source transcript:/path/to/session.jsonl
```

## Why It Is Small

V0 intentionally avoids lesson categories, promotion workflow, transcript ingestion, dashboards, and review scoring.

## Raw Data Chasers

Run log sources are breadcrumbs for later investigation. They can point to agent transcripts, command records, files, URLs, or tool-specific session ids.

## Lessons To Promote

- Keep comments easy before making lessons structured.
- Preserve raw source pointers before building transcript integrations.
- Use real run-log entries to design future review gates.
