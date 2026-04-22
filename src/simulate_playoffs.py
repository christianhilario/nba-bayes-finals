import numpy as np

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def simulate_series(theta_a, theta_b, rng):
    p_a = sigmoid(theta_a - theta_b)
    wins_a = 0
    wins_b = 0
    while wins_a < 4 and wins_b < 4:
        if rng.random() < p_a:
            wins_a += 1
        else:
            wins_b += 1
    return 0 if wins_a == 4 else 1

def simulate_bracket_once(theta_map, rng):
    east_qf = [
        ("Detroit Pistons", "Orlando Magic"),
        ("Boston Celtics", "Philadelphia 76ers"),
        ("New York Knicks", "Atlanta Hawks"),
        ("Cleveland Cavaliers", "Toronto Raptors"),
    ]

    west_qf = [
        ("Oklahoma City Thunder", "Phoenix Suns"),
        ("San Antonio Spurs", "Portland Trail Blazers"),
        ("Denver Nuggets", "Minnesota Timberwolves"),
        ("Los Angeles Lakers", "Houston Rockets"),
    ]

    def play_round(matchups):
        winners = []
        for a, b in matchups:
            winner_idx = simulate_series(theta_map[a], theta_map[b], rng)
            winners.append(a if winner_idx == 0 else b)
        return winners

    east_sf_teams = play_round(east_qf)
    west_sf_teams = play_round(west_qf)

    east_sf = [(east_sf_teams[0], east_sf_teams[1]), (east_sf_teams[2], east_sf_teams[3])]
    west_sf = [(west_sf_teams[0], west_sf_teams[1]), (west_sf_teams[2], west_sf_teams[3])]

    east_cf_teams = play_round(east_sf)
    west_cf_teams = play_round(west_sf)

    east_cf = [(east_cf_teams[0], east_cf_teams[1])]
    west_cf = [(west_cf_teams[0], west_cf_teams[1])]

    east_champ = play_round(east_cf)[0]
    west_champ = play_round(west_cf)[0]

    finals = [(east_champ, west_champ)]
    champ = play_round(finals)[0]
    return champ

def posterior_title_probs(teams, samples, weights, n_outer=3000, random_state=42):
    rng = np.random.default_rng(random_state)
    title_counts = {team: 0.0 for team in teams}

    sample_indices = rng.choice(
        len(samples),
        size=n_outer,
        replace=True,
        p=weights
    )

    for idx in sample_indices:
        theta_map = {team: samples[idx, i] for i, team in enumerate(teams)}
        champ = simulate_bracket_once(theta_map, rng)
        title_counts[champ] += 1

    total = sum(title_counts.values())
    return {team: count / total for team, count in title_counts.items()}