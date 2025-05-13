import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="MLB Odds Analyzer", layout="wide")

# === Load data ===
@st.cache_data
def load_data():
    return pd.read_csv("data/clean_all_props_flat.csv")

df = load_data()

st.title("⚾ MLB Odds Analyzer")
import datetime

# === Date filter ===
st.markdown("### 📅 Select Game Date")
selected_date = st.date_input("Game Date", datetime.date.today())

# Convert game time to date for filtering
df["game_date"] = pd.to_datetime(df["commence_time"]).dt.date
df = df[df["game_date"] == selected_date]

st.markdown("Explore team, batter, and pitcher props from BetOnline.")

# === Filters ===
col1, col2, col3, col4 = st.columns(4)

type_filter = col1.multiselect("Prop Type", df["type"].unique(), default=["batter", "pitcher"])
market_filter = col2.multiselect("Markets", sorted(df["market"].dropna().unique()), default=sorted(df["market"].dropna().unique()))
team_filter = col3.multiselect("Teams (Home/Away)", sorted(set(df["home_team"]) | set(df["away_team"])))
player_search = col4.text_input("Search Player or Team")

filtered = df.copy()
filtered = filtered[filtered["type"].isin(type_filter)]
filtered = filtered[filtered["market"].isin(market_filter)]

if team_filter:
    filtered = filtered[filtered["home_team"].isin(team_filter) | filtered["away_team"].isin(team_filter)]

if player_search:
    filtered = filtered[filtered["player"].str.contains(player_search, case=False, na=False)]

# === Table View ===
st.subheader("📋 Filtered Prop List")
st.dataframe(filtered.sort_values(by=["type", "player", "market", "line"]), use_container_width=True)

# === Chart Section ===
st.subheader("📈 Odds & Line Distribution")

col5, col6 = st.columns(2)

# Odds Distribution
with col5:
    st.markdown("**Odds Distribution**")
    odds_chart = alt.Chart(filtered.dropna(subset=["odds"])).mark_bar().encode(
        x=alt.X("odds:Q", bin=alt.Bin(maxbins=30), title="Odds"),
        y=alt.Y("count():Q", title="Frequency"),
        color="type"
    )
    st.altair_chart(odds_chart, use_container_width=True)

# Line Distribution
with col6:
    st.markdown("**Average Line by Market**")
    avg_line_chart = alt.Chart(filtered.dropna(subset=["line"])).mark_bar().encode(
        x=alt.X("market:N", title="Market"),
        y=alt.Y("mean(line):Q", title="Average Line"),
        color="type:N"
    )
    st.altair_chart(avg_line_chart, use_container_width=True)
