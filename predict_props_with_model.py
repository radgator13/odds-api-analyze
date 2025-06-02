import pandas as pd
import numpy as np
import joblib
from difflib import get_close_matches
from datetime import date, datetime, timedelta
import sys
import json
import sqlite3
import os

if sys.stdout.encoding.lower() != "utf-8":
    print("[WARN] Terminal does not support emojis. Using safe print style.")

def normalize_name(name):
    name = str(name).strip().lower()
    if "," in name:
        parts = name.split(",")
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name

def fuzzy_match(name, candidate_list):
    match = get_close_matches(name, candidate_list, n=1, cutoff=0.85)
    return match[0] if match else None

print("[LOAD] Loading sportsbook props...")
props = pd.read_csv("data/betonline_pitcher_props.csv")
props.columns = [c.strip().lower() for c in props.columns]
props = props[props["market"].str.lower().str.contains("pitcher_strikeout", na=False)]
props = props[props["raw_name"].isin(["Over", "Under"])]
props = props.dropna(subset=["description", "line", "odds", "commence_time"])
props["description"] = props["description"].apply(normalize_name)
props["game_date"] = pd.to_datetime(props["commence_time"]).dt.date

pitcher_lines = props.groupby("description").agg({
    "line": "first",
    "odds": "first",
    "raw_name": "first",
    "commence_time": "first",
    "game_date": "first"
}).reset_index().rename(columns={"description": "player"})

print("[LOAD] Loading Stathead pitcher logs...")
stats = pd.read_csv("new_data/stathead_player_pitching_game_data.csv")
stats["Date"] = pd.to_datetime(stats["Date"], errors="coerce")
stats = stats.dropna(subset=["Date"])
stats["game_date"] = stats["Date"].dt.date
stats["Player_clean"] = stats["Player"].apply(normalize_name)

for col in ["IP", "BB", "BF", "H", "ER", "HR", "SO"]:
    stats[col] = pd.to_numeric(stats[col], errors="coerce")

age_parts = stats["Age"].astype(str).str.extract(r"(\d+)-(\d+)")
age_parts = age_parts.dropna().astype(int)
stats["age_float"] = age_parts[0] + age_parts[1] / 365.0
stats["K_per_IP"] = stats["SO"] / stats["IP"]
stats["K_per_BF"] = stats["SO"] / stats["BF"]

print("[ROLL] Computing rolling stats...")
rolling_features = ["IP", "BB", "BF", "H", "ER", "HR", "K_per_IP", "K_per_BF", "age_float"]
for feat in rolling_features:
    stats[f"r3_{feat}"] = (
        stats
        .groupby("Player_clean", group_keys=False)
        .apply(lambda g: g[feat].shift(1).rolling(3, min_periods=1).mean(), include_groups=False)
    )

latest_stats = stats.groupby("Player_clean").last().reset_index()

print("[MATCH] Matching props to stat logs with fuzzy logic...")
pitcher_lines["Player_clean"] = pitcher_lines["player"].apply(
    lambda name: fuzzy_match(name, latest_stats["Player_clean"].tolist())
)
pitcher_lines = pitcher_lines.dropna(subset=["Player_clean"])

print("[MERGE] Merging stats into props...")
merged = pitcher_lines.merge(latest_stats, on="Player_clean", how="left")
merged["game_date"] = pitcher_lines["game_date"]

if merged.empty:
    print("[FAIL] No matched pitchers. Check name formats or Stathead data freshness.")
    sys.exit(1)

print(f"[INFO] Merged rows: {len(merged)}")

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

# === Enhanced fallback stats
filler = {
    "IP": 5.5, "BB": 1.8, "BF": 24, "H": 4.6, "ER": 2.4, "HR": 0.9,
    "K_per_IP": 1.15, "K_per_BF": 0.25, "age_float": 28.0
}
for stat, val in filler.items():
    model_input[stat] = model_input[stat].fillna(val)

print("[MODEL] Loading model and predicting...")
model = joblib.load("models/strikeout_model.pkl")
with open("models/feature_order.json", "r") as f:
    expected_features = json.load(f)

for col in expected_features:
    if col not in model_input.columns:
        print(f"[FIX] Adding missing column: {col}")
        model_input[col] = 0.0

model_input = model_input.loc[:, ~model_input.columns.duplicated(keep="last")]
X = model_input[expected_features].copy()

if X.empty:
    print("[FAIL] No data available to predict.")
    sys.exit(1)

# === Make predictions
merged["predicted_SO"] = model.predict(X)
merged["predicted_SO"] *= 1.10  # optional boost
merged["edge"] = merged["predicted_SO"] - merged["line"]
merged["bet_recommendation"] = np.where(
    merged["edge"] > 0.75, "✅ Over",
    np.where(merged["edge"] < -0.75, "✅ Under", "❌ No Bet")
)

# === Calibration Debug
print(f"[DEBUG] Avg Market Line: {merged['line'].mean():.2f}")
print(f"[DEBUG] Avg Predicted SO: {merged['predicted_SO'].mean():.2f}")
print(f"[DEBUG] Avg Edge: {merged['edge'].mean():.2f}")

result = merged[[
    "game_date", "player", "line", "odds",
    "predicted_SO", "edge", "bet_recommendation"
]]

print("\n[DATES] Game Dates Predicted:")
print(result["game_date"].value_counts().sort_index())
result.to_csv("data/predicted_pitcher_props_with_edges.csv", index=False)
print("[SAVED] data/predicted_pitcher_props_with_edges.csv")

# === SQLite output
print("[SQL] Saving predictions to SQLite...")
db_path = "data/strikeout_model_bets.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS bets (
    game_date TEXT,
    player TEXT,
    line REAL,
    odds TEXT,
    predicted_SO REAL,
    edge REAL,
    bet_recommendation TEXT,
    confidence TEXT,
    actual_SO REAL,
    result_hit TEXT,
    timestamp TEXT
)
""")

def confidence_level(edge):
    abs_edge = abs(edge)
    if abs_edge >= 3: return "🔥🔥🔥🔥🔥"
    elif abs_edge >= 2: return "🔥🔥🔥🔥"
    elif abs_edge >= 1.5: return "🔥🔥🔥"
    elif abs_edge >= 1: return "🔥🔥"
    elif abs_edge >= 0.75: return "🔥"
    return ""

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
for _, row in result.iterrows():
    cursor.execute("""
    INSERT INTO bets (
        game_date, player, line, odds,
        predicted_SO, edge, bet_recommendation,
        confidence, actual_SO, result_hit, timestamp
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
    """, (
        str(row["game_date"]),
        row["player"],
        float(row["line"]),
        str(row["odds"]),
        float(row["predicted_SO"]),
        float(row["edge"]),
        row["bet_recommendation"],
        confidence_level(row["edge"]),
        now
    ))

conn.commit()
print("[OK] Saved to", db_path)
conn.close()
