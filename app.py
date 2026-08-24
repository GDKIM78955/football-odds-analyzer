import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 설정
st.set_page_config(
    page_title="Football 9-Bookmakers & Stats Hub",
    page_icon="⚽",
    layout="wide"
)

BOOKMAKERS = [
    "bwin", "10x10", "1xbet", "betway", 
    "william hill", "bet365", "pinnacle", "stake", "배트맨"
]
STATS_SHEET_NAME = "경기내용"
SPREADSHEET_ID = "1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ"

st.title("⚽ 축구 9대 배당 업체 & 경기내용 세부 스탯 통합 시스템")

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
        else:
            st.error("Secrets에 GCP 서비스 계정 키가 누락되었습니다.")
            return None
    except Exception as e:
        st.error(f"연동 실패: {e}")
        return None

tab_input, tab_analysis = st.tabs(["📝 데이터 입력 및 통합 저장", "📊 동일 배당 통계"])

with tab_input:
    st.subheader("1️⃣ 경기 기본 정보 & 스코어")
    c_m1, c_m2, c_m3 = st.columns(3)
    season = c_m1.text_input("시즌", value="25-26")
    league = c_m2.text_input("리그명", value="PL")
    match_date = c_m3.text_input("경기 날짜", value="25.08.16")
    
    c_t1, c_t2 = st.columns(2)
    home_team = c_t1.text_input("홈팀", value="리버풀")
    away_team = c_t2.text_input("원정팀", value="본머스")

    st.markdown("---")
    st.subheader("2️⃣ 9대 북메이커 최종 배당 입력 (미제공 시 0으로 설정)")
    
    odds_inputs = {}
    for i in range(0, len(BOOKMAKERS), 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < len(BOOKMAKERS):
                bm = BOOKMAKERS[idx]
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**🏢 [{idx+1}] {bm.upper()}**")
                        oh, od, oa = st.columns(3)
                        def_h = 1.22 if bm == "배트맨" else (1.31 if bm == "bwin" else 0.0)
                        def_d = 5.10 if bm == "배트맨" else (5.75 if bm == "bwin" else 0.0)
                        def_a = 7.50 if bm == "배트맨" else (8.00 if bm == "bwin" else 0.0)
                        
                        h_val = oh.number_input("홈", value=def_h, step=0.01, min_value=0.0, key=f"in_{bm}_h")
                        d_val = od.number_input("무", value=def_d, step=0.01, min_value=0.0, key=f"in_{bm}_d")
                        a_val = oa.number_input("원정", value=def_a, step=0.01, min_value=0.0, key=f"in_{bm}_a")
                        odds_inputs[bm] = (h_val, d_val, a_val)

    st.markdown("---")
    st.subheader("3️⃣ 인게임 세부 경기내용 스탯 입력 (10번 '경기내용' 탭용)")
    
    with st.expander("⚽ 전/후반 득점 및 포메이션(전술)", expanded=True):
        c_g1, c_g2, c_g3, c_g4 = st.columns(4)
        home_1h = c_g1.number_input("홈 전반 득점", min_value=0, value=1)
        home_2h = c_g2.number_input("홈 후반 득점", min_value=0, value=3)
        away_1h = c_g3.number_input("원정 전반 득점", min_value=0, value=0)
        away_2h = c_g4.number_input("원정 후반 득점", min_value=0, value=2)
        
        c_tac1, c_tac2 = st.columns(2)
        home_tac = c_tac1.text_input("홈팀 전술(포메이션)", value="4-2-3-1")
        away_tac = c_tac2.text_input("원정팀 전술(포메이션)", value="4-1-4-1")

    with st.expander("📊 슈팅 / 점유율 / 패스 / 파울 / xG 세부 스탯", expanded=True):
        c_st1, c_st2, c_st3, c_st4 = st.columns(4)
        home_shots = c_st1.number_input("홈 슈팅", min_value=0, value=19)
        away_shots = c_st2.number_input("원정 슈팅", min_value=0, value=10)
        home_sot = c_st3.number_input("홈 유효슈팅", min_value=0, value=10)
        away_sot = c_st4.number_input("원정 유효슈팅", min_value=0, value=3)

        c_ps1, c_ps2, c_ps3, c_ps4 = st.columns(4)
        home_poss = c_ps1.number_input("홈 점유율 (%)", min_value=0.0, max_value=100.0, value=61.0, step=0.1)
        away_poss = c_ps2.number_input("원정 점유율 (%)", min_value=0.0, max_value=100.0, value=39.0, step=0.1)
        home_pass = c_ps3.number_input("홈 패스성공률 (%)", min_value=0.0, max_value=100.0, value=82.0, step=0.1)
        away_pass = c_ps4.number_input("원정 패스성공률 (%)", min_value=0.0, max_value=100.0, value=70.0, step=0.1)

        c_cd1, c_cd2, c_cd3, c_cd4, c_xg1, c_xg2 = st.columns(6)
        home_yc = c_cd1.number_input("홈 경고(옐로)", min_value=0, value=1)
        away_yc = c_cd2.number_input("원정 경고(옐로)", min_value=0, value=2)
        home_rc = c_cd3.number_input("홈 퇴장(레드)", min_value=0, value=0)
        away_rc = c_cd4.number_input("원정 퇴장(레드)", min_value=0, value=0)
        home_xg = c_xg1.number_input("홈 xG", min_value=0.0, value=2.21, step=0.01)
        away_xg = c_xg2.number_input("원정 xG", min_value=0.0, value=1.70, step=0.01)

    # 전/후반 합산 최종 스코어 자동 연산
    home_score = home_1h + home_2h
    away_score = away_1h + away_2h

    st.markdown("---")
    if st.button("💾 구글 시트 1~9번 배당 탭 & 10번 경기내용 탭 일괄 저장 실행", type="primary", use_container_width=True):
        client = get_gspread_client()
        if client:
            with st.spinner("구글 스프레드시트에 배당 및 경기내용 저장 중..."):
                try:
                    spreadsheet = client.open_by_key(SPREADSHEET_ID)
                    
                    # ----------------- [A] 1~9번 배당 탭 저장 연산 -----------------
                    b_h, b_d, b_a = odds_inputs.get("배트맨", (0.0, 0.0, 0.0))
                    if b_h > 0 and b_d > 0 and b_a > 0:
                        b_inv = (1/b_h) + (1/b_d) + (1/b_a)
                        b_payout = 1 / b_inv
                        b_prob_h = (1/b_h) / b_inv
                        b_prob_d = (1/b_d) / b_inv
                        b_prob_a = (1/b_a) / b_inv
                    else:
                        b_payout, b_prob_h, b_prob_d, b_prob_a = 0.0, 0.0, 0.0, 0.0

                    if home_score > away_score:
                        match_res = "홈승"
                    elif home_score == away_score:
                        match_res = "무승부"
                    else:
                        match_res = "원정승"

                    score_total = home_score + away_score
                    score_diff = home_score - away_score
                    score_diff_abs = abs(score_diff)
                    
                    saved_odds_count = 0
                    skipped_list = []
                    
                    for bm_name in BOOKMAKERS:
                        h, d, a = odds_inputs[bm_name]
                        if h <= 0 or d <= 0 or a <= 0:
                            skipped_list.append(bm_name)
                            continue
                        
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
                            home_score, away_score, score_total, score_diff, score_diff_abs,
                            odd_type, match_res, win_odd
                        ]
                        
                        try:
                            ws = spreadsheet.worksheet(bm_name)
                            ws.append_row(row_data_odds, value_input_option="USER_ENTERED")
                            saved_odds_count += 1
                        except gspread.exceptions.WorksheetNotFound:
                            st.warning(f"⚠️ '{bm_name}' 탭을 찾을 수 없습니다.")

                    # ----------------- [B] 10번 '경기내용' 탭 저장 연산 -----------------
                    # 득점 비율 계산
                    h_1h_ratio = round((home_1h / home_score) * 100, 2) if home_score > 0 else 0.0
                    h_2h_ratio = round((home_2h / home_score) * 100, 2) if home_score > 0 else 0.0
                    a_1h_ratio = round((away_1h / away_score) * 100, 2) if away_score > 0 else 0.0
                    a_2h_ratio = round((away_2h / away_score) * 100, 2) if away_score > 0 else 0.0
                    
                    # 유효슈팅 비율 계산
                    h_sot_ratio = round((home_sot / home_shots) * 100, 2) if home_shots > 0 else 0.0
                    a_sot_ratio = round((away_sot / away_shots) * 100, 2) if away_shots > 0 else 0.0

                    row_data_stats = [
                        season, league, match_date, home_team, away_team,
                        home_1h, home_2h, away_1h, away_2h,
                        f"{h_1h_ratio}%", f"{h_2h_ratio}%", f"{a_1h_ratio}%", f"{a_2h_ratio}%",
                        home_tac, away_tac,
                        home_shots, away_shots, home_sot, away_sot,
                        f"{h_sot_ratio}%", f"{a_sot_ratio}%",
                        f"{home_poss}%", f"{away_poss}%",
                        f"{home_pass}%", f"{away_pass}%",
                        home_yc, away_yc, home_rc, away_rc,
                        home_xg, away_xg
                    ]

                    try:
                        ws_stats = spreadsheet.worksheet(STATS_SHEET_NAME)
                        ws_stats.append_row(row_data_stats, value_input_option="USER_ENTERED")
                        stats_saved = True
                    except gspread.exceptions.WorksheetNotFound:
                        st.warning(f"⚠️ '{STATS_SHEET_NAME}' 탭을 찾을 수 없습니다.")
                        stats_saved = False
                    
                    # 저장 결과 피드백
                    st.success(f"🎉 성공: 배당 탭 {saved_odds_count}개 및 '경기내용' 탭에 데이터 저장이 완료되었습니다!")
                    if skipped_list:
                        st.info(f"ℹ️ 배당 미입력 건너뜀: {', '.join(skipped_list)}")
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")

with tab_analysis:
    st.info("📊 데이터가 누적되면 배당 및 경기내용 통합 매칭 통계가 출력됩니다.")
