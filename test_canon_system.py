"""
test_canon_system.py — Comprehensive tests for the Almanack Canon System.

Tests:
  A. Database functions (set_match_canon_status, edit_match_result,
     get_audit_log, reset_world_stats)
  B. API endpoints (Flask test client — all 7 new canon endpoints)
  C. SQL view filtering (batting_averages, bowling_averages, team_records_view,
     partnership_records exclude exhibition/deleted)
  D. Edge cases (invalid inputs, missing matches, empty lists, concurrent updates)
  E. Default canon_status logic in /api/matches/start
  F. Almanack match listing filters (include_deleted, canon_status param)
"""

import sys
import os
import json
import sqlite3
import unittest

# ── path setup ────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SCHEMA_PATH = os.path.join(HERE, 'schema.sql')

import database
import app as flask_app


# ── In-memory DB helpers ──────────────────────────────────────────────────────

def make_test_db():
    """Create a fresh in-memory SQLite DB with schema + migrations applied."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    database.run_migrations(conn)
    return conn


def _seed(db):
    """
    Insert two teams (6 players each), one venue, one world, and return IDs.
    Players alternate pace/spin/none bowling types.
    """
    bowling_types = ['pace', 'pace', 'spin', 'spin', 'pace', 'none']

    venue_id = db.execute(
        "INSERT INTO venues (name, city, country) VALUES ('Test Ground','Testville','Testland')"
    ).lastrowid

    world_id = db.execute(
        "INSERT INTO worlds (name, created_date, current_date) VALUES ('Test World','2024-01-01','2024-01-01')"
    ).lastrowid

    team1_id = db.execute(
        "INSERT INTO teams (name, short_code) VALUES ('Alpha XI','ALP')"
    ).lastrowid
    team2_id = db.execute(
        "INSERT INTO teams (name, short_code) VALUES ('Beta XI','BET')"
    ).lastrowid

    for i in range(1, 7):
        bt = bowling_types[i - 1]
        br = 3 if bt != 'none' else 0
        db.execute(
            "INSERT INTO players (team_id, name, batting_position, batting_rating, "
            "batting_hand, bowling_type, bowling_rating) VALUES (?,?,?,?,?,?,?)",
            (team1_id, f'Alpha Player {i}', i, 3, 'right', bt, br)
        )
        db.execute(
            "INSERT INTO players (team_id, name, batting_position, batting_rating, "
            "batting_hand, bowling_type, bowling_rating) VALUES (?,?,?,?,?,?,?)",
            (team2_id, f'Beta Player {i}', i, 3, 'right', bt, br)
        )

    db.commit()
    return team1_id, team2_id, venue_id, world_id


def _insert_complete_match(db, team1_id, team2_id, venue_id, world_id=None,
                            canon_status='canon'):
    """Insert a minimal complete match with batter/bowler data for view tests."""
    match_id = db.execute(
        "INSERT INTO matches (format, venue_id, match_date, team1_id, team2_id, "
        "  status, result_type, winning_team_id, world_id, canon_status) "
        "VALUES ('T20', ?, '2024-01-15', ?, ?, 'complete', 'runs', ?, ?, ?)",
        (venue_id, team1_id, team2_id, team1_id, world_id, canon_status)
    ).lastrowid

    # innings 1 — team1 bats
    inn_id = db.execute(
        "INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id, "
        "  total_runs, total_wickets, overs_completed, status) "
        "VALUES (?, 1, ?, ?, 120, 8, 20, 'complete')",
        (match_id, team1_id, team2_id)
    ).lastrowid

    # Two batter entries so the views have data
    p1 = db.execute(
        "SELECT id FROM players WHERE team_id=? ORDER BY batting_position LIMIT 1", (team1_id,)
    ).fetchone()['id']
    p2 = db.execute(
        "SELECT id FROM players WHERE team_id=? ORDER BY batting_position LIMIT 1 OFFSET 1", (team1_id,)
    ).fetchone()['id']

    db.execute(
        "INSERT INTO batter_innings (innings_id, player_id, batting_position, runs, "
        "  balls_faced, not_out, status) VALUES (?,?,1,55,40,0,'dismissed')",
        (inn_id, p1)
    )
    db.execute(
        "INSERT INTO batter_innings (innings_id, player_id, batting_position, runs, "
        "  balls_faced, not_out, status) VALUES (?,?,2,42,30,1,'batting')",
        (inn_id, p2)
    )

    # Bowler entry
    b1 = db.execute(
        "SELECT id FROM players WHERE team_id=? AND bowling_type != 'none' LIMIT 1", (team2_id,)
    ).fetchone()['id']
    db.execute(
        "INSERT INTO bowler_innings (innings_id, player_id, overs, runs_conceded, wickets) "
        "VALUES (?,?,4,30,2)",
        (inn_id, b1)
    )

    # Partnership
    db.execute(
        "INSERT INTO partnerships (innings_id, wicket_number, batter1_id, batter2_id, runs, balls) "
        "VALUES (?,0,?,?,97,70)",
        (inn_id, p1, p2)
    )

    db.commit()
    return match_id


# ── Flask test-client fixture ─────────────────────────────────────────────────

def make_client(db):
    """
    Return a Flask test client wired to the provided in-memory DB.
    Patches database.get_db / database.close_db so every request uses our DB.
    """
    flask_app.app.config['TESTING'] = True
    flask_app.app.config['_TEST_DB'] = db

    # Monkey-patch at the module level so app.py sees the patched version
    original_get_db   = database.get_db
    original_close_db = database.close_db

    database.get_db   = lambda: db
    database.close_db = lambda c: None  # don't close — we own the connection

    client = flask_app.app.test_client()
    return client, original_get_db, original_close_db


def restore_db(original_get_db, original_close_db):
    database.get_db   = original_get_db
    database.close_db = original_close_db


# ═════════════════════════════════════════════════════════════════════════════
# A. DATABASE FUNCTION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDatabaseFunctions(unittest.TestCase):

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.match_id = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )

    def tearDown(self):
        self.db.close()

    # ── Schema ─────────────────────────────────────────────────────────────

    def test_canon_status_column_exists(self):
        cols = {r['name'] for r in
                self.db.execute("PRAGMA table_info(matches)").fetchall()}
        self.assertIn('canon_status', cols)

    def test_audit_log_table_exists(self):
        tables = {r['name'] for r in
                  self.db.execute(
                      "SELECT name FROM sqlite_master WHERE type='table'"
                  ).fetchall()}
        self.assertIn('almanack_audit_log', tables)

    def test_audit_log_columns(self):
        cols = {r['name'] for r in
                self.db.execute("PRAGMA table_info(almanack_audit_log)").fetchall()}
        for c in ('id', 'match_id', 'action', 'old_value', 'new_value',
                  'actor', 'note', 'created_at'):
            self.assertIn(c, cols, f"Column '{c}' missing from almanack_audit_log")

    # ── set_match_canon_status ─────────────────────────────────────────────

    def test_set_canon_status_to_exhibition(self):
        ok = database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        self.assertTrue(ok)
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'exhibition')

    def test_set_canon_status_to_deleted(self):
        ok = database.set_match_canon_status(self.db, self.match_id, 'deleted')
        self.assertTrue(ok)
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'deleted')

    def test_set_canon_status_returns_false_for_missing_match(self):
        ok = database.set_match_canon_status(self.db, 99999, 'exhibition')
        self.assertFalse(ok)

    def test_set_canon_status_writes_audit_log(self):
        database.set_match_canon_status(
            self.db, self.match_id, 'exhibition', actor='tester', note='test note'
        )
        row = self.db.execute(
            "SELECT * FROM almanack_audit_log WHERE match_id=?", (self.match_id,)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['action'], 'set_exhibition')
        self.assertEqual(row['new_value'], 'exhibition')
        self.assertEqual(row['actor'], 'tester')
        self.assertEqual(row['note'], 'test note')

    def test_set_canon_status_audit_log_captures_old_value(self):
        # Start as canon, then change
        self.db.execute(
            "UPDATE matches SET canon_status='canon' WHERE id=?", (self.match_id,)
        )
        self.db.commit()
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        row = self.db.execute(
            "SELECT old_value FROM almanack_audit_log WHERE match_id=? ORDER BY id DESC LIMIT 1",
            (self.match_id,)
        ).fetchone()
        self.assertEqual(row['old_value'], 'canon')

    def test_multiple_canon_status_changes_logged(self):
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        database.set_match_canon_status(self.db, self.match_id, 'canon')
        count = self.db.execute(
            "SELECT COUNT(*) as n FROM almanack_audit_log WHERE match_id=?",
            (self.match_id,)
        ).fetchone()['n']
        self.assertEqual(count, 2)

    # ── edit_match_result ─────────────────────────────────────────────────

    def test_edit_match_result_changes_result_type(self):
        ok = database.edit_match_result(self.db, self.match_id, {
            'result_type': 'wickets', 'margin_wickets': 5
        })
        self.assertTrue(ok)
        row = self.db.execute(
            "SELECT result_type, margin_wickets FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertEqual(row['result_type'], 'wickets')
        self.assertEqual(row['margin_wickets'], 5)

    def test_edit_match_result_returns_false_for_missing_match(self):
        ok = database.edit_match_result(self.db, 99999, {'result_type': 'runs'})
        self.assertFalse(ok)

    def test_edit_match_result_writes_audit_log(self):
        database.edit_match_result(self.db, self.match_id, {
            'result_type': 'draw', 'note': 'correcting error'
        })
        row = self.db.execute(
            "SELECT * FROM almanack_audit_log WHERE match_id=? AND action='edit_result'",
            (self.match_id,)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertIn('draw', row['new_value'])

    def test_edit_match_result_only_allowed_fields(self):
        """Editing should not touch disallowed fields like format."""
        database.edit_match_result(self.db, self.match_id, {
            'result_type': 'runs', 'format': 'Test'
        })
        row = self.db.execute(
            "SELECT format FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        # format should NOT have changed
        self.assertEqual(row['format'], 'T20')

    # ── get_audit_log ─────────────────────────────────────────────────────

    def test_get_audit_log_returns_entries(self):
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        entries = database.get_audit_log(self.db, {})
        self.assertGreater(len(entries), 0)

    def test_get_audit_log_filter_by_match_id(self):
        # Create a second match
        m2 = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        database.set_match_canon_status(self.db, m2, 'exhibition')

        entries = database.get_audit_log(self.db, {'match_id': str(self.match_id)})
        for e in entries:
            self.assertEqual(e['match_id'], self.match_id)

    def test_get_audit_log_ordered_newest_first(self):
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        database.set_match_canon_status(self.db, self.match_id, 'canon')
        entries = database.get_audit_log(self.db, {})
        ids = [e['id'] for e in entries]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_get_audit_log_includes_match_date(self):
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        entries = database.get_audit_log(self.db, {})
        self.assertIn('match_date', entries[0])

    # ── reset_world_stats ─────────────────────────────────────────────────

    def test_reset_world_stats_marks_canon_as_exhibition(self):
        m = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            world_id=self.world_id, canon_status='canon'
        )
        count = database.reset_world_stats(self.db, self.world_id)
        self.assertGreater(count, 0)
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (m,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'exhibition')

    def test_reset_world_stats_does_not_touch_exhibition(self):
        m = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            world_id=self.world_id, canon_status='exhibition'
        )
        database.reset_world_stats(self.db, self.world_id)
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (m,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'exhibition')

    def test_reset_world_stats_does_not_touch_deleted(self):
        m = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            world_id=self.world_id, canon_status='deleted'
        )
        database.reset_world_stats(self.db, self.world_id)
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (m,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'deleted')

    def test_reset_world_stats_logs_each_change(self):
        for _ in range(3):
            _insert_complete_match(
                self.db, self.team1_id, self.team2_id, self.venue_id,
                world_id=self.world_id, canon_status='canon'
            )
        database.reset_world_stats(self.db, self.world_id)
        count = self.db.execute(
            "SELECT COUNT(*) as n FROM almanack_audit_log WHERE action='set_exhibition'"
        ).fetchone()['n']
        self.assertGreaterEqual(count, 3)

    def test_reset_world_stats_returns_zero_for_empty_world(self):
        count = database.reset_world_stats(self.db, 99999)
        self.assertEqual(count, 0)


# ═════════════════════════════════════════════════════════════════════════════
# B. SQL VIEW FILTERING TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSQLViewFiltering(unittest.TestCase):
    """
    Verify that the four statistical views include only canon matches
    and exclude exhibition and deleted matches.
    """

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids

    def tearDown(self):
        self.db.close()

    def _batting_run_count(self):
        """Sum of all runs in batting_averages view."""
        row = self.db.execute(
            "SELECT COALESCE(SUM(runs), 0) as total FROM batting_averages"
        ).fetchone()
        return row['total']

    def _bowling_wicket_count(self):
        row = self.db.execute(
            "SELECT COALESCE(SUM(wickets), 0) as total FROM bowling_averages"
        ).fetchone()
        return row['total']

    def _team_records_count(self):
        row = self.db.execute(
            "SELECT COUNT(*) as n FROM team_records_view"
        ).fetchone()
        return row['n']

    def _partnership_count(self):
        row = self.db.execute(
            "SELECT COUNT(*) as n FROM partnership_records"
        ).fetchone()
        return row['n']

    def test_batting_view_includes_canon(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='canon'
        )
        self.assertGreater(self._batting_run_count(), 0)

    def test_batting_view_excludes_exhibition(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='exhibition'
        )
        self.assertEqual(self._batting_run_count(), 0)

    def test_batting_view_excludes_deleted(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='deleted'
        )
        self.assertEqual(self._batting_run_count(), 0)

    def test_batting_view_only_sums_canon_when_mixed(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='canon'
        )
        canon_total = self._batting_run_count()
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='exhibition'
        )
        # Adding an exhibition match should not increase the total
        self.assertEqual(self._batting_run_count(), canon_total)

    def test_bowling_view_includes_canon(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='canon'
        )
        self.assertGreater(self._bowling_wicket_count(), 0)

    def test_bowling_view_excludes_exhibition(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='exhibition'
        )
        self.assertEqual(self._bowling_wicket_count(), 0)

    def test_bowling_view_excludes_deleted(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='deleted'
        )
        self.assertEqual(self._bowling_wicket_count(), 0)

    def test_team_records_view_includes_canon(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='canon'
        )
        self.assertGreater(self._team_records_count(), 0)

    def test_team_records_view_excludes_exhibition(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='exhibition'
        )
        self.assertEqual(self._team_records_count(), 0)

    def test_team_records_view_excludes_deleted(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='deleted'
        )
        self.assertEqual(self._team_records_count(), 0)

    def test_partnership_records_view_includes_canon(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='canon'
        )
        self.assertGreater(self._partnership_count(), 0)

    def test_partnership_records_view_excludes_exhibition(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='exhibition'
        )
        self.assertEqual(self._partnership_count(), 0)

    def test_partnership_records_view_excludes_deleted(self):
        _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='deleted'
        )
        self.assertEqual(self._partnership_count(), 0)

    def test_null_canon_status_treated_as_canon_in_views(self):
        """Rows with NULL canon_status (pre-migration) must appear in views."""
        mid = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            canon_status='canon'
        )
        # Wipe the canon_status to simulate a pre-migration row
        self.db.execute(
            "UPDATE matches SET canon_status = NULL WHERE id = ?", (mid,)
        )
        self.db.commit()
        self.assertGreater(self._batting_run_count(), 0)


# ═════════════════════════════════════════════════════════════════════════════
# C. API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestCanonStatusEndpoint(unittest.TestCase):
    """PATCH /api/matches/<id>/canon-status"""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.match_id = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def patch(self, match_id, body):
        return self.client.patch(
            f'/api/matches/{match_id}/canon-status',
            data=json.dumps(body),
            content_type='application/json'
        )

    def test_set_to_canon_returns_200(self):
        r = self.patch(self.match_id, {'canon_status': 'canon'})
        self.assertEqual(r.status_code, 200)

    def test_set_to_exhibition_returns_200(self):
        r = self.patch(self.match_id, {'canon_status': 'exhibition'})
        self.assertEqual(r.status_code, 200)

    def test_set_to_deleted_returns_200(self):
        """PATCH currently allows 'deleted' (use DELETE endpoint instead for best practice)."""
        r = self.patch(self.match_id, {'canon_status': 'deleted'})
        self.assertEqual(r.status_code, 200)

    def test_invalid_status_returns_400(self):
        r = self.patch(self.match_id, {'canon_status': 'invalid'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', r.get_json())

    def test_missing_status_returns_400(self):
        r = self.patch(self.match_id, {})
        self.assertEqual(r.status_code, 400)

    def test_nonexistent_match_returns_404(self):
        r = self.patch(99999, {'canon_status': 'canon'})
        self.assertEqual(r.status_code, 404)

    def test_response_contains_match(self):
        r = self.patch(self.match_id, {'canon_status': 'exhibition'})
        data = r.get_json()
        self.assertIn('match', data)

    def test_canon_status_persisted(self):
        self.patch(self.match_id, {'canon_status': 'exhibition'})
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'exhibition')


class TestDeleteMatchEndpoint(unittest.TestCase):
    """DELETE /api/matches/<id>"""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.match_id = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def delete(self, match_id, body):
        return self.client.delete(
            f'/api/matches/{match_id}',
            data=json.dumps(body),
            content_type='application/json'
        )

    def test_delete_with_confirm_token_returns_200(self):
        r = self.delete(self.match_id, {'confirm': 'DELETE'})
        self.assertEqual(r.status_code, 200)

    def test_delete_without_confirm_returns_400(self):
        r = self.delete(self.match_id, {})
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', r.get_json())

    def test_delete_with_wrong_token_returns_400(self):
        r = self.delete(self.match_id, {'confirm': 'yes'})
        self.assertEqual(r.status_code, 400)

    def test_delete_nonexistent_match_returns_404(self):
        r = self.delete(99999, {'confirm': 'DELETE'})
        self.assertEqual(r.status_code, 404)

    def test_delete_sets_canon_status_to_deleted(self):
        self.delete(self.match_id, {'confirm': 'DELETE'})
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'deleted')

    def test_delete_response_contains_match_id(self):
        r = self.delete(self.match_id, {'confirm': 'DELETE'})
        data = r.get_json()
        self.assertIn('match_id', data)
        self.assertEqual(data['match_id'], self.match_id)

    def test_match_row_not_physically_removed(self):
        self.delete(self.match_id, {'confirm': 'DELETE'})
        row = self.db.execute(
            "SELECT id FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertIsNotNone(row, "Soft delete must not remove the row")


class TestEditResultEndpoint(unittest.TestCase):
    """PATCH /api/matches/<id>/result"""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.match_id = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def patch(self, match_id, body):
        return self.client.patch(
            f'/api/matches/{match_id}/result',
            data=json.dumps(body),
            content_type='application/json'
        )

    def test_edit_result_on_complete_match_returns_200(self):
        r = self.patch(self.match_id, {'result_type': 'wickets', 'margin_wickets': 3})
        self.assertEqual(r.status_code, 200)

    def test_edit_result_on_incomplete_match_returns_400(self):
        # Insert an in-progress match
        mid = self.db.execute(
            "INSERT INTO matches (format, venue_id, match_date, team1_id, team2_id, "
            "  status, canon_status) "
            "VALUES ('T20', ?, '2024-01-20', ?, ?, 'in_progress', 'canon')",
            (self.venue_id, self.team1_id, self.team2_id)
        ).lastrowid
        self.db.commit()
        r = self.patch(mid, {'result_type': 'runs'})
        self.assertEqual(r.status_code, 400)

    def test_edit_result_nonexistent_returns_404(self):
        r = self.patch(99999, {'result_type': 'runs'})
        self.assertEqual(r.status_code, 404)

    def test_edit_result_persists_changes(self):
        self.patch(self.match_id, {'result_type': 'draw', 'margin_runs': None})
        row = self.db.execute(
            "SELECT result_type FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertEqual(row['result_type'], 'draw')

    def test_edit_result_response_contains_match(self):
        r = self.patch(self.match_id, {'result_type': 'runs', 'margin_runs': 50})
        data = r.get_json()
        self.assertIn('match', data)


class TestBulkCanonStatusEndpoint(unittest.TestCase):
    """POST /api/almanack/bulk-canon-status"""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.m1 = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        self.m2 = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def post(self, body):
        return self.client.post(
            '/api/almanack/bulk-canon-status',
            data=json.dumps(body),
            content_type='application/json'
        )

    def test_bulk_set_returns_200(self):
        r = self.post({'match_ids': [self.m1, self.m2], 'canon_status': 'exhibition'})
        self.assertEqual(r.status_code, 200)

    def test_bulk_set_returns_updated_count(self):
        r = self.post({'match_ids': [self.m1, self.m2], 'canon_status': 'exhibition'})
        data = r.get_json()
        self.assertEqual(data['updated'], 2)

    def test_bulk_set_persists_changes(self):
        self.post({'match_ids': [self.m1, self.m2], 'canon_status': 'exhibition'})
        for mid in (self.m1, self.m2):
            row = self.db.execute(
                "SELECT canon_status FROM matches WHERE id=?", (mid,)
            ).fetchone()
            self.assertEqual(row['canon_status'], 'exhibition')

    def test_bulk_invalid_status_returns_400(self):
        r = self.post({'match_ids': [self.m1], 'canon_status': 'bogus'})
        self.assertEqual(r.status_code, 400)

    def test_bulk_empty_list_returns_400(self):
        r = self.post({'match_ids': [], 'canon_status': 'canon'})
        self.assertEqual(r.status_code, 400)

    def test_bulk_missing_match_ids_returns_400(self):
        r = self.post({'canon_status': 'canon'})
        self.assertEqual(r.status_code, 400)

    def test_bulk_includes_nonexistent_id_updates_valid_ones(self):
        r = self.post({'match_ids': [self.m1, 99999], 'canon_status': 'exhibition'})
        data = r.get_json()
        # Only valid IDs should count
        self.assertEqual(data['updated'], 1)


class TestAuditLogEndpoint(unittest.TestCase):
    """GET /api/almanack/audit-log"""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.match_id = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def test_returns_200(self):
        r = self.client.get('/api/almanack/audit-log')
        self.assertEqual(r.status_code, 200)

    def test_response_has_entries_key(self):
        r = self.client.get('/api/almanack/audit-log')
        data = r.get_json()
        self.assertIn('entries', data)

    def test_response_has_count_key(self):
        r = self.client.get('/api/almanack/audit-log')
        data = r.get_json()
        self.assertIn('count', data)

    def test_count_matches_entries_length(self):
        r = self.client.get('/api/almanack/audit-log')
        data = r.get_json()
        self.assertEqual(data['count'], len(data['entries']))

    def test_entries_non_empty_after_status_change(self):
        r = self.client.get('/api/almanack/audit-log')
        data = r.get_json()
        self.assertGreater(data['count'], 0)

    def test_filter_by_match_id(self):
        m2 = _insert_complete_match(self.db, self.team1_id, self.team2_id, self.venue_id)
        database.set_match_canon_status(self.db, m2, 'exhibition')
        r = self.client.get(f'/api/almanack/audit-log?match_id={self.match_id}')
        data = r.get_json()
        for e in data['entries']:
            self.assertEqual(e['match_id'], self.match_id)

    def test_empty_db_returns_empty_entries(self):
        # Wipe the audit log
        self.db.execute("DELETE FROM almanack_audit_log")
        self.db.commit()
        r = self.client.get('/api/almanack/audit-log')
        data = r.get_json()
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['entries'], [])


class TestResetWorldStatsEndpoint(unittest.TestCase):
    """POST /api/worlds/<id>/reset-stats"""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def test_returns_200_for_existing_world(self):
        r = self.client.post(f'/api/worlds/{self.world_id}/reset-stats')
        self.assertEqual(r.status_code, 200)

    def test_response_contains_world_id(self):
        r = self.client.post(f'/api/worlds/{self.world_id}/reset-stats')
        data = r.get_json()
        self.assertIn('world_id', data)
        self.assertEqual(data['world_id'], self.world_id)

    def test_response_contains_matches_reset(self):
        r = self.client.post(f'/api/worlds/{self.world_id}/reset-stats')
        data = r.get_json()
        self.assertIn('matches_reset', data)

    def test_resets_canon_matches_in_world(self):
        m = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id,
            world_id=self.world_id, canon_status='canon'
        )
        r = self.client.post(f'/api/worlds/{self.world_id}/reset-stats')
        self.assertEqual(r.get_json()['matches_reset'], 1)
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (m,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'exhibition')

    def test_empty_world_returns_zero_reset(self):
        r = self.client.post(f'/api/worlds/{self.world_id}/reset-stats')
        self.assertEqual(r.get_json()['matches_reset'], 0)


# ═════════════════════════════════════════════════════════════════════════════
# D. DEFAULT CANON STATUS IN /api/matches/start
# ═════════════════════════════════════════════════════════════════════════════

class TestStartMatchCanonDefaults(unittest.TestCase):
    """Verify canon_status defaults in POST /api/matches/start."""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def _start(self, extra=None):
        body = {
            'team1_id':    self.team1_id,
            'team2_id':    self.team2_id,
            'format':      'T20',
            'venue_id':    self.venue_id,
            'player_mode': 'ai_vs_ai',
            'match_date':  '2024-02-01',
        }
        if extra:
            body.update(extra)
        return self.client.post(
            '/api/matches/start',
            data=json.dumps(body),
            content_type='application/json'
        )

    def _get_canon_status(self, match_id):
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (match_id,)
        ).fetchone()
        return row['canon_status'] if row else None

    def test_standalone_defaults_to_exhibition(self):
        r = self._start()
        self.assertIn(r.status_code, (200, 201))
        mid = r.get_json()['match']['id']
        self.assertEqual(self._get_canon_status(mid), 'exhibition')

    def test_world_match_defaults_to_canon(self):
        r = self._start({'world_id': self.world_id})
        self.assertIn(r.status_code, (200, 201))
        mid = r.get_json()['match']['id']
        self.assertEqual(self._get_canon_status(mid), 'canon')

    def test_explicit_canon_override_respected(self):
        r = self._start({'canon_status': 'canon'})
        mid = r.get_json()['match']['id']
        self.assertEqual(self._get_canon_status(mid), 'canon')

    def test_explicit_exhibition_override_respected(self):
        r = self._start({'world_id': self.world_id, 'canon_status': 'exhibition'})
        mid = r.get_json()['match']['id']
        self.assertEqual(self._get_canon_status(mid), 'exhibition')

    def test_invalid_explicit_status_falls_back_to_exhibition(self):
        """An invalid explicit canon_status is silently corrected to exhibition."""
        r = self._start({'canon_status': 'unknown_value'})
        mid = r.get_json()['match']['id']
        self.assertEqual(self._get_canon_status(mid), 'exhibition')


# ═════════════════════════════════════════════════════════════════════════════
# E. ALMANACK MATCH LISTING FILTERS
# ═════════════════════════════════════════════════════════════════════════════

class TestAlmanackMatchListing(unittest.TestCase):
    """Verify GET /api/almanack/matches filters for canon_status and include_deleted."""

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids

        self.m_canon     = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id, canon_status='canon')
        self.m_exhib     = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id, canon_status='exhibition')
        self.m_deleted   = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id, canon_status='deleted')

        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def _ids(self, url):
        r = self.client.get(url)
        data = r.get_json()
        # /api/almanack/matches uses 'rows' key
        return {m['id'] for m in data.get('rows', data.get('matches', data.get('records', [])))}

    def test_default_shows_canon_and_exhibition(self):
        ids = self._ids('/api/almanack/matches')
        self.assertIn(self.m_canon, ids)
        self.assertIn(self.m_exhib, ids)

    def test_default_excludes_deleted(self):
        ids = self._ids('/api/almanack/matches')
        self.assertNotIn(self.m_deleted, ids)

    def test_include_deleted_shows_all_three(self):
        ids = self._ids('/api/almanack/matches?include_deleted=1')
        self.assertIn(self.m_canon,   ids)
        self.assertIn(self.m_exhib,   ids)
        self.assertIn(self.m_deleted, ids)

    def test_filter_canon_status_canon_only(self):
        ids = self._ids('/api/almanack/matches?canon_status=canon')
        self.assertIn(self.m_canon, ids)
        self.assertNotIn(self.m_exhib, ids)
        self.assertNotIn(self.m_deleted, ids)

    def test_filter_canon_status_exhibition_only(self):
        ids = self._ids('/api/almanack/matches?canon_status=exhibition')
        self.assertIn(self.m_exhib, ids)
        self.assertNotIn(self.m_canon, ids)
        self.assertNotIn(self.m_deleted, ids)

    def test_null_canon_status_appears_in_default_listing(self):
        """Pre-migration rows with NULL canon_status should appear (treated as canon)."""
        mid = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id, canon_status='canon')
        self.db.execute("UPDATE matches SET canon_status=NULL WHERE id=?", (mid,))
        self.db.commit()
        ids = self._ids('/api/almanack/matches')
        self.assertIn(mid, ids)

    def test_response_includes_canon_status_field(self):
        r = self.client.get('/api/almanack/matches')
        data = r.get_json()
        matches = data.get('rows', data.get('matches', data.get('records', [])))
        self.assertGreater(len(matches), 0)
        self.assertIn('canon_status', matches[0])


# ═════════════════════════════════════════════════════════════════════════════
# F. EDGE CASES
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):

    def setUp(self):
        self.db = make_test_db()
        ids = _seed(self.db)
        self.team1_id, self.team2_id, self.venue_id, self.world_id = ids
        self.match_id = _insert_complete_match(
            self.db, self.team1_id, self.team2_id, self.venue_id
        )
        self.client, self._og, self._oc = make_client(self.db)

    def tearDown(self):
        restore_db(self._og, self._oc)
        self.db.close()

    def test_set_same_status_twice_does_not_error(self):
        """Idempotent update: setting the same status twice is harmless."""
        ok1 = database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        ok2 = database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        self.assertTrue(ok1)
        self.assertTrue(ok2)

    def test_each_status_change_adds_audit_row(self):
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        count = self.db.execute(
            "SELECT COUNT(*) as n FROM almanack_audit_log WHERE match_id=?",
            (self.match_id,)
        ).fetchone()['n']
        self.assertEqual(count, 2)

    def test_reset_world_stats_on_nonexistent_world_returns_zero(self):
        count = database.reset_world_stats(self.db, 99999)
        self.assertEqual(count, 0)

    def test_canon_status_endpoint_with_empty_body_returns_400(self):
        r = self.client.patch(
            f'/api/matches/{self.match_id}/canon-status',
            data='',
            content_type='application/json'
        )
        self.assertEqual(r.status_code, 400)

    def test_bulk_with_string_ids_accepted(self):
        """match_ids sent as strings (from JS) should be coerced to int."""
        r = self.client.post(
            '/api/almanack/bulk-canon-status',
            data=json.dumps({
                'match_ids': [str(self.match_id)],
                'canon_status': 'exhibition'
            }),
            content_type='application/json'
        )
        self.assertEqual(r.status_code, 200)

    def test_audit_log_created_at_is_populated(self):
        database.set_match_canon_status(self.db, self.match_id, 'exhibition')
        row = self.db.execute(
            "SELECT created_at FROM almanack_audit_log WHERE match_id=?",
            (self.match_id,)
        ).fetchone()
        self.assertIsNotNone(row['created_at'])
        self.assertGreater(len(row['created_at']), 0)

    def test_delete_match_can_be_undeleted_via_patch(self):
        """A soft-deleted match can be restored via PATCH canon-status."""
        self.client.delete(
            f'/api/matches/{self.match_id}',
            data=json.dumps({'confirm': 'DELETE'}),
            content_type='application/json'
        )
        r = self.client.patch(
            f'/api/matches/{self.match_id}/canon-status',
            data=json.dumps({'canon_status': 'canon'}),
            content_type='application/json'
        )
        self.assertEqual(r.status_code, 200)
        row = self.db.execute(
            "SELECT canon_status FROM matches WHERE id=?", (self.match_id,)
        ).fetchone()
        self.assertEqual(row['canon_status'], 'canon')


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # Print a header so the output is easy to read in terminal
    print()
    print("=" * 70)
    print("  Roll It & Bowl It — Almanack Canon System Test Suite")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    test_classes = [
        TestDatabaseFunctions,
        TestSQLViewFiltering,
        TestCanonStatusEndpoint,
        TestDeleteMatchEndpoint,
        TestEditResultEndpoint,
        TestBulkCanonStatusEndpoint,
        TestAuditLogEndpoint,
        TestResetWorldStatsEndpoint,
        TestStartMatchCanonDefaults,
        TestAlmanackMatchListing,
        TestEdgeCases,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 70)
    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    print(f"  TOTAL: {total}  |  PASSED: {passed}  |  FAILED: {len(result.failures)}  |  ERRORS: {len(result.errors)}")
    print("=" * 70)
    print()

    sys.exit(0 if result.wasSuccessful() else 1)
