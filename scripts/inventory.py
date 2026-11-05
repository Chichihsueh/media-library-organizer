#!/usr/bin/env python3
"""Read-only inventory of a media directory. No networking or file mutation."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re

EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.m4v', '.wmv', '.webm', '.ts'}
CODE = re.compile(r'(?<![a-z0-9])([a-z]{2,8})[-_ ]?(\d{2,7})(?!\d)', re.I)
PART = re.compile(r'(?:^|[\s._-])(?:cd|part|pt|disc)[\s._-]?(\d{1,2})(?:$|[\s._-])', re.I)
EDITION = re.compile(r'(?<!\w)(2160p|4k|1080p|720p|hevc|h265|h264)(?!\w)', re.I)


def infer(name):
    stem = Path(name).stem
    m = CODE.search(stem)
    p = PART.search(' ' + stem + ' ')
    editions = sorted({x.upper() for x in EDITION.findall(stem)})
    return {'work_id': f'{m.group(1).upper()}-{m.group(2)}' if m else None,
            'id_confidence': 'heuristic' if m else 'unknown',
            'part': int(p.group(1)) if p else None, 'edition_clues': editions}


def inventory(root):
    root = Path(root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Source must be a directory')
    items, errors = [], []
    def onerror(err): errors.append(str(err))
    for current, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        dirs[:] = sorted(d for d in dirs if not (Path(current)/d).is_symlink())
        for name in sorted(files):
            p = Path(current) / name
            if p.suffix.lower() not in EXTENSIONS or p.is_symlink():
                continue
            try:
                st = p.lstat()
                items.append({'relative_path': p.relative_to(root).as_posix(), 'size_bytes': st.st_size,
                              'mtime_ns': st.st_mtime_ns, **infer(name)})
            except OSError as exc:
                errors.append(f'{p}: {exc}')
    return {'schema_version': 1, 'source_root': str(root),
            'scanned_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'files': items, 'errors': errors}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source'); ap.add_argument('--output', required=True)
    args = ap.parse_args()
    out = Path(args.output).expanduser().absolute()
    src = Path(args.source).expanduser().resolve(strict=True)
    if out == src or src in out.parents:
        ap.error('Output must be outside source tree to keep inventory read-only')
    if out.exists():
        ap.error('Output exists; refusing to overwrite')
    report = inventory(src)
    with out.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f'Inventoried {len(report["files"])} files; {len(report["errors"])} errors -> {out}')

if __name__ == '__main__': main()
