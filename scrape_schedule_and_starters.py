from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import pandas as pd
import os
import time

# === ChromeDriver path
chrome_path = r"C:\Users\a1d3r\.wdm\drivers\chromedriver\win64\136.0.7103.94\chromedriver-win32\chromedriver.exe"

# === Headless Chrome setup
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
service = Service(executable_path=chrome_path)
driver = webdriver.Chrome(service=service, options=options)

# === Load ESPN MLB schedule page
url = "https://www.espn.com/mlb/schedule"
driver.get(url)
time.sleep(5)

# === Locate schedule blocks
sections = driver.find_elements(By.CLASS_NAME, "ScheduleTables")
print(f"✅ Found {len(sections)} schedule sections")

all_games = []

for section in sections:
    try:
        game_date = section.find_element(By.CLASS_NAME, "Table__Title").text.strip()
    except:
        continue

    rows = section.find_elements(By.XPATH, ".//tbody/tr[contains(@class, 'Table__TR')]")
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) < 5:
            continue
        try:
            away_team = cols[0].text.strip()
            home_team = cols[1].text.strip().replace("@", "").strip()
            pitching_matchup = cols[4].text.strip()

            if "vs" in pitching_matchup:
                away_pitcher, home_pitcher = [p.strip() for p in pitching_matchup.split("vs", 1)]
            else:
                away_pitcher, home_pitcher = "Undecided", "Undecided"

            all_games.append({
                "GameDate": game_date,
                "AwayTeam": away_team,
                "HomeTeam": home_team,
                "AwayPitcher": away_pitcher,
                "HomePitcher": home_pitcher
            })
        except Exception as e:
            print(f"❌ Error processing row: {e}")

driver.quit()

# === Create DataFrame from scraped data
df = pd.DataFrame(all_games)

# === Load and match pitcher IDs from pitcher_id_map.csv
id_map_path = "data/pitcher_id_map.csv"
if os.path.exists(id_map_path):
    id_map = pd.read_csv(id_map_path)
    id_map["FullName"] = id_map["FullName"].astype(str).str.replace(" ", "").str.strip()
    full_name_to_id = dict(zip(id_map["FullName"], id_map["PlayerID"]))

    def match_id(name):
        key = name.replace(" ", "").strip()
        return full_name_to_id.get(key, "")

    df["AwayPitcherID"] = df["AwayPitcher"].apply(match_id)
    df["HomePitcherID"] = df["HomePitcher"].apply(match_id)

    print("✅ Successfully matched pitcher names to PlayerID.")
else:
    print("❌ pitcher_id_map.csv not found.")
    df["AwayPitcherID"] = ""
    df["HomePitcherID"] = ""

# === Save to enriched CSV
os.makedirs("data", exist_ok=True)
output_path = "data/scheduled_games_and_starters_with_id.csv"
df.to_csv(output_path, index=False)
print(f"✅ Saved enriched CSV → {output_path}")
