"""
test_sim_controls.py — Automated tests for Section 10: In-Match Simulation Controls.
Run with:  python test_sim_controls.py
All 5 tests must show [PASS] and the final line must read: All tests PASSED
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import game_engine

# ── Helper ─────────────────────────────────────────────────────────────────────

def _make_state(
    fmt='T20',
    over_number=0,
    ball_in_over=0,
    total_runs=0,
    total_wickets=0,
    target=None,
    innings_number=1,
    max_overs=None,
):
    """Create a minimal sim state for testing simulate_to()."""
    if max_overs is None:
        max_overs = {'T20': 20, 'ODI': 50, 'Test': None}[fmt]

    batting = []
    for i in range(11):
        batting.append({
            'player_id':     i + 1,
            'name':          f'Batter {i + 1}',
            'batting_rating': 3,
            'runs':          0,
            'balls':         0,
            'dismissed':     False,
            'in':            i < 2,   # first two are at the crease
        })

    bowling = []
    for i in range(6):
        bowling.append({
            'player_id':    100 + i,
            'name':         f'Bowler {i + 1}',
            'bowling_type': 'pace' if i % 2 == 0 else 'spin',
            'bowling_rating': 3,
            'overs_bowled': 0,
            'balls_bowled': 0,
            'runs':         0,
            'wickets':      0,
            'maidens':      0,
            '_this_over_runs': 0,
        })

    return {
        'format':          fmt,
        'max_overs':       max_overs,
        'target':          target,
        'innings_number':  innings_number,
        'over_number':     over_number,
        'ball_in_over':    ball_in_over,
        'is_free_hit':     False,
        'total_runs':      total_runs,
        'total_wickets':   total_wickets,
        'batting_players': batting,
        'striker_idx':     0,
        'non_striker_idx': 1,
        'next_batter_idx': 2,
        'bowling_players': bowling,
        'last_bowler_id':  None,
        'current_bowler_id': None,
    }


# ── Tests ──────────────────────────────────────────────────────────────────────

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


# ── Test 1: simulate_to('wicket') always adds exactly one wicket ────────────────

def test_1_wicket():
    """simulate_to('wicket') from a fresh innings adds exactly 1 wicket (or ends innings)."""
    import random
    random.seed(42)
    for trial in range(20):
        state = _make_state(fmt='T20', over_number=0, ball_in_over=0, total_wickets=0)
        result = game_engine.simulate_to('wicket', state)
        wf = result['sim_digest']['wickets_fallen']
        ic = result['innings_complete']
        # Either exactly 1 wicket was taken, or the innings ended (all-out via overs with 0 wk possible)
        ok = (wf == 1) or (ic and wf >= 0)
        if not ok:
            _check('Test 1: simulate_to(wicket)', False,
                   f'trial {trial}: wickets_fallen={wf}, innings_complete={ic}')
            return
    _check('Test 1: simulate_to(wicket)', True)


# ── Test 2: simulate_to('over') always ends on a complete over ─────────────────

def test_2_over():
    """After simulate_to('over'), ball_in_over must be 0 (complete over boundary)."""
    import random
    random.seed(7)
    failures = []
    for trial in range(20):
        # Start mid-over sometimes
        ball = trial % 6
        state = _make_state(fmt='ODI', over_number=5, ball_in_over=ball)
        result = game_engine.simulate_to('over', state)
        new_ball = result['state']['ball_in_over']
        # Either ball_in_over==0 (complete over) or innings ended
        if new_ball != 0 and not result['innings_complete']:
            failures.append(f'trial {trial} (start_ball={ball}): ball_in_over={new_ball}')
    _check('Test 2: simulate_to(over) ends on complete over',
           len(failures) == 0,
           '; '.join(failures[:3]))


# ── Test 3: simulate_to('session') in Test ends at correct session boundary ────

def test_3_session():
    """simulate_to('session') in Test format ends at a session boundary over."""
    import random
    random.seed(99)

    # Expected session boundaries for day 1
    boundaries = game_engine._TEST_SESSION_BOUNDARIES  # [34, 55, 90, ...]

    failures = []
    for start_over in (0, 10, 35, 56):
        state = _make_state(fmt='Test', over_number=start_over, ball_in_over=0)
        result = game_engine.simulate_to('session', state)
        end_over = result['state']['over_number']
        ic = result['innings_complete']

        if ic:
            # Innings ended before session — acceptable
            continue

        # End over should be one of the session boundaries
        at_boundary = end_over in boundaries
        if not at_boundary:
            failures.append(
                f'start={start_over}: ended at over {end_over}, '
                f'not in boundaries {boundaries[:6]}'
            )

    _check('Test 3: simulate_to(session,Test) ends at session boundary',
           len(failures) == 0,
           '; '.join(failures[:2]))


# ── Test 4: simulate_to('match') on last innings returns completed match ───────

def test_4_match():
    """simulate_to('match') on T20 2nd innings returns match_complete=True with result_string."""
    import random
    random.seed(123)

    # Set up 2nd innings of a T20: chasing 150
    state = _make_state(
        fmt='T20',
        over_number=0,
        ball_in_over=0,
        total_runs=0,
        total_wickets=0,
        target=150,
        innings_number=2,
    )
    result = game_engine.simulate_to('match', state)
    mc = result['match_complete']
    rs = result['sim_digest']['result_string']
    ic = result['innings_complete']

    _check(
        'Test 4: simulate_to(match) returns match_complete+result_string',
        ic and mc and rs is not None,
        f'innings_complete={ic}, match_complete={mc}, result_string={rs!r}'
    )


# ── Test 5: sim_digest always has all required keys ───────────────────────────

def test_5_digest_keys():
    """sim_digest must contain all required keys for any target."""
    required = {'balls_bowled', 'runs_scored', 'wickets_fallen',
                'overs_completed', 'key_events'}
    import random
    random.seed(55)

    targets = ['wicket', 'over', 'session', 'innings', 'match']
    missing_report = []

    for t in targets:
        fmt  = 'Test' if t == 'session' else 'T20'
        inn_num = 1
        tgt  = None
        state = _make_state(fmt=fmt, innings_number=inn_num, target=tgt)
        result = game_engine.simulate_to(t, state)
        digest = result['sim_digest']
        missing = required - set(digest.keys())
        if missing:
            missing_report.append(f'{t}: missing {missing}')

    _check(
        'Test 5: sim_digest always contains all required keys',
        len(missing_report) == 0,
        '; '.join(missing_report)
    )


# ── Test 6: get_match_state simulation drift recovery ──────────────────────────

def test_6_simulation_drift():
    """Verify that get_match_state correctly recovers over/ball and striker state when simulation drift is present."""
    import sqlite3
    import database

    # Set up in-memory DB and run schema/migrations
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    with open('schema.sql') as f:
        conn.executescript(f.read())
    database.run_migrations(conn)

    # Seed minimal data
    venue_id = database.create_venue(conn, {'name': 'Test Venue', 'city': 'City', 'country': 'Country'})
    team1_id = database.create_team(conn, {'name': 'Team A', 'short_code': 'TMA', 'badge_colour': '#ff0000', 'home_venue_id': venue_id})
    team2_id = database.create_team(conn, {'name': 'Team B', 'short_code': 'TMB', 'badge_colour': '#0000ff', 'home_venue_id': venue_id})
    
    # Create two players for each team
    p1 = database.create_player(conn, {'team_id': team1_id, 'name': 'Batsman A1', 'batting_position': 1})
    p2 = database.create_player(conn, {'team_id': team1_id, 'name': 'Batsman A2', 'batting_position': 2})
    p3 = database.create_player(conn, {'team_id': team2_id, 'name': 'Bowler B1', 'batting_position': 1, 'bowling_type': 'pace', 'bowling_rating': 3})
    p4 = database.create_player(conn, {'team_id': team2_id, 'name': 'Bowler B2', 'batting_position': 2, 'bowling_type': 'pace', 'bowling_rating': 3})

    # Create a match and start innings
    match_id = database.create_match(conn, {
        'venue_id': venue_id,
        'format': 'T20',
        'match_date': '2024-01-01',
        'team1_id': team1_id,
        'team2_id': team2_id,
    })
    
    # Create innings
    innings_id = database.create_innings(conn, match_id, 1, team1_id, team2_id)
    
    # Create batter/bowler innings
    database.create_batter_innings(conn, innings_id, p1, 1)
    database.create_batter_innings(conn, innings_id, p2, 2)
    database.create_bowler_innings(conn, innings_id, p3)
    database.create_bowler_innings(conn, innings_id, p4)

    # Set innings and batters status to simulate active play
    conn.execute("UPDATE batter_innings SET status = 'batting' WHERE player_id IN (?, ?)", (p1, p2))
    
    # Now simulate drift by updating the innings overs completed without deliveries
    # Set to 12.4 overs completed
    database.update_innings(conn, innings_id, {'overs_completed': 12.4})
    
    # Retrieve match state
    state = database.get_match_state(conn, match_id)
    
    # Verify that the over/ball count reflects 12.4 overs completed (i.e. over 12, ball 4)
    # and striker/non-striker are recovered
    ok = (
        state['over_number'] == 12 and
        state['ball_in_over'] == 4 and
        state['current_striker_id'] == p1 and
        state['current_non_striker_id'] == p2
    )
    
    _check(
        'Test 6: get_match_state simulation drift recovery',
        ok,
        f"over={state['over_number']}, ball={state['ball_in_over']}, striker={state['current_striker_id']}"
    )


# ── Test 7: static data caching and invalidation ───────────────────────────────

def test_7_static_caching():
    """Verify that static data caches retrieve from memory correctly and invalidate on mutations."""
    import sqlite3
    import database

    # Set up in-memory DB and run schema/migrations
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    with open('schema.sql') as f:
        conn.executescript(f.read())
    database.run_migrations(conn)

    # Clean cache initially
    database.clear_static_caches()

    # Seed minimal data
    venue_id = database.create_venue(conn, {'name': 'Test Venue', 'city': 'City', 'country': 'Country'})
    team_id = database.create_team(conn, {'name': 'Team A', 'short_code': 'TMA', 'badge_colour': '#ff0000', 'home_venue_id': venue_id})
    player_id = database.create_player(conn, {'team_id': team_id, 'name': 'Player A1', 'batting_position': 1})

    # Retrieve and cache
    team_first = database.get_team(conn, team_id)
    player_first = database.get_player(conn, player_id)
    venue_first = database.get_venue(conn, venue_id)

    # Direct database updates (bypassing helpers, so caches are not invalidated)
    conn.execute("UPDATE teams SET name = 'Updated Team Name' WHERE id = ?", (team_id,))
    conn.execute("UPDATE players SET name = 'Updated Player Name' WHERE id = ?", (player_id,))
    conn.execute("UPDATE venues SET name = 'Updated Venue Name' WHERE id = ?", (venue_id,))
    conn.commit()

    # Retrieve again — should return the cached (original) values since we updated bypassing helpers
    team_second = database.get_team(conn, team_id)
    player_second = database.get_player(conn, player_id)
    venue_second = database.get_venue(conn, venue_id)

    cached_ok = (
        team_second['name'] == 'Team A' and
        player_second['name'] == 'Player A1' and
        venue_second['name'] == 'Test Venue'
    )

    # Invalidate cache via helpers
    database.update_team(conn, team_id, {'short_code': 'TMB'})

    # Retrieve again — should now retrieve the updated database values
    team_third = database.get_team(conn, team_id)
    player_third = database.get_player(conn, player_id)
    venue_third = database.get_venue(conn, venue_id)

    invalidated_ok = (
        team_third['name'] == 'Updated Team Name' and
        player_third['name'] == 'Updated Player Name' and
        venue_third['name'] == 'Updated Venue Name'
    )

    _check(
        'Test 7: static data caching and invalidation works',
        cached_ok and invalidated_ok,
        f"cached_ok={cached_ok}, invalidated_ok={invalidated_ok}"
    )


# ── Test 8: LRU cache eviction boundary ────────────────────────────────────────

def test_8_lru_cache_eviction():
    """Verify that LRUCache correctly evicts the least recently used item when maxsize is exceeded."""
    import database
    cache = database.LRUCache(maxsize=3)
    cache.set('a', 1)
    cache.set('b', 2)
    cache.set('c', 3)
    
    # Access 'a' to make it most recently used
    cache.get('a')
    
    # Add 'd' which should trigger eviction of 'b' (since 'b' is now LRU)
    cache.set('d', 4)
    
    evicted_ok = (cache.get('b') is database._MISSING)
    others_ok = (cache.get('a') == 1 and cache.get('c') == 3 and cache.get('d') == 4)
    
    _check(
        'Test 8: LRU cache eviction boundary',
        evicted_ok and others_ok,
        f"evicted_ok={evicted_ok}, others_ok={others_ok}"
    )


# ── Test 9: Global records caching and invalidation ──────────────────────────

def test_9_record_caching():
    """Verify that global records are cached and correctly invalidated upon updates."""
    import sqlite3
    import database

    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    with open('schema.sql') as f:
        conn.executescript(f.read())
    database.run_migrations(conn)

    database.clear_record_caches()

    # Query team record — should return None initially
    record_first = database.get_almanack_highest_team_score(conn, 'T20')
    
    # Insert team score directly in DB (bypass cache invalidation)
    venue_id = database.create_venue(conn, {'name': 'Venue', 'city': 'City', 'country': 'Country'})
    t1_id = database.create_team(conn, {'name': 'Team A', 'short_code': 'TMA', 'badge_colour': '#ff0000', 'home_venue_id': venue_id})
    t2_id = database.create_team(conn, {'name': 'Team B', 'short_code': 'TMB', 'badge_colour': '#0000ff', 'home_venue_id': venue_id})
    match_id = database.create_match(conn, {'venue_id': venue_id, 'format': 'T20', 'match_date': '2024-01-01', 'team1_id': t1_id, 'team2_id': t2_id})
    innings_id = database.create_innings(conn, match_id, 1, t1_id, t2_id)
    
    # Update innings totals and mark match complete
    conn.execute("UPDATE innings SET total_runs = 250, total_wickets = 3 WHERE id = ?", (innings_id,))
    conn.execute("UPDATE matches SET status = 'complete' WHERE id = ?", (match_id,))
    conn.commit()
    
    # Query again — should still return None because cache was not invalidated (updated bypass)
    record_second = database.get_almanack_highest_team_score(conn, 'T20')
    
    # Clear cache
    database.clear_record_caches()
    
    # Query again — should now return the fresh value
    record_third = database.get_almanack_highest_team_score(conn, 'T20')
    
    cached_ok = (record_first is None and record_second is None)
    invalidated_ok = (record_third is not None and record_third['total_runs'] == 250)
    
    _check(
        'Test 9: Global records caching and invalidation',
        cached_ok and invalidated_ok,
        f"cached_ok={cached_ok}, invalidated_ok={invalidated_ok}"
    )


# ── Run all tests ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_1_wicket()
    test_2_over()
    test_3_session()
    test_4_match()
    test_5_digest_keys()
    test_6_simulation_drift()
    test_7_static_caching()
    test_8_lru_cache_eviction()
    test_9_record_caching()

    print()
    print(f'Results: {_passed} passed, {_failed} failed')
    if _failed == 0:
        print('All tests PASSED')
    else:
        print(f'{_failed} test(s) FAILED')
        sys.exit(1)
