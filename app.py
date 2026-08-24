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

# 2. 구글 시트 연동 클라이언트
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
        else:
            return None
    except Exception:
        return None

# 시트 데이터 실시간 캐시 조회 함수
@st.cache_data(ttl=10, show_spinner=False)
def load_sheet_data(bm_name):
    client = get_gspread_client()
    if not client:
        return pd.DataFrame()
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        ws = spreadsheet.worksheet(bm_name)
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# 3. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 필터 설정")
    st.caption(f"연동 시트 ID: `{SPREADSHEET_ID}`")
    tol = st.number_input("배당 오차 허용치 (±)", value=0.03, step=0.01)
    if st.button("🔄 시트 데이터 즉시 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 4. 탭 구성
tab_input, tab_analysis = st.tabs(["📝 데이터 입력 및 저장", "📊 9개사 동일 배당 승률 분석"])

# =========================================================
# TAB 1: 데이터 입력 및 저장
# =========================================================
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

    home_score = home_1h + home_2h
    away_score = away_1h + away_2h

    st.markdown("---")
    if st.button("💾 구글 시트 1~9번 배당 탭 & 10번 경기내용 탭 일괄 저장 실행", type="primary", use_container_width=True):
        client = get_gspread_client()
        if client:
            with st.spinner("구글 스프레드시트에 저장 중..."):
                try:
                    spreadsheet = client.open_by_key(SPREADSHEET_ID)
                    
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

                    # 10번 경기내용 탭 저장
                    h_1h_ratio = round((home_1h / home_score) * 100, 2) if home_score > 0 else 0.0
                    h_2h_ratio = round((home_2h / home_score) * 100, 2) if home_score > 0 else 0.0
                    a_1h_ratio = round((away_1h / away_score) * 100, 2) if away_score > 0 else 0.0
                    a_2h_ratio = round((away_2h / away_score) * 100, 2) if away_score > 0 else 0.0
                    
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
                    except gspread.exceptions.WorksheetNotFound:
                        st.warning(f"⚠️ '{STATS_SHEET_NAME}' 탭을 찾을 수 없습니다.")
                    
                    st.cache_data.clear()  # 캐시 비우기
                    st.success(f"🎉 성공: 배당 탭 {saved_odds_count}개 및 '경기내용' 탭에 저장이 완료되었습니다!")
                    if skipped_list:
                        st.info(f"ℹ️ 배당 미입력 건너뜀: {', '.join(skipped_list)}")
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")

# =========================================================
# TAB 2: 구글 시트 실시간 연동 9개사 동일 배당 분석
# =========================================================
with tab_analysis:
    st.subheader(f"📊 9대 북메이커 동일/유사 배당 (오차 ±{tol}) 과거 승률 분석표")
    
    analysis_rows = []
    matched_detail_dfs = {}
    
    for idx, bm in enumerate(BOOKMAKERS, 1):
        target_h, target_d, target_a = odds_inputs.get(bm, (0.0, 0.0, 0.0))
        
        # 입력 배당이 없는 경우
        if target_h <= 0 or target_d <= 0 or target_a <= 0:
            analysis_rows.append({
                "순번": idx,
                "북메이커": bm.upper(),
                "입력 배당 [홈/무/원]": "미입력 (제외)",
                "환급률(%)": "-",
                "매칭 경기수": 0,
                "홈승 확률": "-",
                "무승부 확률": "-",
                "원정승 확률": "-"
            })
            continue

        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout = (1 / raw_inv) * 100
        
        # 구글 시트에서 해당 북메이커 시트 데이터 불러오기
        df_bm = load_sheet_data(bm)
        
        match_count = 0
        h_prob_str = "0.0%"
        d_prob_str = "0.0%"
        a_prob_str = "0.0%"
        
        if not df_bm.empty and "해당_홈" in df_bm.columns and "경기결과" in df_bm.columns:
            try:
                # 숫자 변환
                df_bm["H_num"] = pd.to_numeric(df_bm["해당_홈"], errors="coerce")
                df_bm["D_num"] = pd.to_numeric(df_bm["해당_무"], errors="coerce")
                df_bm["A_num"] = pd.to_numeric(df_bm["해당_원"], errors="coerce")
                
                # 배당 필터링 (오차 범위 내)
                cond = (
                    (df_bm["H_num"] >= target_h - tol) & (df_bm["H_num"] <= target_h + tol) &
                    (df_bm["D_num"] >= target_d - tol) & (df_bm["D_num"] <= target_d + tol) &
                    (df_bm["A_num"] >= target_a - tol) & (df_bm["A_num"] <= target_a + tol)
                )
                matched_df = df_bm[cond]
                match_count = len(matched_df)
                
                if match_count > 0:
                    matched_detail_dfs[bm.upper()] = matched_df
                    res_counts = matched_df["경기결과"].value_counts()
                    hw = res_counts.get("홈승", 0)
                    dr = res_counts.get("무승부", 0)
                    aw = res_counts.get("원정승", 0)
                    
                    h_prob_str = f"{round((hw / match_count) * 100, 1)}% ({hw}회)"
                    d_prob_str = f"{round((dr / match_count) * 100, 1)}% ({dr}회)"
                    a_prob_str = f"{round((aw / match_count) * 100, 1)}% ({aw}회)"
            except Exception:
                pass
        
        analysis_rows.append({
            "순번": idx,
            "북메이커": bm.upper(),
            "입력 배당 [홈/무/원]": f"{target_h} / {target_d} / {target_a}",
            "환급률(%)": f"{round(payout, 2)}%",
            "매칭 경기수": f"{match_count}건",
            "홈승 확률": h_prob_str,
            "무승부 확률": d_prob_str,
            "원정승 확률": a_prob_str
        })

    summary_df = pd.DataFrame(analysis_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    # 매칭된 경기 상세 내역 조회
    if matched_detail_dfs:
        st.markdown("---")
        st.subheader("📋 매칭된 과거 경기 상세 리스트")
        for name, m_df in matched_detail_dfs.items():
            with st.expander(f"📌 {name} 매칭 내역 ({len(m_df)}건)", expanded=False):
                show_cols = [c for c in ["시즌", "리그명", "날짜", "홈팀", "원정팀", "해당_홈", "해당_무", "해당_원", "홈스코어", "원정스코어", "경기결과", "정/중/역"] if c in m_df.columns]
                st.dataframe(m_df[show_cols], use_container_width=True, hide_index=True)
