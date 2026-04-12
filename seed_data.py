"""
seed_data.py — Pre-loads venues, teams, and full squads into ribi.db.
Idempotent: does nothing if any teams already exist.
"""


def seed(db):
    row = db.execute("SELECT COUNT(*) as cnt FROM teams").fetchone()
    if row['cnt'] > 0:
        return
    _insert_venues(db)
    _insert_teams(db)
    _insert_players(db)
    _insert_journal_prompts_meta(db)
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
