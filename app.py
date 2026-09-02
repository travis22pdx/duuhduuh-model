import streamlit as st
import pandas as pd
import plotly.express as px
from model import evaluate_picks, load_team_epa

st.set_page_config(page_title="duuhduuh model", layout="wide")

st.title(" duuhduuh model")
st.caption("NFL Underdog & Point Spread Differential Engine for 200-Person Pools")

st.sidebar.header("duuhduuh Control Panel")
default_key = st.secrets.get("ODDS_API_KEY", "")
odds_api_key = st.sidebar.text_input("The Odds API Key", value=default_key, type="password")

season = st.sidebar.number_input("Season", min_value=2023, max_value=2026, value=2025)
selected_week = st.sidebar.number_input("NFL Week", min_value=1, max_value=18, value=1)

default_lines = pd.DataFrame({
    'home_team': ['Kansas City Chiefs', 'Dallas Cowboys', 'Detroit Lions', 'Buffalo Bills'],
    'away_team': ['Baltimore Ravens', 'Philadelphia Eagles', 'Green Bay Packers', 'Miami Dolphins'],
    'league_home_spread': [-3.0, 2.5, -6.5, -3.5]
})

st.subheader(f"1. Input Locked League Lines for Week {selected_week}")
edited_league_df = st.data_editor(default_lines, num_rows="dynamic", use_container_width=True)

if st.button("🚀 Run duuhduuh Model Evaluation"):
    with st.spinner("Fetching market shifts and calculating pool leverage..."):
        results = evaluate_picks(edited_league_df, odds_api_key, season)
        
        st.subheader("2. Recommended Picks & Leverage Scores")
        
        col1, col2 = st.columns(2)
        top_pick = results.iloc[results['leverage_score'].abs().idxmax()]
        col1.metric("Highest Leverage Game", f"{top_pick['home_team']} vs {top_pick['away_team']}")
        col2.metric("Top Pick Recommendation", top_pick['recommended_pick'])
        
        st.dataframe(
            results[['home_team', 'away_team', 'league_home_spread', 'market_home_spread', 'spread_diff', 'leverage_score', 'recommended_pick']],
            use_container_width=True
        )
        
        fig = px.bar(
            results,
            x='home_team',
            y='leverage_score',
            color='leverage_score',
            title="Pool Leverage Score (Positive = Pick Home | Negative = Pick Away)",
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)

with st.expander("📊 View Season Team EPA Ranks"):
    if st.button("Fetch EPA Data"):
        epa_df = load_team_epa(season)
        st.dataframe(epa_df.sort_values(by='net_epa', ascending=False), use_container_width=True)
