import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="Football 9-Bookmakers & Analysis Hub",
    page_icon="⚽",
    layout="wide"
)

BOOKMAKERS = [
    "bwin", "10x10", "1xbet", "betway", 
    "william hill", "bet365", "pinnacle", "stake", "배트맨"
]
STATS_SHEET_NAME = "경기내용"
SPREADSHEET_ID = "1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ"

st.title("⚽ 축구 9대 배당 업체 & 통합 데이터 분석 시스템")

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
tab_input, tab_analysis, tab_team_stats, tab_report = st.tabs([
    "📝 데이터 입력 및 저장", 
    "📊 9개사 동일 배당 승률 분석", 
    "📈 팀별 세부내용 평균계산기",
    "📋 원클릭 분석 리포트 (표 형식)"
])

# =========================================================
# TAB 1: 데이터 입력 및 저장
# =========================================================
with tab_input:
    st.subheader("1️⃣ 경기 기본 정보 & 팀명")
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

    sel_season = c_f1.selectbox("시즌", available_seasons if available_seasons else ["전체"])
    sel_league = c_f2.selectbox("경기구분 (리그)", available_leagues if available_leagues else ["전체"])
    sel_team = c_f3.selectbox("경기목록 (팀이름)", available_teams if available_teams else ["팀 선택"])

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
# TAB 4: 원클릭 분석 리포트 생성기 (표 형식 100% 구현)
# =========================================================
with tab_report:
    st.subheader("📋 Boro 축구 경기 분석 리포트 (표 형식 원클릭 생성)")
    st.caption("편집 저작물 - 저작권등록 제 C-2016-010109호")

    # 1. 기본 정보 및 상대 전적
    with st.expander("1️⃣ 기본 정보 & 상대전적 / 최근 10경기 입력", expanded=True):
        r1, r2, r3 = st.columns(3)
        rep_home = r1.text_input("홈팀", value="리버풀")
        rep_away = r2.text_input("원정팀", value="본머스")
        rep_author = r3.text_input("작성자", value="Boro")

        st.markdown("##### 📊 상대전적 (최근 5시즌)")
        c1, c2, c3, c4 = st.columns(4)
        h2h_all_m = c1.text_input("전체 상대전적 (전)", value="10전")
        h2h_all_w = c2.text_input("전체 승", value="8승")
        h2h_all_d = c3.text_input("전체 무", value="1무")
        h2h_all_l = c4.text_input("전체 패", value="1패")

        c5, c6, c7, c8 = st.columns(4)
        h2h_home_m = c5.text_input("홈 기준 상대전적 (전)", value="5전")
        h2h_home_w = c6.text_input("홈 기준 승", value="5승")
        h2h_home_d = c7.text_input("홈 기준 무", value="0무")
        h2h_home_l = c8.text_input("홈 기준 패", value="0패")

        st.markdown("##### ⚽ 상대전적 평균 득실점")
        g1, g2, g3, g4 = st.columns(4)
        h2h_h_gf = g1.text_input("홈경기 평균 득점", value="3.2")
        h2h_h_ga = g2.text_input("홈경기 평균 실점", value="0.6")
        h2h_a_gf = g3.text_input("원정경기 평균 득점", value="2.0")
        h2h_a_ga = g4.text_input("원정경기 평균 실점", value="1.0")

        h2h_note = st.text_input("상대전적 특이사항", value="리버풀 홈 맞대결 5연승 중, 압도적 우세")

        st.markdown("##### 📈 최근 10경기 승패 및 평균 득실점")
        t1, t2, t3, t4 = st.columns(4)
        ten_h_m = t1.text_input("홈팀 최근 10경기", value="10전 7승 2무 1패")
        ten_a_m = t2.text_input("원정팀 최근 10경기", value="10전 4승 2무 4패")
        ten_h_g = t3.text_input("홈팀 최근10경기 득/실", value="2.4득 / 0.9실")
        ten_a_g = t4.text_input("원정팀 최근10경기 득/실", value="1.2득 / 1.5실")
        ten_note = st.text_input("최근 10경기 특이사항", value="리버풀 최근 홈 4연승 무패 행진")

    # 2. 팀별 세부 스탯
    with st.expander("2️⃣ 홈/원정팀 최근 경기 세부 스탯 분석 (전술/지표)"):
        st.markdown(f"##### 🔵 [{rep_home}] 세부 분석")
        st_h1, st_h2 = st.columns(2)
        h_tac_rank = st_h1.text_input("홈팀 전술 순위", value="1순위 4-2-3-1 (75%), 2순위 4-3-3 (25%)")
        h_tac_home = st_h2.text_input("홈경기 주력 전술", value="4-2-3-1 (80%)")
        
        st_h3, st_h4, st_h5 = st.columns(3)
        h_goal_r = st_h3.text_input("홈 득점비율 (시즌전/후, 홈전/후)", value="전25% 후75% / 전30% 후70%")
        h_poss_s = st_h4.text_input("홈 점유율 (홈/원정/시즌)", value="61% / 55% / 58%")
        h_xg_s = st_h5.text_input("홈 xG (홈/원정/시즌)", value="2.21 / 1.80 / 2.01")
        
        st_h6, st_h7, st_h8 = st.columns(3)
        h_sot_r = st_h6.text_input("홈 유효슈팅비율 (홈/원정/시즌)", value="52.6% / 45.0% / 48.8%")
        h_pass_s = st_h7.text_input("홈 패스성공률 (홈/원정/시즌)", value="82% / 78% / 80%")
        h_card_s = st_h8.text_input("홈 경고/퇴장 (장)", value="1.2장 / 0.0장")
        h_spec = st_text_h = st.text_input("홈팀 특이사항", value="후반전 득점 집중력이 매우 높음")

        st.markdown(f"##### 🔴 [{rep_away}] 세부 분석")
        st_a1, st_a2 = st.columns(2)
        a_tac_rank = st_a1.text_input("원정팀 전술 순위", value="1순위 4-1-4-1 (70%), 2순위 5-4-1 (30%)")
        a_tac_away = st_a2.text_input("원정경기 주력 전술", value="4-1-4-1 (75%)")
        
        st_a3, st_a4, st_a5 = st.columns(3)
        a_goal_r = st_a3.text_input("원정 득점비율 (시즌전/후, 원정전/후)", value="전30% 후70% / 전20% 후80%")
        a_poss_s = st_a4.text_input("원정 점유율 (홈/원정/시즌)", value="48% / 39% / 43.5%")
        a_xg_s = st_a5.text_input("원정 xG (홈/원정/시즌)", value="1.50 / 1.10 / 1.30")
        
        st_a6, st_a7, st_a8 = st.columns(3)
        a_sot_r = st_a6.text_input("원정 유효슈팅비율 (홈/원정/시즌)", value="38.0% / 30.0% / 34.0%")
        a_pass_s = st_a7.text_input("원정 패스성공률 (홈/원정/시즌)", value="76% / 70% / 73%")
        a_card_s = st_a8.text_input("원정 경고/퇴장 (장)", value="2.1장 / 0.1장")
        a_spec = st.text_input("원정팀 특이사항", value="원정 경기 시 점유율 및 유효슈팅 급감")

    # 3. 배당/투표율/최종 픽
    with st.expander("3️⃣ 배당 절삭 / 배당조정 / 구매투표율 / 최종 픽"):
        st.markdown("##### 📉 배당 절삭률 & 배당조정")
        bc1, bc2, bc3 = st.columns(3)
        cut_h = bc1.text_input("홈승 절삭률", value="-29.03%")
        cut_d = bc2.text_input("무승부 절삭률", value="-13.68%")
        cut_a = bc3.text_input("원정승 절삭률", value="-7.14%")

        adj1, adj2, adj3 = st.columns(3)
        adj_gen = adj1.text_input("일반 (국내조정 / 해외조정)", value="하락 2회 / 하락 4회")
        adj_hnd = adj2.text_input("핸디캡 (국내조정 / 해외조정)", value="변동 없음 / 하락 1회")
        adj_uno = adj3.text_input("언오버 (국내조정 / 해외조정)", value="오버 하락 3회 / 오버 하락 3회")

        st.markdown("##### 🗳️ 구매투표율 (배트맨 기준)")
        vp1, vp2, vp3 = st.columns(3)
        vote_gen = vp1.text_input("일반 투표율 (홈/무/원)", value="78.5% / 13.2% / 8.3%")
        vote_hnd = vp2.text_input("핸디캡 투표율 (승/무/패)", value="58.0% / 22.0% / 20.0%")
        vote_uno = vp3.text_input("언오버 투표율 (언더/오버)", value="28.0% / 72.0%")

        st.markdown("##### 🎯 최종 픽 & 적중확률")
        p1, p2, p3 = st.columns(3)
        main_pk = p1.text_input("주력픽 / 적중확률 / 배당", value="리버풀 승 | 80% | 1.22")
        sub_pk = p2.text_input("부주력 / 적중확률 / 배당", value="리버풀 -1.0 핸승 | 65% | 1.65")
        uno_pk = p3.text_input("언오버픽 / 적중확률 / 배당", value="3.5 오버 | 60% | 1.85")
        extra_note = st.text_area("결장자 / 동기부여 / 최종 코멘트", value="리버풀은 홈 개막전 전력 풀가동 상태이며, 본머스는 중원 주전 미드필더 결장으로 전력 누수가 큽니다.")

    st.markdown("---")

    if st.button("🚀 정밀 표(Table) 형식 리포트 생성", type="primary", use_container_width=True):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 1. 웹 화면용 HTML 표 리포트
        html_report = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #222;">
            <div style="border-bottom: 2px solid #333; padding-bottom: 8px; margin-bottom: 15px;">
                <p style="margin: 0; font-size: 12px; color: #666;">편집 저작물 - 저작권등록 제 C-2016-010109호</p>
                <h3 style="margin: 5px 0;">⚽ [축구 분석 리포트] {rep_home} vs {rep_away}</h3>
                <p style="margin: 0; font-size: 13px;"><b>작성자:</b> {rep_author} &nbsp;|&nbsp; <b>작성시간:</b> {now_str}</p>
            </div>

            <h4>1. 상대전적 및 득실점 요약</h4>
            <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 13px; margin-bottom: 10px;">
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td>구분</td><td>경기수</td><td>승</td><td>무</td><td>패</td><td>홈경기 평균득실점</td><td>원정경기 평균득실점</td>
                </tr>
                <tr>
                    <td>최근5시즌 상대전적</td><td>{h2h_all_m}</td><td>{h2h_all_w}</td><td>{h2h_all_d}</td><td>{h2h_all_l}</td>
                    <td rowspan="2">{h2h_h_gf}득 / {h2h_h_ga}실</td><td rowspan="2">{h2h_a_gf}득 / {h2h_a_ga}실</td>
                </tr>
                <tr>
                    <td>홈팀기준 상대전적</td><td>{h2h_home_m}</td><td>{h2h_home_w}</td><td>{h2h_home_d}</td><td>{h2h_home_l}</td>
                </tr>
            </table>
            <p style="font-size: 12px; margin-top: -5px;"><b>* 특이사항:</b> {h2h_note}</p>

            <h4>2. 최근 10경기 승패 및 평균 득실점</h4>
            <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 13px; margin-bottom: 10px;">
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td>구분</td><td>최근 10경기 승패</td><td>평균 득실점</td>
                </tr>
                <tr><td>{rep_home} (홈)</td><td>{ten_h_m}</td><td>{ten_h_g}</td></tr>
                <tr><td>{rep_away} (원정)</td><td>{ten_a_m}</td><td>{ten_a_g}</td></tr>
            </table>
            <p style="font-size: 12px; margin-top: -5px;"><b>* 특이사항:</b> {ten_note}</p>

            <h4>3. 팀별 세부 경기내용 비교</h4>
            <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 13px; margin-bottom: 10px;">
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td>세부 항목</td><td>{rep_home} (홈팀)</td><td>{rep_away} (원정팀)</td>
                </tr>
                <tr><td>전술 (포메이션)</td><td>{h_tac_rank} / {h_tac_home}</td><td>{a_tac_rank} / {a_tac_away}</td></tr>
                <tr><td>전/후반 득점비율</td><td>{h_goal_r}</td><td>{a_goal_r}</td></tr>
                <tr><td>점유율 (홈/원정/시즌)</td><td>{h_poss_s}</td><td>{a_poss_s}</td></tr>
                <tr><td>xG 기대득점</td><td>{h_xg_s}</td><td>{a_xg_s}</td></tr>
                <tr><td>유효슈팅 비율</td><td>{h_sot_r}</td><td>{a_sot_r}</td></tr>
                <tr><td>패스성공률</td><td>{h_pass_s}</td><td>{a_pass_s}</td></tr>
                <tr><td>경고 / 퇴장</td><td>{h_card_s}</td><td>{a_card_s}</td></tr>
                <tr><td>특이사항</td><td>{h_spec}</td><td>{a_spec}</td></tr>
            </table>

            <h4>4. 배당 절삭 / 배당조정 / 구매투표율</h4>
            <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 13px; margin-bottom: 10px;">
                <tr style="background-color: #f2f2f2; font-weight: bold;">
                    <td>구분</td><td>홈승</td><td>무승부</td><td>원정승</td><td>핸디캡 / 언오버</td>
                </tr>
                <tr>
                    <td>배당 절삭률</td><td>{cut_h}</td><td>{cut_d}</td><td>{cut_a}</td><td>-</td>
                </tr>
                <tr>
                    <td>배당 조정횟수</td><td colspan="3">{adj_gen}</td><td>핸디({adj_hnd}) / 언오버({adj_uno})</td>
                </tr>
                <tr>
                    <td>구매 투표율</td><td colspan="3">{vote_gen}</td><td>핸디({vote_hnd}) / 언오버({vote_uno})</td>
                </tr>
            </table>

            <h4>5. 최종 픽 & 적중확률</h4>
            <table border="1" style="border-collapse: collapse; width: 100%; text-align: center; font-size: 13px; margin-bottom: 15px;">
                <tr style="background-color: #e6f2ff; font-weight: bold;">
                    <td>구분</td><td>추천 선택지</td><td>적중확률 / 배당</td>
                </tr>
                <tr><td><b>★ 주력픽</b></td><td colspan="2"><b>{main_pk}</b></td></tr>
                <tr><td><b>☆ 부주력</b></td><td colspan="2">{sub_pk}</td></tr>
                <tr><td><b>⚡ 언오버</b></td><td colspan="2">{uno_pk}</td></tr>
            </table>

            <p style="font-size: 12px; color: #444; background-color: #f9f9f9; padding: 8px; border-left: 3px solid #0066cc;">
                <b>* 종합 코멘트:</b> {extra_note}<br>
                <i>* 본 분석은 작성시간 기준이며 차후 변동사항에 따라 분석픽이 달라질 수 있습니다. 무단 도용 시 법적 조치를 받을 수 있습니다.</i>
            </p>
        </div>
        """
        
        st.markdown(html_report, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("📋 블로그/마크다운 전용 복사 텍스트 (표 완벽 지원)")
        
        # 2. 마크다운 표 전용 텍스트
        md_table_text = f"""편집 저작물 - 저작권등록 제 C-2016-010109호
작성자 : {rep_author} | 작성시간 : {now_str}

### ⚽ [축구 분석 리포트] {rep_home} vs {rep_away}

#### 1. 상대전적 및 득실점 요약
| 구분 | 경기수 | 승 | 무 | 패 | 홈경기 평균득실 | 원정경기 평균득실 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **최근5시즌 상대전적** | {h2h_all_m} | {h2h_all_w} | {h2h_all_d} | {h2h_all_l} | {h2h_h_gf}득 / {h2h_h_ga}실 | {h2h_a_gf}득 / {h2h_a_ga}실 |
| **홈팀기준 상대전적** | {h2h_home_m} | {h2h_home_w} | {h2h_home_d} | {h2h_home_l} | - | - |

* 특이사항: {h2h_note}

#### 2. 최근 10경기 승패 및 평균 득실점
| 구분 | 최근 10경기 승패 | 평균 득실점 |
| :--- | :---: | :---: |
| **{rep_home} (홈)** | {ten_h_m} | {ten_h_g} |
| **{rep_away} (원정)** | {ten_a_m} | {ten_a_g} |

* 특이사항: {ten_note}

#### 3. 팀별 세부 경기내용 비교
| 세부 항목 | {rep_home} (홈팀) | {rep_away} (원정팀) |
| :--- | :---: | :---: |
| **전술 (포메이션)** | {h_tac_rank} / {h_tac_home} | {a_tac_rank} / {a_tac_away} |
| **전/후반 득점비율** | {h_goal_r} | {a_goal_r} |
| **점유율 (홈/원정/시즌)** | {h_poss_s} | {a_poss_s} |
| **xG 기대득점** | {h_xg_s} | {a_xg_s} |
| **유효슈팅 비율** | {h_sot_r} | {a_sot_r} |
| **패스성공률** | {h_pass_s} | {a_pass_s} |
| **경고 / 퇴장** | {h_card_s} | {a_card_s} |
| **특이사항** | {h_spec} | {a_spec} |

#### 4. 배당 절삭 / 배당조정 / 구매투표율
| 구분 | 홈승 | 무승부 | 원정승 | 핸디캡 / 언오버 |
| :--- | :---: | :---: | :---: | :---: |
| **배당 절삭률** | {cut_h} | {cut_d} | {cut_a} | - |
| **배당 조정횟수** | {adj_gen} | - | - | 핸디({adj_hnd}) / 언오버({adj_uno}) |
| **구매 투표율** | {vote_gen} | - | - | 핸디({vote_hnd}) / 언오버({vote_uno}) |

#### 5. 최종 픽 & 적중확률
| 구분 | 추천 선택지 및 배당 / 적중확률 |
| :--- | :--- |
| **★ 주력픽** | **{main_pk}** |
| **☆ 부주력** | {sub_pk} |
| **⚡ 언오버** | {uno_pk} |

* **종합 코멘트**: {extra_note}
* *분석은 작성시간 기준이며 차후 변동사항에 따라 분석픽이 달라질 수 있습니다. 무단 도용 시 법적 조치를 받을 수 있습니다.*
"""
        st.text_area("📋 마크다운 표 복사창", value=md_table_text, height=450)
