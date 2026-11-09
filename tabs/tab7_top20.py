import streamlit as st
import pandas as pd
import numpy as np
from database import load_sheet_data
from tabs.tab2_scanner import get_preprocessed_bm_db_v3
from infographics import render_clipboard_component


def generate_naver_top20_ranking_infographic(
    ranked_list, min_cnt_used=5, ou_line=2.5, show_odds=False
):
    if not ranked_list:
        return """
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 720px; margin: 0 auto; border-collapse: collapse; border: 1px solid #cbd5e1;">
            <tr>
                <td bgcolor="#f8fafc" style="background-color: #f8fafc; padding: 20px; text-align: center; color: #64748b; font-family: 'Malgun Gothic', sans-serif;">
                    산출된 최우선 추천픽 데이터가 없습니다.
                </td>
            </tr>
        </table>
        """

    total_shown = len(ranked_list)
    avg_best_prob = round(sum(x["best_prob"] for x in ranked_list) / total_shown, 1) if total_shown > 0 else 0.0
    wdl_pick_cnt = sum(1 for x in ranked_list if x["best_cat"] == "승무패")
    ou_pick_cnt = total_shown - wdl_pick_cnt

    rows_html = ""
    for idx, item in enumerate(ranked_list):
        rank_num = idx + 1
        bg_row = "#ffffff" if idx % 2 == 0 else "#e8eef5"

        # 1~3위 메달 및 순위 박스 색상 지정 (네이버 카페/블로그 밑줄 방지를 위해 내부 table/td bgcolor 사용)
        if rank_num == 1:
            rk_bg, rk_fg, rk_txt = "#b45309", "#ffffff", "🥇 1위"
        elif rank_num == 2:
            rk_bg, rk_fg, rk_txt = "#334155", "#ffffff", "🥈 2위"
        elif rank_num == 3:
            rk_bg, rk_fg, rk_txt = "#7c2d12", "#ffffff", "🥉 3위"
        else:
            rk_bg, rk_fg, rk_txt = "#1e293b", "#f8fafc", f"{rank_num}위"

        best_lbl = item["best_label"]
        best_prob = item["best_prob"]
        best_hits = item["best_hits"]
        best_tot = item["best_total"]

        # 추천픽 유형에 따른 팀명 강조 및 추천 셀 전용 파스텔 배경색
        if "홈승" in best_lbl:
            h_style = "font-weight: 800; color: #1e3a8a; font-size: 15px; text-decoration: none;"
            a_style = "font-weight: 600; color: #475569; font-size: 14px; text-decoration: none;"
            pick_bg, pick_fg = "#dbeafe", "#1d4ed8"
        elif "원정승" in best_lbl:
            h_style = "font-weight: 600; color: #475569; font-size: 14px; text-decoration: none;"
            a_style = "font-weight: 800; color: #991b1b; font-size: 15px; text-decoration: none;"
            pick_bg, pick_fg = "#ffe4e6", "#be123c"
        elif "무승부" in best_lbl:
            h_style = "font-weight: 700; color: #1e293b; font-size: 15px; text-decoration: none;"
            a_style = "font-weight: 700; color: #1e293b; font-size: 15px; text-decoration: none;"
            pick_bg, pick_fg = "#d1fae5", "#047857"
        elif "오버" in best_lbl:
            h_style = "font-weight: 700; color: #0f172a; font-size: 15px; text-decoration: none;"
            a_style = "font-weight: 700; color: #0f172a; font-size: 15px; text-decoration: none;"
            pick_bg, pick_fg = "#ffedd5", "#c2410c"
        else:
            h_style = "font-weight: 700; color: #0f172a; font-size: 15px; text-decoration: none;"
            a_style = "font-weight: 700; color: #0f172a; font-size: 15px; text-decoration: none;"
            pick_bg, pick_fg = "#e0e7ff", "#4338ca"

        bh, bd, ba = item["batman_odds"]
        odds_sub_html = (
            f"<div style='font-size: 11px; color: #64748b; margin-top: 3px; text-decoration: none;'>"
            f"배트맨: {bh} / {bd} / {ba}</div>"
            if show_odds and bh > 0
            else ""
        )

        sec_str = item["second_str"]
        wdl_summary = f"승 {item['win_prob']}% · 무 {item['draw_prob']}% · 패 {item['lose_prob']}%"
        ou_summary = f"{ou_line}오버 {item['over_prob']}% · 언더 {item['under_prob']}%"

        rows_html += f"""
        <tr>
            <td bgcolor="{bg_row}" style="background-color: {bg_row}; padding: 11px 6px; text-align: center; vertical-align: middle; width: 11%; border-bottom: 1px solid #cbd5e1; white-space: nowrap;">
                <table align="center" cellpadding="0" cellspacing="0" style="margin: 0 auto; border-collapse: collapse;">
                    <tr>
                        <td bgcolor="{rk_bg}" style="background-color: {rk_bg}; color: {rk_fg}; font-weight: 800; font-size: 12px; padding: 5px 9px; border-radius: 6px; white-space: nowrap; text-decoration: none;">
                            {rk_txt}
                        </td>
                    </tr>
                </table>
            </td>
            <td bgcolor="{bg_row}" style="background-color: {bg_row}; padding: 11px 6px; text-align: center; vertical-align: middle; width: 14%; border-bottom: 1px solid #cbd5e1; white-space: nowrap; text-decoration: none;">
                <div style="font-size: 12px; color: #0f172a; font-weight: 800; text-decoration: none;">[{item['league']}]</div>
                <div style="font-size: 11px; color: #475569; font-weight: 600; margin-top: 2px; text-decoration: none;">{item['date']}</div>
            </td>
            <td bgcolor="{bg_row}" style="background-color: {bg_row}; padding: 11px 10px; text-align: center; vertical-align: middle; width: 33%; border-bottom: 1px solid #cbd5e1; word-break: keep-all; text-decoration: none;">
                <div style="line-height: 1.35; text-decoration: none;">
                    <span style="{h_style}">{item['home']}</span>
                    <span style="font-size: 12px; color: #94a3b8; font-weight: 700; margin: 0 5px; text-decoration: none;">VS</span>
                    <span style="{a_style}">{item['away']}</span>
                </div>
                {odds_sub_html}
            </td>
            <td bgcolor="{pick_bg}" style="background-color: {pick_bg}; padding: 10px 8px; text-align: center; vertical-align: middle; width: 22%; border-bottom: 1px solid #cbd5e1; border-left: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1; white-space: nowrap; text-decoration: none;">
                <div style="font-size: 14px; font-weight: 800; color: {pick_fg}; text-decoration: none;">
                    {best_lbl}
                </div>
                <div style="font-size: 13px; font-weight: 800; color: #0f172a; margin-top: 3px; text-decoration: none;">
                    적중률 <span style="color: {pick_fg}; font-size: 14px; text-decoration: none;">{best_prob}%</span>
                    <span style="font-size: 11px; color: #475569; font-weight: 700; text-decoration: none;">({best_hits}/{best_tot}건)</span>
                </div>
            </td>
            <td bgcolor="{bg_row}" style="background-color: {bg_row}; padding: 10px 8px; text-align: center; vertical-align: middle; width: 20%; border-bottom: 1px solid #cbd5e1; white-space: nowrap; text-decoration: none;">
                <div style="font-size: 12px; font-weight: 800; color: #334155; margin-bottom: 3px; text-decoration: none;">
                    🥈 {sec_str}
                </div>
                <div style="font-size: 10px; color: #64748b; font-weight: 600; text-decoration: none;">
                    {wdl_summary}
                </div>
                <div style="font-size: 10px; color: #64748b; font-weight: 600; margin-top: 1px; text-decoration: none;">
                    {ou_summary}
                </div>
            </td>
        </tr>
        """

    html = f"""
    <div style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 720px; margin: 0 auto; background-color: #ffffff; border: 2px solid #1e293b; border-radius: 10px; overflow: hidden;">
        <!-- 상단 배너 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background-color: #0f172a; color: #ffffff;">
            <tr>
                <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 16px 20px; vertical-align: middle;">
                    <div style="font-size: 11px; color: #fbbf24; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 4px; text-decoration: none;">
                        🏆 DAILY PRIORITY PICK RANKING (9-BOOKMAKER INTEGRATED)
                    </div>
                    <div style="font-size: 19px; font-weight: 800; color: #ffffff; word-break: keep-all; line-height: 1.3; text-decoration: none;">
                        당일 최우선 주력픽 TOP {total_shown} 종합 랭킹
                    </div>
                    <div style="font-size: 12px; font-weight: 600; color: #cbd5e1; margin-top: 4px; word-break: keep-all; text-decoration: none;">
                        9대 북메이커 과거 동일배당 매칭 데이터 통합 적중확률 순위 (최소 {min_cnt_used}건 이상 검증)
                    </div>
                </td>
                <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 16px 20px; text-align: right; vertical-align: middle; width: 130px; white-space: nowrap;">
                    <table align="right" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                        <tr>
                            <td bgcolor="#1e293b" style="background-color: #1e293b; border: 1px solid #475569; color: #fbbf24; font-size: 14px; font-weight: 800; padding: 8px 14px; border-radius: 6px; white-space: nowrap; text-decoration: none;">
                                상위 {total_shown}경기
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>

        <!-- 상단 3단 요약 바 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background-color: #f1f5f9; border-bottom: 1px solid #cbd5e1;">
            <tr>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 34%; padding: 11px 10px; text-align: center; border-right: 1px solid #cbd5e1;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px; text-decoration: none;">🎯 신뢰도 검증 기준</div>
                    <div style="font-size: 13px; font-weight: 800; color: #0f172a; white-space: nowrap; text-decoration: none;">
                        9개사 합산 <span style="color: #2563eb; text-decoration: none;">최소 {min_cnt_used}건↑</span>
                    </div>
                </td>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 33%; padding: 11px 10px; text-align: center; border-right: 1px solid #cbd5e1;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px; text-decoration: none;">🔥 선정 픽 평균 적중률</div>
                    <div style="font-size: 13px; font-weight: 800; color: #e11d48; white-space: nowrap; text-decoration: none;">
                        평균 {avg_best_prob}%
                    </div>
                </td>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 33%; padding: 11px 10px; text-align: center;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px; text-decoration: none;">📊 주력 종목 비중</div>
                    <div style="font-size: 13px; font-weight: 800; color: #0f172a; white-space: nowrap; text-decoration: none;">
                        승무패 {wdl_pick_cnt}건 · 언오버 {ou_pick_cnt}건
                    </div>
                </td>
            </tr>
        </table>

        <!-- 메인 순위 테이블 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr>
                    <th bgcolor="#cbd5e1" style="background-color: #cbd5e1; padding: 9px 6px; font-size: 12px; color: #1e293b; text-align: center; width: 11%; border-top: 1px solid #94a3b8; border-bottom: 2px solid #94a3b8; text-decoration: none;">순위</th>
                    <th bgcolor="#cbd5e1" style="background-color: #cbd5e1; padding: 9px 6px; font-size: 12px; color: #1e293b; text-align: center; width: 14%; border-top: 1px solid #94a3b8; border-bottom: 2px solid #94a3b8; text-decoration: none;">리그 / 일자</th>
                    <th bgcolor="#cbd5e1" style="background-color: #cbd5e1; padding: 9px 8px; font-size: 12px; color: #1e293b; text-align: center; width: 33%; border-top: 1px solid #94a3b8; border-bottom: 2px solid #94a3b8; text-decoration: none;">매치업 (홈 vs 원정)</th>
                    <th bgcolor="#cbd5e1" style="background-color: #cbd5e1; padding: 9px 8px; font-size: 12px; color: #1e293b; text-align: center; width: 22%; border-top: 1px solid #94a3b8; border-bottom: 2px solid #94a3b8; text-decoration: none;">👑 1순위 추천픽 (확률)</th>
                    <th bgcolor="#cbd5e1" style="background-color: #cbd5e1; padding: 9px 8px; font-size: 12px; color: #1e293b; text-align: center; width: 20%; border-top: 1px solid #94a3b8; border-bottom: 2px solid #94a3b8; text-decoration: none;">🥈 2순위 / 세부비율</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <!-- 하단 주의사항 푸터 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; padding: 12px 16px; text-align: left; font-size: 11px; color: #475569; border-top: 1px solid #cbd5e1; line-height: 1.5; word-break: keep-all; text-decoration: none;">
                    <b style="color: #1e293b; text-decoration: none;">※ 산출 기준 안내:</b> 위 순위는 당일 등록된 경기들을 대상으로 9개 배당 업체의 과거 동일배당 구간 데이터를 전수 대조하여, <b style="color: #1e293b; text-decoration: none;">최소 {min_cnt_used}건 이상 매칭된 항목(승/무/패 및 {ou_line} 언오버)</b> 중 적중 확률과 표본 수가 가장 높은 순서대로 산출한 데이터입니다.
                </td>
            </tr>
        </table>
    </div>
    """
    return html


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

            with st.expander("📊 / 📋 [네이버 블로그/카페 전용] 당일 최우선 추천픽 순위표 인포그래픽 복사 (추천 ⭐)", expanded=True):
                st.markdown("##### 🌟 [네이버 블로그/카페 전용] 당일 최우선 주력픽 순위보드 인포그래픽")
                st.caption("초록색 복사 버튼을 클릭하여 네이버 블로그나 카페 글쓰기 창에 그대로 붙여넣기(Ctrl+V) 하세요!")

                c_ig1, c_ig2 = st.columns(2)
                with c_ig1:
                    limit_opt = st.radio(
                        "인포그래픽에 표시할 순위 범위",
                        ["TOP 20 전체 표시", "TOP 10 (1~10위만 표시)", "TOP 5 (1~5위 핵심만 표시)"],
                        horizontal=True,
                        key="top20_ig_limit_radio"
                    )
                with c_ig2:
                    odds_opt = st.radio(
                        "배트맨 배당 표시 여부",
                        ["배당 숨기기 (깔끔 버전 ⭐)", "배트맨 배당 함께 표시"],
                        horizontal=True,
                        key="top20_ig_odds_radio"
                    )

                if "TOP 5" in limit_opt:
                    ig_target_list = top20_list[:5]
                elif "TOP 10" in limit_opt:
                    ig_target_list = top20_list[:10]
                else:
                    ig_target_list = top20_list

                show_odds_flag = "함께 표시" in odds_opt
                top20_ig_html = generate_naver_top20_ranking_infographic(
                    ig_target_list,
                    min_cnt_used=min_cnt_used,
                    ou_line=ou_used,
                    show_odds=show_odds_flag
                )
                ig_height = min(1150, max(450, 260 + 62 * len(ig_target_list)))
                render_clipboard_component(top20_ig_html, "top20_clip_ranking_ig", height=ig_height)

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
