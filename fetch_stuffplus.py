#!/usr/bin/env python3
"""Fetch FanGraphs Stuff+ / Location+ / Pitching+ for the current season.

Writes: data/stuff_plus_2026.csv with schema:
    name|stuff_plus|location_plus|pitching_plus

Source: the `That's Ball Baby` project already scrapes the MLB-wide
FanGraphs pitch-modeling board (type=36) nightly via browserless — the
only path that reliably gets past FanGraphs' Cloudflare/anti-bot, which
403s GitHub-runner IPs for direct/pybaseball fetches. That project
commits a standalone file:

    sh1nd0/thatsball.baby : src/pipeline/stuff_plus_mlb.json
    { "season": 2026, "asOf": "YYYY-MM-DD",
      "pitchingPlus": { "<name>": {"stuff": int, "loc": int, "pitching": int}, ... } }

We read it via the GitHub contents API (private repo → needs a token)
and transform it to the CSV the dashboard build expects. This replaces
the old pybaseball.pitching_stats call, which has been 403-ing in CI.

Fault-tolerant by contract: any failure (no token, network, empty body,
schema drift) leaves the existing stuff_plus_2026.csv untouched and
exits 0 so the daily build keeps shipping.

Env:
    DPF_SEASON       season to expect (default 2026)
    TBB_READ_TOKEN   GitHub token with contents:read on thatsball.baby
    TBB_SRC_REPO     override source repo  (default sh1nd0/thatsball.baby)
    TBB_SRC_PATH     override source path  (default src/pipeline/stuff_plus_mlb.json)
    TBB_SRC_REF      override source ref   (default main)
"""
from __future__ import annotations
import csv
import json
import os
import sys
import urllib.error
import urllib.request

SEASON = int(os.environ.get('DPF_SEASON', '2026'))
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

SRC_REPO = os.environ.get('TBB_SRC_REPO', 'sh1nd0/thatsball.baby')
SRC_PATH = os.environ.get('TBB_SRC_PATH', 'src/pipeline/stuff_plus_mlb.json')
SRC_REF = os.environ.get('TBB_SRC_REF', 'main')


def _fetch_source() -> dict | None:
    """Fetch + parse stuff_plus_mlb.json from the source repo, or None."""
    token = os.environ.get('TBB_READ_TOKEN') or os.environ.get('TBB_TOKEN')
    if not token:
        print('WARNING: TBB_READ_TOKEN not set — cannot fetch Stuff+ source.')
        return None

    url = f'https://api.github.com/repos/{SRC_REPO}/contents/{SRC_PATH}?ref={SRC_REF}'
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        # raw media type → response body IS the file (no base64 wrapper)
        'Accept': 'application/vnd.github.raw+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'dpf-dashboard-fetch-stuffplus',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8', 'replace')[:200]
        except Exception:
            pass
        print(f'ERROR: GitHub API {e.code} fetching {SRC_REPO}/{SRC_PATH}: {body}')
        if e.code in (401, 403):
            print('  (check TBB_READ_TOKEN has contents:read on the source repo)')
        elif e.code == 404:
            print('  (file/repo/ref not found — has the TBB scrape run yet?)')
        return None
    except (urllib.error.URLError, TimeoutError) as e:
        print(f'ERROR: network error fetching Stuff+ source: {e}')
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f'ERROR: source file is not valid JSON: {e}')
        return None


def fetch_stuffplus() -> int:
    data = _fetch_source()
    if not data:
        return 0

    pp = data.get('pitchingPlus')
    if not isinstance(pp, dict) or not pp:
        print('WARNING: source has no pitchingPlus entries.')
        return 0

    src_season = data.get('season')
    if src_season is not None and int(src_season) != SEASON:
        # Don't hard-fail — just surface the mismatch. The dashboard wants
        # current-season numbers; a stale-season file would be misleading.
        print(f'WARNING: source season {src_season} != expected {SEASON}; using anyway.')
    if data.get('asOf'):
        print(f"Stuff+ source asOf {data['asOf']} ({len(pp)} pitchers)")

    # Build rows first; only write the file if we actually have data so a
    # bad fetch can never truncate the existing CSV.
    rows = []
    for name, vals in pp.items():
        nm = str(name or '').strip()
        if not nm or not isinstance(vals, dict):
            continue
        stuff, loc, pit = vals.get('stuff'), vals.get('loc'), vals.get('pitching')
        if stuff is None and loc is None and pit is None:
            continue

        def _i(v):
            return '' if v is None else int(round(float(v)))

        rows.append([nm, _i(stuff), _i(loc), _i(pit)])

    if not rows:
        print('WARNING: no usable Stuff+ rows after parsing.')
        return 0

    out_path = os.path.join(OUTDIR, f'stuff_plus_{SEASON}.csv')
    with open(out_path, 'w', newline='') as f:
        w = csv.writer(f, delimiter='|')
        w.writerow(['name', 'stuff_plus', 'location_plus', 'pitching_plus'])
        w.writerows(rows)

    print(f'Stuff+ {SEASON}: wrote {len(rows)} rows to {out_path}')
    return len(rows)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    n = fetch_stuffplus()
    if n == 0:
        # Don't fail the build — leave prior CSV in place. Exit 0.
        print('fetch_stuffplus.py: non-fatal, proceeding.')
        sys.exit(0)


if __name__ == '__main__':
    main()
