# Design and safety model

## Separation of concerns

1. File identity: filesystem path plus size and mtime at scan time. Not stable across moves; not a cryptographic identity.
2. Work identity: a *tentative* work code parsed from filename. Can be wrong or ambiguous.
3. Versions and parts: independent media files may belong to the same work. Do not collapse or delete.
4. User-authored metadata: should override automated enrichment only after explicit field-level review.
5. Physical organization: last stage, never a consequence of merely scanning or enriching.

## Risk model

An automation should be evaluated by expected value: benefit - P(error) × cost(error) - operating cost. As data loss is expensive, apply a high threshold for irreversible operations and prefer reversible previews.

## Parsing limits

Current heuristic recognizes Latin-letter identifiers followed by 2–7 digits, e.g. `ABC-123`. It can generate false positives from camera filenames and filenames that happen to match patterns. `CD2`, `PART2`, `1080p`, and `4K` are clues, not definitive metadata. Unicode paths are supported but non-Western ID formats are not exhaustively handled.

## Privacy

No files or pathnames are transmitted. Generated JSON reports list paths and may themselves be sensitive. Do not commit actual user inventories to public GitHub repositories.

## Future work

- Optional local-only NFO import with provenance and conflict management
- Optional `ffprobe` subprocess with explicit opt-in and timeouts
- Optional byte hashing limited by budget, never used as automatic deletion authorization
- Transactional executor with manifest SHA, per-operation state, collision revalidation, recovery journal and rollback tests
- Extensible provider adapters and identifier parsers without bundling third-party credentials

## External attribution

Peach: https://github.com/peach-mitao/peach . This repository reuses only high-level ideas, not project implementation or protected assets.
