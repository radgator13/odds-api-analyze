import pandas as pd

df = pd.read_csv("data/merged_game_props.csv")
print("\n🧪 Prop Summary:")
print("Pitcher props present:", df["pitcher_props"].notna().sum())
print("Batter props present:", df["batter_props"].notna().sum())
