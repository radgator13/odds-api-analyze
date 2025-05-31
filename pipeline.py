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
    ("[STEP] Scraping Stathead stats", "scrape_stathead_stats.py"),
    ("[STEP] Pulling sportsbook props", "run_odds_api.py"),
    ("[STEP] Training strikeout model", "Full_Training_Script.py"),
    ("[STEP] Generating predictions", "predict_props_with_model.py"),
    ("[STEP] Compare strikeouts to actuals", "compare_strikeout_picks_to_actual.py")
]

# === RUN STEPS ===
for label, script in steps:
    print(f"\n{label}")
    result = subprocess.run(
        ["python", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
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
        # Set Git identity if missing
        def ensure_git_identity():
            name = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True).stdout.strip()
            email = subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True).stdout.strip()

            if not name:
                subprocess.run(["git", "config", "--global", "user.name", "Gator"], check=True)
                print("🔧 Set git user.name = Gator")
            if not email:
                subprocess.run(["git", "config", "--global", "user.email", "a1d3r13@gmail.com"], check=True)
                print("🔧 Set git user.email = a1d3r13@gmail.com")

        ensure_git_identity()

        subprocess.run(["git", "add", "."], check=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        commit_message = f"Auto push from run_pipeline at {timestamp}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push", "origin", "master"], check=True)
        print("✅ Git push successful.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e}")


