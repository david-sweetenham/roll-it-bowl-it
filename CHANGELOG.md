# Changelog

All notable changes to Roll It & Bowl It are documented here.

## [0.3.0-dev] — 2026-04-13

### Added

- International, domestic, and combined world creation flows
- Managed world teams for:
  - AI-only worlds
  - one international side
  - one domestic side
  - one international plus one domestic side
- World fixture horizons from `1` to `10` years
- Extendable world calendars so saves can continue beyond the initial generated block
- Domestic world coverage rules:
  - `Selected Clubs`
  - `Full League`
- `Ageless Players` and `Retire & Regens` world lifecycle modes
- World-only regen players with per-world retirement timing
- Country-aware and league-aware regen naming pools
- Domestic and associate nation expansion in the seed data
- Local LAN startup mode via `python start.py --lan`
- Story desk panels on World and Almanack screens
- Archive match layouts for completed matches
- Synthetic scorecards for simulated world matches
- Crowd reactions for major events
- Umpire pop-up signals for `OUT`, `FOUR`, and `SIX`
- Live mini wagon wheel in the match panel

### Changed

- Match presentation now leans more heavily into sports-broadcast hierarchy
- Auto mode ball resolution is clearer and more outcome-led
- Archive matches now open into archive-focused scorecard layouts rather than the live match shell
- World overview now surfaces more context about world rules, schedules, and active series
- Recent results on the Home screen are now recency-aware for newly completed matches

### Fixed

- Completed matches opening into the toss screen instead of an archive/result view
- Archive scorecards being trapped in a small scroll area instead of filling the screen
- Almanack batting tab failing to load data on first open
- Almanack filters being hidden behind an expandable control
- Light-mode selector mismatch in the live score UI
- Required-rate calculation using incorrect over math
- World `My Next Match` misbehaviour when no managed team was selected
- Domestic realistic worlds ignoring selected teams
- Duplicate or broken world series naming in overview feeds
- Toss choice buttons not resetting cleanly between matches
- Batting-first roll button being blocked by bowling-selection logic
- Autoplay continuing while away from the match screen
- Played matches and journal links not opening the proper scorecard/archive view

## [0.2.0-dev] — 2026-04-12

### Added

- `Classic` and `Modern` scoring systems
- first-run scoring choice
- international and domestic setup split
- realistic and random world calendars
- expanded international/associate data
- major domestic competitions and squads
- broadcast-style graphic system
- Almanack honours enrichment against real-world record benchmarks

### Fixed

- Almanack batting and bowling empty-state/API wiring issues
- honours labels using raw DB keys
- bowling figures display inconsistencies
- several setup and presentation issues discovered during review

## [0.1.0-dev] — 2026-04-12

Initial development release.

### Added

- core HOWZAT dice engine
- manual and auto roll modes
- live match screen
- scorecards and commentary
- season/world simulation
- SQLite-backed stats and records
- packaging support
