import os
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
USERNAME = os.getenv("STATHEAD_USERNAME")
PASSWORD = os.getenv("STATHEAD_PASSWORD")

LOGIN_URL = "https://stathead.com/users/login.cgi"

# 👇 Your full result URL captured from browser (adjust if needed)
RESULTS_URL = (
    "https://stathead.com/baseball/player-pitching-game-finder.cgi"
    "?request=1"
    "&match=player_game"
    "&order_by_asc=0"
    "&order_by=p_so"
    "&timeframe=last_n_days"
    "&previous_days=30"
    "&comp_type=reg"
    "&team_game_min=1"
    "&team_game_max=165"
    "&player_game_min=1"
    "&player_game_max=9999"
)

# 👇 Your original save paths
CSV_PATH = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\stathead_player_pitching_game_data.csv"
ARCHIVE_DIR = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\archive"

with requests.Session() as session:
    # Log in
    login_payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "submit": "Login"
    }
    resp = session.post(LOGIN_URL, data=login_payload)
    if "Logout" not in resp.text:
        raise Exception("❌ Login failed")

    print("✅ Logged in.")

    # Fetch results
    result = session.get(RESULTS_URL)
    soup = BeautifulSoup(result.text, "html.parser")
    table = soup.select_one("table.stats_table")
    if not table:
        with open("debug_missing_table.html", "w", encoding="utf-8") as f:
            f.write(result.text)
        raise Exception("❌ Table not found — saved HTML.")

    df = pd.read_html(str(table))[0]
    print(f"📊 Downloaded {len(df)} new rows.")

    # Merge with existing file if it exists
    if os.path.exists(CSV_PATH):
        existing_df = pd.read_csv(CSV_PATH)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        combined_df.drop_duplicates(subset=["Player", "Date", "Team", "IP", "Result"], inplace=True)
        print(f"🔁 Merged with existing. Total rows: {len(combined_df)}")
    else:
        combined_df = df
        print("🆕 No existing file. Created new dataset.")

    # Save to main file
    combined_df.to_csv(CSV_PATH, index=False)
    print(f"💾 Updated main file: {CSV_PATH}")

    # Archive copy
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(ARCHIVE_DIR, f"stathead_player_pitching_game_data_{timestamp}.csv")
    combined_df.to_csv(archive_path, index=False)
    print(f"🗄️ Archived to: {archive_path}")
