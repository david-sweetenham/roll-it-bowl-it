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
import cricket_calendar

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


# ── Test 5: next_my_match with no my_team_id simulates nothing ────────────────

def test_5_next_my_match_without_team():
    """simulate_world_to('next_my_match') should not advance when no user team is set."""
    random.seed(55)
    world_state = _make_world_state([1, 2, 3], my_team_id=None)
    fixtures = _make_fixtures([(1, 2), (2, 3), (1, 3)])

    result = game_engine.simulate_world_to('next_my_match', fixtures, world_state)
    ok = (
        result['matches_simulated'] == 0
        and result['paused_at_fixture'] is None
        and result['results'] == []
    )
    _check('Test 5: simulate_world_to(next_my_match) requires a user team',
           ok, f"matches_simulated={result['matches_simulated']}, paused_at={result['paused_at_fixture']}")


# ── Helpers for domestic / world-rules tests ──────────────────────────────────

def _make_dom_teams(league, ids, prefix='Club'):
    """Return a list of domestic-team dicts usable by generate_domestic_fixtures."""
    return [
        {'team_id': tid, 'name': f'{prefix}{tid}', 'league': league,
         'home_venue_id': tid * 10}
        for tid in ids
    ]


def _parse_world_settings(settings):
    """
    Replicate the normalisation applied by both create_world and
    world_regenerate_calendar so we can test it in isolation.
    """
    world_scope = settings.get('world_scope', 'international')
    if world_scope not in ('international', 'domestic', 'combined'):
        world_scope = 'international'

    domestic_team_mode = settings.get('domestic_team_mode', 'selected')
    if domestic_team_mode not in ('selected', 'full_league'):
        domestic_team_mode = 'selected'

    domestic_leagues = settings.get('domestic_leagues') or []

    return world_scope, domestic_team_mode, domestic_leagues


# ── Test 6: domestic 'selected' mode — only chosen clubs in fixture pool ───────

def test_6_domestic_selected_mode():
    """
    When domestic_team_mode='selected', generate_domestic_fixtures should only
    produce matches between the clubs that were explicitly chosen — not the
    full league roster.
    """
    ALL_IDS      = list(range(41, 49))    # 8 BBL-style clubs
    SELECTED_IDS = {41, 43, 45}           # 3 chosen

    selected_teams = _make_dom_teams('Big Bash League', SELECTED_IDS)
    fixtures = cricket_calendar.generate_domestic_fixtures(
        'bbl', selected_teams, 2026, 2027
    )

    seen_ids   = {f['team1_id'] for f in fixtures} | {f['team2_id'] for f in fixtures}
    unexpected = seen_ids - SELECTED_IDS

    _check(
        'Test 6: domestic selected mode — only selected clubs appear in fixture pool',
        len(unexpected) == 0 and len(fixtures) > 0,
        f'unexpected IDs={unexpected}, fixtures={len(fixtures)}',
    )


# ── Test 7: domestic 'full_league' mode — all clubs in fixture pool ────────────

def test_7_domestic_full_league_mode():
    """
    When domestic_team_mode='full_league', every club in the league appears
    in at least one generated fixture, and home+away round-robin count is met.
    """
    ALL_IDS = list(range(41, 49))   # 8 clubs
    all_teams = _make_dom_teams('Big Bash League', ALL_IDS)

    fixtures = cricket_calendar.generate_domestic_fixtures(
        'bbl', all_teams, 2026, 2027
    )

    seen_ids = {f['team1_id'] for f in fixtures} | {f['team2_id'] for f in fixtures}
    missing  = set(ALL_IDS) - seen_ids

    # BBL has home_away=True → C(8,2)*2 = 56 fixtures per season
    n = len(ALL_IDS)
    expected_min = n * (n - 1)   # 56

    _check(
        'Test 7: domestic full_league mode — all clubs appear and fixture count correct',
        len(missing) == 0 and len(fixtures) >= expected_min,
        f'missing={missing}, fixtures={len(fixtures)}, expected>={expected_min}',
    )


# ── Test 8: combined world — both intl and domestic fixtures generated ──────────

def test_8_combined_world_fixture_types():
    """
    generate_realistic_calendar with non-empty team_ids AND domestic_leagues
    must produce both international bilateral fixtures and domestic fixtures,
    with no fixture crossing the two pools.
    """
    INTL_IDS   = [1, 2, 3, 4]
    INTL_NAMES = {1: 'England', 2: 'Australia', 3: 'India', 4: 'South Africa'}
    INTL_VENUES = {n: [i * 2] for i, n in INTL_NAMES.items()}

    DOM_IDS   = list(range(51, 57))   # 6 IPL teams
    dom_teams = _make_dom_teams('IPL', DOM_IDS, prefix='IPLClub')

    fixtures = cricket_calendar.generate_realistic_calendar(
        team_ids         = INTL_IDS,
        team_names       = INTL_NAMES,
        venue_ids        = INTL_VENUES,
        start_date_str   = '2026-01-01',
        density          = 'moderate',
        years            = 1,
        domestic_leagues = ['ipl'],
        domestic_teams   = dom_teams,
    )

    dom_fxs  = [f for f in fixtures if f.get('domestic_competition')]
    intl_fxs = [f for f in fixtures if not f.get('domestic_competition')]

    # No fixture should pair an international team with a domestic club
    dom_id_set  = set(DOM_IDS)
    intl_id_set = set(INTL_IDS)
    cross = [
        f for f in fixtures
        if (f['team1_id'] in intl_id_set) != (f['team2_id'] in intl_id_set)
           and (f['team1_id'] in dom_id_set or f['team2_id'] in dom_id_set)
    ]

    _check(
        'Test 8: combined world generates both international and domestic fixtures',
        len(dom_fxs) > 0 and len(intl_fxs) > 0,
        f'domestic={len(dom_fxs)}, international={len(intl_fxs)}',
    )
    _check(
        'Test 8b: combined world — no cross-pool (intl vs domestic) fixtures',
        len(cross) == 0,
        f'{len(cross)} cross-pool fixture(s) found',
    )


# ── Test 9: world settings normalisation ──────────────────────────────────────

def test_9_world_settings_normalisation():
    """
    The settings-normalisation logic used by both create_world and
    world_regenerate_calendar must:
      - preserve valid world_scope / domestic_team_mode values
      - fall back to safe defaults for invalid / missing values
    """
    cases = [
        # (input_settings, expected_scope, expected_mode)
        ({'world_scope': 'domestic',      'domestic_team_mode': 'full_league'},
         'domestic',      'full_league',  []),
        ({'world_scope': 'combined',      'domestic_team_mode': 'selected',
          'domestic_leagues': ['ipl', 'bbl']},
         'combined',      'selected',     ['ipl', 'bbl']),
        ({'world_scope': 'international'},
         'international', 'selected',     []),
        ({'world_scope': 'INVALID',       'domestic_team_mode': 'BAD'},
         'international', 'selected',     []),
        ({},
         'international', 'selected',     []),
        ({'world_scope': 'domestic',      'domestic_team_mode': 'full_league',
          'domestic_leagues': ['bbl']},
         'domestic',      'full_league',  ['bbl']),
    ]

    failures = []
    for settings, exp_scope, exp_mode, exp_leagues in cases:
        scope, mode, leagues = _parse_world_settings(settings)
        if scope != exp_scope or mode != exp_mode or leagues != exp_leagues:
            failures.append(
                f'{settings!r}: got ({scope!r},{mode!r},{leagues!r}), '
                f'expected ({exp_scope!r},{exp_mode!r},{exp_leagues!r})'
            )

    _check(
        'Test 9: world settings normalisation handles valid and invalid inputs correctly',
        len(failures) == 0,
        '; '.join(failures),
    )


# ── Test 10: regenerate-calendar preserves team pool across start-date shifts ──

def test_10_regenerate_preserves_team_pool():
    """
    Regenerating a calendar with the same domestic settings but a different
    start date must yield the exact same pool of participating teams.
    This mirrors what world_regenerate_calendar does when the user rebuilds
    their calendar mid-season.
    """
    SELECTED_IDS = {41, 42, 43, 44}
    selected_teams = _make_dom_teams('Big Bash League', SELECTED_IDS)

    original = cricket_calendar.generate_domestic_fixtures(
        'bbl', selected_teams, 2026, 2027
    )
    regen = cricket_calendar.generate_domestic_fixtures(
        'bbl', selected_teams, 2027, 2028    # later start (simulating mid-season regen)
    )

    orig_pool  = {f['team1_id'] for f in original} | {f['team2_id'] for f in original}
    regen_pool = {f['team1_id'] for f in regen}    | {f['team2_id'] for f in regen}

    _check(
        'Test 10: regenerate-calendar (selected mode) — team pool identical across start-date shifts',
        orig_pool == regen_pool == SELECTED_IDS,
        f'original={orig_pool}, regen={regen_pool}, expected={SELECTED_IDS}',
    )


# ── Test 11: domestic world scope — calendar_team_ids is empty (no intl fixtures) ─

def test_11_domestic_scope_no_intl_fixtures():
    """
    When world_scope='domestic', generate_realistic_calendar is called with
    calendar_team_ids=[] so no international bilateral fixtures are produced.
    Only domestic competition fixtures should appear.
    """
    DOM_IDS   = list(range(61, 67))
    dom_teams = _make_dom_teams('IPL', DOM_IDS, prefix='IPLTeam')

    fixtures = cricket_calendar.generate_realistic_calendar(
        team_ids         = [],     # domestic worlds pass empty list for intl
        team_names       = {},
        venue_ids        = {},
        start_date_str   = '2026-01-01',
        density          = 'moderate',
        years            = 1,
        domestic_leagues = ['ipl'],
        domestic_teams   = dom_teams,
    )

    dom_fxs  = [f for f in fixtures if f.get('domestic_competition')]
    intl_fxs = [f for f in fixtures if not f.get('domestic_competition')]

    _check(
        'Test 11: domestic-scope world — no international fixtures, only domestic',
        len(dom_fxs) > 0 and len(intl_fxs) == 0,
        f'domestic={len(dom_fxs)}, international={len(intl_fxs)}',
    )


# ── Run all tests ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_1_quick_sim_keys()
    test_2_next_match()
    test_3_end_of_series()
    test_4_date_and_digest()
    test_5_next_my_match_without_team()
    test_6_domestic_selected_mode()
    test_7_domestic_full_league_mode()
    test_8_combined_world_fixture_types()
    test_9_world_settings_normalisation()
    test_10_regenerate_preserves_team_pool()
    test_11_domestic_scope_no_intl_fixtures()

    print()
    print(f'Results: {_passed} passed, {_failed} failed')
    if _failed == 0:
        print('All tests PASSED')
    else:
        print(f'{_failed} test(s) FAILED')
        sys.exit(1)
