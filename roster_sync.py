#!/usr/bin/env python3
"""Compare CBS rosters with cbs_transactions.json and generate missing Add transactions.

Usage: python3 roster_sync.py
Reads: cbs_rosters.json, data/cbs_transactions.json
Writes: Updated data/cbs_transactions.json with synthetic "Added" transactions
"""
import json, sys
from datetime import datetime

CBS_TEAM_IDS = {
    'Weird Fishes / Arrighetti': '1',
    'Dinosaur Jr Caminero': '2',
    "Colonel Corbin's Ascent": '3',
    'Okamotomami': '4',
    'Buddy Buddy Buddy All On Base': '5',
    'A Pete Crow-Armstrong Looked at Me': '6',
    "Whoop Whoop that's the sound of Dylan Cease": '7',
    'Everythings McGonigle Green': '7',
    'Ballesteros, Let the Rhythm Take You Over': '8',
    'Yesavage Garden': '9',
    'Blame it on the Rainiel': '10',
    'Before and After Shohei': '11',
    "Popped A Mahle I'm Sweating": '12',
}

cbs_rosters = json.load(open('cbs_rosters.json'))
txns = json.load(open('data/cbs_transactions.json'))

def parse_date(s):
    s = s.replace('\u00a0', ' ').replace(' ET', '').strip()
    for fmt in ('%m/%d/%y %I:%M %p', '%m/%d/%y'):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    return datetime.min

txns_sorted = sorted(txns, key=lambda t: parse_date(t['date']))

# Track last action per player
player_last_action = {}
for txn in txns_sorted:
    team_id = str(txn.get('teamId', ''))
    for p in txn.get('players', []):
        name = p.get('name', '')
        if not name:
            continue
        action = p.get('action', '')
        player_last_action[name] = (action, team_id, txn['date'])

new_txns = []
for team_name, players in cbs_rosters.items():
    team_id = CBS_TEAM_IDS.get(team_name, '')
    for player_name in players:
        last = player_last_action.get(player_name)
        if last:
            action, last_team, last_date = last
            if action == 'Dropped':
                new_txns.append({
                    'date': '4/3/26 12:00 AM ET',
                    'teamId': team_id,
                    'team': team_name,
                    'players': [{'name': player_name, 'action': 'Added', 'synthetic': True}]
                })
                print(f"  MISSING ADD: {player_name} → {team_name} (was Dropped on {last_date})")
            elif action in ('Added', 'Added off Waivers') and str(last_team) != str(team_id):
                new_txns.append({
                    'date': '4/3/26 12:00 AM ET',
                    'teamId': team_id,
                    'team': team_name,
                    'players': [{'name': player_name, 'action': 'Added', 'synthetic': True}]
                })
                print(f"  WRONG TEAM: {player_name} → {team_name} (was on team {last_team})")

if new_txns:
    txns.extend(new_txns)
    txns.sort(key=lambda t: parse_date(t['date']), reverse=True)
    json.dump(txns, open('data/cbs_transactions.json', 'w'), indent=2)
    print(f"\nAdded {len(new_txns)} synthetic transactions. Total: {len(txns)}")
else:
    print("No missing transactions found!")
