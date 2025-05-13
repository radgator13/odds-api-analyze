import pandas as pd

# === Load all data ===
pitcher_df = pd.read_csv("data/betonline_pitcher_props.csv")
batter_df = pd.read_csv("data/betonline_batter_props.csv")
team_df = pd.read_csv("data/betonline_team_lines_filtered.csv")  # filtered to only known prop games

# Ensure event_id is str
for df in [pitcher_df, batter_df, team_df]:
    df["event_id"] = df["event_id"].astype(str)

# === Flatten team lines ===
def flatten_team_props(df):
    game_rows = []
    for event_id, group in df.groupby("event_id"):
        row = {
            "event_id": event_id,
            "home_team": group["home_team"].iloc[0],
            "away_team": group["away_team"].iloc[0],
            "commence_time": group["commence_time"].iloc[0],
        }

        for _, market_row in group.iterrows():
            market = market_row["market"]
            name = str(market_row["raw_name"]).lower().replace(" ", "_")
            line = market_row["line"]
            odds = market_row["odds"]
            key = f"{market}_{name}"
            row[f"{key}_line"] = line
            row[f"{key}_odds"] = odds

        game_rows.append(row)
    return pd.DataFrame(game_rows)

team_flat = flatten_team_props(team_df)

# === Group pitcher and batter props by event_id ===
def group_props(df, role):
    prop_cols = ["raw_name", "participant", "description", "line", "odds", "market"]

    def extract_props(group):
        records = []
        for _, row in group.iterrows():
            # ✅ Updated: get player name from the best available field
            name = row.get("description") or row.get("participant") or row.get("raw_name")
            if name and str(name).lower() not in ["over", "under"]:
                records.append({
                    "player": name,
                    "market": row["market"],
                    "line": row["line"],
                    "odds": row["odds"]
                })
        return records

    grouped = df.groupby("event_id", group_keys=False).apply(extract_props).reset_index()
    grouped.columns = ["event_id", f"{role}_props"]
    return grouped

# ✅ Group props
pitcher_grouped = group_props(pitcher_df, "pitcher")
batter_grouped = group_props(batter_df, "batter")

# === Merge all three ===
merged = team_flat.merge(pitcher_grouped, on="event_id", how="left")
merged = merged.merge(batter_grouped, on="event_id", how="left")

# === Save merged output ===
merged.to_json("data/merged_game_props.json", orient="records", indent=2)
merged.to_csv("data/merged_game_props.csv", index=False)

print(f"✅ Merged game-level file saved with {len(merged)} rows")
