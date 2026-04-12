# Development Guide — Roll It & Bowl It

> Independent fan project — not affiliated with any cricket board or governing body.

Technical reference for working on this codebase.

---

## Environment

- **Python**: 3.14.3 (GCC 15.2.1)
- **Flask**: 3.1.3
- **Database**: SQLite (via Python's built-in `sqlite3`)
- **Frontend**: Vanilla JavaScript, no build step
- **Version**: `0.2.0-dev` (set in `config.py` as `APP_VERSION`)

```bash
git clone <repo>
cd roll-it-bowl-it
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python start.py
# → http://127.0.0.1:5001
```

---

## Project structure

```
roll-it-bowl-it/
├── app.py                  # Flask application — API routes
├── game_engine.py          # HOWZAT! dice engine (do not modify)
├── database.py             # DB access layer (do not modify)
├── cricket_calendar.py     # FTP-style calendar engine
├── schema.sql              # SQLite schema — 25+ tables
├── seed_data.py            # Teams, players, venues, world records
├── config.py               # Production config
├── config_dev.py           # Dev overrides (excluded from packaging)
├── start.py                # Entry point (dev + packaged binary)
├── templates/
│   └── index.html          # Single-page app shell
├── static/
│   ├── app.js              # All client-side logic
│   └── style.css           # Styles + CSS animations
├── tests/
│   ├── test_engine.py          # 5 unit tests — dice engine
│   ├── test_sim_controls.py    # 5 tests — simulation controls
│   ├── test_world_sim.py       # 4 tests — world simulation
│   └── test_canon_system.py    # 94 tests — API + system (canon suite)
├── uat/
│   ├── test_calendar.py        # 10 UAT tests — calendar engine
│   └── run_uat.py              # UAT orchestrator
├── screenshots/            # Application screenshots
├── ribi.spec               # PyInstaller spec
├── REVIEW_REPORT.md        # Previous code-review findings + status
└── requirements.txt
```

---

## Configuration

`config.py` — loaded in production and during tests:

```python
APP_VERSION = '0.1.0-dev'
DATABASE = 'ribi.db'
SECRET_KEY = '...'
DEBUG = False
PORT = 5001
```

`config_dev.py` — overrides for local development (never packaged):

```python
DEBUG = True
# any local overrides
```

`start.py` loads `config_dev` when it exists, falls back to `config`. The PyInstaller spec (`ribi.spec`) explicitly excludes `config_dev` from builds.

---

## The dice engine

`game_engine.py` is the core simulation layer. It now supports two scoring modes:

- `classic`
- `modern`

Both modes share the same HOWZAT appeal chain, but Stage 1 scoring resolution differs slightly.

### What the engine exposes

The engine's main entry point takes a delivery request and returns a `delivery` dict:

```python
{
  "stage1_roll": int,         # 1–6
  "stage2_roll": int | None,  # present if appeal triggered
  "stage3_roll": int | None,  # present if not-out resolution needed
  "stage4_roll": int | None,  # present if dismissed
  "stage4b_roll": int | None, # present if caught
  "outcome": str,             # "dot", "runs", "wide", "noball", "wicket", ...
  "runs": int,
  "wicket": bool,
  "dismissal_type": str | None,
  "catch_location": str | None,
  # ... additional metadata
}
```

The presence of `stage2_roll` (not `None`) is the correct test for whether a delivery went through the appeal system. Do not use `stage1_roll == 1` as a proxy — both stage1=1 and stage1=2 can trigger appeals depending on delivery type.

### Scoring modes

`Classic`
- `1=1`
- `2=2`
- `3=3`
- `4=4`
- `5=appeal`
- `6=6`

`Modern`
- same visible mapping
- keeps the same appeal chain on `5`
- in longer formats, some `4` and `6` outcomes can be moderated

### Batter out thresholds

| Rating | Out if Stage 2 roll ≥ |
|--------|----------------------|
| 5      | 6                    |
| 4      | 5                    |
| 3      | 4                    |
| 2      | 3                    |
| 1      | 2                    |

Each step is one pip on the die, producing the ~5% gradient confirmed in automated testing (27.2% → 21.2% → 16.2% → 11.2% → 6.2%).

---

## Database

All DB access goes through `database.py`.

Schema is in `schema.sql` (25+ tables). Key tables:

- `matches` — fixtures, format, venue, status
- `innings`, `balls` — ball-by-ball records
- `players`, `teams` — roster and squad data
- `teams.team_type`, `teams.league` — separates international and domestic/franchise teams
- `season_standings` — points, NRR, wins/losses
- `career_batting`, `career_bowling` — aggregate stats
- `records` — historical highs (highest score, best figures, etc.)

The DB file is `ribi.db` in the project root. Delete it and restart to reset everything (the seed runs automatically on first start).

---

## API routes

`app.py` registers all routes. Key groupings:

### Match lifecycle
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/matches` | GET | List all matches |
| `/api/matches/<id>` | GET | Match detail |
| `/api/matches/<id>/ball` | POST | Roll a ball |
| `/api/matches/<id>/fast-sim` | POST | Simulate remaining balls |
| `/api/matches/<id>/tension` | GET | Tension data for suggestion banner |
| `/api/matches/<id>/innings-complete` | POST | Close out an innings |

### World simulation
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/world/sim-day` | POST | Simulate one day of fixtures |
| `/api/world/sim-season` | POST | Simulate entire season |

### World creation
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/worlds` | POST | Create a world with `world_scope`, `calendar_style`, selected teams, and optional domestic leagues |
| `/api/domestic-leagues` | GET | Return available domestic competitions for wizard/UI filtering |

### Statistics
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/stats/batting` | GET | Career batting averages |
| `/api/stats/bowling` | GET | Career bowling averages |
| `/api/records` | GET | All-time records |

### Almanack
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/almanack/batting` | GET | Batting records — returns `{rows, total, exhibition_fallback}` |
| `/api/almanack/bowling` | GET | Bowling records — same shape |
| `/api/almanack/honours` | GET | In-game honours board |
| `/api/almanack/honours/with-world-records` | GET | Honours enriched with real-world benchmarks and `pct_of_world_record` |

### Calendar
| Route | Method | Purpose |
|-------|--------|---------|
| `/api/worlds/<id>/calendar/upcoming` | GET | Upcoming fixtures (supports `?days=N`) |

### Tension endpoint

`GET /api/matches/<id>/tension` returns:

```json
{
  "format": "T20",
  "innings_number": 2,
  "overs_remaining": 1.4,
  "runs_required": 12,
  "wickets_remaining": 3,
  "run_rate_required": 7.5,
  "current_batter_runs": 97,
  "is_last_wicket": false,
  "is_tied": false,
  "suggest_manual": true,
  "suggestion_reason": "Century in sight — 97 not out",
  "suggestion_key": "century"
}
```

`suggest_manual` is `true` when any of the five conditions are met. `suggestion_key` identifies which condition triggered (used to suppress re-showing after dismissal).

---

## Frontend architecture

`static/app.js` is a single ~2000-line vanilla JS file. No framework, no build step. The key structures:

Important setup state now includes:

- `AppState.defaultScoringMode`
- `AppState._playCricketScope`
- `AppState._playDomesticLeague`
- `WorldUI.wizardScope`

### MatchUI object

Central state store for the live match view:

```javascript
const MatchUI = {
  matchId: null,
  lastState: null,         // latest API response from /ball
  diceState: 'idle',       // current DiceState machine state
  rollMode: 'auto',        // 'auto' | 'manual'
  _pendingDelivery: null,  // stored delivery for manual mode
  _pendingRes: null,       // stored API response for manual mode
  _ballInProgress: false,  // true while a ball is in any stage
  _pendingRollModeSwitch: null,  // queued mode change
  _dismissedSuggestions: [],     // suggestion keys dismissed this innings
  // ... scoring, session stats, etc.
};
```

### DiceState machine

13 states control all button visibility and animation triggers:

```javascript
const DiceState = {
  IDLE:           'idle',         // waiting for Roll
  ROLLING_S1:     'rolling_s1',   // Stage 1 animating
  HOWZAT:         'howzat',       // waiting for Appeal press (manual)
  ROLLING_S2:     'rolling_s2',   // Stage 2 animating
  NOT_OUT:        'not_out',      // waiting for Continue press (manual)
  OUT_PENDING:    'out_pending',  // waiting for Dismissal press (manual)
  ROLLING_S3:     'rolling_s3',   // Stage 3 animating
  ROLLING_S4:     'rolling_s4',   // Stage 4 animating
  ROLLING_S4B:    'rolling_s4b',  // Stage 4b animating
  RESULT:         'result',       // ball complete, display updating
  FREE_HIT:       'free_hit',     // free hit banner visible
  INNINGS_END:    'innings_end',  // innings-complete flow
  MATCH_END:      'match_end',    // match-complete flow
};
```

Transitions are logged to the console as `[DiceState] old → new`.

`_setDiceState(newState)` is the only way to change state. It calls `_updateDiceStateUI(state)` which manages button visibility for the current mode.

### Manual mode flow

```
rollBall()
  └─ ROLLING_S1
       └─ stage2_roll != null?
            ├─ no  → RESULT → _completeBall()
            └─ yes → _manualRollBegin()
                        └─ HOWZAT (wait)
                             └─ manualAppeal()
                                  └─ ROLLING_S2
                                       ├─ not out → NOT_OUT (wait)
                                       │             └─ manualContinue()
                                       │                  └─ ROLLING_S3? → RESULT → _completeBall()
                                       └─ out → OUT_PENDING (wait)
                                                 └─ manualDismissal()
                                                      └─ ROLLING_S4
                                                           ├─ not caught → RESULT → _completeBall()
                                                           └─ caught → show Caught Where? (wait)
                                                                         └─ manualCaughtWhere()
                                                                              └─ ROLLING_S4B → RESULT → _completeBall()
```

### _completeBall()

Shared post-ball processing called by both Auto and Manual paths. Handles:
- Sound effects
- Session stat updates
- Commentary rendering
- State refresh (scorecards, over display)
- Milestone detection (50s, 100s, five-fors)
- Record checks
- Fielding tint
- Free-hit banner clear
- Innings/match completion
- Queued roll mode switch execution
- Tension poll (`_pollTension()`)
- AI restart (if AI turn just ended)
- Bowling panel check

### Roll mode management

`setRollMode(mode)` — user-facing. If a ball is in progress and switching Manual → Auto, queues the switch in `_pendingRollModeSwitch`.

`_applyRollMode(mode)` — internal. Updates `MatchUI.rollMode`, persists to `localStorage` under key `ribi_roll_mode`, updates button active states.

Auto → Manual switching is immediate. Manual → Auto is queued to the end of the current ball.

### LocalStorage

| Key | Value | Purpose |
|-----|-------|---------|
| `ribi_roll_mode` | `'auto'` \| `'manual'` | Persisted roll mode |

---

## CSS architecture

`static/style.css` uses CSS custom properties for the design system. Key variables:

```css
--danger:   /* red — used for HOWZAT!, out state, howzat-title */
--accent:   /* primary accent — not-out result */
--accent2:  /* secondary accent — howzat appeal team label */
--fs-3xl:   /* font size for howzat-title */
--fs-2xl:   /* font size for out result display */
```

### Animation keyframes added for Manual mode

| Keyframe | Applied to | Effect |
|----------|-----------|--------|
| `howzatEntrance` | `.manual-howzat-display` | Scale 0.6→1 on appear |
| `howzatFlash` | `.howzat-title` | Text-shadow alternation (red pulse) |
| `howzatDiePulse` | `.die-face.howzat-active` | Border glow during HOWZAT state |
| `appealPulse` | `.btn-howzat` | Opacity pulse on Appeal button |
| `appealPulseBroadcast` | `.btn-howzat` (broadcast mode) | Slower appeal pulse |
| `notOutEntrance` | `.manual-result-notout` | Slide-in from above |
| `outEntrance` | `.manual-result-out` | Scale 0.5→1 |
| `freeHitPulse` | `.free-hit-banner` | Box-shadow glow |
| `tensionPulse` | `.tension-suggestion` | Opacity 0.85→1 (2.5s) |

---

## Tests

```bash
pytest -q                     # current automated suite
pytest tests/test_engine.py   # 5 engine tests
pytest tests/test_canon_system.py -v   # 94 system tests
```

### Test suites

**`test_engine.py`** (5 tests) — pure engine unit tests. Validates outcome distributions, stage transitions, free hit behaviour, batter threshold mechanics. Run as standalone (no Flask).

**`test_sim_controls.py`** (5 tests) — simulation control tests: starting, pausing, resuming, aborting fast-sim.

**`test_world_sim.py`** (4 tests) — world simulation: sim-day, sim-season, standings update, NRR calculation.

**`test_canon_system.py`** (94 tests) — the full system test suite. Spins up a real Flask test client against a real (temp) SQLite database. Exercises all major API routes including the full match lifecycle, innings completion, record-breaking events, and edge cases.

### UAT suite (calendar engine)

```bash
python uat/run_uat.py           # run all UAT suites
python uat/test_calendar.py     # run calendar suite directly
```

The UAT suite runs against a live application instance (requires the server to be running on port 5001, or spun up by the test). 10 tests covering:

| Test | Checks |
|------|--------|
| England home season | No England home fixtures in January or February |
| India home season | No India home fixtures in July or August |
| Ashes present | England-Australia series exists when density allows |
| No double-booking | No two fixtures on the same date involve the same team |
| Avoid months | No fixtures in configured `avoid_months` |
| India-Pakistan | India vs Pakistan matches only appear at ICC events |
| Format order | Within a series, T20s before ODIs before Tests |
| Fixture count by density | Relaxed < Moderate < Busy |
| Required fields | Every fixture has `date`, `home_team`, `away_team`, `format`, `venue` |
| ICC event presence | At least one ICC event per calendar year in multi-year worlds |

### What the tests do not cover

- `game_engine.py` internal implementation (black-box only)
- `database.py` internal implementation
- Frontend JavaScript (no browser automation)
- PyInstaller packaging

---

## Cricket Calendar Engine

`cricket_calendar.py` — the FTP-style calendar generator. Called from `app.py` when `calendar_style == 'realistic'` during world creation.

### Key concepts

**Home season windows** — each team has months when they host cricket at home. England: May–September. India: October–March. These mirror real international cricket scheduling.

**`_schedule_bilateral(home, away, formats, density)`** — places a home series for `home` vs `away`. In `relaxed` mode only one direction is scheduled per cycle (the reciprocal is skipped). In `moderate`/`busy` mode, both directions are scheduled across the year range.

**`_place_icc_events(year, event_type)`** — places a multi-team ICC event (group stage + knockout rounds). Uses `team_last_date` dict to prevent the same team appearing in two fixtures on the same date (ICC double-booking fix).

**`generate_realistic_calendar(world_id, teams, start_year, end_year, density)`** — top-level entry point. Returns a list of fixture dicts ready for insertion.

### Calendar Style wizard option

The World Wizard Step 2 includes a Calendar Style radio group:
- **Realistic**: calls `generate_realistic_calendar()` — proper home seasons, tours, ICC events
- **Random**: original rotation (faster, no FTP logic)

After Realistic world creation, a preview panel shows fixture counts and the first 30 upcoming fixtures before navigating to the world.

---

## Almanack: canon/exhibition system

### How records are filtered

The `batting_averages` and `bowling_averages` views group by `(player_id, format, canon_status)`. When querying, `database.py` tries `canon_status = 'canon'` first; if no rows come back it falls back to `canon_status != 'deleted'` (all exhibition matches).

The exhibition fallback banner in the Almanack appears when `exhibition_fallback=True` is returned by the batting/bowling endpoints.

### Real-world records benchmarks

`real_world_records` table is seeded at startup (idempotent) with 28 reference records. The `GET /api/almanack/honours/with-world-records` endpoint enriches in-game honours with `real_world` data and `pct_of_world_record`.

Bowling records use `display_value` (pre-formatted `W/R` string) rather than separate wickets/runs columns, matching the `formatBowlingFigures()` display in the frontend.

---

## Constraints

These files must not be modified:

- `game_engine.py` — stable engine, covered by tests, any change risks breaking the probability model
- `database.py` — DB access layer, changes break the canon system tests

Both test suites (`test_canon_system.py` and `uat/test_calendar.py`) must remain green. They are the acceptance gates for all changes.

---

## Known deferred items (POLISH)

From `REVIEW_REPORT.md` — all BLOCKER and MINOR issues were fixed before this session. Four POLISH items remain deferred:

1. **Follow-on not implemented** — Test matches track the follow-on threshold but don't yet enforce it (would require game_engine changes)
2. **Repeated imports** — A few modules are imported twice in `app.py` (harmless, cosmetic)
3. **Calendar pagination** — The schedule view loads all fixtures; could be slow for very long seasons
4. **FK pragma** — `PRAGMA foreign_keys = ON` is set at connection time in `database.py` but not in `schema.sql` itself

---

## Packaging

```bash
pip install pyinstaller
pyinstaller ribi.spec
# → dist/RollItBowlIt
```

The spec bundles `templates/`, `static/`, `schema.sql`, `seed_data.py`, and `config.py`. It excludes `config_dev.py`. The executable is a single-file binary that self-extracts on first run.

Set `console=True` in `ribi.spec` temporarily if you need to debug packaging issues (the spec file has a comment about this).

---

## Adding a new API route

1. Add the route function to `app.py`
2. Add a corresponding test in `test_canon_system.py` (or the appropriate suite)
3. If the route needs new DB queries, add them to `database.py`
4. Run `pytest tests/` to verify nothing is broken

---

## Database reset

Delete `ribi.db` and restart. The seed runs automatically:

```bash
rm ribi.db
python start.py
```

All teams, players, venues, and a fresh season schedule are re-created from `seed_data.py`.
