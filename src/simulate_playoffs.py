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
    # Round 2 remaining matchups
    east_r2 = [
        ("Cleveland Cavaliers", "Detroit Pistons"),
    ]
    west_r2 = [
        ("San Antonio Spurs", "Minnesota Timberwolves"),
    ]

    # Round 2 already completed
    east_r2_winners = ["New York Knicks", "Cleveland Cavaliers"]
    west_r2_winners = ["Oklahoma City Thunder", "San Antonio Spurs"]

    def play_round(matchups):
        winners = []
        for a, b in matchups:
            winner_idx = simulate_series(theta_map[a], theta_map[b], rng)
            winners.append(a if winner_idx == 0 else b)
        return winners

    # Finish Round 2
    east_r2_winners += play_round(east_r2)
    west_r2_winners += play_round(west_r2)

    # Conference Finals
    east_cf = [(east_r2_winners[0], east_r2_winners[1])]
    west_cf = [(west_r2_winners[0], west_r2_winners[1])]

    east_champ = play_round(east_cf)[0]
    west_champ = play_round(west_cf)[0]

    # Finals
    champ = play_round([(east_champ, west_champ)])[0]
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