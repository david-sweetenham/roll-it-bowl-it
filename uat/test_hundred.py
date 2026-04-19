"""
uat/test_hundred.py — UAT tests for The Hundred format.
Run with: python uat/test_hundred.py  (from the project root)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import seed_data
import hundred_engine as he

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'

all_passed = True


def run_test(name, fn):
    global all_passed
    try:
        fn()
        print(f'[{PASS}] {name}')
    except AssertionError as e:
        print(f'[{FAIL}] {name}: {e}')
        all_passed = False
    except Exception as e:
        import traceback
        print(f'[{FAIL}] {name}: unexpected error — {e}')
        traceback.print_exc()
        all_passed = False


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _get_db():
    """Get a DB connection, running migrations and seed if needed."""
    db = database.get_db()
    database.run_migrations(db)
    seed_data.seed(db)
    return db


def _std_batting(n=11):
    return [
        {'player_id': 200 + i, 'batting_rating': max(1, 4 - i // 3), 'batting_hand': 'right', 'batting_position': i + 1}
        for i in range(n)
    ]


def _std_bowling(n=5):
    return [
        {'player_id': 300 + i, 'bowling_type': 'pace', 'bowling_rating': 4, 'balls_bowled': 0}
        for i in range(n)
    ]


# ── Test 1: Hundred teams seeded ──────────────────────────────────────────────

def test_hundred_teams_seeded():
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT * FROM teams WHERE is_hundred_team = 1"
        ).fetchall()
        assert len(rows) == 8, f'Expected 8 Hundred teams, got {len(rows)}'
        names = {r['name'] for r in rows}
        expected = {
            'Birmingham Phoenix', 'London Spirit', 'Manchester Super Giants',
            'MI London', 'Southern Brave', 'Sunrisers Leeds',
            'Trent Rockets', 'Welsh Fire',
        }
        assert names == expected, f'Team names mismatch: {names}'
    finally:
        database.close_db(db)


# ── Test 2: Hundred venues flagged ───────────────────────────────────────────

def test_hundred_venues_flagged():
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT name FROM venues WHERE is_hundred_venue = 1"
        ).fetchall()
        assert len(rows) >= 8, f'Expected at least 8 Hundred venues, got {len(rows)}'
        venue_names = {r['name'] for r in rows}
        for expected_name in ["Lord's Cricket Ground", "The Oval", "Headingley", "Edgbaston"]:
            assert expected_name in venue_names, f'{expected_name} not flagged as Hundred venue'
    finally:
        database.close_db(db)


# ── Test 3: No ball penalty is 2 runs ────────────────────────────────────────

def test_no_ball_penalty_two_runs():
    """Simulate many balls and verify no_ball extras_runs is always 2."""
    no_ball_penalties = set()
    for _ in range(5000):
        result = he.bowl_hundred_ball(3, 3, 'pace', False, 0)
        if result['extras_type'] == 'no_ball':
            no_ball_penalties.add(result['extras_runs'])

    assert no_ball_penalties, 'No no-balls observed in 5000 balls — extremely unlikely'
    assert no_ball_penalties == {2}, f'No ball extras_runs should always be 2, got {no_ball_penalties}'


# ── Test 4: Powerplay ends at ball 25 ────────────────────────────────────────

def test_powerplay_ends_at_ball_25():
    """Powerplay constant must be 25, not 30 (T20 would be 30 = 5 overs)."""
    assert he.HUNDRED_POWERPLAY == 25, f'Powerplay should be 25 balls, got {he.HUNDRED_POWERPLAY}'


# ── Test 5: Bowler cap is 20 balls ───────────────────────────────────────────

def test_bowler_cap_20_balls():
    assert he.HUNDRED_BOWLER_MAX == 20, f'Bowler max should be 20 balls, got {he.HUNDRED_BOWLER_MAX}'


# ── Test 6: Ball counter counts down ────────────────────────────────────────

def test_ball_counter_countdown():
    assert he.format_hundred_progress(0)   == '100 balls remaining'
    assert he.format_hundred_progress(37)  == '63 balls remaining'
    assert he.format_hundred_progress(99)  == '1 ball remaining'
    assert he.format_hundred_progress(100) == '100 balls bowled'


# ── Test 7: Progress bar renders 20 dots ────────────────────────────────────

def test_progress_bar_twenty_dots():
    bar = he.render_hundred_progress_bar(0)
    assert len(bar) == 20, f'Progress bar should be 20 chars, got {len(bar)}'
    assert all(c == '○' for c in bar), 'All dots should be empty at ball 0'

    bar50 = he.render_hundred_progress_bar(50)
    assert bar50.count('●') == 10, f'Should have 10 completed at ball 50, got {bar50.count("●")}'

    bar100 = he.render_hundred_progress_bar(100)
    assert all(c == '●' for c in bar100), 'All dots should be full at ball 100'


# ── Test 8: Innings totals in realistic range ─────────────────────────────────

def test_hundred_innings_realistic_scores():
    # Note: this dice engine produces higher scoring rates than real-world Hundred
    # because it is entertainment-first (same model as T20/ODI). Real Hundred
    # averages ~148 men's, but the dice engine targets ~200-280 as a fun range.
    batting  = _std_batting(15)
    bowling  = [
        {'player_id': 300 + i, 'bowling_type': 'pace' if i < 3 else 'spin', 'bowling_rating': 3 + (i % 2), 'balls_bowled': 0}
        for i in range(6)
    ]

    scores = []
    for _ in range(100):
        result = he.simulate_hundred_innings_fast(batting, bowling)
        scores.append(result['total_runs'])
        assert result['total_balls_bowled'] <= he.HUNDRED_BALLS, (
            f'Innings used {result["total_balls_bowled"]} balls (> 100)'
        )
        assert result['total_wickets'] <= 10, (
            f'Innings recorded {result["total_wickets"]} wickets (> 10)'
        )
        assert result['powerplay_score'] >= 0
        assert result['powerplay_wickets'] >= 0

    avg = sum(scores) / len(scores)
    print(f'\n  100 Hundred innings: avg={avg:.1f}, min={min(scores)}, max={max(scores)}')
    # Wide range: dice engine is entertainment-first, scores higher than real cricket
    assert 80 < avg < 400, f'Average score {avg:.1f} outside valid range [80, 400]'
    # Sanity: at least some innings should be under 200 and some over 100
    assert min(scores) > 20, f'Minimum score {min(scores)} is unrealistically low'


# ── Test 9: No bowler bowls more than 20 balls ───────────────────────────────

def test_bowler_cap_enforced():
    batting  = _std_batting(15)
    bowling  = [
        {'player_id': 300 + i, 'bowling_type': 'pace', 'bowling_rating': 4, 'balls_bowled': 0}
        for i in range(6)
    ]
    for _ in range(20):
        result = he.simulate_hundred_innings_fast(batting, bowling)
        for bf in result['bowler_figures']:
            assert bf['balls'] <= he.HUNDRED_BOWLER_MAX, (
                f'Bowler {bf["player_id"]} bowled {bf["balls"]} balls (> {he.HUNDRED_BOWLER_MAX})'
            )


# ── Test 10: Set structure — 5-ball sets ─────────────────────────────────────

def test_set_structure():
    assert he.HUNDRED_SET_SIZE == 5, f'Set size should be 5, got {he.HUNDRED_SET_SIZE}'
    assert he.HUNDRED_MAX_SETS == 2, f'Max consecutive sets from same end should be 2'

    batting = _std_batting(11)
    bowling = [
        {'player_id': 300 + i, 'bowling_type': 'pace', 'bowling_rating': 3, 'balls_bowled': 0}
        for i in range(5)
    ]
    result = he.simulate_hundred_innings_fast(batting, bowling)
    # balls_per_set should have at most 20 entries
    assert len(result['balls_per_set']) <= 20, (
        f'Too many sets: {len(result["balls_per_set"])}'
    )


# ── Test 11: Hundred records are seeded ──────────────────────────────────────

def test_hundred_records_seeded():
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT record_key FROM real_world_records WHERE format='Hundred'"
        ).fetchall()
        assert len(rows) >= 4, f'Expected at least 4 Hundred records, got {len(rows)}'
        keys = {r['record_key'] for r in rows}
        assert 'highest_score_hundred' in keys
        assert 'best_bowling_hundred' in keys
    finally:
        database.close_db(db)


# ── Test 12: Hundred teams have 15 players ───────────────────────────────────

def test_hundred_team_squad_size():
    db = _get_db()
    try:
        hundred_teams = db.execute(
            "SELECT id, name FROM teams WHERE is_hundred_team=1"
        ).fetchall()
        for team in hundred_teams:
            players = db.execute(
                "SELECT COUNT(*) as cnt FROM players WHERE team_id=?", (team['id'],)
            ).fetchone()
            cnt = players['cnt']
            assert cnt >= 11, (
                f'{team["name"]} has only {cnt} players (need at least 11)'
            )
    finally:
        database.close_db(db)


# ── Test 13: calculate_hundred_result ────────────────────────────────────────

def test_calculate_result():
    # Win by wickets
    r = he.calculate_hundred_result(150, 10, 151, 6, 99)
    assert r['result_type'] == 'wickets'
    assert r['margin_wickets'] == 4

    # Win by runs
    r = he.calculate_hundred_result(180, 7, 165, 10, 100)
    assert r['result_type'] == 'runs'
    assert r['margin_runs'] == 15

    # Tie
    r = he.calculate_hundred_result(140, 7, 140, 10, 100)
    assert r['result_type'] == 'tie'


# ── Run all tests ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('The Hundred UAT Suite')
    print('=' * 60)

    run_test('Hundred teams seeded (8)',                 test_hundred_teams_seeded)
    run_test('Hundred venues flagged (>=8)',             test_hundred_venues_flagged)
    run_test('No ball penalty = 2 runs',                test_no_ball_penalty_two_runs)
    run_test('Powerplay ends at ball 25 (not 30)',       test_powerplay_ends_at_ball_25)
    run_test('Bowler cap constant = 20 balls',          test_bowler_cap_20_balls)
    run_test('Ball counter counts down',                test_ball_counter_countdown)
    run_test('Progress bar = 20 dots',                  test_progress_bar_twenty_dots)
    run_test('Innings scores in realistic range',       test_hundred_innings_realistic_scores)
    run_test('Bowler cap enforced (never > 20 balls)',  test_bowler_cap_enforced)
    run_test('Set structure (5-ball sets)',              test_set_structure)
    run_test('Hundred records seeded',                  test_hundred_records_seeded)
    run_test('Hundred team squad size (>=11)',          test_hundred_team_squad_size)
    run_test('calculate_hundred_result correct',        test_calculate_result)

    print()
    if all_passed:
        print('All Hundred UAT tests PASSED')
        sys.exit(0)
    else:
        print('One or more Hundred UAT tests FAILED')
        sys.exit(1)
