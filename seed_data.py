"""
seed_data.py — Pre-loads venues, teams, and full squads into ribi.db.
Idempotent: does nothing if any teams already exist.
"""


def seed(db):
    _insert_venues(db)
    _insert_teams(db)
    _insert_players(db)
    _insert_journal_prompts_meta(db)
    seed_world_records(db)

    # Domestic and franchise competitions
    from seed_domestic import england_county, australia_domestic, australia_bbl, ipl, cpl, psl
    england_county.seed(db)
    australia_domestic.seed(db)
    australia_bbl.seed(db)
    ipl.seed(db)
    cpl.seed(db)
    psl.seed(db)

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
        ("Harare Sports Club",          "Harare",     "Zimbabwe"),
        ("Queens Sports Club",          "Bulawayo",   "Zimbabwe"),
        ("Malahide Cricket Club Ground","Dublin",     "Ireland"),
        ("Civil Service Cricket Club",  "Belfast",    "Ireland"),
        ("The Grange Club",             "Edinburgh",  "Scotland"),
        ("VRA Ground",                  "Amstelveen", "Netherlands"),
        ("Wanderers Cricket Ground",    "Windhoek",   "Namibia"),
        ("Tribhuvan University Ground", "Kirtipur",   "Nepal"),
        ("Al Amerat Cricket Ground",    "Muscat",     "Oman"),
        ("Grand Prairie Stadium",       "Dallas",     "United States"),
        ("Maple Leaf North-West Ground","King City",  "Canada"),
    ]
    for name, city, country in venues:
        exists = db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone()
        if exists:
            continue
        db.execute(
            "INSERT INTO venues (name, city, country) VALUES (?, ?, ?)",
            (name, city, country)
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
        ("Zimbabwe",     "ZIM", "#d4af37", "Harare Sports Club"),
        ("Ireland",      "IRE", "#169b62", "Malahide Cricket Club Ground"),
        ("Scotland",     "SCO", "#005eb8", "The Grange Club"),
        ("Netherlands",  "NED", "#f36c21", "VRA Ground"),
        ("Namibia",      "NAM", "#003580", "Wanderers Cricket Ground"),
        ("Nepal",        "NEP", "#dc143c", "Tribhuvan University Ground"),
        ("UAE",          "UAE", "#c8102e", "Dubai International Stadium"),
        ("Oman",         "OMA", "#b22222", "Al Amerat Cricket Ground"),
        ("United States","USA", "#3c3b6e", "Grand Prairie Stadium"),
        ("Canada",       "CAN", "#d52b1e", "Maple Leaf North-West Ground"),
    ]
    for name, code, colour, venue_name in teams:
        exists = db.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
        if exists:
            continue
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

    # ── ZIMBABWE ─────────────────────────────────────────────────────────────
    ("Zimbabwe", "J. Gumbie",         1, 3, "left",  "none",  None,                   0),
    ("Zimbabwe", "C. Ervine",         2, 4, "left",  "none",  None,                   0),
    ("Zimbabwe", "S. Raza",           3, 5, "right", "spin",  "off-break",            3),
    ("Zimbabwe", "T. Marumani",       4, 3, "left",  "none",  None,                   0),
    ("Zimbabwe", "C. Madande",        5, 3, "right", "none",  None,                   0),
    ("Zimbabwe", "R. Burl",           6, 3, "right", "spin",  "leg-break",            3),
    ("Zimbabwe", "W. Madhevere",      7, 3, "right", "spin",  "off-break",            2),
    ("Zimbabwe", "L. Jongwe",         8, 2, "right", "pace",  "right-arm medium",     3),
    ("Zimbabwe", "B. Muzarabani",     9, 1, "right", "pace",  "right-arm fast",       4),
    ("Zimbabwe", "R. Ngarava",       10, 1, "left",  "pace",  "left-arm fast-medium", 4),
    ("Zimbabwe", "T. Gwandu",        11, 1, "right", "pace",  "right-arm medium",     3),

    # ── IRELAND ──────────────────────────────────────────────────────────────
    ("Ireland", "A. Balbirnie",       1, 4, "right", "none",  None,                   0),
    ("Ireland", "P. Stirling",        2, 4, "right", "spin",  "off-break",            1),
    ("Ireland", "L. Tucker",          3, 4, "right", "none",  None,                   0),
    ("Ireland", "H. Tector",          4, 4, "right", "none",  None,                   0),
    ("Ireland", "C. Campher",         5, 3, "right", "pace",  "right-arm medium",     3),
    ("Ireland", "G. Dockrell",        6, 3, "left",  "spin",  "left-arm orthodox",    3),
    ("Ireland", "C. Adair",           7, 3, "right", "pace",  "right-arm medium-fast",3),
    ("Ireland", "A. McBrine",         8, 2, "right", "spin",  "off-break",            4),
    ("Ireland", "M. Humphreys",       9, 1, "left",  "spin",  "left-arm orthodox",    3),
    ("Ireland", "J. Little",         10, 1, "left",  "pace",  "left-arm fast-medium", 4),
    ("Ireland", "M. Adair",          11, 2, "right", "pace",  "right-arm fast-medium",4),

    # ── SCOTLAND ─────────────────────────────────────────────────────────────
    ("Scotland", "G. Munsey",         1, 4, "left",  "none",  None,                   0),
    ("Scotland", "M. Cross",          2, 3, "right", "none",  None,                   0),
    ("Scotland", "B. McMullen",       3, 4, "right", "pace",  "right-arm medium",     3),
    ("Scotland", "R. Berrington",     4, 4, "right", "none",  None,                   0),
    ("Scotland", "M. Jones",          5, 4, "right", "none",  None,                   0),
    ("Scotland", "M. Leask",          6, 3, "right", "spin",  "leg-break",            3),
    ("Scotland", "C. Greaves",        7, 3, "right", "spin",  "leg-break",            3),
    ("Scotland", "M. Watt",           8, 2, "left",  "spin",  "left-arm orthodox",    4),
    ("Scotland", "B. Wheal",          9, 1, "right", "pace",  "right-arm fast-medium",4),
    ("Scotland", "C. Sole",          10, 1, "right", "pace",  "right-arm medium-fast",4),
    ("Scotland", "S. Sharif",        11, 1, "right", "pace",  "right-arm medium-fast",3),

    # ── NETHERLANDS ──────────────────────────────────────────────────────────
    ("Netherlands", "M. O'Dowd",      1, 4, "right", "none",  None,                   0),
    ("Netherlands", "V. Singh",       2, 3, "left",  "none",  None,                   0),
    ("Netherlands", "W. Barresi",     3, 3, "right", "none",  None,                   0),
    ("Netherlands", "B. de Leede",    4, 4, "right", "pace",  "right-arm medium",     3),
    ("Netherlands", "S. Edwards",     5, 3, "right", "none",  None,                   0),
    ("Netherlands", "T. Nidamanuru",  6, 3, "right", "none",  None,                   0),
    ("Netherlands", "R. van der Merwe",7,3, "left",  "spin",  "left-arm orthodox",    4),
    ("Netherlands", "T. Pringle",     8, 2, "left",  "spin",  "left-arm orthodox",    3),
    ("Netherlands", "P. van Meekeren",9, 1, "right", "pace",  "right-arm fast-medium",4),
    ("Netherlands", "L. van Beek",   10, 1, "right", "pace",  "right-arm medium-fast",4),
    ("Netherlands", "A. Dutt",       11, 1, "right", "spin",  "off-break",            4),

    # ── NAMIBIA ──────────────────────────────────────────────────────────────
    ("Namibia", "M. van Lingen",      1, 3, "left",  "none",  None,                   0),
    ("Namibia", "J. Smit",            2, 3, "right", "pace",  "right-arm medium",     2),
    ("Namibia", "N. Davin",           3, 3, "right", "none",  None,                   0),
    ("Namibia", "G. Erasmus",         4, 4, "right", "spin",  "off-break",            3),
    ("Namibia", "J.J. Smit",          5, 3, "left",  "pace",  "left-arm medium-fast", 3),
    ("Namibia", "Z. Green",           6, 3, "right", "none",  None,                   0),
    ("Namibia", "D. Wiese",           7, 4, "right", "pace",  "right-arm fast-medium",4),
    ("Namibia", "J. Loftie-Eaton",    8, 3, "right", "spin",  "off-break",            2),
    ("Namibia", "R. Trumpelmann",     9, 1, "left",  "pace",  "left-arm fast-medium", 4),
    ("Namibia", "B. Scholtz",        10, 1, "left",  "spin",  "left-arm orthodox",    4),
    ("Namibia", "T. Lungameni",      11, 1, "right", "pace",  "right-arm fast-medium",3),

    # ── NEPAL ────────────────────────────────────────────────────────────────
    ("Nepal", "K. Bhurtel",           1, 4, "right", "none",  None,                   0),
    ("Nepal", "A. Sheikh",            2, 3, "right", "none",  None,                   0),
    ("Nepal", "G. Jha",               3, 3, "right", "pace",  "right-arm medium",     2),
    ("Nepal", "R. Paudel",            4, 4, "right", "none",  None,                   0),
    ("Nepal", "D. Airee",             5, 3, "right", "spin",  "leg-break",            2),
    ("Nepal", "K. Malla",             6, 3, "left",  "spin",  "off-break",            2),
    ("Nepal", "S. Kami",              7, 2, "right", "pace",  "right-arm fast-medium",4),
    ("Nepal", "A. Sah",               8, 2, "right", "none",  None,                   0),
    ("Nepal", "S. Lamichhane",        9, 2, "right", "spin",  "leg-break",            5),
    ("Nepal", "K. Karan",            10, 1, "right", "pace",  "right-arm fast-medium",4),
    ("Nepal", "L. Rajbanshi",        11, 1, "left",  "spin",  "left-arm orthodox",    4),

    # ── UAE ──────────────────────────────────────────────────────────────────
    ("UAE", "M. Waseem",              1, 4, "left",  "none",  None,                   0),
    ("UAE", "V. Aravind",             2, 3, "right", "none",  None,                   0),
    ("UAE", "A. Khan",                3, 3, "right", "none",  None,                   0),
    ("UAE", "A. Sharafu",             4, 4, "right", "none",  None,                   0),
    ("UAE", "A. Naseer",              5, 3, "left",  "pace",  "left-arm medium-fast", 3),
    ("UAE", "B. Hameed",              6, 3, "right", "spin",  "leg-break",            3),
    ("UAE", "Aayan Khan",             7, 2, "left",  "spin",  "left-arm orthodox",    4),
    ("UAE", "J. Siddique",            8, 2, "right", "pace",  "right-arm medium-fast",3),
    ("UAE", "K. Sharma",              9, 1, "left",  "spin",  "left-arm orthodox",    3),
    ("UAE", "A. Javed",              10, 1, "right", "pace",  "right-arm fast-medium",4),
    ("UAE", "M. Jawadullah",         11, 1, "left",  "pace",  "left-arm fast-medium", 4),

    # ── OMAN ─────────────────────────────────────────────────────────────────
    ("Oman", "K. Prajapati",          1, 3, "left",  "none",  None,                   0),
    ("Oman", "J. Singh",              2, 4, "right", "none",  None,                   0),
    ("Oman", "A. Ilyas",              3, 4, "right", "spin",  "off-break",            2),
    ("Oman", "S. Khan",               4, 3, "right", "pace",  "right-arm medium",     2),
    ("Oman", "Z. Maqsood",            5, 4, "left",  "spin",  "left-arm orthodox",    4),
    ("Oman", "A. Kaleem",             6, 3, "left",  "spin",  "left-arm orthodox",    3),
    ("Oman", "M. Nadeem",             7, 3, "left",  "spin",  "left-arm orthodox",    3),
    ("Oman", "N. Khan",               8, 2, "right", "pace",  "right-arm medium-fast",3),
    ("Oman", "B. Khan",               9, 1, "left",  "pace",  "left-arm fast-medium", 4),
    ("Oman", "K. Ali",               10, 1, "right", "spin",  "off-break",            3),
    ("Oman", "F. Butt",              11, 1, "left",  "pace",  "left-arm fast-medium", 4),

    # ── UNITED STATES ────────────────────────────────────────────────────────
    ("United States", "S. Jahangir",  1, 3, "right", "none",  None,                   0),
    ("United States", "A. Jones",     2, 4, "right", "none",  None,                   0),
    ("United States", "M. Patel",     3, 4, "right", "none",  None,                   0),
    ("United States", "A. Gous",      4, 4, "right", "none",  None,                   0),
    ("United States", "H. Singh",     5, 3, "left",  "spin",  "left-arm orthodox",    3),
    ("United States", "N. Kenjige",   6, 2, "left",  "spin",  "left-arm orthodox",    4),
    ("United States", "C. Anderson",  7, 3, "left",  "pace",  "left-arm fast-medium", 3),
    ("United States", "A. Khan",      8, 2, "right", "pace",  "right-arm fast",       5),
    ("United States", "S. Netravalkar",9,1, "left",  "pace",  "left-arm fast-medium", 5),
    ("United States", "J. Singh",    10, 1, "right", "pace",  "right-arm fast-medium",3),
    ("United States", "S. Taylor",   11, 2, "right", "spin",  "off-break",            2),

    # ── CANADA ───────────────────────────────────────────────────────────────
    ("Canada", "A. Kumar",            1, 3, "right", "none",  None,                   0),
    ("Canada", "N. Kirton",           2, 4, "left",  "none",  None,                   0),
    ("Canada", "P. Kumar",            3, 3, "right", "pace",  "right-arm medium",     2),
    ("Canada", "A. Johnson",          4, 4, "right", "none",  None,                   0),
    ("Canada", "S. Movva",            5, 3, "right", "none",  None,                   0),
    ("Canada", "D. Heyliger",         6, 3, "right", "pace",  "right-arm medium-fast",4),
    ("Canada", "S. Zafar",            7, 3, "left",  "spin",  "left-arm orthodox",    4),
    ("Canada", "A. Sana",             8, 2, "right", "pace",  "right-arm medium-fast",4),
    ("Canada", "K. Nitish",           9, 2, "right", "spin",  "off-break",            2),
    ("Canada", "J. Gordon",          10, 1, "right", "pace",  "right-arm fast-medium",3),
    ("Canada", "C. Kallicharan",     11, 2, "left",  "none",  None,                   0),
]


def _insert_players(db):
    for row in SQUADS:
        team_name, name, pos, bat_rat, bat_hand, bowl_type, bowl_action, bowl_rat = row
        team_id = _team_id(db, team_name)
        if team_id is None:
            print(f"  WARNING: team '{team_name}' not found for player '{name}'")
            continue
        exists = db.execute(
            "SELECT id FROM players WHERE team_id=? AND name=?",
            (team_id, name)
        ).fetchone()
        if exists:
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


# ── The Hundred ────────────────────────────────────────────────────────────────

# "The Hundred" is a registered trademark of the England and Wales Cricket Board (ECB).
# The team names Birmingham Phoenix, London Spirit, Manchester Super Giants, MI London,
# Southern Brave, Sunrisers Leeds, Trent Rockets, and Welsh Fire are trademarks of their
# respective owners. This is an independent fan recreation not affiliated with the ECB.

HUNDRED_VENUES = [
    # Existing venues that need flagging — also add missing Hundred grounds
    # (name, city, country)  — inserted only if not present, then flagged
    ("Lord's Cricket Ground",      "London",       "England"),
    ("The Oval",                   "London",       "England"),
    ("Headingley",                 "Leeds",        "England"),
    ("Edgbaston",                  "Birmingham",   "England"),
    ("Old Trafford",               "Manchester",   "England"),
    ("Ageas Bowl",                 "Southampton",  "England"),
    ("Trent Bridge",               "Nottingham",   "England"),
    ("Sophia Gardens",             "Cardiff",      "Wales"),
]

# Tuple: (team_name, player_name, batting_pos, bat_rating, bat_hand,
#          bowl_type, bowl_action, bowl_rating)
HUNDRED_SQUADS = [

    # ── BIRMINGHAM PHOENIX ────────────────────────────────────────────────────
    ("Birmingham Phoenix", "P. Salt",          1, 4, "right", "none",  None,                       0),
    ("Birmingham Phoenix", "D. Mousley",       2, 3, "right", "none",  None,                       0),
    ("Birmingham Phoenix", "H. Hameed",        3, 3, "right", "none",  None,                       0),
    ("Birmingham Phoenix", "M. Critchley",     4, 3, "right", "spin",  "leg-break",                3),
    ("Birmingham Phoenix", "B. Cox",           5, 3, "right", "none",  None,                       0),
    ("Birmingham Phoenix", "K. Pieters",       6, 3, "right", "none",  None,                       0),
    ("Birmingham Phoenix", "L. Banks",         7, 3, "left",  "spin",  "left-arm orthodox",        3),
    ("Birmingham Phoenix", "C. Woakes",        8, 3, "right", "pace",  "right-arm seam",           4),
    ("Birmingham Phoenix", "H. Brookes",       9, 2, "right", "pace",  "right-arm fast-medium",    3),
    ("Birmingham Phoenix", "T. Mills",        10, 2, "left",  "pace",  "left-arm fast",            4),
    ("Birmingham Phoenix", "O. Hannon-Dalby", 11, 1, "right", "pace",  "right-arm fast-medium",    3),
    ("Birmingham Phoenix", "E. Bamber",       12, 1, "right", "pace",  "right-arm fast",           4),
    ("Birmingham Phoenix", "R. Patel",        13, 2, "right", "spin",  "off-break",                3),
    ("Birmingham Phoenix", "F. Vilas",        14, 4, "right", "none",  None,                       0),
    ("Birmingham Phoenix", "J. Finch",        15, 3, "right", "spin",  "off-break",                2),

    # ── LONDON SPIRIT ─────────────────────────────────────────────────────────
    ("London Spirit", "Z. Crawley",          1, 3, "right", "none",  None,                         0),
    ("London Spirit", "J. Roy",              2, 4, "right", "none",  None,                         0),
    ("London Spirit", "D. Vince",            3, 3, "right", "none",  None,                         0),
    ("London Spirit", "R. Bopara",           4, 3, "right", "pace",  "right-arm medium",           2),
    ("London Spirit", "J. de Silva",         5, 3, "right", "spin",  "off-break",                  3),
    ("London Spirit", "J. Overton",          6, 3, "right", "pace",  "right-arm fast-medium",      3),
    ("London Spirit", "G. Clark",            7, 3, "right", "none",  None,                         0),
    ("London Spirit", "Z. Gohar",            8, 2, "left",  "spin",  "left-arm orthodox",          4),
    ("London Spirit", "D. Payne",            9, 1, "left",  "pace",  "left-arm fast-medium",       3),
    ("London Spirit", "C. McKerr",          10, 1, "right", "pace",  "right-arm fast",             3),
    ("London Spirit", "B. White",           11, 1, "right", "pace",  "right-arm fast-medium",      3),
    ("London Spirit", "M. Quinn",           12, 1, "right", "pace",  "right-arm fast",             4),
    ("London Spirit", "L. Trevaskis",       13, 2, "left",  "spin",  "left-arm orthodox",          3),
    ("London Spirit", "S. Robson",          14, 3, "right", "none",  None,                         0),
    ("London Spirit", "P. Handscomb",       15, 4, "right", "none",  None,                         0),

    # ── MANCHESTER SUPER GIANTS ───────────────────────────────────────────────
    ("Manchester Super Giants", "L. Livingstone",   1, 4, "right", "spin",  "leg-break",           2),
    ("Manchester Super Giants", "S. Hain",          2, 3, "right", "none",  None,                  0),
    ("Manchester Super Giants", "J. Buttler",       3, 5, "right", "none",  None,                  0),
    ("Manchester Super Giants", "T. Head",          4, 4, "left",  "spin",  "off-break",           2),
    ("Manchester Super Giants", "D. Bedingham",     5, 3, "right", "none",  None,                  0),
    ("Manchester Super Giants", "R. Gleeson",       6, 1, "right", "pace",  "right-arm fast",      4),
    ("Manchester Super Giants", "M. Parkinson",     7, 1, "right", "spin",  "leg-break",           4),
    ("Manchester Super Giants", "T. Hartley",       8, 2, "left",  "spin",  "left-arm orthodox",   4),
    ("Manchester Super Giants", "L. Wood",          9, 2, "left",  "pace",  "left-arm fast-medium",3),
    ("Manchester Super Giants", "K. Carver",       10, 1, "right", "spin",  "leg-break",           3),
    ("Manchester Super Giants", "J. Blatherwick",  11, 1, "right", "pace",  "right-arm fast",      3),
    ("Manchester Super Giants", "J. Anderson",     12, 1, "right", "pace",  "right-arm fast-medium",4),
    ("Manchester Super Giants", "M. Revis",        13, 3, "right", "none",  None,                  0),
    ("Manchester Super Giants", "H. Hameed",       14, 3, "right", "none",  None,                  0),
    ("Manchester Super Giants", "T. Tully",        15, 2, "right", "pace",  "right-arm medium",    2),

    # ── MI LONDON ─────────────────────────────────────────────────────────────
    ("MI London", "J. Burns",           1, 3, "right", "none",  None,                               0),
    ("MI London", "W. Jacks",           2, 4, "right", "spin",  "off-break",                        3),
    ("MI London", "D. Miller",          3, 4, "left",  "none",  None,                               0),
    ("MI London", "S. Curran",          4, 3, "left",  "pace",  "left-arm fast-medium",             4),
    ("MI London", "M. Pepper",          5, 3, "right", "none",  None,                               0),
    ("MI London", "L. Plunkett",        6, 3, "right", "pace",  "right-arm fast-medium",            3),
    ("MI London", "J. Winslow",         7, 3, "right", "none",  None,                               0),
    ("MI London", "D. Willey",          8, 3, "left",  "pace",  "left-arm fast-medium",             4),
    ("MI London", "T. Curran",          9, 3, "right", "pace",  "right-arm fast-medium",            4),
    ("MI London", "R. Clarke",         10, 1, "right", "pace",  "right-arm fast-medium",            3),
    ("MI London", "D. Moriarty",       11, 1, "left",  "spin",  "left-arm orthodox",                4),
    ("MI London", "B. Geddes",         12, 1, "right", "pace",  "right-arm fast",                   3),
    ("MI London", "J. Smith",          13, 3, "right", "spin",  "off-break",                        2),
    ("MI London", "O. Pope",           14, 4, "right", "none",  None,                               0),
    ("MI London", "N. Maddinson",      15, 3, "left",  "none",  None,                               0),

    # ── SOUTHERN BRAVE ────────────────────────────────────────────────────────
    ("Southern Brave", "J. Vince",          1, 4, "right", "none",  None,                           0),
    ("Southern Brave", "Q. de Kock",        2, 4, "left",  "none",  None,                           0),
    ("Southern Brave", "T. Alsop",          3, 3, "left",  "none",  None,                           0),
    ("Southern Brave", "A. Rossington",     4, 3, "right", "none",  None,                           0),
    ("Southern Brave", "C. Morris",         5, 3, "right", "pace",  "right-arm fast-medium",        4),
    ("Southern Brave", "A. Turner",         6, 4, "right", "spin",  "off-break",                    2),
    ("Southern Brave", "C. Jordan",         7, 2, "right", "pace",  "right-arm fast",               4),
    ("Southern Brave", "D. Pretorius",      8, 2, "right", "pace",  "right-arm fast-medium",        3),
    ("Southern Brave", "R. Topley",         9, 1, "left",  "pace",  "left-arm fast",                4),
    ("Southern Brave", "C. Overton",       10, 2, "right", "pace",  "right-arm fast-medium",        3),
    ("Southern Brave", "L. Dawson",        11, 3, "right", "spin",  "left-arm orthodox",            3),
    ("Southern Brave", "F. Organ",         12, 3, "right", "spin",  "off-break",                    3),
    ("Southern Brave", "J. Weatherley",    13, 3, "right", "none",  None,                           0),
    ("Southern Brave", "I. Holland",       14, 2, "right", "spin",  "off-break",                    3),
    ("Southern Brave", "T. Prest",         15, 3, "right", "none",  None,                           0),

    # ── SUNRISERS LEEDS ───────────────────────────────────────────────────────
    ("Sunrisers Leeds", "A. Lyth",           1, 3, "left",  "none",  None,                           0),
    ("Sunrisers Leeds", "D. Malan",          2, 4, "left",  "spin",  "leg-break",                    1),
    ("Sunrisers Leeds", "H. Brook",          3, 5, "right", "none",  None,                           0),
    ("Sunrisers Leeds", "M. Lees",           4, 3, "right", "none",  None,                           0),
    ("Sunrisers Leeds", "J. Tattersall",     5, 3, "right", "none",  None,                           0),
    ("Sunrisers Leeds", "A. Hickey",         6, 3, "left",  "none",  None,                           0),
    ("Sunrisers Leeds", "D. Willey",         7, 3, "left",  "pace",  "left-arm fast-medium",         4),
    ("Sunrisers Leeds", "A. Waite",          8, 2, "right", "pace",  "right-arm fast-medium",        3),
    ("Sunrisers Leeds", "M. Fisher",         9, 1, "right", "pace",  "right-arm fast",               3),
    ("Sunrisers Leeds", "J. Thompson",      10, 1, "right", "pace",  "right-arm fast-medium",        3),
    ("Sunrisers Leeds", "M. Cummins",       11, 1, "right", "pace",  "right-arm fast",               4),
    ("Sunrisers Leeds", "D. Wiese",         12, 3, "right", "pace",  "right-arm fast-medium",        3),
    ("Sunrisers Leeds", "A. Rashid",        13, 2, "right", "spin",  "leg-break",                    4),
    ("Sunrisers Leeds", "T. Köhler-Cadmore",14, 4, "right", "none",  None,                           0),
    ("Sunrisers Leeds", "B. Coad",          15, 1, "right", "pace",  "right-arm fast-medium",        3),

    # ── TRENT ROCKETS ─────────────────────────────────────────────────────────
    ("Trent Rockets", "A. Hales",         1, 4, "right", "none",  None,                              0),
    ("Trent Rockets", "D. Conway",        2, 4, "left",  "none",  None,                              0),
    ("Trent Rockets", "J. Fraser-McGurk", 3, 4, "right", "none",  None,                              0),
    ("Trent Rockets", "G. Billings",      4, 3, "right", "none",  None,                              0),
    ("Trent Rockets", "D. Christian",     5, 3, "right", "pace",  "right-arm medium",                3),
    ("Trent Rockets", "L. Gregory",       6, 3, "right", "pace",  "right-arm fast-medium",           3),
    ("Trent Rockets", "S. Mullaney",      7, 3, "right", "pace",  "right-arm medium",                2),
    ("Trent Rockets", "L. Fletcher",      8, 2, "right", "pace",  "right-arm fast-medium",           4),
    ("Trent Rockets", "J. Ball",          9, 1, "right", "pace",  "right-arm fast",                  4),
    ("Trent Rockets", "M. Carter",       10, 1, "right", "spin",  "off-break",                       3),
    ("Trent Rockets", "Z. Chappell",     11, 1, "right", "pace",  "right-arm fast",                  3),
    ("Trent Rockets", "P. Coughlin",     12, 2, "right", "pace",  "right-arm fast-medium",           3),
    ("Trent Rockets", "R. Paik",         13, 2, "right", "spin",  "off-break",                       3),
    ("Trent Rockets", "S. Patel",        14, 3, "right", "spin",  "off-break",                       3),
    ("Trent Rockets", "B. Duckett",      15, 3, "left",  "none",  None,                              0),

    # ── WELSH FIRE ────────────────────────────────────────────────────────────
    ("Welsh Fire", "T. Beaumont",        1, 4, "right", "none",  None,                               0),
    ("Welsh Fire", "D. Lloyd",           2, 3, "left",  "none",  None,                               0),
    ("Welsh Fire", "M. Labuschagne",     3, 5, "right", "spin",  "leg-break",                        2),
    ("Welsh Fire", "C. Cooke",           4, 3, "right", "none",  None,                               0),
    ("Welsh Fire", "K. Neesham",         5, 4, "left",  "pace",  "right-arm fast-medium",            3),
    ("Welsh Fire", "R. Das",             6, 3, "right", "none",  None,                               0),
    ("Welsh Fire", "K. Denly",           7, 3, "right", "spin",  "leg-break",                        2),
    ("Welsh Fire", "M. de Lange",        8, 1, "right", "pace",  "right-arm fast",                   4),
    ("Welsh Fire", "T. van der Gugten",  9, 1, "right", "pace",  "right-arm fast",                   4),
    ("Welsh Fire", "L. Carey",          10, 1, "right", "pace",  "right-arm fast-medium",            3),
    ("Welsh Fire", "R. Higgins",        11, 2, "right", "pace",  "right-arm fast-medium",            3),
    ("Welsh Fire", "A. Salter",         12, 2, "right", "spin",  "off-break",                        3),
    ("Welsh Fire", "N. Selman",         13, 3, "right", "none",  None,                               0),
    ("Welsh Fire", "J. Weighell",       14, 2, "right", "pace",  "right-arm fast-medium",            3),
    ("Welsh Fire", "D. Douthwaite",     15, 3, "right", "pace",  "right-arm fast-medium",            3),
]


def seed_hundred_teams(db):
    """Seed The Hundred franchise teams, venues, players, and records. Idempotent."""

    # 1. Ensure Hundred venues exist and are flagged
    for name, city, country in HUNDRED_VENUES:
        exists = db.execute("SELECT id FROM venues WHERE name=?", (name,)).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO venues (name, city, country) VALUES (?, ?, ?)",
                (name, city, country)
            )
        # Flag as Hundred venue (idempotent update)
        db.execute(
            "UPDATE venues SET is_hundred_venue=1 WHERE name=?", (name,)
        )

    # 2. Hundred team definitions
    hundred_team_defs = [
        ("Birmingham Phoenix",     "PHX", "#FF6B35", "Edgbaston"),
        ("London Spirit",          "SPR", "#003087", "Lord's Cricket Ground"),
        ("Manchester Super Giants","MSG", "#C41E3A", "Old Trafford"),
        ("MI London",              "MIL", "#004BA0", "The Oval"),
        ("Southern Brave",         "BRV", "#E4002B", "Ageas Bowl"),
        ("Sunrisers Leeds",        "SRL", "#FF6600", "Headingley"),
        ("Trent Rockets",          "TRR", "#00205B", "Trent Bridge"),
        ("Welsh Fire",             "WLF", "#E4002B", "Sophia Gardens"),
    ]

    for team_name, code, colour, venue_name in hundred_team_defs:
        exists = db.execute("SELECT id FROM teams WHERE name=?", (team_name,)).fetchone()
        if exists:
            continue
        venue_row = db.execute("SELECT id FROM venues WHERE name=?", (venue_name,)).fetchone()
        venue_id  = venue_row['id'] if venue_row else None
        db.execute(
            "INSERT INTO teams (name, short_code, badge_colour, home_venue_id, "
            "is_real, team_type, league, is_hundred_team) "
            "VALUES (?, ?, ?, ?, 1, 'domestic', 'The Hundred', 1)",
            (team_name, code, colour, venue_id)
        )

    # 3. Seed players for each Hundred team
    for (team_name, name, pos, bat_r, bat_h, bowl_t, bowl_a, bowl_r) in HUNDRED_SQUADS:
        team_row = db.execute("SELECT id FROM teams WHERE name=?", (team_name,)).fetchone()
        if not team_row:
            continue
        team_id = team_row['id']
        exists = db.execute(
            "SELECT id FROM players WHERE team_id=? AND name=?", (team_id, name)
        ).fetchone()
        if exists:
            continue
        db.execute(
            "INSERT INTO players (team_id, name, batting_position, batting_rating, "
            "batting_hand, bowling_type, bowling_action, bowling_rating) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (team_id, name, pos, bat_r, bat_h, bowl_t, bowl_a, bowl_r)
        )

    # 4. Seed Hundred real-world records
    hundred_records = [
        {
            'record_key':   'highest_score_hundred',
            'format':       'Hundred',
            'record_type':  'batting_score',
            'value_runs':   118,
            'display_value':'118',
            'holder_name':  'T. Beaumont',
            'team_name':    'Welsh Fire',
            'opponent_name':'Trent Rockets',
            'match_date':   '2023-08-14',
            'notes':        'Highest individual score in Hundred history (Women, 61 balls)',
        },
        {
            'record_key':   'highest_team_total_hundred',
            'format':       'Hundred',
            'record_type':  'team_total',
            'value_runs':   226,
            'value_wickets': 4,
            'display_value':'226/4',
            'team_name':    'MI London',
            'opponent_name':'Welsh Fire',
            'notes':        'Highest team total in Hundred history (Men)',
        },
        {
            'record_key':   'lowest_team_total_hundred',
            'format':       'Hundred',
            'record_type':  'team_total_low',
            'value_runs':   75,
            'value_wickets': 10,
            'display_value':'75 all out',
            'team_name':    'Birmingham Phoenix',
            'opponent_name':'Manchester Originals',
            'notes':        'Lowest team total in Hundred history (Men, 74 balls)',
        },
        {
            'record_key':   'best_bowling_hundred',
            'format':       'Hundred',
            'record_type':  'bowling_figures',
            'value_wickets': 5,
            'value_runs_conceded': 16,
            'display_value':'5/16',
            'holder_name':  'S. Curran',
            'team_name':    'MI London',
            'opponent_name':'London Spirit',
            'notes':        'Best bowling figures in Hundred history (Men)',
        },
    ]

    insert_sql = (
        "INSERT OR IGNORE INTO real_world_records "
        "(record_key, format, record_type, value_runs, value_wickets, "
        " value_runs_conceded, value_decimal, display_value, "
        " holder_name, team_name, opponent_name, venue_name, match_date, notes) "
        "VALUES "
        "(:record_key, :format, :record_type, :value_runs, :value_wickets, "
        " :value_runs_conceded, :value_decimal, :display_value, "
        " :holder_name, :team_name, :opponent_name, :venue_name, :match_date, :notes)"
    )
    rec_defaults = {
        'value_runs': None, 'value_wickets': None, 'value_runs_conceded': None,
        'value_decimal': None, 'holder_name': None, 'team_name': None,
        'opponent_name': None, 'venue_name': None, 'match_date': None, 'notes': None,
    }
    for r in hundred_records:
        db.execute(insert_sql, {**rec_defaults, **r})

    db.commit()
