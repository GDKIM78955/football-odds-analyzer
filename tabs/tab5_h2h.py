import streamlit as st
import pandas as pd
import numpy as np
from database import load_sheet_data
from infographics import generate_naver_match_infographic, render_clipboard_component

def render_tab5(spreadsheet_id):
    st.subheader("⚔️ 홈팀 vs 원정팀 역대 맞대결(H2H) 종합 분석 및 세부 지표")
    st.caption("두 팀을 선택하면 역대 맞대결 경기들의 평균 지표, 사용된 전술 횟수, 전/후반 득점 및 비율(%) 통계가 출력됩니다.")

    stats_sheet_name = "경기내용"
    df_stats_h2h = load_sheet_data(stats_sheet_name, spreadsheet_id)

    teams_set_h2h = set()
    if not df_stats_h2h.empty:
        if "홈팀" in df_stats_h2h.columns:
            teams_set_h2h.update(df_stats_h2h["홈팀"].dropna().unique())
        if "원정팀" in df_stats_h2h.columns:
            teams_set_h2h.update(df_stats_h2h["원정팀"].dropna().unique())
    available_h2h_teams = sorted(list(teams_set_h2h)) if teams_set_h2h else ["리버풀", "본머스", "웨스트햄", "맨체스터시티"]

    default_h_idx = 0
    default_a_idx = 1 if len(available_h2h_teams) > 1 else 0

    if "selected_scan_match" in st.session_state and st.session_state.selected_scan_match:
        sm = st.session_state.selected_scan_match
        if sm["home"] in available_h2h_teams:
            default_h_idx = available_h2h_teams.index(sm["home"])
        if sm["away"] in available_h2h_teams:
            default_a_idx = available_h2h_teams.index(sm["away"])

    c_h2h_1, c_h2h_2 = st.columns(2)
    sel_home_h2h = c_h2h_1.selectbox("🏠 홈팀 선택", available_h2h_teams, index=default_h_idx, key="sel_h2h_home")
    sel_away_h2h = c_h2h_2.selectbox("🚗 원정팀 선택", available_h2h_teams, index=default_a_idx, key="sel_h2h_away")

    st.markdown("---")

    df_h2h_summary = pd.DataFrame()
    df_h_tac = pd.DataFrame()
    df_a_tac = pd.DataFrame()
    df_h2h_goals = pd.DataFrame()

    if not df_stats_h2h.empty and "홈팀" in df_stats_h2h.columns and "원정팀" in df_stats_h2h.columns:
        def to_num(series):
            return pd.to_numeric(series.astype(str).str.replace("%", "").str.strip(), errors="coerce").fillna(0)

        cond_exact = (df_stats_h2h["홈팀"] == sel_home_h2h) & (df_stats_h2h["원정팀"] == sel_away_h2h)
        cond_all = ((df_stats_h2h["홈팀"] == sel_home_h2h) & (df_stats_h2h["원정팀"] == sel_away_h2h)) | \
                   ((df_stats_h2h["홈팀"] == sel_away_h2h) & (df_stats_h2h["원정팀"] == sel_home_h2h))

        df_h2h_exact = df_stats_h2h[cond_exact].copy()
        df_h2h_all = df_stats_h2h[cond_all].copy()

        total_h2h_count = len(df_h2h_all)
        exact_h2h_count = len(df_h2h_exact)

        if total_h2h_count > 0:
            st.markdown(f"### 📋 [{sel_home_h2h}] vs [{sel_away_h2h}] 역대 맞대결 기록 (총 {total_h2h_count}경기 / 홈원정 동일 매치업 {exact_h2h_count}경기)")

            h_wins, draws, a_wins = 0, 0, 0
            for _, r in df_h2h_all.iterrows():
                h_g = to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_홈", 0)])).iloc[0]
                ag = to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0]
                
                if r["홈팀"] == sel_home_h2h:
                    if h_g > ag: h_wins += 1
                    elif h_g == ag: draws += 1
                    else: a_wins += 1
                else:
                    if ag > h_g: h_wins += 1
                    elif ag == h_g: draws += 1
                    else: a_wins += 1

            ex_h_wins, ex_draws, ex_a_wins = 0, 0, 0
            for _, r in df_h2h_exact.iterrows():
                h_g = to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_홈", 0)])).iloc[0]
                ag = to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0]
                if h_g > ag: ex_h_wins += 1
                elif h_g == ag: ex_draws += 1
                else: ex_a_wins += 1

            h2h_all_text = f"{sel_home_h2h} 기준 {total_h2h_count}전 {h_wins}승 {draws}무 {a_wins}패 (승률: {round((h_wins/total_h2h_count)*100, 1)}%)"
            
            if exact_h2h_count > 0:
                h2h_exact_text = f"{sel_home_h2h}(홈) 기준 {exact_h2h_count}전 {ex_h_wins}승 {ex_draws}무 {ex_a_wins}패 (승률: {round((ex_h_wins/exact_h2h_count)*100, 1)}%)"
            else:
                h2h_exact_text = f"동일 매치업 과거 경기 기록 없음 (0전 0승 0무 0패)"

            st.info(f"🏆 **역대 전체 상대전적:** {h2h_all_text}\n\n🏠 **홈/원정 동일 조건 상대전적:** {h2h_exact_text}")

            def get_h2h_stat_avg(col_h, col_a):
                home_team_vals, away_team_vals = [], []
                for _, r in df_h2h_all.iterrows():
                    if r["홈팀"] == sel_home_h2h:
                        if col_h in r: home_team_vals.append(to_num(pd.Series([r[col_h]])).iloc[0])
                        if col_a in r: away_team_vals.append(to_num(pd.Series([r[col_a]])).iloc[0])
                    else:
                        if col_a in r: home_team_vals.append(to_num(pd.Series([r[col_a]])).iloc[0])
                        if col_h in r: away_team_vals.append(to_num(pd.Series([r[col_h]])).iloc[0])
                avg_home = round(np.mean(home_team_vals), 2) if home_team_vals else 0.0
                avg_away = round(np.mean(away_team_vals), 2) if away_team_vals else 0.0
                return avg_home, avg_away

            poss_h, poss_a = get_h2h_stat_avg("점유율_홈", "점유율_원")
            sot_h, sot_a = get_h2h_stat_avg("유효슈팅_홈", "유효슈팅_원")
            pass_h, pass_a = get_h2h_stat_avg("패스성공률_홈", "패스성공률_원")
            yc_h, yc_a = get_h2h_stat_avg("경고_홈", "경고_원")
            rc_h, rc_a = get_h2h_stat_avg("퇴장_홈", "퇴장_원")
            xg_h, xg_a = get_h2h_stat_avg("xG_홈", "xG_원")
            ratio_h, ratio_a = get_h2h_stat_avg("유효슈팅비율_홈", "유효슈팅비율_원")

            h2h_summary_table = {
                "구분": ["점유율 (%)", "유효슈팅 (회)", "패스성공률 (%)", "경고 (회)", "퇴장 (회)", "xG (기대득점)", "유효슈팅비율 (%)"],
                f"{sel_home_h2h} (맞대결 평균)": [f"{poss_h}%", f"{sot_h}", f"{pass_h}%", f"{yc_h}", f"{rc_h}", f"{xg_h}", f"{ratio_h}%"],
                f"{sel_away_h2h} (맞대결 평균)": [f"{poss_a}%", f"{sot_a}", f"{pass_a}%", f"{yc_a}", f"{rc_a}", f"{xg_a}", f"{ratio_a}%"]
            }
            df_h2h_summary = pd.DataFrame(h2h_summary_table)
            st.dataframe(df_h2h_summary, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### ♟️ 맞대결 시 양 팀의 전술(포메이션) 사용 횟수")

            home_team_tacs, away_team_tacs = [], []
            for _, r in df_h2h_all.iterrows():
                if r["홈팀"] == sel_home_h2h:
                    if "전술_홈" in r and r["전술_홈"]: home_team_tacs.append(str(r["전술_홈"]).strip())
                    if "전술_원" in r and r["전술_원"]: away_team_tacs.append(str(r["전술_원"]).strip())
                else:
                    if "전술_원" in r and r["전술_원"]: home_team_tacs.append(str(r["전술_원"]).strip())
                    if "전술_홈" in r and r["전술_홈"]: away_team_tacs.append(str(r["전술_홈"]).strip())

            c_tc1, c_tc2 = st.columns(2)
            with c_tc1:
                st.markdown(f"**🔵 [{sel_home_h2h}] 맞대결 전술 빈도**")
                h_tac_vc = pd.Series(home_team_tacs).value_counts()
                if not h_tac_vc.empty:
                    df_h_tac = pd.DataFrame({"전술": h_tac_vc.index, "사용 횟수": [f"{c}회 ({round((c/total_h2h_count)*100, 1)}%)" for c in h_tac_vc.values]})
                    st.dataframe(df_h_tac, use_container_width=True, hide_index=True)

            with c_tc2:
                st.markdown(f"**🔴 [{sel_away_h2h}] 맞대결 전술 빈도**")
                a_tac_vc = pd.Series(away_team_tacs).value_counts()
                if not a_tac_vc.empty:
                    df_a_tac = pd.DataFrame({"전술": a_tac_vc.index, "사용 횟수": [f"{c}회 ({round((c/total_h2h_count)*100, 1)}%)" for c in a_tac_vc.values]})
                    st.dataframe(df_a_tac, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### ⚽ 맞대결 전/후반 득점 및 비율(%) 통계표")

            h_1h_list, h_2h_list, a_1h_list, a_2h_list = [], [], [], []
            for _, r in df_h2h_all.iterrows():
                if r["홈팀"] == sel_home_h2h:
                    h_1h_list.append(to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + 0)
                    h_2h_list.append(to_num(pd.Series([r.get("후반득점_홈", 0)])).iloc[0] + 0)
                    a_1h_list.append(to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + 0)
                    a_2h_list.append(to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0] + 0)
                else:
                    h_1h_list.append(to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + 0)
                    h_2h_list.append(to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0] + 0)
                    a_1h_list.append(to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + 0)
                    a_2h_list.append(to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0] + 0)

            sum_h_1h, sum_h_2h = sum(h_1h_list), sum(h_2h_list)
            sum_a_1h, sum_a_2h = sum(a_1h_list), sum(a_2h_list)
            tot_h_score, tot_a_score = sum_h_1h + sum_h_2h, sum_a_1h + sum_a_2h

            avg_h_1h, avg_h_2h, avg_h_tot = round(sum_h_1h / total_h2h_count, 2), round(sum_h_2h / total_h2h_count, 2), round(tot_h_score / total_h2h_count, 2)
            avg_a_1h, avg_a_2h, avg_a_tot = round(sum_a_1h / total_h2h_count, 2), round(sum_a_2h / total_h2h_count, 2), round(tot_a_score / total_h2h_count, 2)

            ratio_h_2h = f"{round((sum_h_2h / tot_h_score) * 100, 1)}%" if tot_h_score > 0 else "0.0%"
            ratio_a_2h = f"{round((sum_a_2h / tot_a_score) * 100, 1)}%" if tot_a_score > 0 else "0.0%"
            tot_all_2h, tot_all_score = sum_h_2h + sum_a_2h, tot_h_score + tot_a_score
            ratio_all_2h = f"{round((tot_all_2h / tot_all_score) * 100, 1)}%" if tot_all_score > 0 else "0.0%"

            h2h_goal_table = {
                "구분": [sel_home_h2h, sel_away_h2h, "맞대결 전체 합계"],
                "전반 총득점": [int(sum_h_1h), int(sum_a_1h), int(sum_h_1h + sum_a_1h)],
                "후반 총득점": [int(sum_h_2h), int(sum_a_2h), int(tot_all_2h)],
                "총점": [int(tot_h_score), int(tot_a_score), int(tot_all_score)],
                "후반 득점비율": [ratio_h_2h, ratio_a_2h, ratio_all_2h],
                "전반 평균": [avg_h_1h, avg_a_1h, round(avg_h_1h + avg_a_1h, 2)],
                "후반 평균": [avg_h_2h, avg_a_2h, round(avg_h_2h + avg_a_2h, 2)],
                "경기당 평균득점": [avg_h_tot, avg_a_tot, round(avg_h_tot + avg_a_tot, 2)]
            }
            df_h2h_goals = pd.DataFrame(h2h_goal_table)
            st.dataframe(df_h2h_goals, use_container_width=True, hide_index=True)

            with st.expander("📊 / 📋 네이버 블로그/카페용 맞대결 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
                st.markdown("##### 🌟 [네이버 블로그/카페 전용] 맞대결 지표 비교 도표")
                st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

                gauge_stats = {
                    "점유율 (%)": (poss_h, poss_a),
                    "기대득점 (xG)": (xg_h, xg_a),
                    "유효슈팅 (회)": (sot_h, sot_a),
                    "패스성공률 (%)": (pass_h, pass_a),
                    "경기당 평균득점": (avg_h_tot, avg_a_tot)
                }
                
                naver_info_html = generate_naver_match_infographic(
                    sel_home_h2h, sel_away_h2h, gauge_stats, df_h2h_goals, 
                    h2h_all_str=h2h_all_text, h2h_exact_str=h2h_exact_text
                )
                
                render_clipboard_component(naver_info_html, "t4_clip", height=560)

            st.markdown("---")
            st.markdown("### 📋 역대 맞대결 전체 경기 세부 내역")
            pref_h2h_cols = ["시즌", "리그명", "경기날짜", "홈팀", "원정팀", "전반득점_홈", "후반득점_홈", "전반득점_원", "후반득점_원", "전술_홈", "전술_원", "점유율_홈", "점유율_원", "슈팅_홈", "슈팅_원", "유효슈팅_홈", "유효슈팅_원", "xG_홈", "xG_원"]
            show_h2h_cols = [c for c in pref_h2h_cols if c in df_h2h_all.columns]
            st.dataframe(df_h2h_all[show_h2h_cols] if show_h2h_cols else df_h2h_all, use_container_width=True, hide_index=True)

        else:
            st.info(f"💡 [{sel_home_h2h}]와 [{sel_away_h2h}] 간의 과거 맞대결 경기 데이터가 아직 10번 시트에 없습니다.")
    else:
        st.info("💡 10번 '경기내용' 탭에 데이터가 없습니다.")
