import time
import streamlit as st
import pandas as pd
import gspread
from gspread.utils import rowcol_to_a1
from database import get_gspread_client, load_sheet_data, clear_sheet_cache


def render_tab9_admin(spreadsheet_id, bookmakers):
    st.subheader("🛠️ 구글 시트 팀명 일괄 수정 (오타 / 표기 통일)")
    st.caption("배당 9개사 시트, '경기내용', '라운드스캔' 총 11개 시트의 홈팀/원정팀 열에서 잘못 적힌 팀명을 한 번에 찾아 안전하게 수정합니다.")

    target_sheets = list(bookmakers) + ["경기내용", "라운드스캔"]

    # 현재 시트에 등록된 팀명 목록을 참고용으로 불러오기 (경기내용 + 배트맨 기준)
    with st.expander("📋 현재 시트에 등록된 팀명 목록 확인하기 (오타 찾기용)", expanded=False):
        teams_set = set()
        for ref_sheet in ["경기내용", "배트맨", "라운드스캔"]:
            df_ref = load_sheet_data(ref_sheet, spreadsheet_id)
            if not df_ref.empty:
                for col_name in ["홈팀", "원정팀"]:
                    if col_name in df_ref.columns:
                        vals = df_ref[col_name].dropna().astype(str).str.strip().unique()
                        teams_set.update([v for v in vals if v])

        sorted_teams = sorted(list(teams_set))
        if sorted_teams:
            search_kw = st.text_input("🔍 팀명 필터 검색", placeholder="예: 셰필드, 세필드, 맨체스터", key="admin_team_filter")
            filtered_teams = [t for t in sorted_teams if search_kw.strip().lower() in t.lower()] if search_kw.strip() else sorted_teams
            st.caption(f"총 {len(filtered_teams)}개 팀명 발견")
            st.write(", ".join([f"`{t}`" for t in filtered_teams]))
        else:
            st.info("불러올 팀명 데이터가 없습니다.")

    st.markdown("---")

    with st.container(border=True):
        st.markdown("##### 1️⃣ 변경할 팀명 입력")
        c1, c2 = st.columns(2)
        old_name = c1.text_input(
            "찾을 팀명 (기존 오타/구버전)",
            placeholder="예: 세필드유나이티드",
            key="admin_old_team_name"
        )
        new_name = c2.text_input(
            "바꿀 팀명 (정확한 새 이름)",
            placeholder="예: 셰필드유나이티드",
            key="admin_new_team_name"
        )

        st.caption("⚠️ 정확히 일치하는 팀명만 변경됩니다. (예: '맨체스터'를 바꿔도 '맨체스터시티'는 건드리지 않아 안전합니다.)")

        if st.button("🔍 [1단계] 전체 11개 시트 검색 및 변경 대상 미리보기", type="primary", use_container_width=True):
            old_clean = old_name.strip()
            new_clean = new_name.strip()

            if not old_clean or not new_clean:
                st.warning("찾을 팀명과 바꿀 팀명을 모두 입력해 주세요.")
            elif old_clean == new_clean:
                st.warning("찾을 팀명과 바꿀 팀명이 동일합니다.")
            else:
                client = get_gspread_client()
                if not client:
                    st.error("구글 시트 연동 실패: Secrets 설정을 확인하세요.")
                else:
                    with st.spinner("11개 시트를 스캔하는 중입니다..."):
                        try:
                            spreadsheet = client.open_by_key(spreadsheet_id)
                            preview_summary = []
                            update_plan = {}  # {sheet_name: [(row_idx_1based, col_idx_1based, a1_cell), ...]}
                            total_found = 0

                            for s_name in target_sheets:
                                try:
                                    ws = spreadsheet.worksheet(s_name)
                                    all_vals = ws.get_all_values()
                                except gspread.exceptions.WorksheetNotFound:
                                    continue

                                if len(all_vals) <= 1:
                                    continue

                                header = [str(c).strip() for c in all_vals[0]]
                                # 홈팀/원정팀 열 인덱스 찾기 (없으면 기본 D열=3, E열=4 사용)
                                home_col_idx = header.index("홈팀") if "홈팀" in header else (3 if len(header) > 3 else None)
                                away_col_idx = header.index("원정팀") if "원정팀" in header else (4 if len(header) > 4 else None)

                                target_cols = [c for c in [home_col_idx, away_col_idx] if c is not None]
                                sheet_hits = []

                                for r_idx, row in enumerate(all_vals[1:], start=2):
                                    for c_idx in target_cols:
                                        if c_idx < len(row):
                                            cell_val = str(row[c_idx]).strip()
                                            if cell_val == old_clean:
                                                a1 = rowcol_to_a1(r_idx, c_idx + 1)
                                                sheet_hits.append((r_idx, c_idx + 1, a1))

                                if sheet_hits:
                                    update_plan[s_name] = sheet_hits
                                    total_found += len(sheet_hits)
                                    preview_summary.append({
                                        "시트명": s_name,
                                        "발견 건수": f"{len(sheet_hits)}건",
                                        "대상 셀 예시": ", ".join([h[2] for h in sheet_hits[:5]]) + (" ..." if len(sheet_hits) > 5 else "")
                                    })

                                time.sleep(0.1)

                            st.session_state["admin_update_plan"] = update_plan
                            st.session_state["admin_preview_summary"] = preview_summary
                            st.session_state["admin_old_clean"] = old_clean
                            st.session_state["admin_new_clean"] = new_clean
                            st.session_state["admin_total_found"] = total_found

                        except Exception as e:
                            st.error(f"시트 검색 중 오류 발생: {e}")

    # 2단계: 미리보기 결과 출력 및 일괄 변경 실행
    if "admin_update_plan" in st.session_state:
        total_found = st.session_state.get("admin_total_found", 0)
        p_old = st.session_state.get("admin_old_clean", "")
        p_new = st.session_state.get("admin_new_clean", "")
        preview_summary = st.session_state.get("admin_preview_summary", [])
        update_plan = st.session_state.get("admin_update_plan", {})

        st.markdown("---")
        if total_found == 0:
            st.info(f"💡 전체 11개 시트에서 **'{p_old}'** 팀명이 발견되지 않았습니다. 띄어쓰기나 철자를 다시 확인해 주세요.")
        else:
            st.success(f"🔎 총 **{len(update_plan)}개 시트**에서 **'{p_old}'** 팀명이 **총 {total_found}건** 발견되었습니다.")
            st.dataframe(pd.DataFrame(preview_summary), use_container_width=True, hide_index=True)

            st.warning(f"⚠️ 아래 버튼을 누르면 위 **{total_found}개 셀**의 **'{p_old}'**가 모두 **'{p_new}'**(으)로 영구 변경됩니다.")

            if st.button(f"🚀 [2단계] '{p_old}' ➔ '{p_new}' 일괄 변경 실행 ({total_found}건)", type="primary", use_container_width=True):
                client = get_gspread_client()
                if not client:
                    st.error("구글 시트 연동 실패: Secrets 설정을 확인하세요.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    updated_total = 0
                    sheet_names = list(update_plan.keys())

                    try:
                        spreadsheet = client.open_by_key(spreadsheet_id)
                        for idx, s_name in enumerate(sheet_names):
                            hits = update_plan[s_name]
                            status_text.text(f"⏳ [{s_name}] 시트 업데이트 중... ({len(hits)}건)")
                            ws = spreadsheet.worksheet(s_name)

                            # gspread batch_update로 한 번에 고속 반영
                            batch_payload = [
                                {"range": a1, "values": [[p_new]]}
                                for (_, _, a1) in hits
                            ]
                            ws.batch_update(batch_payload, value_input_option="USER_ENTERED")
                            updated_total += len(hits)

                            progress_bar.progress((idx + 1) / len(sheet_names))
                            time.sleep(0.2)

                        clear_sheet_cache()
                        st.cache_data.clear()
                        status_text.empty()
                        st.success(f"🎉 완료! 총 {len(sheet_names)}개 시트, {updated_total}건의 팀명이 '{p_new}'(으)로 일괄 수정되었습니다!")

                        # 완료 후 이전 계획 초기화
                        del st.session_state["admin_update_plan"]

                    except Exception as e:
                        st.error(f"일괄 변경 중 오류 발생: {e}")
