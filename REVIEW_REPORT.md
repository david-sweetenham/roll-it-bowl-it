# Roll It & Bowl It — Peer Review Report

**Date:** 2026-04-11  
**Reviewer:** Section 17A Automated Audit  
**Total findings:** 10 (1 BLOCKER · 5 MINOR · 4 POLISH)

---

## Executive Summary

The codebase is well-structured and substantially complete. The three-layer architecture (Flask routes in `app.py`, pure SQL in `database.py`, game logic in `game_engine.py`) is clean and consistent. SQLite is used safely via parameterised queries in almost every place — the one exception is a SQL injection flaw in the world calendar route. One BLOCKER will cause the home dashboard to throw a 500 error on any database that contains at least one completed match, because a raw SQL query references a column named `bi.runs_scored` that has never existed (the column is called `runs`). That bug must be fixed before the app is shared. The remaining five MINOR findings are real correctness issues (slightly wrong NRR values, settings lost on refresh, one fragile Python idiom) that are safe to fix in a follow-up pass. The four POLISH items are dead code or style inconsistencies with no user-visible impact.

---

## Severity Summary

| Severity | Count |
|----------|-------|
| BLOCKER  | 1     |
| MINOR    | 5     |
| POLISH   | 4     |

---

## Area 1 — File Structure

**Result: PASS**

All expected files present and accounted for:

| File | Status |
|------|--------|
| `app.py` | Present (~3 131 lines) |
| `database.py` | Present (~1 200 lines) |
| `game_engine.py` | Present |
| `seed_data.py` | Present — idempotency guard checks team count before seeding |
| `schema.sql` | Present — 16 tables, 4 views, 6 indexes |
| `start.py` | Present |
| `start.sh` / `start.bat` | Present |
| `static/app.js` | Present |
| `static/style.css` | Present (2 225 lines) |
| `templates/index.html` | Present |
| `test_engine.py`, `test_sim_controls.py`, `test_world_sim.py` | Present |

No stray or unexpected files at the project root. The `.venv` directory exists and contains Flask.

---

## Area 2 — Game Engine (`game_engine.py`)

**Result: PASS**

- `bowl_ball()`: 4-stage dice mechanic (stage 1 ball type → stage 2 appeal → stage 3 not-out resolution → stage 4 dismissal type). All code paths return a complete result dict. No dangling branches found.
- `simulate_innings_fast()`: standalone innings simulator using `bowl_ball()`. Correctly terminates on 10 wickets or overs exhausted.
- `simulate_to()`: 6 valid targets (`wicket`, `over`, `session`, `day`, `innings`, `match`). Has a 5 000-iteration safety limit. Test session/day boundaries correctly defined at 5 days × 3 sessions = 15 boundaries.
- `quick_sim_match()`: entirely stats-based — makes no `bowl_ball()` calls. Separation from the dice engine is clean.
- `update_rankings()` / NRR formula: zero-division guards present in `game_engine`. The NRR formula applied in the engine is correct. (See Area 4 for a different NRR bug in `app.py`.)
- `generate_fixture_calendar()`: calendar density levels (`light`, `moderate`, `dense`) present.

No game-engine bugs found.

---

## Area 3 — Database Schema (`schema.sql` + `database.py`)

**Result: PASS with notes**

Schema notes:
- `PRAGMA foreign_keys = ON` is set per-connection in `database.get_db()` (database.py:17), not in schema.sql itself. Direct SQLite CLI connections to `ribi.db` will not enforce FK constraints by default.
- The `deliveries_archive_json` column on `matches` is not in schema.sql — it is added by `database.run_migrations()`, which is called at module load time (app.py:3124–3128). Fresh databases get the column applied before any request is served. Safe.
- Views (`batting_averages`, `bowling_averages`, `team_records_view`, `partnership_records`) are well-formed and used by Almanack endpoints.
- `database.py` uses parameterised queries (`?` and named bindings) throughout. The `update_*` functions use an allowed-list pattern to prevent unexpected column updates.

No schema bugs found.

---

## Area 4 — API Routes (`app.py`)

**Result: 2 BLOCKER/MINOR bugs found**

### BLOCKER-1 — `bi.runs_scored` does not exist (home dashboard broken)

**Location:** `app.py` lines 268, 274, 282  
**Endpoint:** `GET /api/stats/quick`

```python
# app.py:267–274
hs_row = db.execute(
    "SELECT bi.runs_scored, p.name as player_name, m.format, m.match_date "
    "FROM batter_innings bi "
    ...
    "ORDER BY bi.runs_scored DESC LIMIT 1"
).fetchone()

# app.py:282
"WHERE bi.runs_scored >= 100 AND m.status = 'complete' "
```

The `batter_innings` table has no column named `runs_scored`. The column is named `runs` (confirmed in `database.py:334` allowed-list and `schema.sql`). SQLite validates column names at query preparation time, so **this endpoint throws an `OperationalError` (500) on any database that has completed matches**. The home screen dashboard will never load stats once the first match is completed.

A secondary symptom: `app.js:320` reads `hs.runs_scored` from the JSON response. When the Python side is corrected to select `bi.runs`, the JS key must also be updated to `hs.runs`.

**Fix:**
```python
# Line 268: change bi.runs_scored → bi.runs
"SELECT bi.runs, p.name as player_name, m.format, m.match_date "
# Line 274: change bi.runs_scored → bi.runs
"ORDER BY bi.runs DESC LIMIT 1"
# Line 282: change bi.runs_scored → bi.runs
"WHERE bi.runs >= 100 AND m.status = 'complete' "
```
```javascript
// app.js:320: change hs.runs_scored → hs.runs
<div class="home-stat-value">${hs ? hs.runs : '—'}</div>
```

---

### MINOR-1 — SQL injection in `world_calendar` status filter

**Location:** `app.py` line 2480  
**Endpoint:** `GET /api/worlds/<id>/calendar`

```python
"WHERE f.world_id = ?" + (f" AND f.status = '{status}'" if status else ""),
```

The `status` parameter is taken directly from `request.args` and interpolated into the SQL string via an f-string. This is a SQL injection vulnerability. While the app runs on localhost only (so exploitation requires local access), the fix is trivial.

**Fix:** Add `status` to the parameterised arguments:
```python
base_sql = "WHERE f.world_id = ?"
params = (id,)
if status:
    base_sql += " AND f.status = ?"
    params = (id, status)
```

---

## Area 5 — Cross-Section Integration

**Result: 1 MINOR bug found**

### MINOR-2 — Tournament NRR uses cricket-notation overs as decimal overs

**Location:** `app.py` lines 1738–1754, function `_update_tournament_nrr`

The `overs_completed` field in the `innings` table is stored in **cricket notation** (e.g., `3.4` meaning 3 overs and 4 balls) using the calculation `new_over + new_ball / 10` (app.py:1209). However, `_update_tournament_nrr` reads this value and uses it directly as a **decimal float** in NRR arithmetic:

```python
inn1_overs = float(m.get('inn1_overs') or max_overs)
# ... later:
nrr = (rs / of - rc / ob) if (of > 0 and ob > 0) else 0.0
```

`3.4` in cricket notation = 3 overs + 4 balls = 22 balls total = `3.667` decimal overs. Using `3.4` directly understates the overs and overstates NRR. The error is up to ~0.08 overs per innings in the worst case (5 balls into an over).

**Fix:** Convert cricket notation to decimal before using in arithmetic:
```python
def _cricket_to_decimal(overs_str):
    parts = str(overs_str).split('.')
    return int(parts[0]) + (int(parts[1]) / 6 if len(parts) > 1 else 0)
```

---

## Area 6 — Edge Cases

**Result: 1 MINOR bug found**

### MINOR-3 — `'result' in dir()` anti-pattern; NameError possible on unusual path

**Location:** `app.py` line 1312  
**Endpoint:** `POST /api/matches/<id>/simulate`

```python
'innings_complete': result['innings_complete'] if 'result' in dir() else False,
```

Using `dir()` (which returns names in the current local scope) to guard against an undefined variable is non-idiomatic Python and fragile. If `_build_sim_state` returns `None` immediately, the loop body never executes and `result` is never assigned. The `'result' in dir()` guard catches this, but only by accident. A future refactor that moves the `result =` assignment could silently break the guard.

**Fix:** Initialise `result = None` before the while loop and replace the guard:
```python
result = None
while loop_count < max_loops:
    ...
    result = game_engine.simulate_to(...)
    ...
# Then:
'innings_complete': (result['innings_complete'] if result else False),
```

---

## Area 7 — Cricket Terminology & Rules

**Result: PASS with 1 POLISH note**

Terminology is consistent and correct throughout: over/ball/innings/wicket/maiden/extra (byes, leg-byes, wides, no-balls), toss, declaration, follow-on.

POLISH-1 (see Area 11): Test follow-on logic is not implemented despite a `follow_on` column existing in the `innings` table. Not a terminology issue, noted under Polish.

---

## Area 8 — Navigation & Frontend (`app.js` + `index.html`)

**Result: PASS**

- `showScreen()` correctly guards against leaving an in-progress match without confirmation.
- `onScreenLoad()` covers all 17+ screen names with appropriate load hooks; unrecognised screens log a warning.
- The API loading bar uses a counter (`_apiCallCount`) to handle concurrent requests correctly — bar appears on 0→1 and hides on any→0.
- `startBtn.replaceWith(startBtn.cloneNode(true))` pattern correctly prevents duplicate event listener accumulation on repeated calls to `loadPlayScreen()`.
- Error banner auto-dismisses after 5 seconds with `clearTimeout` preventing double-timer issues.

---

## Area 9 — Performance

**Result: PASS**

- `bulk_create_fixtures()` uses `executemany` without per-row commits (database.py:793–801).
- Almanack queries hit SQLite views with indexed columns.
- The deliveries archive pattern (`archive_old_matches`) compresses old delivery rows into a JSON blob to keep the `deliveries` table small.
- The world simulation processes up to 100 fixtures per call (capped in `game_engine.simulate_world_to`).
- No N+1 patterns detected in hot paths. The world calendar query fetches all fixtures in one query (app.py:2468–2482).

---

## Area 10 — Settings & Persistence

**Result: 1 MINOR bug found**

### MINOR-4 — User preferences not persisted across page refreshes

**Location:** `app.js` — `toggleDarkMode`, `toggleSound`, `toggleBroadcastMode`, `AppState.defaultFormat`, `AppState.defaultVenueId`

Only `animationSpeed` (`ribi_anim_speed`) and the first-run welcome flag (`ribi_welcomed`) are saved to `localStorage`. All other user preferences (`darkMode`, `soundEnabled`, `broadcastMode`, `defaultFormat`, `defaultVenueId`) live only in `AppState` and reset to their defaults on every page refresh.

**Fix:** Save each preference to `localStorage` on change and restore in the init block alongside the existing `ribi_anim_speed` restore (app.js ~line 3993).

---

## Area 11 — `start.py`, `start.sh`, `start.bat`

**Result: PASS**

- `start.py` correctly re-execs into the venv Python if not already running inside it.
- Python version check enforces 3.10+.
- Flask import check gives a clear error message.
- `DB_PATH` / `SCHEMA_PATH` use `os.path` correctly; portable across OS.
- `app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)` — correct for local use; `threaded=True` allows concurrent API calls.
- Browser auto-open uses a daemon thread with a 1.5 s delay. Safe.
- `database.run_migrations()` is called at app.py module load time (lines 3124–3128), ensuring the `deliveries_archive_json` column exists before any request is served.

---

## Area 12 — Print / Export

**Result: PASS with 1 MINOR note**

### MINOR-5 — `import_full_backup` table_order contains stale table names

**Location:** `app.py` lines 3012–3015

```python
table_order = [
    ...
    'series_matches',        # ← does not exist; should be 'series'
    'tournament_entries',    # ← does not exist; should be 'tournament_teams'
    ...
]
```

The actual schema tables are `series` and `tournament_teams`. The stale names appear in both the DELETE loop and the INSERT loop. The DELETE loop silently swallows errors (`except: pass`) and the INSERT loop inserts 0 rows (no matching key in the export dict). This means a full-backup restore will silently skip `series` and `tournament_teams` data, leaving those tables empty after a restore.

Note: `series` and `tournament_teams` do also appear separately in the list, so this may be intentional dead code from a rename. Confirm and remove the stale entries.

---

## Polish Notes

**POLISH-1 — Test follow-on not implemented**

`_determine_next_innings()` (app.py:45–64) always follows the fixed innings-order pattern (1A, 2B, 3A, 4B) and ignores the `follow_on` column on the `innings` table. If a follow-on rule were applied, innings 3 would be batted by the team that just batted in innings 2. Not a crash bug — the game still plays correctly as a no-follow-on Test — but the schema implies this was planned.

**POLISH-2 — Repeated `import json as _json` inside function bodies**

`app.py` contains roughly 20 function-scoped `import json as _json` statements. Python caches module imports, so this has no performance impact, but it is non-idiomatic. A single top-level `import json` would be cleaner.

**POLISH-3 — `world_calendar` always returns all fixtures before slicing**

`app.py` lines 2484–2510: All fixtures are fetched from SQLite, converted to a list of dicts, sorted in Python, and then sliced by `offset`/`limit`. For large worlds with thousands of fixtures this is inefficient. The sort and pagination could be pushed into the SQL query.

**POLISH-4 — `PRAGMA foreign_keys = ON` not in `schema.sql`**

Any tool that connects to `ribi.db` directly (e.g., DB Browser for SQLite, the sqlite3 CLI) will silently ignore foreign key constraints. Adding `PRAGMA foreign_keys = ON;` at the top of `schema.sql` and/or documenting this in a `README` would protect manual operations.

---

## Recommended Fix Order

### Must fix before sharing / shipping:

1. **BLOCKER-1** — `bi.runs_scored` → `bi.runs` in `app.py` (3 sites) and `hs.runs_scored` → `hs.runs` in `app.js` (1 site).

### Should fix in next maintenance pass:

2. **MINOR-1** — Parameterise `status` in the `world_calendar` SQL query.
3. **MINOR-2** — Convert cricket-notation `overs_completed` to decimal before NRR arithmetic.
4. **MINOR-4** — Persist dark mode, sound, broadcast, default format to `localStorage`.
5. **MINOR-5** — Remove or correct `series_matches` / `tournament_entries` in `import_full_backup` table_order.
6. **MINOR-3** — Replace `'result' in dir()` with `result = None` sentinel initialisation.

### Nice to have:

7. POLISH-1 through POLISH-4 — follow-on, deferred imports, calendar pagination, FK pragma.

---

## Remediation Log (Section 17B)

**Date:** 2026-04-11  
**Engineer:** Section 17B Automated Remediation  
**Test suite:** 14 tests — 5 (test_engine) + 5 (test_sim_controls) + 4 (test_world_sim) — all passing before and after remediation.

---

### Schema Integrity Sweep

Identifiers checked across `app.py`, `database.py`, `app.js`:

| Identifier | File | Line(s) | Disposition |
|---|---|---|---|
| `bi.runs_scored` | `app.py` | 268, 274, 282 | **BUG** — `batter_innings` has no `runs_scored` column. Fixed (BLOCKER-1). |
| `hs.runs_scored` | `app.js` | 320 | **BUG** — mirrors BLOCKER-1; reads wrong key from JSON. Fixed alongside BLOCKER-1. |
| `runs_scored` (Python variable) | `app.py` | 629, 631, 692, 697, 777, 807, 1256, 1279 | SAFE — local Python variable or dict key, not a SQL column reference. |
| `runs_scored` (deliveries table column) | `app.py` | 672, 719 | SAFE — `deliveries` table has a `runs_scored` column. |
| `runs_scored` (deliveries INSERT) | `database.py` | 388, 394, 410 | SAFE — inserting into `deliveries` table. |
| `runs_scored` (tournament_teams column) | `database.py` | 740 | SAFE — column exists in `tournament_teams`. |
| `runs_scored` (deliveries SELECT) | `database.py` | 1584, 1888 | SAFE — selecting from `deliveries` table. |
| `runs_scored` (delivery event) | `app.js` | 815, 951, 3138 | SAFE — reading from `deliveries` API response or sim_digest dict key. |
| `series_matches` (table name) | `app.py` | 3012 | **BUG** — table doesn't exist; stale name in `import_full_backup`. Fixed (BLOCKER-2). |
| `tournament_entries` (table name) | `app.py` | 3013 | **BUG** — table doesn't exist; stale name in `import_full_backup`. Fixed (BLOCKER-2). |
| `series_matches` (function call) | `app.py` | 1352, 1641 | SAFE — calling `database.get_series_matches()`, a valid Python function. |
| `get_series_matches` (function def) | `database.py` | 645 | SAFE — function definition for series match query. |

**Additional stale identifiers beyond documented findings:** None found.

---

### Finding Remediation Table

| ID | Description | Original Severity | Applied Severity | Status | Files Changed |
|---|---|---|---|---|---|
| BLOCKER-1 | `bi.runs_scored` does not exist — home dashboard 500 | BLOCKER | BLOCKER | **FIXED** | `app.py`, `app.js` |
| BLOCKER-2 (was MINOR-5) | `series_matches` / `tournament_entries` stale table names in `import_full_backup` | MINOR (reclassified BLOCKER) | BLOCKER | **FIXED** | `app.py` |
| MINOR-3 | `'result' in dir()` anti-pattern in simulate endpoint | MINOR | MINOR | **FIXED** | `app.py` |
| MINOR-2 | Tournament NRR uses cricket-notation overs as decimal | MINOR | MINOR | **FIXED** | `app.py` |
| MINOR-1 | SQL injection: `status` param interpolated into `world_calendar` SQL | MINOR | MINOR | **FIXED** | `app.py` |
| MINOR-4 | User preferences not persisted to `localStorage` | MINOR | MINOR | **FIXED** | `app.js` |
| POLISH-1 | Test follow-on not implemented | POLISH | POLISH | DEFERRED — design decision, not a crash bug |
| POLISH-2 | Repeated `import json as _json` in function bodies | POLISH | POLISH | DEFERRED — no impact |
| POLISH-3 | `world_calendar` pagination done in Python, not SQL | POLISH | POLISH | DEFERRED — no impact until very large worlds |
| POLISH-4 | `PRAGMA foreign_keys = ON` not in `schema.sql` | POLISH | POLISH | DEFERRED — runtime FK enforcement is in place |

---

### Detailed Fix Notes

**BLOCKER-1 fix** (`app.py:267–284`, `app.js:320`):  
Root cause: `quick_stats` queries used `bi.runs_scored` against the `batter_innings` table, which has the column named `runs`. SQLite raises `OperationalError: no such column: bi.runs_scored` at query preparation time. Replaced all three SQL occurrences with `bi.runs`. Also replaced the corresponding JS read from `hs.runs_scored` → `hs.runs` so the home dashboard card renders correctly.

**BLOCKER-2 fix** (`app.py:3012–3013`):  
Root cause: `import_full_backup`'s `table_order` list contained `'series_matches'` and `'tournament_entries'` — both stale names from a schema rename that was never applied here. The actual tables are `series` and `tournament_teams`. The DELETE loop had `except: pass` that swallowed the `OperationalError`, and the INSERT loop silently inserted 0 rows (no matching key in the backup dict), leaving those tables empty after a restore. Fixed by replacing `'series_matches'` with `'tournament_teams'` (in the correct FK insertion order: after `'tournaments'`) and removing `'tournament_entries'` entirely. The correct table `'series'` was already present in the list.

**MINOR-3 fix** (`app.py:1262`, `app.py:1313`):  
Root cause: `'result' in dir()` is a fragile guard for an uninitialized variable — relying on `dir()` listing local scope names is non-idiomatic and would fail silently if the variable assignment moved. Added `result = None` sentinel before the while loop; changed guard to `result is not None`.

**MINOR-2 fix** (`app.py:1700–1713`):  
Root cause: `overs_completed` is stored in cricket notation (e.g. `3.4` = 3 overs 4 balls) but was cast directly to `float` for NRR arithmetic, treating it as decimal overs (3.4 decimal overs ≠ 3 overs 4 balls = 3.667 decimal overs). Added helper `_cricket_overs_to_decimal()` that splits on `.` and divides the ball count by 6. Applied to both `inn1_overs` and `inn2_overs` in `_update_tournament_nrr`.

**MINOR-1 fix** (`app.py:2492–2494`):  
Root cause: `status` query parameter interpolated into SQL string via f-string: `f" AND f.status = '{status}'"`. Fixed by appending a `?` placeholder and passing `status` as a bound parameter.

**MINOR-4 fix** (`app.js`):  
Root cause: `toggleDarkMode`, `toggleSound`, `toggleBroadcastMode`, `setDefaultFormat`, `setDefaultVenue` each mutated `AppState` but never persisted to `localStorage`. Added `localStorage.setItem(...)` calls in each function. Added restore block in `DOMContentLoaded` after the existing `ribi_anim_speed` restore, covering all five preferences with valid-value guards. Checked `almanackFilters` (session-level UI state, appropriate not to persist), journal entries (server-side data), and world sim progress indicators (transient) — none share the pattern and none were changed.

---

*End of report.*
