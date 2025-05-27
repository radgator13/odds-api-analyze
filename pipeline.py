import subprocess
import time
import os

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

print("\n✅ All steps complete. You can now run:")
print("   streamlit run app.py")
