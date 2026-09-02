import requests
import pandas as pd
import numpy as np
import nfl_data_py as nfl

KEY_NUMBERS = {3: 0.25, 7: 0.15, 6: 0.08, 10: 0.06, 4: 0.05}

def get_realtime_odds(api_key: str):
    if not api_key:
        return pd.DataFrame()
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "spreads",
        "oddsFormat": "american"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        games = []
        for game in data:
            home = game['home_team']
            away = game['away_team']
            spreads = []
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home:
                                spreads.append(outcome['point'])
            avg_spread = np.mean(spreads) if spreads else np.nan
            games.append({
                "home_team": home,
                "away_team": away,
                "market_home_spread": avg_spread
            })
        return pd.DataFrame(games)
    except Exception as e:
        return pd.DataFrame()

def load_team_epa(season: int):
    try:
        pbp = nfl.import_pbp_data([season])
        pbp_clean = pbp[pbp['epa'].notna() & (pbp['play_type'].isin(['pass', 'run']))]
        epa_df = pbp_clean.groupby('posteam').agg(
            off_epa=('epa', 'mean')
        ).reset_index().rename(columns={'posteam': 'team'})
        def_epa = pbp_clean.groupby('defteam').agg(
            def_epa=('epa', 'mean')
        ).reset_index().rename(columns={'defteam': 'team'})
        combined = pd.merge(epa_df, def_epa, on='team')
        combined['net_epa'] = combined['off_epa'] - combined['def_epa']
        return combined
    except Exception as e:
        return pd.DataFrame()

def calculate_key_boost(league_spread, market_spread):
    boost = 0.0
    low = min(league_spread, market_spread)
    high = max(league_spread, market_spread)
    for key, weight in KEY_NUMBERS.items():
        for sign in [-1, 1]:
            target_key = key * sign
            if low <= target_key <= high:
                boost += weight
    return boost

def evaluate_picks(league_df: pd.DataFrame, odds_api_key: str, season: int):
    live_odds = get_realtime_odds(odds_api_key)
    merged = league_df.copy()
    if not live_odds.empty:
        merged = pd.merge(merged, live_odds, on=['home_team', 'away_team'], how='left')
    else:
        merged['market_home_spread'] = merged['league_home_spread']
        
    merged['spread_diff'] = merged['league_home_spread'] - merged['market_home_spread']
    merged['key_boost'] = merged.apply(
        lambda r: calculate_key_boost(r['league_home_spread'], r['market_home_spread']), 
        axis=1
    )
    merged['leverage_score'] = (merged['spread_diff'] * 1.5) + (merged['key_boost'] * 2.0)
    
    def get_rec(row):
        score = row['leverage_score']
        if score >= 1.5:
            return f"SLAM {row['home_team']} (Home Value)"
        elif score <= -1.5:
            return f"SLAM {row['away_team']} (Away Value)"
        elif 0.5 <= score < 1.5:
            return f"Lean {row['home_team']}"
        elif -1.5 < score <= -0.5:
            return f"Lean {row['away_team']}"
        else:
            return "Pass / Neutral"
            
    merged['recommended_pick'] = merged.apply(get_rec, axis=1)
    return merged
