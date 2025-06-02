import streamlit as st
import pandas as pd
from datetime import datetime
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="Pitcher SO Prop Model", layout="wide")
st.title("🎯 MLB Strikeout Prop Dashboard")

# === TAB NAVIGATION ===
tab1, tab2 = st.tabs(["📈 Strikeout Prop Model", "📅 Results Viewer"])

# ========== TAB 1: Prediction Viewer ==========
with tab1:
    @st.cache_data
    def load_predictions():
        df = pd.read_csv("data/predicted_pitcher_props_with_edges.csv")
        df.columns = df.columns.str.lower()
        df["game_date"] = pd.to_datetime(df["game_date"]).dt.date
        return df

    df = load_predictions()

    st.sidebar.header("🔍 Filters")

    # 🔥 Edge distribution chart
    st.sidebar.subheader("📊 Edge Distribution")
    fig, ax = plt.subplots()
    df["edge"].hist(bins=40, ax=ax)
    st.sidebar.pyplot(fig)

    st.sidebar.markdown(f"**Avg Line:** {df['line'].mean():.2f}")
    st.sidebar.markdown(f"**Avg Predicted SO:** {df['predicted_so'].mean():.2f}")

    min_edge = st.sidebar.slider("Minimum Edge", -5.0, 5.0, value=0.75, step=0.05)
    odds_range = st.sidebar.slider("Odds Range", -200, 200, (-200, 200), step=5)
    recommendation = st.sidebar.multiselect(
        "Bet Recommendation",
        options=["✅ Over", "✅ Under", "❌ No Bet"],
        default=["✅ Over", "✅ Under"]
    )

    min_date = df["game_date"].min()
    max_date = df["game_date"].max()
    selected_date = st.sidebar.date_input(
        "Game Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )

    # Ensure bet_recommendation exists
    df["bet_recommendation"] = df["edge"].apply(lambda e:
        "✅ Over" if e > 0.75 else
        "✅ Under" if e < -0.75 else
        "❌ No Bet"
    )

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

    df["confidence"] = df["edge"].apply(fireball_confidence)

    filtered = df[
        (df["edge"].abs() >= min_edge) &
        (df["odds"].between(odds_range[0], odds_range[1])) &
        (df["bet_recommendation"].isin(recommendation)) &
        (df["game_date"] == selected_date)
    ]

    st.subheader(f"📋 Filtered Results ({len(filtered)} bets shown)")

    display_cols = [col for col in ["game_date", "player", "line", "odds", "predicted_so", "edge", "bet_recommendation", "confidence"] if col in filtered.columns]

    st.dataframe(
        filtered[display_cols].style.format({
            "predicted_so": "{:.2f}",
            "edge": "{:.2f}",
            "odds": "{:+}"
        }),
        use_container_width=True
    )

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"filtered_bets_{timestamp}.csv"
    output_dir = "filtered_bets"
    os.makedirs(output_dir, exist_ok=True)
    local_path = os.path.join(output_dir, filename)

    filtered[display_cols].to_csv(local_path, index=False)

    st.download_button(
        label="📥 Download Filtered Bets",
        data=filtered[display_cols].to_csv(index=False),
        file_name=filename,
        mime="text/csv"
    )

# ========== TAB 2: Results Viewer ==========
with tab2:
    st.subheader("📅 Bet Results Viewer")

    @st.cache_data
    def load_results():
        df_results = pd.read_csv("data/bets_vs_actuals_strikeouts.csv")
        df_results.columns = df_results.columns.str.lower()
        df_results["game_date"] = pd.to_datetime(df_results["game_date"]).dt.date
        df_results.rename(columns={"result": "actual_result"}, inplace=True)
        return df_results

    results_df = load_results()

    date_options = results_df["game_date"].dropna().unique()
    selected_result_date = st.date_input(
        "Select Result Date",
        value=max(date_options),
        min_value=min(date_options),
        max_value=max(date_options)
    )

    daily_df = results_df[results_df["game_date"] == selected_result_date]
    daily_df_complete = daily_df[daily_df["actual_result"] != "No Data"]

    rolling_df = results_df[results_df["game_date"] <= selected_result_date]
    rolling_df_complete = rolling_df[rolling_df["actual_result"] != "No Data"]

    total = len(daily_df_complete)
    wins = (daily_df_complete["actual_result"] == daily_df_complete["bet_recommendation"].str.replace("✅ ", "")).sum()
    win_rate = (wins / total * 100) if total > 0 else 0

    st.markdown(f"### 🎯 Results for {selected_result_date} ({len(daily_df)} picks)")
    st.markdown(f"**✅ Correct Picks:** {wins} / {total}  &nbsp; &nbsp; **Win Rate:** {win_rate:.1f}%")

    r_total = len(rolling_df_complete)
    r_wins = (rolling_df_complete["actual_result"] == rolling_df_complete["bet_recommendation"].str.replace("✅ ", "")).sum()
    r_win_rate = (r_wins / r_total * 100) if r_total > 0 else 0

    st.markdown(f"**📈 Rolling Total (up to {selected_result_date}):** {r_wins} / {r_total} correct — {r_win_rate:.1f}%")

    def highlight_result(row):
        color = "background-color: green;" if row["actual_result"] == row["bet_recommendation"].replace("✅ ", "") else \
                "background-color: red;" if row["actual_result"] in ["Over", "Under"] else ""
        return [color] * len(row)

    format_cols = {col: "{:.2f}" for col in ["predicted_k", "edge", "odds"] if col in daily_df.columns}
    if "strikeouts" in daily_df.columns:
        format_cols["strikeouts"] = "{:.1f}"

    styled = daily_df.style.apply(highlight_result, axis=1).format(format_cols)

    st.dataframe(styled, use_container_width=True)
