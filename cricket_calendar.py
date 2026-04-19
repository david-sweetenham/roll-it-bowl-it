"""
cricket_calendar.py — Realistic international cricket calendar engine.

Generates FTP-style bilateral tour schedules and ICC event anchors that
respect home season windows, monsoon avoidance, and rivalry conventions.

generate_realistic_calendar() is the main entry point.
generate_fixture_calendar() in game_engine.py remains available as the
'random' style fallback and is not modified.
"""

from datetime import date, timedelta
from itertools import combinations
import competition_rules

# ── Home Season Windows ────────────────────────────────────────────────────────

HOME_SEASONS = {
    'England': {
        'months': [5, 6, 7, 8, 9],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'north',
        'preferred_test_months': [5, 6, 7, 8],
        'avoid_months': [10, 11, 12, 1, 2, 3, 4],
    },
    'Australia': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'south',
        'preferred_test_months': [11, 12, 1, 2],
        'avoid_months': [],
    },
    'India': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'subcontinent',
        'preferred_test_months': [11, 12, 1, 2],
        'avoid_months': [6, 7, 8, 9],
    },
    'Pakistan': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'subcontinent',
        'preferred_test_months': [11, 12, 1, 2],
        'avoid_months': [6, 7, 8],
    },
    'New Zealand': {
        'months': [11, 12, 1, 2, 3, 4],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'south',
        'preferred_test_months': [12, 1, 2],
        'avoid_months': [],
    },
    'South Africa': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'south',
        'preferred_test_months': [11, 12, 1, 2, 3],
        'avoid_months': [],
    },
    'West Indies': {
        'months': [1, 2, 3, 4, 7, 8],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'caribbean',
        'preferred_test_months': [1, 2, 3, 4],
        'avoid_months': [9, 10, 11],
    },
    'Sri Lanka': {
        'months': [1, 2, 3, 7, 8, 9],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'subcontinent',
        'preferred_test_months': [1, 2, 3],
        'avoid_months': [5, 6],
    },
    'Bangladesh': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'subcontinent',
        'preferred_test_months': [11, 12, 1, 2],
        'avoid_months': [6, 7, 8, 9],
    },
    'Afghanistan': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['T20', 'ODI'],
        'hemisphere': 'subcontinent',
        'preferred_test_months': [],
        'avoid_months': [6, 7, 8],
        'neutral_venue': True,
    },
    'Zimbabwe': {
        'months': [10, 11, 12, 1, 2, 3, 4],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'south',
        'preferred_test_months': [11, 12, 1, 2],
        'avoid_months': [],
    },
    'Ireland': {
        'months': [5, 6, 7, 8],
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'north',
        'preferred_test_months': [6, 7],
        'avoid_months': [10, 11, 12, 1, 2, 3, 4, 9],
    },
    'Scotland': {
        'months': [5, 6, 7, 8],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'north',
        'preferred_test_months': [],
        'avoid_months': [10, 11, 12, 1, 2, 3, 4, 9],
    },
    'Netherlands': {
        'months': [5, 6, 7, 8],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'north',
        'preferred_test_months': [],
        'avoid_months': [10, 11, 12, 1, 2, 3, 4, 9],
    },
    'Namibia': {
        'months': [9, 10, 11, 12, 1, 2, 3],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'south',
        'preferred_test_months': [],
        'avoid_months': [4, 5, 6, 7, 8],
    },
    'Nepal': {
        'months': [2, 3, 4, 10, 11],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'subcontinent',
        'preferred_test_months': [],
        'avoid_months': [5, 6, 7, 8, 9],
    },
    'UAE': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'gulf',
        'preferred_test_months': [],
        'avoid_months': [5, 6, 7, 8, 9],
    },
    'Oman': {
        'months': [10, 11, 12, 1, 2, 3],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'gulf',
        'preferred_test_months': [],
        'avoid_months': [5, 6, 7, 8, 9],
    },
    'United States': {
        'months': [4, 5, 6, 7, 8, 9],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'north',
        'preferred_test_months': [],
        'avoid_months': [11, 12, 1, 2],
    },
    'Canada': {
        'months': [5, 6, 7, 8, 9],
        'formats': ['ODI', 'T20'],
        'hemisphere': 'north',
        'preferred_test_months': [],
        'avoid_months': [10, 11, 12, 1, 2, 3, 4],
    },
}

# ── Tour Structure Templates ───────────────────────────────────────────────────

TOUR_TEMPLATES = {
    'full_tour_major': {
        'tests': 3,
        'odis': 3,
        't20s': 3,
        'duration_days': 45,
        'gap_between_formats_days': 3,
        'gap_between_matches': {'Test': 5, 'ODI': 2, 'T20': 1},
    },
    'full_tour_standard': {
        'tests': 2,
        'odis': 3,
        't20s': 3,
        'duration_days': 35,
        'gap_between_formats_days': 3,
        'gap_between_matches': {'Test': 5, 'ODI': 2, 'T20': 1},
    },
    'short_tour': {
        'tests': 1,
        'odis': 3,
        't20s': 3,
        'duration_days': 25,
        'gap_between_formats_days': 2,
        'gap_between_matches': {'Test': 5, 'ODI': 2, 'T20': 1},
    },
    't20_series_only': {
        'tests': 0,
        'odis': 0,
        't20s': 5,
        'duration_days': 12,
        'gap_between_formats_days': 0,
        'gap_between_matches': {'T20': 2},
    },
    'odi_series_only': {
        'tests': 0,
        'odis': 5,
        't20s': 0,
        'duration_days': 14,
        'gap_between_formats_days': 0,
        'gap_between_matches': {'ODI': 2},
    },
    'test_series_only': {
        'tests': 5,
        'odis': 0,
        't20s': 0,
        'duration_days': 50,
        'gap_between_formats_days': 0,
        'gap_between_matches': {'Test': 6},
    },
    'ashes_odi_t20': {
        # Separate ODI + T20 series on an Ashes tour window
        'tests': 0,
        'odis': 3,
        't20s': 3,
        'duration_days': 18,
        'gap_between_formats_days': 3,
        'gap_between_matches': {'ODI': 2, 'T20': 1},
    },
    'gap_fill_t20': {
        'tests': 0,
        'odis': 0,
        't20s': 3,
        'duration_days': 8,
        'gap_between_formats_days': 0,
        'gap_between_matches': {'T20': 2},
    },
    'white_ball_standard': {
        'tests': 0,
        'odis': 3,
        't20s': 3,
        'duration_days': 16,
        'gap_between_formats_days': 2,
        'gap_between_matches': {'ODI': 2, 'T20': 1},
    },
    'associate_white_ball': {
        'tests': 0,
        'odis': 2,
        't20s': 3,
        'duration_days': 12,
        'gap_between_formats_days': 2,
        'gap_between_matches': {'ODI': 2, 'T20': 1},
    },
}

# ── Special Series ─────────────────────────────────────────────────────────────

SPECIAL_SERIES = {
    ('England', 'Australia'): {
        'name': 'The Ashes',
        'test_template': 'test_series_only',
        'odi_t20_template': 'ashes_odi_t20',
        'odi_t20_separate': True,
        'tests': 5,
        'frequency_years': 2,
    },
    ('Australia', 'New Zealand'): {
        'name': 'Trans-Tasman Trophy',
        'preferred_template': 'full_tour_standard',
    },
    ('England', 'West Indies'): {
        'name': 'Wisden Trophy',
        'preferred_template': 'full_tour_standard',
    },
    ('England', 'India'): {
        'name': 'Pataudi Trophy',
        'preferred_template': 'full_tour_major',
    },
    ('India', 'Pakistan'): {
        'name': 'India vs Pakistan',
        'neutral_venue_only': True,
        'bilateral_blocked': True,
    },
    ('Australia', 'England'): {
        'name': 'The Ashes',
        'test_template': 'test_series_only',
        'odi_t20_template': 'ashes_odi_t20',
        'odi_t20_separate': True,
        'tests': 5,
        'frequency_years': 2,
    },
}

# ── Major nations (get full tours by default) ──────────────────────────────────
_FULL_MEMBERS = frozenset([
    'England', 'Australia', 'India', 'Pakistan',
    'New Zealand', 'South Africa', 'West Indies', 'Sri Lanka',
    'Bangladesh', 'Afghanistan', 'Zimbabwe', 'Ireland',
])

_ASSOCIATE_PRIORITY = [
    'Scotland', 'Netherlands', 'Namibia', 'Nepal',
    'UAE', 'Oman', 'United States', 'Canada',
]


# ── ICC Event Cycle ────────────────────────────────────────────────────────────

def get_icc_events(start_year, end_year):
    """
    Return a list of ICC events scheduled between start_year and end_year.
    Based on the real ICC cycle from 2024 onwards.
    """
    events = []

    for year in range(start_year, end_year + 1):

        # T20 World Cup — every 2 years (even years)
        if year % 2 == 0:
            events.append({
                'name': f"ICC Men's T20 World Cup {year}",
                'format': 'T20',
                'type': 'world_cup',
                'start_month': 6,
                'duration_days': 25,
                'teams': 16,
                'host': _get_t20_wc_host(year),
                'year': year,
            })

        # 50-over World Cup — every 4 years
        if year in [2027, 2031, 2035, 2039]:
            events.append({
                'name': f"ICC Men's Cricket World Cup {year}",
                'format': 'ODI',
                'type': 'world_cup',
                'start_month': 10,
                'duration_days': 45,
                'teams': 10,
                'host': _get_50over_wc_host(year),
                'year': year,
            })

        # World Test Championship Final — every 2 years (odd years), June, England
        if year % 2 == 1:
            events.append({
                'name': f'ICC World Test Championship Final {year}',
                'format': 'Test',
                'type': 'wtc_final',
                'start_month': 6,
                'duration_days': 7,
                'teams': 2,
                'host': 'England',
                'year': year,
            })

        # Champions Trophy — every 4 years
        if year in [2025, 2029, 2033, 2037]:
            events.append({
                'name': f'ICC Champions Trophy {year}',
                'format': 'ODI',
                'type': 'champions_trophy',
                'start_month': 3,
                'duration_days': 18,
                'teams': 8,
                'host': _get_ct_host(year),
                'year': year,
            })

    return events


def _get_t20_wc_host(year):
    hosts = {
        2024: 'West Indies',
        2026: 'India',
        2028: 'England',
        2030: 'Australia',
        2032: 'South Africa',
        2034: 'New Zealand',
        2036: 'Pakistan',
    }
    return hosts.get(year, 'India')


def _get_50over_wc_host(year):
    hosts = {
        2027: 'South Africa',
        2031: 'India',
        2035: 'England',
        2039: 'Australia',
    }
    return hosts.get(year, 'India')


def _get_ct_host(year):
    hosts = {
        2025: 'Pakistan',
        2029: 'India',
        2033: 'England',
        2037: 'Australia',
    }
    return hosts.get(year, 'India')


# ── Weather / Season Validity ──────────────────────────────────────────────────

def is_valid_fixture_date(host_nation, match_date, format_='Test'):
    """
    Returns (is_valid: bool, reason: str).
    Checks whether the proposed date is within acceptable conditions for the host.
    """
    month = match_date.month
    season_data = _get_season_data(host_nation)
    avoid = season_data.get('avoid_months', [])
    valid_months = season_data.get('months', list(range(1, 13)))

    if month in avoid:
        return False, f'Off-season/monsoon in {host_nation} during month {month}'
    if month not in valid_months:
        return False, f'Outside {host_nation} home season (month {month})'

    # Tests during preferred months only (soft check — returns valid but flags it)
    if format_ == 'Test':
        preferred = season_data.get('preferred_test_months', valid_months)
        if preferred and month not in preferred:
            return True, f'Valid but outside preferred Test window for {host_nation}'

    return True, 'OK'


# ── Team Name Normalisation ────────────────────────────────────────────────────

def _normalise(name):
    """Return normalised team name for HOME_SEASONS lookup."""
    if not name:
        return name
    # Exact match
    if name in HOME_SEASONS:
        return name
    # Case-insensitive
    for k in HOME_SEASONS:
        if k.lower() == name.lower():
            return k
    # Partial
    for k in HOME_SEASONS:
        if k.lower() in name.lower() or name.lower() in k.lower():
            return k
    return name  # unknown — caller handles the fallback


def _get_season_data(team_name):
    """Return HOME_SEASONS entry for a team, with fallback for unknowns."""
    norm = _normalise(team_name)
    return HOME_SEASONS.get(norm, {
        'months': list(range(1, 13)),
        'formats': ['Test', 'ODI', 'T20'],
        'hemisphere': 'unknown',
        'preferred_test_months': list(range(1, 13)),
        'avoid_months': [],
    })


def _supported_formats(team_name):
    return _get_season_data(team_name).get('formats', ['Test', 'ODI', 'T20'])


def _team_tier(team_name):
    norm = _normalise(team_name)
    if norm in _FULL_MEMBERS:
        return 'full'
    return 'associate'


def _is_major(team_name):
    return _normalise(team_name) in _FULL_MEMBERS


# ── Schedule Tracker ───────────────────────────────────────────────────────────

class _Schedule:
    """Tracks committed date ranges per team (team_id -> list of (start, end))."""

    def __init__(self, team_ids):
        self._busy = {tid: [] for tid in team_ids}

    def is_free(self, team_id, start, end):
        for s, e in self._busy.get(team_id, []):
            if not (end < s or start > e):
                return False
        return True

    def book(self, team_id, start, end):
        self._busy.setdefault(team_id, []).append((start, end))

    def first_free_after(self, team_id, after_date):
        """Return the first day >= after_date when team_id has no commitment."""
        d = after_date
        while True:
            blocked = any(s <= d <= e for s, e in self._busy.get(team_id, []))
            if not blocked:
                return d
            d += timedelta(days=1)


# ── Window Finding ─────────────────────────────────────────────────────────────

def _window_months_ok(start, end, valid_months):
    """Return True if every calendar month spanned by [start, end] is in valid_months."""
    cy, cm = start.year, start.month
    ey, em = end.year, end.month
    while (cy, cm) <= (ey, em):
        if cm not in valid_months:
            return False
        if cm == 12:
            cy += 1
            cm = 1
        else:
            cm += 1
    return True


def _find_window(host_name, host_id, visitor_id, search_from, deadline,
                 duration_days, sched):
    """
    Find the first date >= search_from where:
    - the window falls within host's home season months
    - both teams are free for the full duration
    Returns a date or None.
    """
    valid_months = set(_get_season_data(host_name).get('months', range(1, 13)))
    avoid_months = set(_get_season_data(host_name).get('avoid_months', []))

    current = search_from
    while current + timedelta(days=duration_days) <= deadline:
        if current.month not in valid_months or current.month in avoid_months:
            # Jump to the 1st of the next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
            continue

        window_end = current + timedelta(days=duration_days)

        if _window_months_ok(current, window_end, valid_months):
            if (sched.is_free(host_id, current, window_end) and
                    sched.is_free(visitor_id, current, window_end)):
                return current

        current += timedelta(days=1)

    return None


# ── Fixture List Builder ────────────────────────────────────────────────────────

def _get_venue(team_name, venue_lookup, match_idx=0):
    """Return a venue ID for the given team, cycling through available venues."""
    norm = _normalise(team_name)
    vlist = venue_lookup.get(norm) or venue_lookup.get(team_name) or []
    if not vlist:
        return None
    return vlist[match_idx % len(vlist)]


def _build_tour_fixtures(host_id, visitor_id, host_name, visitor_name,
                          template_name, series_name, series_key,
                          start_date, host_formats, venue_lookup,
                          is_icc=False, icc_event_name=None):
    """
    Generate the fixture list for one bilateral tour following the given template.
    Returns a list of fixture dicts. Tests precede ODIs precede T20s.
    """
    tmpl = TOUR_TEMPLATES[template_name]
    fixtures = []
    current = start_date
    match_idx = 0

    # Determine which formats to include (respects team's supported formats)
    can_test = 'Test' in host_formats and 'Test' in _get_season_data(host_name).get('formats', ['Test', 'ODI', 'T20'])

    # Collect formats in canonical order: Tests → ODIs → T20s
    schedule_plan = []
    n_tests = tmpl.get('tests', 0) if can_test else 0
    n_odis  = tmpl.get('odis', 0)
    n_t20s  = tmpl.get('t20s', 0)
    total   = n_tests + n_odis + n_t20s

    if n_tests:
        schedule_plan.append(('Test', n_tests, tmpl['gap_between_matches'].get('Test', 5)))
    if n_odis:
        schedule_plan.append(('ODI', n_odis, tmpl['gap_between_matches'].get('ODI', 2)))
    if n_t20s:
        schedule_plan.append(('T20', n_t20s, tmpl['gap_between_matches'].get('T20', 1)))

    overall_match_num = 0
    for fmt, count, gap_days in schedule_plan:
        for i in range(count):
            overall_match_num += 1
            venue_id = _get_venue(host_name, venue_lookup, match_idx)
            fixtures.append({
                'fixture_id':              f'{series_key}_m{overall_match_num}',
                'series_name':             series_name,
                'series_key':              series_key,
                'team1_id':                host_id,
                'team2_id':                visitor_id,
                'scheduled_date':          current.isoformat(),
                'format':                  fmt,
                'venue_id':                venue_id,
                'is_icc_event':            is_icc,
                'icc_event_name':          icc_event_name,
                'match_number_in_series':  i + 1,
                'series_length':           count,
                'is_home_for_team1':       True,
                'tour_template':           template_name,
            })
            current += timedelta(days=gap_days)
            match_idx += 1

        # Gap between format blocks
        current += timedelta(days=tmpl.get('gap_between_formats_days', 2))

    return fixtures, current


# ── ICC Event Placement ────────────────────────────────────────────────────────

def _place_icc_events(team_ids, id_to_name, venue_lookup, sched,
                       start_date, end_date, density):
    """
    Generate ICC event fixtures and block team schedules for the event duration.
    Returns list of fixture dicts.
    """
    start_year = start_date.year
    end_year   = end_date.year
    events     = get_icc_events(start_year, end_year)
    fixtures   = []
    series_ctr = [0]

    def next_key():
        series_ctr[0] += 1
        return f'icc_{series_ctr[0]:04d}'

    def select_participants(event):
        limit = min(len(team_ids), event.get('teams', len(team_ids)))
        host_name = _normalise(event.get('host', ''))
        host_id = next((tid for tid in team_ids if _normalise(id_to_name.get(tid, '')) == host_name), None)

        ordered = []
        if host_id is not None:
            ordered.append(host_id)

        fulls = [
            tid for tid in team_ids
            if tid != host_id and _team_tier(id_to_name.get(tid, '')) == 'full'
        ]
        associates = []
        for assoc_name in _ASSOCIATE_PRIORITY:
            for tid in team_ids:
                if tid == host_id or tid in fulls or tid in associates:
                    continue
                if _normalise(id_to_name.get(tid, '')) == assoc_name:
                    associates.append(tid)
        leftovers = [
            tid for tid in team_ids
            if tid not in ordered and tid not in fulls and tid not in associates
        ]
        ordered.extend(fulls)
        ordered.extend(associates)
        ordered.extend(leftovers)
        return ordered[:limit]

    for event in events:
        event_start = date(event['year'], event['start_month'], 1)
        if event_start < start_date or event_start >= end_date:
            continue

        event_end = event_start + timedelta(days=event['duration_days'])
        fmt       = event['format']
        host_name = event.get('host', 'India')
        ev_name   = event['name']
        ev_type   = event['type']

        # WTC Final: 2-team special — just block England's schedule, no fixtures generated
        # (bilateral engine will handle it as a single Test match if both teams present)
        if ev_type == 'wtc_final':
            for tid in team_ids:
                name = _normalise(id_to_name.get(tid, ''))
                if name == 'England':
                    sched.book(tid, event_start, event_end)
            continue

        participants = select_participants(event)

        # Block participating teams only for the event duration
        for tid in participants:
            sched.book(tid, event_start, event_end)

        # Generate round-robin group fixtures between all participating teams
        pairs = list(combinations(participants, 2))

        if density == 'relaxed':
            pairs = pairs[:max(len(pairs) // 2, 3)]
        elif density == 'moderate':
            pairs = pairs[:min(len(pairs), 20)]

        series_key     = next_key()
        current        = event_start
        gap            = 1 if fmt == 'T20' else 2
        team_last_date = {}  # tid -> last date they were scheduled

        for i, (t1, t2) in enumerate(pairs):
            if current >= event_end:
                break

            # Ensure neither team plays twice on the same day
            earliest = max(
                team_last_date.get(t1, current),
                team_last_date.get(t2, current),
            )
            if earliest > current:
                current = earliest
            if current >= event_end:
                break

            # Also advance every 2 games to simulate a realistic day's play schedule
            if i > 0 and i % 2 == 0 and current == (
                    team_last_date.get(t1, current - timedelta(days=1))):
                current += timedelta(days=gap)

            venue_id = _get_venue(host_name, venue_lookup, i)

            fixtures.append({
                'fixture_id':             f'{series_key}_g{i + 1}',
                'series_name':            ev_name,
                'series_key':             series_key,
                'team1_id':               t1,
                'team2_id':               t2,
                'scheduled_date':         current.isoformat(),
                'format':                 fmt,
                'venue_id':               venue_id,
                'is_icc_event':           True,
                'icc_event_name':         ev_name,
                'match_number_in_series': i + 1,
                'series_length':          len(pairs),
                'is_home_for_team1':      False,
                'tour_template':          'icc_event',
            })

            team_last_date[t1] = current + timedelta(days=1)
            team_last_date[t2] = current + timedelta(days=1)

        # Add knockout stubs (SF + Final) for larger events
        if len(participants) >= 4 and density != 'relaxed':
            ko_start = event_start + timedelta(days=event['duration_days'] - 8)
            knockout_pairs = [
                ('Semi-Final 1', 0, participants[0], participants[3]),
                ('Semi-Final 2', 2, participants[1], participants[2]),
                ('Final', 5, participants[0], participants[1]),
            ]
            for label, offset, t1, t2 in knockout_pairs:
                if ko_start + timedelta(days=offset) >= event_end:
                    break
                fixtures.append({
                    'fixture_id':             f'{series_key}_{label.replace(" ", "_").lower()}',
                    'series_name':            f'{ev_name} — {label}',
                    'series_key':             series_key,
                    'team1_id':               t1,
                    'team2_id':               t2,
                    'scheduled_date':         (ko_start + timedelta(days=offset)).isoformat(),
                    'format':                 fmt,
                    'venue_id':               _get_venue(host_name, venue_lookup, 99),
                    'is_icc_event':           True,
                    'icc_event_name':         ev_name,
                    'match_number_in_series': 1,
                    'series_length':          1,
                    'is_home_for_team1':      False,
                    'tour_template':          'icc_event',
                })

    return fixtures


# ── Ashes Scheduling ───────────────────────────────────────────────────────────

def schedule_ashes(calendar_fixtures, start_year, england_venues, australia_venues,
                   england_id, australia_id, sched, start_date, end_date, density):
    """
    Schedule Ashes series for the generation period.
    Alternates home/away every 2 years.
    England hosts in English summer (July–August).
    Australia hosts in Australian summer (November–January).
    Always 5 Tests, with separate ODI/T20 series on the same touring window.
    """
    fixtures = []
    series_ctr = [0]

    def next_key(label):
        series_ctr[0] += 1
        return f'ashes_{series_ctr[0]:03d}_{label}'

    for year in range(start_year, end_date.year + 1):
        # Determine host based on year parity (even → Australia hosts; odd → England hosts)
        if year % 2 == 0:
            host_id    = australia_id
            visitor_id = england_id
            host_name  = 'Australia'
            venues     = australia_venues
            # Australian Ashes: Nov–Jan
            tour_start = date(year, 11, 1)
            odi_start  = date(year + 1, 1, 20)
        else:
            host_id    = england_id
            visitor_id = australia_id
            host_name  = 'England'
            venues     = england_venues
            # England Ashes: July–August
            tour_start = date(year, 7, 1)
            odi_start  = date(year, 8, 20)

        if tour_start < start_date or tour_start >= end_date:
            continue

        duration = TOUR_TEMPLATES['test_series_only']['duration_days']
        window   = _find_window(host_name, host_id, visitor_id,
                                tour_start, end_date, duration, sched)
        if window is None:
            continue

        window_end = window + timedelta(days=duration)
        sched.book(host_id,    window, window_end)
        sched.book(visitor_id, window, window_end)

        series_key = next_key('tests')
        fxs, _ = _build_tour_fixtures(
            host_id, visitor_id, host_name, 'visitor',
            'test_series_only',
            'The Ashes',
            series_key, window,
            host_formats=_get_season_data(host_name).get('formats', ['Test', 'ODI', 'T20']),
            venue_lookup={host_name: venues},
        )
        fixtures.extend(fxs)

        # ODI + T20 series on the same tour
        if density != 'relaxed':
            odi_dur    = TOUR_TEMPLATES['ashes_odi_t20']['duration_days']
            odi_window = _find_window(host_name, host_id, visitor_id,
                                      odi_start, end_date, odi_dur, sched)
            if odi_window:
                odi_end = odi_window + timedelta(days=odi_dur)
                sched.book(host_id,    odi_window, odi_end)
                sched.book(visitor_id, odi_window, odi_end)

                odi_key = next_key('odi_t20')
                fxs2, _ = _build_tour_fixtures(
                    host_id, visitor_id, host_name, 'visitor',
                    'ashes_odi_t20',
                    'England v Australia',
                    odi_key, odi_window,
                    host_formats=['ODI', 'T20'],
                    venue_lookup={host_name: venues},
                )
                fixtures.extend(fxs2)

    return fixtures


# ── Standard Bilateral Scheduling ─────────────────────────────────────────────

def _pick_template(host_name, visitor_name, density, special=None):
    """Return the tour template name for this bilateral pair."""
    host_tier = _team_tier(host_name)
    visitor_tier = _team_tier(visitor_name)
    host_formats = set(_supported_formats(host_name))
    visitor_formats = set(_supported_formats(visitor_name))
    can_play_tests = 'Test' in host_formats and 'Test' in visitor_formats

    if special and special.get('preferred_template'):
        tmpl = special['preferred_template']
    elif not can_play_tests:
        tmpl = 'white_ball_standard' if host_tier == 'full' or visitor_tier == 'full' else 'associate_white_ball'
    elif host_tier == 'full' and visitor_tier == 'full':
        tmpl = 'full_tour_major' if density == 'busy' else 'full_tour_standard'
    elif host_tier == 'associate' and visitor_tier == 'associate':
        tmpl = 'associate_white_ball'
    else:
        tmpl = 'short_tour' if density != 'busy' else 'full_tour_standard'

    if density == 'relaxed':
        if tmpl == 'white_ball_standard':
            tmpl = 'associate_white_ball'
        elif tmpl not in ('associate_white_ball', 't20_series_only', 'odi_series_only'):
            tmpl = 'short_tour'

    return tmpl


def _schedule_one_tour(host_id, visitor_id, host_name, visitor_name,
                        template_name, series_name, series_key,
                        search_from, end_date, venue_lookup, sched):
    """
    Find a window and generate fixtures for one bilateral tour.
    Returns (fixtures, booked_end_date) or ([], None) if no window found.
    """
    tmpl        = TOUR_TEMPLATES[template_name]
    duration    = tmpl['duration_days']
    host_fmts   = _get_season_data(host_name).get('formats', ['Test', 'ODI', 'T20'])

    window = _find_window(host_name, host_id, visitor_id,
                          search_from, end_date, duration, sched)
    if window is None:
        return [], None

    window_end = window + timedelta(days=duration)
    sched.book(host_id,    window, window_end)
    sched.book(visitor_id, window, window_end)

    fxs, _ = _build_tour_fixtures(
        host_id, visitor_id, host_name, visitor_name,
        template_name, series_name, series_key,
        window, host_fmts, venue_lookup,
    )
    return fxs, window_end


def _schedule_bilateral(team_ids, id_to_name, venue_lookup, sched,
                         start_date, end_date, density, years, series_ctr):
    """
    Schedule bilateral tours for all team pairs, respecting home seasons.
    In a 2-year period: team A hosts team B, team B hosts team A (one each direction).
    """
    fixtures = []
    pairs    = list(combinations(team_ids, 2))

    for t1, t2 in pairs:
        n1 = _normalise(id_to_name.get(t1, f'Team{t1}'))
        n2 = _normalise(id_to_name.get(t2, f'Team{t2}'))
        tier1 = _team_tier(n1)
        tier2 = _team_tier(n2)

        key1    = (n1, n2)
        key2    = (n2, n1)
        special = SPECIAL_SERIES.get(key1) or SPECIAL_SERIES.get(key2)

        # Skip bilaterally blocked pairs
        if special and special.get('bilateral_blocked'):
            continue

        # Skip Ashes — handled separately
        if special and special.get('name') == 'The Ashes':
            continue

        if tier1 == 'associate' and tier2 == 'associate' and density == 'relaxed':
            continue

        series_name_base = special.get('name', f'{n1} v {n2}') if special else f'{n1} v {n2}'
        tmpl             = _pick_template(n1, n2, density, special)
        host_label_1     = f'{n1} v {n2}'
        host_label_2     = f'{n2} v {n1}'
        series_name_1    = series_name_base if series_name_base == host_label_1 else f'{series_name_base} — {host_label_1}'
        series_name_2    = series_name_base if series_name_base == host_label_2 else f'{series_name_base} — {host_label_2}'

        # Tour 1: t1 hosts t2 — search from start of period
        series_ctr[0] += 1
        key1_str   = f's{series_ctr[0]:04d}'
        fxs, t1end = _schedule_one_tour(
            t1, t2, n1, n2, tmpl,
            series_name_1,
            key1_str,
            start_date, end_date, venue_lookup, sched,
        )
        fixtures.extend(fxs)

        should_return = False
        if years >= 2 and density != 'relaxed':
            if tier1 == 'full' and tier2 == 'full':
                should_return = True
            elif (tier1 == 'full' or tier2 == 'full') and years >= 3:
                should_return = True
            elif density == 'busy' and years >= 4:
                should_return = True

        # Tour 2: t2 hosts t1 — search from midpoint when warranted
        if should_return:
            mid_date = start_date + timedelta(days=365)
            series_ctr[0] += 1
            key2_str   = f's{series_ctr[0]:04d}'
            fxs2, _ = _schedule_one_tour(
                t2, t1, n2, n1, tmpl,
                series_name_2,
                key2_str,
                mid_date, end_date, venue_lookup, sched,
            )
            fixtures.extend(fxs2)

    return fixtures


# ── Gap-filling T20 Series ─────────────────────────────────────────────────────

def _fill_gaps(team_ids, id_to_name, venue_lookup, sched,
               start_date, end_date, series_ctr):
    """
    Fill 3+ week free stretches with short T20 series.
    Only runs in 'busy' density mode.
    """
    fixtures = []
    pairs    = list(combinations(team_ids, 2))

    for t1, t2 in pairs:
        n1 = _normalise(id_to_name.get(t1, f'Team{t1}'))
        n2 = _normalise(id_to_name.get(t2, f'Team{t2}'))

        # Try to fit a T20 series during t1's home season gap
        series_ctr[0] += 1
        key = f's{series_ctr[0]:04d}'

        fxs, _ = _schedule_one_tour(
            t1, t2, n1, n2, 'gap_fill_t20',
            f'{n1} v {n2} T20 Series',
            key,
            start_date, end_date, venue_lookup, sched,
        )
        fixtures.extend(fxs)

    return fixtures


# ── Main Calendar Generator ────────────────────────────────────────────────────

# ── Domestic Competition Definitions ──────────────────────────────────────────

DOMESTIC_COMPETITIONS = {
    'county_championship': {
        'name':        'County Championship',
        'league':      'County Championship',
        'format':      'Test',
        'start_month': 4,
        'end_month':   9,
        'gap_days':    5,        # days between matches in the season
        'home_away':   True,
        'series_key_prefix': 'county',
    },
    't20_blast': {
        'name':        'Vitality T20 Blast',
        'league':      'County Championship',  # same clubs
        'format':      'T20',
        'start_month': 6,
        'end_month':   8,
        'gap_days':    3,
        'home_away':   True,
        'series_key_prefix': 't20blast',
    },
    'royal_london_cup': {
        'name':        'Royal London One-Day Cup',
        'league':      'County Championship',
        'format':      'ODI',
        'start_month': 4,
        'end_month':   5,
        'gap_days':    3,
        'home_away':   True,
        'series_key_prefix': 'rlcup',
    },
    'sheffield_shield': {
        'name':        'Sheffield Shield',
        'league':      'Sheffield Shield',
        'format':      'Test',
        'start_month': 10,
        'end_month':   3,   # wraps into next year
        'gap_days':    7,
        'home_away':   True,
        'series_key_prefix': 'shield',
    },
    'marsh_cup': {
        'name':        'Marsh One-Day Cup',
        'league':      'Sheffield Shield',
        'format':      'ODI',
        'start_month': 9,
        'end_month':   11,
        'gap_days':    3,
        'home_away':   True,
        'series_key_prefix': 'marsh',
    },
    'bbl': {
        'name':        'Big Bash League',
        'league':      'Big Bash League',
        'format':      'T20',
        'start_month': 12,
        'end_month':   2,   # wraps Jan-Feb
        'gap_days':    2,
        'home_away':   True,
        'series_key_prefix': 'bbl',
    },
    'ipl': {
        'name':        'Indian Premier League',
        'league':      'IPL',
        'format':      'T20',
        'start_month': 3,
        'end_month':   5,
        'gap_days':    2,
        'home_away':   True,
        'series_key_prefix': 'ipl',
    },
    'cpl': {
        'name':        'Caribbean Premier League',
        'league':      'CPL',
        'format':      'T20',
        'start_month': 8,
        'end_month':   9,
        'gap_days':    2,
        'home_away':   True,
        'series_key_prefix': 'cpl',
    },
    'psl': {
        'name':        'Pakistan Super League',
        'league':      'PSL',
        'format':      'T20',
        'start_month': 2,
        'end_month':   3,
        'gap_days':    2,
        'home_away':   True,
        'series_key_prefix': 'psl',
    },
    'the_hundred': {
        'name':        'The Hundred',
        'league':      'The Hundred',
        'format':      'Hundred',
        'start_month': 7,
        'end_month':   8,
        'gap_days':    2,        # 100-ball matches every 2 days through July-August
        'home_away':   True,
        'series_key_prefix': 'hundred',
        'duration_weeks': 3,     # ~3 weeks annual slot
        'annual': True,
    },
}

# ── The Hundred annual schedule ───────────────────────────────────────────────

HUNDRED_SCHEDULE = {
    'months':         [7, 8],       # July – August
    'duration_weeks': 3,
    'annual':         True,
    'format':         'Hundred',
    'teams':          'hundred_teams',
}


def _season_start(year, start_month):
    """Return the first date of the competition window in the given year."""
    try:
        return date(year, start_month, 1)
    except ValueError:
        return date(year, 1, 1)


def _season_end(year, start_month, end_month):
    """Return the last date of the competition window, handling year wraps."""
    if end_month >= start_month:
        return date(year, end_month, 28)
    else:
        # wraps into next year (e.g. Dec → Feb)
        return date(year + 1, end_month, 28)


def generate_domestic_fixtures(comp_key, comp_teams, start_year, end_year):
    """
    Generate round-robin fixtures for a domestic competition.

    Parameters
    ----------
    comp_key   : str — key in DOMESTIC_COMPETITIONS
    comp_teams : list of dicts with keys: team_id, home_venue_id, name
    start_year : int
    end_year   : int (exclusive)

    Returns list of fixture dicts compatible with create_world() expectations.
    """
    comp = DOMESTIC_COMPETITIONS.get(comp_key)
    if not comp or len(comp_teams) < 2:
        return []

    fixtures  = []
    fx_ctr    = [0]

    def _next_id():
        fx_ctr[0] += 1
        return f"dom_{comp_key}_{fx_ctr[0]}"

    for year in range(start_year, end_year):
        sm   = comp['start_month']
        em   = comp['end_month']
        gap  = comp['gap_days']
        fmt  = comp['format']
        name = comp['name']
        pfx  = comp['series_key_prefix']

        season_start = _season_start(year, sm)
        season_end   = _season_end(year, sm, em)

        # Generate all pairings
        from itertools import combinations as _comb
        pairs = list(_comb(range(len(comp_teams)), 2))
        if comp['home_away']:
            # both home and away
            pairs = [(a, b) for a, b in pairs] + [(b, a) for a, b in pairs]

        # Spread fixtures evenly across the season window
        window_days = max(1, (season_end - season_start).days)
        if len(pairs) == 0:
            continue
        step = max(gap, window_days // len(pairs))

        current_date = season_start
        for i, (a_idx, b_idx) in enumerate(pairs):
            t1 = comp_teams[a_idx]
            t2 = comp_teams[b_idx]
            fdate = season_start + timedelta(days=i * step)
            if fdate > season_end:
                fdate = season_end - timedelta(days=1)

            sk = f"{pfx}_{year}_{t1['team_id']}_{t2['team_id']}"
            fixtures.append({
                'fixture_id':              _next_id(),
                'series_name':             f"{name} {year}",
                'series_key':              f"{pfx}_{year}",
                'team1_id':                t1['team_id'],
                'team2_id':                t2['team_id'],
                'scheduled_date':          fdate.isoformat(),
                'format':                  fmt,
                'venue_id':                t1.get('home_venue_id'),
                'is_icc_event':            False,
                'icc_event_name':          None,
                'match_number_in_series':  i + 1,
                'series_length':           len(pairs),
                'is_home_for_team1':       True,
                'tour_template':           f'domestic_{comp_key}',
                'domestic_competition':    comp_key,
            })

    return fixtures


def generate_realistic_calendar(
    team_ids,
    team_names,
    venue_ids,
    start_date_str,
    density='moderate',
    years=2,
    use_real_schedule=True,
    domestic_leagues=None,
    domestic_teams=None,
):
    """
    Generate a realistic FTP-style international cricket calendar.

    Parameters
    ----------
    team_ids       : list of int
    team_names     : dict  {team_id: team_name}
    venue_ids      : dict  {team_name: [venue_id, ...]}
    start_date_str : str   'YYYY-MM-DD'
    density        : str   'busy' | 'moderate' | 'relaxed'
    years          : int   how many years to generate
    use_real_schedule : bool  (reserved; always True when called from here)

    Returns
    -------
    list of fixture dicts with keys:
        fixture_id, series_name, series_key, team1_id, team2_id,
        scheduled_date, format, venue_id, is_icc_event, icc_event_name,
        match_number_in_series, series_length, is_home_for_team1, tour_template
    """
    start_date = date.fromisoformat(start_date_str)
    end_date   = date(start_date.year + years, start_date.month, start_date.day)

    # Normalised name lookup
    id_to_name  = {tid: _normalise(team_names.get(tid, f'Team{tid}')) for tid in team_ids}
    name_to_id  = {v: k for k, v in id_to_name.items()}

    # Normalise venue lookup to use normalised team names as keys
    venue_lookup = {}
    for raw_name, vlist in venue_ids.items():
        norm = _normalise(raw_name) or raw_name
        venue_lookup[norm] = vlist if isinstance(vlist, list) else [vlist]

    sched       = _Schedule(team_ids)
    series_ctr  = [0]
    all_fixtures = []

    # ── Step 1: Place ICC events ──────────────────────────────────────────────
    icc_fxs = competition_rules.generate_icc_competitions(
        team_ids, team_names, venue_ids, start_date, end_date
    )
    all_fixtures.extend(icc_fxs)
    icc_windows = {}
    for fx in icc_fxs:
        sk = fx.get('series_key')
        if not sk:
            continue
        slot = icc_windows.setdefault(sk, {
            'min': fx.get('scheduled_date'),
            'max': fx.get('scheduled_date'),
            'teams': set(),
        })
        fx_date = fx.get('scheduled_date')
        if fx_date and (not slot['min'] or fx_date < slot['min']):
            slot['min'] = fx_date
        if fx_date and (not slot['max'] or fx_date > slot['max']):
            slot['max'] = fx_date
        if fx.get('team1_id'):
            slot['teams'].add(fx['team1_id'])
        if fx.get('team2_id'):
            slot['teams'].add(fx['team2_id'])
    for slot in icc_windows.values():
        if not slot.get('min') or not slot.get('max'):
            continue
        start_busy = date.fromisoformat(slot['min'])
        end_busy = date.fromisoformat(slot['max'])
        for tid in slot['teams']:
            sched.book(tid, start_busy, end_busy)

    # ── Step 2: Ashes (if both England and Australia present) ─────────────────
    eng_id = name_to_id.get('England')
    aus_id = name_to_id.get('Australia')
    if eng_id is not None and aus_id is not None:
        eng_venues = venue_lookup.get('England', [None])
        aus_venues = venue_lookup.get('Australia', [None])
        ashes_fxs = schedule_ashes(
            all_fixtures,
            start_date.year,
            eng_venues, aus_venues,
            eng_id, aus_id,
            sched, start_date, end_date, density,
        )
        all_fixtures.extend(ashes_fxs)

    # ── Step 3: Bilateral tours ───────────────────────────────────────────────
    bilateral_fxs = _schedule_bilateral(
        team_ids, id_to_name, venue_lookup, sched,
        start_date, end_date, density, years, series_ctr,
    )
    all_fixtures.extend(bilateral_fxs)

    # ── Step 4: Gap-filling T20s (busy only) ──────────────────────────────────
    if density == 'busy':
        gap_fxs = _fill_gaps(
            team_ids, id_to_name, venue_lookup, sched,
            start_date, end_date, series_ctr,
        )
        all_fixtures.extend(gap_fxs)

    # ── Step 5: Domestic league fixtures ────────────────────────────────────────
    if domestic_leagues and domestic_teams:
        start_year = start_date.year
        end_year   = start_date.year + years
        for comp_key in domestic_leagues:
            comp = DOMESTIC_COMPETITIONS.get(comp_key)
            if not comp:
                continue
            league_name = comp['league']
            # Filter domestic_teams to those belonging to this competition
            league_team_list = [
                t for t in domestic_teams
                if t.get('league') == league_name
            ]
            if len(league_team_list) < 2:
                continue
            # Use generate_domestic_fixtures (works with generic team IDs)
            # instead of competition_rules.generate_domestic_competition
            # (which requires real team names like "Mumbai Indians")
            dom_fxs = generate_domestic_fixtures(
                comp_key, league_team_list, start_year, end_year
            )
            all_fixtures.extend(dom_fxs)

    # ── Step 6: Filter out fixtures outside the generation window ─────────────
    all_fixtures = [
        fx for fx in all_fixtures
        if start_date.isoformat() <= fx.get('scheduled_date', '') < end_date.isoformat()
    ]

    # ── Step 7: Sort by date ──────────────────────────────────────────────────
    all_fixtures.sort(key=lambda x: x.get('scheduled_date', ''))

    return all_fixtures
