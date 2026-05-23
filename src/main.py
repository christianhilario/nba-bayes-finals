import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from load_data import load_teams, load_playoff_results
from priors import build_prior_means
from update_model import bayesian_update
from simulate_playoffs import posterior_title_probs



def main():
    teams_df = load_teams("data/teams_2026.csv")
    playoff_df, ROUND = load_playoff_results()

    from dashboard_model import load_all_round_results

    results_by_round = load_all_round_results()

    priors_df = build_prior_means(teams_df)
    teams, samples, weights = bayesian_update(priors_df, playoff_df)
    probs = posterior_title_probs(
        teams, samples, weights, teams_df, results_by_round, n_outer=3000
    )

    out_df = pd.DataFrame({
        "team": list(probs.keys()),
        "posterior_finals_win_prob": list(probs.values())
    }).sort_values("posterior_finals_win_prob", ascending=False)

    print("\n--- Posterior Probability of Winning 2026 NBA Finals ---\n")
    print(out_df.to_string(index=False))

    out_df.to_csv(f"outputs/round{ROUND}_posterior_probs.csv", index=False)

    top_df = out_df.head(10)
    plt.figure(figsize=(10, 6))
    plt.bar(top_df["team"], top_df["posterior_finals_win_prob"], color="steelblue")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Posterior Probability")
    plt.title(f"Posterior Probability of Winning 2026 NBA Finals\n(Bayesian Model — Round {ROUND})")
    plt.tight_layout()
    plt.savefig(f"outputs/round{ROUND}_chart.png")
    plt.show()
    print(f"\nChart saved to outputs/round{ROUND}_chart.png")

if __name__ == "__main__":
    main()