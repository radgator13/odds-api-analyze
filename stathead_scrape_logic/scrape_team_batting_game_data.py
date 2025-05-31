import os
import time
import glob
import pandas as pd
import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# === Load credentials ===
load_dotenv()
USERNAME = os.getenv("STATHEAD_USERNAME")
PASSWORD = os.getenv("STATHEAD_PASSWORD")

LOGIN_URL = "https://stathead.com/users/login.cgi"
TARGET_URL = "https://stathead.com/baseball/team-batting-game-finder.cgi"

# === Paths ===
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
CSV_PATH = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\stathead_batting_game_data.csv"
ARCHIVE_DIR = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\archive"

# === Chrome setup: VISIBLE (headless removed) ===
options = Options()
# options.add_argument("--headless=new")  # <-- Removed for visual debugging
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")  # Required for consistent rendering

options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
})
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

def debug(label):
    path = f"{label}.png"
    driver.save_screenshot(path)
    print(f"📸 Screenshot saved: {path}")

try:
    print("🔐 Logging into Stathead...")
    driver.get(LOGIN_URL)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]'))).click()
    wait.until(EC.url_changes(LOGIN_URL))
    print("✅ Login successful.")
    debug("step0_logged_in")

    driver.get(TARGET_URL)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("🌐 Navigated to team batting finder.")
    debug("step1_target_loaded")
    # # === Click "Show Criteria" to reveal all fields
    # show_criteria = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#criteria_opener")))

    # show_criteria.click()
    # print("📂 Clicked 'Show Criteria'")
    # debug("step1b_show_criteria_clicked")
    # time.sleep(1)

    # # === Click 2025 ===
    # season_button = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@type="button" and text()="2025"]')))
    # driver.execute_script("arguments[0].click();", season_button)
    # print("📅 Clicked 2025 season button.")
    # debug("step2_clicked_2025")

    # === Select Last N Days ===
    last_n_radio = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@name="timeframe" and @value="last_n_days"]')))
    driver.execute_script("arguments[0].click();", last_n_radio)
    print("📆 Selected Last N Days radio.")
    debug("step3_selected_lastn")

    last_n_input = wait.until(EC.presence_of_element_located((By.NAME, "previous_days")))
    last_n_input.clear()
    last_n_input.send_keys("5")
    print("✍️ Entered 5.")
    debug("step4_entered_5")

    # === Click Get Results ===
    get_results = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@type="submit" and @value="Get Results"]')))
    driver.execute_script("arguments[0].click();", get_results)
    print("🚀 Clicked 'Get Results'")
    time.sleep(3)
    debug("step5_after_get_results")

    # === Wait 10 seconds for results to render ===
    print("⏳ Waiting 10 seconds for results to load...")
    time.sleep(10)

    # === Export ===
    export_menu = wait.until(EC.presence_of_element_located((By.XPATH, '//span[normalize-space()="Export Data"]')))
    ActionChains(driver).move_to_element(export_menu).perform()
    print("📂 Hovered on Export Data menu.")
    debug("step6_hover_export")

    time.sleep(1)
    export_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Get as Excel Workbook")]')))
    export_button.click()
    print("📥 Clicked 'Get as Excel Workbook'.")
    time.sleep(3)
    debug("step7_export_clicked")

    # === Use only latest downloaded file ===
    latest_xls = max(glob.glob(os.path.join(DOWNLOAD_DIR, "sportsref_download*.xls")), key=os.path.getmtime)
    print("📥 Using freshly downloaded XLS:", latest_xls)

    if os.path.getsize(latest_xls) < 1024:
        debug("step8_EMPTY_XLS")
        raise Exception("❌ Downloaded .xls appears to be empty or corrupt.")

    df = pd.read_html(latest_xls, flavor="bs4")[0]

    # === Append new data ===
    print("📂 Confirmed full CSV path:", CSV_PATH)

    if os.path.exists(CSV_PATH):
        existing_df = pd.read_csv(CSV_PATH)
        print(f"📊 Loaded rows from main file: {len(existing_df)}")
        print(f"🧪 Columns (existing): {existing_df.columns.tolist()}")
        print(f"🧪 Columns (new): {df.columns.tolist()}")

        combined_df = pd.concat([existing_df, df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["Team", "Date", "Opp", "Result"]).reset_index(drop=True)

        print(f"✅ Final row count after merge: {len(combined_df)}")
    else:
        print("🆕 No existing file found, creating a new one.")
        combined_df = df

    # Save to main file
    combined_df.to_csv(CSV_PATH, index=False)
    print(f"✅ Saved updated CSV: {CSV_PATH}")
    debug("step8_csv_saved")

    # === Archive full copy ===
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(ARCHIVE_DIR, f"stathead_team_batting_game_data_{timestamp}.csv")
    combined_df.to_csv(archive_path, index=False)
    print(f"🗄️ Archived to: {archive_path}")

finally:
    driver.quit()
    print("✅ Done. Browser closed.")
