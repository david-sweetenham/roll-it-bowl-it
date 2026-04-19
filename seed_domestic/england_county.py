"""
seed_domestic/england_county.py
English domestic cricket: 18 County Championship / T20 Blast / Royal London Cup clubs.
"""

VENUES = [
    # (name, city, country)
    ("Old Trafford",                     "Manchester",    "England"),
    ("Trent Bridge",                     "Nottingham",    "England"),
    ("Emirates Riverside",               "Chester-le-Street", "England"),
    ("The Spitfire Ground St Lawrence",  "Canterbury",    "England"),
    ("The Cloud County Ground",          "Chelmsford",    "England"),
    ("The Utilita Bowl",                   "Southampton",   "England"),
    ("The County Ground Taunton",        "Taunton",       "England"),
    ("The County Ground Bristol",        "Bristol",       "England"),
    ("The County Ground Northampton",    "Northampton",   "England"),
    ("New Road",                         "Worcester",     "England"),
    ("The County Ground Derby",          "Derby",         "England"),
    ("Uptonsteel County Ground",         "Leicester",     "England"),
    ("The 1st Central County Ground",    "Hove",          "England"),
    ("Sophia Gardens",                   "Cardiff",       "Wales"),
]

# (name, short_code, badge_colour, home_venue_name, team_type, league)
TEAMS = [
    ("Yorkshire",        "YKS", "#1C4B82", "Headingley",                        "county", "County Championship"),
    ("Lancashire",       "LAN", "#DC143C", "Old Trafford",                      "county", "County Championship"),
    ("Warwickshire",     "WAR", "#003399", "Edgbaston",                         "county", "County Championship"),
    ("Surrey",           "SUR", "#1B3A6B", "The Oval",                          "county", "County Championship"),
    ("Middlesex",        "MDX", "#003DA5", "Lord's Cricket Ground",             "county", "County Championship"),
    ("Nottinghamshire",  "NOT", "#003F87", "Trent Bridge",                      "county", "County Championship"),
    ("Durham",           "DUR", "#003DA5", "Emirates Riverside",                "county", "County Championship"),
    ("Kent",             "KNT", "#D01010", "The Spitfire Ground St Lawrence",   "county", "County Championship"),
    ("Essex",            "ESS", "#232066", "The Cloud County Ground",           "county", "County Championship"),
    ("Hampshire",        "HAM", "#004B87", "The Utilita Bowl",                    "county", "County Championship"),
    ("Somerset",         "SOM", "#2B2E83", "The County Ground Taunton",         "county", "County Championship"),
    ("Gloucestershire",  "GLS", "#003366", "The County Ground Bristol",         "county", "County Championship"),
    ("Northamptonshire", "NOR", "#8B0000", "The County Ground Northampton",     "county", "County Championship"),
    ("Worcestershire",   "WOR", "#000000", "New Road",                          "county", "County Championship"),
    ("Derbyshire",       "DRB", "#003DA5", "The County Ground Derby",           "county", "County Championship"),
    ("Leicestershire",   "LEI", "#003DA5", "Uptonsteel County Ground",          "county", "County Championship"),
    ("Sussex",           "SSX", "#003DA5", "The 1st Central County Ground",     "county", "County Championship"),
    ("Glamorgan",        "GLA", "#003DA5", "Sophia Gardens",                    "county", "County Championship"),
]

# (team_name, player_name, pos, bat_r, bat_hand, bowl_type, bowl_action, bowl_r)
SQUADS = [

    # ── YORKSHIRE ──
    ("Yorkshire", "A. Lyth",          1, 3, "left",  "none", None,                    0),
    ("Yorkshire", "W. Fraine",        2, 3, "right", "none", None,                    0),
    ("Yorkshire", "H. Brook",         3, 5, "right", "none", None,                    0),
    ("Yorkshire", "J. Leaning",       4, 3, "right", "none", None,                    0),
    ("Yorkshire", "G. Ballance",      5, 4, "right", "none", None,                    0),
    ("Yorkshire", "J. Tattersall",    6, 3, "right", "none", None,                    0),
    ("Yorkshire", "D. Bess",          7, 2, "right", "spin", "off-break",             3),
    ("Yorkshire", "M. Fisher",        8, 2, "right", "pace", "right-arm seam",        3),
    ("Yorkshire", "B. Coad",          9, 1, "right", "pace", "right-arm seam",        4),
    ("Yorkshire", "J. Thompson",     10, 1, "right", "pace", "right-arm seam",        3),
    ("Yorkshire", "R. Gibson",       11, 1, "right", "spin", "leg-break",             3),

    # ── LANCASHIRE ──
    ("Lancashire", "K. Jennings",     1, 3, "left",  "none", None,                    0),
    ("Lancashire", "L. Wells",        2, 3, "left",  "none", None,                    0),
    ("Lancashire", "S. Hameed",       3, 3, "right", "none", None,                    0),
    ("Lancashire", "D. Vilas",        4, 3, "right", "none", None,                    0),
    ("Lancashire", "G. Lloyd",        5, 3, "right", "none", None,                    0),
    ("Lancashire", "R. Jones",        6, 3, "right", "none", None,                    0),
    ("Lancashire", "L. Wood",         7, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Lancashire", "T. Bailey",       8, 2, "right", "pace", "right-arm seam",        4),
    ("Lancashire", "S. Mahmood",      9, 1, "right", "pace", "right-arm fast",        4),
    ("Lancashire", "J. Morley",      10, 1, "left",  "spin", "left-arm orthodox",     3),
    ("Lancashire", "T. Hartley",     11, 1, "left",  "spin", "left-arm orthodox",     4),

    # ── WARWICKSHIRE ──
    ("Warwickshire", "D. Sibley",     1, 3, "right", "none", None,                    0),
    ("Warwickshire", "R. Yates",      2, 3, "left",  "none", None,                    0),
    ("Warwickshire", "S. Hain",       3, 4, "right", "none", None,                    0),
    ("Warwickshire", "M. Lamb",       4, 3, "right", "none", None,                    0),
    ("Warwickshire", "A. Hose",       5, 3, "right", "none", None,                    0),
    ("Warwickshire", "M. Burgess",    6, 3, "right", "none", None,                    0),
    ("Warwickshire", "C. Woakes",     7, 3, "right", "pace", "right-arm seam",        4),
    ("Warwickshire", "O. Hannon-Dalby",8,1, "right", "pace", "right-arm seam",        3),
    ("Warwickshire", "H. Brookes",    9, 1, "right", "pace", "right-arm fast-medium", 4),
    ("Warwickshire", "D. Payne",     10, 1, "right", "pace", "right-arm seam",        3),
    ("Warwickshire", "J. Lintott",   11, 1, "right", "spin", "leg-break",             3),

    # ── SURREY ──
    ("Surrey", "R. Burns",            1, 3, "left",  "none", None,                    0),
    ("Surrey", "Z. Crawley",          2, 3, "right", "none", None,                    0),
    ("Surrey", "O. Pope",             3, 4, "right", "none", None,                    0),
    ("Surrey", "D. Elgar",            4, 4, "left",  "spin", "left-arm orthodox",     2),
    ("Surrey", "B. Foakes",           5, 3, "right", "none", None,                    0),
    ("Surrey", "J. Smith",            6, 3, "right", "pace", "right-arm seam",        2),
    ("Surrey", "C. Overton",          7, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Surrey", "G. Batty",            8, 1, "right", "spin", "off-break",             3),
    ("Surrey", "J. Clark",            9, 1, "right", "pace", "right-arm seam",        3),
    ("Surrey", "G. Atkinson",        10, 1, "right", "pace", "right-arm fast",        4),
    ("Surrey", "M. Morkel",          11, 1, "right", "pace", "right-arm fast",        5),

    # ── MIDDLESEX ──
    ("Middlesex", "M. Robson",        1, 3, "left",  "none", None,                    0),
    ("Middlesex", "S. Eskinazi",      2, 3, "right", "none", None,                    0),
    ("Middlesex", "N. Gubbins",       3, 3, "left",  "none", None,                    0),
    ("Middlesex", "D. Malan",         4, 4, "left",  "none", None,                    0),
    ("Middlesex", "J. Cracknell",     5, 3, "right", "none", None,                    0),
    ("Middlesex", "J. Simpson",       6, 3, "right", "none", None,                    0),
    ("Middlesex", "T. Helm",          7, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Middlesex", "N. Sowter",        8, 1, "right", "spin", "leg-break",             3),
    ("Middlesex", "E. Bamber",        9, 1, "right", "pace", "right-arm seam",        4),
    ("Middlesex", "T. Murtagh",      10, 1, "right", "pace", "right-arm seam",        3),
    ("Middlesex", "R. White",        11, 1, "right", "spin", "off-break",             3),

    # ── NOTTINGHAMSHIRE ──
    ("Nottinghamshire", "H. Hameed",  1, 3, "right", "none", None,                    0),
    ("Nottinghamshire", "B. Slater",  2, 3, "left",  "none", None,                    0),
    ("Nottinghamshire", "J. Evison",  3, 3, "right", "pace", "right-arm seam",        2),
    ("Nottinghamshire", "L. Fletcher",4, 3, "right", "pace", "right-arm seam",        3),
    ("Nottinghamshire", "S. Mullaney",5, 3, "right", "pace", "right-arm seam",        3),
    ("Nottinghamshire", "T. Moores",  6, 3, "right", "none", None,                    0),
    ("Nottinghamshire", "L. Patterson-White",7,2,"left","spin","left-arm orthodox",    3),
    ("Nottinghamshire", "J. Ball",    8, 1, "right", "pace", "right-arm fast",        4),
    ("Nottinghamshire", "S. Broad",   9, 2, "right", "pace", "right-arm fast",        4),
    ("Nottinghamshire", "D. Paterson",10,1, "right", "pace", "right-arm fast-medium", 3),
    ("Nottinghamshire", "L. Wood",   11, 1, "left",  "pace", "left-arm fast-medium",  3),

    # ── DURHAM ──
    ("Durham", "A. Lees",             1, 3, "left",  "none", None,                    0),
    ("Durham", "S. Steel",            2, 3, "right", "none", None,                    0),
    ("Durham", "D. Bedingham",        3, 4, "right", "none", None,                    0),
    ("Durham", "M. Stoneman",         4, 3, "left",  "none", None,                    0),
    ("Durham", "S. Dickson",          5, 3, "right", "none", None,                    0),
    ("Durham", "B. Raine",            6, 3, "right", "pace", "right-arm fast-medium", 3),
    ("Durham", "L. Trevaskis",        7, 2, "left",  "spin", "left-arm orthodox",     3),
    ("Durham", "C. Rushworth",        8, 1, "right", "pace", "right-arm seam",        4),
    ("Durham", "M. Potts",            9, 1, "right", "pace", "right-arm seam",        4),
    ("Durham", "M. Turner",          10, 1, "right", "pace", "right-arm fast",        3),
    ("Durham", "O. Robinson",        11, 1, "right", "pace", "right-arm seam",        3),

    # ── KENT ──
    ("Kent", "D. Bell-Drummond",      1, 3, "right", "none", None,                    0),
    ("Kent", "Z. Crawley",            2, 4, "right", "none", None,                    0),
    ("Kent", "J. Cox",                3, 3, "right", "none", None,                    0),
    ("Kent", "J. Denly",              4, 3, "right", "spin", "leg-break",             2),
    ("Kent", "H. Rouse",              5, 3, "right", "none", None,                    0),
    ("Kent", "M. O'Riordan",          6, 3, "right", "spin", "off-break",             3),
    ("Kent", "T. Stewart",            7, 2, "right", "none", None,                    0),
    ("Kent", "G. Stewart",            8, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Kent", "M. Milnes",             9, 1, "right", "pace", "right-arm seam",        4),
    ("Kent", "M. Claydon",           10, 1, "right", "pace", "right-arm seam",        3),
    ("Kent", "I. Taylor",            11, 1, "right", "spin", "off-break",             3),

    # ── ESSEX ──
    ("Essex", "A. Cook",              1, 4, "left",  "none", None,                    0),
    ("Essex", "N. Browne",            2, 3, "right", "none", None,                    0),
    ("Essex", "D. Lawrence",          3, 4, "right", "none", None,                    0),
    ("Essex", "P. Walter",            4, 3, "right", "pace", "right-arm seam",        3),
    ("Essex", "T. Westley",           5, 3, "right", "spin", "off-break",             2),
    ("Essex", "A. Wheater",           6, 3, "right", "none", None,                    0),
    ("Essex", "S. Snater",            7, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Essex", "S. Cook",              8, 1, "right", "pace", "right-arm seam",        4),
    ("Essex", "M. Quinn",             9, 1, "right", "pace", "right-arm fast-medium", 3),
    ("Essex", "J. Porter",           10, 1, "right", "pace", "right-arm seam",        4),
    ("Essex", "S. Harmer",           11, 1, "right", "spin", "off-break",             4),

    # ── HAMPSHIRE ──
    ("Hampshire", "B. McMahon",       1, 3, "right", "none", None,                    0),
    ("Hampshire", "J. Northeast",     2, 4, "right", "none", None,                    0),
    ("Hampshire", "T. Alsop",         3, 3, "left",  "none", None,                    0),
    ("Hampshire", "J. Vince",         4, 4, "right", "none", None,                    0),
    ("Hampshire", "L. Dawson",        5, 3, "left",  "spin", "left-arm orthodox",     3),
    ("Hampshire", "L. McManus",       6, 3, "right", "none", None,                    0),
    ("Hampshire", "K. Abbott",        7, 2, "right", "pace", "right-arm fast-medium", 4),
    ("Hampshire", "M. de Lange",      8, 1, "right", "pace", "right-arm fast",        4),
    ("Hampshire", "B. Taylor",        9, 1, "right", "pace", "right-arm seam",        3),
    ("Hampshire", "J. Wheal",        10, 1, "right", "pace", "right-arm seam",        3),
    ("Hampshire", "C. Tongue",       11, 1, "right", "pace", "right-arm fast-medium", 3),

    # ── SOMERSET ──
    ("Somerset", "M. Renshaw",        1, 3, "left",  "none", None,                    0),
    ("Somerset", "T. Lammonby",       2, 3, "left",  "none", None,                    0),
    ("Somerset", "J. Hildreth",       3, 4, "right", "none", None,                    0),
    ("Somerset", "T. Abell",          4, 3, "right", "pace", "right-arm seam",        2),
    ("Somerset", "L. Goldsworthy",    5, 3, "right", "spin", "off-break",             2),
    ("Somerset", "S. Davies",         6, 3, "right", "none", None,                    0),
    ("Somerset", "L. Gregory",        7, 3, "right", "pace", "right-arm fast-medium", 3),
    ("Somerset", "J. Overton",        8, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Somerset", "B. Green",          9, 2, "right", "pace", "right-arm seam",        3),
    ("Somerset", "J. Raine",         10, 1, "right", "pace", "right-arm seam",        3),
    ("Somerset", "C. Overton",       11, 1, "right", "pace", "right-arm fast-medium", 4),

    # ── GLOUCESTERSHIRE ──
    ("Gloucestershire", "C. Dent",    1, 3, "left",  "none", None,                    0),
    ("Gloucestershire", "M. Higgins", 2, 3, "right", "pace", "right-arm seam",        2),
    ("Gloucestershire", "G. Hankins", 3, 3, "right", "none", None,                    0),
    ("Gloucestershire", "J. Taylor",  4, 3, "right", "none", None,                    0),
    ("Gloucestershire", "R. Bracey",  5, 3, "right", "none", None,                    0),
    ("Gloucestershire", "M. Hammond", 6, 3, "right", "none", None,                    0),
    ("Gloucestershire", "T. Price",   7, 2, "left",  "spin", "left-arm orthodox",     3),
    ("Gloucestershire", "D. Payne",   8, 1, "right", "pace", "right-arm seam",        4),
    ("Gloucestershire", "J. Shaw",    9, 1, "right", "pace", "right-arm fast-medium", 3),
    ("Gloucestershire", "G. Drissell",10,1, "right", "spin", "off-break",             3),
    ("Gloucestershire", "B. Charlesworth",11,1,"right","pace","right-arm seam",       3),

    # ── NORTHAMPTONSHIRE ──
    ("Northamptonshire", "E. Gay",    1, 3, "left",  "none", None,                    0),
    ("Northamptonshire", "B. Curran", 2, 3, "right", "pace", "right-arm seam",        2),
    ("Northamptonshire", "R. Keogh",  3, 3, "right", "spin", "off-break",             3),
    ("Northamptonshire", "L. Procter",4, 3, "right", "spin", "off-break",             3),
    ("Northamptonshire", "A. Wakely", 5, 3, "right", "none", None,                    0),
    ("Northamptonshire", "J. Libby",  6, 3, "right", "none", None,                    0),
    ("Northamptonshire", "C. White",  7, 2, "right", "pace", "right-arm seam",        3),
    ("Northamptonshire", "B. Sanderson",8,1,"right", "pace", "right-arm seam",        4),
    ("Northamptonshire", "T. Taylor", 9, 1, "right", "pace", "right-arm seam",        3),
    ("Northamptonshire", "G. Berg",  10, 1, "right", "pace", "right-arm seam",        3),
    ("Northamptonshire", "N. Buck",  11, 1, "right", "pace", "right-arm fast",        3),

    # ── WORCESTERSHIRE ──
    ("Worcestershire", "J. Haynes",   1, 3, "right", "none", None,                    0),
    ("Worcestershire", "D. Mitchell", 2, 4, "right", "pace", "right-arm medium",      2),
    ("Worcestershire", "T. Head",     3, 4, "left",  "spin", "off-break",             2),
    ("Worcestershire", "M. Kohler-Cadmore",4,3,"right","none",None,                   0),
    ("Worcestershire", "G. Roderick", 5, 3, "right", "none", None,                    0),
    ("Worcestershire", "E. Barnard",  6, 3, "right", "pace", "right-arm seam",        3),
    ("Worcestershire", "J. Tongue",   7, 2, "right", "pace", "right-arm fast",        4),
    ("Worcestershire", "O. Cox",      8, 2, "right", "none", None,                    0),
    ("Worcestershire", "C. Morris",   9, 1, "right", "pace", "right-arm fast-medium", 4),
    ("Worcestershire", "D. Pennington",10,1,"left",  "pace", "left-arm fast-medium",  3),
    ("Worcestershire", "J. Leach",   11, 1, "left",  "spin", "left-arm orthodox",     4),

    # ── DERBYSHIRE ──
    ("Derbyshire", "L. du Plooy",     1, 3, "left",  "none", None,                    0),
    ("Derbyshire", "H. Hosein",       2, 3, "right", "none", None,                    0),
    ("Derbyshire", "W. Madsen",       3, 3, "right", "none", None,                    0),
    ("Derbyshire", "B. Aitchison",    4, 3, "right", "pace", "right-arm seam",        3),
    ("Derbyshire", "M. Critchley",    5, 3, "right", "spin", "leg-break",             3),
    ("Derbyshire", "A. Dal",          6, 2, "right", "pace", "right-arm seam",        3),
    ("Derbyshire", "J. du Plooy",     7, 2, "right", "none", None,                    0),
    ("Derbyshire", "S. Conners",      8, 1, "right", "pace", "right-arm seam",        3),
    ("Derbyshire", "M. McKiernan",    9, 1, "right", "spin", "off-break",             3),
    ("Derbyshire", "T. Wood",        10, 1, "right", "pace", "right-arm seam",        3),
    ("Derbyshire", "J. Hardman",     11, 1, "right", "pace", "right-arm seam",        3),

    # ── LEICESTERSHIRE ──
    ("Leicestershire", "C. Miles",    1, 3, "right", "pace", "right-arm seam",        3),
    ("Leicestershire", "H. Dearden",  2, 3, "right", "none", None,                    0),
    ("Leicestershire", "L. Kimber",   3, 3, "right", "none", None,                    0),
    ("Leicestershire", "N. Dexter",   4, 3, "right", "none", None,                    0),
    ("Leicestershire", "B. Mike",     5, 3, "right", "pace", "right-arm seam",        2),
    ("Leicestershire", "H. Swindells",6, 3, "right", "none", None,                    0),
    ("Leicestershire", "L. Davis",    7, 2, "right", "pace", "right-arm seam",        3),
    ("Leicestershire", "C. Benjamin", 8, 1, "right", "pace", "right-arm fast",        4),
    ("Leicestershire", "N. Patel",    9, 1, "right", "spin", "off-break",             3),
    ("Leicestershire", "G. Rhodes",  10, 1, "right", "spin", "off-break",             3),
    ("Leicestershire", "W. Davis",   11, 1, "right", "pace", "right-arm fast",        3),

    # ── SUSSEX ──
    ("Sussex", "T. Salt",             1, 3, "right", "none", None,                    0),
    ("Sussex", "H. van Zyl",          2, 3, "right", "none", None,                    0),
    ("Sussex", "S. van Zyl",          3, 3, "left",  "none", None,                    0),
    ("Sussex", "T. Clark",            4, 3, "right", "none", None,                    0),
    ("Sussex", "A. McGrath",          5, 3, "right", "none", None,                    0),
    ("Sussex", "L. Wright",           6, 3, "right", "none", None,                    0),
    ("Sussex", "J. Coles",            7, 2, "right", "pace", "right-arm seam",        3),
    ("Sussex", "O. Robinson",         8, 2, "right", "pace", "right-arm seam",        4),
    ("Sussex", "D. Wiese",            9, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Sussex", "J. Garton",          10, 1, "left",  "pace", "left-arm fast-medium",  3),
    ("Sussex", "F. Hasan",           11, 1, "right", "pace", "right-arm fast",        3),

    # ── GLAMORGAN ──
    ("Glamorgan", "N. Selman",        1, 3, "right", "none", None,                    0),
    ("Glamorgan", "E. Byrom",         2, 3, "right", "none", None,                    0),
    ("Glamorgan", "S. Northeast",     3, 3, "right", "none", None,                    0),
    ("Glamorgan", "C. Cooke",         4, 3, "right", "none", None,                    0),
    ("Glamorgan", "K. Carlson",       5, 3, "right", "none", None,                    0),
    ("Glamorgan", "D. Lloyd",         6, 3, "right", "none", None,                    0),
    ("Glamorgan", "T. van der Gugten",7, 2, "right", "pace", "right-arm fast-medium", 3),
    ("Glamorgan", "L. Carey",         8, 1, "right", "pace", "right-arm seam",        3),
    ("Glamorgan", "R. Hogan",         9, 1, "right", "pace", "right-arm seam",        3),
    ("Glamorgan", "T. Cullen",       10, 1, "right", "pace", "right-arm seam",        3),
    ("Glamorgan", "P. Sisodiya",     11, 1, "left",  "spin", "left-arm orthodox",     3),
]


def _venue_id(db, name):
    row = db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


def _team_id(db, name):
    row = db.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
    return row['id'] if row else None


def seed(db):
    # Venues
    for name, city, country in VENUES:
        if not db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone():
            db.execute("INSERT INTO venues (name, city, country) VALUES (?,?,?)",
                       (name, city, country))

    # Teams
    for name, code, colour, venue_name, team_type, league in TEAMS:
        if not db.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone():
            vid = _venue_id(db, venue_name)
            db.execute(
                "INSERT INTO teams (name, short_code, badge_colour, home_venue_id, "
                "is_real, team_type, league) VALUES (?,?,?,?,1,?,?)",
                (name, code, colour, vid, team_type, league)
            )

    # Players
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
