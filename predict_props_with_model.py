import pandas as pd
import numpy as np
import joblib
from difflib import get_close_matches
from datetime import date
import sys
import json

if sys.stdout.encoding.lower() != "utf-8":
    print("[WARN] Terminal does not support emojis. Using safe print style.")

# === Normalize names ===
def normalize_name(name):
    name = str(name).strip().lower()
    if "," in name:
        parts = name.split(",")
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name

# === Fuzzy match to closest stathead player ===
def fuzzy_match(name, candidate_list):
    match = get_close_matches(name, candidate_list, n=1, cutoff=0.85)
    return match[0] if match else None

# === Load sportsbook props ===
print("[LOAD] Loading sportsbook props...")
props = pd.read_csv("data/betonline_pitcher_props.csv")
props.columns = [c.strip().lower() for c in props.columns]

props = props[props["market"].str.lower().str.contains("pitcher_strikeout", na=False)]
props = props[props["raw_name"].isin(["Over", "Under"])]
props = props.dropna(subset=["description", "line", "odds", "commence_time"])
props["description"] = props["description"].apply(normalize_name)
props["game_date"] = pd.to_datetime(props["commence_time"]).dt.date

# === Deduplicate to one row per player
pitcher_lines = props.groupby("description").agg({
    "line": "first",
    "odds": "first",
    "raw_name": "first",
    "commence_time": "first",
    "game_date": "first"
}).reset_index().rename(columns={"description": "player"})

# === Load Stathead pitcher logs ===
print("[LOAD] Loading Stathead pitcher logs...")
stats = pd.read_csv("new_data/stathead_player_pitching_game_data.csv")
stats["Date"] = pd.to_datetime(stats["Date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0])
stats["Player_clean"] = stats["Player"].apply(normalize_name)

for col in ["IP", "BB", "BF", "H", "ER", "HR", "SO"]:
    stats[col] = pd.to_numeric(stats[col], errors="coerce")

age_parts = stats["Age"].astype(str).str.extract(r"(\d+)-(\d+)")
age_parts = age_parts.dropna().astype(int)
stats["age_float"] = age_parts[0] + age_parts[1] / 365.0
stats["K_per_IP"] = stats["SO"] / stats["IP"]
stats["K_per_BF"] = stats["SO"] / stats["BF"]

# === Rolling 3-game stats ===
print("[ROLL] Computing rolling stats...")
rolling_features = ["IP", "BB", "BF", "H", "ER", "HR", "K_per_IP", "K_per_BF", "age_float"]
for feat in rolling_features:
    stats[f"r3_{feat}"] = (
        stats
        .groupby("Player_clean", group_keys=False)
        .apply(lambda g: g[feat].shift(1).rolling(3, min_periods=1).mean())
    )

latest_stats = stats.groupby("Player_clean").last().reset_index()

# === Fuzzy match prop players to stathead
print("[MATCH] Matching props to stat logs with fuzzy logic...")
pitcher_lines["Player_clean"] = pitcher_lines["player"].apply(
    lambda name: fuzzy_match(name, latest_stats["Player_clean"].tolist())
)
pitcher_lines = pitcher_lines.dropna(subset=["Player_clean"])

# === Merge props and rolling stats ===
print("[MERGE] Merging stats into props...")
merged = pitcher_lines.merge(
    latest_stats,
    on="Player_clean",
    how="left"
)

if merged.empty:
    print("[FAIL] No matched pitchers. Check name formats or Stathead data freshness.")
    sys.exit(1)

print(f"[INFO] Merged rows: {len(merged)}")

# === Fill in default context
print("[PREP] Building model input...")
defaults = {
    "opp_K_rate": 0.215, "OBP": 0.312, "SLG": 0.410,
    "OPS": 0.722, "BA": 0.248, "team_K_rate": 0.220
}
for col, val in defaults.items():
    merged[col] = val
merged["is_home"] = 1

model_input = merged.rename(columns={
    "r3_IP": "IP", "r3_BB": "BB", "r3_BF": "BF", "r3_H": "H",
    "r3_ER": "ER", "r3_HR": "HR", "r3_K_per_IP": "K_per_IP",
    "r3_K_per_BF": "K_per_BF", "r3_age_float": "age_float"
})

# === Fallback stats for new pitchers
filler = {
    "IP": 5.2, "BB": 1.8, "BF": 23, "H": 4.5, "ER": 2.1, "HR": 0.8,
    "K_per_IP": 1.0, "K_per_BF": 0.22, "age_float": 28.5
}
for stat, val in filler.items():
    model_input[stat] = model_input[stat].fillna(val)

# === Load model
print("[MODEL] Loading model and predicting...")
model = joblib.load("models/strikeout_model.pkl")
with open("models/feature_order.json", "r") as f:
    expected_features = json.load(f)

for col in expected_features:
    if col not in model_input.columns:
        print(f"[FIX] Adding missing column: {col}")
        model_input[col] = 0.0
        # === Finalize input
model_input = model_input.loc[:, ~model_input.columns.duplicated(keep="last")]
X = model_input[expected_features].copy()


# Reorder strictly to match training input
X = model_input[expected_features].copy()
# === Debug shape and columns
print("[DEBUG] Expected columns from training:")
print(expected_features)

print("[DEBUG] Model input columns before predict():")
print(X.columns.tolist())

print("[DEBUG] Any mismatch?", set(expected_features) ^ set(X.columns.tolist()))


# === Predict and Output
if X.empty:
    print("[FAIL] No data available to predict.")
else:
    merged["predicted_SO"] = model.predict(X)
    merged["edge"] = merged["predicted_SO"] - merged["line"]
    merged["bet_recommendation"] = np.where(
        merged["edge"] > 0.75, "✅ Over",
        np.where(merged["edge"] < -0.75, "✅ Under", "❌ No Bet")
    )

    result = merged[[
        "game_date", "player", "line", "odds",
        "predicted_SO", "edge", "bet_recommendation"
    ]]

    today = date.today()
    print("\n[DATES] Game Dates Predicted:")
    print(result["game_date"].value_counts().sort_index())

    result.to_csv("data/predicted_pitcher_props_with_edges.csv", index=False)
    print("\n[SAVED] data/predicted_pitcher_props_with_edges.csv")
