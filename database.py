"""
database.py — All SQL queries and database logic for Roll It & Bowl It.
No Flask imports. All functions accept a db (sqlite3.Connection) parameter.
"""

import sqlite3
import config

DB_PATH = config.DB_PATH


# ── Connection helpers ────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def close_db(conn):
    if conn:
        conn.close()


# get_db() supports use as a context manager: with get_db() as db: ...
# sqlite3.Connection already supports __enter__/__exit__ (commits on exit).


# ── Row helpers ───────────────────────────────────────────────────────────────

def dict_from_row(row):
    """Convert a sqlite3.Row (or None) to a plain dict."""
    if row is None:
        return None
    return dict(row)


def dict_from_rows(rows):
    """Convert a list of sqlite3.Row objects to plain dicts."""
    return [dict(r) for r in rows]


# ── Teams ─────────────────────────────────────────────────────────────────────

def get_teams(db):
    rows = db.execute(
        "SELECT t.*, v.name as venue_name FROM teams t "
        "LEFT JOIN venues v ON t.home_venue_id = v.id "
        "ORDER BY t.name"
    ).fetchall()
    return dict_from_rows(rows)


def get_team(db, id):
    row = db.execute(
        "SELECT t.*, v.name as venue_name FROM teams t "
        "LEFT JOIN venues v ON t.home_venue_id = v.id "
        "WHERE t.id = ?", (id,)
    ).fetchone()
    return dict_from_row(row)


def create_team(db, data):
    cur = db.execute(
        "INSERT INTO teams (name, short_code, badge_colour, home_venue_id, is_real, is_custom) "
        "VALUES (:name, :short_code, :badge_colour, :home_venue_id, :is_real, :is_custom)",
        {
            'name': data.get('name'),
            'short_code': data.get('short_code'),
            'badge_colour': data.get('badge_colour'),
            'home_venue_id': data.get('home_venue_id'),
            'is_real': data.get('is_real', 0),
            'is_custom': data.get('is_custom', 0),
        }
    )
    db.commit()
    return cur.lastrowid


def update_team(db, id, data):
    allowed = ['name', 'short_code', 'badge_colour', 'home_venue_id']
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE teams SET {sets} WHERE id = :_id", data)
    db.commit()


def get_players_for_team(db, team_id, world_id=None):
    if world_id is None:
        rows = db.execute(
            "SELECT * FROM players "
            "WHERE team_id = ? AND COALESCE(source_world_id, 0) = 0 "
            "ORDER BY batting_position, id",
            (team_id,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM players "
            "WHERE team_id = ? AND (source_world_id IS NULL OR source_world_id = ?) "
            "ORDER BY batting_position, id",
            (team_id, world_id)
        ).fetchall()
    return dict_from_rows(rows)


# ── Players ───────────────────────────────────────────────────────────────────

def get_player(db, id):
    row = db.execute(
        "SELECT p.*, t.name as team_name, t.short_code as team_code, t.badge_colour "
        "FROM players p JOIN teams t ON p.team_id = t.id WHERE p.id = ?",
        (id,)
    ).fetchone()
    return dict_from_row(row)


def create_player(db, data):
    cur = db.execute(
        "INSERT INTO players (team_id, name, batting_position, batting_rating, "
        "batting_hand, bowling_type, bowling_action, bowling_rating, source_world_id, is_regen) "
        "VALUES (:team_id, :name, :batting_position, :batting_rating, "
        ":batting_hand, :bowling_type, :bowling_action, :bowling_rating, :source_world_id, :is_regen)",
        {
            'team_id': data['team_id'],
            'name': data['name'],
            'batting_position': data.get('batting_position'),
            'batting_rating': data.get('batting_rating', 3),
            'batting_hand': data.get('batting_hand', 'right'),
            'bowling_type': data.get('bowling_type', 'none'),
            'bowling_action': data.get('bowling_action'),
            'bowling_rating': data.get('bowling_rating', 0),
            'source_world_id': data.get('source_world_id'),
            'is_regen': data.get('is_regen', 0),
        }
    )
    db.commit()
    return cur.lastrowid


# ── Venues ────────────────────────────────────────────────────────────────────

def get_venues(db):
    rows = db.execute("SELECT * FROM venues ORDER BY name").fetchall()
    return dict_from_rows(rows)


def get_venue(db, id):
    row = db.execute("SELECT * FROM venues WHERE id = ?", (id,)).fetchone()
    return dict_from_row(row)


def create_venue(db, data):
    cur = db.execute(
        "INSERT INTO venues (name, city, country, is_custom) VALUES (:name, :city, :country, :is_custom)",
        {
            'name': data['name'],
            'city': data.get('city'),
            'country': data.get('country'),
            'is_custom': data.get('is_custom', 0),
        }
    )
    db.commit()
    return cur.lastrowid


# ── Matches ───────────────────────────────────────────────────────────────────

def create_match(db, data):
    cur = db.execute(
        "INSERT INTO matches "
        "(series_id, tournament_id, world_id, format, venue_id, match_date, "
        " team1_id, team2_id, status, player_mode, human_team_id, canon_status, scoring_mode) "
        "VALUES (:series_id, :tournament_id, :world_id, :format, :venue_id, :match_date, "
        " :team1_id, :team2_id, 'in_progress', :player_mode, :human_team_id, :canon_status, :scoring_mode)",
        {
            'series_id':     data.get('series_id'),
            'tournament_id': data.get('tournament_id'),
            'world_id':      data.get('world_id'),
            'format':        data['format'],
            'venue_id':      data['venue_id'],
            'match_date':    data['match_date'],
            'team1_id':      data['team1_id'],
            'team2_id':      data['team2_id'],
            'player_mode':   data.get('player_mode', 'ai_vs_ai'),
            'human_team_id': data.get('human_team_id'),
            'canon_status':  data.get('canon_status', 'canon'),
            'scoring_mode':  data.get('scoring_mode', 'modern'),
        }
    )
    db.commit()
    return cur.lastrowid


def get_match(db, id):
    row = db.execute(
        "SELECT m.*, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " v.name as venue_name, v.city as venue_city, v.country as venue_country, "
        " v.capacity as venue_capacity, "
        " tw.name as toss_winner_name, "
        " wt.name as winning_team_name, "
        " pom.name as player_of_match_name "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "JOIN venues v ON m.venue_id = v.id "
        "LEFT JOIN teams tw ON m.toss_winner_id = tw.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "LEFT JOIN players pom ON m.player_of_match_id = pom.id "
        "WHERE m.id = ?",
        (id,)
    ).fetchone()
    return dict_from_row(row)


def update_match(db, id, data):
    allowed = [
        'toss_winner_id', 'toss_choice', 'result_type', 'winning_team_id',
        'margin_runs', 'margin_wickets', 'player_of_match_id', 'status', 'match_notes',
        'player_mode', 'human_team_id', 'scoring_mode', 'attendance',
    ]
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE matches SET {sets} WHERE id = :_id", data)
    db.commit()


def get_recent_world_matches(db, world_id, limit=8):
    rows = db.execute(
        "SELECT m.id, m.match_date, m.format, m.result_type, "
        " m.margin_runs, m.margin_wickets, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " wt.name as winning_team_name, wt.id as winning_team_id "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE m.world_id = ? AND m.status = 'complete' "
        "ORDER BY m.match_date DESC, m.id DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    return dict_from_rows(rows)


def get_recent_matches(db, limit=10):
    rows = db.execute(
        "SELECT m.id, m.match_date, m.format, m.result_type, "
        " m.margin_runs, m.margin_wickets, "
        " COALESCE(m.player_mode, 'ai_vs_ai') as player_mode, "
        " COALESCE(m.canon_status, 'canon') as canon_status, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " v.name as venue_name, v.city as venue_city, "
        " wt.name as winning_team_name "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "JOIN venues v ON m.venue_id = v.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE m.status = 'complete' "
        "  AND COALESCE(m.canon_status, 'canon') != 'deleted' "
        "ORDER BY m.match_date DESC, m.id DESC "
        "LIMIT ?",
        (limit,)
    ).fetchall()
    return dict_from_rows(rows)


# ── Innings ───────────────────────────────────────────────────────────────────

def create_innings(db, match_id, innings_number, batting_team_id, bowling_team_id):
    cur = db.execute(
        "INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id, status) "
        "VALUES (?, ?, ?, ?, 'in_progress')",
        (match_id, innings_number, batting_team_id, bowling_team_id)
    )
    db.commit()
    return cur.lastrowid


def get_innings(db, match_id):
    rows = db.execute(
        "SELECT i.*, "
        " bt.name as batting_team_name, bt.short_code as batting_team_code, "
        " bwt.name as bowling_team_name, bwt.short_code as bowling_team_code "
        "FROM innings i "
        "JOIN teams bt ON i.batting_team_id = bt.id "
        "JOIN teams bwt ON i.bowling_team_id = bwt.id "
        "WHERE i.match_id = ? ORDER BY i.innings_number",
        (match_id,)
    ).fetchall()
    return dict_from_rows(rows)


def get_innings_by_id(db, innings_id):
    row = db.execute(
        "SELECT i.*, "
        " bt.name as batting_team_name, bt.short_code as batting_team_code, "
        " bwt.name as bowling_team_name, bwt.short_code as bowling_team_code "
        "FROM innings i "
        "JOIN teams bt ON i.batting_team_id = bt.id "
        "JOIN teams bwt ON i.bowling_team_id = bwt.id "
        "WHERE i.id = ?",
        (innings_id,)
    ).fetchone()
    return dict_from_row(row)


def update_innings(db, innings_id, data):
    allowed = [
        'total_runs', 'total_wickets', 'overs_completed',
        'runs_at_100_overs', 'wickets_at_100_overs',
        'runs_at_110_overs', 'wickets_at_110_overs',
        'extras_byes', 'extras_legbyes', 'extras_wides', 'extras_noballs',
        'declared', 'follow_on', 'status',
        # The Hundred phase columns
        'balls_used', 'powerplay_runs', 'powerplay_wickets',
        'death_runs', 'death_wickets', 'strategic_timeout_ball',
    ]
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = innings_id
    db.execute(f"UPDATE innings SET {sets} WHERE id = :_id", data)
    db.commit()


# ── Batter Innings ────────────────────────────────────────────────────────────

def create_batter_innings(db, innings_id, player_id, batting_position):
    cur = db.execute(
        "INSERT INTO batter_innings (innings_id, player_id, batting_position, status) "
        "VALUES (?, ?, ?, 'yet_to_bat')",
        (innings_id, player_id, batting_position)
    )
    db.commit()
    return cur.lastrowid


def get_batter_innings(db, innings_id):
    rows = db.execute(
        "SELECT bi.*, p.name, p.name as player_name, p.batting_hand "
        "FROM batter_innings bi "
        "JOIN players p ON bi.player_id = p.id "
        "WHERE bi.innings_id = ? ORDER BY bi.batting_position",
        (innings_id,)
    ).fetchall()
    return dict_from_rows(rows)


def update_batter_innings(db, id, data):
    allowed = [
        'runs', 'balls_faced', 'fours', 'sixes',
        'dismissal_type', 'bowler_id', 'fielder_id',
        'not_out', 'retired_hurt', 'status'
    ]
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE batter_innings SET {sets} WHERE id = :_id", data)
    db.commit()


# ── Bowler Innings ────────────────────────────────────────────────────────────

def create_bowler_innings(db, innings_id, player_id):
    cur = db.execute(
        "INSERT INTO bowler_innings (innings_id, player_id) VALUES (?, ?)",
        (innings_id, player_id)
    )
    db.commit()
    return cur.lastrowid


def get_bowler_innings(db, innings_id):
    rows = db.execute(
        "SELECT bwi.*, p.name, p.name as player_name, p.bowling_type, p.bowling_rating "
        "FROM bowler_innings bwi "
        "JOIN players p ON bwi.player_id = p.id "
        "WHERE bwi.innings_id = ? ORDER BY bwi.id",
        (innings_id,)
    ).fetchall()
    return dict_from_rows(rows)


def update_bowler_innings(db, id, data):
    allowed = [
        'overs', 'balls', 'maidens', 'runs_conceded',
        'wickets', 'wides', 'no_balls'
    ]
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE bowler_innings SET {sets} WHERE id = :_id", data)
    db.commit()


# ── Deliveries ────────────────────────────────────────────────────────────────

def insert_delivery(db, data):
    cur = db.execute(
        "INSERT INTO deliveries "
        "(innings_id, over_number, ball_number, bowler_id, striker_id, non_striker_id, "
        " stage1_roll, stage2_roll, stage3_roll, stage4_roll, stage4b_roll, "
        " outcome_type, runs_scored, extras_type, extras_runs, "
        " dismissal_type, dismissed_batter_id, shot_angle, "
        " is_free_hit, is_wide, is_no_ball, commentary) "
        "VALUES "
        "(:innings_id, :over_number, :ball_number, :bowler_id, :striker_id, :non_striker_id, "
        " :stage1_roll, :stage2_roll, :stage3_roll, :stage4_roll, :stage4b_roll, "
        " :outcome_type, :runs_scored, :extras_type, :extras_runs, "
        " :dismissal_type, :dismissed_batter_id, :shot_angle, "
        " :is_free_hit, :is_wide, :is_no_ball, :commentary)",
        {
            'innings_id':          data['innings_id'],
            'over_number':         data['over_number'],
            'ball_number':         data['ball_number'],
            'bowler_id':           data['bowler_id'],
            'striker_id':          data['striker_id'],
            'non_striker_id':      data['non_striker_id'],
            'stage1_roll':         data.get('stage1_roll'),
            'stage2_roll':         data.get('stage2_roll'),
            'stage3_roll':         data.get('stage3_roll'),
            'stage4_roll':         data.get('stage4_roll'),
            'stage4b_roll':        data.get('stage4b_roll'),
            'outcome_type':        data.get('outcome_type', 'dot'),
            'runs_scored':         data.get('runs_scored', 0),
            'extras_type':         data.get('extras_type'),
            'extras_runs':         data.get('extras_runs', 0),
            'dismissal_type':      data.get('dismissal_type'),
            'dismissed_batter_id': data.get('dismissed_batter_id'),
            'shot_angle':          data.get('shot_angle'),
            'is_free_hit':         1 if data.get('is_free_hit') else 0,
            'is_wide':             1 if data.get('is_wide') else 0,
            'is_no_ball':          1 if data.get('is_no_ball') else 0,
            'commentary':          data.get('commentary', ''),
        }
    )
    db.commit()
    return cur.lastrowid


def get_deliveries(db, innings_id):
    rows = db.execute(
        "SELECT d.*, "
        " b.name as bowler_name, "
        " s.name as striker_name, "
        " ns.name as non_striker_name "
        "FROM deliveries d "
        "JOIN players b  ON d.bowler_id      = b.id "
        "JOIN players s  ON d.striker_id     = s.id "
        "JOIN players ns ON d.non_striker_id = ns.id "
        "WHERE d.innings_id = ? "
        "ORDER BY d.over_number, d.ball_number",
        (innings_id,)
    ).fetchall()
    return dict_from_rows(rows)


def get_all_deliveries_for_match(db, match_id):
    """All deliveries across all innings for a match.
    Falls back to deliveries_archive_json if live table has no rows."""
    import json as _json
    rows = db.execute(
        "SELECT d.*, i.innings_number, "
        " b.name as bowler_name, "
        " s.name as striker_name "
        "FROM deliveries d "
        "JOIN innings i ON d.innings_id = i.id "
        "JOIN players b ON d.bowler_id  = b.id "
        "JOIN players s ON d.striker_id = s.id "
        "WHERE i.match_id = ? "
        "ORDER BY i.innings_number, d.over_number, d.ball_number",
        (match_id,)
    ).fetchall()
    if rows:
        return dict_from_rows(rows)
    # Check archive
    match_row = db.execute(
        "SELECT deliveries_archive_json FROM matches WHERE id = ?", (match_id,)
    ).fetchone()
    if match_row and match_row['deliveries_archive_json']:
        try:
            return _json.loads(match_row['deliveries_archive_json'])
        except Exception:
            pass
    return []


# ── Partnerships ──────────────────────────────────────────────────────────────

def create_partnership(db, innings_id, wicket_number, b1_id, b2_id):
    cur = db.execute(
        "INSERT INTO partnerships (innings_id, wicket_number, batter1_id, batter2_id) "
        "VALUES (?, ?, ?, ?)",
        (innings_id, wicket_number, b1_id, b2_id)
    )
    db.commit()
    return cur.lastrowid


def update_partnership(db, id, data):
    allowed = ['runs', 'balls']
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE partnerships SET {sets} WHERE id = :_id", data)
    db.commit()


def get_partnership(db, innings_id, wicket_number):
    row = db.execute(
        "SELECT p.*, "
        " b1.name as batter1_name, b2.name as batter2_name "
        "FROM partnerships p "
        "JOIN players b1 ON p.batter1_id = b1.id "
        "JOIN players b2 ON p.batter2_id = b2.id "
        "WHERE p.innings_id = ? AND p.wicket_number = ?",
        (innings_id, wicket_number)
    ).fetchone()
    return dict_from_row(row)


def get_all_partnerships(db, innings_id):
    rows = db.execute(
        "SELECT p.*, "
        " b1.name as batter1_name, b2.name as batter2_name "
        "FROM partnerships p "
        "JOIN players b1 ON p.batter1_id = b1.id "
        "JOIN players b2 ON p.batter2_id = b2.id "
        "WHERE p.innings_id = ? ORDER BY p.wicket_number",
        (innings_id,)
    ).fetchall()
    return dict_from_rows(rows)


# ── Fall of Wickets ───────────────────────────────────────────────────────────

def insert_fall_of_wicket(db, innings_id, wicket_number, score, overs, batter_id):
    cur = db.execute(
        "INSERT INTO fall_of_wickets "
        "(innings_id, wicket_number, score_at_fall, overs_at_fall, dismissed_batter_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (innings_id, wicket_number, score, overs, batter_id)
    )
    db.commit()
    return cur.lastrowid


def get_fall_of_wickets(db, innings_id):
    rows = db.execute(
        "SELECT fow.*, p.name as batter_name "
        "FROM fall_of_wickets fow "
        "JOIN players p ON fow.dismissed_batter_id = p.id "
        "WHERE fow.innings_id = ? ORDER BY fow.wicket_number",
        (innings_id,)
    ).fetchall()
    return dict_from_rows(rows)


# ── Match Journal ─────────────────────────────────────────────────────────────

def save_journal_entry(db, match_id, text, note_type='match_report'):
    cur = db.execute(
        "INSERT INTO match_journal (match_id, note_text, note_type) VALUES (?, ?, ?)",
        (match_id, text, note_type)
    )
    db.commit()
    return cur.lastrowid


def get_journal_entries(db, match_id):
    rows = db.execute(
        "SELECT * FROM match_journal WHERE match_id = ? ORDER BY created_at DESC",
        (match_id,)
    ).fetchall()
    return dict_from_rows(rows)


def get_all_journal_entries(db, search=None, format_filter=None, limit=50, offset=0):
    query = (
        "SELECT mj.*, m.match_date, m.format, "
        " t1.name as team1_name, t2.name as team2_name, "
        " wt.name as winning_team_name, m.result_type, m.margin_runs, m.margin_wickets "
        "FROM match_journal mj "
        "JOIN matches m ON mj.match_id = m.id "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE 1=1"
    )
    params = []
    if search:
        query += " AND mj.note_text LIKE ?"
        params.append(f'%{search}%')
    if format_filter:
        query += " AND m.format = ?"
        params.append(format_filter)
    query += " ORDER BY mj.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = db.execute(query, params).fetchall()
    return dict_from_rows(rows)


def count_journal_entries(db, search=None, format_filter=None):
    query = (
        "SELECT COUNT(*) as c FROM match_journal mj "
        "JOIN matches m ON mj.match_id = m.id "
        "WHERE 1=1"
    )
    params = []
    if search:
        query += " AND mj.note_text LIKE ?"
        params.append(f'%{search}%')
    if format_filter:
        query += " AND m.format = ?"
        params.append(format_filter)
    row = db.execute(query, params).fetchone()
    return row['c'] if row else 0


# ── Series ────────────────────────────────────────────────────────────────────

def create_series(db, data):
    cur = db.execute(
        "INSERT INTO series (name, format, series_type, world_id, start_date, "
        " team1_id, team2_id, status, settings_json) "
        "VALUES (:name, :format, :series_type, :world_id, :start_date, "
        " :team1_id, :team2_id, 'scheduled', :settings_json)",
        {
            'name': data['name'],
            'format': data['format'],
            'series_type': data.get('series_type', 'bilateral'),
            'world_id': data.get('world_id'),
            'start_date': data.get('start_date'),
            'team1_id': data['team1_id'],
            'team2_id': data['team2_id'],
            'settings_json': data.get('settings_json'),
        }
    )
    db.commit()
    return cur.lastrowid


def get_series(db, id):
    row = db.execute(
        "SELECT s.*, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " wt.name as winner_name "
        "FROM series s "
        "JOIN teams t1 ON s.team1_id = t1.id "
        "JOIN teams t2 ON s.team2_id = t2.id "
        "LEFT JOIN teams wt ON s.winner_team_id = wt.id "
        "WHERE s.id = ?",
        (id,)
    ).fetchone()
    return dict_from_row(row)


def get_series_matches(db, series_id):
    rows = db.execute(
        "SELECT m.*, "
        " t1.name as team1_name, t1.short_code as team1_code, "
        " t2.name as team2_name, t2.short_code as team2_code, "
        " v.name as venue_name, "
        " wt.name as winning_team_name "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "JOIN venues v ON m.venue_id = v.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE m.series_id = ? ORDER BY m.match_date",
        (series_id,)
    ).fetchall()
    return dict_from_rows(rows)


def get_series_list(db):
    rows = db.execute(
        "SELECT s.*, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " wt.name as winner_name "
        "FROM series s "
        "JOIN teams t1 ON s.team1_id = t1.id "
        "JOIN teams t2 ON s.team2_id = t2.id "
        "LEFT JOIN teams wt ON s.winner_team_id = wt.id "
        "ORDER BY s.start_date DESC"
    ).fetchall()
    return dict_from_rows(rows)


def update_series(db, id, data):
    allowed = ['winner_team_id', 'status', 'end_date']
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE series SET {sets} WHERE id = :_id", data)
    db.commit()


# ── Tournaments ───────────────────────────────────────────────────────────────

def create_tournament(db, data):
    cur = db.execute(
        "INSERT INTO tournaments (name, format, tournament_type, world_id, start_date, status, settings_json) "
        "VALUES (:name, :format, :tournament_type, :world_id, :start_date, 'scheduled', :settings_json)",
        {
            'name': data['name'],
            'format': data.get('format', 'ODI'),
            'tournament_type': data.get('tournament_type', 'world_cup'),
            'world_id': data.get('world_id'),
            'start_date': data.get('start_date'),
            'settings_json': data.get('settings_json'),
        }
    )
    db.commit()
    return cur.lastrowid


def get_tournament(db, id):
    row = db.execute(
        "SELECT t.*, wt.name as winner_name "
        "FROM tournaments t LEFT JOIN teams wt ON t.winner_team_id = wt.id "
        "WHERE t.id = ?",
        (id,)
    ).fetchone()
    return dict_from_row(row)


def get_tournament_teams(db, tournament_id):
    rows = db.execute(
        "SELECT tt.*, t.name as team_name, t.short_code, t.badge_colour "
        "FROM tournament_teams tt JOIN teams t ON tt.team_id = t.id "
        "WHERE tt.tournament_id = ? "
        "ORDER BY tt.group_name, tt.points DESC, tt.nrr DESC",
        (tournament_id,)
    ).fetchall()
    return dict_from_rows(rows)


def update_tournament(db, id, data):
    allowed = ['winner_team_id', 'status']
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE tournaments SET {sets} WHERE id = :_id", data)
    db.commit()


def update_tournament_team(db, id, data):
    allowed = ['played', 'won', 'lost', 'drawn', 'no_result', 'points',
               'runs_scored', 'overs_faced', 'runs_conceded', 'overs_bowled', 'nrr']
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE tournament_teams SET {sets} WHERE id = :_id", data)
    db.commit()


def get_tournament_team_row(db, tournament_id, team_id):
    row = db.execute(
        "SELECT * FROM tournament_teams WHERE tournament_id = ? AND team_id = ?",
        (tournament_id, team_id)
    ).fetchone()
    return dict_from_row(row)


def create_tournament_team(db, tournament_id, team_id, group_name):
    cur = db.execute(
        "INSERT INTO tournament_teams (tournament_id, team_id, group_name) VALUES (?, ?, ?)",
        (tournament_id, team_id, group_name)
    )
    db.commit()
    return cur.lastrowid


# ── Fixtures ──────────────────────────────────────────────────────────────────

def create_fixture(db, data):
    cur = db.execute(
        "INSERT INTO fixtures "
        "(tournament_id, series_id, world_id, scheduled_date, venue_id, "
        " team1_id, team2_id, fixture_type, format, is_user_match, status) "
        "VALUES (:tournament_id, :series_id, :world_id, :scheduled_date, :venue_id, "
        " :team1_id, :team2_id, :fixture_type, :format, :is_user_match, 'scheduled')",
        {
            'tournament_id':  data.get('tournament_id'),
            'series_id':      data.get('series_id'),
            'world_id':       data.get('world_id'),
            'scheduled_date': data.get('scheduled_date'),
            'venue_id':       data.get('venue_id'),
            'team1_id':       data['team1_id'],
            'team2_id':       data['team2_id'],
            'fixture_type':   data.get('fixture_type', 'league'),
            'format':         data.get('format'),
            'is_user_match':  data.get('is_user_match', 0),
        }
    )
    db.commit()
    return cur.lastrowid


def bulk_create_fixtures(db, fixtures):
    """Insert many fixtures at once without per-row commits."""
    db.executemany(
        "INSERT INTO fixtures "
        "(tournament_id, series_id, world_id, scheduled_date, venue_id, "
        " team1_id, team2_id, fixture_type, format, is_user_match, status, "
        " series_name, match_number_in_series, series_length, "
        " is_icc_event, icc_event_name, is_home_for_team1, tour_template, season_year, "
        " competition_key, competition_name, competition_stage, competition_group, "
        " competition_round, competition_order) "
        "VALUES (:tournament_id, :series_id, :world_id, :scheduled_date, :venue_id, "
        " :team1_id, :team2_id, :fixture_type, :format, :is_user_match, 'scheduled', "
        " :series_name, :match_number_in_series, :series_length, "
        " :is_icc_event, :icc_event_name, :is_home_for_team1, :tour_template, :season_year, "
        " :competition_key, :competition_name, :competition_stage, :competition_group, "
        " :competition_round, :competition_order)",
        [{
            **f,
            'format':                  f.get('format'),
            'is_user_match':           f.get('is_user_match', 0),
            'series_name':             f.get('series_name'),
            'match_number_in_series':  f.get('match_number_in_series', 1),
            'series_length':           f.get('series_length', 1),
            'is_icc_event':            1 if f.get('is_icc_event') else 0,
            'icc_event_name':          f.get('icc_event_name'),
            'is_home_for_team1':       1 if f.get('is_home_for_team1', True) else 0,
            'tour_template':           f.get('tour_template'),
            'season_year':             f.get('season_year'),
            'competition_key':         f.get('competition_key'),
            'competition_name':        f.get('competition_name'),
            'competition_stage':       f.get('competition_stage'),
            'competition_group':       f.get('competition_group'),
            'competition_round':       f.get('competition_round'),
            'competition_order':       f.get('competition_order'),
        } for f in fixtures]
    )
    db.commit()


def create_world_series(db, data):
    """Insert a world_series record and return its id."""
    cur = db.execute(
        "INSERT INTO world_series "
        "(world_id, series_name, format, team1_id, team2_id, host_team_id, "
        " start_date, end_date, total_matches, is_icc_event, icc_event_name, status) "
        "VALUES (:world_id, :series_name, :format, :team1_id, :team2_id, :host_team_id, "
        " :start_date, :end_date, :total_matches, :is_icc_event, :icc_event_name, 'scheduled')",
        {
            'world_id':       data['world_id'],
            'series_name':    data['series_name'],
            'format':         data.get('format'),
            'team1_id':       data.get('team1_id'),
            'team2_id':       data.get('team2_id'),
            'host_team_id':   data.get('host_team_id'),
            'start_date':     data.get('start_date'),
            'end_date':       data.get('end_date'),
            'total_matches':  data.get('total_matches', 0),
            'is_icc_event':   1 if data.get('is_icc_event') else 0,
            'icc_event_name': data.get('icc_event_name'),
        }
    )
    db.commit()
    return cur.lastrowid


def get_world_series(db, world_id, status=None):
    """Return all series for a world, optionally filtered by status."""
    q = (
        "SELECT ws.*, "
        "  t1.name as team1_name, t2.name as team2_name, "
        "  ht.name as host_team_name "
        "FROM world_series ws "
        "LEFT JOIN teams t1 ON ws.team1_id = t1.id "
        "LEFT JOIN teams t2 ON ws.team2_id = t2.id "
        "LEFT JOIN teams ht ON ws.host_team_id = ht.id "
        "WHERE ws.world_id = ?"
    )
    params = [world_id]
    if status:
        q += " AND ws.status = ?"
        params.append(status)
    q += " ORDER BY ws.start_date"
    rows = db.execute(q, params).fetchall()
    return dict_from_rows(rows)


def get_fixtures(db, world_id=None, series_id=None, tournament_id=None, status=None):
    query = (
        "SELECT f.*, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " v.name as venue_name "
        "FROM fixtures f "
        "JOIN teams t1 ON f.team1_id = t1.id "
        "JOIN teams t2 ON f.team2_id = t2.id "
        "LEFT JOIN venues v ON f.venue_id = v.id "
        "WHERE 1=1"
    )
    params = []
    if world_id is not None:
        query += " AND f.world_id = ?"
        params.append(world_id)
    if series_id is not None:
        query += " AND f.series_id = ?"
        params.append(series_id)
    if tournament_id is not None:
        query += " AND f.tournament_id = ?"
        params.append(tournament_id)
    if status is not None:
        query += " AND f.status = ?"
        params.append(status)
    query += " ORDER BY f.scheduled_date, f.id"
    rows = db.execute(query, params).fetchall()
    return dict_from_rows(rows)


def update_fixture(db, id, data):
    allowed = ['match_id', 'status', 'is_user_match', 'format']
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE fixtures SET {sets} WHERE id = :_id", data)
    db.commit()


# ── Worlds ────────────────────────────────────────────────────────────────────

def create_world(db, data):
    cur = db.execute(
        "INSERT INTO worlds (name, created_date, current_date, calendar_density, settings_json, is_active) "
        "VALUES (:name, :created_date, :current_date, :calendar_density, :settings_json, 1)",
        {
            'name':             data['name'],
            'created_date':     data.get('created_date'),
            'current_date':     data.get('current_date', data.get('created_date')),
            'calendar_density': data.get('calendar_density', 'moderate'),
            'settings_json':    data.get('settings_json'),
        }
    )
    db.commit()
    return cur.lastrowid


def get_world(db, id):
    row = db.execute("SELECT * FROM worlds WHERE id = ?", (id,)).fetchone()
    return dict_from_row(row)


def get_worlds(db):
    rows = db.execute("SELECT * FROM worlds ORDER BY created_date DESC").fetchall()
    return dict_from_rows(rows)


def update_world(db, id, data):
    allowed = ['current_date', 'is_active', 'settings_json']
    sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
    if not sets:
        return
    data['_id'] = id
    db.execute(f"UPDATE worlds SET {sets} WHERE id = :_id", data)
    db.commit()


def delete_world(db, world_id):
    """Delete a world and all world-scoped data linked to it."""
    world = get_world(db, world_id)
    if not world:
        return False

    match_rows = db.execute(
        "SELECT id FROM matches WHERE world_id = ?",
        (world_id,)
    ).fetchall()
    match_ids = [row['id'] for row in match_rows]

    if match_ids:
        marks = ','.join('?' * len(match_ids))
        innings_rows = db.execute(
            f"SELECT id FROM innings WHERE match_id IN ({marks})",
            match_ids
        ).fetchall()
        innings_ids = [row['id'] for row in innings_rows]
        if innings_ids:
            imarks = ','.join('?' * len(innings_ids))
            db.execute(f"DELETE FROM deliveries WHERE innings_id IN ({imarks})", innings_ids)
            db.execute(f"DELETE FROM fall_of_wickets WHERE innings_id IN ({imarks})", innings_ids)
            db.execute(f"DELETE FROM partnerships WHERE innings_id IN ({imarks})", innings_ids)
            db.execute(f"DELETE FROM batter_innings WHERE innings_id IN ({imarks})", innings_ids)
            db.execute(f"DELETE FROM bowler_innings WHERE innings_id IN ({imarks})", innings_ids)
            db.execute(f"DELETE FROM innings WHERE id IN ({imarks})", innings_ids)
        db.execute(f"DELETE FROM match_journal WHERE match_id IN ({marks})", match_ids)
        db.execute(f"DELETE FROM almanack_audit_log WHERE match_id IN ({marks})", match_ids)
        db.execute(f"DELETE FROM ranking_history WHERE after_match_id IN ({marks})", match_ids)
        db.execute(f"DELETE FROM matches WHERE id IN ({marks})", match_ids)

    tournament_rows = db.execute(
        "SELECT id FROM tournaments WHERE world_id = ?",
        (world_id,)
    ).fetchall()
    tournament_ids = [row['id'] for row in tournament_rows]
    if tournament_ids:
        tmarks = ','.join('?' * len(tournament_ids))
        db.execute(f"DELETE FROM tournament_teams WHERE tournament_id IN ({tmarks})", tournament_ids)
        db.execute(f"DELETE FROM tournaments WHERE id IN ({tmarks})", tournament_ids)

    db.execute("DELETE FROM fixtures WHERE world_id = ?", (world_id,))
    db.execute("DELETE FROM world_series WHERE world_id = ?", (world_id,))
    db.execute("DELETE FROM world_rankings WHERE world_id = ?", (world_id,))
    db.execute("DELETE FROM ranking_history WHERE world_id = ?", (world_id,))
    db.execute("DELETE FROM world_records WHERE world_id = ?", (world_id,))
    db.execute("DELETE FROM player_world_state WHERE world_id = ?", (world_id,))
    db.execute("DELETE FROM series WHERE world_id = ?", (world_id,))
    db.execute("DELETE FROM worlds WHERE id = ?", (world_id,))
    db.commit()
    return True


# ── World Rankings ────────────────────────────────────────────────────────────

def get_world_rankings(db, world_id, format_filter=None):
    query = (
        "SELECT wr.*, t.name as team_name, t.short_code, t.badge_colour "
        "FROM world_rankings wr JOIN teams t ON wr.team_id = t.id "
        "WHERE wr.world_id = ?"
    )
    params = [world_id]
    if format_filter:
        query += " AND wr.format = ?"
        params.append(format_filter)
    query += " ORDER BY wr.format, wr.position"
    rows = db.execute(query, params).fetchall()
    return dict_from_rows(rows)


def insert_ranking_history(db, world_id, team_id, format_, points, position, snapshot_date, after_match_id=None):
    db.execute(
        "INSERT INTO ranking_history (world_id, team_id, format, points, position, snapshot_date, after_match_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (world_id, team_id, format_, points, position, snapshot_date, after_match_id)
    )
    db.commit()


def get_ranking_history(db, world_id, team_id=None, format_=None, limit=10):
    query = (
        "SELECT rh.*, t.name as team_name "
        "FROM ranking_history rh JOIN teams t ON rh.team_id = t.id "
        "WHERE rh.world_id = ?"
    )
    params = [world_id]
    if team_id:
        query += " AND rh.team_id = ?"
        params.append(team_id)
    if format_:
        query += " AND rh.format = ?"
        params.append(format_)
    query += " ORDER BY rh.snapshot_date DESC, rh.id DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(query, params).fetchall()
    return dict_from_rows(rows)


def upsert_world_ranking(db, world_id, team_id, format_, points, position, matches):
    existing = db.execute(
        "SELECT id FROM world_rankings WHERE world_id=? AND team_id=? AND format=?",
        (world_id, team_id, format_)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE world_rankings SET points=?, position=?, matches_counted=?, updated_date=date('now') "
            "WHERE id=?",
            (points, position, matches, existing['id'])
        )
    else:
        db.execute(
            "INSERT INTO world_rankings (world_id, team_id, format, points, position, matches_counted, updated_date) "
            "VALUES (?, ?, ?, ?, ?, ?, date('now'))",
            (world_id, team_id, format_, points, position, matches)
        )
    db.commit()


# ── World Records ─────────────────────────────────────────────────────────────

def get_world_records(db, world_id):
    rows = db.execute(
        "SELECT * FROM world_records WHERE world_id = ? ORDER BY record_key",
        (world_id,)
    ).fetchall()
    return dict_from_rows(rows)


def upsert_world_record(db, world_id, record_key, record_value, context_json, format_=None):
    existing = db.execute(
        "SELECT id FROM world_records WHERE world_id=? AND record_key=?",
        (world_id, record_key)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE world_records SET record_value=?, context_json=?, format=?, updated_at=CURRENT_TIMESTAMP "
            "WHERE id=?",
            (record_value, context_json, format_, existing['id'])
        )
    else:
        db.execute(
            "INSERT INTO world_records (world_id, record_key, record_value, context_json, format) "
            "VALUES (?, ?, ?, ?, ?)",
            (world_id, record_key, record_value, context_json, format_)
        )
    db.commit()


# ── Player World State ────────────────────────────────────────────────────────

def get_player_world_states(db, world_id):
    """Return {player_id: state_dict} for all players in a world."""
    rows = db.execute(
        "SELECT * FROM player_world_state WHERE world_id = ?", (world_id,)
    ).fetchall()
    return {row['player_id']: dict(row) for row in rows}


def upsert_player_world_state(db, world_id, player_id, data):
    existing = db.execute(
        "SELECT id FROM player_world_state WHERE world_id=? AND player_id=?",
        (world_id, player_id)
    ).fetchone()
    if existing:
        allowed = ['form_adjustment', 'fatigue', 'career_runs',
                   'career_wickets', 'career_matches', 'last_match_dates',
                   'age', 'last_age_year', 'active', 'retirement_reason',
                   'retired_on', 'regen_generation', 'retire_age']
        sets = ', '.join(f"{k} = :{k}" for k in allowed if k in data)
        if sets:
            data['_id'] = existing['id']
            db.execute(f"UPDATE player_world_state SET {sets} WHERE id = :_id", data)
    else:
        db.execute(
            "INSERT INTO player_world_state "
            "(world_id, player_id, form_adjustment, fatigue, career_runs, "
            " career_wickets, career_matches, last_match_dates, age, last_age_year, "
            " active, retirement_reason, retired_on, regen_generation, retire_age) "
            "VALUES (:world_id, :player_id, :form_adjustment, :fatigue, :career_runs, "
            " :career_wickets, :career_matches, :last_match_dates, :age, :last_age_year, "
            " :active, :retirement_reason, :retired_on, :regen_generation, :retire_age)",
            {
                'world_id':          world_id,
                'player_id':         player_id,
                'form_adjustment':   data.get('form_adjustment', 0),
                'fatigue':           data.get('fatigue', 0),
                'career_runs':       data.get('career_runs', 0),
                'career_wickets':    data.get('career_wickets', 0),
                'career_matches':    data.get('career_matches', 0),
                'last_match_dates':  data.get('last_match_dates', '[]'),
                'age':               data.get('age'),
                'last_age_year':     data.get('last_age_year'),
                'active':            data.get('active', 1),
                'retirement_reason': data.get('retirement_reason'),
                'retired_on':        data.get('retired_on'),
                'regen_generation':  data.get('regen_generation', 0),
                'retire_age':        data.get('retire_age'),
            }
        )
    db.commit()


# ── Schema Migrations ─────────────────────────────────────────────────────────

def run_migrations(db):
    """Apply incremental schema migrations (idempotent — safe to run on every startup)."""
    migrations = [
        "ALTER TABLE fixtures ADD COLUMN format TEXT",
        "ALTER TABLE fixtures ADD COLUMN is_user_match INTEGER DEFAULT 0",
        "ALTER TABLE matches ADD COLUMN deliveries_archive_json TEXT",
        "ALTER TABLE matches ADD COLUMN canon_status TEXT DEFAULT 'canon'",
        "ALTER TABLE matches ADD COLUMN player_mode TEXT DEFAULT 'ai_vs_ai'",
        "ALTER TABLE matches ADD COLUMN human_team_id INTEGER DEFAULT NULL",
        "ALTER TABLE matches ADD COLUMN scoring_mode TEXT DEFAULT 'modern'",
        "ALTER TABLE innings ADD COLUMN runs_at_100_overs INTEGER",
        "ALTER TABLE innings ADD COLUMN wickets_at_100_overs INTEGER",
        "ALTER TABLE innings ADD COLUMN runs_at_110_overs INTEGER",
        "ALTER TABLE innings ADD COLUMN wickets_at_110_overs INTEGER",
        # Calendar engine columns
        "ALTER TABLE fixtures ADD COLUMN series_name TEXT",
        "ALTER TABLE fixtures ADD COLUMN match_number_in_series INTEGER DEFAULT 1",
        "ALTER TABLE fixtures ADD COLUMN series_length INTEGER DEFAULT 1",
        "ALTER TABLE fixtures ADD COLUMN is_icc_event INTEGER DEFAULT 0",
        "ALTER TABLE fixtures ADD COLUMN icc_event_name TEXT",
        "ALTER TABLE fixtures ADD COLUMN is_home_for_team1 INTEGER DEFAULT 1",
        "ALTER TABLE fixtures ADD COLUMN tour_template TEXT",
        "ALTER TABLE fixtures ADD COLUMN season_year INTEGER",
        "ALTER TABLE fixtures ADD COLUMN competition_key TEXT",
        "ALTER TABLE fixtures ADD COLUMN competition_name TEXT",
        "ALTER TABLE fixtures ADD COLUMN competition_stage TEXT",
        "ALTER TABLE fixtures ADD COLUMN competition_group TEXT",
        "ALTER TABLE fixtures ADD COLUMN competition_round TEXT",
        "ALTER TABLE fixtures ADD COLUMN competition_order INTEGER",
        # Calendar style on worlds table
        "ALTER TABLE worlds ADD COLUMN calendar_style TEXT DEFAULT 'random'",
        # Domestic / franchise team type
        "ALTER TABLE teams ADD COLUMN team_type TEXT DEFAULT 'international'",
        "ALTER TABLE teams ADD COLUMN league TEXT",
        "ALTER TABLE players ADD COLUMN source_world_id INTEGER",
        "ALTER TABLE players ADD COLUMN is_regen INTEGER DEFAULT 0",
        # domestic_leagues on worlds settings (stored in settings_json; no column needed)
        # The Hundred — team and venue flags
        "ALTER TABLE teams ADD COLUMN is_hundred_team INTEGER DEFAULT 0",
        "ALTER TABLE venues ADD COLUMN is_hundred_venue INTEGER DEFAULT 0",
        # The Hundred — innings phase columns
        "ALTER TABLE innings ADD COLUMN powerplay_runs INTEGER DEFAULT 0",
        "ALTER TABLE innings ADD COLUMN powerplay_wickets INTEGER DEFAULT 0",
        "ALTER TABLE innings ADD COLUMN death_runs INTEGER DEFAULT 0",
        "ALTER TABLE innings ADD COLUMN death_wickets INTEGER DEFAULT 0",
        "ALTER TABLE innings ADD COLUMN balls_used INTEGER DEFAULT 0",
        "ALTER TABLE innings ADD COLUMN strategic_timeout_ball INTEGER DEFAULT NULL",
    ]
    for sql in migrations:
        try:
            db.execute(sql)
        except Exception:
            pass  # column already exists

    # The Hundred — widen format CHECK on matches and series to include 'Hundred'.
    # SQLite can't ALTER a column constraint, so we do the rename→create→copy→drop dance.
    # Wrapped in a savepoint so it's atomic and safe to re-run (idempotent via the sentinel).
    _matches_sentinel = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='matches' "
        "AND sql LIKE '%Hundred%'"
    ).fetchone()
    if not _matches_sentinel:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("PRAGMA legacy_alter_table = ON")
        db.execute("ALTER TABLE matches RENAME TO matches_old")
        db.execute(
            "CREATE TABLE matches ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  series_id INTEGER,"
            "  tournament_id INTEGER,"
            "  world_id INTEGER,"
            "  format TEXT CHECK(format IN ('Test','ODI','T20','Hundred')),"
            "  venue_id INTEGER NOT NULL,"
            "  match_date TEXT NOT NULL,"
            "  team1_id INTEGER NOT NULL,"
            "  team2_id INTEGER NOT NULL,"
            "  toss_winner_id INTEGER,"
            "  toss_choice TEXT CHECK(toss_choice IN ('bat','field')),"
            "  result_type TEXT CHECK(result_type IN ('runs','wickets','draw','tie','no_result')),"
            "  winning_team_id INTEGER,"
            "  margin_runs INTEGER,"
            "  margin_wickets INTEGER,"
            "  player_of_match_id INTEGER,"
            "  status TEXT DEFAULT 'in_progress',"
            "  scoring_mode TEXT DEFAULT 'modern',"
            "  match_notes TEXT,"
            "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "  deliveries_archive_json TEXT,"
            "  canon_status TEXT DEFAULT 'canon',"
            "  player_mode TEXT DEFAULT 'ai_vs_ai',"
            "  human_team_id INTEGER DEFAULT NULL,"
            "  FOREIGN KEY (series_id) REFERENCES series(id),"
            "  FOREIGN KEY (tournament_id) REFERENCES tournaments(id),"
            "  FOREIGN KEY (world_id) REFERENCES worlds(id),"
            "  FOREIGN KEY (venue_id) REFERENCES venues(id),"
            "  FOREIGN KEY (team1_id) REFERENCES teams(id),"
            "  FOREIGN KEY (team2_id) REFERENCES teams(id)"
            ")"
        )
        db.execute(
            "INSERT INTO matches SELECT "
            "  id, series_id, tournament_id, world_id, format, venue_id, match_date,"
            "  team1_id, team2_id, toss_winner_id, toss_choice, result_type,"
            "  winning_team_id, margin_runs, margin_wickets, player_of_match_id,"
            "  status, scoring_mode, match_notes, created_at, deliveries_archive_json,"
            "  canon_status, player_mode, human_team_id "
            "FROM matches_old"
        )
        db.execute("DROP TABLE matches_old")
        db.execute("PRAGMA legacy_alter_table = OFF")
        db.execute("PRAGMA foreign_keys = ON")

    _series_sentinel = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='series' "
        "AND sql LIKE '%Hundred%'"
    ).fetchone()
    if not _series_sentinel:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute("PRAGMA legacy_alter_table = ON")
        db.execute("ALTER TABLE series RENAME TO series_old")
        db.execute(
            "CREATE TABLE series ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name TEXT NOT NULL,"
            "  format TEXT CHECK(format IN ('Test','ODI','T20','Hundred')),"
            "  series_type TEXT,"
            "  world_id INTEGER,"
            "  start_date TEXT,"
            "  end_date TEXT,"
            "  team1_id INTEGER,"
            "  team2_id INTEGER,"
            "  winner_team_id INTEGER,"
            "  status TEXT DEFAULT 'scheduled',"
            "  settings_json TEXT,"
            "  FOREIGN KEY (world_id) REFERENCES worlds(id),"
            "  FOREIGN KEY (team1_id) REFERENCES teams(id),"
            "  FOREIGN KEY (team2_id) REFERENCES teams(id)"
            ")"
        )
        db.execute("INSERT INTO series SELECT * FROM series_old")
        db.execute("DROP TABLE series_old")
        db.execute("PRAGMA legacy_alter_table = OFF")
        db.execute("PRAGMA foreign_keys = ON")

    # The Hundred — set-by-set data table
    db.execute(
        "CREATE TABLE IF NOT EXISTS hundred_sets ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  innings_id INTEGER NOT NULL,"
        "  set_number INTEGER NOT NULL,"
        "  bowler_id INTEGER NOT NULL,"
        "  end_name TEXT,"
        "  balls_bowled INTEGER DEFAULT 0,"
        "  runs_conceded INTEGER DEFAULT 0,"
        "  wickets INTEGER DEFAULT 0,"
        "  is_powerplay INTEGER DEFAULT 0,"
        "  FOREIGN KEY (innings_id) REFERENCES innings(id)"
        ")"
    )

    # Ensure player_world_state table exists (for DBs created before this migration)
    db.execute(
        "CREATE TABLE IF NOT EXISTS player_world_state ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  world_id INTEGER NOT NULL,"
        "  player_id INTEGER NOT NULL,"
        "  form_adjustment INTEGER DEFAULT 0,"
        "  fatigue INTEGER DEFAULT 0,"
        "  career_runs INTEGER DEFAULT 0,"
        "  career_wickets INTEGER DEFAULT 0,"
        "  career_matches INTEGER DEFAULT 0,"
        "  last_match_dates TEXT DEFAULT '[]',"
        "  age INTEGER,"
        "  last_age_year INTEGER,"
        "  active INTEGER DEFAULT 1,"
        "  retirement_reason TEXT,"
        "  retired_on TEXT,"
        "  regen_generation INTEGER DEFAULT 0,"
        "  retire_age INTEGER,"
        "  UNIQUE(world_id, player_id),"
        "  FOREIGN KEY (world_id) REFERENCES worlds(id),"
        "  FOREIGN KEY (player_id) REFERENCES players(id)"
        ")"
    )

    for sql in [
        "ALTER TABLE player_world_state ADD COLUMN age INTEGER",
        "ALTER TABLE player_world_state ADD COLUMN last_age_year INTEGER",
        "ALTER TABLE player_world_state ADD COLUMN active INTEGER DEFAULT 1",
        "ALTER TABLE player_world_state ADD COLUMN retirement_reason TEXT",
        "ALTER TABLE player_world_state ADD COLUMN retired_on TEXT",
        "ALTER TABLE player_world_state ADD COLUMN regen_generation INTEGER DEFAULT 0",
        "ALTER TABLE player_world_state ADD COLUMN retire_age INTEGER",
    ]:
        try:
            db.execute(sql)
        except Exception:
            pass

    # Audit log table for canon/result edits
    db.execute(
        "CREATE TABLE IF NOT EXISTS almanack_audit_log ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  match_id INTEGER NOT NULL,"
        "  action TEXT NOT NULL,"
        "  old_value TEXT,"
        "  new_value TEXT,"
        "  actor TEXT DEFAULT 'user',"
        "  note TEXT,"
        "  created_at TEXT DEFAULT (datetime('now')),"
        "  FOREIGN KEY (match_id) REFERENCES matches(id)"
        ")"
    )

    # world_series table — tracks series context for world mode
    db.execute(
        "CREATE TABLE IF NOT EXISTS world_series ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  world_id INTEGER NOT NULL,"
        "  series_name TEXT NOT NULL,"
        "  format TEXT,"
        "  team1_id INTEGER,"
        "  team2_id INTEGER,"
        "  host_team_id INTEGER,"
        "  start_date TEXT,"
        "  end_date TEXT,"
        "  total_matches INTEGER,"
        "  matches_completed INTEGER DEFAULT 0,"
        "  is_icc_event INTEGER DEFAULT 0,"
        "  icc_event_name TEXT,"
        "  status TEXT DEFAULT 'scheduled',"
        "  winner_team_id INTEGER,"
        "  FOREIGN KEY (world_id) REFERENCES worlds(id)"
        ")"
    )

    # Recreate statistical views so fresh and migrated DBs agree on canon filtering.
    # (DROP + CREATE is idempotent — views have no data)
    db.execute("DROP VIEW IF EXISTS batting_averages")
    db.execute(
        "CREATE VIEW batting_averages AS "
        "SELECT "
        " p.id as player_id, p.name, t.name as team_name, t.id as team_id, m.format, "
        " COALESCE(m.canon_status, 'canon') as canon_status, "
        " COUNT(DISTINCT m.id) as matches, COUNT(bi.id) as innings, "
        " SUM(CASE WHEN bi.not_out=1 OR bi.status='batting' OR bi.status='not_out' THEN 1 ELSE 0 END) as not_outs, "
        " SUM(bi.runs) as runs, MAX(bi.runs) as highest_score, "
        " MAX(CASE WHEN bi.not_out=1 OR bi.status='batting' OR bi.status='not_out' THEN bi.runs ELSE 0 END) as highest_not_out, "
        " ROUND(CAST(SUM(bi.runs) AS REAL) / NULLIF(COUNT(bi.id) - "
        "   SUM(CASE WHEN bi.not_out=1 OR bi.status='batting' OR bi.status='not_out' THEN 1 ELSE 0 END), 0), 2) as average, "
        " ROUND(CAST(SUM(bi.runs) AS REAL) / NULLIF(SUM(bi.balls_faced), 0) * 100, 2) as strike_rate, "
        " SUM(CASE WHEN bi.runs >= 100 THEN 1 ELSE 0 END) as hundreds, "
        " SUM(CASE WHEN bi.runs >= 50 AND bi.runs < 100 THEN 1 ELSE 0 END) as fifties, "
        " SUM(CASE WHEN bi.runs = 0 AND bi.not_out = 0 AND bi.status != 'batting' AND bi.status != 'not_out' THEN 1 ELSE 0 END) as ducks, "
        " SUM(bi.fours) as fours, SUM(bi.sixes) as sixes, SUM(bi.balls_faced) as balls_faced "
        "FROM batter_innings bi "
        "JOIN innings i ON bi.innings_id = i.id "
        "JOIN matches m ON i.match_id = m.id "
        "JOIN players p ON bi.player_id = p.id "
        "JOIN teams t ON p.team_id = t.id "
        "WHERE bi.status != 'yet_to_bat' "
        "  AND COALESCE(m.canon_status, 'canon') = 'canon' "
        "GROUP BY p.id, m.format, COALESCE(m.canon_status, 'canon')"
    )

    db.execute("DROP VIEW IF EXISTS bowling_averages")
    db.execute(
        "CREATE VIEW bowling_averages AS "
        "SELECT "
        " p.id as player_id, p.name, p.bowling_type, t.name as team_name, t.id as team_id, m.format, "
        " COALESCE(m.canon_status, 'canon') as canon_status, "
        " COUNT(DISTINCT m.id) as matches, COUNT(bwi.id) as innings_bowled, "
        " SUM(bwi.overs) as overs, SUM(bwi.maidens) as maidens, "
        " SUM(bwi.runs_conceded) as runs_conceded, SUM(bwi.wickets) as wickets, "
        " ROUND(CAST(SUM(bwi.runs_conceded) AS REAL) / NULLIF(SUM(bwi.wickets), 0), 2) as average, "
        " ROUND(CAST(SUM(bwi.runs_conceded) AS REAL) / NULLIF(SUM(bwi.overs), 0), 2) as economy, "
        " ROUND(CAST(SUM(bwi.overs) * 6 AS REAL) / NULLIF(SUM(bwi.wickets), 0), 2) as strike_rate, "
        " SUM(CASE WHEN bwi.wickets >= 5 THEN 1 ELSE 0 END) as five_fors "
        "FROM bowler_innings bwi "
        "JOIN innings i ON bwi.innings_id = i.id "
        "JOIN matches m ON i.match_id = m.id "
        "JOIN players p ON bwi.player_id = p.id "
        "JOIN teams t ON p.team_id = t.id "
        "WHERE bwi.overs > 0 "
        "  AND COALESCE(m.canon_status, 'canon') = 'canon' "
        "GROUP BY p.id, m.format, COALESCE(m.canon_status, 'canon')"
    )

    db.execute("DROP VIEW IF EXISTS team_records_view")
    db.execute(
        "CREATE VIEW team_records_view AS "
        "SELECT "
        " t.id as team_id, t.name as team_name, m.format, "
        " COUNT(DISTINCT m.id) as matches_played, "
        " SUM(CASE WHEN m.winning_team_id = t.id THEN 1 ELSE 0 END) as won, "
        " SUM(CASE WHEN m.winning_team_id != t.id "
        "     AND m.result_type NOT IN ('draw','tie','no_result') THEN 1 ELSE 0 END) as lost, "
        " SUM(CASE WHEN m.result_type = 'draw' THEN 1 ELSE 0 END) as drawn, "
        " SUM(CASE WHEN m.result_type = 'tie' THEN 1 ELSE 0 END) as tied "
        "FROM teams t "
        "JOIN matches m ON (m.team1_id = t.id OR m.team2_id = t.id) "
        "WHERE m.status = 'complete' "
        "  AND COALESCE(m.canon_status, 'canon') = 'canon' "
        "GROUP BY t.id, m.format"
    )

    db.execute("DROP VIEW IF EXISTS partnership_records")
    db.execute(
        "CREATE VIEW partnership_records AS "
        "SELECT "
        " p.id, p.innings_id, p.wicket_number, p.runs, p.balls, "
        " b1.name as batter1_name, b2.name as batter2_name, "
        " p.batter1_id, p.batter2_id, m.format, i.match_id "
        "FROM partnerships p "
        "JOIN players b1 ON p.batter1_id = b1.id "
        "JOIN players b2 ON p.batter2_id = b2.id "
        "JOIN innings i ON p.innings_id = i.id "
        "JOIN matches m ON i.match_id = m.id "
        "WHERE COALESCE(m.canon_status, 'canon') = 'canon'"
    )

    # Draw outcomes — persisted results of group/bracket draws for world competitions
    db.execute(
        "CREATE TABLE IF NOT EXISTS draw_outcomes ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  world_id INTEGER NOT NULL,"
        "  competition_key TEXT NOT NULL,"
        "  season_key TEXT NOT NULL,"
        "  draw_type TEXT NOT NULL,"
        "  outcome_json TEXT NOT NULL,"
        "  created_at TEXT DEFAULT (datetime('now')),"
        "  UNIQUE(world_id, competition_key, season_key),"
        "  FOREIGN KEY (world_id) REFERENCES worlds(id)"
        ")"
    )

    # Real-world records reference table
    db.execute(
        "CREATE TABLE IF NOT EXISTS real_world_records ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  record_key TEXT NOT NULL,"
        "  format TEXT NOT NULL,"
        "  record_type TEXT NOT NULL,"
        "  value_runs INTEGER,"
        "  value_wickets INTEGER,"
        "  value_runs_conceded INTEGER,"
        "  value_decimal REAL,"
        "  display_value TEXT NOT NULL,"
        "  holder_name TEXT,"
        "  team_name TEXT,"
        "  opponent_name TEXT,"
        "  venue_name TEXT,"
        "  match_date TEXT,"
        "  notes TEXT"
        ")"
    )

    # The Hundred — seed franchise teams, venues, players, and records (idempotent)
    import seed_data as _sd
    _sd.seed_hundred_teams(db)

    # Venue capacity + match attendance columns
    for col_sql in [
        "ALTER TABLE venues ADD COLUMN capacity INTEGER",
        "ALTER TABLE matches ADD COLUMN attendance INTEGER",
    ]:
        try:
            db.execute(col_sql)
        except Exception:
            pass

    _seed_venue_capacities(db)

    # Venue coordinates — add columns then seed known lat/lng (idempotent)
    for col_sql in [
        "ALTER TABLE venues ADD COLUMN latitude REAL",
        "ALTER TABLE venues ADD COLUMN longitude REAL",
    ]:
        try:
            db.execute(col_sql)
        except Exception:
            pass  # already exists

    _seed_venue_coordinates(db)

    db.commit()


def _seed_venue_capacities(db):
    """Seed real-world capacity figures for known cricket venues (safe to re-run)."""
    capacities = {
        # Australia
        'Adelaide Oval':                      53000,
        'Blundstone Arena':                   19500,
        'Manuka Oval':                        13550,
        'Marvel Stadium':                     56347,
        'Melbourne Cricket Ground':          100024,
        'Optus Stadium':                      60000,
        'Sydney Cricket Ground':              48000,
        'The Gabba':                          41000,
        # Bangladesh
        'Shere Bangla National Stadium':      25000,
        # Canada
        'Maple Leaf North-West Ground':        7000,
        # England
        'Edgbaston':                          25000,
        'Emirates Riverside':                 17000,
        'Headingley':                         18350,
        "Lord's Cricket Ground":              30000,
        'New Road':                            4900,
        'Old Trafford':                       26500,
        'The 1st Central County Ground':       6500,
        'The Cloud County Ground':             6500,
        'The County Ground Bristol':           7000,
        'The County Ground Derby':             5000,
        'The County Ground Northampton':       7000,
        'The County Ground Taunton':           7500,
        'The Oval':                           27500,
        'The Spitfire Ground St Lawrence':    15000,
        'The Utilita Bowl':                   25000,
        'Utilita Bowl':                       25000,
        'Trent Bridge':                       17500,
        'Uptonsteel County Ground':            5000,
        # India
        'Arun Jaitley Stadium':               35200,
        'BRSABV Ekana Cricket Stadium':       50000,
        'Eden Gardens':                       68000,
        'M. Chinnaswamy Stadium':             40000,
        'MA Chidambaram Stadium':             37505,
        'Narendra Modi Stadium':             132000,
        'Punjab Cricket Association Stadium': 26950,
        'Rajiv Gandhi International Stadium': 39200,
        'Sawai Mansingh Stadium':             24000,
        'Wankhede Stadium':                   33100,
        # Ireland
        'Civil Service Cricket Club':          3000,
        'Malahide Cricket Club Ground':        5000,
        # Namibia
        'Wanderers Cricket Ground':            7000,
        # Nepal
        'Tribhuvan University Ground':        10000,
        # Netherlands
        'VRA Ground':                          4500,
        # New Zealand
        'Eden Park':                          42000,
        # Oman
        'Al Amerat Cricket Ground':            4000,
        # Pakistan
        'Arbab Niaz Stadium':                 20000,
        'Bugti Stadium':                      20000,
        'Gaddafi Stadium':                    34000,
        'Multan Cricket Stadium':             30000,
        'National Stadium':                   30000,
        'Rawalpindi Cricket Stadium':         15000,
        # Scotland
        'The Grange Club':                     4000,
        # South Africa
        'Newlands':                           25000,
        'The Wanderers':                      34000,
        # Sri Lanka
        'R. Premadasa Stadium':               35000,
        # UAE
        'Dubai International Stadium':        25000,
        'Sharjah Cricket Stadium':            27000,
        # United States
        'Grand Prairie Stadium':               7200,
        # Wales
        'Sophia Gardens':                     16000,
        # West Indies
        'Daren Sammy National Cricket Stadium': 15000,
        'Kensington Oval':                    28000,
        'National Cricket Stadium Grenada':   12000,
        'Providence Stadium':                 15000,
        "Queen's Park Oval":                  20000,
        'Sabina Park':                        30000,
        'Warner Park':                        18000,
        # Zimbabwe
        'Harare Sports Club':                 10000,
        'Queens Sports Club':                 10000,
    }
    for name, cap in capacities.items():
        existing = db.execute("SELECT capacity FROM venues WHERE name=?", (name,)).fetchone()
        if existing and existing['capacity'] is None:
            db.execute("UPDATE venues SET capacity=? WHERE name=?", (cap, name))


def _seed_venue_coordinates(db):
    """Seed approximate lat/lng for known cricket venues (safe to re-run)."""
    coords = {
        # Australia
        'Adelaide Oval':                   (-34.9155,  138.5963),
        'Blundstone Arena':                (-42.8785,  147.3290),
        'Manuka Oval':                     (-35.3224,  149.1396),
        'Marvel Stadium':                  (-37.8165,  144.9475),
        'Melbourne Cricket Ground':        (-37.8200,  144.9834),
        'Optus Stadium':                   (-31.9509,  115.8894),
        'Sydney Cricket Ground':           (-33.8916,  151.2246),
        'The Gabba':                       (-27.4858,  153.0381),
        # Bangladesh
        'Shere Bangla National Stadium':   ( 23.7533,   90.3863),
        # Canada
        'Maple Leaf North-West Ground':    ( 43.9267,  -79.5320),
        # England
        'Edgbaston':                       ( 52.4560,   -1.9022),
        'Emirates Riverside':              ( 54.7859,   -1.5719),
        'Headingley':                      ( 53.8178,   -1.5817),
        "Lord's Cricket Ground":           ( 51.5296,   -0.1728),
        'New Road':                        ( 52.1972,   -2.2246),
        'Old Trafford':                    ( 53.4567,   -2.2873),
        'The 1st Central County Ground':   ( 50.8370,   -0.1682),
        'The Cloud County Ground':         ( 51.7360,    0.4688),
        'The County Ground Bristol':       ( 51.4569,   -2.5828),
        'The County Ground Derby':         ( 52.9219,   -1.4809),
        'The County Ground Northampton':   ( 52.2415,   -0.9039),
        'The County Ground Taunton':       ( 51.0262,   -3.1093),
        'The Oval':                        ( 51.4840,   -0.1153),
        'The Spitfire Ground St Lawrence': ( 51.2866,    1.0738),
        'The Utilita Bowl':                ( 50.9248,   -1.3215),
        'Utilita Bowl':                    ( 50.9248,   -1.3215),
        'Trent Bridge':                    ( 52.9336,   -1.1323),
        'Uptonsteel County Ground':        ( 52.6255,   -1.1330),
        # India
        'Arun Jaitley Stadium':            ( 28.6435,   77.2014),
        'BRSABV Ekana Cricket Stadium':    ( 26.8480,   80.9462),
        'Eden Gardens':                    ( 22.5645,   88.3433),
        'M. Chinnaswamy Stadium':          ( 12.9790,   77.5996),
        'MA Chidambaram Stadium':          ( 13.0633,   80.2793),
        'Narendra Modi Stadium':           ( 23.0902,   72.5952),
        'Punjab Cricket Association Stadium': ( 30.6835, 76.7098),
        'Rajiv Gandhi International Stadium': ( 17.4062, 78.5442),
        'Sawai Mansingh Stadium':          ( 26.8973,   75.8212),
        'Wankhede Stadium':                ( 18.9388,   72.8258),
        # Ireland
        'Civil Service Cricket Club':      ( 54.6277,   -5.9346),
        'Malahide Cricket Club Ground':    ( 53.4512,   -6.1540),
        # Namibia
        'Wanderers Cricket Ground':        (-22.5597,   17.0832),
        # Nepal
        'Tribhuvan University Ground':     ( 27.6853,   85.2782),
        # Netherlands
        'VRA Ground':                      ( 52.3011,    4.8475),
        # New Zealand
        'Eden Park':                       (-36.8756,  174.7435),
        # Oman
        'Al Amerat Cricket Ground':        ( 23.5817,   58.5847),
        # Pakistan
        'Arbab Niaz Stadium':              ( 34.0050,   71.5249),
        'Bugti Stadium':                   ( 30.1798,   67.0174),
        'Gaddafi Stadium':                 ( 31.5196,   74.3366),
        'Multan Cricket Stadium':          ( 30.1575,   71.5249),
        'National Stadium':                ( 24.8922,   67.0545),
        'Rawalpindi Cricket Stadium':      ( 33.6007,   73.0679),
        # Scotland
        'The Grange Club':                 ( 55.9436,   -3.2218),
        # South Africa
        'Newlands':                        (-33.9231,   18.4113),
        'The Wanderers':                   (-26.1522,   28.0552),
        # Sri Lanka
        'R. Premadasa Stadium':            (  6.9168,   79.8674),
        # UAE
        'Dubai International Stadium':     ( 25.2048,   55.2708),
        'Sharjah Cricket Stadium':         ( 25.3511,   55.4003),
        # United States
        'Grand Prairie Stadium':           ( 32.7767,  -96.8089),
        # Wales
        'Sophia Gardens':                  ( 51.4895,   -3.1907),
        # West Indies
        'Daren Sammy National Cricket Stadium': ( 14.0723, -60.9514),
        'Kensington Oval':                 ( 13.1004,  -59.6148),
        'National Cricket Stadium Grenada':( 12.0560,  -61.7480),
        'Providence Stadium':              (  6.8007,  -58.1570),
        "Queen's Park Oval":               ( 10.6596,  -61.5197),
        'Sabina Park':                     ( 17.9988,  -76.7923),
        'Warner Park':                     ( 17.3033,  -62.7180),
        # Zimbabwe
        'Harare Sports Club':              (-17.8300,   31.0500),
        'Queens Sports Club':              (-20.1440,   28.5840),
    }
    for name, (lat, lng) in coords.items():
        existing = db.execute(
            "SELECT latitude FROM venues WHERE name=?", (name,)
        ).fetchone()
        if existing and existing['latitude'] is None:
            db.execute(
                "UPDATE venues SET latitude=?, longitude=? WHERE name=?",
                (lat, lng, name)
            )


# ── Almanack helpers ──────────────────────────────────────────────────────────

def build_almanack_filters(params, table_alias='', context='batting'):
    """
    Build WHERE-clause additions from common Almanack filter params.

    params      : dict of query params (e.g. request.args)
    table_alias : optional SQL table alias prefix (e.g. 'm' → 'm.format = ?')
    context     : 'batting' or 'bowling' — controls the innings column name
                  (batting_averages uses 'innings'; bowling_averages uses 'innings_bowled')

    Returns (where_str, params_list)
    where_str is either empty or begins with ' AND '.
    """
    alias   = (table_alias + '.') if table_alias else ''
    clauses = []
    p       = []

    if params.get('format'):
        clauses.append(f"{alias}format = ?")
        p.append(params['format'])
    if params.get('team_id'):
        clauses.append(f"{alias}team_id = ?")
        p.append(int(params['team_id']))
    if params.get('player'):
        clauses.append(f"{alias}name LIKE ?")
        p.append(f"%{params['player']}%")
    if params.get('min_innings'):
        innings_col = 'innings_bowled' if context == 'bowling' else 'innings'
        clauses.append(f"{alias}{innings_col} >= ?")
        p.append(int(params['min_innings']))
    # date_from/date_to apply when the query has a match_date column
    if params.get('date_from'):
        clauses.append(f"{alias}match_date >= ?")
        p.append(params['date_from'])
    if params.get('date_to'):
        clauses.append(f"{alias}match_date <= ?")
        p.append(params['date_to'])
    # opponent_id — for matches queries; works alongside team_id
    if params.get('opponent_id'):
        oid = int(params['opponent_id'])
        clauses.append(f"({alias}team1_id = ? OR {alias}team2_id = ?)")
        p.extend([oid, oid])
    if params.get('venue_id'):
        clauses.append(f"{alias}venue_id = ?")
        p.append(int(params['venue_id']))
    if params.get('series_id'):
        clauses.append(f"{alias}series_id = ?")
        p.append(int(params['series_id']))
    if params.get('world_id'):
        clauses.append(f"{alias}world_id = ?")
        p.append(int(params['world_id']))

    where = (' AND ' + ' AND '.join(clauses)) if clauses else ''
    return where, p


def _safe_sort(col, allowed, default):
    return col if col in allowed else default


def _batting_query(db, canon_filter, extra, p, sort_col, sort_dir, limit, offset):
    base  = f"SELECT * FROM batting_averages WHERE canon_status {canon_filter}" + extra
    total = db.execute(f"SELECT COUNT(*) as cnt FROM ({base})", p).fetchone()['cnt']
    rows  = db.execute(base + f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?",
                       p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def get_almanack_batting(db, params):
    sort_col = _safe_sort(params.get('sort', 'runs'),
                          {'runs', 'average', 'strike_rate', 'hundreds', 'fifties',
                           'matches', 'innings', 'highest_score', 'ducks', 'balls_faced'},
                          'runs')
    sort_dir = 'ASC' if params.get('dir', 'desc').lower() == 'asc' else 'DESC'
    limit    = int(params.get('limit', 50))
    offset   = int(params.get('offset', 0))
    extra, p = build_almanack_filters(params)

    # Canon matches first; fall back to all non-deleted matches
    rows, total = _batting_query(db, "= 'canon'", extra, p, sort_col, sort_dir, limit, offset)
    if rows:
        return rows, total, False

    rows, total = _batting_query(db, "!= 'deleted'", extra, p, sort_col, sort_dir, limit, offset)
    return rows, total, bool(rows)   # True = exhibition fallback


def _bowling_query(db, canon_filter, extra, p, sort_col, sort_dir, limit, offset):
    base  = f"SELECT * FROM bowling_averages WHERE wickets > 0 AND canon_status {canon_filter}" + extra
    total = db.execute(f"SELECT COUNT(*) as cnt FROM ({base})", p).fetchone()['cnt']
    rows  = db.execute(base + f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?",
                       p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def get_almanack_bowling(db, params):
    sort_col = _safe_sort(params.get('sort', 'wickets'),
                          {'wickets', 'average', 'economy', 'strike_rate', 'five_fors',
                           'matches', 'overs', 'runs_conceded', 'maidens', 'innings_bowled'},
                          'wickets')
    sort_dir = 'ASC' if params.get('dir', 'desc').lower() == 'asc' else 'DESC'
    limit    = int(params.get('limit', 50))
    offset   = int(params.get('offset', 0))
    extra, p = build_almanack_filters(params, context='bowling')

    rows, total = _bowling_query(db, "= 'canon'", extra, p, sort_col, sort_dir, limit, offset)
    if rows:
        return rows, total, False

    rows, total = _bowling_query(db, "!= 'deleted'", extra, p, sort_col, sort_dir, limit, offset)
    return rows, total, bool(rows)


def get_almanack_allrounders(db, params):
    """JOIN batting + bowling on player_id+format. Filter: innings>=3, wickets>=5."""
    sort_col = _safe_sort(params.get('sort', 'ar_index'),
                          {'ar_index', 'runs', 'wickets', 'batting_average', 'bowling_average',
                           'matches', 'innings'},
                          'ar_index')
    sort_dir = 'ASC' if params.get('dir', 'desc').lower() == 'asc' else 'DESC'
    limit    = int(params.get('limit', 50))
    offset   = int(params.get('offset', 0))

    canon_clause = "bat.canon_status = 'canon'"
    # Check if any canon data exists; if not, fall back to all non-deleted
    _test = db.execute(
        "SELECT 1 FROM batting_averages WHERE canon_status = 'canon' LIMIT 1"
    ).fetchone()
    if not _test:
        canon_clause = "bat.canon_status != 'deleted'"

    base = (
        "SELECT bat.player_id, bat.name, bat.team_name, bat.team_id, bat.format, "
        " bat.matches, bat.innings, bat.not_outs, bat.runs, bat.highest_score, "
        " bat.average AS batting_average, bat.strike_rate AS batting_sr, "
        " bat.hundreds, bat.fifties, "
        " bowl.innings_bowled, bowl.wickets, bowl.overs, bowl.runs_conceded, "
        " bowl.average AS bowling_average, bowl.economy, bowl.five_fors, "
        " ROUND(COALESCE(bat.average,0) + COALESCE(bowl.wickets,0) * 20.0, 2) AS ar_index "
        "FROM batting_averages bat "
        "JOIN bowling_averages bowl ON bat.player_id=bowl.player_id "
        "  AND bat.format=bowl.format AND bat.canon_status=bowl.canon_status "
        f"WHERE {canon_clause} AND bat.innings >= 3 AND bowl.wickets >= 5"
    )
    p = []
    if params.get('format'):
        base += " AND bat.format = ?"
        p.append(params['format'])
    if params.get('team_id'):
        base += " AND bat.team_id = ?"
        p.append(int(params['team_id']))
    if params.get('player'):
        base += " AND bat.name LIKE ?"
        p.append(f"%{params['player']}%")

    total = db.execute(f"SELECT COUNT(*) as cnt FROM ({base})", p).fetchone()['cnt']
    base += f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?"
    rows = db.execute(base, p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def get_almanack_teams(db, params):
    sort_col = _safe_sort(params.get('sort', 'win_percentage'),
                          {'matches_played', 'won', 'lost', 'drawn', 'tied',
                           'win_percentage', 'team_name'},
                          'win_percentage')
    sort_dir = 'ASC' if params.get('dir', 'desc').lower() == 'asc' else 'DESC'
    limit    = int(params.get('limit', 50))
    offset   = int(params.get('offset', 0))

    query = (
        "SELECT trv.*, "
        " ROUND(CAST(trv.won AS REAL)/NULLIF(trv.matches_played,0)*100, 1) AS win_percentage "
        "FROM team_records_view trv WHERE 1=1"
    )
    p = []
    if params.get('format'):
        query += " AND trv.format = ?"
        p.append(params['format'])

    total = db.execute(f"SELECT COUNT(*) as cnt FROM ({query})", p).fetchone()['cnt']
    query += f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?"
    rows = db.execute(query, p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def get_almanack_partnerships(db, params):
    sort_col = _safe_sort(params.get('sort', 'runs'), {'runs', 'balls'}, 'runs')
    sort_dir = 'ASC' if params.get('dir', 'desc').lower() == 'asc' else 'DESC'
    limit    = int(params.get('limit', 50))
    offset   = int(params.get('offset', 0))

    extra, p = build_almanack_filters({'format': params.get('format')} if params.get('format') else {})
    query    = "SELECT * FROM partnership_records WHERE 1=1" + extra
    total    = db.execute(f"SELECT COUNT(*) as cnt FROM ({query})", p).fetchone()['cnt']

    query += f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?"
    rows = db.execute(query, p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def get_almanack_matches(db, params):
    sort_col = _safe_sort(params.get('sort', 'match_date'),
                          {'match_date', 'format'}, 'match_date')
    sort_dir = 'ASC' if params.get('dir', 'desc').lower() == 'asc' else 'DESC'
    limit    = int(params.get('limit', 50))
    offset   = int(params.get('offset', 0))

    include_deleted = params.get('include_deleted') in ('1', 'true', True)

    query = (
        "SELECT m.id, m.match_date, m.format, m.result_type, "
        " m.margin_runs, m.margin_wickets, m.status, "
        " COALESCE(m.canon_status, 'canon') AS canon_status, "
        " m.team1_id, m.team2_id, m.venue_id, "
        " COALESCE(m.player_mode, 'ai_vs_ai') AS player_mode, "
        " m.attendance, "
        " t1.name AS team1_name, t1.short_code AS team1_code, "
        " t2.name AS team2_name, t2.short_code AS team2_code, "
        " v.name AS venue_name, v.city AS venue_city, v.capacity AS venue_capacity, "
        " wt.name AS winning_team_name, "
        " pom.name AS player_of_match_name "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "JOIN venues v ON m.venue_id = v.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "LEFT JOIN players pom ON m.player_of_match_id = pom.id "
        "WHERE m.status = 'complete'"
    )
    if not include_deleted:
        query += " AND COALESCE(m.canon_status, 'canon') != 'deleted'"
    p = []
    if params.get('format'):
        query += " AND m.format = ?"
        p.append(params['format'])
    if params.get('player_mode'):
        query += " AND COALESCE(m.player_mode, 'ai_vs_ai') = ?"
        p.append(params['player_mode'])
    if params.get('canon_status'):
        query += " AND COALESCE(m.canon_status, 'canon') = ?"
        p.append(params['canon_status'])
    if params.get('team_id'):
        tid = int(params['team_id'])
        query += " AND (m.team1_id = ? OR m.team2_id = ?)"
        p.extend([tid, tid])
    if params.get('venue_id'):
        query += " AND m.venue_id = ?"
        p.append(int(params['venue_id']))
    if params.get('date_from'):
        query += " AND m.match_date >= ?"
        p.append(params['date_from'])
    if params.get('date_to'):
        query += " AND m.match_date <= ?"
        p.append(params['date_to'])
    if params.get('series_id'):
        query += " AND m.series_id = ?"
        p.append(int(params['series_id']))
    if params.get('world_id'):
        query += " AND m.world_id = ?"
        p.append(int(params['world_id']))

    total = db.execute(f"SELECT COUNT(*) as cnt FROM ({query})", p).fetchone()['cnt']
    query += f" ORDER BY m.{sort_col} {sort_dir}, m.id DESC LIMIT ? OFFSET ?"
    rows = db.execute(query, p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def set_match_canon_status(db, match_id, new_status, actor='user', note=None):
    """Update canon_status on a match and write an audit log entry."""
    match = db.execute(
        "SELECT canon_status FROM matches WHERE id = ?", (match_id,)
    ).fetchone()
    if not match:
        return False
    old_status = match['canon_status'] or 'canon'
    db.execute(
        "UPDATE matches SET canon_status = ? WHERE id = ?",
        (new_status, match_id)
    )
    db.execute(
        "INSERT INTO almanack_audit_log "
        " (match_id, action, old_value, new_value, actor, note) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (match_id, f'set_{new_status}', old_status, new_status, actor, note)
    )
    db.commit()
    return True


def edit_match_result(db, match_id, data):
    """Edit result fields on a complete match and write audit entry."""
    match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        return False
    allowed = {'result_type', 'margin_runs', 'margin_wickets',
               'winning_team_id', 'player_of_match_id'}
    sets, vals = [], []
    for k in allowed:
        if k in data:
            sets.append(f"{k} = ?")
            vals.append(data[k])
    if sets:
        vals.append(match_id)
        db.execute(f"UPDATE matches SET {', '.join(sets)} WHERE id = ?", vals)
    old_snap = str({k: match[k] for k in allowed if k in dict(match)})
    new_snap = str({k: data[k] for k in allowed if k in data})
    db.execute(
        "INSERT INTO almanack_audit_log "
        " (match_id, action, old_value, new_value, actor, note) "
        "VALUES (?, 'edit_result', ?, ?, 'user', ?)",
        (match_id, old_snap, new_snap, data.get('note', ''))
    )
    db.commit()
    return True


def get_audit_log(db, params):
    query = (
        "SELECT al.*, m.match_date, "
        " t1.name as team1_name, t2.name as team2_name "
        "FROM almanack_audit_log al "
        "JOIN matches m ON al.match_id = m.id "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "WHERE 1=1"
    )
    p = []
    if params.get('match_id'):
        query += " AND al.match_id = ?"
        p.append(int(params['match_id']))
    query += " ORDER BY al.id DESC LIMIT 500"
    rows = db.execute(query, p).fetchall()
    return dict_from_rows(rows)


def reset_world_stats(db, world_id):
    """Mark all canon matches in a world as exhibition, clearing their stats contribution."""
    rows = db.execute(
        "SELECT id FROM matches WHERE world_id = ? AND status = 'complete' "
        "  AND COALESCE(canon_status, 'canon') = 'canon'",
        (world_id,)
    ).fetchall()
    count = 0
    for row in rows:
        db.execute(
            "UPDATE matches SET canon_status = 'exhibition' WHERE id = ?", (row['id'],)
        )
        db.execute(
            "INSERT INTO almanack_audit_log "
            " (match_id, action, old_value, new_value, actor, note) "
            "VALUES (?, 'set_exhibition', 'canon', 'exhibition', 'user', 'World stats reset')",
            (row['id'],)
        )
        count += 1
    db.commit()
    return count


def get_almanack_honours(db):
    series_rows = db.execute(
        "SELECT s.name, s.format, s.start_date, "
        " t1.name AS team1_name, t2.name AS team2_name, "
        " wt.name AS winner_name "
        "FROM series s "
        "JOIN teams t1 ON s.team1_id = t1.id "
        "JOIN teams t2 ON s.team2_id = t2.id "
        "LEFT JOIN teams wt ON s.winner_team_id = wt.id "
        "WHERE s.status = 'complete' ORDER BY s.start_date DESC"
    ).fetchall()

    tournament_rows = db.execute(
        "SELECT t.name, t.format, t.start_date, wt.name AS winner_name "
        "FROM tournaments t LEFT JOIN teams wt ON t.winner_team_id = wt.id "
        "WHERE t.status = 'complete' ORDER BY t.start_date DESC"
    ).fetchall()

    worlds = db.execute("SELECT id, name FROM worlds").fetchall()
    world_record_sections = []
    for w in worlds:
        recs = db.execute(
            "SELECT * FROM world_records WHERE world_id=? ORDER BY record_key",
            (w['id'],)
        ).fetchall()
        world_record_sections.append({
            'world': dict(w),
            'records': dict_from_rows(recs),
        })

    return {
        'series':         dict_from_rows(series_rows),
        'tournaments':    dict_from_rows(tournament_rows),
        'world_records':  world_record_sections,
    }


def get_almanack_honours_with_world_records(db):
    """
    Returns the honours board enriched with real-world record comparisons.
    Each entry includes an in-game record and the matching real-world benchmark.
    """
    real_world_recs = {
        r['record_key']: dict(r)
        for r in db.execute("SELECT * FROM real_world_records").fetchall()
    }

    # ── Batting records ───────────────────────────────────────────────────────
    BATTING_KEYS = [
        ('highest_score_test',  'Test',  'highest_score'),
        ('highest_score_odi',   'ODI',   'highest_score'),
        ('highest_score_t20',   'T20',   'highest_score'),
        ('most_runs_test',      'Test',  'most_runs'),
        ('most_runs_odi',       'ODI',   'most_runs'),
        ('most_runs_t20',       'T20',   'most_runs'),
        ('best_average_test',   'Test',  'best_average'),
        ('best_average_odi',    'ODI',   'best_average'),
        ('most_centuries_test', 'Test',  'most_centuries'),
        ('most_centuries_odi',  'ODI',   'most_centuries'),
    ]

    BOWLING_KEYS = [
        ('best_bowling_test',         'Test', 'best_bowling'),
        ('best_bowling_odi',          'ODI',  'best_bowling'),
        ('best_bowling_t20',          'T20',  'best_bowling'),
        ('most_wickets_test',         'Test', 'most_wickets'),
        ('most_wickets_odi',          'ODI',  'most_wickets'),
        ('most_wickets_t20',          'T20',  'most_wickets'),
        ('best_bowling_average_test', 'Test', 'best_bowling_average'),
        ('most_five_fors_test',       'Test', 'most_five_fors'),
    ]

    TEAM_KEYS = [
        ('highest_team_total_test', 'Test', 'highest_team_total'),
        ('highest_team_total_odi',  'ODI',  'highest_team_total'),
        ('highest_team_total_t20',  'T20',  'highest_team_total'),
        ('lowest_team_total_test',  'Test', 'lowest_team_total'),
        ('lowest_team_total_odi',   'ODI',  'lowest_team_total'),
    ]

    def _in_game_batting(fmt, record_type):
        if record_type == 'highest_score':
            for cs in ("= 'canon'", "!= 'deleted'"):
                row = db.execute(
                    "SELECT player_id, name as player_name, team_name, highest_score as value, "
                    " not_outs "
                    f"FROM batting_averages WHERE format=? AND canon_status {cs} "
                    "ORDER BY highest_score DESC LIMIT 1", (fmt,)
                ).fetchone()
                if row: return dict(row)
        elif record_type == 'most_runs':
            for cs in ("= 'canon'", "!= 'deleted'"):
                row = db.execute(
                    "SELECT player_id, name as player_name, team_name, SUM(runs) as value "
                    f"FROM batting_averages WHERE format=? AND canon_status {cs} "
                    "GROUP BY player_id, name, team_name ORDER BY value DESC LIMIT 1", (fmt,)
                ).fetchone()
                if row: return dict(row)
        elif record_type == 'best_average':
            for cs in ("= 'canon'", "!= 'deleted'"):
                row = db.execute(
                    "SELECT player_id, name as player_name, team_name, average as value "
                    f"FROM batting_averages WHERE format=? AND canon_status {cs} "
                    "AND innings >= 5 ORDER BY average DESC LIMIT 1", (fmt,)
                ).fetchone()
                if row: return dict(row)
        elif record_type == 'most_centuries':
            for cs in ("= 'canon'", "!= 'deleted'"):
                row = db.execute(
                    "SELECT player_id, name as player_name, team_name, SUM(hundreds) as value "
                    f"FROM batting_averages WHERE format=? AND canon_status {cs} "
                    "GROUP BY player_id, name, team_name ORDER BY value DESC LIMIT 1", (fmt,)
                ).fetchone()
                if row: return dict(row)
        return None

    def _in_game_bowling(fmt, record_type):
        if record_type == 'best_bowling':
            row = db.execute(
                "SELECT p.name as player_name, t.name as team_name, "
                " bwi.wickets, bwi.runs_conceded, "
                " (bwi.wickets || '/' || bwi.runs_conceded) as display_value, "
                " m.match_date, opp.name as opponent_name, v.name as venue_name "
                "FROM bowler_innings bwi "
                "JOIN innings i ON bwi.innings_id = i.id "
                "JOIN matches m ON i.match_id = m.id "
                "JOIN players p ON bwi.player_id = p.id "
                "JOIN teams t ON p.team_id = t.id "
                "JOIN teams opp ON ("
                "  CASE WHEN i.batting_team_id = t.id "
                "  THEN i.bowling_team_id ELSE i.batting_team_id END) = opp.id "
                "LEFT JOIN venues v ON m.venue_id = v.id "
                "WHERE m.format = ? AND bwi.wickets > 0 "
                "  AND COALESCE(m.canon_status,'canon') != 'deleted' "
                "ORDER BY bwi.wickets DESC, bwi.runs_conceded ASC LIMIT 1", (fmt,)
            ).fetchone()
            return dict(row) if row else None
        elif record_type == 'most_wickets':
            for cs in ("= 'canon'", "!= 'deleted'"):
                row = db.execute(
                    "SELECT player_id, name as player_name, team_name, SUM(wickets) as value "
                    f"FROM bowling_averages WHERE format=? AND canon_status {cs} "
                    "GROUP BY player_id, name, team_name ORDER BY value DESC LIMIT 1", (fmt,)
                ).fetchone()
                if row: return dict(row)
        elif record_type == 'best_bowling_average':
            for cs in ("= 'canon'", "!= 'deleted'"):
                row = db.execute(
                    "SELECT player_id, name as player_name, team_name, average as value "
                    f"FROM bowling_averages WHERE format=? AND canon_status {cs} "
                    "AND wickets >= 5 ORDER BY average ASC LIMIT 1", (fmt,)
                ).fetchone()
                if row: return dict(row)
        elif record_type == 'most_five_fors':
            for cs in ("= 'canon'", "!= 'deleted'"):
                row = db.execute(
                    "SELECT player_id, name as player_name, team_name, SUM(five_fors) as value "
                    f"FROM bowling_averages WHERE format=? AND canon_status {cs} "
                    "GROUP BY player_id, name, team_name ORDER BY value DESC LIMIT 1", (fmt,)
                ).fetchone()
                if row: return dict(row)
        return None

    def _in_game_team(fmt, record_type):
        order = 'DESC' if record_type == 'highest_team_total' else 'ASC'
        row = db.execute(
            "SELECT i.total_runs as value, i.total_wickets as wickets, "
            " t.name as team_name, opp.name as opponent_name, "
            " v.name as venue_name, m.match_date "
            "FROM innings i JOIN matches m ON i.match_id=m.id "
            "JOIN teams t ON i.batting_team_id=t.id "
            "JOIN teams opp ON (CASE WHEN i.batting_team_id=m.team1_id "
            "  THEN m.team2_id ELSE m.team1_id END)=opp.id "
            "LEFT JOIN venues v ON m.venue_id=v.id "
            f"WHERE m.format=? AND m.status='complete' AND i.total_runs > 0 "
            "  AND COALESCE(m.canon_status,'canon') != 'deleted' "
            f"ORDER BY i.total_runs {order} LIMIT 1", (fmt,)
        ).fetchone()
        return dict(row) if row else None

    def _enrich(key, in_game, in_game_num_value=None):
        rw = real_world_recs.get(key)
        if not rw:
            return None
        rw_num = rw.get('value_runs') or rw.get('value_wickets') or rw.get('value_decimal')
        ig_num  = in_game_num_value or (in_game.get('value') if in_game else None)
        pct = None
        if ig_num and rw_num and rw_num != 0:
            pct = round(float(ig_num) / float(rw_num) * 100, 1)
        return {
            'key':                key,
            'in_game':            in_game,
            'real_world':         rw,
            'pct_of_world_record': pct,
        }

    batting_out, bowling_out, team_out = [], [], []

    for key, fmt, rt in BATTING_KEYS:
        ig = _in_game_batting(fmt, rt)
        entry = _enrich(key, ig)
        if entry:
            batting_out.append(entry)

    for key, fmt, rt in BOWLING_KEYS:
        ig = _in_game_bowling(fmt, rt)
        entry = _enrich(key, ig,
                        in_game_num_value=ig.get('wickets') if ig and rt == 'best_bowling' else None)
        if entry:
            bowling_out.append(entry)

    for key, fmt, rt in TEAM_KEYS:
        ig = _in_game_team(fmt, rt)
        entry = _enrich(key, ig)
        if entry:
            team_out.append(entry)

    return {'batting': batting_out, 'bowling': bowling_out, 'teams': team_out}


def get_almanack_search(db, q):
    """Search players, teams and matches. Returns list of {type, id, name, context}."""
    if not q or len(q.strip()) < 2:
        return []
    like = f'%{q.strip()}%'
    results = []

    players = db.execute(
        "SELECT p.id, p.name, t.name AS team_name "
        "FROM players p JOIN teams t ON p.team_id=t.id "
        "WHERE p.name LIKE ? LIMIT 10",
        (like,)
    ).fetchall()
    for r in players:
        results.append({'type': 'player', 'id': r['id'],
                        'name': r['name'], 'context': r['team_name']})

    teams = db.execute(
        "SELECT id, name, short_code FROM teams WHERE name LIKE ? LIMIT 5",
        (like,)
    ).fetchall()
    for r in teams:
        results.append({'type': 'team', 'id': r['id'],
                        'name': r['name'], 'context': r['short_code'] or ''})

    matches = db.execute(
        "SELECT m.id, m.match_date, m.format, "
        " t1.name AS team1_name, t2.name AS team2_name "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id=t1.id "
        "JOIN teams t2 ON m.team2_id=t2.id "
        "WHERE m.status='complete' "
        " AND (t1.name LIKE ? OR t2.name LIKE ? OR m.match_date LIKE ?) "
        "ORDER BY m.match_date DESC LIMIT 10",
        (like, like, like)
    ).fetchall()
    for r in matches:
        results.append({'type': 'match', 'id': r['id'],
                        'name': f"{r['team1_name']} vs {r['team2_name']}",
                        'context': f"{r['format']} • {r['match_date']}"})

    return results


# ── Almanack records ──────────────────────────────────────────────────────────

def get_almanack_batting_record(db, format_, record_type='highest_score'):
    for cs in ("= 'canon'", "!= 'deleted'"):
        if record_type == 'highest_score':
            row = db.execute(
                "SELECT player_id, name, team_name, highest_score as value "
                f"FROM batting_averages WHERE format=? AND canon_status {cs} "
                "ORDER BY highest_score DESC LIMIT 1",
                (format_,)
            ).fetchone()
        elif record_type == 'highest_average':
            row = db.execute(
                "SELECT player_id, name, team_name, average as value "
                f"FROM batting_averages WHERE format=? AND canon_status {cs} "
                "AND innings >= 5 ORDER BY average DESC LIMIT 1",
                (format_,)
            ).fetchone()
        else:
            return None
        if row:
            return dict_from_row(row)
    return None


def get_almanack_bowling_record(db, format_, record_type='best_figures'):
    if record_type == 'best_figures':
        # Best = most wickets, then fewest runs
        row = db.execute(
            "SELECT bwi.id, p.name, t.name as team_name, "
            " bwi.wickets, bwi.runs_conceded "
            "FROM bowler_innings bwi "
            "JOIN innings i ON bwi.innings_id = i.id "
            "JOIN matches m ON i.match_id = m.id "
            "JOIN players p ON bwi.player_id = p.id "
            "JOIN teams t ON p.team_id = t.id "
            "WHERE m.format = ? AND bwi.wickets > 0 "
            "ORDER BY bwi.wickets DESC, bwi.runs_conceded ASC LIMIT 1",
            (format_,)
        ).fetchone()
    else:
        return None
    return dict_from_row(row)


# ── Venue stats ───────────────────────────────────────────────────────────────

def get_venue_stats(db, venue_id):
    match_count = db.execute(
        "SELECT COUNT(*) as cnt FROM matches WHERE venue_id=? AND status='complete'",
        (venue_id,)
    ).fetchone()['cnt']

    highest = db.execute(
        "SELECT i.total_runs, i.total_wickets, i.declared, "
        " t.name as team_name, m.match_date "
        "FROM innings i JOIN matches m ON i.match_id=m.id "
        "JOIN teams t ON i.batting_team_id=t.id "
        "WHERE m.venue_id=? AND m.status='complete' "
        "ORDER BY i.total_runs DESC LIMIT 1",
        (venue_id,)
    ).fetchone()

    top_score = db.execute(
        "SELECT p.name as player_name, t.name as team_name, bi.runs, m.match_date "
        "FROM batter_innings bi "
        "JOIN innings i ON bi.innings_id=i.id "
        "JOIN matches m ON i.match_id=m.id "
        "JOIN players p ON bi.player_id=p.id "
        "JOIN teams t ON p.team_id=t.id "
        "WHERE m.venue_id=? AND m.status='complete' "
        "ORDER BY bi.runs DESC LIMIT 1",
        (venue_id,)
    ).fetchone()

    best_bowling = db.execute(
        "SELECT p.name as player_name, t.name as team_name, "
        " bwi.wickets, bwi.runs_conceded, m.match_date "
        "FROM bowler_innings bwi "
        "JOIN innings i ON bwi.innings_id=i.id "
        "JOIN matches m ON i.match_id=m.id "
        "JOIN players p ON bwi.player_id=p.id "
        "JOIN teams t ON p.team_id=t.id "
        "WHERE m.venue_id=? AND m.status='complete' AND bwi.wickets > 0 "
        "ORDER BY bwi.wickets DESC, bwi.runs_conceded ASC LIMIT 1",
        (venue_id,)
    ).fetchone()

    return {
        'match_count': match_count,
        'highest_team_score': dict_from_row(highest),
        'highest_individual_score': dict_from_row(top_score),
        'best_bowling': dict_from_row(best_bowling),
    }


# ── Player profile helpers ────────────────────────────────────────────────────

def get_player_profile(db, player_id):
    player = get_player(db, player_id)
    if not player:
        return None

    bat_rows = db.execute(
        "SELECT player_id, name, team_name, team_id, format, "
        " SUM(matches) as matches, SUM(innings) as innings, SUM(not_outs) as not_outs, "
        " SUM(runs) as runs, MAX(highest_score) as highest_score, "
        " ROUND(CAST(SUM(runs) AS REAL) / NULLIF(SUM(innings)-SUM(not_outs),0),2) as average, "
        " ROUND(CAST(SUM(runs) AS REAL) / NULLIF(SUM(balls_faced),0)*100,2) as strike_rate, "
        " SUM(hundreds) as hundreds, SUM(fifties) as fifties, SUM(ducks) as ducks, "
        " SUM(fours) as fours, SUM(sixes) as sixes, SUM(balls_faced) as balls_faced "
        "FROM batting_averages WHERE player_id = ? AND canon_status != 'deleted' "
        "GROUP BY player_id, name, team_name, team_id, format ORDER BY format",
        (player_id,)
    ).fetchall()

    bowl_rows = db.execute(
        "SELECT player_id, name, bowling_type, team_name, team_id, format, "
        " SUM(matches) as matches, SUM(innings_bowled) as innings_bowled, "
        " SUM(overs) as overs, SUM(maidens) as maidens, "
        " SUM(runs_conceded) as runs_conceded, SUM(wickets) as wickets, "
        " ROUND(CAST(SUM(runs_conceded) AS REAL)/NULLIF(SUM(wickets),0),2) as average, "
        " ROUND(CAST(SUM(runs_conceded) AS REAL)/NULLIF(SUM(overs),0),2) as economy, "
        " ROUND(CAST(SUM(overs)*6 AS REAL)/NULLIF(SUM(wickets),0),2) as strike_rate, "
        " SUM(five_fors) as five_fors "
        "FROM bowling_averages WHERE player_id = ? AND canon_status != 'deleted' "
        "GROUP BY player_id, name, bowling_type, team_name, team_id, format ORDER BY format",
        (player_id,)
    ).fetchall()

    recent_innings = db.execute(
        "SELECT bi.runs, bi.balls_faced, bi.fours, bi.sixes, bi.dismissal_type, bi.not_out, "
        " bi.batting_position, "
        " m.match_date, m.format, m.id as match_id, "
        " opp.name as opponent_name, v.name as venue_name, "
        " bowl.name as bowler_name "
        "FROM batter_innings bi "
        "JOIN innings i ON bi.innings_id = i.id "
        "JOIN matches m ON i.match_id = m.id "
        "JOIN venues v ON m.venue_id = v.id "
        "JOIN teams opp ON (CASE WHEN i.batting_team_id = m.team1_id THEN m.team2_id ELSE m.team1_id END) = opp.id "
        "LEFT JOIN players bowl ON bi.bowler_id = bowl.id "
        "WHERE bi.player_id = ? AND (bi.status = 'dismissed' OR bi.not_out = 1) "
        "ORDER BY m.match_date DESC, bi.id DESC LIMIT 10",
        (player_id,)
    ).fetchall()

    mil_bat = db.execute(
        "SELECT SUM(runs) as total_runs, SUM(matches) as total_matches, "
        " SUM(innings) as total_innings, SUM(hundreds) as hundreds, "
        " SUM(fifties) as fifties, SUM(ducks) as ducks "
        "FROM batting_averages WHERE player_id = ? AND canon_status != 'deleted'",
        (player_id,)
    ).fetchone()

    mil_bowl = db.execute(
        "SELECT SUM(wickets) as total_wickets, SUM(five_fors) as five_fors "
        "FROM bowling_averages WHERE player_id = ? AND canon_status != 'deleted'",
        (player_id,)
    ).fetchone()

    mil = dict_from_row(mil_bat) or {}
    mb  = dict_from_row(mil_bowl) or {}
    mil['total_wickets'] = mb.get('total_wickets') or 0
    mil['five_fors']     = mb.get('five_fors') or 0

    return {
        'player':         player,
        'batting':        dict_from_rows(bat_rows),
        'bowling':        dict_from_rows(bowl_rows),
        'recent_innings': dict_from_rows(recent_innings),
        'milestones':     mil,
    }


def get_player_innings_list(db, player_id, params):
    limit  = int(params.get('limit', 50))
    offset = int(params.get('offset', 0))
    fmt    = params.get('format')

    query = (
        "SELECT bi.id, bi.runs, bi.balls_faced, bi.fours, bi.sixes, "
        " bi.dismissal_type, bi.not_out, bi.batting_position, "
        " CASE WHEN bi.balls_faced > 0 "
        "  THEN ROUND(CAST(bi.runs AS REAL)/bi.balls_faced*100,1) ELSE 0 END as strike_rate, "
        " m.match_date, m.format, m.id as match_id, "
        " opp.name as opponent_name, opp.id as opponent_id, "
        " v.name as venue_name, "
        " bowl.name as bowler_name "
        "FROM batter_innings bi "
        "JOIN innings i ON bi.innings_id = i.id "
        "JOIN matches m ON i.match_id = m.id "
        "JOIN venues v ON m.venue_id = v.id "
        "JOIN teams opp ON (CASE WHEN i.batting_team_id = m.team1_id "
        "  THEN m.team2_id ELSE m.team1_id END) = opp.id "
        "LEFT JOIN players bowl ON bi.bowler_id = bowl.id "
        "WHERE bi.player_id = ? AND (bi.status = 'dismissed' OR bi.not_out = 1)"
    )
    p = [player_id]
    if fmt:
        query += " AND m.format = ?"
        p.append(fmt)

    total = db.execute(f"SELECT COUNT(*) as cnt FROM ({query})", p).fetchone()['cnt']
    query += " ORDER BY m.match_date DESC, bi.id DESC LIMIT ? OFFSET ?"
    rows   = db.execute(query, p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def get_player_bowling_list(db, player_id, params):
    limit  = int(params.get('limit', 50))
    offset = int(params.get('offset', 0))
    fmt    = params.get('format')

    query = (
        "SELECT bwi.id, bwi.overs, bwi.balls, bwi.maidens, "
        " bwi.runs_conceded, bwi.wickets, bwi.wides, bwi.no_balls, "
        " CASE WHEN bwi.overs > 0 "
        "  THEN ROUND(CAST(bwi.runs_conceded AS REAL)/bwi.overs,2) ELSE 0 END as economy, "
        " m.match_date, m.format, m.id as match_id, "
        " opp.name as opponent_name, opp.id as opponent_id, "
        " v.name as venue_name "
        "FROM bowler_innings bwi "
        "JOIN innings i ON bwi.innings_id = i.id "
        "JOIN matches m ON i.match_id = m.id "
        "JOIN venues v ON m.venue_id = v.id "
        "JOIN teams opp ON (CASE WHEN i.bowling_team_id = m.team1_id "
        "  THEN m.team2_id ELSE m.team1_id END) = opp.id "
        "WHERE bwi.player_id = ? AND bwi.overs > 0"
    )
    p = [player_id]
    if fmt:
        query += " AND m.format = ?"
        p.append(fmt)

    total = db.execute(f"SELECT COUNT(*) as cnt FROM ({query})", p).fetchone()['cnt']
    query += " ORDER BY m.match_date DESC, bwi.id DESC LIMIT ? OFFSET ?"
    rows   = db.execute(query, p + [limit, offset]).fetchall()
    return dict_from_rows(rows), total


def get_player_wagon_wheel(db, player_id, format_filter=None):
    query = (
        "SELECT d.shot_angle, d.runs_scored, d.outcome_type "
        "FROM deliveries d "
        "JOIN innings i ON d.innings_id = i.id "
        "JOIN matches m ON i.match_id = m.id "
        "WHERE d.striker_id = ? AND d.shot_angle IS NOT NULL AND d.is_wide = 0"
    )
    p = [player_id]
    if format_filter:
        query += " AND m.format = ?"
        p.append(format_filter)
    rows = db.execute(query, p).fetchall()
    return dict_from_rows(rows)


# ── Team profile ──────────────────────────────────────────────────────────────

def get_team_profile(db, team_id):
    team = get_team(db, team_id)
    if not team:
        return None

    players = get_players_for_team(db, team_id)

    format_records = db.execute(
        "SELECT *, ROUND(CAST(won AS REAL)/NULLIF(matches_played,0)*100,1) as win_pct "
        "FROM team_records_view WHERE team_id = ? ORDER BY format",
        (team_id,)
    ).fetchall()

    recent_matches = db.execute(
        "SELECT m.id, m.match_date, m.format, m.result_type, "
        " m.margin_runs, m.margin_wickets, "
        " COALESCE(m.player_mode, 'ai_vs_ai') as player_mode, "
        " COALESCE(m.canon_status, 'canon') as canon_status, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " v.name as venue_name, "
        " wt.name as winning_team_name, wt.id as winning_team_id "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "JOIN venues v ON m.venue_id = v.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE m.status = 'complete' AND (m.team1_id = ? OR m.team2_id = ?) "
        "  AND COALESCE(m.canon_status, 'canon') != 'deleted' "
        "ORDER BY m.match_date DESC, m.id DESC LIMIT 10",
        (team_id, team_id)
    ).fetchall()

    top_scorers = db.execute(
        "SELECT player_id, name, SUM(runs) as runs, SUM(matches) as matches, "
        " SUM(innings) as innings, SUM(hundreds) as hundreds, SUM(fifties) as fifties "
        "FROM batting_averages WHERE team_id = ? AND canon_status != 'deleted' "
        "GROUP BY player_id, name ORDER BY runs DESC LIMIT 5",
        (team_id,)
    ).fetchall()

    top_bowlers = db.execute(
        "SELECT player_id, name, SUM(wickets) as wickets, SUM(matches) as matches, "
        " SUM(innings_bowled) as innings_bowled, SUM(five_fors) as five_fors "
        "FROM bowling_averages WHERE team_id = ? AND canon_status != 'deleted' "
        "GROUP BY player_id, name ORDER BY wickets DESC LIMIT 5",
        (team_id,)
    ).fetchall()

    highest_score = db.execute(
        "SELECT i.total_runs, i.total_wickets, i.declared, m.match_date, m.format, "
        " opp.name as opponent_name, v.name as venue_name "
        "FROM innings i JOIN matches m ON i.match_id = m.id "
        "JOIN venues v ON m.venue_id = v.id "
        "JOIN teams opp ON (CASE WHEN i.batting_team_id = m.team1_id "
        "  THEN m.team2_id ELSE m.team1_id END) = opp.id "
        "WHERE i.batting_team_id = ? AND m.status = 'complete' "
        "ORDER BY i.total_runs DESC LIMIT 1",
        (team_id,)
    ).fetchone()

    lowest_score = db.execute(
        "SELECT i.total_runs, i.total_wickets, i.declared, m.match_date, m.format, "
        " opp.name as opponent_name, v.name as venue_name "
        "FROM innings i JOIN matches m ON i.match_id = m.id "
        "JOIN venues v ON m.venue_id = v.id "
        "JOIN teams opp ON (CASE WHEN i.batting_team_id = m.team1_id "
        "  THEN m.team2_id ELSE m.team1_id END) = opp.id "
        "WHERE i.batting_team_id = ? AND m.status = 'complete' AND i.total_wickets >= 10 "
        "ORDER BY i.total_runs ASC LIMIT 1",
        (team_id,)
    ).fetchone()

    squad_stats = db.execute(
        "SELECT p.id as player_id, p.name, p.batting_position, "
        " p.batting_rating, p.bowling_rating, p.bowling_type, "
        " COALESCE(SUM(bat.runs), 0) as total_runs, "
        " COALESCE(SUM(bat.matches), 0) as bat_matches, "
        " COALESCE(SUM(bat.innings), 0) as bat_innings, "
        " COALESCE(SUM(bat.hundreds), 0) as hundreds, "
        " COALESCE(SUM(bat.fifties), 0) as fifties, "
        " COALESCE(SUM(bowl.wickets), 0) as total_wickets "
        "FROM players p "
        "LEFT JOIN batting_averages bat ON bat.player_id = p.id "
        "  AND bat.canon_status != 'deleted' "
        "LEFT JOIN bowling_averages bowl ON bowl.player_id = p.id "
        "  AND bowl.canon_status != 'deleted' "
        "WHERE p.team_id = ? "
        "GROUP BY p.id ORDER BY p.batting_position",
        (team_id,)
    ).fetchall()

    return {
        'team':           team,
        'players':        players,
        'format_records': dict_from_rows(format_records),
        'recent_matches': dict_from_rows(recent_matches),
        'top_scorers':    dict_from_rows(top_scorers),
        'top_bowlers':    dict_from_rows(top_bowlers),
        'highest_score':  dict_from_row(highest_score),
        'lowest_score':   dict_from_row(lowest_score),
        'squad_stats':    dict_from_rows(squad_stats),
    }


# ── Venue profile ─────────────────────────────────────────────────────────────

def get_venue_profile(db, venue_id):
    venue = get_venue(db, venue_id)
    if not venue:
        return None

    stats = get_venue_stats(db, venue_id)

    avg_first = db.execute(
        "SELECT m.format, ROUND(AVG(i.total_runs),1) as avg_runs, COUNT(*) as matches "
        "FROM innings i JOIN matches m ON i.match_id = m.id "
        "WHERE m.venue_id = ? AND m.status = 'complete' AND i.innings_number = 1 "
        "GROUP BY m.format ORDER BY m.format",
        (venue_id,)
    ).fetchall()

    team_counts = db.execute(
        "SELECT t.id as team_id, t.name as team_name, t.badge_colour, COUNT(*) as matches "
        "FROM matches m "
        "JOIN teams t ON (m.team1_id = t.id OR m.team2_id = t.id) "
        "WHERE m.venue_id = ? AND m.status = 'complete' "
        "GROUP BY t.id ORDER BY matches DESC LIMIT 5",
        (venue_id,)
    ).fetchall()

    lowest_innings = db.execute(
        "SELECT i.total_runs, i.total_wickets, "
        " t.name as team_name, m.match_date, m.format "
        "FROM innings i JOIN matches m ON i.match_id = m.id "
        "JOIN teams t ON i.batting_team_id = t.id "
        "WHERE m.venue_id = ? AND m.status = 'complete' AND i.total_wickets >= 10 "
        "ORDER BY i.total_runs ASC LIMIT 1",
        (venue_id,)
    ).fetchone()

    recent_matches = db.execute(
        "SELECT m.id, m.match_date, m.format, m.result_type, m.attendance, "
        " COALESCE(m.player_mode, 'ai_vs_ai') as player_mode, "
        " COALESCE(m.canon_status, 'canon') as canon_status, "
        " t1.name as team1_name, t1.short_code as team1_code, t1.badge_colour as team1_colour, "
        " t2.name as team2_name, t2.short_code as team2_code, t2.badge_colour as team2_colour, "
        " wt.name as winning_team_name "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE m.venue_id = ? AND m.status = 'complete' "
        "  AND COALESCE(m.canon_status, 'canon') != 'deleted' "
        "ORDER BY m.match_date DESC LIMIT 10",
        (venue_id,)
    ).fetchall()

    # Attendance aggregates
    att_stats = db.execute(
        "SELECT AVG(attendance) as avg_att, MAX(attendance) as max_att "
        "FROM matches WHERE venue_id=? AND status='complete' AND attendance IS NOT NULL",
        (venue_id,)
    ).fetchone()
    if att_stats:
        stats['avg_attendance'] = att_stats['avg_att']
        stats['max_attendance'] = att_stats['max_att']

    stats['avg_first_innings'] = dict_from_rows(avg_first)
    stats['team_counts']       = dict_from_rows(team_counts)
    stats['lowest_innings']    = dict_from_row(lowest_innings)

    return {
        'venue':          venue,
        'stats':          stats,
        'recent_matches': dict_from_rows(recent_matches),
    }


# ── Head to head ──────────────────────────────────────────────────────────────

def get_head_to_head(db, team1_id, team2_id):
    rows = db.execute(
        "SELECT m.id, m.match_date, m.format, m.result_type, "
        " m.margin_runs, m.margin_wickets, "
        " t1.name as team1_name, t2.name as team2_name, "
        " wt.name as winning_team_name, wt.id as winning_team_id, "
        " v.name as venue_name "
        "FROM matches m "
        "JOIN teams t1 ON m.team1_id = t1.id "
        "JOIN teams t2 ON m.team2_id = t2.id "
        "JOIN venues v ON m.venue_id = v.id "
        "LEFT JOIN teams wt ON m.winning_team_id = wt.id "
        "WHERE m.status = 'complete' "
        " AND ((m.team1_id=? AND m.team2_id=?) OR (m.team1_id=? AND m.team2_id=?)) "
        "ORDER BY m.match_date DESC",
        (team1_id, team2_id, team2_id, team1_id)
    ).fetchall()
    return dict_from_rows(rows)


# ── Match State ───────────────────────────────────────────────────────────────

def get_match_state(db, match_id):
    """
    Build a comprehensive match state dict from the DB.
    Reconstructs current striker, bowler, over/ball counts from deliveries.
    Returns None if match not found.
    """
    match = get_match(db, match_id)
    if not match:
        return None

    all_innings = get_innings(db, match_id)
    fmt = match['format']
    max_overs_map = {'T20': 20, 'ODI': 50, 'Test': None, 'Hundred': 20}
    max_overs = max_overs_map.get(fmt)

    current_innings = next((i for i in all_innings if i['status'] == 'in_progress'), None)

    if not current_innings:
        return {
            'match':                  match,
            'innings':                all_innings,
            'current_innings':        None,
            'current_innings_id':     None,
            'batting_team_players':   [],
            'bowling_team_players':   [],
            'batter_innings':         [],
            'bowler_innings':         [],
            'current_striker_id':     None,
            'current_non_striker_id': None,
            'current_bowler_id':      None,
            'last_bowler_id':         None,
            'partnerships':           [],
            'fall_of_wickets':        [],
            'over_number':            0,
            'ball_in_over':           0,
            'current_over_deliveries': [],
            'is_free_hit':            False,
            'format':                 fmt,
            'max_overs':              max_overs,
            'target':                 None,
        }

    innings_id = current_innings['id']
    batting_team_id  = current_innings['batting_team_id']
    bowling_team_id  = current_innings['bowling_team_id']

    batting_team_players = get_players_for_team(db, batting_team_id)
    bowling_team_players = get_players_for_team(db, bowling_team_id)
    batter_innings_list  = get_batter_innings(db, innings_id)
    bowler_innings_list  = get_bowler_innings(db, innings_id)
    partnerships         = get_all_partnerships(db, innings_id)
    fow                  = get_fall_of_wickets(db, innings_id)

    # Count legal deliveries to compute over/ball state
    total_legal = db.execute(
        "SELECT COUNT(*) AS c FROM deliveries "
        "WHERE innings_id=? AND is_wide=0 AND is_no_ball=0",
        (innings_id,)
    ).fetchone()['c']

    over_number  = total_legal // 6
    ball_in_over = total_legal % 6

    # Current over deliveries (for ball-by-ball display)
    cur_over_rows = db.execute(
        "SELECT outcome_type, runs_scored, is_wide, is_no_ball "
        "FROM deliveries WHERE innings_id=? AND over_number=? ORDER BY id",
        (innings_id, over_number)
    ).fetchall()
    current_over_deliveries = [dict(r) for r in cur_over_rows]

    # Last delivery for state reconstruction
    last_del = db.execute(
        "SELECT * FROM deliveries WHERE innings_id=? ORDER BY id DESC LIMIT 1",
        (innings_id,)
    ).fetchone()
    last_del = dict(last_del) if last_del else None

    is_free_hit      = bool(last_del and last_del['is_no_ball'])
    current_bowler_id = None
    last_bowler_id    = None

    if last_del:
        is_legal_last = not bool(last_del['is_wide']) and not bool(last_del['is_no_ball'])
        if ball_in_over > 0:
            # Mid-over: last delivery's bowler is still bowling
            current_bowler_id = last_del['bowler_id']
            # Find who bowled the previous completed over
            prev_del = db.execute(
                "SELECT bowler_id FROM deliveries "
                "WHERE innings_id=? AND over_number=? AND is_wide=0 AND is_no_ball=0 "
                "ORDER BY id DESC LIMIT 1",
                (innings_id, over_number - 1)
            ).fetchone()
            last_bowler_id = prev_del['bowler_id'] if prev_del else None
        else:
            # ball_in_over == 0 and total_legal > 0 means we just completed an over
            last_bowler_id = last_del['bowler_id']
            current_bowler_id = None

    # Reconstruct current striker / non-striker from last delivery
    if not last_del:
        # Start of innings: first two 'batting' batters by position
        batting_now = sorted(
            [b for b in batter_innings_list if b['status'] == 'batting'],
            key=lambda x: x['batting_position'] or 99
        )
        current_striker_id     = batting_now[0]['player_id'] if len(batting_now) > 0 else None
        current_non_striker_id = batting_now[1]['player_id'] if len(batting_now) > 1 else None
    else:
        s  = last_del['striker_id']
        ns = last_del['non_striker_id']
        runs_on_last = last_del['runs_scored']
        is_legal_last = not bool(last_del['is_wide']) and not bool(last_del['is_no_ball'])
        was_wicket = last_del['outcome_type'] == 'wicket'

        # Step 1: run-based swap (odd runs on legal non-wicket delivery)
        if is_legal_last and not was_wicket and runs_on_last % 2 == 1:
            s, ns = ns, s

        # Step 2: wicket — new batter comes in at striker end
        if was_wicket:
            batting_now = [b for b in batter_innings_list if b['status'] == 'batting']
            new_b = next((b['player_id'] for b in batting_now if b['player_id'] != ns), None)
            s = new_b

        # Step 3: end-of-over swap (total_legal > 0 and ball_in_over just became 0)
        elif is_legal_last and total_legal > 0 and ball_in_over == 0:
            s, ns = ns, s

        # Step 4: sanity-check against batter_innings.
        # simulate_to updates batter status (dismissals/new batters) without writing
        # delivery rows, so last_del can be stale. If the computed striker is no longer
        # active (dismissed by a prior simulate_to call), fall back to batter_innings.
        batting_set = {b['player_id'] for b in batter_innings_list if b['status'] == 'batting'}
        if s not in batting_set or ns not in batting_set:
            batting_now = sorted(
                [b for b in batter_innings_list if b['status'] == 'batting'],
                key=lambda x: x['batting_position'] or 99
            )
            # Preserve whichever end is still valid; replace only the stale one
            if s not in batting_set and ns not in batting_set:
                s  = batting_now[0]['player_id'] if len(batting_now) > 0 else None
                ns = batting_now[1]['player_id'] if len(batting_now) > 1 else None
            elif s not in batting_set:
                s = next((b['player_id'] for b in batting_now if b['player_id'] != ns), None)
            else:
                ns = next((b['player_id'] for b in batting_now if b['player_id'] != s), None)

        current_striker_id     = s
        current_non_striker_id = ns

    # Calculate target for second / third / fourth innings
    target = None
    innings_num = current_innings['innings_number']
    if innings_num > 1:
        if fmt in ('ODI', 'T20'):
            first = next((i for i in all_innings if i['innings_number'] == 1), None)
            if first:
                target = first['total_runs'] + 1
        else:  # Test
            if innings_num == 2:
                first = next((i for i in all_innings if i['innings_number'] == 1), None)
                target = (first['total_runs'] + 1) if first else None
            elif innings_num == 4:
                i1 = next((i for i in all_innings if i['innings_number'] == 1), None)
                i2 = next((i for i in all_innings if i['innings_number'] == 2), None)
                i3 = next((i for i in all_innings if i['innings_number'] == 3), None)
                if i1 and i2 and i3:
                    target = i1['total_runs'] + i3['total_runs'] - i2['total_runs'] + 1

    return {
        'match':                  match,
        'innings':                all_innings,
        'current_innings':        current_innings,
        'current_innings_id':     innings_id,
        'batting_team_players':   batting_team_players,
        'bowling_team_players':   bowling_team_players,
        'batter_innings':         batter_innings_list,
        'bowler_innings':         bowler_innings_list,
        'current_striker_id':     current_striker_id,
        'current_non_striker_id': current_non_striker_id,
        'current_bowler_id':      current_bowler_id,
        'last_bowler_id':         last_bowler_id,
        'partnerships':           partnerships,
        'fall_of_wickets':        fow,
        'over_number':            over_number,
        'ball_in_over':           ball_in_over,
        'current_over_deliveries': current_over_deliveries,
        'is_free_hit':            is_free_hit,
        'format':                 fmt,
        'max_overs':              max_overs,
        'target':                 target,
    }


# ── Draw Outcomes ─────────────────────────────────────────────────────────────

def save_draw_outcome(db, world_id, competition_key, season_key, draw_type, outcome_json_str):
    """Persist a draw outcome for a competition season. Idempotent (upsert)."""
    db.execute(
        "INSERT INTO draw_outcomes (world_id, competition_key, season_key, draw_type, outcome_json) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(world_id, competition_key, season_key) "
        "DO UPDATE SET draw_type=excluded.draw_type, outcome_json=excluded.outcome_json, "
        "  created_at=datetime('now')",
        (world_id, competition_key, season_key, draw_type, outcome_json_str),
    )
    db.commit()


def get_draw_outcome(db, world_id, competition_key, season_key):
    """Return a single draw outcome dict or None."""
    row = db.execute(
        "SELECT * FROM draw_outcomes WHERE world_id=? AND competition_key=? AND season_key=?",
        (world_id, competition_key, season_key),
    ).fetchone()
    return dict(row) if row else None


def get_world_draw_outcomes(db, world_id):
    """Return all draw outcomes for a world, ordered by season_key."""
    rows = db.execute(
        "SELECT * FROM draw_outcomes WHERE world_id=? ORDER BY season_key",
        (world_id,),
    ).fetchall()
    return [dict(r) for r in rows]
