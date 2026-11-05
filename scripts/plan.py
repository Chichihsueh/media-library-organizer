#!/usr/bin/env python3
"""Generate a non-executable preview for media organization. Never moves files."""
import argparse
import json
from pathlib import Path
import re

SAFE_ID = re.compile(r'^[A-Z]{2,8}-\d{2,7}$')

def is_within(path, root):
    return path == root or root in path.parents

def plan(inventory, destination):
    source = Path(inventory['source_root']).resolve(strict=True)
    dest = Path(destination).expanduser().resolve(strict=False)
    if is_within(dest, source) or is_within(source, dest):
        raise ValueError('Destination and source must be separate trees')
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
        if not src.is_file() or src.is_symlink():
            rec.update(status='conflict', reason='source missing or changed')
        elif target.exists() or target.is_symlink() or str(target).casefold() in reserved:
            rec.update(status='conflict', reason='destination exists or collision')
        else:
            rec.update(status='proposed', reason='preview only')
            reserved.add(str(target).casefold())
        rows.append(rec)
    counts = {k: sum(x['status'] == k for x in rows) for k in ('proposed','skipped','conflict')}
    return {'schema_version': 1, 'action': 'preview_only', 'source_root': str(source),
            'destination_root': str(dest), 'summary': counts, 'changes': rows}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inventory'); ap.add_argument('--destination', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    inp = Path(args.inventory).expanduser().resolve(strict=True)
    output = Path(args.output).expanduser().absolute()
    if output.exists(): ap.error('Output exists; refusing to overwrite')
    with inp.open(encoding='utf-8') as f: data=json.load(f)
    report=plan(data,args.destination)
    with output.open('x',encoding='utf-8') as f: json.dump(report,f,indent=2,ensure_ascii=False)
    print(f'Preview: {report["summary"]} -> {output}')

if __name__ == '__main__': main()
