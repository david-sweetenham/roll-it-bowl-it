"""
seed_domestic/psl.py
Pakistan Super League: 6 franchise teams.
"""

VENUES = [
    ("Rawalpindi Cricket Stadium", "Rawalpindi", "Pakistan"),
    ("Multan Cricket Stadium",     "Multan",     "Pakistan"),
]

# (name, short_code, badge_colour, home_venue_name, team_type, league)
TEAMS = [
    ("Karachi Kings",      "KAR", "#15375A", "National Stadium",            "franchise", "PSL"),
    ("Lahore Qalandars",   "LAH", "#006633", "Gaddafi Stadium",             "franchise", "PSL"),
    ("Multan Sultans",     "MUL", "#8B0000", "Multan Cricket Stadium",      "franchise", "PSL"),
    ("Peshawar Zalmi",     "PES", "#FFD700", "Arbab Niaz Stadium",          "franchise", "PSL"),
    ("Quetta Gladiators",  "QUE", "#CC0000", "Bugti Stadium",               "franchise", "PSL"),
    ("Islamabad United",   "ISL", "#CC0000", "Rawalpindi Cricket Stadium",  "franchise", "PSL"),
]

SQUADS = [

    # ── KARACHI KINGS ──
    ("Karachi Kings", "B. Azam",          1, 5, "right", "spin", "off-break",             1),
    ("Karachi Kings", "S. Sharjeel",      2, 4, "left",  "none", None,                    0),
    ("Karachi Kings", "M. Rizwan",        3, 4, "right", "none", None,                    0),
    ("Karachi Kings", "A. Khan",          4, 3, "right", "none", None,                    0),
    ("Karachi Kings", "I. Khan",          5, 3, "right", "none", None,                    0),
    ("Karachi Kings", "D. Wiese",         6, 3, "right", "pace", "right-arm fast-medium", 3),
    ("Karachi Kings", "A. Amin",          7, 2, "right", "pace", "right-arm seam",        3),
    ("Karachi Kings", "H. Ali",           8, 2, "right", "pace", "right-arm fast",        4),
    ("Karachi Kings", "A. Khan Dur",      9, 1, "right", "pace", "right-arm fast",        3),
    ("Karachi Kings", "U. Ahmed",        10, 1, "right", "spin", "off-break",             3),
    ("Karachi Kings", "M. Hasnain",      11, 1, "right", "pace", "right-arm fast",        4),

    # ── LAHORE QALANDARS ──
    ("Lahore Qalandars", "F. Zaman",      1, 3, "left",  "none", None,                    0),
    ("Lahore Qalandars", "S. Masood",     2, 4, "left",  "none", None,                    0),
    ("Lahore Qalandars", "A. Abdullah",   3, 3, "right", "none", None,                    0),
    ("Lahore Qalandars", "R. Riaz",       4, 3, "right", "none", None,                    0),
    ("Lahore Qalandars", "S. Amir",       5, 3, "left",  "none", None,                    0),
    ("Lahore Qalandars", "D. Aziz",       6, 3, "right", "pace", "right-arm seam",        2),
    ("Lahore Qalandars", "Z. Khan",       7, 2, "left",  "pace", "left-arm fast",         4),
    ("Lahore Qalandars", "H. Rauf",       8, 1, "right", "pace", "right-arm fast",        5),
    ("Lahore Qalandars", "L. Meriwala",   9, 1, "right", "pace", "right-arm fast-medium", 3),
    ("Lahore Qalandars", "A. Afridi",    10, 1, "right", "pace", "right-arm fast",        3),
    ("Lahore Qalandars", "S. Irfan",     11, 1, "right", "pace", "right-arm fast",        3),

    # ── MULTAN SULTANS ──
    ("Multan Sultans", "M. Rizwan",       1, 4, "right", "none", None,                    0),
    ("Multan Sultans", "R. Ali",          2, 4, "right", "none", None,                    0),
    ("Multan Sultans", "S. Masood",       3, 4, "left",  "none", None,                    0),
    ("Multan Sultans", "T. Iqbal",        4, 3, "right", "none", None,                    0),
    ("Multan Sultans", "U. Amin",         5, 3, "right", "none", None,                    0),
    ("Multan Sultans", "K. Afridi",       6, 3, "right", "pace", "right-arm fast-medium", 3),
    ("Multan Sultans", "I. Wasim",        7, 3, "left",  "pace", "left-arm fast",         3),
    ("Multan Sultans", "N. Shah",         8, 2, "right", "pace", "right-arm fast",        5),
    ("Multan Sultans", "A. Naseem",       9, 1, "right", "pace", "right-arm fast",        4),
    ("Multan Sultans", "U. Mir",         10, 1, "right", "pace", "right-arm fast",        3),
    ("Multan Sultans", "A. Rauf",        11, 1, "right", "spin", "off-break",             3),

    # ── PESHAWAR ZALMI ──
    ("Peshawar Zalmi", "K. Akmal",        1, 4, "right", "none", None,                    0),
    ("Peshawar Zalmi", "S. Butt",         2, 3, "left",  "none", None,                    0),
    ("Peshawar Zalmi", "B. Azam",         3, 5, "right", "spin", "off-break",             1),
    ("Peshawar Zalmi", "L. Simmons",      4, 3, "right", "none", None,                    0),
    ("Peshawar Zalmi", "D. Sammy",        5, 3, "right", "pace", "right-arm fast-medium", 3),
    ("Peshawar Zalmi", "M. Nawaz",        6, 3, "right", "spin", "off-break",             3),
    ("Peshawar Zalmi", "U. Amin",         7, 3, "right", "none", None,                    0),
    ("Peshawar Zalmi", "W. Riaz",         8, 2, "right", "pace", "right-arm fast",        4),
    ("Peshawar Zalmi", "H. Ali",          9, 1, "right", "pace", "right-arm fast",        4),
    ("Peshawar Zalmi", "T. Naseem",      10, 1, "right", "pace", "right-arm fast",        3),
    ("Peshawar Zalmi", "S. Afridi",      11, 1, "right", "pace", "right-arm fast",        4),

    # ── QUETTA GLADIATORS ──
    ("Quetta Gladiators", "A. Shafique",  1, 3, "right", "none", None,                    0),
    ("Quetta Gladiators", "S. Aslam",     2, 3, "right", "none", None,                    0),
    ("Quetta Gladiators", "S. Maqsood",   3, 3, "right", "none", None,                    0),
    ("Quetta Gladiators", "J. Roy",       4, 4, "right", "none", None,                    0),
    ("Quetta Gladiators", "K. Pollard",   5, 4, "right", "pace", "right-arm fast-medium", 3),
    ("Quetta Gladiators", "M. Hafeez",    6, 3, "right", "spin", "off-break",             2),
    ("Quetta Gladiators", "U. Akmal",     7, 3, "right", "none", None,                    0),
    ("Quetta Gladiators", "F. Rauf",      8, 2, "right", "pace", "right-arm fast",        4),
    ("Quetta Gladiators", "N. Afridi",    9, 1, "right", "pace", "right-arm fast",        3),
    ("Quetta Gladiators", "N. Memon",    10, 1, "right", "spin", "leg-break",             3),
    ("Quetta Gladiators", "M. Amir",     11, 1, "left",  "pace", "left-arm fast",         4),

    # ── ISLAMABAD UNITED ──
    ("Islamabad United", "A. Ali",        1, 4, "right", "none", None,                    0),
    ("Islamabad United", "P. Stirling",   2, 4, "right", "spin", "off-break",             2),
    ("Islamabad United", "U. Akhtar",     3, 3, "right", "none", None,                    0),
    ("Islamabad United", "A. Salman",     4, 3, "right", "spin", "off-break",             3),
    ("Islamabad United", "C. Delport",    5, 3, "right", "none", None,                    0),
    ("Islamabad United", "F. Azam",       6, 3, "right", "none", None,                    0),
    ("Islamabad United", "H. Azam",       7, 3, "right", "none", None,                    0),
    ("Islamabad United", "S. Tanvir",     8, 2, "left",  "pace", "left-arm fast",         4),
    ("Islamabad United", "Z. Khan",       9, 1, "right", "pace", "right-arm fast",        4),
    ("Islamabad United", "A. Butt",      10, 1, "right", "pace", "right-arm fast-medium", 3),
    ("Islamabad United", "S. Amir",      11, 1, "left",  "pace", "left-arm fast",         4),
]

# Peshawar Zalmi & Quetta Gladiators share Arbab Niaz and Bugti stadiums
# which we add inline as they're not major international grounds
_EXTRA_VENUES = [
    ("Arbab Niaz Stadium", "Peshawar", "Pakistan"),
    ("Bugti Stadium",      "Quetta",   "Pakistan"),
]


def _venue_id(db, name):
    row = db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


def _team_id(db, name):
    row = db.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


def seed(db):
    for name, city, country in VENUES + _EXTRA_VENUES:
        if not db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone():
            db.execute("INSERT INTO venues (name, city, country) VALUES (?,?,?)",
                       (name, city, country))

    for name, code, colour, venue_name, team_type, league in TEAMS:
        if not db.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone():
            vid = _venue_id(db, venue_name)
            db.execute(
                "INSERT INTO teams (name, short_code, badge_colour, home_venue_id, "
                "is_real, team_type, league) VALUES (?,?,?,?,1,?,?)",
                (name, code, colour, vid, team_type, league)
            )

    for row in SQUADS:
        team_name, pname, pos, bat_r, bat_hand, bowl_type, bowl_action, bowl_r = row
        tid = _team_id(db, team_name)
        if not tid:
            continue
        if not db.execute("SELECT id FROM players WHERE team_id=? AND name=?",
                          (tid, pname)).fetchone():
            db.execute(
                "INSERT INTO players (team_id, name, batting_position, batting_rating, "
                "batting_hand, bowling_type, bowling_action, bowling_rating) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (tid, pname, pos, bat_r, bat_hand, bowl_type, bowl_action, bowl_r)
            )
