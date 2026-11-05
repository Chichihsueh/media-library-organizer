#!/usr/bin/env python3
"""Generate a non-executable preview for media organization. Never moves files."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import re

SAFE_ID = re.compile(r'^[A-Z]{2,8}-\d{2,7}$')
SCHEMA_VERSION = 2


def is_within(path, root):
    return path == root or root in path.parents


def nearest_existing(path):
    for p in (path, *path.parents):
        if p.exists():
            return p
    return None


def same_volume(a, b):
    try:
        return a.stat().st_dev == b.stat().st_dev
    except OSError:
        return None


def plan(inventory, destination):
    source = Path(inventory['source_root']).resolve(strict=True)
    dest = Path(destination).expanduser().resolve(strict=False)
    if is_within(dest, source) or is_within(source, dest):
        raise ValueError('Destination and source must be separate trees')
    warnings = []
    anchor = nearest_existing(dest)
    if anchor is None:
        warnings.append('destination volume could not be determined')
    elif same_volume(source, anchor) is False:
        warnings.append('destination is on a different volume: a move becomes copy+delete; '
                        'verify free space and use a journaled executor')
    rows, reserved = [], set()
    for item in inventory['files']:
        rel = Path(item['relative_path'])
        src = (source / rel).resolve(strict=False)
        rec = {'source': str(src), 'work_id': item.get('work_id')}
        if rel.is_absolute() or '..' in rel.parts or not is_within(src, source):
            rec.update(status='conflict', reason='invalid source path'); rows.append(rec); continue
        work_id = item.get('work_id')
        if not work_id or not SAFE_ID.fullmatch(work_id):
            rec.update(status='skipped', reason='unidentified work'); rows.append(rec); continue
        target = dest / work_id / rel.name
        rec['destination'] = str(target)
        rec['evidence'] = {'id_confidence': item.get('id_confidence'), 'part': item.get('part'),
                           'edition_clues': item.get('edition_clues', [])}
        try:
            st = src.lstat()
        except OSError:
            st = None
        if st is None or not src.is_file() or src.is_symlink():
            rec.update(status='conflict', reason='source missing or changed')
        elif ('size_bytes' in item and st.st_size != item['size_bytes']) or \
             ('mtime_ns' in item and st.st_mtime_ns != item['mtime_ns']):
            rec.update(status='conflict', reason='source changed since inventory (size/mtime); re-scan')
        elif target.exists() or target.is_symlink() or str(target).casefold() in reserved:
            rec.update(status='conflict', reason='destination exists or collision')
        else:
            rec.update(status='proposed', reason='preview only')
            reserved.add(str(target).casefold())
        rows.append(rec)
    counts = {k: sum(x['status'] == k for x in rows) for k in ('proposed', 'skipped', 'conflict')}
    return {'schema_version': SCHEMA_VERSION, 'action': 'preview_only', 'source_root': str(source),
            'destination_root': str(dest), 'summary': counts, 'warnings': warnings,
            'review_groups': review_groups(inventory['files']), 'changes': rows}


def review_groups(files):
    """Works with several files. A shared ID is a relationship, never proof of identical content."""
    groups = defaultdict(list)
    for item in files:
        if item.get('work_id'):
            groups[item['work_id']].append(item)
    out = []
    for work_id, items in sorted(groups.items()):
        if len(items) < 2:
            continue
        parts = sorted({i['part'] for i in items if i.get('part')})
        editions = sorted({tuple(i.get('edition_clues', [])) for i in items})
        reason = ('multi-part set' if len(parts) == len(items) else
                  'multiple versions or ambiguous parts: possible duplicates, do not delete')
        out.append({'work_id': work_id, 'file_count': len(items), 'parts': parts,
                    'edition_variants': [list(e) for e in editions], 'reason': reason,
                    'files': sorted(i['relative_path'] for i in items)})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inventory'); ap.add_argument('--destination', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    inp = Path(args.inventory).expanduser().resolve(strict=True)
    output = Path(args.output).expanduser().absolute()
    if output.exists(): ap.error('Output exists; refusing to overwrite')
    with inp.open(encoding='utf-8') as f: data = json.load(f)
    if data.get('schema_version') != 1: ap.error('Unsupported inventory schema_version')
    report = plan(data, args.destination)
    if is_within(output, Path(report['source_root'])):
        ap.error('Output must be outside the source tree')
    with output.open('x', encoding='utf-8') as f: json.dump(report, f, indent=2, ensure_ascii=False)
    print(f'Preview: {report["summary"]}, review groups: {len(report["review_groups"])} -> {output}')
    for w in report['warnings']: print(f'WARNING: {w}')

if __name__ == '__main__': main()
