import sys
from flask import Flask, request, jsonify
from flask_cors import CORS

from flask import Flask, jsonify, request, render_template, Response, stream_with_context
from flask_cors import CORS
import json
import os
import random
from werkzeug.exceptions import HTTPException
import database
import game_engine
import cricket_calendar
import competition_rules
import ai_captain
import config


# ── Match helpers ─────────────────────────────────────────────────────────────

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
    """Convert decimal overs to cricket notation.
    Internally overs are stored as true decimals where 0.5 = 3 balls (3/6).

    Examples:
        13.8333 -> "13.5"  (13 overs, 5 balls: 5/6 = 0.8333)
        15.5    -> "15.3"  (15 overs, 3 balls: 3/6 = 0.5)
        4.1667  -> "4.1"   (4 overs, 1 ball:  1/6 = 0.1667)
        20.0    -> "20"
    """
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


def _build_result_description(match, all_innings):
    """Build human-readable result string from match/innings data."""
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

app = Flask(__name__,
            template_folder=config.TEMPLATE_DIR,
            static_folder=config.STATIC_DIR)
CORS(app)


@app.errorhandler(HTTPException)
def handle_http_exception(exc):
    if request.path.startswith('/api/'):
        return jsonify({'error': exc.description or exc.name}), exc.code
    return exc


@app.errorhandler(Exception)
def handle_unhandled_exception(exc):
    if request.path.startswith('/api/'):
        app.logger.exception('Unhandled API exception on %s', request.path)
        return jsonify({'error': str(exc) or 'Internal server error'}), 500
    raise exc


@app.route('/')
def index():
    return render_template('index.html')


def stub():
    return jsonify({"status": "ok", "stub": True})


def err(msg, code=400):
    return jsonify({"error": msg}), code


# ── Health ────────────────────────────────────────────────────────────────────

@app.route('/api/health')
def health():
    db = database.get_db()
    try:
        team_count = db.execute("SELECT COUNT(*) as c FROM teams").fetchone()['c']
        match_count = db.execute("SELECT COUNT(*) as c FROM matches").fetchone()['c']
        delivery_count = db.execute("SELECT COUNT(*) as c FROM deliveries").fetchone()['c']
        player_count = db.execute("SELECT COUNT(*) as c FROM players").fetchone()['c']
        venue_count = db.execute("SELECT COUNT(*) as c FROM venues").fetchone()['c']
        innings_count = db.execute("SELECT COUNT(*) as c FROM innings").fetchone()['c']
        batter_count = db.execute("SELECT COUNT(*) as c FROM batter_innings").fetchone()['c']
        bowler_count = db.execute("SELECT COUNT(*) as c FROM bowler_innings").fetchone()['c']

        db_size = 0
        db_path = database.DB_PATH
        if os.path.exists(db_path):
            db_size = round(os.path.getsize(db_path) / (1024 * 1024), 3)

        sqlite_ver = db.execute("SELECT sqlite_version()").fetchone()[0]
        return jsonify({
            "status": "ok",
            "db_path": db_path,
            "db_size_mb": db_size,
            "sqlite_version": sqlite_ver,
            "flask_debug": app.debug,
            "tables": {
                "teams":         team_count,
                "players":       player_count,
                "venues":        venue_count,
                "matches":       match_count,
                "innings":       innings_count,
                "batter_innings":batter_count,
                "bowler_innings":bowler_count,
                "deliveries":    delivery_count,
            }
        })
    finally:
        database.close_db(db)


# ── Quick Stats (Home Dashboard) ─────────────────────────────────────────────

@app.route('/api/stats/quick', methods=['GET'])
def quick_stats():
    db = database.get_db()
    try:
        totals = db.execute(
            "SELECT COUNT(DISTINCT m.id) as matches, "
            " COALESCE(SUM(i.total_runs),0) as total_runs, "
            " COALESCE(SUM(i.total_wickets),0) as total_wickets "
            "FROM matches m LEFT JOIN innings i ON i.match_id = m.id "
            "WHERE m.status = 'complete'"
        ).fetchone()
        hs_row = db.execute(
            "SELECT bi.runs, p.name as player_name, m.format, m.match_date "
            "FROM batter_innings bi "
            "JOIN players p ON bi.player_id = p.id "
            "JOIN innings i ON bi.innings_id = i.id "
            "JOIN matches m ON i.match_id = m.id "
            "WHERE m.status = 'complete' "
            "ORDER BY bi.runs DESC LIMIT 1"
        ).fetchone()
        centuries_row = db.execute(
            "SELECT p.name as player_name, COUNT(*) as centuries "
            "FROM batter_innings bi "
            "JOIN players p ON bi.player_id = p.id "
            "JOIN innings i ON bi.innings_id = i.id "
            "JOIN matches m ON i.match_id = m.id "
            "WHERE bi.runs >= 100 AND m.status = 'complete' "
            "GROUP BY bi.player_id ORDER BY centuries DESC LIMIT 1"
        ).fetchone()
        recent = db.execute(
            "SELECT m.id, m.match_date, m.format, m.result_type, "
            " m.margin_runs, m.margin_wickets, "
            " COALESCE(m.player_mode, 'ai_vs_ai') as player_mode, "
            " COALESCE(m.canon_status, 'canon') as canon_status, "
            " t1.name as team1_name, t2.name as team2_name, "
            " wt.name as winning_team_name "
            "FROM matches m "
            "JOIN teams t1 ON m.team1_id = t1.id "
            "JOIN teams t2 ON m.team2_id = t2.id "
            "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
            "WHERE m.status = 'complete' "
            "  AND COALESCE(m.canon_status, 'canon') != 'deleted' "
            "ORDER BY COALESCE(m.created_at, m.match_date) DESC, m.id DESC LIMIT 5"
        ).fetchall()
        return jsonify({
            'matches':          int(totals['matches'] or 0),
            'total_runs':       int(totals['total_runs'] or 0),
            'total_wickets':    int(totals['total_wickets'] or 0),
            'highest_score':    database.dict_from_row(hs_row),
            'most_centuries':   database.dict_from_row(centuries_row),
            'recent_results':   database.dict_from_rows(recent),
        })
    finally:
        database.close_db(db)


# ── Teams ─────────────────────────────────────────────────────────────────────

@app.route('/api/teams', methods=['GET'])
def get_teams():
    db = database.get_db()
    try:
        teams = database.get_teams(db)
        # Optional filter: ?hundred=1 returns only Hundred teams; ?hundred=0 excludes them
        hundred_filter = request.args.get('hundred')
        if hundred_filter == '1':
            teams = [t for t in teams if t.get('is_hundred_team')]
        elif hundred_filter == '0':
            teams = [t for t in teams if not t.get('is_hundred_team')]
        return jsonify({"teams": teams, "count": len(teams)})
    finally:
        database.close_db(db)


@app.route('/api/teams/<int:id>', methods=['GET'])
def get_team(id):
    db = database.get_db()
    try:
        team = database.get_team(db, id)
        if not team:
            return err("Team not found", 404)
        players = database.get_players_for_team(db, id)
        return jsonify({"team": team, "players": players})
    finally:
        database.close_db(db)


@app.route('/api/teams', methods=['POST'])
def create_team():
    data = request.get_json() or {}
    if not data.get('name'):
        return err("name is required")
    db = database.get_db()
    try:
        new_id = database.create_team(db, data)
        team = database.get_team(db, new_id)
        return jsonify({"team": team}), 201
    finally:
        database.close_db(db)


@app.route('/api/teams/<int:id>', methods=['PUT'])
def update_team(id):
    data = request.get_json() or {}
    db = database.get_db()
    try:
        database.update_team(db, id, data)
        team = database.get_team(db, id)
        return jsonify({"team": team})
    finally:
        database.close_db(db)


@app.route('/api/teams/<int:id>/profile', methods=['GET'])
def team_profile(id):
    db = database.get_db()
    try:
        data = database.get_team_profile(db, id)
        if not data:
            return err("Team not found", 404)
        return jsonify(data)
    finally:
        database.close_db(db)


@app.route('/api/teams/<int:id>/head-to-head/<int:id2>', methods=['GET'])
def head_to_head(id, id2):
    db = database.get_db()
    try:
        matches = database.get_head_to_head(db, id, id2)
        # Group by format
        by_format = {}
        for m in matches:
            fmt = m['format']
            if fmt not in by_format:
                by_format[fmt] = {'matches': [], 'team1_wins': 0, 'team2_wins': 0, 'draws': 0}
            by_format[fmt]['matches'].append(m)
            if m['winning_team_id'] == id:
                by_format[fmt]['team1_wins'] += 1
            elif m['winning_team_id'] == id2:
                by_format[fmt]['team2_wins'] += 1
            else:
                by_format[fmt]['draws'] += 1
        return jsonify({'matches': matches, 'by_format': by_format,
                        'total': len(matches)})
    finally:
        database.close_db(db)


# ── Players ───────────────────────────────────────────────────────────────────

@app.route('/api/players/<int:id>', methods=['GET'])
def get_player(id):
    db = database.get_db()
    try:
        data = database.get_player_profile(db, id)
        if not data:
            return err("Player not found", 404)
        return jsonify(data)
    finally:
        database.close_db(db)


@app.route('/api/players/<int:id>/innings', methods=['GET'])
def player_innings(id):
    db = database.get_db()
    try:
        rows, total = database.get_player_innings_list(db, id, request.args)
        return jsonify({'innings': rows, 'total': total})
    finally:
        database.close_db(db)


@app.route('/api/players/<int:id>/bowling', methods=['GET'])
def player_bowling(id):
    db = database.get_db()
    try:
        rows, total = database.get_player_bowling_list(db, id, request.args)
        return jsonify({'spells': rows, 'total': total})
    finally:
        database.close_db(db)


@app.route('/api/players/<int:id>/wagon-wheel', methods=['GET'])
def player_wagon_wheel(id):
    db = database.get_db()
    try:
        fmt = request.args.get('format')
        rows = database.get_player_wagon_wheel(db, id, fmt)
        return jsonify({'deliveries': rows, 'count': len(rows)})
    finally:
        database.close_db(db)


# ── Venues ────────────────────────────────────────────────────────────────────

@app.route('/api/venues', methods=['GET'])
def get_venues():
    db = database.get_db()
    try:
        venues = database.get_venues(db)
        # Optional filter: ?hundred=1 returns only Hundred venues
        hundred_filter = request.args.get('hundred')
        if hundred_filter == '1':
            venues = [v for v in venues if v.get('is_hundred_venue')]
        elif hundred_filter == '0':
            venues = [v for v in venues if not v.get('is_hundred_venue')]
        return jsonify({"venues": venues, "count": len(venues)})
    finally:
        database.close_db(db)


@app.route('/api/venues/<int:id>', methods=['GET'])
def get_venue(id):
    db = database.get_db()
    try:
        data = database.get_venue_profile(db, id)
        if not data:
            return err("Venue not found", 404)
        return jsonify(data)
    finally:
        database.close_db(db)


@app.route('/api/venues', methods=['POST'])
def create_venue():
    data = request.get_json() or {}
    if not data.get('name'):
        return err("name is required")
    db = database.get_db()
    try:
        new_id = database.create_venue(db, data)
        venue = database.get_venue(db, new_id)
        return jsonify({"venue": venue}), 201
    finally:
        database.close_db(db)


# ── Matches ───────────────────────────────────────────────────────────────────

@app.route('/api/matches/start', methods=['POST'])
def start_match():
    data = request.get_json() or {}
    for field in ('team1_id', 'team2_id', 'format', 'venue_id', 'match_date'):
        if not data.get(field):
            return err(f'{field} is required')
    if data['format'] not in ('Test', 'ODI', 'T20', 'Hundred'):
        return err('format must be Test, ODI, T20 or Hundred')
    scoring_mode = data.get('scoring_mode', 'modern')
    if scoring_mode not in ('classic', 'modern'):
        scoring_mode = 'modern'
    data['scoring_mode'] = scoring_mode
    player_mode = data.get('player_mode', 'ai_vs_ai')
    if player_mode not in ('ai_vs_ai', 'human_vs_ai', 'human_vs_human'):
        player_mode = 'ai_vs_ai'
    data['player_mode'] = player_mode

    # Canon status: explicit value takes priority; otherwise:
    # - standalone single match → exhibition (doesn't pollute career stats)
    # - part of series/tournament/world → canon
    if 'canon_status' in data:
        cs = data['canon_status']
        if cs not in ('canon', 'exhibition'):
            cs = 'exhibition'
        data['canon_status'] = cs
    elif data.get('series_id') or data.get('tournament_id') or data.get('world_id'):
        data['canon_status'] = 'canon'
    else:
        data['canon_status'] = 'exhibition'

    db = database.get_db()
    try:
        match_id = database.create_match(db, data)
        match = database.get_match(db, match_id)
        return jsonify({'match_id': match_id, 'match': match}), 201
    finally:
        database.close_db(db)


@app.route('/api/matches/recent', methods=['GET'])
def recent_matches():
    db = database.get_db()
    try:
        matches = database.get_recent_matches(db)
        for m in matches:
            m['result_string'] = _build_result_description(m, [])
        return jsonify({'matches': matches, 'count': len(matches)})
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>', methods=['GET'])
def get_match_route(id):
    db = database.get_db()
    try:
        state = database.get_match_state(db, id)
        if not state:
            return err('Match not found', 404)
        return jsonify(state)
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/canon-status', methods=['PATCH'])
def set_canon_status(id):
    data = request.get_json() or {}
    new_status = data.get('canon_status')
    if new_status not in ('canon', 'exhibition', 'deleted'):
        return err('canon_status must be canon, exhibition, or deleted')
    note = data.get('note', '')
    db = database.get_db()
    try:
        ok = database.set_match_canon_status(db, id, new_status, note=note)
        if not ok:
            return err('Match not found', 404)
        match = database.get_match(db, id)
        return jsonify({'match': match})
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>', methods=['DELETE'])
def delete_match_route(id):
    data = request.get_json() or {}
    if data.get('confirm') != 'DELETE':
        return err('Soft-delete requires {"confirm":"DELETE"} in request body')
    note = data.get('note', 'Soft deleted')
    db = database.get_db()
    try:
        ok = database.set_match_canon_status(db, id, 'deleted', note=note)
        if not ok:
            return err('Match not found', 404)
        return jsonify({'deleted': True, 'match_id': id})
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/result', methods=['PATCH'])
def edit_match_result(id):
    data = request.get_json() or {}
    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)
        if match.get('status') != 'complete':
            return err('Match is not complete — cannot edit result')
        ok = database.edit_match_result(db, id, data)
        if not ok:
            return err('Failed to edit result')
        updated = database.get_match(db, id)
        return jsonify({'match': updated})
    finally:
        database.close_db(db)


@app.route('/api/almanack/bulk-canon-status', methods=['POST'])
def bulk_canon_status():
    data = request.get_json() or {}
    match_ids = data.get('match_ids', [])
    new_status = data.get('canon_status')
    if new_status not in ('canon', 'exhibition', 'deleted'):
        return err('canon_status must be canon, exhibition, or deleted')
    if not match_ids or not isinstance(match_ids, list):
        return err('match_ids must be a non-empty list')
    note = data.get('note', f'Bulk set to {new_status}')
    db = database.get_db()
    try:
        updated = 0
        for mid in match_ids:
            if database.set_match_canon_status(db, int(mid), new_status, note=note):
                updated += 1
        return jsonify({'updated': updated, 'canon_status': new_status})
    finally:
        database.close_db(db)


@app.route('/api/almanack/audit-log', methods=['GET'])
def audit_log():
    db = database.get_db()
    try:
        entries = database.get_audit_log(db, request.args)
        return jsonify({'entries': entries, 'count': len(entries)})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/reset-stats', methods=['POST'])
def reset_world_stats(id):
    db = database.get_db()
    try:
        count = database.reset_world_stats(db, id)
        return jsonify({'world_id': id, 'matches_reset': count})
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/toss', methods=['POST'])
def match_toss(id):
    data = request.get_json() or {}
    toss_winner_id = data.get('toss_winner_id')
    toss_choice    = data.get('toss_choice')
    if not toss_winner_id or toss_choice not in ('bat', 'field'):
        return err('toss_winner_id and toss_choice (bat|field) required')

    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)
        if match['status'] != 'in_progress':
            return err('Match is not in progress')
        if toss_winner_id not in (match['team1_id'], match['team2_id']):
            return err('toss_winner_id must be one of the match teams')

        # Determine who bats first
        other_id = match['team2_id'] if toss_winner_id == match['team1_id'] else match['team1_id']
        if toss_choice == 'bat':
            batting_team_id  = toss_winner_id
            bowling_team_id  = other_id
        else:
            batting_team_id  = other_id
            bowling_team_id  = toss_winner_id

        database.update_match(db, id, {
            'toss_winner_id': toss_winner_id,
            'toss_choice':    toss_choice,
        })

        _start_innings(db, id, 1, batting_team_id, bowling_team_id)
        state = database.get_match_state(db, id)
        return jsonify(state)
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/ball', methods=['POST'])
def bowl_ball_route(id):
    db = database.get_db()
    try:
        state = database.get_match_state(db, id)
        if not state:
            return err('Match not found', 404)
        if state['match']['status'] != 'in_progress':
            return err('Match is not in progress')
        if not state['current_innings']:
            return err('No active innings — toss not yet taken')

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
            return err('Cannot determine current batters')

        # Select bowler if start of over
        bowler_id = state['current_bowler_id']
        req_data  = request.get_json() or {}
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
                return err('bowler_id required for human-controlled bowling changes')
            if requested_bowler:
                rb = next((b for b in bowler_list if b['player_id'] == requested_bowler), None)
                if fmt == 'Hundred':
                    import hundred_engine as _he
                    balls_this_bowler = (rb['overs_bowled'] * 6 + rb['balls_bowled']) if rb else 0
                    valid = (rb is not None and balls_this_bowler < _he.HUNDRED_BOWLER_MAX)
                else:
                    valid = (rb is not None
                             and rb['player_id'] != state['last_bowler_id']
                             and (cap is None or rb['overs_bowled'] < cap))
                if valid:
                    bowler_id = requested_bowler
                elif human_bowling:
                    return err('Invalid bowler selection for this over')
            if bowler_id is None:
                if fmt == 'Hundred':
                    import hundred_engine as _he
                    _b100_list = [
                        {**b, 'balls_bowled': b['overs_bowled'] * 6 + b['balls_bowled']}
                        for b in bowler_list
                    ]
                    # Derive bowling end from legal balls bowled (toggles every 2 sets of 5)
                    _legal_bowled = over_number * 6 + ball_in_over
                    _complete_sets = _legal_bowled // _he.HUNDRED_SET_SIZE
                    _end_block = _complete_sets // _he.HUNDRED_MAX_SETS
                    _hundred_end = 'pavilion' if _end_block % 2 == 0 else 'nursery'
                    _sets_this_end = (_complete_sets % _he.HUNDRED_MAX_SETS) + 1
                    sel = _he.select_hundred_bowler(
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
            return err('Cannot find striker or bowler data')

        # ── Roll the ball ──────────────────────────────────────────────────────
        if fmt == 'Hundred':
            import hundred_engine as _he
            # Count legal balls bowled so far this innings
            _legal_so_far = over_number * 6 + ball_in_over
            _is_pp = _legal_so_far < _he.HUNDRED_POWERPLAY
            ball_result = _he.bowl_hundred_ball(
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

        # ── Persist delivery ───────────────────────────────────────────────────
        database.insert_delivery(db, {
            'innings_id':          innings_id,
            'over_number':         over_number,
            'ball_number':         del_in_over + 1,
            'bowler_id':           bowler_id,
            'striker_id':          striker_id,
            'non_striker_id':      non_striker_id,
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
        fmt_for_record = fmt  # 'T20' | 'ODI' | 'Test'

        # Previous records (from COMPLETED matches only — current match not yet complete)
        def _prev_batting_record(record_type):
            return database.get_almanack_batting_record(db, fmt_for_record, record_type)

        def _prev_bowling_record(record_type):
            return database.get_almanack_bowling_record(db, fmt_for_record, record_type)

        # 1) Highest individual score
        if is_legal and not is_wicket and runs_scored > 0:
            batter_runs_now = batter_runs_after
            prev = _prev_batting_record('highest_score')
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
            prev = _prev_bowling_record('best_figures')
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
            prev_team = db.execute(
                "SELECT i.total_runs, t.name as team_name "
                "FROM innings i JOIN matches m ON i.match_id=m.id "
                "JOIN teams t ON i.batting_team_id=t.id "
                "WHERE m.format=? AND m.status='complete' "
                "ORDER BY i.total_runs DESC LIMIT 1",
                (fmt_for_record,)
            ).fetchone()
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
            prev_part = db.execute(
                "SELECT pr.runs, pr.batter1_name, pr.batter2_name "
                "FROM partnership_records pr "
                "JOIN innings i ON pr.innings_id=i.id "
                "JOIN matches m ON i.match_id=m.id "
                "WHERE m.format=? AND m.status='complete' "
                "ORDER BY pr.runs DESC LIMIT 1",
                (fmt_for_record,)
            ).fetchone()
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
            prev_six = db.execute(
                "SELECT MAX(bi.sixes) as mx, p.name "
                "FROM batter_innings bi "
                "JOIN innings i ON bi.innings_id=i.id "
                "JOIN matches m ON i.match_id=m.id "
                "JOIN players p ON bi.player_id=p.id "
                "WHERE m.format=? AND m.status='complete'",
                (fmt_for_record,)
            ).fetchone()
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
                prev_low = db.execute(
                    "SELECT i.total_runs, t.name as team_name "
                    "FROM innings i JOIN matches m ON i.match_id=m.id "
                    "JOIN teams t ON i.batting_team_id=t.id "
                    "WHERE m.format=? AND m.status='complete' AND i.total_wickets=10 "
                    "ORDER BY i.total_runs ASC LIMIT 1",
                    (fmt_for_record,)
                ).fetchone()
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

        # ── Build response ────────────────────────────────────────────────────
        fresh_state = database.get_match_state(db, id)
        delivery_row = db.execute(
            "SELECT * FROM deliveries WHERE innings_id=? ORDER BY id DESC LIMIT 1",
            (innings_id,)
        ).fetchone()

        # Hundred-specific state additions
        hundred_state = None
        if fmt == 'Hundred':
            import hundred_engine as _he
            _legal_total = legal_after
            hundred_state = {
                'balls_bowled':    _legal_total,
                'balls_remaining': max(0, _he.HUNDRED_BALLS - _legal_total),
                'is_powerplay':    _legal_total < _he.HUNDRED_POWERPLAY,
                'powerplay_complete': _legal_total >= _he.HUNDRED_POWERPLAY,
                'set_number':      (_legal_total // _he.HUNDRED_SET_SIZE) + 1,
                'ball_in_set':     _legal_total % _he.HUNDRED_SET_SIZE,
                'set_complete':    is_legal and (_legal_total % _he.HUNDRED_SET_SIZE == 0),
                'final_ten':       _legal_total >= 90,
                'final_five':      _legal_total >= 95,
                'final_ball':      _legal_total == 99,
                'progress_bar':    _he.render_hundred_progress_bar(_legal_total),
                'progress_text':   _he.format_hundred_progress(_legal_total),
            }

        return jsonify({
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
        })
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/tension', methods=['GET'])
def match_tension(id):
    """Return match-situation tension data for the Manual mode suggestion banner."""
    db = database.get_db()
    try:
        state = database.get_match_state(db, id)
        if not state:
            return err('Match not found', 404)

        match = state['match']
        if match['status'] != 'in_progress':
            return jsonify({'suggest_manual': False, 'suggestion_reason': None,
                            'suggestion_key': None})

        fmt = state['format']
        inn = state['current_innings']
        if not inn:
            return jsonify({'suggest_manual': False, 'suggestion_reason': None,
                            'suggestion_key': None})

        max_overs    = state['max_overs'] or 0
        over_number  = state['over_number'] or 0
        ball_in_over = state['ball_in_over'] or 0

        overs_completed = over_number + ball_in_over / 6.0
        overs_remaining = max(0.0, max_overs - overs_completed) if max_overs else None

        total_wickets     = inn.get('total_wickets', 0) or 0
        total_runs        = inn.get('total_runs', 0) or 0
        wickets_remaining = 10 - total_wickets
        innings_number    = inn.get('innings_number', 1)

        target = state.get('target')
        runs_required = (target - total_runs) if (target and target > total_runs) else None

        rrr = None
        if runs_required and overs_remaining and overs_remaining > 0:
            rrr = runs_required / overs_remaining

        # Current striker runs
        current_batter_runs = 0
        striker_id = state.get('current_striker_id')
        if striker_id:
            bi = next(
                (b for b in state.get('batter_innings', [])
                 if b['player_id'] == striker_id and b['status'] == 'batting'),
                None
            )
            if bi:
                current_batter_runs = bi.get('runs', 0) or 0

        is_last_wicket = (wickets_remaining <= 1)
        is_tied        = (runs_required == 0) if runs_required is not None else False

        suggest_manual   = False
        suggestion_reason = None
        suggestion_key   = None

        if (fmt == 'T20' and overs_remaining is not None and overs_remaining <= 2
                and runs_required is not None and 0 < runs_required < 15):
            suggest_manual    = True
            suggestion_reason = '🎲 Switch to Manual for the finish?'
            suggestion_key    = 't20_finish'
        elif is_last_wicket:
            suggest_manual    = True
            suggestion_reason = '🎲 Last wicket — Manual mode for the drama?'
            suggestion_key    = 'last_wicket'
        elif current_batter_runs >= 95:
            suggest_manual    = True
            suggestion_reason = '🎲 Century incoming — Manual mode?'
            suggestion_key    = 'century'
        elif rrr is not None and rrr > 12:
            suggest_manual    = True
            suggestion_reason = '🎲 Pressure is on — Manual mode?'
            suggestion_key    = 'high_rrr'
        elif is_tied and overs_remaining is not None and overs_remaining <= 1:
            suggest_manual    = True
            suggestion_reason = "🎲 It's a tie-breaker — go Manual!"
            suggestion_key    = 'tied'

        return jsonify({
            'format':              fmt,
            'innings_number':      innings_number,
            'overs_remaining':     overs_remaining,
            'runs_required':       runs_required,
            'wickets_remaining':   wickets_remaining,
            'run_rate_required':   round(rrr, 2) if rrr else None,
            'current_batter_runs': current_batter_runs,
            'is_last_wicket':      is_last_wicket,
            'is_tied':             is_tied,
            'suggest_manual':      suggest_manual,
            'suggestion_reason':   suggestion_reason,
            'suggestion_key':      suggestion_key,
        })
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/fast-sim', methods=['POST'])
def fast_sim(id):
    db = database.get_db()
    try:
        state = database.get_match_state(db, id)
        if not state:
            return err('Match not found', 404)
        if state['match']['status'] != 'in_progress':
            return err('Match is not in progress')
        if not state['current_innings']:
            return err('No active innings')

        fmt = state['format']

        # Sim all remaining innings (including current)
        while state['current_innings']:
            innings    = state['current_innings']
            innings_id = state['current_innings_id']
            max_overs  = state['max_overs']
            target     = state['target']

            batting_players = [
                {
                    'player_id':       p['id'],
                    'batting_rating':  p['batting_rating'],
                    'batting_hand':    p['batting_hand'],
                    'batting_position': p['batting_position'],
                }
                for p in sorted(state['batting_team_players'],
                                key=lambda x: x['batting_position'] or 99)
            ]
            bowling_players = [
                {
                    'player_id':      p['id'],
                    'bowling_type':   p['bowling_type'],
                    'bowling_rating': p['bowling_rating'],
                }
                for p in state['bowling_team_players'] if p['bowling_type'] != 'none'
            ]

            if fmt == 'Hundred':
                import hundred_engine as _he
                result = _he.simulate_hundred_innings_fast(
                    batting_players, bowling_players, target
                )
            else:
                result = game_engine.simulate_innings_fast(
                    batting_players, bowling_players, fmt, target,
                    scoring_mode=state['match'].get('scoring_mode', 'modern')
                )

            # Persist batter scores
            for bs in result['batter_scores']:
                row = next(
                    (b for b in state['batter_innings'] if b['player_id'] == bs['player_id']),
                    None
                )
                if row:
                    database.update_batter_innings(db, row['id'], {
                        'runs':          bs['runs'],
                        'balls_faced':   bs['balls'],
                        'fours':         bs['fours'],
                        'sixes':         bs['sixes'],
                        'dismissal_type': bs['dismissal_type'],
                        'not_out':       1 if bs['not_out'] else 0,
                        'status':        'not_out' if bs['not_out'] else 'dismissed',
                    })

            # Persist bowler figures
            for bf in result['bowler_figures']:
                row = next(
                    (b for b in state['bowler_innings'] if b['player_id'] == bf['player_id']),
                    None
                )
                if row:
                    if fmt == 'Hundred':
                        # Hundred: track balls not overs; convert for DB storage
                        total_balls = bf['balls']
                        overs_full  = total_balls // 6
                        balls_rem   = total_balls % 6
                        database.update_bowler_innings(db, row['id'], {
                            'overs':        overs_full,
                            'balls':        balls_rem,
                            'runs_conceded': bf['runs'],
                            'wickets':      bf['wickets'],
                            'maidens':      0,
                        })
                    else:
                        database.update_bowler_innings(db, row['id'], {
                            'overs':        bf['overs'],
                            'balls':        bf['balls'],
                            'runs_conceded': bf['runs'],
                            'wickets':      bf['wickets'],
                            'maidens':      bf['maidens'],
                        })

            # Persist fall of wickets
            for fow in result.get('fall_of_wickets', []):
                if fmt == 'Hundred':
                    # Hundred uses balls, not overs
                    fow_overs = round(fow['balls'] / 6, 2)
                else:
                    fow_overs = fow['overs']
                database.insert_fall_of_wicket(
                    db, innings_id,
                    fow['wicket'], fow['score'], fow_overs, fow['player_id']
                )

            if fmt == 'Hundred':
                balls_bowled = result.get('total_balls_bowled', 0)
                overs_dec = round(balls_bowled / 6, 2)
            else:
                overs_dec = result['overs_completed']
            innings_update = {
                'total_runs':     result['total_runs'],
                'total_wickets':  result['total_wickets'],
                'overs_completed': overs_dec,
                'runs_at_100_overs': result.get('runs_at_100_overs'),
                'wickets_at_100_overs': result.get('wickets_at_100_overs'),
                'runs_at_110_overs': result.get('runs_at_110_overs'),
                'wickets_at_110_overs': result.get('wickets_at_110_overs'),
                'extras_wides':   result['extras']['wides'],
                'extras_noballs': result['extras']['no_balls'],
                'extras_byes':    result['extras']['byes'],
                'extras_legbyes': result['extras']['leg_byes'],
                'status':         'complete',
            }
            if fmt == 'Hundred':
                innings_update['balls_used']        = result.get('total_balls_bowled', 0)
                innings_update['powerplay_runs']    = result.get('powerplay_score', 0)
                innings_update['powerplay_wickets'] = result.get('powerplay_wickets', 0)
                innings_update['death_runs']        = result.get('death_score', 0)
                innings_update['death_wickets']     = result.get('death_wickets', 0)
                if result.get('strategic_timeout_at_ball') is not None:
                    innings_update['strategic_timeout_ball'] = result['strategic_timeout_at_ball']
            database.update_innings(db, innings_id, _apply_innings_cutoff_snapshots(innings, innings_update))

            # Next innings or complete
            all_innings_fresh = database.get_innings(db, id)
            nxt = _determine_next_innings(state['match'], all_innings_fresh, fmt)
            if nxt:
                batting_tid, bowling_tid, next_inn_num = nxt
                _start_innings(db, id, next_inn_num, batting_tid, bowling_tid)
                state = database.get_match_state(db, id)
            else:
                all_innings_fresh2 = database.get_innings(db, id)
                match_fresh = database.get_match(db, id)
                _calculate_and_complete_match(db, id, match_fresh, all_innings_fresh2)
                break

        return scorecard_response(id, db)
    finally:
        database.close_db(db)


def _build_sim_state(state):
    """Convert get_match_state() result into the dict format expected by game_engine.simulate_to()."""
    fmt     = state['format']
    innings = state['current_innings']
    if not innings:
        return None

    innings_num = innings['innings_number']
    max_overs   = state['max_overs']

    # Batting players, ordered by batting position
    all_batting = {p['id']: p for p in state['batting_team_players']}
    batter_rows = sorted(state['batter_innings'], key=lambda b: b.get('batting_position') or 99)

    batting_players = []
    for bi in batter_rows:
        p = all_batting.get(bi['player_id'], {})
        batting_players.append({
            'player_id':     bi['player_id'],
            'name':          p.get('name', f'Player {bi["player_id"]}'),
            'batting_rating': p.get('batting_rating', 3),
            'runs':           bi.get('runs', 0) or 0,
            'balls':          bi.get('balls_faced', 0) or 0,
            'dismissed':      bi.get('status') == 'dismissed',
            'in':             bi.get('status') == 'batting',
        })

    striker_id     = state['current_striker_id']
    non_striker_id = state['current_non_striker_id']
    striker_idx     = next((i for i, p in enumerate(batting_players) if p['player_id'] == striker_id), 0)
    non_striker_idx = next((i for i, p in enumerate(batting_players) if p['player_id'] == non_striker_id), 1)
    next_batter_idx = next((i for i, p in enumerate(batting_players)
                            if not p['dismissed'] and not p['in']), len(batting_players))

    # Bowling players
    all_bowling = {p['id']: p for p in state['bowling_team_players']}
    bowling_players = []
    for bwi in state['bowler_innings']:
        p = all_bowling.get(bwi['player_id'], {})
        bt = bwi.get('bowling_type') or p.get('bowling_type', 'pace')
        if p.get('bowling_type', 'none') == 'none':
            continue
        bowling_players.append({
            'player_id':    bwi['player_id'],
            'name':         p.get('name', f'Player {bwi["player_id"]}'),
            'bowling_type': bt,
            'bowling_rating': p.get('bowling_rating', 3),
            'overs_bowled': bwi.get('overs', 0) or 0,
            'balls_bowled': bwi.get('balls', 0) or 0,
            'runs':         bwi.get('runs_conceded', 0) or 0,
            'wickets':      bwi.get('wickets', 0) or 0,
            'maidens':      bwi.get('maidens', 0) or 0,
            '_this_over_runs': 0,
        })

    return {
        'format':          fmt,
        'scoring_mode':    state['match'].get('scoring_mode', 'modern'),
        'max_overs':       max_overs,
        'target':          state['target'],
        'innings_number':  innings_num,
        'over_number':     state['over_number'],
        'ball_in_over':    state['ball_in_over'],
        'is_free_hit':     state['is_free_hit'],
        'total_runs':      innings['total_runs'],
        'total_wickets':   innings['total_wickets'],
        'batting_players': batting_players,
        'striker_idx':     striker_idx,
        'non_striker_idx': non_striker_idx,
        'next_batter_idx': next_batter_idx,
        'bowling_players': bowling_players,
        'last_bowler_id':  state['last_bowler_id'],
        'current_bowler_id': state['current_bowler_id'],
    }


def _persist_sim_result(db, match_id, match_state, sim_result):
    """Write simulate_to() results back to the database."""
    innings_id    = match_state['current_innings_id']
    innings       = match_state['current_innings']
    updated_state = sim_result['state']
    fmt           = match_state['format']

    # Batter innings
    bi_by_pid = {b['player_id']: b for b in match_state['batter_innings']}
    for bp in updated_state['batting_players']:
        row = bi_by_pid.get(bp['player_id'])
        if not row:
            continue
        upd = {'runs': bp.get('runs', 0), 'balls_faced': bp.get('balls', 0)}
        if bp.get('dismissed') and row.get('status') != 'dismissed':
            upd['status'] = 'dismissed'
        elif bp.get('in') and row.get('status') == 'yet_to_bat':
            upd['status'] = 'batting'
        database.update_batter_innings(db, row['id'], upd)

    # Bowler innings
    bwi_by_pid = {b['player_id']: b for b in match_state['bowler_innings']}
    for bw in updated_state['bowler_map'].values():
        row = bwi_by_pid.get(bw['player_id'])
        if not row:
            continue
        total_b = bw.get('balls_bowled', 0)
        overs_b = bw.get('overs_bowled', 0)
        database.update_bowler_innings(db, row['id'], {
            'overs':        overs_b,
            'balls':        total_b % 6,
            'runs_conceded': bw.get('runs', 0),
            'wickets':      bw.get('wickets', 0),
            'maidens':      bw.get('maidens', 0),
        })

    # Innings totals
    new_over = updated_state['over_number']
    new_ball = updated_state['ball_in_over']
    inn_upd  = {
        'total_runs':      updated_state['total_runs'],
        'total_wickets':   updated_state['total_wickets'],
        'overs_completed': new_over + new_ball / 10,
        'runs_at_100_overs': updated_state.get('runs_at_100_overs'),
        'wickets_at_100_overs': updated_state.get('wickets_at_100_overs'),
        'runs_at_110_overs': updated_state.get('runs_at_110_overs'),
        'wickets_at_110_overs': updated_state.get('wickets_at_110_overs'),
    }
    if sim_result['innings_complete']:
        inn_upd['status'] = 'complete'
    database.update_innings(db, innings_id, _apply_innings_cutoff_snapshots(innings, inn_upd))

    # Handle innings → match completion
    match_complete = False
    if sim_result['innings_complete']:
        all_innings_fresh = database.get_innings(db, match_id)
        nxt = _determine_next_innings(match_state['match'], all_innings_fresh, fmt)
        if nxt:
            batting_tid, bowling_tid, next_inn_num = nxt
            _start_innings(db, match_id, next_inn_num, batting_tid, bowling_tid)
        else:
            match_complete = True
            all_innings_fresh2 = database.get_innings(db, match_id)
            match_fresh = database.get_match(db, match_id)
            _calculate_and_complete_match(db, match_id, match_fresh, all_innings_fresh2)
            if match_fresh.get('series_id'):
                _update_series_after_match(db, match_fresh['series_id'])
            if match_fresh.get('tournament_id'):
                _update_tournament_nrr(db, match_fresh['tournament_id'], match_fresh)

    return match_complete


@app.route('/api/matches/<int:id>/simulate', methods=['POST'])
def simulate_match(id):
    data   = request.get_json() or {}
    target = data.get('target', 'over')
    valid  = ('wicket', 'over', 'session', 'day', 'innings', 'match')
    if target not in valid:
        return err(f'target must be one of: {", ".join(valid)}')

    db = database.get_db()
    try:
        state = database.get_match_state(db, id)
        if not state:
            return err('Match not found', 404)
        if state['match']['status'] != 'in_progress':
            return err('Match is not in progress')
        if not state['current_innings']:
            return err('No active innings — take the toss first')

        # Aggregate digest across potentially multiple innings (for 'match' target)
        agg_digest = {
            'balls_bowled': 0, 'runs_scored': 0, 'wickets_fallen': 0,
            'overs_completed': 0, 'key_events': [], 'wicket_events': [],
            'start_score': None, 'end_score': None, 'result_string': None,
        }

        overall_match_complete = False
        loop_count = 0
        max_loops  = 10  # safeguard for multi-innings
        result     = None

        while loop_count < max_loops:
            loop_count += 1
            sim_state = _build_sim_state(state)
            if sim_state is None:
                break

            if agg_digest['start_score'] is None:
                agg_digest['start_score'] = sim_state['total_runs']
                agg_digest['start_wkts']  = sim_state['total_wickets']

            result = game_engine.simulate_to(target, sim_state)
            digest = result['sim_digest']

            agg_digest['balls_bowled']    += digest['balls_bowled']
            agg_digest['runs_scored']     += digest['runs_scored']
            agg_digest['wickets_fallen']  += digest['wickets_fallen']
            agg_digest['overs_completed'] += digest['overs_completed']
            agg_digest['key_events'].extend(digest.get('key_events', []))
            agg_digest['wicket_events'].extend(digest.get('wicket_events', []))
            agg_digest['result_string'] = digest.get('result_string')

            overall_match_complete = _persist_sim_result(db, id, state, result)

            if overall_match_complete or target != 'match':
                break

            # Reload state for next innings (target=='match' loops)
            state = database.get_match_state(db, id)
            if not state or not state['current_innings']:
                break

        # Build final end score from fresh DB state
        fresh = database.get_match_state(db, id)
        if fresh and fresh['current_innings']:
            inn = fresh['current_innings']
            agg_digest['end_score'] = format_score(inn['total_runs'], inn['total_wickets'])
        agg_digest['key_events'] = agg_digest['key_events'][:5]

        result_str = agg_digest.get('result_string')
        if overall_match_complete and not result_str:
            match_rec = database.get_match(db, id)
            all_inn   = database.get_innings(db, id)
            result_str = _build_result_description(match_rec, all_inn)

        return jsonify({
            'sim_digest':    agg_digest,
            'result_string': result_str,
            'innings_complete': result['innings_complete'] if result is not None else False,
            'match_complete':  overall_match_complete,
        })
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/declare', methods=['POST'])
def declare(id):
    db = database.get_db()
    try:
        state = database.get_match_state(db, id)
        if not state:
            return err('Match not found', 404)
        if state['format'] != 'Test':
            return err('Declaration only valid in Test matches')
        if not state['current_innings']:
            return err('No active innings')

        innings_id = state['current_innings_id']
        database.update_innings(db, innings_id, {'status': 'complete', 'declared': 1})

        all_innings_fresh = database.get_innings(db, id)
        nxt = _determine_next_innings(state['match'], all_innings_fresh, 'Test')
        if nxt:
            batting_tid, bowling_tid, next_inn_num = nxt
            _start_innings(db, id, next_inn_num, batting_tid, bowling_tid)

        fresh_state = database.get_match_state(db, id)
        return jsonify(fresh_state)
    finally:
        database.close_db(db)


def _update_series_after_match(db, series_id):
    """After a match completes, check if the series is now decided."""
    import json as _json
    series = database.get_series(db, series_id)
    if not series or series['status'] == 'complete':
        return
    all_matches = database.get_series_matches(db, series_id)
    completed   = [m for m in all_matches if m['status'] == 'complete']
    team1_id    = series['team1_id']
    team2_id    = series['team2_id']
    wins1 = sum(1 for m in completed if m.get('winning_team_id') == team1_id)
    wins2 = sum(1 for m in completed if m.get('winning_team_id') == team2_id)

    total_matches = None
    if series.get('settings_json'):
        try:
            settings = _json.loads(series['settings_json'])
            total_matches = settings.get('total_matches')
        except Exception:
            pass
    if total_matches is None:
        total_matches = len(all_matches)

    remaining = max(0, total_matches - len(completed))
    winner_id = None
    if wins1 > wins2 + remaining:
        winner_id = team1_id
    elif wins2 > wins1 + remaining:
        winner_id = team2_id
    elif remaining == 0 and wins1 != wins2:
        winner_id = team1_id if wins1 > wins2 else team2_id

    if winner_id is not None or remaining == 0:
        database.update_series(db, series_id, {
            'status': 'complete',
            'winner_team_id': winner_id,
        })


@app.route('/api/matches/<int:id>/complete', methods=['POST'])
def complete_match(id):
    data = request.get_json() or {}
    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)

        # Only run result calculation if not already complete
        if match['status'] != 'complete':
            all_innings = database.get_innings(db, id)
            _calculate_and_complete_match(db, id, match, all_innings)
            # Guard: verify result_type was determined before proceeding
            post_calc = database.get_match(db, id)
            if not post_calc.get('result_type'):
                return err('Cannot complete match — result could not be determined. Ensure all innings are complete.', 400)

        # Apply POM and notes
        updates = {'status': 'complete'}
        if data.get('player_of_match_id'):
            updates['player_of_match_id'] = int(data['player_of_match_id'])
        if data.get('match_notes'):
            updates['match_notes'] = data['match_notes']
        database.update_match(db, id, updates)

        # Save journal entry if notes provided
        if data.get('match_notes'):
            database.save_journal_entry(db, id, data['match_notes'], 'match_report')

        # World records
        updated = database.get_match(db, id)
        if updated.get('world_id'):
            _check_world_records(db, updated['world_id'], id, updated)

        # Series tracking
        series_won = None
        if updated.get('series_id'):
            s_before = database.get_series(db, updated['series_id'])
            was_complete = s_before and s_before['status'] == 'complete'
            _update_series_after_match(db, updated['series_id'])
            if not was_complete:
                s = database.get_series(db, updated['series_id'])
                if s and s['status'] == 'complete' and s.get('winner_team_id'):
                    series_won = {
                        'name':        s['name'],
                        'format':      s.get('format'),
                        'winner_name': s.get('winner_name'),
                        'start_date':  s.get('start_date'),
                    }

        # Tournament NRR tracking
        tournament_won = None
        if updated.get('tournament_id'):
            t_before = db.execute(
                "SELECT status FROM tournaments WHERE id=?", (updated['tournament_id'],)
            ).fetchone()
            t_was_complete = t_before and t_before['status'] == 'complete'
            _update_tournament_nrr(db, updated['tournament_id'], updated)
            if not t_was_complete:
                t = db.execute(
                    "SELECT t.name, t.format, t.start_date, t.status, wt.name AS winner_name "
                    "FROM tournaments t LEFT JOIN teams wt ON t.winner_team_id = wt.id "
                    "WHERE t.id=?", (updated['tournament_id'],)
                ).fetchone()
                if t and t['status'] == 'complete' and t['winner_name']:
                    tournament_won = {
                        'name':        t['name'],
                        'format':      t['format'],
                        'winner_name': t['winner_name'],
                        'start_date':  t['start_date'],
                    }

        result_string = _build_result_description(updated, database.get_innings(db, id))
        return jsonify({
            'success': True,
            'result': {
                'result_type':        updated.get('result_type'),
                'winning_team_name':  updated.get('winning_team_name'),
                'margin_runs':        updated.get('margin_runs'),
                'margin_wickets':     updated.get('margin_wickets'),
                'player_of_match_name': updated.get('player_of_match_name'),
                'result_string':      result_string,
            },
            'series_won':     series_won,
            'tournament_won': tournament_won,
        })
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/journal-prompts', methods=['GET'])
def journal_prompts(id):
    prompts = random.sample(game_engine.JOURNAL_PROMPTS, min(5, len(game_engine.JOURNAL_PROMPTS)))
    return jsonify({'prompts': prompts})


@app.route('/api/matches/<int:id>/journal', methods=['GET'])
def match_journal(id):
    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)
        entries = database.get_journal_entries(db, id)
        return jsonify({'entries': entries, 'count': len(entries)})
    finally:
        database.close_db(db)


# ── Journal ───────────────────────────────────────────────────────────────────

@app.route('/api/journal', methods=['GET'])
def journal_list():
    db = database.get_db()
    try:
        search = request.args.get('search', '').strip() or None
        fmt    = request.args.get('format', '').strip() or None
        match_id_filter = request.args.get('match_id', type=int)
        page   = max(1, request.args.get('page', 1, type=int))
        limit  = 20
        offset = (page - 1) * limit

        if match_id_filter:
            entries = database.get_journal_entries(db, match_id_filter)
            return jsonify({'entries': entries, 'count': len(entries), 'page': 1, 'total_pages': 1})

        entries = database.get_all_journal_entries(db, search=search, format_filter=fmt,
                                                   limit=limit, offset=offset)
        # total count for pagination
        total = database.count_journal_entries(db, search=search, format_filter=fmt)
        total_pages = max(1, -(-total // limit))  # ceiling division
        return jsonify({'entries': entries, 'count': total, 'page': page,
                        'total_pages': total_pages})
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/scorecard', methods=['GET'])
def scorecard(id):
    db = database.get_db()
    try:
        return scorecard_response(id, db)
    finally:
        database.close_db(db)


def scorecard_response(match_id, db):
    match = database.get_match(db, match_id)
    if not match:
        return err('Match not found', 404)
    all_innings = database.get_innings(db, match_id)

    innings_data = []
    for inn in all_innings:
        batters = database.get_batter_innings(db, inn['id'])
        for b in batters:
            rf = b['balls_faced'] or 0
            b['strike_rate'] = round(b['runs'] / rf * 100, 1) if rf > 0 else 0

        bowlers = database.get_bowler_innings(db, inn['id'])
        for bw in bowlers:
            overs_f = bw['overs'] + bw['balls'] / 6
            bw['economy'] = round(bw['runs_conceded'] / overs_f, 2) if overs_f > 0 else 0
            bw['overs_str'] = f"{bw['overs']}.{bw['balls']}"

        fow  = database.get_fall_of_wickets(db, inn['id'])
        extras_total = (inn.get('extras_byes', 0) or 0) + \
                       (inn.get('extras_legbyes', 0) or 0) + \
                       (inn.get('extras_wides', 0) or 0) + \
                       (inn.get('extras_noballs', 0) or 0)

        inn_dict = {
            'innings_number':   inn['innings_number'],
            'batting_team_id':  inn['batting_team_id'],
            'batting_team_name': inn['batting_team_name'],
            'bowling_team_name': inn['bowling_team_name'],
            'total_runs':       inn['total_runs'],
            'total_wickets':    inn['total_wickets'],
            'overs_completed':  inn['overs_completed'],
            'declared':         bool(inn['declared']),
            'status':           inn['status'],
            'batters':          batters,
            'bowlers':          bowlers,
            'fall_of_wickets':  fow,
            'extras': {
                'byes':     inn.get('extras_byes', 0) or 0,
                'leg_byes': inn.get('extras_legbyes', 0) or 0,
                'wides':    inn.get('extras_wides', 0) or 0,
                'no_balls': inn.get('extras_noballs', 0) or 0,
                'total':    extras_total,
            },
        }
        # Hundred-specific fields
        if match.get('format') == 'Hundred':
            balls_used = inn.get('balls_used') or 0
            inn_dict['balls_used']        = balls_used
            inn_dict['balls_remaining']   = max(0, 100 - balls_used)
            inn_dict['powerplay_score']   = inn.get('powerplay_runs', 0) or 0
            inn_dict['powerplay_wickets'] = inn.get('powerplay_wickets', 0) or 0
            inn_dict['death_score']       = inn.get('death_runs', 0) or 0
            inn_dict['death_wickets']     = inn.get('death_wickets', 0) or 0
            inn_dict['strategic_timeout_ball'] = inn.get('strategic_timeout_ball')
            # Per-bowler: convert to balls-only display
            for bw in bowlers:
                total_balls_bw = bw['overs'] * 6 + bw['balls']
                bw['total_balls'] = total_balls_bw
                bw['balls_remaining'] = max(0, 20 - total_balls_bw)
        innings_data.append(inn_dict)

    return jsonify({
        'match':        match,
        'innings':      innings_data,
        'result_string': _build_result_description(match, all_innings),
    })


@app.route('/api/matches/<int:id>/player-mode', methods=['GET'])
def match_player_mode(id):
    """Return the player mode and human team for a match."""
    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)
        return jsonify({
            'player_mode':   match.get('player_mode', 'ai_vs_ai'),
            'human_team_id': match.get('human_team_id'),
            'team1_id':      match.get('team1_id'),
            'team2_id':      match.get('team2_id'),
            'team1_name':    match.get('team1_name'),
            'team2_name':    match.get('team2_name'),
        })
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/ai-decision', methods=['POST'])
def ai_decision(id):
    """
    Ask the AI captain for a decision.
    Body: { "decision_type": str, "innings_id": int, "context": {} }
    """
    data  = request.get_json() or {}
    dtype = data.get('decision_type', 'bowling_change')
    ctx   = data.get('context', {})

    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)
        fmt = match['format']

        if dtype == 'bowling_change':
            bowlers = ctx.get('bowlers', [])
            innings_state = ctx.get('innings_state', {})
            chosen = ai_captain.choose_bowler(bowlers, innings_state, fmt)
            return jsonify({'decision': 'bowling_change', 'bowler_id': chosen})

        elif dtype == 'declare':
            result = ai_captain.should_declare(
                ctx.get('innings_number', 1),
                ctx.get('lead', 0),
                ctx.get('total_wickets', 0),
                ctx.get('overs_completed', 0),
                ctx.get('estimated_overs_remaining', 0),
            )
            return jsonify({'decision': 'declare', 'should_declare': result})

        elif dtype == 'follow_on':
            result = ai_captain.should_enforce_follow_on(
                ctx.get('lead', 0),
                ctx.get('bowling_team_bowlers', []),
                ctx.get('total_overs_bowled', 0),
            )
            return jsonify({'decision': 'follow_on', 'should_enforce': result})

        elif dtype == 'nightwatchman':
            result = ai_captain.should_send_nightwatchman(
                ctx.get('wickets_fallen', 0),
                ctx.get('overs_to_notional_close', 99),
                ctx.get('batting_position', 11),
            )
            return jsonify({'decision': 'nightwatchman', 'send': result})

        else:
            return err(f'Unknown decision_type: {dtype}')
    finally:
        database.close_db(db)


@app.route('/api/matches/<int:id>/deliveries', methods=['GET'])
def deliveries(id):
    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)
        rows = database.get_all_deliveries_for_match(db, id)
        for r in rows:
            r['over_ball'] = f"{r['over_number']}.{r['ball_number']}"
        return jsonify({'deliveries': rows, 'count': len(rows)})
    finally:
        database.close_db(db)


# ── Series ────────────────────────────────────────────────────────────────────

@app.route('/api/series', methods=['GET'])
def list_series():
    db = database.get_db()
    try:
        series = database.get_series_list(db)
        return jsonify({'series': series})
    finally:
        database.close_db(db)


@app.route('/api/series', methods=['POST'])
def create_series():
    import json as _json
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    fmt = data.get('format')
    team1_id = data.get('team1_id')
    team2_id = data.get('team2_id')
    num_matches = int(data.get('num_matches', 3))
    venue_ids = data.get('venue_ids', [])
    start_date = data.get('start_date')
    world_id = data.get('world_id')

    if not name or not fmt or not team1_id or not team2_id:
        return err('name, format, team1_id and team2_id are required')
    if fmt not in ('Test', 'ODI', 'T20', 'Hundred'):
        return err('format must be Test, ODI, T20 or Hundred')
    if num_matches not in (2, 3, 5, 7):
        return err('num_matches must be 2, 3, 5 or 7')
    if not venue_ids:
        return err('at least one venue_id required')

    db = database.get_db()
    try:
        series_id = database.create_series(db, {
            'name': name,
            'format': fmt,
            'team1_id': team1_id,
            'team2_id': team2_id,
            'world_id': world_id,
            'start_date': start_date,
            'series_type': 'bilateral',
            'settings_json': _json.dumps({'total_matches': num_matches}),
        })
        rows = []
        for i in range(num_matches):
            venue_id = venue_ids[i % len(venue_ids)]
            rows.append({
                'tournament_id': None,
                'series_id': series_id,
                'world_id': world_id,
                'scheduled_date': start_date,
                'venue_id': venue_id,
                'team1_id': team1_id,
                'team2_id': team2_id,
                'fixture_type': 'league',
            })
        database.bulk_create_fixtures(db, rows)
        fixtures = database.get_fixtures(db, series_id=series_id)
        return jsonify({'series_id': series_id, 'fixtures': fixtures})
    finally:
        database.close_db(db)


@app.route('/api/series/<int:id>', methods=['GET'])
def get_series(id):
    import json as _json
    db = database.get_db()
    try:
        series = database.get_series(db, id)
        if not series:
            return err('Series not found', 404)
        fixtures = database.get_fixtures(db, series_id=id)
        matches = database.get_series_matches(db, id)
        team1_id = series['team1_id']
        team2_id = series['team2_id']
        completed = [m for m in matches if m['status'] == 'complete']
        wins1 = sum(1 for m in completed if m.get('winning_team_id') == team1_id)
        wins2 = sum(1 for m in completed if m.get('winning_team_id') == team2_id)
        total_matches = num_played = len(completed)
        if series.get('settings_json'):
            try:
                total_matches = _json.loads(series['settings_json']).get('total_matches', total_matches)
            except Exception:
                pass
        remaining = max(0, total_matches - num_played)
        to_win = total_matches // 2 + 1
        can_be_won = (
            series['status'] != 'complete' and (
                wins1 + remaining >= to_win or wins2 + remaining >= to_win
            )
        )
        return jsonify({
            'series': series,
            'fixtures': fixtures,
            'matches': matches,
            'score': {'team1_wins': wins1, 'team2_wins': wins2, 'played': num_played, 'total': total_matches},
            'can_be_won': can_be_won,
        })
    finally:
        database.close_db(db)


@app.route('/api/series/<int:id>/complete', methods=['PUT'])
def complete_series(id):
    data = request.get_json() or {}
    db = database.get_db()
    try:
        series = database.get_series(db, id)
        if not series:
            return err('Series not found', 404)
        database.update_series(db, id, {
            'status': 'complete',
            'winner_team_id': data.get('winner_team_id'),
        })
        return jsonify({'success': True})
    finally:
        database.close_db(db)


# ── Tournaments ───────────────────────────────────────────────────────────────

def _round_robin_pairs(teams):
    """All unique pairs from a list of teams."""
    pairs = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            pairs.append((teams[i], teams[j]))
    return pairs


def _cricket_overs_to_decimal(overs_val, fallback=0.0):
    """Convert cricket-notation overs (e.g. 3.4 = 3 overs 4 balls) to decimal overs."""
    try:
        s = str(float(overs_val))
        int_part, _, frac_part = s.partition('.')
        balls = int(frac_part[:1]) if frac_part else 0
        return int(int_part) + balls / 6
    except (TypeError, ValueError):
        return fallback


def _update_tournament_nrr(db, tournament_id, match):
    """Recalculate NRR for both teams in a completed tournament match."""
    all_matches = db.execute(
        "SELECT m.*, i1.total_runs as inn1_runs, i1.overs_completed as inn1_overs, "
        " i1.total_wickets as inn1_wickets, i1.batting_team_id as inn1_bat, "
        " i2.total_runs as inn2_runs, i2.overs_completed as inn2_overs, "
        " i2.total_wickets as inn2_wickets, i2.batting_team_id as inn2_bat "
        "FROM matches m "
        "LEFT JOIN innings i1 ON i1.match_id = m.id AND i1.innings_number = 1 "
        "LEFT JOIN innings i2 ON i2.match_id = m.id AND i2.innings_number = 2 "
        "WHERE m.tournament_id = ? AND m.status = 'complete'",
        (tournament_id,)
    ).fetchall()

    # Get all team IDs in this tournament
    tt_rows = database.get_tournament_teams(db, tournament_id)
    for tt in tt_rows:
        tid = tt['team_id']
        rs = rc = of = ob = played = won = lost = drawn = nr = 0
        for m in all_matches:
            m = dict(m)
            bat_first = m.get('inn1_bat')
            bat_second = m.get('inn2_bat')
            if tid not in (bat_first, bat_second):
                continue
            played += 1
            wid = m.get('winning_team_id')
            rt = m.get('result_type')
            if wid == tid:
                won += 1
            elif rt in ('draw',):
                drawn += 1
            elif rt == 'no_result':
                nr += 1
            elif wid is not None:
                lost += 1
            fmt = m.get('format', 'ODI')
            max_overs = 50 if fmt == 'ODI' else 20
            inn1_runs = m.get('inn1_runs') or 0
            inn1_overs = _cricket_overs_to_decimal(m.get('inn1_overs') or max_overs, fallback=float(max_overs))
            inn2_runs = m.get('inn2_runs') or 0
            inn2_overs = _cricket_overs_to_decimal(m.get('inn2_overs') or max_overs, fallback=float(max_overs))
            if tid == bat_first:
                rs += inn1_runs
                of += inn1_overs
                rc += inn2_runs
                ob += inn2_overs
            else:
                rs += inn2_runs
                of += inn2_overs
                rc += inn1_runs
                ob += inn1_overs
        # Points: win=2, no_result=1, loss=0
        fmt_global = match.get('format', 'ODI') if match else 'ODI'
        pts = won * 2 + nr
        nrr = (rs / of - rc / ob) if (of > 0 and ob > 0) else 0.0
        database.update_tournament_team(db, tt['id'], {
            'played': played, 'won': won, 'lost': lost,
            'drawn': drawn, 'no_result': nr, 'points': pts,
            'runs_scored': rs, 'overs_faced': of,
            'runs_conceded': rc, 'overs_bowled': ob,
            'nrr': round(nrr, 3),
        })


@app.route('/api/tournaments', methods=['GET'])
def list_tournaments():
    db = database.get_db()
    try:
        rows = db.execute(
            "SELECT t.*, wt.name as winner_name FROM tournaments t "
            "LEFT JOIN teams wt ON t.winner_team_id = wt.id "
            "ORDER BY t.start_date DESC"
        ).fetchall()
        from database import dict_from_rows
        return jsonify({'tournaments': dict_from_rows(rows)})
    finally:
        database.close_db(db)


@app.route('/api/tournaments', methods=['POST'])
def create_tournament():
    import json as _json
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    fmt = data.get('format', 'ODI')
    ttype = data.get('tournament_type', 'world_cup')
    team_ids = [int(x) for x in data.get('team_ids', [])]
    start_date = data.get('start_date')
    world_id = data.get('world_id')
    venue_ids = data.get('venue_ids', [])

    if not name:
        return err('name is required')
    if fmt not in ('Test', 'ODI', 'T20', 'Hundred'):
        return err('format must be Test, ODI, T20 or Hundred')
    if ttype not in ('world_cup', 't20_world_cup', 'tri_series', 'the_hundred'):
        return err('tournament_type must be world_cup, t20_world_cup or tri_series')

    expected = {'world_cup': 10, 't20_world_cup': 8, 'tri_series': 3}
    if len(team_ids) != expected[ttype]:
        return err(f'{ttype} requires exactly {expected[ttype]} teams')

    db = database.get_db()
    try:
        t_id = database.create_tournament(db, {
            'name': name, 'format': fmt, 'tournament_type': ttype,
            'world_id': world_id, 'start_date': start_date,
            'settings_json': _json.dumps({'venue_ids': venue_ids}),
        })

        fixtures = []
        def _venue(i):
            return venue_ids[i % len(venue_ids)] if venue_ids else None

        if ttype == 'tri_series':
            for team_id in team_ids:
                database.create_tournament_team(db, t_id, team_id, 'A')
            pairs = _round_robin_pairs(team_ids)
            for rep in range(2):
                for i, (t1, t2) in enumerate(pairs):
                    fixtures.append({
                        'tournament_id': t_id, 'series_id': None, 'world_id': world_id,
                        'scheduled_date': start_date, 'venue_id': _venue(len(fixtures)),
                        'team1_id': t1, 'team2_id': t2, 'fixture_type': 'league',
                    })
        else:
            # world_cup: 2 groups of 5; t20_world_cup: 2 groups of 4
            group_size = 5 if ttype == 'world_cup' else 4
            group_a = team_ids[:group_size]
            group_b = team_ids[group_size:]
            for tid in group_a:
                database.create_tournament_team(db, t_id, tid, 'A')
            for tid in group_b:
                database.create_tournament_team(db, t_id, tid, 'B')
            for t1, t2 in _round_robin_pairs(group_a):
                fixtures.append({
                    'tournament_id': t_id, 'series_id': None, 'world_id': world_id,
                    'scheduled_date': start_date, 'venue_id': _venue(len(fixtures)),
                    'team1_id': t1, 'team2_id': t2, 'fixture_type': 'league',
                })
            for t1, t2 in _round_robin_pairs(group_b):
                fixtures.append({
                    'tournament_id': t_id, 'series_id': None, 'world_id': world_id,
                    'scheduled_date': start_date, 'venue_id': _venue(len(fixtures)),
                    'team1_id': t1, 'team2_id': t2, 'fixture_type': 'league',
                })

        database.bulk_create_fixtures(db, fixtures)
        all_fixtures = database.get_fixtures(db, tournament_id=t_id)
        return jsonify({'tournament_id': t_id, 'fixtures': all_fixtures})
    finally:
        database.close_db(db)


@app.route('/api/tournaments/<int:id>', methods=['GET'])
def get_tournament(id):
    db = database.get_db()
    try:
        tournament = database.get_tournament(db, id)
        if not tournament:
            return err('Tournament not found', 404)
        tt = database.get_tournament_teams(db, id)
        fixtures = database.get_fixtures(db, tournament_id=id)

        # Split standings by group
        groups = {}
        for row in tt:
            g = row.get('group_name') or 'A'
            groups.setdefault(g, []).append(row)
        for g in groups:
            groups[g].sort(key=lambda r: (-r['points'], -r['nrr']))

        # Separate fixtures by type
        league = [f for f in fixtures if f['fixture_type'] == 'league']
        semis  = [f for f in fixtures if f['fixture_type'] == 'semi']
        finals = [f for f in fixtures if f['fixture_type'] == 'final']

        # Determine stage
        league_done = all(f['status'] == 'complete' for f in league) if league else False
        semis_done  = all(f['status'] == 'complete' for f in semis)  if semis  else False
        if finals:
            stage = 'complete' if all(f['status'] == 'complete' for f in finals) else 'final'
        elif semis:
            stage = 'final' if semis_done else 'semi'
        elif league_done:
            stage = 'ready_to_advance'
        else:
            stage = 'league'

        return jsonify({
            'tournament': tournament,
            'standings': groups,
            'league_fixtures': league,
            'semi_fixtures': semis,
            'final_fixtures': finals,
            'stage': stage,
        })
    finally:
        database.close_db(db)


@app.route('/api/tournaments/<int:id>/advance', methods=['PUT'])
def advance_tournament(id):
    db = database.get_db()
    try:
        tournament = database.get_tournament(db, id)
        if not tournament:
            return err('Tournament not found', 404)

        ttype = tournament.get('tournament_type', 'world_cup')
        fixtures = database.get_fixtures(db, tournament_id=id)
        league = [f for f in fixtures if f['fixture_type'] == 'league']
        semis  = [f for f in fixtures if f['fixture_type'] == 'semi']
        finals_f = [f for f in fixtures if f['fixture_type'] == 'final']
        tt = database.get_tournament_teams(db, id)
        fmt = tournament.get('format', 'ODI')
        start_date = tournament.get('start_date')
        world_id = tournament.get('world_id')

        import json as _json
        venue_ids = []
        if tournament.get('settings_json'):
            try:
                venue_ids = _json.loads(tournament['settings_json']).get('venue_ids', [])
            except Exception:
                pass

        def _venue(i):
            return venue_ids[i % len(venue_ids)] if venue_ids else None

        # Stage 1: league → create semis
        if not semis and all(f['status'] == 'complete' for f in league):
            groups = {}
            for row in tt:
                g = row.get('group_name') or 'A'
                groups.setdefault(g, []).append(row)
            for g in groups:
                groups[g].sort(key=lambda r: (-r['points'], -r['nrr']))

            if ttype == 'tri_series':
                # Top 2 from group A to final
                top2 = [r['team_id'] for r in groups.get('A', [])[:2]]
                if len(top2) < 2:
                    return err('Not enough teams for final')
                database.bulk_create_fixtures(db, [{
                    'tournament_id': id, 'series_id': None, 'world_id': world_id,
                    'scheduled_date': start_date, 'venue_id': _venue(0),
                    'team1_id': top2[0], 'team2_id': top2[1], 'fixture_type': 'final',
                }])
                database.update_tournament(db, id, {'status': 'knockout'})
            else:
                # 1A vs 2B, 1B vs 2A
                top_a = [r['team_id'] for r in groups.get('A', [])]
                top_b = [r['team_id'] for r in groups.get('B', [])]
                qualifiers_per_group = 2  # top 2 from each group for both world_cup and t20_world_cup

                if len(top_a) < qualifiers_per_group or len(top_b) < qualifiers_per_group:
                    return err('Not enough qualified teams')

                # Both world_cup and t20_world_cup: 1A vs 2B, 1B vs 2A
                semi_fixtures = [
                    {'team1_id': top_a[0], 'team2_id': top_b[1]},
                    {'team1_id': top_b[0], 'team2_id': top_a[1]},
                ]

                rows = []
                for i, sf in enumerate(semi_fixtures):
                    rows.append({
                        'tournament_id': id, 'series_id': None, 'world_id': world_id,
                        'scheduled_date': start_date, 'venue_id': _venue(i),
                        'team1_id': sf['team1_id'], 'team2_id': sf['team2_id'],
                        'fixture_type': 'semi',
                    })
                database.bulk_create_fixtures(db, rows)
                database.update_tournament(db, id, {'status': 'knockout'})

            new_fixtures = database.get_fixtures(db, tournament_id=id)
            return jsonify({'success': True, 'fixtures': new_fixtures})

        # Stage 2: semis done → create final
        if semis and all(f['status'] == 'complete' for f in semis) and not finals_f:
            # Find winners of each semi
            finalists = []
            for sf in semis:
                # Look up the match to get winner
                m = None
                if sf.get('match_id'):
                    m = database.get_match(db, sf['match_id'])
                if m and m.get('winning_team_id'):
                    finalists.append(m['winning_team_id'])
            if len(finalists) < 2:
                return err('Semi-final results incomplete')
            database.bulk_create_fixtures(db, [{
                'tournament_id': id, 'series_id': None, 'world_id': world_id,
                'scheduled_date': start_date, 'venue_id': _venue(0),
                'team1_id': finalists[0], 'team2_id': finalists[1], 'fixture_type': 'final',
            }])
            new_fixtures = database.get_fixtures(db, tournament_id=id)
            return jsonify({'success': True, 'fixtures': new_fixtures})

        # Stage 3: final done → mark tournament complete
        if finals_f and all(f['status'] == 'complete' for f in finals_f):
            winner_id = None
            if finals_f[0].get('match_id'):
                m = database.get_match(db, finals_f[0]['match_id'])
                if m:
                    winner_id = m.get('winning_team_id')
            database.update_tournament(db, id, {'status': 'complete', 'winner_team_id': winner_id})
            return jsonify({'success': True, 'winner_team_id': winner_id})

        return err('No advancement action available at this stage')
    finally:
        database.close_db(db)


# ── Worlds — helpers ─────────────────────────────────────────────────────────

def _build_world_state(db, world_id):
    """Build a world_state dict ready for game_engine world functions."""
    import json
    world = database.get_world(db, world_id)
    if not world:
        return None
    settings = {}
    if world.get('settings_json'):
        try:
            settings = json.loads(world['settings_json'])
        except Exception:
            pass

    team_ids   = settings.get('team_ids', [])
    my_team_id = settings.get('my_team_id')
    my_domestic_team_id = settings.get('my_domestic_team_id')

    raw_states    = database.get_player_world_states(db, world_id)
    player_states = {}
    for pid, state in raw_states.items():
        ps = dict(state)
        if isinstance(ps.get('last_match_dates'), str):
            try:
                ps['last_match_dates'] = json.loads(ps['last_match_dates'])
            except Exception:
                ps['last_match_dates'] = []
        player_states[pid] = ps

    teams = {}
    team_roster_targets = {}
    for tid in team_ids:
        team = database.get_team(db, tid)
        if not team:
            continue
        players = database.get_players_for_team(db, tid, world_id=world_id)
        team_roster_targets[tid] = max(11, len(players))
        active_players = [
            p for p in players
            if int((player_states.get(p['id']) or {}).get('active', 1) or 0) == 1
        ]
        teams[tid] = {
            'name':          team['name'],
            'short_code':    team.get('short_code', ''),
            'badge_colour':  team.get('badge_colour', '#666'),
            'home_venue_id': team.get('home_venue_id'),
            'players':       active_players,
        }

    return {
        'my_team_id':     my_team_id,
        'my_domestic_team_id': my_domestic_team_id,
        'user_team_ids':  list(_user_team_ids(settings)),
        'current_date':   world.get('current_date', ''),
        'settings':       settings,
        'teams':          teams,
        'team_roster_targets': team_roster_targets,
        'player_states':  player_states,
    }


_REGEN_FIRST_NAMES = [
    'Aadi', 'Aarav', 'Aaron', 'Aayan', 'Abel', 'Adam', 'Adil', 'Aditya', 'Aiden', 'Ainsley',
    'Ajeet', 'Akhil', 'Alan', 'Albert', 'Alec', 'Alfie', 'Ali', 'Amir', 'Anderson', 'Andre',
    'Angus', 'Anik', 'Archer', 'Arin', 'Arjun', 'Arlo', 'Aryan', 'Asher', 'Ayaan', 'Bailey',
    'Ben', 'Benjamin', 'Bilal', 'Blake', 'Bodhi', 'Brandon', 'Caden', 'Cai', 'Caleb', 'Callum',
    'Cameron', 'Carl', 'Casey', 'Charles', 'Charlie', 'Chris', 'Christopher', 'Cooper', 'Curtis', 'Cyrus',
    'Daniel', 'Danny', 'Darshan', 'David', 'Declan', 'Dev', 'Dylan', 'Eddie', 'Edward', 'Ehsan',
    'Eli', 'Elijah', 'Elliot', 'Ethan', 'Euan', 'Evan', 'Farhan', 'Felix', 'Finn', 'Fletcher',
    'Fraser', 'Gabriel', 'George', 'Gideon', 'Hamish', 'Haris', 'Harry', 'Harvey', 'Hasan', 'Hugo',
    'Ibrahim', 'Imran', 'Ishaan', 'Isaac', 'Isaiah', 'Ivan', 'Jack', 'Jackson', 'Jacob', 'Jai',
    'Jake', 'James', 'Jamie', 'Jared', 'Jason', 'Jay', 'Joel', 'John', 'Jonah', 'Joseph',
    'Josh', 'Joshua', 'Jude', 'Julian', 'Kacper', 'Kai', 'Karan', 'Kasim', 'Keegan', 'Kian',
    'Kieran', 'Kit', 'Kris', 'Kunal', 'Lachlan', 'Lennon', 'Leo', 'Lewis', 'Liam', 'Logan',
    'Louis', 'Luca', 'Lucas', 'Luke', 'Mackenzie', 'Marcus', 'Mason', 'Mateo', 'Matteo', 'Max',
    'Maxwell', 'Micah', 'Michael', 'Mikael', 'Miles', 'Milan', 'Mohammad', 'Mohammed', 'Monty', 'Muhammad',
    'Nate', 'Nathan', 'Nayan', 'Neil', 'Noah', 'Nolan', 'Oliver', 'Ollie', 'Omar', 'Oscar',
    'Owen', 'Parth', 'Patrick', 'Paul', 'Rafi', 'Raheem', 'Ralph', 'Ravi', 'Rayhan', 'Reece',
    'Rehan', 'Riley', 'Rishi', 'Rohan', 'Ronan', 'Rory', 'Ryan', 'Saad', 'Sam', 'Sami',
    'Samuel', 'Scott', 'Sean', 'Seb', 'Sebastian', 'Shane', 'Shaan', 'Siddharth', 'Simon', 'Sohail',
    'Sonny', 'Spencer', 'Stanley', 'Stefan', 'Sufyan', 'Taha', 'Taran', 'Tariq', 'Taylor', 'Theo',
    'Thomas', 'Toby', 'Tom', 'Tristan', 'Tyler', 'Usman', 'Vihaan', 'Victor', 'Will', 'William',
    'Xavier', 'Yash', 'Yousef', 'Yusuf', 'Zac', 'Zach', 'Zain', 'Zaid', 'Zak', 'Zayan'
]
_REGEN_LAST_NAMES = [
    'Ahmed', 'Akhtar', 'Ali', 'Allen', 'Anderson', 'Ashraf', 'Atkinson', 'Aziz', 'Barker', 'Barnes',
    'Barrett', 'Bashir', 'Bell', 'Bennett', 'Bhatti', 'Bishop', 'Blair', 'Bond', 'Booth', 'Bowen',
    'Boyd', 'Bradley', 'Brown', 'Butcher', 'Butler', 'Butt', 'Caldwell', 'Campbell', 'Carey', 'Carpenter',
    'Carr', 'Carroll', 'Chand', 'Chapman', 'Chaudhry', 'Clarke', 'Coleman', 'Collins', 'Cook', 'Cooper',
    'Crawford', 'Cross', 'Cunningham', 'Curtis', 'Dale', 'Das', 'Davidson', 'Davies', 'Davis', 'Dean',
    'Dixon', 'Douglas', 'Doyle', 'Drummond', 'Dunbar', 'Edwards', 'Ellis', 'Evans', 'Farooq', 'Ferguson',
    'Fernandes', 'Fielding', 'Fisher', 'Fitzpatrick', 'Fleming', 'Foster', 'Fraser', 'Fuller', 'Gardner', 'George',
    'Ghani', 'Gibson', 'Gill', 'Gordon', 'Graham', 'Grant', 'Gray', 'Green', 'Griffith', 'Habib',
    'Hale', 'Hall', 'Hamilton', 'Hammond', 'Haque', 'Harding', 'Harper', 'Harris', 'Hart', 'Hasan',
    'Hassan', 'Hayes', 'Henderson', 'Hicks', 'Hogan', 'Holland', 'Hood', 'Hooper', 'Hughes', 'Hussain',
    'Iqbal', 'Irving', 'Islam', 'Iyer', 'Jackson', 'Jadeja', 'Jahangir', 'James', 'Javed', 'Jenkins',
    'Johnson', 'Jones', 'Joseph', 'Kamal', 'Kaur', 'Kerr', 'Khalid', 'Khan', 'Khatri', 'Knight',
    'Kumar', 'Lamb', 'Lawrence', 'Leach', 'Lee', 'Lennox', 'Lewis', 'Lloyd', 'Long', 'Lowe',
    'Mahmood', 'Majid', 'Malik', 'Mann', 'Marshall', 'Martin', 'Mason', 'Mathews', 'McAllister', 'McBride',
    'McCormick', 'McDonald', 'McGregor', 'McKenzie', 'Mehta', 'Miller', 'Mills', 'Mitchell', 'Mohamed', 'Moore',
    'Morgan', 'Morris', 'Mukherjee', 'Murphy', 'Murray', 'Nadeem', 'Nair', 'Naseem', 'Nicholls', 'Norris',
    'O Brien', 'O Connell', 'O Dowd', 'Parker', 'Parmar', 'Patel', 'Pearson', 'Perera', 'Peters', 'Phillips',
    'Potter', 'Powell', 'Qadri', 'Qureshi', 'Rafiq', 'Rahman', 'Rashid', 'Reed', 'Reid', 'Reynolds',
    'Richards', 'Roberts', 'Robertson', 'Robinson', 'Ross', 'Saeed', 'Sahota', 'Saleem', 'Saunders', 'Scott',
    'Shah', 'Shaikh', 'Sharma', 'Sheikh', 'Short', 'Siddiqui', 'Silva', 'Singh', 'Sinha', 'Sloan',
    'Smith', 'Smyth', 'Spencer', 'Steele', 'Stephens', 'Stewart', 'Sullivan', 'Sweeney', 'Tariq', 'Taylor',
    'Thomas', 'Thompson', 'Turner', 'Usman', 'Vaughan', 'Verma', 'Walker', 'Walsh', 'Ward', 'Watson',
    'White', 'Wilkins', 'Williams', 'Wilson', 'Wood', 'Wright', 'Young', 'Zaidi', 'Zaman', 'Zia',
    'Bennett-Smith', 'Brown-Reid', 'Campbell-Thomas', 'Clarke-Jones', 'Davies-Evans', 'Edwards-Hughes', 'Foster-Lee', 'Grant-Wilson', 'Halliday-Brown', 'Khan-Patel',
    'Lewis-Clarke', 'Martin-Young', 'Morgan-Shaw', 'Patel-Singh', 'Rahman-Ali', 'Reid-Campbell', 'Roberts-Gray', 'Shah-Hussain', 'Taylor-Mills', 'Walker-James'
]

_REGEN_NAME_POOLS = {
    'england': {
        'first': ['Oliver', 'George', 'Harry', 'Jack', 'Charlie', 'Thomas', 'Alfie', 'Theo', 'Oscar', 'William',
                  'Jacob', 'Leo', 'Archie', 'Henry', 'Freddie', 'Arthur', 'James', 'Lucas', 'Joshua', 'Edward',
                  'Samuel', 'Max', 'Luke', 'Joseph', 'Ben', 'Tom', 'Callum', 'Cameron', 'Liam', 'Rory'],
        'last': ['Smith', 'Jones', 'Taylor', 'Brown', 'Wilson', 'Johnson', 'Davies', 'Robinson', 'Wright', 'Walker',
                 'Thompson', 'White', 'Hughes', 'Edwards', 'Clarke', 'Turner', 'Hill', 'Baker', 'Carter', 'Phillips',
                 'Cooper', 'Ward', 'Butler', 'Collins', 'Brooks', 'Gray', 'Foster', 'Parker', 'Taylor-Jones', 'Clarke-Smith']
    },
    'australia': {
        'first': ['Jack', 'Noah', 'Oliver', 'William', 'Thomas', 'Lucas', 'Henry', 'Leo', 'Charlie', 'James',
                  'Harry', 'Max', 'Archie', 'Hudson', 'Lachlan', 'Xavier', 'Cooper', 'Bailey', 'Riley', 'Mitchell',
                  'Cameron', 'Marcus', 'Harvey', 'Mason', 'Oscar', 'Finn', 'Ethan', 'Angus', 'Hamish', 'Tyler'],
        'last': ['Smith', 'Jones', 'Williams', 'Brown', 'Wilson', 'Taylor', 'Anderson', 'Thomas', 'White', 'Martin',
                 'Thompson', 'Moore', 'Walker', 'Hall', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Green',
                 'Campbell', 'Murray', 'Evans', 'Murphy', 'Fraser', 'Harris', 'Cooper', 'Griffiths', 'Miller-White', 'Taylor-Brown']
    },
    'india': {
        'first': ['Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Krishna', 'Ishaan', 'Ayaan', 'Rohan', 'Karan',
                  'Sai', 'Dhruv', 'Aadi', 'Yash', 'Rahul', 'Rishi', 'Aryan', 'Dev', 'Parth', 'Siddharth',
                  'Varun', 'Aniket', 'Rajat', 'Aman', 'Akash', 'Nikhil', 'Harsh', 'Kabir', 'Pranav', 'Rudra'],
        'last': ['Sharma', 'Patel', 'Singh', 'Kumar', 'Gupta', 'Verma', 'Yadav', 'Joshi', 'Iyer', 'Nair',
                 'Jadeja', 'Pandya', 'Reddy', 'Kulkarni', 'Chopra', 'Saxena', 'Gill', 'Saini', 'Choudhary', 'Mehta',
                 'Bose', 'Malhotra', 'Kapoor', 'Bhat', 'Mishra', 'Tripathi', 'Kohli', 'Rana', 'Patel-Shah', 'Singh-Rana']
    },
    'pakistan': {
        'first': ['Muhammad', 'Ahmed', 'Ali', 'Hassan', 'Hussain', 'Hamza', 'Abdullah', 'Usman', 'Bilal', 'Ayaan',
                  'Saad', 'Rayyan', 'Taha', 'Zayan', 'Daniyal', 'Raza', 'Sufyan', 'Talha', 'Rehan', 'Ammar',
                  'Farhan', 'Ahsan', 'Kashif', 'Imran', 'Babar', 'Shan', 'Shahzaib', 'Muneeb', 'Haris', 'Zubair'],
        'last': ['Khan', 'Ahmed', 'Ali', 'Hussain', 'Malik', 'Butt', 'Shah', 'Qureshi', 'Chaudhry', 'Iqbal',
                 'Raza', 'Mahmood', 'Akhtar', 'Saeed', 'Nawaz', 'Sheikh', 'Javed', 'Farooq', 'Rashid', 'Azam',
                 'Haider', 'Mirza', 'Aslam', 'Siddiqui', 'Bhatti', 'Shafiq', 'Saleem', 'Shahid', 'Khan-Ali', 'Shah-Hussain']
    },
    'new_zealand': {
        'first': ['Noah', 'Oliver', 'Jack', 'Leo', 'Theodore', 'George', 'Luca', 'Arthur', 'William', 'Charlie',
                  'Mason', 'Hunter', 'Lachlan', 'Isaac', 'Finn', 'Cooper', 'James', 'Max', 'Sam', 'Ben',
                  'Harley', 'Tom', 'Hamish', 'Riley', 'Micah', 'Arlo', 'Tyler', 'Carter', 'Logan', 'Niko'],
        'last': ['Smith', 'Wilson', 'Taylor', 'Brown', 'Williams', 'Thompson', 'Walker', 'Cooper', 'Martin', 'Anderson',
                 'King', 'Bell', 'Campbell', 'Harris', 'Fraser', 'Reid', 'Murray', 'Bennett', 'Mason', 'Scott',
                 'Young', 'Nicholls', 'McKenzie', 'Robertson', 'Ellis', 'Sullivan', 'Parker', 'Reid-Walker', 'Campbell-Young', 'Scott-Brown']
    },
    'south_africa': {
        'first': ['Liam', 'Noah', 'Ethan', 'Luke', 'Daniel', 'Joshua', 'Nathan', 'Aiden', 'Jason', 'Caleb',
                  'Aaron', 'Ruan', 'Jean', 'Francois', 'Wiaan', 'Keegan', 'Mihlali', 'Lutho', 'Siyabonga', 'Thabo',
                  'Aphiwe', 'Kagiso', 'Temba', 'Aiden', 'Ziyaad', 'Jody', 'Cameron', 'Ryan', 'Dylan', 'Morne'],
        'last': ['Smith', 'Naidoo', 'van der Merwe', 'Botha', 'Pillay', 'Ndlovu', 'Mokoena', 'Jacobs', 'Adams', 'Visser',
                 'Steyn', 'Petersen', 'Muller', 'van Wyk', 'Mahlangu', 'Mokoena', 'Dlamini', 'Hendricks', 'Meyer', 'Coetzee',
                 'Pretorius', 'Williams', 'Daniels', 'Khumalo', 'du Plessis', 'Bosch', 'van Rooyen', 'Petersen-Jacobs', 'Naidoo-Pillay', 'Smith-Coetzee']
    },
    'west_indies': {
        'first': ['Jayden', 'Kemar', 'Shai', 'Roston', 'Kraigg', 'Akeem', 'Andre', 'Alzarri', 'Marlon', 'Keacy',
                  'Alick', 'Jomel', 'Kavem', 'Rovman', 'Shimron', 'Tagenarine', 'Joshua', 'Brandon', 'Tyrone', 'Devon',
                  'Kirk', 'Jason', 'Oshane', 'Jaden', 'Jermaine', 'Kevlon', 'Che', 'Kadeem', 'Nicholas', 'Rahkeem'],
        'last': ['Joseph', 'Holder', 'Charles', 'Hope', 'Chase', 'Brathwaite', 'Phillip', 'Seales', 'Roach', 'Pooran',
                 'Mayers', 'Lewis', 'Carty', 'Sinclair', 'Hosein', 'McCaskie', 'Greaves', 'Paul', 'Cornwall', 'King',
                 'Motie', 'Athanaze', 'Forde', 'Johnson', 'Bishop', 'Campbell', 'Richards', 'Thomas-Joseph', 'King-Hope', 'Charles-Bishop']
    },
    'sri_lanka': {
        'first': ['Nethmin', 'Sahan', 'Dulaj', 'Kavindu', 'Pasindu', 'Dineth', 'Avishka', 'Charith', 'Kusal', 'Pathum',
                  'Kamindu', 'Dhananjaya', 'Asitha', 'Kasun', 'Wanindu', 'Maheesh', 'Lahiru', 'Dasun', 'Bhanuka', 'Chamindu',
                  'Janith', 'Vishwa', 'Ashen', 'Minod', 'Oshada', 'Ramesh', 'Shevon', 'Niroshan', 'Matheesha', 'Pramod'],
        'last': ['Perera', 'Fernando', 'Silva', 'Kumara', 'Mendis', 'Nissanka', 'Hasaranga', 'Karunaratne', 'Madushanka', 'Asalanka',
                 'Gunathilaka', 'Rajapaksa', 'Rathnayake', 'Samarawickrama', 'Vandersay', 'Pathirana', 'Lakshan', 'Bandara', 'Wijesinghe', 'Peiris',
                 'Dhananjaya', 'Jayasuriya', 'Abeyratne', 'Kulasekara', 'Herath', 'Dananjaya', 'Perera-Silva', 'Fernando-Kumara', 'Mendis-Perera', 'Silva-Bandara']
    },
    'bangladesh': {
        'first': ['Rahim', 'Tamim', 'Litton', 'Towhid', 'Najmul', 'Mahmudul', 'Shanto', 'Taskin', 'Mustafizur', 'Shakib',
                  'Mehidy', 'Nasum', 'Soumya', 'Anamul', 'Mushfiqur', 'Hasan', 'Rakib', 'Naim', 'Tanzid', 'Mahedi',
                  'Ebadot', 'Rishad', 'Tawhid', 'Aminul', 'Akbar', 'Shadman', 'Yasir', 'Mrittunjoy', 'Zaker', 'Parvez'],
        'last': ['Hasan', 'Hossain', 'Rahman', 'Islam', 'Ahmed', 'Ali', 'Das', 'Miah', 'Sarkar', 'Mia',
                 'Haque', 'Naim', 'Shanto', 'Saifuddin', 'Mahmud', 'Zaman', 'Akter', 'Bashar', 'Kabir', 'Roy',
                 'Nayeem', 'Shamim', 'Rakib', 'Rana', 'Rafi', 'Anik', 'Rahman-Das', 'Hossain-Ali', 'Islam-Sarkar', 'Ahmed-Roy']
    },
    'afghanistan': {
        'first': ['Ahmad', 'Rahmanullah', 'Ibrahim', 'Hashmatullah', 'Najibullah', 'Rashid', 'Mohammad', 'Mujeeb', 'Naveen', 'Fazalhaq',
                  'Noor', 'Abdul', 'Azmatullah', 'Ikram', 'Sediqullah', 'Darwish', 'Zia', 'Afsar', 'Bilal', 'Farid',
                  'Hamid', 'Javed', 'Khalid', 'Latif', 'Noman', 'Qais', 'Rahim', 'Samiullah', 'Tariq', 'Wafadar'],
        'last': ['Shah', 'Zadran', 'Ahmadzai', 'Nabi', 'Gurbaz', 'Omarzai', 'Farooqi', 'Khan', 'Noorzai', 'Stanikzai',
                 'Safi', 'Shinwari', 'Mohammadi', 'Jadran', 'Azizi', 'Rahmani', 'Wali', 'Sulaiman', 'Yousafzai', 'Wardak',
                 'Nasiri', 'Hamza', 'Sediqi', 'Popalzai', 'Hakimi', 'Rahimzai', 'Khan-Zadran', 'Shah-Ahmadzai', 'Safi-Wardak', 'Azizi-Nabi']
    },
    'ireland': {
        'first': ['Jack', 'James', 'Noah', 'Conor', 'Cian', 'Oisin', 'Fionn', 'Darragh', 'Tadhg', 'Rian',
                  'Cillian', 'Patrick', 'Rory', 'Shane', 'Sean', 'Daniel', 'Ben', 'Tom', 'Luke', 'Eoin',
                  'Niall', 'Ryan', 'Adam', 'Harry', 'Cathal', 'Michael', 'Finn', 'Kian', 'Jamie', 'Dylan'],
        'last': ['Murphy', 'Kelly', 'Walsh', 'Byrne', 'Ryan', 'O Brien', 'O Sullivan', 'Doyle', 'McCarthy', 'Gallagher',
                 'Dunne', 'Lynch', 'Kennedy', 'Quinn', 'McCann', 'Byrne', 'Kavanagh', 'Fitzgerald', 'Reilly', 'Brennan',
                 'Delany', 'Barry', 'Murray', 'Nolan', 'Connolly', 'Healy', 'O Brien-Kelly', 'Murphy-Byrne', 'Doyle-Quinn', 'Ryan-Walsh']
    },
    'scotland': {
        'first': ['Jack', 'Callum', 'Lewis', 'Finlay', 'Rory', 'Fraser', 'Hamish', 'Euan', 'Alasdair', 'Blair',
                  'Cameron', 'Ben', 'Tom', 'Jamie', 'Lachlan', 'Logan', 'Max', 'Dylan', 'Archie', 'Aidan',
                  'Craig', 'Gregor', 'Iain', 'Matthew', 'Ross', 'Stuart', 'Zander', 'Kieran', 'Ryan', 'Sean'],
        'last': ['Smith', 'Stewart', 'MacLeod', 'Fraser', 'Campbell', 'Munro', 'Forbes', 'McIntosh', 'Kerr', 'Allan',
                 'Davidson', 'Greer', 'Wallace', 'Leslie', 'Buchanan', 'Mackenzie', 'Graham', 'Robertson', 'Baird', 'Ritchie',
                 'Henderson', 'Morrison', 'Scott', 'Watson', 'Watt', 'Douglas', 'Fraser-Stewart', 'MacLeod-Scott', 'Kerr-Wallace', 'Graham-Forbes']
    },
    'netherlands': {
        'first': ['Daan', 'Sem', 'Levi', 'Milan', 'Finn', 'Luuk', 'Lars', 'Noah', 'Mees', 'Bram',
                  'Jesse', 'Thijs', 'Niels', 'Joris', 'Stijn', 'Koen', 'Ruben', 'Cas', 'Timo', 'Sven',
                  'Jelle', 'Wesley', 'Roelof', 'Bas', 'Pieter', 'Johan', 'Aryan', 'Shariz', 'Vikram', 'Ryan'],
        'last': ['de Vries', 'van der Merwe', 'van Beek', 'Edwards', 'Ackermann', 'Croes', 'Klaassen', 'de Leede', 'Snater', 'Pringle',
                 'Kingma', 'van Meekeren', 'Zulfiqar', 'Singh', 'Nidamanuru', 'O Dowd', 'Dutt', 'Doram', 'Klein', 'Vos',
                 'Jansen', 'Bakker', 'de Boer', 'van Rijn', 'Pieters', 'Smit', 'van der Berg', 'de Vries-Jansen', 'van Beek-de Boer', 'Klein-Dutt']
    },
    'zimbabwe': {
        'first': ['Tadiwanashe', 'Wesley', 'Takudzwa', 'Clive', 'Joylord', 'Brandon', 'Craig', 'Sean', 'Tafadzwa', 'Blessing',
                  'Richard', 'Ryan', 'Milton', 'Faraz', 'Tanaka', 'Prince', 'Victor', 'Luke', 'Ernest', 'Dion',
                  'Brian', 'Carl', 'Kevin', 'Nicholas', 'Tinashe', 'Trevor', 'Donald', 'Ashley', 'Shingirai', 'Kudzai'],
        'last': ['Muzarabani', 'Raza', 'Bennett', 'Ervine', 'Williams', 'Burl', 'Madhevere', 'Ngarava', 'Masakadza', 'Kaia',
                 'Marumani', 'Munyonga', 'Shumba', 'Campbell', 'Mavuta', 'Chivanga', 'Mpofu', 'Jongwe', 'Matigimu', 'Munyati',
                 'Chisoro', 'Mtetwa', 'Nyauchi', 'Muzondo', 'Mlambo', 'Mawoyo', 'Bennett-Williams', 'Raza-Kaia', 'Masakadza-Burl', 'Campbell-Ervine']
    },
    'nepal': {
        'first': ['Aarav', 'Aayush', 'Ritvik', 'Rohit', 'Kushal', 'Aasif', 'Dipendra', 'Gulsan', 'Karan', 'Lalit',
                  'Sandeep', 'Sompal', 'Bhim', 'Anil', 'Aakash', 'Nandan', 'Pawan', 'Bibek', 'Roshan', 'Sagar',
                  'Aman', 'Nabin', 'Pratis', 'Rijan', 'Sushil', 'Yuvraj', 'Bikram', 'Binod', 'Hemant', 'Sujan'],
        'last': ['Paudel', 'Malla', 'Airee', 'Kumar', 'Jha', 'Bohara', 'Kami', 'Singh', 'Chand', 'Khadka',
                 'Aalam', 'Maharjan', 'Bhatta', 'Gurung', 'Shahi', 'Thapa', 'Shrestha', 'Rawal', 'Joshi', 'Yadav',
                 'Koirala', 'Bista', 'Karki', 'Lama', 'Malla-Shahi', 'Paudel-Thapa', 'Joshi-Gurung', 'Rawal-Bohara', 'Chand-Khadka', 'Shrestha-Yadav']
    },
    'uae': {
        'first': ['Muhammad', 'Waseem', 'Aryan', 'Dhruv', 'Basil', 'Vriitya', 'Aayan', 'Ali', 'Zahoor', 'Akeel',
                  'Junaid', 'Kashif', 'Khalid', 'Lovepreet', 'Rahul', 'Sanchit', 'Nilansh', 'Karthik', 'Usman', 'Ammar',
                  'Aarush', 'Ansh', 'Harit', 'Jay', 'Mihir', 'Parth', 'Rayan', 'Tanish', 'Yash', 'Zayed'],
        'last': ['Khan', 'Ahmed', 'Shah', 'Ali', 'Siddique', 'Panoly', 'Suri', 'Aravind', 'Bharadwaj', 'Maqsood',
                 'Naseer', 'Rizwan', 'Farooq', 'Thakur', 'Patel', 'Singh', 'Bhandari', 'Lal', 'Bhupinder', 'Kumar',
                 'Zahid', 'Asif', 'Merchant', 'Chopra', 'Shah-Khan', 'Patel-Singh', 'Ahmed-Ali', 'Kumar-Patel', 'Suri-Aravind', 'Bharadwaj-Thakur']
    },
    'oman': {
        'first': ['Aqib', 'Jatinder', 'Kashyap', 'Shoaib', 'Bilal', 'Zeeshan', 'Ayaan', 'Faisal', 'Karan', 'Naseem',
                  'Shakeel', 'Pratik', 'Aamir', 'Arjun', 'Nikhil', 'Rakesh', 'Sandeep', 'Usama', 'Yatin', 'Zubair',
                  'Aman', 'Chetan', 'Danish', 'Haroon', 'Imran', 'Jayesh', 'Noman', 'Rohit', 'Sufyan', 'Tanveer'],
        'last': ['Khan', 'Singh', 'Shah', 'Kumar', 'Patel', 'Ahmed', 'Ali', 'Ilyas', 'Maqsood', 'Butt',
                 'Rafiq', 'Naseem', 'Bharat', 'Mehta', 'Sharma', 'Rana', 'Qadri', 'Aslam', 'Naqvi', 'Joshi',
                 'Sood', 'Verma', 'Tariq', 'Chopra', 'Khan-Singh', 'Patel-Kumar', 'Ali-Shah', 'Ahmed-Rafiq', 'Mehta-Joshi', 'Sharma-Verma']
    },
    'united_states': {
        'first': ['Liam', 'Noah', 'Oliver', 'Elijah', 'James', 'William', 'Benjamin', 'Lucas', 'Henry', 'Alexander',
                  'Aaron', 'Cameron', 'Corey', 'Monank', 'Saurabh', 'Harmeet', 'Jasdeep', 'Ali', 'Nisarg', 'Rajan',
                  'Steven', 'Tyler', 'Ryan', 'Jason', 'Ethan', 'Milan', 'Shayan', 'Vatsal', 'Yuvraj', 'Zeeshan'],
        'last': ['Jones', 'Smith', 'Williams', 'Brown', 'Davis', 'Miller', 'Wilson', 'Anderson', 'Taylor', 'Moore',
                 'Patel', 'Kumar', 'Singh', 'Khan', 'Ali', 'Shah', 'Netravalkar', 'Taylor', 'Jones', 'Brown',
                 'Ahmed', 'Desai', 'Rana', 'Sharma', 'White', 'Clark', 'Patel-Singh', 'Brown-Taylor', 'Khan-Ali', 'Jones-Williams']
    },
    'canada': {
        'first': ['Noah', 'Liam', 'William', 'Benjamin', 'Lucas', 'Ethan', 'Ayaan', 'Aaron', 'Cale', 'Dilpreet',
                  'Harsh', 'Navneet', 'Nikhil', 'Pargat', 'Ravinder', 'Saad', 'Shreyas', 'Uday', 'Yuvraj', 'Zaid',
                  'Cameron', 'Declan', 'Finn', 'Gurpal', 'Junaid', 'Kabir', 'Parth', 'Ryan', 'Sajid', 'Tyler'],
        'last': ['Singh', 'Kumar', 'Patel', 'Shah', 'Khan', 'Ali', 'Johnson', 'Smith', 'Brown', 'Thomas',
                 'Gill', 'Joshi', 'Sandhu', 'Ahmed', 'Sana', 'Mann', 'Dhaliwal', 'Bajwa', 'Brar', 'Grewal',
                 'Sodhi', 'Kapoor', 'Riaz', 'Rehman', 'Taylor', 'Wilson', 'Singh-Brar', 'Patel-Shah', 'Khan-Ali', 'Dhaliwal-Sandhu']
    },
}

_REGEN_TEAM_POOL_OVERRIDES = {
    'England': 'england',
    'Australia': 'australia',
    'India': 'india',
    'Pakistan': 'pakistan',
    'New Zealand': 'new_zealand',
    'South Africa': 'south_africa',
    'West Indies': 'west_indies',
    'Sri Lanka': 'sri_lanka',
    'Bangladesh': 'bangladesh',
    'Afghanistan': 'afghanistan',
    'Ireland': 'ireland',
    'Scotland': 'scotland',
    'Netherlands': 'netherlands',
    'Zimbabwe': 'zimbabwe',
    'Nepal': 'nepal',
    'UAE': 'uae',
    'Oman': 'oman',
    'United States': 'united_states',
    'Canada': 'canada',
}

_REGEN_LEAGUE_POOL_OVERRIDES = {
    'county_championship': 'england',
    't20_blast': 'england',
    'royal_london_cup': 'england',
    'sheffield_shield': 'australia',
    'marsh_cup': 'australia',
    'bbl': 'australia',
    'ipl': 'india',
    'cpl': 'west_indies',
    'psl': 'pakistan',
}


def _world_player_lifecycle_mode(world_state):
    settings = world_state.get('settings') or {}
    return 'realistic' if settings.get('player_lifecycle') == 'realistic' else 'ageless'


def _initial_world_player_age(player):
    roll = random.random()
    if roll < 0.18:
        age = random.randint(19, 22)
    elif roll < 0.48:
        age = random.randint(23, 27)
    elif roll < 0.76:
        age = random.randint(28, 31)
    elif roll < 0.94:
        age = random.randint(32, 35)
    else:
        age = random.randint(36, 38)
    if (player.get('batting_rating') or 0) >= 4:
        age = min(39, age + random.choice([0, 0, 1]))
    if (player.get('bowling_rating') or 0) >= 4 and (player.get('batting_rating') or 0) <= 2:
        age = max(19, age - random.choice([0, 1]))
    return age


def _initial_retire_age(player, current_age):
    target = random.choices([34, 35, 36, 37, 38, 39, 40], weights=[6, 10, 16, 18, 16, 10, 6], k=1)[0]
    if (player.get('bowling_rating') or 0) >= 4 and (player.get('batting_rating') or 0) <= 2:
        target -= 1
    if (player.get('batting_rating') or 0) >= 4:
        target += 1
    target = max(current_age + 1, min(41, target))
    return target


def _default_world_player_state(player, current_year):
    age = _initial_world_player_age(player)
    return {
        'form_adjustment': 0,
        'fatigue': 0,
        'career_runs': 0,
        'career_wickets': 0,
        'career_matches': 0,
        'last_match_dates': [],
        'age': age,
        'last_age_year': current_year,
        'active': 1,
        'retirement_reason': None,
        'retired_on': None,
        'regen_generation': 1 if player.get('is_regen') else 0,
        'retire_age': _initial_retire_age(player, age),
    }


def _ensure_world_player_states(db, world_id, world_state):
    current_year = int((world_state.get('current_date') or '2025-01-01')[:4] or '2025')
    player_states = world_state.setdefault('player_states', {})
    changed = False
    for tid, team_data in (world_state.get('teams') or {}).items():
        team_players = database.get_players_for_team(db, tid, world_id=world_id)
        world_state.setdefault('team_roster_targets', {})[tid] = max(11, len(team_players))
        active_players = []
        for player in team_players:
            pid = player['id']
            state = player_states.get(pid)
            if not state:
                state = _default_world_player_state(player, current_year)
                player_states[pid] = state
                changed = True
            state.setdefault('last_match_dates', [])
            if state.get('active', 1):
                active_players.append(player)
        team_data['players'] = sorted(active_players, key=lambda p: (p.get('batting_position') or 99, p.get('id') or 0))
    if changed:
        for pid, state in player_states.items():
            ps = dict(state)
            if isinstance(ps.get('last_match_dates'), list):
                ps['last_match_dates'] = json.dumps(ps['last_match_dates'])
            database.upsert_player_world_state(db, world_id, pid, ps)


def _world_sim_horizon_date(fixtures, world_state, target, target_date=None):
    user_team_ids = set(world_state.get('user_team_ids') or [])
    first_series_id = None
    horizon = world_state.get('current_date') or ''
    for fixture in fixtures:
        if fixture.get('status', 'scheduled') != 'scheduled':
            continue
        f_date = fixture.get('scheduled_date', '') or horizon
        if target == 'date' and target_date and f_date > target_date:
            return target_date
        if fixture.get('is_user_match'):
            return f_date
        if target == 'next_my_match' and user_team_ids:
            if fixture.get('team1_id') in user_team_ids or fixture.get('team2_id') in user_team_ids:
                return f_date
        if target == 'end_of_series':
            if first_series_id is None:
                first_series_id = fixture.get('series_id')
            elif fixture.get('series_id') != first_series_id:
                return horizon
        horizon = f_date
        if target == 'next_match':
            return horizon
    return horizon


def _should_retire_player(player, state):
    age = int(state.get('age') or 0)
    retire_age = int(state.get('retire_age') or max(age + 1, 36))
    injury_risk = 0.003 + max(0, age - 31) * 0.003
    if (player.get('bowling_rating') or 0) >= 4:
        injury_risk += 0.004
    if random.random() < min(0.16, injury_risk):
        return 'injury'
    if age >= retire_age:
        chance = 0.38 + max(0, age - retire_age) * 0.18
        if (player.get('batting_rating') or 0) >= 4 or (player.get('bowling_rating') or 0) >= 4:
            chance -= 0.06
        if random.random() < min(0.97, max(0.18, chance)):
            return 'age'
    if age >= retire_age - 1 and random.random() < 0.08:
        return 'age'
    return None


def _regen_name_pool_for_team(db, team):
    if not team:
        return None
    if team.get('name') in _REGEN_TEAM_POOL_OVERRIDES:
        return _REGEN_NAME_POOLS.get(_REGEN_TEAM_POOL_OVERRIDES[team['name']])
    league = team.get('league')
    if league and league in _REGEN_LEAGUE_POOL_OVERRIDES:
        return _REGEN_NAME_POOLS.get(_REGEN_LEAGUE_POOL_OVERRIDES[league])
    venue_id = team.get('home_venue_id')
    if venue_id:
        venue = database.get_venue(db, venue_id)
        country = (venue or {}).get('country')
        if country and country in _REGEN_TEAM_POOL_OVERRIDES:
            return _REGEN_NAME_POOLS.get(_REGEN_TEAM_POOL_OVERRIDES[country])
    return None


def _generate_regen_name(db, team):
    pool = _regen_name_pool_for_team(db, team) or {}
    first_names = pool.get('first') or _REGEN_FIRST_NAMES
    last_names = pool.get('last') or _REGEN_LAST_NAMES
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def _create_world_regen_player(db, world_id, team_id, template_player, year):
    bat_rating = max(1, min(5, int((template_player.get('batting_rating') or 3) + random.choice([-1, 0, 0, 1]))))
    bowl_rating = max(0, min(5, int((template_player.get('bowling_rating') or 0) + random.choice([-1, 0, 0, 1]))))
    if template_player.get('bowling_type') == 'none':
        bowl_rating = 0
    batting_position = template_player.get('batting_position') or random.randint(1, 11)
    team = database.get_team(db, team_id) or {}
    player_data = {
        'team_id': team_id,
        'name': _generate_regen_name(db, team),
        'batting_position': batting_position,
        'batting_rating': bat_rating,
        'batting_hand': random.choice(['right', 'left']),
        'bowling_type': template_player.get('bowling_type') or 'none',
        'bowling_action': template_player.get('bowling_action'),
        'bowling_rating': bowl_rating,
        'source_world_id': world_id,
        'is_regen': 1,
    }
    player_id = database.create_player(db, player_data)
    player = database.get_player(db, player_id)
    state = {
        'form_adjustment': 0,
        'fatigue': 0,
        'career_runs': 0,
        'career_wickets': 0,
        'career_matches': 0,
        'last_match_dates': '[]',
        'age': random.randint(18, 22),
        'last_age_year': year,
        'active': 1,
        'retirement_reason': None,
        'retired_on': None,
        'regen_generation': int((template_player.get('regen_generation') or 0)) + 1,
        'retire_age': random.randint(34, 39),
    }
    database.upsert_player_world_state(db, world_id, player_id, state)
    return player


def _apply_world_player_lifecycle(db, world_id, world_state, fixtures, target, target_date=None):
    if _world_player_lifecycle_mode(world_state) != 'realistic':
        return

    _ensure_world_player_states(db, world_id, world_state)
    current_date = world_state.get('current_date') or '2025-01-01'
    horizon_date = _world_sim_horizon_date(fixtures, world_state, target, target_date)
    if not horizon_date:
        return

    try:
        current_year = int(current_date[:4])
        horizon_year = int(horizon_date[:4])
    except Exception:
        return
    if horizon_year <= current_year:
        return

    player_states = world_state.setdefault('player_states', {})
    team_targets = world_state.setdefault('team_roster_targets', {})

    for year in range(current_year + 1, horizon_year + 1):
        for tid, team_data in (world_state.get('teams') or {}).items():
            roster = database.get_players_for_team(db, tid, world_id=world_id)
            retired_templates = []
            for player in roster:
                pid = player['id']
                state = player_states.setdefault(pid, _default_world_player_state(player, current_year))
                if not state.get('active', 1):
                    continue
                last_age_year = int(state.get('last_age_year') or current_year)
                if year <= last_age_year:
                    continue
                state['age'] = int(state.get('age') or _initial_world_player_age(player)) + (year - last_age_year)
                state['last_age_year'] = year
                reason = _should_retire_player(player, state)
                if reason:
                    state['active'] = 0
                    state['retirement_reason'] = reason
                    state['retired_on'] = f'{year}-01-01'
                    retired_templates.append((player, dict(state)))

            roster = database.get_players_for_team(db, tid, world_id=world_id)
            active_roster = [p for p in roster if int((player_states.get(p['id']) or {}).get('active', 1) or 0) == 1]
            target_size = max(11, team_targets.get(tid) or len(roster) or 11)
            team_targets[tid] = target_size
            while len(active_roster) < target_size:
                template_player = retired_templates[len(active_roster) % len(retired_templates)][0] if retired_templates else random.choice(roster or active_roster or team_data.get('players') or [{'batting_position': len(active_roster) + 1, 'batting_rating': 3, 'bowling_rating': 1, 'bowling_type': 'none'}])
                regen = _create_world_regen_player(db, world_id, tid, template_player, year)
                player_states[regen['id']] = {
                    'form_adjustment': 0,
                    'fatigue': 0,
                    'career_runs': 0,
                    'career_wickets': 0,
                    'career_matches': 0,
                    'last_match_dates': [],
                    'age': random.randint(18, 22),
                    'last_age_year': year,
                    'active': 1,
                    'retirement_reason': None,
                    'retired_on': None,
                    'regen_generation': 1,
                    'retire_age': random.randint(34, 39),
                }
                active_roster.append(regen)

            team_data['players'] = sorted(active_roster, key=lambda p: (p.get('batting_position') or 99, p.get('id') or 0))

    for pid, state in player_states.items():
        ps = dict(state)
        if isinstance(ps.get('last_match_dates'), list):
            ps['last_match_dates'] = json.dumps(ps['last_match_dates'])
        database.upsert_player_world_state(db, world_id, pid, ps)


def _check_world_records(db, world_id, match_id, match):
    """Check and update world records after a completed full (ball-by-ball) match."""
    import json as _json
    fmt        = match.get('format')
    match_date = match.get('match_date', '')

    all_innings = database.get_innings(db, match_id)
    for inn in all_innings:
        batting_id = inn.get('batting_team_id')
        bowling_id = inn.get('bowling_team_id')
        # Resolve names from the match dict
        if batting_id == match.get('team1_id'):
            bat_name, opp_name = match.get('team1_name', ''), match.get('team2_name', '')
        else:
            bat_name, opp_name = match.get('team2_name', ''), match.get('team1_name', '')

        total = inn.get('total_runs') or 0
        wkts  = inn.get('total_wickets') or 0

        # Highest team total
        ex = db.execute(
            "SELECT record_value FROM world_records WHERE world_id=? AND record_key='highest_team_total' AND format=?",
            (world_id, fmt)).fetchone()
        if total > 0 and (not ex or total > (ex['record_value'] or 0)):
            database.upsert_world_record(db, world_id, 'highest_team_total', total,
                _json.dumps({'team_name': bat_name, 'opponent_name': opp_name,
                             'match_date': match_date, 'match_id': match_id, 'value': total}), fmt)

        # Lowest team total (all-out only)
        if wkts >= 10 and total > 0:
            ex_low = db.execute(
                "SELECT record_value FROM world_records WHERE world_id=? AND record_key='lowest_team_total' AND format=?",
                (world_id, fmt)).fetchone()
            if not ex_low or total < (ex_low['record_value'] or 9999):
                database.upsert_world_record(db, world_id, 'lowest_team_total', total,
                    _json.dumps({'team_name': bat_name, 'opponent_name': opp_name,
                                 'match_date': match_date, 'match_id': match_id, 'value': total}), fmt)

        # Highest individual score
        batters = database.get_batter_innings(db, inn['id'])
        for bi in batters:
            runs = bi.get('runs') or 0
            ex_hs = db.execute(
                "SELECT record_value FROM world_records WHERE world_id=? AND record_key='highest_score' AND format=?",
                (world_id, fmt)).fetchone()
            if runs > 0 and (not ex_hs or runs > (ex_hs['record_value'] or 0)):
                database.upsert_world_record(db, world_id, 'highest_score', runs,
                    _json.dumps({'player_name': bi.get('player_name', ''), 'team_name': bat_name,
                                 'opponent_name': opp_name, 'match_date': match_date,
                                 'match_id': match_id, 'value': runs}), fmt)

        # Best bowling
        bowlers = database.get_bowler_innings(db, inn['id'])
        for bwi in bowlers:
            bw_wkts = bwi.get('wickets') or 0
            bw_runs = bwi.get('runs_conceded') or 0
            if bw_wkts > 0:
                ex_bb = db.execute(
                    "SELECT record_value, context_json FROM world_records "
                    "WHERE world_id=? AND record_key='best_bowling' AND format=?",
                    (world_id, fmt)).fetchone()
                better = not ex_bb
                if ex_bb:
                    ex_wk = ex_bb['record_value'] or 0
                    ex_rc = (_json.loads(ex_bb['context_json'] or '{}') or {}).get('runs_conceded', 9999)
                    better = bw_wkts > ex_wk or (bw_wkts == ex_wk and bw_runs < ex_rc)
                if better:
                    database.upsert_world_record(db, world_id, 'best_bowling', bw_wkts,
                        _json.dumps({'player_name': bwi.get('player_name', ''), 'team_name': opp_name,
                                     'opponent_name': bat_name, 'match_date': match_date,
                                     'match_id': match_id, 'value': bw_wkts,
                                     'runs_conceded': bw_runs}), fmt)


def _check_quick_sim_world_records(db, world_id, res, match_id, teams_map):
    """Check and update world records from a quick_sim match result."""
    import json as _json
    fmt        = res.get('format', 'T20')
    match_date = res.get('scheduled_date', '')
    t1_id      = res.get('team1_id')
    t2_id      = res.get('team2_id')
    t1_name    = (teams_map.get(t1_id) or {}).get('name', '?')
    t2_name    = (teams_map.get(t2_id) or {}).get('name', '?')

    def _parse_runs(score_str):
        try:
            return int(str(score_str).split('/')[0])
        except Exception:
            return 0

    for runs, bat_name, opp in [
        (_parse_runs(res.get('team1_score', '0')), t1_name, t2_name),
        (_parse_runs(res.get('team2_score', '0')), t2_name, t1_name),
    ]:
        if runs > 0:
            ex = db.execute(
                "SELECT record_value FROM world_records WHERE world_id=? AND record_key='highest_team_total' AND format=?",
                (world_id, fmt)).fetchone()
            if not ex or runs > (ex['record_value'] or 0):
                database.upsert_world_record(db, world_id, 'highest_team_total', runs,
                    _json.dumps({'team_name': bat_name, 'opponent_name': opp,
                                 'match_date': match_date, 'match_id': match_id, 'value': runs}), fmt)

    ts = res.get('top_scorer') or {}
    ts_runs = ts.get('runs') or 0
    if ts_runs > 0:
        ex_hs = db.execute(
            "SELECT record_value FROM world_records WHERE world_id=? AND record_key='highest_score' AND format=?",
            (world_id, fmt)).fetchone()
        if not ex_hs or ts_runs > (ex_hs['record_value'] or 0):
            ts_pid = ts.get('player_id')
            t1_pids = [p['id'] for p in (teams_map.get(t1_id) or {}).get('players', [])]
            scorer_team = t1_name if ts_pid in t1_pids else t2_name
            scorer_opp  = t2_name if scorer_team == t1_name else t1_name
            database.upsert_world_record(db, world_id, 'highest_score', ts_runs,
                _json.dumps({'player_name': ts.get('name', ''), 'team_name': scorer_team,
                             'opponent_name': scorer_opp, 'match_date': match_date,
                             'match_id': match_id, 'value': ts_runs}), fmt)

    tb = res.get('top_bowler') or {}
    tb_wkts = tb.get('wickets') or 0
    if tb_wkts > 0:
        ex_bb = db.execute(
            "SELECT record_value, context_json FROM world_records "
            "WHERE world_id=? AND record_key='best_bowling' AND format=?",
            (world_id, fmt)).fetchone()
        better = not ex_bb
        if ex_bb:
            ex_wk = ex_bb['record_value'] or 0
            ex_rc = (_json.loads(ex_bb['context_json'] or '{}') or {}).get('runs_conceded', 9999)
            better = tb_wkts > ex_wk or (tb_wkts == ex_wk and (tb.get('runs') or 0) < ex_rc)
        if better:
            tb_pid = tb.get('player_id')
            t1_pids = [p['id'] for p in (teams_map.get(t1_id) or {}).get('players', [])]
            bowl_team = t1_name if tb_pid in t1_pids else t2_name
            bowl_opp  = t2_name if bowl_team == t1_name else t1_name
            database.upsert_world_record(db, world_id, 'best_bowling', tb_wkts,
                _json.dumps({'player_name': tb.get('name', ''), 'team_name': bowl_team,
                             'opponent_name': bowl_opp, 'match_date': match_date,
                             'match_id': match_id, 'value': tb_wkts,
                             'runs_conceded': tb.get('runs') or 0}), fmt)


def _parse_quick_scoreline(score_str):
    text = str(score_str or '').strip()
    if not text:
        return 0, 0, 0.0
    parts = text.split()
    score_bits = parts[0]
    overs_text = parts[1] if len(parts) > 1 else '0.0'
    try:
        runs_text, wkts_text = score_bits.split('/', 1)
        runs = int(runs_text)
        wkts = int(wkts_text)
    except Exception:
        runs, wkts = 0, 0
    try:
        overs = float(overs_text)
    except Exception:
        overs = 0.0
    return runs, wkts, overs


def _cricket_overs_to_balls(overs_value):
    text = str(overs_value or '0')
    if '.' in text:
        ovs, balls = text.split('.', 1)
        return max(0, int(ovs or 0) * 6 + int((balls or '0')[:1] or 0))
    return max(0, int(float(text) * 6))


def _balls_to_cricket_overs(ball_count):
    overs = max(0, int(ball_count or 0)) // 6
    balls = max(0, int(ball_count or 0)) % 6
    return float(f"{overs}.{balls}")


def _allocate_integer_total(weights, total, minimums=None):
    if total <= 0 or not weights:
        return [0 for _ in weights]
    if minimums is None:
        minimums = [0 for _ in weights]
    minimums = list(minimums) + [0] * max(0, len(weights) - len(minimums))
    allocations = minimums[:len(weights)]
    remaining = max(0, total - sum(allocations))
    if remaining == 0:
        return allocations
    shaped = [max(0.1, float(w)) * random.uniform(0.8, 1.2) for w in weights]
    weight_sum = sum(shaped) or 1.0
    raw = [(w / weight_sum) * remaining for w in shaped]
    ints = [int(x) for x in raw]
    fracs = sorted(
        range(len(raw)),
        key=lambda idx: (raw[idx] - ints[idx]),
        reverse=True
    )
    for idx, val in enumerate(ints):
        allocations[idx] += val
    leftover = remaining - sum(ints)
    for idx in fracs[:leftover]:
        allocations[idx] += 1
    return allocations


def _boundary_breakdown(runs):
    remaining = max(0, int(runs or 0))
    sixes = 0
    fours = 0
    if remaining >= 12:
        six_cap = min(remaining // 6, 4)
        sixes = random.randint(0, six_cap)
        remaining -= sixes * 6
    if remaining >= 4:
        four_cap = min(remaining // 4, 10)
        fours = random.randint(0, four_cap)
        remaining -= fours * 4
    return fours, sixes


def _persist_quick_sim_innings(db, match_id, innings_number, batting_team_id, bowling_team_id,
                               total_runs, total_wickets, overs_completed, fmt,
                               top_scorer=None, top_bowler=None):
    innings_id = database.create_innings(db, match_id, innings_number, batting_team_id, bowling_team_id)

    batting_players = sorted(
        database.get_players_for_team(db, batting_team_id),
        key=lambda p: (p.get('batting_position') or 99, p.get('id') or 0)
    )
    bowling_players = [
        p for p in database.get_players_for_team(db, bowling_team_id)
        if p.get('bowling_type') != 'none'
    ]
    bowling_players = sorted(
        bowling_players,
        key=lambda p: (-(p.get('bowling_rating') or 0), p.get('id') or 0)
    )

    batter_row_ids = {}
    for p in batting_players:
        batter_row_ids[p['id']] = database.create_batter_innings(
            db, innings_id, p['id'], p.get('batting_position')
        )

    bowler_row_ids = {}
    for p in bowling_players:
        bowler_row_ids[p['id']] = database.create_bowler_innings(db, innings_id, p['id'])

    total_balls = max(12, _cricket_overs_to_balls(overs_completed))
    extra_cap = min(max(4, total_runs // 12), 20)
    extras_total = min(total_runs, random.randint(4, extra_cap)) if total_runs > 0 else 0
    batting_total = max(0, total_runs - extras_total)
    dismissed_count = max(0, min(int(total_wickets or 0), 10))

    min_batted = dismissed_count + 1 if dismissed_count >= 10 else dismissed_count + 2
    batters_used = min(len(batting_players), max(2, min_batted))
    active_batters = batting_players[:batters_used]

    run_weights = []
    for idx, p in enumerate(active_batters):
        base = max(1.0, 14 - idx + (p.get('batting_rating') or 3) * 1.8)
        if top_scorer and p['id'] == top_scorer.get('player_id'):
            base *= 2.4
        run_weights.append(base)
    run_alloc = _allocate_integer_total(run_weights, batting_total)
    if top_scorer and top_scorer.get('player_id') in [p['id'] for p in active_batters]:
        anchor_idx = next(i for i, p in enumerate(active_batters) if p['id'] == top_scorer.get('player_id'))
        top_idx = max(range(len(run_alloc)), key=lambda i: run_alloc[i])
        if top_idx != anchor_idx:
            run_alloc[anchor_idx], run_alloc[top_idx] = run_alloc[top_idx], run_alloc[anchor_idx]

    ball_weights = [
        max(1.0, runs + (8 if idx < 2 else 3) + random.uniform(0, 6))
        for idx, runs in enumerate(run_alloc)
    ]
    ball_minimums = [1 if runs > 0 else 0 for runs in run_alloc]
    balls_alloc = _allocate_integer_total(ball_weights, total_balls, minimums=ball_minimums)

    not_out_count = 1 if dismissed_count >= 10 else max(1, batters_used - dismissed_count)
    dismissed_batters = active_batters[:dismissed_count]
    not_out_batters = active_batters[dismissed_count:dismissed_count + not_out_count]

    byes = random.randint(0, min(4, extras_total))
    remaining_extras = extras_total - byes
    leg_byes = random.randint(0, min(4, remaining_extras))
    remaining_extras -= leg_byes
    wides = random.randint(0, remaining_extras)
    remaining_extras -= wides
    no_balls = remaining_extras

    innings_row = database.get_innings_by_id(db, innings_id)
    database.update_innings(db, innings_id, _apply_innings_cutoff_snapshots(innings_row, {
        'total_runs': total_runs,
        'total_wickets': total_wickets,
        'overs_completed': overs_completed,
        'extras_byes': byes,
        'extras_legbyes': leg_byes,
        'extras_wides': wides,
        'extras_noballs': no_balls,
        'status': 'complete',
    }))

    for idx, batter in enumerate(active_batters):
        runs = run_alloc[idx]
        balls = max(1 if runs > 0 else 0, balls_alloc[idx])
        fours, sixes = _boundary_breakdown(runs)
        update = {
            'runs': runs,
            'balls_faced': balls,
            'fours': fours,
            'sixes': sixes,
        }
        if batter in dismissed_batters:
            update.update({
                'dismissal_type': random.choice(['caught', 'bowled', 'lbw', 'run out']),
                'not_out': 0,
                'status': 'dismissed',
            })
        elif batter in not_out_batters:
            update.update({
                'not_out': 1,
                'status': 'batting',
            })
        database.update_batter_innings(db, batter_row_ids[batter['id']], update)

    running_score = 0
    running_balls = 0
    if len(active_batters) >= 2:
        opening_pid_1 = active_batters[0]['id']
        opening_pid_2 = active_batters[1]['id']
        partnership_id = database.create_partnership(db, innings_id, 0, opening_pid_1, opening_pid_2)
        if dismissed_count:
            first_partnership_runs = max(0, int(total_runs * random.uniform(0.08, 0.18)))
            first_partnership_balls = max(6, int(total_balls * random.uniform(0.08, 0.18)))
        else:
            first_partnership_runs = total_runs
            first_partnership_balls = total_balls
        database.update_partnership(db, partnership_id, {
            'runs': min(total_runs, first_partnership_runs),
            'balls': min(total_balls, first_partnership_balls),
        })

    for wicket_no, batter in enumerate(dismissed_batters, start=1):
        remaining_wickets = max(1, dismissed_count - wicket_no + 1)
        remaining_runs = max(0, total_runs - running_score)
        remaining_balls = max(1, total_balls - running_balls)
        increment_runs = remaining_runs if wicket_no == dismissed_count else max(
            1, int(remaining_runs / remaining_wickets * random.uniform(0.75, 1.15))
        )
        increment_balls = remaining_balls if wicket_no == dismissed_count else max(
            1, int(remaining_balls / remaining_wickets * random.uniform(0.75, 1.15))
        )
        running_score = min(total_runs, running_score + increment_runs)
        running_balls = min(total_balls, running_balls + increment_balls)
        database.insert_fall_of_wicket(
            db, innings_id, wicket_no, running_score,
            _balls_to_cricket_overs(running_balls), batter['id']
        )
        if wicket_no < batters_used - 1:
            b1 = active_batters[min(wicket_no, batters_used - 2)]['id']
            b2 = active_batters[min(wicket_no + 1, batters_used - 1)]['id']
            pid = database.create_partnership(db, innings_id, wicket_no, b1, b2)
            next_runs = max(0, total_runs - running_score) if wicket_no == dismissed_count else max(
                0, int((total_runs - running_score) / max(1, remaining_wickets - 1))
            )
            next_balls = max(0, total_balls - running_balls) if wicket_no == dismissed_count else max(
                0, int((total_balls - running_balls) / max(1, remaining_wickets - 1))
            )
            database.update_partnership(db, pid, {'runs': next_runs, 'balls': next_balls})

    if dismissed_count == 0 and len(active_batters) >= 2:
        # Keep opening partnership as full unbeaten stand
        pass

    bowlers_used = bowling_players[:min(len(bowling_players), 5 if fmt in ('T20', 'ODI') else 6)]
    if top_bowler and top_bowler.get('player_id') and all(p['id'] != top_bowler['player_id'] for p in bowlers_used):
        anchored = next((p for p in bowling_players if p['id'] == top_bowler.get('player_id')), None)
        if anchored:
            bowlers_used = ([anchored] + bowlers_used)[:max(1, len(bowlers_used))]

    max_balls_per_bowler = {'T20': 24, 'ODI': 60}.get(fmt)
    bowling_weights = []
    for idx, bowler in enumerate(bowlers_used):
        base = max(1.0, (bowler.get('bowling_rating') or 3) * 2.2 - idx * 0.4)
        if top_bowler and bowler['id'] == top_bowler.get('player_id'):
            base *= 1.8
        bowling_weights.append(base)
    balls_alloc = _allocate_integer_total(bowling_weights, total_balls)
    if max_balls_per_bowler:
        overflow = 0
        for idx, balls in enumerate(balls_alloc):
            if balls > max_balls_per_bowler:
                overflow += balls - max_balls_per_bowler
                balls_alloc[idx] = max_balls_per_bowler
        idx = 0
        while overflow > 0 and bowlers_used:
            cap_left = max_balls_per_bowler - balls_alloc[idx % len(bowlers_used)]
            if cap_left > 0:
                add = min(cap_left, overflow)
                balls_alloc[idx % len(bowlers_used)] += add
                overflow -= add
            idx += 1

    wicket_weights = []
    for idx, bowler in enumerate(bowlers_used):
        base = max(1.0, (bowler.get('bowling_rating') or 3) + random.uniform(0, 2))
        if top_bowler and bowler['id'] == top_bowler.get('player_id'):
            base *= 2.2
        wicket_weights.append(base)
    wickets_alloc = _allocate_integer_total(wicket_weights, total_wickets)
    if top_bowler and top_bowler.get('player_id') in [p['id'] for p in bowlers_used]:
        anchor_idx = next(i for i, p in enumerate(bowlers_used) if p['id'] == top_bowler.get('player_id'))
        top_idx = max(range(len(wickets_alloc)), key=lambda i: wickets_alloc[i])
        if top_idx != anchor_idx:
            wickets_alloc[anchor_idx], wickets_alloc[top_idx] = wickets_alloc[top_idx], wickets_alloc[anchor_idx]

    run_weights = []
    for idx, bowler in enumerate(bowlers_used):
        base = max(1.0, balls_alloc[idx] + random.uniform(0, 8))
        if top_bowler and bowler['id'] == top_bowler.get('player_id'):
            base *= 0.8
        run_weights.append(base)
    runs_alloc = _allocate_integer_total(run_weights, total_runs)

    for idx, bowler in enumerate(bowlers_used):
        balls = balls_alloc[idx]
        overs = balls // 6
        rem_balls = balls % 6
        conceded = runs_alloc[idx]
        wickets = wickets_alloc[idx]
        maiden_cap = overs if conceded <= overs * 3 else max(0, overs - 1)
        maidens = random.randint(0, maiden_cap) if maiden_cap > 0 else 0
        wides_conceded = min(wides, random.randint(0, wides)) if wides else 0
        no_balls_conceded = min(no_balls, random.randint(0, no_balls)) if no_balls else 0
        database.update_bowler_innings(db, bowler_row_ids[bowler['id']], {
            'overs': overs,
            'balls': rem_balls,
            'maidens': maidens,
            'runs_conceded': conceded,
            'wickets': wickets,
            'wides': wides_conceded,
            'no_balls': no_balls_conceded,
        })

    return innings_id


def _persist_world_sim(db, world_id, results, new_current_date, updated_player_states,
                       world_state=None):
    """Persist simulate_world_to() results into the database."""
    import json

    def _pick_quick_sim_pom_id(match_result):
        top_bat = match_result.get('top_scorer') or {}
        top_bowl = match_result.get('top_bowler') or {}
        bat_score = (top_bat.get('runs') or 0)
        bowl_score = (top_bowl.get('wickets') or 0) * 20 - (top_bowl.get('runs') or 0) * 0.1
        if top_bat.get('player_id') and bat_score >= bowl_score:
            return top_bat.get('player_id')
        if top_bowl.get('player_id'):
            return top_bowl.get('player_id')
        return top_bat.get('player_id') or None

    # Default venue fallback
    venues = database.get_venues(db)
    fallback_venue_id = venues[0]['id'] if venues else 1

    # Load current rankings
    all_ranking_rows  = database.get_world_rankings(db, world_id)
    rankings_by_fmt   = {}
    matches_by_fmt_team = {}  # {fmt: {tid: count}} — for incrementing matches_counted
    for r in all_ranking_rows:
        fmt = r['format']
        rankings_by_fmt.setdefault(fmt, {})[r['team_id']] = r['points']
        matches_by_fmt_team.setdefault(fmt, {})[r['team_id']] = r['matches_counted']

    for res in results:
        fixture_id = res.get('fixture_id')
        fmt        = res.get('format', 'T20')
        team1_id   = res.get('team1_id')
        team2_id   = res.get('team2_id')
        winner_id  = res.get('winner_id')
        top_scorer = res.get('top_scorer') or {}
        top_bowler = res.get('top_bowler') or {}
        team1_player_ids = {p['id'] for p in (world_state.get('teams', {}).get(team1_id) or {}).get('players', [])} if world_state else set()
        team2_player_ids = {p['id'] for p in (world_state.get('teams', {}).get(team2_id) or {}).get('players', [])} if world_state else set()

        # Determine venue from fixture if possible
        venue_id = fallback_venue_id
        if fixture_id:
            row = db.execute("SELECT venue_id FROM fixtures WHERE id=?", (fixture_id,)).fetchone()
            if row and row['venue_id']:
                venue_id = row['venue_id']

        # Create a completed match record
        match_id = database.create_match(db, {
            'world_id':   world_id,
            'format':     fmt,
            'venue_id':   venue_id,
            'match_date': res.get('scheduled_date', new_current_date),
            'team1_id':   team1_id,
            'team2_id':   team2_id,
        })
        database.update_match(db, match_id, {
            'result_type':      res.get('result_type'),
            'winning_team_id':  winner_id,
            'margin_runs':      res.get('margin_runs'),
            'margin_wickets':   res.get('margin_wickets'),
            'player_of_match_id': _pick_quick_sim_pom_id(res),
            'status':           'complete',
            'match_notes':      json.dumps({
                'quick_sim':   True,
                'team1_score': res.get('team1_score'),
                'team2_score': res.get('team2_score'),
                'top_scorer':  res.get('top_scorer'),
                'top_bowler':  res.get('top_bowler'),
            }),
        })

        t1_runs, t1_wkts, t1_overs = _parse_quick_scoreline(res.get('team1_score'))
        t2_runs, t2_wkts, t2_overs = _parse_quick_scoreline(res.get('team2_score'))
        _persist_quick_sim_innings(
            db, match_id, 1, team1_id, team2_id,
            t1_runs, t1_wkts, t1_overs, fmt,
            top_scorer=top_scorer if top_scorer.get('player_id') in team1_player_ids else None,
            top_bowler=top_bowler if top_bowler.get('player_id') in team2_player_ids else None,
        )
        _persist_quick_sim_innings(
            db, match_id, 2, team2_id, team1_id,
            t2_runs, t2_wkts, t2_overs, fmt,
            top_scorer=top_scorer if top_scorer.get('player_id') in team2_player_ids else None,
            top_bowler=top_bowler if top_bowler.get('player_id') in team1_player_ids else None,
        )

        if fixture_id:
            database.update_fixture(db, fixture_id, {'match_id': match_id, 'status': 'complete'})

        # Update world records
        _teams_map = world_state.get('teams', {}) if world_state else {}
        _check_quick_sim_world_records(db, world_id, res, match_id, _teams_map)

        # Snapshot rankings history (once per match per team per format)
        for tid in [team1_id, team2_id]:
            if tid:
                cur_pts = rankings_by_fmt.setdefault(fmt, {}).get(tid, 0)
                cur_pos = matches_by_fmt_team.setdefault(fmt, {}).get(tid, 0)
                database.insert_ranking_history(
                    db, world_id, tid, fmt, cur_pts,
                    cur_pos, res.get('scheduled_date', new_current_date), match_id)

        # Update rankings
        cur_pts = rankings_by_fmt.setdefault(fmt, {})
        updated = game_engine.update_rankings(cur_pts, {
            'winning_team_id': winner_id,
            'losing_team_id':  res.get('loser_id'),
            'team1_id':        team1_id,
            'team2_id':        team2_id,
            'is_draw':         res.get('result_type') == 'draw',
        }, home_team_id=res.get('home_team_id'))
        rankings_by_fmt[fmt] = updated

        for tid in [team1_id, team2_id]:
            if tid:
                matches_by_fmt_team.setdefault(fmt, {})[tid] = \
                    matches_by_fmt_team.get(fmt, {}).get(tid, 0) + 1

    # Persist rankings
    for fmt, team_pts in rankings_by_fmt.items():
        sorted_teams = sorted(team_pts.items(), key=lambda x: -x[1])
        for pos, (tid, pts) in enumerate(sorted_teams, 1):
            mc = matches_by_fmt_team.get(fmt, {}).get(tid, 0)
            database.upsert_world_ranking(db, world_id, tid, fmt, pts, pos, mc)

    # Persist player states
    for pid, state in updated_player_states.items():
        ps = dict(state)
        if isinstance(ps.get('last_match_dates'), list):
            ps['last_match_dates'] = json.dumps(ps['last_match_dates'])
        ps['fatigue'] = 1 if ps.get('fatigue') else 0
        database.upsert_player_world_state(db, world_id, pid, ps)

    # Advance world current date
    database.update_world(db, world_id, {'current_date': new_current_date})
    _advance_world_competitions(db, world_id)


def _user_team_ids(settings):
    """Return a set of all user-controlled team IDs from a world settings dict."""
    ids = set()
    if settings.get('my_team_id'):
        ids.add(int(settings['my_team_id']))
    if settings.get('my_domestic_team_id'):
        ids.add(int(settings['my_domestic_team_id']))
    return ids


def _fixture_result_string(fixture):
    rt = fixture.get('result_type')
    winner = fixture.get('winning_team_name', '')
    if fixture.get('status') != 'complete' or not rt:
        return ''
    if rt == 'runs':
        return f"{winner} won by {fixture.get('margin_runs') or 0} runs"
    if rt == 'wickets':
        return f"{winner} won by {fixture.get('margin_wickets') or 0} wickets"
    if rt == 'draw':
        return 'Match drawn'
    if rt == 'tie':
        return 'Match tied'
    if rt == 'no_result':
        return 'No result'
    return str(rt)


def _world_competition_rows(db, world_id, competition_key):
    rows = db.execute(
        "SELECT f.id, f.world_id, f.scheduled_date, f.status, f.fixture_type, f.format, "
        " f.is_user_match, f.match_id, f.series_name, f.match_number_in_series, f.series_length, "
        " f.tour_template, f.season_year, f.competition_key, f.competition_name, "
        " f.competition_stage, f.competition_group, f.competition_round, f.competition_order, "
        " f.is_icc_event, f.icc_event_name, f.team1_id, f.team2_id, "
        " t1.name as team1_name, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.badge_colour as team2_colour, "
        " v.name as venue_name, "
        " m.result_type, m.margin_runs, m.margin_wickets, m.winning_team_id, "
        " wt.name as winning_team_name "
        "FROM fixtures f "
        "JOIN teams t1 ON f.team1_id = t1.id "
        "JOIN teams t2 ON f.team2_id = t2.id "
        "LEFT JOIN venues v ON f.venue_id = v.id "
        "LEFT JOIN matches m ON f.match_id = m.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE f.world_id = ? AND f.competition_key = ? "
        "ORDER BY COALESCE(f.competition_order, 999999), f.scheduled_date, f.id",
        (world_id, competition_key)
    ).fetchall()
    fixtures = [dict(r) for r in rows]
    for fixture in fixtures:
        fixture['result_string'] = _fixture_result_string(fixture)
    return fixtures


def _competition_match_innings(db, match_ids):
    if not match_ids:
        return {}
    placeholders = ','.join('?' for _ in match_ids)
    rows = db.execute(
        "SELECT match_id, innings_number, batting_team_id, total_runs, total_wickets, overs_completed "
        f"FROM innings WHERE match_id IN ({placeholders}) ORDER BY match_id, innings_number",
        list(match_ids)
    ).fetchall()
    out = {}
    for row in rows:
        r = dict(row)
        out.setdefault(r['match_id'], []).append(r)
    return out


def _limited_team_stats(innings_rows):
    stats = {}
    for inn in innings_rows[:2]:
        tid = inn.get('batting_team_id')
        if tid:
            stats[tid] = {
                'runs': int(inn.get('total_runs') or 0),
                'overs': _cricket_overs_to_decimal(inn.get('overs_completed') or 0, fallback=0.0),
                'wickets': int(inn.get('total_wickets') or 0),
            }
    return stats


def _county_bonus_points(innings_rows):
    by_team = {}
    seen = set()
    for inn in innings_rows:
        tid = inn.get('batting_team_id')
        if tid and tid not in seen:
            seen.add(tid)
            snapshot_runs = inn.get('runs_at_110_overs')
            snapshot_wickets = inn.get('wickets_at_110_overs')
            runs = int(snapshot_runs if snapshot_runs is not None else (inn.get('total_runs') or 0))
            wickets_lost = int(snapshot_wickets if snapshot_wickets is not None else (inn.get('total_wickets') or 0))
            bat = 0
            for threshold in (250, 300, 350, 400, 450):
                if runs >= threshold:
                    bat += 1
            bowl = 0
            for threshold in (3, 6, 9):
                if wickets_lost >= threshold:
                    bowl += 1
            by_team[tid] = {'batting_bonus': bat, 'bowling_bonus': bowl}
        if len(by_team) >= 2:
            break
    return by_team


def _shield_bonus_points(innings_rows):
    by_team = {}
    seen = set()
    for inn in innings_rows:
        tid = inn.get('batting_team_id')
        if tid and tid not in seen:
            seen.add(tid)
            snapshot_runs = inn.get('runs_at_100_overs')
            snapshot_wickets = inn.get('wickets_at_100_overs')
            overs = _cricket_overs_to_decimal(inn.get('overs_completed') or 0, fallback=0.0)
            if snapshot_runs is not None and snapshot_wickets is not None:
                runs = int(snapshot_runs)
                wickets_lost = int(snapshot_wickets)
            else:
                runs = int(inn.get('total_runs') or 0)
                wickets_lost = int(inn.get('total_wickets') or 0)
                if not (overs and overs <= 100):
                    by_team[tid] = {'batting_bonus': 0.0, 'bowling_bonus': 0.0}
                    if len(by_team) >= 2:
                        break
                    continue
            bat = round(max(0.0, runs - 200) * 0.01, 2)
            bowl = round(min(10, wickets_lost) * 0.1, 2)
            by_team[tid] = {'batting_bonus': bat, 'bowling_bonus': bowl}
        if len(by_team) >= 2:
            break
    return by_team


def _marsh_victory_bonus(fixture, innings_rows):
    if not innings_rows or fixture.get('result_type') not in ('runs', 'wickets'):
        return {}
    limited = _limited_team_stats(innings_rows)
    winner_id = fixture.get('winning_team_id')
    if not winner_id or winner_id not in limited:
        return {}
    loser_id = fixture.get('team1_id') if winner_id == fixture.get('team2_id') else fixture.get('team2_id')
    if loser_id not in limited:
        return {}

    winner = limited[winner_id]
    loser = limited[loser_id]
    winner_batted_second = innings_rows[1].get('batting_team_id') == winner_id if len(innings_rows) > 1 else False

    # Marsh Cup bonus point: either win while batting first with run rate >= 1.25 x opponent,
    # or chase the target inside 40 overs.
    if winner_batted_second:
        if (winner.get('overs') or 0) <= 40:
            return {winner_id: {'batting_bonus': 1}}
        return {}

    loser_overs = loser.get('overs') or 0
    winner_overs = winner.get('overs') or 0
    if winner_overs > 0 and loser_overs > 0:
        winner_rr = winner['runs'] / winner_overs
        loser_rr = loser['runs'] / loser_overs
        if winner_rr >= loser_rr * 1.25:
            return {winner_id: {'batting_bonus': 1}}
    return {}


def _sort_competition_rows(rows, tie_breakers):
    def key(row):
        vals = []
        for breaker in tie_breakers or []:
            if breaker in ('points', 'wins', 'nrr', 'pct'):
                vals.append(-(row.get(breaker) or 0))
            else:
                vals.append(row.get(breaker) or '')
        vals.append(row.get('team_name') or '')
        return tuple(vals)
    ordered = sorted(rows, key=key)
    for idx, row in enumerate(ordered, start=1):
        row['position'] = idx
    return ordered


def _build_competition_standings(rule, fixtures, innings_map):
    points_system = (rule or {}).get('points_system', 'limited_nrr')
    grouping_mode = (rule or {}).get('standings_grouping', 'combined')
    standings = {}

    def ensure_team(tid, name, colour, group_name=None):
        if tid not in standings:
            standings[tid] = {
                'team_id': tid,
                'team_name': name or '?',
                'badge_colour': colour or '#888',
                'competition_group': group_name,
                'played': 0,
                'won': 0,
                'lost': 0,
                'drawn': 0,
                'tied': 0,
                'no_result': 0,
                'points': 0,
                'wins': 0,
                'runs_scored': 0,
                'runs_conceded': 0,
                'overs_faced': 0.0,
                'overs_bowled': 0.0,
                'nrr': 0.0,
                'batting_bonus': 0,
                'bowling_bonus': 0,
                'pct': 0.0,
            }
        elif group_name and not standings[tid].get('competition_group'):
            standings[tid]['competition_group'] = group_name
        return standings[tid]

    for fixture in fixtures:
        group_name = fixture.get('competition_group')
        t1 = ensure_team(fixture.get('team1_id'), fixture.get('team1_name'), fixture.get('team1_colour'), group_name)
        t2 = ensure_team(fixture.get('team2_id'), fixture.get('team2_name'), fixture.get('team2_colour'), group_name)
        if fixture.get('status') != 'complete':
            continue

        t1['played'] += 1
        t2['played'] += 1
        rt = fixture.get('result_type')
        winner_id = fixture.get('winning_team_id')
        if rt in ('runs', 'wickets') and winner_id:
            if winner_id == fixture.get('team1_id'):
                t1['won'] += 1
                t1['wins'] += 1
                t2['lost'] += 1
            elif winner_id == fixture.get('team2_id'):
                t2['won'] += 1
                t2['wins'] += 1
                t1['lost'] += 1
        elif rt == 'draw':
            t1['drawn'] += 1
            t2['drawn'] += 1
        elif rt == 'tie':
            t1['tied'] += 1
            t2['tied'] += 1
        elif rt == 'no_result':
            t1['no_result'] += 1
            t2['no_result'] += 1

        innings_rows = innings_map.get(fixture.get('match_id'), [])
        limited = _limited_team_stats(innings_rows)
        for team, opp in ((t1, t2), (t2, t1)):
            tid = team['team_id']
            oid = opp['team_id']
            if tid in limited:
                team['runs_scored'] += limited[tid]['runs']
                team['overs_faced'] += limited[tid]['overs']
            if oid in limited:
                team['runs_conceded'] += limited[oid]['runs']
                team['overs_bowled'] += limited[oid]['overs']

        if points_system in ('limited_nrr', 'marsh_cup'):
            if rt in ('runs', 'wickets') and winner_id:
                if winner_id == fixture.get('team1_id'):
                    t1['points'] += 2 if points_system == 'limited_nrr' else 4
                elif winner_id == fixture.get('team2_id'):
                    t2['points'] += 2 if points_system == 'limited_nrr' else 4
            elif rt in ('tie', 'no_result'):
                split = 1 if points_system == 'limited_nrr' else 2
                t1['points'] += split
                t2['points'] += split
            if points_system == 'marsh_cup':
                for tid, extra in _marsh_victory_bonus(fixture, innings_rows).items():
                    if tid in standings:
                        standings[tid]['batting_bonus'] += extra.get('batting_bonus', 0)
                        standings[tid]['points'] += extra.get('batting_bonus', 0)
        elif points_system == 'county':
            if rt in ('runs', 'wickets') and winner_id:
                if winner_id == fixture.get('team1_id'):
                    t1['points'] += 16
                elif winner_id == fixture.get('team2_id'):
                    t2['points'] += 16
            elif rt == 'draw':
                t1['points'] += 8
                t2['points'] += 8
            elif rt == 'tie':
                t1['points'] += 8
                t2['points'] += 8
            elif rt == 'no_result':
                t1['points'] += 8
                t2['points'] += 8
            bonus = _county_bonus_points(innings_rows)
            for tid, vals in bonus.items():
                if tid in standings:
                    standings[tid]['batting_bonus'] += vals.get('batting_bonus', 0)
                    standings[tid]['bowling_bonus'] += vals.get('bowling_bonus', 0)
                    standings[tid]['points'] += vals.get('batting_bonus', 0) + vals.get('bowling_bonus', 0)
        elif points_system == 'shield':
            if rt in ('runs', 'wickets') and winner_id:
                if winner_id == fixture.get('team1_id'):
                    t1['points'] += 6
                elif winner_id == fixture.get('team2_id'):
                    t2['points'] += 6
            elif rt == 'draw':
                t1['points'] += 1
                t2['points'] += 1
            elif rt == 'tie':
                t1['points'] += 3
                t2['points'] += 3
            elif rt == 'no_result':
                t1['points'] += 3
                t2['points'] += 3
            bonus = _shield_bonus_points(innings_rows)
            for tid, vals in bonus.items():
                if tid in standings:
                    standings[tid]['batting_bonus'] += vals.get('batting_bonus', 0)
                    standings[tid]['bowling_bonus'] += vals.get('bowling_bonus', 0)
                    standings[tid]['points'] += vals.get('batting_bonus', 0) + vals.get('bowling_bonus', 0)

    for row in standings.values():
        if row['overs_faced'] > 0 and row['overs_bowled'] > 0:
            row['nrr'] = round(
                (row['runs_scored'] / row['overs_faced']) - (row['runs_conceded'] / row['overs_bowled']),
                3
            )
        if points_system == 'wtc':
            possible = max(1, row['played'] * 12)
            row['pct'] = round((row['points'] / possible) * 100, 2)

    grouped = {}
    for row in standings.values():
        group_name = row.get('competition_group') if grouping_mode == 'by_group' else 'Standings'
        grouped.setdefault(group_name or 'Standings', []).append(row)

    ordered_groups = []
    for group_name, rows in grouped.items():
        ordered_groups.append({
            'group': group_name,
            'rows': _sort_competition_rows(rows, (rule or {}).get('tie_breakers', [])),
        })
    ordered_groups.sort(key=lambda g: g['group'])
    flat = [row for group in ordered_groups for row in group['rows']]
    return flat, ordered_groups


def _competition_stage_blocks(fixtures):
    blocks = {}
    for fixture in fixtures:
        stage = fixture.get('competition_stage') or fixture.get('fixture_type') or 'league'
        blocks.setdefault(stage, []).append(fixture)
    return blocks


def _competition_next_date(fixtures, gap_days=2):
    from datetime import date, timedelta
    max_date = None
    for fixture in fixtures:
        try:
            dt = date.fromisoformat(fixture.get('scheduled_date'))
        except Exception:
            continue
        max_date = dt if max_date is None or dt > max_date else max_date
    base = max_date or date.today()
    return (base + timedelta(days=gap_days)).isoformat()


def _competition_add_world_fixture(db, world_id, template, team1_id, team2_id, stage, round_label, order_index, match_date, group_name=None):
    before = db.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM fixtures").fetchone()['max_id']
    database.bulk_create_fixtures(db, [{
        'world_id': world_id,
        'tournament_id': None,
        'series_id': None,
        'scheduled_date': match_date,
        'venue_id': template.get('venue_id'),
        'team1_id': team1_id,
        'team2_id': team2_id,
        'fixture_type': stage,
        'format': template.get('format'),
        'is_user_match': template.get('is_user_match', 0),
        'series_name': template.get('series_name'),
        'match_number_in_series': order_index + 1,
        'series_length': 1,
        'is_icc_event': template.get('is_icc_event', False),
        'icc_event_name': template.get('icc_event_name'),
        'is_home_for_team1': True,
        'tour_template': template.get('tour_template'),
        'season_year': template.get('season_year'),
        'competition_key': template.get('competition_key'),
        'competition_name': template.get('competition_name'),
        'competition_stage': stage,
        'competition_group': group_name,
        'competition_round': round_label,
        'competition_order': (template.get('competition_order') or 0) + order_index + 1000,
    }])
    row = db.execute("SELECT MAX(id) AS max_id FROM fixtures").fetchone()
    return row['max_id'] if row and row['max_id'] and row['max_id'] > before else None


def _advance_world_competitions(db, world_id):
    rows = db.execute(
        "SELECT DISTINCT competition_key, series_name "
        "FROM fixtures WHERE world_id = ? AND competition_key IS NOT NULL",
        (world_id,)
    ).fetchall()
    advanced = 0
    for row in rows:
        competition_key = row['competition_key']
        season_name = row['series_name']
        fixtures = [f for f in _world_competition_rows(db, world_id, competition_key) if f.get('series_name') == season_name]
        if not fixtures:
            continue
        rule = competition_rules.get_rule(competition_key)
        if not rule:
            continue
        stages = _competition_stage_blocks(fixtures)
        league_done = stages.get('league') and all(f.get('status') == 'complete' for f in stages.get('league', []))
        match_ids = [f.get('match_id') for f in fixtures if f.get('match_id')]
        innings_map = _competition_match_innings(db, match_ids)
        _, grouped = _build_competition_standings(rule, stages.get('league', []), innings_map)
        overall = [r for group in grouped for r in group['rows']]
        template = fixtures[0]
        next_date = _competition_next_date(fixtures, gap_days=max(1, rule.get('default_gap_days', 2)))

        def winners(stage_name):
            out = []
            for fixture in stages.get(stage_name, []):
                if fixture.get('status') != 'complete':
                    return None
                if fixture.get('winning_team_id'):
                    out.append(fixture['winning_team_id'])
            return out

        if competition_key == 't20_blast' and league_done and not stages.get('quarter'):
            by_group = {g['group']: g['rows'] for g in grouped}
            north = by_group.get('North', [])
            south = by_group.get('South', [])
            pairs = []
            if len(north) >= 4 and len(south) >= 4:
                pairs = [
                    (north[0]['team_id'], south[3]['team_id']),
                    (south[0]['team_id'], north[3]['team_id']),
                    (north[1]['team_id'], south[2]['team_id']),
                    (south[1]['team_id'], north[2]['team_id']),
                ]
            for idx, (a, b) in enumerate(pairs):
                _competition_add_world_fixture(db, world_id, template, a, b, 'quarter', f'Quarter-Final {idx + 1}', idx, next_date)
                advanced += 1
            continue

        if competition_key == 'royal_london_cup' and league_done and not stages.get('quarter') and not stages.get('semi'):
            by_group = {g['group']: g['rows'] for g in grouped}
            ga = by_group.get('Group A', [])
            gb = by_group.get('Group B', [])
            if len(ga) >= 3 and len(gb) >= 3:
                _competition_add_world_fixture(db, world_id, template, ga[1]['team_id'], gb[2]['team_id'], 'quarter', 'Quarter-Final 1', 0, next_date)
                _competition_add_world_fixture(db, world_id, template, gb[1]['team_id'], ga[2]['team_id'], 'quarter', 'Quarter-Final 2', 1, next_date)
                advanced += 2
            continue

        if competition_key in ('icc_champions_trophy',) and league_done and not stages.get('semi'):
            by_group = {g['group']: g['rows'] for g in grouped}
            ga = by_group.get('Group A', [])
            gb = by_group.get('Group B', [])
            if len(ga) >= 2 and len(gb) >= 2:
                _competition_add_world_fixture(db, world_id, template, ga[0]['team_id'], gb[1]['team_id'], 'semi', 'Semi-Final 1', 0, next_date)
                _competition_add_world_fixture(db, world_id, template, gb[0]['team_id'], ga[1]['team_id'], 'semi', 'Semi-Final 2', 1, next_date)
                advanced += 2
            continue

        if competition_key in ('icc_cricket_world_cup',) and league_done and not stages.get('semi') and len(overall) >= 4:
            _competition_add_world_fixture(db, world_id, template, overall[0]['team_id'], overall[3]['team_id'], 'semi', 'Semi-Final 1', 0, next_date)
            _competition_add_world_fixture(db, world_id, template, overall[1]['team_id'], overall[2]['team_id'], 'semi', 'Semi-Final 2', 1, next_date)
            advanced += 2
            continue

        if competition_key in ('sheffield_shield', 'marsh_cup') and league_done and not stages.get('final') and len(overall) >= 2:
            _competition_add_world_fixture(db, world_id, template, overall[0]['team_id'], overall[1]['team_id'], 'final', 'Final', 0, next_date)
            advanced += 1
            continue

        if competition_key in ('ipl', 'psl') and league_done and not stages.get('qualifier') and not stages.get('eliminator') and len(overall) >= 4:
            _competition_add_world_fixture(db, world_id, template, overall[0]['team_id'], overall[1]['team_id'], 'qualifier', 'Qualifier 1', 0, next_date)
            _competition_add_world_fixture(db, world_id, template, overall[2]['team_id'], overall[3]['team_id'], 'eliminator', 'Eliminator', 1, next_date)
            advanced += 2
            continue

        if competition_key == 'bbl' and league_done and not stages.get('qualifier') and not stages.get('knockout') and len(overall) >= 4:
            _competition_add_world_fixture(db, world_id, template, overall[0]['team_id'], overall[1]['team_id'], 'qualifier', 'Qualifier', 0, next_date)
            _competition_add_world_fixture(db, world_id, template, overall[2]['team_id'], overall[3]['team_id'], 'knockout', 'Knockout', 1, next_date)
            advanced += 2
            continue

        if competition_key == 'cpl' and league_done and not stages.get('qualifier') and not stages.get('eliminator') and len(overall) >= 4:
            _competition_add_world_fixture(db, world_id, template, overall[0]['team_id'], overall[1]['team_id'], 'qualifier', 'Qualifier 1', 0, next_date)
            _competition_add_world_fixture(db, world_id, template, overall[2]['team_id'], overall[3]['team_id'], 'eliminator', 'Eliminator', 1, next_date)
            advanced += 2
            continue

        if competition_key == 'icc_t20_world_cup' and league_done and not stages.get('super8'):
            by_group = {g['group']: g['rows'] for g in grouped}
            groups = {name: by_group.get(name, []) for name in ('Group A', 'Group B', 'Group C', 'Group D')}
            if all(len(groups[name]) >= 2 for name in groups):
                super8_groups = {
                    'Super 8 Group 1': [
                        groups['Group A'][0]['team_id'],
                        groups['Group B'][0]['team_id'],
                        groups['Group C'][1]['team_id'],
                        groups['Group D'][1]['team_id'],
                    ],
                    'Super 8 Group 2': [
                        groups['Group A'][1]['team_id'],
                        groups['Group B'][1]['team_id'],
                        groups['Group C'][0]['team_id'],
                        groups['Group D'][0]['team_id'],
                    ],
                }
                idx = 0
                for grp, team_ids in super8_groups.items():
                    for a, b in _round_robin_pairs(team_ids):
                        _competition_add_world_fixture(
                            db, world_id, template, a, b, 'super8', 'Super 8', idx, next_date, group_name=grp
                        )
                        idx += 1
                advanced += idx
            continue

        if stages.get('quarter') and all(f.get('status') == 'complete' for f in stages.get('quarter', [])) and not stages.get('semi'):
            quarter_winners = winners('quarter') or []
            if competition_key == 'royal_london_cup':
                by_group = {g['group']: g['rows'] for g in grouped}
                ga = by_group.get('Group A', [])
                gb = by_group.get('Group B', [])
                if len(ga) >= 1 and len(gb) >= 1 and len(quarter_winners) >= 2:
                    _competition_add_world_fixture(db, world_id, template, ga[0]['team_id'], quarter_winners[1], 'semi', 'Semi-Final 1', 0, next_date)
                    _competition_add_world_fixture(db, world_id, template, gb[0]['team_id'], quarter_winners[0], 'semi', 'Semi-Final 2', 1, next_date)
                    advanced += 2
            elif len(quarter_winners) >= 4:
                _competition_add_world_fixture(db, world_id, template, quarter_winners[0], quarter_winners[1], 'semi', 'Semi-Final 1', 0, next_date)
                _competition_add_world_fixture(db, world_id, template, quarter_winners[2], quarter_winners[3], 'semi', 'Semi-Final 2', 1, next_date)
                advanced += 2
            continue

        if stages.get('semi') and all(f.get('status') == 'complete' for f in stages.get('semi', [])) and not stages.get('final'):
            semi_winners = winners('semi') or []
            if len(semi_winners) >= 2:
                _competition_add_world_fixture(db, world_id, template, semi_winners[0], semi_winners[1], 'final', 'Final', 0, next_date)
                advanced += 1
            continue

        if competition_key in ('ipl', 'psl', 'cpl') and stages.get('qualifier') and stages.get('eliminator'):
            qualifier_winners = winners('qualifier')
            eliminator_winners = winners('eliminator')
            qualifier_losers = [
                f['team2_id'] if f.get('winning_team_id') == f.get('team1_id') else f['team1_id']
                for f in stages.get('qualifier', []) if f.get('status') == 'complete' and f.get('winning_team_id')
            ]
            if qualifier_winners and eliminator_winners and qualifier_losers and not stages.get('challenger'):
                _competition_add_world_fixture(db, world_id, template, qualifier_losers[0], eliminator_winners[0], 'challenger', 'Qualifier 2', 0, next_date)
                advanced += 1
                continue
            if stages.get('challenger') and all(f.get('status') == 'complete' for f in stages.get('challenger', [])) and not stages.get('final'):
                challenger_winners = winners('challenger') or []
                if qualifier_winners and challenger_winners:
                    _competition_add_world_fixture(db, world_id, template, qualifier_winners[0], challenger_winners[0], 'final', 'Final', 0, next_date)
                    advanced += 1
                    continue

        if competition_key == 'bbl' and stages.get('qualifier') and stages.get('knockout'):
            qualifier_winners = winners('qualifier')
            knockout_winners = winners('knockout')
            qualifier_losers = [
                f['team2_id'] if f.get('winning_team_id') == f.get('team1_id') else f['team1_id']
                for f in stages.get('qualifier', []) if f.get('status') == 'complete' and f.get('winning_team_id')
            ]
            if qualifier_winners and knockout_winners and qualifier_losers and not stages.get('challenger'):
                _competition_add_world_fixture(db, world_id, template, qualifier_losers[0], knockout_winners[0], 'challenger', 'Challenger', 0, next_date)
                advanced += 1
                continue
            if stages.get('challenger') and all(f.get('status') == 'complete' for f in stages.get('challenger', [])) and not stages.get('final'):
                challenger_winners = winners('challenger') or []
                if qualifier_winners and challenger_winners:
                    _competition_add_world_fixture(db, world_id, template, qualifier_winners[0], challenger_winners[0], 'final', 'Final', 0, next_date)
                    advanced += 1
                    continue

        if competition_key == 'icc_t20_world_cup' and stages.get('super8') and all(f.get('status') == 'complete' for f in stages.get('super8', [])) and not stages.get('semi'):
            super8_flat, super8_groups = _build_competition_standings(
                {**rule, 'tie_breakers': ['points', 'nrr', 'wins', 'team_name']},
                stages.get('super8', []),
                innings_map
            )
            by_group = {g['group']: g['rows'] for g in super8_groups}
            g1 = by_group.get('Super 8 Group 1', [])
            g2 = by_group.get('Super 8 Group 2', [])
            if len(g1) >= 2 and len(g2) >= 2:
                _competition_add_world_fixture(db, world_id, template, g1[0]['team_id'], g2[1]['team_id'], 'semi', 'Semi-Final 1', 0, next_date)
                _competition_add_world_fixture(db, world_id, template, g2[0]['team_id'], g1[1]['team_id'], 'semi', 'Semi-Final 2', 1, next_date)
                advanced += 2
                continue
    if advanced:
        db.commit()
    return advanced


def _world_available_competitions(db, world_id):
    rows = db.execute(
        "SELECT competition_key, competition_name, MIN(is_icc_event) AS is_icc_event, MIN(series_name) AS label "
        "FROM fixtures WHERE world_id=? AND competition_key IS NOT NULL "
        "GROUP BY competition_key, competition_name "
        "ORDER BY MIN(COALESCE(competition_order, 999999)), competition_name",
        (world_id,)
    ).fetchall()
    items = []
    for row in rows:
        key = row['competition_key']
        rule = competition_rules.get_rule(key) or {}
        items.append({
            'key': key,
            'name': row['competition_name'] or rule.get('name') or key,
            'format': rule.get('format'),
            'is_icc_event': bool(row['is_icc_event']),
        })
    has_test_fixtures = db.execute(
        "SELECT 1 FROM fixtures WHERE world_id=? AND format='Test' AND competition_key IS NULL LIMIT 1",
        (world_id,)
    ).fetchone()
    if has_test_fixtures and not any(item['key'] == 'icc_world_test_championship' for item in items):
        items.append({
            'key': 'icc_world_test_championship',
            'name': 'ICC World Test Championship',
            'format': 'Test',
            'is_icc_event': True,
        })
    return items

# ── Worlds — routes ───────────────────────────────────────────────────────────

@app.route('/api/worlds', methods=['POST'])
def create_world():
    import json
    body              = request.get_json() or {}
    name              = (body.get('name') or '').strip()
    team_ids          = body.get('team_ids', [])
    my_team_id          = body.get('my_team_id')
    my_domestic_team_id = body.get('my_domestic_team_id')
    start_date        = body.get('start_date', '2025-01-01')
    density           = body.get('calendar_density', 'moderate')
    cal_style         = body.get('calendar_style', 'random')  # 'realistic' | 'random'
    cal_years         = int(body.get('calendar_years', 2))
    cal_years         = max(1, min(10, cal_years))
    player_lifecycle  = body.get('player_lifecycle', 'ageless')
    domestic_leagues  = body.get('domestic_leagues', [])   # e.g. ['ipl', 'bbl', 'county_championship']
    domestic_team_mode = body.get('domestic_team_mode', 'selected')
    world_scope       = body.get('world_scope', 'international')
    if world_scope not in ('international', 'domestic', 'combined'):
        world_scope = 'international'
    if player_lifecycle not in ('ageless', 'realistic'):
        player_lifecycle = 'ageless'
    if domestic_team_mode not in ('selected', 'full_league'):
        domestic_team_mode = 'selected'

    if not name:
        return err('name required')
    if len(team_ids) < 2:
        return err('at least 2 teams required')
    if world_scope == 'domestic' and cal_style == 'realistic' and not domestic_leagues:
        return err('domestic realistic worlds require at least one domestic league')

    db = database.get_db()
    try:
        settings = {'team_ids': team_ids, 'my_team_id': my_team_id,
                    'my_domestic_team_id': my_domestic_team_id,
                    'calendar_style': cal_style,
                    'calendar_years': cal_years,
                    'player_lifecycle': player_lifecycle,
                    'domestic_leagues': domestic_leagues,
                    'domestic_team_mode': domestic_team_mode,
                    'world_scope': world_scope}
        world_id = database.create_world(db, {
            'name':             name,
            'created_date':     start_date,
            'current_date':     start_date,
            'calendar_density': density,
            'settings_json':    json.dumps(settings),
        })

        # Store calendar_style on the world row (via migration column)
        try:
            db.execute("UPDATE worlds SET calendar_style = ? WHERE id = ?",
                       (cal_style, world_id))
            db.commit()
        except Exception:
            pass  # column may not exist on older DBs

        # Build team name + venue lookups
        team_name_map  = {}   # team_id  -> name
        venue_name_map = {}   # team_name -> [venue_id]
        team_venues    = {}   # team_id  -> primary venue_id  (for random fallback)
        for tid in team_ids:
            t = database.get_team(db, tid)
            if t:
                tname = t.get('name', f'Team{tid}')
                team_name_map[tid] = tname
                vid = t.get('home_venue_id')
                if vid:
                    team_venues[tid] = vid
                    venue_name_map[tname] = [vid]

        venues         = database.get_venues(db)
        fallback_venue = venues[0]['id'] if venues else None

        # ── Build domestic team lookup (for leagues opted in) ─────────────────
        selected_team_ids = set(team_ids)
        domestic_team_list = []
        if domestic_leagues and cal_style == 'realistic':
            all_leagues_needed = set()
            for comp_key in domestic_leagues:
                comp = cricket_calendar.DOMESTIC_COMPETITIONS.get(comp_key)
                if comp:
                    all_leagues_needed.add(comp['league'])
            if all_leagues_needed:
                dom_rows = db.execute(
                    "SELECT t.id as team_id, t.name, t.league, t.home_venue_id "
                    "FROM teams t WHERE t.league IN ({})".format(
                        ','.join('?' * len(all_leagues_needed))
                    ),
                    list(all_leagues_needed)
                ).fetchall()
                domestic_team_list = [dict(r) for r in dom_rows]
                if world_scope == 'domestic' and domestic_team_mode != 'full_league':
                    domestic_team_list = [
                        dt for dt in domestic_team_list
                        if dt.get('team_id') in selected_team_ids
                    ]
                # Also add their home venues to the fallback map
                for dt in domestic_team_list:
                    if dt.get('home_venue_id'):
                        team_venues.setdefault(dt['team_id'], dt['home_venue_id'])

        # ── Generate fixture calendar ─────────────────────────────────────────
        effective_team_ids = list(team_ids)
        if world_scope == 'domestic' and cal_style == 'realistic' and domestic_team_mode == 'full_league':
            effective_team_ids = sorted({dt['team_id'] for dt in domestic_team_list if dt.get('team_id')})
            settings['team_ids'] = effective_team_ids
            db.execute("UPDATE worlds SET settings_json = ? WHERE id = ?", (json.dumps(settings), world_id))
            db.commit()

        calendar_team_ids = effective_team_ids if world_scope != 'domestic' else []

        if cal_style == 'realistic':
            raw_fixtures = cricket_calendar.generate_realistic_calendar(
                team_ids         = calendar_team_ids,
                team_names       = team_name_map,
                venue_ids        = venue_name_map,
                start_date_str   = start_date,
                density          = density,
                years            = cal_years,
                domestic_leagues = domestic_leagues or None,
                domestic_teams   = domestic_team_list or None,
            )
        else:
            raw_fixtures = game_engine.generate_fixture_calendar(
                team_ids, start_date, density, months=cal_years * 12)

        # ── Convert to DB-ready rows ──────────────────────────────────────────
        fixtures_to_insert = []
        series_dates       = {}   # series_key -> {min_date, max_date, t1, t2, fmt}

        for fx in raw_fixtures:
            t1       = fx['team1_id']
            t2       = fx['team2_id']
            venue_id = (fx.get('venue_id')
                        or team_venues.get(t1)
                        or team_venues.get(t2)
                        or fallback_venue)
            _utids   = _user_team_ids(settings)
            is_user  = 1 if _utids and (t1 in _utids or t2 in _utids) else 0
            sdate    = fx.get('scheduled_date', start_date)

            # Track series date ranges for world_series creation
            sk = fx.get('series_key')
            if sk:
                if sk not in series_dates:
                    series_dates[sk] = {
                        'min': sdate, 'max': sdate,
                        't1': t1, 't2': t2,
                        'fmt': fx.get('format'),
                        'name': fx.get('series_name', ''),
                        'is_icc': bool(fx.get('is_icc_event')),
                        'icc_name': fx.get('icc_event_name'),
                        'tmpl': fx.get('tour_template'),
                        'count': 0,
                    }
                entry = series_dates[sk]
                if sdate < entry['min']:
                    entry['min'] = sdate
                if sdate > entry['max']:
                    entry['max'] = sdate
                entry['count'] += 1

            year = int(sdate[:4]) if sdate else None
            fixtures_to_insert.append({
                'world_id':                world_id,
                'tournament_id':           None,
                'series_id':               None,
                'scheduled_date':          sdate,
                'venue_id':                venue_id,
                'team1_id':                t1,
                'team2_id':                t2,
                'fixture_type':            fx.get('fixture_type', 'world'),
                'format':                  fx.get('format'),
                'is_user_match':           is_user,
                'series_name':             fx.get('series_name'),
                'match_number_in_series':  fx.get('match_number_in_series', 1),
                'series_length':           fx.get('series_length', 1),
                'is_icc_event':            fx.get('is_icc_event', False),
                'icc_event_name':          fx.get('icc_event_name'),
                'is_home_for_team1':       fx.get('is_home_for_team1', True),
                'tour_template':           fx.get('tour_template'),
                'season_year':             year,
                'competition_key':         fx.get('competition_key'),
                'competition_name':        fx.get('competition_name'),
                'competition_stage':       fx.get('competition_stage'),
                'competition_group':       fx.get('competition_group'),
                'competition_round':       fx.get('competition_round'),
                'competition_order':       fx.get('competition_order'),
            })

        database.bulk_create_fixtures(db, fixtures_to_insert)

        # ── Persist draw outcomes for seeded ICC competitions ─────────────────
        if cal_style == 'realistic' and calendar_team_ids:
            try:
                team_colours_map = {}
                for tid in calendar_team_ids:
                    t = database.get_team(db, tid)
                    if t:
                        team_colours_map[tid] = t.get('badge_colour', '#888888')
                draw_outcomes = competition_rules.compute_icc_draw_outcomes(
                    calendar_team_ids, team_name_map, start_date, end_date, team_colours_map
                )
                for outcome in draw_outcomes:
                    database.save_draw_outcome(
                        db,
                        world_id,
                        outcome['competition_key'],
                        outcome['season_key'],
                        outcome['draw_type'],
                        json.dumps(outcome),
                    )
            except Exception:
                pass  # non-fatal

        # ── Create world_series records ───────────────────────────────────────
        for sk, sd in series_dates.items():
            try:
                database.create_world_series(db, {
                    'world_id':       world_id,
                    'series_name':    sd['name'],
                    'format':         sd['fmt'],
                    'team1_id':       sd['t1'],
                    'team2_id':       sd['t2'],
                    'host_team_id':   sd['t1'],
                    'start_date':     sd['min'],
                    'end_date':       sd['max'],
                    'total_matches':  sd['count'],
                    'is_icc_event':   sd['is_icc'],
                    'icc_event_name': sd['icc_name'],
                })
            except Exception:
                pass

        # ── Initialise rankings (international teams only) ────────────────────
        ranking_seed_ids = set(team_ids)
        if world_scope == 'domestic' and domestic_team_list:
            ranking_seed_ids.update(dt['team_id'] for dt in domestic_team_list if dt.get('team_id'))

        intl_team_ids = []
        domestic_rank_ids = []
        for tid in ranking_seed_ids:
            t = database.get_team(db, tid)
            if not t:
                continue
            if t.get('team_type', 'international') == 'international':
                intl_team_ids.append(tid)
            else:
                domestic_rank_ids.append(tid)
        for pos, tid in enumerate(sorted(intl_team_ids), 1):
            for fmt in ('Test', 'ODI', 'T20'):
                database.upsert_world_ranking(db, world_id, tid, fmt, 100, pos, 0)
        for pos, tid in enumerate(sorted(domestic_rank_ids), 1):
            for fmt in ('Test', 'ODI', 'T20'):
                database.upsert_world_ranking(db, world_id, tid, fmt, 100, pos, 0)

        world = database.get_world(db, world_id)
        return jsonify({'world_id': world_id, 'fixture_count': len(fixtures_to_insert),
                        'world': world, 'calendar_style': cal_style, 'world_scope': world_scope})
    finally:
        database.close_db(db)


@app.route('/api/domestic-leagues', methods=['GET'])
def get_domestic_leagues():
    """Return available domestic competition definitions with team counts."""
    db = database.get_db()
    try:
        result = []
        for comp_key, comp in cricket_calendar.DOMESTIC_COMPETITIONS.items():
            league_name = comp['league']
            count = db.execute(
                "SELECT COUNT(*) as c FROM teams WHERE league=?", (league_name,)
            ).fetchone()['c']
            result.append({
                'key':    comp_key,
                'name':   comp['name'],
                'league': league_name,
                'format': comp['format'],
                'team_count': count,
            })
        return jsonify({'leagues': result})
    finally:
        database.close_db(db)


@app.route('/api/worlds', methods=['GET'])
def get_worlds():
    db = database.get_db()
    try:
        worlds = database.get_worlds(db)
        # Annotate each world with fixture/match counts
        for w in worlds:
            wid = w['id']
            w['fixture_count'] = db.execute(
                "SELECT COUNT(*) as c FROM fixtures WHERE world_id=?", (wid,)
            ).fetchone()['c']
            w['matches_played'] = db.execute(
                "SELECT COUNT(*) as c FROM matches WHERE world_id=? AND status='complete'", (wid,)
            ).fetchone()['c']
        return jsonify(worlds)
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>', methods=['DELETE'])
def delete_world_route(id):
    data = request.get_json() or {}
    if data.get('confirm') != 'DELETE':
        return err('Deleting a world requires {"confirm":"DELETE"} in request body')
    db = database.get_db()
    try:
        ok = database.delete_world(db, id)
        if not ok:
            return err('World not found', 404)
        return jsonify({'deleted': True, 'world_id': id})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>', methods=['GET'])
def get_world(id):
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        fixtures   = database.get_fixtures(db, world_id=id, status='scheduled')
        completed  = database.get_fixtures(db, world_id=id, status='complete')

        # Rankings grouped by format, sorted by position (top 5 each)
        all_rankings = database.get_world_rankings(db, id)
        rankings_by_fmt = {}
        for r in all_rankings:
            fmt = r['format']
            rankings_by_fmt.setdefault(fmt, []).append(r)
        for fmt in rankings_by_fmt:
            rankings_by_fmt[fmt].sort(key=lambda r: (r.get('position') or 999))
            rankings_by_fmt[fmt] = rankings_by_fmt[fmt][:5]

        # Recent results (last 8 matches in this world)
        recent_results = database.get_recent_world_matches(db, id, limit=8)

        # World records
        world_records = database.get_world_records(db, id)

        # Two-week window of upcoming fixtures
        from datetime import date, timedelta
        cur = date.fromisoformat(world.get('current_date') or date.today().isoformat())
        two_weeks_later = (cur + timedelta(days=14)).isoformat()
        next_two_weeks = [f for f in fixtures if f.get('scheduled_date', '') <= two_weeks_later]
        generated_through_row = db.execute(
            "SELECT MAX(scheduled_date) AS max_date FROM fixtures WHERE world_id=?",
            (id,)
        ).fetchone()
        generated_through = generated_through_row['max_date'] if generated_through_row else None

        return jsonify({
            'world':            world,
            'next_fixtures':    fixtures[:5],
            'upcoming_fixtures': next_two_weeks,
            'rankings':         rankings_by_fmt,
            'recent_results':   recent_results,
            'world_records':    world_records,
            'completed_count':  len(completed),
            'upcoming_count':   len(fixtures),
            'generated_through': generated_through,
            'available_competitions': _world_available_competitions(db, id),
        })
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/calendar', methods=['GET'])
def world_calendar(id):
    status  = request.args.get('status')
    offset  = int(request.args.get('offset', 0))
    limit   = int(request.args.get('limit', 0))   # 0 = all
    year    = request.args.get('year')             # optional YYYY filter
    month   = request.args.get('month')            # optional MM filter (requires year)
    db      = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        # Build WHERE clause
        where  = "WHERE f.world_id = ?"
        params = [id]
        if status:
            where += " AND f.status = ?"
            params.append(status)
        if year and month:
            prefix = f"{int(year):04d}-{int(month):02d}"
            where += " AND f.scheduled_date LIKE ?"
            params.append(f"{prefix}%")
        elif year:
            where += " AND f.scheduled_date LIKE ?"
            params.append(f"{int(year):04d}%")

        rows = db.execute(
            "SELECT f.id, f.scheduled_date, f.format, f.status, f.is_user_match, "
            " f.match_id, f.series_id, f.series_name, f.match_number_in_series, "
            " f.series_length, f.is_icc_event, f.icc_event_name, "
            " f.is_home_for_team1, f.tour_template, "
            " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
            " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
            " v.name as venue_name, "
            " m.result_type, m.margin_runs, m.margin_wickets, m.winning_team_id, "
            " wt.name as winning_team_name "
            "FROM fixtures f "
            "JOIN teams t1 ON f.team1_id = t1.id "
            "JOIN teams t2 ON f.team2_id = t2.id "
            "LEFT JOIN venues v ON f.venue_id = v.id "
            "LEFT JOIN matches m ON f.match_id = m.id "
            "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
            + where,
            params
        ).fetchall()

        fixtures = []
        for r in rows:
            f = dict(r)
            if f['status'] == 'complete' and f.get('result_type'):
                rt = f['result_type']
                w  = f.get('winning_team_name', '')
                if rt == 'runs':
                    f['result_string'] = f"{w} won by {f['margin_runs']} runs"
                elif rt == 'wickets':
                    f['result_string'] = f"{w} won by {f['margin_wickets']} wkts"
                elif rt == 'draw':
                    f['result_string'] = 'Match drawn'
                elif rt == 'tie':
                    f['result_string'] = 'Match tied'
                else:
                    f['result_string'] = rt or ''
            else:
                f['result_string'] = ''
            fixtures.append(f)

        fixtures.sort(key=lambda x: (x.get('scheduled_date') or ''))
        total = len(fixtures)

        if limit > 0:
            page = fixtures[offset: offset + limit]
        else:
            page = fixtures[offset:]

        # Group by month
        by_month = {}
        for f in page:
            d = f.get('scheduled_date', '')
            month_key = d[:7] if d else 'Unknown'
            by_month.setdefault(month_key, []).append(f)

        return jsonify({'fixtures': page, 'by_month': by_month,
                        'total': total, 'offset': offset})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/calendar/upcoming', methods=['GET'])
def world_calendar_upcoming(id):
    """Return fixtures in the next N days from the world's current date."""
    days = int(request.args.get('days', 30))
    db   = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)
        from datetime import date, timedelta
        today     = world.get('current_date') or date.today().isoformat()
        until     = (date.fromisoformat(today) + timedelta(days=days)).isoformat()
        rows = db.execute(
            "SELECT f.id, f.team1_id, f.team2_id, f.scheduled_date, f.format, f.status, "
            " f.is_user_match, f.series_name, f.match_number_in_series, f.series_length, "
            " f.is_icc_event, f.icc_event_name, "
            " t1.name as team1_name, t1.short_code as team1_code, "
            " t2.name as team2_name, t2.short_code as team2_code, "
            " v.name as venue_name "
            "FROM fixtures f "
            "JOIN teams t1 ON f.team1_id = t1.id "
            "JOIN teams t2 ON f.team2_id = t2.id "
            "LEFT JOIN venues v ON f.venue_id = v.id "
            "WHERE f.world_id = ? AND f.scheduled_date >= ? AND f.scheduled_date < ? "
            "  AND f.status = 'scheduled' "
            "ORDER BY f.scheduled_date "
            "LIMIT 200",
            (id, today, until)
        ).fetchall()
        return jsonify({'fixtures': [dict(r) for r in rows],
                        'from_date': today, 'until_date': until})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/calendar/series', methods=['GET'])
def world_calendar_series(id):
    """Return all active and upcoming world_series records."""
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)
        series = database.get_world_series(db, id)
        # Annotate with matches played vs remaining
        for s in series:
            sid = s.get('id')
            completed = db.execute(
                "SELECT COUNT(*) FROM fixtures "
                "WHERE world_id=? AND series_name=? AND status='complete'",
                (id, s.get('series_name', ''))
            ).fetchone()[0]
            s['matches_played']    = completed
            s['matches_remaining'] = max(0, (s.get('total_matches') or 0) - completed)
        return jsonify({'series': series})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/competitions/<comp_key>', methods=['GET'])
def world_competition_detail(id, comp_key):
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        rule = competition_rules.get_rule(comp_key)
        if not rule:
            return err('Competition not found', 404)

        if comp_key == 'icc_world_test_championship':
            rows = db.execute(
                "SELECT f.id, f.world_id, f.scheduled_date, f.status, f.fixture_type, f.format, "
                " f.is_user_match, f.match_id, f.series_name, f.match_number_in_series, f.series_length, "
                " f.team1_id, f.team2_id, t1.name as team1_name, t1.badge_colour as team1_colour, "
                " t2.name as team2_name, t2.badge_colour as team2_colour, v.name as venue_name, "
                " m.result_type, m.margin_runs, m.margin_wickets, m.winning_team_id, wt.name as winning_team_name "
                "FROM fixtures f "
                "JOIN teams t1 ON f.team1_id = t1.id "
                "JOIN teams t2 ON f.team2_id = t2.id "
                "LEFT JOIN venues v ON f.venue_id = v.id "
                "LEFT JOIN matches m ON f.match_id = m.id "
                "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
                "WHERE f.world_id = ? AND f.format = 'Test' AND f.is_icc_event = 0 "
                "AND f.competition_key IS NULL "
                "ORDER BY f.scheduled_date, f.id",
                (id,)
            ).fetchall()
            fixtures = [dict(r) for r in rows]
            for fixture in fixtures:
                fixture['result_string'] = _fixture_result_string(fixture)
                fixture['season_key'] = fixture.get('scheduled_date', '')[:4]
                fixture['competition_group'] = 'Championship'
            cycle_map = {}
            for fixture in fixtures:
                try:
                    year = int((fixture.get('scheduled_date') or '0')[:4])
                except Exception:
                    continue
                cycle_start = year if year % 2 == 0 else year - 1
                season_key = f"{cycle_start}-{cycle_start + 1}"
                fixture['season_key'] = season_key
                bucket = cycle_map.setdefault(season_key, {
                    'key': season_key,
                    'label': f"WTC {season_key}",
                    'from_date': fixture.get('scheduled_date'),
                    'to_date': fixture.get('scheduled_date'),
                    'fixture_count': 0,
                    'completed_count': 0,
                })
                fx_date = fixture.get('scheduled_date')
                if fx_date and (not bucket['from_date'] or fx_date < bucket['from_date']):
                    bucket['from_date'] = fx_date
                if fx_date and (not bucket['to_date'] or fx_date > bucket['to_date']):
                    bucket['to_date'] = fx_date
                bucket['fixture_count'] += 1
                if fixture.get('status') == 'complete':
                    bucket['completed_count'] += 1
            seasons = sorted(cycle_map.values(), key=lambda s: s['key'], reverse=True)
            if not seasons:
                return err('No Test championship fixtures found in this world', 404)
            requested_season = request.args.get('season')
            selected_season = requested_season if requested_season in cycle_map else seasons[0]['key']
            season_fixtures = [f for f in fixtures if f.get('season_key') == selected_season]
            innings_map = _competition_match_innings(db, [f.get('match_id') for f in season_fixtures if f.get('match_id')])
            standings_rows, grouped_rows = _build_competition_standings({
                **rule,
                'tie_breakers': ['pct', 'points', 'wins', 'team_name'],
            }, season_fixtures, innings_map)
            for row in standings_rows:
                row['played'] = row.get('played') or 0
                row['points'] = row.get('won', 0) * 12 + row.get('drawn', 0) * 4 + row.get('tied', 0) * 6
                row['pct'] = round((row['points'] / max(1, row['played'] * 12)) * 100, 2) if row.get('played') else 0.0
            standings_groups = [{
                'group': 'Championship Table',
                'rows': _sort_competition_rows(standings_rows, ['pct', 'points', 'wins', 'team_name']),
            }]
            upcoming = [f for f in season_fixtures if f.get('status') == 'scheduled']
            results = [f for f in season_fixtures if f.get('status') == 'complete']
            bracket = {'quarter_finals': [], 'semi_finals': [], 'finals': []}
        else:
            fixtures = _world_competition_rows(db, id, comp_key)
            if not fixtures:
                return err('No fixtures found for this competition in the selected world', 404)

            season_map = {}
            for fixture in fixtures:
                season_key = fixture.get('series_name') or f"{rule.get('name', comp_key)} {fixture.get('season_year') or ''}".strip()
                bucket = season_map.setdefault(season_key, {
                    'key': season_key,
                    'label': season_key,
                    'from_date': fixture.get('scheduled_date'),
                    'to_date': fixture.get('scheduled_date'),
                    'fixture_count': 0,
                    'completed_count': 0,
                })
                fx_date = fixture.get('scheduled_date')
                if fx_date and (not bucket['from_date'] or fx_date < bucket['from_date']):
                    bucket['from_date'] = fx_date
                if fx_date and (not bucket['to_date'] or fx_date > bucket['to_date']):
                    bucket['to_date'] = fx_date
                bucket['fixture_count'] += 1
                if fixture.get('status') == 'complete':
                    bucket['completed_count'] += 1
                fixture['season_key'] = season_key

            seasons = sorted(
                season_map.values(),
                key=lambda s: (s.get('from_date') or '', s.get('label') or ''),
                reverse=True
            )
            requested_season = request.args.get('season')
            selected_season = requested_season if requested_season in season_map else seasons[0]['key']
            season_fixtures = [f for f in fixtures if f.get('season_key') == selected_season]
            innings_map = _competition_match_innings(db, [f.get('match_id') for f in season_fixtures if f.get('match_id')])
            super8_fixtures = [f for f in season_fixtures if (f.get('competition_stage') or f.get('fixture_type')) == 'super8']
            league_fixtures = super8_fixtures or [
                f for f in season_fixtures if (f.get('competition_stage') or 'league') == 'league'
            ]
            standings_rows, standings_groups = _build_competition_standings(rule, league_fixtures, innings_map)
            upcoming = [f for f in season_fixtures if f.get('status') == 'scheduled']
            results = [f for f in season_fixtures if f.get('status') == 'complete']
            bracket = {
                'quarter_finals': [f for f in season_fixtures if (f.get('competition_stage') or f.get('fixture_type')) == 'quarter'],
                'semi_finals': [f for f in season_fixtures if (f.get('competition_stage') or f.get('fixture_type')) in ('semi', 'qualifier', 'eliminator', 'knockout', 'challenger')],
                'finals': [f for f in season_fixtures if (f.get('competition_stage') or f.get('fixture_type')) == 'final'],
            }

        # Check if a persisted draw outcome exists for the selected season
        has_draw = False
        try:
            import re as _re
            m = _re.search(r'(\d{4})\s*$', selected_season or '')
            if m:
                candidate_key = f"{comp_key}_{m.group(1)}"
                has_draw = database.get_draw_outcome(db, id, comp_key, candidate_key) is not None
        except Exception:
            pass

        return jsonify({
            'competition': {
                'key': comp_key,
                'name': rule.get('name', comp_key),
                'format': rule.get('format'),
                'world_name': world.get('name'),
                'draw_type': rule.get('draw_type'),
            },
            'rules': competition_rules.get_rule_explainer(comp_key),
            'seasons': seasons,
            'selected_season': selected_season,
            'standings': standings_rows,
            'standings_groups': standings_groups,
            'upcoming_fixtures': upcoming,
            'results': list(reversed(results)),
            'bracket': bracket,
            'has_draw_outcome': has_draw,
        })
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/competitions/<comp_key>/rules', methods=['GET'])
def world_competition_rules(id, comp_key):
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        rule = competition_rules.get_rule(comp_key)
        if not rule:
            return err('Competition not found', 404)

        explainer = competition_rules.get_rule_explainer(comp_key)
        if not explainer:
            return err('Competition rules not found', 404)

        available = _world_available_competitions(db, id)
        in_world = any(item.get('key') == comp_key for item in available)
        if not in_world and comp_key != 'icc_world_test_championship':
            return err('Competition not found in this world', 404)

        return jsonify({
            'competition': {
                'key': comp_key,
                'name': rule.get('name', comp_key),
                'format': rule.get('format'),
                'world_name': world.get('name'),
            },
            'rules': explainer,
        })
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/regenerate-calendar', methods=['POST'])
def world_regenerate_calendar(id):
    """
    Regenerate the calendar from a given date forward.
    Completed fixtures are untouched. Body: {from_date, style, density, years}.
    """
    import json
    body      = request.get_json() or {}
    from_date = body.get('from_date')
    style     = body.get('style', 'random')
    density   = body.get('density', 'moderate')
    years     = int(body.get('years', 2))
    years     = max(1, min(10, years))

    if not from_date:
        return err('from_date required')

    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        # Delete all scheduled (not completed/skipped) fixtures from from_date onward
        db.execute(
            "DELETE FROM fixtures WHERE world_id=? AND scheduled_date >= ? "
            "AND status NOT IN ('complete', 'skipped')",
            (id, from_date)
        )
        db.commit()

        # Also remove world_series records that started on/after from_date
        db.execute(
            "DELETE FROM world_series WHERE world_id=? AND start_date >= ?",
            (id, from_date)
        )
        db.commit()

        # Get teams from settings
        settings_json = world.get('settings_json') or '{}'
        settings      = json.loads(settings_json)
        team_ids            = settings.get('team_ids', [])
        my_team_id          = settings.get('my_team_id')
        domestic_leagues    = settings.get('domestic_leagues', [])
        domestic_team_mode  = settings.get('domestic_team_mode', 'selected')
        world_scope         = settings.get('world_scope', 'international')
        if world_scope not in ('international', 'domestic', 'combined'):
            world_scope = 'international'
        if domestic_team_mode not in ('selected', 'full_league'):
            domestic_team_mode = 'selected'
        settings['calendar_years'] = years

        if not team_ids:
            return err('No teams found in world settings')

        team_name_map  = {}
        venue_name_map = {}
        team_venues    = {}
        for tid in team_ids:
            t = database.get_team(db, tid)
            if t:
                tname = t.get('name', f'Team{tid}')
                team_name_map[tid]   = tname
                vid = t.get('home_venue_id')
                if vid:
                    team_venues[tid]       = vid
                    venue_name_map[tname]  = [vid]

        venues         = database.get_venues(db)
        fallback_venue = venues[0]['id'] if venues else None

        selected_team_ids = set(team_ids)
        domestic_team_list = []
        if domestic_leagues and style == 'realistic':
            all_leagues_needed = set()
            for comp_key in domestic_leagues:
                comp = cricket_calendar.DOMESTIC_COMPETITIONS.get(comp_key)
                if comp:
                    all_leagues_needed.add(comp['league'])
            if all_leagues_needed:
                dom_rows = db.execute(
                    "SELECT t.id as team_id, t.name, t.league, t.home_venue_id "
                    "FROM teams t WHERE t.league IN ({})".format(
                        ','.join('?' * len(all_leagues_needed))
                    ),
                    list(all_leagues_needed)
                ).fetchall()
                domestic_team_list = [dict(r) for r in dom_rows]
                if world_scope == 'domestic' and domestic_team_mode != 'full_league':
                    domestic_team_list = [
                        dt for dt in domestic_team_list
                        if dt.get('team_id') in selected_team_ids
                    ]
                for dt in domestic_team_list:
                    if dt.get('home_venue_id'):
                        team_venues.setdefault(dt['team_id'], dt['home_venue_id'])

        calendar_team_ids = team_ids if world_scope != 'domestic' else []

        if style == 'realistic':
            raw_fixtures = cricket_calendar.generate_realistic_calendar(
                team_ids       = calendar_team_ids,
                team_names     = team_name_map,
                venue_ids      = venue_name_map,
                start_date_str = from_date,
                density        = density,
                years          = years,
                domestic_leagues = domestic_leagues or None,
                domestic_teams   = domestic_team_list or None,
            )
        else:
            raw_fixtures = game_engine.generate_fixture_calendar(
                team_ids, from_date, density, months=years * 12)

        series_dates = {}
        fixtures_to_insert = []
        for fx in raw_fixtures:
            t1      = fx['team1_id']
            t2      = fx['team2_id']
            vid     = (fx.get('venue_id') or team_venues.get(t1)
                       or team_venues.get(t2) or fallback_venue)
            _utids  = _user_team_ids(settings)
            is_user = 1 if _utids and (t1 in _utids or t2 in _utids) else 0
            sdate   = fx.get('scheduled_date', from_date)
            sk      = fx.get('series_key')
            if sk:
                if sk not in series_dates:
                    series_dates[sk] = {
                        'min': sdate, 'max': sdate, 't1': t1, 't2': t2,
                        'fmt': fx.get('format'), 'name': fx.get('series_name', ''),
                        'is_icc': bool(fx.get('is_icc_event')),
                        'icc_name': fx.get('icc_event_name'), 'count': 0,
                    }
                entry = series_dates[sk]
                if sdate < entry['min']: entry['min'] = sdate
                if sdate > entry['max']: entry['max'] = sdate
                entry['count'] += 1

            fixtures_to_insert.append({
                'world_id': id, 'tournament_id': None, 'series_id': None,
                'scheduled_date': sdate, 'venue_id': vid,
                'team1_id': t1, 'team2_id': t2, 'fixture_type': fx.get('fixture_type', 'world'),
                'format': fx.get('format'), 'is_user_match': is_user,
                'series_name': fx.get('series_name'),
                'match_number_in_series': fx.get('match_number_in_series', 1),
                'series_length': fx.get('series_length', 1),
                'is_icc_event': fx.get('is_icc_event', False),
                'icc_event_name': fx.get('icc_event_name'),
                'is_home_for_team1': fx.get('is_home_for_team1', True),
                'tour_template': fx.get('tour_template'),
                'season_year': int(sdate[:4]) if sdate else None,
                'competition_key': fx.get('competition_key'),
                'competition_name': fx.get('competition_name'),
                'competition_stage': fx.get('competition_stage'),
                'competition_group': fx.get('competition_group'),
                'competition_round': fx.get('competition_round'),
                'competition_order': fx.get('competition_order'),
            })

        database.bulk_create_fixtures(db, fixtures_to_insert)

        for sk, sd in series_dates.items():
            try:
                database.create_world_series(db, {
                    'world_id': id, 'series_name': sd['name'],
                    'format': sd['fmt'], 'team1_id': sd['t1'], 'team2_id': sd['t2'],
                    'host_team_id': sd['t1'], 'start_date': sd['min'],
                    'end_date': sd['max'], 'total_matches': sd['count'],
                    'is_icc_event': sd['is_icc'], 'icc_event_name': sd['icc_name'],
                })
            except Exception:
                pass

        try:
            db.execute("UPDATE worlds SET calendar_style=? WHERE id=?", (style, id))
            db.execute("UPDATE worlds SET settings_json=? WHERE id=?", (json.dumps(settings), id))
            db.commit()
        except Exception:
            pass

        return jsonify({'success': True, 'new_fixture_count': len(fixtures_to_insert),
                        'from_date': from_date, 'style': style})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/skip-fixture/<int:fid>', methods=['POST'])
def skip_fixture(id, fid):
    db = database.get_db()
    try:
        database.update_fixture(db, fid, {'status': 'skipped'})
        return jsonify({'success': True})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/extend-calendar', methods=['POST'])
def world_extend_calendar(id):
    """
    Append a further block of fixtures after the current generated horizon.
    Body: {years}
    """
    import json
    from datetime import date, timedelta

    body = request.get_json() or {}
    years = int(body.get('years', 0) or 0)

    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        settings = {}
        if world.get('settings_json'):
            try:
                settings = json.loads(world['settings_json'])
            except Exception:
                settings = {}

        years = max(1, min(10, years or int(settings.get('calendar_years', 2) or 2)))
        style = world.get('calendar_style') or settings.get('calendar_style') or 'random'
        density = world.get('calendar_density') or 'moderate'
        team_ids = settings.get('team_ids', [])
        my_team_id = settings.get('my_team_id')
        domestic_leagues = settings.get('domestic_leagues', [])
        domestic_team_mode = settings.get('domestic_team_mode', 'selected')
        world_scope = settings.get('world_scope', 'international')
        if world_scope not in ('international', 'domestic', 'combined'):
            world_scope = 'international'
        if domestic_team_mode not in ('selected', 'full_league'):
            domestic_team_mode = 'selected'

        if not team_ids:
            return err('No teams found in world settings')

        max_row = db.execute(
            "SELECT MAX(scheduled_date) AS max_date FROM fixtures WHERE world_id=?",
            (id,)
        ).fetchone()
        base_date = max_row['max_date'] if max_row and max_row['max_date'] else (world.get('current_date') or date.today().isoformat())
        from_date = (date.fromisoformat(base_date) + timedelta(days=1)).isoformat()

        team_name_map = {}
        venue_name_map = {}
        team_venues = {}
        for tid in team_ids:
            t = database.get_team(db, tid)
            if t:
                tname = t.get('name', f'Team{tid}')
                team_name_map[tid] = tname
                vid = t.get('home_venue_id')
                if vid:
                    team_venues[tid] = vid
                    venue_name_map[tname] = [vid]

        venues = database.get_venues(db)
        fallback_venue = venues[0]['id'] if venues else None

        selected_team_ids = set(team_ids)
        domestic_team_list = []
        if domestic_leagues and style == 'realistic':
            all_leagues_needed = set()
            for comp_key in domestic_leagues:
                comp = cricket_calendar.DOMESTIC_COMPETITIONS.get(comp_key)
                if comp:
                    all_leagues_needed.add(comp['league'])
            if all_leagues_needed:
                dom_rows = db.execute(
                    "SELECT t.id as team_id, t.name, t.league, t.home_venue_id "
                    "FROM teams t WHERE t.league IN ({})".format(
                        ','.join('?' * len(all_leagues_needed))
                    ),
                    list(all_leagues_needed)
                ).fetchall()
                domestic_team_list = [dict(r) for r in dom_rows]
                if world_scope == 'domestic' and domestic_team_mode != 'full_league':
                    domestic_team_list = [
                        dt for dt in domestic_team_list
                        if dt.get('team_id') in selected_team_ids
                    ]
                for dt in domestic_team_list:
                    if dt.get('home_venue_id'):
                        team_venues.setdefault(dt['team_id'], dt['home_venue_id'])

        effective_team_ids = list(team_ids)
        if world_scope == 'domestic' and style == 'realistic' and domestic_team_mode == 'full_league':
            effective_team_ids = sorted({dt['team_id'] for dt in domestic_team_list if dt.get('team_id')})
            settings['team_ids'] = effective_team_ids

        calendar_team_ids = effective_team_ids if world_scope != 'domestic' else []

        if style == 'realistic':
            raw_fixtures = cricket_calendar.generate_realistic_calendar(
                team_ids=calendar_team_ids,
                team_names=team_name_map,
                venue_ids=venue_name_map,
                start_date_str=from_date,
                density=density,
                years=years,
                domestic_leagues=domestic_leagues or None,
                domestic_teams=domestic_team_list or None,
            )
        else:
            raw_fixtures = game_engine.generate_fixture_calendar(
                effective_team_ids, from_date, density, months=years * 12)

        series_dates = {}
        fixtures_to_insert = []
        for fx in raw_fixtures:
            t1 = fx['team1_id']
            t2 = fx['team2_id']
            vid = (fx.get('venue_id') or team_venues.get(t1)
                   or team_venues.get(t2) or fallback_venue)
            _utids  = _user_team_ids(settings)
            is_user = 1 if _utids and (t1 in _utids or t2 in _utids) else 0
            sdate = fx.get('scheduled_date', from_date)
            sk = fx.get('series_key')
            if sk:
                if sk not in series_dates:
                    series_dates[sk] = {
                        'min': sdate, 'max': sdate, 't1': t1, 't2': t2,
                        'fmt': fx.get('format'), 'name': fx.get('series_name', ''),
                        'is_icc': bool(fx.get('is_icc_event')),
                        'icc_name': fx.get('icc_event_name'), 'count': 0,
                    }
                entry = series_dates[sk]
                if sdate < entry['min']:
                    entry['min'] = sdate
                if sdate > entry['max']:
                    entry['max'] = sdate
                entry['count'] += 1

            fixtures_to_insert.append({
                'world_id': id, 'tournament_id': None, 'series_id': None,
                'scheduled_date': sdate, 'venue_id': vid,
                'team1_id': t1, 'team2_id': t2, 'fixture_type': fx.get('fixture_type', 'world'),
                'format': fx.get('format'), 'is_user_match': is_user,
                'series_name': fx.get('series_name'),
                'match_number_in_series': fx.get('match_number_in_series', 1),
                'series_length': fx.get('series_length', 1),
                'is_icc_event': fx.get('is_icc_event', False),
                'icc_event_name': fx.get('icc_event_name'),
                'is_home_for_team1': fx.get('is_home_for_team1', True),
                'tour_template': fx.get('tour_template'),
                'season_year': int(sdate[:4]) if sdate else None,
                'competition_key': fx.get('competition_key'),
                'competition_name': fx.get('competition_name'),
                'competition_stage': fx.get('competition_stage'),
                'competition_group': fx.get('competition_group'),
                'competition_round': fx.get('competition_round'),
                'competition_order': fx.get('competition_order'),
            })

        if fixtures_to_insert:
            database.bulk_create_fixtures(db, fixtures_to_insert)

        for sk, sd in series_dates.items():
            try:
                database.create_world_series(db, {
                    'world_id': id,
                    'series_name': sd['name'],
                    'format': sd['fmt'],
                    'team1_id': sd['t1'],
                    'team2_id': sd['t2'],
                    'host_team_id': sd['t1'],
                    'start_date': sd['min'],
                    'end_date': sd['max'],
                    'total_matches': sd['count'],
                    'is_icc_event': sd['is_icc'],
                    'icc_event_name': sd['icc_name'],
                })
            except Exception:
                pass

        settings['calendar_years'] = years
        settings['calendar_style'] = style
        db.execute("UPDATE worlds SET settings_json=? WHERE id=?", (json.dumps(settings), id))
        db.commit()

        generated_through_row = db.execute(
            "SELECT MAX(scheduled_date) AS max_date FROM fixtures WHERE world_id=?",
            (id,)
        ).fetchone()
        return jsonify({
            'success': True,
            'new_fixture_count': len(fixtures_to_insert),
            'from_date': from_date,
            'generated_through': generated_through_row['max_date'] if generated_through_row else None,
        })
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/fixtures/<int:fid>/toggle-play', methods=['POST'])
def toggle_play_fixture(id, fid):
    db = database.get_db()
    try:
        row = db.execute("SELECT is_user_match FROM fixtures WHERE id=?", (fid,)).fetchone()
        if not row:
            return err('Fixture not found', 404)
        new_val = 0 if row['is_user_match'] else 1
        database.update_fixture(db, fid, {'is_user_match': new_val})
        return jsonify({'is_user_match': new_val})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/draws', methods=['GET'])
def world_draws_list(id):
    """Return all persisted draw outcomes for a world."""
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)
        outcomes = database.get_world_draw_outcomes(db, id)
        # Return light summary (without full steps for list view)
        summaries = []
        for o in outcomes:
            try:
                data = json.loads(o['outcome_json'])
            except Exception:
                data = {}
            summaries.append({
                'competition_key':  o['competition_key'],
                'competition_name': data.get('competition_name', o['competition_key']),
                'season_key':       o['season_key'],
                'draw_type':        o['draw_type'],
                'year':             data.get('year'),
                'group_names':      data.get('group_names', []),
            })
        return jsonify({'draws': summaries})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/draws/<comp_key>/<season_key>', methods=['GET'])
def world_draw_detail(id, comp_key, season_key):
    """Return the full draw outcome for a specific competition season."""
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)
        outcome = database.get_draw_outcome(db, id, comp_key, season_key)
        if not outcome:
            return err('Draw outcome not found', 404)
        try:
            data = json.loads(outcome['outcome_json'])
        except Exception:
            return err('Invalid draw outcome data', 500)
        return jsonify({'draw': data})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/rankings', methods=['GET'])
def world_rankings(id):
    fmt = request.args.get('format')
    db  = database.get_db()
    try:
        rows = database.get_world_rankings(db, id, format_filter=fmt)
        # Group by format, sorted by position
        by_format = {}
        for r in rows:
            by_format.setdefault(r['format'], []).append(r)
        for f in by_format:
            by_format[f].sort(key=lambda r: (r.get('position') or 999))

        # Attach last-10 history per team per format
        for fmt_key, team_rows in by_format.items():
            for r in team_rows:
                hist = database.get_ranking_history(
                    db, id, team_id=r['team_id'], format_=fmt_key, limit=10)
                r['history'] = hist

        return jsonify({'rankings': by_format})
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/records', methods=['GET'])
def world_records(id):
    db = database.get_db()
    try:
        records = database.get_world_records(db, id)
        return jsonify({'records': records})
    finally:
        database.close_db(db)


# ── Broadcast World ───────────────────────────────────────────────────────────

@app.route('/api/worlds/<int:id>/broadcast/queue', methods=['GET'])
def world_broadcast_queue(id):
    """Ordered list of upcoming scheduled fixtures for broadcast playthrough."""
    scope = request.args.get('scope', 'next5')
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        from datetime import date as _date
        today = world.get('current_date') or _date.today().isoformat()

        limit = 10
        extra_where = ''
        extra_params: list = []

        if scope.startswith('next'):
            try:
                limit = int(scope[4:]) if scope[4:] else 5
            except ValueError:
                limit = 5
        elif scope.startswith('series:'):
            extra_where = ' AND f.series_name = ?'
            extra_params = [scope[7:]]
            limit = 200
        elif scope.startswith('to_date:'):
            extra_where = ' AND f.scheduled_date <= ?'
            extra_params = [scope[8:]]
            limit = 200
        elif scope.startswith('year:'):
            year = scope[5:]
            # Full calendar year — override the today lower-bound so Jan fixtures aren't skipped
            today = f'{year}-01-01'
            extra_where = ' AND f.scheduled_date <= ?'
            extra_params = [f'{year}-12-31']
            limit = 1000

        rows = db.execute(
            "SELECT f.id, f.team1_id, f.team2_id, f.scheduled_date, f.format, f.status, "
            " f.is_user_match, f.series_name, f.match_number_in_series, f.series_length, "
            " f.venue_id, f.match_id, "
            " t1.name as team1_name, t1.short_code as team1_code, "
            " t2.name as team2_name, t2.short_code as team2_code, "
            " v.name as venue_name, v.city as venue_city "
            "FROM fixtures f "
            "JOIN teams t1 ON f.team1_id = t1.id "
            "JOIN teams t2 ON f.team2_id = t2.id "
            "LEFT JOIN venues v ON f.venue_id = v.id "
            f"WHERE f.world_id = ? AND f.scheduled_date >= ? AND f.status = 'scheduled'{extra_where} "
            "ORDER BY f.scheduled_date, f.id "
            f"LIMIT {limit}",
            [id, today] + extra_params,
        ).fetchall()

        return jsonify({
            'fixtures': [dict(r) for r in rows],
            'world_id': id,
            'from_date': today,
            'scope': scope,
        })
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/fixtures/<int:fid>/start-live', methods=['POST'])
def fixture_start_live(id, fid):
    """Create a live match for a world fixture (auto-toss included)."""
    import random as _random
    from datetime import date as _date
    db = database.get_db()
    try:
        world = database.get_world(db, id)
        if not world:
            return err('World not found', 404)

        row = db.execute(
            "SELECT f.id, f.team1_id, f.team2_id, f.scheduled_date, f.format, "
            " f.venue_id, f.match_id, f.series_id, f.series_name "
            "FROM fixtures f WHERE f.id = ? AND f.world_id = ?",
            (fid, id),
        ).fetchone()
        if not row:
            return err('Fixture not found', 404)
        fixture = dict(row)

        # Return existing in-progress match rather than create a duplicate
        if fixture.get('match_id'):
            existing = database.get_match(db, fixture['match_id'])
            if existing and existing.get('status') == 'in_progress':
                state = database.get_match_state(db, fixture['match_id'])
                return jsonify({'match_id': fixture['match_id'], 'match': state, 'reused': True})

        # Venue fallback
        venue_id = fixture.get('venue_id')
        if not venue_id:
            fb = db.execute("SELECT id FROM venues ORDER BY RANDOM() LIMIT 1").fetchone()
            venue_id = fb['id'] if fb else None

        fmt = fixture.get('format', 'T20')
        if fmt not in ('Test', 'ODI', 'T20', 'Hundred'):
            fmt = 'T20'

        world_state = _build_world_state(db, id)
        if world_state:
            _apply_world_player_lifecycle(
                db, id, world_state, [dict(fixture)], target='date',
                target_date=fixture.get('scheduled_date')
            )

        match_id = database.create_match(db, {
            'world_id':     id,
            'format':       fmt,
            'venue_id':     venue_id,
            'match_date':   fixture.get('scheduled_date') or _date.today().isoformat(),
            'team1_id':     fixture['team1_id'],
            'team2_id':     fixture['team2_id'],
            'player_mode':  'ai_vs_ai',
            'canon_status': 'canon',
            'series_id':    fixture.get('series_id'),
        })
        database.update_fixture(db, fid, {'match_id': match_id})

        # Auto-toss
        toss_winner_id = _random.choice([fixture['team1_id'], fixture['team2_id']])
        toss_choice    = _random.choice(['bat', 'field'])
        other_id = fixture['team2_id'] if toss_winner_id == fixture['team1_id'] else fixture['team1_id']
        batting_team_id = toss_winner_id if toss_choice == 'bat' else other_id
        bowling_team_id = other_id       if toss_choice == 'bat' else toss_winner_id

        database.update_match(db, match_id, {
            'toss_winner_id': toss_winner_id,
            'toss_choice':    toss_choice,
        })
        _start_innings(db, match_id, 1, batting_team_id, bowling_team_id)

        state = database.get_match_state(db, match_id)
        return jsonify({'match_id': match_id, 'match': state,
                        'fixture': fixture, 'reused': False}), 201
    finally:
        database.close_db(db)


def _broadcast_auto_pom(db, match_id):
    """Pick POM from live scorecard: highest scorer, or most wickets as tie-break."""
    all_innings = database.get_innings(db, match_id)
    best_pid, best_runs, best_wkts = None, 0, 0
    for inn in all_innings:
        for b in database.get_batter_innings(db, inn['id']):
            if (b.get('runs') or 0) > best_runs:
                best_runs = b['runs']
                best_pid  = b['player_id']
        for bw in database.get_bowler_innings(db, inn['id']):
            if (bw.get('wickets') or 0) > best_wkts:
                best_wkts = bw['wickets']
                if best_pid is None:
                    best_pid = bw['player_id']
    return best_pid


@app.route('/api/matches/<int:id>/broadcast-complete', methods=['POST'])
def broadcast_complete_match(id):
    """Auto-complete a broadcast match: pick POM and update world calendar + rankings."""
    db = database.get_db()
    try:
        match = database.get_match(db, id)
        if not match:
            return err('Match not found', 404)

        if match['status'] != 'complete':
            all_innings = database.get_innings(db, id)
            _calculate_and_complete_match(db, id, match, all_innings)
            post = database.get_match(db, id)
            if not post.get('result_type'):
                return err('Result could not be determined', 400)

        pom_id = _broadcast_auto_pom(db, id)
        database.update_match(db, id, {
            'status': 'complete',
            **(({'player_of_match_id': pom_id}) if pom_id else {}),
        })

        updated = database.get_match(db, id)
        all_innings = database.get_innings(db, id)
        result_string = _build_result_description(updated, all_innings)

        world_id = updated.get('world_id')
        rankings = []
        if world_id:
            _check_world_records(db, world_id, id, updated)

            # Mark fixture complete
            fx_row = db.execute(
                "SELECT id FROM fixtures WHERE match_id=? AND world_id=?", (id, world_id)
            ).fetchone()
            if fx_row:
                database.update_fixture(db, fx_row['id'], {'status': 'complete'})

            # Update world rankings for this format
            fmt = updated.get('format', 'T20')
            rank_rows = db.execute(
                "SELECT team_id, points, matches_counted FROM world_rankings "
                "WHERE world_id=? AND format=?", (world_id, fmt)
            ).fetchall()
            cur_pts  = {r['team_id']: r['points']          for r in rank_rows}
            cur_mc   = {r['team_id']: r['matches_counted']  for r in rank_rows}

            t1, t2 = updated.get('team1_id'), updated.get('team2_id')
            w_id   = updated.get('winning_team_id')
            l_id   = (t2 if w_id == t1 else t1) if w_id else None
            new_pts = game_engine.update_rankings(cur_pts, {
                'winning_team_id': w_id,
                'losing_team_id':  l_id,
                'team1_id':        t1,
                'team2_id':        t2,
                'is_draw':         updated.get('result_type') == 'draw',
            })
            sorted_teams = sorted(new_pts.items(), key=lambda x: -x[1])
            for pos, (tid, pts) in enumerate(sorted_teams, 1):
                mc = cur_mc.get(tid, 0) + (1 if tid in (t1, t2) else 0)
                database.upsert_world_ranking(db, world_id, tid, fmt, pts, pos, mc)

            # Advance world current_date
            md = updated.get('match_date') or ''
            world = database.get_world(db, world_id)
            if md and md >= (world.get('current_date') or ''):
                database.update_world(db, world_id, {'current_date': md})
            _advance_world_competitions(db, world_id)

            # Rankings for response
            rank_rows2 = db.execute(
                "SELECT wr.team_id, t.name as team_name, t.short_code, wr.points, wr.position "
                "FROM world_rankings wr JOIN teams t ON wr.team_id = t.id "
                "WHERE wr.world_id=? AND wr.format=? ORDER BY wr.position LIMIT 8",
                (world_id, fmt)
            ).fetchall()
            rankings = [dict(r) for r in rank_rows2]

        db.commit()
        return jsonify({
            'success': True,
            'result': {
                'result_type':           updated.get('result_type'),
                'winning_team_name':     updated.get('winning_team_name'),
                'winning_team_id':       updated.get('winning_team_id'),
                'team1_id':              updated.get('team1_id'),
                'team2_id':              updated.get('team2_id'),
                'margin_runs':           updated.get('margin_runs'),
                'margin_wickets':        updated.get('margin_wickets'),
                'player_of_match_name':  updated.get('player_of_match_name'),
                'result_string':         result_string,
            },
            'rankings': rankings,
            'format':   updated.get('format', 'T20'),
        })
    finally:
        database.close_db(db)


@app.route('/api/worlds/<int:id>/simulate', methods=['POST'])
def simulate_world(id):
    import json as _json
    body        = request.get_json() or {}
    target      = body.get('target', 'next_match')
    target_date = body.get('target_date')

    valid_targets = {'next_match', 'end_of_series', 'date', 'next_my_match'}
    if target not in valid_targets:
        return err(f'target must be one of {sorted(valid_targets)}')
    if target == 'date' and not target_date:
        return err('target_date required for date target')

    def _sse(obj):
        return f"data: {_json.dumps(obj)}\n\n"

    def generate():
        db = database.get_db()
        try:
            yield _sse({'type': 'progress', 'step': 'loading', 'message': 'Loading world data…'})

            world = database.get_world(db, id)
            if not world:
                yield _sse({'type': 'error', 'message': 'World not found'})
                return
            settings = {}
            if world.get('settings_json'):
                try:
                    settings = _json.loads(world['settings_json'])
                except Exception:
                    settings = {}
            if target == 'next_my_match' and not _user_team_ids(settings):
                yield _sse({'type': 'error', 'message': 'No user-controlled team selected for this world'})
                return

            world_state = _build_world_state(db, id)
            if not world_state:
                yield _sse({'type': 'error', 'message': 'Could not build world state'})
                return
            if target_date:
                world_state['target_date'] = target_date

            fixtures = database.get_fixtures(db, world_id=id, status='scheduled')
            n_sched  = sum(1 for f in fixtures if f.get('status', 'scheduled') == 'scheduled')
            noun     = 'fixture' if n_sched == 1 else 'fixtures'
            yield _sse({'type': 'progress', 'step': 'fixtures',
                        'message': f'Found {n_sched:,} {noun} to simulate',
                        'fixture_count': n_sched})

            _apply_world_player_lifecycle(db, id, world_state, fixtures, target, target_date)

            yield _sse({'type': 'progress', 'step': 'simulating',
                        'message': f'Simulating {n_sched:,} {noun}…'})

            sim_result = game_engine.simulate_world_to(target, fixtures, world_state)

            results   = sim_result['results']
            n_results = len(results)

            if not results and not sim_result.get('paused_at_fixture'):
                yield _sse({'type': 'done', 'data': {
                    'matches_simulated': 0,
                    'message':           'No scheduled fixtures to simulate',
                    'paused_at_fixture': None,
                    'truncated':         False,
                    'sim_report':        None,
                }})
                return

            yield _sse({'type': 'progress', 'step': 'saving',
                        'message': f'Saving {n_results:,} result{"s" if n_results != 1 else ""}…'})

            # Snapshot rankings BEFORE persistence so we can diff them
            rankings_before_list = database.get_world_rankings(db, id)
            rankings_before = {}   # {format: {team_id: {position, points}}}
            for rb in rankings_before_list:
                rankings_before.setdefault(rb['format'], {})[rb['team_id']] = {
                    'position': rb.get('position'), 'points': rb.get('points'),
                }

            if results:
                _persist_world_sim(
                    db, id, results,
                    sim_result['new_current_date'],
                    sim_result['updated_player_states'],
                    world_state=world_state,
                )

            # Enrich each result with team names.
            # teams_map only contains teams in settings.team_ids; combined worlds also
            # contain domestic teams that weren't in that list, so fall back to DB.
            teams_map  = world_state.get('teams', {})
            name_cache = {tid: info.get('name', '?') for tid, info in teams_map.items()}
            missing_tids = set()
            for r in results:
                if r.get('team1_id') and r['team1_id'] not in name_cache:
                    missing_tids.add(r['team1_id'])
                if r.get('team2_id') and r['team2_id'] not in name_cache:
                    missing_tids.add(r['team2_id'])
            for tid in missing_tids:
                team_row = database.get_team(db, tid)
                if team_row:
                    name_cache[tid] = team_row['name']
            for r in results:
                r['team1_name'] = name_cache.get(r.get('team1_id'), '?')
                r['team2_name'] = name_cache.get(r.get('team2_id'), '?')
                # Rebuild summary now that we have real names
                w_name = r['team1_name'] if r.get('winner_id') == r.get('team1_id') else r['team2_name']
                if r.get('result_type') == 'runs' and r.get('margin_runs'):
                    r['summary'] = f"{w_name} won by {r['margin_runs']} run{'s' if r['margin_runs'] != 1 else ''}"
                elif r.get('result_type') == 'wickets' and r.get('margin_wickets'):
                    r['summary'] = f"{w_name} won by {r['margin_wickets']} wicket{'s' if r['margin_wickets'] != 1 else ''}"
                elif r.get('result_type') == 'tie':
                    r['summary'] = "Match tied"
                elif r.get('result_type') == 'draw':
                    r['summary'] = "Match drawn"

            # Build notable events string list (kept for backward compat)
            dates   = [r['scheduled_date'] for r in results if r.get('scheduled_date')]
            notable = []
            for r in results:
                if r.get('result_type') == 'runs' and (r.get('margin_runs') or 0) >= 60:
                    w_name = r['team1_name'] if r.get('winner_id') == r.get('team1_id') else r['team2_name']
                    notable.append(f"{w_name} crushed opponent by {r['margin_runs']} runs")
                ts = r.get('top_scorer')
                if ts and ts.get('runs', 0) >= 80:
                    notable.append(f"{ts['name']} scored {ts['runs']} runs")
                tb = r.get('top_bowler')
                if tb and tb.get('wickets', 0) >= 5:
                    notable.append(f"{tb['name']} took {tb['wickets']} wickets")

            # Reload updated rankings and compute position changes
            updated_rankings = database.get_world_rankings(db, id)
            by_fmt = {}
            ranking_changes = {}   # {format: [{team_name, old_pos, new_pos, pos_change}]}
            for r in updated_rankings:
                by_fmt.setdefault(r['format'], []).append(r)
                fmt    = r['format']
                before = rankings_before.get(fmt, {}).get(r['team_id'])
                if before and before.get('position') and r.get('position'):
                    delta = (before['position'] or 99) - (r['position'] or 99)
                    if delta != 0:
                        ranking_changes.setdefault(fmt, []).append({
                            'team_name':    r.get('team_name', '?'),
                            'team_id':      r.get('team_id'),
                            'old_position': before['position'],
                            'new_position': r['position'],
                            'pos_change':   delta,   # positive = moved up the table
                            'points':       round(r.get('points') or 0),
                        })
            # Sort movers: biggest moves first
            for fmt_moves in ranking_changes.values():
                fmt_moves.sort(key=lambda x: -abs(x['pos_change']))

            # Biggest result (most decisive win by runs; fallback to wickets)
            run_wins  = [r for r in results if r.get('result_type') == 'runs'    and r.get('margin_runs')]
            wkt_wins  = [r for r in results if r.get('result_type') == 'wickets' and r.get('margin_wickets')]
            biggest_by_runs    = max(run_wins,  key=lambda r: r['margin_runs'],    default=None)
            biggest_by_wickets = max(wkt_wins,  key=lambda r: r['margin_wickets'], default=None)

            # Top batting & bowling performances across all simulated matches
            def _perf_entry(match_result, kind):
                p = match_result.get(kind)
                if not p:
                    return None
                return {
                    'name':      p.get('name', '?'),
                    'player_id': p.get('player_id'),
                    'runs':      p.get('runs'),
                    'wickets':   p.get('wickets'),
                    'format':    match_result.get('format', ''),
                    'date':      match_result.get('scheduled_date', ''),
                    'match':     f"{match_result['team1_name']} v {match_result['team2_name']}",
                }

            batting_perfs = sorted(
                [e for r in results if (e := _perf_entry(r, 'top_scorer'))],
                key=lambda x: -(x['runs'] or 0)
            )[:3]
            bowling_perfs = sorted(
                [e for r in results if (e := _perf_entry(r, 'top_bowler'))],
                key=lambda x: -(x['wickets'] or 0)
            )[:3]

            # Next scheduled fixtures after the sim (for "What's Next")
            next_scheduled        = database.get_fixtures(db, world_id=id, status='scheduled')
            next_fixtures_preview = [dict(f) for f in next_scheduled[:4]]

            sim_report = {
                'matches_simulated':       sim_result['matches_simulated'],
                'date_from':               dates[0] if dates else None,
                'date_to':                 dates[-1] if dates else None,
                'results':                 results,
                'notable_events':          notable[:10],
                'updated_rankings':        by_fmt,
                'ranking_changes':         ranking_changes,
                'biggest_by_runs':         biggest_by_runs,
                'biggest_by_wickets':      biggest_by_wickets,
                'top_batting_perfs':       batting_perfs,
                'top_bowling_perfs':       bowling_perfs,
                'next_fixtures_preview':   next_fixtures_preview,
                'truncated':               sim_result['truncated'],
            }

            yield _sse({'type': 'done', 'data': {
                'matches_simulated': sim_result['matches_simulated'],
                'paused_at_fixture': sim_result['paused_at_fixture'],
                'truncated':         sim_result['truncated'],
                'sim_report':        sim_report,
            }})

        except Exception as e:
            yield _sse({'type': 'error', 'message': str(e)})
        finally:
            database.close_db(db)

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


# ── Almanack ──────────────────────────────────────────────────────────────────

@app.route('/api/almanack/batting', methods=['GET'])
def almanack_batting():
    db = database.get_db()
    try:
        rows, total, is_fallback = database.get_almanack_batting(db, request.args)
        return jsonify({'rows': rows, 'total': total,
                        'offset': int(request.args.get('offset', 0)),
                        'limit':  int(request.args.get('limit', 50)),
                        'exhibition_fallback': is_fallback})
    finally:
        database.close_db(db)


@app.route('/api/almanack/bowling', methods=['GET'])
def almanack_bowling():
    db = database.get_db()
    try:
        rows, total, is_fallback = database.get_almanack_bowling(db, request.args)
        return jsonify({'rows': rows, 'total': total,
                        'offset': int(request.args.get('offset', 0)),
                        'limit':  int(request.args.get('limit', 50)),
                        'exhibition_fallback': is_fallback})
    finally:
        database.close_db(db)


@app.route('/api/almanack/allrounders', methods=['GET'])
def almanack_allrounders():
    db = database.get_db()
    try:
        rows, total = database.get_almanack_allrounders(db, request.args)
        return jsonify({'rows': rows, 'total': total,
                        'offset': int(request.args.get('offset', 0)),
                        'limit':  int(request.args.get('limit', 50))})
    finally:
        database.close_db(db)


@app.route('/api/almanack/teams', methods=['GET'])
def almanack_teams():
    db = database.get_db()
    try:
        rows, total = database.get_almanack_teams(db, request.args)
        return jsonify({'rows': rows, 'total': total,
                        'offset': int(request.args.get('offset', 0)),
                        'limit':  int(request.args.get('limit', 50))})
    finally:
        database.close_db(db)


@app.route('/api/almanack/matches', methods=['GET'])
def almanack_matches():
    db = database.get_db()
    try:
        rows, total = database.get_almanack_matches(db, request.args)
        # Attach result_string to each row
        for r in rows:
            rt = r.get('result_type')
            wn = r.get('winning_team_name') or '?'
            if rt == 'draw':
                r['result_string'] = 'Match drawn'
            elif rt == 'tie':
                r['result_string'] = 'Match tied'
            elif rt == 'runs':
                r['result_string'] = f'{wn} won by {r.get("margin_runs",0)} run(s)'
            elif rt == 'wickets':
                r['result_string'] = f'{wn} won by {r.get("margin_wickets",0)} wicket(s)'
            else:
                r['result_string'] = ''
        return jsonify({'rows': rows, 'total': total,
                        'offset': int(request.args.get('offset', 0)),
                        'limit':  int(request.args.get('limit', 50))})
    finally:
        database.close_db(db)


@app.route('/api/almanack/partnerships', methods=['GET'])
def almanack_partnerships():
    db = database.get_db()
    try:
        rows, total = database.get_almanack_partnerships(db, request.args)
        return jsonify({'rows': rows, 'total': total,
                        'offset': int(request.args.get('offset', 0)),
                        'limit':  int(request.args.get('limit', 50))})
    finally:
        database.close_db(db)


@app.route('/api/almanack/honours', methods=['GET'])
def almanack_honours():
    db = database.get_db()
    try:
        data = database.get_almanack_honours(db)
        return jsonify(data)
    finally:
        database.close_db(db)


@app.route('/api/almanack/honours/with-world-records', methods=['GET'])
def almanack_honours_with_world_records():
    db = database.get_db()
    try:
        data = database.get_almanack_honours_with_world_records(db)
        return jsonify(data)
    finally:
        database.close_db(db)


@app.route('/api/almanack/search', methods=['GET'])
def almanack_search():
    q  = request.args.get('q', '').strip()
    db = database.get_db()
    try:
        results = database.get_almanack_search(db, q)
        return jsonify({'results': results, 'q': q})
    finally:
        database.close_db(db)


# ── Export / Import ───────────────────────────────────────────────────────────

def _match_full_dict(db, match_id):
    """Build a complete match dict including all innings/deliveries/partnerships/fow."""
    match = database.get_match(db, match_id)
    if not match:
        return None
    all_innings = database.get_innings(db, match_id)
    innings_out = []
    for inn in all_innings:
        inn_id = inn['id']
        inn_dict = dict(inn)
        inn_dict['batter_innings']  = database.get_batter_innings(db, inn_id)
        inn_dict['bowler_innings']  = database.get_bowler_innings(db, inn_id)
        inn_dict['partnerships']    = database.get_all_partnerships(db, inn_id)
        inn_dict['fall_of_wickets'] = database.get_fall_of_wickets(db, inn_id)
        innings_out.append(inn_dict)
    match['innings'] = innings_out
    match['deliveries'] = database.get_all_deliveries_for_match(db, match_id)
    match['journal'] = database.get_journal_entries(db, match_id)
    return match


@app.route('/api/export/almanack', methods=['GET'])
def export_almanack():
    import json as _json
    from datetime import date
    db = database.get_db()
    try:
        teams    = database.get_teams(db)
        venues   = database.get_venues(db)
        players  = database.dict_from_rows(db.execute("SELECT * FROM players ORDER BY id").fetchall())
        series   = database.dict_from_rows(db.execute("SELECT * FROM series ORDER BY id").fetchall())
        tournaments = database.dict_from_rows(db.execute("SELECT * FROM tournaments ORDER BY id").fetchall())
        worlds   = database.dict_from_rows(db.execute("SELECT * FROM worlds ORDER BY id").fetchall())
        wrecords = database.dict_from_rows(db.execute("SELECT * FROM world_records ORDER BY id").fetchall())
        journals = database.dict_from_rows(db.execute("SELECT * FROM match_journal ORDER BY id").fetchall())
        matches_raw = database.dict_from_rows(db.execute("SELECT id FROM matches ORDER BY id").fetchall())
        matches = [_match_full_dict(db, m['id']) for m in matches_raw]

        payload = _json.dumps({
            'exported_at': date.today().isoformat(),
            'teams': teams, 'venues': venues, 'players': players,
            'series': series, 'tournaments': tournaments,
            'worlds': worlds, 'world_records': wrecords,
            'journals': journals, 'matches': matches,
        }, default=str)
        filename = f'ribi-almanack-{date.today().isoformat()}.json'
        return Response(payload, mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename={filename}'})
    finally:
        database.close_db(db)


@app.route('/api/export/match/<int:id>', methods=['GET'])
def export_match(id):
    import json as _json
    from datetime import date
    db = database.get_db()
    try:
        match = _match_full_dict(db, id)
        if not match:
            return err('Match not found', 404)
        payload = _json.dumps(match, default=str)
        filename = f'ribi-match-{id}-{date.today().isoformat()}.json'
        return Response(payload, mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename={filename}'})
    finally:
        database.close_db(db)


@app.route('/api/export/table', methods=['GET'])
def export_table():
    import csv, io
    q = request.args.get('q', '').strip()
    if not q:
        return err('q parameter required')

    # Security: SELECT only — no semicolons, no DDL/DML
    q_upper = q.upper()
    if ';' in q:
        return err('semicolons not allowed')
    for kw in ('DROP', 'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CREATE',
                'ATTACH', 'DETACH', 'PRAGMA', 'VACUUM'):
        if kw in q_upper:
            return err(f'{kw} not allowed in export queries')
    if not q_upper.lstrip().startswith('SELECT'):
        return err('Only SELECT queries are allowed')

    db = database.get_db()
    try:
        rows = db.execute(q).fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        if rows:
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(list(row))
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=almanack_export.csv'}
        )
    except Exception as exc:
        return err(f'Query error: {exc}')
    finally:
        database.close_db(db)


@app.route('/api/export/full-backup', methods=['GET'])
def export_full_backup():
    import json as _json
    from datetime import date
    db = database.get_db()
    try:
        # Enumerate all user tables
        table_rows = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        data = {}
        for t in table_rows:
            tname = t['name']
            rows = db.execute(f"SELECT * FROM {tname}").fetchall()
            data[tname] = [dict(r) for r in rows]
        payload = _json.dumps({'exported_at': date.today().isoformat(), 'data': data}, default=str)
        filename = f'ribi-backup-{date.today().isoformat()}.json'
        return Response(payload, mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename={filename}'})
    finally:
        database.close_db(db)


@app.route('/api/import/almanack', methods=['POST'])
def import_almanack():
    import json as _json
    # Accept both JSON body and multipart file upload
    if request.content_type and 'multipart' in request.content_type:
        f = request.files.get('file')
        if not f:
            return err('No file provided')
        try:
            data = _json.loads(f.read())
        except Exception:
            return err('Invalid JSON in uploaded file')
    else:
        data = request.get_json(silent=True) or {}

    required = ['teams', 'venues', 'players', 'matches']
    missing = [k for k in required if k not in data]
    if missing:
        return err(f'Missing required keys: {missing}')

    db = database.get_db()
    try:
        counts = {}

        # Teams
        for t in data.get('teams', []):
            db.execute(
                "INSERT OR REPLACE INTO teams (id, name, short_code, badge_colour, home_venue_id) "
                "VALUES (:id, :name, :short_code, :badge_colour, :home_venue_id)",
                {k: t.get(k) for k in ('id', 'name', 'short_code', 'badge_colour', 'home_venue_id')}
            )
        counts['teams'] = len(data.get('teams', []))

        # Venues
        for v in data.get('venues', []):
            db.execute(
                "INSERT OR REPLACE INTO venues (id, name, city, country, capacity, pitch_type) "
                "VALUES (:id, :name, :city, :country, :capacity, :pitch_type)",
                {k: v.get(k) for k in ('id', 'name', 'city', 'country', 'capacity', 'pitch_type')}
            )
        counts['venues'] = len(data.get('venues', []))

        # Players
        for p in data.get('players', []):
            db.execute(
                "INSERT OR REPLACE INTO players "
                "(id, team_id, name, batting_rating, bowling_rating, bowling_type, batting_position) "
                "VALUES (:id, :team_id, :name, :batting_rating, :bowling_rating, :bowling_type, :batting_position)",
                {k: p.get(k) for k in ('id', 'team_id', 'name', 'batting_rating', 'bowling_rating',
                                        'bowling_type', 'batting_position')}
            )
        counts['players'] = len(data.get('players', []))

        # Matches (header only — no innings/deliveries to avoid complexity)
        match_count = 0
        for m in data.get('matches', []):
            db.execute(
                "INSERT OR REPLACE INTO matches "
                "(id, team1_id, team2_id, venue_id, format, status, match_date, "
                " result_type, winning_team_id, margin_runs, margin_wickets, scoring_mode, match_notes, "
                " series_id, tournament_id, world_id) "
                "VALUES (:id, :team1_id, :team2_id, :venue_id, :format, :status, :match_date, "
                " :result_type, :winning_team_id, :margin_runs, :margin_wickets, :scoring_mode, :match_notes, "
                " :series_id, :tournament_id, :world_id)",
                {
                    **{k: m.get(k) for k in ('id', 'team1_id', 'team2_id', 'venue_id', 'format', 'status',
                                             'match_date', 'result_type', 'winning_team_id', 'margin_runs',
                                             'margin_wickets', 'match_notes', 'series_id',
                                             'tournament_id', 'world_id')},
                    'scoring_mode': m.get('scoring_mode') or 'modern',
                }
            )
            match_count += 1
        counts['matches'] = match_count

        db.commit()
        return jsonify({'restored': counts})
    except Exception as exc:
        db.rollback()
        return err(f'Import failed: {exc}')
    finally:
        database.close_db(db)


@app.route('/api/import/full-backup', methods=['POST'])
def import_full_backup():
    import json as _json
    body = request.get_json(silent=True) or {}
    if not body.get('confirm'):
        return err('confirm:true required')
    data = body.get('data', {})
    if not data:
        return err('data is required')

    db = database.get_db()
    try:
        table_order = [
            'venues', 'teams', 'players', 'matches', 'innings', 'batter_innings',
            'bowler_innings', 'deliveries', 'partnerships', 'fall_of_wickets',
            'match_journal', 'series', 'tournaments', 'tournament_teams',
            'worlds', 'fixtures', 'world_rankings',
            'ranking_history', 'world_records', 'player_world_state',
        ]
        counts = {}
        # Delete in reverse order to respect FK constraints
        for tname in reversed(table_order):
            try:
                db.execute(f"DELETE FROM {tname}")
            except Exception:
                pass

        # Insert
        for tname in table_order:
            rows = data.get(tname, [])
            if not rows:
                counts[tname] = 0
                continue
            cols = list(rows[0].keys())
            placeholders = ', '.join('?' for _ in cols)
            col_list = ', '.join(cols)
            inserted = 0
            for row in rows:
                try:
                    db.execute(
                        f"INSERT OR REPLACE INTO {tname} ({col_list}) VALUES ({placeholders})",
                        [row.get(c) for c in cols]
                    )
                    inserted += 1
                except Exception:
                    pass
            counts[tname] = inserted

        db.commit()
        return jsonify({'status': 'ok', 'restored': counts})
    except Exception as exc:
        db.rollback()
        return err(f'Full restore failed: {exc}')
    finally:
        database.close_db(db)


# ── Archive ───────────────────────────────────────────────────────────────────

@app.route('/api/archive/old-matches', methods=['POST'])
def archive_old_matches():
    import json as _json
    from datetime import date, timedelta
    body = request.get_json(silent=True) or {}
    older_than_days = body.get('older_than_days', 30)
    if not isinstance(older_than_days, int) or older_than_days < 1:
        return err('older_than_days must be a positive integer')

    cutoff = (date.today() - timedelta(days=older_than_days)).isoformat()

    db = database.get_db()
    try:
        # Find complete matches older than cutoff that still have live deliveries
        matches_raw = db.execute(
            "SELECT DISTINCT m.id FROM matches m "
            "JOIN innings i ON i.match_id = m.id "
            "JOIN deliveries d ON d.innings_id = i.id "
            "WHERE m.status = 'complete' AND m.match_date < ? "
            "AND (m.deliveries_archive_json IS NULL OR m.deliveries_archive_json = '')",
            (cutoff,)
        ).fetchall()
        match_ids = [r['id'] for r in matches_raw]

        deliveries_removed = 0
        for mid in match_ids:
            # Serialize current deliveries
            rows = db.execute(
                "SELECT d.*, i.innings_number "
                "FROM deliveries d JOIN innings i ON d.innings_id = i.id "
                "WHERE i.match_id = ? ORDER BY i.innings_number, d.over_number, d.ball_number",
                (mid,)
            ).fetchall()
            archive = [dict(r) for r in rows]
            db.execute(
                "UPDATE matches SET deliveries_archive_json = ? WHERE id = ?",
                (_json.dumps(archive), mid)
            )
            # Delete from deliveries via innings
            inn_ids = db.execute(
                "SELECT id FROM innings WHERE match_id = ?", (mid,)
            ).fetchall()
            for inn in inn_ids:
                count = db.execute(
                    "SELECT COUNT(*) as c FROM deliveries WHERE innings_id = ?",
                    (inn['id'],)
                ).fetchone()['c']
                deliveries_removed += count
                db.execute("DELETE FROM deliveries WHERE innings_id = ?", (inn['id'],))

        db.commit()

        db_path = database.DB_PATH
        db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 3) if os.path.exists(db_path) else 0

        return jsonify({
            'archived_matches': len(match_ids),
            'deliveries_removed': deliveries_removed,
            'space_saved_estimate_mb': round(deliveries_removed * 150 / (1024 * 1024), 3),
            'db_size_mb': db_size_mb,
        })
    finally:
        database.close_db(db)


# ── Demo Mode ─────────────────────────────────────────────────────────────────

@app.route('/api/demo/data')
def get_demo_data():
    """Return real stats to enrich the demo if matches have been played."""
    try:
        db = database.get_db()
        row = db.execute("SELECT COUNT(*) as cnt FROM matches WHERE status='completed'").fetchone()
        match_count = row['cnt'] if row else 0

        if match_count > 0:
            total_runs = (db.execute("SELECT COALESCE(SUM(total_runs),0) as t FROM innings").fetchone() or {}).get('t', 0)
            total_wickets = (db.execute("SELECT COALESCE(SUM(total_wickets),0) as t FROM innings").fetchone() or {}).get('t', 0)
            centuries = db.execute(
                "SELECT COUNT(*) as cnt FROM batter_innings WHERE runs >= 100"
            ).fetchone()
            century_count = centuries['cnt'] if centuries else 0
            top_row = db.execute("""
                SELECT p.name, bi.runs, bi.balls_faced, t.name as team
                FROM batter_innings bi
                JOIN players p ON bi.player_id = p.id
                JOIN innings i ON bi.innings_id = i.id
                JOIN matches m ON i.match_id = m.id
                JOIN teams t ON p.team_id = t.id
                ORDER BY bi.runs DESC LIMIT 1
            """).fetchone()
            top_score = dict(top_row) if top_row else None
            database.close_db(db)
            return jsonify({
                'has_real_data': True,
                'match_count': int(match_count),
                'total_runs': int(total_runs),
                'total_wickets': int(total_wickets),
                'centuries': int(century_count),
                'top_score': top_score,
            })

        database.close_db(db)
        return jsonify({'has_real_data': False})
    except Exception as e:
        return jsonify({'has_real_data': False, 'error': str(e)})


# ── Disclaimer ────────────────────────────────────────────────────────────────

@app.route('/api/disclaimer')
def get_disclaimer():
    return jsonify({
        'short': 'An independent fan-made project. Not affiliated with any cricket board, '
                 'governing body, or commercial cricket organisation.',
        'full': (
            'Roll It & Bowl It is an independent fan-made project created for personal '
            'entertainment. It is not affiliated with, endorsed by, or connected to any '
            'cricket board, governing body, broadcaster, or commercial cricket organisation, '
            'including but not limited to the ICC, ECB, Cricket Australia, BCCI, or any '
            'other national or international cricket authority.\n\n'
            'Player names used in pre-loaded squads are included for entertainment purposes '
            'only in the spirit of the dice cricket tradition. No association with or '
            'endorsement by any named individual is implied or should be inferred.\n\n'
            '"Wisden" and "Wisden Cricketers\' Almanack" are registered trademarks of '
            'John Wisden & Co. "The Dice Cricketers\' Almanack" is an original name created '
            'for this project and is not affiliated with or derived from Wisden in any '
            'commercial sense.\n\n'
            'This application is not a commercial product. It is free, open source, and '
            'intended solely for personal use and enjoyment.'
        ),
        'version': config.APP_VERSION,
    })


# ── Entry point ───────────────────────────────────────────────────────────────

# Run DB migrations on startup
_mig_db = database.get_db()
try:
    database.run_migrations(_mig_db)
finally:
    database.close_db(_mig_db)

if __name__ == '__main__':
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
