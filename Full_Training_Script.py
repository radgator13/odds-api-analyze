import pandas as pd
import numpy as np
import sqlite3
import joblib
import json
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import sys

if sys.stdout.encoding.lower() != "utf-8":
    print("[WARN] Terminal does not support emojis. Using safe print style.")

# === Load all data ===
print("[INFO] Loading data...")
player_df = pd.read_csv("new_data/stathead_player_pitching_game_data.csv")
batting_df = pd.read_csv("new_data/stathead_batting_game_data.csv")
team_pitch_df = pd.read_csv("new_data/stathead_team_pitching_game_data.csv")

# === Clean pitcher data ===
print("[CLEAN] Cleaning pitcher data...")
player_df["Date"] = pd.to_datetime(player_df["Date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0])
age_parts = player_df["Age"].astype(str).str.extract(r"(\d+)-(\d+)")
age_parts = age_parts.dropna().astype(int)
player_df["age_float"] = age_parts[0] + age_parts[1] / 365.0

for col in ["IP", "BB", "BF", "H", "ER", "HR", "SO"]:
    player_df[col] = pd.to_numeric(player_df[col], errors="coerce")

player_df = player_df[player_df["IP"] >= 1.0]
player_df["K_per_IP"] = player_df["SO"] / player_df["IP"]
player_df["K_per_BF"] = player_df["SO"] / player_df["BF"]
player_df["WHIP"] = (player_df["BB"] + player_df["H"]) / player_df["IP"]
player_df["KBB"] = player_df["SO"] / player_df["BB"].replace(0, np.nan)
player_df["KBB"] = player_df["KBB"].fillna(0)
player_df["ERA_est"] = (player_df["ER"] * 9) / player_df["IP"]
player_df["is_home"] = player_df["Unnamed: 7"].apply(lambda x: 0 if str(x).strip() == "@" else 1)

# === Rolling averages (3-game) ===
print("[ROLL] Computing rolling stats...")
player_df = player_df.sort_values(by=["Player", "Date"])
rolling_feats = ["IP", "SO", "BB", "K_per_IP", "K_per_BF", "WHIP", "KBB", "ERA_est"]
for feat in rolling_feats:
    player_df[f"r3_{feat}"] = (
        player_df.groupby("Player", group_keys=False)[feat]
        .transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    )

# === Clean batting data ===
print("[CLEAN] Cleaning opponent batting...")
batting_df = batting_df.loc[:, ~batting_df.columns.str.contains("^Unnamed")]
batting_df = batting_df.loc[:, ~batting_df.columns.duplicated()]
batting_df["Date"] = pd.to_datetime(batting_df["Date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0])
for col in ["SO", "PA", "OBP", "SLG", "OPS", "BA"]:
    batting_df[col] = pd.to_numeric(batting_df[col], errors="coerce")
batting_df["opp_K_rate"] = batting_df["SO"] / batting_df["PA"]

# === Clean team pitching data ===
print("[CLEAN] Cleaning team pitching...")
team_pitch_df = team_pitch_df.loc[:, ~team_pitch_df.columns.str.contains("^Unnamed")]
team_pitch_df["Date"] = pd.to_datetime(team_pitch_df["Date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0])
for col in ["SO.1", "BF"]:
    team_pitch_df[col] = pd.to_numeric(team_pitch_df[col], errors="coerce")
team_pitch_df["team_K_rate"] = team_pitch_df["SO.1"] / team_pitch_df["BF"]
team_pitch_df = team_pitch_df.rename(columns={"Team": "Team_pitch"})

# === Merge all sources ===
print("[MERGE] Merging opponent and team stats...")
df = player_df.merge(
    batting_df[["Date", "Opp", "opp_K_rate", "OBP", "SLG", "OPS", "BA"]],
    on=["Date", "Opp"], how="left"
)
df = df.merge(
    team_pitch_df[["Date", "Team_pitch", "team_K_rate"]],
    left_on=["Date", "Team"],
    right_on=["Date", "Team_pitch"],
    how="left"
)

# === Final feature list ===
print("[PREP] Preparing features...")
base_features = [
    "IP", "BB", "BF", "H", "ER", "HR", "age_float", "is_home",
    "K_per_IP", "K_per_BF", "WHIP", "KBB", "ERA_est",
    "r3_IP", "r3_SO", "r3_BB", "r3_K_per_IP", "r3_K_per_BF", "r3_WHIP", "r3_KBB", "r3_ERA_est",
    "opp_K_rate", "OBP", "SLG", "OPS", "BA", "team_K_rate"
]

required = ["SO"] + base_features
df = df.dropna(subset=required)
X = df[base_features]
y = df["SO"]

# === Train model ===
print("[MODEL] Training model (RandomForest)...")
model = RandomForestRegressor(n_estimators=150, max_depth=6, random_state=42)
model.fit(X, y)

y_pred = model.predict(X)
mae = mean_absolute_error(y, y_pred)
r2 = r2_score(y, y_pred)
print(f"[METRIC] Model MAE: {mae:.2f} | R²: {r2:.3f}")

# === Save model and feature order ===
print("[SAVE] Saving model and features...")
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/strikeout_model.pkl")
with open("models/feature_order.json", "w") as f:
    json.dump(base_features, f)

# === Predict and export ===
print("[SQL] Saving predictions to SQLite...")
df["predicted_SO"] = y_pred
predictions = df[["Date", "Player", "Team", "Opp", "SO", "predicted_SO"]]

conn = sqlite3.connect("strikeout_predictions.db")
predictions.to_sql("predictions", conn, if_exists="replace", index=False)
conn.commit()
conn.close()

print("[DONE] All done. Model trained, saved, and predictions logged.")
