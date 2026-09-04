import streamlit as st
import pandas as pd
from database import save_match_data_to_sheets

def render_tab1(spreadsheet_id, bookmakers):
    st.subheader("📝 경기 데이터 입력 & 저장")
    
    input_mode = st.radio(
        "입력 모드 선택",
        ["🚀 2단계 분할 입력 (와이즈토토 먼저 모아서 ➔ 해외 배당 순차 입력)", "⚡ 기존 일괄 입력 (한 경기씩 모든 데이터 작성)"],
        horizontal=True
    )
    st.markdown("---")

    if "2단계 분할 입력" in input_mode:
        col_step1, col_step2 = st.columns([1, 1], gap="large")

        with col_step1:
            st.subheader("1️⃣ [1단계] 와이즈토토 배트맨 경기 등록")
            st.caption("와이즈토토를 보면서 배트맨 배당과 경기 정보를 등록해 대기열에 담아둡니다.")

            with st.container(border=True):
                c_q1, c_q2, c_q3 = st.columns(3)
                q_season = c_q1.text_input("시즌", value="25-26", key="q_in_season")
                q_league = c_q2.text_input("리그명", value="PL", key="q_in_league")
                q_date = c_q3.text_input("경기 날짜", value="25.08.16", key="q_in_date")

                c_qt1, c_qt2 = st.columns(2)
                q_home = c_qt1.text_input("홈팀", value="", placeholder="예: 리버풀", key="q_in_home")
                q_away = c_qt2.text_input("원정팀", value="", placeholder="예: 본머스", key="q_in_away")

                st.markdown("**🏢 [1] 배트맨 최종 배당 입력**")
                qb_h, qb_d, qb_a = st.columns(3)
                q_bh_val = qb_h.number_input("홈", value=0.0, step=0.01, min_value=0.0, key="q_in_bh")
                q_bd_val = qb_d.number_input("무", value=0.0, step=0.01, min_value=0.0, key="q_in_bd")
                q_ba_val = qb_a.number_input("원정", value=0.0, step=0.01, min_value=0.0, key="q_in_ba")

                st.markdown("**🌐 대상 해외 북메이커 선택**")
                selected_overseas = []
                overseas_bms = [b for b in bookmakers if b != "배트맨"]
                cols_chk = st.columns(4)
                for idx, obm in enumerate(overseas_bms):
                    with cols_chk[idx % 4]:
                        if st.checkbox(obm.upper(), value=True, key=f"chk_{obm}"):
                            selected_overseas.append(obm)

                if st.button("➕ 대기열에 경기 등록 (와이즈토토 계속 입력)", type="primary", use_container_width=True):
                    if q_home.strip() and q_away.strip():
                        st.session_state.match_queue.append({
                            "season": q_season, "league": q_league, "date": q_date,
                            "home": q_home.strip(), "away": q_away.strip(),
                            "batman_odds": (q_bh_val, q_bd_val, q_ba_val),
                            "target_bms": selected_overseas
                        })
                        st.success(f"🎉 [{q_home} vs {q_away}] 경기가 대기열에 추가되었습니다! (총 {len(st.session_state.match_queue)}경기 대기 중)")
                    else:
                        st.warning("홈팀과 원정팀명을 입력해 주세요.")

            if st.session_state.match_queue:
                st.markdown("##### 📋 현재 대기열에 등록된 경기 목록")
                q_preview = []
                for i, m in enumerate(st.session_state.match_queue):
                    status = "👉 [작성 차례]" if i == st.session_state.current_queue_idx else ("⏳ [대기 중]" if i > st.session_state.current_queue_idx else "✅ [완료]")
                    q_preview.append({
                        "순번": i + 1, "상태": status,
                        "경기": f"{m['home']} vs {m['away']}", "리그/날짜": f"{m['league']} ({m['date']})",
                        "배트맨 배당": f"{m['batman_odds'][0]} / {m['batman_odds'][1]} / {m['batman_odds'][2]}",
                        "대상 해외사": f"{len(m['target_bms'])}개사"
                    })
                st.dataframe(pd.DataFrame(q_preview), use_container_width=True, hide_index=True)

                with st.container(border=True):
                    st.markdown("##### ✏️ 대기열 특정 경기 내용 수정하기")
                    q_indices = [f"#{i+1} : {m['home']} vs {m['away']}" for i, m in enumerate(st.session_state.match_queue)]
                    sel_q_str = st.selectbox("수정할 대기 경기 선택", q_indices, key="sel_queue_to_edit")
                    sel_q_idx = int(sel_q_str.split(":")[0].replace("#", "").strip()) - 1
                    target_q_item = st.session_state.match_queue[sel_q_idx]

                    e_qh = st.text_input("홈팀명 수정", value=target_q_item["home"], key="edit_qh")
                    e_qa = st.text_input("원정팀명 수정", value=target_q_item["away"], key="edit_qa")
                    e_ql = st.text_input("리그명 수정", value=target_q_item["league"], key="edit_ql")
                    e_qd = st.text_input("날짜 수정", value=target_q_item["date"], key="edit_qd")
                    
                    eb1, eb2, eb3 = st.columns(3)
                    e_bh = eb1.number_input("배트맨 홈", value=float(target_q_item["batman_odds"][0]), step=0.01, key="edit_qbh")
                    e_bd = eb2.number_input("배트맨 무", value=float(target_q_item["batman_odds"][1]), step=0.01, key="edit_qbd")
                    e_ba = eb3.number_input("배트맨 원정", value=float(target_q_item["batman_odds"][2]), step=0.01, key="edit_qba")

                    if st.button("🔄 선택한 대기 경기 내용 갱신", type="primary", use_container_width=True):
                        st.session_state.match_queue[sel_q_idx]["home"] = e_qh.strip()
                        st.session_state.match_queue[sel_q_idx]["away"] = e_qa.strip()
                        st.session_state.match_queue[sel_q_idx]["league"] = e_ql.strip()
                        st.session_state.match_queue[sel_q_idx]["date"] = e_qd.strip()
                        st.session_state.match_queue[sel_q_idx]["batman_odds"] = (e_bh, e_bd, e_ba)
                        st.success(f"🎉 대기열 #{sel_q_idx + 1} 경기 정보가 성공적으로 수정되었습니다!")
                        st.rerun()

                if st.button("🗑️ 대기열 전체 비우기"):
                    st.session_state.match_queue = []
                    st.session_state.current_queue_idx = 0
                    st.rerun()

        with col_step2:
            st.subheader("2️⃣ [2단계] 해외 배당 및 경기내용 순차 입력")
            queue_len = len(st.session_state.match_queue)
            cur_idx = st.session_state.current_queue_idx

            if queue_len == 0:
                st.info("💡 1단계에서 경기를 먼저 등록하시면 여기에 해외 배당 입력창이 순서대로 나타납니다.")
            elif cur_idx >= queue_len:
                st.success(f"🎉 대기열에 등록된 모든 경기(총 {queue_len}경기) 저장이 완료되었습니다!")
                if st.button("🔄 새 대기열 시작하기"):
                    st.session_state.match_queue = []
                    st.session_state.current_queue_idx = 0
                    st.rerun()
            else:
                cur_match = st.session_state.match_queue[cur_idx] if cur_idx < queue_len else None
                if not cur_match:
                    st.session_state.current_queue_idx = 0
                    st.rerun()
                
                next_match = st.session_state.match_queue[cur_idx + 1] if cur_idx + 1 < queue_len else None

                st.markdown(f"""
                <div style="background-color: #1e3a8a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <div style="font-size: 13px; color: #93c5fd;">[진행 중: {cur_idx + 1} / {queue_len} 번째 경기]</div>
                    <div style="font-size: 18px; font-weight: bold; margin-top: 4px;">👉 {cur_match['home']} vs {cur_match['away']} ({cur_match['league']})</div>
                    <div style="font-size: 13px; margin-top: 4px;">배트맨 배당: {cur_match['batman_odds'][0]} / {cur_match['batman_odds'][1]} / {cur_match['batman_odds'][2]} | 날짜: {cur_match['date']}</div>
                </div>
                """, unsafe_allow_html=True)

                if next_match:
                    st.caption(f"⏭️ **다음 대기 경기:** [{next_match['home']} vs {next_match['away']}] ({next_match['league']})")
                else:
                    st.caption("🏁 이번 경기가 대기열의 마지막 경기입니다.")

                st.markdown("##### 🏢 해외 배당 입력")
                q_odds_inputs = {"배트맨": cur_match["batman_odds"]}
                target_bms = cur_match["target_bms"]
                if target_bms:
                    for i in range(0, len(target_bms), 2):
                        cols_obm = st.columns(2)
                        for j in range(2):
                            idx = i + j
                            if idx < len(target_bms):
                                bm = target_bms[idx]
                                with cols_obm[j]:
                                    with st.container(border=True):
                                        st.markdown(f"**🏢 {bm.upper()}**")
                                        oh, od, oa = st.columns(3)
                                        h_val = oh.number_input("홈", value=0.0, step=0.01, min_value=0.0, key=f"q_{cur_idx}_{bm}_h")
                                        d_val = od.number_input("무", value=0.0, step=0.01, min_value=0.0, key=f"q_{cur_idx}_{bm}_d")
                                        a_val = oa.number_input("원정", value=0.0, step=0.01, min_value=0.0, key=f"q_{cur_idx}_{bm}_a")
                                        q_odds_inputs[bm] = (h_val, d_val, a_val)

                st.markdown("##### ⚽ 인게임 스탯 (10번 경기내용 탭용)")
                with st.expander("⚽ 득점 & 포메이션 & 세부 스탯", expanded=True):
                    c_g1, c_g2, c_g3, c_g4 = st.columns(4)
                    q_home_1h = c_g1.number_input("홈 전반 득점", min_value=0, value=0, key=f"q_{cur_idx}_home_1h")
                    q_home_2h = c_g2.number_input("홈 후반 득점", min_value=0, value=0, key=f"q_{cur_idx}_home_2h")
                    q_away_1h = c_g3.number_input("원정 전반 득점", min_value=0, value=0, key=f"q_{cur_idx}_away_1h")
                    q_away_2h = c_g4.number_input("원정 후반 득점", min_value=0, value=0, key=f"q_{cur_idx}_away_2h")
                    
                    c_tac1, c_tac2 = st.columns(2)
                    q_home_tac = c_tac1.text_input("홈팀 전술(포메이션)", value="4-2-3-1", key=f"q_{cur_idx}_home_tac")
                    q_away_tac = c_tac2.text_input("원정팀 전술(포메이션)", value="4-3-3", key=f"q_{cur_idx}_away_tac")

                    c_st1, c_st2, c_st3, c_st4 = st.columns(4)
                    q_home_shots = c_st1.number_input("홈 슈팅", min_value=0, value=0, key=f"q_{cur_idx}_home_shots")
                    q_away_shots = c_st2.number_input("원정 슈팅", min_value=0, value=0, key=f"q_{cur_idx}_away_shots")
                    q_home_sot = c_st3.number_input("홈 유효슈팅", min_value=0, value=0, key=f"q_{cur_idx}_home_sot")
                    q_away_sot = c_st4.number_input("원정 유효슈팅", min_value=0, value=0, key=f"q_{cur_idx}_away_sot")

                    c_ps1, c_ps2, c_ps3, c_ps4 = st.columns(4)
                    q_home_poss = c_ps1.number_input("홈 점유율 (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.1, key=f"q_{cur_idx}_home_poss")
                    q_away_poss = c_ps2.number_input("원정 점유율 (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.1, key=f"q_{cur_idx}_away_poss")
                    q_home_pass = c_ps3.number_input("홈 패스성공률 (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1, key=f"q_{cur_idx}_home_pass")
                    q_away_pass = c_ps4.number_input("원정 패스성공률 (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1, key=f"q_{cur_idx}_away_pass")

                    c_cd1, c_cd2, c_cd3, c_cd4, c_xg1, c_xg2 = st.columns(6)
                    q_home_yc = c_cd1.number_input("홈 경고", min_value=0, value=0, key=f"q_{cur_idx}_home_yc")
                    q_away_yc = c_cd2.number_input("원정 경고", min_value=0, value=0, key=f"q_{cur_idx}_home_yc")
                    q_home_rc = c_cd3.number_input("홈 퇴장", min_value=0, value=0, key=f"q_{cur_idx}_home_rc")
                    q_away_rc = c_cd4.number_input("원정 퇴장", min_value=0, value=0, key=f"q_{cur_idx}_home_rc")
                    q_home_xg = c_xg1.number_input("홈 xG", min_value=0.0, value=0.00, step=0.01, key=f"q_{cur_idx}_home_xg")
                    q_away_xg = c_xg2.number_input("원정 xG", min_value=0.0, value=0.00, step=0.01, key=f"q_{cur_idx}_away_xg")

                q_stats_dict = {
                    "home_1h": q_home_1h, "home_2h": q_home_2h, "away_1h": q_away_1h, "away_2h": q_away_2h,
                    "home_tac": q_home_tac, "away_tac": q_away_tac,
                    "home_shots": q_home_shots, "away_shots": q_away_shots,
                    "home_sot": q_home_sot, "away_sot": q_away_sot,
                    "home_poss": q_home_poss, "away_poss": q_away_poss,
                    "home_pass": q_home_pass, "away_pass": q_away_pass,
                    "home_yc": q_home_yc, "away_yc": q_away_yc,
                    "home_rc": q_home_rc, "away_rc": q_away_rc,
                    "home_xg": q_home_xg, "away_xg": q_away_xg
                }

                if st.button("💾 구글 시트 저장 및 다음 경기로 넘어가기 ➔", type="primary", use_container_width=True):
                    with st.spinner("구글 시트에 저장 중..."):
                        success, msg = save_match_data_to_sheets(
                            spreadsheet_id, bookmakers, "경기내용", cur_match, q_odds_inputs, q_stats_dict
                        )
                        if success:
                            st.session_state.current_queue_idx += 1
                            st.cache_data.clear()
                            st.success(f"🎉 [{cur_match['home']} vs {cur_match['away']}] 저장 완료!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"저장 실패: {msg}")

    else:
        st.subheader("1️⃣ 경기 기본 정보 & 팀명")
        c_m1, c_m2, c_m3 = st.columns(3)
        season = c_m1.text_input("시즌", value="25-26", key="in_season")
        league = c_m2.text_input("리그명", value="PL", key="in_league")
        match_date = c_m3.text_input("경기 날짜", value="25.08.16", key="in_match_date")
        
        c_t1, c_t2 = st.columns(2)
        home_team = c_t1.text_input("홈팀", value="", placeholder="예: 리버풀", key="in_home_team")
        away_team = c_t2.text_input("원정팀", value="", placeholder="예: 본머스", key="in_away_team")

        st.markdown("---")
        st.subheader("2️⃣ 9대 북메이커 최종 배당 입력 (미제공 시 0으로 설정)")
        
        odds_inputs_t1 = {}
        for i in range(0, len(bookmakers), 3):
            cols = st.columns(3)
            for j in range(3):
                idx = i + j
                if idx < len(bookmakers):
                    bm = bookmakers[idx]
                    with cols[j]:
                        with st.container(border=True):
                            st.markdown(f"**🏢 [{idx+1}] {bm.upper()}**")
                            oh, od, oa = st.columns(3)
                            h_val = oh.number_input("홈", value=0.0, step=0.01, min_value=0.0, key=f"t1_{bm}_h")
                            d_val = od.number_input("무", value=0.0, step=0.01, min_value=0.0, key=f"t1_{bm}_d")
                            a_val = oa.number_input("원정", value=0.0, step=0.01, min_value=0.0, key=f"t1_{bm}_a")
                            odds_inputs_t1[bm] = (h_val, d_val, a_val)

        st.markdown("---")
        st.subheader("3️⃣ 인게임 세부 경기내용 스탯 입력 (10번 '경기내용' 탭용)")
        
        with st.expander("⚽ 전/후반 득점 및 포메이션(전술)", expanded=True):
            c_g1, c_g2, c_g3, c_g4 = st.columns(4)
            home_1h = c_g1.number_input("홈 전반 득점", min_value=0, value=0, key="in_home_1h")
            home_2h = c_g2.number_input("홈 후반 득점", min_value=0, value=0, key="in_home_2h")
            away_1h = c_g3.number_input("원정 전반 득점", min_value=0, value=0, key="in_away_1h")
            away_2h = c_g4.number_input("원정 후반 득점", min_value=0, value=0, key="in_away_2h")
            
            c_tac1, c_tac2 = st.columns(2)
            home_tac = c_tac1.text_input("홈팀 전술(포메이션)", value="4-2-3-1", key="in_home_tac")
            away_tac = c_tac2.text_input("원정팀 전술(포메이션)", value="4-3-3", key="in_away_tac")

        with st.expander("📊 슈팅 / 점유율 / 패스 / 파울 / xG 세부 스탯", expanded=True):
            c_st1, c_st2, c_st3, c_st4 = st.columns(4)
            home_shots = c_st1.number_input("홈 슈팅", min_value=0, value=0, key="in_home_shots")
            away_shots = c_st2.number_input("원정 슈팅", min_value=0, value=0, key="in_away_shots")
            home_sot = c_st3.number_input("홈 유효슈팅", min_value=0, value=0, key="in_home_sot")
            away_sot = c_st4.number_input("원정 유효슈팅", min_value=0, value=0, key="in_home_sot")

            c_ps1, c_ps2, c_ps3, c_ps4 = st.columns(4)
            home_poss = c_ps1.number_input("홈 점유율 (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.1, key="in_home_poss")
            away_poss = c_ps2.number_input("원정 점유율 (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.1, key="in_away_poss")
            home_pass = c_ps3.number_input("홈 패스성공률 (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1, key="in_home_pass")
            away_pass = c_ps4.number_input("원정 패스성공률 (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1, key="in_home_pass_single")

            c_cd1, c_cd2, c_cd3, c_cd4, c_xg1, c_xg2 = st.columns(6)
            home_yc = c_cd1.number_input("홈 경고(옐로)", min_value=0, value=0, key="in_home_yc")
            away_yc = c_cd2.number_input("원정 경고(옐로)", min_value=0, value=0, key="in_home_yc_single")
            home_rc = c_cd3.number_input("홈 퇴장(레드)", min_value=0, value=0, key="in_home_rc")
            away_rc = c_cd4.number_input("원정 퇴장(레드)", min_value=0, value=0, key="in_home_rc_single")
            home_xg = c_xg1.number_input("홈 xG", min_value=0.0, value=0.00, step=0.01, key="in_home_xg")
            away_xg = c_xg2.number_input("원정 xG", min_value=0.0, value=0.00, step=0.01, key="in_home_xg_single")

        st.markdown("---")
        if st.button("💾 구글 시트 1~9번 배당 탭 & 10번 경기내용 탭 일괄 저장 실행", type="primary", use_container_width=True):
            match_info_single = {"season": season, "league": league, "date": match_date, "home": home_team, "away": away_team}
            stats_dict_single = {
                "home_1h": home_1h, "home_2h": home_2h, "away_1h": away_1h, "away_2h": away_2h,
                "home_tac": home_tac, "away_tac": away_tac,
                "home_shots": home_shots, "away_shots": away_shots,
                "home_sot": home_sot, "away_sot": away_sot,
                "home_poss": home_poss, "away_poss": away_poss,
                "home_pass": home_pass, "away_pass": away_pass,
                "home_yc": home_yc, "away_yc": away_yc,
                "home_rc": home_rc, "away_rc": away_rc,
                "home_xg": home_xg, "away_xg": away_xg
            }
            with st.spinner("구글 스프레드시트에 저장 중..."):
                success, msg = save_match_data_to_sheets(
                    spreadsheet_id, bookmakers, "경기내용", match_info_single, odds_inputs_t1, stats_dict_single
                )
                if success:
                    st.cache_data.clear()
                    st.success(f"🎉 성공: {msg}")
                else:
                    st.error(f"저장 중 오류 발생: {msg}")
