import streamlit as st
import pandas as pd
import numpy as np
from database import load_sheet_data

def render_tab2(spreadsheet_id, bookmakers, overseas_bookmakers, tol):
    st.subheader("📡 라운드 경기 배당 자동 스캐너 & 추천픽 레이더")
    st.caption("와이즈토토로 배트맨 경기를 연속으로 담아두고 해외 배당을 차례대로 채워 '라운드스캔' 시트에 저장 및 분석합니다.")

    scanner_sheet_name = "라운드스캔"
    stats_sheet_name = "경기내용"

    df_scan_raw = load_sheet_data(scanner_sheet_name, spreadsheet_id)

    def safe_flt(val, default):
        try:
            return float(str(val).replace("%", "").strip())
        except:
            return default

    scan_input_mode = st.radio(
        "스캔 경기 입력 방식",
        ["🚀 [2단계 분할 입력] 와이즈토토 먼저 모아서 ➔ 해외 배당 순차 입력 (추천 ⭐)", "⚡ [1경기 직접 등록 및 기존 배당 수정]"],
        horizontal=True,
        key="scan_input_mode_radio"
    )

    if "2단계 분할 입력" in scan_input_mode:
        c_sc_step1, c_sc_step2 = st.columns([1, 1], gap="large")

        with c_sc_step1:
            st.markdown("##### 1️⃣ [1단계] 와이즈토토 배트맨 경기 연속 등록")
            st.caption("와이즈토토를 보면서 이번 라운드 경기들의 배트맨 배당을 대기열에 담아둡니다.")

            with st.container(border=True):
                c_sq1, c_sq2, c_sq3 = st.columns(3)
                sq_season = c_sq1.text_input("시즌", value="25-26", key="sq_in_season")
                sq_league = c_sq2.text_input("리그명", value="PL", key="sq_in_league")
                sq_date = c_sq3.text_input("경기 날짜", value="25.08.30", key="sq_in_date")

                c_sqt1, c_sqt2 = st.columns(2)
                sq_home = c_sqt1.text_input("홈팀명", placeholder="예: 아스날", key="sq_in_home")
                sq_away = c_sqt2.text_input("원정팀명", placeholder="예: 브라이튼", key="sq_in_away")

                st.markdown("**🏢 배트맨 최종 배당**")
                sqb_h, sqb_d, sqb_a = st.columns(3)
                sq_bh = sqb_h.number_input("홈", value=0.0, step=0.01, min_value=0.0, key="sq_in_bh")
                sq_bd = sqb_d.number_input("무", value=0.0, step=0.01, min_value=0.0, key="sq_in_bd")
                sq_ba = sqb_a.number_input("원정", value=0.0, step=0.01, min_value=0.0, key="sq_in_ba")

                if st.button("➕ 스캔 대기열에 경기 추가 (계속 등록)", type="primary", use_container_width=True, key="btn_add_scan_queue"):
                    if sq_home.strip() and sq_away.strip():
                        st.session_state.scan_queue.append({
                            "season": sq_season, "league": sq_league, "date": sq_date,
                            "home": sq_home.strip(), "away": sq_away.strip(),
                            "batman_odds": (sq_bh, sq_bd, sq_ba)
                        })
                        st.success(f"🎉 [{sq_home} vs {sq_away}] 스캔 대기열 추가 완료! (총 {len(st.session_state.scan_queue)}경기 대기 중)")
                    else:
                        st.warning("홈팀명과 원정팀명을 입력해 주세요.")

            if st.session_state.scan_queue:
                st.markdown("##### 📋 현재 스캔 대기열 목록")
                sq_preview = []
                for i, m in enumerate(st.session_state.scan_queue):
                    status = "👉 [작성 차례]" if i == st.session_state.current_scan_queue_idx else ("⏳ [대기 중]" if i > st.session_state.current_scan_queue_idx else "✅ [완료]")
                    sq_preview.append({
                        "순번": i + 1, "상태": status,
                        "매치업": f"{m['home']} vs {m['away']}", "리그/날짜": f"{m['league']} ({m['date']})",
                        "배트맨 배당": f"{m['batman_odds'][0]} / {m['batman_odds'][1]} / {m['batman_odds'][2]}"
                    })
                st.dataframe(pd.DataFrame(sq_preview), use_container_width=True, hide_index=True)

                with st.container(border=True):
                    st.markdown("##### ✏️ 스캔 대기열 특정 경기 내용 수정하기")
                    sq_indices = [f"#{i+1} : {m['home']} vs {m['away']}" for i, m in enumerate(st.session_state.scan_queue)]
                    sel_sq_str = st.selectbox("수정할 스캔 대기 경기 선택", sq_indices, key="sel_scan_queue_to_edit")
                    sel_sq_idx = int(sel_sq_str.split(":")[0].replace("#", "").strip()) - 1
                    target_sq_item = st.session_state.scan_queue[sel_sq_idx]

                    e_sqh = st.text_input("홈팀명 수정", value=target_sq_item["home"], key="edit_sqh")
                    e_sqa = st.text_input("원정팀명 수정", value=target_sq_item["away"], key="edit_sqa")
                    e_sql = st.text_input("리그명 수정", value=target_sq_item["league"], key="edit_sql")
                    e_sqd = st.text_input("날짜 수정", value=target_sq_item["date"], key="edit_sqd")
                    
                    seb1, seb2, seb3 = st.columns(3)
                    e_sbh = seb1.number_input("배트맨 홈", value=float(target_sq_item["batman_odds"][0]), step=0.01, key="edit_sbh")
                    e_sbd = seb2.number_input("배트맨 무", value=float(target_sq_item["batman_odds"][1]), step=0.01, key="edit_sbd")
                    e_sba = seb3.number_input("배트맨 원정", value=float(target_sq_item["batman_odds"][2]), step=0.01, key="edit_sba")

                    if st.button("🔄 선택한 스캔 대기 경기 갱신", type="primary", use_container_width=True):
                        st.session_state.scan_queue[sel_sq_idx]["home"] = e_sqh.strip()
                        st.session_state.scan_queue[sel_sq_idx]["away"] = e_sqa.strip()
                        st.session_state.scan_queue[sel_sq_idx]["league"] = e_sql.strip()
                        st.session_state.scan_queue[sel_sq_idx]["date"] = e_sqd.strip()
                        st.session_state.scan_queue[sel_sq_idx]["batman_odds"] = (e_sbh, e_sbd, e_sba)
                        st.success(f"🎉 스캔 대기열 #{sel_sq_idx + 1} 경기 정보가 성공적으로 수정되었습니다!")
                        st.rerun()

                if st.button("🗑️ 스캔 대기열 비우기", key="btn_clear_scan_queue"):
                    st.session_state.scan_queue = []
                    st.session_state.current_scan_queue_idx = 0
                    st.rerun()

        with c_sc_step2:
            st.markdown("##### 2️⃣ [2단계] 해외 배당 입력 및 '라운드스캔' 시트 저장")
            s_q_len = len(st.session_state.scan_queue)
            s_cur_idx = st.session_state.current_scan_queue_idx

            if s_q_len == 0:
                st.info("💡 1단계에서 경기를 먼저 등록하시면 여기에 해외 배당 입력창이 순서대로 나타납니다.")
            elif s_cur_idx >= s_q_len:
                st.success(f"🎉 대기열의 모든 경기(총 {s_q_len}경기) 저장이 완료되었습니다! 아래 스캐너 랭킹을 확인하세요.")
                if st.button("🔄 새 스캔 대기열 시작하기", key="btn_restart_scan_queue"):
                    st.session_state.scan_queue = []
                    st.session_state.current_scan_queue_idx = 0
                    st.rerun()
            else:
                cur_s_match = st.session_state.scan_queue[s_cur_idx] if s_cur_idx < s_q_len else None
                if not cur_s_match:
                    st.session_state.current_scan_queue_idx = 0
                    st.rerun()

                next_s_match = st.session_state.scan_queue[s_cur_idx + 1] if s_cur_idx + 1 < s_q_len else None

                st.markdown(f"""
                <div style="background-color: #047857; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <div style="font-size: 13px; color: #a7f3d0;">[진행 중: {s_cur_idx + 1} / {s_q_len} 번째 경기]</div>
                    <div style="font-size: 18px; font-weight: bold; margin-top: 4px;">👉 {cur_s_match['home']} vs {cur_s_match['away']} ({cur_s_match['league']})</div>
                    <div style="font-size: 13px; margin-top: 4px;">배트맨 배당: {cur_s_match['batman_odds'][0]} / {cur_s_match['batman_odds'][1]} / {cur_s_match['batman_odds'][2]} | 날짜: {cur_s_match['date']}</div>
                </div>
                """, unsafe_allow_html=True)

                if next_s_match:
                    st.caption(f"⏭️ **다음 대기 경기:** [{next_s_match['home']} vs {next_s_match['away']}] ({next_s_match['league']})")
                else:
                    st.caption("🏁 이번 경기가 스캔 대기열의 마지막 경기입니다.")

                st.markdown("##### 🌐 주요 해외 북메이커 배당 입력 (있는 것만 입력)")
                sq_overseas_inputs = {}
                for i in range(0, len(overseas_bookmakers), 4):
                    cols_sq_bm = st.columns(4)
                    for j in range(4):
                        idx = i + j
                        if idx < len(overseas_bookmakers):
                            obm = overseas_bookmakers[idx]
                            with cols_sq_bm[j]:
                                with st.container(border=True):
                                    st.caption(f"**{obm.upper()}**")
                                    dh, dd, da = st.columns(3)
                                    h_v = dh.number_input("홈", value=0.0, step=0.01, min_value=0.0, key=f"sq_{s_cur_idx}_{obm}_h")
                                    d_v = dd.number_input("무", value=0.0, step=0.01, min_value=0.0, key=f"sq_{s_cur_idx}_{obm}_d")
                                    a_v = da.number_input("원정", value=0.0, step=0.01, min_value=0.0, key=f"sq_{s_cur_idx}_{obm}_a")
                                    sq_overseas_inputs[obm] = (h_v, d_v, a_v)

                if st.button("💾 '라운드스캔' 시트 저장 및 다음 경기 ➔", type="primary", use_container_width=True, key="btn_save_next_scan"):
                    from database import get_gspread_client
                    client = get_gspread_client()
                    if client:
                        try:
                            spreadsheet = client.open_by_key(spreadsheet_id)
                            ws_scan = spreadsheet.worksheet(scanner_sheet_name)
                            
                            new_scan_row = [
                                cur_s_match["season"], cur_s_match["league"], cur_s_match["date"],
                                cur_s_match["home"], cur_s_match["away"],
                                cur_s_match["batman_odds"][0], cur_s_match["batman_odds"][1], cur_s_match["batman_odds"][2]
                            ]
                            for obm in overseas_bookmakers:
                                oh, od, oa = sq_overseas_inputs.get(obm, (0.0, 0.0, 0.0))
                                new_scan_row.extend([oh, od, oa])

                            all_data = ws_scan.get_all_values()
                            target_row_idx = None
                            
                            if len(all_data) > 1:
                                for r_i, row in enumerate(all_data[1:], start=2):
                                    if len(row) >= 5:
                                        r_home = str(row[3]).strip()
                                        r_away = str(row[4]).strip()
                                        if r_home == cur_s_match["home"] and r_away == cur_s_match["away"]:
                                            target_row_idx = r_i
                                            break
                            
                            if target_row_idx:
                                ws_scan.update(f"A{target_row_idx}:AF{target_row_idx}", [new_scan_row], value_input_option="USER_ENTERED")
                            else:
                                ws_scan.append_row(new_scan_row, value_input_option="USER_ENTERED")
                            
                            st.session_state.current_scan_queue_idx += 1
                            st.cache_data.clear()
                            st.success(f"🎉 [{cur_s_match['home']} vs {cur_s_match['away']}] 저장 완료!")
                            import time
                            time.sleep(0.4)
                            st.rerun()
                        except Exception as e:
                            st.error(f"저장 실패: {e}")

    else:
        def on_scan_match_change():
            sel = st.session_state.sel_scan_loader
            if sel == "➕ [새로운 경기 직접 입력]":
                st.session_state.ds_season = "25-26"
                st.session_state.ds_league = "PL"
                st.session_state.ds_date = "25.08.30"
                st.session_state.ds_home = ""
                st.session_state.ds_away = ""
                st.session_state.ds_bh = 0.0
                st.session_state.ds_bd = 0.0
                st.session_state.ds_ba = 0.0
                for obm in overseas_bookmakers:
                    st.session_state[f"ds_{obm}_h"] = 0.0
                    st.session_state[f"ds_{obm}_d"] = 0.0
                    st.session_state[f"ds_{obm}_a"] = 0.0
            else:
                if not df_scan_raw.empty:
                    for _, r in df_scan_raw.iterrows():
                        lbl = f"{r.get('홈팀', '')} vs {r.get('원정팀', '')} ({r.get('리그명', '')})"
                        if lbl == sel:
                            st.session_state.ds_season = str(r.get("시즌", "25-26"))
                            st.session_state.ds_league = str(r.get("리그명", "PL"))
                            st.session_state.ds_date = str(r.get("경기날짜", "25.08.30"))
                            st.session_state.ds_home = str(r.get("홈팀", ""))
                            st.session_state.ds_away = str(r.get("원정팀", ""))
                            st.session_state.ds_bh = safe_flt(r.get("배트맨_홈"), 0.0)
                            st.session_state.ds_bd = safe_flt(r.get("배트맨_무"), 0.0)
                            st.session_state.ds_ba = safe_flt(r.get("배트맨_원"), 0.0)
                            for obm in overseas_bookmakers:
                                st.session_state[f"ds_{obm}_h"] = safe_flt(r.get(f"{obm}_홈"), 0.0)
                                st.session_state[f"ds_{obm}_d"] = safe_flt(r.get(f"{obm}_무"), 0.0)
                                st.session_state[f"ds_{obm}_a"] = safe_flt(r.get(f"{obm}_원"), 0.0)
                            break

        with st.container(border=True):
            if not df_scan_raw.empty and "홈팀" in df_scan_raw.columns:
                st.markdown("##### 🔍 [기존 등록 경기 배당 불러와서 수정하기]")
                match_labels = ["➕ [새로운 경기 직접 입력]"] + [f"{r.get('홈팀', '')} vs {r.get('원정팀', '')} ({r.get('리그명', '')})" for _, r in df_scan_raw.iterrows()]
                st.selectbox(
                    "불러올 경기 선택 (선택 시 아래 입력창에 즉시 자동 반영)", 
                    match_labels, 
                    index=0, 
                    key="sel_scan_loader",
                    on_change=on_scan_match_change
                )

            c_ds1, c_ds2, c_ds3 = st.columns(3)
            ds_season = c_ds1.text_input("시즌", value="25-26", key="ds_season")
            ds_league = c_ds2.text_input("리그명", value="PL", key="ds_league")
            ds_date = c_ds3.text_input("경기 날짜", value="25.08.30", key="ds_date")

            c_dt1, c_dt2 = st.columns(2)
            ds_home = c_dt1.text_input("홈팀명", value="", placeholder="예: 아스날", key="ds_home")
            ds_away = c_dt2.text_input("원정팀명", value="", placeholder="예: 브라이튼", key="ds_away")

            st.markdown("**🏢 배트맨 최종 배당 (필수)**")
            c_db1, c_db2, c_db3 = st.columns(3)
            ds_bh = c_db1.number_input("홈", value=0.0, step=0.01, min_value=0.0, key="ds_bh")
            ds_bd = c_db2.number_input("무", value=0.0, step=0.01, min_value=0.0, key="ds_bd")
            ds_ba = c_db3.number_input("원정", value=0.0, step=0.01, min_value=0.0, key="ds_ba")

            st.markdown("**🌐 주요 해외 북메이커 배당 (선택: 있는 것만 입력)**")
            ds_overseas_inputs = {}
            for i in range(0, len(overseas_bookmakers), 4):
                cols_ds_bm = st.columns(4)
                for j in range(4):
                    idx = i + j
                    if idx < len(overseas_bookmakers):
                        obm = overseas_bookmakers[idx]
                        with cols_ds_bm[j]:
                            with st.container(border=True):
                                st.caption(f"**{obm.upper()}**")
                                dh, dd, da = st.columns(3)
                                h_v = dh.number_input("홈", value=0.0, step=0.01, min_value=0.0, key=f"ds_{obm}_h")
                                d_v = dd.number_input("무", value=0.0, step=0.01, min_value=0.0, key=f"ds_{obm}_d")
                                a_v = da.number_input("원정", value=0.0, step=0.01, min_value=0.0, key=f"ds_{obm}_a")
                                ds_overseas_inputs[obm] = (h_v, d_v, a_v)

            col_add_btn, col_del_btn = st.columns([2, 1])
            with col_add_btn:
                if st.button("💾 [라운드스캔] 신규 등록 또는 기존 배당 덮어쓰기(수정)", type="primary", use_container_width=True, key="btn_single_save_scan"):
                    if ds_home.strip() and ds_away.strip():
                        from database import get_gspread_client
                        client = get_gspread_client()
                        if client:
                            try:
                                spreadsheet = client.open_by_key(spreadsheet_id)
                                ws_scan = spreadsheet.worksheet(scanner_sheet_name)
                                
                                new_scan_row = [
                                    ds_season, ds_league, ds_date, ds_home.strip(), ds_away.strip(),
                                    ds_bh, ds_bd, ds_ba
                                ]
                                for obm in overseas_bookmakers:
                                    oh, od, oa = ds_overseas_inputs.get(obm, (0.0, 0.0, 0.0))
                                    new_scan_row.extend([oh, od, oa])

                                all_data = ws_scan.get_all_values()
                                target_row_idx = None
                                
                                if len(all_data) > 1:
                                    for r_i, row in enumerate(all_data[1:], start=2):
                                        if len(row) >= 5:
                                            r_home = str(row[3]).strip()
                                            r_away = str(row[4]).strip()
                                            if r_home == ds_home.strip() and r_away == ds_away.strip():
                                                target_row_idx = r_i
                                                break
                                
                                if target_row_idx:
                                    ws_scan.update(f"A{target_row_idx}:AF{target_row_idx}", [new_scan_row], value_input_option="USER_ENTERED")
                                    import time
                                    time.sleep(0.3)
                                    st.cache_data.clear()
                                    st.success(f"🔄 [{ds_home} vs {ds_away}] 기존 경기의 배당이 최신 데이터로 성공적으로 덮어쓰기(수정)되었습니다!")
                                else:
                                    ws_scan.append_row(new_scan_row, value_input_option="USER_ENTERED")
                                    import time
                                    time.sleep(0.3)
                                    st.cache_data.clear()
                                    st.success(f"🎉 [{ds_home} vs {ds_away}] 경기가 `라운드스캔` 시트에 신규 저장되었습니다!")
                                
                                st.rerun()
                            except Exception as e:
                                st.error(f"저장 실패: {e}")
                    else:
                        st.warning("홈팀명과 원정팀명을 입력해 주세요.")
            
            with col_del_btn:
                if st.button("🗑️ [라운드스캔] 최근 등록 1경기 삭제", type="secondary", use_container_width=True, key="btn_del_single_scan"):
                    from database import get_gspread_client
                    client = get_gspread_client()
                    if client:
                        try:
                            spreadsheet = client.open_by_key(spreadsheet_id)
                            ws_scan = spreadsheet.worksheet(scanner_sheet_name)
                            all_rows = ws_scan.get_all_values()
                            if len(all_rows) > 1:
                                ws_scan.delete_rows(len(all_rows))
                                import time
                                time.sleep(0.3)
                                st.cache_data.clear()
                                st.success("🗑️ 최근 등록된 마지막 1경기가 삭제되었습니다.")
                                st.rerun()
                            else:
                                st.info("삭제할 데이터가 없습니다.")
                        except Exception as e:
                            st.error(f"삭제 실패: {e}")

    st.markdown("---")

    df_h2h_all_db = load_sheet_data(stats_sheet_name, spreadsheet_id)

    if df_scan_raw.empty:
        st.warning(f"⚠️ `{scanner_sheet_name}` 시트에 스캔할 경기 데이터가 없습니다. 위의 [2단계 분할 입력] 또는 [1경기 직접 등록]을 통해 경기를 등록해 주세요.")
    else:
        ALL_CRITERIA_OPTIONS = ["배트맨"] + overseas_bookmakers + ["🌟 해외 8개사 종합평균"]
        
        cached_dbs = {}
        for bm in bookmakers:
            cached_dbs[bm] = load_sheet_data(bm, spreadsheet_id)

        def count_matched_in_db(df_db, h_val, d_val, a_val):
            if df_db.empty or h_val < 1.01 or d_val < 1.01 or a_val < 1.01:
                return 0, 0, 0, 0
            try:
                cols = list(df_db.columns)
                h_col = next((c for c in cols if any(k in c for k in ["해당_홈", "배당_홈", "홈배당", "홈_승", "H_ODDS"])), None)
                d_col = next((c for c in cols if any(k in c for k in ["해당_무", "배당_무", "무배당", "무승부", "D_ODDS"])), None)
                a_col = next((c for c in cols if any(k in c for k in ["해당_원", "배당_원", "원정배당", "원정_승", "A_ODDS"])), None)
                res_col = next((c for c in cols if any(k in c for k in ["경기결과", "결과", "Result"])), None)

                if not h_col and len(cols) > 14:
                    h_col, d_col, a_col = cols[12], cols[13], cols[14]
                if not res_col:
                    res_col = cols[32] if len(cols) > 32 else cols[-1]

                if not h_col or not d_col or not a_col:
                    return 0, 0, 0, 0

                df_w = df_db.copy()
                df_w["H_num"] = pd.to_numeric(df_w[h_col], errors="coerce").fillna(0.0)
                df_w["D_num"] = pd.to_numeric(df_w[d_col], errors="coerce").fillna(0.0)
                df_w["A_num"] = pd.to_numeric(df_w[a_col], errors="coerce").fillna(0.0)

                cond = (
                    (df_w["H_num"] >= 1.01) & (df_w["D_num"] >= 1.01) & (df_w["A_num"] >= 1.01) &
                    (df_w["H_num"] >= h_val - tol) & (df_w["H_num"] <= h_val + tol) &
                    (df_w["D_num"] >= d_val - tol) & (df_w["D_num"] <= d_val + tol) &
                    (df_w["A_num"] >= a_val - tol) & (df_w["A_num"] <= a_val + tol)
                )
                matched = df_w[cond]
                cnt = len(matched)
                if cnt > 0 and res_col in matched.columns:
                    vc = matched[res_col].value_counts()
                    return cnt, vc.get("홈승", 0), vc.get("무승부", 0), vc.get("원정승", 0)
            except Exception:
                pass
            return 0, 0, 0, 0

        def get_matched_details_in_db(df_db, h_val, d_val, a_val):
            if df_db.empty or h_val < 1.01 or d_val < 1.01 or a_val < 1.01:
                return []
            try:
                cols = list(df_db.columns)
                h_col = next((c for c in cols if any(k in c for k in ["해당_홈", "배당_홈", "홈배당", "홈_승", "H_ODDS"])), None)
                d_col = next((c for c in cols if any(k in c for k in ["해당_무", "배당_무", "무배당", "무승부", "D_ODDS"])), None)
                a_col = next((c for c in cols if any(k in c for k in ["해당_원", "배당_원", "원정배당", "원정_승", "A_ODDS"])), None)
                res_col = next((c for c in cols if any(k in c for k in ["경기결과", "결과", "Result"])), None)
                date_col = next((c for c in cols if any(k in c for k in ["날짜", "경기날짜", "Date"])), None)
                home_col = next((c for c in cols if any(k in c for k in ["홈팀", "Home"])), None)
                away_col = next((c for c in cols if any(k in c for k in ["원정팀", "Away"])), None)

                if not h_col and len(cols) > 14:
                    h_col, d_col, a_col = cols[12], cols[13], cols[14]
                if not res_col:
                    res_col = cols[32] if len(cols) > 32 else cols[-1]

                if not h_col or not d_col or not a_col:
                    return []

                df_w = df_db.copy()
                df_w["H_num"] = pd.to_numeric(df_w[h_col], errors="coerce").fillna(0.0)
                df_w["D_num"] = pd.to_numeric(df_w[d_col], errors="coerce").fillna(0.0)
                df_w["A_num"] = pd.to_numeric(df_w[a_col], errors="coerce").fillna(0.0)

                cond = (
                    (df_w["H_num"] >= 1.01) & (df_w["D_num"] >= 1.01) & (df_w["A_num"] >= 1.01) &
                    (df_w["H_num"] >= h_val - tol) & (df_w["H_num"] <= h_val + tol) &
                    (df_w["D_num"] >= d_val - tol) & (df_w["D_num"] <= d_val + tol) &
                    (df_w["A_num"] >= a_val - tol) & (df_w["A_num"] <= a_val + tol)
                )
                matched = df_w[cond]
                
                details = []
                for _, mr in matched.iterrows():
                    m_date = str(mr[date_col]) if date_col and date_col in mr else "-"
                    m_home = str(mr[home_col]) if home_col and home_col in mr else "-"
                    m_away = str(mr[away_col]) if away_col and away_col in mr else "-"
                    m_res = str(mr[res_col]) if res_col and res_col in mr else "-"
                    m_odds = f"{mr['H_num']} / {mr['D_num']} / {mr['A_num']}"
                    details.append({
                        "날짜": m_date, "매치업": f"{m_home} vs {m_away}",
                        "당시배당(홈/무/원)": m_odds, "경기결과": m_res
                    })
                return details
            except Exception:
                return []

        matching_counts_summary = {crit: 0 for crit in ALL_CRITERIA_OPTIONS}
        detailed_match_records = {crit: [] for crit in ALL_CRITERIA_OPTIONS}
        
        for _, r in df_scan_raw.iterrows():
            r_home = str(r.get("홈팀", "")).strip()
            r_away = str(r.get("원정팀", "")).strip()
            r_lg = str(r.get("리그명", "")).strip()
            match_name_str = f"[{r_lg}] {r_home} vs {r_away}"

            bh = safe_flt(r.get("배트맨_홈"), 0.0)
            bd = safe_flt(r.get("배트맨_무"), 0.0)
            ba = safe_flt(r.get("배트맨_원"), 0.0)
            if bh >= 1.01 and bd >= 1.01 and ba >= 1.01:
                dets = get_matched_details_in_db(cached_dbs.get("배트맨", pd.DataFrame()), bh, bd, ba)
                if dets:
                    matching_counts_summary["배트맨"] += len(dets)
                    for d in dets:
                        d["대상경기"] = match_name_str
                        detailed_match_records["배트맨"].append(d)

            valid_oh, valid_od, valid_oa = [], [], []
            for obm in overseas_bookmakers:
                oh = safe_flt(r.get(f"{obm}_홈"), 0.0)
                od = safe_flt(r.get(f"{obm}_무"), 0.0)
                oa = safe_flt(r.get(f"{obm}_원"), 0.0)
                if oh >= 1.01 and od >= 1.01 and oa >= 1.01:
                    valid_oh.append(oh)
                    valid_od.append(od)
                    valid_oa.append(oa)
                    dets = get_matched_details_in_db(cached_dbs.get(obm, pd.DataFrame()), oh, od, oa)
                    if dets:
                        matching_counts_summary[obm] += len(dets)
                        for d in dets:
                            d["대상경기"] = match_name_str
                            detailed_match_records[obm].append(d)

            if valid_oh:
                avg_oh = round(float(np.mean(valid_oh)), 2)
                avg_od = round(float(np.mean(valid_od)), 2)
                avg_oa = round(float(np.mean(valid_oa)), 2)
                if avg_oh >= 1.01 and avg_od >= 1.01 and avg_oa >= 1.01:
                    for obm in overseas_bookmakers:
                        dets = get_matched_details_in_db(cached_dbs.get(obm, pd.DataFrame()), avg_oh, avg_od, avg_oa)
                        if dets:
                            matching_counts_summary["🌟 해외 8개사 종합평균"] += len(dets)
                            for d in dets:
                                d["대상경기"] = match_name_str
                                detailed_match_records["🌟 해외 8개사 종합평균"].append(d)

        st.markdown("#### 📊 이번 라운드 경기들의 업체별 과거 동일배당 매칭 데이터 현황")
        
        badges = []
        for crit in ALL_CRITERIA_OPTIONS:
            cnt_val = matching_counts_summary[crit]
            if cnt_val > 0:
                color_bg = "#eff6ff"
                color_border = "#3b82f6"
                label_color = "#1e3a8a"
                cnt_color = "#2563eb"
            else:
                color_bg = "#f1f5f9"
                color_border = "#cbd5e1"
                label_color = "#334155"
                cnt_color = "#64748b"
                
            badges.append(
                f"<div style='background-color: {color_bg}; border: 1px solid {color_border}; border-radius: 6px; padding: 6px 12px; font-size: 13px; color: {label_color}; white-space: nowrap; display: inline-block;'>"
                f"<b style='color: {label_color};'>{crit}</b>: <span style='color: {cnt_color}; font-weight: bold;'>{cnt_val}건</span></div>"
            )
        
        badge_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;'>" + "".join(badges) + "</div>"
        st.markdown(badge_html, unsafe_allow_html=True)

        with st.expander("🔍 [업체별 동일배당 매칭 상세 내역 검증기] (어떤 과거 경기가 카운팅되었는지 확인하기)", expanded=False):
            sel_inspect_bm = st.selectbox("상세 내역을 조회할 업체 선택", ALL_CRITERIA_OPTIONS, key="sel_inspect_bm_box")
            bm_records = detailed_match_records.get(sel_inspect_bm, [])
            
            if bm_records:
                st.success(f"📌 **[{sel_inspect_bm}]** 기준 총 **{len(bm_records)}건**의 과거 매칭 경기 내역입니다.")
                st.dataframe(pd.DataFrame(bm_records), use_container_width=True, hide_index=True)
            else:
                st.info(f"💡 **[{sel_inspect_bm}]** 시트에 이번 라운드 경기들과 일치하는 과거 동일배당 매칭 내역이 없습니다. (0건)")

        c_crit1, c_crit2 = st.columns([2, 3])
        with c_crit1:
            selected_radar_criteria = st.selectbox(
                "🎯 1, 2번 레이더 기준 북메이커(배당) 선택",
                ALL_CRITERIA_OPTIONS,
                index=0,
                key="sel_radar_criteria"
            )
        with c_crit2:
            st.caption(f"💡 현재 **[{selected_radar_criteria}]** 배당 및 과거 시트 데이터를 기준으로 고승률픽/폭탄주의픽을 자동 계산합니다.")

        def run_round_scan(criteria_name):
            scanned_list = []
            
            for idx, r in df_scan_raw.iterrows():
                season = str(r.get("시즌", "25-26"))
                league = str(r.get("리그명", "PL"))
                m_date = str(r.get("경기날짜", "-"))
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

                match_cnt, win_prob, draw_prob, lose_prob = 0, 0.0, 0.0, 0.0
                crit_h, crit_d, crit_a = 0.0, 0.0, 0.0

                if criteria_name == "배트맨":
                    crit_h, crit_d, crit_a = bh, bd, ba
                    if bh >= 1.01 and bd >= 1.01 and ba >= 1.01:
                        match_cnt, hw, dr, aw = count_matched_in_db(cached_dbs.get("배트맨", pd.DataFrame()), bh, bd, ba)
                        if match_cnt > 0:
                            win_prob = round((hw / match_cnt) * 100, 1)
                            draw_prob = round((dr / match_cnt) * 100, 1)
                            lose_prob = round((aw / match_cnt) * 100, 1)
                elif criteria_name in overseas_bookmakers:
                    crit_h, crit_d, crit_a = all_bms_odds.get(criteria_name, (0.0, 0.0, 0.0))
                    if crit_h >= 1.01 and crit_d >= 1.01 and crit_a >= 1.01:
                        match_cnt, hw, dr, aw = count_matched_in_db(cached_dbs.get(criteria_name, pd.DataFrame()), crit_h, crit_d, crit_a)
                        if match_cnt > 0:
                            win_prob = round((hw / match_cnt) * 100, 1)
                            draw_prob = round((dr / match_cnt) * 100, 1)
                            lose_prob = round((aw / match_cnt) * 100, 1)
                elif criteria_name == "🌟 해외 8개사 종합평균":
                    crit_h, crit_d, crit_a = avg_oh, avg_od, avg_oa
                    if avg_oh >= 1.01 and avg_od >= 1.01 and avg_oa >= 1.01:
                        tot_m, tot_hw, tot_dr, tot_aw = 0, 0, 0, 0
                        for obm in overseas_bookmakers:
                            c_m, c_hw, c_dr, c_aw = count_matched_in_db(cached_dbs.get(obm, pd.DataFrame()), avg_oh, avg_od, avg_oa)
                            tot_m += c_m
                            tot_hw += c_hw
                            tot_dr += c_dr
                            tot_aw += c_aw
                        match_cnt = tot_m
                        if match_cnt > 0:
                            win_prob = round((tot_hw / match_cnt) * 100, 1)
                            draw_prob = round((tot_dr / match_cnt) * 100, 1)
                            lose_prob = round((tot_aw / match_cnt) * 100, 1)

                h2h_cnt, h2h_hw, h2h_dr, h2h_aw = 0, 0, 0, 0
                if not df_h2h_all_db.empty and "홈팀" in df_h2h_all_db.columns:
                    cond_h2h = ((df_h2h_all_db["홈팀"] == home) & (df_h2h_all_db["원정팀"] == away)) | \
                               ((df_h2h_all_db["홈팀"] == away) & (df_h2h_all_db["원정팀"] == home))
                    m_h2h = df_h2h_all_db[cond_h2h]
                    h2h_cnt = len(m_h2h)
                    for _, hr in m_h2h.iterrows():
                        hg = safe_flt(hr.get("전반득점_홈"), 0.0) + safe_flt(hr.get("후반득점_홈"), 0.0)
                        ag = safe_flt(hr.get("전반득점_원"), 0.0) + safe_flt(hr.get("후반득점_원", 0.0), 0.0)
                        if hr["홈팀"] == home:
                            if hg > ag: h2h_hw += 1
                            elif hg == ag: h2h_dr += 1
                            else: h2h_aw += 1
                        else:
                            if ag > hg: h2h_hw += 1
                            elif ag == hg: h2h_dr += 1
                            else: h2h_aw += 1

                diff_h = round(bh - avg_oh, 2) if (bh > 0 and avg_oh > 0) else 0.0
                tags = []

                if match_cnt >= 2 and (win_prob >= 70.0 or lose_prob >= 70.0):
                    tags.append(f"🔥 고승률({selected_radar_criteria})")
                if crit_h > 0 and crit_a > 0 and crit_h < crit_a and (draw_prob + lose_prob) >= 55.0 and match_cnt >= 2:
                    tags.append(f"⚡ 역배폭탄({selected_radar_criteria})")
                if diff_h >= 0.05:
                    tags.append("💰 배당 메리트")
                if h2h_cnt >= 2 and (h2h_hw == h2h_cnt or h2h_aw == h2h_cnt):
                    tags.append("⚔️ 천적 극상성")

                if not tags:
                    tags.append("일반 분석")

                scanned_list.append({
                    "season": season, "league": league, "date": m_date,
                    "home": home, "away": away,
                    "batman_odds": (bh, bd, ba),
                    "crit_odds": (crit_h, crit_d, crit_a),
                    "overseas_avg": (avg_oh, avg_od, avg_oa),
                    "all_odds": all_bms_odds,
                    "match_cnt": match_cnt,
                    "win_prob": win_prob, "draw_prob": draw_prob, "lose_prob": lose_prob,
                    "h2h_cnt": h2h_cnt, "h2h_record": f"{h2h_cnt}전 {h2h_hw}승 {h2h_dr}무 {h2h_aw}패",
                    "diff_h": diff_h,
                    "tags": tags
                })

            return scanned_list

        scanned_results = run_round_scan(selected_radar_criteria)

        col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
        f_all = col_f1.button("🌐 전체 경기 보기", use_container_width=True)
        f_high = col_f2.button(f"🔥 [고승률 주력픽 TOP 5]", use_container_width=True)
        f_upset = col_f3.button(f"⚡ [역배/무 폭탄주의 TOP 5]", use_container_width=True)
        f_value = col_f4.button("💰 [배당 메리트 TOP 5]", use_container_width=True)
        f_h2h = col_f5.button("⚔️ [천적 극상성 TOP 5]", use_container_width=True)

        display_list = scanned_results
        filter_title = "📋 이번 라운드 전체 스캔 리스트"
        is_top5_view = False

        if f_high:
            display_list = [m for m in scanned_results if any("🔥 고승률" in t for t in m["tags"])]
            display_list = sorted(display_list, key=lambda x: max(x["win_prob"], x["lose_prob"]), reverse=True)[:5]
            filter_title = f"🔥 [{selected_radar_criteria} 기준 고승률 / 주력픽 TOP 5] 추천 경기"
            is_top5_view = True
        elif f_upset:
            display_list = [m for m in scanned_results if any("⚡ 역배폭탄" in t for t in m["tags"])]
            display_list = sorted(display_list, key=lambda x: (x["draw_prob"] + x["lose_prob"]), reverse=True)[:5]
            filter_title = f"⚡ [{selected_radar_criteria} 기준 역배 / 무승부 폭탄 주의픽 TOP 5] 추천 경기"
            is_top5_view = True
        elif f_value:
            display_list = [m for m in scanned_results if "💰 배당 메리트" in m["tags"]]
            display_list = sorted(display_list, key=lambda x: x["diff_h"], reverse=True)[:5]
            filter_title = "💰 [해외 대비 가치배당 / 메리트픽 TOP 5] 추천 경기"
            is_top5_view = True
        elif f_h2h:
            display_list = [m for m in scanned_results if "⚔️ 천적 극상성" in m["tags"]]
            display_list = sorted(display_list, key=lambda x: x["h2h_cnt"], reverse=True)[:5]
            filter_title = "⚔️ [상대전적 극상성 / 천적픽 TOP 5] 추천 경기"
            is_top5_view = True

        st.markdown("---")

        if is_top5_view:
            st.subheader(f"{filter_title} (총 {len(display_list)}경기)")
            if not display_list:
                st.info(f"💡 선택하신 조건({selected_radar_criteria})에 일치하는 추천 경기가 없습니다. (과거 매칭 2건 이상 및 승률/역배 기준 미충족)")
            else:
                for i, item in enumerate(display_list):
                    with st.container(border=True):
                        c_head1, c_head2, c_head3 = st.columns([2, 3, 2])
                        
                        with c_head1:
                            tag_badges = " ".join([f"`{t}`" for t in item["tags"]])
                            st.markdown(f"### #{i+1} {item['home']} vs {item['away']}")
                            st.caption(f"🏆 {item['league']} | 📅 {item['date']} | {tag_badges}")

                        with c_head2:
                            bh, bd, ba = item["batman_odds"]
                            oh, od, oa = item["overseas_avg"]
                            ch, cd, ca = item["crit_odds"]
                            diff_str = f"+{item['diff_h']}" if item['diff_h'] > 0 else f"{item['diff_h']}"
                            
                            st.markdown(f"**🏢 배트맨 배당:** `{bh}` / `{bd}` / `{ba}` &nbsp;|&nbsp; **해외 평균:** `{oh}` / `{od}` / `{oa}` (편차: `{diff_str}`)")
                            st.markdown(f"🎯 **[{selected_radar_criteria} 동일배당 ({ch}/{cd}/{ca}) 승률 (과거 {item['match_cnt']}건)]**")
                            st.markdown(f"👉 홈승 **{item['win_prob']}%** / 무승부 **{item['draw_prob']}%** / 원정 **{item['lose_prob']}%**")
                            st.caption(f"⚔️ **상대전적:** {item['h2h_record']}")

                        with c_head3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button(f"👉 이 경기 즉시 분석/도표 생성", key=f"btn_scan_top5_{i}", type="primary", use_container_width=True):
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
                                st.session_state.inj_filter_team = item["home"]
                                st.rerun()

        else:
            st.subheader(f"📋 이번 라운드 전체 등록 경기 빠른 검색 & 원클릭 상세 분석 (총 {len(scanned_results)}경기)")

            f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 1])
            all_leagues = ["전체"] + sorted(list(set([m["league"] for m in scanned_results if m.get("league")])))
            with f_col1:
                selected_league = st.selectbox("🏆 리그 필터", all_leagues, key="filter_scan_league")
            with f_col2:
                search_team = st.text_input("🔍 팀명 검색 (홈/원정)", "", placeholder="예: 아스널, 맨시티", key="filter_scan_team")
            with f_col3:
                sort_option = st.selectbox("🔢 정렬 기준", ["등록순 (기본)", "배트맨 홈배당 낮은순", "배트맨 홈배당 높은순"], key="filter_scan_sort")

            filtered_matches = scanned_results.copy()
            if selected_league != "전체":
                filtered_matches = [m for m in filtered_matches if m["league"] == selected_league]
            if search_team.strip():
                t_term = search_team.strip().lower()
                filtered_matches = [m for m in filtered_matches if (t_term in m["home"].lower() or t_term in m["away"].lower())]
            
            if sort_option == "배트맨 홈배당 낮은순":
                filtered_matches = sorted(filtered_matches, key=lambda x: x["batman_odds"][0])
            elif sort_option == "배트맨 홈배당 높은순":
                filtered_matches = sorted(filtered_matches, key=lambda x: x["batman_odds"][0], reverse=True)

            st.caption(f"💡 검색 결과: 총 **{len(filtered_matches)}**경기 (전체 {len(scanned_results)}경기 중)")

            if not filtered_matches:
                st.info("검색 조건에 일치하는 경기가 없습니다.")
            else:
                summary_rows = []
                for m in filtered_matches:
                    bh, bd, ba = m["batman_odds"]
                    summary_rows.append({
                        "날짜": m["date"], "리그": m["league"], "홈팀": m["home"], "원정팀": m["away"],
                        "배트맨(홈)": bh, "배트맨(무)": bd, "배트맨(원)": ba, "주요 레이더": ", ".join(m["tags"])
                    })
                
                st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, height=min(240, 36 * (len(summary_rows) + 1)), hide_index=True)
                st.markdown("#### 👉 상세 분석할 경기 선택")

                match_options = []
                for idx, m in enumerate(filtered_matches):
                    bh, bd, ba = m["batman_odds"]
                    match_options.append((f"[{m['league']}] {m['date']} {m['home']} vs {m['away']}", idx))

                selected_label = st.selectbox("분석할 경기를 목록에서 선택하세요", options=[opt[0] for opt in match_options], key="scanner_match_selector")
                selected_match_idx = next(opt[1] for opt in match_options if opt[0] == selected_label)
                target_item = filtered_matches[selected_match_idx]

                with st.container():
                    bh, bd, ba = target_item["batman_odds"]
                    oh, od, oa = target_item["overseas_avg"]
                    ch, cd, ca = target_item["crit_odds"]
                    st.markdown(f"""
                    <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; margin-top: 10px; margin-bottom: 12px; color: #0f172a;">
                        <h4 style="margin: 0; color: #0f172a;">📌 [{target_item['league']}] {target_item['home']} (홈) vs {target_item['away']} (원정)</h4>
                        <p style="margin: 6px 0 0 0; color: #334155; font-size: 13px;">
                            배트맨 배당: <b style="color: #dc2626;">승 {bh}</b> | <b style="color: #059669;">무 {bd}</b> | <b style="color: #2563eb;">패 {ba}</b> &nbsp;|&nbsp; 
                            해외 평균: <b>{oh} / {od} / {oa}</b><br>
                            🎯 <b>{selected_radar_criteria} 동일배당 ({ch}/{cd}/{ca}) 승률 (과거 {target_item['match_cnt']}건):</b> 
                            홈 <b>{target_item['win_prob']}%</b> / 무 <b>{target_item['draw_prob']}%</b> / 원 <b>{target_item['lose_prob']}%</b>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button("👉 이 경기 즉시 분석/도표 생성 (탭 3, 5, 6 전송)", key=f"btn_send_fast_{selected_match_idx}", type="primary", use_container_width=True):
                        st.session_state.selected_scan_match = target_item
                        st.session_state.t2_target_league = target_item["league"]
                        st.session_state.t2_home_team = target_item["home"]
                        st.session_state.t2_away_team = target_item["away"]
                        for bm in bookmakers:
                            h_val, d_val, a_val = target_item["all_odds"].get(bm, (0.0, 0.0, 0.0))
                            st.session_state[f"t2_{bm}_h"] = float(h_val)
                            st.session_state[f"t2_{bm}_d"] = float(d_val)
                            st.session_state[f"t2_{bm}_a"] = float(a_val)
                        st.session_state.sel_h2h_home = target_item["home"]
                        st.session_state.sel_h2h_away = target_item["away"]
                        st.session_state.inj_filter_team = target_item["home"]
                        st.success(f"🎯 [{target_item['home']} vs {target_item['away']}] 경기가 분석 탭으로 전송되었습니다! (상단 탭 3, 5, 6 확인)")
                        st.rerun()
