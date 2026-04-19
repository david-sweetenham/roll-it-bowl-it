"""
hundred_engine.py — The Hundred format engine for Roll It & Bowl It.
100-ball cricket. Distinct rules from T20/ODI/Test.
Imports game_engine for bowl_ball() and commentary only.

"The Hundred" is a registered trademark of the England and Wales Cricket Board (ECB).
The team names Birmingham Phoenix, London Spirit, Manchester Super Giants, MI London,
Southern Brave, Sunrisers Leeds, Trent Rockets, and Welsh Fire are trademarks of their
respective owners. This implementation is an independent fan recreation for personal
entertainment and is not affiliated with, endorsed by, or connected to the ECB.
"""

import random
from game_engine import bowl_ball, COMMENTARY

# ── Constants ─────────────────────────────────────────────────────────────────

HUNDRED_BALLS     = 100   # balls per innings
HUNDRED_SET_SIZE  = 5     # balls per set
HUNDRED_MAX_SETS  = 2     # consecutive sets from same end before mandatory end change
HUNDRED_BOWLER_MAX = 20   # max balls per bowler per innings
HUNDRED_POWERPLAY  = 25   # powerplay lasts first 25 balls
HUNDRED_DEATH_START = 76  # death overs start at ball 76 (last 25 balls)
HUNDRED_NO_BALL_RUNS = 2  # no ball penalty (not 1)


# ── Ball Delivery ─────────────────────────────────────────────────────────────

def bowl_hundred_ball(batter_rating, bowler_rating, bowling_type,
                      is_free_hit=False, balls_faced=0,
                      is_powerplay=False) -> dict:
    """
    Wrapper around bowl_ball() with Hundred-specific adjustments:
    - No ball penalty = 2 runs (not 1)
    - Minor powerplay boundary boost
    """
    result = bowl_ball(
        batter_rating, bowler_rating, bowling_type,
        is_free_hit, balls_faced,
        scoring_mode='modern', format='T20'
    )

    # The Hundred: no ball penalty is 2 runs
    if result['extras_type'] == 'no_ball':
        result['extras_runs'] = HUNDRED_NO_BALL_RUNS

    # Powerplay minor boundary boost: 15% chance two becomes four
    if is_powerplay and result['outcome_type'] == 'two':
        if random.random() < 0.15:
            result['outcome_type'] = 'four'
            result['runs'] = 4
            result['commentary_key'] = 'four'

    return result


# ── Bowler Selection ──────────────────────────────────────────────────────────

def select_hundred_bowler(bowlers, last_bowler_id, current_end,
                          sets_from_current_end) -> dict:
    """
    Select the next bowler for a Hundred set.

    Returns {player_id, must_change_end, suggested_end, balls_remaining_for_bowler}.

    Rules:
    - A bowler cannot bowl more than 20 balls total
    - Same bowler CAN bowl consecutive sets (unlike T20 same-bowler restriction)
    - After HUNDRED_MAX_SETS consecutive sets from same end, must change end
    - Captain can voluntarily switch end after just 1 set
    """
    must_change_end = sets_from_current_end > HUNDRED_MAX_SETS
    new_end = 'nursery' if current_end == 'pavilion' else 'pavilion'

    def eligible(b):
        return b['balls_bowled'] < HUNDRED_BOWLER_MAX

    candidates = [b for b in bowlers if eligible(b)]

    if not candidates:
        # All bowlers maxed — allow anyone (edge case, shouldn't happen in practice)
        candidates = list(bowlers)

    # Sort: highest rating first, then fewest balls bowled (freshest best bowler)
    candidates.sort(key=lambda b: (-b['bowling_rating'], b['balls_bowled']))
    chosen = candidates[0]

    return {
        'player_id': chosen['player_id'],
        'must_change_end': must_change_end,
        'suggested_end': new_end if must_change_end else current_end,
        'balls_remaining_for_bowler': HUNDRED_BOWLER_MAX - chosen['balls_bowled'],
    }


# ── Innings Simulation ────────────────────────────────────────────────────────

def simulate_hundred_innings_fast(batting_players, bowling_players,
                                  target=None) -> dict:
    """
    Simulate a complete Hundred innings.

    Key differences from simulate_innings_fast():
    - 100 legal balls total (not overs)
    - 5-ball sets; bowler selected per set, not per over
    - Batters do NOT change ends at end of a set
    - Mandatory end change after 2 consecutive sets from same end
    - Powerplay: first 25 balls (max 2 fielders outside ring)
    - Strategic timeout: AI uses at ball 50 if losing
    - No ball = 2 runs
    """

    # ── State ──
    total_runs      = 0
    total_wickets   = 0
    total_balls     = 0   # legal deliveries only (counts toward 100)
    is_free_hit     = False

    # Set / end tracking
    current_set_ball      = 0   # 0–4 within current set
    current_set_number    = 1   # 1-based set counter (up to 20)
    sets_from_current_end = 1   # reset to 1 each time end changes
    current_end           = 'pavilion'

    # Phase accumulators
    powerplay_runs     = 0
    powerplay_wickets  = 0
    death_runs         = 0
    death_wickets      = 0

    # Strategic timeout
    strategic_timeout_used    = False
    strategic_timeout_at_ball = None

    # Batter setup
    striker_idx     = 0
    non_striker_idx = 1
    next_batter_idx = 2

    batter_scores = []
    for i, p in enumerate(batting_players):
        batter_scores.append({
            'player_id': p['player_id'],
            'runs':  0,
            'balls': 0,
            'fours': 0,
            'sixes': 0,
            'dismissal_type': None,
            'not_out': True,
            'batting': i < 2,
        })

    # Bowler setup (track balls, not overs)
    bowler_map = {}
    for b in bowling_players:
        bowler_map[b['player_id']] = {
            'player_id':     b['player_id'],
            'bowling_type':  b.get('bowling_type', 'pace'),
            'bowling_rating': b.get('bowling_rating', 3),
            'balls_bowled':  0,
            'runs':          0,
            'wickets':       0,
        }

    fall_of_wickets = []
    extras = {'wides': 0, 'no_balls': 0, 'byes': 0, 'leg_byes': 0, 'total': 0}
    deliveries = []

    # Set-by-set tracking
    balls_per_set    = []
    current_set_runs = 0

    # ── Pick initial bowler ──
    last_bowler_id    = None
    current_bowler_id = None

    def _pick_bowler():
        nonlocal current_bowler_id, last_bowler_id
        sel = select_hundred_bowler(
            list(bowler_map.values()),
            last_bowler_id,
            current_end,
            sets_from_current_end,
        )
        current_bowler_id = sel['player_id']

    _pick_bowler()

    # ── Main innings loop ──
    while total_wickets < 10 and total_balls < HUNDRED_BALLS:

        # Target achieved (run chase)?
        if target is not None and total_runs >= target:
            break

        # AI strategic timeout at ball 50 if behind in chase
        if (not strategic_timeout_used and total_balls == 50
                and target is not None and total_runs < target // 2):
            strategic_timeout_used    = True
            strategic_timeout_at_ball = 50

        is_powerplay = total_balls < HUNDRED_POWERPLAY

        striker = batter_scores[striker_idx]
        bowler  = bowler_map[current_bowler_id]

        batter_rating = batting_players[striker_idx].get('batting_rating', 3)
        bowler_rating = bowler['bowling_rating']
        bowling_type  = bowler['bowling_type']

        ball_result = bowl_hundred_ball(
            batter_rating, bowler_rating, bowling_type,
            is_free_hit, striker['balls'],
            is_powerplay=is_powerplay,
        )
        deliveries.append(ball_result)

        is_free_hit = ball_result['next_is_free_hit']
        is_legal    = ball_result['outcome_type'] not in ('wide', 'no_ball')

        runs_scored   = ball_result['runs']
        extras_scored = ball_result['extras_runs']
        total_runs   += runs_scored + extras_scored
        current_set_runs += runs_scored + extras_scored

        bowler['runs'] += runs_scored + extras_scored

        # Tally extras
        if ball_result['outcome_type'] == 'wide':
            extras['wides']    += extras_scored
            extras['total']    += extras_scored
        elif ball_result['outcome_type'] == 'no_ball':
            extras['no_balls'] += extras_scored
            extras['total']    += extras_scored
        elif ball_result['extras_type'] == 'bye':
            extras['byes']     += extras_scored
            extras['total']    += extras_scored
        elif ball_result['extras_type'] == 'leg_bye':
            extras['leg_byes'] += extras_scored
            extras['total']    += extras_scored

        if ball_result['outcome_type'] == 'wicket':
            striker['dismissal_type'] = ball_result['dismissal_type']
            striker['not_out']        = False
            bowler['wickets']        += 1
            total_wickets            += 1

            if is_powerplay:
                powerplay_wickets += 1
            elif total_balls >= HUNDRED_DEATH_START - 1:
                death_wickets += 1

            fall_of_wickets.append({
                'wicket':    total_wickets,
                'score':     total_runs,
                'balls':     total_balls,
                'player_id': striker['player_id'],
            })

            if next_batter_idx < len(batter_scores):
                batter_scores[next_batter_idx]['batting'] = True
                striker_idx     = next_batter_idx
                next_batter_idx += 1
            else:
                break

        else:
            if is_legal:
                striker['balls'] += 1
                striker['runs']  += runs_scored
                if ball_result['outcome_type'] == 'four':
                    striker['fours'] += 1
                elif ball_result['outcome_type'] == 'six':
                    striker['sixes'] += 1

            # Strike rotation on odd runs within a set (NOT at end of set)
            if is_legal and runs_scored % 2 == 1:
                striker_idx, non_striker_idx = non_striker_idx, striker_idx

        if is_legal:
            # Phase run accumulation
            if is_powerplay:
                powerplay_runs += runs_scored + extras_scored
            elif total_balls >= HUNDRED_DEATH_START - 1:
                death_runs += runs_scored + extras_scored

            bowler['balls_bowled'] += 1
            total_balls            += 1
            current_set_ball       += 1

            # End of set (every 5 legal balls)
            if current_set_ball == HUNDRED_SET_SIZE:
                balls_per_set.append(current_set_runs)
                current_set_runs  = 0
                current_set_ball  = 0
                last_bowler_id    = current_bowler_id

                # Determine end logic
                sets_from_current_end += 1
                if sets_from_current_end > HUNDRED_MAX_SETS:
                    # Mandatory end change
                    current_end           = 'nursery' if current_end == 'pavilion' else 'pavilion'
                    sets_from_current_end = 1

                # NOTE: batters do NOT change ends at end of set
                current_set_number += 1

                if total_balls < HUNDRED_BALLS:
                    _pick_bowler()

    # Handle partial final set
    if current_set_ball > 0:
        balls_per_set.append(current_set_runs)

    # ── Build result ──
    active_batter_scores = [b for b in batter_scores if b['batting']]
    clean_batter_scores  = [
        {
            'player_id':      b['player_id'],
            'runs':           b['runs'],
            'balls':          b['balls'],
            'fours':          b['fours'],
            'sixes':          b['sixes'],
            'dismissal_type': b['dismissal_type'],
            'not_out':        b['not_out'],
        }
        for b in active_batter_scores
    ]

    bowler_figures = []
    for b in bowler_map.values():
        if b['balls_bowled'] > 0:
            bowler_figures.append({
                'player_id': b['player_id'],
                'balls':     b['balls_bowled'],
                'sets':      b['balls_bowled'] // HUNDRED_SET_SIZE,
                'runs':      b['runs'],
                'wickets':   b['wickets'],
            })

    return {
        'total_runs':              total_runs,
        'total_wickets':           total_wickets,
        'total_balls_bowled':      total_balls,
        'batter_scores':           clean_batter_scores,
        'bowler_figures':          bowler_figures,
        'fall_of_wickets':         fall_of_wickets,
        'extras':                  extras,
        'deliveries':              deliveries,
        'balls_per_set':           balls_per_set,
        'powerplay_score':         powerplay_runs,
        'powerplay_wickets':       powerplay_wickets,
        'death_score':             death_runs,
        'death_wickets':           death_wickets,
        'strategic_timeout_used':  strategic_timeout_used,
        'strategic_timeout_at_ball': strategic_timeout_at_ball,
    }


# ── Result Calculation ────────────────────────────────────────────────────────

def calculate_hundred_result(innings1_runs, innings1_wickets,
                              innings2_runs, innings2_wickets,
                              balls_used) -> dict:
    """
    No draw possible in The Hundred. Win by runs or win by wickets only.
    """
    target = innings1_runs + 1
    result = {
        'result_type':    None,
        'winning_team':   None,
        'margin_runs':    None,
        'margin_wickets': None,
        'description':    '',
    }

    if innings2_runs >= target:
        wickets_remaining    = 10 - innings2_wickets
        result['result_type']    = 'wickets'
        result['winning_team']   = 2
        result['margin_wickets'] = wickets_remaining
        result['description']    = (
            f'Team 2 won by {wickets_remaining} wicket{"s" if wickets_remaining != 1 else ""}'
        )
    elif innings2_runs == innings1_runs:
        result['result_type']  = 'tie'
        result['description']  = 'Match tied'
    else:
        margin                = innings1_runs - innings2_runs
        result['result_type'] = 'runs'
        result['winning_team'] = 1
        result['margin_runs']  = margin
        result['description']  = (
            f'Team 1 won by {margin} run{"s" if margin != 1 else ""}'
        )

    return result


# ── Display Helpers ───────────────────────────────────────────────────────────

def format_hundred_progress(balls_bowled: int) -> str:
    """'37 balls remaining' or '100 balls bowled'."""
    remaining = HUNDRED_BALLS - balls_bowled
    if remaining <= 0:
        return '100 balls bowled'
    return f'{remaining} ball{"s" if remaining != 1 else ""} remaining'


def render_hundred_progress_bar(balls_bowled: int) -> str:
    """
    20 dots representing 20 sets of 5. Returns ASCII progress bar.
    Completed sets: ●  Partial set: ◐  Remaining: ○
    """
    sets_complete = balls_bowled // HUNDRED_SET_SIZE
    has_partial   = (balls_bowled % HUNDRED_SET_SIZE) > 0
    bar = ''
    for i in range(20):
        if i < sets_complete:
            bar += '●'
        elif i == sets_complete and has_partial:
            bar += '◐'
        else:
            bar += '○'
    return bar
