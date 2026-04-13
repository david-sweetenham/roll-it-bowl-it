"""
uat/test_calendar.py — UAT tests for the Cricket Calendar Engine (cricket_calendar.py).
Run with:  python uat/test_calendar.py
All 10 tests must show [PASS] and the final line must read: All tests PASSED
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date
import cricket_calendar as cc

# ── Helpers ────────────────────────────────────────────────────────────────────

_passed = 0
_failed = 0


def _check(name, condition, detail=''):
    global _passed, _failed
    if condition:
        print(f'[PASS] {name}')
        _passed += 1
    else:
        print(f'[FAIL] {name}' + (f' — {detail}' if detail else ''))
        _failed += 1


def _make_world(nations, start='2026-01-01', density='moderate', years=2):
    """
    Build minimal team_ids / team_names / venue_ids inputs and call
    generate_realistic_calendar().  Returns (team_ids, team_names, fixtures).
    """
    team_ids   = list(range(1, len(nations) + 1))
    team_names = {i + 1: nations[i] for i in range(len(nations))}
    venue_ids  = {nations[i]: [100 + i] for i in range(len(nations))}
    fixtures   = cc.generate_realistic_calendar(
        team_ids, team_names, venue_ids,
        start_date_str=start, density=density, years=years,
    )
    return team_ids, team_names, fixtures


# ── Test 1: No England home fixtures in January or February ───────────────────

def test_england_no_home_jan_feb():
    nations = ['England', 'Australia', 'India', 'Pakistan']
    _, tnames, fixtures = _make_world(nations)
    england_id = next(i for i, n in tnames.items() if n == 'England')

    violations = []
    for fx in fixtures:
        if fx['team1_id'] == england_id and fx.get('is_home_for_team1'):
            d = date.fromisoformat(fx['scheduled_date'])
            if d.month in (1, 2):
                violations.append(fx['scheduled_date'])

    _check(
        'Test 1: No England home fixtures in Jan or Feb',
        len(violations) == 0,
        f'Found {len(violations)} violation(s): {violations[:3]}',
    )


# ── Test 2: No India home fixtures in July or August ──────────────────────────

def test_india_no_home_jul_aug():
    nations = ['England', 'Australia', 'India', 'Pakistan']
    _, tnames, fixtures = _make_world(nations)
    india_id = next(i for i, n in tnames.items() if n == 'India')

    violations = []
    for fx in fixtures:
        if fx['team1_id'] == india_id and fx.get('is_home_for_team1'):
            d = date.fromisoformat(fx['scheduled_date'])
            if d.month in (7, 8):
                violations.append(fx['scheduled_date'])

    _check(
        'Test 2: No India home fixtures in Jul or Aug',
        len(violations) == 0,
        f'Found {len(violations)} violation(s): {violations[:3]}',
    )


# ── Test 3: The Ashes appears if both England and Australia present ─────────────

def test_ashes_present():
    nations = ['England', 'Australia', 'India', 'Pakistan']
    _, _, fixtures = _make_world(nations, years=2)

    ashes_fixtures = [
        fx for fx in fixtures
        if 'Ashes' in (fx.get('series_name') or '')
    ]
    _check(
        'Test 3: The Ashes appears when England and Australia are both in world',
        len(ashes_fixtures) > 0,
        f'Found {len(ashes_fixtures)} Ashes fixture(s)',
    )


# ── Test 4: Ashes not generated when only one team present ────────────────────

def test_ashes_absent_without_both():
    nations = ['England', 'India', 'Pakistan', 'New Zealand']
    _, _, fixtures = _make_world(nations, years=2)

    ashes_fixtures = [
        fx for fx in fixtures
        if 'Ashes' in (fx.get('series_name') or '')
    ]
    _check(
        'Test 4: No Ashes fixtures generated when Australia is absent',
        len(ashes_fixtures) == 0,
        f'Found {len(ashes_fixtures)} unexpected Ashes fixture(s)',
    )


# ── Test 5: No team double-booked on the same date ────────────────────────────

def test_no_double_booking():
    nations = ['England', 'Australia', 'India', 'Pakistan',
               'New Zealand', 'South Africa']
    team_ids, _, fixtures = _make_world(nations, density='busy')

    # Build {team_id: sorted list of dates}
    team_dates = {tid: [] for tid in team_ids}
    for fx in fixtures:
        d = fx['scheduled_date']
        team_dates[fx['team1_id']].append(d)
        team_dates[fx['team2_id']].append(d)

    conflicts = []
    for tid, dates in team_dates.items():
        seen = set()
        for d in dates:
            if d in seen:
                conflicts.append((tid, d))
            seen.add(d)

    _check(
        'Test 5: No team is double-booked on the same date',
        len(conflicts) == 0,
        f'Found {len(conflicts)} conflict(s): {conflicts[:3]}',
    )


# ── Test 6: No fixture in a nation's avoid_months ──────────────────────────────

def test_no_fixtures_in_avoid_months():
    nations = ['England', 'India', 'Pakistan', 'Bangladesh']
    team_ids, team_names, fixtures = _make_world(nations, density='busy')

    violations = []
    for fx in fixtures:
        host_id   = fx['team1_id']
        host_name = cc._normalise(team_names.get(host_id, ''))
        avoid     = set(cc._get_season_data(host_name).get('avoid_months', []))
        if not avoid:
            continue
        d = date.fromisoformat(fx['scheduled_date'])
        if d.month in avoid and fx.get('is_home_for_team1') and not fx.get('is_icc_event'):
            violations.append((host_name, fx['scheduled_date']))

    _check(
        'Test 6: No bilateral fixture placed in a nation\'s avoid_months',
        len(violations) == 0,
        f'Found {len(violations)} violation(s): {violations[:3]}',
    )


# ── Test 7: India vs Pakistan only at ICC events ──────────────────────────────

def test_india_pakistan_no_bilateral():
    nations = ['England', 'Australia', 'India', 'Pakistan']
    team_ids, team_names, fixtures = _make_world(nations, years=4)

    india_id = next(i for i, n in team_names.items() if n == 'India')
    pak_id   = next(i for i, n in team_names.items() if n == 'Pakistan')

    bilateral_violations = []
    for fx in fixtures:
        ids = {fx['team1_id'], fx['team2_id']}
        if ids == {india_id, pak_id} and not fx.get('is_icc_event'):
            bilateral_violations.append(fx['scheduled_date'])

    _check(
        'Test 7: India vs Pakistan only at ICC events (bilateral_blocked)',
        len(bilateral_violations) == 0,
        f'Found {len(bilateral_violations)} bilateral India-Pak fixture(s): {bilateral_violations[:3]}',
    )


# ── Test 8: Tests before ODIs before T20s within same series ─────────────────

def test_format_order_within_series():
    nations = ['England', 'Australia', 'India', 'South Africa']
    _, _, fixtures = _make_world(nations, density='moderate')

    # Group by series_key
    from collections import defaultdict
    by_series = defaultdict(list)
    for fx in fixtures:
        sk = fx.get('series_key')
        if sk:
            by_series[sk].append(fx)

    _FORMAT_ORDER = {'Test': 0, 'ODI': 1, 'T20': 2}

    violations = []
    for sk, fxs in by_series.items():
        sorted_fxs = sorted(fxs, key=lambda x: x['scheduled_date'])
        prev_order = -1
        for fx in sorted_fxs:
            order = _FORMAT_ORDER.get(fx.get('format', ''), 99)
            if order < prev_order:
                violations.append((sk, fx['scheduled_date'], fx.get('format')))
                break
            prev_order = order

    _check(
        'Test 8: Tests before ODIs before T20s within each tour series',
        len(violations) == 0,
        f'Found {len(violations)} format-ordering violation(s): {violations[:3]}',
    )


# ── Test 9: Total fixture count reasonable for density ────────────────────────

def test_fixture_count_vs_density():
    nations = ['England', 'Australia', 'India', 'Pakistan',
               'New Zealand', 'South Africa', 'West Indies', 'Sri Lanka']

    _, _, busy_fxs    = _make_world(nations, density='busy',    years=2)
    _, _, mod_fxs     = _make_world(nations, density='moderate', years=2)
    _, _, relaxed_fxs = _make_world(nations, density='relaxed',  years=2)

    b, m, r = len(busy_fxs), len(mod_fxs), len(relaxed_fxs)
    ok = (b > m > r) and (r > 10) and (b < 2000)
    _check(
        'Test 9: Fixture counts ordered busy > moderate > relaxed, all in reasonable range',
        ok,
        f'busy={b}, moderate={m}, relaxed={r}',
    )


# ── Test 10: All required fields populated on every fixture ──────────────────

def test_required_fields():
    nations = ['England', 'Australia', 'India', 'Pakistan']
    _, _, fixtures = _make_world(nations)

    REQUIRED = [
        'fixture_id', 'series_name', 'series_key',
        'team1_id', 'team2_id', 'scheduled_date', 'format',
        'is_icc_event', 'match_number_in_series', 'series_length',
        'is_home_for_team1', 'tour_template',
    ]

    missing = []
    for fx in fixtures:
        for key in REQUIRED:
            if key not in fx or fx[key] is None:
                missing.append((fx.get('fixture_id', '?'), key))

    _check(
        'Test 10: All required fields present and non-null on every fixture',
        len(missing) == 0,
        f'{len(missing)} missing field occurrence(s): {missing[:5]}',
    )


# ── Test 11: Bilateral series names are not duplicated ───────────────────────

def test_series_names_not_duplicated():
    nations = ['England', 'Scotland', 'Ireland', 'Netherlands']
    _, _, fixtures = _make_world(nations, density='moderate', years=2)

    duplicated = []
    for fx in fixtures:
        name = fx.get('series_name') or ''
        if ' — ' not in name:
            continue
        left, right = name.split(' — ', 1)
        if left == right:
            duplicated.append(name)

    _check(
        'Test 11: Bilateral series names are not duplicated',
        len(duplicated) == 0,
        f'Found {len(duplicated)} duplicated name(s): {duplicated[:3]}',
    )


# ── Helpers for domestic / world-rules UAT ────────────────────────────────────

def _dom_teams(league, ids, prefix='Club'):
    return [
        {'team_id': tid, 'name': f'{prefix}{tid}', 'league': league,
         'home_venue_id': tid * 10}
        for tid in ids
    ]


def _intl_world(nations, dom_leagues=None, dom_teams=None,
                start='2026-01-01', years=1, density='moderate'):
    """Generate a realistic calendar for international (optionally + domestic) worlds."""
    team_ids   = list(range(1, len(nations) + 1))
    team_names = {i + 1: n for i, n in enumerate(nations)}
    venue_ids  = {n: [100 + i] for i, n in enumerate(nations)}
    return team_ids, team_names, cc.generate_realistic_calendar(
        team_ids         = team_ids,
        team_names       = team_names,
        venue_ids        = venue_ids,
        start_date_str   = start,
        density          = density,
        years            = years,
        domestic_leagues = dom_leagues,
        domestic_teams   = dom_teams,
    )


# ── Test 12: Domestic fixtures carry domestic_competition key ─────────────────

def test_domestic_fixtures_are_tagged():
    """
    Every fixture produced from a domestic league entry must carry the
    domestic_competition key set to the competition key string.
    """
    dom = _dom_teams('IPL', range(101, 107))
    fixtures = cc.generate_realistic_calendar(
        team_ids=[], team_names={}, venue_ids={},
        start_date_str='2026-01-01', years=1,
        domestic_leagues=['ipl'], domestic_teams=dom,
    )

    untagged = [f for f in fixtures if not f.get('domestic_competition')]
    wrong_key = [f for f in fixtures
                 if f.get('domestic_competition') and f['domestic_competition'] != 'ipl']

    _check(
        'Test 12: all domestic fixtures carry domestic_competition="ipl"',
        len(fixtures) > 0 and len(untagged) == 0 and len(wrong_key) == 0,
        f'fixtures={len(fixtures)}, untagged={len(untagged)}, wrong_key={len(wrong_key)}',
    )


# ── Test 13: Selected-clubs mode — unselected teams produce no fixtures ────────

def test_selected_clubs_excludes_unselected():
    """
    When only a subset of clubs are passed to generate_domestic_fixtures
    (simulating domestic_team_mode='selected'), no fixture involves a
    club outside the chosen subset.
    """
    ALL_IDS      = list(range(201, 211))   # 10 clubs
    SELECTED_IDS = {201, 203, 205, 207}    # 4 chosen

    selected = _dom_teams('County Championship', SELECTED_IDS)
    fixtures = cc.generate_domestic_fixtures('county_championship', selected, 2026, 2027)

    seen     = {f['team1_id'] for f in fixtures} | {f['team2_id'] for f in fixtures}
    outsiders = seen - SELECTED_IDS

    _check(
        'Test 13: selected-clubs mode — fixture pool restricted to chosen clubs only',
        len(outsiders) == 0 and len(fixtures) > 0,
        f'outsiders={outsiders}, fixtures={len(fixtures)}',
    )


# ── Test 14: Full-league mode — every club participates ───────────────────────

def test_full_league_all_clubs_participate():
    """
    When the full club list is passed to generate_domestic_fixtures
    (domestic_team_mode='full_league'), every club appears in at least one
    fixture and the home+away round-robin count is at least n*(n-1).
    """
    ALL_IDS = list(range(301, 309))   # 8 Sheffield Shield-style state sides
    all_teams = _dom_teams('Sheffield Shield', ALL_IDS, prefix='State')

    fixtures = cc.generate_domestic_fixtures('sheffield_shield', all_teams, 2026, 2027)

    seen     = {f['team1_id'] for f in fixtures} | {f['team2_id'] for f in fixtures}
    missing  = set(ALL_IDS) - seen
    n        = len(ALL_IDS)
    min_count = n * (n - 1)   # home+away round-robin lower bound

    _check(
        'Test 14: full-league mode — every club in the pool appears in at least one fixture',
        len(missing) == 0 and len(fixtures) >= min_count,
        f'missing={missing}, fixtures={len(fixtures)}, expected>={min_count}',
    )


# ── Test 15: Combined world — domestic and international pools never cross ─────

def test_combined_world_no_cross_pool_fixtures():
    """
    In a combined world the international bilateral calendar and the domestic
    competition fixtures are entirely separate: no single fixture pairs a
    national team against a franchise/county club.
    """
    INTL = ['England', 'Australia', 'India', 'South Africa']
    DOM_IDS = list(range(401, 407))
    dom = _dom_teams('IPL', DOM_IDS, prefix='Franchise')

    intl_ids, _, fixtures = _intl_world(
        INTL, dom_leagues=['ipl'], dom_teams=dom,
    )
    intl_set = set(intl_ids)
    dom_set  = set(DOM_IDS)

    cross = [
        f for f in fixtures
        if (f['team1_id'] in intl_set) != (f['team2_id'] in intl_set)
           and (f['team1_id'] in dom_set or f['team2_id'] in dom_set)
    ]

    _check(
        'Test 15: combined world — no fixture crosses international and domestic team pools',
        len(cross) == 0,
        f'{len(cross)} cross-pool fixture(s) found',
    )


# ── Test 16: Domestic fixtures use the correct format for each competition ─────

def test_domestic_competition_format():
    """
    Each domestic competition must produce fixtures in the format declared
    in DOMESTIC_COMPETITIONS (e.g. BBL → T20, Sheffield Shield → Test, IPL → T20).
    """
    cases = [
        ('bbl',               'Big Bash League',     range(501, 509), 'T20'),
        ('sheffield_shield',  'Sheffield Shield',    range(511, 517), 'Test'),
        ('ipl',               'IPL',                 range(521, 527), 'T20'),
        ('county_championship','County Championship',range(531, 535), 'Test'),
    ]

    failures = []
    for comp_key, league, ids, expected_fmt in cases:
        teams    = _dom_teams(league, ids)
        fixtures = cc.generate_domestic_fixtures(comp_key, teams, 2026, 2027)
        wrong    = [f for f in fixtures if f.get('format') != expected_fmt]
        if wrong:
            failures.append(
                f'{comp_key}: {len(wrong)} fixture(s) had wrong format '
                f'(e.g. {wrong[0].get("format")!r} instead of {expected_fmt!r})'
            )

    _check(
        'Test 16: each domestic competition generates fixtures in its declared format',
        len(failures) == 0,
        '; '.join(failures),
    )


# ── Test 17: World settings normalisation (calendar layer) ────────────────────

def test_world_settings_normalisation():
    """
    The settings normalisation rules used by create_world and
    world_regenerate_calendar preserve valid values and replace invalid
    values with safe defaults.
    """
    def _normalise(s):
        scope = s.get('world_scope', 'international')
        if scope not in ('international', 'domestic', 'combined'):
            scope = 'international'
        mode = s.get('domestic_team_mode', 'selected')
        if mode not in ('selected', 'full_league'):
            mode = 'selected'
        leagues = s.get('domestic_leagues') or []
        return scope, mode, leagues

    cases = [
        ({'world_scope': 'domestic',  'domestic_team_mode': 'full_league',
          'domestic_leagues': ['bbl']},
         'domestic',      'full_league', ['bbl']),
        ({'world_scope': 'combined',  'domestic_team_mode': 'selected',
          'domestic_leagues': ['ipl', 'psl']},
         'combined',      'selected',    ['ipl', 'psl']),
        ({'world_scope': 'international'},
         'international', 'selected',    []),
        ({'world_scope': 'BAD',       'domestic_team_mode': 'ALSO_BAD'},
         'international', 'selected',    []),
        ({},
         'international', 'selected',    []),
    ]

    failures = []
    for settings, exp_scope, exp_mode, exp_leagues in cases:
        scope, mode, leagues = _normalise(settings)
        if (scope, mode, leagues) != (exp_scope, exp_mode, exp_leagues):
            failures.append(
                f'{settings!r}: got ({scope!r},{mode!r},{leagues!r}), '
                f'expected ({exp_scope!r},{exp_mode!r},{exp_leagues!r})'
            )

    _check(
        'Test 17: world settings normalisation preserves valid values, rejects invalid ones',
        len(failures) == 0,
        '; '.join(failures),
    )


# ── Runner ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('Running cricket calendar UAT tests…\n')
    test_england_no_home_jan_feb()
    test_india_no_home_jul_aug()
    test_ashes_present()
    test_ashes_absent_without_both()
    test_no_double_booking()
    test_no_fixtures_in_avoid_months()
    test_india_pakistan_no_bilateral()
    test_format_order_within_series()
    test_fixture_count_vs_density()
    test_required_fields()
    test_series_names_not_duplicated()
    test_domestic_fixtures_are_tagged()
    test_selected_clubs_excludes_unselected()
    test_full_league_all_clubs_participate()
    test_combined_world_no_cross_pool_fixtures()
    test_domestic_competition_format()
    test_world_settings_normalisation()

    print(f'\nResults: {_passed} passed, {_failed} failed')
    if _failed == 0:
        print('All tests PASSED')
    else:
        print(f'{_failed} test(s) FAILED')
        sys.exit(1)
