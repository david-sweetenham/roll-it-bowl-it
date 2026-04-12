# Roll It & Bowl It

**Dice Cricket Done Digitally** — a local-first cricket simulation built around visible dice rules, long-form stats, and a world that keeps its own history.

The project is designed to keep the old-school feel of tabletop dice cricket while adding the things pen-and-paper versions struggle with: full scorecards, persistent records, world calendars, domestic leagues, broadcast-friendly presentation, and a proper statistical archive.

---

## What it does

- **Live match play** with a multi-stage HOWZAT dice engine for appeals, dismissals, and catch locations
- **Two scoring systems**:
  `Classic` keeps the die literal: `1, 2, 3, 4, 6` score exactly that, `5` triggers the appeal chain
  `Modern` keeps the same face meanings but lightly tones down some boundary results in longer formats
- **Two roll modes**:
  `Auto` resolves every stage for speed
  `Manual` lets you press through each appeal stage yourself
- **International and domestic cricket**:
  national sides, counties, states, and franchise leagues can now be separated at setup time
- **Persistent worlds** with `International`, `Domestic`, or `Combined` structures
- **Realistic or random calendars** depending on how simulation-heavy you want the save to be
- **The Dice Cricketers' Almanack** with career stats, honours, records, and canon filtering
- **Broadcast mode** and story graphics built for recorded play and long-form series

---

## Core Dice Rules

Every delivery starts with a visible Stage 1 roll:

| Face | Classic | Modern |
|------|---------|--------|
| **1** | 1 run | 1 run |
| **2** | 2 runs | 2 runs |
| **3** | 3 runs | 3 runs |
| **4** | 4 runs | usually 4, sometimes cut back in longer formats |
| **5** | HOWZAT appeal chain | HOWZAT appeal chain |
| **6** | 6 runs | usually 6, sometimes cut back in longer formats |

After a `5`, the ball can move through the appeal and dismissal stages:

| Stage | Die roll decides |
|-------|-----------------|
| **Stage 2** | Appeal outcome — out or not out |
| **Stage 3** | Not-out resolution — dot, bye, leg-bye, wide, no-ball |
| **Stage 4** | Dismissal type — bowled, lbw, caught, run out, stumped |
| **Stage 4b** | Catch location — if caught, where it went |

That gives the game its identity: literal run faces for scoring, multi-roll drama for wickets.

---

## Quick Start

```bash
# Clone and set up
git clone <repo>
cd roll-it-bowl-it
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run (development)
python start.py

# Open http://127.0.0.1:5001 in your browser
```

The database is created and seeded automatically on first run. The seed now includes international sides and major domestic competitions.

---

## Match Setup

The Play screen now lets you choose:

- **Cricket Type**: `International` or `Domestic`
- **Format**: `Test/ODI/T20` in international mode, or `First-Class/One-Day/T20` in domestic mode
- **Scoring System**: `Classic` or `Modern`
- **Domestic League**: optional filter when domestic mode is active

That means you can quickly set up:

- England vs New Zealand in a Test
- Surrey vs Yorkshire in a First-Class match
- Mumbai Indians vs Chennai Super Kings in T20

without mixing all teams into one picker.

## Rolling Modes

### Auto-Roll (default)
Every dice stage resolves the moment you click **Roll** (or press Space/R). The die face animates, the result appears, and the ball is immediately recorded. Great for fast play and simming through innings you care less about.

### Manual Roll
Each dice stage waits for you. After Stage 1 triggers an appeal:

1. "HOWZAT!" flashes up — the fielding team appealing
2. You press **Appeal!** to roll Stage 2
3. The die lands — either **NOT OUT** (press Continue) or **OUT** (press Dismissal)
4. If out via caught, you press **Caught Where?** to roll Stage 4b

Switch modes with the toggle in the match header, or press **M** while no ball is in flight. Switching Manual → Auto mid-over queues the change until the current ball completes.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| Space / R | Roll (when idle) |
| A | Appeal (Manual mode, HOWZAT state) |
| C | Continue / Not Out (Manual mode) |
| D | Dismissal (Manual mode, out pending) / Toggle dark mode (otherwise) |
| M | Toggle roll mode (when idle, not AI vs AI) |
| F | Fast-sim current match |

---

## Tension suggestion banner

When the match situation is tense, a banner appears suggesting you switch to Manual mode:

- T20 with ≤ 2 overs left and < 15 runs needed
- Last wicket standing
- Batter on 95+ runs (century approach)
- Required run rate > 12
- Scores tied with ≤ 1 over left

The banner is per-innings — dismiss it and it won't reappear for that innings.

---

## Project layout

```
roll-it-bowl-it/
├── app.py              # Flask app — all API routes
├── game_engine.py      # HOWZAT! dice engine — do not modify
├── database.py         # DB access layer — do not modify
├── cricket_calendar.py # FTP-style calendar engine
├── schema.sql          # SQLite schema (25+ tables)
├── seed_data.py        # Initial teams, players, venues, world records
├── config.py           # Production config
├── config_dev.py       # Development overrides (not packaged)
├── start.py            # Entry point for both dev and packaged exe
├── templates/
│   └── index.html      # Single-page app shell
├── static/
│   ├── app.js          # All client-side logic
│   └── style.css       # Styles + animations
├── tests/
│   ├── test_engine.py          # 5 engine unit tests
│   ├── test_sim_controls.py    # 5 simulation-control tests
│   ├── test_world_sim.py       # 4 world-simulation tests
│   └── test_canon_system.py    # 94 API + system tests
├── uat/
│   ├── test_calendar.py        # 10 calendar engine UAT tests
│   └── run_uat.py              # UAT orchestrator
├── screenshots/        # Application screenshots
└── ribi.spec           # PyInstaller packaging spec
```

---

## Running the tests

```bash
source .venv/bin/activate
pytest -q
```

The current suite passes end to end and covers engine behavior, simulation controls, world simulation, and canon/stat filtering.

### UAT suite (calendar engine)

```bash
python uat/run_uat.py
# or run a suite directly:
python uat/test_calendar.py
```

10 acceptance tests covering: home-season month enforcement, ICC event placement, double-booking prevention, avoid_months respected, India-Pakistan isolation, format ordering, fixture count by density.

---

## Screenshots

### Match in progress — HOWZAT! appeal (dark mode)
![Match HOWZAT](screenshots/match-howzat.png)

### Match result screen
![Match Result](screenshots/match-result.png)

### Match start — batting and bowling panels
![Match Start](screenshots/match-start-dark.png)

### The Dice Cricketers' Almanack — Teams tab
![Almanack Teams](screenshots/almanack-teams.png)

### The Dice Cricketers' Almanack — Batting records
![Almanack Batting](screenshots/almanack-batting.png)

### The Dice Cricketers' Almanack — Honours with real-world benchmarks
![Almanack Honours](screenshots/almanack-honours.png)

### Series & Tournaments
![Series and Tournaments](screenshots/series-tournaments.png)

---

## Building a standalone executable

```bash
pip install pyinstaller
pyinstaller ribi.spec
```

The output is `dist/RollItBowlIt` (Linux/Mac) or `dist/RollItBowlIt.exe` (Windows). The development config (`config_dev.py`) is excluded from the build by the spec file.

---

## World Modes

World creation now supports three structures:

- **International**: national teams only, international calendar focus
- **Domestic**: league and franchise cricket only
- **Combined**: international cricket plus selected domestic competitions in the same save

In realistic worlds, domestic competitions can be layered into the calendar using the domestic league selector in the wizard.

---

## Disclaimer

Roll It & Bowl It is an independent fan-made project created for personal
entertainment. It is not affiliated with, endorsed by, or connected to any
cricket board, governing body, broadcaster, or commercial cricket organisation,
including but not limited to the ICC, ECB, Cricket Australia, BCCI, or any
other national or international cricket authority.

Player names used in pre-loaded squads are included for entertainment purposes
only in the spirit of the dice cricket tradition. No association with or
endorsement by any named individual is implied or should be inferred.

"The Dice Cricketers' Almanack" is an original name created for this project
and is not affiliated with Wisden or John Wisden & Co. in any commercial sense.

This is a free, open source personal project. It is not a commercial product.

---

## Version

`0.2.0-dev` — Python 3.14.3, Flask 3.1.3

See [CHANGELOG.md](CHANGELOG.md) for what's in this release.
For how to play, see [HOWTO_PLAY.md](HOWTO_PLAY.md).
For development notes, see [DEVELOPMENT.md](DEVELOPMENT.md).
