"""
test_world_sim.py — Automated tests for Section 11: World Mode Calendar Simulation.
Run with:  python test_world_sim.py
All 4 tests must show [PASS] and the final line must read: All tests PASSED
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import random
import game_engine

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_team(team_id, name='Team', batting=3, bowling=3):
    players = []
    for i in range(11):
        players.append({
            'id': team_id * 100 + i,
            'team_id': team_id,
            'name': f'{name} P{i+1}',
            'batting_rating': batting,
            'bowling_rating': bowling if i >= 5 else 0,
            'bowling_type': 'pace',
        })
    return {
        'name': name,
        'short_code': name[:3].upper(),
        'badge_colour': '#888',
        'home_venue_id': team_id * 10,
        'players': players,
    }


def _make_world_state(team_ids, my_team_id=None):
    teams = {tid: _make_team(tid, f'Team{tid}') for tid in team_ids}
    return {
        'my_team_id':    my_team_id,
        'current_date':  '2025-01-01',
        'teams':         teams,
        'player_states': {},
    }


def _make_fixtures(team_pairs, fmt='T20', start='2025-01-10', series_id=1, world_id=1):
    fixtures = []
    from datetime import date, timedelta
    d = date.fromisoformat(start)
    for i, (t1, t2) in enumerate(team_pairs):
        fixtures.append({
            'id':             i + 1,
            'team1_id':       t1,
            'team2_id':       t2,
            'format':         fmt,
            'venue_id':       t1 * 10,
            'scheduled_date': (d + timedelta(days=i * 4)).isoformat(),
            'status':         'scheduled',
            'series_id':      series_id,
            'world_id':       world_id,
            'is_user_match':  0,
        })
    return fixtures


# ── Test infrastructure ────────────────────────────────────────────────────────

_passed = 0
_failed = 0


def _check(name, condition, detail=''):
    global _passed, _failed
    if condition:
        print(f'[PASS] {name}')
        _passed += 1
    else:
        print(f'[FAIL] {name}' + (f' — {detail}' if detail else ''))
        _failed += 1


# ── Test 1: quick_sim_match returns all required keys and valid values ──────────

def test_1_quick_sim_keys():
    """quick_sim_match must return all required keys with valid types."""
    random.seed(11)
    required_keys = {
        'winner_id', 'loser_id', 'result_type', 'margin_runs', 'margin_wickets',
        'team1_score', 'team2_score', 'top_scorer', 'top_bowler', 'summary',
        'home_team_id',
    }
    valid_result_types = {'runs', 'wickets', 'draw', 'tie'}
    failures = []

    for fmt in ('T20', 'ODI', 'Test'):
        world_state = _make_world_state([1, 2])
        fixture = {
            'team1_id': 1, 'team2_id': 2,
            'format': fmt, 'venue_id': 10,
        }
        for trial in range(10):
            res = game_engine.quick_sim_match(fixture, world_state)
            missing = required_keys - set(res.keys())
            if missing:
                failures.append(f'{fmt} trial {trial}: missing {missing}')
                continue
            if res['result_type'] not in valid_result_types:
                failures.append(f'{fmt}: invalid result_type {res["result_type"]!r}')
            if res['result_type'] == 'draw' and res['winner_id'] is not None:
                failures.append(f'{fmt}: draw should have winner_id=None')
            if res['result_type'] != 'draw' and res['winner_id'] not in (1, 2):
                failures.append(f'{fmt}: winner_id should be 1 or 2, got {res["winner_id"]}')
            if res['winner_id'] and res['winner_id'] == res['loser_id']:
                failures.append(f'{fmt}: winner_id == loser_id')
            if not isinstance(res['summary'], str) or not res['summary']:
                failures.append(f'{fmt}: summary must be a non-empty string')
            if not isinstance(res['team1_score'], str) or not res['team1_score']:
                failures.append(f'{fmt}: team1_score must be a non-empty string')

    _check('Test 1: quick_sim_match returns valid result', len(failures) == 0,
           '; '.join(failures[:3]))


# ── Test 2: simulate_world_to('next_match') simulates exactly one match ────────

def test_2_next_match():
    """simulate_world_to('next_match') must simulate exactly 1 fixture."""
    random.seed(22)
    world_state = _make_world_state([1, 2, 3])
    fixtures = _make_fixtures([(1, 2), (2, 3), (1, 3)])

    result = game_engine.simulate_world_to('next_match', fixtures, world_state)
    n = result['matches_simulated']
    ok = (n == 1)
    _check('Test 2: simulate_world_to(next_match) simulates exactly 1 match',
           ok, f'matches_simulated={n}')


# ── Test 3: simulate_world_to('end_of_series') covers all series fixtures ───────

def test_3_end_of_series():
    """simulate_world_to('end_of_series') must simulate all fixtures in the first series."""
    random.seed(33)
    world_state = _make_world_state([1, 2, 3, 4])

    # Series 1: 3 fixtures.  Series 2: 2 fixtures (different series_id)
    series1 = _make_fixtures([(1, 2), (3, 4), (1, 3)], series_id=10)
    series2 = _make_fixtures([(2, 4), (1, 4)], series_id=20, start='2025-04-01')
    all_fixtures = series1 + series2

    result = game_engine.simulate_world_to('end_of_series', all_fixtures, world_state)
    n = result['matches_simulated']
    ok = (n == 3)
    _check('Test 3: simulate_world_to(end_of_series) covers full first series',
           ok, f'matches_simulated={n}, expected 3')


# ── Test 4: simulate_world_to('date') stops at target date; digest keys present ─

def test_4_date_and_digest():
    """simulate_world_to('date') must stop at target_date and results have required keys."""
    random.seed(44)
    world_state = _make_world_state([1, 2])
    world_state['target_date'] = '2025-02-15'

    from datetime import date, timedelta
    base = date(2025, 1, 10)
    fixtures = []
    for i in range(10):
        d = (base + timedelta(days=i * 7)).isoformat()
        fixtures.append({
            'id': i + 1,
            'team1_id': 1, 'team2_id': 2,
            'format': 'T20',
            'venue_id': 10,
            'scheduled_date': d,
            'status': 'scheduled',
            'series_id': 1,
            'world_id': 1,
            'is_user_match': 0,
        })

    result = game_engine.simulate_world_to('date', fixtures, world_state)

    # All results must have scheduled_date <= target_date
    bad_dates = [r['scheduled_date'] for r in result['results']
                 if r.get('scheduled_date', '') > '2025-02-15']

    required_result_keys = {'winner_id', 'loser_id', 'result_type', 'summary',
                            'team1_score', 'team2_score', 'fixture_id', 'format'}
    key_failures = []
    for r in result['results']:
        missing = required_result_keys - set(r.keys())
        if missing:
            key_failures.append(f'missing {missing}')

    ok = len(bad_dates) == 0 and len(key_failures) == 0
    detail = ''
    if bad_dates:
        detail += f'dates beyond target: {bad_dates[:2]}; '
    if key_failures:
        detail += f'key failures: {key_failures[:2]}'
    _check('Test 4: simulate_world_to(date) respects target_date and result keys are complete',
           ok, detail)


# ── Run all tests ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_1_quick_sim_keys()
    test_2_next_match()
    test_3_end_of_series()
    test_4_date_and_digest()

    print()
    print(f'Results: {_passed} passed, {_failed} failed')
    if _failed == 0:
        print('All tests PASSED')
    else:
        print(f'{_failed} test(s) FAILED')
        sys.exit(1)
