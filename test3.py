import os

csv_path = r"C:\Users\a1d3r\source\repos\Odds API Baseball Betting Lines V1.00\new_data\stathead_player_pitching_game_data.csv"

with open(csv_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Normalize header for comparison
def normalize(line):
    return line.strip().lower().replace('"', '').replace("'", '').replace(',', '').replace(' ', '')

header_norm = normalize(lines[0])
cleaned = [lines[0]] + [line for line in lines[1:] if normalize(line) != header_norm]

with open(csv_path, "w", encoding="utf-8") as f:
    f.writelines(cleaned)

print(f"✅ Cleaned CSV: Removed any duplicate headers from {csv_path}")
