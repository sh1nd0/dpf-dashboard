#!/usr/bin/env python3
"""Normalize data/injuries.json to remove name-mangling artifacts.

The CBS injuries scraper occasionally emits names as
"X. LastFirst Last" — the abbreviated link text concatenated with the full
name (same anchor covering two cells). We recover the full name by finding
the longest suffix that appears twice in the string: that suffix is the
surname, and the text AFTER its earlier occurrence is the real full name.

Examples:
  "G. SpringerGeorge Springer"    → "George Springer"
  "A. Smith-ShawverA.J. Smith-Shawver" → "A.J. Smith-Shawver"
  "T. d'ArnaudTravis d'Arnaud"    → "Travis d'Arnaud"
  "Ha-seong Kim"                  → "Ha-seong Kim"   (unchanged; no doubling)
"""
from __future__ import annotations
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "injuries.json"


def unmangle_name(s: str) -> str:
    if not s:
        return s
    s = unicodedata.normalize("NFC", s).strip()
    n = len(s)
    # Look for the longest suffix of s that also appears earlier in s. That
    # suffix is the surname repeated at the end of both the short and full
    # forms. Start with a generous max length that still leaves room for
    # something reasonable to precede the duplicate.
    for length in range(min(n // 2, 30), 3, -1):
        suffix = s[-length:]
        earlier = s.rfind(suffix, 0, n - length)
        if earlier > 0:
            candidate = s[earlier + length:].strip()
            # Sanity: the recovered full name should start with a capital
            # letter (initial or Firstname), contain at least one space or be
            # a hyphenated name, and not itself be duplicative.
            if candidate and candidate[0].isupper() and (" " in candidate or "-" in candidate):
                return candidate
    return s


def main(argv):
    data = json.loads(PATH.read_text())
    changed = 0
    for row in data:
        orig = row.get("name", "")
        fixed = unmangle_name(orig)
        if fixed != orig:
            row["name"] = fixed
            changed += 1
    PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Normalized {changed} injury names (of {len(data)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
