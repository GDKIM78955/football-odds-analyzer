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
    "🚑 블로그용 부상자/결장자 명단 생성기"
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
# TAB 2: 배당률 과거 승률 분석
# =========================================================
with tab_analysis:
    st.subheader(f"📊 9대 북메이커 동일 배당 (오차 ±{tol}) 과거 승률 분석")
    analysis_rows = []
    matched_detail_dfs = {}
    
    for idx, bm in enumerate(BOOKMAKERS, 1):
        target_h, target_d, target_a = odds_inputs.get(bm, (0.0, 0.0, 0.0))
        if target_h <= 0 or target_d <= 0 or target_a <= 0:
            analysis_rows.append({
                "순번": idx, "북메이커": bm.upper(), "입력 배당": "미입력", "환급률": "-",
                "매칭 경기": "0건", "홈승 확률": "-", "무승부 확률": "-", "원정승 확률": "-"
            })
            continue

        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout = (1 / raw_inv) * 100
        df_bm = load_sheet_data(bm)
        
        match_count = 0
        h_str, d_str, a_str = "0.0%", "0.0%", "0.0%"
        
        if not df_bm.empty and "해당_홈" in df_bm.columns and "경기결과" in df_bm.columns:
            try:
                df_bm["H_num"] = pd.to_numeric(df_bm["해당_홈"], errors="coerce")
                df_bm["D_num"] = pd.to_numeric(df_bm["해당_무"], errors="coerce")
                df_bm["A_num"] = pd.to_numeric(df_bm["해당_원"], errors="coerce")
                
                cond = (
                    (df_bm["H_num"] >= target_h - tol) & (df_bm["H_num"] <= target_h + tol) &
                    (df_bm["D_num"] >= target_d - tol) & (df_bm["D_num"] <= target_d + tol) &
                    (df_bm["A_num"] >= target_a - tol) & (df_bm["A_num"] <= target_a + tol)
                )
                matched_df = df_bm[cond]
                match_count = len(matched_df)
                
                if match_count > 0:
                    matched_detail_dfs[bm.upper()] = matched_df
                    res_c = matched_df["경기결과"].value_counts()
                    hw, dr, aw = res_c.get("홈승", 0), res_c.get("무승부", 0), res_c.get("원정승", 0)
                    h_str = f"{round((hw/match_count)*100, 1)}% ({hw}회)"
                    d_str = f"{round((dr/match_count)*100, 1)}% ({dr}회)"
                    a_str = f"{round((aw/match_count)*100, 1)}% ({aw}회)"
            except Exception:
                pass
        
        analysis_rows.append({
            "순번": idx, "북메이커": bm.upper(),
            "입력 배당": f"{target_h} / {target_d} / {target_a}",
            "환급률": f"{round(payout, 2)}%",
            "매칭 경기": f"{match_count}건",
            "홈승 확률": h_str, "무승부 확률": d_str, "원정승 확률": a_str
        })

    st.dataframe(pd.DataFrame(analysis_rows), use_container_width=True, hide_index=True)
    if matched_detail_dfs:
        st.markdown("---")
        for name, m_df in matched_detail_dfs.items():
            with st.expander(f"📌 {name} 매칭 내역 ({len(m_df)}건)", expanded=False):
                st.dataframe(m_df, use_container_width=True, hide_index=True)

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
    available_teams = sorted(list(teams_set)) if teams_set else ["맨체스터시티", "리버풀", "본머스"]

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
# TAB 4: 블로그용 부상자/결장자 명단 생성기 (새로 추가)
# =========================================================
with tab_injuries:
    st.subheader("🚑 블로그 전용 선수 결장/결장의심 명단 생성기")
    st.caption("선수 데이터를 입력하면 블로그에 바로 붙여넣을 수 있는 스타일 표(분홍색 결장의심 자동 적용)가 생성됩니다.")

    # 세션 상태에 결장자 리스트 초기화 (예시 기본 데이터 탑재)
    if "injury_list" not in st.session_state:
        st.session_state.injury_list = [
            {"name_en": "Lucas Paquetá", "name_kr": "루카스 파케타", "pos": "MF", "start": 20, "sub": 3, "goals": 4, "assists": 0, "role": "주전", "reason": "부상", "note": "팀 내 득점 3위"},
            {"name_en": "Michail Antonio", "name_kr": "미카일 안토니오", "pos": "FW", "start": 11, "sub": 3, "goals": 1, "assists": 1, "role": "-", "reason": "부상", "note": "-"},
            {"name_en": "Niclas Füllkrug", "name_kr": "니클라스 퓔크루크", "pos": "FW", "start": 3, "sub": 6, "goals": 2, "assists": 1, "role": "-", "reason": "결장의심", "note": "경기 당일 테스트 예정"},
            {"name_en": "Crysencio Summerville", "name_kr": "크리센시오 서머빌", "pos": "MF", "start": 7, "sub": 12, "goals": 1, "assists": 1, "role": "-", "reason": "부상", "note": "-"},
        ]

    # 1. 헤더 설정 (팀명, 리그)
    c_th1, c_th2 = st.columns(2)
    inj_team = c_th1.text_input("대상 팀명", value="웨스트햄", key="inj_team_name")
    inj_league = c_th2.text_input("리그/대회 기준", value="잉글랜드 1부리그 기록", key="inj_league_title")

    # 2. 선수 추가 입력창
    with st.expander("➕ 선수 추가하기", expanded=True):
        f1, f2, f3 = st.columns(3)
        p_name_en = f1.text_input("선수 영문명", value="", placeholder="예: Lucas Paquetá", key="p_name_en")
        p_name_kr = f2.text_input("선수 한글명", value="", placeholder="예: 루카스 파케타", key="p_name_kr")
        p_pos = f3.selectbox("포지션", ["FW", "MF", "DF", "GK"], key="p_pos")

        f4, f5, f6, f7 = st.columns(4)
        p_start = f4.number_input("선발 출전", min_value=0, value=0, key="p_start")
        p_sub = f5.number_input("교체 출전", min_value=0, value=0, key="p_sub")
        p_goals = f6.number_input("골", min_value=0, value=0, key="p_goals")
        p_assists = f7.number_input("도움", min_value=0, value=0, key="p_assists")

        f8, f9, f10 = st.columns(3)
        p_role = f8.text_input("팀 내 역할", value="주전", placeholder="예: 주전, 로테이션, -", key="p_role")
        p_reason = f9.selectbox("결장 사유", ["부상", "결장의심", "징계/퇴장", "기타"], key="p_reason")
        p_note = f10.text_input("특이사항", value="-", placeholder="예: 햄스트링 부상, 팀 내 최다 득점", key="p_note")

        c_btn1, c_btn2 = st.columns([1, 4])
        if c_btn1.button("➕ 선수 목록에 추가", type="primary", use_container_width=True):
            if p_name_en.strip() or p_name_kr.strip():
                st.session_state.injury_list.append({
                    "name_en": p_name_en.strip(),
                    "name_kr": p_name_kr.strip(),
                    "pos": p_pos,
                    "start": p_start,
                    "sub": p_sub,
                    "goals": p_goals,
                    "assists": p_assists,
                    "role": p_role if p_role.strip() else "-",
                    "reason": p_reason,
                    "note": p_note if p_note.strip() else "-"
                })
                st.success(f"{p_name_kr or p_name_en} 선수가 추가되었습니다.")
                st.rerun()

        if c_btn2.button("🗑️ 목록 전체 비우기"):
            st.session_state.injury_list = []
            st.rerun()

    # 3. 현재 등록된 선수 목록 테이블
    if st.session_state.injury_list:
        st.markdown(f"### 📋 등록된 결장자 목록 ({len(st.session_state.injury_list)}명)")
        
        # 목록 미리보기 표
        view_data = []
        for idx, item in enumerate(st.session_state.injury_list):
            name_full = f"{item['name_en']}\n({item['name_kr']})" if item['name_kr'] else item['name_en']
            view_data.append({
                "번호": idx + 1,
                "선수명": name_full,
                "포지션": item["pos"],
                "선발": item["start"],
                "교체": item["sub"],
                "골": item["goals"],
                "도움": item["assists"],
                "역할": item["role"],
                "사유": item["reason"],
                "특이사항": item["note"]
            })
        st.dataframe(pd.DataFrame(view_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📰 블로그용 서식 결과 (드래그하여 블로그에 그대로 붙여넣기)")
        
        # HTML 표 생성 (분홍색 강조 적용)
        html_rows = ""
        for item in st.session_state.injury_list:
            is_doubt = (item["reason"] == "결장의심")
            # 결장의심이면 분홍색 배경 적용
            bg_style = 'style="background-color: #ffebee; color: #c2185b; font-weight: bold;"' if is_doubt else ""
            
            name_display = f"<b>{item['name_en']}</b>" if item['name_en'] else ""
            if item['name_kr']:
                name_display += f"<br>({item['name_kr']})"
                
            html_rows += f"""
            <tr {bg_style}>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{name_display}</td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{item['pos']}</td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{item['start']}</td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{item['sub']}</td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{item['goals']}</td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{item['assists']}</td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{item['role']}</td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;"><b>{item['reason']}</b></td>
                <td style="padding: 8px 10px; border: 1px solid #ddd; text-align: center;">{item['note']}</td>
            </tr>
            """

        blog_html = f"""
        <div style="font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto;">
            <div style="border-left: 4px solid #0066cc; padding-left: 10px; margin-bottom: 12px;">
                <h3 style="margin: 0; font-size: 18px; color: #111;">{inj_team} 선수 예상결장명단</h3>
                <p style="margin: 4px 0 0 0; font-size: 12px; color: #e91e63; font-weight: bold;">* 분홍색: 결장의심 (출전 불투명) *</p>
                <p style="margin: 2px 0 0 0; font-size: 12px; color: #666;">기준: {inj_league}</p>
            </div>
            <table style="border-collapse: collapse; width: 100%; font-size: 13px; text-align: center; border: 1px solid #ddd;">
                <thead>
                    <tr style="background-color: #f7f9fa; color: #333; font-weight: bold; border-bottom: 2px solid #ccc;">
                        <th style="padding: 10px; border: 1px solid #ddd;">이름</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">포지션</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">선발</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">교체</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">골</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">도움</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">역할</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">사유</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">특이사항</th>
                    </tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
        </div>
        """
        st.markdown(blog_html, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("📋 마크다운(Markdown) 텍스트 복사창")
        
        md_rows = ""
        for item in st.session_state.injury_list:
            name_str = f"{item['name_en']} ({item['name_kr']})" if item['name_kr'] else item['name_en']
            reason_str = f"**{item['reason']}** (의심)" if item['reason'] == "결장의심" else item['reason']
            md_rows += f"| {name_str} | {item['pos']} | {item['start']} | {item['sub']} | {item['goals']} | {item['assists']} | {item['role']} | {reason_str} | {item['note']} |\n"

        md_output = f"""### {inj_team} 선수 예상결장명단
*💡 분홍색/강조: 결장의심*
*{inj_league}*

| 이름 | 포지션 | 선발 | 교체 | 골 | 도움 | 역할 | 사유 | 특이사항 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
{md_rows}
"""
        st.text_area("📋 블로그/마크다운 전용 텍스트 복사", value=md_output, height=250)
