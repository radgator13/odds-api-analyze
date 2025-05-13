import pandas as pd

df = pd.read_csv("data/merged_game_props.csv")

print("Pitcher props column types:")
print(df["pitcher_props"].apply(type).value_counts())

print("\nFirst few values:")
print(df["pitcher_props"].head(5))
