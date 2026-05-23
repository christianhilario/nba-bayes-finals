import numpy as np

from bracket import (
    _lookup_result,
    _winner_from_scores,
    conference_round_pairs,
    conference_teams,
    filter_results_for_conference,
    sigmoid,
)


def simulate_series(theta_a, theta_b, rng, wins_a=0, wins_b=0):
    wa, wb = wins_a, wins_b
    while wa < 4 and wb < 4:
        if rng.random() < sigmoid(theta_a - theta_b):
            wa += 1
        else:
            wb += 1
    return wa, wb


def resolve_series(team_a, team_b, results_df, theta_map, rng):
    scores = _lookup_result(results_df, team_a, team_b)
    wa, wb = scores if scores else (0, 0)
    winner = _winner_from_scores(team_a, team_b, wa, wb)
    if winner:
        return winner
    wa, wb = simulate_series(theta_map[team_a], theta_map[team_b], rng, wa, wb)
    return team_a if wa == 4 else team_b


def simulate_conference(teams_df, results_by_round, theta_map, rng):
    conf_label = teams_df["conference"].iloc[0]
    label = "East" if conf_label == "East" else "West"
    conf_results = filter_results_for_conference(
        results_by_round, conference_teams(teams_df)
    )

    r1_pairs = conference_round_pairs(teams_df, label, conf_results, 1)
    r1_winners = [
        resolve_series(a, b, conf_results.get(1), theta_map, rng) for a, b in r1_pairs
    ]

    r2_pairs = conference_round_pairs(
        teams_df, label, conf_results, 2, r1_winners=r1_winners
    )
    if not r2_pairs:
        return None
    r2_winners = [
        resolve_series(a, b, conf_results.get(2), theta_map, rng) for a, b in r2_pairs
    ]

    r3_pairs = conference_round_pairs(
        teams_df, label, conf_results, 3, r2_winners=r2_winners
    )
    if not r3_pairs:
        return None
    return resolve_series(
        r3_pairs[0][0], r3_pairs[0][1], conf_results.get(3), theta_map, rng
    )


def simulate_bracket_once(theta_map, rng, teams_df, results_by_round):
    east_df = teams_df[teams_df["conference"] == "East"]
    west_df = teams_df[teams_df["conference"] == "West"]

    east_champ = simulate_conference(east_df, results_by_round, theta_map, rng)
    west_champ = simulate_conference(west_df, results_by_round, theta_map, rng)

    if not east_champ or not west_champ:
        return east_champ or west_champ

    return resolve_series(
        east_champ, west_champ, results_by_round.get(4), theta_map, rng
    )


def posterior_title_probs(
    teams, samples, weights, teams_df, results_by_round, n_outer=1200, random_state=42
):
    rng = np.random.default_rng(random_state)
    title_counts = {team: 0.0 for team in teams}

    sample_indices = rng.choice(
        len(samples),
        size=n_outer,
        replace=True,
        p=weights,
    )

    for idx in sample_indices:
        theta_map = {team: samples[idx, i] for i, team in enumerate(teams)}
        champ = simulate_bracket_once(theta_map, rng, teams_df, results_by_round)
        if champ:
            title_counts[champ] += 1

    total = sum(title_counts.values())
    if total == 0:
        return {team: 0.0 for team in teams}
    return {team: count / total for team, count in title_counts.items()}
