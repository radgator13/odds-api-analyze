import subprocess
import time
import os
import sys
if sys.stdout.encoding.lower() != "utf-8":
    print("[WARN] Terminal does not support emojis. Using safe print style.")

# === CONFIG ===
steps = [
    ("🔄 Scraping Stathead stats", "scrape_stathead_stats.py"),
    ("💰 Pulling sportsbook props", "run_odds_api.py"),
    ("🤖 Training strikeout model", "Full_Training_Script.py"),
    ("🎯 Generating predictions", "predict_props_with_model.py")
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
    # === LAUNCH STREAMLIT ===
    print("\n✅ All steps complete. Launching Streamlit...")
    try:
        subprocess.Popen(["streamlit", "run", "app.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        print("🚀 Streamlit launched in a new console window.")
    except Exception as e:
        print(f"❌ Failed to launch Streamlit: {e}")

