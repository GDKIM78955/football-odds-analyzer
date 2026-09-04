import streamlit as st
import pandas as pd
import numpy as np
from database import load_sheet_data
from infographics import generate_naver_odds_infographic, render_clipboard_component

def render_tab3(spreadsheet_id, bookmakers, overseas_bookmakers, tol):
    st.subheader("🔬 3번 탭: 9대 북메이커 배당 입력 및 승률 분석")

    scanner_sheet_name = "라운드스캔"
    df_t3_scan = load_sheet_data(scanner_sheet_name, spreadsheet_id)
    
    def safe_flt(val, default):
        try:
            return float(str(val).replace("%", "").strip())
        except:
            return default

    def on_t3_match_load():
        sel_t3 = st.session_state.sel_t3_match_loader
        if sel_t3 != "➕ [직접 수동 입력하기]":
            if not df_t3_scan.empty:
                for _, r in df_t3_scan.iterrows():
                    match_lbl = f"[{r.get('리그명', '')}] {r.get('홈팀', '')} vs {r.get('원정팀', '')} ({r.get('경기날짜', '')})"
                    if match_lbl == sel_t3:
                        st.session_state.t2_target_league = str(r.get("리그명", "PL"))
                        st.session_state.t2_home_team = str(r.get("홈팀", ""))
                        st.session_state.t2_away_team = str(r.get("원정팀", ""))
                        
                        st.session_state[f"t2_배트맨_h"] = float(safe_flt(r.get("배트맨_홈"), 0.0))
                        st.session_state[f"t2_배트맨_d"] = float(safe_flt(r.get("배트맨_무"), 0.0))
                        st.session_state[f"t2_배트맨_a"] = float(safe_flt(r.get("배트맨_원"), 0.0))
                        
                        for obm in overseas_bookmakers:
                            st.session_state[f"t2_{obm}_h"] = float(safe_flt(r.get(f"{obm}_홈"), 0.0))
                            st.session_state[f"t2_{obm}_d"] = float(safe_flt(r.get(f"{obm}_무"), 0.0))
                            st.session_state[f"t2_{obm}_a"] = float(safe_flt(r.get(f"{obm}_원"), 0.0))
                        break

    with st.container(border=True):
        if not df_t3_scan.empty and "홈팀" in df_t3_scan.columns:
            st.markdown("##### 🔍 [라운드스캔 시트에서 분석할 경기 불러오기] (선택 시 9개사 배당 자동 세팅)")
            t3_match_labels = ["➕ [직접 수동 입력하기]"] + [f"[{r.get('리그명', '')}] {r.get('홈팀', '')} vs {r.get('원정팀', '')} ({r.get('경기날짜', '')})" for _, r in df_t3_scan.iterrows()]
            st.selectbox(
                "분석할 경기를 선택하면 아래 입력창에 배당이 자동으로 채워집니다.",
                t3_match_labels,
                index=0,
                key="sel_t3_match_loader",
                on_change=on_t3_match_load
            )
        else:
            st.caption("💡 2번 탭(스캐너)에 등록된 경기가 있으면 여기에 목록이 나타납니다. (현재 스캔 시트 비어있음)")

    if "selected_scan_match" in st.session_state and st.session_state.selected_scan_match:
        sm = st.session_state.selected_scan_match
        st.success(f"🎯 [스캐너 연동 완료] 현재 **[{sm['home']} vs {sm['away']}]** 경기의 배당 데이터가 자동 적용되어 있습니다.")

    c_an_l1, c_an_l2, c_an_l3 = st.columns([1, 1, 1])
    target_league = c_an_l1.text_input("🔍 리그명", value="PL", key="t2_target_league")
    t2_home_team = c_an_l2.text_input("🏠 홈팀명 (블로그 도표용)", value="", placeholder="예: 리버풀", key="t2_home_team")
    t2_away_team = c_an_l3.text_input("🚗 원정팀명 (블로그 도표용)", value="", placeholder="예: 본머스", key="t2_away_team")

    st.markdown("##### 🏢 분석할 9대 북메이커 배당 입력")
    odds_inputs_t2 = {}
    for i in range(0, len(bookmakers), 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < len(bookmakers):
                bm = bookmakers[idx]
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**[{idx+1}] {bm.upper()}**")
                        oh, od, oa = st.columns(3)
                        h_val = oh.number_input("홈", value=0.0, step=0.01, min_value=0.0, key=f"t2_{bm}_h")
                        d_val = od.number_input("무", value=0.0, step=0.01, min_value=0.0, key=f"t2_{bm}_d")
                        a_val = oa.number_input("원정", value=0.0, step=0.01, min_value=0.0, key=f"t2_{bm}_a")
                        odds_inputs_t2[bm] = (h_val, d_val, a_val)

    st.markdown("---")

    def compute_odds_analysis(is_league_filter=False, league_name=""):
        rows = []
        matched_dict = {}
        tot_bm = 0
        tot_payout = 0.0
        tot_m = 0
        tot_hw = 0
        tot_dr = 0
        tot_aw = 0

        for idx, bm in enumerate(bookmakers, 1):
            h, d, a = odds_inputs_t2.get(bm, (0.0, 0.0, 0.0))
            if h <= 0 or d <= 0 or a <= 0:
                rows.append({
                    "순번": str(idx), "북메이커": bm.upper(), "입력 배당": "미입력", "환급률": "-",
                    "매칭 경기": "0건", "홈승 확률": "-", "무승부 확률": "-", "원정승 확률": "-"
                })
                continue

            raw_inv = (1/h) + (1/d) + (1/a)
            payout = (1 / raw_inv) * 100
            tot_payout += payout
            tot_bm += 1

            df_bm = load_sheet_data(bm, spreadsheet_id)
            m_count = 0
            h_str, d_str, a_str = "0.0%", "0.0%", "0.0%"

            if not df_bm.empty:
                try:
                    cols = list(df_bm.columns)
                    h_col = next((c for c in cols if any(k in c for k in ["해당_홈", "배당_홈", "홈배당", "홈_승", "H_ODDS"])), None)
                    d_col = next((c for c in cols if any(k in c for k in ["해당_무", "배당_무", "무배당", "무승부", "D_ODDS"])), None)
                    a_col = next((c for c in cols if any(k in c for k in ["해당_원", "배당_원", "원정배당", "원정_승", "A_ODDS"])), None)
                    res_col = next((c for c in cols if any(k in c for k in ["경기결과", "결과", "Result"])), None)
                    lg_col = next((c for c in cols if any(k in c for k in ["리그명", "리그", "League"])), None)

                    if not h_col and len(cols) > 14:
                        h_col, d_col, a_col = cols[12], cols[13], cols[14]
                    if not res_col:
                        res_col = cols[32] if len(cols) > 32 else cols[-1]

                    if h_col and d_col and a_col and res_col:
                        df_work = df_bm.copy()
                        if is_league_filter and lg_col and league_name.strip():
                            df_work = df_work[df_work[lg_col].astype(str).str.upper() == league_name.strip().upper()]

                        df_work["H_num"] = pd.to_numeric(df_work[h_col], errors="coerce").fillna(0.0)
                        df_work["D_num"] = pd.to_numeric(df_work[d_col], errors="coerce").fillna(0.0)
                        df_work["A_num"] = pd.to_numeric(df_work[a_col], errors="coerce").fillna(0.0)

                        cond = (
                            (df_work["H_num"] >= 1.01) & (df_work["D_num"] >= 1.01) & (df_work["A_num"] >= 1.01) &
                            (df_work["H_num"] >= h - tol) & (df_work["H_num"] <= h + tol) &
                            (df_work["D_num"] >= d - tol) & (df_work["D_num"] <= d + tol) &
                            (df_work["A_num"] >= a - tol) & (df_work["A_num"] <= a + tol)
                        )
                        matched = df_work[cond]
                        m_count = len(matched)

                        if m_count > 0:
                            matched_dict[bm.upper()] = matched
                            res_c = matched[res_col].value_counts()
                            hw = res_c.get("홈승", 0)
                            dr = res_c.get("무승부", 0)
                            aw = res_c.get("원정승", 0)

                            tot_m += m_count
                            tot_hw += hw
                            tot_dr += dr
                            tot_aw += aw

                            h_str = f"{round((hw/m_count)*100, 1)}% ({hw}회)"
                            d_str = f"{round((dr/m_count)*100, 1)}% ({dr}회)"
                            a_str = f"{round((aw/m_count)*100, 1)}% ({aw}회)"
                except Exception:
                    pass

            rows.append({
                "순번": str(idx), "북메이커": bm.upper(),
                "입력 배당": f"{h} / {d} / {a}",
                "환급률": f"{round(payout, 2)}%",
                "매칭 경기": f"{m_count}건",
                "홈승 확률": h_str, "무승부 확률": d_str, "원정승 확률": a_str
            })

        avg_p_str = f"{round(tot_payout / tot_bm, 2)}%" if tot_bm > 0 else "-"
        if tot_m > 0:
            tot_h_str = f"{round((tot_hw / tot_m) * 100, 1)}% ({tot_hw}회)"
            tot_d_str = f"{round((tot_dr / tot_m) * 100, 1)}% ({tot_dr}회)"
            tot_a_str = f"{round((tot_aw / tot_m) * 100, 1)}% ({tot_aw}회)"
        else:
            tot_h_str, tot_d_str, tot_a_str = "0.0%", "0.0%", "0.0%"

        rows.append({
            "순번": "🔥",
            "북메이커": "종합 가중평균 (누적)",
            "입력 배당": f"유효 {tot_bm}개사",
            "환급률": avg_p_str,
            "매칭 경기": f"총 {tot_m}건",
            "홈승 확률": tot_h_str,
            "무승부 확률": tot_d_str,
            "원정승 확률": tot_a_str
        })

        return pd.DataFrame(rows), matched_dict

    df_all_league, matched_all = compute_odds_analysis(is_league_filter=False)
    df_target_league, matched_target = compute_odds_analysis(is_league_filter=True, league_name=target_league)

    st.subheader("1️⃣ [전체 리그 기준] 동일 배당 승률 분석표")
    st.dataframe(df_all_league, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader(f"2️⃣ [{target_league} 동일 리그 전용] 동일 배당 승률 분석표")
    st.dataframe(df_target_league, use_container_width=True, hide_index=True)

    with st.expander("📊 / 📋 네이버 블로그/카페용 배당 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
        st.markdown("##### 🌟 [네이버 블로그/카페 전용] 배당 & 승률 인포그래픽 카드")
        st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

        compare_options = ["🌟 해외 종합 가중평균 (전체 평균)"] + overseas_bookmakers
        sel_compare_target = st.selectbox("비교할 대상 선택", compare_options, index=0, key="sel_compare_bm_t2")

        b_odds_val = odds_inputs_t2.get("배트맨", (0.0, 0.0, 0.0))

        if "종합 가중평균" in sel_compare_target:
            valid_h, valid_d, valid_a = [], [], []
            for obm in overseas_bookmakers:
                oh, od, oa = odds_inputs_t2.get(obm, (0.0, 0.0, 0.0))
                if oh >= 1.01 and od >= 1.01 and oa >= 1.01:
                    valid_h.append(oh)
                    valid_d.append(od)
                    valid_a.append(oa)
            
            if valid_h:
                avg_oh = round(float(np.mean(valid_h)), 2)
                avg_od = round(float(np.mean(valid_od)), 2)
                avg_oa = round(float(np.mean(valid_oa)), 2)
                o_odds_val = (avg_oh, avg_od, avg_oa)
            else:
                o_odds_val = (0.0, 0.0, 0.0)
            
            display_name = f"해외 종합평균 (유효 {len(valid_h)}개사)"
        else:
            o_odds_val = odds_inputs_t2.get(sel_compare_target, (0.0, 0.0, 0.0))
            display_name = sel_compare_target

        naver_odds_html = generate_naver_odds_infographic(
            b_odds_val, display_name, o_odds_val, 
            league_name=target_league, home_team=t2_home_team.strip(), away_team=t2_away_team.strip()
        )

        render_clipboard_component(naver_odds_html, "t2_clip", height=490)

    st.markdown("---")
    st.subheader("📋 매칭된 과거 경기 상세 리스트 (업체별 전체 내역)")
    
    view_option = st.radio("상세 리스트 필터 선택", ["전체 리그 매칭 내역", f"[{target_league}] 동일 리그 매칭 내역"], horizontal=True)
    active_matched = matched_target if "동일 리그" in view_option else matched_all

    if active_matched:
        for name, m_df in active_matched.items():
            with st.expander(f"📌 [{name}] 매칭 내역 총 {len(m_df)}건 확인하기", expanded=False):
                pref_cols = ["시즌", "리그명", "날짜", "홈팀", "원정팀", "해당_홈", "해당_무", "해당_원", "홈스코어", "원정스코어", "경기결과", "정/중/역", "적중배당"]
                show_cols = [c for c in pref_cols if c in m_df.columns]
                st.dataframe(m_df[show_cols] if show_cols else m_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"💡 현재 선택된 조건에 일치(오차 범위 ±{tol})하는 과거 경기 데이터가 없습니다.")
