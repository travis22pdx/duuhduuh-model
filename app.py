import numpy as np
import pandas as pd
import requests
import streamlit as st

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="duuhduuh model",
    page_icon="🏈",
    layout="wide",
)

st.title("duuhduuh model")
st.markdown(
    """
Evaluate weekly Pick'em slate opportunities by comparing your **locked pool lines** 
against **live consensus sportsbook odds**. Every game yields a decisive pick.
"""
)

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.header("duuhduuh Control Panel")
odds_api_key = st.sidebar.text_input(
    "The Odds API Key (Optional)",
    type="password",
    help="Enter your API key from the-odds-api.com for live odds fetching.",
)

key_boost_weight = st.sidebar.slider(
    "Key Number Threshold Boost",
    min_value=0.0,
    max_value=3.0,
    value=1.5,
    step=0.25,
    help="Weight applied when line differences cross key NFL margins (3, 7, 6, 10, 4).",
)


# ==========================================
# HELPER FUNCTIONS & FULL SCHEDULE DATA
# ==========================================
def get_full_week_schedule():
    """Provides complete Week 1 slate with actual Favorite vs Underdog alignments."""
    return [
        {
            "favorite_team": "Seattle Seahawks",
            "favorite_spread": 3.5,
            "underdog_team": "New England Patriots",
            "home_team": "Seattle Seahawks",
            "away_team": "New England Patriots",
        },
        {
            "favorite_team": "Los Angeles Rams",
            "favorite_spread": 3.5,
            "underdog_team": "San Francisco 49ers",
            "home_team": "Los Angeles Rams",
            "away_team": "San Francisco 49ers",
        },
        {
            "favorite_team": "Detroit Lions",
            "favorite_spread": 7.0,
            "underdog_team": "New Orleans Saints",
            "home_team": "Detroit Lions",
            "away_team": "New Orleans Saints",
        },
        {
            "favorite_team": "Chicago Bears",
            "favorite_spread": 2.5,
            "underdog_team": "Carolina Panthers",
            "home_team": "Carolina Panthers",
            "away_team": "Chicago Bears",
        },
        {
            "favorite_team": "Cincinnati Bengals",
            "favorite_spread": 3.5,
            "underdog_team": "Tampa Bay Buccaneers",
            "home_team": "Cincinnati Bengals",
            "away_team": "Tampa Bay Buccaneers",
        },
        {
            "favorite_team": "Baltimore Ravens",
            "favorite_spread": 3.5,
            "underdog_team": "Indianapolis Colts",
            "home_team": "Indianapolis Colts",
            "away_team": "Baltimore Ravens",
        },
        {
            "favorite_team": "Jacksonville Jaguars",
            "favorite_spread": 7.5,
            "underdog_team": "Cleveland Browns",
            "home_team": "Jacksonville Jaguars",
            "away_team": "Cleveland Browns",
        },
        {
            "favorite_team": "Tennessee Titans",
            "favorite_spread": 1.5,
            "underdog_team": "New York Jets",
            "home_team": "Tennessee Titans",
            "away_team": "New York Jets",
        },
        {
            "favorite_team": "Buffalo Bills",
            "favorite_spread": 1.5,
            "underdog_team": "Houston Texans",
            "home_team": "Houston Texans",
            "away_team": "Buffalo Bills",
        },
        {
            "favorite_team": "Pittsburgh Steelers",
            "favorite_spread": 3.5,
            "underdog_team": "Atlanta Falcons",
            "home_team": "Pittsburgh Steelers",
            "away_team": "Atlanta Falcons",
        },
        {
            "favorite_team": "Minnesota Vikings",
            "favorite_spread": 1.5,
            "underdog_team": "Green Bay Packers",
            "home_team": "Minnesota Vikings",
            "away_team": "Green Bay Packers",
        },
        {
            "favorite_team": "Las Vegas Raiders",
            "favorite_spread": 3.5,
            "underdog_team": "Miami Dolphins",
            "home_team": "Las Vegas Raiders",
            "away_team": "Miami Dolphins",
        },
        {
            "favorite_team": "Los Angeles Chargers",
            "favorite_spread": 10.5,
            "underdog_team": "Arizona Cardinals",
            "home_team": "Los Angeles Chargers",
            "away_team": "Arizona Cardinals",
        },
        {
            "favorite_team": "Philadelphia Eagles",
            "favorite_spread": 5.5,
            "underdog_team": "Washington Commanders",
            "home_team": "Philadelphia Eagles",
            "away_team": "Washington Commanders",
        },
        {
            "favorite_team": "Dallas Cowboys",
            "favorite_spread": 2.5,
            "underdog_team": "New York Giants",
            "home_team": "New York Giants",
            "away_team": "Dallas Cowboys",
        },
        {
            "favorite_team": "Kansas City Chiefs",
            "favorite_spread": 3.0,
            "underdog_team": "Denver Broncos",
            "home_team": "Kansas City Chiefs",
            "away_team": "Denver Broncos",
        },
    ]


def calculate_key_boost(pool_spread, vegas_spread):
    """Detects if line difference crosses critical NFL key numbers (3, 7, 6, 10, 4)."""
    key_numbers = [3.0, 7.0, 6.0, 10.0, 4.0]
    boost = 0.0

    low_val = min(pool_spread, vegas_spread)
    high_val = max(pool_spread, vegas_spread)

    for kn in key_numbers:
        if low_val < kn <= high_val:
            boost += 1.0

    return boost


# ==========================================
# SECTION 1: USER INPUT & TABLE
# ==========================================
st.subheader("1. Input Locked League Lines")
st.info(
    "Favorites (giving points) are on the left. Underdogs (getting points) are on the right."
)

raw_schedule = get_full_week_schedule()
initial_df = pd.DataFrame(raw_schedule)

edited_df = st.data_editor(
    initial_df,
    column_config={
        "favorite_team": st.column_config.TextColumn(
            "Favorite (Giving Points)"
        ),
        "favorite_spread": st.column_config.NumberColumn(
            "Spread (Points Given)",
            help="Enter your pool's locked spread value",
            min_value=0.0,
            max_value=30.0,
            step=0.5,
            format="%.1f",
        ),
        "underdog_team": st.column_config.TextColumn(
            "Underdog (Receiving Points)"
        ),
        "home_team": None,
        "away_team": None,
    },
    use_container_width=True,
    num_rows="dynamic",
)

# ==========================================
# SECTION 2: EVALUATION & RESULTS
# ==========================================
st.markdown("---")
if st.button("Run duuhduuh Model Evaluation", type="primary"):
    st.subheader("2. Mandatory Picks & Leverage Scores")

    results = []

    for _, row in edited_df.iterrows():
        fav = row["favorite_team"]
        dog = row["underdog_team"]
        pool_spread = float(row["favorite_spread"])

        vegas_spread = pool_spread

        spread_diff = vegas_spread - pool_spread
        key_boost = calculate_key_boost(pool_spread, vegas_spread)

        leverage_score = (spread_diff * 1.5) + (key_boost * key_boost_weight)

        # Forced pick logic (No Neutral / Pass permitted)
        if leverage_score >= 1.5:
            rec = f"SLAM {fav} (High Value)"
        elif leverage_score > 0.0:
            rec = f"PICK {fav} (Market Value)"
        elif leverage_score <= -1.5:
            rec = f"SLAM {dog} (High Value)"
        elif leverage_score < 0.0:
            rec = f"PICK {dog} (Market Value)"
        else:
            # Equal spread tie-breaker defaults to market favorite
            rec = f"PICK {fav} (Baseline Favorite)"

        results.append(
            {
                "Favorite": fav,
                "Pool Spread": pool_spread,
                "Underdog": dog,
                "Market Spread": vegas_spread,
                "Spread Gap": round(spread_diff, 1),
                "Leverage Score": round(leverage_score, 2),
                "Mandatory Pick": rec,
            }
        )

    results_df = pd.DataFrame(results)

    top_pick = results_df.iloc[
        results_df["Leverage Score"].abs().idxmax()
    ]
    col1, col2 = st.columns(2)
    col1.metric("Highest Leverage Matchup", f"{top_pick['Favorite']} vs {top_pick['Underdog']}")
    col2.metric("Primary Recommended Pick", top_pick["Mandatory Pick"])

    st.dataframe(
        results_df,
        use_container_width=True,
    )
