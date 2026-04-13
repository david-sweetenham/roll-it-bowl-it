# Roll It & Bowl It

**Dice Cricket Done Digitally** is a local-first cricket sim built around visible dice rules, long-form stats, broadcast-style presentation, and persistent worlds that keep their own history.

It is designed to preserve the old-school tabletop feel of dice cricket while adding the things paper play struggles to track well: scorecards, records, domestic leagues, world calendars, and a proper statistical archive.

## Highlights

- Visible dice-led match play with a multi-stage HOWZAT appeal chain
- Two scoring systems:
  - `Classic`: literal dice scoring, where `1/2/3/4/6` score exactly that and `5` triggers the appeal mechanic
  - `Modern`: the same readable face meanings, with light realism tuning in longer formats
- Two roll styles:
  - `Auto` for faster play
  - `Manual` for step-by-step appeal drama
- International and domestic cricket, with separate setup flows
- Persistent worlds in `International`, `Domestic`, or `Combined` formats
- Domestic world coverage rules: `Selected Clubs` or `Full League`
- Broadcast-friendly live match screen with story strips, lower-thirds, flags, and a live mini wagon wheel
- The Dice Cricketers' Almanack for career stats, records, honours, and canon-aware filtering
- World and Almanack story desks that surface in-form players, record threats, and milestone watches

## Core Dice Rules

Every ball starts with a visible Stage 1 roll.

| Face | Classic | Modern |
|------|---------|--------|
| `1` | 1 run | 1 run |
| `2` | 2 runs | 2 runs |
| `3` | 3 runs | 3 runs |
| `4` | 4 runs | Usually 4, sometimes moderated in longer formats |
| `5` | HOWZAT appeal chain | HOWZAT appeal chain |
| `6` | 6 runs | Usually 6, sometimes moderated in longer formats |

When a `5` is rolled, the game moves into the appeal chain:

| Stage | Purpose |
|------|---------|
| Stage 2 | Out / not out decision |
| Stage 3 | Not-out resolution such as dot, wide, no-ball, bye, leg-bye |
| Stage 4 | Dismissal type |
| Stage 4b | Catch location, if required |

That keeps scoring faces readable while making wickets the dramatic, multi-roll event.

## Quick Start

### Recommended

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python start.py
```

Open `http://127.0.0.1:5000`.

### LAN Hosting

If you want to open the game from other devices on your local network, start it with:

```bash
python start.py --lan
```

The launcher will bind Flask to `0.0.0.0`, keep opening your own browser locally, and print a `LAN access` URL such as `http://192.168.1.20:5000` for phones, laptops, or other machines on the same network.

This is the right first step for local multiplayer or showing the game on another device in your house. Proper internet hosting is a later-stage job and would need a production server setup, firewall/router rules or tunnelling, and some security hardening before exposing the app publicly.

### Direct Flask run

If you prefer to start the app directly:

```bash
source .venv/bin/activate
python app.py
```

You can also override the bind host and port directly with environment variables:

```bash
RIBI_HOST=0.0.0.0 RIBI_PORT=5000 python app.py
```

The database is created and seeded automatically on first run. The seed includes international teams, associate nations, and major domestic competitions.

### Desktop launcher (Linux)

To add a taskbar / app-menu shortcut with the bat-and-ball icon, run once from the project root:

```bash
bash install-launcher.sh
```

This writes a `.desktop` entry to `~/.local/share/applications/` pointing at your clone. On **KDE** right-click the entry in the application menu → *Pin to Taskbar*; on **GNOME** drag it from Activities to the dock. Clicking it starts the server and opens your browser automatically.

## Match Setup

The Play screen supports:

- `Cricket Type`: `International` or `Domestic`
- `Format`:
  - international: `Test`, `ODI`, `T20`
  - domestic: `First-Class`, `One-Day`, `T20`
- `Scoring System`: `Classic` or `Modern`
- domestic league filtering when domestic cricket is selected

You can also choose a default scoring preference on first launch and change it later in Settings, while still overriding it match by match.

## Live Match Presentation

The live screen is built for long-form play and recording:

- broadcast mode for cleaner large-format presentation
- commentary-first layout with stronger event hierarchy
- story strip and story alerts for pressure, milestones, and momentum
- small national flags where appropriate
- live mini wagon wheel beside the die
- visible dice guide so viewers can learn the rules as they watch

## Worlds

World creation supports three structures:

- `International`: national teams only
- `Domestic`: domestic and franchise cricket only
- `Combined`: international cricket plus selected domestic leagues

Calendar generation supports:

- `Realistic` or `Random` scheduling
- domestic coverage rules for realistic domestic worlds:
  - `Selected Clubs`
  - `Full League`

The World screen includes:

- overview, rankings, and records tabs
- active series and event summaries
- world story desk panels
- simulation controls including `My Next Match`
- world deletion directly from the worlds list

## Almanack

The Dice Cricketers' Almanack is the long-form stats archive for the save.

It includes:

- batting, bowling, all-round, team, match, partnership, and honours views
- visible format filters
- canon-aware stats handling
- story panels for records under threat, players in form, and milestone chances

## Project Layout

```text
roll-it-bowl-it/
├── app.py
├── cricket_calendar.py
├── database.py
├── game_engine.py
├── schema.sql
├── seed_data.py
├── config.py
├── start.py
├── templates/
│   └── index.html
├── static/
│   ├── app.js
│   ├── style.css
│   └── canvas.js
├── uat/
│   ├── run_uat.py
│   └── test_calendar.py
├── test_engine.py
├── test_sim_controls.py
├── test_world_sim.py
├── test_canon_system.py
├── screenshots/
└── ribi.spec
```

## Testing

Run the automated test suite with:

```bash
source .venv/bin/activate
pytest -q
```

The repository also includes calendar-focused UAT coverage:

```bash
python uat/run_uat.py
```

## Packaging

To build a standalone executable:

```bash
pip install pyinstaller
pyinstaller ribi.spec
```

## Screenshots

- Match in progress: `screenshots/match-howzat.png`
- Match result: `screenshots/match-result.png`
- Match start: `screenshots/match-start-dark.png`
- Almanack teams: `screenshots/almanack-teams.png`
- Almanack batting: `screenshots/almanack-batting.png`
- Almanack honours: `screenshots/almanack-honours.png`
- Series and tournaments: `screenshots/series-tournaments.png`

## Notes

This is a local-first fan project made for personal entertainment. It is not affiliated with the ICC, any domestic board, any broadcaster, or any commercial cricket organisation.

`The Dice Cricketers' Almanack` is an original project feature and is not affiliated with Wisden.

## More

- [HOWTO_PLAY.md](HOWTO_PLAY.md)
- [DEVELOPMENT.md](DEVELOPMENT.md)
- [CHANGELOG.md](CHANGELOG.md)
