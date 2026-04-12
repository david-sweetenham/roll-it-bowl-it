"""
ai_captain.py — AI Captain decision logic for Roll It & Bowl It.
Pure Python — no Flask imports, no database imports.
All functions receive their required data as arguments.
"""

import random
import statistics

# ── Over caps ──────────────────────────────────────────────────────────────────

_OVER_CAP = {'T20': 4, 'ODI': 10, 'Test': None}
_MAX_OVERS = {'T20': 20, 'ODI': 50, 'Test': None}


# ── Bowling decisions ──────────────────────────────────────────────────────────

def choose_bowler(bowlers, innings_state, match_format):
    """
    Select the best eligible bowler for this over.
    Returns player_id.

    bowlers: list of dicts with keys:
        player_id, bowling_rating, bowling_type, overs_bowled,
        balls_bowled, wickets_this_spell, runs_this_spell, last_bowled_over
    innings_state: dict with keys:
        total_runs, total_wickets, overs_completed, target,
        balls_remaining, last_bowler_id
    """
    cap = _OVER_CAP.get(match_format)
    max_overs = _MAX_OVERS.get(match_format)
    last_bowler_id = innings_state.get('last_bowler_id')
    overs_completed = innings_state.get('overs_completed', 0)

    def total_overs(b):
        return b.get('overs_bowled', 0) + b.get('balls_bowled', 0) / 6.0

    def is_eligible(b):
        if b['player_id'] == last_bowler_id:
            return False
        if cap is not None and b.get('overs_bowled', 0) >= cap:
            return False
        return True

    def is_specialist(b):
        return b.get('bowling_type', 'none') != 'none'

    eligible = [b for b in bowlers if is_eligible(b)]
    specialists = [b for b in eligible if is_specialist(b)]
    candidates = specialists if specialists else eligible

    # Final fallback: any non-last bowler
    if not candidates:
        candidates = [b for b in bowlers if b['player_id'] != last_bowler_id]
    if not candidates:
        return bowlers[0]['player_id']

    # Rule: bowler with 2+ wickets in spell and overs remaining — 70% continue
    hot = [b for b in candidates
           if b.get('wickets_this_spell', 0) >= 2
           and (cap is None or b.get('overs_bowled', 0) < cap)]
    if hot and random.random() < 0.70:
        hot.sort(key=lambda b: (-b.get('wickets_this_spell', 0), -b.get('bowling_rating', 1)))
        return hot[0]['player_id']

    # Death overs: highest rated
    if max_overs is not None:
        overs_left = max_overs - overs_completed
        death = 5 if match_format == 'T20' else (10 if match_format == 'ODI' else 0)
        if death and overs_left <= death:
            candidates.sort(key=lambda b: (-b.get('bowling_rating', 1), total_overs(b)))
            return candidates[0]['player_id']

    # Determine last bowler type for alternation preference
    last_type = None
    if last_bowler_id is not None:
        lb = next((b for b in bowlers if b['player_id'] == last_bowler_id), None)
        if lb:
            last_type = lb.get('bowling_type')

    def score(b):
        rating = b.get('bowling_rating', 1)
        ov = total_overs(b)
        btype = b.get('bowling_type', 'none')
        # Small bonus for alternating pace/spin
        type_bonus = 0.0
        if last_type == 'pace' and btype == 'spin':
            type_bonus = 0.3
        elif last_type == 'spin' and btype == 'pace':
            type_bonus = 0.3
        # Penalise bowlers who have bowled many overs (keep fresh legs)
        return rating + type_bonus - ov * 0.05

    candidates.sort(key=lambda b: -score(b))
    return candidates[0]['player_id']


# ── Declaration ────────────────────────────────────────────────────────────────

def should_declare(innings_number, lead, total_wickets,
                   overs_completed, estimated_overs_remaining):
    """
    Returns True if the AI captain should declare (Tests only).
    The caller is responsible for only calling this for Test matches.
    """
    if total_wickets < 7:
        return False
    if estimated_overs_remaining < 30:
        return False

    if innings_number == 1:
        return (lead >= 300
                and estimated_overs_remaining >= 80
                and total_wickets >= 7)
    else:
        # 2nd or 3rd innings (batting second or third)
        return (lead >= 180
                and estimated_overs_remaining >= 40
                and total_wickets >= 7)


# ── Follow-on ──────────────────────────────────────────────────────────────────

def should_enforce_follow_on(lead, bowling_team_bowlers, total_overs_bowled):
    """
    Returns True if the AI should enforce the follow-on.

    bowling_team_bowlers: list of dicts with bowling_rating and overs_bowled.
    """
    if lead < 200:
        return False

    if total_overs_bowled >= 60:
        return False

    top4 = sorted(
        bowling_team_bowlers,
        key=lambda b: b.get('bowling_rating', 1),
        reverse=True
    )[:4]

    if lead >= 250:
        if top4:
            mean_rating = statistics.mean(b.get('bowling_rating', 1) for b in top4)
        else:
            mean_rating = 0.0
        if mean_rating >= 3.5:
            return True

    # 200–249 band
    if 200 <= lead < 250 and lead >= 220:
        top3 = top4[:3]
        if top3 and all(b.get('overs_bowled', 0) < 20 for b in top3):
            return True

    return False


# ── Nightwatchman ──────────────────────────────────────────────────────────────

def should_send_nightwatchman(wickets_fallen, overs_to_notional_close,
                               batting_position):
    """
    Returns True if a nightwatchman should be sent in.
    The caller selects the actual player (highest-rated unused bowler).
    """
    return (
        overs_to_notional_close <= 3
        and wickets_fallen < 9
        and batting_position <= 7
    )


# ── Batting order ──────────────────────────────────────────────────────────────

def set_batting_order(players, nightwatchman_id=None):
    """
    Returns the batting order as a sorted list.
    If nightwatchman_id is provided, moves that player to position 3
    (after the openers) regardless of their normal batting position.
    """
    ordered = sorted(players, key=lambda p: p.get('batting_position', 99))

    if nightwatchman_id is None:
        return ordered

    wm = next(
        (p for p in ordered
         if p.get('player_id') == nightwatchman_id or p.get('id') == nightwatchman_id),
        None
    )
    if wm is None:
        return ordered

    remaining = [p for p in ordered if p is not wm]
    # Insert nightwatchman at position 3 (index 2)
    insert_at = min(2, len(remaining))
    return remaining[:insert_at] + [wm] + remaining[insert_at:]


# ── Match summary / over summary ───────────────────────────────────────────────

def ai_match_summary(match_state):
    """
    Called after each over in AI vs AI (or AI-controlled) mode.
    Analyses the current state and returns a decisions dict.

    Returns:
        {
            'bowling_change': bool,
            'suggested_bowler_id': int | None,
            'declare': bool,
            'enforce_follow_on': bool | None,
            'send_nightwatchman': bool,
            'nightwatchman_player_id': int | None,
        }
    """
    innings = match_state.get('current_innings') or {}
    bowlers = match_state.get('bowler_innings', [])
    fmt = match_state.get('format', 'T20')
    over_number = match_state.get('over_number', 0)
    max_overs = match_state.get('max_overs')
    target = match_state.get('target')
    last_bowler_id = match_state.get('last_bowler_id')
    current_bowler_id = match_state.get('current_bowler_id')

    innings_state = {
        'total_runs':      innings.get('total_runs', 0),
        'total_wickets':   innings.get('total_wickets', 0),
        'overs_completed': float(innings.get('overs_completed', 0)),
        'target':          target,
        'balls_remaining': ((max_overs - over_number) * 6) if max_overs else 9999,
        'last_bowler_id':  last_bowler_id,
    }

    bowler_list = [
        {
            'player_id':          b['player_id'],
            'bowling_rating':     b.get('bowling_rating', 1),
            'bowling_type':       b.get('bowling_type', 'none'),
            'overs_bowled':       b.get('overs', 0),
            'balls_bowled':       b.get('balls', 0),
            'wickets_this_spell': b.get('wickets', 0),
            'runs_this_spell':    b.get('runs_conceded', 0),
            'last_bowled_over':   None,
        }
        for b in bowlers
    ]

    # Bowling change needed when current_bowler_id is None (start of over)
    bowling_change = (current_bowler_id is None)
    suggested_bowler_id = None
    if bowling_change and bowler_list:
        suggested_bowler_id = choose_bowler(bowler_list, innings_state, fmt)

    # Declaration (Tests only, rough heuristic)
    declare = False
    if fmt == 'Test' and innings and target is None:
        inn_num = innings.get('innings_number', 1)
        lead = innings.get('total_runs', 0)
        overs_remaining = max(0, 90 - over_number)
        declare = should_declare(
            inn_num, lead,
            innings.get('total_wickets', 0),
            over_number, overs_remaining
        )

    return {
        'bowling_change':          bowling_change,
        'suggested_bowler_id':     suggested_bowler_id,
        'declare':                 declare,
        'enforce_follow_on':       None,
        'send_nightwatchman':      False,
        'nightwatchman_player_id': None,
    }
