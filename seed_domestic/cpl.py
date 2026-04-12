"""
seed_domestic/cpl.py
Caribbean Premier League: 6 franchise teams.
"""

VENUES = [
    ("Queen's Park Oval",                    "Port of Spain", "West Indies"),
    ("Providence Stadium",                   "Guyana",        "West Indies"),
    ("Sabina Park",                          "Kingston",      "West Indies"),
    ("Warner Park",                          "Basseterre",    "West Indies"),
    ("Daren Sammy National Cricket Stadium", "Gros Islet",    "West Indies"),
    ("National Cricket Stadium Grenada",     "St George's",   "West Indies"),
]

# (name, short_code, badge_colour, home_venue_name, team_type, league)
TEAMS = [
    ("Barbados Royals",         "BAR", "#003DA5", "Kensington Oval",                        "franchise", "CPL"),
    ("Guyana Amazon Warriors",  "GAW", "#00813A", "Providence Stadium",                     "franchise", "CPL"),
    ("Jamaica Tallawahs",       "JAM", "#FFD100", "Sabina Park",                            "franchise", "CPL"),
    ("St Kitts & Nevis Patriots","SKN","#8B0000",  "Warner Park",                           "franchise", "CPL"),
    ("Trinbago Knight Riders",  "TKR", "#3A225D", "Queen's Park Oval",                      "franchise", "CPL"),
    ("St Lucia Kings",          "SLK", "#1B4F8A", "Daren Sammy National Cricket Stadium",   "franchise", "CPL"),
]

SQUADS = [

    # ── BARBADOS ROYALS ──
    ("Barbados Royals", "J. Blackwood",       1, 3, "right", "none", None,                  0),
    ("Barbados Royals", "S. Hope",            2, 4, "right", "none", None,                  0),
    ("Barbados Royals", "K. Mayers",          3, 4, "right", "pace", "right-arm fast-medium",2),
    ("Barbados Royals", "A. Athanaze",        4, 3, "right", "none", None,                  0),
    ("Barbados Royals", "R. Chase",           5, 3, "right", "spin", "off-break",           3),
    ("Barbados Royals", "J. Greaves",         6, 3, "right", "none", None,                  0),
    ("Barbados Royals", "J. Holder",          7, 3, "right", "pace", "right-arm fast-medium",4),
    ("Barbados Royals", "T. Cork",            8, 2, "right", "pace", "right-arm fast",      3),
    ("Barbados Royals", "A. Seales",          9, 1, "right", "pace", "right-arm fast",      4),
    ("Barbados Royals", "K. Pierre",         10, 1, "right", "spin", "off-break",           3),
    ("Barbados Royals", "L. Sebastien",      11, 1, "right", "pace", "right-arm seam",      3),

    # ── GUYANA AMAZON WARRIORS ──
    ("Guyana Amazon Warriors", "B. King",     1, 4, "right", "none", None,                  0),
    ("Guyana Amazon Warriors", "C. Hemraj",   2, 3, "left",  "none", None,                  0),
    ("Guyana Amazon Warriors", "S. Hetmyer",  3, 4, "left",  "none", None,                  0),
    ("Guyana Amazon Warriors", "N. Pooran",   4, 5, "left",  "none", None,                  0),
    ("Guyana Amazon Warriors", "R. Reifer",   5, 3, "left",  "pace", "left-arm fast-medium",2),
    ("Guyana Amazon Warriors", "R. Shepherd", 6, 3, "right", "pace", "right-arm fast-medium",3),
    ("Guyana Amazon Warriors", "K. Sinclair", 7, 3, "right", "spin", "off-break",           2),
    ("Guyana Amazon Warriors", "I. Wardlaw",  8, 1, "right", "pace", "right-arm fast-medium",3),
    ("Guyana Amazon Warriors", "Q. Archer",   9, 1, "right", "pace", "right-arm fast",      4),
    ("Guyana Amazon Warriors", "A. Phagoo",  10, 1, "right", "spin", "leg-break",           3),
    ("Guyana Amazon Warriors", "O. McCoy",   11, 1, "left",  "pace", "left-arm fast",       4),

    # ── JAMAICA TALLAWAHS ──
    ("Jamaica Tallawahs", "C. Walton",        1, 4, "right", "none", None,                  0),
    ("Jamaica Tallawahs", "K. Rutherford",    2, 4, "right", "none", None,                  0),
    ("Jamaica Tallawahs", "B. King",          3, 4, "right", "none", None,                  0),
    ("Jamaica Tallawahs", "A. Russell",       4, 4, "right", "pace", "right-arm fast",      4),
    ("Jamaica Tallawahs", "R. Patel",         5, 3, "right", "spin", "off-break",           3),
    ("Jamaica Tallawahs", "N. Miller",        6, 3, "left",  "spin", "left-arm orthodox",   3),
    ("Jamaica Tallawahs", "J. Da Silva",      7, 3, "right", "none", None,                  0),
    ("Jamaica Tallawahs", "A. Nurse",         8, 2, "right", "spin", "off-break",           3),
    ("Jamaica Tallawahs", "K. Williams",      9, 1, "right", "pace", "right-arm fast",      3),
    ("Jamaica Tallawahs", "N. Wagg",         10, 1, "right", "pace", "right-arm seam",      3),
    ("Jamaica Tallawahs", "S. Cottrell",     11, 1, "left",  "pace", "left-arm fast",       4),

    # ── ST KITTS & NEVIS PATRIOTS ──
    ("St Kitts & Nevis Patriots", "J. Campbell",    1, 4, "right", "none", None,            0),
    ("St Kitts & Nevis Patriots", "E. Lewis",       2, 4, "left",  "none", None,            0),
    ("St Kitts & Nevis Patriots", "T. David",       3, 4, "right", "none", None,            0),
    ("St Kitts & Nevis Patriots", "A. Nortje",      4, 3, "right", "pace", "right-arm fast",4),
    ("St Kitts & Nevis Patriots", "D. Bravo",       5, 3, "right", "pace", "right-arm fast-medium",3),
    ("St Kitts & Nevis Patriots", "J. Greaves",     6, 3, "right", "none", None,            0),
    ("St Kitts & Nevis Patriots", "P. Washington",  7, 2, "right", "spin", "off-break",     3),
    ("St Kitts & Nevis Patriots", "A. Khan",        8, 1, "right", "spin", "leg-break",     4),
    ("St Kitts & Nevis Patriots", "A. Phillip",     9, 1, "right", "pace", "right-arm fast",3),
    ("St Kitts & Nevis Patriots", "R. Emrit",      10, 1, "right", "pace", "right-arm fast-medium",3),
    ("St Kitts & Nevis Patriots", "W. Hasaranga",  11, 1, "right", "spin", "leg-break",     4),

    # ── TRINBAGO KNIGHT RIDERS ──
    ("Trinbago Knight Riders", "L. Simmons",   1, 3, "right", "none", None,                 0),
    ("Trinbago Knight Riders", "A. Fletcher",  2, 4, "right", "none", None,                 0),
    ("Trinbago Knight Riders", "N. Pooran",    3, 5, "left",  "none", None,                 0),
    ("Trinbago Knight Riders", "D. Bravo",     4, 4, "right", "pace", "right-arm fast-medium",3),
    ("Trinbago Knight Riders", "K. Pollard",   5, 4, "right", "pace", "right-arm fast-medium",3),
    ("Trinbago Knight Riders", "T. Imad",      6, 3, "left",  "spin", "left-arm orthodox",  3),
    ("Trinbago Knight Riders", "S. Narine",    7, 3, "right", "spin", "off-break",          4),
    ("Trinbago Knight Riders", "A. Hosein",    8, 2, "left",  "spin", "left-arm orthodox",  3),
    ("Trinbago Knight Riders", "R. Khan",      9, 1, "right", "spin", "leg-break",          5),
    ("Trinbago Knight Riders", "R. Rampaul",  10, 1, "right", "pace", "right-arm fast",     3),
    ("Trinbago Knight Riders", "K. Mayers",   11, 2, "right", "pace", "right-arm fast-medium",3),

    # ── ST LUCIA KINGS ──
    ("St Lucia Kings", "M. Ackerman",          1, 3, "right", "none", None,                 0),
    ("St Lucia Kings", "R. Ingram",            2, 3, "right", "none", None,                 0),
    ("St Lucia Kings", "D. Smith",             3, 4, "left",  "none", None,                 0),
    ("St Lucia Kings", "F. du Plessis",        4, 4, "right", "none", None,                 0),
    ("St Lucia Kings", "D. Miller",            5, 4, "left",  "none", None,                 0),
    ("St Lucia Kings", "J. Matara",            6, 3, "right", "none", None,                 0),
    ("St Lucia Kings", "R. Khan",              7, 2, "right", "spin", "leg-break",          5),
    ("St Lucia Kings", "O. Thomas",            8, 1, "right", "pace", "right-arm fast",     4),
    ("St Lucia Kings", "C. Roach",             9, 1, "right", "pace", "right-arm fast",     4),
    ("St Lucia Kings", "A. Paul",             10, 1, "right", "pace", "right-arm fast",     3),
    ("St Lucia Kings", "I. Sodhi",            11, 1, "right", "spin", "leg-break",          3),
]


def _venue_id(db, name):
    row = db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


def _team_id(db, name):
    row = db.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


def seed(db):
    for name, city, country in VENUES:
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
