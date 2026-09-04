import streamlit as st
import pandas as pd
import re
from database import load_sheet_data
from infographics import generate_naver_injury_infographic, render_clipboard_component

def render_tab6(spreadsheet_id):
    st.subheader("🚑 팀별 부상자/결장자 명단 및 카드 리포트 (11번 시트 연동)")

    injury_sheet_name = "부상자명단"
    stats_sheet_name = "경기내용"

    df_injuries = load_sheet_data(injury_sheet_name, spreadsheet_id)
    df_stats_red = load_sheet_data(stats_sheet_name, spreadsheet_id)

    def extract_month_day(date_str):
        if not date_str or not str(date_str).strip():
            return None
        s = str(date_str).strip()
        digits = re.findall(r"\d+", s)
        if len(digits) >= 3:
            m = int(digits[1])
            d = int(digits[2])
            return m * 100 + d
        elif len(digits) == 2:
            m = int(digits[0])
            d = int(digits[1])
            return m * 100 + d
        return None

    with st.expander("🚨 [기간 및 리그별 퇴장 발생 경기 자동 추적 레이더] (놓친 징계 선수 찾기)", expanded=True):
        st.caption("10번 '경기내용' 시트에 기록된 경기 중 퇴장(레드카드)이 발생한 매치업을 기간 및 리그별로 자동 추출합니다.")
        
        date_col_name = None
        if not df_stats_red.empty:
            for c_cand in ["경기날짜", "날짜", "일자", "경기일자", "Date"]:
                if c_cand in df_stats_red.columns:
                    date_col_name = c_cand
                    break
            if date_col_name is None and len(df_stats_red.columns) > 2:
                date_col_name = df_stats_red.columns[2]

        lg_col_name = "리그명" if "리그명" in df_stats_red.columns else (df_stats_red.columns[1] if len(df_stats_red.columns) > 1 else "리그명")

        all_stat_leagues = ["전체 리그"]
        if not df_stats_red.empty and lg_col_name in df_stats_red.columns:
            all_stat_leagues += sorted([str(x).strip() for x in df_stats_red[lg_col_name].dropna().unique().tolist() if str(x).strip()])
        
        c_rc1, c_rc2, c_rc3 = st.columns([1, 1, 1])
        sel_rc_league = c_rc1.selectbox("조회할 리그", all_stat_leagues, key="rc_filter_league")
        
        rc_date_from = c_rc2.text_input("시작 날짜 필터 (포함)", placeholder="예: 08.21 또는 25.08.21", key="rc_date_from")
        rc_date_to = c_rc3.text_input("종료 날짜 필터 (포함)", placeholder="예: 08.29 또는 25.08.29", key="rc_date_to")

        val_from = extract_month_day(rc_date_from)
        val_to = extract_month_day(rc_date_to)

        if not df_stats_red.empty and "퇴장_홈" in df_stats_red.columns and "퇴장_원" in df_stats_red.columns:
            def to_num_rc(val):
                try:
                    return float(str(val).replace("%", "").strip())
                except:
                    return 0.0

            red_card_records = []
            for _, r in df_stats_red.iterrows():
                r_league = str(r.get(lg_col_name, "")).strip()
                r_date_raw = str(r.get(date_col_name, "")).strip() if date_col_name else ""
                r_date_val = extract_month_day(r_date_raw)
                
                r_home = str(r.get("홈팀", "")).strip()
                r_away = str(r.get("원정팀", "")).strip()
                
                rc_h = to_num_rc(r.get("퇴장_홈", 0))
                rc_a = to_num_rc(r.get("퇴장_원", 0))

                if sel_rc_league != "전체 리그" and r_league.upper() != sel_rc_league.upper():
                    continue

                if val_from is not None and r_date_val is not None:
                    if r_date_val < val_from:
                        continue
                elif rc_date_from.strip():
                    if r_date_raw < rc_date_from.strip():
                        continue

                if val_to is not None and r_date_val is not None:
                    if r_date_val > val_to:
                        continue
                elif rc_date_to.strip():
                    if r_date_raw > rc_date_to.strip():
                        continue

                if rc_h > 0 or rc_a > 0:
                    red_teams = []
                    if rc_h > 0: red_teams.append(f"🔴 홈팀 [{r_home}] ({int(rc_h)}명 퇴장)")
                    if rc_a > 0: red_teams.append(f"🔴 원정팀 [{r_away}] ({int(rc_a)}명 퇴장)")

                    red_card_records.append({
                        "경기날짜": r_date_raw if r_date_raw else "-",
                        "리그": r_league, "매치업": f"{r_home} vs {r_away}",
                        "🚨 퇴장 발생 팀": " / ".join(red_teams),
                        "홈 퇴장": int(rc_h), "원정 퇴장": int(rc_a)
                    })

            if red_card_records:
                st.error(f"🚨 선택하신 조건에서 **총 {len(red_card_records)}건의 퇴장 발생 경기**가 발견되었습니다! 해당 팀의 선수를 아래 결장 명단에 등록하세요.")
                st.dataframe(pd.DataFrame(red_card_records), use_container_width=True, hide_index=True)
            else:
                st.success("✅ 선택하신 기간 및 리그 조건에서 퇴장(레드카드)이 발생한 경기가 없습니다.")
        else:
            st.info("💡 10번 '경기내용' 탭에 퇴장 기록 데이터가 없습니다.")

    st.markdown("---")

    all_known_teams = set()
    if not df_injuries.empty:
        for col_cand in ["팀명", "팀", "Team"]:
            if col_cand in df_injuries.columns:
                all_known_teams.update(df_injuries[col_cand].dropna().unique())
                break
        if not all_known_teams and len(df_injuries.columns) > 2:
            all_known_teams.update(df_injuries.iloc[:, 2].dropna().unique())

    if not df_stats_red.empty:
        for col_cand in ["홈팀", "Home"]:
            if col_cand in df_stats_red.columns:
                all_known_teams.update(df_stats_red[col_cand].dropna().unique())
                break
        for col_cand in ["원정팀", "Away"]:
            if col_cand in df_stats_red.columns:
                all_known_teams.update(df_stats_red[col_cand].dropna().unique())
                break

    fallback_teams = ["웨스트햄", "리버풀", "맨체스터시티", "아스날", "첼시", "토트넘", "맨체스터유나이티드", "뉴캐슬", "아스톤빌라", "브라이튼"]
    all_known_teams.update(fallback_teams)
    
    team_options = sorted([str(t).strip() for t in all_known_teams if str(t).strip() and str(t).strip() != "nan"])

    c_s1, c_s2 = st.columns(2)
    default_inj_idx = 0
    if "selected_scan_match" in st.session_state and st.session_state.selected_scan_match:
        sm = st.session_state.selected_scan_match
        if sm["home"] in team_options:
            default_inj_idx = team_options.index(sm["home"])

    selected_team = c_s1.selectbox("조회할 팀명 선택", team_options, index=default_inj_idx, key="inj_filter_team")
    inj_league_title = c_s2.text_input("리그/대회 기준 표기", value="잉글랜드 1부리그 기록", key="inj_custom_league")

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        with st.expander(f"➕ 새로운 결장 선수 추가", expanded=False):
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
            p_role = f8.text_input("팀 내 역할", value="주전", placeholder="예: 주전, 로테이션", key="p_role")
            p_reason = f9.selectbox("결장 사유", ["부상", "결장의심", "징계/퇴장", "기타"], key="p_reason")
            p_note = f10.text_input("특이사항", value="-", placeholder="예: 복귀 예정 10월", key="p_note")

            if st.button("💾 구글 시트 11번 탭에 저장", type="primary", use_container_width=True):
                if p_name_en.strip() or p_name_kr.strip():
                    from database import get_gspread_client
                    client = get_gspread_client()
                    if client:
                        try:
                            spreadsheet = client.open_by_key(spreadsheet_id)
                            ws_inj = spreadsheet.worksheet(injury_sheet_name)
                            new_row = [
                                add_season, add_league, add_team,
                                p_name_en.strip(), p_name_kr.strip(),
                                p_pos, p_start, p_sub, p_goals, p_assists,
                                p_role.strip() if p_role.strip() else "-",
                                p_reason,
                                p_note.strip() if p_note.strip() else "-"
                            ]
                            ws_inj.append_row(new_row, value_input_option="USER_ENTERED")
                            import time
                            time.sleep(0.3)
                            st.cache_data.clear()
                            st.success(f"🎉 {add_team}의 [{p_name_kr or p_name_en}] 선수가 저장되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"저장 실패: {e}")
                else:
                    st.warning("선수 이름을 입력해 주세요.")

    with col_btn2:
        with st.expander(f"✏️ 부상 선수 정보 수정하기", expanded=False):
            team_col_name = "팀명" if not df_injuries.empty and "팀명" in df_injuries.columns else df_injuries.columns[2] if not df_injuries.empty and len(df_injuries.columns) > 2 else None
            
            if not df_injuries.empty and team_col_name:
                filtered_df_edit = df_injuries[df_injuries[team_col_name] == selected_team]
                if not filtered_df_edit.empty:
                    edit_player_ids = []
                    edit_player_labels = {}
                    for idx, row in filtered_df_edit.iterrows():
                        kr = row.get("선수한글명", row.get(df_injuries.columns[4], ""))
                        en = row.get("선수영문명", row.get(df_injuries.columns[3], ""))
                        disp_name = f"{kr} ({en})" if kr and en else (kr or en)
                        edit_player_ids.append(idx)
                        edit_player_labels[idx] = disp_name

                    if "edit_selected_idx" not in st.session_state or st.session_state.edit_selected_idx not in edit_player_ids:
                        st.session_state.edit_selected_idx = edit_player_ids[0]

                    sel_idx = st.selectbox(
                        "수정할 선수 선택", 
                        edit_player_ids, 
                        format_func=lambda x: edit_player_labels[x], 
                        key="edit_selected_idx"
                    )
                    
                    target_row_data = filtered_df_edit.loc[sel_idx]

                    e_kr = st.text_input("선수 한글명 수정", value=str(target_row_data.get("선수한글명", target_row_data.get(df_injuries.columns[4], ""))), key=f"edit_kr_{sel_idx}")
                    e_en = st.text_input("선수 영문명 수정", value=str(target_row_data.get("선수영문명", target_row_data.get(df_injuries.columns[3], ""))), key=f"edit_en_{sel_idx}")
                    
                    pos_list = ["FW", "MF", "DF", "GK"]
                    curr_pos = str(target_row_data.get("포지션", target_row_data.get(df_injuries.columns[5], "MF")))
                    pos_idx = pos_list.index(curr_pos) if curr_pos in pos_list else 1
                    e_pos = st.selectbox("포지션 수정", pos_list, index=pos_idx, key=f"edit_pos_{sel_idx}")

                    e1, e2, e3, e4 = st.columns(4)
                    e_start = e1.number_input("선발", min_value=0, value=int(target_row_data.get("선발", target_row_data.get(df_injuries.columns[6], 0)) or 0), key=f"edit_start_{sel_idx}")
                    e_sub = e2.number_input("교체", min_value=0, value=int(target_row_data.get("교체", target_row_data.get(df_injuries.columns[7], 0)) or 0), key=f"edit_sub_{sel_idx}")
                    e_goals = e3.number_input("골", min_value=0, value=int(target_row_data.get("골", target_row_data.get(df_injuries.columns[8], 0)) or 0), key=f"edit_goals_{sel_idx}")
                    e_assists = e4.number_input("도움", min_value=0, value=int(target_row_data.get("도움", target_row_data.get(df_injuries.columns[9], 0)) or 0), key=f"edit_assists_{sel_idx}")

                    e_role = st.text_input("팀 내 역할 수정", value=str(target_row_data.get("역할", target_row_data.get(df_injuries.columns[10], "주전"))), key=f"edit_role_{sel_idx}")
                    
                    reason_list = ["부상", "결장의심", "징계/퇴장", "기타"]
                    curr_reason = str(target_row_data.get("결장사유", target_row_data.get("사유", target_row_data.get(df_injuries.columns[11], "부상"))))
                    reason_idx = reason_list.index(curr_reason) if curr_reason in reason_list else 0
                    e_reason = st.selectbox("결장 사유 수정", reason_list, index=reason_idx, key=f"edit_reason_{sel_idx}")
                    
                    e_note = st.text_input("특이사항 (복귀예상일 등) 수정", value=str(target_row_data.get("특이사항", target_row_data.get(df_injuries.columns[12], "-"))), key=f"edit_note_{sel_idx}")

                    if st.button("🔄 부상 선수 정보 갱신하기", type="primary", use_container_width=True):
                        from database import get_gspread_client
                        client = get_gspread_client()
                        if client:
                            try:
                                spreadsheet = client.open_by_key(spreadsheet_id)
                                ws_inj = spreadsheet.worksheet(injury_sheet_name)
                                
                                updated_row_values = [
                                    str(target_row_data.get("시즌", "25-26")),
                                    str(target_row_data.get("리그명", "PL")),
                                    str(selected_team),
                                    e_en.strip(),
                                    e_kr.strip(),
                                    e_pos,
                                    e_start,
                                    e_sub,
                                    e_goals,
                                    e_assists,
                                    e_role.strip() if e_role.strip() else "-",
                                    e_reason,
                                    e_note.strip() if e_note.strip() else "-"
                                ]
                                
                                ws_inj.update(f"A{sel_idx + 2}:M{sel_idx + 2}", [updated_row_values], value_input_option="USER_ENTERED")
                                import time
                                time.sleep(0.3)
                                st.cache_data.clear()
                                st.success(f"🎉 [{e_kr or e_en}] 선수의 부상/결장 정보가 성공적으로 수정되었습니다!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"수정 실패: {e}")
                else:
                    st.info(f"현재 [{selected_team}]에 수정할 부상 선수가 없습니다.")
            else:
                st.info("시트에 등록된 선수 데이터가 없습니다.")

    with col_btn3:
        with st.expander(f"🗑️ 복귀 선수 명단에서 제외", expanded=False):
            team_col_name = "팀명" if not df_injuries.empty and "팀명" in df_injuries.columns else df_injuries.columns[2] if not df_injuries.empty and len(df_injuries.columns) > 2 else None
            if not df_injuries.empty and team_col_name:
                filtered_df_rm = df_injuries[df_injuries[team_col_name] == selected_team]
                if not filtered_df_rm.empty:
                    player_options = []
                    for idx, row in filtered_df_rm.iterrows():
                        kr = row.get("선수한글명", "")
                        en = row.get("선수영문명", "")
                        name_display = f"{kr} ({en})" if kr and en else (kr or en)
                        player_options.append((idx, name_display))
                    
                    sel_player_to_remove = st.selectbox("복귀한 선수 선택", player_options, format_func=lambda x: x[1], key="sel_remove_player")
                    
                    if st.button("🚀 선택한 선수 복귀 완료 (삭제)", type="secondary", use_container_width=True):
                        from database import get_gspread_client
                        client = get_gspread_client()
                        if client:
                            with st.spinner("구글 시트에서 선수 삭제 중..."):
                                try:
                                    spreadsheet = client.open_by_key(spreadsheet_id)
                                    ws_inj = spreadsheet.worksheet(injury_sheet_name)
                                    target_row_index = sel_player_to_remove[0] + 2
                                    ws_inj.delete_rows(target_row_index)
                                    import time
                                    time.sleep(0.3)
                                    st.cache_data.clear()
                                    st.success(f"🎉 [{sel_player_to_remove[1]}] 선수가 명단에서 정상적으로 제외되었습니다!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"삭제 실패: {e}")
                else:
                    st.info(f"현재 [{selected_team}]에 등록된 선수가 없습니다.")
            else:
                st.info("시트에 등록된 선수 데이터가 없습니다.")

    st.markdown("---")

    filtered_df = pd.DataFrame()
    if not df_injuries.empty:
        team_col_name = "팀명" if "팀명" in df_injuries.columns else (df_injuries.columns[2] if len(df_injuries.columns) > 2 else None)
        if team_col_name:
            filtered_df = df_injuries[df_injuries[team_col_name].astype(str).str.strip() == str(selected_team).strip()]

    reason_col = None
    if not filtered_df.empty:
        for c in filtered_df.columns:
            if any(k in c for k in ["결장사유", "사유", "비고"]):
                reason_col = c
                break
        if reason_col is None and len(filtered_df.columns) > 11:
            reason_col = filtered_df.columns[11]

    confirmed_players = []
    doubt_players = []

    if not filtered_df.empty and reason_col and reason_col in filtered_df.columns:
        for _, p_row in filtered_df.iterrows():
            p_dict = p_row.to_dict()
            val_reason = str(p_dict.get(reason_col, "")).strip()
            if "의심" in val_reason or "GTD" in val_reason:
                doubt_players.append(p_dict)
            else:
                confirmed_players.append(p_dict)
    elif not filtered_df.empty:
        confirmed_players = filtered_df.to_dict("records")

    st.subheader(f"📋 [{selected_team}] 결장자 현황 (총 {len(filtered_df)}명)")

    with st.expander("📊 / 📋 네이버 블로그/카페용 결장자 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
        st.markdown(f"##### 🌟 [네이버 블로그/카페 전용] [{selected_team}] 결장자 리포트 카드")
        st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

        naver_inj_html = generate_naver_injury_infographic(
            selected_team, inj_league_title, confirmed_players, doubt_players
        )

        render_clipboard_component(naver_inj_html, "t5_clip", height=520)

    card_text = f"### 🚑 {selected_team} 결장 & 결장의심 명단\n"
    card_text += f"*({inj_league_title})*\n\n"

    if not filtered_df.empty:
        if confirmed_players:
            card_text += "🔴 **[결장 확정 / 징계]**\n"
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
                reason = p.get(reason_col, "부상") if reason_col else "부상"
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
                reason = p.get(reason_col, "결장의심") if reason_col else "결장의심"
                note = p.get("특이사항", "-")
                note_str = f" *({note})*" if note != "-" else ""
                card_text += f"* ❓ **{name_str}** | `{pos}` · `{role}`\n"
                card_text += f"  * 📊 **기록**: {start}선발 {sub}교체 / {goals}골 {assists}도움\n"
                card_text += f"  * ⚠️ **사유**: {reason}{note_str}\n\n"
    else:
        card_text += "✅ 현재 등록된 부상 및 징계 결장자가 없습니다. (스쿼드 100% 전력 구성 완료 👑)\n"

    with st.expander("📝 심플 텍스트 복사용"):
        st.text_area("텍스트 복사창", value=card_text, height=250)
    
    with st.expander("🔍 시트에 저장된 원본 데이터 표 보기"):
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 [{selected_team}]에 등록된 부상/결장 선수 데이터가 없습니다.")
