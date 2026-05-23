"""Playoff bracket structure, results parsing, and matchup probabilities."""

import numpy as np
import pandas as pd

FIRST_ROUND_PAIRS = [(1, 8), (2, 7), (3, 6), (4, 5)]


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def _winner_from_scores(team_a, team_b, wins_a, wins_b):
    if wins_a >= 4:
        return team_a
    if wins_b >= 4:
        return team_b
    return None


def _lookup_result(results_df, team_a, team_b):
    if results_df is None or results_df.empty:
        return None
    for _, row in results_df.iterrows():
        a, b = row["team_a"], row["team_b"]
        if {a, b} == {team_a, team_b}:
            if a == team_a:
                return int(row["wins_a"]), int(row["wins_b"])
            return int(row["wins_b"]), int(row["wins_a"])
    return None


def conference_teams(teams_df):
    return set(teams_df["team"])


def filter_results_for_conference(results_by_round, conf_teams):
    """Only series where both teams are in this conference."""
    filtered = {}
    columns = ["team_a", "team_b", "wins_a", "wins_b"]
    for rnd in range(1, 5):
        df = results_by_round.get(rnd)
        if df is None or df.empty:
            filtered[rnd] = pd.DataFrame(columns=columns)
            continue
        mask = df.apply(
            lambda r: r["team_a"] in conf_teams and r["team_b"] in conf_teams, axis=1
        )
        filtered[rnd] = df.loc[mask].copy().reset_index(drop=True)
    return filtered


def matchups_from_results_df(results_df, conf_teams):
    """Pairings from results; if duplicate pairings exist, keep the one with most games played."""
    if results_df is None or results_df.empty:
        return []
    best = {}
    for _, row in results_df.iterrows():
        a, b = row["team_a"], row["team_b"]
        if a not in conf_teams or b not in conf_teams:
            continue
        key = frozenset({a, b})
        games = int(row["wins_a"]) + int(row["wins_b"])
        prev = best.get(key)
        if prev is None or games > prev[2]:
            best[key] = (a, b, games)
    return [(a, b) for a, b, _ in best.values()]


def first_round_matchups(teams_df, conference, results_df=None):
    conf_teams = conference_teams(teams_df)
    from_csv = matchups_from_results_df(results_df, conf_teams)
    if len(from_csv) >= 4:
        return from_csv[:4]
    conf = teams_df[teams_df["conference"] == conference].sort_values("seed")
    by_seed = dict(zip(conf["seed"], conf["team"]))
    return [(by_seed[hi], by_seed[lo]) for hi, lo in FIRST_ROUND_PAIRS]


def conference_round_pairs(teams_df, conf_label, results_by_round, round_num, r1_winners=None, r2_winners=None):
    """Matchups for a round: prefer results file, else bracket tree from winners."""
    conf_teams = conference_teams(teams_df)
    pairs = matchups_from_results_df(results_by_round.get(round_num), conf_teams)
    if pairs:
        return pairs
    if round_num == 1:
        return first_round_matchups(teams_df, conf_label, results_by_round.get(1))
    if round_num == 2 and r1_winners:
        return next_round_matchups(r1_winners)
    if round_num == 3 and r2_winners and len(r2_winners) == 2 and None not in r2_winners:
        return [(r2_winners[0], r2_winners[1])]
    return []


def advance_winners(matchups, results_df):
    winners = []
    for team_a, team_b in matchups:
        scores = _lookup_result(results_df, team_a, team_b)
        if scores is None:
            winners.append(None)
            continue
        winners.append(_winner_from_scores(team_a, team_b, scores[0], scores[1]))
    return winners


def next_round_matchups(winners):
    """NBA fixed bracket: 1v8 winner plays 4v5 winner; 2v7 winner plays 3v6 winner."""
    if len(winners) != 4 or any(w is None for w in winners):
        return []
    return [(winners[0], winners[3]), (winners[1], winners[2])]


def game_win_prob(team_a, team_b, samples, weights, team_to_idx):
    ia, ib = team_to_idx[team_a], team_to_idx[team_b]
    p = sigmoid(samples[:, ia] - samples[:, ib])
    return float(np.average(p, weights=weights))


def series_win_prob(
    team_a,
    team_b,
    wins_a,
    wins_b,
    samples,
    weights,
    team_to_idx,
    n_sim=800,
    rng=None,
):
    if wins_a >= 4:
        return 1.0
    if wins_b >= 4:
        return 0.0

    rng = rng or np.random.default_rng(42)
    ia, ib = team_to_idx[team_a], team_to_idx[team_b]
    idx = rng.choice(len(samples), size=n_sim, replace=True, p=weights)

    wins = 0
    for i in idx:
        wa, wb = wins_a, wins_b
        theta_a, theta_b = samples[i, ia], samples[i, ib]
        while wa < 4 and wb < 4:
            if rng.random() < sigmoid(theta_a - theta_b):
                wa += 1
            else:
                wb += 1
        if wa == 4:
            wins += 1
    return wins / n_sim


def matchup_payload(
    team_a,
    team_b,
    results_df,
    samples,
    weights,
    team_to_idx,
    seed_map,
    conference,
    series_n_sim=800,
):
    scores = _lookup_result(results_df, team_a, team_b)
    wins_a = wins_b = 0
    complete = False
    if scores:
        wins_a, wins_b = scores
        complete = wins_a >= 4 or wins_b >= 4

    p_a = series_win_prob(
        team_a, team_b, wins_a, wins_b, samples, weights, team_to_idx, n_sim=series_n_sim
    )
    predicted = team_a if p_a >= 0.5 else team_b
    winner = _winner_from_scores(team_a, team_b, wins_a, wins_b)

    p_b = 1.0 - p_a
    return {
        "team_a": team_a,
        "team_b": team_b,
        "seed_a": seed_map.get(team_a),
        "seed_b": seed_map.get(team_b),
        "conference": conference,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "complete": complete,
        "winner": winner,
        "predicted_winner": predicted,
        "prob_a_wins_series": round(p_a, 4),
        "prob_b_wins_series": round(p_b, 4),
        "game_prob_a": round(game_win_prob(team_a, team_b, samples, weights, team_to_idx), 4),
        "game_prob_b": round(1.0 - game_win_prob(team_a, team_b, samples, weights, team_to_idx), 4),
    }


def round_matchups_for_display(
    teams_df, conf_label, conf_results, round_num, r1_winners=None, r2_winners=None
):
    """
    Matchups shown in the UI: always use results CSV for that round when present,
    so Round 2/3 appear even if earlier rounds were not inferred from seeds.
    """
    conf_teams = conference_teams(teams_df)
    pairs = matchups_from_results_df(conf_results.get(round_num), conf_teams)
    if pairs:
        return pairs
    return conference_round_pairs(
        teams_df,
        conf_label,
        conf_results,
        round_num,
        r1_winners=r1_winners,
        r2_winners=r2_winners,
    )


def build_conference_bracket(
    teams_df, results_by_round, samples, weights, team_to_idx, series_n_sim=800
):
    seed_map = dict(zip(teams_df["team"], teams_df["seed"]))
    conference = teams_df["conference"].iloc[0]
    conf_label = "East" if conference == "East" else "West"
    conf_teams = conference_teams(teams_df)
    conf_results = filter_results_for_conference(results_by_round, conf_teams)

    def payload(a, b, rnd):
        return matchup_payload(
            a,
            b,
            conf_results.get(rnd),
            samples,
            weights,
            team_to_idx,
            seed_map,
            conf_label,
            series_n_sim=series_n_sim,
        )

    r1_pairs = round_matchups_for_display(teams_df, conf_label, conf_results, 1)
    r1_matchups = [payload(a, b, 1) for a, b in r1_pairs]
    r1_winners = [m["winner"] for m in r1_matchups]

    r2_pairs = round_matchups_for_display(
        teams_df, conf_label, conf_results, 2, r1_winners=r1_winners
    )
    r2_matchups = [payload(a, b, 2) for a, b in r2_pairs]
    r2_winners = [m["winner"] for m in r2_matchups]

    r3_pairs = round_matchups_for_display(
        teams_df, conf_label, conf_results, 3, r2_winners=r2_winners
    )
    r3_matchups = [payload(a, b, 3) for a, b in r3_pairs]

    return {
        "conference": conf_label,
        "round1": r1_matchups,
        "round2": r2_matchups,
        "round3": r3_matchups,
    }


def build_finals_matchup(east_champ, west_champ, results_df, samples, weights, team_to_idx, seed_map):
    if not east_champ or not west_champ:
        return None
    return matchup_payload(
        east_champ,
        west_champ,
        results_df,
        samples,
        weights,
        team_to_idx,
        seed_map,
        "Finals",
    )


def infer_champion_from_results(results_by_round):
    """Return the Finals winner only when the championship series is complete."""
    df = results_by_round.get(4)
    if df is None or df.empty:
        return None
    for _, row in df.iterrows():
        if row["wins_a"] >= 4:
            return row["team_a"]
        if row["wins_b"] >= 4:
            return row["team_b"]
    return None
