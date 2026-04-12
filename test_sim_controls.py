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


# ── Run all tests ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_1_wicket()
    test_2_over()
    test_3_session()
    test_4_match()
    test_5_digest_keys()

    print()
    print(f'Results: {_passed} passed, {_failed} failed')
    if _failed == 0:
        print('All tests PASSED')
    else:
        print(f'{_failed} test(s) FAILED')
        sys.exit(1)
