import pandas as pd
import os

def load_teams(path="data/teams_2026.csv"):
    df = pd.read_csv(path)
    df["win_pct"] = df["wins"] / (df["wins"] + df["losses"])
    return df

def load_playoff_results():
    # automatically detect the latest round with data
    for round_num in [4, 3, 2, 1]:
        path = f"data/round{round_num}_results.csv"
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"Loading Round {round_num} results...")
            return pd.read_csv(path), round_num
    raise FileNotFoundError("No playoff results CSV found with data.")