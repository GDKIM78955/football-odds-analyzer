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

# 2. 9대 배당 업체 정의
BOOKMAKERS = [
    "bwin", "10x10", "1xbet", "betway", 
    "william hill", "bet365", "pinnacle", "stake", "배트맨"
]
STATS_SHEET_NAME = "경기내용"
SPREADSHEET_ID = "1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ"

st.title("⚽ 축구 9대 배당 업체 & 경기내용 통합 분석 시스템")

# 3. 구글 시트 API 연동 함수
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
            st.error("Streamlit Secrets에 `gcp_service_account` 설정이 누락되었습니다.")
            return None
    except Exception as e:
        st.error(f"구글 인증 연동 실패: {e}")
        return None

# 4. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.caption(f"연동 시트 ID: `{SPREADSHEET_ID}`")
    tol = st.number_input("동일/유사 배당 오차 허용치 (±)", value=0.03, step=0.01)

# 5. 2개 탭 구성
tab_input, tab_analysis = st.tabs(["📝 데이터 입력 및 저장", "📊 9개사 동일 배당 승률 분석"])

# =========================================================
# TAB 1: 데이터 입력 및 자동 계산 후 시트 저장
# =========================================================
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
    st.subheader("2️⃣ 9대 업체 최종 배당률 입력 (미제공 업체는 0으로 두면 자동 제외)")
    
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
                        def_h = 1.22 if bm == "배트맨" or bm == "bwin" else (1.25 if idx < 4 else 0.0)
                        def_d = 5.10 if bm == "배트맨" or bm == "bwin" else (5.25 if idx < 4 else 0.0)
                        def_a = 7.50 if bm == "배트맨" or bm == "bwin" else (7.80 if idx < 4 else 0.0)
                        
                        h_val = oh.number_input("홈", value=def_h, step=0.01, min_value=0.0, key=f"in_{bm}_h")
                        d_val = od.number_input("무", value=def_d, step=0.01, min_value=0.0, key=f"in_{bm}_d")
                        a_val = oa.number_input("원정", value=def_a, step=0.01, min_value=0.0, key=f"in_{bm}_a")
                        odds_inputs[bm] = (h_val, d_val, a_val)

    st.markdown("---")
    if st.button("💾 구글 시트 9개 탭에 일괄 분기 저장 실행", type="primary", use_container_width=True):
        client = get_gspread_client()
        if client:
            with st.spinner("구글 스프레드시트에 계산 및 저장 중..."):
                try:
                    spreadsheet = client.open_by_key(SPREADSHEET_ID)
                    
                    # 1. 베트맨 배당 및 지표 계산
                    bm_betman_h, bm_betman_d, bm_betman_a = odds_inputs.get("배트맨", (0.0, 0.0, 0.0))
                    if bm_betman_h > 0 and bm_betman_d > 0 and bm_betman_a > 0:
                        betman_payout = 1 / ((1/bm_betman_h) + (1/bm_betman_d) + (1/bm_betman_a))
                        betman_prob_h = (1/bm_betman_h) / ((1/bm_betman_h) + (1/bm_betman_d) + (1/bm_betman_a))
                    else:
                        betman_payout, betman_prob_h = 0.0, 0.0

                    # 2. 경기 결과 판정
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
                        
                        # 해당 업체 지표 자동 계산
                        bm_payout = 1 / ((1/h) + (1/d) + (1/a))
                        bm_prob_h = (1/h) / ((1/h) + (1/d) + (1/a))
                        
                        # 편차 및 손상률
                        diff_h = round(h - bm_betman_h, 2) if bm_betman_h > 0 else 0.0
                        diff_d = round(d - bm_betman_d, 2) if bm_betman_d > 0 else 0.0
                        diff_a = round(a - bm_betman_a, 2) if bm_betman_a > 0 else 0.0
                        
                        loss_h = round((diff_h / bm_betman_h) * 100, 2) if bm_betman_h > 0 else 0.0
                        loss_d = round((diff_d / bm_betman_d) * 100, 2) if bm_betman_d > 0 else 0.0
                        loss_a = round((diff_a / bm_betman_a) * 100, 2) if bm_betman_a > 0 else 0.0
                        
                        # 적정 배당
                        fair_h = round(1 / ((1/h) / ((1/h) + (1/d) + (1/a))), 2)
                        fair_d = round(1 / ((1/d) / ((1/h) + (1/d) + (1/a))), 2)
                        fair_a = round(1 / ((1/a) / ((1/h) + (1/d) + (1/a))), 2)
                        
                        # 정/중/역 & 적중 배당 판정
                        odds_list = [h, d, a]
                        min_odd = min(odds_list)
                        max_odd = max(odds_list)
                        
                        if match_res == "홈승":
                            win_odd = h
                        elif match_res == "무승부":
                            win_odd = d
                        else:
                            win_odd = a

                        if win_odd == min_odd:
                            odd_type = "정배"
                        elif win_odd == max_odd:
                            odd_type = "역배"
                        else:
                            odd_type = "중배"

                        # A~AE 전체 열 완성 데이터 행
                        row_data = [
                            season, league, match_date, home_team, away_team,
                            bm_betman_h, bm_betman_d, bm_betman_a,
                            f"{round(betman_payout * 100, 2)}%", f"{round(betman_prob_h * 100, 2)}%",
                            h, d, a,
                            f"{round(bm_payout * 100, 2)}%", f"{round(bm_prob_h * 100, 2)}%",
                            diff_h, diff_d, diff_a,
                            f"{loss_h}%", f"{loss_d}%", f"{loss_a}%",
                            fair_h, fair_d, fair_a,
                            home_score, away_score, score_total, score_diff,
                            odd_type, match_res, win_odd
                        ]
                        
                        try:
                            ws = spreadsheet.worksheet(bm_name)
                            ws.append_row(row_data, value_input_option="USER_ENTERED")
                            saved_count += 1
                        except gspread.exceptions.WorksheetNotFound:
                            st.warning(f"⚠️ '{bm_name}' 탭을 찾을 수 없어 건너뛰었습니다.")
                    
                    st.success(f"🎉 성공: 총 {saved_count}개 북메이커 시트에 모든 수식 연산 결과가 완벽하게 저장되었습니다!")
                    if skipped_list:
                        st.info(f"ℹ️ 배당 미입력으로 건너뛴 탭: {', '.join(skipped_list)}")
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")

# =========================================================
# TAB 2: 과거 동일 배당 매칭 통계
# =========================================================
with tab_analysis:
    st.subheader("🔍 9대 북메이커 동일 배당 과거 매칭 통계")
    
    analysis_rows = []
    for idx, bm in enumerate(BOOKMAKERS, 1):
        target_h, target_d, target_a = odds_inputs.get(bm, (0.0, 0.0, 0.0))
        
        if target_h <= 0 or target_d <= 0 or target_a <= 0:
            analysis_rows.append({
                "순번": idx,
                "북메이커": bm.upper(),
                "입력 배당 [홈/무/원]": "미제공 (건너뜀)",
                "환급률(%)": "-",
                "매칭 경기수": "-",
                "홈승 확률(%)": "-",
                "무승부 확률(%)": "-",
                "원정승 확률(%)": "-"
            })
            continue

        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout = (1 / raw_inv) * 100
        
        analysis_rows.append({
            "순번": idx,
            "북메이커": bm.upper(),
            "입력 배당 [홈/무/원]": f"{target_h} / {target_d} / {target_a}",
            "환급률(%)": round(payout, 2),
            "매칭 경기수": 0,
            "홈승 확률(%)": 0.0,
            "무승부 확률(%)": 0.0,
            "원정승 확률(%)": 0.0
        })

    res_df = pd.DataFrame(analysis_rows)
    st.dataframe(res_df, use_container_width=True, hide_index=True)
