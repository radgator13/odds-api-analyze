import os
import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# === Load login credentials ===
load_dotenv()
USERNAME = os.getenv("STATHEAD_USERNAME")
PASSWORD = os.getenv("STATHEAD_PASSWORD")

# === Login and output paths ===
LOGIN_URL = "https://stathead.com/users/login.cgi"
CSV_PATH = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\stathead_team_pitching_game_data.csv"
ARCHIVE_DIR = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\archive"

# === Final working GET URL (no describe_only=1)
TEAM_PITCHING_URL = (
    "https://stathead.com/baseball/team-pitching-game-finder.cgi"
    "?request=1"
    "&match=team_game"
    "&order_by_asc=0"
    "&order_by=p_so"
    "&year_min=1901"
    "&year_max=2025"
    "&timeframe=last_n_days"
    "&previous_days=5"
    "&comp_type=reg"
    "&team_game_min=1"
    "&team_game_max=165"
    "&div_finish_comp=eq"
    "&div_finish_val=1"
    "&team_wins_comp=gt"
    "&team_wins_val=81"
    "&win_pct_comp=gt"
    "&win_pct_val=.500"
    "&comp_id[]=AL"
    "&comp_id[]=NL"
    "&comp_id[]=FL"
    "&opp_comp_id[]=AL"
    "&opp_comp_id[]=NL"
    "&opp_comp_id[]=FL"
    "&div_finish_comp_opp=eq"
    "&div_finish_val_opp=1"
    "&team_wins_comp_opp=gt"
    "&team_wins_val_opp=81"
    "&win_pct_comp_opp=gt"
    "&win_pct_val_opp=.500"
    "&score_ps_comp=gt"
    "&score_pa_comp=gt"
    "&score_margin_comp=gt"
    "&min_temperature=0"
    "&max_temperature=120"
    "&min_wind_speed=0"
    "&max_wind_speed=90"
)

with requests.Session() as session:
    # Step 1: Login to Stathead
    login_payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "submit": "Login"
    }

    login_response = session.post(LOGIN_URL, data=login_payload)
    if "Logout" not in login_response.text:
        raise Exception("❌ Login failed")

    print("✅ Logged in to Stathead.")

    # Step 2: Fetch table
    response = session.get(TEAM_PITCHING_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one("table.stats_table")

    if not table:
        with open("debug_team_pitching_results.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        raise Exception("❌ Could not find the table — saved to debug_team_pitching_results.html")

    df = pd.read_html(str(table))[0]
    print(f"📊 Retrieved {len(df)} team pitching rows.")

    # Step 3: Merge with existing data
    if os.path.exists(CSV_PATH):
        existing_df = pd.read_csv(CSV_PATH)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        combined_df.drop_duplicates(subset=["Team", "Date", "Opp", "Result", "IP"], inplace=True)
        print(f"🔁 Merged with existing. Total rows: {len(combined_df)}")
    else:
        combined_df = df
        print("🆕 Created new CSV.")

    # Step 4: Save main file
    combined_df.to_csv(CSV_PATH, index=False)
    print(f"💾 Saved updated CSV: {CSV_PATH}")

    # Step 5: Archive with timestamp
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(ARCHIVE_DIR, f"stathead_team_pitching_game_data_{timestamp}.csv")
    combined_df.to_csv(archive_path, index=False)
    print(f"🗄️ Archived to: {archive_path}")
