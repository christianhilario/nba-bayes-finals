"""Build dashboard JSON from playoff results (actual or user scenario)."""

import hashlib
import json
import os
from datetime import date

import pandas as pd

# Tuned for interactive dashboard (main.py keeps higher defaults)
DASHBOARD_N_SAMPLES = 6000
DASHBOARD_TITLE_SIMS = 1000
DASHBOARD_MATCHUP_SIMS = 500

_PAYLOAD_CACHE = {}
_MODEL_CACHE = {}
_CACHE_MAX = 32

from bracket import (
    build_conference_bracket,
    build_finals_matchup,
    infer_champion_from_results,
)
from load_data import load_teams
from priors import build_prior_means
from simulate_playoffs import posterior_title_probs
from update_model import bayesian_update


def load_all_round_results():
    results = {}
    for rnd in range(1, 5):
        path = f"data/round{rnd}_results.csv"
        if os.path.exists(path) and os.path.getsize(path) > 0:
            results[rnd] = pd.read_csv(path)
        else:
            results[rnd] = pd.DataFrame(columns=["team_a", "team_b", "wins_a", "wins_b"])
    return results


def results_data_fingerprint():
    """Changes when any playoff CSV is edited."""
    parts = []
    for rnd in range(1, 5):
        path = f"data/round{rnd}_results.csv"
        if os.path.exists(path):
            parts.append(f"{rnd}:{os.path.getmtime(path)}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def merge_series_lists(baseline, overrides):
    """Full playoff state: baseline + user edits (override wins on same matchup)."""
    by_key = {}
    for row in baseline or []:
        key = (int(row["round"]), frozenset({row["team_a"], row["team_b"]}))
        by_key[key] = dict(row)
    for row in overrides or []:
        key = (int(row["round"]), frozenset({row["team_a"], row["team_b"]}))
        by_key[key] = dict(row)
    return list(by_key.values())


def series_list_to_results_by_round(series_list):
    columns = ["team_a", "team_b", "wins_a", "wins_b"]
    results = {rnd: pd.DataFrame(columns=columns) for rnd in range(1, 5)}

    for row in series_list:
        rnd = int(row["round"])
        key = frozenset({row["team_a"], row["team_b"]})
        df = results[rnd]
        if not df.empty:
            keep = df.apply(
                lambda r: frozenset({r["team_a"], r["team_b"]}) != key, axis=1
            )
            df = df[keep]
        new_row = pd.DataFrame(
            [
                {
                    "team_a": row["team_a"],
                    "team_b": row["team_b"],
                    "wins_a": int(row["wins_a"]),
                    "wins_b": int(row["wins_b"]),
                }
            ]
        )
        results[rnd] = pd.concat([df, new_row], ignore_index=True)
    return results


def results_to_series_list(results_by_round):
    series = []
    for rnd in range(1, 5):
        df = results_by_round.get(rnd)
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            if row["wins_a"] > 0 or row["wins_b"] > 0:
                series.append(
                    {
                        "round": rnd,
                        "team_a": row["team_a"],
                        "team_b": row["team_b"],
                        "wins_a": int(row["wins_a"]),
                        "wins_b": int(row["wins_b"]),
                    }
                )
    return series


def flatten_bracket_to_series(east, west, finals=None):
    series = []
    for conf in (east, west):
        for rnd_num, key in enumerate(("round1", "round2", "round3"), start=1):
            for m in conf.get(key, []):
                if m["wins_a"] > 0 or m["wins_b"] > 0 or m.get("complete"):
                    series.append(
                        {
                            "round": rnd_num,
                            "team_a": m["team_a"],
                            "team_b": m["team_b"],
                            "wins_a": m["wins_a"],
                            "wins_b": m["wins_b"],
                        }
                    )
    if finals and (finals["wins_a"] > 0 or finals["wins_b"] > 0 or finals.get("complete")):
        series.append(
            {
                "round": 4,
                "team_a": finals["team_a"],
                "team_b": finals["team_b"],
                "wins_a": finals["wins_a"],
                "wins_b": finals["wins_b"],
            }
        )
    return series


def playoff_df_from_results(results_by_round):
    rows = []
    for rnd in range(1, 5):
        df = results_by_round.get(rnd)
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            if row["wins_a"] > 0 or row["wins_b"] > 0:
                rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["team_a", "team_b", "wins_a", "wins_b"])
    return pd.DataFrame(rows)


def current_round_from_results(results_by_round):
    for rnd in (4, 3, 2, 1):
        df = results_by_round.get(rnd)
        if df is not None and not df.empty and (df["wins_a"] + df["wins_b"]).sum() > 0:
            return rnd
    return 1


def conference_champion(conf_bracket):
    r3 = conf_bracket.get("round3") or []
    if not r3:
        return None
    m = r3[0]
    if m.get("complete") and m.get("winner"):
        return m["winner"]
    return m.get("predicted_winner")


def _cache_key(results_by_round):
    blob = json.dumps(results_to_series_list(results_by_round), sort_keys=True)
    blob += "|fp=" + results_data_fingerprint()
    return hashlib.md5(blob.encode()).hexdigest()


def _cached_bayesian(priors_df, playoff_df):
    key = playoff_df.to_csv(index=False) if not playoff_df.empty else "empty"
    if key not in _MODEL_CACHE:
        if len(_MODEL_CACHE) >= _CACHE_MAX:
            _MODEL_CACHE.pop(next(iter(_MODEL_CACHE)))
        _MODEL_CACHE[key] = bayesian_update(
            priors_df, playoff_df, n_samples=DASHBOARD_N_SAMPLES
        )
    return _MODEL_CACHE[key]


def build_dashboard_payload(
    results_by_round,
    *,
    data_source="local",
    use_cache=True,
):
    cache_key = _cache_key(results_by_round)
    if use_cache and cache_key in _PAYLOAD_CACHE:
        return _PAYLOAD_CACHE[cache_key]

    teams_df = load_teams("data/teams_2026.csv")
    playoff_df = playoff_df_from_results(results_by_round)
    current_round = current_round_from_results(results_by_round)

    priors_df = build_prior_means(teams_df)
    teams, samples, weights = _cached_bayesian(priors_df, playoff_df)
    title_probs = posterior_title_probs(
        teams,
        samples,
        weights,
        teams_df,
        results_by_round,
        n_outer=DASHBOARD_TITLE_SIMS,
    )
    team_to_idx = {team: i for i, team in enumerate(teams)}
    seed_map = dict(zip(teams_df["team"], teams_df["seed"]))

    east_df = teams_df[teams_df["conference"] == "East"]
    west_df = teams_df[teams_df["conference"] == "West"]

    east = build_conference_bracket(
        east_df,
        results_by_round,
        samples,
        weights,
        team_to_idx,
        series_n_sim=DASHBOARD_MATCHUP_SIMS,
    )
    west = build_conference_bracket(
        west_df,
        results_by_round,
        samples,
        weights,
        team_to_idx,
        series_n_sim=DASHBOARD_MATCHUP_SIMS,
    )

    east_champ = conference_champion(east)
    west_champ = conference_champion(west)
    finals = build_finals_matchup(
        east_champ,
        west_champ,
        results_by_round.get(4),
        samples,
        weights,
        team_to_idx,
        seed_map,
    )

    prob_rows = sorted(title_probs.items(), key=lambda x: x[1], reverse=True)
    active_teams = set()
    for conf in (east, west):
        for rnd in ("round1", "round2", "round3"):
            for m in conf.get(rnd, []):
                active_teams.add(m["team_a"])
                active_teams.add(m["team_b"])
                if m.get("winner"):
                    active_teams.add(m["winner"])

    baseline = results_to_series_list(results_by_round)

    payload = {
        "generated_at": date.today().isoformat(),
        "current_round": current_round,
        "data_source": data_source,
        "champion_if_decided": infer_champion_from_results(results_by_round),
        "title_probabilities": [
            {
                "team": team,
                "probability": round(prob, 4),
                "seed": int(seed_map.get(team, 0)),
                "active": team in active_teams and prob > 0,
            }
            for team, prob in prob_rows
        ],
        "east": east,
        "west": west,
        "finals": finals,
        "baseline_series": baseline,
    }
    if use_cache:
        if len(_PAYLOAD_CACHE) >= _CACHE_MAX:
            _PAYLOAD_CACHE.pop(next(iter(_PAYLOAD_CACHE)))
        _PAYLOAD_CACHE[cache_key] = payload
    return payload
