import os
import subprocess
import sys

def main():
    root = os.path.abspath(os.path.dirname(__file__))
    os.chdir(root)
    
    # Embed fresh data into the HTML
    subprocess.run([sys.executable, "src/generate_dashboard.py"])
    
    # Open directly in browser
    html_path = os.path.abspath("dashboard/dashboard.html")
    print(f"Opening dashboard: {html_path}")
    os.startfile(html_path)

if __name__ == "__main__":
    main()