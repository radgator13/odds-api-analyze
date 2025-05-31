import os
import time
import glob
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import builtins

# === Safe print for Unicode
original_print = builtins.print
def safe_print(*args, **kwargs):
    try:
        original_print(*args, **kwargs)
    except UnicodeEncodeError:
        fallback = [str(arg).encode('ascii', errors='ignore').decode() for arg in args]
        original_print(*fallback, **kwargs)
builtins.print = safe_print

# === Load credentials
load_dotenv()
USERNAME = os.getenv("STATHEAD_USERNAME")
PASSWORD = os.getenv("STATHEAD_PASSWORD")

# === Paths
DOWNLOAD_DIR = os.path.abspath("downloads")
CSV_TARGET_DIR = r"C:\Users\a1d3r\source\repos\MLB Spreads-OU-V1.01\new_data"
LOGIN_URL = "https://stathead.com/users/login.cgi"

today = date.today()
five_days_ago = (today - timedelta(days=5)).strftime('%Y-%m-%d')
today_str = today.strftime('%Y-%m-%d')




# === Target URLs with fixed date range
URLS = {
    "batting": f"https://stathead.com/baseball/team-batting-game-finder.cgi?request=1&order_by=date&fromdate={five_days_ago}&todate={today_str}",
    "team_pitching": f"https://stathead.com/baseball/team-pitching-game-finder.cgi?request=1&order_by=date&fromdate={five_days_ago}&todate={today_str}",
    "player_pitching": f"https://stathead.com/baseball/player-pitching-game-finder.cgi?request=1&order_by=p_ip&cstat[1]=p_ip&ccomp[1]=gt&cval[1]=3.5&fromdate={five_days_ago}&todate={today_str}",
    "game_logs": f"https://stathead.com/baseball/team-batting-game-finder.cgi?request=1&order_by=date&fromdate={five_days_ago}&todate={today_str}"
}





OUTPUT_FILES = {
    "batting": "stathead_batting_game_data.csv",
    "team_pitching": "stathead_team_pitching_game_data.csv",
    "player_pitching": "stathead_player_pitching_game_data.csv",
    "game_logs": "stathead_game_logs.csv"
}

# === Headless browser setup
options = Options()
options.add_argument("--headless=new")
options.add_argument("--start-maximized")
options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
})
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# === Export and deduplication logic
def download_and_convert(url: str, output_filename: str):
    print(f"\n🌐 Navigating to {url}")
    driver.get(url)
    step = 1

    try:
        # === Show Criteria
        show_criteria = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Show Criteria")]')))
        show_criteria.click()
        driver.save_screenshot(f"step{step}_show_criteria.png"); step += 1
        print("📂 Show Criteria clicked.")
        time.sleep(1)

        # === Click season 2025 (label click is safer than input)
        season_label = wait.until(EC.element_to_be_clickable((By.XPATH, '//label[contains(text(), "2025")]')))
        season_label.click()
        driver.save_screenshot(f"step{step}_season_2025.png"); step += 1
        print("📆 Season 2025 selected.")
        time.sleep(0.5)

        # === Click "Last N Days"
        last_n_radio = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@name="timeframe" and @value="last_n_days"]')))
        driver.execute_script("arguments[0].click();", last_n_radio)
        driver.save_screenshot(f"step{step}_lastn_selected.png"); step += 1
        print("📅 Last N Days selected.")
        time.sleep(0.5)

        # === Enter 5 into box
        last_n_input = wait.until(EC.presence_of_element_located((By.NAME, "previous_days")))
        last_n_input.clear()
        last_n_input.send_keys("5")
        driver.save_screenshot(f"step{step}_lastn_filled.png"); step += 1
        print("🕔 Entered 5 days.")

        # === Player pitching filters
        if "player-pitching" in url:
            try:
                from selenium.webdriver.support.ui import Select
                Select(driver.find_element(By.NAME, "cstat[1]")).select_by_value("p_ip")
                Select(driver.find_element(By.NAME, "ccomp[1]")).select_by_value("gt")
                val = driver.find_element(By.NAME, "cval[1]")
                val.clear()
                val.send_keys("3.5")
                driver.save_screenshot(f"step{step}_ip_filter.png"); step += 1
                print("🎯 IP > 3.5 filter set.")
            except Exception as e:
                print("⚠️ Could not set IP > 3.5 filter:", e)

        # === Click "Get Results"
        get_results = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Get Results")]')))
        get_results.click()
        driver.save_screenshot(f"step{step}_after_get_results.png"); step += 1
        print("🔁 Get Results clicked.")
        time.sleep(3)

    except Exception as e:
        driver.save_screenshot(f"step{step}_ERROR.png")
        print(f"❌ Failed to configure filters for {output_filename}: {e}")
        return

    # === Wait for table or export button
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "stats_table")] | //span[normalize-space()="Export Data"]')))
    except:
        driver.save_screenshot(f"step{step}_no_results.png")
        print(f"❌ No results or export found for {output_filename}.")
        return

    # === Export
    try:
        export_span = wait.until(EC.presence_of_element_located((By.XPATH, '//span[normalize-space()="Export Data"]')))
        ActionChains(driver).move_to_element(export_span).perform()
        time.sleep(1)
        export_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Get as Excel Workbook")]')))
        export_button.click()
        driver.save_screenshot(f"step{step}_export_clicked.png"); step += 1
        print(f"✅ Export clicked for {output_filename}. Waiting for download...")
        time.sleep(10)
    except Exception as e:
        driver.save_screenshot(f"step{step}_export_FAIL.png")
        print(f"❌ Export failed for {output_filename}: {e}")
        return

    # === Read and save
    xls_files = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "*.xls")), key=os.path.getmtime, reverse=True)
    if not xls_files:
        raise FileNotFoundError("❌ No .xls file found after export.")

    latest_xls = xls_files[0]
    df_new = pd.read_html(latest_xls, flavor="bs4")[0]
    os.remove(latest_xls)

    csv_path = os.path.join(CSV_TARGET_DIR, output_filename)
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        before = len(df_existing)
        combined = pd.concat([df_existing, df_new], ignore_index=True).drop_duplicates()
        after = len(combined)
        added = after - before
        combined.to_csv(csv_path, index=False)
        if added == 0:
            print(f"⚠️ No new rows added to {output_filename} (all duplicates)")
        else:
            print(f"✅ Appended {added} new rows to {output_filename}")
    else:
        df_new.to_csv(csv_path, index=False)
        print(f"✅ Created {output_filename} with {len(df_new)} rows")



    # === Parse and Save ===
    xls_files = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "*.xls")), key=os.path.getmtime, reverse=True)
    if not xls_files:
        raise FileNotFoundError("❌ No .xls file found after export.")

    latest_xls = xls_files[0]
    df_new = pd.read_html(latest_xls, flavor="bs4")[0]
    os.remove(latest_xls)

    csv_path = os.path.join(CSV_TARGET_DIR, output_filename)
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        before = len(df_existing)
        combined = pd.concat([df_existing, df_new], ignore_index=True).drop_duplicates()
        after = len(combined)
        added = after - before
        combined.to_csv(csv_path, index=False)
        if added == 0:
            print(f"⚠️ No new rows added to {output_filename} (all duplicates)")
        else:
            print(f"✅ Appended {added} new rows to {output_filename}")
    else:
        df_new.to_csv(csv_path, index=False)
        print(f"✅ Created {output_filename} with {len(df_new)} rows")



# === Main process
try:
    print("🔐 Logging into Stathead...")
    driver.get(LOGIN_URL)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]'))).click()
    wait.until(EC.url_changes(LOGIN_URL))
    print("✅ Login successful.")

    # Process each export
    for key in URLS:
        download_and_convert(URLS[key], OUTPUT_FILES[key])

finally:
    driver.quit()
    print("\n✅ All exports complete. Browser closed.")
