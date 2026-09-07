import streamlit as st
import pandas as pd
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials

# 1. 구글 시트 연동 클라이언트
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
        return None
    except Exception:
        return None

# 2. 안전한 시트 데이터 로딩 함수 (캐시 적용)
@st.cache_data(ttl=30, show_spinner=False)
def load_sheet_data(sheet_name, spreadsheet_id=""):
    client = get_gspread_client()
    if not client or not spreadsheet_id:
        return pd.DataFrame()
    for attempt in range(4):
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
            ws = spreadsheet.worksheet(sheet_name)
            data = ws.get_all_values()
            if len(data) > 1:
                cols = [str(c).strip() for c in data[0]]
                df = pd.DataFrame(data[1:], columns=cols)
                df = df.dropna(how='all')
                return df
            return pd.DataFrame()
        except Exception as e:
            time.sleep(1.0 * (attempt + 1))
            continue
    return pd.DataFrame()

# 3. 경기 데이터 구글 시트 일괄 저장 함수 (중복 방지 및 누락 검증 장치 포함)
def save_match_data_to_sheets(spreadsheet_id, bookmakers, stats_sheet_name, match_info, odds_dict, stats_dict):
    client = get_gspread_client()
    if not client:
        return False, "구글 시트 연동 실패: Secrets 설정을 확인하세요."
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        season = match_info["season"]
        league = match_info["league"]
        match_date = match_info["date"]
        home_team = match_info["home"]
        away_team = match_info["away"]
        
        # 실제 입력 대상인 유효 북메이커 개수 산출 (누락 감지용)
        expected_bms = [bm for bm in bookmakers if bm in odds_dict and odds_dict[bm][0] > 0 and odds_dict[bm][1] > 0 and odds_dict[bm][2] > 0]
        expected_count = len(expected_bms)

        b_h, b_d, b_a = odds_dict.get("배트맨", (0.0, 0.0, 0.0))
        if b_h > 0 and b_d > 0 and b_a > 0:
            b_inv = (1/b_h) + (1/b_d) + (1/b_a)
            b_payout = 1 / b_inv
            b_prob_h = (1/b_h) / b_inv
            b_prob_d = (1/b_d) / b_inv
            b_prob_a = (1/b_a) / b_inv
        else:
            b_payout, b_prob_h, b_prob_d, b_prob_a = 0.0, 0.0, 0.0, 0.0

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
        failed_bms = []
        duplicate_bms = []
        
        for bm_name in bookmakers:
            if bm_name not in odds_dict:
                continue
            h, d, a = odds_dict[bm_name]
            if h <= 0 or d <= 0 or a <= 0:
                continue
            
            # 🛡️ [중복 방지 검사] 시트의 마지막 행과 현재 입력하려는 경기가 완벽히 일치하는지 대조
            try:
                ws = spreadsheet.worksheet(bm_name)
                all_rows = ws.get_all_values()
                if len(all_rows) > 1:
                    last_row = all_rows[-1]
                    if len(last_row) >= 5:
                        if (str(last_row[0]).strip() == str(season).strip() and
                            str(last_row[1]).strip() == str(league).strip() and
                            str(last_row[3]).strip() == str(home_team).strip() and
                            str(last_row[4]).strip() == str(away_team).strip()):
                            duplicate_bms.append(bm_name)
                            continue # 중복이므로 저장을 건너뜀
            except Exception:
                pass
            
            bm_inv = (1/h) + (1/d) + (1/a)
            bm_payout = 1 / bm_inv
            bm_prob_h = (1/h) / bm_inv
            bm_prob_d = (1/d) / bm_inv
            bm_prob_a = (1/a) / bm_inv
            
            diff_h = round(b_h - h, 2) if b_h > 0 else 0.0
            diff_d = round(b_d - d, 2) if d > 0 else 0.0
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
                home_score, away_score, score_total, score_diff, score_diff_abs,
                odd_type, match_res, win_odd
            ]
            
            # 🛡️ [누락 검증] 429 에러 등으로 통신 실패 시 실패 목록에 담음
            try:
                ws = spreadsheet.worksheet(bm_name)
                ws.append_row(row_data_odds, value_input_option="USER_ENTERED")
                saved_count += 1
                time.sleep(0.12)
            except Exception:
                failed_bms.append(bm_name)

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

        # 경기내용 탭 중복 검사
        stats_duplicate = False
        try:
            ws_stats = spreadsheet.worksheet(stats_sheet_name)
            all_stats_rows = ws_stats.get_all_values()
            if len(all_stats_rows) > 1:
                last_stats_row = all_stats_rows[-1]
                if len(last_stats_row) >= 5:
                    if (str(last_stats_row[0]).strip() == str(season).strip() and
                        str(last_stats_row[1]).strip() == str(league).strip() and
                        str(last_stats_row[3]).strip() == str(home_team).strip() and
                        str(last_stats_row[4]).strip() == str(away_team).strip()):
                        stats_duplicate = True
        except Exception:
            pass

        stats_saved = False
        if not stats_duplicate:
            try:
                ws_stats = spreadsheet.worksheet(stats_sheet_name)
                ws_stats.append_row(row_data_stats, value_input_option="USER_ENTERED")
                stats_saved = True
                time.sleep(0.12)
            except Exception:
                pass
        
        # 🚨 [알람 메시지 조립] 결과에 따라 누락/중복 상태를 상세히 안내
        msg_parts = [f"배당 {saved_count}/{expected_count}개사 저장"]
        if stats_saved:
            msg_parts.append(f"'{stats_sheet_name}' 탭 기록 완료")
        elif stats_duplicate:
            msg_parts.append(f"'{stats_sheet_name}' 탭 중복 감지(건너뜀)")
        else:
            msg_parts.append(f"'{stats_sheet_name}' 탭 저장 실패")

        final_msg = " & ".join(msg_parts)
        
        if failed_bms:
            return True, f"⚠️ [일부 누락 경고] 다음 북메이커 시트 저장이 누락되었습니다: [{', '.join(failed_bms)}]. (결과: {final_msg})"
        if duplicate_bms:
            return True, f"🔄 [중복 감지 알람] 이미 동일 경기가 등록되어 있어 다음 업체의 저장을 건너뛰었습니다: [{', '.join(duplicate_bms)}]."
        
        return True, f"🎉 성공: {final_msg}"
    except Exception as e:
        return False, str(e)
