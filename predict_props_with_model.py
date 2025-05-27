import pandas as pd
import numpy as np
import joblib

# === Normalize names ===
def normalize_name(name):
    name = str(name).strip().lower()
    if "," in name:
        parts = name.split(",")
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name

# === Load sportsbook props ===
print("🔄 Loading sportsbook props...")
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

# === Load pitcher logs ===
print("📚 Loading Stathead pitcher logs...")
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
print("📈 Computing rolling stats...")
rolling_features = ["IP", "BB", "BF", "H", "ER", "HR", "K_per_IP", "K_per_BF", "age_float"]
for feat in rolling_features:
    stats[f"r3_{feat}"] = (
        stats
        .groupby("Player_clean", group_keys=False)
        .apply(lambda g: g[feat].shift(1).rolling(3, min_periods=1).mean())
    )

latest_stats = stats.groupby("Player_clean").last().reset_index()

# === Merge rolling stats into props ===
print("🔗 Merging rolling stats into props...")
merged = pitcher_lines.merge(
    latest_stats,
    left_on="player",
    right_on="Player_clean",
    how="left"
)

print(f"🔢 Merged rows: {len(merged)}")
print("✅ Using fallback values where needed.")

# === Build model input ===
print("⚙️ Building model input...")
defaults = {
    "opp_K_rate": 0.215,
    "OBP": 0.312,
    "SLG": 0.410,
    "OPS": 0.722,
    "BA": 0.248,
    "team_K_rate": 0.220
}
for col, val in defaults.items():
    merged[col] = val
merged["is_home"] = 1

model_input = merged.rename(columns={
    "r3_IP": "IP", "r3_BB": "BB", "r3_BF": "BF", "r3_H": "H",
    "r3_ER": "ER", "r3_HR": "HR", "r3_K_per_IP": "K_per_IP",
    "r3_K_per_BF": "K_per_BF", "r3_age_float": "age_float"
})

filler = {
    "IP": 5.2, "BB": 1.8, "BF": 23, "H": 4.5, "ER": 2.1, "HR": 0.8,
    "K_per_IP": 1.0, "K_per_BF": 0.22, "age_float": 28.5
}
for stat, val in filler.items():
    model_input[stat] = model_input[stat].fillna(val)

# === Load model and predict ===
print("📦 Loading model and predicting...")
model = joblib.load("models/strikeout_model.pkl")
expected_features = list(model.feature_names_in_)

for col in expected_features:
    if col not in model_input.columns:
        print(f"🔧 Adding missing column: {col}")
        model_input[col] = 0.0
model_input = model_input.loc[:, ~model_input.columns.duplicated(keep="last")]
X = model_input[expected_features]

# === Predict
if len(X) == 0:
    print("🚨 No rows to predict.")
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
    print("\n🔍 Final Betting Edge Table:")
    print(result)

    result.to_csv("predicted_pitcher_props_with_edges.csv", index=False)
    print("\n📁 Saved to: predicted_pitcher_props_with_edges.csv")
