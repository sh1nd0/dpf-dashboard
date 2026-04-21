#!/usr/bin/env python3
"""Deduplicate + repair data/cbs_transactions.json.

The CBS scraper occasionally emits multiple rows for a single real transaction
— duplicated across team-id encodings, mojibake, and partial/complete player
sets. This script reconstructs one canonical row per (date, team, action-type).

Strategy:
  Non-trade rows
    Group by (date, teamId, action-type). Within each group, union all players
    keyed on normalized name, picking the cleanest action string per player.

  Trade rows
    Reconstruct from ground truth — the "Traded from <Team>" substring in each
    player's action tells us the SOURCE team; the row's own team is the
    DESTINATION. So for each trade date we:
      1. Collect every (player, from_team) pair seen across all copies.
      2. Partition players by from_team.
      3. Emit one row per destination team: destination = the OTHER team,
         players = the from-this-team set with `Traded from <from_team>`.
    This guarantees exactly 2 rows per 2-team trade, no matter how many
    duplicate/partial/misattributed copies the scraper produced.

Safe to run idempotently.
"""
from __future__ import annotations
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TX_PATH = ROOT / "data" / "cbs_transactions.json"

TEAM_IDS = {
    "Weird Fishes / Arrighetti": "1",
    "Dinosaur Jr Caminero": "2",
    "Colonel Corbin's Ascent": "3",
    "Okamotomami": "4",
    "Buddy Buddy Buddy All On Base": "5",
    "A Pete Crow-Armstrong Looked at Me": "6",
    "Whoop Whoop that's the sound of Dylan Cease": "7",
    "Ballesteros, Let the Rhythm Take You Over": "8",
    "Yesavage Garden": "9",
    "Blame it on the Rainiel": "10",
    "Before and After Shohei": "11",
    "Popped A Mahle I'm Sweating": "12",
}
ID_TO_NAME = {v: k for k, v in TEAM_IDS.items()}


def strip_mojibake(s: str) -> str:
    if not s:
        return s or ""
    for _ in range(6):
        if "Ã" not in s and "Â" not in s:
            break
        try:
            decoded = s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if decoded == s:
            break
        s = decoded
    return unicodedata.normalize("NFC", s)


def normalize_team_name(s: str) -> str:
    s = strip_mojibake(s or "")
    s = (s.replace("\u2019", "'")
          .replace("\u2018", "'")
          .replace("\u201c", '"')
          .replace("\u201d", '"'))
    return s.strip()


def clean_name(s: str) -> str:
    return strip_mojibake(s or "").strip()


def clean_action(s: str) -> str:
    if not s:
        return s or ""
    s = strip_mojibake(s).replace("\u2019", "'")
    s = s.split(" - ", 1)[0].strip()
    m = re.match(r'^(Traded from .+?)(?=[A-Z][a-z]+ (?:[A-Z][a-zA-Z.\- ]*)? ?• )', s)
    if m:
        s = m.group(1).strip()
    s = re.sub(r"^(Added|Dropped)([A-Z])", r"\1", s)
    return s


def canonical_team_for_row(tx: dict) -> tuple[str, str]:
    """Return (team_id, team_name). team_id is '' when unknown."""
    name = normalize_team_name(tx.get("teamName") or tx.get("team") or "")
    if name in TEAM_IDS:
        return TEAM_IDS[name], name
    raw = tx.get("teamId")
    if raw not in (None, "", 0, "0"):
        tid = str(raw)
        if tid in ID_TO_NAME:
            return tid, ID_TO_NAME[tid]
    return "", name


def action_type(action: str) -> str:
    if not action:
        return "unknown"
    if "Traded" in action:
        return "trade"
    if action.startswith(("Added", "Dropped", "Claimed")):
        return "adddrop"
    return "adddrop"


def parse_date(d: str) -> datetime:
    d = (d or "").replace("\u00a0", " ").replace(" ET", "").strip()
    try:
        return datetime.strptime(d, "%m/%d/%y %I:%M %p")
    except ValueError:
        return datetime.min


def action_quality(a: str) -> tuple[int, int, int]:
    if not a:
        return (-100, 0, 0)
    moji = -(a.count("Ã") + a.count("Â"))
    junk = -(a.count("•") * 5)
    length = -len(a)
    return (moji, junk, length)


# ── Non-trade row consolidation ─────────────────────────────────────────────
def merge_players(rows: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for row in rows:
        for p in row.get("players") or []:
            name = clean_name(p.get("name") or "")
            if not name:
                continue
            incoming = dict(p)
            incoming["name"] = name
            incoming["action"] = clean_action(p.get("action") or "")
            if p.get("mlbTeam"):
                incoming["mlbTeam"] = strip_mojibake(p["mlbTeam"]).strip()
            existing = merged.get(name)
            if existing is None:
                merged[name] = incoming
                continue
            if action_quality(incoming["action"]) > action_quality(existing.get("action", "")):
                existing["action"] = incoming["action"]
            for k in ("pos", "mlbTeam"):
                if incoming.get(k) and not existing.get(k):
                    existing[k] = incoming[k]
    return list(merged.values())


# ── Trade-specific reconstruction ───────────────────────────────────────────
FROM_RE = re.compile(r"Traded from\s+(.+?)(?:\s+\-\s+|$)")


def extract_from_team(action: str) -> str:
    if not action:
        return ""
    m = FROM_RE.search(strip_mojibake(action).replace("\u2019", "'"))
    if not m:
        return ""
    name = normalize_team_name(m.group(1))
    # Trim any trailing concatenation: "Colonel Corbin's AscentVladimir..." →
    # match the longest known team name prefix.
    for known in sorted(TEAM_IDS.keys(), key=len, reverse=True):
        if name.startswith(known):
            return known
    return name  # unknown team — caller will drop


def reconstruct_trades(date: str, rows: list[dict]) -> list[dict]:
    """Given all trade-rows on a single date, reconstruct canonical rows.

    Returns one row per destination team, with players = the set coming from
    the other team in the trade. Supports multi-way trades by partitioning
    players by from-team and emitting a row per involved team.
    """
    # Collect every (player_name, from_team, player_dict) seen
    seen: dict[tuple[str, str], dict] = {}
    for row in rows:
        for p in row.get("players") or []:
            name = clean_name(p.get("name") or "")
            if not name:
                continue
            from_team = extract_from_team(p.get("action") or "")
            if not from_team:
                continue
            key = (name, from_team)
            incoming = dict(p)
            incoming["name"] = name
            incoming["action"] = f"Traded from {from_team}"
            if p.get("mlbTeam"):
                incoming["mlbTeam"] = strip_mojibake(p["mlbTeam"]).strip()
            existing = seen.get(key)
            if existing is None:
                seen[key] = incoming
            else:
                for k in ("pos", "mlbTeam"):
                    if incoming.get(k) and not existing.get(k):
                        existing[k] = incoming[k]

    # Group players by from_team → these are the packages each team SENT
    sent: dict[str, list[dict]] = defaultdict(list)
    for (name, from_team), p in seen.items():
        sent[from_team].append(p)

    involved = [t for t in sent if t in TEAM_IDS]
    if len(involved) < 2:
        # Not enough info to reconstruct — skip (callers can log)
        return []

    out = []
    # For a 2-team trade: team A receives what team B sent, and vice versa.
    # For N-way (rare), each team receives the union of everyone else's sent.
    for dest in involved:
        received = []
        for src in involved:
            if src == dest:
                continue
            for p in sent[src]:
                # Action should reflect 'from src' (already set)
                received.append(p)
        if not received:
            continue
        out.append({
            "date": date,
            "teamId": TEAM_IDS[dest],
            "teamName": dest,
            "team": dest,
            "players": received,
        })
    return out


# ── Main pipeline ───────────────────────────────────────────────────────────
def is_trade_row(tx: dict) -> bool:
    return any("Traded" in (p.get("action") or "") for p in tx.get("players") or [])


def consolidate(rows: list[dict]) -> tuple[list[dict], int]:
    # Split trade rows from non-trade rows
    trade_rows_by_date: dict[str, list[dict]] = defaultdict(list)
    non_trade_groups: dict[tuple, list[dict]] = defaultdict(list)
    unattributed: list[dict] = []

    for tx in rows:
        if is_trade_row(tx):
            date = (tx.get("date") or "").replace("\u00a0", " ").strip()
            trade_rows_by_date[date].append(tx)
        else:
            tid, _ = canonical_team_for_row(tx)
            if not tid:
                unattributed.append(tx)
                continue
            date = (tx.get("date") or "").replace("\u00a0", " ").strip()
            non_trade_groups[(date, tid)].append(tx)

    out: list[dict] = []

    # Non-trade consolidation
    for (date, tid), members in non_trade_groups.items():
        players = merge_players(members)
        if not players:
            continue
        template = members[0]
        entry = {
            "date": date,
            "teamId": tid,
            "teamName": ID_TO_NAME[tid],
            "team": ID_TO_NAME[tid],
            "players": players,
        }
        if template.get("effective"):
            entry["effective"] = template["effective"]
        out.append(entry)

    # Trade reconstruction
    for date, trows in trade_rows_by_date.items():
        reconstructed = reconstruct_trades(date, trows)
        out.extend(reconstructed)

    # Unattributed (shouldn't happen much) — keep as-is
    out.extend(unattributed)

    out.sort(key=lambda x: parse_date(x.get("date", "")))
    return out, len(rows) - len(out)


def main(argv: list[str]) -> int:
    data = json.loads(TX_PATH.read_text())
    cleaned, dropped = consolidate(data)
    TX_PATH.write_text(json.dumps(cleaned, indent=2) + "\n")
    print(f"Cleaned transactions: {len(data)} → {len(cleaned)} (dropped {dropped})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
