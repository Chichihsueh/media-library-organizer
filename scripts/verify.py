#!/usr/bin/env python3
"""Opt-in online check of tentative work IDs against r18.dev's public JSON.

Sends ONLY the validated ID (e.g. ABC-123) -- never filenames or paths. Dry run unless
--online is given. Writes a report; never touches media files. A match means the ID exists
and the service returned the same ID; it does NOT prove the local file is that work.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SAFE_ID = re.compile(r'^[A-Z]{2,8}-\d{2,7}$')
BASE = 'https://r18.dev/videos/vod/movies/detail/-/dvd_id={id}/json'
USER_AGENT = 'media-library-organizer/0.1.2 (+local verification)'
SCHEMA_VERSION = 1


def norm(value):
    return re.sub(r'[^A-Za-z0-9]', '', str(value or '')).upper()


def fetch_json(work_id, timeout=10):
    """Return (http_status, parsed_json_or_None). Host is fixed; only a validated ID is interpolated."""
    if not SAFE_ID.fullmatch(work_id):
        raise ValueError('refusing to query an unvalidated ID')
    req = urllib.request.Request(BASE.format(id=work_id), headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        return exc.code, None


def id_from_content(content_id):
    """'118ama00027' / 'h_1329askd00007' / '1dandy911r' -> (LABEL, number); None for unusual shapes."""
    m = re.fullmatch(r'(?:[a-z]_)?\d{0,5}([a-z]{2,8})0*(\d{1,7})[a-z]?', str(content_id or '').lower())
    return (m.group(1).upper(), int(m.group(2))) if m else None


def classify(work_id, status, body):
    if status == 429 or (status and status >= 500):
        return {'status': 'error', 'detail': f'HTTP {status}'}
    if status == 404 or not body:
        return {'status': 'not_found', 'detail': 'no record (not proof the ID is wrong)'}
    returned = body.get('dvd_id') or body.get('dvdId')
    rec = {'returned_id': returned, 'content_id': body.get('content_id'),
           'release_date': body.get('release_date'), 'runtime_mins': body.get('runtime_mins')}
    if returned:
        if norm(returned) == norm(work_id):
            return {'status': 'id_match', 'detail': 'service returned the same ID', **rec}
        return {'status': 'mismatch', 'detail': 'service returned a different ID', **rec}
    # The dvd_id lookup may omit dvd_id; derive the ID from content_id instead.
    derived = id_from_content(body.get('content_id'))
    label, _, number = work_id.partition('-')
    if derived is None:
        return {'status': 'unconfirmed', 'detail': 'record found but ID not comparable', **rec}
    if derived == (label, int(number)):
        return {'status': 'id_match', 'detail': 'matched via content_id', **rec}
    return {'status': 'mismatch', 'detail': 'content_id points to a different ID', **rec}


def verify(ids, fetch=fetch_json, cache=None, delay=1.0, limit=50, sleep=time.sleep, on_progress=None):
    cache = {} if cache is None else cache
    results, sent = {}, 0
    for work_id in ids:
        if not SAFE_ID.fullmatch(work_id):
            results[work_id] = {'status': 'skipped', 'detail': 'not a valid ID format'}
        elif work_id in cache:
            results[work_id] = {**cache[work_id], 'from_cache': True}
        elif sent >= limit:
            results[work_id] = {'status': 'skipped', 'detail': 'request limit reached'}
        else:
            if sent: sleep(delay)
            sent += 1
            try:
                res = classify(work_id, *fetch(work_id))
            except (OSError, ValueError) as exc:
                res = {'status': 'error', 'detail': type(exc).__name__}
            results[work_id] = res
            if res['status'] != 'error': cache[work_id] = res
            if on_progress and sent % 50 == 0: on_progress(sent, len(ids))
            if res['detail'] == 'HTTP 429':  # fail closed: stop hammering a rate-limiting service
                break
    return results, sent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inventory'); ap.add_argument('--output', required=True)
    ap.add_argument('--online', action='store_true', help='actually query the network (default: dry run)')
    ap.add_argument('--cache', help='JSON cache file (read, then rewritten atomically)')
    ap.add_argument('--delay', type=float, default=1.0, help='seconds between requests (min 0.5)')
    ap.add_argument('--limit', type=int, default=50, help='max network requests per run')
    args = ap.parse_args()
    inv = json.loads(Path(args.inventory).expanduser().read_text(encoding='utf-8'))
    ids = sorted({f['work_id'] for f in inv['files'] if f.get('work_id')})
    out = Path(args.output).expanduser().absolute()
    if out.exists(): ap.error('Output exists; refusing to overwrite')
    if Path(inv['source_root']).resolve() in out.parents: ap.error('Output must be outside the source tree')
    if not args.online:
        print(f'Dry run: would send {len(ids)} ID(s) only (no filenames/paths). Re-run with --online.')
        print('\n'.join(ids[:20]) + ('\n...' if len(ids) > 20 else ''))
        return
    cache_path = Path(args.cache).expanduser() if args.cache else None
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path and cache_path.exists() else {}
    def save_cache():
        if cache_path:
            tmp = cache_path.with_suffix('.tmp')
            tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8'); tmp.replace(cache_path)
    def progress(sent, total):
        save_cache(); print(f'  ... {sent} requests sent ({len(cache)} cached of {total} IDs)', flush=True)
    try:
        results, sent = verify(ids, cache=cache, delay=max(args.delay, 0.5), limit=args.limit, on_progress=progress)
    except KeyboardInterrupt:
        save_cache(); sys.exit('Interrupted: progress saved to cache; re-run the same command to resume.')
    save_cache()
    summary = {k: sum(r['status'] == k for r in results.values())
               for k in ('id_match', 'mismatch', 'unconfirmed', 'not_found', 'error', 'skipped')}
    report = {'schema_version': SCHEMA_VERSION, 'source': 'r18.dev', 'requests_sent': sent,
              'summary': summary, 'results': results,
              'note': 'id_match does not prove the local file is that work; confirm duration/title before renaming.'}
    with out.open('x', encoding='utf-8') as f: json.dump(report, f, indent=2, ensure_ascii=False)
    print(f'Verified {len(ids)} ID(s), {sent} request(s): {summary} -> {out}')

if __name__ == '__main__': main()
