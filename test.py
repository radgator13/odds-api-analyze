import pandas as pd

files = {
    "Player Pitching": "new_data/stathead_player_pitching_game_data.csv",
    "Team Pitching": "new_data/stathead_team_pitching_game_data.csv",
    "Batting": "new_data/stathead_batting_game_data.csv",
    "Game Logs": "new_data/stathead_game_logs.csv"
}

for label, path in files.items():
    print(f"\n=== {label} ===")
    df = pd.read_csv(path)
    
    print("Columns:")
    print(df.columns.tolist())
    
    print("\nSample row:")
    print(df.iloc[0])

