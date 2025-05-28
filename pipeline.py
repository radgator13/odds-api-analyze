import subprocess
import time
import os
import sys

if sys.stdout.encoding.lower() != "utf-8":
    print("[WARN] Terminal does not support emojis. Using safe print style.")

# === CONFIG ===
steps = [
    ("[STEP] Scraping Stathead stats", "scrape_stathead_stats.py"),
    ("[STEP] Pulling sportsbook props", "run_odds_api.py"),
    ("[STEP] Training strikeout model", "Full_Training_Script.py"),
    ("[STEP] Generating predictions", "predict_props_with_model.py")
]

# === RUN STEPS ===
for label, script in steps:
    print(f"\n{label}")
    result = subprocess.run(["python", script], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error running {script}:\n{result.stderr}")
        break
    else:
        print(result.stdout)

else:
    # === GIT PUSH ===
    print("\n📦 Committing and pushing to GitHub...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        commit_message = f"Auto push from run_pipeline at {timestamp}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ Git push successful.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e}")

    # === LAUNCH STREAMLIT ===
    print("\n🚀 Launching Streamlit...")
    try:
        subprocess.Popen(["streamlit", "run", "app.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        print("🌐 Streamlit launched in a new window.")
    except Exception as e:
        print(f"❌ Failed to launch Streamlit: {e}")


