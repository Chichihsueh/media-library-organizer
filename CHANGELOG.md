# Changelog

## 0.1.2
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
