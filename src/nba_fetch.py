"""Fetch playoff series scores from NBA.com / stats.nba.com (with CSV fallback)."""

import json
import os
import re
import urllib.error
import urllib.request

import pandas as pd

from dashboard_model import load_all_round_results, series_list_to_results_by_round

NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/playoffs",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

# 2025-26 playoffs on stats.nba.com
DEFAULT_SEASON = "2025"
SEASON_ID = "22025"

TRICODE_MAP = {
    "ATL": "Atlanta Hawks",
    "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "LA Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}


def _get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or NBA_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _allowed_teams(teams_path="data/teams_2026.csv"):
    return set(pd.read_csv(teams_path)["team"])


def _tri_map(teams_path="data/teams_2026.csv"):
    allowed = _allowed_teams(teams_path)
    return {tri: name for tri, name in TRICODE_MAP.items() if name in allowed}


def _resolve_team(raw, tri_map):
    if not raw:
        return None
    if isinstance(raw, dict):
        tri = raw.get("teamTricode") or raw.get("triCode")
        if tri and tri in tri_map:
            return tri_map[tri]
        name = raw.get("teamName") or raw.get("name")
        if name in tri_map.values():
            return name
        return None
    if raw in tri_map.values():
        return raw
    return None


def fetch_from_cdn_playoff_branch(season=DEFAULT_SEASON, teams_path="data/teams_2026.csv"):
    url = f"https://cdn.nba.com/static/json/liveData/playoff/branch/branch_00_{season}.json"
    try:
        data = _get_json(url, headers={"User-Agent": NBA_HEADERS["User-Agent"], "Referer": "https://www.nba.com/"})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, f"cdn.nba.com failed: {exc}"

    allowed = _allowed_teams(teams_path)
    tri_map = _tri_map(teams_path)
    series_rows = []

    rounds = data.get("bracket", data.get("playoffBracket", data))
    if isinstance(rounds, dict):
        rounds = rounds.get("rounds", rounds.get("series", []))
    if not isinstance(rounds, list):
        return None, "cdn.nba.com: unexpected JSON shape"

    for rnd_block in rounds:
        rnd_num = int(rnd_block.get("roundNum", rnd_block.get("round", 1)))
        for s in rnd_block.get("series", rnd_block.get("matchups", [])):
            if "awayTeam" in s and "homeTeam" in s:
                ta = _resolve_team(s["awayTeam"], tri_map)
                tb = _resolve_team(s["homeTeam"], tri_map)
                wa = int(s["awayTeam"].get("wins", 0) or 0)
                wb = int(s["homeTeam"].get("wins", 0) or 0)
            elif "highSeed" in s:
                ta = _resolve_team(s["highSeed"], tri_map)
                tb = _resolve_team(s["lowSeed"], tri_map)
                wa = int(s["highSeed"].get("wins", 0) or 0)
                wb = int(s["lowSeed"].get("wins", 0) or 0)
            else:
                continue

            if ta not in allowed or tb not in allowed:
                continue
            if wa > 0 or wb > 0:
                series_rows.append(
                    {"round": rnd_num, "team_a": ta, "team_b": tb, "wins_a": wa, "wins_b": wb}
                )

    if not series_rows:
        return None, "cdn.nba.com: no series with scores"
    return series_list_to_results_by_round(series_rows), f"nba.com CDN ({len(series_rows)} series)"


def fetch_from_stats_playoff_bracket(teams_path="data/teams_2026.csv"):
    url = (
        "https://stats.nba.com/stats/playoffBracket?"
        f"LeagueID=00&Season={DEFAULT_SEASON}&Stage=1"
    )
    try:
        data = _get_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return None, f"stats.nba.com failed: {exc}"

    sets = data.get("resultSets", [])
    if not sets:
        return None, "stats.nba.com: empty response"

    allowed = _allowed_teams(teams_path)
    tri_map = _tri_map(teams_path)
    series_rows = []

    for rs in sets:
        headers = rs.get("headers", [])
        rows = rs.get("rowSet", [])
        if not headers or not rows:
            continue
        idx = {h: i for i, h in enumerate(headers)}
        for row in rows:
            tri_a = row[idx["HOME_TEAM"]] if "HOME_TEAM" in idx else None
            tri_b = row[idx["VISITOR_TEAM"]] if "VISITOR_TEAM" in idx else None
            if tri_a in tri_map:
                ta, tb = tri_map[tri_a], tri_map.get(tri_b)
                wa = row[idx.get("HOME_WINS", idx.get("HOME_SERIES_WINS", -1))]
                wb = row[idx.get("VISITOR_WINS", idx.get("VISITOR_SERIES_WINS", -1))]
            else:
                continue
            rnd = row[idx.get("ROUND", 1)] if "ROUND" in idx else 1
            if ta and tb and ta in allowed and tb in allowed and (wa or wb):
                series_rows.append(
                    {
                        "round": int(rnd),
                        "team_a": ta,
                        "team_b": tb,
                        "wins_a": int(wa),
                        "wins_b": int(wb),
                    }
                )

    if not series_rows:
        return None, "stats.nba.com: could not parse bracket rows"
    return series_list_to_results_by_round(series_rows), f"stats.nba.com ({len(series_rows)} series)"


def merge_results_local_wins(local, fetched):
    """Keep local CSV pairings/scores; only add NBA series not already in local data."""
    merged = {}
    for rnd in range(1, 5):
        local_df = local.get(rnd, pd.DataFrame())
        fetch_df = fetched.get(rnd, pd.DataFrame()) if fetched else pd.DataFrame()
        if local_df.empty and fetch_df.empty:
            merged[rnd] = pd.DataFrame(columns=["team_a", "team_b", "wins_a", "wins_b"])
            continue
        if fetch_df.empty:
            merged[rnd] = local_df.copy()
            continue

        rows = [row.to_dict() for _, row in local_df.iterrows()]
        seen = {frozenset({r["team_a"], r["team_b"]}) for r in rows}
        for _, row in fetch_df.iterrows():
            key = frozenset({row["team_a"], row["team_b"]})
            if key not in seen:
                rows.append(row.to_dict())
                seen.add(key)
        merged[rnd] = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["team_a", "team_b", "wins_a", "wins_b"]
        )
    return merged


def test_nba_fetch():
    """Return status dict for /api/nba-status (does not change dashboard data)."""
    out = {"cdn": None, "stats": None, "working": False}
    fetched, note = fetch_from_cdn_playoff_branch()
    out["cdn"] = note
    if fetched:
        out["working"] = True
        out["sample_round1"] = fetched.get(1).to_dict(orient="records") if 1 in fetched else []
        return out
    fetched, note = fetch_from_stats_playoff_bracket()
    out["stats"] = note
    if fetched:
        out["working"] = True
        out["sample_round1"] = fetched.get(1).to_dict(orient="records") if 1 in fetched else []
    return out


def fetch_actual_results(source="csv", teams_path="data/teams_2026.csv"):
    """
    Load playoff results. Default ``csv`` = your data/round*_results.csv (reliable).
    ``auto`` / ``nba`` try NBA.com then fall back to CSV without overwriting local scores.
    """
    local = load_all_round_results()

    if source == "csv":
        return local, "local CSV files (data/round*_results.csv)"

    nba_notes = []
    if source in ("auto", "nba"):
        fetched, n1 = fetch_from_cdn_playoff_branch(teams_path=teams_path)
        if fetched:
            return merge_results_local_wins(local, fetched), n1
        nba_notes.append(n1)

        fetched, n2 = fetch_from_stats_playoff_bracket(teams_path=teams_path)
        if fetched:
            return merge_results_local_wins(local, fetched), n2
        nba_notes.append(n2)

        note = "NBA.com fetch failed — using local CSV. " + " | ".join(nba_notes)
        return local, note

    return local, "local CSV files"
