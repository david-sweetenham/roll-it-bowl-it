"""
seed_domestic/australia_bbl.py
Big Bash League: 8 franchise teams.
Venues largely share with Sheffield Shield state grounds plus Marvel Stadium.
"""

VENUES = [
    ("Marvel Stadium",  "Melbourne", "Australia"),
    ("Manuka Oval",     "Canberra",  "Australia"),
]

# (name, short_code, badge_colour, home_venue_name, team_type, league)
TEAMS = [
    ("Adelaide Strikers",    "STR", "#009AC7", "Adelaide Oval",             "franchise", "Big Bash League"),
    ("Brisbane Heat",        "HEA", "#E4173E", "The Gabba",                 "franchise", "Big Bash League"),
    ("Hobart Hurricanes",    "HUR", "#6C1D8E", "Blundstone Arena",          "franchise", "Big Bash League"),
    ("Melbourne Renegades",  "REN", "#EF3340", "Marvel Stadium",            "franchise", "Big Bash League"),
    ("Melbourne Stars",      "STA", "#007A33", "Melbourne Cricket Ground",  "franchise", "Big Bash League"),
    ("Perth Scorchers",      "SCO", "#F15A22", "Optus Stadium",             "franchise", "Big Bash League"),
    ("Sydney Sixers",        "SIX", "#FF69B4", "Sydney Cricket Ground",     "franchise", "Big Bash League"),
    ("Sydney Thunder",       "THU", "#FFED00", "Manuka Oval",               "franchise", "Big Bash League"),
]

# T20 specialists: power hitters, death bowlers
SQUADS = [

    # ── ADELAIDE STRIKERS ──
    ("Adelaide Strikers", "M. Short",          1, 4, "right", "spin", "off-break",            3),
    ("Adelaide Strikers", "T. Head",           2, 4, "left",  "spin", "off-break",            2),
    ("Adelaide Strikers", "J. Weatherald",     3, 4, "left",  "none", None,                   0),
    ("Adelaide Strikers", "J. Lehmann",        4, 3, "right", "none", None,                   0),
    ("Adelaide Strikers", "H. Nielsen",        5, 3, "right", "none", None,                   0),
    ("Adelaide Strikers", "A. Ross",           6, 3, "right", "none", None,                   0),
    ("Adelaide Strikers", "W. Sutherland",     7, 3, "right", "pace", "right-arm seam",       3),
    ("Adelaide Strikers", "D. Worrall",        8, 2, "right", "pace", "right-arm fast-medium",4),
    ("Adelaide Strikers", "P. Siddle",         9, 1, "right", "pace", "right-arm fast-medium",3),
    ("Adelaide Strikers", "J. Richardson",    10, 1, "right", "pace", "right-arm fast",       4),
    ("Adelaide Strikers", "B. Laughlin",      11, 1, "right", "pace", "right-arm seam",       3),

    # ── BRISBANE HEAT ──
    ("Brisbane Heat", "M. Renshaw",            1, 3, "left",  "none", None,                   0),
    ("Brisbane Heat", "X. Bartlett",           2, 3, "right", "pace", "right-arm fast",       1),
    ("Brisbane Heat", "U. Khawaja",            3, 4, "left",  "none", None,                   0),
    ("Brisbane Heat", "J. Peirson",            4, 3, "right", "none", None,                   0),
    ("Brisbane Heat", "B. Labrooy",            5, 3, "right", "none", None,                   0),
    ("Brisbane Heat", "C. Lynn",               6, 4, "right", "none", None,                   0),
    ("Brisbane Heat", "J. Bazley",             7, 3, "right", "pace", "right-arm fast-medium",3),
    ("Brisbane Heat", "M. Kuhnemann",          8, 2, "left",  "spin", "left-arm orthodox",    3),
    ("Brisbane Heat", "T. Sangha",             9, 1, "right", "spin", "leg-break",            3),
    ("Brisbane Heat", "M. Swepson",           10, 1, "right", "spin", "leg-break",            3),
    ("Brisbane Heat", "P. Rasika",            11, 1, "right", "pace", "right-arm seam",       3),

    # ── HOBART HURRICANES ──
    ("Hobart Hurricanes", "B. McDermott",      1, 4, "right", "none", None,                   0),
    ("Hobart Hurricanes", "M. Wade",           2, 4, "left",  "none", None,                   0),
    ("Hobart Hurricanes", "D. Short",          3, 4, "right", "spin", "off-break",            2),
    ("Hobart Hurricanes", "C. Jewell",         4, 3, "left",  "none", None,                   0),
    ("Hobart Hurricanes", "T. Ward",           5, 3, "right", "none", None,                   0),
    ("Hobart Hurricanes", "B. Webster",        6, 4, "right", "pace", "right-arm fast-medium",2),
    ("Hobart Hurricanes", "J. Rose",           7, 2, "right", "pace", "right-arm seam",       3),
    ("Hobart Hurricanes", "R. Milnes",         8, 1, "right", "pace", "right-arm seam",       3),
    ("Hobart Hurricanes", "S. Lamichhane",     9, 1, "right", "spin", "leg-break",            4),
    ("Hobart Hurricanes", "J. Bird",          10, 1, "right", "pace", "right-arm fast-medium",4),
    ("Hobart Hurricanes", "L. Rainbird",      11, 1, "left",  "pace", "left-arm fast-medium", 3),

    # ── MELBOURNE RENEGADES ──
    ("Melbourne Renegades", "J. Fraser-McGurk",1,4, "right", "none", None,                    0),
    ("Melbourne Renegades", "A. Finch",        2, 4, "right", "none", None,                   0),
    ("Melbourne Renegades", "S. Harper",       3, 3, "right", "none", None,                   0),
    ("Melbourne Renegades", "J. Inglis",       4, 4, "right", "none", None,                   0),
    ("Melbourne Renegades", "W. Sherburn",     5, 3, "right", "none", None,                   0),
    ("Melbourne Renegades", "M. Forsyth",      6, 3, "right", "none", None,                   0),
    ("Melbourne Renegades", "J. Merlo",        7, 3, "right", "pace", "right-arm seam",       3),
    ("Melbourne Renegades", "K. Richardson",   8, 2, "right", "pace", "right-arm fast",       4),
    ("Melbourne Renegades", "J. Holder",       9, 2, "right", "pace", "right-arm fast-medium",4),
    ("Melbourne Renegades", "C. Boyce",       10, 1, "right", "spin", "leg-break",            3),
    ("Melbourne Renegades", "T. Rogers",      11, 1, "right", "pace", "right-arm seam",       3),

    # ── MELBOURNE STARS ──
    ("Melbourne Stars", "J. Burns",            1, 3, "left",  "none", None,                   0),
    ("Melbourne Stars", "P. Handscomb",        2, 4, "right", "none", None,                   0),
    ("Melbourne Stars", "N. Maddinson",        3, 4, "right", "none", None,                   0),
    ("Melbourne Stars", "M. Stoinis",          4, 4, "right", "pace", "right-arm medium",     3),
    ("Melbourne Stars", "H. Cartwright",       5, 3, "right", "pace", "right-arm seam",       2),
    ("Melbourne Stars", "B. Couch",            6, 3, "right", "none", None,                   0),
    ("Melbourne Stars", "A. Zampa",            7, 2, "right", "spin", "leg-break",            4),
    ("Melbourne Stars", "S. Mayer",            8, 2, "right", "pace", "right-arm fast",       3),
    ("Melbourne Stars", "B. Couch",            9, 1, "right", "spin", "off-break",            3),
    ("Melbourne Stars", "T. Boult",           10, 1, "left",  "pace", "left-arm fast",        5),
    ("Melbourne Stars", "C. Green",           11, 1, "right", "pace", "right-arm fast-medium",3),

    # ── PERTH SCORCHERS ──
    ("Perth Scorchers", "J. Inglis",           1, 4, "right", "none", None,                   0),
    ("Perth Scorchers", "C. Bancroft",         2, 3, "right", "none", None,                   0),
    ("Perth Scorchers", "A. Turner",           3, 4, "right", "none", None,                   0),
    ("Perth Scorchers", "A. Hardie",           4, 3, "right", "none", None,                   0),
    ("Perth Scorchers", "M. Marsh",            5, 4, "right", "pace", "right-arm fast-medium",3),
    ("Perth Scorchers", "L. Evans",            6, 3, "right", "none", None,                   0),
    ("Perth Scorchers", "A. Tye",              7, 2, "right", "pace", "right-arm fast",       4),
    ("Perth Scorchers", "J. Behrendorff",      8, 1, "left",  "pace", "left-arm fast",        4),
    ("Perth Scorchers", "F. Mills",            9, 1, "right", "pace", "right-arm fast",       3),
    ("Perth Scorchers", "L. Carey",           10, 1, "right", "pace", "right-arm fast-medium",3),
    ("Perth Scorchers", "T. Ansell",          11, 1, "right", "pace", "right-arm seam",       3),

    # ── SYDNEY SIXERS ──
    ("Sydney Sixers", "D. Hughes",             1, 4, "left",  "none", None,                   0),
    ("Sydney Sixers", "J. Vince",              2, 4, "right", "none", None,                   0),
    ("Sydney Sixers", "M. Henriques",          3, 4, "right", "pace", "right-arm seam",       2),
    ("Sydney Sixers", "J. Avendano",           4, 3, "right", "none", None,                   0),
    ("Sydney Sixers", "J. Philippe",           5, 4, "right", "none", None,                   0),
    ("Sydney Sixers", "B. Dwarshuis",          6, 2, "left",  "pace", "left-arm fast",        4),
    ("Sydney Sixers", "S. Abbott",             7, 2, "right", "pace", "right-arm fast-medium",4),
    ("Sydney Sixers", "T. Curran",             8, 2, "right", "pace", "right-arm fast-medium",3),
    ("Sydney Sixers", "H. Kerr",               9, 1, "right", "pace", "right-arm fast",       3),
    ("Sydney Sixers", "S. O'Keefe",           10, 1, "left",  "spin", "left-arm orthodox",    4),
    ("Sydney Sixers", "J. Hazlewood",         11, 1, "right", "pace", "right-arm fast-medium",5),

    # ── SYDNEY THUNDER ──
    ("Sydney Thunder", "M. Gilkes",            1, 3, "right", "none", None,                   0),
    ("Sydney Thunder", "A. Hales",             2, 5, "right", "none", None,                   0),
    ("Sydney Thunder", "J. Sangha",            3, 3, "right", "spin", "leg-break",            2),
    ("Sydney Thunder", "A. Ross",              4, 4, "right", "none", None,                   0),
    ("Sydney Thunder", "D. Warner",            5, 4, "left",  "none", None,                   0),
    ("Sydney Thunder", "O. Davies",            6, 3, "right", "none", None,                   0),
    ("Sydney Thunder", "C. Green",             7, 3, "right", "pace", "right-arm fast-medium",3),
    ("Sydney Thunder", "D. Sams",              8, 2, "right", "pace", "right-arm fast",       4),
    ("Sydney Thunder", "N. Gilkes",            9, 1, "right", "none", None,                   0),
    ("Sydney Thunder", "T. Sangha",           10, 1, "right", "spin", "leg-break",            4),
    ("Sydney Thunder", "N. Storrar",          11, 1, "right", "pace", "right-arm seam",       3),
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
