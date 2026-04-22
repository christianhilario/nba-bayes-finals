import pandas as pd

def load_teams(path="data/teams_2026.csv"):
    df = pd.read_csv(path)
    df["win_pct"] = df["wins"] / (df["wins"] + df["losses"])
    return df

def load_playoff_results(path="data/playoff_results_apr22_2026.csv"):
    return pd.read_csv(path)
    