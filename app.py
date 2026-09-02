import streamlit as st
import pandas as pd
import plotly.express as px
import nfl_data_py as nfl
from model import evaluate_picks, load_team_epa

st.set_page_config(page_title="duuhduuh model", layout="wide")

st.title("duuhduuh model")

st.sidebar.header("duuhduuh Control Panel")
default_key = st.secrets.get("ODDS_API_KEY", "")
odds_api_key = st.sidebar.text_input("The Odds API Key", value=default_key, type="password")

season = st.sidebar.number_input("Season", min_value=2023, max_value=2026, value=2025)
selected_week = st.sidebar.number_input("Week", min_value=1, max_value=18, value=1)

@st.cache_data
def get_nfl_schedule(season_year, week_num):
    try:
        sched = nfl.import_schedules([season_year])
        week_games = sched[(sched['week'] == week_num) & (sched['game_type'] == 'REG')]
        
        if week_games.empty:
            return pd.DataFrame()
            
        team_mapping = {
            'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
            'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
            'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
            'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
            'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars',
            'KC': 'Kansas City Chiefs', 'LA': 'Los Angeles Rams', 'LAC': 'Los Angeles Chargers',
            'LV': 'Las Vegas Raiders', 'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings',
            'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants',
            'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers',
            'SEA': 'Seattle Seahawks', 'SF': 'San Francisco 49ers', 'TB': 'Tampa Bay Buccaneers',
            'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders'
        }
        
        schedule_df = pd.DataFrame({
            'favorite_team': week_games['home_team'].map(team_mapping).fillna(week_games['home_team']),
            'favorite_spread': 3.0,
            'underdog_team': week_games['away_team'].map(team_mapping).fillna(week_games['away_team']),
            'home_team': week_games['home_team'].map(team_mapping).fillna(week_games['home_team']),
            'away_team': week_games['away_team'].map(team_mapping).fillna(week_games['away_team'])
        })
        return schedule_df
    except Exception as e:
        return pd.DataFrame()

full_schedule = get_nfl_schedule(season, selected_week)

if full_schedule.empty:
    full_schedule = pd.DataFrame({
        'favorite_team': ['Kansas City Chiefs', 'Dallas Cowboys', 'Detroit Lions', 'Buffalo Bills'],
        'favorite_spread': [3.0, 2.5, 6.5, 3.5],
        'underdog_team': ['Baltimore Ravens', 'Philadelphia Eagles', 'Green Bay Packers', 'Miami Dolphins'],
        'home_team': ['Kansas City Chiefs', 'Dallas Cowboys', 'Detroit Lions', 'Buffalo Bills'],
        'away_team': ['Baltimore Ravens', 'Philadelphia Eagles', 'Green Bay Packers', 'Miami Dolphins']
    })

st.subheader(f"1. Input Locked League Lines for Week {selected_week}")
st.info("Favorites (giving points) are on the left. Underdogs (getting points) are on the right.")

edited_league_df = st.data_editor(
    full_schedule[['favorite_team', 'favorite_spread', 'underdog_team', 'home_team', 'away_team']], 
    column_config={
        "favorite_team": "Favorite (Giving Points)",
        "favorite_spread": st.column_config.NumberColumn("Spread (Points Given)", help="Enter positive spread (e.g. 3.5)", min_value=0.0, step=0.5),
        "underdog_team": "Underdog (Receiving Points)",
        "home_team": None,
        "away_team": None
    },
    use_container_width=True
)

eval_df = edited_league_df.copy()
eval_df['league_home_spread'] = eval_df.apply(
    lambda r: -abs(r['favorite_spread']) if r['favorite_team'] == r['home_team'] else abs(r['favorite_spread']),
    axis=1
)

if st.button("Run duuhduuh Model Evaluation"):
    with st.spinner("Fetching market shifts and calculating pool leverage..."):
        results = evaluate_picks(eval_df, odds_api_key, season)
        
        st.subheader("2. Recommended Picks & Leverage Scores")
        
        col1, col2 = st.columns(2)
        top_pick = results.iloc[results['leverage_score'].abs().idxmax()]
        col1.metric("Highest Leverage Game", f"{top_pick['favorite_team']} vs {top_pick['underdog_team']}")
        col2.metric("Top Pick Recommendation", top_pick['recommended_pick'])
        
        st.dataframe(
            results[['favorite_team', 'favorite_spread', 'underdog_team', 'market_home_spread', 'spread_diff', 'leverage_score', 'recommended_pick']],
            use_container_width=True
        )
        
        fig = px.bar(
            results,
            x='favorite_team',
            y='leverage_score',
            color='leverage_score',
            title="Pool Leverage Score (Positive = Favorite Value | Negative = Underdog Value)",
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)

with st.expander("View Season Team EPA Ranks"):
    if st.button("Fetch EPA Data"):
        epa_df = load_team_epa(season)
        st.dataframe(epa_df.sort_values(by='net_epa', ascending=False), use_container_width=True)
