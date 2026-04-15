import json
import os
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import app as flask_app
import competition_rules
import database


SCHEMA_PATH = os.path.join(HERE, 'schema.sql')


def make_test_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    database.run_migrations(conn)
    return conn


def make_client(db):
    flask_app.app.config['TESTING'] = True
    original_get_db = database.get_db
    original_close_db = database.close_db
    database.get_db = lambda: db
    database.close_db = lambda _: None
    return flask_app.app.test_client(), original_get_db, original_close_db


def restore_db(original_get_db, original_close_db):
    database.get_db = original_get_db
    database.close_db = original_close_db


class TestCompetitionRulesApi(unittest.TestCase):

    def setUp(self):
        self.db = make_test_db()
        self.world_id = database.create_world(self.db, {
            'name': 'Rules Test World',
            'created_date': '2026-01-01',
            'current_date': '2026-01-01',
            'calendar_density': 'moderate',
            'settings_json': json.dumps({'world_scope': 'combined', 'domestic_leagues': ['ipl']}),
        })
        self.venue_id = self.db.execute(
            "INSERT INTO venues (name, city, country) VALUES ('Rules Oval', 'Test City', 'Testland')"
        ).lastrowid
        self.team1_id = self.db.execute(
            "INSERT INTO teams (name, short_code, badge_colour) VALUES ('Alpha XI', 'ALP', '#123456')"
        ).lastrowid
        self.team2_id = self.db.execute(
            "INSERT INTO teams (name, short_code, badge_colour) VALUES ('Beta XI', 'BET', '#654321')"
        ).lastrowid
        self.db.execute(
            "INSERT INTO fixtures (world_id, scheduled_date, venue_id, team1_id, team2_id, fixture_type, "
            " status, format, series_name, season_year, competition_key, competition_name, "
            " competition_stage, competition_round, competition_order, is_icc_event) "
            "VALUES (?, '2026-03-20', ?, ?, ?, 'league', 'scheduled', 'T20', 'Indian Premier League 2026', "
            " 2026, 'ipl', 'Indian Premier League', 'league', 'League Stage', 1, 0)",
            (self.world_id, self.venue_id, self.team1_id, self.team2_id)
        )
        self.db.commit()
        self.client, self.original_get_db, self.original_close_db = make_client(self.db)

    def tearDown(self):
        restore_db(self.original_get_db, self.original_close_db)
        self.db.close()

    def test_rule_explainer_reflects_core_rule_fields(self):
        data = competition_rules.get_rule_explainer('icc_t20_world_cup')
        self.assertEqual(data['points_system_key'], competition_rules.get_rule('icc_t20_world_cup')['points_system'])
        self.assertEqual(data['draw_type'], competition_rules.get_rule('icc_t20_world_cup')['draw_type'])
        self.assertIn('Super 8', data['stage_path'])
        self.assertIn('seeded into pots', data['draw_method'])

    def test_world_competition_rules_route_returns_world_scoped_payload(self):
        res = self.client.get(f'/api/worlds/{self.world_id}/competitions/ipl/rules')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['competition']['name'], 'Indian Premier League')
        self.assertEqual(data['competition']['world_name'], 'Rules Test World')
        self.assertEqual(data['rules']['draw_type'], 'fixed_groups')
        self.assertIn('top four teams', data['rules']['qualification'].lower())
        self.assertIn('Qualifier', ''.join(data['rules']['stages']))

    def test_world_competition_detail_includes_rules_payload(self):
        res = self.client.get(f'/api/worlds/{self.world_id}/competitions/ipl')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('rules', data)
        self.assertEqual(data['rules']['points_system_key'], 'limited_nrr')


if __name__ == '__main__':
    unittest.main()
