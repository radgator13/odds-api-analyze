import subprocess
import time
import os
import sys
import builtins

# === Safe print for emoji/Unicode issues ===
original_print = builtins.print
def safe_print(*args, **kwargs):
    try:
        original_print(*args, **kwargs)
    except UnicodeEncodeError:
        fallback = [str(arg).encode('ascii', errors='ignore').decode() for arg in args]
        original_print(*fallback, **kwargs)
builtins.print = safe_print

# === Ensure subprocess output handles UTF-8 ===
os.environ["PYTHONIOENCODING"] = "utf-8"

# === SCRIPT ORDER ===
steps = [
    ("[STEP 1] Scraping player pitching game data", "stathead_scrape_logic/scrape_player_pitching_game_data.py"),
    ("[STEP 2] Scraping team pitching game data", "stathead_scrape_logic/scrape_team_pitching_game_data.py"),
    ("[STEP 3] Scraping team batting game data", "stathead_scrape_logic/scrape_team_batting_game_data.py")
]

# === Run Each Step ===
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
        print(result.stdout.strip())

else:
    print("\n✅ All scrape scripts completed successfully.")
