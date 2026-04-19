-- TEAMS
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    short_code TEXT,
    badge_colour TEXT,
    home_venue_id INTEGER,
    is_real INTEGER DEFAULT 0,
    is_custom INTEGER DEFAULT 0,
    team_type TEXT DEFAULT 'international',
    league TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PLAYERS
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    batting_position INTEGER,
    batting_rating INTEGER CHECK(batting_rating BETWEEN 1 AND 5),
    batting_hand TEXT CHECK(batting_hand IN ('right','left')),
    bowling_type TEXT CHECK(bowling_type IN ('pace','spin','none')),
    bowling_action TEXT,
    bowling_rating INTEGER CHECK(bowling_rating BETWEEN 0 AND 5),
    source_world_id INTEGER,
    is_regen INTEGER DEFAULT 0,
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- VENUES
CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT,
    country TEXT,
    is_custom INTEGER DEFAULT 0
);

-- WORLDS
CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_date TEXT,
    current_date TEXT,
    calendar_density TEXT CHECK(calendar_density IN ('busy','moderate','relaxed')),
    settings_json TEXT,
    is_active INTEGER DEFAULT 0
);

-- SERIES
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    format TEXT CHECK(format IN ('Test','ODI','T20')),
    series_type TEXT,
    world_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    team1_id INTEGER,
    team2_id INTEGER,
    winner_team_id INTEGER,
    status TEXT DEFAULT 'scheduled',
    settings_json TEXT,
    FOREIGN KEY (world_id) REFERENCES worlds(id),
    FOREIGN KEY (team1_id) REFERENCES teams(id),
    FOREIGN KEY (team2_id) REFERENCES teams(id)
);

-- TOURNAMENTS
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    format TEXT,
    tournament_type TEXT,
    world_id INTEGER,
    start_date TEXT,
    status TEXT DEFAULT 'scheduled',
    settings_json TEXT,
    winner_team_id INTEGER,
    FOREIGN KEY (world_id) REFERENCES worlds(id)
);

-- TOURNAMENT TEAMS
CREATE TABLE IF NOT EXISTS tournament_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    group_name TEXT,
    played INTEGER DEFAULT 0,
    won INTEGER DEFAULT 0,
    lost INTEGER DEFAULT 0,
    drawn INTEGER DEFAULT 0,
    no_result INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    runs_scored INTEGER DEFAULT 0,
    overs_faced REAL DEFAULT 0,
    runs_conceded INTEGER DEFAULT 0,
    overs_bowled REAL DEFAULT 0,
    nrr REAL DEFAULT 0,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- FIXTURES
CREATE TABLE IF NOT EXISTS fixtures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER,
    series_id INTEGER,
    world_id INTEGER,
    match_id INTEGER,
    scheduled_date TEXT,
    venue_id INTEGER,
    team1_id INTEGER,
    team2_id INTEGER,
    fixture_type TEXT,
    status TEXT DEFAULT 'scheduled',
    format TEXT,
    is_user_match INTEGER DEFAULT 0,
    series_name TEXT,
    match_number_in_series INTEGER DEFAULT 1,
    series_length INTEGER DEFAULT 1,
    is_icc_event INTEGER DEFAULT 0,
    icc_event_name TEXT,
    is_home_for_team1 INTEGER DEFAULT 1,
    tour_template TEXT,
    season_year INTEGER,
    competition_key TEXT,
    competition_name TEXT,
    competition_stage TEXT,
    competition_group TEXT,
    competition_round TEXT,
    competition_order INTEGER,
    FOREIGN KEY (venue_id) REFERENCES venues(id)
);

-- MATCHES
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER,
    tournament_id INTEGER,
    world_id INTEGER,
    format TEXT CHECK(format IN ('Test','ODI','T20')),
    venue_id INTEGER NOT NULL,
    match_date TEXT NOT NULL,
    team1_id INTEGER NOT NULL,
    team2_id INTEGER NOT NULL,
    toss_winner_id INTEGER,
    toss_choice TEXT CHECK(toss_choice IN ('bat','field')),
    result_type TEXT CHECK(result_type IN ('runs','wickets','draw','tie','no_result')),
    winning_team_id INTEGER,
    margin_runs INTEGER,
    margin_wickets INTEGER,
    player_of_match_id INTEGER,
    status TEXT DEFAULT 'in_progress',
    scoring_mode TEXT DEFAULT 'modern',
    match_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (series_id) REFERENCES series(id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
    FOREIGN KEY (world_id) REFERENCES worlds(id),
    FOREIGN KEY (venue_id) REFERENCES venues(id),
    FOREIGN KEY (team1_id) REFERENCES teams(id),
    FOREIGN KEY (team2_id) REFERENCES teams(id)
);

-- INNINGS
CREATE TABLE IF NOT EXISTS innings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    innings_number INTEGER NOT NULL,
    batting_team_id INTEGER NOT NULL,
    bowling_team_id INTEGER NOT NULL,
    total_runs INTEGER DEFAULT 0,
    total_wickets INTEGER DEFAULT 0,
    overs_completed REAL DEFAULT 0,
    runs_at_100_overs INTEGER,
    wickets_at_100_overs INTEGER,
    runs_at_110_overs INTEGER,
    wickets_at_110_overs INTEGER,
    extras_byes INTEGER DEFAULT 0,
    extras_legbyes INTEGER DEFAULT 0,
    extras_wides INTEGER DEFAULT 0,
    extras_noballs INTEGER DEFAULT 0,
    declared INTEGER DEFAULT 0,
    follow_on INTEGER DEFAULT 0,
    status TEXT DEFAULT 'in_progress',
    FOREIGN KEY (match_id) REFERENCES matches(id)
);

-- BATTER INNINGS
CREATE TABLE IF NOT EXISTS batter_innings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    batting_position INTEGER,
    runs INTEGER DEFAULT 0,
    balls_faced INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    dismissal_type TEXT,
    bowler_id INTEGER,
    fielder_id INTEGER,
    not_out INTEGER DEFAULT 0,
    retired_hurt INTEGER DEFAULT 0,
    status TEXT DEFAULT 'yet_to_bat',
    FOREIGN KEY (innings_id) REFERENCES innings(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- BOWLER INNINGS
CREATE TABLE IF NOT EXISTS bowler_innings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    overs INTEGER DEFAULT 0,
    balls INTEGER DEFAULT 0,
    maidens INTEGER DEFAULT 0,
    runs_conceded INTEGER DEFAULT 0,
    wickets INTEGER DEFAULT 0,
    wides INTEGER DEFAULT 0,
    no_balls INTEGER DEFAULT 0,
    FOREIGN KEY (innings_id) REFERENCES innings(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- PARTNERSHIPS
CREATE TABLE IF NOT EXISTS partnerships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL,
    wicket_number INTEGER NOT NULL,
    batter1_id INTEGER NOT NULL,
    batter2_id INTEGER NOT NULL,
    runs INTEGER DEFAULT 0,
    balls INTEGER DEFAULT 0,
    FOREIGN KEY (innings_id) REFERENCES innings(id)
);

-- DELIVERIES
CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL,
    over_number INTEGER NOT NULL,
    ball_number INTEGER NOT NULL,
    bowler_id INTEGER NOT NULL,
    striker_id INTEGER NOT NULL,
    non_striker_id INTEGER NOT NULL,
    stage1_roll INTEGER,
    stage2_roll INTEGER,
    stage3_roll INTEGER,
    stage4_roll INTEGER,
    stage4b_roll INTEGER,
    outcome_type TEXT,
    runs_scored INTEGER DEFAULT 0,
    extras_type TEXT,
    extras_runs INTEGER DEFAULT 0,
    dismissal_type TEXT,
    dismissed_batter_id INTEGER,
    shot_angle REAL,
    is_free_hit INTEGER DEFAULT 0,
    is_wide INTEGER DEFAULT 0,
    is_no_ball INTEGER DEFAULT 0,
    commentary TEXT,
    FOREIGN KEY (innings_id) REFERENCES innings(id),
    FOREIGN KEY (bowler_id) REFERENCES players(id),
    FOREIGN KEY (striker_id) REFERENCES players(id)
);

-- FALL OF WICKETS
CREATE TABLE IF NOT EXISTS fall_of_wickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    innings_id INTEGER NOT NULL,
    wicket_number INTEGER NOT NULL,
    score_at_fall INTEGER NOT NULL,
    overs_at_fall REAL NOT NULL,
    dismissed_batter_id INTEGER NOT NULL,
    FOREIGN KEY (innings_id) REFERENCES innings(id)
);

-- WORLD RANKINGS
CREATE TABLE IF NOT EXISTS world_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    format TEXT NOT NULL,
    points REAL DEFAULT 0,
    position INTEGER,
    matches_counted INTEGER DEFAULT 0,
    updated_date TEXT,
    FOREIGN KEY (world_id) REFERENCES worlds(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- RANKING HISTORY
CREATE TABLE IF NOT EXISTS ranking_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    format TEXT NOT NULL,
    points REAL,
    position INTEGER,
    snapshot_date TEXT,
    after_match_id INTEGER,
    FOREIGN KEY (world_id) REFERENCES worlds(id)
);

-- MATCH JOURNAL
CREATE TABLE IF NOT EXISTS match_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    note_text TEXT,
    note_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches(id)
);

-- WORLD RECORDS
CREATE TABLE IF NOT EXISTS world_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER,
    record_key TEXT NOT NULL,
    record_value REAL,
    context_json TEXT,
    format TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PLAYER WORLD STATE
CREATE TABLE IF NOT EXISTS player_world_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    form_adjustment INTEGER DEFAULT 0,
    fatigue INTEGER DEFAULT 0,
    career_runs INTEGER DEFAULT 0,
    career_wickets INTEGER DEFAULT 0,
    career_matches INTEGER DEFAULT 0,
    last_match_dates TEXT DEFAULT '[]',
    age INTEGER,
    last_age_year INTEGER,
    active INTEGER DEFAULT 1,
    retirement_reason TEXT,
    retired_on TEXT,
    regen_generation INTEGER DEFAULT 0,
    retire_age INTEGER,
    UNIQUE(world_id, player_id),
    FOREIGN KEY (world_id) REFERENCES worlds(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_deliveries_innings ON deliveries(innings_id);
CREATE INDEX IF NOT EXISTS idx_batter_innings_player ON batter_innings(player_id);
CREATE INDEX IF NOT EXISTS idx_bowler_innings_player ON bowler_innings(player_id);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(team1_id, team2_id);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_ranking_history ON ranking_history(world_id, format, team_id);

-- VIEWS
CREATE VIEW IF NOT EXISTS batting_averages AS
SELECT
    p.id as player_id,
    p.name,
    t.name as team_name,
    t.id as team_id,
    m.format,
    COALESCE(m.canon_status, 'canon') as canon_status,
    COUNT(DISTINCT m.id) as matches,
    COUNT(bi.id) as innings,
    SUM(bi.not_out) as not_outs,
    SUM(bi.runs) as runs,
    MAX(bi.runs) as highest_score,
    ROUND(CAST(SUM(bi.runs) AS REAL) /
          NULLIF(COUNT(bi.id) - SUM(bi.not_out), 0), 2) as average,
    ROUND(CAST(SUM(bi.runs) AS REAL) /
          NULLIF(SUM(bi.balls_faced), 0) * 100, 2) as strike_rate,
    SUM(CASE WHEN bi.runs >= 100 THEN 1 ELSE 0 END) as hundreds,
    SUM(CASE WHEN bi.runs >= 50 AND bi.runs < 100 THEN 1 ELSE 0 END) as fifties,
    SUM(CASE WHEN bi.runs = 0 AND bi.not_out = 0 THEN 1 ELSE 0 END) as ducks,
    SUM(bi.fours) as fours,
    SUM(bi.sixes) as sixes,
    SUM(bi.balls_faced) as balls_faced
FROM batter_innings bi
JOIN innings i ON bi.innings_id = i.id
JOIN matches m ON i.match_id = m.id
JOIN players p ON bi.player_id = p.id
JOIN teams t ON p.team_id = t.id
WHERE (bi.status = 'dismissed' OR bi.not_out = 1)
  AND COALESCE(m.canon_status, 'canon') = 'canon'
GROUP BY p.id, m.format, COALESCE(m.canon_status, 'canon');

CREATE VIEW IF NOT EXISTS bowling_averages AS
SELECT
    p.id as player_id,
    p.name,
    p.bowling_type,
    t.name as team_name,
    t.id as team_id,
    m.format,
    COALESCE(m.canon_status, 'canon') as canon_status,
    COUNT(DISTINCT m.id) as matches,
    COUNT(bwi.id) as innings_bowled,
    SUM(bwi.overs) as overs,
    SUM(bwi.maidens) as maidens,
    SUM(bwi.runs_conceded) as runs_conceded,
    SUM(bwi.wickets) as wickets,
    ROUND(CAST(SUM(bwi.runs_conceded) AS REAL) /
          NULLIF(SUM(bwi.wickets), 0), 2) as average,
    ROUND(CAST(SUM(bwi.runs_conceded) AS REAL) /
          NULLIF(SUM(bwi.overs), 0), 2) as economy,
    ROUND(CAST(SUM(bwi.overs) * 6 AS REAL) /
          NULLIF(SUM(bwi.wickets), 0), 2) as strike_rate,
    SUM(CASE WHEN bwi.wickets >= 5 THEN 1 ELSE 0 END) as five_fors
FROM bowler_innings bwi
JOIN innings i ON bwi.innings_id = i.id
JOIN matches m ON i.match_id = m.id
JOIN players p ON bwi.player_id = p.id
JOIN teams t ON p.team_id = t.id
WHERE bwi.overs > 0
  AND COALESCE(m.canon_status, 'canon') = 'canon'
GROUP BY p.id, m.format, COALESCE(m.canon_status, 'canon');

CREATE VIEW IF NOT EXISTS team_records_view AS
SELECT
    t.id as team_id,
    t.name as team_name,
    m.format,
    COUNT(DISTINCT m.id) as matches_played,
    SUM(CASE WHEN m.winning_team_id = t.id THEN 1 ELSE 0 END) as won,
    SUM(CASE WHEN m.winning_team_id != t.id AND m.result_type NOT IN ('draw','tie','no_result') THEN 1 ELSE 0 END) as lost,
    SUM(CASE WHEN m.result_type = 'draw' THEN 1 ELSE 0 END) as drawn,
    SUM(CASE WHEN m.result_type = 'tie' THEN 1 ELSE 0 END) as tied
FROM teams t
JOIN matches m ON (m.team1_id = t.id OR m.team2_id = t.id)
WHERE m.status = 'complete'
  AND COALESCE(m.canon_status, 'canon') = 'canon'
GROUP BY t.id, m.format;

CREATE VIEW IF NOT EXISTS partnership_records AS
SELECT
    p.id,
    p.innings_id,
    p.wicket_number,
    p.runs,
    p.balls,
    b1.name as batter1_name,
    b2.name as batter2_name,
    p.batter1_id,
    p.batter2_id,
    m.format,
    i.match_id
FROM partnerships p
JOIN players b1 ON p.batter1_id = b1.id
JOIN players b2 ON p.batter2_id = b2.id
JOIN innings i ON p.innings_id = i.id
JOIN matches m ON i.match_id = m.id
WHERE COALESCE(m.canon_status, 'canon') = 'canon';

-- REAL WORLD RECORDS
CREATE TABLE IF NOT EXISTS real_world_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_key TEXT NOT NULL,
    format TEXT NOT NULL,
    record_type TEXT NOT NULL,
    value_runs INTEGER,
    value_wickets INTEGER,
    value_runs_conceded INTEGER,
    value_decimal REAL,
    display_value TEXT NOT NULL,
    holder_name TEXT,
    team_name TEXT,
    opponent_name TEXT,
    venue_name TEXT,
    match_date TEXT,
    notes TEXT
);
