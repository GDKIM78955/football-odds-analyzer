import streamlit as st
import pandas as pd
from database import load_sheet_data
from infographics import generate_naver_team_stats_infographic, render_clipboard_component

def render_tab4(spreadsheet_id):
    st.subheader("📈 팀별 과거 세부 경기내용 평균계산기 (단일 팀 기준)")
    
    stats_sheet_name = "경기내용"
    
    # [최적화] 시트 데이터를 안전하게 로드 (실패 시 빈 데이터프레임)
    df_stats_all = pd.DataFrame()
    try:
        df_stats_all = load_sheet_data(stats_sheet_name, spreadsheet_id)
    except Exception:
        pass
    
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

    # =========================================================
    # 🚀 [최적화] 분석 실행 버튼 도입 (무한 로딩 및 멈춤 방지)
    # =========================================================
    st.markdown("### 🚀 팀 세부 지표 분석 실행")
    st.info("💡 조건을 선택한 후 아래 버튼을 누르면 해당 팀의 세부 지표와 인포그래픽이 생성됩니다.")

    if st.button("🔥 팀 지표 분석 시작하기", type="primary", use_container_width=True):
        if df_stats_all.empty:
            st.warning("💡 '경기내용' 시트에 데이터가 없거나 불러오지 못했습니다.")
            st.session_state["t4_analyzed"] = False
        else:
            with st.spinner(f"[{sel_team}]의 과거 경기 데이터를 분석 중입니다..."):
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

                if total_cnt == 0:
                    st.warning(f"💡 선택한 조건(시즌: {sel_season}, 리그: {sel_league})에 [{sel_team}]의 경기 기록이 없습니다.")
                    st.session_state["t4_analyzed"] = False
                else:
                    h_1h_goals = to_num(df_home_matches["전반득점_홈"]).sum() if h_cnt > 0 and "전반득점_홈" in df_home_matches.columns else 0
                    h_2h_goals = to_num(df_home_matches["후반득점_홈"]).sum() if h_cnt > 0 and "후반득점_홈" in df_home_matches.columns else 0
                    h_tot_goals = h_1h_goals + h_2h_goals

                    a_1h_goals = to_num(df_away_matches["전반득점_원"]).sum() if a_cnt > 0 and "전반득점_원" in df_away_matches.columns else 0
                    a_2h_goals = to_num(df_away_matches["후반득점_원"]).sum() if a_cnt > 0 and "후반득점_원" in df_away_matches.columns else 0
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

                    stat_summary_data = {
                        "구분": ["점유율 (%)", "유효슈팅 (회)", "패스성공률 (%)", "경고 (회)", "퇴장 (회)", "xG (기대득점)", "유효슈팅비율 (%)"],
                        "홈 (Home)": [f"{poss_h}%", f"{sot_h}", f"{pass_h}%", f"{yc_h}", f"{rc_h}", f"{xg_h}", f"{ratio_h}%"],
                        "원정 (Away)": [f"{poss_a}%", f"{sot_a}", f"{pass_a}%", f"{yc_a}", f"{rc_a}", f"{xg_a}", f"{ratio_a}%"],
                        "시즌 전체 평균": [f"{poss_tot}%", f"{sot_tot}", f"{pass_tot}%", f"{yc_tot}", f"{rc_tot}", f"{xg_tot}", f"{ratio_tot}%"]
                    }
                    df_summary = pd.DataFrame(stat_summary_data)

                    # 전술 분석
                    home_tacs = df_home_matches["전술_홈"].dropna().astype(str).str.strip().tolist() if "전술_홈" in df_home_matches.columns else []
                    away_tacs = df_away_matches["전술_원"].dropna().astype(str).str.strip().tolist() if "전술_원" in df_away_matches.columns else []
                    all_tacs = home_tacs + away_tacs
                    unique_tacs = sorted(list(set([t for t in all_tacs if t and t != "-"])))
                    
                    tac_rows = []
                    if unique_tacs and total_cnt > 0:
                        for t in unique_tacs:
                            h_c = home_tacs.count(t)
                            a_c = away_tacs.count(t)
                            tot_c = h_c + a_c
                            ratio = round((tot_c / total_cnt) * 100, 1)
                            tac_rows.append({
                                "전술 (포메이션)": t,
                                "전체 사용 횟수": f"{tot_c}회 ({ratio}%)",
                                "홈경기 사용": f"{h_c}회",
                                "원정경기 사용": f"{a_c}회"
                            })
                    tac_df = pd.DataFrame(tac_rows).sort_values(by="전체 사용 횟수", ascending=False) if tac_rows else pd.DataFrame()

                    # 득점 통계
                    goal_table_data = {
                        "구분": ["홈 (평균)", "원정 (평균)", "시즌 전체 평균"],
                        "전반 총득점": [int(h_1h_goals), int(a_1h_goals), "-"],
                        "후반 총득점": [int(h_2h_goals), int(a_2h_goals), "-"],
                        "총점": [int(h_tot_goals), int(a_tot_goals), "-"],
                        "전반 평균": [h_1h_avg, a_1h_avg, tot_1h_avg],
                        "후반 평균": [h_2h_avg, a_2h_avg, tot_2h_avg],
                        "합계 평균": [h_tot_avg, a_tot_avg, tot_all_avg]
                    }
                    df_goals = pd.DataFrame(goal_table_data)

                    # 세션에 저장
                    st.session_state["t4_analyzed"] = True
                    st.session_state["t4_total_cnt"] = total_cnt
                    st.session_state["t4_h_cnt"] = h_cnt
                    st.session_state["t4_a_cnt"] = a_cnt
                    st.session_state["t4_df_summary"] = df_summary
                    st.session_state["t4_tac_df"] = tac_df
                    st.session_state["t4_df_goals"] = df_goals

    # 분석 완료된 경우에만 결과 출력
    if st.session_state.get("t4_analyzed", False):
        total_cnt = st.session_state["t4_total_cnt"]
        h_cnt = st.session_state["t4_h_cnt"]
        a_cnt = st.session_state["t4_a_cnt"]
        df_summary = st.session_state["t4_df_summary"]
        tac_df = st.session_state["t4_tac_df"]
        df_goals = st.session_state["t4_df_goals"]

        st.markdown(f"### 📋 [{sel_team}] 시즌 평균 지표 종합 요약 (총 {total_cnt}경기: 홈 {h_cnt}경기 / 원정 {a_cnt}경기)")
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ♟️ 팀 전술(포메이션) 사용 횟수 및 비율")
        if not tac_df.empty:
            st.dataframe(tac_df, use_container_width=True, hide_index=True)
        else:
            st.info("💡 등록된 전술 데이터가 없습니다.")

        st.markdown("---")
        st.markdown("### ⚽ 전/후반 득점 통계표")
        st.dataframe(df_goals, use_container_width=True, hide_index=True)
        
        with st.expander("📊 / 📋 네이버 블로그/카페용 팀 지표 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
            st.markdown(f"##### 🌟 [네이버 블로그/카페 전용] [{sel_team}] 시즌 지표 인포그래픽 카드")
            st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

            match_info_str = f"총 {total_cnt}경기: 홈 {h_cnt} / 원정 {a_cnt}"
            naver_team_html = generate_naver_team_stats_infographic(
                sel_team, sel_season, sel_league, match_info_str, 
                df_summary, tac_df, df_goals
            )

            render_clipboard_component(naver_team_html, "t3_clip", height=620)
