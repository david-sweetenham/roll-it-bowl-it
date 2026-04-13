# Roll It & Bowl It

**Dice Cricket, Done Digitally.**

Roll It & Bowl It is a local-first cricket sim built around visible dice rules, long-form scorekeeping, persistent worlds, domestic and international schedules, and a statistical archive called **The Dice Cricketers' Almanack**.

It is designed to keep the old tabletop feel of dice cricket while adding the things paper play does badly: scorecards, records, broadcast presentation, world calendars, multi-season saves, and deep historical stats.

## What It Does

- Plays cricket through a visible dice-led ruleset
- Supports both `Classic` and `Modern` scoring systems
- Supports `Manual` and `Auto` roll styles
- Includes international teams, associate nations, and seeded domestic competitions
- Runs persistent worlds in `International`, `Domestic`, or `Combined` form
- Tracks long-form batting, bowling, team, venue, and honours data in the Almanack
- Presents live matches with commentary, lower-thirds, mini wagon wheel, story panels, umpire signals, and crowd reactions

## Core Rules

Every ball begins with a visible die roll.

### Classic

- `1` = 1 run
- `2` = 2 runs
- `3` = 3 runs
- `4` = 4 runs
- `5` = HOWZAT appeal chain
- `6` = 6 runs

### Modern

- keeps the same readable face meanings
- keeps the same appeal chain on `5`
- lightly moderates some boundary outcomes in longer formats

### Appeal Chain

When `5` is rolled, the game moves into the multi-stage dismissal system:

1. appeal outcome
2. not-out resolution, if needed
3. dismissal type, if out
4. catch location, if applicable

That keeps wickets dramatic while letting normal scoring stay readable.

## Main Features

### Match Play

- `International` and `Domestic` setup flows
- `Test`, `ODI`, `T20`
- domestic format relabels: `First-Class`, `One-Day`, `T20`
- human play, spectator play, AI vs AI
- toss flow, declarations, follow-on-aware long-form structure

### Broadcast Presentation

- large-format live scoreboard
- commentary-first match view
- story strip and story alerts
- live mini wagon wheel
- crowd reactions for major events
- umpire pop-up signals for wickets and boundaries
- innings-break and result packages designed for recording/streaming

### Worlds

- `International`, `Domestic`, and `Combined` worlds
- realistic or random scheduling
- domestic coverage rules:
  - `Selected Clubs`
  - `Full League`
- fixture horizon blocks from `1` to `10` years
- extendable calendars for effectively endless saves
- managed-team support:
  - AI only
  - one international team
  - one domestic team
  - one international and one domestic team in combined worlds
- player lifecycle choice:
  - `Ageless Players`
  - `Retire & Regens`

### Almanack

- batting, bowling, all-round, teams, matches, partnerships, honours
- canon-aware stats handling
- format filters
- world and Almanack story desks:
  - records under threat
  - players in form
  - milestone watch

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python start.py
```

Open:

```text
http://127.0.0.1:5000
```

### LAN Hosting

To open the game on other machines on your local network:

```bash
python start.py --lan
```

That binds the app to `0.0.0.0` and prints a LAN URL such as `http://192.168.x.x:5000`.

### Direct Run

```bash
source .venv/bin/activate
python app.py
```

Optional host and port overrides:

```bash
RIBI_HOST=0.0.0.0 RIBI_PORT=5000 python app.py
```

## Project Layout

```text
roll-it-bowl-it/
├── app.py
├── game_engine.py
├── cricket_calendar.py
├── database.py
├── schema.sql
├── seed_data.py
├── start.py
├── config.py
├── templates/
│   └── index.html
├── static/
│   ├── app.js
│   ├── style.css
│   └── canvas.js
├── seed_domestic/
├── screenshots/
├── uat/
├── test_engine.py
├── test_sim_controls.py
├── test_world_sim.py
├── test_canon_system.py
└── ribi.spec
```

## Testing

```bash
source .venv/bin/activate
pytest -q
```

Calendar UAT:

```bash
python uat/run_uat.py
```

## Build

```bash
pip install pyinstaller
pyinstaller ribi.spec
```

## Suggested GitHub Screenshots

The existing screenshots should be refreshed. The best set for GitHub would be:

1. Home screen with recent results, quick stats, and quick actions
2. Play screen showing the international/domestic split and scoring-mode choice
3. Live match screen in Broadcast Mode with die, mini wagon wheel, commentary, and story strip visible
4. A HOWZAT or wicket moment in Manual mode
5. Innings-break screen with the new continue/countdown treatment
6. Full match result screen with score summary and notes cards
7. Almanack batting tab with visible filters and story desk
8. World detail overview showing world rules, active series, and world desk cards
9. World wizard showing lifecycle choice (`Ageless Players` vs `Retire & Regens`)
10. Archive match view showing a full scorecard rather than live-match controls

If you want, I can also capture a recommended set directly from the running local app.

## Notes

This is an independent fan-made project. It is not affiliated with the ICC, any domestic board, any broadcaster, or any commercial cricket organisation.

`The Dice Cricketers' Almanack` is an original in-project feature and is not affiliated with Wisden.

## More

- [HOWTO_PLAY.md](HOWTO_PLAY.md)
- [DEVELOPMENT.md](DEVELOPMENT.md)
- [CHANGELOG.md](CHANGELOG.md)
