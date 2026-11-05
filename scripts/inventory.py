#!/usr/bin/env python3
"""Read-only inventory of a media directory. No networking or file mutation."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re

EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.m4v', '.wmv', '.webm', '.ts',
              '.rmvb', '.rm', '.flv', '.mpg', '.mpeg', '.3gp', '.vob', '.divx', '.asf'}
# Directories created by NAS/OS tooling; never contain user media worth indexing.
SKIP_DIRS = {'#recycle', '@eadir', '.trashes', '.spotlight-v100', '.fseventsd', '$recycle.bin'}
# Letter prefixes produced by cameras, phones and tools, not catalogue codes.
NON_CODE_PREFIXES = {'IMG', 'DSC', 'DSCN', 'DSCF', 'PXL', 'VID', 'MOV', 'MVI', 'MAH', 'GOPR', 'GP',
                     'WA', 'SCREEN', 'REC', 'CLIP', 'PART', 'DISC', 'CD', 'PT', 'EP', 'SEASON', 'TRACK'}
RESOLUTIONS = {360, 480, 540, 576, 720, 1080, 1440, 2160, 4320}
CODE = re.compile(r'(?<![a-z0-9])([a-z]{2,8})[-_ ]?(\d{2,7})(?!\d)([pik])?', re.I)
PART = re.compile(r'(?:^|[\s._-])(?:cd|part|pt|disc)[\s._-]?(\d{1,2})(?:$|[\s._-])', re.I)
EDITION = re.compile(r'(?<![a-z0-9])(4320p|2160p|1440p|1080[pi]|720p|576p|540p|480p|360p|8k|4k|hevc|h\.?265|h\.?264|x265|x264)(?![a-z0-9])', re.I)


def find_code(stem):
    """First plausible catalogue code; skips resolutions, camera names and lone-prefix noise."""
    for m in CODE.finditer(stem):
        prefix, digits, suffix = m.group(1).upper(), m.group(2), m.group(3)
        if prefix in NON_CODE_PREFIXES:
            continue
        if suffix and int(digits) in RESOLUTIONS:  # e.g. "ABC 1080p"
            continue
        if int(digits) in RESOLUTIONS and not re.search(r'[-_]', stem[m.start():m.end()]):
            continue  # "ABC 720" without a separator is far more likely a resolution
        if len(digits) >= 5 and digits.startswith('0'):
            digits = digits.lstrip('0').zfill(3)  # DMM-style padding: club00502 -> CLUB-502
        return prefix, digits
    return None


def infer(name):
    stem = Path(name).stem
    m = find_code(stem)
    p = PART.search(' ' + stem + ' ')
    editions = sorted({x.upper() for x in EDITION.findall(stem)})
    return {'work_id': f'{m[0]}-{m[1]}' if m else None,
            'id_confidence': 'heuristic' if m else 'unknown',
            'part': int(p.group(1)) if p else None, 'edition_clues': editions}


def inventory(root):
    root = Path(root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Source must be a directory')
    items, errors = [], []
    def onerror(err): errors.append(str(err))
    for current, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        dirs[:] = sorted(d for d in dirs
                         if d.casefold() not in SKIP_DIRS and not (Path(current)/d).is_symlink())
        for name in sorted(files):
            p = Path(current) / name
            if name.startswith('._') or p.suffix.lower() not in EXTENSIONS or p.is_symlink():
                continue  # '._*' are macOS AppleDouble sidecars, not videos
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
