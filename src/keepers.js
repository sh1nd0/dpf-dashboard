// ── Draft Picks & Keeper Cost Model ──────────────────────────────────────
// Constants encode the league rules in LEAGUE_RULES.md. If the rules change,
// update both this file AND that doc. See "Keepers — Major League" section.
//
//   KEEPER_ADVANCE = 4         → "Annual Advancement: each keeper moves up 4 rounds per year"
//   KEEPER_FLOOR = 4           → "Players valued in R1-R4 are not keepable; once a player
//                                  reaches R1-R4, he becomes permanently ineligible".
//                                  Eligibility keys off the round you're keeping FROM, not
//                                  the advanced cost: any player drafted after Round 4 in
//                                  2026 (round > 4) is keepable for 2027. Advancing may put
//                                  their 2027 cost in R1-R4 (e.g. an R6 pick → R2) — that is
//                                  simply their FINAL keeper year; they're ineligible the
//                                  season after. Only players already at R1-R4 in 2026
//                                  (round <= 4) can't be kept at all.
//   UNDRAFTED_KEEPER_START=15  → "Undrafted players begin keeper life in Round 15. Former
//                                  rookie keepers converting to major league status also
//                                  begin in Round 15. All then advance 4 rounds annually."
//
// NOT yet encoded here (handled manually by commissioner via league_config.json):
//   - 2026 One-Time Mulligan: a draft-day-only affordance that lets one player
//     per team be kept at R1 despite normally being ineligible. It does NOT
//     extend the player's keeper life into 2027 — every R1-R4 keeper in 2026
//     is unkeepable for 2027, mulligan or not. The keepable2027 math here
//     already enforces this (a R1 mulligan-keeper has effectiveRound = 1, which
//     fails the `effectiveRound > KEEPER_FLOOR` test). So no special-casing is
//     needed in this file; the per-team flag in league_config.json is informational.
//   - Round Conflicts (when two keepers land in the same round, owner picks)
const DRAFT_PICKS = __DRAFT_PICKS_JSON__;
const KEEPER_ADVANCE = 4;  // LEAGUE_RULES.md → Annual Advancement
const KEEPER_FLOOR = 4;    // LEAGUE_RULES.md → Eligibility Limits (R1-R4 ineligible going forward)
const UNDRAFTED_KEEPER_START = 15;  // LEAGUE_RULES.md → Undrafted & Rookie Conversions

// Build lookup: player name → { round, pick, team, keeper }
const PICK_BY_NAME = {};
DRAFT_PICKS.forEach(dp => {
  PICK_BY_NAME[dp.n] = { round: dp.r, pick: dp.p, team: dp.t, keeper: dp.k };
});

// Keeper cost calculation
function getKeeperInfo(playerName) {
  const dp = PICK_BY_NAME[playerName];
  const draftRound = dp ? dp.round : null;
  const wasKeeper2026 = dp ? dp.keeper : false;

  // If not in draft, they're a potential FA pickup → R15 start
  const effectiveRound = draftRound || UNDRAFTED_KEEPER_START;

  // 2027 keeper cost = this year's round - 4 (advance 4 rounds)
  const cost2027 = effectiveRound - KEEPER_ADVANCE;

  // Can this player be kept in 2027? Eligibility is set by the round you're
  // keeping FROM: any player drafted after Round 4 in 2026 (round > 4) is
  // keepable for 2027 — even when advancing lands the cost in R1-R4, which just
  // makes 2027 their final keeper year. Players already at R1-R4 in 2026 aren't.
  const keepable2027 = effectiveRound > KEEPER_FLOOR;

  // How many more years keepable (including 2027)? You may keep while the round
  // you're keeping from is still > 4; the year it advances into R1-R4 is the last.
  let yearsLeft = 0;
  let r = effectiveRound;
  while (r > KEEPER_FLOOR) {
    yearsLeft++;
    r -= KEEPER_ADVANCE;
  }

  // Surplus value: player's LCV minus the "replacement value" at their keeper cost round
  // A round-4 player is essentially a 4th-round talent (~top 48 pick)
  // We normalize: round 1 pick is worth ~6.2 LCV, round 31 pick ~0 LCV
  // In a 12-team keeper league (~60 keepers), draft picks are less valuable
  // Linear approximation: roundValue = max(0, (32 - round) * 0.20)
  const roundValue = Math.max(0, (32 - effectiveRound) * 0.20);
  const costValue2027 = keepable2027 ? Math.max(0, (32 - cost2027) * 0.20) : 0;
  const p = _plyrI(playerName);
  const playerLCV = p ? (p.lcv || 0) : 0;
  // Surplus = production above what you'd expect from that draft slot
  // For keeper purposes: how much better is this player than what their keeper round implies?
  const surplusNow = playerLCV - roundValue;
  const surplus2027 = keepable2027 ? (playerLCV - costValue2027) : 0;

  // Multi-year surplus (discounted): sum of future surplus values
  // Now includes age-curve decay: older players' LCV projected to decline
  const playerAge = p ? (p.age || 28) : 28;
  let multiYearSurplus = 0;
  r = effectiveRound;
  let yr = 0;
  while (r > KEEPER_FLOOR) {
    r -= KEEPER_ADVANCE;
    yr++;
    const futureSlotVal = Math.max(0, (32 - r) * 0.20);
    const ageDec = ageDecayFactor(playerAge, yr);
    multiYearSurplus += (playerLCV * ageDec - futureSlotVal) * Math.pow(0.85, yr); // 15% annual discount + age decay
  }

  // Prospect FV bonus: high-FV prospects add future value to keeper calculations
  // FV² × 0.0001 gives: FV50=0.25, FV55=0.30, FV60=0.36, FV70=0.49
  const pr = (typeof findProspect === 'function') ? findProspect(playerName) : null;
  const prospectFV = pr ? (pr.fv || 0) : 0;
  const prospectBonus = prospectFV >= 50 ? (prospectFV * prospectFV * 0.0001) : 0;
  if (prospectBonus > 0 && yearsLeft >= 1) {
    multiYearSurplus += prospectBonus * yearsLeft * 0.8; // FV bonus scales with years of control
  }

  return {
    draftRound: draftRound,
    wasKeeper: wasKeeper2026,
    effectiveRound: effectiveRound,
    cost2027: keepable2027 ? cost2027 : null,
    keepable2027: keepable2027,
    yearsLeft: yearsLeft,
    surplusNow: surplusNow,
    surplus2027: surplus2027,
    multiYearSurplus: multiYearSurplus,
    roundValue: roundValue,
    prospectFV: prospectFV
  };
}

