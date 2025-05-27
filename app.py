import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Pitcher SO Prop Model", layout="wide")

st.title("🎯 MLB Strikeout Prop Model")

# === Load Data ===
@st.cache_data
def load_data():
    df = pd.read_csv("predicted_pitcher_props_with_edges.csv")
    df["game_date"] = pd.to_datetime(df["game_date"]).dt.date  # ensure it's date, not string
    return df

df = load_data()

# === Sidebar filters ===
st.sidebar.header("🔍 Filters")

# Edge slider
min_edge = st.sidebar.slider("Minimum Edge", -5.0, 5.0, value=0.75, step=0.05)

# Odds slider
odds_range = st.sidebar.slider("Odds Range", -200, 200, (-200, 200), step=5)

# Recommendation selector
recommendation = st.sidebar.multiselect(
    "Bet Recommendation",
    options=["✅ Over", "✅ Under", "❌ No Bet"],
    default=["✅ Over", "✅ Under"]
)

# Game date selector
min_date = df["game_date"].min()
max_date = df["game_date"].max()
selected_date = st.sidebar.date_input(
    "Game Date",
    value=min_date,
    min_value=min_date,
    max_value=max_date
)

# === Filtered Data ===
filtered = df[
    (df["edge"].abs() >= min_edge) &
    (df["odds"].between(odds_range[0], odds_range[1])) &
    (df["bet_recommendation"].isin(recommendation)) &
    (df["game_date"] == selected_date)
]

# === Add Fireball Confidence (1–5) ===
def fireball_confidence(edge):
    abs_edge = abs(edge)
    if abs_edge >= 2.5:
        return "🔥🔥🔥🔥🔥"
    elif abs_edge >= 2.0:
        return "🔥🔥🔥🔥"
    elif abs_edge >= 1.5:
        return "🔥🔥🔥"
    elif abs_edge >= 1.0:
        return "🔥🔥"
    elif abs_edge >= 0.75:
        return "🔥"
    else:
        return "❌"

filtered["confidence"] = filtered["edge"].apply(fireball_confidence)

# === Main Table ===
st.subheader(f"📋 Filtered Results ({len(filtered)} bets shown)")
st.dataframe(
    filtered[[
        "game_date", "player", "line", "odds", "predicted_SO", "edge", "bet_recommendation", "confidence"
    ]].style.format({
        "predicted_SO": "{:.2f}",
        "edge": "{:.2f}",
        "odds": "{:+}"
    }),
    use_container_width=True
)

# === Download CSV ===
# Generate filename with timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
filename = f"filtered_bets_{timestamp}.csv"

# Save file to disk in the target directory
output_dir = "filtered_bets"
os.makedirs(output_dir, exist_ok=True)
local_path = os.path.join(output_dir, filename)

filtered[[
    "game_date", "player", "line", "odds", "predicted_SO", "edge", "bet_recommendation", "confidence"
]].to_csv(local_path, index=False)

st.download_button(
    label="📥 Download Filtered Bets",
    data=filtered[[
        "game_date", "player", "line", "odds", "predicted_SO", "edge", "bet_recommendation", "confidence"
    ]].to_csv(index=False),
    file_name=filename,
    mime="text/csv"
)
