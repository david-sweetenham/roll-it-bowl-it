from datetime import date, timedelta
from itertools import combinations
import random


COUNTY_DIVISIONS = {
    "Division 1": [
        "Durham", "Essex", "Hampshire", "Nottinghamshire", "Somerset",
        "Surrey", "Sussex", "Warwickshire", "Worcestershire", "Yorkshire",
    ],
    "Division 2": [
        "Derbyshire", "Glamorgan", "Gloucestershire", "Kent",
        "Lancashire", "Leicestershire", "Middlesex", "Northamptonshire",
    ],
}

BLAST_GROUPS = {
    "North": [
        "Birmingham Bears", "Derbyshire", "Durham", "Lancashire", "Leicestershire",
        "Northamptonshire", "Nottinghamshire", "Worcestershire", "Yorkshire",
    ],
    "South": [
        "Essex", "Glamorgan", "Gloucestershire", "Hampshire", "Kent",
        "Middlesex", "Somerset", "Surrey", "Sussex",
    ],
}

ROYAL_LONDON_GROUPS = {
    "Group A": [
        "Durham", "Essex", "Gloucestershire", "Hampshire", "Kent",
        "Lancashire", "Northamptonshire", "Surrey", "Warwickshire",
    ],
    "Group B": [
        "Derbyshire", "Glamorgan", "Leicestershire", "Middlesex", "Nottinghamshire",
        "Somerset", "Sussex", "Worcestershire", "Yorkshire",
    ],
}

IPL_GROUPS = {
    "Group A": [
        "Mumbai Indians", "Kolkata Knight Riders", "Rajasthan Royals",
        "Delhi Capitals", "Lucknow Super Giants",
    ],
    "Group B": [
        "Chennai Super Kings", "Sunrisers Hyderabad", "Royal Challengers Bangalore",
        "Punjab Kings", "Gujarat Titans",
    ],
}

IPL_CROSS_PAIR = {
    "Mumbai Indians": "Chennai Super Kings",
    "Kolkata Knight Riders": "Sunrisers Hyderabad",
    "Rajasthan Royals": "Royal Challengers Bangalore",
    "Delhi Capitals": "Punjab Kings",
    "Lucknow Super Giants": "Gujarat Titans",
}

MARSH_CUP_REPEAT_PAIRS = [
    ("New South Wales", "Queensland"),
    ("Victoria", "Tasmania"),
    ("South Australia", "Western Australia"),
]

INTERNATIONAL_PRIORITY = [
    "Australia", "India", "England", "New Zealand", "South Africa",
    "Pakistan", "Sri Lanka", "West Indies", "Bangladesh", "Afghanistan",
    "Ireland", "Zimbabwe", "Scotland", "Netherlands", "Nepal", "Namibia",
    "UAE", "Oman", "Canada", "USA", "Papua New Guinea", "Uganda",
]

FORMAT_LABELS = {
    "Test": "First-class / multi-day cricket",
    "ODI": "50-over limited-overs cricket",
    "T20": "20-over cricket",
}

FORMAT_DESCRIBERS = {
    "international": {
        "Test": "International Test cricket with national sides playing the longest format.",
        "ODI": "International 50-over cricket between national teams.",
        "T20": "International T20 cricket between national teams.",
    },
    "domestic": {
        "Test": "Domestic first-class cricket played by counties, states, or provinces.",
        "ODI": "Domestic one-day cricket played by professional regional or county sides.",
        "T20": "Domestic franchise or county T20 cricket.",
    },
}

TIE_BREAKER_LABELS = {
    "points": "points",
    "nrr": "net run rate",
    "wins": "wins",
    "pct": "points percentage",
    "team_name": "team name",
}

STAGE_LABELS = {
    "league": "League Stage",
    "quarter": "Quarter-Finals",
    "semi": "Semi-Finals",
    "final": "Final",
    "qualifier": "Qualifier",
    "knockout": "Knockout",
    "challenger": "Challenger",
    "eliminator": "Eliminator",
    "super8": "Super 8",
}

POINTS_SYSTEM_DETAILS = {
    "limited_nrr": {
        "label": "Standard white-ball table",
        "summary": "A win is worth 2 points. A tie or no result gives 1 point to each side. A loss gives 0 points.",
    },
    "county": {
        "label": "County Championship points",
        "summary": "A win is worth 16 points. A draw or tie gives 8 points each, then first-innings batting and bowling bonus points are added.",
    },
    "shield": {
        "label": "Sheffield Shield points",
        "summary": "A win is worth 6 points. A draw gives 1 point each and a tie gives 3 points each, with capped batting and bowling bonus points added on top.",
    },
    "marsh_cup": {
        "label": "Marsh Cup points",
        "summary": "A win is worth 4 points. A tie or no result gives 2 points each, and a batting bonus point is added for reaching 300 in the first innings.",
    },
    "wtc": {
        "label": "World Test Championship table",
        "summary": "Teams earn 12 points for a win, 4 for a draw, and 6 for a tie. The table is ordered by points percentage rather than raw totals.",
    },
}

DRAW_METHOD_DETAILS = {
    "single_table": "No draw is needed. Every team starts in the same table.",
    "fixed_groups": "Groups or divisions are fixed in the rules, so teams begin the season in a pre-set section.",
    "seeded_groups": "Teams are seeded into pots and drawn into groups, with the host locked into Group A when applicable.",
}

COMPETITION_RULES = {
    "county_championship": {
        "name": "County Championship",
        "format": "Test",
        "season_start_month": 4,
        "season_end_month": 9,
        "default_gap_days": 6,
        "table_groups": COUNTY_DIVISIONS,
        "stage_order": ["league"],
        "points_system": "county",
        "tie_breakers": ["points", "wins", "team_name"],
        "draw_type": "fixed_groups",
        "format_scope": "domestic",
        "standings_grouping": "by_group",
        "generation_profile": "county_championship",
        "progression_profile": "league_only",
        "structure_summary": "Two divisions. Teams play home and away within their own division across the season.",
        "qualification_summary": "There is no knockout bracket. Final placings come from the divisional tables.",
        "knockout_summary": "No knockout path. The league tables decide the season.",
    },
    "t20_blast": {
        "name": "Vitality Blast",
        "format": "T20",
        "season_start_month": 5,
        "season_end_month": 9,
        "default_gap_days": 2,
        "table_groups": BLAST_GROUPS,
        "stage_order": ["league", "quarter", "semi", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "fixed_groups",
        "format_scope": "domestic",
        "standings_grouping": "by_group",
        "generation_profile": "t20_blast",
        "progression_profile": "t20_blast",
        "structure_summary": "North and South groups. Teams play a round-robin inside their group, with derby repeat fixtures adding the extra local matchups.",
        "qualification_summary": "The top four teams from each group qualify for the quarter-finals.",
        "knockout_summary": "Quarter-finals cross over by group placing: 1st North v 4th South, 1st South v 4th North, 2nd North v 3rd South, and 2nd South v 3rd North. The winners move to semi-finals, then the final.",
    },
    "royal_london_cup": {
        "name": "Royal London Cup",
        "format": "ODI",
        "season_start_month": 7,
        "season_end_month": 9,
        "default_gap_days": 2,
        "table_groups": ROYAL_LONDON_GROUPS,
        "stage_order": ["league", "quarter", "semi", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "fixed_groups",
        "format_scope": "domestic",
        "standings_grouping": "by_group",
        "generation_profile": "royal_london_cup",
        "progression_profile": "royal_london_cup",
        "structure_summary": "Two groups of counties. Each team plays the others in its group once.",
        "qualification_summary": "The group winners go straight to the semi-finals. The teams finishing 2nd and 3rd in each group enter the quarter-finals.",
        "knockout_summary": "Quarter-final 1 is 2nd in Group A v 3rd in Group B, and Quarter-final 2 is 2nd in Group B v 3rd in Group A. Each group winner then hosts the opposite quarter-final winner in the semi-finals, followed by the final.",
    },
    "sheffield_shield": {
        "name": "Sheffield Shield",
        "format": "Test",
        "season_start_month": 10,
        "season_end_month": 3,
        "default_gap_days": 7,
        "stage_order": ["league", "final"],
        "points_system": "shield",
        "tie_breakers": ["points", "team_name"],
        "draw_type": "single_table",
        "format_scope": "domestic",
        "standings_grouping": "combined",
        "generation_profile": "sheffield_shield",
        "progression_profile": "top_two_final",
        "structure_summary": "A single league table. Teams play home and away fixtures across the season.",
        "qualification_summary": "The top two teams on the table reach the final.",
        "knockout_summary": "There is a single final between 1st and 2nd.",
    },
    "marsh_cup": {
        "name": "Marsh One-Day Cup",
        "format": "ODI",
        "season_start_month": 9,
        "season_end_month": 2,
        "default_gap_days": 3,
        "stage_order": ["league", "final"],
        "points_system": "marsh_cup",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "single_table",
        "format_scope": "domestic",
        "standings_grouping": "combined",
        "generation_profile": "marsh_cup",
        "progression_profile": "top_two_final",
        "structure_summary": "A single league table. Teams meet once during the regular season.",
        "qualification_summary": "The top two teams qualify for the final.",
        "knockout_summary": "There is a single final between 1st and 2nd.",
    },
    "bbl": {
        "name": "Big Bash League",
        "format": "T20",
        "season_start_month": 12,
        "season_end_month": 2,
        "default_gap_days": 2,
        "stage_order": ["league", "qualifier", "knockout", "challenger", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "single_table",
        "format_scope": "domestic",
        "standings_grouping": "combined",
        "generation_profile": "bbl",
        "progression_profile": "bbl",
        "structure_summary": "A single league table. Teams play every opponent once, with a set of repeat rivalry fixtures added to complete the season.",
        "qualification_summary": "The top four teams qualify for the finals series.",
        "knockout_summary": "1st plays 2nd in the Qualifier and 3rd plays 4th in the Knockout. The Qualifier winner goes straight to the final. The Qualifier loser faces the Knockout winner in the Challenger, and that winner reaches the final.",
    },
    "ipl": {
        "name": "Indian Premier League",
        "format": "T20",
        "season_start_month": 3,
        "season_end_month": 5,
        "default_gap_days": 1,
        "table_groups": IPL_GROUPS,
        "stage_order": ["league", "qualifier", "eliminator", "challenger", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "fixed_groups",
        "format_scope": "domestic",
        "standings_grouping": "combined",
        "generation_profile": "ipl",
        "progression_profile": "ipl_psl",
        "structure_summary": "Two groups of five. Teams play home and away inside their own group, home and away against one paired rival from the other group, and single matches against the other cross-group sides.",
        "qualification_summary": "The top four teams on the overall table qualify, regardless of group.",
        "knockout_summary": "1st plays 2nd in Qualifier 1 and 3rd plays 4th in the Eliminator. The Eliminator winner meets the Qualifier 1 loser in Qualifier 2, and that winner meets the Qualifier 1 winner in the final.",
    },
    "cpl": {
        "name": "Caribbean Premier League",
        "format": "T20",
        "season_start_month": 8,
        "season_end_month": 9,
        "default_gap_days": 2,
        "stage_order": ["league", "qualifier", "eliminator", "challenger", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "single_table",
        "format_scope": "domestic",
        "standings_grouping": "combined",
        "generation_profile": "cpl",
        "progression_profile": "ipl_psl",
        "structure_summary": "A single league table. Teams play home-and-away style round-robin fixtures.",
        "qualification_summary": "The top four teams qualify for the playoffs.",
        "knockout_summary": "1st plays 2nd in Qualifier 1 and 3rd plays 4th in the Eliminator. The Eliminator winner then faces the Qualifier 1 loser in Qualifier 2, and the winner of that match reaches the final.",
    },
    "psl": {
        "name": "Pakistan Super League",
        "format": "T20",
        "season_start_month": 2,
        "season_end_month": 3,
        "default_gap_days": 2,
        "stage_order": ["league", "qualifier", "eliminator", "challenger", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "single_table",
        "format_scope": "domestic",
        "standings_grouping": "combined",
        "generation_profile": "psl",
        "progression_profile": "ipl_psl",
        "structure_summary": "A single league table. Teams play home-and-away style round-robin fixtures.",
        "qualification_summary": "The top four teams qualify for the playoffs.",
        "knockout_summary": "1st plays 2nd in the Qualifier and 3rd plays 4th in the Eliminator. The Eliminator winner then faces the Qualifier loser in Qualifier 2, and the winner of that match reaches the final.",
    },
    "icc_champions_trophy": {
        "name": "ICC Champions Trophy",
        "format": "ODI",
        "season_start_month": 2,
        "season_end_month": 3,
        "default_gap_days": 1,
        "stage_order": ["league", "semi", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "seeded_groups",
        "format_scope": "international",
        "standings_grouping": "by_group",
        "generation_profile": "icc_champions_trophy",
        "progression_profile": "icc_champions_trophy",
        "structure_summary": "Eight teams are split into two seeded groups of four, and each team plays the others in its group once.",
        "qualification_summary": "The top two teams in each group qualify for the semi-finals.",
        "knockout_summary": "Semi-Final 1 is Group A 1st v Group B 2nd and Semi-Final 2 is Group B 1st v Group A 2nd, followed by the final.",
    },
    "icc_cricket_world_cup": {
        "name": "ICC Men's Cricket World Cup",
        "format": "ODI",
        "season_start_month": 10,
        "season_end_month": 11,
        "default_gap_days": 1,
        "stage_order": ["league", "semi", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "single_table",
        "format_scope": "international",
        "standings_grouping": "combined",
        "generation_profile": "icc_cricket_world_cup",
        "progression_profile": "icc_cricket_world_cup",
        "structure_summary": "A single 10-team league stage. Every team plays every other team once.",
        "qualification_summary": "The top four teams on the league table reach the semi-finals.",
        "knockout_summary": "Semi-Final 1 is 1st v 4th and Semi-Final 2 is 2nd v 3rd, followed by the final.",
    },
    "icc_t20_world_cup": {
        "name": "ICC Men's T20 World Cup",
        "format": "T20",
        "season_start_month": 6,
        "season_end_month": 7,
        "default_gap_days": 1,
        "stage_order": ["league", "super8", "semi", "final"],
        "points_system": "limited_nrr",
        "tie_breakers": ["points", "nrr", "wins", "team_name"],
        "draw_type": "seeded_groups",
        "format_scope": "international",
        "standings_grouping": "by_group",
        "generation_profile": "icc_t20_world_cup",
        "progression_profile": "icc_t20_world_cup",
        "structure_summary": "Twenty teams are drawn into four seeded first-round groups of five. The top two from each group advance to the Super 8 stage.",
        "qualification_summary": "After the first round, the top two teams from each group qualify for the Super 8. The top two teams in each Super 8 group then qualify for the semi-finals.",
        "knockout_summary": "Super 8 Group 1 contains A1, B1, C2, and D2, while Super 8 Group 2 contains A2, B2, C1, and D1. Semi-Final 1 is Super 8 Group 1 winner v Super 8 Group 2 runner-up, and Semi-Final 2 is Super 8 Group 2 winner v Super 8 Group 1 runner-up, followed by the final.",
    },
    "icc_world_test_championship": {
        "name": "ICC World Test Championship",
        "format": "Test",
        "season_start_month": 6,
        "season_end_month": 6,
        "default_gap_days": 1,
        "stage_order": ["league", "final"],
        "points_system": "wtc",
        "tie_breakers": ["pct", "points", "team_name"],
        "draw_type": "single_table",
        "format_scope": "international",
        "standings_grouping": "combined",
        "generation_profile": "icc_world_test_championship",
        "progression_profile": "top_two_final",
        "structure_summary": "A rolling championship table covering all qualifying non-ICC Test fixtures in the cycle.",
        "qualification_summary": "The top two teams by points percentage qualify for the final.",
        "knockout_summary": "There is a single final between the top two teams in the cycle table.",
    },
}


ICC_EVENTS = {
    2025: {"key": "icc_champions_trophy", "host": "Pakistan", "participants": 8},
    2026: {"key": "icc_t20_world_cup", "host": "India", "participants": 20},
    2027: {"key": "icc_cricket_world_cup", "host": "South Africa", "participants": 10},
    2028: {"key": "icc_t20_world_cup", "host": "England", "participants": 20},
    2029: {"key": "icc_champions_trophy", "host": "India", "participants": 8},
    2030: {"key": "icc_t20_world_cup", "host": "Australia", "participants": 20},
    2031: {"key": "icc_cricket_world_cup", "host": "India", "participants": 10},
    2032: {"key": "icc_t20_world_cup", "host": "South Africa", "participants": 20},
    2033: {"key": "icc_champions_trophy", "host": "England", "participants": 8},
    2034: {"key": "icc_t20_world_cup", "host": "New Zealand", "participants": 20},
    2035: {"key": "icc_cricket_world_cup", "host": "England", "participants": 10},
    2036: {"key": "icc_t20_world_cup", "host": "Pakistan", "participants": 20},
    2037: {"key": "icc_champions_trophy", "host": "South Africa", "participants": 8},
}


def get_rule(key):
    return COMPETITION_RULES.get(key)


def get_competition_matrix():
    return COMPETITION_RULES


def _human_join(parts):
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def _table_group_summary(rule):
    groups = rule.get("table_groups") or {}
    if not groups:
        return "Single table"
    sizes = sorted({len(v) for v in groups.values()})
    group_count = len(groups)
    if len(sizes) == 1:
        team_text = f"{sizes[0]} team{'s' if sizes[0] != 1 else ''}"
    else:
        team_text = "different-sized groups"
    names = list(groups.keys())
    if group_count <= 4:
        return f"{group_count} groups/divisions ({team_text}): {_human_join(names)}."
    return f"{group_count} groups/divisions ({team_text})."


def _stage_path(rule):
    labels = [STAGE_LABELS.get(stage, stage.replace('_', ' ').title()) for stage in rule.get("stage_order", [])]
    if not labels:
        return "League table only"
    return " -> ".join(labels)


def _tie_breaker_summary(rule):
    breakers = [TIE_BREAKER_LABELS.get(b, b.replace('_', ' ')) for b in rule.get("tie_breakers", [])]
    if not breakers:
        return "No tie-breakers defined."
    if len(breakers) == 1:
        return f"Teams are separated by {breakers[0]}."
    return f"Teams are separated by {_human_join(breakers)} in that order."


def get_rule_explainer(key):
    rule = get_rule(key)
    if not rule:
        return None
    format_key = rule.get("format")
    scope_key = rule.get("format_scope", "international")
    points_key = rule.get("points_system")
    draw_key = rule.get("draw_type") or "single_table"
    points_info = POINTS_SYSTEM_DETAILS.get(points_key, {})
    stages = [STAGE_LABELS.get(stage, stage.replace('_', ' ').title()) for stage in rule.get("stage_order", [])]
    return {
        "key": key,
        "name": rule.get("name", key),
        "format": format_key,
        "format_label": FORMAT_LABELS.get(format_key, format_key or ""),
        "format_scope": scope_key,
        "format_description": FORMAT_DESCRIBERS.get(scope_key, {}).get(format_key, FORMAT_LABELS.get(format_key, format_key or "")),
        "structure": rule.get("structure_summary") or _table_group_summary(rule),
        "group_summary": _table_group_summary(rule),
        "stage_path": _stage_path(rule),
        "stages": stages,
        "points_system_key": points_key,
        "points_system_label": points_info.get("label", points_key or ""),
        "points_system": points_info.get("summary", "Points system not described."),
        "tie_breakers": _tie_breaker_summary(rule),
        "qualification": rule.get("qualification_summary") or "Qualification rules are not defined.",
        "knockout_path": rule.get("knockout_summary") or "No knockout path is defined.",
        "draw_type": draw_key,
        "draw_method": DRAW_METHOD_DETAILS.get(draw_key, "Draw method not described."),
        "standings_grouping": rule.get("standings_grouping", "combined"),
        "generation_profile": rule.get("generation_profile", key),
        "progression_profile": rule.get("progression_profile", key),
        "season_window": {
            "start_month": rule.get("season_start_month"),
            "end_month": rule.get("season_end_month"),
            "gap_days": rule.get("default_gap_days"),
        },
    }


def build_fixture(
    competition_key,
    season_label,
    series_key,
    fixture_id,
    team1_id,
    team2_id,
    scheduled_date,
    venue_id,
    stage,
    round_label,
    order_index,
    format_,
    competition_name=None,
    group_name=None,
    is_icc_event=False,
    icc_event_name=None,
):
    return {
        "fixture_id": fixture_id,
        "series_name": season_label,
        "series_key": series_key,
        "team1_id": team1_id,
        "team2_id": team2_id,
        "scheduled_date": scheduled_date,
        "format": format_,
        "venue_id": venue_id,
        "is_icc_event": is_icc_event,
        "icc_event_name": icc_event_name,
        "match_number_in_series": order_index + 1,
        "series_length": 1,
        "is_home_for_team1": True,
        "tour_template": f"competition_{competition_key}",
        "competition_key": competition_key,
        "competition_name": competition_name or season_label,
        "competition_stage": stage,
        "competition_group": group_name,
        "competition_round": round_label,
        "competition_order": order_index,
        "fixture_type": stage,
        "domestic_competition": None if is_icc_event else competition_key,
    }


def _season_bounds(year, start_month, end_month):
    start = date(year, start_month, 1)
    end_year = year if end_month >= start_month else year + 1
    end = date(end_year, end_month, 28)
    return start, end


def _series_key(comp_key, year):
    return f"{comp_key}_{year}"


def _label(rule, year):
    return f"{rule['name']} {year}"


def _team_lookup(teams):
    return {t["name"]: t for t in teams}


def _preferred_participants(team_ids, team_names, count):
    named = {tid: team_names.get(tid, f"Team {tid}") for tid in team_ids}
    preferred = []
    for name in INTERNATIONAL_PRIORITY:
        for tid, team_name in named.items():
            if team_name == name and tid not in preferred:
                preferred.append(tid)
    for tid in sorted(team_ids, key=lambda x: named.get(x, "")):
        if tid not in preferred:
            preferred.append(tid)
    return preferred[: min(len(preferred), count)]


def _draw_rng(*parts):
    sys_rng = random.SystemRandom()
    token = "|".join(str(p) for p in parts)
    return random.Random(f"{token}|{sys_rng.randrange(1 << 62)}")


def _draw_seeded_groups(participants, team_names, group_names, host_name=None, host_group=None, seed_token=""):
    groups, _, _ = _draw_seeded_groups_full(participants, team_names, group_names, host_name, host_group, seed_token)
    return groups


def _draw_seeded_groups_full(participants, team_names, group_names, host_name=None, host_group=None, seed_token=""):
    """Like _draw_seeded_groups but also returns pot metadata and step-by-step draw record.

    Returns (groups, pots_info, steps) where:
      groups    — {group_name: [team_id, ...]}
      pots_info — [{"number": N, "teams": [{"team_id", "team_name"}, ...]}, ...]
      steps     — [{"type": "host_placed"|"pot_drawn", "pot": N|None, "team_id", "team_name", "group"}, ...]
    """
    if not participants or not group_names:
        return {name: [] for name in group_names}, [], []

    rng = _draw_rng("draw", seed_token, len(participants), len(group_names))
    groups = {name: [] for name in group_names}
    group_count = len(group_names)
    pots_raw = [list(participants[i:i + group_count]) for i in range(0, len(participants), group_count)]
    steps = []

    # ── Build pot membership BEFORE host removal so pot labels are stable ──────
    # The original _draw_seeded_groups removes host from pot in-place before
    # shuffling, so we replicate: map each team to its natural pot number first.
    tid_to_pot = {}
    for pot_idx, pot in enumerate(pots_raw):
        for tid in pot:
            tid_to_pot[tid] = pot_idx + 1

    host_id = None
    if host_name:
        for tid in participants:
            if team_names.get(tid) == host_name:
                host_id = tid
                break
    if host_id and host_group in groups:
        groups[host_group].append(host_id)
        steps.append({
            "type": "host_placed",
            "pot": tid_to_pot.get(host_id),
            "team_id": host_id,
            "team_name": team_names.get(host_id, "?"),
            "group": host_group,
        })
        for pot in pots_raw:
            if host_id in pot:
                pot.remove(host_id)
                break

    pots_info = []
    for pot_idx, pot in enumerate(pots_raw):
        pot_copy = list(pot)
        rng.shuffle(pot_copy)
        # Build pot display list (original order before shuffle for clarity)
        pot_display = [{"team_id": tid, "team_name": team_names.get(tid, "?")} for tid in pot_copy]
        pots_info.append({"number": pot_idx + 1, "teams": pot_display})

        order = list(group_names)
        rng.shuffle(order)
        for tid in pot_copy:
            choices = [g for g in order if len(groups[g]) < len(pots_raw)]
            target = min(choices or group_names, key=lambda g: len(groups[g]))
            groups[target].append(tid)
            steps.append({
                "type": "pot_drawn",
                "pot": pot_idx + 1,
                "team_id": tid,
                "team_name": team_names.get(tid, "?"),
                "group": target,
            })

    return groups, pots_info, steps


def compute_icc_draw_outcomes(team_ids, team_names, start_date_str, end_date_str, team_colours=None):
    """Return a list of draw outcome dicts for all seeded ICC events in the date range.

    Each dict:
      {
        "competition_key":  str,
        "competition_name": str,
        "season_key":       str,   # e.g. "icc_champions_trophy_2025"
        "year":             int,
        "draw_type":        str,   # "seeded_groups"
        "host_name":        str | None,
        "host_group":       str | None,
        "group_names":      [str, ...],
        "pots":             [{number, teams:[{team_id, team_name, badge_colour}]}, ...],
        "groups":           {group_name: [{team_id, team_name, pot, is_host, badge_colour}]},
        "steps":            [{type, pot, team_id, team_name, group}, ...],
      }
    """
    from datetime import date as _date

    colours = team_colours or {}

    try:
        start_date = _date.fromisoformat(start_date_str[:10])
        end_date   = _date.fromisoformat(end_date_str[:10])
    except Exception:
        return []

    outcomes = []

    for year, event in ICC_EVENTS.items():
        rule = get_rule(event["key"])
        if not rule:
            continue
        # Only events with a seeded draw
        if rule.get("draw_type") != "seeded_groups":
            continue
        event_start, _ = _season_bounds(year, rule["season_start_month"], rule["season_end_month"])
        if event_start < start_date or event_start >= end_date:
            continue

        participants = _preferred_participants(team_ids, team_names, event["participants"])
        host_name  = event.get("host")
        host_group = "Group A"

        group_names = (
            ["Group A", "Group B"]
            if event["key"] == "icc_champions_trophy"
            else ["Group A", "Group B", "Group C", "Group D"]
        )
        seed_token = f"{event['key']}:{year}"
        groups, pots_info, steps = _draw_seeded_groups_full(
            participants, team_names, group_names,
            host_name=host_name, host_group=host_group,
            seed_token=seed_token,
        )

        # Annotate pots with badge_colour
        for pot in pots_info:
            for t in pot["teams"]:
                t["badge_colour"] = colours.get(t["team_id"], "#888888")

        # Build annotated groups
        tid_to_pot_num = {}
        for pot in pots_info:
            for t in pot["teams"]:
                tid_to_pot_num[t["team_id"]] = pot["number"]
        # host's pot (already removed from pots_info; look it up from steps)
        for s in steps:
            if s["type"] == "host_placed":
                tid_to_pot_num[s["team_id"]] = s["pot"]

        annotated_groups = {}
        host_id = None
        for t in participants:
            if team_names.get(t) == host_name:
                host_id = t
                break
        for gname, tids in groups.items():
            annotated_groups[gname] = [
                {
                    "team_id":      tid,
                    "team_name":    team_names.get(tid, "?"),
                    "pot":          tid_to_pot_num.get(tid),
                    "is_host":      tid == host_id,
                    "badge_colour": colours.get(tid, "#888888"),
                }
                for tid in tids
            ]

        # Annotate steps with badge_colour
        for s in steps:
            s["badge_colour"] = colours.get(s["team_id"], "#888888")

        season_key = _series_key(event["key"], year)
        outcomes.append({
            "competition_key":  event["key"],
            "competition_name": f"{rule['name']} {year}",
            "season_key":       season_key,
            "year":             year,
            "draw_type":        "seeded_groups",
            "host_name":        host_name,
            "host_group":       host_group,
            "group_names":      group_names,
            "pots":             pots_info,
            "groups":           annotated_groups,
            "steps":            steps,
        })

    return outcomes


def _match_date(start, idx, gap_days):
    return (start + timedelta(days=idx * gap_days)).isoformat()


def _round_robin_pairs(team_ids):
    return list(combinations(team_ids, 2))


def _append_home_away(pairs):
    out = []
    for a, b in pairs:
        out.append((a, b))
        out.append((b, a))
    return out


def generate_domestic_competition(comp_key, teams, start_year, end_year):
    rule = get_rule(comp_key)
    if not rule:
        return []
    by_name = _team_lookup(teams)
    fixtures = []
    fx_index = 0

    def add_fixture(year, stage, round_label, order_index, team1_name, team2_name, match_date, group_name=None):
        nonlocal fx_index
        t1 = by_name.get(team1_name)
        t2 = by_name.get(team2_name)
        if not t1 or not t2:
            return
        series_key = _series_key(comp_key, year)
        season_label = _label(rule, year)
        fixtures.append(build_fixture(
            comp_key,
            season_label,
            series_key,
            f"{series_key}_{stage}_{fx_index + 1}",
            t1["team_id"],
            t2["team_id"],
            match_date,
            t1.get("home_venue_id"),
            stage,
            round_label,
            fx_index,
            rule["format"],
            competition_name=rule["name"],
            group_name=group_name,
        ))
        fx_index += 1

    for year in range(start_year, end_year):
        start, _ = _season_bounds(year, rule["season_start_month"], rule["season_end_month"])
        gap = rule["default_gap_days"]

        if comp_key == "county_championship":
            idx = 0
            for group_name, team_names in COUNTY_DIVISIONS.items():
                group_pairs = _append_home_away(_round_robin_pairs([by_name[n]["team_id"] for n in team_names if n in by_name]))
                for a, b in group_pairs:
                    t1 = next(t["name"] for t in teams if t["team_id"] == a)
                    t2 = next(t["name"] for t in teams if t["team_id"] == b)
                    add_fixture(year, "league", group_name, idx, t1, t2, _match_date(start, idx, gap), group_name)
                    idx += 1
        elif comp_key == "t20_blast":
            idx = 0
            rivals = [
                ("Lancashire", "Yorkshire"),
                ("Nottinghamshire", "Derbyshire"),
                ("Durham", "Yorkshire"),
                ("Leicestershire", "Northamptonshire"),
                ("Birmingham Bears", "Worcestershire"),
                ("Surrey", "Middlesex"),
                ("Hampshire", "Sussex"),
                ("Somerset", "Glamorgan"),
                ("Kent", "Essex"),
            ]
            # Map county seed name for Warwickshire
            aliases = {"Birmingham Bears": "Warwickshire"}
            for group_name, group in BLAST_GROUPS.items():
                seed_names = [aliases.get(n, n) for n in group]
                pairs = _round_robin_pairs([by_name[n]["team_id"] for n in seed_names if n in by_name])
                for a, b in pairs:
                    t1 = next(t["name"] for t in teams if t["team_id"] == a)
                    t2 = next(t["name"] for t in teams if t["team_id"] == b)
                    add_fixture(year, "league", "Group Stage", idx, t1, t2, _match_date(start, idx, gap), group_name)
                    idx += 1
                for raw_a, raw_b in rivals:
                    a_name = aliases.get(raw_a, raw_a)
                    b_name = aliases.get(raw_b, raw_b)
                    if a_name in seed_names and b_name in seed_names:
                        add_fixture(year, "league", "Group Stage", idx, a_name, b_name, _match_date(start, idx, gap), group_name)
                        idx += 1
                        add_fixture(year, "league", "Group Stage", idx, b_name, a_name, _match_date(start, idx, gap), group_name)
                        idx += 1
        elif comp_key == "royal_london_cup":
            idx = 0
            for group_name, group in ROYAL_LONDON_GROUPS.items():
                pairs = _round_robin_pairs([by_name[n]["team_id"] for n in group if n in by_name])
                for a, b in pairs:
                    t1 = next(t["name"] for t in teams if t["team_id"] == a)
                    t2 = next(t["name"] for t in teams if t["team_id"] == b)
                    add_fixture(year, "league", "Group Stage", idx, t1, t2, _match_date(start, idx, gap), group_name)
                    idx += 1
        elif comp_key in {"sheffield_shield", "marsh_cup", "cpl", "psl"}:
            idx = 0
            pairs = _append_home_away(_round_robin_pairs([t["team_id"] for t in teams]))
            if comp_key == "marsh_cup":
                pairs = _round_robin_pairs([t["team_id"] for t in teams])
            for a, b in pairs:
                t1 = next(t["name"] for t in teams if t["team_id"] == a)
                t2 = next(t["name"] for t in teams if t["team_id"] == b)
                add_fixture(year, "league", "League Stage", idx, t1, t2, _match_date(start, idx, gap))
                idx += 1
            if comp_key == "marsh_cup":
                names = {t["name"] for t in teams}
                for a_name, b_name in MARSH_CUP_REPEAT_PAIRS:
                    if a_name in names and b_name in names:
                        add_fixture(year, "league", "League Stage", idx, a_name, b_name, _match_date(start, idx, gap))
                        idx += 1
                        add_fixture(year, "league", "League Stage", idx, b_name, a_name, _match_date(start, idx, gap))
                        idx += 1
        elif comp_key == "bbl":
            idx = 0
            names = [t["name"] for t in teams]
            pairs = _round_robin_pairs([t["team_id"] for t in teams])
            for a, b in pairs:
                t1 = next(t["name"] for t in teams if t["team_id"] == a)
                t2 = next(t["name"] for t in teams if t["team_id"] == b)
                add_fixture(year, "league", "League Stage", idx, t1, t2, _match_date(start, idx, gap))
                idx += 1
            repeat_pairs = [
                ("Sydney Sixers", "Sydney Thunder"),
                ("Melbourne Stars", "Melbourne Renegades"),
                ("Brisbane Heat", "Perth Scorchers"),
                ("Hobart Hurricanes", "Adelaide Strikers"),
            ]
            for a_name, b_name in repeat_pairs:
                if a_name in names and b_name in names:
                    add_fixture(year, "league", "League Stage", idx, a_name, b_name, _match_date(start, idx, gap))
                    idx += 1
                    add_fixture(year, "league", "League Stage", idx, b_name, a_name, _match_date(start, idx, gap))
                    idx += 1
        elif comp_key == "ipl":
            idx = 0
            for group_name, group in IPL_GROUPS.items():
                ids = [by_name[n]["team_id"] for n in group if n in by_name]
                for a, b in _append_home_away(_round_robin_pairs(ids)):
                    t1 = next(t["name"] for t in teams if t["team_id"] == a)
                    t2 = next(t["name"] for t in teams if t["team_id"] == b)
                    add_fixture(year, "league", "League Stage", idx, t1, t2, _match_date(start, idx, gap), group_name)
                    idx += 1
            for a_name, b_name in IPL_CROSS_PAIR.items():
                if a_name in by_name and b_name in by_name:
                    add_fixture(year, "league", "League Stage", idx, a_name, b_name, _match_date(start, idx, gap))
                    idx += 1
                    add_fixture(year, "league", "League Stage", idx, b_name, a_name, _match_date(start, idx, gap))
                    idx += 1
            for a_name, a_team in by_name.items():
                own_group = next((g for g, names in IPL_GROUPS.items() if a_name in names), None)
                if not own_group:
                    continue
                for other_group_name, other_names in IPL_GROUPS.items():
                    if other_group_name == own_group:
                        continue
                    cross_pair = IPL_CROSS_PAIR.get(a_name)
                    for b_name in other_names:
                        if b_name == cross_pair or b_name not in by_name:
                            continue
                        if a_name < b_name:
                            add_fixture(year, "league", "League Stage", idx, a_name, b_name, _match_date(start, idx, gap))
                            idx += 1
        else:
            idx = 0
            pairs = _append_home_away(_round_robin_pairs([t["team_id"] for t in teams]))
            for a, b in pairs:
                t1 = next(t["name"] for t in teams if t["team_id"] == a)
                t2 = next(t["name"] for t in teams if t["team_id"] == b)
                add_fixture(year, "league", "League Stage", idx, t1, t2, _match_date(start, idx, gap))
                idx += 1

    return fixtures


def generate_icc_competitions(team_ids, team_names, venue_lookup, start_date, end_date):
    fixtures = []
    id_to_name = {tid: team_names.get(tid, f"Team {tid}") for tid in team_ids}
    fx_index = 0

    def host_venue(host_name, idx):
        venues = venue_lookup.get(host_name, []) or venue_lookup.get(host_name.lower(), [])
        if venues:
            return venues[idx % len(venues)]
        for name, ids in venue_lookup.items():
            if ids:
                return ids[0]
        return None

    for year, event in ICC_EVENTS.items():
        rule = get_rule(event["key"])
        if not rule:
            continue
        event_start, _ = _season_bounds(year, rule["season_start_month"], rule["season_end_month"])
        if event_start < start_date or event_start >= end_date:
            continue
        participants = _preferred_participants(team_ids, team_names, event["participants"])
        series_key = _series_key(event["key"], year)
        season_label = _label(rule, year)
        gap = rule["default_gap_days"]

        def add(team1_id, team2_id, idx, stage, round_label, group_name=None):
            nonlocal fx_index
            fixtures.append(build_fixture(
                event["key"],
                season_label,
                series_key,
                f"{series_key}_{stage}_{fx_index + 1}",
                team1_id,
                team2_id,
                _match_date(event_start, idx, gap),
                host_venue(event["host"], idx),
                stage,
                round_label,
                fx_index,
                rule["format"],
                competition_name=rule["name"],
                group_name=group_name,
                is_icc_event=True,
                icc_event_name=season_label,
            ))
            fx_index += 1

        if event["key"] == "icc_champions_trophy":
            groups = _draw_seeded_groups(
                participants,
                team_names,
                ["Group A", "Group B"],
                host_name=event.get("host"),
                host_group="Group A",
                seed_token=f"{event['key']}:{year}",
            )
            idx = 0
            for group_name, ids in groups.items():
                for a, b in _round_robin_pairs(ids):
                    add(a, b, idx, "league", "Group Stage", group_name)
                    idx += 1
        elif event["key"] == "icc_cricket_world_cup":
            idx = 0
            for a, b in _round_robin_pairs(participants[:10]):
                add(a, b, idx, "league", "League Stage")
                idx += 1
        elif event["key"] == "icc_t20_world_cup":
            groups = _draw_seeded_groups(
                participants,
                team_names,
                ["Group A", "Group B", "Group C", "Group D"],
                host_name=event.get("host"),
                host_group="Group A",
                seed_token=f"{event['key']}:{year}",
            )
            idx = 0
            for group_name, ids in groups.items():
                for a, b in _round_robin_pairs(ids):
                    add(a, b, idx, "league", "First Round", group_name)
                    idx += 1

    return fixtures
