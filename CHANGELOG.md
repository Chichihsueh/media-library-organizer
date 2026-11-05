# Changelog

## Next release (known issues, deferred)
- Recognise non-`ABC-123` catalogue formats (FC2-PPV-######, HEYZO-####, MMDDYY-NNN, 300MIUM-###); ~360 files in a real library stayed unidentified.
- Prefix sanity check: words such as `COLLEGE-33` pass the code heuristic; compare prefixes against known labels or require verification.
- Ship a journaled same-folder rename/flatten preview and executor (`CODE_resolution.ext`) with rollback instead of one-off scripts.
- Warn when two files collapse to the same target name (keep originals, list for review) as `plan.py` rename mode.
- `verify.py` is untested against the live endpoint; confirm field names on first real run and add duration comparison via ffprobe.
- Original titles/performer names are lost on rename; keep an old-to-new mapping report by default.

## 0.1.2
### Added
- `verify.py`: checkpoints the cache every 50 requests and saves on Ctrl-C so long runs can resume.
### Fixed
- `verify.py`: first live run showed the dvd_id endpoint can omit `dvd_id`; the ID is now derived from `content_id` (`118ama00027` -> AMA-027), with a new `unconfirmed` status. Runtime still needs the `combined=` endpoint (next release).
### Fixed
- `inventory.py`: `.rmvb`, `.rm`, `.flv`, `.mpg`, `.mpeg`, `.3gp`, `.vob`, `.divx`, `.asf` were silently skipped; found while organizing a real library (100 files missed).
### Added
- `scripts/verify.py`: opt-in, ID-only check against r18.dev public JSON (dry run by default, delay, limit, cache, fail-closed on 429). Live endpoint behaviour is untested in CI; tests use mocked responses.

## 0.1.1
### Fixed
- `inventory.py`: `ABC 1080p` was read as work ID `ABC-1080`; resolutions are no longer codes.
- `inventory.py`: camera/phone names (`IMG_0045`, `DSC_0012`, `PXL_*`) are no longer treated as codes.
- `inventory.py`: macOS `._*` sidecars and NAS folders (`#recycle`, `@eaDir`) are skipped.
- `inventory.py`: `480p`, `576p`, `360p`, `8k`, `x264/x265` are now recognised as edition clues.
- `plan.py`: files modified after the scan (size or mtime differs) are reported as conflicts.

### Added
- `plan.py` schema v2: `warnings` (cross-volume destination), `review_groups`, per-file `evidence`.
- Tests for the above (12 total) and a GitHub Actions workflow.

### Changed
- `SKILL.md` description rewritten with explicit "use when" triggers.

## 0.1.0
- Initial read-only inventory and preview planner.
