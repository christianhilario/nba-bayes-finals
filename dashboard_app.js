const API_BASE = "http://127.0.0.1:8765";

const TEAM_META = {
  "Oklahoma City Thunder": { abbr: "OKC", color: "#007ac1" },
  "San Antonio Spurs": { abbr: "SAS", color: "#c4ced4" },
  "Denver Nuggets": { abbr: "DEN", color: "#fec524" },
  "Los Angeles Lakers": { abbr: "LAL", color: "#552583" },
  "Houston Rockets": { abbr: "HOU", color: "#ce1141" },
  "Minnesota Timberwolves": { abbr: "MIN", color: "#236192" },
  "Phoenix Suns": { abbr: "PHX", color: "#e56020" },
  "Portland Trail Blazers": { abbr: "POR", color: "#e03a3e" },
  "Detroit Pistons": { abbr: "DET", color: "#c8102e" },
  "Boston Celtics": { abbr: "BOS", color: "#007a33" },
  "New York Knicks": { abbr: "NYK", color: "#f58426" },
  "Cleveland Cavaliers": { abbr: "CLE", color: "#860038" },
  "Toronto Raptors": { abbr: "TOR", color: "#ce1141" },
  "Atlanta Hawks": { abbr: "ATL", color: "#e03a3e" },
  "Philadelphia 76ers": { abbr: "PHI", color: "#006bb6" },
  "Orlando Magic": { abbr: "ORL", color: "#0077c0" },
};

function teamMeta(name) {
  return TEAM_META[name] || { abbr: name.split(" ").pop().slice(0, 3).toUpperCase(), color: "#555" };
}

function pct(n) {
  return (n * 100).toFixed(1) + "%";
}

function setStatus(msg, isError = false) {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
}

/** Prefer embedded JSON if API returns incomplete west bracket (stale server). */
function normalizePayload(data) {
  const emb = window.DASHBOARD_DATA;
  const westOk =
    data?.west?.round2?.length >= 2 && data?.west?.round3?.length >= 1;
  const embOk = emb?.west?.round2?.length >= 2 && emb?.west?.round3?.length >= 1;
  if (!westOk && embOk) return emb;
  return data;
}

function renderProbs(data) {
  const list = document.getElementById("prob-list");
  const teams = data.title_probabilities
    .filter((t) => t.active)
    .sort((a, b) => b.probability - a.probability);

  const maxP = Math.max(...teams.map((t) => t.probability), 0.01);

  list.innerHTML =
    teams.length === 0
      ? '<p class="muted-dash">No active teams</p>'
      : teams
          .map((t) => {
            const w = (t.probability / maxP) * 100;
            return `
        <div class="prob-row">
          <span class="prob-name">${teamMeta(t.team).abbr} · ${t.team.split(" ").slice(-1)[0]}</span>
          <span class="prob-pct">${pct(t.probability)}</span>
          <div class="prob-bar-wrap"><div class="prob-bar" style="width:${w}%"></div></div>
        </div>`;
          })
          .join("");
}

function teamLine(team, seed, score, isActual, isPredicted, seriesProb) {
  const meta = teamMeta(team);
  let cls = "team-line";
  if (isActual) cls += " winner-actual";
  else if (isPredicted) cls += " winner-predicted";
  const textColor = parseInt(meta.color.slice(1), 16) > 0x888888 ? "#111" : "#fff";
  const odds =
    seriesProb != null
      ? `<span class="series-pct" title="Chance to win this series">${pct(seriesProb)}</span>`
      : "";

  return `
    <div class="${cls}">
      <div class="team-left">
        <span class="seed">${seed ?? ""}</span>
        <span class="abbr" style="background:${meta.color};color:${textColor}">${meta.abbr}</span>
        <span class="team-name">${team}</span>
      </div>
      <span class="score">${score}${odds}</span>
    </div>`;
}

function renderMatchup(m) {
  if (!m) return "";
  const live = !m.complete && (m.wins_a > 0 || m.wins_b > 0);
  const predA = m.predicted_winner === m.team_a;
  const predB = m.predicted_winner === m.team_b;
  const actA = m.winner === m.team_a;
  const actB = m.winner === m.team_b;
  const pA = m.prob_a_wins_series ?? 0.5;
  const pB = m.prob_b_wins_series ?? 1 - pA;
  const showOdds = !m.complete;

  return `
    <article class="matchup ${live ? "live" : ""}">
      ${teamLine(m.team_a, m.seed_a, m.wins_a, actA, showOdds && predA, showOdds ? pA : null)}
      ${teamLine(m.team_b, m.seed_b, m.wins_b, actB, showOdds && predB, showOdds ? pB : null)}
      <div class="matchup-footer">
        <span>${m.complete ? "Final" : live ? "In progress" : "Upcoming"}</span>
        <span class="odds-pair">${teamMeta(m.team_a).abbr} ${pct(pA)} · ${teamMeta(m.team_b).abbr} ${pct(pB)}</span>
      </div>
    </article>`;
}

function renderConference(conf, targetId) {
  const rounds = [
    { key: "round1", label: "Round 1" },
    { key: "round2", label: "Round 2" },
    { key: "round3", label: "Conf. Finals" },
  ];

  const cols = rounds
    .map((r) => {
      const matchups = conf[r.key] || [];
      return `
      <div class="round-col">
        <h3>${r.label}</h3>
        ${matchups.map(renderMatchup).join("") || '<p class="muted-dash">No series yet</p>'}
      </div>`;
    })
    .join("");

  const badge = conf.conference === "East" ? "east" : "west";
  const el = document.getElementById(targetId);
  if (!el) return;

  el.innerHTML = `
    <div class="conf-header">
      <span class="conf-badge ${badge}">${conf.conference}ern Conference</span>
    </div>
    <p class="scroll-hint-bracket">Scroll right → to see Round 2 and Conference Finals</p>
    <div class="conf-bracket-scroll">
      <div class="bracket">${cols}</div>
    </div>`;
}

function render(data) {
  data = normalizePayload(data);

  document.getElementById("meta").innerHTML = `
    Round <strong>${data.current_round}</strong> ·
    Updated <strong>${data.generated_at}</strong>`;

  setStatus(data.data_source || "Playoff results loaded");

  renderProbs(data);

  renderConference(data.east, "east-panel");
  renderConference(data.west, "west-panel");

  const finalsSec = document.getElementById("finals-section");
  const finalsEl = document.getElementById("finals-bracket");
  if (data.finals) {
    finalsSec.hidden = false;
    finalsEl.innerHTML = `<div class="round-col"><h3>Finals</h3>${renderMatchup(data.finals)}</div>`;
  } else {
    finalsSec.hidden = true;
  }
}

async function loadBracket() {
  setStatus("Loading playoff results and running model…");
  try {
    const res = await fetch(`${API_BASE}/api/bracket?source=csv&_=${Date.now()}`);
    if (!res.ok) throw new Error("API error");
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    render(data);
  } catch {
    if (window.DASHBOARD_DATA) {
      render(window.DASHBOARD_DATA);
      setStatus(
        window.DASHBOARD_DATA.data_source ||
          "Loaded from page data — run python open_dashboard.py to refresh"
      );
    } else {
      document.getElementById("east-panel").innerHTML = `
        <div class="empty-state"><p>Run <code>python open_dashboard.py</code></p></div>`;
    }
  }
}

document.getElementById("btn-refresh")?.addEventListener("click", loadBracket);

loadBracket();
