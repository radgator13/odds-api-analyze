import pandas as pd
import os
import re
from datetime import datetime
from difflib import get_close_matches

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

valid_files = [f for f in bet_files if extract_date_from_filename(f) and extract_date_from_filename(f) < today]
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
rename_map = {'game_date': 'Game_Date', 'player': 'Pitcher', 'predicted_SO': 'Predicted_K'}
all_bets.rename(columns=rename_map, inplace=True)

# === COLUMN CHECK ===
required_cols = ['Game_Date', 'Pitcher', 'Predicted_K']
missing = [col for col in required_cols if col not in all_bets.columns]
if missing:
    print(f"❌ ERROR: Missing required column(s): {missing}")
    exit()

# === CLEANING ===
all_bets['Game_Date'] = pd.to_datetime(all_bets['Game_Date']).dt.date
all_bets['Pitcher'] = all_bets['Pitcher'].astype(str).str.lower().str.strip().str.replace(r"[^\w\s]", "", regex=True)
all_bets['Pitcher_clean'] = all_bets['Pitcher']

# === LOAD STATS FILE ===
try:
    actuals = pd.read_csv(stats_file)
    print("\n✅ Loaded actual stats:", stats_file)
    print("   Columns:", actuals.columns.tolist())
except FileNotFoundError:
    print(f"❌ ERROR: File not found -> {stats_file}")
    exit()

# === ACTUALS CLEANING ===
actuals.rename(columns={'Date': 'Game_Date', 'Player': 'Pitcher', 'SO': 'Strikeouts'}, inplace=True)
actuals['Game_Date'] = pd.to_datetime(actuals['Game_Date'], errors='coerce').dt.date
actuals['Pitcher'] = actuals['Pitcher'].astype(str).str.lower().str.strip().str.replace(r"[^\w\s]", "", regex=True)
actuals['Pitcher_clean'] = actuals['Pitcher']
actuals = actuals.dropna(subset=['Game_Date', 'Pitcher', 'Strikeouts'])

# 🆕 Keep one row per Game_Date + Pitcher_clean (latest row if duplicates exist)
actuals = actuals.sort_values("Game_Date")
actuals = actuals.groupby(['Game_Date', 'Pitcher_clean'], as_index=False).agg({"Strikeouts": "last"})


# === FUZZY MATCHING ===
print("\n🔁 Performing fuzzy name matching...")
actual_names = actuals['Pitcher_clean'].dropna().unique().tolist()
pitcher_map = {}

for name in all_bets['Pitcher_clean'].unique():
    match = get_close_matches(name, actual_names, n=1, cutoff=0.80)
    if match:
        pitcher_map[name] = match[0]
    else:
        print(f"[NO MATCH] '{name}' — closest: {get_close_matches(name, actual_names, n=3, cutoff=0.5)}")

all_bets['Pitcher_fuzzy'] = all_bets['Pitcher_clean'].map(pitcher_map)
actuals['Pitcher_fuzzy'] = actuals['Pitcher_clean']

# === MERGE ===
merged = pd.merge(
    all_bets,
    actuals[['Game_Date', 'Pitcher_fuzzy', 'Strikeouts']],
    left_on=['Game_Date', 'Pitcher_fuzzy'],
    right_on=['Game_Date', 'Pitcher_fuzzy'],
    how='left'
)

# === Handle unmatched rows with fallback name-only match ===
unmatched = merged[merged['Strikeouts'].isna()].copy()
print("\n=== ⚠️ UNMATCHED PREDICTIONS (exact date match failed) ===")
print(unmatched[['Game_Date', 'Pitcher']].drop_duplicates().to_string(index=False))

# === Fallback: Try to match by name only (last known game) ===
fallback_matches = []
for _, row in unmatched.iterrows():
    fuzzy_name = row['Pitcher_fuzzy']
    possible = actuals[actuals['Pitcher_fuzzy'] == fuzzy_name]
    if not possible.empty:
        latest = possible.sort_values("Game_Date").iloc[-1]
        row['Strikeouts'] = latest['Strikeouts']
        fallback_matches.append(row)

# Combine successful matches and fallback
if fallback_matches:
    fallback_df = pd.DataFrame(fallback_matches)
    matched_df = merged[~merged.index.isin(unmatched.index)]
    merged = pd.concat([matched_df, fallback_df], ignore_index=True)

# === Sample from actuals ===
print("\n=== 🔍 Sample ACTUALS (cleaned) ===")
print(actuals[['Game_Date', 'Pitcher_clean', 'Strikeouts']].dropna().sample(10).to_string(index=False))



# === DETERMINE RESULTS ===
def compare(row):
    if pd.isna(row['Strikeouts']) or pd.isna(row['Predicted_K']):
        return 'No Data'
    elif row['Strikeouts'] > row['Predicted_K']:
        return 'Over'
    elif row['Strikeouts'] < row['Predicted_K']:
        return 'Under'
    else:
        return 'Push'

merged['Result'] = merged.apply(compare, axis=1)

# === OUTPUT ===
print("\n=== ✅ Summary of Predictions vs Actuals ===")
print(merged[['Game_Date', 'Pitcher', 'Predicted_K', 'Strikeouts', 'Result']])

# === EXPORT ===
output_file = "data/bets_vs_actuals_strikeouts.csv"
merged.to_csv(output_file, index=False)
print(f"\n📁 Output saved to {output_file}")
