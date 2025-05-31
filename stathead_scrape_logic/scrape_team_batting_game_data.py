import os
import time
import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# === Load credentials ===
load_dotenv()
USERNAME = os.getenv("STATHEAD_USERNAME")
PASSWORD = os.getenv("STATHEAD_PASSWORD")

# === URLs ===
LOGIN_URL = "https://stathead.com/users/login.cgi"
TARGET_URL = "https://stathead.com/baseball/team-batting-game-finder.cgi"

# === File Paths ===
CSV_PATH = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\stathead_batting_game_data.csv"
ARCHIVE_DIR = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\archive"

# === Login and fetch ===
with requests.Session() as session:
    # Step 1: Log in
    login_payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "submit": "Login"
    }

    login_resp = session.post(LOGIN_URL, data=login_payload)
    if "Logout" not in login_resp.text and "My Account" not in login_resp.text:
        raise Exception("❌ Login failed — check username/password or site changes.")

    print("✅ Logged in successfully.")

    # Step 2: Submit form for last 5 days
    form_payload = {
        "request": "1",
        "order_by": "date",
        "timeframe": "last_n_days",
        "previous_days": "5",
    }

    response = session.post(TARGET_URL, data=form_payload)
    if response.status_code != 200:
        raise Exception("❌ Failed to fetch results page.")

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one("table.stats_table")

    if not table:
        raise Exception("❌ Could not find results table.")

    df = pd.read_html(str(table))[0]
    print(f"📊 Retrieved {len(df)} rows of team batting data.")

# === Save merged data ===
if os.path.exists(CSV_PATH):
    existing_df = pd.read_csv(CSV_PATH)
    combined_df = pd.concat([existing_df, df], ignore_index=True)
    combined_df.drop_duplicates(subset=["Team", "Date", "Opp", "Result"], inplace=True)
    print(f"🔁 Merged with existing. Total rows: {len(combined_df)}")
else:
    combined_df = df
    print("🆕 No existing file found — creating new CSV.")

combined_df.to_csv(CSV_PATH, index=False)
print(f"💾 Saved updated CSV: {CSV_PATH}")

# === Archive copy ===
os.makedirs(ARCHIVE_DIR, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
archive_path = os.path.join(ARCHIVE_DIR, f"stathead_team_batting_game_data_{timestamp}.csv")
combined_df.to_csv(archive_path, index=False)
print(f"🗄️ Archived version to: {archive_path}")
