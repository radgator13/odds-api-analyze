import pandas as pd

csv_path = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\stathead_player_pitching_game_data.csv"

df = pd.read_csv(csv_path)
print(f"📊 Final row count: {len(df)}")




