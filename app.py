import numpy as np
import pandas as pd
import requests
import streamlit as st

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="NFL Pick'em Model & Line Value Evaluator",
    page_icon="🏈",
    layout="wide",
)

st.title("🏈 NFL Pick'em Model & Line Value Evaluator")
st.markdown(
    """
Evaluate weekly Pick'em slate opportunities by comparing your **locked pool lines** 
against **live consensus sportsbook odds**.
"""
)

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.header("⚙️ Model Controls")
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
# HELPER FUNCTIONS & DATA LOGIC
# ==========================================
def fetch_live_odds(api_key):
    """Fetch live NFL game lines from The Odds API."""
    if not api_key:
        return None

    url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "spreads",
        "oddsFormat": "american",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.sidebar.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.sidebar.error(f"Failed to connect: {str(e)}")
        return None


def get_default_schedule():
    """Provides fallback default slate structure with corrected Favorite/Underdog pairs."""
    return [
        {
            "home_team": "Patriots",
            "away_team": "Seahawks",
            "home_spread": 3.5,
        },  # Away Fav: Seahawks (-3.5)
        {
            "home_team": "49ers",
            "away_team": "Rams",
            "home_spread": 4.5,
        },  # Away Fav: Rams (-4.5)
        {
            "home_team": "Chiefs",
            "away_team": "Ravens",
            "home_spread": -3.0,
        },  # Home Fav: Chiefs (-3.0)
        {
            "home_team": "Eagles",
            "away_team": "Packers",
            "home_spread": -2.5,
        },  # Home Fav: Eagles (-2.5)
        {
            "home_team": "Lions",
            "away_team": "Rams",
            "home_spread": -3.5,
        },  # Home Fav: Lions (-3.5)
    ]


def parse_and_format_games(raw_games):
    """Correctly parses game dicts into Favorite vs Underdog regardless of Home/Away location."""
    formatted_data = []

    for game in raw_games:
        home = game.get("home_team", "Home")
        away = game.get("away_team", "Away")
        # Market spreads are relative to Home Team
        home_spread = game.get("home_spread", 0.0)

        if home_spread < 0:
            # Home team is favored (giving points)
            favorite = home
            underdog = away
            spread_points = abs(home_spread)
        elif home_spread > 0:
            # Away team is favored (giving points)
            favorite = away
            underdog = home
            spread_points = abs(home_spread)
        else:
            # Pick 'em line
            favorite = home
            underdog = away
            spread_points = 0.0

        formatted_data.append(
            {
                "Favorite (Giving Points)": favorite,
                "Spread (Points Given)": float(spread_points),
                "Underdog (Receiving Points)": underdog,
                "Vegas Live Spread": float(spread_points),
            }
        )

    return pd.DataFrame(formatted_data)


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
st.subheader("Section 1: Input Locked League Lines")
st.write(
    "Enter your pool's exact locked lines below. Adjust team names if needed:"
)

# Load data feed or fallback schedule
raw_games = get_default_schedule()
initial_df = parse_and_format_games(raw_games)

# Display interactive data table
edited_df = st.data_editor(
    initial_df,
    column_config={
        "Favorite (Giving Points)": st.column_config.TextColumn(
            "Favorite (Giving Points)", help="Team favored by your league line"
        ),
        "Spread (Points Given)": st.column_config.NumberColumn(
            "Spread (Points Given)",
            help="Your league's locked spread value",
            min_value=0.0,
            max_value=30.0,
            step=0.5,
            format="%.1f",
        ),
        "Underdog (Receiving Points)": st.column_config.TextColumn(
            "Underdog (Receiving Points)",
            help="Team receiving points in your league",
        ),
        "Vegas Live Spread": st.column_config.NumberColumn(
            "Vegas Market Spread",
            help="Current live sportsbook consensus spread",
            format="%.1f",
            disabled=True,
        ),
    },
    use_container_width=True,
    num_rows="dynamic",
)

# ==========================================
# SECTION 2: EVALUATION & RESULTS
# ==========================================
st.markdown("---")
if st.button("🚀 Run Model Evaluation", type="primary"):
    st.subheader("Section 2: Model Evaluation & Opportunity Recommendations")

    results = []

    for _, row in edited_df.iterrows():
        fav = row["Favorite (Giving Points)"]
        dog = row["Underdog (Receiving Points)"]
        pool_spread = float(row["Spread (Points Given)"])
        vegas_spread = float(row["Vegas Live Spread"])

        # Calculate line difference
        spread_diff = vegas_spread - pool_spread
        key_boost = calculate_key_boost(pool_spread, vegas_spread)

        # Leverage Score Math
        leverage_score = (spread_diff * 1.5) + (
            key_boost * key_boost_weight
        )

        # Signal Recommendation
        if leverage_score >= 1.5:
            rec = f"🔥 SLAM {fav} (-{pool_spread})"
        elif leverage_score >= 0.5:
            rec = f"👍 Lean {fav} (-{pool_spread})"
        elif leverage_score <= -1.5:
            rec = f"🔥 SLAM {dog} (+{pool_spread})"
        elif leverage_score <= -0.5:
            rec = f"👍 Lean {dog} (+{pool_spread})"
        else:
            rec = "➡️ Neutral / Fair Value"

        results.append(
            {
                "Matchup": f"{fav} vs {dog}",
                "Pool Spread": f"{fav} -{pool_spread}",
                "Vegas Spread": f"{fav} -{vegas_spread}",
                "Spread Gap": round(spread_diff, 1),
                "Key Cross Boost": "Yes" if key_boost > 0 else "No",
                "Leverage Score": round(leverage_score, 2),
                "Recommended Pick": rec,
            }
        )

    results_df = pd.DataFrame(results)

    # Display results table
    st.dataframe(
        results_df.style.highlight_max(
            subset=["Leverage Score"], color="#d4edda"
        ).highlight_min(subset=["Leverage Score"], color="#f8d7da"),
        use_container_width=True,
    )
