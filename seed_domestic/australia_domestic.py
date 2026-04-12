"""
seed_domestic/australia_domestic.py
Australian domestic cricket: 6 Sheffield Shield / Marsh One-Day Cup state teams.
"""

VENUES = [
    ("The Gabba",           "Brisbane", "Australia"),
    ("Adelaide Oval",       "Adelaide", "Australia"),
    ("Optus Stadium",       "Perth",    "Australia"),
    ("Blundstone Arena",    "Hobart",   "Australia"),
]

# (name, short_code, badge_colour, home_venue_name, team_type, league)
TEAMS = [
    ("New South Wales Blues",    "NSW", "#002B5C", "Sydney Cricket Ground",    "state", "Sheffield Shield"),
    ("Victoria Bushrangers",     "VIC", "#003DA5", "Melbourne Cricket Ground",  "state", "Sheffield Shield"),
    ("Queensland Bulls",         "QLD", "#8B0000", "The Gabba",                 "state", "Sheffield Shield"),
    ("South Australia Redbacks", "SAU", "#CC0000", "Adelaide Oval",             "state", "Sheffield Shield"),
    ("Western Australia Warriors","WAU", "#FFD700", "Optus Stadium",             "state", "Sheffield Shield"),
    ("Tasmania Tigers",          "TAS", "#FFD700", "Blundstone Arena",           "state", "Sheffield Shield"),
]

SQUADS = [

    # ── NEW SOUTH WALES BLUES ──
    ("New South Wales Blues", "D. Hughes",       1, 4, "left",  "none", None,                   0),
    ("New South Wales Blues", "M. Gilkes",       2, 3, "right", "none", None,                   0),
    ("New South Wales Blues", "K. Patterson",    3, 4, "right", "none", None,                   0),
    ("New South Wales Blues", "P. Nevill",       4, 3, "right", "none", None,                   0),
    ("New South Wales Blues", "J. Sangha",       5, 3, "right", "spin", "leg-break",            2),
    ("New South Wales Blues", "M. Henriques",    6, 4, "right", "pace", "right-arm seam",       2),
    ("New South Wales Blues", "B. Geddes",       7, 2, "right", "none", None,                   0),
    ("New South Wales Blues", "C. Green",        8, 3, "right", "pace", "right-arm fast-medium",3),
    ("New South Wales Blues", "H. Kerr",         9, 1, "right", "pace", "right-arm fast",       4),
    ("New South Wales Blues", "T. Sangha",      10, 1, "right", "spin", "leg-break",            3),
    ("New South Wales Blues", "J. Hazlewood",   11, 1, "right", "pace", "right-arm fast-medium",4),

    # ── VICTORIA BUSHRANGERS ──
    ("Victoria Bushrangers", "M. Short",         1, 3, "right", "spin", "off-break",            2),
    ("Victoria Bushrangers", "J. Fraser-McGurk", 2, 4, "right", "none", None,                   0),
    ("Victoria Bushrangers", "P. Handscomb",     3, 4, "right", "none", None,                   0),
    ("Victoria Bushrangers", "M. Labuschagne",   4, 5, "right", "spin", "leg-break",            2),
    ("Victoria Bushrangers", "W. Sutherland",    5, 3, "right", "pace", "right-arm seam",       2),
    ("Victoria Bushrangers", "S. Harper",        6, 3, "right", "none", None,                   0),
    ("Victoria Bushrangers", "C. McClure",       7, 2, "right", "none", None,                   0),
    ("Victoria Bushrangers", "J. Merlo",         8, 2, "right", "pace", "right-arm seam",       3),
    ("Victoria Bushrangers", "S. Mayer",         9, 1, "right", "pace", "right-arm fast",       3),
    ("Victoria Bushrangers", "M. Perry",        10, 1, "left",  "pace", "left-arm fast-medium", 4),
    ("Victoria Bushrangers", "M. Boland",       11, 1, "right", "pace", "right-arm seam",       4),

    # ── QUEENSLAND BULLS ──
    ("Queensland Bulls", "M. Renshaw",           1, 3, "left",  "none", None,                   0),
    ("Queensland Bulls", "J. Peirson",           2, 3, "right", "none", None,                   0),
    ("Queensland Bulls", "U. Khawaja",           3, 4, "left",  "none", None,                   0),
    ("Queensland Bulls", "T. Head",              4, 4, "left",  "spin", "off-break",            2),
    ("Queensland Bulls", "M. Bryant",            5, 3, "right", "none", None,                   0),
    ("Queensland Bulls", "J. Bazley",            6, 3, "right", "pace", "right-arm fast-medium",2),
    ("Queensland Bulls", "M. Kuhnemann",         7, 2, "left",  "spin", "left-arm orthodox",    3),
    ("Queensland Bulls", "X. Bartlett",          8, 1, "right", "pace", "right-arm fast",       4),
    ("Queensland Bulls", "B. Doggett",           9, 1, "right", "pace", "right-arm fast-medium",3),
    ("Queensland Bulls", "M. Swepson",          10, 1, "right", "spin", "leg-break",            3),
    ("Queensland Bulls", "N. Reardon",          11, 1, "right", "pace", "right-arm seam",       3),

    # ── SOUTH AUSTRALIA REDBACKS ──
    ("South Australia Redbacks", "N. McSweeney",  1, 3, "right", "none", None,                  0),
    ("South Australia Redbacks", "H. Hunt",       2, 3, "right", "none", None,                  0),
    ("South Australia Redbacks", "J. Weatherald", 3, 4, "left",  "none", None,                  0),
    ("South Australia Redbacks", "J. Lehmann",    4, 3, "right", "none", None,                  0),
    ("South Australia Redbacks", "D. Drew",       5, 3, "right", "none", None,                  0),
    ("South Australia Redbacks", "A. Ross",       6, 2, "right", "none", None,                  0),
    ("South Australia Redbacks", "H. Nielsen",    7, 3, "right", "none", None,                  0),
    ("South Australia Redbacks", "D. Worrall",    8, 1, "right", "pace", "right-arm fast-medium",4),
    ("South Australia Redbacks", "L. Pope",       9, 1, "right", "pace", "right-arm seam",      3),
    ("South Australia Redbacks", "B. Gill",      10, 1, "right", "spin", "off-break",           3),
    ("South Australia Redbacks", "G. Garton",    11, 1, "left",  "pace", "left-arm fast-medium",3),

    # ── WESTERN AUSTRALIA WARRIORS ──
    ("Western Australia Warriors", "S. Whiteman",  1, 3, "right", "none", None,                 0),
    ("Western Australia Warriors", "C. Bancroft",  2, 4, "right", "none", None,                 0),
    ("Western Australia Warriors", "M. Marsh",     3, 3, "right", "pace", "right-arm fast-medium",3),
    ("Western Australia Warriors", "H. Cartwright",4, 3, "right", "pace", "right-arm seam",     2),
    ("Western Australia Warriors", "J. Inglis",    5, 4, "right", "none", None,                 0),
    ("Western Australia Warriors", "A. Hardie",    6, 3, "right", "none", None,                 0),
    ("Western Australia Warriors", "A. Tye",       7, 2, "right", "pace", "right-arm fast",     3),
    ("Western Australia Warriors", "J. Behrendorff",8,1,"left",  "pace", "left-arm fast",        4),
    ("Western Australia Warriors", "L. Carey",     9, 1, "right", "pace", "right-arm fast-medium",3),
    ("Western Australia Warriors", "M. Kelly",    10, 1, "right", "pace", "right-arm seam",     3),
    ("Western Australia Warriors", "C. Haggett",  11, 1, "right", "pace", "right-arm seam",     3),

    # ── TASMANIA TIGERS ──
    ("Tasmania Tigers", "J. Ward",            1, 3, "right", "none", None,                      0),
    ("Tasmania Tigers", "T. Ward",            2, 3, "right", "none", None,                      0),
    ("Tasmania Tigers", "C. Jewell",          3, 3, "left",  "none", None,                      0),
    ("Tasmania Tigers", "T. Bailey",          4, 3, "right", "none", None,                      0),
    ("Tasmania Tigers", "B. Webster",         5, 4, "right", "pace", "right-arm fast-medium",   2),
    ("Tasmania Tigers", "T. Paine",           6, 3, "right", "none", None,                      0),
    ("Tasmania Tigers", "P. Siddle",          7, 2, "right", "pace", "right-arm fast-medium",   3),
    ("Tasmania Tigers", "J. Bird",            8, 1, "right", "pace", "right-arm fast-medium",   4),
    ("Tasmania Tigers", "C. Sayers",          9, 1, "right", "pace", "right-arm seam",          3),
    ("Tasmania Tigers", "M. Owen",           10, 1, "right", "spin", "off-break",               3),
    ("Tasmania Tigers", "L. Rainbird",       11, 1, "left",  "pace", "left-arm fast-medium",    3),
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
