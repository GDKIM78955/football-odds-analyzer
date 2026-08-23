import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 설정
st.set_page_config(
    page_title="Football 9-Bookmakers Hub",
    page_icon="⚽",
    layout="wide"
)

BOOKMAKERS = [
    "bwin", "10x10", "1xbet", "betway", 
    "william hill", "bet365", "pinnacle", "stake", "배트맨"
]
SPREADSHEET_ID = "1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ"

st.title("⚽ 축구 9대 배당 업체 정밀 분석 & 시트 자동 연동 시스템")

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
            st.error("Secrets에 GCP 서비스 계정 키가 설정되지 않았습니다.")
            return None
    except Exception as e:
        st.error(f"연동 실패: {e}")
        return None

tab_input, tab_analysis = st.tabs(["📝 배당 데이터 입력 및 저장", "📊 동일 배당 통계"])

with tab_input:
    st.subheader("1️⃣ 경기 기본 정보 & 스코어")
    c_m1, c_m2, c_m3 = st.columns(3)
    season = c_m1.text_input("시즌", value="25-26")
    league = c_m2.text_input("리그명", value="PL")
    match_date = c_m3.text_input("경기 날짜", value="25.08.16")
    
    c_t1, c_t2, c_s1, c_s2 = st.columns(4)
    home_team = c_t1.text_input("홈팀", value="리버풀")
    away_team = c_t2.text_input("원정팀", value="본머스")
    home_score = c_s1.number_input("홈 득점", min_value=0, value=4)
    away_score = c_s2.number_input("원정 득점", min_value=0, value=2)

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
                        # 기본 예시값
                        def_h = 1.22 if bm == "배트맨" else (1.31 if bm == "bwin" else 0.0)
                        def_d = 5.10 if bm == "배트맨" else (5.75 if bm == "bwin" else 0.0)
                        def_a = 7.50 if bm == "배트맨" else (8.00 if bm == "bwin" else 0.0)
                        
                        h_val = oh.number_input("홈", value=def_h, step=0.01, min_value=0.0, key=f"in_{bm}_h")
                        d_val = od.number_input("무", value=def_d, step=0.01, min_value=0.0, key=f"in_{bm}_d")
                        a_val = oa.number_input("원정", value=def_a, step=0.01, min_value=0.0, key=f"in_{bm}_a")
                        odds_inputs[bm] = (h_val, d_val, a_val)

    st.markdown("---")
    if st.button("💾 구글 시트 9개 탭에 일괄 자동 연산 저장 실행", type="primary", use_container_width=True):
        client = get_gspread_client()
        if client:
            with st.spinner("구글 스프레드시트에 정밀 계산 데이터 저장 중..."):
                try:
                    spreadsheet = client.open_by_key(SPREADSHEET_ID)
                    
                    # 1. 베트맨 배당 기본값 및 확률/환급률 산출
                    b_h, b_d, b_a = odds_inputs.get("배트맨", (0.0, 0.0, 0.0))
                    if b_h > 0 and b_d > 0 and b_a > 0:
                        b_inv = (1/b_h) + (1/b_d) + (1/b_a)
                        b_payout = 1 / b_inv
                        b_prob_h = (1/b_h) / b_inv
                        b_prob_d = (1/b_d) / b_inv
                        b_prob_a = (1/b_a) / b_inv
                    else:
                        b_payout, b_prob_h, b_prob_d, b_prob_a = 0.0, 0.0, 0.0, 0.0

                    # 2. 스코어 및 승패 판정
                    if home_score > away_score:
                        match_res = "홈승"
                    elif home_score == away_score:
                        match_res = "무승부"
                    else:
                        match_res = "원정승"

                    score_total = home_score + away_score
                    score_diff = home_score - away_score
                    
                    saved_count = 0
                    skipped_list = []
                    
                    for bm_name in BOOKMAKERS:
                        h, d, a = odds_inputs[bm_name]
                        if h <= 0 or d <= 0 or a <= 0:
                            skipped_list.append(bm_name)
                            continue
                        
                        # 해당 업체 확률 & 환급률
                        bm_inv = (1/h) + (1/d) + (1/a)
                        bm_payout = 1 / bm_inv
                        bm_prob_h = (1/h) / bm_inv
                        bm_prob_d = (1/d) / bm_inv
                        bm_prob_a = (1/a) / bm_inv
                        
                        # 배당 편차 (베트맨 - 해당업체)
                        diff_h = round(b_h - h, 2) if b_h > 0 else 0.0
                        diff_d = round(b_d - d, 2) if b_d > 0 else 0.0
                        diff_a = round(b_a - a, 2) if b_a > 0 else 0.0
                        
                        # 적정 배당 (베트맨 환급률 / 해당업체 확률)
                        fair_h = round(b_payout / bm_prob_h, 6) if (b_payout > 0 and bm_prob_h > 0) else 0.0
                        fair_d = round(b_payout / bm_prob_d, 6) if (b_payout > 0 and bm_prob_d > 0) else 0.0
                        fair_a = round(b_payout / bm_prob_a, 6) if (b_payout > 0 and bm_prob_a > 0) else 0.0
                        
                        # 손상률
                        loss_h = round(((b_h - fair_h) / fair_h) * 100, 5) if fair_h > 0 else 0.0
                        loss_d = round(((b_d - fair_d) / fair_d) * 100, 5) if fair_d > 0 else 0.0
                        loss_a = round(((b_a - fair_a) / fair_a) * 100, 5) if fair_a > 0 else 0.0
                        
                        # 정/중/역 판정
                        min_odd, max_odd = min(h, d, a), max(h, d, a)
                        win_odd = h if match_res == "홈승" else (d if match_res == "무승부" else a)
                        odd_type = "정배" if win_odd == min_odd else ("역배" if win_odd == max_odd else "중배")

                        # 전체 35개 열 완성 데이터
                        row_data = [
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
                            home_score, away_score, score_total, score_diff, score_diff,
                            odd_type, match_res, win_odd
                        ]
                        
                        try:
                            ws = spreadsheet.worksheet(bm_name)
                            ws.append_row(row_data, value_input_option="USER_ENTERED")
                            saved_count += 1
                        except gspread.exceptions.WorksheetNotFound:
                            st.warning(f"⚠️ '{bm_name}' 탭을 찾을 수 없습니다.")
                    
                    st.success(f"🎉 성공: 총 {saved_count}개 시트에 원본 엑셀 공식 그대로 계산되어 저장되었습니다!")
                    if skipped_list:
                        st.info(f"ℹ️ 배당 미입력 건너뜀: {', '.join(skipped_list)}")
                except Exception as e:
                    st.error(f"저장 중 오류: {e}")

with tab_analysis:
    st.info("📊 과거 경기 배당 데이터가 누적되면 실시간 승률 통계가 활성화됩니다.")
