"""Local server: serves dashboard + playoff bracket API (read-only)."""

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(__file__))

from dashboard_model import _MODEL_CACHE, _PAYLOAD_CACHE, build_dashboard_payload
from nba_fetch import fetch_actual_results


def _warm_cache():
    _PAYLOAD_CACHE.clear()
    _MODEL_CACHE.clear()
    results, note = fetch_actual_results(source="csv")
    build_dashboard_payload(results, data_source=note, use_cache=False)


class DashboardHandler(SimpleHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/bracket":
            qs = parse_qs(parsed.query)
            source = qs.get("source", ["auto"])[0]
            results, note = fetch_actual_results(source=source)
            payload = build_dashboard_payload(results, data_source=note, use_cache=False)
            self._send_json(payload)
            return
        if parsed.path == "/api/health":
            self._send_json({"ok": True})
            return
        return super().do_GET()


def main(port=8765):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(root)
    print("Loading playoff data and running Bayesian model…")
    _warm_cache()
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Dashboard: http://127.0.0.1:{port}/dashboard/dashboard.html")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
