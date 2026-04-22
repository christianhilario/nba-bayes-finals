import numpy as np

def build_prior_means(teams_df):
    """
    Create prior means for latent team strength using regular-season performance.
    """
    df = teams_df.copy()

    # Simple strength formula
    df["prior_mean"] = (
        4.0 * (df["win_pct"] - df["win_pct"].mean())
        + 0.15 * (9 - df["seed"])
    )

    # Same uncertainty for all teams in version 1
    df["prior_sd"] = 0.75
    return df[["team", "prior_mean", "prior_sd"]]