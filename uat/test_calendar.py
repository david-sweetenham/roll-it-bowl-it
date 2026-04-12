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

    print(f'\nResults: {_passed} passed, {_failed} failed')
    if _failed == 0:
        print('All tests PASSED')
    else:
        print(f'{_failed} test(s) FAILED')
        sys.exit(1)
