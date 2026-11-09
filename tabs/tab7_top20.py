import streamlit as st
import pandas as pd
import numpy as np
from database import load_sheet_data
from tabs.tab2_scanner import get_preprocessed_bm_db_v3


def render_tab6_top20(spreadsheet_id, bookmakers, overseas_bookmakers, tol):
    st.subheader("🏆 당일 최우선 추천픽 TOP 20 종합 랭킹 (9개사 통합 분석)")
    st.caption("라운드스캔에 등록된 모든 경기를 대상으로 9개 북메이커 전체 과거 동일배당(승무패 + 언오버) 데이터를 종합 분석하여 적중 확률이 가장 높은 1~20위 경기를 우선순위로 산출합니다.")

    scanner_sheet_name = "라운드스캔"
    df_scan_raw = load_sheet_data(scanner_sheet_name, spreadsheet_id)

    def safe_flt(val, default=0.0):
        try:
            res = float(str(val).replace("%", "").strip())
            return res if res > 0 else default
        except Exception:
            return default

    with st.container(border=True):
        st.markdown("##### ⚙️ TOP 20 산출 기준 및 신뢰도 필터 설정")
        c_set1, c_set2, c_set3 = st.columns([1.2, 1.2, 2.6])
        with c_set1:
            min_match_cnt = st.number_input(
                "🎯 9개사 합산 최소 매칭 건수 기준",
                min_value=1,
                max_value=200,
                value=5,
                step=1,
                key="top20_min_match_cnt"
            )
        with c_set2:
            ou_options = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
            ou_line_val = float(
                st.selectbox(
                    "⚽ 언오버 분석 기준점",
                    ou_options,
                    index=ou_options.index(2.5),
                    key="top20_ou_line"
                )
            )
        with c_set3:
            st.info(
                "💡 **데이터 누적량별 최소 매칭 건수 권장 기준**\n"
                "- **현재 (~1,500줄):** 최소 **5건** 권장\n"
                "- **중기 (1,500~3,000줄):** 최소 **8~10건** 권장\n"
                "- **장기 (3,000~6,000줄):** 최소 **15건** / **6,000줄 이상:** **20건+** 권장"
            )

        run_top20_btn = st.button(
            f"🔥 [라운드스캔 전체 경기 대상] 당일 최우선 TOP 20 적중확률 산출하기 (최소 {min_match_cnt}건 이상)",
            type="primary",
            use_container_width=True,
            key="btn_run_top20_ranking"
        )

    if df_scan_raw.empty:
        st.warning(f"⚠️ 현재 `{scanner_sheet_name}` 시트에 등록된 경기가 없습니다. 2번 탭에서 이번 라운드 경기를 먼저 등록해 주세요.")
        return

    if run_top20_btn:
        with st.spinner("9개 북메이커 전체 시트를 통합하여 당일 최우선 TOP 20 경기를 산출 중입니다..."):
            cached_dbs = {bm: get_preprocessed_bm_db_v3(bm, spreadsheet_id) for bm in bookmakers}
            ranked_matches = []

            for _, r in df_scan_raw.iterrows():
                season = str(r.get("시즌", "25-26")).strip()
                league = str(r.get("리그명", "PL")).strip()
                m_date = str(r.get("경기날짜", "-")).strip()
                home = str(r.get("홈팀", "")).strip()
                away = str(r.get("원정팀", "")).strip()

                if not home or not away:
                    continue

                bh = safe_flt(r.get("배트맨_홈"), 0.0)
                bd = safe_flt(r.get("배트맨_무"), 0.0)
                ba = safe_flt(r.get("배트맨_원"), 0.0)

                all_bms_odds = {"배트맨": (bh, bd, ba)}
                valid_oh, valid_od, valid_oa = [], [], []
                for obm in overseas_bookmakers:
                    oh = safe_flt(r.get(f"{obm}_홈"), 0.0)
                    od = safe_flt(r.get(f"{obm}_무"), 0.0)
                    oa = safe_flt(r.get(f"{obm}_원"), 0.0)
                    all_bms_odds[obm] = (oh, od, oa)
                    if oh >= 1.01 and od >= 1.01 and oa >= 1.01:
                        valid_oh.append(oh)
                        valid_od.append(od)
                        valid_oa.append(oa)

                avg_oh = round(float(np.mean(valid_oh)), 2) if valid_oh else 0.0
                avg_od = round(float(np.mean(valid_od)), 2) if valid_od else 0.0
                avg_oa = round(float(np.mean(valid_oa)), 2) if valid_oa else 0.0

                tot_wdl_cnt, tot_hw, tot_dr, tot_aw = 0, 0, 0, 0
                tot_ou_cnt, tot_ov, tot_un = 0, 0, 0
                active_bm_cnt = 0

                for bm in bookmakers:
                    h_v, d_v, a_v = all_bms_odds.get(bm, (0.0, 0.0, 0.0))
                    if h_v < 1.01 or d_v < 1.01 or a_v < 1.01:
                        continue
                    active_bm_cnt += 1
                    prep_db = cached_dbs.get(bm)
                    if not prep_db:
                        continue

                    h_arr, d_arr, a_arr = prep_db["h_arr"], prep_db["d_arr"], prep_db["a_arr"]
                    cond = (
                        (h_arr >= h_v - tol) & (h_arr <= h_v + tol) &
                        (d_arr >= d_v - tol) & (d_arr <= d_v + tol) &
                        (a_arr >= a_v - tol) & (a_arr <= a_v + tol)
                    )
                    c_cnt = int(np.sum(cond))
                    if c_cnt > 0:
                        m_res = prep_db["res_arr"][cond]
                        tot_wdl_cnt += c_cnt
                        tot_hw += int(np.sum(m_res == "홈승"))
                        tot_dr += int(np.sum(m_res == "무승부"))
                        tot_aw += int(np.sum(m_res == "원정승"))

                        v_goals = prep_db["tot_goals_arr"][cond]
                        v_goals = v_goals[v_goals >= 0]
                        c_ou = int(len(v_goals))
                        if c_ou > 0:
                            c_ov = int(np.sum(v_goals > ou_line_val))
                            tot_ou_cnt += c_ou
                            tot_ov += c_ov
                            tot_un += int(c_ou - c_ov)

                win_prob = round((tot_hw / tot_wdl_cnt) * 100, 1) if tot_wdl_cnt > 0 else 0.0
                draw_prob = round((tot_dr / tot_wdl_cnt) * 100, 1) if tot_wdl_cnt > 0 else 0.0
                lose_prob = round((tot_aw / tot_wdl_cnt) * 100, 1) if tot_wdl_cnt > 0 else 0.0

                over_prob = round((tot_ov / tot_ou_cnt) * 100, 1) if tot_ou_cnt > 0 else 0.0
                under_prob = round((tot_un / tot_ou_cnt) * 100, 1) if tot_ou_cnt > 0 else 0.0

                # 승무패 + 언오버 통합 후보 중 최소 매칭 건수(min_match_cnt)를 충족하는 픽 수집
                candidates = []
                if tot_wdl_cnt >= min_match_cnt:
                    candidates.append(("🏠 홈승", win_prob, tot_hw, tot_wdl_cnt, "승무패"))
                    candidates.append(("⚖️ 무승부", draw_prob, tot_dr, tot_wdl_cnt, "승무패"))
                    candidates.append(("🚗 원정승", lose_prob, tot_aw, tot_wdl_cnt, "승무패"))
                if tot_ou_cnt >= min_match_cnt:
                    candidates.append((f"📈 {ou_line_val} 오버", over_prob, tot_ov, tot_ou_cnt, "언오버"))
                    candidates.append((f"📉 {ou_line_val} 언더", under_prob, tot_un, tot_ou_cnt, "언오버"))

                if not candidates:
                    continue

                # 확률 높은 순 -> 매칭 건수 많은 순 정렬
                candidates.sort(key=lambda x: (x[1], x[3], x[2]), reverse=True)
                best_pick = candidates[0]
                second_pick = candidates[1] if len(candidates) > 1 else None

                ranked_matches.append({
                    "season": season,
                    "league": league,
                    "date": m_date,
                    "home": home,
                    "away": away,
                    "batman_odds": (bh, bd, ba),
                    "overseas_avg": (avg_oh, avg_od, avg_oa),
                    "all_odds": all_bms_odds,
                    "active_bm_cnt": active_bm_cnt,
                    "tot_wdl_cnt": tot_wdl_cnt,
                    "tot_hw": tot_hw,
                    "tot_dr": tot_dr,
                    "tot_aw": tot_aw,
                    "win_prob": win_prob,
                    "draw_prob": draw_prob,
                    "lose_prob": lose_prob,
                    "tot_ou_cnt": tot_ou_cnt,
                    "tot_ov": tot_ov,
                    "tot_un": tot_un,
                    "over_prob": over_prob,
                    "under_prob": under_prob,
                    "best_label": best_pick[0],
                    "best_prob": best_pick[1],
                    "best_hits": best_pick[2],
                    "best_total": best_pick[3],
                    "best_cat": best_pick[4],
                    "second_str": f"{second_pick[0]} ({second_pick[1]}%)" if second_pick else "-"
                })

            # 전체 경기 중 1순위: 최고 적중확률, 2순위: 매칭 표본 건수, 3순위: 적중 횟수로 정렬 후 상위 20개 추출
            ranked_matches.sort(
                key=lambda x: (x["best_prob"], x["best_total"], x["best_hits"]),
                reverse=True
            )
            st.session_state["top20_results"] = ranked_matches[:20]
            st.session_state["top20_total_scanned"] = len(df_scan_raw)
            st.session_state["top20_qualified_cnt"] = len(ranked_matches)
            st.session_state["top20_min_cnt_used"] = min_match_cnt
            st.session_state["top20_ou_line_used"] = ou_line_val

    if "top20_results" in st.session_state:
        top20_list = st.session_state["top20_results"]
        total_scanned = st.session_state.get("top20_total_scanned", 0)
        qualified_cnt = st.session_state.get("top20_qualified_cnt", 0)
        min_cnt_used = st.session_state.get("top20_min_cnt_used", 5)
        ou_used = st.session_state.get("top20_ou_line_used", 2.5)

        st.markdown("---")
        st.subheader(
            f"👑 당일 최우선 주력픽 TOP {len(top20_list)} 순위표 "
            f"(전체 {total_scanned}경기 중 최소 {min_cnt_used}건 이상 충족: {qualified_cnt}경기)"
        )

        if not top20_list:
            st.info(
                f"💡 현재 최소 매칭 건수({min_cnt_used}건 이상)를 충족하는 경기가 없습니다. "
                f"상단에서 최소 매칭 건수 기준을 낮추어 다시 실행해 보세요."
            )
        else:
            table_rows = []
            for rank_idx, item in enumerate(top20_list, 1):
                bh, bd, ba = item["batman_odds"]
                table_rows.append({
                    "순위": f"🏆 {rank_idx}위" if rank_idx <= 3 else f"{rank_idx}위",
                    "리그/날짜": f"{item['league']} ({item['date']})",
                    "매치업 (홈 vs 원정)": f"{item['home']} vs {item['away']}",
                    "👑 최우선 추천픽": item["best_label"],
                    "적중확률 (성공/매칭)": f"{item['best_prob']}% ({item['best_hits']}/{item['best_total']}건)",
                    "🥈 차선책 (2순위)": item["second_str"],
                    "9개사 승/무/패 종합": f"승 {item['win_prob']}% / 무 {item['draw_prob']}% / 패 {item['lose_prob']}% ({item['tot_wdl_cnt']}건)",
                    f"9개사 {ou_used} 언오버": f"오버 {item['over_prob']}% / 언더 {item['under_prob']}% ({item['tot_ou_cnt']}건)",
                    "배트맨 배당": f"{bh} / {bd} / {ba}"
                })

            st.dataframe(
                pd.DataFrame(table_rows),
                use_container_width=True,
                height=min(760, 38 * (len(table_rows) + 1)),
                hide_index=True
            )

            st.markdown("---")
            st.markdown("#### 📋 1~20위 경기별 상세 브리핑 & 3번 탭(도표 생성) 원클릭 연동")

            for rank_idx, item in enumerate(top20_list, 1):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.2, 3.3, 1.8])
                    with c1:
                        rank_badge = f"🥇 1위" if rank_idx == 1 else (f"🥈 2위" if rank_idx == 2 else (f"🥉 3위" if rank_idx == 3 else f"#{rank_idx}위"))
                        st.markdown(f"### {rank_badge} {item['home']} vs {item['away']}")
                        st.caption(f"🏆 {item['league']} | 📅 {item['date']} | 분석 업체: {item['active_bm_cnt']}개사")
                        st.markdown(
                            f"👑 **최우선 추천:** `{item['best_label']}` "
                            f"(**{item['best_prob']}%** · {item['best_hits']}/{item['best_total']}건)"
                        )
                    with c2:
                        bh, bd, ba = item["batman_odds"]
                        oh, od, oa = item["overseas_avg"]
                        st.markdown(
                            f"**🏢 배트맨:** `{bh}` / `{bd}` / `{ba}` &nbsp;|&nbsp; "
                            f"**해외평균:** `{oh}` / `{od}` / `{oa}`"
                        )
                        st.markdown(
                            f"📊 **9개사 승무패 ({item['tot_wdl_cnt']}건):** "
                            f"홈승 **{item['win_prob']}%** ({item['tot_hw']}회) / "
                            f"무 **{item['draw_prob']}%** ({item['tot_dr']}회) / "
                            f"원정 **{item['lose_prob']}%** ({item['tot_aw']}회)"
                        )
                        st.markdown(
                            f"⚽ **9개사 {ou_used} 언오버 ({item['tot_ou_cnt']}건):** "
                            f"오버 **{item['over_prob']}%** ({item['tot_ov']}회) / "
                            f"언더 **{item['under_prob']}%** ({item['tot_un']}회) &nbsp;|&nbsp; "
                            f"🥈 **2순위:** `{item['second_str']}`"
                        )
                    with c3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button(
                            "👉 3번 탭 도표/상세 분석 전송",
                            key=f"btn_top20_send_{rank_idx}",
                            type="primary",
                            use_container_width=True
                        ):
                            st.session_state.selected_scan_match = item
                            st.session_state.t2_target_league = item["league"]
                            st.session_state.t2_home_team = item["home"]
                            st.session_state.t2_away_team = item["away"]
                            for bm in bookmakers:
                                h_val, d_val, a_val = item["all_odds"].get(bm, (0.0, 0.0, 0.0))
                                st.session_state[f"t2_{bm}_h"] = float(h_val)
                                st.session_state[f"t2_{bm}_d"] = float(d_val)
                                st.session_state[f"t2_{bm}_a"] = float(a_val)
                            st.session_state.sel_h2h_home = item["home"]
                            st.session_state.sel_h2h_away = item["away"]
                            st.success(f"🎯 [{item['home']} vs {item['away']}] 배당이 3번 탭으로 전송되었습니다!")
                            st.rerun()
