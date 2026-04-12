"""
seed_data.py — Pre-loads venues, teams, and full squads into ribi.db.
Idempotent: does nothing if any teams already exist.
"""


def seed(db):
    row = db.execute("SELECT COUNT(*) as cnt FROM teams").fetchone()
    if row['cnt'] > 0:
        seed_world_records(db)
        return
    _insert_venues(db)
    _insert_teams(db)
    _insert_players(db)
    _insert_journal_prompts_meta(db)
    seed_world_records(db)
    db.commit()
    print(f"Seed complete.")


# ── Venues ────────────────────────────────────────────────────────────────────

def _insert_venues(db):
    venues = [
        # (name, city, country)
        ("Lord's Cricket Ground",      "London",     "England"),       # 1
        ("The Oval",                    "London",     "England"),       # 2
        ("Melbourne Cricket Ground",    "Melbourne",  "Australia"),     # 3
        ("Sydney Cricket Ground",       "Sydney",     "Australia"),     # 4
        ("Eden Gardens",                "Kolkata",    "India"),         # 5
        ("Wankhede Stadium",            "Mumbai",     "India"),         # 6
        ("Gaddafi Stadium",             "Lahore",     "Pakistan"),      # 7
        ("Newlands",                    "Cape Town",  "South Africa"),  # 8
        ("Eden Park",                   "Auckland",   "New Zealand"),   # 9
        ("Kensington Oval",             "Bridgetown", "West Indies"),   # 10
        ("National Stadium",            "Karachi",    "Pakistan"),      # 11
        ("Headingley",                  "Leeds",      "England"),       # 12
        ("Edgbaston",                   "Birmingham", "England"),       # 13
        ("The Wanderers",               "Johannesburg","South Africa"), # 14
        ("R. Premadasa Stadium",        "Colombo",    "Sri Lanka"),     # 15
        ("Shere Bangla National Stadium","Dhaka",     "Bangladesh"),    # 16
        ("Sharjah Cricket Stadium",     "Sharjah",    "UAE"),           # 17
        ("Dubai International Stadium", "Dubai",      "UAE"),           # 18
    ]
    db.executemany(
        "INSERT INTO venues (name, city, country) VALUES (?, ?, ?)",
        venues
    )


def _venue_id(db, name):
    row = db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


# ── Teams ─────────────────────────────────────────────────────────────────────

def _insert_teams(db):
    # (name, short_code, badge_colour, home_venue_name)
    teams = [
        ("England",      "ENG", "#003366", "Lord's Cricket Ground"),
        ("Australia",    "AUS", "#FFD700", "Melbourne Cricket Ground"),
        ("India",        "IND", "#0080FF", "Eden Gardens"),
        ("Pakistan",     "PAK", "#009900", "Gaddafi Stadium"),
        ("New Zealand",  "NZL", "#000000", "Eden Park"),
        ("South Africa", "RSA", "#006600", "Newlands"),
        ("West Indies",  "WI",  "#7B0041", "Kensington Oval"),
        ("Sri Lanka",    "SL",  "#003580", "R. Premadasa Stadium"),
        ("Bangladesh",   "BAN", "#006A4E", "Shere Bangla National Stadium"),
        ("Afghanistan",  "AFG", "#0033A0", "Sharjah Cricket Stadium"),
    ]
    for name, code, colour, venue_name in teams:
        venue_id = _venue_id(db, venue_name)
        db.execute(
            "INSERT INTO teams (name, short_code, badge_colour, home_venue_id, is_real) "
            "VALUES (?, ?, ?, ?, 1)",
            (name, code, colour, venue_id)
        )


def _team_id(db, name):
    row = db.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


# ── Players ───────────────────────────────────────────────────────────────────
# Each player tuple:
# (team_name, name, pos, bat_rating, bat_hand, bowl_type, bowl_action, bowl_rating)
# bat_rating:  1=tailender, 2=lower-order, 3=useful, 4=good, 5=elite
# bowl_rating: 0=none, 1=part-time, 2=useful, 3=good, 4=very good, 5=elite

SQUADS = [

    # ── ENGLAND ──────────────────────────────────────────────────────────────
    # Bazball era — aggressive top order, pace attack
    ("England", "Z. Crawley",      1, 3, "right", "none",  None,             0),
    ("England", "B. Duckett",      2, 3, "left",  "none",  None,             0),
    ("England", "O. Pope",         3, 4, "right", "none",  None,             0),
    ("England", "J. Root",         4, 5, "right", "spin",  "off-break",      2),
    ("England", "H. Brook",        5, 5, "right", "none",  None,             0),
    ("England", "B. Stokes",       6, 4, "left",  "pace",  "right-arm fast", 3),
    ("England", "J. Bairstow",     7, 4, "right", "none",  None,             0),
    ("England", "C. Woakes",       8, 3, "right", "pace",  "right-arm seam", 4),
    ("England", "G. Atkinson",     9, 2, "right", "pace",  "right-arm fast", 4),
    ("England", "M. Wood",        10, 1, "right", "pace",  "right-arm fast", 4),
    ("England", "S. Bashir",      11, 1, "right", "spin",  "off-break",      4),

    # ── AUSTRALIA ────────────────────────────────────────────────────────────
    # Strong batting, pace-heavy attack
    ("Australia", "U. Khawaja",      1, 4, "left",  "none",  None,                  0),
    ("Australia", "D. Warner",        2, 4, "left",  "none",  None,                  0),
    ("Australia", "M. Labuschagne",   3, 5, "right", "spin",  "leg-break",           2),
    ("Australia", "S. Smith",         4, 5, "right", "spin",  "leg-break",           1),
    ("Australia", "T. Head",          5, 4, "left",  "spin",  "off-break",           2),
    ("Australia", "M. Marsh",         6, 3, "right", "pace",  "right-arm fast-medium",3),
    ("Australia", "A. Inglis",        7, 3, "right", "none",  None,                  0),
    ("Australia", "P. Cummins",       8, 3, "right", "pace",  "right-arm fast",      5),
    ("Australia", "M. Starc",         9, 2, "left",  "pace",  "left-arm fast",       4),
    ("Australia", "N. Lyon",         10, 1, "right", "spin",  "off-break",           4),
    ("Australia", "J. Hazlewood",    11, 1, "right", "pace",  "right-arm fast-medium",4),

    # ── INDIA ────────────────────────────────────────────────────────────────
    # Deep batting, varied bowling
    ("India", "R. Gill",          1, 4, "right", "none",  None,                    0),
    ("India", "Y. Jaiswal",       2, 4, "left",  "none",  None,                    0),
    ("India", "V. Kohli",         3, 5, "right", "none",  None,                    0),
    ("India", "R. Sharma",        4, 4, "right", "spin",  "off-break",              1),
    ("India", "S. Iyer",          5, 4, "right", "none",  None,                    0),
    ("India", "R. Jadeja",        6, 4, "left",  "spin",  "left-arm orthodox",      4),
    ("India", "K. Pant",          7, 4, "left",  "none",  None,                    0),
    ("India", "R. Ashwin",        8, 3, "right", "spin",  "off-break",              5),
    ("India", "M. Shami",         9, 2, "right", "pace",  "right-arm fast-medium",  4),
    ("India", "J. Bumrah",       10, 1, "right", "pace",  "right-arm fast",         5),
    ("India", "M. Siraj",        11, 1, "right", "pace",  "right-arm fast-medium",  3),

    # ── PAKISTAN ─────────────────────────────────────────────────────────────
    # Unpredictable batting, world-class pace
    ("Pakistan", "A. Shafique",    1, 3, "right", "none",  None,                   0),
    ("Pakistan", "I. Masood",      2, 3, "left",  "none",  None,                   0),
    ("Pakistan", "B. Azam",        3, 5, "right", "spin",  "off-break",             1),
    ("Pakistan", "M. Rizwan",      4, 4, "right", "none",  None,                   0),
    ("Pakistan", "S. Masood",      5, 4, "left",  "none",  None,                   0),
    ("Pakistan", "A. Salman",      6, 3, "right", "spin",  "off-break",             3),
    ("Pakistan", "F. Zaman",       7, 3, "left",  "none",  None,                   0),
    ("Pakistan", "S. Afridi",      8, 2, "right", "pace",  "right-arm fast",        4),
    ("Pakistan", "N. Shah",        9, 1, "right", "pace",  "right-arm fast",        5),
    ("Pakistan", "A. Butt",       10, 1, "right", "pace",  "right-arm fast-medium", 3),
    ("Pakistan", "Z. Khan",       11, 1, "left",  "pace",  "left-arm fast",         4),

    # ── NEW ZEALAND ──────────────────────────────────────────────────────────
    # Composed batting, seam movement
    ("New Zealand", "T. Latham",      1, 4, "left",  "none",  None,                   0),
    ("New Zealand", "D. Conway",      2, 4, "left",  "none",  None,                   0),
    ("New Zealand", "K. Williamson",  3, 5, "right", "spin",  "off-break",             1),
    ("New Zealand", "D. Mitchell",    4, 4, "right", "pace",  "right-arm medium",      2),
    ("New Zealand", "G. Phillips",    5, 3, "right", "spin",  "off-break",             2),
    ("New Zealand", "D. Nicholls",    6, 3, "left",  "none",  None,                   0),
    ("New Zealand", "T. Blundell",    7, 3, "right", "none",  None,                   0),
    ("New Zealand", "M. Henry",       8, 2, "right", "pace",  "right-arm fast-medium", 4),
    ("New Zealand", "T. Boult",       9, 1, "left",  "pace",  "left-arm fast-medium",  4),
    ("New Zealand", "N. Wagner",     10, 2, "left",  "pace",  "left-arm fast",          4),
    ("New Zealand", "A. Patel",      11, 2, "left",  "spin",  "left-arm orthodox",      4),

    # ── SOUTH AFRICA ─────────────────────────────────────────────────────────
    # Power batting, express pace
    ("South Africa", "D. Elgar",      1, 4, "left",  "spin",  "left-arm orthodox",     1),
    ("South Africa", "T. Bavuma",     2, 4, "right", "none",  None,                    0),
    ("South Africa", "A. Markram",    3, 4, "right", "spin",  "off-break",              2),
    ("South Africa", "R. van der Dussen",4,4,"right","none",  None,                    0),
    ("South Africa", "D. Miller",     5, 4, "left",  "none",  None,                    0),
    ("South Africa", "M. Jansen",     6, 3, "left",  "pace",  "left-arm fast-medium",   4),
    ("South Africa", "Q. de Kock",    7, 4, "left",  "none",  None,                    0),
    ("South Africa", "K. Rabada",     8, 2, "right", "pace",  "right-arm fast",         5),
    ("South Africa", "A. Nortje",     9, 1, "right", "pace",  "right-arm fast",         4),
    ("South Africa", "K. Maharaj",   10, 2, "right", "spin",  "left-arm orthodox",      4),
    ("South Africa", "G. Coetzee",   11, 1, "right", "pace",  "right-arm fast",          3),

    # ── WEST INDIES ──────────────────────────────────────────────────────────
    # Big hitters, pace and bounce
    ("West Indies", "M. Louis",       1, 3, "right", "none",  None,                   0),
    ("West Indies", "K. Brathwaite",  2, 4, "right", "spin",  "off-break",             1),
    ("West Indies", "K. Mayers",      3, 4, "right", "pace",  "right-arm fast-medium", 3),
    ("West Indies", "R. Chase",       4, 3, "right", "spin",  "off-break",             3),
    ("West Indies", "J. Blackwood",   5, 3, "right", "none",  None,                   0),
    ("West Indies", "A. Athanaze",    6, 3, "left",  "none",  None,                   0),
    ("West Indies", "J. Da Silva",    7, 3, "right", "none",  None,                   0),
    ("West Indies", "J. Holder",      8, 3, "right", "pace",  "right-arm fast-medium", 4),
    ("West Indies", "A. Joseph",      9, 1, "right", "pace",  "right-arm fast",         4),
    ("West Indies", "S. Joseph",     10, 1, "right", "pace",  "right-arm fast",          4),
    ("West Indies", "K. Roach",      11, 1, "right", "pace",  "right-arm fast-medium",  4),

    # ── SRI LANKA ────────────────────────────────────────────────────────────
    # Classical batting, spin-friendly
    ("Sri Lanka", "P. Nissanka",    1, 3, "right", "none",  None,               0),
    ("Sri Lanka", "D. Karunaratne", 2, 4, "left",  "none",  None,               0),
    ("Sri Lanka", "K. Mendis",      3, 4, "right", "none",  None,               0),
    ("Sri Lanka", "A. Mathews",     4, 4, "right", "pace",  "right-arm medium", 2),
    ("Sri Lanka", "D. Chandimal",   5, 4, "right", "none",  None,               0),
    ("Sri Lanka", "D. de Silva",    6, 3, "right", "spin",  "off-break",         3),
    ("Sri Lanka", "N. Dickwella",   7, 3, "left",  "none",  None,               0),
    ("Sri Lanka", "R. Embuldeniya", 8, 2, "left",  "spin",  "left-arm orthodox", 4),
    ("Sri Lanka", "P. Jayawickrama",9, 1, "left",  "spin",  "left-arm orthodox", 4),
    ("Sri Lanka", "L. Kumara",     10, 1, "right", "pace",  "right-arm fast",    4),
    ("Sri Lanka", "A. Fernando",   11, 1, "right", "pace",  "right-arm fast",    3),

    # ── BANGLADESH ───────────────────────────────────────────────────────────
    # Spin strength, improving batting
    ("Bangladesh", "Tamim Iqbal",      1, 4, "left",  "none",  None,                  0),
    ("Bangladesh", "Litton Das",       2, 3, "right", "none",  None,                  0),
    ("Bangladesh", "Najmul Shanto",    3, 3, "left",  "none",  None,                  0),
    ("Bangladesh", "Mominul Haque",    4, 3, "left",  "spin",  "left-arm orthodox",    1),
    ("Bangladesh", "Mushfiqur Rahim",  5, 4, "right", "none",  None,                  0),
    ("Bangladesh", "Shakib Al Hasan",  6, 4, "left",  "spin",  "left-arm orthodox",    4),
    ("Bangladesh", "Mehidy Hasan",     7, 3, "right", "spin",  "off-break",             4),
    ("Bangladesh", "Nurul Hasan",      8, 2, "right", "none",  None,                  0),
    ("Bangladesh", "Taskin Ahmed",     9, 1, "right", "pace",  "right-arm fast-medium", 4),
    ("Bangladesh", "Shoriful Islam",  10, 1, "left",  "pace",  "left-arm fast-medium",  3),
    ("Bangladesh", "Mustafizur Rahman",11,1, "left",  "pace",  "left-arm fast-medium",  4),

    # ── AFGHANISTAN ──────────────────────────────────────────────────────────
    # World-class spin, improving all round
    ("Afghanistan", "Ibrahim Zadran",  1, 3, "right", "none",  None,                  0),
    ("Afghanistan", "Rahmanullah Gurbaz",2,4,"right", "none",  None,                  0),
    ("Afghanistan", "Rhmat Shah",      3, 3, "right", "none",  None,                  0),
    ("Afghanistan", "Hashmatullah Shahidi",4,3,"left","none",  None,                  0),
    ("Afghanistan", "Azmatullah Omarzai",5,3,"right","pace",  "right-arm fast-medium", 3),
    ("Afghanistan", "Najibullah Zadran",6,3,"left",  "none",  None,                  0),
    ("Afghanistan", "Mohammad Nabi",   7, 3, "right", "spin",  "off-break",             3),
    ("Afghanistan", "Rashid Khan",     8, 3, "right", "spin",  "leg-break",             5),
    ("Afghanistan", "Mujeeb Ur Rahman",9, 1, "right", "spin",  "off-break",             4),
    ("Afghanistan", "Noor Ahmad",     10, 1, "left",  "spin",  "left-arm wrist-spin",   4),
    ("Afghanistan", "Fazalhaq Farooqi",11,1,"left",  "pace",  "left-arm fast-medium",   4),
]


def _insert_players(db):
    for row in SQUADS:
        team_name, name, pos, bat_rat, bat_hand, bowl_type, bowl_action, bowl_rat = row
        team_id = _team_id(db, team_name)
        if team_id is None:
            print(f"  WARNING: team '{team_name}' not found for player '{name}'")
            continue
        db.execute(
            "INSERT INTO players "
            "(team_id, name, batting_position, batting_rating, batting_hand, "
            " bowling_type, bowling_action, bowling_rating) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (team_id, name, pos, bat_rat, bat_hand, bowl_type, bowl_action, bowl_rat)
        )


# ── Journal prompts metadata ──────────────────────────────────────────────────
# These are stored in game_engine.JOURNAL_PROMPTS (Section 3).
# Nothing to insert into DB — purely in-memory in game_engine.
def _insert_journal_prompts_meta(db):
    pass  # placeholder for future expansion


# ── Real-world records seeding ────────────────────────────────────────────────

def seed_world_records(db):
    """
    Seeds real-world cricket records as reference benchmarks.
    Displayed in the Honours board alongside in-game records.
    Marked with record_type so they are visually distinguished.
    Idempotent — only seeds if table is empty.
    """
    try:
        cur = db.execute("SELECT COUNT(*) as cnt FROM real_world_records")
        if cur.fetchone()['cnt'] > 0:
            return
    except Exception:
        return  # Table doesn't exist yet — migrations will create it

    records = [
        # ── TEST BATTING ──────────────────────────────────────────────
        {'record_key': 'highest_score_test', 'format': 'Test',
         'record_type': 'batting_score', 'value_runs': 400,
         'display_value': '400*', 'holder_name': 'B.C. Lara',
         'team_name': 'West Indies', 'opponent_name': 'England',
         'venue_name': 'Antigua Recreation Ground', 'match_date': '2004-04-12',
         'notes': 'Highest individual score in Test cricket history'},
        {'record_key': 'most_runs_test', 'format': 'Test',
         'record_type': 'career_runs', 'value_runs': 15921,
         'display_value': '15,921', 'holder_name': 'S.R. Tendulkar',
         'team_name': 'India', 'notes': '200 Tests, 329 innings'},
        {'record_key': 'best_average_test', 'format': 'Test',
         'record_type': 'batting_average', 'value_decimal': 99.94,
         'display_value': '99.94', 'holder_name': 'D.G. Bradman',
         'team_name': 'Australia',
         'notes': '52 Tests, 80 innings, 6996 runs — the greatest batting average in history'},
        {'record_key': 'most_centuries_test', 'format': 'Test',
         'record_type': 'centuries', 'value_runs': 51,
         'display_value': '51', 'holder_name': 'S.R. Tendulkar',
         'team_name': 'India', 'notes': 'Most Test centuries in history'},
        {'record_key': 'highest_partnership_test', 'format': 'Test',
         'record_type': 'partnership', 'value_runs': 624,
         'display_value': '624', 'holder_name': 'K.C. Sangakkara & M.S. Atapattu',
         'team_name': 'Sri Lanka', 'opponent_name': 'South Africa',
         'match_date': '2006-08-04', 'notes': '2nd wicket — highest partnership in Test history'},
        # ── TEST BOWLING ──────────────────────────────────────────────
        {'record_key': 'best_bowling_test', 'format': 'Test',
         'record_type': 'bowling_figures', 'value_wickets': 10,
         'value_runs_conceded': 53, 'display_value': '10/53',
         'holder_name': 'J.C. Laker', 'team_name': 'England',
         'opponent_name': 'Australia', 'venue_name': 'Old Trafford, Manchester',
         'match_date': '1956-07-31', 'notes': 'Best innings figures in Test history'},
        {'record_key': 'most_wickets_test', 'format': 'Test',
         'record_type': 'career_wickets', 'value_wickets': 800,
         'display_value': '800', 'holder_name': 'M. Muralitharan',
         'team_name': 'Sri Lanka', 'notes': '133 Tests — most Test wickets in history'},
        {'record_key': 'best_bowling_average_test', 'format': 'Test',
         'record_type': 'bowling_average', 'value_decimal': 10.75,
         'display_value': '10.75', 'holder_name': 'G.A. Lohmann',
         'team_name': 'England', 'notes': 'Min 25 wickets — Victorian era, 112 wickets'},
        {'record_key': 'most_five_fors_test', 'format': 'Test',
         'record_type': 'five_fors', 'value_wickets': 67,
         'display_value': '67', 'holder_name': 'M. Muralitharan',
         'team_name': 'Sri Lanka', 'notes': 'Most five-wicket hauls in Test history'},
        # ── TEST TEAM ─────────────────────────────────────────────────
        {'record_key': 'highest_team_total_test', 'format': 'Test',
         'record_type': 'team_total', 'value_runs': 952, 'value_wickets': 6,
         'display_value': '952/6 dec', 'team_name': 'Sri Lanka',
         'opponent_name': 'India', 'venue_name': 'R. Premadasa Stadium, Colombo',
         'match_date': '1997-08-06', 'notes': 'Highest team total in Test history'},
        {'record_key': 'lowest_team_total_test', 'format': 'Test',
         'record_type': 'team_total_low', 'value_runs': 26, 'value_wickets': 10,
         'display_value': '26 all out', 'team_name': 'New Zealand',
         'opponent_name': 'England', 'venue_name': 'Basin Reserve, Wellington',
         'match_date': '1955-03-28', 'notes': 'Lowest team total in Test history'},
        {'record_key': 'biggest_win_runs_test', 'format': 'Test',
         'record_type': 'win_margin', 'value_runs': 675,
         'display_value': '675 runs', 'team_name': 'England',
         'opponent_name': 'Australia', 'venue_name': 'Brisbane Cricket Ground',
         'match_date': '1928-12-01', 'notes': 'Largest victory margin by runs in Tests'},
        # ── ODI BATTING ───────────────────────────────────────────────
        {'record_key': 'highest_score_odi', 'format': 'ODI',
         'record_type': 'batting_score', 'value_runs': 264,
         'display_value': '264', 'holder_name': 'R.R. Rohit Sharma',
         'team_name': 'India', 'opponent_name': 'Sri Lanka',
         'venue_name': 'Eden Gardens, Kolkata', 'match_date': '2014-11-13',
         'notes': 'Highest individual score in ODI history'},
        {'record_key': 'most_runs_odi', 'format': 'ODI',
         'record_type': 'career_runs', 'value_runs': 18426,
         'display_value': '18,426', 'holder_name': 'S.R. Tendulkar',
         'team_name': 'India', 'notes': '463 innings — most ODI runs in history'},
        {'record_key': 'best_average_odi', 'format': 'ODI',
         'record_type': 'batting_average', 'value_decimal': 53.58,
         'display_value': '53.58', 'holder_name': 'M.S. Dhoni',
         'team_name': 'India', 'notes': 'Min 70 innings'},
        {'record_key': 'most_centuries_odi', 'format': 'ODI',
         'record_type': 'centuries', 'value_runs': 49,
         'display_value': '49', 'holder_name': 'S.R. Tendulkar',
         'team_name': 'India', 'notes': 'Most ODI centuries in history'},
        {'record_key': 'highest_team_total_odi', 'format': 'ODI',
         'record_type': 'team_total', 'value_runs': 481, 'value_wickets': 6,
         'display_value': '481/6', 'team_name': 'England',
         'opponent_name': 'Australia', 'venue_name': 'Trent Bridge, Nottingham',
         'match_date': '2018-06-19', 'notes': 'Highest ODI team total in history'},
        {'record_key': 'lowest_team_total_odi', 'format': 'ODI',
         'record_type': 'team_total_low', 'value_runs': 35, 'value_wickets': 10,
         'display_value': '35 all out', 'team_name': 'Zimbabwe',
         'opponent_name': 'Sri Lanka', 'match_date': '2004-04-25',
         'notes': 'Lowest ODI team total in history'},
        # ── ODI BOWLING ───────────────────────────────────────────────
        {'record_key': 'best_bowling_odi', 'format': 'ODI',
         'record_type': 'bowling_figures', 'value_wickets': 8,
         'value_runs_conceded': 19, 'display_value': '8/19',
         'holder_name': 'C.J. Anderson', 'team_name': 'New Zealand',
         'opponent_name': 'West Indies', 'match_date': '2014-01-01',
         'notes': 'Best bowling figures in ODI history'},
        {'record_key': 'most_wickets_odi', 'format': 'ODI',
         'record_type': 'career_wickets', 'value_wickets': 534,
         'display_value': '534', 'holder_name': 'M. Muralitharan',
         'team_name': 'Sri Lanka', 'notes': 'Most ODI wickets in history'},
        {'record_key': 'best_economy_odi', 'format': 'ODI',
         'record_type': 'economy', 'value_decimal': 3.09,
         'display_value': '3.09', 'holder_name': 'J. Garner',
         'team_name': 'West Indies',
         'notes': 'Best career economy rate in ODIs (min 50 wickets)'},
        # ── T20 BATTING ───────────────────────────────────────────────
        {'record_key': 'highest_score_t20', 'format': 'T20',
         'record_type': 'batting_score', 'value_runs': 172,
         'display_value': '172*', 'holder_name': 'A.J. Finch',
         'team_name': 'Australia', 'opponent_name': 'Zimbabwe',
         'venue_name': 'Harare Sports Club', 'match_date': '2018-07-03',
         'notes': 'Highest individual score in T20I history'},
        {'record_key': 'most_runs_t20', 'format': 'T20',
         'record_type': 'career_runs', 'value_runs': 4357,
         'display_value': '4,357', 'holder_name': 'V. Kohli',
         'team_name': 'India', 'notes': 'Most T20I runs in history (to 2024)'},
        {'record_key': 'highest_team_total_t20', 'format': 'T20',
         'record_type': 'team_total', 'value_runs': 314, 'value_wickets': 3,
         'display_value': '314/3', 'team_name': 'Czech Republic',
         'opponent_name': 'Turkey', 'match_date': '2019-08-22',
         'notes': 'Highest T20I total (associate). Full Members: 278/3 — Afghanistan'},
        {'record_key': 'lowest_team_total_t20', 'format': 'T20',
         'record_type': 'team_total_low', 'value_runs': 6, 'value_wickets': 10,
         'display_value': '6 all out', 'team_name': 'Maldives',
         'opponent_name': 'Bhutan', 'match_date': '2019-10-05',
         'notes': 'Lowest T20I total. Full Members: 39 all out — Sri Lanka'},
        # ── T20 BOWLING ───────────────────────────────────────────────
        {'record_key': 'best_bowling_t20', 'format': 'T20',
         'record_type': 'bowling_figures', 'value_wickets': 6,
         'value_runs_conceded': 7, 'display_value': '6/7',
         'holder_name': 'Oman player', 'team_name': 'Oman',
         'notes': 'Best T20I bowling figures. Full Members: 6/8 — S.C.J. Broad'},
        {'record_key': 'most_wickets_t20', 'format': 'T20',
         'record_type': 'career_wickets', 'value_wickets': 147,
         'display_value': '147', 'holder_name': 'Shaheen Shah Afridi',
         'team_name': 'Pakistan', 'notes': 'Most T20I wickets in history (to 2024)'},
        {'record_key': 'best_economy_t20', 'format': 'T20',
         'record_type': 'economy', 'value_decimal': 5.73,
         'display_value': '5.73', 'holder_name': 'Umar Gul',
         'team_name': 'Pakistan', 'notes': 'Best T20I economy rate (min 30 wickets)'},
    ]

    insert_sql = (
        "INSERT INTO real_world_records "
        "(record_key, format, record_type, value_runs, value_wickets, "
        " value_runs_conceded, value_decimal, display_value, "
        " holder_name, team_name, opponent_name, venue_name, match_date, notes) "
        "VALUES "
        "(:record_key, :format, :record_type, :value_runs, :value_wickets, "
        " :value_runs_conceded, :value_decimal, :display_value, "
        " :holder_name, :team_name, :opponent_name, :venue_name, :match_date, :notes)"
    )
    defaults = {'value_runs': None, 'value_wickets': None, 'value_runs_conceded': None,
                'value_decimal': None, 'holder_name': None, 'team_name': None,
                'opponent_name': None, 'venue_name': None, 'match_date': None, 'notes': None}
    for r in records:
        row = {**defaults, **r}
        db.execute(insert_sql, row)
    db.commit()
