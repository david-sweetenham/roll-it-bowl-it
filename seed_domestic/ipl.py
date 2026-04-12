"""
seed_domestic/ipl.py
Indian Premier League: 10 franchise teams.
"""

VENUES = [
    ("MA Chidambaram Stadium",          "Chennai",    "India"),
    ("M. Chinnaswamy Stadium",           "Bangalore",  "India"),
    ("Arun Jaitley Stadium",             "Delhi",      "India"),
    ("Sawai Mansingh Stadium",           "Jaipur",     "India"),
    ("Punjab Cricket Association Stadium","Mohali",    "India"),
    ("Rajiv Gandhi International Stadium","Hyderabad", "India"),
    ("Narendra Modi Stadium",            "Ahmedabad",  "India"),
    ("BRSABV Ekana Cricket Stadium",     "Lucknow",    "India"),
]

# (name, short_code, badge_colour, home_venue_name, team_type, league)
TEAMS = [
    ("Mumbai Indians",          "MI",  "#004BA0", "Wankhede Stadium",                     "franchise", "IPL"),
    ("Chennai Super Kings",     "CSK", "#F9CD05", "MA Chidambaram Stadium",               "franchise", "IPL"),
    ("Royal Challengers Bangalore","RCB","#EC1C24","M. Chinnaswamy Stadium",              "franchise", "IPL"),
    ("Delhi Capitals",          "DC",  "#17479E", "Arun Jaitley Stadium",                 "franchise", "IPL"),
    ("Punjab Kings",            "PBK", "#ED1B24", "Punjab Cricket Association Stadium",   "franchise", "IPL"),
    ("Rajasthan Royals",        "RR",  "#E91F8B", "Sawai Mansingh Stadium",               "franchise", "IPL"),
    ("Kolkata Knight Riders",   "KKR", "#3A225D", "Eden Gardens",                         "franchise", "IPL"),
    ("Sunrisers Hyderabad",     "SRH", "#FF822A", "Rajiv Gandhi International Stadium",   "franchise", "IPL"),
    ("Gujarat Titans",          "GT",  "#1C1C1C", "Narendra Modi Stadium",                "franchise", "IPL"),
    ("Lucknow Super Giants",    "LSG", "#A4C8E0", "BRSABV Ekana Cricket Stadium",         "franchise", "IPL"),
]

SQUADS = [

    # ── MUMBAI INDIANS ──
    ("Mumbai Indians", "R. Sharma",        1, 4, "right", "spin", "off-break",             1),
    ("Mumbai Indians", "I. Kishan",        2, 4, "left",  "none", None,                    0),
    ("Mumbai Indians", "S. Iyer",          3, 4, "right", "none", None,                    0),
    ("Mumbai Indians", "S. Tendulkar",     4, 3, "right", "none", None,                    0),
    ("Mumbai Indians", "H. Pandya",        5, 4, "right", "pace", "right-arm fast-medium", 3),
    ("Mumbai Indians", "T. Stubbs",        6, 4, "right", "none", None,                    0),
    ("Mumbai Indians", "K. Pollard",       7, 4, "right", "pace", "right-arm fast-medium", 3),
    ("Mumbai Indians", "J. Bumrah",        8, 2, "right", "pace", "right-arm fast",        5),
    ("Mumbai Indians", "J. Behrendorff",   9, 1, "left",  "pace", "left-arm fast",         4),
    ("Mumbai Indians", "P. Chawla",       10, 1, "right", "spin", "leg-break",             3),
    ("Mumbai Indians", "A. Nehra",        11, 1, "left",  "pace", "left-arm fast",         4),

    # ── CHENNAI SUPER KINGS ──
    ("Chennai Super Kings", "R. Gaikwad",  1, 4, "right", "none", None,                    0),
    ("Chennai Super Kings", "D. Conway",   2, 4, "left",  "none", None,                    0),
    ("Chennai Super Kings", "S. Raina",    3, 4, "left",  "spin", "off-break",             2),
    ("Chennai Super Kings", "A. Rayudu",   4, 4, "right", "none", None,                    0),
    ("Chennai Super Kings", "M. Dhoni",    5, 4, "right", "none", None,                    0),
    ("Chennai Super Kings", "R. Jadeja",   6, 4, "left",  "spin", "left-arm orthodox",     4),
    ("Chennai Super Kings", "S. Dube",     7, 3, "left",  "pace", "right-arm seam",        2),
    ("Chennai Super Kings", "D. Chahar",   8, 3, "right", "pace", "right-arm fast-medium", 4),
    ("Chennai Super Kings", "M. Pathirana",9, 1, "right", "pace", "right-arm fast",        4),
    ("Chennai Super Kings", "T. Boult",   10, 1, "left",  "pace", "left-arm fast",         5),
    ("Chennai Super Kings", "R. Ashwin",  11, 1, "right", "spin", "off-break",             5),

    # ── ROYAL CHALLENGERS BANGALORE ──
    ("Royal Challengers Bangalore", "V. Kohli",     1, 5, "right", "none", None,           0),
    ("Royal Challengers Bangalore", "F. du Plessis",2, 4, "right", "none", None,           0),
    ("Royal Challengers Bangalore", "G. Maxwell",   3, 5, "right", "spin", "off-break",    3),
    ("Royal Challengers Bangalore", "R. Patidar",   4, 4, "right", "none", None,           0),
    ("Royal Challengers Bangalore", "S. Dube",      5, 3, "left",  "pace", "right-arm seam",2),
    ("Royal Challengers Bangalore", "D. Padikkal",  6, 4, "left",  "none", None,           0),
    ("Royal Challengers Bangalore", "A. Russell",   7, 4, "right", "pace", "right-arm fast",4),
    ("Royal Challengers Bangalore", "H. Vihari",    8, 2, "right", "none", None,           0),
    ("Royal Challengers Bangalore", "M. Siraj",     9, 1, "right", "pace", "right-arm fast-medium",4),
    ("Royal Challengers Bangalore", "Y. Dayal",    10, 1, "left",  "pace", "left-arm fast-medium",3),
    ("Royal Challengers Bangalore", "W. Hasaranga", 11,1, "right", "spin", "leg-break",    4),

    # ── DELHI CAPITALS ──
    ("Delhi Capitals", "D. Warner",        1, 4, "left",  "none", None,                    0),
    ("Delhi Capitals", "P. Shaw",          2, 4, "right", "none", None,                    0),
    ("Delhi Capitals", "S. Gill",          3, 4, "right", "none", None,                    0),
    ("Delhi Capitals", "M. Agarwal",       4, 4, "right", "none", None,                    0),
    ("Delhi Capitals", "A. Pant",          5, 4, "left",  "none", None,                    0),
    ("Delhi Capitals", "R. Powell",        6, 4, "right", "none", None,                    0),
    ("Delhi Capitals", "A. Nortje",        7, 2, "right", "pace", "right-arm fast",        5),
    ("Delhi Capitals", "A. Mishra",        8, 1, "right", "spin", "leg-break",             3),
    ("Delhi Capitals", "K. Rabada",        9, 1, "right", "pace", "right-arm fast",        5),
    ("Delhi Capitals", "C. Woakes",       10, 2, "right", "pace", "right-arm seam",        4),
    ("Delhi Capitals", "R. Ashwin",       11, 1, "right", "spin", "off-break",             5),

    # ── PUNJAB KINGS ──
    ("Punjab Kings", "S. Dhawan",          1, 4, "left",  "none", None,                    0),
    ("Punjab Kings", "J. Bairstow",        2, 4, "right", "none", None,                    0),
    ("Punjab Kings", "L. Livingstone",     3, 4, "right", "spin", "leg-break",             3),
    ("Punjab Kings", "A. Raghuvanshi",     4, 3, "right", "none", None,                    0),
    ("Punjab Kings", "R. Dhruv Jurel",     5, 3, "right", "none", None,                    0),
    ("Punjab Kings", "S. Curran",          6, 3, "left",  "pace", "left-arm fast-medium",  3),
    ("Punjab Kings", "S. Khan",            7, 2, "right", "none", None,                    0),
    ("Punjab Kings", "A. Markram",         8, 3, "right", "spin", "off-break",             3),
    ("Punjab Kings", "H. Rauf",            9, 1, "right", "pace", "right-arm fast",        4),
    ("Punjab Kings", "R. Chahar",         10, 1, "right", "pace", "right-arm fast-medium", 3),
    ("Punjab Kings", "B. Kumar",          11, 1, "right", "pace", "right-arm fast-medium", 4),

    # ── RAJASTHAN ROYALS ──
    ("Rajasthan Royals", "Y. Jaiswal",     1, 4, "left",  "none", None,                    0),
    ("Rajasthan Royals", "J. Buttler",     2, 5, "right", "none", None,                    0),
    ("Rajasthan Royals", "S. Samson",      3, 4, "right", "none", None,                    0),
    ("Rajasthan Royals", "D. Miller",      4, 4, "left",  "none", None,                    0),
    ("Rajasthan Royals", "R. Parag",       5, 4, "right", "spin", "off-break",             2),
    ("Rajasthan Royals", "S. Hetmyer",     6, 4, "left",  "none", None,                    0),
    ("Rajasthan Royals", "R. Ashwin",      7, 2, "right", "spin", "off-break",             5),
    ("Rajasthan Royals", "T. Boult",       8, 1, "left",  "pace", "left-arm fast",         5),
    ("Rajasthan Royals", "P. Jurel",       9, 1, "right", "none", None,                    0),
    ("Rajasthan Royals", "Y. Dayal",      10, 1, "left",  "pace", "left-arm fast-medium",  3),
    ("Rajasthan Royals", "A. Zampa",      11, 1, "right", "spin", "leg-break",             4),

    # ── KOLKATA KNIGHT RIDERS ──
    ("Kolkata Knight Riders", "S. Gill",        1, 4, "right", "none", None,               0),
    ("Kolkata Knight Riders", "V. Iyer",         2, 4, "right", "none", None,              0),
    ("Kolkata Knight Riders", "A. Russell",      3, 4, "right", "pace", "right-arm fast",  4),
    ("Kolkata Knight Riders", "N. Rana",         4, 4, "left",  "pace", "right-arm medium",2),
    ("Kolkata Knight Riders", "R. Baba",         5, 3, "right", "none", None,              0),
    ("Kolkata Knight Riders", "S. Narine",       6, 3, "right", "spin", "off-break",       4),
    ("Kolkata Knight Riders", "T. David",        7, 4, "right", "none", None,              0),
    ("Kolkata Knight Riders", "P. Krishna",      8, 2, "right", "pace", "right-arm fast",  4),
    ("Kolkata Knight Riders", "H. Ferguson",     9, 1, "right", "pace", "right-arm fast",  4),
    ("Kolkata Knight Riders", "V. Chakravarthy",10, 1, "right", "spin", "leg-break",       4),
    ("Kolkata Knight Riders", "M. Starc",       11, 1, "left",  "pace", "left-arm fast",   5),

    # ── SUNRISERS HYDERABAD ──
    ("Sunrisers Hyderabad", "M. Agarwal",       1, 4, "right", "none", None,               0),
    ("Sunrisers Hyderabad", "T. Head",           2, 4, "left",  "spin", "off-break",       2),
    ("Sunrisers Hyderabad", "H. Klaasen",        3, 5, "right", "none", None,              0),
    ("Sunrisers Hyderabad", "A. Sharma",         4, 4, "right", "none", None,              0),
    ("Sunrisers Hyderabad", "N. Pooran",         5, 4, "left",  "none", None,              0),
    ("Sunrisers Hyderabad", "S. Marsh",          6, 3, "right", "none", None,              0),
    ("Sunrisers Hyderabad", "P. Cummins",        7, 3, "right", "pace", "right-arm fast",  5),
    ("Sunrisers Hyderabad", "A. Markram",        8, 3, "right", "spin", "off-break",       3),
    ("Sunrisers Hyderabad", "M. Rashid",         9, 1, "right", "spin", "leg-break",       5),
    ("Sunrisers Hyderabad", "B. Kumar",         10, 1, "right", "pace", "right-arm fast-medium",4),
    ("Sunrisers Hyderabad", "T. Natarajan",     11, 1, "left",  "pace", "left-arm fast-medium",3),

    # ── GUJARAT TITANS ──
    ("Gujarat Titans", "S. Gill",               1, 4, "right", "none", None,               0),
    ("Gujarat Titans", "W. Saha",               2, 3, "right", "none", None,               0),
    ("Gujarat Titans", "D. Miller",             3, 4, "left",  "none", None,               0),
    ("Gujarat Titans", "A. Pandya",             4, 4, "right", "pace", "right-arm fast-medium",3),
    ("Gujarat Titans", "R. Tewatia",            5, 4, "right", "spin", "leg-break",        2),
    ("Gujarat Titans", "S. Sudharsan",          6, 3, "right", "none", None,               0),
    ("Gujarat Titans", "R. Khan",               7, 2, "right", "spin", "leg-break",        4),
    ("Gujarat Titans", "N. Khan",               8, 2, "left",  "pace", "left-arm fast",    4),
    ("Gujarat Titans", "M. Shami",              9, 1, "right", "pace", "right-arm fast-medium",5),
    ("Gujarat Titans", "A. Joseph",            10, 1, "right", "pace", "right-arm fast",   4),
    ("Gujarat Titans", "Y. Dayal",             11, 1, "left",  "pace", "left-arm fast-medium",3),

    # ── LUCKNOW SUPER GIANTS ──
    ("Lucknow Super Giants", "Q. de Kock",      1, 5, "left",  "none", None,               0),
    ("Lucknow Super Giants", "K. Rahul",         2, 5, "right", "none", None,              0),
    ("Lucknow Super Giants", "M. Agarwal",       3, 4, "right", "none", None,              0),
    ("Lucknow Super Giants", "N. Pooran",        4, 4, "left",  "none", None,              0),
    ("Lucknow Super Giants", "D. Hooda",         5, 3, "right", "spin", "off-break",       2),
    ("Lucknow Super Giants", "K. Gowtham",       6, 3, "right", "spin", "off-break",       3),
    ("Lucknow Super Giants", "A. Badoni",        7, 3, "right", "none", None,              0),
    ("Lucknow Super Giants", "M. Vohra",         8, 2, "right", "pace", "right-arm seam",  2),
    ("Lucknow Super Giants", "A. Khan",          9, 1, "right", "pace", "right-arm fast",  4),
    ("Lucknow Super Giants", "R. Bishnoi",      10, 1, "right", "spin", "leg-break",       4),
    ("Lucknow Super Giants", "M. Gill",         11, 1, "right", "pace", "right-arm fast",  3),
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
