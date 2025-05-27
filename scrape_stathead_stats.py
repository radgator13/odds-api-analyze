import os
import time
import glob
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import builtins
import sys
original_print = builtins.print

def safe_print(*args, **kwargs):
    try:
        original_print(*args, **kwargs)
    except UnicodeEncodeError:
        fallback = [str(arg).encode('ascii', errors='ignore').decode() for arg in args]
        original_print(*fallback, **kwargs)

builtins.print = safe_print


# === LOAD .env VARIABLES
load_dotenv()
USERNAME = os.getenv("STATHEAD_USERNAME")
PASSWORD = os.getenv("STATHEAD_PASSWORD")

# === PATHS
DOWNLOAD_DIR = os.path.abspath("downloads")
CSV_TARGET_DIR = r"C:\Users\a1d3r\source\repos\MLB Spreads-OU-V1.01\new_data"

LOGIN_URL = "https://stathead.com/users/login.cgi"
URLS = {
    "batting": "https://stathead.com/baseball/team-batting-game-finder.cgi?request=1&order_by=date&timeframe=last_n_days&previous_days=3",
    "team_pitching": "https://stathead.com/baseball/team-pitching-game-finder.cgi?request=1&timeframe=last_n_days&previous_days=3",
    "player_pitching": "https://stathead.com/baseball/player-pitching-game-finder.cgi?request=1&order_by=p_ip&timeframe=last_n_days&previous_days=3&ccomp%5B1%5D=gt&cval%5B1%5D=3.5&cstat%5B1%5D=p_ip",
    "game_logs": "https://stathead.com/baseball/team-batting-game-finder.cgi?request=1&timeframe=last_n_days&previous_days=3"
}

OUTPUT_FILES = {
    "batting": "stathead_batting_game_data.csv",
    "team_pitching": "stathead_team_pitching_game_data.csv",
    "player_pitching": "stathead_player_pitching_game_data.csv",
    "game_logs": "stathead_game_logs.csv"
}

# === SETUP HEADLESS CHROME
options = Options()
options.add_argument("--headless=new")  # ✅ Headless mode (no browser window)
options.add_argument("--start-maximized")
options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
})

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

def download_and_convert(url: str, output_filename: str):
    print(f"\n🌐 Navigating to {url}")
    driver.get(url)

    # Hover on Export Data dropdown
    export_span = wait.until(EC.presence_of_element_located(
        (By.XPATH, '//span[normalize-space()="Export Data"]')
    ))
    ActionChains(driver).move_to_element(export_span).perform()
    time.sleep(1)

    # Click "Get as Excel Workbook"
    export_button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, '//button[contains(text(), "Get as Excel Workbook")]')
    ))
    export_button.click()

    print(f"✅ Export clicked for {output_filename}. Waiting for download...")
    time.sleep(10)

    # Convert latest .xls to .csv
    xls_files = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "*.xls")), key=os.path.getmtime, reverse=True)
    if not xls_files:
        raise FileNotFoundError("❌ No .xls file found after export.")
    
    latest_xls = xls_files[0]
    df = pd.read_html(latest_xls, flavor="bs4")[0]
    csv_path = os.path.join(CSV_TARGET_DIR, output_filename)
    # Append if file exists; write header only if it's a new file
    write_header = not os.path.exists(csv_path)
    df.to_csv(csv_path, mode="a", header=write_header, index=False)
    print(f"✅ Appended {len(df)} rows to {csv_path}")
    print(f"✅ Saved CSV to {csv_path}")

try:
    # === LOGIN
    driver.get(LOGIN_URL)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]'))).click()
    wait.until(EC.url_changes(LOGIN_URL))
    print("✅ Logged in successfully.")

    # === RUN EXPORTS
    for key in URLS:
        download_and_convert(URLS[key], OUTPUT_FILES[key])

finally:
    driver.quit()
    print("\n✅ All exports complete. Browser closed.")
