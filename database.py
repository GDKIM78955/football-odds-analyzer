import os
import pandas as pd
import streamlit as st

# 엑셀 파일 경로 설정 ('자료' 폴더 안의 '배당초안.xlsx')
EXCEL_PATH = os.path.join("자료", "배당초안.xlsx")

def get_gspread_client():
    """엑셀 전환으로 인해 더 이상 사용하지 않지만 호환성을 위해 유지합니다."""
    return None

# 1. 안전한 엑셀 시트 데이터 로딩 함수 (캐시 적용)
@st.cache_data(ttl=30, show_spinner=False)
def load_sheet_data(sheet_name, spreadsheet_id=""):
    """
    지정한 시트(엑셀의 탭) 이름을 읽어와서 판다스 데이터프레임으로 반환합니다.
    """
    if not os.path.exists(EXCEL_PATH):
        return pd.DataFrame()
    
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how='all')
        return df
    except Exception:
        return pd.DataFrame()

# 2. 경기 데이터 엑셀 일괄 저장 함수 (미입력 값은 빈 칸 공백으로 처리)
def save_match_data_to_sheets(spreadsheet_id, bookmakers, stats_sheet_name, match_info, odds_dict, stats_dict, hc_info=None, ou_info=None):
    if not os.path.exists(EXCEL_PATH):
        return False, f"🚨 [저장 실패] '{EXCEL_PATH}' 엑셀 파일을 찾을 수 없습니다."
    
    # 필수 기준인 '배트맨' 배당 검증
    if "배트맨" not in odds_dict:
        return False, "🚨 [저장 실패] 배트맨 배당 정보가 누락되었습니다."
    
    b_h, b_d, b_a = odds_dict["배트맨"]
    if b_h <= 0 or b_d <= 0 or b_a <= 0:
        return False, "🚨 [저장 실패] 배트맨 배당이 0 또는 유효하지 않은 값으로 입력되었습니다."

    try:
        # 기존 엑셀 파일의 모든 탭 읽기
        excel_book = pd.ExcelFile(EXCEL_PATH)
        sheet_names = excel_book.sheet_names
        dfs = {s: pd.read_excel(EXCEL_PATH, sheet_name=s) for s in sheet_names}

        season = match_info["season"]
        league = match_info["league"]
        match_date = match_info["date"]
        home_team = match_info["home"]
        away_team = match_info["away"]
        
        # 핸디캡 / 언오버 기본값 처리
        hc_line = hc_info.get("line", -1.0) if hc_info else -1.0
        ou_line = ou_info.get("line", 2.5) if ou_info else 2.5
        
        b_inv = (1/b_h) + (1/b_d) + (1/b_a)
        b_payout = 1 / b_inv
        b_prob_h = (1/b_h) / b_inv
        b_prob_d = (1/b_d) / b_inv
        b_prob_a = (1/b_a) / b_inv

        home_score = stats_dict["home_1h"] + stats_dict["home_2h"]
        away_score = stats_dict["away_1h"] + stats_dict["away_2h"]

        if home_score > away_score:
            match_res = "홈승"
        elif home_score == away_score:
            match_res = "무승부"
        else:
            match_res = "원정승"

        score_total = home_score + away_score
        score_diff = home_score - away_score
        score_diff_abs = abs(score_diff)
        
        saved_count = 0
        
        # 각 북메이커 탭별로 데이터 추가
        for bm_name in bookmakers:
            if bm_name not in odds_dict:
                continue
            h, d, a = odds_dict[bm_name]
            if h <= 0 or d <= 0 or a <= 0:
                continue  # 선택되지 않거나 0인 북메이커는 스킵
            
            raw_hc_h = hc_info.get(bm_name, {}).get("h", "") if hc_info else ""
            raw_hc_a = hc_info.get(bm_name, {}).get("a", "") if hc_info else ""
            raw_ou_o = ou_info.get(bm_name, {}).get("over", "") if ou_info else ""
            raw_ou_u = ou_info.get(bm_name, {}).get("under", "") if ou_info else ""
            
            hc_h_val = raw_hc_h if (isinstance(raw_hc_h, (int, float)) and raw_hc_h > 0) else ""
            hc_a_val = raw_hc_a if (isinstance(raw_hc_a, (int, float)) and raw_hc_a > 0) else ""
            ou_o_val = raw_ou_o if (isinstance(raw_ou_o, (int, float)) and raw_ou_o > 0) else ""
            ou_u_val = raw_ou_u if (isinstance(raw_ou_u, (int, float)) and raw_ou_u > 0) else ""

            bm_inv = (1/h) + (1/d) + (1/a)
            bm_payout = 1 / bm_inv
            bm_prob_h = (1/h) / bm_inv
            bm_prob_d = (1/d) / bm_inv
            bm_prob_a = (1/a) / bm_inv
            
            diff_h = round(b_h - h, 2) if b_h > 0 else 0.0
            diff_d = round(b_d - d, 2) if b_d > 0 else 0.0
            diff_a = round(b_a - a, 2) if b_a > 0 else 0.0
            
            fair_h = round(b_payout / bm_prob_h, 6) if (b_payout > 0 and bm_prob_h > 0) else 0.0
            fair_d = round(b_payout / bm_prob_d, 6) if (b_payout > 0 and bm_prob_d > 0) else 0.0
            fair_a = round(b_payout / bm_prob_a, 6) if (b_payout > 0 and bm_prob_a > 0) else 0.0
            
            loss_h = round(((b_h - fair_h) / fair_h) * 100, 5) if fair_h > 0 else 0.0
            loss_d = round(((b_d - fair_d) / fair_d) * 100, 5) if fair_d > 0 else 0.0
            loss_a = round(((b_a - fair_a) / fair_a) * 100, 5) if fair_a > 0 else 0.0
            
            min_odd, max_odd = min(h, d, a), max(h, d, a)
            win_odd = h if match_res == "홈승" else (d if match_res == "무승부" else a)
            odd_type = "정배" if win_odd == min_odd else ("역배" if win_odd == max_odd else "중배")

            row_data_odds = [
                season, league, match_date, home_team, away_team,
                b_h, b_d, b_a,
                f"{round(b_payout * 100, 2)}%",
                f"{round(b_prob_h * 100, 2)}%", f"{round(b_prob_d * 100, 2)}%", f"{round(b_prob_a * 100, 2)}%",
                h, d, a,
                f"{round(bm_payout * 100, 2)}%",
                f"{round(bm_prob_h * 100, 2)}%", f"{round(bm_prob_d * 100, 2)}%", f"{round(bm_prob_a * 100, 2)}%",
                diff_h, diff_d, diff_a,
                loss_h, loss_d, loss_a,
                fair_h, fair_d, fair_a,
                hc_line, hc_h_val, hc_a_val,
                ou_line, ou_o_val, ou_u_val,
                home_score, away_score, score_total, score_diff, score_diff_abs,
                odd_type, match_res, win_odd
            ]
            
            if bm_name not in dfs:
                dfs[bm_name] = pd.DataFrame(columns=[f"col_{i}" for i in range(len(row_data_odds))])
            
            df_bm = dfs[bm_name]
            # 딕셔너리 형태로 행 변환 후 추가
            row_dict = {df_bm.columns[i]: row_data_odds[i] if i < len(df_bm.columns) else row_data_odds[i] for i in range(len(row_data_odds))}
            dfs[bm_name] = pd.concat([df_bm, pd.DataFrame([row_dict])], ignore_index=True)
            saved_count += 1

        # 경기내용(stats) 탭 데이터 추가
        h_1h = stats_dict["home_1h"]
        h_2h = stats_dict["home_2h"]
        a_1h = stats_dict["away_1h"]
        a_2h = stats_dict["away_2h"]
        h_shots = stats_dict["home_shots"]
        a_shots = stats_dict["away_shots"]
        h_sot = stats_dict["home_sot"]
        a_sot = stats_dict["away_sot"]

        h_1h_ratio = round((h_1h / home_score) * 100, 2) if home_score > 0 else 0.0
        h_2h_ratio = round((h_2h / home_score) * 100, 2) if home_score > 0 else 0.0
        a_1h_ratio = round((a_1h / away_score) * 100, 2) if away_score > 0 else 0.0
        a_2h_ratio = round((a_2h / away_score) * 100, 2) if away_score > 0 else 0.0
        
        h_sot_ratio = round((h_sot / h_shots) * 100, 2) if h_shots > 0 else 0.0
        a_sot_ratio = round((a_sot / a_shots) * 100, 2) if a_shots > 0 else 0.0

        home_tac_safe = f"'{stats_dict['home_tac'].strip()}" if stats_dict['home_tac'].strip() else ""
        away_tac_safe = f"'{stats_dict['away_tac'].strip()}" if stats_dict['away_tac'].strip() else ""

        row_data_stats = [
            season, league, match_date, home_team, away_team,
            h_1h, h_2h, a_1h, a_2h,
            f"{h_1h_ratio}%", f"{h_2h_ratio}%", f"{a_1h_ratio}%", f"{a_2h_ratio}%",
            home_tac_safe, away_tac_safe,
            h_shots, a_shots, h_sot, a_sot,
            f"{h_sot_ratio}%", f"{a_sot_ratio}%",
            f"{stats_dict['home_poss']}%", f"{stats_dict['away_poss']}%",
            f"{stats_dict['home_pass']}%", f"{stats_dict['away_pass']}%",
            stats_dict['home_yc'], stats_dict['away_yc'], stats_dict['home_rc'], stats_dict['away_rc'],
            stats_dict['home_xg'], stats_dict['away_xg']
        ]

        if stats_sheet_name not in dfs:
            dfs[stats_sheet_name] = pd.DataFrame(columns=[f"col_{i}" for i in range(len(row_data_stats))])
        
        df_stats = dfs[stats_sheet_name]
        stats_dict_row = {df_stats.columns[i]: row_data_stats[i] if i < len(df_stats.columns) else row_data_stats[i] for i in range(len(row_data_stats))}
        dfs[stats_sheet_name] = pd.concat([df_stats, pd.DataFrame([stats_dict_row])], ignore_index=True)

        # 최종 엑셀 파일로 통째로 저장 (모든 탭 유지)
        with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
            for s, d_frame in dfs.items():
                d_frame.to_excel(writer, sheet_name=s, index=False)
        
        st.cache_data.clear()
        return True, f"배당 {saved_count}개사 탭 & '{stats_sheet_name}' 탭 엑셀 저장 완료"
    except Exception as e:
        return False, str(e)
