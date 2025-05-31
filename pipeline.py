import subprocess
import time
import os
import sys
import builtins

# === Force all subprocess output to UTF-8 ===
os.environ["PYTHONIOENCODING"] = "utf-8"

# === Safe print override for this launcher ===
original_print = builtins.print
def safe_print(*args, **kwargs):
    try:
        original_print(*args, **kwargs)
    except UnicodeEncodeError:
        fallback = [str(arg).encode('ascii', errors='ignore').decode() for arg in args]
        original_print(*fallback, **kwargs)
builtins.print = safe_print

if sys.stdout.encoding.lower() != "utf-8":
    print("[WARN] Terminal does not support emojis. Using safe print style.")

# === CONFIG ===
steps = [
    ("[STEP] Scraping Stathead stats", "scrape_player_pitching_game_data.py"),
    ("[STEP] Pulling sportsbook props", "run_odds_api.py"),
    ("[STEP] Training strikeout model", "Full_Training_Script.py"),
    ("[STEP] Generating predictions", "predict_props_with_model.py")
]

# === RUN STEPS ===
for label, script in steps:
    print(f"\n{label}")
    result = subprocess.run(
        ["python", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"  # avoids crashing on emoji/UTF-8 mismatches
    )

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
