import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 1. 페이지 기본 설정
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
INJURY_SHEET_NAME = "부상자명단"
SPREADSHEET_ID = "1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ"

st.title("⚽ 축구 9대 배당 업체 & 경기 세부 스탯 통합 분석 허브")

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
        return None
    except Exception:
        return None

# 구글 시트 탭 실시간 데이터 로더
@st.cache_data(ttl=10, show_spinner=False)
def load_sheet_data(sheet_name):
    client = get_gspread_client()
    if not client:
        return pd.DataFrame()
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        ws = spreadsheet.worksheet(sheet_name)
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# 3. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.caption(f"연동 시트 ID: `{SPREADSHEET_ID}`")
    tol = st.number_input("배당 오차 허용치 (±)", value=0.03, step=0.01)
    if st.button("🔄 전체 시트 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 4. 4개 탭 구성
tab_input, tab_analysis, tab_team_stats, tab_injuries = st.tabs([
    "📝 데이터 입력 및 통합 저장", 
    "📊 9개사 동일 배당 승률 분석", 
    "📈 팀별 세부 경기내용 평균계산기",
    "🚑 팀별 부상자/결장자 명단 (11번 시트 연동)"
])

# =========================================================
# TAB 1: 데이터 입력 및 저장
# =========================================================
with tab_input:
    st.subheader("1️⃣ 경기 기본 정보 & 팀명")
    c_m1, c_m2, c_m3 = st.columns(3)
    season = c_m1.text_input("시즌", value="25-26", key="in_season")
    league = c_m2.text_input("리그명", value="PL", key="in_league")
    match_date = c_m3.text_input("경기 날짜", value="25.08.16", key="in_match_date")
    
    c_t1, c_t2 = st.columns(2)
    home_team = c_t1.text_input("홈팀", value="리버풀", key="in_home_team")
    away_team = c_t2.text_input("원정팀", value="본머스", key="in_away_team")

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
        home_1h = c_g1.number_input("홈 전반 득점", min_value=0, value=1, key="in_home_1h")
        home_2h = c_g2.number_input("홈 후반 득점", min_value=0, value=3, key="in_home_2h")
        away_1h = c_g3.number_input("원정 전반 득점", min_value=0, value=0, key="in_away_1h")
        away_2h = c_g4.number_input("원정 후반 득점", min_value=0, value=2, key="in_away_2h")
        
        c_tac1, c_tac2 = st.columns(2)
        home_tac = c_tac1.text_input("홈팀 전술(포메이션)", value="4-2-3-1", key="in_home_tac")
        away_tac = c_tac2.text_input("원정팀 전술(포메이션)", value="4-1-4-1", key="in_away_tac")

    with st.expander("📊 슈팅 / 점유율 / 패스 / 파울 / xG 세부 스탯", expanded=True):
        c_st1, c_st2, c_st3, c_st4 = st.columns(4)
        home_shots = c_st1.number_input("홈 슈팅", min_value=0, value=19, key="in_home_shots")
        away_shots = c_st2.number_input("원정 슈팅", min_value=0, value=10, key="in_away_shots")
        home_sot = c_st3.number_input("홈 유효슈팅", min_value=0, value=10, key="in_home_sot")
        away_sot = c_st4.number_input("원정 유효슈팅", min_value=0, value=3, key="in_away_sot")

        c_ps1, c_ps2, c_ps3, c_ps4 = st.columns(4)
        home_poss = c_ps1.number_input("홈 점유율 (%)", min_value=0.0, max_value=100.0, value=61.0, step=0.1, key="in_home_poss")
        away_poss = c_ps2.number_input("원정 점유율 (%)", min_value=0.0, max_value=100.0, value=39.0, step=0.1, key="in_away_poss")
        home_pass = c_ps3.number_input("홈 패스성공률 (%)", min_value=0.0, max_value=100.0, value=82.0, step=0.1, key="in_home_pass")
        away_pass = c_ps4.number_input("원정 패스성공률 (%)", min_value=0.0, max_value=100.0, value=70.0, step=0.1, key="in_away_pass")

        c_cd1, c_cd2, c_cd3, c_cd4, c_xg1, c_xg2 = st.columns(6)
        home_yc = c_cd1.number_input("홈 경고(옐로)", min_value=0, value=1, key="in_home_yc")
        away_yc = c_cd2.number_input("원정 경고(옐로)", min_value=0, value=2, key="in_away_yc")
        home_rc = c_cd3.number_input("홈 퇴장(레드)", min_value=0, value=0, key="in_home_rc")
        away_rc = c_cd4.number_input("원정 퇴장(레드)", min_value=0, value=0, key="in_away_rc")
        home_xg = c_xg1.number_input("홈 xG", min_value=0.0, value=2.21, step=0.01, key="in_home_xg")
        away_xg = c_xg2.number_input("원정 xG", min_value=0.0, value=1.70, step=0.01, key="in_away_xg")

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
                            pass

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
                        pass
                    
                    st.cache_data.clear()
                    st.success(f"🎉 성공: 배당 {saved_odds_count}개 탭 & '경기내용' 탭에 저장이 완료되었습니다!")
                    if skipped_list:
                        st.info(f"ℹ️ 배당 미입력 건너뜀: {', '.join(skipped_list)}")
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")

# =========================================================
# TAB 2: 배당률 과거 승률 분석 (평균 행 + 상세 매칭 리스트 복구)
# =========================================================
with tab_analysis:
    st.subheader(f"📊 9대 북메이커 동일 배당 (오차 ±{tol}) 과거 승률 분석")
    analysis_rows = []
    matched_detail_dfs = {}
    
    total_valid_bm = 0
    total_payout_sum = 0.0
    total_matches_count = 0
    total_hw_count = 0
    total_dr_count = 0
    total_aw_count = 0
    
    for idx, bm in enumerate(BOOKMAKERS, 1):
        target_h, target_d, target_a = odds_inputs.get(bm, (0.0, 0.0, 0.0))
        if target_h <= 0 or target_d <= 0 or target_a <= 0:
            analysis_rows.append({
                "순번": str(idx), "북메이커": bm.upper(), "입력 배당": "미입력", "환급률": "-",
                "매칭 경기": "0건", "홈승 확률": "-", "무승부 확률": "-", "원정승 확률": "-"
            })
            continue

        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout = (1 / raw_inv) * 100
        total_payout_sum += payout
        total_valid_bm += 1

        df_bm = load_sheet_data(bm)
        
        match_count = 0
        h_str, d_str, a_str = "0.0%", "0.0%", "0.0%"
        
        if not df_bm.empty:
            try:
                # 배당 열 자동 감지 (해당_홈 또는 홈 또는 13번째 열 등 유연하게 탐색)
                h_col = "해당_홈" if "해당_홈" in df_bm.columns else (df_bm.columns[12] if len(df_bm.columns) > 12 else None)
                d_col = "해당_무" if "해당_무" in df_bm.columns else (df_bm.columns[13] if len(df_bm.columns) > 13 else None)
                a_col = "해당_원" if "해당_원" in df_bm.columns else (df_bm.columns[14] if len(df_bm.columns) > 14 else None)
                res_col = "경기결과" if "경기결과" in df_bm.columns else (df_bm.columns[32] if len(df_bm.columns) > 32 else None)
                
                if h_col and d_col and a_col and res_col:
                    df_bm["H_num"] = pd.to_numeric(df_bm[h_col], errors="coerce")
                    df_bm["D_num"] = pd.to_numeric(df_bm[d_col], errors="coerce")
                    df_bm["A_num"] = pd.to_numeric(df_bm[a_col], errors="coerce")
                    
                    cond = (
                        (df_bm["H_num"] >= target_h - tol) & (df_bm["H_num"] <= target_h + tol) &
                        (df_bm["D_num"] >= target_d - tol) & (df_bm["D_num"] <= target_d + tol) &
                        (df_bm["A_num"] >= target_a - tol) & (df_bm["A_num"] <= target_a + tol)
                    )
                    matched_df = df_bm[cond]
                    match_count = len(matched_df)
                    
                    if match_count > 0:
                        matched_detail_dfs[bm.upper()] = matched_df
                        res_c = matched_df[res_col].value_counts()
                        hw = res_c.get("홈승", 0)
                        dr = res_c.get("무승부", 0)
                        aw = res_c.get("원정승", 0)
                        
                        total_matches_count += match_count
                        total_hw_count += hw
                        total_dr_count += dr
                        total_aw_count += aw
                        
                        h_str = f"{round((hw/match_count)*100, 1)}% ({hw}회)"
                        d_str = f"{round((dr/match_count)*100, 1)}% ({dr}회)"
                        a_str = f"{round((aw/match_count)*100, 1)}% ({aw}회)"
            except Exception:
                pass
        
        analysis_rows.append({
            "순번": str(idx), "북메이커": bm.upper(),
            "입력 배당": f"{target_h} / {target_d} / {target_a}",
            "환급률": f"{round(payout, 2)}%",
            "매칭 경기": f"{match_count}건",
            "홈승 확률": h_str, "무승부 확률": d_str, "원정승 확률": a_str
        })

    # 종합 가중평균 행
    avg_payout_str = f"{round(total_payout_sum / total_valid_bm, 2)}%" if total_valid_bm > 0 else "-"
    if total_matches_count > 0:
        avg_h_prob_str = f"{round((total_hw_count / total_matches_count) * 100, 1)}% ({total_hw_count}회)"
        avg_d_prob_str = f"{round((total_dr_count / total_matches_count) * 100, 1)}% ({total_dr_count}회)"
        avg_a_prob_str = f"{round((total_aw_count / total_matches_count) * 100, 1)}% ({total_aw_count}회)"
    else:
        avg_h_prob_str, avg_d_prob_str, avg_a_prob_str = "0.0%", "0.0%", "0.0%"

    analysis_rows.append({
        "순번": "🔥",
        "북메이커": "종합 가중평균 (전체 누적)",
        "입력 배당": f"유효 {total_valid_bm}개사",
        "환급률": avg_payout_str,
        "매칭 경기": f"총 {total_matches_count}건",
        "홈승 확률": avg_h_prob_str,
        "무승부 확률": avg_d_prob_str,
        "원정승 확률": avg_a_prob_str
    })

    # 상단 요약 테이블
    st.dataframe(pd.DataFrame(analysis_rows), use_container_width=True, hide_index=True)

    # -------------------------------------------------------------
    # 하단 매칭 경기 상세 리스트 영역 (복구 완료)
    # -------------------------------------------------------------
    if matched_detail_dfs:
        st.markdown("---")
        st.subheader("📋 매칭된 과거 경기 상세 리스트 (업체별 아코디언)")
        for name, m_df in matched_detail_dfs.items():
            with st.expander(f"📌 [{name}] 매칭 내역 총 {len(m_df)}건 확인하기", expanded=False):
                # 표시할 주요 컬럼 우선 선별
                pref_cols = ["시즌", "리그명", "날짜", "홈팀", "원정팀", "해당_홈", "해당_무", "해당_원", "홈스코어", "원정스코어", "경기결과", "정/중/역", "적중배당"]
                show_cols = [c for c in pref_cols if c in m_df.columns]
                
                # 만약 지정 컬럼명이 없으면 전체 컬럼 표시
                if show_cols:
                    st.dataframe(m_df[show_cols], use_container_width=True, hide_index=True)
                else:
                    st.dataframe(m_df, use_container_width=True, hide_index=True)
    else:
        st.markdown("---")
        st.info("💡 현재 입력된 배당과 일치(오차 범위 내)하는 과거 경기 데이터가 아직 없습니다.")

# =========================================================
# TAB 3: 팀별 경기내용 평균계산기
# =========================================================
with tab_team_stats:
    st.subheader("📈 팀별 과거 세부 경기내용 평균계산기")
    df_stats_all = load_sheet_data(STATS_SHEET_NAME)
    
    c_f1, c_f2, c_f3 = st.columns(3)
    available_seasons = sorted(df_stats_all["시즌"].dropna().unique().tolist()) if not df_stats_all.empty and "시즌" in df_stats_all.columns else ["25-26", "2025"]
    available_leagues = sorted(df_stats_all["리그명"].dropna().unique().tolist()) if not df_stats_all.empty and "리그명" in df_stats_all.columns else ["PL", "EPL"]
    
    teams_set = set()
    if not df_stats_all.empty:
        if "홈팀" in df_stats_all.columns:
            teams_set.update(df_stats_all["홈팀"].dropna().unique())
        if "원정팀" in df_stats_all.columns:
            teams_set.update(df_stats_all["원정팀"].dropna().unique())
    available_teams = sorted(list(teams_set)) if teams_set else ["맨체스터시티", "리버풀", "본머스", "웨스트햄"]

    sel_season = c_f1.selectbox("시즌", available_seasons if available_seasons else ["전체"], key="sel_stat_season")
    sel_league = c_f2.selectbox("경기구분 (리그)", available_leagues if available_leagues else ["전체"], key="sel_stat_league")
    sel_team = c_f3.selectbox("경기목록 (팀이름)", available_teams if available_teams else ["팀 선택"], key="sel_stat_team")

    st.markdown("---")

    if not df_stats_all.empty and "홈팀" in df_stats_all.columns:
        df_target = df_stats_all.copy()
        if sel_season != "전체":
            df_target = df_target[df_target["시즌"] == sel_season]
        if sel_league != "전체":
            df_target = df_target[df_target["리그명"] == sel_league]

        df_home_matches = df_target[df_target["홈팀"] == sel_team]
        df_away_matches = df_target[df_target["원정팀"] == sel_team]

        def to_num(series):
            return pd.to_numeric(series.astype(str).str.replace("%", "").str.strip(), errors="coerce").fillna(0)

        h_cnt = len(df_home_matches)
        a_cnt = len(df_away_matches)
        total_cnt = h_cnt + a_cnt

        h_1h_goals = to_num(df_home_matches["전반득점_홈"]).sum() if h_cnt > 0 else 0
        h_2h_goals = to_num(df_home_matches["후반득점_홈"]).sum() if h_cnt > 0 else 0
        h_tot_goals = h_1h_goals + h_2h_goals

        a_1h_goals = to_num(df_away_matches["전반득점_원"]).sum() if a_cnt > 0 else 0
        a_2h_goals = to_num(df_away_matches["후반득점_원"]).sum() if a_cnt > 0 else 0
        a_tot_goals = a_1h_goals + a_2h_goals

        h_1h_avg = round(h_1h_goals / h_cnt, 2) if h_cnt > 0 else 0.0
        h_2h_avg = round(h_2h_goals / h_cnt, 2) if h_cnt > 0 else 0.0
        h_tot_avg = round(h_tot_goals / h_cnt, 2) if h_cnt > 0 else 0.0

        a_1h_avg = round(a_1h_goals / a_cnt, 2) if a_cnt > 0 else 0.0
        a_2h_avg = round(a_2h_goals / a_cnt, 2) if a_cnt > 0 else 0.0
        a_tot_avg = round(a_tot_goals / a_cnt, 2) if a_cnt > 0 else 0.0

        tot_1h_avg = round((h_1h_goals + a_1h_goals) / total_cnt, 2) if total_cnt > 0 else 0.0
        tot_2h_avg = round((h_2h_goals + a_2h_goals) / total_cnt, 2) if total_cnt > 0 else 0.0
        tot_all_avg = round((h_tot_goals + a_tot_goals) / total_cnt, 2) if total_cnt > 0 else 0.0

        def calc_avg(h_col, a_col):
            h_val = to_num(df_home_matches[h_col]).mean() if h_cnt > 0 and h_col in df_home_matches.columns else 0.0
            a_val = to_num(df_away_matches[a_col]).mean() if a_cnt > 0 and a_col in df_away_matches.columns else 0.0
            tot_val = (to_num(df_home_matches[h_col]).sum() + to_num(df_away_matches[a_col]).sum()) / total_cnt if total_cnt > 0 else 0.0
            return round(h_val, 2), round(a_val, 2), round(tot_val, 2)

        poss_h, poss_a, poss_tot = calc_avg("점유율_홈", "점유율_원")
        sot_h, sot_a, sot_tot = calc_avg("유효슈팅_홈", "유효슈팅_원")
        pass_h, pass_a, pass_tot = calc_avg("패스성공률_홈", "패스성공률_원")
        yc_h, yc_a, yc_tot = calc_avg("경고_홈", "경고_원")
        rc_h, rc_a, rc_tot = calc_avg("퇴장_홈", "퇴장_원")
        xg_h, xg_a, xg_tot = calc_avg("xG_홈", "xG_원")
        ratio_h, ratio_a, ratio_tot = calc_avg("유효슈팅비율_홈", "유효슈팅비율_원")

        st.markdown(f"### 📋 [{sel_team}] 시즌 평균 지표 종합 요약 (총 {total_cnt}경기: 홈 {h_cnt}경기 / 원정 {a_cnt}경기)")

        stat_summary_data = {
            "구분": ["점유율 (%)", "유효슈팅 (회)", "패스성공률 (%)", "경고 (회)", "퇴장 (회)", "xG (기대득점)", "유효슈팅비율 (%)"],
            "홈 (Home)": [f"{poss_h}%", f"{sot_h}", f"{pass_h}%", f"{yc_h}", f"{rc_h}", f"{xg_h}", f"{ratio_h}%"],
            "원정 (Away)": [f"{poss_a}%", f"{sot_a}", f"{pass_a}%", f"{yc_a}", f"{rc_a}", f"{xg_a}", f"{ratio_a}%"],
            "시즌 전체 평균": [f"{poss_tot}%", f"{sot_tot}", f"{pass_tot}%", f"{yc_tot}", f"{rc_tot}", f"{xg_tot}", f"{ratio_tot}%"]
        }
        st.dataframe(pd.DataFrame(stat_summary_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ⚽ 전/후반 득점 통계표")

        goal_table_data = {
            "구분": ["홈", "원정", "시즌 평균"],
            "전반 총득점": [int(h_1h_goals), int(a_1h_goals), "-"],
            "후반 총득점": [int(h_2h_goals), int(a_2h_goals), "-"],
            "총점": [int(h_tot_goals), int(a_tot_goals), "-"],
            "전반 평균": [h_1h_avg, a_1h_avg, tot_1h_avg],
            "후반 평균": [h_2h_avg, a_2h_avg, tot_2h_avg],
            "합계 평균": [h_tot_avg, a_tot_avg, tot_all_avg]
        }
        st.dataframe(pd.DataFrame(goal_table_data), use_container_width=True, hide_index=True)
    else:
        st.info("💡 10번 '경기내용' 탭에 아직 데이터가 없습니다.")

# =========================================================
# TAB 4: 11번 구글 시트 연동 팀별 부상자/결장자 카드 리포트
# =========================================================
with tab_injuries:
    st.subheader("🚑 팀별 부상자/결장자 명단 및 카드 리포트 (11번 시트 연동)")
    
    df_injuries = load_sheet_data(INJURY_SHEET_NAME)

    c_s1, c_s2 = st.columns(2)
    team_options = sorted(df_injuries["팀명"].dropna().unique().tolist()) if not df_injuries.empty and "팀명" in df_injuries.columns else ["웨스트햄", "리버풀", "맨체스터시티"]
    selected_team = c_s1.selectbox("조회할 팀명 선택", team_options if team_options else ["직접 등록 필요"], key="inj_filter_team")
    
    inj_league_title = c_s2.text_input("리그/대회 기준 표기", value="잉글랜드 1부리그 기록", key="inj_custom_league")

    with st.expander(f"➕ [{selected_team}] 새로운 결장 선수 구글 시트에 추가", expanded=False):
        f_s1, f_s2, f_s3 = st.columns(3)
        add_season = f_s1.text_input("시즌", value="25-26", key="add_inj_season")
        add_league = f_s2.text_input("리그명", value="PL", key="add_inj_league")
        add_team = f_s3.text_input("팀명", value=selected_team, key="add_inj_team")

        f1, f2, f3 = st.columns(3)
        p_name_en = f1.text_input("선수 영문명", placeholder="예: Lucas Paquetá", key="p_name_en")
        p_name_kr = f2.text_input("선수 한글명", placeholder="예: 루카스 파케타", key="p_name_kr")
        p_pos = f3.selectbox("포지션", ["FW", "MF", "DF", "GK"], key="p_pos")

        f4, f5, f6, f7 = st.columns(4)
        p_start = f4.number_input("선발 출전", min_value=0, value=0, key="p_start")
        p_sub = f5.number_input("교체 출전", min_value=0, value=0, key="p_sub")
        p_goals = f6.number_input("골", min_value=0, value=0, key="p_goals")
        p_assists = f7.number_input("도움", min_value=0, value=0, key="p_assists")

        f8, f9, f10 = st.columns(3)
        p_role = f8.text_input("팀 내 역할", value="주전", placeholder="예: 주전, 로테이션, 백업", key="p_role")
        p_reason = f9.selectbox("결장 사유", ["부상", "결장의심", "징계/퇴장", "기타"], key="p_reason")
        p_note = f10.text_input("특이사항", value="-", placeholder="예: 팀 내 득점 3위", key="p_note")

        if st.button("💾 구글 시트 11번 탭(부상자명단)에 저장", type="primary", use_container_width=True):
            if p_name_en.strip() or p_name_kr.strip():
                client = get_gspread_client()
                if client:
                    try:
                        spreadsheet = client.open_by_key(SPREADSHEET_ID)
                        ws_inj = spreadsheet.worksheet(INJURY_SHEET_NAME)
                        new_row = [
                            add_season, add_league, add_team,
                            p_name_en.strip(), p_name_kr.strip(),
                            p_pos, p_start, p_sub, p_goals, p_assists,
                            p_role.strip() if p_role.strip() else "-",
                            p_reason,
                            p_note.strip() if p_note.strip() else "-"
                        ]
                        ws_inj.append_row(new_row, value_input_option="USER_ENTERED")
                        st.cache_data.clear()
                        st.success(f"🎉 {add_team}의 [{p_name_kr or p_name_en}] 선수가 11번 시트에 성공적으로 저장되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
            else:
                st.warning("선수 이름을 최소 1개 이상 입력해 주세요.")

    st.markdown("---")

    if not df_injuries.empty and "팀명" in df_injuries.columns:
        filtered_df = df_injuries[df_injuries["팀명"] == selected_team]

        if not filtered_df.empty:
            st.subheader(f"📋 [{selected_team}] 결장자 현황 (총 {len(filtered_df)}명)")

            reason_col = "결장사유" if "결장사유" in filtered_df.columns else "사유"
            confirmed_players = filtered_df[filtered_df[reason_col] != "결장의심"].to_dict("records")
            doubt_players = filtered_df[filtered_df[reason_col] == "결장의심"].to_dict("records")

            card_text = f"### 🚑 {selected_team} 결장 & 결장의심 명단\n"
            card_text += f"*({inj_league_title})*\n\n"

            if confirmed_players:
                card_text += "🔴 **[결장 확정]**\n"
                for p in confirmed_players:
                    kr = p.get("선수한글명", "")
                    en = p.get("선수영문명", "")
                    name_str = f"{kr} ({en})" if kr and en else (kr or en)
                    role = p.get("역할", "-")
                    pos = p.get("포지션", "MF")
                    start = p.get("선발", 0)
                    sub = p.get("교체", 0)
                    goals = p.get("골", 0)
                    assists = p.get("도움", 0)
                    reason = p.get(reason_col, "부상")
                    note = p.get("특이사항", "-")
                    
                    icon = "👑" if "주전" in role else "🏃"
                    note_str = f" *({note})*" if note != "-" else ""
                    
                    card_text += f"* {icon} **{name_str}** | `{pos}` · `{role}`\n"
                    card_text += f"  * 📊 **기록**: {start}선발 {sub}교체 / {goals}골 {assists}도움\n"
                    card_text += f"  * ⚠️ **사유**: {reason}{note_str}\n\n"

            if doubt_players:
                card_text += "---\n\n🟡 **[결장 의심 (GTD)]**\n"
                for p in doubt_players:
                    kr = p.get("선수한글명", "")
                    en = p.get("선수영문명", "")
                    name_str = f"{kr} ({en})" if kr and en else (kr or en)
                    role = p.get("역할", "-")
                    pos = p.get("포지션", "MF")
                    start = p.get("선발", 0)
                    sub = p.get("교체", 0)
                    goals = p.get("골", 0)
                    assists = p.get("도움", 0)
                    reason = p.get(reason_col, "결장의심")
                    note = p.get("특이사항", "-")
                    
                    note_str = f" *({note})*" if note != "-" else ""
                    
                    card_text += f"* ❓ **{name_str}** | `{pos}` · `{role}`\n"
                    card_text += f"  * 📊 **기록**: {start}선발 {sub}교체 / {goals}골 {assists}도움\n"
                    card_text += f"  * ⚠️ **사유**: {reason}{note_str}\n\n"

            st.markdown(card_text)

            st.markdown("---")
            st.subheader(f"📋 [{selected_team}] 블로그 복사용 텍스트 (Ctrl+C로 복사)")
            st.text_area("복사창", value=card_text, height=350)
            
            with st.expander("🔍 시트에 저장된 원본 데이터 표 보기"):
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 현재 [{selected_team}]에 등록된 결장 선수가 없습니다. 위의 '➕ 새로운 결장 선수 추가'에서 등록해 보세요.")
    else:
        st.info("💡 11번 구글 시트(`부상자명단`)에 데이터가 없거나 탭이 생성되지 않았습니다.")
