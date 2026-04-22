import numpy as np
import pandas as pd

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def bayesian_update(priors_df, playoff_df, n_samples=20000, random_state=42):
    """
    Approximate Bayesian update by importance weighting.
    Each team has latent strength theta.
    Prior: theta ~ Normal(prior_mean, prior_sd^2)
    Likelihood: observed playoff wins from current first-round series.
    """
    rng = np.random.default_rng(random_state)

    teams = priors_df["team"].tolist()
    team_to_idx = {team: i for i, team in enumerate(teams)}

    prior_means = priors_df["prior_mean"].to_numpy()
    prior_sds = priors_df["prior_sd"].to_numpy()

    samples = rng.normal(
        loc=prior_means,
        scale=prior_sds,
        size=(n_samples, len(teams))
    )

    log_weights = np.zeros(n_samples)

    for _, row in playoff_df.iterrows():
        a = team_to_idx[row["team_a"]]
        b = team_to_idx[row["team_b"]]
        wins_a = int(row["wins_a"])
        wins_b = int(row["wins_b"])

        p_a = sigmoid(samples[:, a] - samples[:, b])
        p_a = np.clip(p_a, 1e-9, 1 - 1e-9)

        log_weights += wins_a * np.log(p_a) + wins_b * np.log(1 - p_a)

    weights = np.exp(log_weights - np.max(log_weights))
    weights = weights / weights.sum()

    return teams, samples, weights