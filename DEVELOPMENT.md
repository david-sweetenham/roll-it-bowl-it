# Development Guide

Technical reference for working on Roll It & Bowl It.

## Stack

- Python
- Flask
- SQLite
- Vanilla HTML/CSS/JS
- Canvas visualisations
- No frontend build step

## Runtime

Recommended local run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python start.py
```

Default URL:

```text
http://127.0.0.1:5000
```

LAN mode:

```bash
python start.py --lan
```

## Important Files

- [app.py](/home/davids/roll-it-bowl-it/app.py): Flask app, routes, world orchestration, match flow
- [game_engine.py](/home/davids/roll-it-bowl-it/game_engine.py): core dice engine and quick simulation logic
- [database.py](/home/davids/roll-it-bowl-it/database.py): DB access layer and migrations
- [cricket_calendar.py](/home/davids/roll-it-bowl-it/cricket_calendar.py): realistic calendar and scheduling logic
- [schema.sql](/home/davids/roll-it-bowl-it/schema.sql): schema definitions
- [seed_data.py](/home/davids/roll-it-bowl-it/seed_data.py): international teams, venues, squads
- [seed_domestic](/home/davids/roll-it-bowl-it/seed_domestic): domestic and franchise seed packs
- [templates/index.html](/home/davids/roll-it-bowl-it/templates/index.html): SPA shell
- [static/app.js](/home/davids/roll-it-bowl-it/static/app.js): main client logic
- [static/style.css](/home/davids/roll-it-bowl-it/static/style.css): styling and broadcast presentation
- [static/canvas.js](/home/davids/roll-it-bowl-it/static/canvas.js): canvas-specific rendering helpers

## Architecture Notes

### Match Layer

- live matches are served by Flask APIs and rendered in the single-page frontend
- the game supports human play, AI play, and AI-vs-AI presentation
- match archives and live matches now use different layouts

### Dice Engine

The engine supports two scoring systems:

- `classic`
- `modern`

Both share the same appeal chain.

### Worlds

World saves now include:

- world type: international / domestic / combined
- calendar style: realistic / random
- domestic coverage mode
- fixture horizon
- managed teams
- player lifecycle:
  - ageless
  - retire and regens

World sim uses per-world player state rather than mutating the base squads directly.

### Regens

In lifecycle-enabled worlds:

- players age per world save
- retirements are randomized per world
- injury retirements are possible
- replacement players are generated as world-only players
- regen naming is country-aware or league-aware where possible

## Database Notes

The DB is SQLite and migrations run at startup.

Key concepts:

- `matches`, `innings`, `deliveries`, `batter_innings`, `bowler_innings`
- `worlds`, `fixtures`, `world_series`, `world_records`, `ranking_history`
- `player_world_state` for world-specific player lifecycle and career tracking

Do not assume a fresh DB. New features should tolerate migrated databases.

## Frontend Notes

- no framework
- no bundler
- large single-file JS architecture
- direct DOM updates
- broadcast graphics and match UI live in the same frontend runtime

When changing the UI, test:

- normal desktop play
- Broadcast Mode
- archive match view
- world wizard
- dark/light mode

## Testing

Run the main suite:

```bash
source .venv/bin/activate
pytest -q
```

Run the calendar UAT:

```bash
python uat/run_uat.py
```

Useful quick checks:

```bash
node --check static/app.js
.venv/bin/python -m py_compile app.py database.py game_engine.py
```

## Packaging

PyInstaller build:

```bash
pip install pyinstaller
pyinstaller ribi.spec
```

## Documentation Guidance

When updating GitHub-facing docs, keep these in sync:

- [README.md](README.md)
- [HOWTO_PLAY.md](HOWTO_PLAY.md)
- [DEVELOPMENT.md](DEVELOPMENT.md)
- [CHANGELOG.md](CHANGELOG.md)

The common drift points are:

- wrong port or startup instructions
- stale world features
- missing domestic support
- outdated screenshot descriptions
- old claims about player/world systems

## Practical Review Notes

The strongest current product pillars are:

- visible dice identity
- strong match presentation
- long-form world play
- Almanack/stat depth

The biggest ongoing maintenance risks are:

- very large `app.py`
- very large `static/app.js`
- broad world-mode surface area
- keeping docs and screenshots current as features evolve
