"""
match_service.py — Domain service layer for Roll It & Bowl It.
Handles match simulation, game loop orchestration, and helper calculations.
No Flask dependencies. Accepts a database connection/cursor.
"""

import random
import sqlite3
import database
import game_engine
import hundred_engine

def _players_for_match_team(db, match_id, team_id):
    match = database.get_match(db, match_id)
    world_id = match.get('world_id') if match else None
    players = database.get_players_for_team(db, team_id, world_id=world_id) if world_id else database.get_players_for_team(db, team_id)
    if world_id:
        states = database.get_player_world_states(db, world_id)
        players = [p for p in players if int((states.get(p['id']) or {}).get('active', 1) or 0) == 1]
    return sorted(players, key=lambda p: (p.get('batting_position') or 99, p.get('id') or 0))


def _start_innings(db, match_id, innings_number, batting_team_id, bowling_team_id):
    """Create innings, batter/bowler rows, and opening partnership."""
    innings_id = database.create_innings(db, match_id, innings_number,
                                         batting_team_id, bowling_team_id)
    batting_players = _players_for_match_team(db, match_id, batting_team_id)
    for p in batting_players:
        database.create_batter_innings(db, innings_id, p['id'], p['batting_position'])

    # First two batters are 'batting'
    for p in batting_players[:2]:
        row = db.execute(
            "SELECT id FROM batter_innings WHERE innings_id=? AND player_id=?",
            (innings_id, p['id'])
        ).fetchone()
        if row:
            database.update_batter_innings(db, row['id'], {'status': 'batting'})

    # Bowler innings for every player who can bowl
    for p in _players_for_match_team(db, match_id, bowling_team_id):
        if p['bowling_type'] != 'none':
            database.create_bowler_innings(db, innings_id, p['id'])

    # Opening partnership
    if len(batting_players) >= 2:
        database.create_partnership(
            db, innings_id, 0,
            batting_players[0]['id'], batting_players[1]['id']
        )
    return innings_id


def _apply_innings_cutoff_snapshots(existing_innings, innings_update):
    existing = existing_innings or {}
    updated = dict(innings_update or {})
    overs = updated.get('overs_completed')
    if overs is None:
        overs = existing.get('overs_completed')
    if overs is None:
        return updated

    current_runs = updated.get('total_runs', existing.get('total_runs'))
    current_wickets = updated.get('total_wickets', existing.get('total_wickets'))
    if overs >= 100 and existing.get('runs_at_100_overs') is None and updated.get('runs_at_100_overs') is None:
        updated['runs_at_100_overs'] = current_runs
        updated['wickets_at_100_overs'] = current_wickets
    if overs >= 110 and existing.get('runs_at_110_overs') is None and updated.get('runs_at_110_overs') is None:
        updated['runs_at_110_overs'] = current_runs
        updated['wickets_at_110_overs'] = current_wickets
    return updated


def _pick_keeper_candidate(fielders, bowler_id):
    candidates = [p for p in fielders if p.get('id') != bowler_id]
    non_bowlers = [p for p in candidates if p.get('bowling_type') == 'none']
    if non_bowlers:
        return min(non_bowlers, key=lambda p: (p.get('batting_position') or 99, p.get('id') or 0))
    if candidates:
        return min(candidates, key=lambda p: (p.get('batting_position') or 99, p.get('id') or 0))
    return None


def _choose_fielder_for_wicket(fielders, bowler_id, dismissal_type, caught_type=None):
    if dismissal_type not in ('caught', 'run_out', 'stumped'):
        return None

    if dismissal_type == 'stumped' or caught_type == 'caught_behind':
        keeper = _pick_keeper_candidate(fielders, bowler_id)
        return keeper.get('id') if keeper else None

    non_bowler_fielders = [p for p in fielders if p.get('id') != bowler_id]
    all_fielders = list(fielders)

    if dismissal_type == 'run_out':
        pool = non_bowler_fielders or all_fielders
        if not pool:
            return None
        return random.choice(pool).get('id')

    if dismissal_type == 'caught':
        if caught_type in ('caught_slip', 'caught_boundary'):
            pool = non_bowler_fielders or all_fielders
            if not pool:
                return None
            return random.choice(pool).get('id')

        caught_and_bowled_roll = random.random()
        if bowler_id and caught_and_bowled_roll < 0.18:
            return bowler_id

        pool = non_bowler_fielders or all_fielders
        if not pool:
            return bowler_id
        return random.choice(pool).get('id')

    return None


def _determine_next_innings(match, all_innings, fmt):
    """Return (batting_team_id, bowling_team_id, innings_number) or None if match over."""
    completed = [i for i in all_innings if i['status'] == 'complete']
    n = len(completed)
    if fmt in ('ODI', 'T20', 'Hundred'):
        if n == 1:
            first = completed[0]
            return (first['bowling_team_id'], first['batting_team_id'], 2)
        return None
    # Test
    if n == 1:
        first = completed[0]
        return (first['bowling_team_id'], first['batting_team_id'], 2)
    if n == 2:
        first = all_innings[0]
        return (first['batting_team_id'], first['bowling_team_id'], 3)
    if n == 3:
        first = all_innings[0]
        return (first['bowling_team_id'], first['batting_team_id'], 4)
    return None


def _is_innings_complete(total_wickets, new_over, max_overs, total_runs, target):
    if total_wickets >= 10:
        return True
    if max_overs is not None and new_over >= max_overs:
        return True
    if target is not None and total_runs >= target:
        return True
    return False


def format_score(runs, wickets):
    """Cricket score string: 179/10 → '179 all out', 147/4 → '147/4'."""
    if wickets >= 10:
        return f"{runs} all out"
    return f"{runs}/{wickets}"


def format_overs(overs_decimal):
    if overs_decimal is None:
        return '0'
    complete_overs = int(overs_decimal)
    remainder = overs_decimal - complete_overs
    balls = round(remainder * 6)
    if balls >= 6:
        complete_overs += 1
        balls = 0
    if balls == 0:
        return str(complete_overs)
    return f"{complete_overs}.{balls}"


def _calculate_attendance(match, team1, team2):
    capacity = match.get('venue_capacity')
    if not capacity:
        return None

    t1_type = team1.get('team_type', 'international')
    t2_type = team2.get('team_type', 'international')
    fmt     = match.get('format', 'T20')

    _TIER1 = {'England', 'Australia', 'India', 'Pakistan',
              'New Zealand', 'South Africa', 'West Indies', 'Sri Lanka', 'Bangladesh'}
    _TIER2 = {'Zimbabwe', 'Ireland', 'Afghanistan'}

    def _nation_tier(team):
        if team.get('team_type') != 'international':
            return 0  # domestic
        n = team.get('name', '')
        if n in _TIER1: return 3
        if n in _TIER2: return 2
        return 1  # associates

    t1_tier = _nation_tier(team1)
    t2_tier = _nation_tier(team2)
    is_intl  = t1_tier > 0 and t2_tier > 0
    avg_tier = (t1_tier + t2_tier) / 2  # 0–3

    _TOP3 = {'England', 'Australia', 'India'}
    is_rivalry = (team1.get('name') in _TOP3 and team2.get('name') in _TOP3)
    is_icc = bool(match.get('tournament_id'))
    league = team1.get('league') or team2.get('league') or ''

    if not is_intl:
        if fmt == 'Hundred':
            lo, hi = 0.42, 0.78
        elif t1_type == 'county' or t2_type == 'county':
            lo, hi = 0.05, 0.22
        elif league in ('IPL', 'PSL', 'Big Bash League', 'CPL'):
            lo, hi = 0.45, 0.88
        else:
            lo, hi = 0.20, 0.55
    else:
        if fmt == 'Test':
            if avg_tier >= 2.8 or is_rivalry: lo, hi = 0.55, 0.92
            elif avg_tier >= 2.0:             lo, hi = 0.28, 0.62
            elif avg_tier >= 1.5:             lo, hi = 0.15, 0.42
            else:                             lo, hi = 0.08, 0.28
        elif fmt == 'ODI':
            if avg_tier >= 2.8 or is_rivalry: lo, hi = 0.62, 0.95
            elif avg_tier >= 2.0:             lo, hi = 0.38, 0.72
            elif avg_tier >= 1.5:             lo, hi = 0.22, 0.50
            else:                             lo, hi = 0.12, 0.35
        elif fmt in ('T20', 'Hundred'):
            if avg_tier >= 2.8 or is_rivalry: lo, hi = 0.65, 0.98
            elif avg_tier >= 2.0:             lo, hi = 0.42, 0.78
            elif avg_tier >= 1.5:             lo, hi = 0.25, 0.58
            else:                             lo, hi = 0.15, 0.45
        else:
            lo, hi = 0.30, 0.65

    if is_icc:
        lo = min(1.0, lo * 1.15)
        hi = min(1.0, hi * 1.10)

    if capacity > 60000 and not is_rivalry and not is_icc:
        hi *= 0.78
        lo *= 0.70

    fill = random.uniform(lo, hi)
    attendance = int(capacity * fill)
    attendance = max(50, min(attendance, capacity))
    attendance = round(attendance / 50) * 50
    return attendance


def _build_result_description(match, all_innings):
    if match.get('status') not in (None, 'complete'):
        return 'Match in progress'
    rt = match.get('result_type')
    if rt == 'draw':
        return 'Match drawn'
    if rt == 'tie':
        return 'Match tied'
    if rt == 'no_result':
        return 'No result'
    wname = match.get('winning_team_name', 'Unknown')
    if rt == 'runs':
        return f"{wname} won by {match.get('margin_runs', 0)} run(s)"
    if rt == 'wickets':
        return f"{wname} won by {match.get('margin_wickets', 0)} wicket(s)"
    return 'Result unknown'


def _calculate_and_complete_match(db, match_id, match, all_innings):
    """Run calculate_result() and stamp the match as complete."""
    fmt = match['format']
    inn1 = next((i for i in all_innings if i['innings_number'] == 1), None)
    inn2 = next((i for i in all_innings if i['innings_number'] == 2), None)

    if not inn1 or not inn2:
        return

    if fmt in ('ODI', 'T20', 'Hundred'):
        result = game_engine.calculate_result(
            inn1['total_runs'], inn1['total_wickets'],
            inn2['total_runs'], inn2['total_wickets'],
            fmt, inn2['status'] == 'complete'
        )
        winning_team_id = None
        if result['winning_team'] == 1:
            winning_team_id = inn1['batting_team_id']
        elif result['winning_team'] == 2:
            winning_team_id = inn2['batting_team_id']
        database.update_match(db, match_id, {
            'status': 'complete',
            'result_type': result['result_type'],
            'winning_team_id': winning_team_id,
            'margin_runs': result['margin_runs'],
            'margin_wickets': result['margin_wickets'],
        })
    else:
        # Test: sum across all innings
        inn3 = next((i for i in all_innings if i['innings_number'] == 3), None)
        inn4 = next((i for i in all_innings if i['innings_number'] == 4), None)
        team1_total = (inn1['total_runs'] if inn1 else 0) + (inn3['total_runs'] if inn3 else 0)
        team2_total = (inn2['total_runs'] if inn2 else 0) + (inn4['total_runs'] if inn4 else 0)
        team1_id = inn1['batting_team_id']
        team2_id = inn2['batting_team_id']

        last_inn = inn4 or inn3 or inn2
        is_complete = last_inn['status'] == 'complete' if last_inn else False

        if not is_complete:
            database.update_match(db, match_id, {
                'status': 'complete',
                'result_type': 'draw',
                'winning_team_id': None,
                'margin_runs': None,
                'margin_wickets': None,
            })
        elif team1_total > team2_total:
            margin = team1_total - team2_total
            database.update_match(db, match_id, {
                'status': 'complete',
                'result_type': 'runs',
                'winning_team_id': team1_id,
                'margin_runs': margin,
                'margin_wickets': None,
            })
        elif team2_total > team1_total:
            last_batting = last_inn['batting_team_id']
            last_wickets = last_inn['total_wickets']
            margin_w = 10 - last_wickets
            database.update_match(db, match_id, {
                'status': 'complete',
                'result_type': 'wickets',
                'winning_team_id': last_batting,
                'margin_runs': None,
                'margin_wickets': margin_w,
            })
        else:
            database.update_match(db, match_id, {
                'status': 'complete',
                'result_type': 'tie',
                'winning_team_id': None,
                'margin_runs': None,
                'margin_wickets': None,
            })


def _condense_state(state):
    """Return a lightweight state dict for the /ball response."""
    inn = state['current_innings']
    if not inn:
        return {}
    runs  = inn['total_runs']
    wkts  = inn['total_wickets']
    overs = inn['overs_completed']
    target = state['target']
    legal  = state['over_number'] * 6 + state['ball_in_over']
    crr    = round(runs / (legal / 6), 2) if legal >= 6 else None
    rrr    = None
    if target and state['max_overs']:
        remaining_overs = state['max_overs'] - state['over_number'] - state['ball_in_over'] / 6
        needed = target - runs
        if remaining_overs > 0:
            rrr = round(needed / remaining_overs, 2)
    return {
        'runs': runs, 'wickets': wkts, 'overs': overs,
        'current_rr': crr, 'required_rr': rrr,
    }


def bowl_ball(db, id, req_data):
    """
    Core game simulation loop for a single ball.
    Returns a dictionary of execution results. Raises ValueError on input/state validation errors.
    """
    state = database.get_match_state(db, id)
    if not state:
        raise ValueError('Match not found')
    if state['match']['status'] != 'in_progress':
        raise ValueError('Match is not in progress')
    if not state['current_innings']:
        raise ValueError('No active innings — toss not yet taken')

    innings    = state['current_innings']
    innings_id = state['current_innings_id']
    fmt        = state['format']
    over_number = state['over_number']
    ball_in_over = state['ball_in_over']
    is_free_hit  = state['is_free_hit']
    max_overs    = state['max_overs']
    target       = state['target']

    striker_id     = state['current_striker_id']
    non_striker_id = state['current_non_striker_id']
    if not striker_id or not non_striker_id:
        raise ValueError('Cannot determine current batters')

    # Select bowler if start of over
    bowler_id = state['current_bowler_id']
    if bowler_id is None:
        match_rec = state.get('match', {})
        player_mode = match_rec.get('player_mode', 'ai_vs_ai')
        human_team_id = match_rec.get('human_team_id')
        human_bowling = (
            player_mode == 'human_vs_human' or
            (player_mode == 'human_vs_ai' and human_team_id and innings.get('bowling_team_id') == human_team_id)
        )
        # Allow human to specify a bowler choice
        requested_bowler = req_data.get('bowler_id')
        bowler_list = [
            {
                'player_id':     b['player_id'],
                'bowling_type':  b['bowling_type'],
                'bowling_rating': b['bowling_rating'],
                'overs_bowled':  b['overs'],
                'balls_bowled':  b['balls'],
            }
            for b in state['bowler_innings']
        ]
        cap_map = {'T20': 4, 'ODI': 10, 'Test': None, 'Hundred': None}
        cap = cap_map.get(fmt)
        if human_bowling and not requested_bowler:
            raise ValueError('bowler_id required for human-controlled bowling changes')
        if requested_bowler:
            rb = next((b for b in bowler_list if b['player_id'] == requested_bowler), None)
            if fmt == 'Hundred':
                balls_this_bowler = (rb['overs_bowled'] * 6 + rb['balls_bowled']) if rb else 0
                valid = (rb is not None and balls_this_bowler < hundred_engine.HUNDRED_BOWLER_MAX)
            else:
                valid = (rb is not None
                         and rb['player_id'] != state['last_bowler_id']
                         and (cap is None or rb['overs_bowled'] < cap))
            if valid:
                bowler_id = requested_bowler
            elif human_bowling:
                raise ValueError('Invalid bowler selection for this over')
        if bowler_id is None:
            if fmt == 'Hundred':
                _b100_list = [
                    {**b, 'balls_bowled': b['overs_bowled'] * 6 + b['balls_bowled']}
                    for b in bowler_list
                ]
                _legal_bowled = over_number * 6 + ball_in_over
                _complete_sets = _legal_bowled // hundred_engine.HUNDRED_SET_SIZE
                _end_block = _complete_sets // hundred_engine.HUNDRED_MAX_SETS
                _hundred_end = 'pavilion' if _end_block % 2 == 0 else 'nursery'
                _sets_this_end = (_complete_sets % hundred_engine.HUNDRED_MAX_SETS) + 1
                sel = hundred_engine.select_hundred_bowler(
                    _b100_list, state['last_bowler_id'],
                    _hundred_end, _sets_this_end,
                )
                bowler_id = sel['player_id']
            else:
                bowler_id = game_engine.select_bowler(
                    bowler_list, over_number, fmt, state['last_bowler_id']
                )

    # Look up current entities
    striker = next(
        (p for p in state['batting_team_players'] if p['id'] == striker_id), None
    )
    bowler_row = next(
        (b for b in state['bowler_innings'] if b['player_id'] == bowler_id), None
    )
    batter_innings_row = next(
        (b for b in state['batter_innings']
         if b['player_id'] == striker_id and b['status'] == 'batting'), None
    )
    if not striker or not bowler_row or not batter_innings_row:
        raise ValueError('Cannot find striker or bowler data')

    # ── Roll the ball ──────────────────────────────────────────────────────
    if fmt == 'Hundred':
        _legal_so_far = over_number * 6 + ball_in_over
        _is_pp = _legal_so_far < hundred_engine.HUNDRED_POWERPLAY
        ball_result = hundred_engine.bowl_hundred_ball(
            batter_rating  = striker['batting_rating'],
            bowler_rating  = bowler_row['bowling_rating'],
            bowling_type   = bowler_row['bowling_type'],
            is_free_hit    = is_free_hit,
            balls_faced    = 0,
            is_powerplay   = _is_pp,
        )
    else:
        ball_result = game_engine.bowl_ball(
            batter_rating  = striker['batting_rating'],
            bowler_rating  = bowler_row['bowling_rating'],
            bowling_type   = bowler_row['bowling_type'],
            is_free_hit    = is_free_hit,
            partnership_balls = 0,
            scoring_mode   = state['match'].get('scoring_mode', 'modern'),
            format         = fmt,
        )

    is_legal  = ball_result['outcome_type'] not in ('wide', 'no_ball')
    is_wicket = ball_result['outcome_type'] == 'wicket'
    runs_scored   = ball_result['runs']
    extras_scored = ball_result['extras_runs']
    total_added   = runs_scored + extras_scored

    # Legal ball counter (before this ball)
    legal_before = over_number * 6 + ball_in_over
    legal_after  = legal_before + (1 if is_legal else 0)
    new_over     = legal_after // 6
    new_ball     = legal_after % 6

    # Delivery sequence number in this over (for ball_number column)
    del_in_over = db.execute(
        "SELECT COUNT(*) AS c FROM deliveries WHERE innings_id=? AND over_number=?",
        (innings_id, over_number)
    ).fetchone()['c']

    # Generate commentary
    all_players = {p['id']: p['name']
                   for p in state['batting_team_players'] + state['bowling_team_players']}
    ctx = {
        'batter': all_players.get(striker_id, ''),
        'bowler': all_players.get(bowler_id, ''),
        'runs':   runs_scored,
        'score':  innings['total_runs'] + total_added,
        'wickets': innings['total_wickets'] + (1 if is_wicket else 0),
        'overs':  f'{over_number}.{ball_in_over}',
    }
    commentary = game_engine.generate_commentary(ball_result['commentary_key'], ctx, [])
    fielder_id = _choose_fielder_for_wicket(
        state['bowling_team_players'],
        bowler_id,
        ball_result.get('dismissal_type'),
        ball_result.get('caught_type'),
    ) if is_wicket else None

    # ── Persist delivery ───────────────────────────────────────────────────
    database.insert_delivery(db, {
        'innings_id':          innings_id,
        'over_number':         over_number,
        'ball_number':         del_in_over + 1,
        'bowler_id':           bowler_id,
        'striker_id':          striker_id,
        'non_striker_id':      non_striker_id,
        'fielder_id':          fielder_id,
        'stage1_roll':         ball_result['stage1'],
        'stage2_roll':         ball_result['stage2'],
        'stage3_roll':         ball_result['stage3'],
        'stage4_roll':         ball_result['stage4'],
        'stage4b_roll':        ball_result['stage4b'],
        'outcome_type':        ball_result['outcome_type'],
        'runs_scored':         runs_scored,
        'extras_type':         ball_result['extras_type'],
        'extras_runs':         extras_scored,
        'dismissal_type':      ball_result['dismissal_type'],
        'dismissed_batter_id': striker_id if is_wicket else None,
        'shot_angle':          ball_result['shot_angle'],
        'is_free_hit':         is_free_hit,
        'is_wide':             ball_result['outcome_type'] == 'wide',
        'is_no_ball':          ball_result['outcome_type'] == 'no_ball',
        'commentary':          commentary,
    })

    # ── Update batter innings ─────────────────────────────────────────────
    otype = ball_result['outcome_type']
    bi_update = {}
    if is_legal:
        bi_update['balls_faced'] = batter_innings_row['balls_faced'] + 1
    if is_wicket:
        bi_update['status']         = 'dismissed'
        bi_update['dismissal_type'] = ball_result['dismissal_type']
        bi_update['runs']           = batter_innings_row['runs'] + runs_scored
        if fielder_id:
            bi_update['fielder_id'] = fielder_id
        # Bowler credited with wicket (not run-outs)
        if ball_result['dismissal_type'] not in ('run_out',):
            bi_update['bowler_id'] = bowler_id
    elif otype not in ('wide', 'no_ball', 'leg_bye', 'bye') and is_legal:
        bi_update['runs']  = batter_innings_row['runs'] + runs_scored
        bi_update['fours'] = batter_innings_row['fours'] + (1 if otype == 'four' else 0)
        bi_update['sixes'] = batter_innings_row['sixes'] + (1 if otype == 'six' else 0)
    if bi_update:
        database.update_batter_innings(db, batter_innings_row['id'], bi_update)

    # ── Update bowler innings ─────────────────────────────────────────────
    bwi_update = {'runs_conceded': bowler_row['runs_conceded'] + total_added}
    if otype == 'wide':
        bwi_update['wides']    = bowler_row['wides'] + 1
    elif otype == 'no_ball':
        bwi_update['no_balls'] = bowler_row['no_balls'] + 1

    is_bowler_wicket = is_wicket and ball_result['dismissal_type'] not in ('run_out',)
    if is_bowler_wicket:
        bwi_update['wickets'] = bowler_row['wickets'] + 1

    if is_legal:
        end_of_over = (new_ball == 0)
        if end_of_over:
            # Check maiden: sum all runs this over (including current)
            over_runs_row = db.execute(
                "SELECT COALESCE(SUM(runs_scored + extras_runs), 0) AS s "
                "FROM deliveries WHERE innings_id=? AND over_number=?",
                (innings_id, over_number)
            ).fetchone()
            over_runs = (over_runs_row['s'] or 0) + total_added
            bwi_update['overs'] = bowler_row['overs'] + 1
            bwi_update['balls'] = 0
            if over_runs == 0:
                bwi_update['maidens'] = bowler_row['maidens'] + 1
        else:
            bwi_update['balls'] = bowler_row['balls'] + 1

    database.update_bowler_innings(db, bowler_row['id'], bwi_update)

    # ── Update totals ─────────────────────────────────────────────────────
    new_wickets = innings['total_wickets'] + (1 if is_wicket else 0)
    new_runs    = innings['total_runs'] + total_added
    inn_update  = {
        'total_runs':     new_runs,
        'total_wickets':  new_wickets,
        'overs_completed': new_over + new_ball / 10,
    }
    if otype == 'wide':
        inn_update['extras_wides']   = innings['extras_wides'] + extras_scored
    elif otype == 'no_ball':
        inn_update['extras_noballs'] = innings['extras_noballs'] + extras_scored
    elif ball_result['extras_type'] == 'bye':
        inn_update['extras_byes']    = innings['extras_byes'] + extras_scored
    elif ball_result['extras_type'] == 'leg_bye':
        inn_update['extras_legbyes'] = innings['extras_legbyes'] + extras_scored
    inn_update = _apply_innings_cutoff_snapshots(innings, inn_update)

    # ── Update current partnership ────────────────────────────────────────
    current_partnership = state['partnerships'][-1] if state['partnerships'] else None
    if current_partnership:
        p_update = {'runs': current_partnership['runs'] + total_added}
        if is_legal:
            p_update['balls'] = current_partnership['balls'] + 1
        database.update_partnership(db, current_partnership['id'], p_update)

    # ── Wicket handling ───────────────────────────────────────────────────
    if is_wicket:
        overs_at_fall = over_number + ball_in_over / 10
        database.insert_fall_of_wicket(
            db, innings_id, new_wickets, new_runs, overs_at_fall, striker_id
        )
        next_batter = next(
            (b for b in state['batter_innings'] if b['status'] == 'yet_to_bat'), None
        )
        if next_batter:
            database.update_batter_innings(db, next_batter['id'], {'status': 'batting'})
            database.create_partnership(
                db, innings_id, new_wickets,
                next_batter['player_id'], non_striker_id
            )

    # ── Milestone detection ───────────────────────────────────────────────
    milestones = []
    batter_runs_before = batter_innings_row['runs']
    batter_runs_after  = batter_runs_before + runs_scored if not is_wicket and otype not in ('wide', 'no_ball', 'leg_bye', 'bye') else batter_runs_before
    for thresh in (50, 100, 150, 200):
        if batter_runs_before < thresh <= batter_runs_after:
            milestones.append({'type': f'batter_{thresh}', 'player_id': striker_id})

    if is_bowler_wicket:
        bowler_wkts_after = bowler_row['wickets'] + 1
        for thresh in (5, 10):
            if bowler_row['wickets'] < thresh <= bowler_wkts_after:
                milestones.append({'type': f'bowler_{thresh}fer', 'player_id': bowler_id})

    if current_partnership:
        p_runs_before = current_partnership['runs']
        p_runs_after  = p_runs_before + total_added
        for thresh in (50, 100, 150, 200):
            if p_runs_before < thresh <= p_runs_after:
                milestones.append({'type': f'partnership_{thresh}', 'runs': p_runs_after})

    # ── Record detection ─────────────────────────────────────────────────
    records_broken = []
    fmt_for_record = fmt

    # 1) Highest individual score
    if is_legal and not is_wicket and runs_scored > 0:
        batter_runs_now = batter_runs_after
        prev = database.get_almanack_batting_record(db, fmt_for_record, 'highest_score')
        prev_val = prev['value'] if prev else 0
        if batter_runs_now > prev_val:
            pname = (database.get_player(db, striker_id) or {}).get('name', '')
            records_broken.append({
                'type':            'highest_individual_score',
                'format':          fmt_for_record,
                'player_name':     pname,
                'new_value':       batter_runs_now,
                'previous_value':  prev_val,
                'previous_holder': prev['name'] if prev else None,
            })

    # 2) Best bowling figures (after a wicket)
    if is_bowler_wicket:
        bowler_wkts_now = bowler_row['wickets'] + 1
        bowler_runs_now = bowler_row['runs_conceded'] + total_added
        prev = database.get_almanack_bowling_record(db, fmt_for_record, 'best_figures')
        is_better = False
        if prev is None:
            is_better = True
        else:
            if bowler_wkts_now > prev['wickets']:
                is_better = True
            elif bowler_wkts_now == prev['wickets'] and bowler_runs_now < prev['runs_conceded']:
                is_better = True
        if is_better:
            pname = (database.get_player(db, bowler_id) or {}).get('name', '')
            records_broken.append({
                'type':            'best_bowling_figures',
                'format':          fmt_for_record,
                'player_name':     pname,
                'new_value':       f'{bowler_wkts_now}/{bowler_runs_now}',
                'previous_value':  f"{prev['wickets']}/{prev['runs_conceded']}" if prev else None,
                'previous_holder': prev['name'] if prev else None,
            })

    # 3) Highest team score (after runs added)
    if total_added > 0:
        prev_team = database.get_almanack_highest_team_score(db, fmt_for_record)
        prev_team_score = prev_team['total_runs'] if prev_team else 0
        if new_runs > prev_team_score:
            records_broken.append({
                'type':            'highest_team_score',
                'format':          fmt_for_record,
                'player_name':     innings.get('batting_team_name', ''),
                'new_value':       new_runs,
                'previous_value':  prev_team_score,
                'previous_holder': prev_team['team_name'] if prev_team else None,
            })

    # 4) Highest partnership
    if current_partnership and total_added > 0:
        p_runs_now = current_partnership['runs'] + total_added
        prev_part = database.get_almanack_highest_partnership(db, fmt_for_record)
        prev_part_val = prev_part['runs'] if prev_part else 0
        if p_runs_now > prev_part_val:
            records_broken.append({
                'type':            'highest_partnership',
                'format':          fmt_for_record,
                'player_name':     f"{current_partnership.get('batter1_name','')} & {current_partnership.get('batter2_name','')}",
                'new_value':       p_runs_now,
                'previous_value':  prev_part_val,
                'previous_holder': f"{prev_part['batter1_name']} & {prev_part['batter2_name']}" if prev_part else None,
            })

    # 5) Most sixes in an innings
    if otype == 'six':
        sixes_now = batter_innings_row['sixes'] + 1
        prev_six = database.get_almanack_most_sixes(db, fmt_for_record)
        prev_six_val = prev_six['mx'] if prev_six and prev_six['mx'] else 0
        if sixes_now > prev_six_val:
            pname = (database.get_player(db, striker_id) or {}).get('name', '')
            records_broken.append({
                'type':            'most_sixes_innings',
                'format':          fmt_for_record,
                'player_name':     pname,
                'new_value':       sixes_now,
                'previous_value':  prev_six_val,
                'previous_holder': prev_six['name'] if prev_six and prev_six['mx'] else None,
            })

    # ── Innings / match completion ────────────────────────────────────────
    innings_complete = False
    match_complete   = False

    if _is_innings_complete(new_wickets, new_over, max_overs, new_runs, target):
        innings_complete = True
        inn_update['status'] = 'complete'
        database.update_innings(db, innings_id, inn_update)

        # Decide whether to start next innings or complete match
        all_innings_fresh = database.get_innings(db, id)
        nxt = _determine_next_innings(state['match'], all_innings_fresh, fmt)
        if nxt:
            batting_tid, bowling_tid, next_inn_num = nxt
            _start_innings(db, id, next_inn_num, batting_tid, bowling_tid)
        else:
            match_complete = True
            all_innings_fresh2 = database.get_innings(db, id)
            match_fresh = database.get_match(db, id)
            _calculate_and_complete_match(db, id, match_fresh, all_innings_fresh2)

        # 6) Lowest team score (only on all-out — new_wickets==10)
        if new_wickets >= 10 and new_runs > 0:
            prev_low = database.get_almanack_lowest_team_score(db, fmt_for_record)
            prev_low_val = prev_low['total_runs'] if prev_low else None
            if prev_low_val is None or new_runs < prev_low_val:
                records_broken.append({
                    'type':            'lowest_team_score',
                    'format':          fmt_for_record,
                    'player_name':     innings.get('batting_team_name', ''),
                    'new_value':       new_runs,
                    'previous_value':  prev_low_val,
                    'previous_holder': prev_low['team_name'] if prev_low else None,
                })
    else:
        database.update_innings(db, innings_id, inn_update)

    # ── Reload fresh state ───────────────────────────────────────────────────
    fresh_state = database.get_match_state(db, id)
    delivery_row = db.execute(
        "SELECT * FROM deliveries WHERE innings_id=? ORDER BY id DESC LIMIT 1",
        (innings_id,)
    ).fetchone()

    hundred_state = None
    if fmt == 'Hundred':
        _legal_total = legal_after
        hundred_state = {
            'balls_bowled':    _legal_total,
            'balls_remaining': max(0, hundred_engine.HUNDRED_BALLS - _legal_total),
            'is_powerplay':    _legal_total < hundred_engine.HUNDRED_POWERPLAY,
            'powerplay_complete': _legal_total >= hundred_engine.HUNDRED_POWERPLAY,
            'set_number':      (_legal_total // hundred_engine.HUNDRED_SET_SIZE) + 1,
            'ball_in_set':     _legal_total % hundred_engine.HUNDRED_SET_SIZE,
            'set_complete':    is_legal and (_legal_total % hundred_engine.HUNDRED_SET_SIZE == 0),
            'final_ten':       _legal_total >= 90,
            'final_five':      _legal_total >= 95,
            'final_ball':      _legal_total == 99,
            'progress_bar':    hundred_engine.render_hundred_progress_bar(_legal_total),
            'progress_text':   hundred_engine.format_hundred_progress(_legal_total),
        }

    return {
        'delivery':       database.dict_from_row(delivery_row),
        'innings_state':  _condense_state(fresh_state),
        'commentary':     commentary,
        'milestones':     milestones,
        'records_broken': records_broken,
        'innings_complete': innings_complete,
        'match_complete':   match_complete,
        'hundred_state':    hundred_state,
        'match_state':      {
            'over_number':   fresh_state['over_number'],
            'ball_in_over':  fresh_state['ball_in_over'],
            'is_free_hit':   fresh_state['is_free_hit'],
            'striker_id':    fresh_state['current_striker_id'],
            'non_striker_id': fresh_state['current_non_striker_id'],
            'bowler_id':     fresh_state['current_bowler_id'],
            'innings_number': fresh_state['current_innings']['innings_number'] if fresh_state['current_innings'] else None,
        },
    }
