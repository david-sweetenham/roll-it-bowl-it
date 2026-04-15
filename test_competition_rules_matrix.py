import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import app
import competition_rules
import game_engine


def _fixture(team1_id, team2_id, winner_id, group_name=None, result_type='runs', match_id=1):
    return {
        'team1_id': team1_id,
        'team2_id': team2_id,
        'team1_name': f'Team {team1_id}',
        'team2_name': f'Team {team2_id}',
        'team1_colour': '#111111',
        'team2_colour': '#222222',
        'competition_group': group_name,
        'status': 'complete',
        'result_type': result_type,
        'winning_team_id': winner_id,
        'match_id': match_id,
    }


class TestCompetitionRulesMatrix(unittest.TestCase):

    def test_every_competition_has_explicit_profiles(self):
        for key, rule in competition_rules.get_competition_matrix().items():
            with self.subTest(key=key):
                self.assertIn(rule.get('format_scope'), ('international', 'domestic'))
                self.assertIn(rule.get('standings_grouping'), ('combined', 'by_group'))
                self.assertTrue(rule.get('generation_profile'))
                self.assertTrue(rule.get('progression_profile'))
                self.assertIn(rule.get('draw_type'), ('single_table', 'fixed_groups', 'seeded_groups'))

    def test_international_and_domestic_format_describers_are_distinct(self):
        intl = competition_rules.get_rule_explainer('icc_t20_world_cup')
        dom = competition_rules.get_rule_explainer('ipl')
        self.assertEqual(intl['format_scope'], 'international')
        self.assertEqual(dom['format_scope'], 'domestic')
        self.assertNotEqual(intl['format_description'], dom['format_description'])

    def test_ipl_standings_are_combined_not_split_by_groups(self):
        rule = competition_rules.get_rule('ipl')
        fixtures = [
            _fixture(1, 2, 1, group_name='Group A', match_id=1),
            _fixture(3, 4, 3, group_name='Group B', match_id=2),
            _fixture(1, 3, 1, group_name='Group A', match_id=3),
            _fixture(2, 4, 4, group_name='Group B', match_id=4),
        ]
        innings_map = {
            1: [
                {'batting_team_id': 1, 'total_runs': 180, 'total_wickets': 6, 'overs_completed': 20},
                {'batting_team_id': 2, 'total_runs': 150, 'total_wickets': 8, 'overs_completed': 20},
            ],
            2: [
                {'batting_team_id': 3, 'total_runs': 170, 'total_wickets': 5, 'overs_completed': 20},
                {'batting_team_id': 4, 'total_runs': 160, 'total_wickets': 9, 'overs_completed': 20},
            ],
            3: [
                {'batting_team_id': 1, 'total_runs': 190, 'total_wickets': 4, 'overs_completed': 20},
                {'batting_team_id': 3, 'total_runs': 165, 'total_wickets': 8, 'overs_completed': 20},
            ],
            4: [
                {'batting_team_id': 2, 'total_runs': 155, 'total_wickets': 7, 'overs_completed': 20},
                {'batting_team_id': 4, 'total_runs': 156, 'total_wickets': 4, 'overs_completed': 18.4},
            ],
        }
        flat, grouped = app._build_competition_standings(rule, fixtures, innings_map)
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]['group'], 'Standings')
        self.assertEqual(flat[0]['team_id'], 1)

    def test_marsh_cup_schedule_uses_explicit_repeat_pairs(self):
        teams = []
        for idx, name in enumerate([
            'New South Wales', 'Queensland', 'Victoria',
            'Tasmania', 'South Australia', 'Western Australia',
        ], start=1):
            teams.append({'team_id': idx, 'name': name, 'home_venue_id': idx})
        fixtures = competition_rules.generate_domestic_competition('marsh_cup', teams, 2026, 2027)
        self.assertEqual(len(fixtures), 21)

    def test_marsh_cup_bonus_point_uses_victory_condition(self):
        fixture = _fixture(1, 2, 2, match_id=1, result_type='wickets')
        innings_rows = [
            {'batting_team_id': 1, 'total_runs': 240, 'total_wickets': 10, 'overs_completed': 50},
            {'batting_team_id': 2, 'total_runs': 241, 'total_wickets': 4, 'overs_completed': 39.2},
        ]
        bonus = app._marsh_victory_bonus(fixture, innings_rows)
        self.assertEqual(bonus, {2: {'batting_bonus': 1}})

    def test_county_no_result_awards_shared_points(self):
        rule = competition_rules.get_rule('county_championship')
        flat, _ = app._build_competition_standings(
            rule,
            [_fixture(1, 2, None, group_name='Division 1', match_id=1, result_type='no_result')],
            {1: []},
        )
        self.assertEqual({row['team_id']: row['points'] for row in flat}, {1: 8, 2: 8})

    def test_snapshot_helper_sets_cutoff_scores(self):
        innings = {'overs_completed': 99.5, 'total_runs': 301, 'total_wickets': 4}
        update = {'overs_completed': 100.0, 'total_runs': 304, 'total_wickets': 4}
        snapped = app._apply_innings_cutoff_snapshots(innings, update)
        self.assertEqual(snapped['runs_at_100_overs'], 304)
        self.assertEqual(snapped['wickets_at_100_overs'], 4)

    def test_simulate_to_records_100_over_snapshot(self):
        batting = []
        for i in range(11):
            batting.append({
                'player_id': i + 1,
                'name': f'Batter {i + 1}',
                'batting_rating': 3,
                'runs': 0,
                'balls': 0,
                'dismissed': False,
                'in': i < 2,
            })
        bowling = []
        for i in range(6):
            bowling.append({
                'player_id': 100 + i,
                'name': f'Bowler {i + 1}',
                'bowling_type': 'pace',
                'bowling_rating': 3,
                'overs_bowled': 0,
                'balls_bowled': 0,
                'runs': 0,
                'wickets': 0,
                'maidens': 0,
                '_this_over_runs': 0,
            })
        state = {
            'format': 'Test',
            'max_overs': None,
            'target': None,
            'innings_number': 1,
            'over_number': 99,
            'ball_in_over': 5,
            'is_free_hit': False,
            'total_runs': 250,
            'total_wickets': 2,
            'batting_players': batting,
            'striker_idx': 0,
            'non_striker_idx': 1,
            'next_batter_idx': 2,
            'bowling_players': bowling,
            'last_bowler_id': None,
            'current_bowler_id': None,
        }
        result = game_engine.simulate_to('over', state)
        self.assertEqual(result['state']['runs_at_100_overs'], result['state']['total_runs'])
        self.assertEqual(result['state']['wickets_at_100_overs'], result['state']['total_wickets'])


if __name__ == '__main__':
    unittest.main()
