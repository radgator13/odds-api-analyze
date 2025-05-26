import pandas as pd

# Load sportsbook props data
props = pd.read_csv("data/clean_all_props_flat.csv")
props["game_date"] = pd.to_datetime(props["commence_time"]).dt.date

# Filter for pitcher strikeout props only
pitcher_props = props[
    (props["type"] == "pitcher") & 
    (props["market"].str.lower().str.contains("strikeout"))
].copy()

# Normalize player names for matching
pitcher_props["player_clean"] = pitcher_props["player"].str.lower().str.strip()

# Load pitcher game stats
stats = pd.read_csv("new_data/stathead_player_pitching_game_data.csv")
stats["Date"] = stats["Date"].astype(str).str.split().str[0]
stats["Date"] = pd.to_datetime(stats["Date"], errors="coerce").dt.date

stats["Player_clean"] = stats["Player"].str.lower().str.strip()
print("Sample prop players:", pitcher_props["player_clean"].unique()[:5])
print("Sample stat players:", stats["Player_clean"].unique()[:5])

print("Prop game dates:", pitcher_props["game_date"].unique()[:5])
print("Stat game dates:", stats["Date"].unique()[:5])
# Step 1: Restrict props to only dates that exist in the stats
available_dates = set(stats["Date"])
pitcher_props = pitcher_props[pitcher_props["game_date"].isin(available_dates)]


# Merge on player + game date
merged = pd.merge(
    pitcher_props,
    stats,
    how="inner",
    left_on=["player_clean", "game_date"],
    right_on=["Player_clean", "Date"]
)

# Preview merged dataset
print("Merged rows:", len(merged))
print("Columns:", list(merged.columns))
print(merged[["player", "game_date", "market", "line", "odds", "SO"]].head())
