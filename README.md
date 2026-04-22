# NBA Finals 2026 — Bayesian Prediction Model

A Python project that uses Bayesian inference to estimate each playoff team's probability of winning the 2026 NBA Finals. Built as a personal extension of concepts from DS-122 at Boston University. (Thank you Professor Wobbes)

## The Idea
After learning about Bayesian updating and probability of superiority in class, I wanted to apply it to something real. The question I asked:

"Given what we know from the regular season and the first round so far, how likely is each team to win the Finals?"

## How It Works

**1. Prior**
Each team gets a strength score based on their regular season win percentage and seed. This is our starting belief before looking at playoff results.

**2. Update**
We use first-round playoff results (as of April 22, 2026) to update those beliefs. Teams performing better than expected get a boost. This uses importance sampling with 20,000 Monte Carlo draws.

**3. Simulation**
We draw 3,000 scenarios from the posterior and simulate the full bracket each time. Whoever wins most often across those simulations is our predicted champion.

## Results (April 22, 2026)

| Team | Win Probability |
|---|---|
| Oklahoma City Thunder | 31% |
| Detroit Pistons | 24% |
| San Antonio Spurs | 9.5% |
| Cleveland Cavaliers | 8.4% |
| Los Angeles Lakers | 8.1% |
| Denver Nuggets | 7.5% |
| Boston Celtics | 6.3% |
| New York Knicks | 3.0% |
| Minnesota Timberwolves | 0.7% |
| Atlanta Hawks | 0.6% |

![Finals Chart](outputs/finals_chart.png)

## How to Run

pip install pandas numpy matplotlib scipy

python src/main.py

## How to Update After New Games
Just edit the series scores in data/playoff_results_apr22_2026.csv and run main.py again. The model updates automatically.

## Limitations
- Prior weights were chosen manually, not fit to historical data
- Does not factor in injuries, home court, or player matchups
- Only uses wins and losses, not point differential or advanced stats
- Small sample size — first round is not even done yet

## Stack
Python, pandas, numpy, matplotlib, scipy

## Course Connection
DS-122 at Boston University — topics applied: Bayesian inference, probability of superiority, Monte Carlo simulation.