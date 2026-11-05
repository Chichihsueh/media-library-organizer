# Media Library Organizer — Agent Skill

A safety-first, open-source Agent Skill for **inventorying, identifying, grouping, and previewing organization** of video libraries. Inspired by general media-asset-management practices and the workflow concepts discussed in the [Peach project](https://github.com/peach-mitao/peach). **Independent project, not affiliated with or endorsed by Peach. No Peach source code is copied.**

## What it does

- Read-only local media inventory (paths, sizes, timestamps, filename-based work IDs, part and edition clues)
- Conservative grouping heuristics with unknowns kept unresolved
- Generates a JSON **dry-run** plan for per-work folders
- Reports collisions and skips; never silently overwrites
- Includes tests and agent instructions in `SKILL.md`

## What it does NOT do

- No automatic file moves, renames, deletes, hashing or network scraping
- No automatic metadata-provider integration or NFO/ffprobe parsing in this first version
- No guaranteed identity/deduplication detection
- No execution engine or rollback implementation (design guidance only)

## Usage

Python 3.9+ (standard library only):

```sh
python3 scripts/inventory.py "/path/to/Media" --output inventory.json
python3 scripts/plan.py inventory.json --destination "/path/to/Organized" --output plan.json
python3 -m unittest discover -s tests -v
```

Reports include full local paths; keep them private. The source and destination must be separate folder trees. No original media is modified.

To install as a skill, copy the entire repository folder into the skills directory supported by your AI agent and follow the agent's configuration instructions. `SKILL.md` is the main instruction file.

## Safety

Review every proposed change. Treat identifiers inferred from filenames as uncertain. Keep backups before implementing any independently approved execution workflow. See `references/design.md`.

## License

MIT, see `LICENSE`.
