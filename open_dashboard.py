"""Start interactive dashboard server and open in browser."""

import os
import subprocess
import sys
import time
import webbrowser


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    subprocess.run(
        [sys.executable, os.path.join("src", "generate_dashboard.py")],
        check=True,
    )

    port = 8765
    server_script = os.path.join("src", "dashboard_server.py")

    proc = subprocess.Popen([sys.executable, server_script])
    time.sleep(0.6)

    url = f"http://127.0.0.1:{port}/dashboard/dashboard.html"
    webbrowser.open(url)
    print(f"Interactive dashboard: {url}")
    print("Edit matchups in the browser. Ctrl+C here stops the server.")

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
