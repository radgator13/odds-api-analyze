import pandas as pd
import os
import re
from datetime import datetime

# === CONFIG ===
bets_dir = "filtered_bets"
stats_file = "new_data/stathead_player_pitching_game_data.csv"

today = datetime.today().date()

# === EXTRACT DATE FROM FILENAME ===
def extract_date_from_filename(filename):
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    return None

# === COLLECT VALID FILES ===
bet_files = [
    os.path.join(bets_dir, f)
    for f in os.listdir(bets_dir)
    if f.endswith(".csv") and "filtered_bets_" in f
]

valid_files = []
for f in bet_files:
    file_date = extract_date_from_filename(f)
    if file_date and file_date < today:
        valid_files.append(f)

if not valid_files:
    print("⚠️ No valid filtered_bets CSVs found before today.")
    exit()

# === DEBUG: INSPECT FILES ===
print("=== DEBUG: Valid bet files loaded ===")
dfs = []
for f in valid_files:
    print(f"\n→ Reading: {f}")
    try:
        df = pd.read_csv(f)
        print("   Columns:", df.columns.tolist())
        if not df.empty:
            print("   Sample row:", df.iloc[0].to_dict())
            dfs.append(df)
        else:
            print("   ⚠️ Skipped: File is empty.")
    except Exception as e:
        print("   ❌ Error reading file:", e)

if not dfs:
    print("❌ All valid files are empty or failed to load.")
    exit()

# === MERGE & DEDUPLICATE ===
all_bets = pd.concat(dfs, ignore_index=True).drop_duplicates()

# === RENAME TO EXPECTED NAMES ===
rename_map = {
    'game_date': 'Game_Date',
    'player': 'Pitcher',
    'predicted_SO': 'Predicted_K'
}
all_bets.rename(columns=rename_map, inplace=True)

# === COLUMN CHECK ===
required_cols = ['Game_Date', 'Pitcher', 'Predicted_K']
missing = [col for col in required_cols if col not in all_bets.columns]
if missing:
    print(f"❌ ERROR: Missing required column(s): {missing}")
    print("Available columns in all_bets:", all_bets.columns.tolist())
    exit()

# === CLEANING ===
all_bets['Game_Date'] = pd.to_datetime(all_bets['Game_Date']).dt.date
all_bets['Pitcher'] = all_bets['Pitcher'].str.lower().str.strip()

# === LOAD STATS FILE ===
try:
    actuals = pd.read_csv(stats_file)
    print("\n✅ Loaded actual stats:", stats_file)
    print("   Columns:", actuals.columns.tolist())
except FileNotFoundError:
    print(f"❌ ERROR: File not found -> {stats_file}")
    exit()

# === ACTUALS CLEANING ===
# === RENAME ACTUALS COLUMNS TO MATCH EXPECTED NAMES ===
actuals.rename(columns={
    'Date': 'Game_Date',
    'Player': 'Pitcher',
    'SO': 'Strikeouts'
}, inplace=True)

required_actuals = ['Game_Date', 'Pitcher', 'Strikeouts']
missing_actuals = [col for col in required_actuals if col not in actuals.columns]
if missing_actuals:
    print(f"❌ ERROR: Missing required column(s) in actuals: {missing_actuals}")
    print("Available columns in actuals:", actuals.columns.tolist())
    exit()


# Strip any trailing notes like " (2)" from the raw date strings
actuals['Game_Date'] = (
    actuals['Game_Date']
    .astype(str)
    .str.extract(r'(\d{4}-\d{2}-\d{2})')[0]  # extract clean date
)

# Convert to datetime.date
actuals['Game_Date'] = pd.to_datetime(actuals['Game_Date'], errors='coerce').dt.date
if actuals['Game_Date'].isna().any():
    print("⚠️ WARNING: Some rows in actuals had invalid or missing Game_Date values after cleanup.")
    print(actuals[actuals['Game_Date'].isna()][['Pitcher', 'Game_Date']])


actuals['Pitcher'] = actuals['Pitcher'].str.lower().str.strip()

# === MERGE ===
merged = pd.merge(
    all_bets,
    actuals[['Game_Date', 'Pitcher', 'Strikeouts']],
    on=['Game_Date', 'Pitcher'],
    how='left'
)
unmatched = merged[merged['Strikeouts'].isna()]
print("\n=== ⚠️ UNMATCHED PREDICTIONS ===")
print(unmatched[['Game_Date', 'Pitcher']].drop_duplicates().to_string(index=False))

# Show sample from actuals to help comparison
print("\n=== 🔍 Sample ACTUALS (cleaned) ===")
print(actuals[['Game_Date', 'Pitcher', 'Strikeouts']].dropna().sample(10).to_string(index=False))

# === DETERMINE RESULTS ===
def compare(row):
    try:
        if pd.isna(row['Strikeouts']) or pd.isna(row['Predicted_K']):
            return 'No Data'
        elif row['Strikeouts'] > row['Predicted_K']:
            return 'Over'
        elif row['Strikeouts'] < row['Predicted_K']:
            return 'Under'
        else:
            return 'Push'
    except:
        return 'Error'

merged['Result'] = merged.apply(compare, axis=1)

# === OUTPUT ===
print("\n=== ✅ Summary of Predictions vs Actuals ===")
print(merged[['Game_Date', 'Pitcher', 'Predicted_K', 'Strikeouts', 'Result']])

# === EXPORT ===
output_file = "bets_vs_actuals_strikeouts.csv"
merged.to_csv(output_file, index=False)
print(f"\n📁 Output saved to {output_file}")
