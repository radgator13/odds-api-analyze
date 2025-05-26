import pandas as pd
import sqlite3
import joblib
from sklearn.linear_model import LinearRegression

# === Load all data ===
print("🔄 Loading data...")
player_df = pd.read_csv("new_data/stathead_player_pitching_game_data.csv")
batting_df = pd.read_csv("new_data/stathead_batting_game_data.csv")
team_pitch_df = pd.read_csv("new_data/stathead_team_pitching_game_data.csv")

# === Clean & engineer pitcher data ===
print("⚙️ Cleaning pitcher data...")
player_df["Date"] = pd.to_datetime(player_df["Date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0], errors="coerce")
age_parts = player_df["Age"].astype(str).str.extract(r"(\d+)-(\d+)")
age_parts = age_parts.dropna().astype(int)
player_df["age_float"] = age_parts[0] + age_parts[1] / 365.0
for col in ["IP", "BB", "BF", "H", "ER", "HR", "SO"]:
    player_df[col] = pd.to_numeric(player_df[col], errors="coerce")
player_df = player_df[player_df["IP"] >= 4.0]
player_df["K_per_IP"] = player_df["SO"] / player_df["IP"]
player_df["K_per_BF"] = player_df["SO"] / player_df["BF"]
player_df["is_home"] = player_df["Unnamed: 7"].apply(lambda x: 0 if str(x).strip() == "@" else 1)

# === Clean batting data ===
print("🧹 Cleaning opponent batting...")
batting_df = batting_df.loc[:, ~batting_df.columns.str.contains("^Unnamed")]
batting_df = batting_df.loc[:, ~batting_df.columns.duplicated()]
batting_df["Date"] = pd.to_datetime(batting_df["Date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0], errors="coerce")
for col in ["SO", "PA", "OBP", "SLG", "OPS", "BA"]:
    batting_df[col] = pd.to_numeric(batting_df[col], errors="coerce")
batting_df["opp_K_rate"] = batting_df["SO"] / batting_df["PA"]

# === Clean team pitching data ===
print("🧹 Cleaning team pitching...")
team_pitch_df = team_pitch_df.loc[:, ~team_pitch_df.columns.str.contains("^Unnamed")]
team_pitch_df["Date"] = pd.to_datetime(team_pitch_df["Date"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2})")[0], errors="coerce")
for col in ["SO.1", "BF"]:
    team_pitch_df[col] = pd.to_numeric(team_pitch_df[col], errors="coerce")
team_pitch_df["team_K_rate"] = team_pitch_df["SO.1"] / team_pitch_df["BF"]
team_pitch_df = team_pitch_df.rename(columns={"Team": "Team_pitch"})

# === Merge opponent batting (left) ===
print("🔗 Merging opponent batting...")
df = player_df.merge(
    batting_df[["Date", "Opp", "opp_K_rate", "OBP", "SLG", "OPS", "BA"]],
    on=["Date", "Opp"],
    how="left"
)

# === Merge team pitching (left) ===
print("🔗 Merging team pitching...")
df = df.merge(
    team_pitch_df[["Date", "Team_pitch", "team_K_rate"]],
    left_on=["Date", "Team"],
    right_on=["Date", "Team_pitch"],
    how="left"
)

# === Final features ===
print("✅ Preparing final features...")
base_features = [
    "IP", "BB", "BF", "H", "ER", "HR",
    "age_float", "is_home", "K_per_IP", "K_per_BF",
    "opp_K_rate", "OBP", "SLG", "OPS", "BA", "team_K_rate"
]

# Drop rows with missing criticals
df = df.dropna(subset=["SO", "IP", "BB", "BF", "K_per_IP", "K_per_BF", "age_float"])
# Fill opponent/team features if needed
df[["opp_K_rate", "OBP", "SLG", "OPS", "BA", "team_K_rate"]] = df[[
    "opp_K_rate", "OBP", "SLG", "OPS", "BA", "team_K_rate"
]].fillna(0)

X = df[base_features]
y = df["SO"]

# === Train model ===
print("🤖 Training Linear Regression model...")
model = LinearRegression()
model.fit(X, y)
joblib.dump(model, "models/strikeout_model.pkl")
print("✅ Model saved to models/strikeout_model.pkl")

# === Predict and export ===
print("🔮 Making predictions...")
df["predicted_SO"] = model.predict(X)
export_cols = ["Date", "Player", "Team", "Opp", "SO", "predicted_SO"]
predictions = df[export_cols].copy()

# === Write to SQLite ===
print("💾 Writing to SQLite...")
conn = sqlite3.connect("strikeout_predictions.db")
predictions.to_sql("predictions", conn, if_exists="replace", index=False)
conn.commit()
conn.close()
print("✅ Predictions written to strikeout_predictions.db")
