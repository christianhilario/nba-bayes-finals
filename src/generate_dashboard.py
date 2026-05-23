"""Run the Bayesian model and embed data in the static dashboard."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dashboard_model import build_dashboard_payload
from nba_fetch import fetch_actual_results


def embed_data_in_dashboard_html(
    payload, html_path=os.path.join("dashboard", "dashboard.html")
):
    if not os.path.exists(html_path):
        return

    data_js = "window.DASHBOARD_DATA = " + json.dumps(payload) + ";"
    marker = '<script id="nba-dashboard-data">'
    end_marker = "</script>"

    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    start = html.find(marker)
    if start == -1:
        return

    content_start = start + len(marker)
    end = html.find(end_marker, content_start)
    if end == -1:
        return

    new_html = html[:content_start] + "\n    " + data_js + "\n  " + html[end:]
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(root)

    results, note = fetch_actual_results(source="csv")
    payload = build_dashboard_payload(results, data_source=note)

    os.makedirs("outputs", exist_ok=True)
    json_path = os.path.join("outputs", "dashboard_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    embed_data_in_dashboard_html(payload)

    print(f"Dashboard data written to {json_path}")
    print("Open with: python open_dashboard.py")


if __name__ == "__main__":
    main()
