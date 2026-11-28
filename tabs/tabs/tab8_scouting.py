"""
[팀 종합 스카우팅 리포트 - V1 (9대 핵심 지표)]
1. 시즌 성적 & 현재 흐름 (전체/홈/원정, 최근 5경기, 연속 기록, 홈/원정 괴리)
2. 공격·수비력 & xG/xGA 결정력 (득실점, 클린시트/무득점, 골 결정력, 수비 안정감)
3. 전·후반 패턴 & HT/FT (전후반 득실, 전반 리드 굳히기, 전반 열세 역전/승점)
4. 베팅 DNA (정배 승률, 역배 승점률, 누적 ROI, 2.5 언오버, BTTS, 2골차+ 대승, 최다 스코어 TOP3)
5. 리그 내 상대 순위 & 최근 5경기 폼 비교 (상승세/하락세 판독)
6. 슈팅 퀄리티 (슈팅당 xG, 유효슈팅 골 전환율)
7. 상대 전력별 성적 (배트맨 배당 구간 기준 약팀/호각세/강팀 상대 승률)
8. 배트맨 vs 해외 배당 반응도 (환급률 보정 기준 배트맨 경계 구간 vs 가치 구간 승률)
9. 자동 스카우팅 태그 & 네이버 블로그/카페 원클릭 인포그래픽

[📌 V2 추후 확장 백로그 메모]
- 전술(포메이션)별 승률 & 3백/4백 상대 상성
- 점유율 스타일 분석 (55%+ 지공형 vs 45%- 역습형)
- 패배 직후 반등력 (연패 방지 멘탈 지수)
- 경기 변동성 지수 (안정형 vs 롤러코스터형)
- 경기 간격(휴식일)별 성적 (4일 이하 강행군 체력 변수)
- 카드 리스크 (평균 경고/퇴장 및 경고 3장 이상 경기 승률)
- 월별/시기별 컨디션 그래프
"""

import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter
from database import load_sheet_data
from infographics import render_clipboard_component
from tabs.tab3_analysis import normalize_bm_dataframe


def _to_float(val, default=0.0):
    try:
        s = str(val).replace("%", "").replace(",", "").strip()
        if not s or s == "-":
            return default
        return float(s)
    except Exception:
        return default


def _parse_date_sort_key(d_str):
    s = str(d_str).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 6:
        return "20" + digits
    if len(digits) >= 8:
        return digits[:8]
    return s


def _extract_bm_cols(df_norm):
    cols = list(df_norm.columns)
    h_col = next((c for c in cols if any(k in c for k in ["해당_홈", "배당_홈", "홈배당", "홈_승", "H_ODDS"])), cols[12] if len(cols) > 14 else None)
    d_col = next((c for c in cols if any(k in c for k in ["해당_무", "배당_무", "무배당", "무승부", "D_ODDS"])), cols[13] if len(cols) > 14 else None)
    a_col = next((c for c in cols if any(k in c for k in ["해당_원", "배당_원", "원정배당", "원정_승", "A_ODDS"])), cols[14] if len(cols) > 14 else None)
    dt_col = next((c for c in cols if any(k in c for k in ["경기날짜", "날짜", "Date"])), cols[2] if len(cols) > 2 else None)
    sn_col = next((c for c in cols if "시즌" in c), cols[0] if len(cols) > 0 else None)
    lg_col = next((c for c in cols if any(k in c for k in ["리그명", "리그"])), cols[1] if len(cols) > 1 else None)
    hm_col = next((c for c in cols if "홈팀" in c), cols[3] if len(cols) > 3 else None)
    aw_col = next((c for c in cols if "원정팀" in c), cols[4] if len(cols) > 4 else None)
    return sn_col, lg_col, dt_col, hm_col, aw_col, h_col, d_col, a_col


def _build_bm_lookup(spreadsheet_id, sheet_name):
    """(홈팀, 원정팀, 날짜) 및 (홈팀, 원정팀) 키로 배당 조회 딕셔너리 생성"""
    df_raw = load_sheet_data(sheet_name, spreadsheet_id)
    if df_raw.empty:
        return {}
    df_n = normalize_bm_dataframe(df_raw)
    sn_c, lg_c, dt_c, hm_c, aw_c, h_c, d_c, a_c = _extract_bm_cols(df_n)
    if not (hm_c and aw_c and h_c and d_c and a_c):
        return {}

    lookup = {}
    for _, r in df_n.iterrows():
        hm = str(r.get(hm_c, "")).strip()
        aw = str(r.get(aw_c, "")).strip()
        dt = str(r.get(dt_c, "")).strip() if dt_c else ""
        sn = str(r.get(sn_c, "")).strip() if sn_c else ""
        hv = _to_float(r.get(h_c), 0.0)
        dv = _to_float(r.get(d_c), 0.0)
        av = _to_float(r.get(a_c), 0.0)
        if hm and aw and hv >= 1.01 and dv >= 1.01 and av >= 1.01:
            lookup[(sn, dt, hm, aw)] = (hv, dv, av)
            lookup[(dt, hm, aw)] = (hv, dv, av)
    return lookup


def generate_naver_scouting_infographic(rpt):
    tags_html = "".join(
        f"<td bgcolor='#1e293b' style='background-color: #1e293b; border: 1px solid #475569; color: #38bdf8; font-size: 11px; font-weight: 800; padding: 4px 9px; border-radius: 5px; white-space: nowrap; text-decoration: none;'>{t}</td><td width='6'></td>"
        for t in rpt["tags"][:5]
    )

    # 최근 5경기 배지
    recent_cells = ""
    for res_ch in rpt["recent5_list"]:
        if res_ch == "승":
            bg, fg = "#2563eb", "#ffffff"
        elif res_ch == "무":
            bg, fg = "#10b981", "#ffffff"
        else:
            bg, fg = "#e11d48", "#ffffff"
        recent_cells += f"<td bgcolor='{bg}' style='background-color: {bg}; color: {fg}; font-size: 12px; font-weight: 800; padding: 4px 8px; border-radius: 4px; text-align: center; text-decoration: none;'>{res_ch}</td><td width='4'></td>"

    # 최다 스코어 TOP 3
    top_scores_str = " / ".join([f"{sc} ({cnt}회)" for sc, cnt in rpt["top_scores"]]) if rpt["top_scores"] else "-"

    # xG / xGA 색상
    xg_diff = rpt["xg_diff"]
    xg_fg = "#1d4ed8" if xg_diff >= 0.1 else ("#e11d48" if xg_diff <= -0.1 else "#334155")
    xga_diff = rpt["xga_diff"]  # 실제실점 - xGA (음수일수록 수비 우수)
    xga_fg = "#047857" if xga_diff <= -0.1 else ("#e11d48" if xga_diff >= 0.1 else "#334155")
    roi_fg = "#047857" if rpt["roi_pct"] >= 0 else "#e11d48"

    html = f"""
    <div style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 720px; margin: 0 auto; background-color: #ffffff; border: 2px solid #1e293b; border-radius: 10px; overflow: hidden;">
        <!-- 상단 배너 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background-color: #0f172a; color: #ffffff;">
            <tr>
                <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 18px 20px; vertical-align: middle;">
                    <div style="font-size: 11px; color: #fbbf24; font-weight: 800; letter-spacing: 0.6px; margin-bottom: 4px; text-decoration: none;">
                        📋 TEAM COMPREHENSIVE SCOUTING REPORT ({rpt['season']} · {rpt['league']})
                    </div>
                    <div style="font-size: 22px; font-weight: 800; color: #ffffff; line-height: 1.3; text-decoration: none;">
                        {rpt['team']} 종합 전력 분석 리포트
                    </div>
                    <div style="font-size: 12px; font-weight: 600; color: #cbd5e1; margin-top: 4px; text-decoration: none;">
                        총 {rpt['total_n']}경기 분석 · {rpt['streak_text']} · {rpt['ha_gap_label']}
                    </div>
                    <table cellpadding="0" cellspacing="0" style="border-collapse: collapse; margin-top: 10px;">
                        <tr>{tags_html}</tr>
                    </table>
                </td>
                <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 18px 20px; text-align: right; vertical-align: middle; width: 150px; white-space: nowrap;">
                    <div style="font-size: 11px; color: #94a3b8; font-weight: 700; margin-bottom: 5px; text-decoration: none;">최근 5경기 흐름</div>
                    <table align="right" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                        <tr>{recent_cells}</tr>
                    </table>
                </td>
            </tr>
        </table>

        <!-- 핵심 KPI 3단 바 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background-color: #f1f5f9; border-bottom: 1px solid #cbd5e1;">
            <tr>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 34%; padding: 12px 10px; text-align: center; border-right: 1px solid #cbd5e1;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px; text-decoration: none;">📊 시즌 전체 성적</div>
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; text-decoration: none;">
                        {rpt['w']}승 {rpt['d']}무 {rpt['l']}패 <span style="color: #2563eb; text-decoration: none;">({rpt['win_pct']}%)</span>
                    </div>
                    <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-top: 2px; text-decoration: none;">
                        홈 {rpt['hw']}승{rpt['hd']}무{rpt['hl']}패 · 원정 {rpt['aw']}승{rpt['ad']}무{rpt['al']}패
                    </div>
                </td>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 33%; padding: 12px 10px; text-align: center; border-right: 1px solid #cbd5e1;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px; text-decoration: none;">⚽ 평균 득점 / 실점</div>
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; text-decoration: none;">
                        <span style="color: #1d4ed8; text-decoration: none;">{rpt['avg_gf']}골</span> / <span style="color: #be123c; text-decoration: none;">{rpt['avg_ga']}실점</span>
                    </div>
                    <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-top: 2px; text-decoration: none;">
                        무실점 {rpt['cs_pct']}% · 무득점 {rpt['fts_pct']}%
                    </div>
                </td>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 33%; padding: 12px 10px; text-align: center;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px; text-decoration: none;">💰 배당 수익률 (ROI)</div>
                    <div style="font-size: 14px; font-weight: 800; color: {roi_fg}; text-decoration: none;">
                        {rpt['roi_pct']:+.1f}%
                    </div>
                    <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-top: 2px; text-decoration: none;">
                        정배 승률 {rpt['fav_win_pct']}% · 역배 승점 {rpt['dog_pts_pct']}%
                    </div>
                </td>
            </tr>
        </table>

        <!-- 본문 2단 상세 테이블 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="#cbd5e1" colspan="2" style="background-color: #cbd5e1; padding: 8px 14px; font-size: 12px; color: #1e293b; text-align: left; border-bottom: 1px solid #94a3b8; text-decoration: none;">
                    ⚔️ 공격·수비 퀄리티 & 전·후반 패턴 (리그 내 순위 포함)
                </th>
            </tr>
            <tr>
                <td bgcolor="#ffffff" style="background-color: #ffffff; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.65; text-decoration: none;">
                    <b style="color: #0f172a; text-decoration: none;">• xG 결정력:</b> xG {rpt['avg_xg']} vs 득점 {rpt['avg_gf']} (<b style="color: {xg_fg}; text-decoration: none;">{xg_diff:+.2f}</b>)<br>
                    <b style="color: #0f172a; text-decoration: none;">• xGA 수비력:</b> xGA {rpt['avg_xga']} vs 실점 {rpt['avg_ga']} (<b style="color: {xga_fg}; text-decoration: none;">{xga_diff:+.2f}</b>)<br>
                    <b style="color: #0f172a; text-decoration: none;">• 슈팅 퀄리티:</b> 슈팅당 xG <b>{rpt['xg_per_shot']}</b> · 유효슈팅 전환율 <b>{rpt['sot_conv_pct']}%</b><br>
                    <b style="color: #0f172a; text-decoration: none;">• 리그 내 순위:</b> 득점 <b>{rpt['rank_gf']}</b> · 최소실점 <b>{rpt['rank_ga']}</b> · xG <b>{rpt['rank_xg']}</b>
                </td>
                <td bgcolor="#ffffff" style="background-color: #ffffff; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.65; text-decoration: none;">
                    <b style="color: #0f172a; text-decoration: none;">• 전/후반 득점비:</b> 전반 {rpt['gf_1h_pct']}% / 후반 <b>{rpt['gf_2h_pct']}%</b><br>
                    <b style="color: #0f172a; text-decoration: none;">• 전반 리드 굳히기:</b> 최종 승률 <b style="color: #1d4ed8; text-decoration: none;">{rpt['ht_lead_win_pct']}%</b> ({rpt['ht_lead_str']})<br>
                    <b style="color: #0f172a; text-decoration: none;">• 전반 열세 반격력:</b> 승점 획득 <b style="color: #047857; text-decoration: none;">{rpt['ht_trail_pts_pct']}%</b> ({rpt['ht_trail_str']})<br>
                    <b style="color: #0f172a; text-decoration: none;">• 최근 5경기 폼:</b> 득점 {rpt['r5_gf']} ({rpt['r5_gf_diff']:+.2f}) · xG {rpt['r5_xg']} ({rpt['r5_xg_diff']:+.2f})
                </td>
            </tr>
            <tr>
                <th bgcolor="#cbd5e1" colspan="2" style="background-color: #cbd5e1; padding: 8px 14px; font-size: 12px; color: #1e293b; text-align: left; border-bottom: 1px solid #94a3b8; text-decoration: none;">
                    🎯 베팅 DNA · 상대 전력별 승률 · 배트맨 vs 해외 반응도
                </th>
            </tr>
            <tr>
                <td bgcolor="#f8fafc" style="background-color: #f8fafc; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.65; text-decoration: none;">
                    <b style="color: #0f172a; text-decoration: none;">• 2.5 언오버 / BTTS:</b> 오버 <b style="color: #e11d48; text-decoration: none;">{rpt['ov25_pct']}%</b> · 양팀득점 <b>{rpt['btts_pct']}%</b><br>
                    <b style="color: #0f172a; text-decoration: none;">• 2골 차+ 대승 비율:</b> <b>{rpt['big_win_pct']}%</b> ({rpt['big_win_cnt']}회)<br>
                    <b style="color: #0f172a; text-decoration: none;">• 최다 스코어 TOP3:</b> {top_scores_str}
                </td>
                <td bgcolor="#f8fafc" style="background-color: #f8fafc; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.65; text-decoration: none;">
                    <b style="color: #0f172a; text-decoration: none;">• 약팀 상대 (≤1.7):</b> 승률 <b>{rpt['vs_weak_pct']}</b> ({rpt['vs_weak_rec']})<br>
                    <b style="color: #0f172a; text-decoration: none;">• 호각세 (1.7~2.8):</b> 승률 <b>{rpt['vs_mid_pct']}</b> ({rpt['vs_mid_rec']})<br>
                    <b style="color: #0f172a; text-decoration: none;">• 강팀 상대 (&gt;2.8):</b> 승률 <b>{rpt['vs_strong_pct']}</b> ({rpt['vs_strong_rec']})<br>
                    <b style="color: #0f172a; text-decoration: none;">• 배트맨 경계 vs 가치:</b> 경계 <b>{rpt['bm_tight_pct']}</b> · 가치 <b>{rpt['bm_value_pct']}</b>
                </td>
            </tr>
        </table>

        <!-- 하단 푸터 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; padding: 10px 16px; font-size: 11px; color: #475569; border-top: 1px solid #cbd5e1; text-decoration: none;">
                    <b style="color: #1e293b; text-decoration: none;">※ 분석 기준:</b> '경기내용' 시트 및 배트맨·해외 배당 시트 교차 분석 데이터입니다. (배트맨 경계 = 환급률 보정 시 해외 대비 배트맨이 배당을 깎은 경기 / 가치 = 후하게 준 경기)
                </td>
            </tr>
        </table>
    </div>
    """
    return html


def render_tab8_scouting(spreadsheet_id, overseas_bookmakers):
    st.subheader("📋 팀 종합 스카우팅 리포트 (경기내용 + 배당 교차 분석)")
    st.caption("시즌, 리그, 팀을 선택하면 성적·xG/xGA·슈팅 퀄리티·전후반 패턴·상대 전력별 승률·배당 DNA까지 한눈에 보고서와 블로그 인포그래픽으로 출력합니다.")

    df_stats = load_sheet_data("경기내용", spreadsheet_id)
    if df_stats.empty or "홈팀" not in df_stats.columns or "원정팀" not in df_stats.columns:
        st.warning("⚠️ '경기내용' 시트에 데이터가 없습니다.")
        return

    seasons = ["전체"] + sorted(df_stats["시즌"].dropna().astype(str).str.strip().unique().tolist(), reverse=True) if "시즌" in df_stats.columns else ["전체"]
    leagues = ["전체"] + sorted(df_stats["리그명"].dropna().astype(str).str.strip().unique().tolist()) if "리그명" in df_stats.columns else ["전체"]

    c_sel1, c_sel2, c_sel3 = st.columns(3)
    sel_season = c_sel1.selectbox("📅 시즌 선택", seasons, index=0, key="scout_season")
    sel_league = c_sel2.selectbox("🏆 리그(대회) 선택", leagues, index=0, key="scout_league")

    df_filtered = df_stats.copy()
    if sel_season != "전체" and "시즌" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["시즌"].astype(str).str.strip() == sel_season]
    if sel_league != "전체" and "리그명" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["리그명"].astype(str).str.strip() == sel_league]

    teams_set = set()
    teams_set.update(df_filtered["홈팀"].dropna().astype(str).str.strip().unique())
    teams_set.update(df_filtered["원정팀"].dropna().astype(str).str.strip().unique())
    available_teams = sorted([t for t in teams_set if t])

    if not available_teams:
        st.info("💡 선택한 시즌/리그 조건에 해당하는 팀 데이터가 없습니다.")
        return

    sel_team = c_sel3.selectbox("⚽ 분석할 팀 선택", available_teams, key="scout_team")

    if not st.button(f"🔍 [{sel_team}] 종합 스카우팅 리포트 생성하기", type="primary", use_container_width=True, key="btn_run_scouting"):
        return

    with st.spinner(f"[{sel_team}] 경기내용 및 배트맨·해외 배당 데이터를 교차 분석 중입니다..."):
        # 배트맨 & 해외 대표 시트(pinnacle 우선, 없으면 bet365) 배당 룩업
        bm_lookup = _build_bm_lookup(spreadsheet_id, "배트맨")
        overseas_ref_bm = "pinnacle" if "pinnacle" in overseas_bookmakers else (overseas_bookmakers[0] if overseas_bookmakers else None)
        ov_lookup = _build_bm_lookup(spreadsheet_id, overseas_ref_bm) if overseas_ref_bm else {}

        # 리그 내 모든 팀 통계 집계 (상대 순위 계산용)
        team_league_agg = {}
        for _, r in df_filtered.iterrows():
            hm = str(r.get("홈팀", "")).strip()
            aw = str(r.get("원정팀", "")).strip()
            if not hm or not aw:
                continue
            hg = _to_float(r.get("전반득점_홈")) + _to_float(r.get("후반득점_홈"))
            ag = _to_float(r.get("전반득점_원")) + _to_float(r.get("후반득점_원"))
            h_xg = _to_float(r.get("xG_홈"))
            a_xg = _to_float(r.get("xG_원"))
            h_pos = _to_float(r.get("점유율_홈"))
            a_pos = _to_float(r.get("점유율_원"))

            for t_name, gf, ga, xg, pos in [(hm, hg, ag, h_xg, h_pos), (aw, ag, hg, a_xg, a_pos)]:
                if t_name not in team_league_agg:
                    team_league_agg[t_name] = {"gf": [], "ga": [], "xg": [], "pos": []}
                team_league_agg[t_name]["gf"].append(gf)
                team_league_agg[t_name]["ga"].append(ga)
                team_league_agg[t_name]["xg"].append(xg)
                if pos > 0:
                    team_league_agg[t_name]["pos"].append(pos)

        def _get_rank_str(metric_key, ascending=False):
            avgs = []
            for tn, vals in team_league_agg.items():
                if vals[metric_key]:
                    avgs.append((tn, float(np.mean(vals[metric_key]))))
            if not avgs:
                return "-"
            avgs.sort(key=lambda x: x[1], reverse=not ascending)
            total_t = len(avgs)
            for idx_r, (tn, _) in enumerate(avgs, 1):
                if tn == sel_team:
                    return f"{idx_r}위/{total_t}팀"
            return "-"

        # 선택 팀 경기 추출 및 날짜순 정렬
        matches = []
        for _, r in df_filtered.iterrows():
            hm = str(r.get("홈팀", "")).strip()
            aw = str(r.get("원정팀", "")).strip()
            if hm != sel_team and aw != sel_team:
                continue

            is_home = (hm == sel_team)
            sn = str(r.get("시즌", "")).strip()
            dt = str(r.get("경기날짜", "")).strip()

            gf_1h = _to_float(r.get("전반득점_홈" if is_home else "전반득점_원"))
            gf_2h = _to_float(r.get("후반득점_홈" if is_home else "후반득점_원"))
            ga_1h = _to_float(r.get("전반득점_원" if is_home else "전반득점_홈"))
            ga_2h = _to_float(r.get("후반득점_원" if is_home else "후반득점_홈"))
            gf = gf_1h + gf_2h
            ga = ga_1h + ga_2h

            xg = _to_float(r.get("xG_홈" if is_home else "xG_원"))
            xga = _to_float(r.get("xG_원" if is_home else "xG_홈"))
            shots = _to_float(r.get("슈팅_홈" if is_home else "슈팅_원"))
            sot = _to_float(r.get("유효슈팅_홈" if is_home else "유효슈팅_원"))
            poss = _to_float(r.get("점유율_홈" if is_home else "점유율_원"))

            res = "승" if gf > ga else ("무" if gf == ga else "패")

            # 배트맨 / 해외 배당 매칭
            bm_odds = bm_lookup.get((sn, dt, hm, aw)) or bm_lookup.get((dt, hm, aw))
            ov_odds = ov_lookup.get((sn, dt, hm, aw)) or ov_lookup.get((dt, hm, aw))

            team_bm_odd = (bm_odds[0] if is_home else bm_odds[2]) if bm_odds else 0.0
            opp_bm_odd = (bm_odds[2] if is_home else bm_odds[0]) if bm_odds else 0.0
            is_fav = (team_bm_odd > 0 and opp_bm_odd > 0 and team_bm_odd < opp_bm_odd)
            is_dog = (team_bm_odd > 0 and opp_bm_odd > 0 and team_bm_odd > opp_bm_odd)

            # 환급률 보정 배트맨 vs 해외 반응도 판별
            bm_react = None  # "tight"(경계) or "value"(가치)
            if bm_odds and ov_odds:
                bm_p_inv = (1 / bm_odds[0]) + (1 / bm_odds[1]) + (1 / bm_odds[2])
                ov_p_inv = (1 / ov_odds[0]) + (1 / ov_odds[1]) + (1 / ov_odds[2])
                if bm_p_inv > 0 and ov_p_inv > 0:
                    bm_team_prob = (1 / team_bm_odd) / bm_p_inv
                    ov_team_odd = ov_odds[0] if is_home else ov_odds[2]
                    ov_team_prob = (1 / ov_team_odd) / ov_p_inv
                    # 배트맨 내재확률이 해외보다 높으면 = 배트맨이 배당을 더 깎아 경계함
                    bm_react = "tight" if bm_team_prob > ov_team_prob else "value"

            matches.append({
                "sort_k": _parse_date_sort_key(dt),
                "date": dt, "is_home": is_home, "opp": aw if is_home else hm,
                "gf_1h": gf_1h, "gf_2h": gf_2h, "ga_1h": ga_1h, "ga_2h": ga_2h,
                "gf": gf, "ga": ga, "xg": xg, "xga": xga,
                "shots": shots, "sot": sot, "poss": poss, "res": res,
                "team_bm_odd": team_bm_odd, "is_fav": is_fav, "is_dog": is_dog,
                "bm_react": bm_react
            })

        matches.sort(key=lambda x: x["sort_k"])
        total_n = len(matches)
        if total_n == 0:
            st.info(f"💡 [{sel_team}]의 경기 데이터가 없습니다.")
            return

        # 1. 성적 & 흐름
        w = sum(1 for m in matches if m["res"] == "승")
        d = sum(1 for m in matches if m["res"] == "무")
        l = sum(1 for m in matches if m["res"] == "패")
        win_pct = round((w / total_n) * 100, 1)

        h_ms = [m for m in matches if m["is_home"]]
        a_ms = [m for m in matches if not m["is_home"]]
        hw, hd, hl = sum(1 for m in h_ms if m["res"] == "승"), sum(1 for m in h_ms if m["res"] == "무"), sum(1 for m in h_ms if m["res"] == "패")
        aw, ad, al = sum(1 for m in a_ms if m["res"] == "승"), sum(1 for m in a_ms if m["res"] == "무"), sum(1 for m in a_ms if m["res"] == "패")

        h_ppg = (hw * 3 + hd) / len(h_ms) if h_ms else 0.0
        a_ppg = (aw * 3 + ad) / len(a_ms) if a_ms else 0.0
        if len(h_ms) >= 2 and len(a_ms) >= 2:
            if h_ppg - a_ppg >= 0.8:
                ha_gap_label = "🏠 극단적 안방 여포"
            elif a_ppg - h_ppg >= 0.8:
                ha_gap_label = "🚗 원정 깡패 성향"
            else:
                ha_gap_label = "⚖️ 홈/원정 균형형"
        else:
            ha_gap_label = "홈/원정 표본 누적 중"

        recent5_list = [m["res"] for m in matches[-5:]]
        last_res = matches[-1]["res"]
        streak_cnt = 0
        for m in reversed(matches):
            if m["res"] == last_res:
                streak_cnt += 1
            else:
                break
        if last_res == "승" and streak_cnt >= 2:
            streak_text = f"🔥 최근 {streak_cnt}연승 중"
        elif last_res == "패" and streak_cnt >= 2:
            streak_text = f"❄️ 최근 {streak_cnt}연패 중"
        else:
            unbeaten = 0
            for m in reversed(matches):
                if m["res"] != "패":
                    unbeaten += 1
                else:
                    break
            streak_text = f"🛡️ 최근 {unbeaten}경기 무패" if unbeaten >= 3 else f"최근 경기: {last_res}"

        # 2. 공수 & xG/xGA & 6. 슈팅 퀄리티
        avg_gf = round(float(np.mean([m["gf"] for m in matches])), 2)
        avg_ga = round(float(np.mean([m["ga"] for m in matches])), 2)
        avg_xg = round(float(np.mean([m["xg"] for m in matches])), 2)
        avg_xga = round(float(np.mean([m["xga"] for m in matches])), 2)
        xg_diff = round(avg_gf - avg_xg, 2)
        xga_diff = round(avg_ga - avg_xga, 2)

        cs_pct = round((sum(1 for m in matches if m["ga"] == 0) / total_n) * 100, 1)
        fts_pct = round((sum(1 for m in matches if m["gf"] == 0) / total_n) * 100, 1)

        tot_shots = sum(m["shots"] for m in matches)
        tot_sot = sum(m["sot"] for m in matches)
        tot_gf = sum(m["gf"] for m in matches)
        tot_xg = sum(m["xg"] for m in matches)
        xg_per_shot = round(tot_xg / tot_shots, 3) if tot_shots > 0 else 0.0
        sot_conv_pct = round((tot_gf / tot_sot) * 100, 1) if tot_sot > 0 else 0.0

        # 3. 전/후반 & HT/FT
        sum_1h = sum(m["gf_1h"] for m in matches)
        sum_2h = sum(m["gf_2h"] for m in matches)
        gf_1h_pct = round((sum_1h / tot_gf) * 100, 1) if tot_gf > 0 else 0.0
        gf_2h_pct = round((sum_2h / tot_gf) * 100, 1) if tot_gf > 0 else 0.0

        ht_leads = [m for m in matches if m["gf_1h"] > m["ga_1h"]]
        ht_lead_w = sum(1 for m in ht_leads if m["res"] == "승")
        ht_lead_win_pct = round((ht_lead_w / len(ht_leads)) * 100, 1) if ht_leads else 0.0
        ht_lead_str = f"{ht_lead_w}/{len(ht_leads)}경기"

        ht_trails = [m for m in matches if m["gf_1h"] < m["ga_1h"]]
        ht_trail_pts = sum(1 for m in ht_trails if m["res"] in ("승", "무"))
        ht_trail_pts_pct = round((ht_trail_pts / len(ht_trails)) * 100, 1) if ht_trails else 0.0
        ht_trail_str = f"{ht_trail_pts}/{len(ht_trails)}경기"

        # 4. 베팅 DNA
        ov25_pct = round((sum(1 for m in matches if (m["gf"] + m["ga"]) > 2.5) / total_n) * 100, 1)
        btts_pct = round((sum(1 for m in matches if m["gf"] > 0 and m["ga"] > 0) / total_n) * 100, 1)
        big_win_cnt = sum(1 for m in matches if (m["gf"] - m["ga"]) >= 2)
        big_win_pct = round((big_win_cnt / total_n) * 100, 1)

        score_counter = Counter(f"{int(m['gf'])}:{int(m['ga'])}" for m in matches)
        top_scores = score_counter.most_common(3)

        bm_valid = [m for m in matches if m["team_bm_odd"] >= 1.01]
        if bm_valid:
            roi_return = sum(m["team_bm_odd"] for m in bm_valid if m["res"] == "승")
            roi_pct = round(((roi_return - len(bm_valid)) / len(bm_valid)) * 100, 1)
        else:
            roi_pct = 0.0

        fav_ms = [m for m in bm_valid if m["is_fav"]]
        fav_win_pct = round((sum(1 for m in fav_ms if m["res"] == "승") / len(fav_ms)) * 100, 1) if fav_ms else 0.0
        dog_ms = [m for m in bm_valid if m["is_dog"]]
        dog_pts_pct = round((sum(1 for m in dog_ms if m["res"] in ("승", "무")) / len(dog_ms)) * 100, 1) if dog_ms else 0.0

        # 5. 최근 5경기 폼 비교
        r5 = matches[-5:]
        r5_gf = round(float(np.mean([m["gf"] for m in r5])), 2)
        r5_xg = round(float(np.mean([m["xg"] for m in r5])), 2)
        r5_gf_diff = round(r5_gf - avg_gf, 2)
        r5_xg_diff = round(r5_xg - avg_xg, 2)

        # 7. 상대 전력별 성적
        def _tier_stat(sub_list):
            if not sub_list:
                return "-", "0전"
            tw = sum(1 for x in sub_list if x["res"] == "승")
            td = sum(1 for x in sub_list if x["res"] == "무")
            tl = sum(1 for x in sub_list if x["res"] == "패")
            return f"{round((tw / len(sub_list)) * 100, 1)}%", f"{tw}승{td}무{tl}패"

        vs_weak_pct, vs_weak_rec = _tier_stat([m for m in bm_valid if m["team_bm_odd"] <= 1.7])
        vs_mid_pct, vs_mid_rec = _tier_stat([m for m in bm_valid if 1.7 < m["team_bm_odd"] <= 2.8])
        vs_strong_pct, vs_strong_rec = _tier_stat([m for m in bm_valid if m["team_bm_odd"] > 2.8])

        # 8. 배트맨 vs 해외 반응도
        tight_ms = [m for m in matches if m["bm_react"] == "tight"]
        value_ms = [m for m in matches if m["bm_react"] == "value"]
        bm_tight_pct = f"{round((sum(1 for m in tight_ms if m['res'] == '승') / len(tight_ms)) * 100, 1)}% ({len(tight_ms)}전)" if tight_ms else "-"
        bm_value_pct = f"{round((sum(1 for m in value_ms if m['res'] == '승') / len(value_ms)) * 100, 1)}% ({len(value_ms)}전)" if value_ms else "-"

        # 9. 자동 스카우팅 태그 생성
        tags = []
        if win_pct >= 60: tags.append("#상위권강호")
        if h_ppg - a_ppg >= 0.8 and len(h_ms) >= 2: tags.append("#안방여포")
        if a_ppg - h_ppg >= 0.8 and len(a_ms) >= 2: tags.append("#원정깡패")
        if ov25_pct >= 60: tags.append("#다득점오버형")
        elif ov25_pct <= 40: tags.append("#저득점언더형")
        if xg_diff >= 0.25: tags.append("#골결정력우수")
        if xga_diff <= -0.25: tags.append("#짠물수비")
        if gf_2h_pct >= 60: tags.append("#후반뒷심형")
        if fav_win_pct >= 75 and len(fav_ms) >= 3: tags.append("#정배신뢰도최상")
        if roi_pct >= 15 and len(bm_valid) >= 3: tags.append("#배당효자팀")
        if not tags: tags.append("#밸런스형")

        rpt = {
            "season": sel_season, "league": sel_league, "team": sel_team,
            "total_n": total_n, "w": w, "d": d, "l": l, "win_pct": win_pct,
            "hw": hw, "hd": hd, "hl": hl, "aw": aw, "ad": ad, "al": al,
            "ha_gap_label": ha_gap_label, "recent5_list": recent5_list, "streak_text": streak_text,
            "avg_gf": avg_gf, "avg_ga": avg_ga, "avg_xg": avg_xg, "avg_xga": avg_xga,
            "xg_diff": xg_diff, "xga_diff": xga_diff, "cs_pct": cs_pct, "fts_pct": fts_pct,
            "xg_per_shot": xg_per_shot, "sot_conv_pct": sot_conv_pct,
            "rank_gf": _get_rank_str("gf", ascending=False),
            "rank_ga": _get_rank_str("ga", ascending=True),
            "rank_xg": _get_rank_str("xg", ascending=False),
            "gf_1h_pct": gf_1h_pct, "gf_2h_pct": gf_2h_pct,
            "ht_lead_win_pct": ht_lead_win_pct, "ht_lead_str": ht_lead_str,
            "ht_trail_pts_pct": ht_trail_pts_pct, "ht_trail_str": ht_trail_str,
            "r5_gf": r5_gf, "r5_xg": r5_xg, "r5_gf_diff": r5_gf_diff, "r5_xg_diff": r5_xg_diff,
            "ov25_pct": ov25_pct, "btts_pct": btts_pct, "big_win_pct": big_win_pct, "big_win_cnt": big_win_cnt,
            "top_scores": top_scores, "roi_pct": roi_pct, "fav_win_pct": fav_win_pct, "dog_pts_pct": dog_pts_pct,
            "vs_weak_pct": vs_weak_pct, "vs_weak_rec": vs_weak_rec,
            "vs_mid_pct": vs_mid_pct, "vs_mid_rec": vs_mid_rec,
            "vs_strong_pct": vs_strong_pct, "vs_strong_rec": vs_strong_rec,
            "bm_tight_pct": bm_tight_pct, "bm_value_pct": bm_value_pct,
            "tags": tags
        }

        # 화면 요약 KPI 출력
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("시즌 성적 (승률)", f"{w}승 {d}무 {l}패", f"{win_pct}% · {streak_text}")
        m2.metric("평균 득점 / 실점", f"{avg_gf} / {avg_ga}", f"xG {avg_xg} ({xg_diff:+.2f})")
        m3.metric("배당 누적 ROI", f"{roi_pct:+.1f}%", f"정배 {fav_win_pct}% · 역배승점 {dog_pts_pct}%")
        m4.metric("2.5 오버 / BTTS", f"{ov25_pct}% / {btts_pct}%", f"슈팅당 xG {xg_per_shot}")

        # 네이버 블로그/카페용 원클릭 인포그래픽
        with st.expander("📊 / 📋 [네이버 블로그/카페 전용] 팀 종합 스카우팅 리포트 인포그래픽 복사 (추천 ⭐)", expanded=True):
            st.caption("초록색 버튼을 1번 클릭한 뒤 네이버 블로그/카페 글쓰기 창에서 Ctrl+V 하세요!")
            ig_html = generate_naver_scouting_infographic(rpt)
            render_clipboard_component(ig_html, "t8_clip_scouting", height=580)
