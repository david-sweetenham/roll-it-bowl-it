# Changelog

All notable changes to Roll It & Bowl It are documented here.

---

## [0.1.0-dev] — 2026-04-12

Initial development release. Core game engine, full season simulation, live match play, and two rolling modes.

### Added

**HOWZAT! Engine**
- 4-stage dice system for every delivery: Stage 1 (delivery type), Stage 2 (appeal outcome), Stage 3 (not-out resolution), Stage 4 (dismissal type), Stage 4b (catch location)
- Batter rating system (1–5) with per-rating dismissal thresholds: rating 5 needs roll ≥ 6 to be out; each step down adds one pip (rating 1 is out on ≥ 2)
- Real wicket rates confirmed over 5,000-delivery automated runs: 27.2% / 21.2% / 16.2% / 11.2% / 6.2% per appeal by rating
- Bowler rating (1–5) influencing wicket-possible frequency in Stage 1
- Free hit mechanic: wicket-possible deliveries after a no-ball skip the appeal and cannot dismiss the batter
- All formats supported: T20 (20 overs), ODI (50 overs), Test (two innings, up to 5 days)

**Manual Roll mode**
- 13-state DiceState machine (`IDLE`, `ROLLING_S1`, `HOWZAT`, `ROLLING_S2`, `NOT_OUT`, `OUT_PENDING`, `ROLLING_S3`, `ROLLING_S4`, `ROLLING_S4B`, `RESULT`, `FREE_HIT`, `INNINGS_END`, `MATCH_END`)
- Each dice stage waits for a button press: Appeal, Continue, Dismissal, Caught Where?
- HOWZAT! display with fielding team name and animated die during appeal state
- NOT OUT / OUT result labels with entrance animations
- Roll mode toggle in match header, persisted to localStorage (`ribi_roll_mode`)
- Mid-ball mode switching: Manual → Auto queued to end of current ball; Auto → Manual immediate
- Broadcast mode: slower animations (700ms → 1200ms flicker), 2-second hold before Appeal button appears
- Free hit banner visible throughout free-hit deliveries in Manual mode

**Auto-Roll mode**
- All dice stages resolve immediately on Roll press
- Same underlying engine, no waiting
- Default mode for new sessions

**Tension detection**
- `GET /api/matches/<id>/tension` endpoint
- Five tension conditions: T20 finish (≤ 2 overs, < 15 runs needed), last wicket, century approach (95+ runs), required rate > 12, tied match (≤ 1 over left)
- Suggestion banner appears when any condition is met; user can dismiss per-innings
- Click banner to switch to Manual mode immediately
- Dismissed suggestions reset at innings change

**Keyboard shortcuts**
- Space / R: Roll (when idle)
- A: Appeal (Manual mode, HOWZAT state)
- C: Continue / not out (Manual mode)
- D: Dismissal (Manual mode, out pending) or toggle dark mode (otherwise)
- M: Toggle roll mode (when idle, not AI vs AI)
- F: Fast-sim current match

**Teams and venues**
- 10 seeded international teams: England, Australia, India, Pakistan, New Zealand, South Africa, West Indies, Sri Lanka, Bangladesh, Afghanistan
- 18 venues with home-ground advantage modelling
- Full player rosters with individual batter and bowler ratings

**Season management**
- Full season schedule generated on first run
- Fast-sim: simulate remaining balls in the current match instantly
- World sim: sim-day and sim-season endpoints for unattended season progression
- Standings updated after every match: points, NRR, wins, losses, no results

**Statistics and records**
- Ball-by-ball recording to SQLite (25+ tables)
- Career batting and bowling aggregates
- Partnership records
- All-time records: highest individual scores, best bowling figures, highest team totals
- Head-to-head team records

**API**
- 71 REST endpoints covering match lifecycle, world simulation, statistics, and records
- All responses in JSON

**Frontend**
- Single-page application (vanilla JavaScript, no build step)
- Live scorecards updating after every ball
- Ball-by-ball commentary feed
- Dark mode toggle
- Broadcast mode
- CSS animations: die face flicker, HOWZAT entrance/flash, appeal pulse, not-out/out result entrances, free hit glow, tension suggestion pulse

**Packaging**
- PyInstaller spec (`ribi.spec`) for single-binary distribution
- Dev config excluded from packaged builds
- `console=False` for clean desktop experience

### Fixed (pre-release review — all BLOCKER and MINOR issues resolved)

- **BLOCKER-1**: `bi.runs_scored` reference corrected — was referencing wrong variable in innings total calculation
- **BLOCKER-2**: Stale table names removed — several queries referenced table names from an earlier schema revision
- **MINOR-1**: SQL injection risk eliminated — parameterised queries used throughout `app.py`
- **MINOR-2**: NRR calculation corrected — net run rate now uses overs faced correctly in edge cases (all-out vs overs complete)
- **MINOR-3**: `dir()` anti-pattern removed — config loading now uses explicit attribute access
- **MINOR-4**: localStorage persistence implemented — roll mode and dark mode preference now survive page refresh

### Deferred (POLISH — no impact on gameplay or correctness)

- Follow-on enforcement in Test matches (threshold tracked, not yet enforced)
- Duplicate import statements in `app.py` (cosmetic)
- Schedule pagination for very long seasons
- `PRAGMA foreign_keys = ON` not present in `schema.sql` (set at connection time in `database.py`)

### Technical

- Python 3.14.3 (GCC 15.2.1), Flask 3.1.3, SQLite via built-in `sqlite3`
- 103 automated tests passing: 5 engine, 5 sim controls, 4 world sim, 94 canon system
