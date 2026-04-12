"""
test_engine.py — Tests for game_engine.py
Run with: python test_engine.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import game_engine as ge

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'

REQUIRED_KEYS = {
    'stage1', 'stage2', 'stage3', 'stage4', 'stage4b',
    'outcome_type', 'runs', 'extras_type', 'extras_runs',
    'dismissal_type', 'caught_type', 'shot_angle',
    'is_free_hit', 'next_is_free_hit', 'commentary_key',
}

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
        print(f'[{FAIL}] {name}: unexpected error — {e}')
        all_passed = False


# ── Test 1: Outcome frequency distribution ────────────────────────────────────

def test_outcome_frequency():
    n = 10_000
    counts = {}
    for _ in range(n):
        r = ge.bowl_ball(3, 3, 'pace', False, 0)
        ot = r['outcome_type']
        counts[ot] = counts.get(ot, 0) + 1

    total = sum(counts.values())
    pct = {k: v / total * 100 for k, v in counts.items()}

    print('\n  Outcome distribution (n=10,000):')
    for k, v in sorted(pct.items(), key=lambda x: -x[1]):
        print(f'    {k:20s} {v:5.1f}%  ({counts.get(k, 0)})')

    wicket_pct = pct.get('wicket', 0)
    dot_pct = pct.get('dot', 0)
    four_pct = pct.get('four', 0)
    six_pct = pct.get('six', 0)
    extras_pct = pct.get('wide', 0) + pct.get('no_ball', 0)

    three_pct = pct.get('three', 0)

    assert 5 <= wicket_pct <= 15, f'Wicket rate {wicket_pct:.1f}% not in [5%, 15%]'
    assert 1 <= dot_pct <= 8, f'Dot rate {dot_pct:.1f}% not in [1%, 8%]'
    assert 10 <= three_pct <= 20, f'Three rate {three_pct:.1f}% not in [10%, 20%]'
    assert 10 <= four_pct <= 20, f'Four rate {four_pct:.1f}% not in [10%, 20%]'
    assert 10 <= six_pct <= 20, f'Six rate {six_pct:.1f}% not in [10%, 20%]'
    assert extras_pct < 15, f'Extras rate {extras_pct:.1f}% >= 15%'


# ── Test 2: Batter rating effect ──────────────────────────────────────────────

def test_batter_rating():
    n = 5_000
    wicket_rates = {}

    print('\n  Wicket rates by batter_rating (n=5,000 each):')
    for rating in range(1, 6):
        wickets = sum(
            1 for _ in range(n)
            if ge.bowl_ball(rating, 3, 'pace', False, 0)['outcome_type'] == 'wicket'
        )
        rate = wickets / n * 100
        wicket_rates[rating] = rate
        print(f'    Rating {rating}: {rate:.1f}%')

    assert wicket_rates[5] < wicket_rates[1], (
        f'Rating 5 wicket rate ({wicket_rates[5]:.1f}%) not lower than '
        f'rating 1 ({wicket_rates[1]:.1f}%)'
    )
    assert wicket_rates[5] < 6, f'Rating 5 wicket rate {wicket_rates[5]:.1f}% not < 6%'
    assert wicket_rates[1] > 10, f'Rating 1 wicket rate {wicket_rates[1]:.1f}% not > 10%'


# ── Test 3: Fast sim scorecard ────────────────────────────────────────────────

def test_fast_sim():
    batting = [
        {'player_id': 101, 'batting_rating': 5, 'batting_hand': 'right', 'batting_position': 1},
        {'player_id': 102, 'batting_rating': 4, 'batting_hand': 'right', 'batting_position': 2},
        {'player_id': 103, 'batting_rating': 5, 'batting_hand': 'right', 'batting_position': 3},
        {'player_id': 104, 'batting_rating': 4, 'batting_hand': 'right', 'batting_position': 4},
        {'player_id': 105, 'batting_rating': 3, 'batting_hand': 'right', 'batting_position': 5},
        {'player_id': 106, 'batting_rating': 3, 'batting_hand': 'right', 'batting_position': 6},
        {'player_id': 107, 'batting_rating': 3, 'batting_hand': 'right', 'batting_position': 7},
        {'player_id': 108, 'batting_rating': 2, 'batting_hand': 'right', 'batting_position': 8},
        {'player_id': 109, 'batting_rating': 2, 'batting_hand': 'right', 'batting_position': 9},
        {'player_id': 110, 'batting_rating': 1, 'batting_hand': 'right', 'batting_position': 10},
        {'player_id': 111, 'batting_rating': 1, 'batting_hand': 'right', 'batting_position': 11},
    ]

    bowling = [
        {'player_id': 201, 'bowling_type': 'pace', 'bowling_rating': 5},
        {'player_id': 202, 'bowling_type': 'pace', 'bowling_rating': 4},
        {'player_id': 203, 'bowling_type': 'spin', 'bowling_rating': 4},
        {'player_id': 204, 'bowling_type': 'pace', 'bowling_rating': 3},
        {'player_id': 205, 'bowling_type': 'spin', 'bowling_rating': 3},
    ]

    result = ge.simulate_innings_fast(batting, bowling, 'T20')

    print(f'\n  T20 Innings: {result["total_runs"]}/{result["total_wickets"]} '
          f'in {result["overs_completed"]} overs')
    print(f'  Extras: {result["extras"]}')
    print(f'  Batters who scored:')
    for b in result['batter_scores']:
        not_out_str = '*' if b['not_out'] else ''
        print(f'    Player {b["player_id"]}: {b["runs"]}{not_out_str} '
              f'({b["balls"]} balls, {b["fours"]}x4, {b["sixes"]}x6) '
              f'dismissal={b["dismissal_type"]}')
    print(f'  Bowlers:')
    for b in result['bowler_figures']:
        balls_in_over = b['balls']
        overs_str = f"{b['overs']}.{balls_in_over}"
        print(f'    Player {b["player_id"]}: {overs_str} overs, '
              f'{b["runs"]} runs, {b["wickets"]}W, {b["maidens"]} maidens')

    assert result['total_wickets'] <= 10, f'Wickets {result["total_wickets"]} > 10'
    assert result['overs_completed'] <= 20.0, f'Overs {result["overs_completed"]} > 20'

    required_keys = {'player_id', 'runs', 'balls', 'fours', 'sixes', 'dismissal_type', 'not_out'}
    for b in result['batter_scores']:
        missing = required_keys - set(b.keys())
        assert not missing, f'Batter score missing keys: {missing}'

    assert 'total_runs' in result
    assert 'total_wickets' in result
    assert 'overs_completed' in result
    assert 'batter_scores' in result
    assert 'bowler_figures' in result
    assert 'fall_of_wickets' in result
    assert 'extras' in result
    assert 'deliveries' in result


# ── Test 4: Commentary recency buffer ────────────────────────────────────────

def test_commentary_buffer():
    buffer = []
    outputs = []
    for _ in range(20):
        line = ge.generate_commentary('dot', {}, buffer)
        outputs.append(line)

    # Check no template repeats within any 5 consecutive calls
    for i in range(len(outputs) - 4):
        window = outputs[i:i + 5]
        assert len(set(window)) == len(window), (
            f'Repeated commentary within 5 consecutive calls at position {i}: {window}'
        )

    print(f'\n  Sample commentary lines:')
    for line in outputs[:5]:
        print(f'    "{line}"')


# ── Test 5: Dict completeness and shot_angle rules ────────────────────────────

def test_dict_completeness():
    n = 100
    fails = []

    for i in range(n):
        r = ge.bowl_ball(3, 3, 'pace', False, 0)

        missing = REQUIRED_KEYS - set(r.keys())
        if missing:
            fails.append(f'Call {i}: missing keys {missing}')

        if r.get('dismissal_type') in ('bowled', 'lbw'):
            if r.get('shot_angle') is not None:
                fails.append(f'Call {i}: shot_angle should be None for {r["dismissal_type"]}')

    assert not fails, '\n  ' + '\n  '.join(fails[:5])


# ── Run all tests ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('=' * 60)
    print('game_engine.py test suite')
    print('=' * 60)

    run_test('Test 1 — Outcome frequency distribution', test_outcome_frequency)
    run_test('Test 2 — Batter rating effect', test_batter_rating)
    run_test('Test 3 — Fast sim scorecard', test_fast_sim)
    run_test('Test 4 — Commentary recency buffer', test_commentary_buffer)
    run_test('Test 5 — Dict completeness', test_dict_completeness)

    print()
    print('=' * 60)
    if all_passed:
        print('All tests PASSED.')
    else:
        print('Some tests FAILED — see above.')
        sys.exit(1)
