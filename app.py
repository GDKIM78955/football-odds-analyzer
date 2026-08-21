import pandas as pd
import numpy as np

def analyze_multi_bookmakers(sheets_dict, target_home_odd, target_draw_odd, target_away_odd, tolerance=0.03):
    """
    sheets_dict: {'BWIN': df1, 'BET365': df2, ...} 형태의 딕셔너리
    tolerance: 유사 배당 오차 허용 범위 (기본 ±0.03)
    """
    summary_results = []
    
    for bookmaker_name, df in sheets_dict.items():
        if df.empty or '홈배당' not in df.columns or '결과' not in df.columns:
            continue
            
        # 동일/유사 배당 과거 경기 필터링
        matched_games = df[
            (np.isclose(df['홈배당'], target_home_odd, atol=tolerance)) &
            (np.isclose(df['무배당'], target_draw_odd, atol=tolerance)) &
            (np.isclose(df['원정배당'], target_away_odd, atol=tolerance))
        ]
        
        total_matches = len(matched_games)
        if total_matches > 0:
            home_win_pct = (matched_games['결과'] == '홈승').mean() * 100
            draw_pct = (matched_games['결과'] == '무').mean() * 100
            away_win_pct = (matched_games['결과'] == '원정승').mean() * 100
        else:
            home_win_pct, draw_pct, away_win_pct = np.nan, np.nan, np.nan
            
        summary_results.append({
            '북메이커': bookmaker_name,
            '과거 매칭 경기수': total_matches,
            '홈승 확률(%)': home_win_pct,
            '무승부 확률(%)': draw_pct,
            '원정승 확률(%)': away_win_pct
        })
        
    res_df = pd.DataFrame(summary_results)
    
    # 8개 회사 종합 평균 행 추가
    if not res_df.dropna(subset=['과거 매칭 경기수']).empty:
        valid_df = res_df.dropna()
        avg_row = {
            '북메이커': '🔥 종합 평균 (평균 승률)',
            '과거 매칭 경기수': int(valid_df['과거 매칭 경기수'].sum()),
            '홈승 확률(%)': valid_df['홈승 확률(%)'].mean(),
            '무승부 확률(%)': valid_df['무승부 확률(%)'].mean(),
            '원정승 확률(%)': valid_df['원정승 확률(%)'].mean()
        }
        res_df = pd.concat([res_df, pd.DataFrame([avg_row])], ignore_index=True)
        
    return res_df
