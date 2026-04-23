# Daily Playing of Fantasy — League Rules (2026)

Source: https://dpf.baseball.cbssports.com/rules (exported 2026-04-23).
Commissioners: Matt Dennewitz, Andrew Gaerig.

This file is the source of truth for league-rule constants used throughout the
codebase (`src/keepers.js`, `build_dashboard.py`, `validate.py`). If a rule
here changes, update both this file AND the corresponding constant in code.

## League identity
- **Name:** Daily Playing of Fantasy
- **URL:** https://dpf.baseball.cbssports.com
- **Teams:** 12
- **Player pool:** AL + NL
- **Fees:** $150/team ($1,800 pot → $150 CBS fee → $1,650 net)
  - H2H: 1st $300, 2nd $150
  - Rotisserie: 1st $450, 2nd $350, 3rd $250, 4th $150
  - Payouts sum if a team places in both formats. Due by draft day, paid by end of World Series.

## Draft
- **Format:** Snake, live
- **Date:** Sun Mar 15 2026, 3:00pm ET
- **Rounds:** 31 (60 sec/pick; draft robot for auto-picks)
- **Order:** reverse of prior season's final *Rotisserie* standings
- **Keepers** cost their assigned draft round (see Keepers section).
- Rosters must be legal by Opening Day (Wed Mar 25 2026).

## Rosters (34 total)
| Slot | Count |
|------|-------|
| Active | 19 |
| Reserve (bench) | 7 |
| IL | 4 |
| Minor League | 4 |

**Active lineup (19):** C, 1B, 2B, 3B, SS, LF, CF, RF, U (9 hitters) + 5 SP + 5 RP (10 pitchers).

Note: the printed constitution says "5 SP, 6 RP" — CBS settings say 5 SP, 5 RP, which matches the 19-active count. Treat the CBS table as authoritative.

- Injured / Minor players do NOT count against positional limits.
- Illegal rosters score 0 for the period.

## Scoring

**Head-to-Head, Most Categories** (bi-weekly periods, total stats per period, ties allowed — no tiebreaker).

| Batting (8) | Pitching (8) |
|-------------|--------------|
| BA          | ERA          |
| HR          | HD (Holds)   |
| KO (batter strikeouts — negative) | HRA (negative) |
| OBP         | K (pitcher)  |
| R           | QS           |
| RBI         | S (Saves)    |
| SB          | W            |
| SLG         | WHIP (negative) |

Rotisserie runs simultaneously across the whole season, same categories, independent standings. 8–8 H2H ties allowed. Rotisserie tiebreaker: Winning % → Head-to-Head → League vote.

## Schedule
- **Season start:** Wed Mar 25 2026
- **Periods:** bi-weekly, Monday–Sunday
- **H2H matchups:** 11 two-week periods
- **Playoffs:** top 4 advance; playoffs start Period 12; last 2 periods
- **Playoff tiebreaker:** better H

## Keepers — Major League (5)
Each team keeps five (5) MLB-level players from its final roster.

- **Annual advancement:** +4 rounds/year (R8 keeper → R4 keeper the next year).
- **Eligibility floor:** players valued in Rounds 1–4 are NOT keepable. Once a player reaches R1–R4, they are permanently ineligible.
- **2026 One-Time Mulligan:** each team may keep one player who would otherwise fall in R1–R4. That player is assigned to Round 1. May not be kept again. Valid 2026 only.
- **Undrafted / rookie conversion:** undrafted FA pickups begin keeper life at Round 15. Former rookie keepers converting to major-league status also start at R15. Both then advance +4 rounds/year.
- **Round conflicts:** if two keepers occupy the same round, one stays and the other(s) move to the next *earlier available* round. Owner selects which stays.
- **Deadline:** keepers due one week prior to draft; commissioners publish simultaneously.

## Keepers — Minor League (4)
Each team keeps up to four (4) minor leaguers / rookies.

- **Rookie eligibility (standard MLB rules):**
  - Hitters: <130 MLB AB
  - Pitchers: <50 MLB IP
- MiLB keepers do NOT count toward the five MLB keepers.
- When fully promoted, the player must occupy an active/reserve slot.
- When converted to MLB keeper status, begins at Round 15 the following season (see MLB keepers, undrafted conversion).

## Waivers & trades
- **Add/drop** is all via waivers. Plain "Added" only appears in the CBS log during the pre-season roster-setup window right after the draft; once waivers are live, every pickup is "Added off Waivers".
- **Waivers run:** every night (Sun–Sat).
- **Waiver period:** dropped players on waivers ≥ 2 days.
- **Waiver order:** reverse draft order; per the constitution, does NOT reset during the regular season. (The CBS config shows "resets after each week's games" — constitution supersedes.)
- **Waiver limits:** no cap on offers per period.
- **Trades:** process immediately, no league approval.
- **Trade deadline:** 11:59pm ET, Mon Aug 31 2026.
- **Offseason trades** allowed (players + draft picks).

## Player eligibility
- Positional: primary position, plus any position the player played 20 games last year OR 10 games this year.
- SP: 5 starts last year OR 5 starts this year.
- RP: 10 relief appearances last year OR 10 this year.

## Commissioner tl;dr
"KEEP UPDATING THOS M'FUCKIN LINEUPZ"
