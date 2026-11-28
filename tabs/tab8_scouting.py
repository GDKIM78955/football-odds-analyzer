import math
import re
import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter
from database import load_sheet_data
from infographics import render_clipboard_component
from tabs.tab2_scanner import (
    HC_OPTIONS, OU_OPTIONS, format_hc_label, sort_hc_lines
)
from tabs.tab3_analysis import normalize_bm_dataframe


def _to_float(val, default=0.0):
    try:
        s = str(val).replace("%", "").replace(",", "").strip()
        if not s or s == "-":
            return default
        return float(s)
    except Exception:
        return default


def _norm_date(d_str):
    """날짜 문자열을 YYYYMMDD 형태로 정규화 (25.8.3 -> 20250803)"""
    s = str(d_str).strip()
    nums = re.findall(r"\d+", s)
    if len(nums) >= 3:
        y, m, d = nums[0], nums[1].zfill(2), nums[2].zfill(2)
        if len(y) == 2:
            y = "20" + y
        return f"{y}{m}{d}"
    digits = "".join(nums)
    if len(digits) == 6:
        return "20" + digits
    return digits if digits else s


def _poisson_xpts(xg, xga):
    """포아송 분포 기반 경기당 기대승점(xPts) 계산"""
    if xg <= 0 and xga <= 0:
        return 1.0
    max_g = 8
    p_h = [math.exp(-xg) * (xg ** k) / math.factorial(k) for k in range(max_g)]
    p_a = [math.exp(-xga) * (xga ** k) / math.factorial(k) for k in range(max_g)]
    win_p, draw_p = 0.0, 0.0
    for i in range(max_g):
        for j in range(max_g):
            prob = p_h[i] * p_a[j]
            if i > j:
                win_p += prob
            elif i == j:
                draw_p += prob
    return win_p * 3.0 + draw_p * 1.0


def _extract_bm_cols(df_norm):
    cols = list(df_norm.columns)
    h_col = next((c for c in cols if any(k in c for k in ["해당_홈", "배당_홈", "홈배당", "홈_승", "H_ODDS"])), cols[12] if len(cols) > 14 else None)
    d_col = next((c for c in cols if any(k in c for k in ["해당_무", "배당_무", "무배당", "무승부", "D_ODDS"])), cols[13] if len(cols) > 14 else None)
    a_col = next((c for c in cols if any(k in c for k in ["해당_원", "배당_원", "원정배당", "원정_승", "A_ODDS"])), cols[14] if len(cols) > 14 else None)
    dt_col = next((c for c in cols if any(k in c for k in ["경기날짜", "날짜", "Date"])), cols[2] if len(cols) > 2 else None)
    sn_col = next((c for c in cols if "시즌" in c), cols[0] if len(cols) > 0 else None)
    hm_col = next((c for c in cols if "홈팀" in c), cols[3] if len(cols) > 3 else None)
    aw_col = next((c for c in cols if "원정팀" in c), cols[4] if len(cols) > 4 else None)
    return sn_col, dt_col, hm_col, aw_col, h_col, d_col, a_col


@st.cache_data(ttl=300, show_spinner=False)
def _build_odds_lookups_cached(spreadsheet_id, overseas_bookmakers_tuple):
    """배트맨 배당 및 해외 8개사 평균 배당 룩업 테이블 생성 (다단계 키 매칭)"""
    def _parse_sheet(sheet_name):
        df_raw = load_sheet_data(sheet_name, spreadsheet_id)
        if df_raw.empty:
            return {}, {}, {}
        df_n = normalize_bm_dataframe(df_raw)
        sn_c, dt_c, hm_c, aw_c, h_c, d_c, a_c = _extract_bm_cols(df_n)
        if not (hm_c and aw_c and h_c and d_c and a_c):
            return {}, {}, {}

        by_dt, by_sn, by_pair = {}, {}, {}
        for _, r in df_n.iterrows():
            hm = str(r.get(hm_c, "")).strip()
            aw = str(r.get(aw_c, "")).strip()
            dt = _norm_date(r.get(dt_c, "")) if dt_c else ""
            sn = str(r.get(sn_c, "")).strip() if sn_c else ""
            hv = _to_float(r.get(h_c), 0.0)
            dv = _to_float(r.get(d_c), 0.0)
            av = _to_float(r.get(a_c), 0.0)
            if hm and aw and hv >= 1.01 and dv >= 1.01 and av >= 1.01:
                if dt:
                    by_dt[(dt, hm, aw)] = (hv, dv, av)
                if sn:
                    by_sn[(sn, hm, aw)] = (hv, dv, av)
                by_pair[(hm, aw)] = (hv, dv, av)
        return by_dt, by_sn, by_pair

    bm_dt, bm_sn, bm_pair = _parse_sheet("배트맨")

    ov_dt_acc, ov_sn_acc, ov_pair_acc = {}, {}, {}
    for obm in overseas_bookmakers_tuple:
        o_dt, o_sn, o_pair = _parse_sheet(obm)
        for k, v in o_dt.items():
            ov_dt_acc.setdefault(k, []).append(v)
        for k, v in o_sn.items():
            ov_sn_acc.setdefault(k, []).append(v)
        for k, v in o_pair.items():
            ov_pair_acc.setdefault(k, []).append(v)

    def _avg_dict(acc):
        res = {}
        for k, lst in acc.items():
            res[k] = (
                round(float(np.mean([x[0] for x in lst])), 3),
                round(float(np.mean([x[1] for x in lst])), 3),
                round(float(np.mean([x[2] for x in lst])), 3),
            )
        return res

    return (
        (bm_dt, bm_sn, bm_pair),
        (_avg_dict(ov_dt_acc), _avg_dict(ov_sn_acc), _avg_dict(ov_pair_acc))
    )


def _lookup_odds(lookup_tuple, norm_dt, sn, hm, aw):
    by_dt, by_sn, by_pair = lookup_tuple
    if (norm_dt, hm, aw) in by_dt:
        return by_dt[(norm_dt, hm, aw)]
    if (sn, hm, aw) in by_sn:
        return by_sn[(sn, hm, aw)]
    return by_pair.get((hm, aw))


def generate_naver_scouting_infographic(rpt):
    tags_html = "".join(
        f"<td bgcolor='#1e293b' style='background-color: #1e293b; border: 1px solid #475569; color: #38bdf8; font-size: 11px; font-weight: 800; padding: 4px 8px; border-radius: 5px; white-space: nowrap; text-decoration: none;'>{t}</td><td width='5'></td>"
        for t in rpt["tags"][:5]
    )

    recent_cells = ""
    for res_ch in rpt["recent5_list"]:
        bg = "#2563eb" if res_ch == "승" else ("#10b981" if res_ch == "무" else "#e11d48")
        recent_cells += f"<td bgcolor='{bg}' style='background-color: {bg}; color: #ffffff; font-size: 12px; font-weight: 800; padding: 4px 8px; border-radius: 4px; text-align: center; text-decoration: none;'>{res_ch}</td><td width='4'></td>"

    top_scores_str = " / ".join([f"{sc} ({cnt}회)" for sc, cnt in rpt["top_scores"]]) if rpt["top_scores"] else "-"
    xg_fg = "#1d4ed8" if rpt["xg_diff"] >= 0.1 else ("#e11d48" if rpt["xg_diff"] <= -0.1 else "#334155")
    xga_fg = "#047857" if rpt["xga_diff"] <= -0.1 else ("#e11d48" if rpt["xga_diff"] >= 0.1 else "#334155")
    roi_fg = "#047857" if rpt["roi_pct"] >= 0 else "#e11d48"
    draw_roi_fg = "#047857" if rpt["draw_roi_pct"] >= 0 else "#e11d48"
    xpts_fg = "#e11d48" if rpt["pts_diff"] >= 2.0 else ("#1d4ed8" if rpt["pts_diff"] <= -2.0 else "#334155")

    hc_lines_html = ""
    for h_item in rpt["hc_stats"]:
        hc_lines_html += (
            f"<b style='color: #0f172a; text-decoration: none;'>• 핸디캡 ({h_item['label']}):</b> "
            f"승 <b style='color: #1d4ed8; text-decoration: none;'>{h_item['w_pct']}%</b> · "
            f"무 {h_item['d_pct']}% · 패 {h_item['l_pct']}%<br>"
        )

    tac_html = " / ".join([f"<b>{t['tac']}</b> {t['cnt']}회(승률 {t['win_pct']}%)" for t in rpt["top_tactics"]]) if rpt["top_tactics"] else "-"

    log_rows_html = ""
    for idx_l, m in enumerate(rpt["recent5_detail"]):
        bg_l = "#ffffff" if idx_l % 2 == 0 else "#f1f5f9"
        ha_badge = "홈" if m["is_home"] else "원정"
        res_fg_l = "#1d4ed8" if m["res"] == "승" else ("#047857" if m["res"] == "무" else "#be123c")
        odd_txt = f"{m['team_bm_odd']:.2f}" if m["team_bm_odd"] >= 1.01 else "-"
        log_rows_html += f"""
        <tr>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 7px 6px; font-size: 11px; color: #475569; text-align: center; border-bottom: 1px solid #e2e8f0; text-decoration: none;">{m['date']}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 7px 6px; font-size: 11px; color: #0f172a; font-weight: 700; text-align: center; border-bottom: 1px solid #e2e8f0; text-decoration: none;">{ha_badge}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 7px 8px; font-size: 12px; color: #0f172a; font-weight: 700; text-align: left; border-bottom: 1px solid #e2e8f0; text-decoration: none;">{m['opp']}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 7px 6px; font-size: 12px; color: {res_fg_l}; font-weight: 800; text-align: center; border-bottom: 1px solid #e2e8f0; text-decoration: none;">{int(m['gf'])}:{int(m['ga'])} ({m['res']})</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 7px 6px; font-size: 11px; color: #334155; text-align: center; border-bottom: 1px solid #e2e8f0; text-decoration: none;">{m['xg']:.2f} / {m['xga']:.2f}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 7px 6px; font-size: 11px; color: #334155; font-weight: 700; text-align: center; border-bottom: 1px solid #e2e8f0; text-decoration: none;">{odd_txt}</td>
        </tr>
        """

    html = f"""
    <div style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 740px; margin: 0 auto; background-color: #ffffff; border: 2px solid #1e293b; border-radius: 10px; overflow: hidden;">
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
                        총 {rpt['total_n']}경기 · {rpt['streak_text']} · {rpt['ha_gap_label']}
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
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px;">📊 시즌 성적 & 기대승점(xPts)</div>
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a;">
                        {rpt['w']}승 {rpt['d']}무 {rpt['l']}패 <span style="color: #2563eb;">({rpt['win_pct']}%)</span>
                    </div>
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-top: 2px;">
                        승점 {rpt['pts']}점 vs xPts {rpt['xpts']}점 (<span style="color: {xpts_fg};">{rpt['pts_diff']:+.1f}</span>)
                    </div>
                </td>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 33%; padding: 12px 10px; text-align: center; border-right: 1px solid #cbd5e1;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px;">⚽ 평균 득점 / 실점</div>
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a;">
                        <span style="color: #1d4ed8;">{rpt['avg_gf']}골</span> / <span style="color: #be123c;">{rpt['avg_ga']}실점</span>
                    </div>
                    <div style="font-size: 11px; color: #475569; font-weight: 600; margin-top: 2px;">
                        2득점↑ {rpt['gf2_pct']}% · 2실점↑ {rpt['ga2_pct']}% · CS {rpt['cs_pct']}%
                    </div>
                </td>
                <td bgcolor="#f1f5f9" style="background-color: #f1f5f9; width: 33%; padding: 12px 10px; text-align: center;">
                    <div style="font-size: 11px; color: #475569; font-weight: 700; margin-bottom: 3px;">💰 배당 수익률 (배트맨 {rpt['bm_matched_n']}건)</div>
                    <div style="font-size: 14px; font-weight: 800; color: {roi_fg};">
                        승 ROI {rpt['roi_pct']:+.1f}%
                    </div>
                    <div style="font-size: 11px; color: #475569; font-weight: 600; margin-top: 2px;">
                        정배 승률 {rpt['fav_win_pct']}% · 역배 승점 {rpt['dog_pts_pct']}%
                    </div>
                </td>
            </tr>
        </table>

        <!-- 섹션 1: 홈 vs 원정 정밀 비교표 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="#cbd5e1" colspan="7" style="background-color: #cbd5e1; padding: 8px 14px; font-size: 12px; color: #1e293b; text-align: left; border-bottom: 1px solid #94a3b8;">
                    🏠 홈 vs 원정 정밀 비교표 (설정 언오버 {rpt['sel_ou']} 기준)
                </th>
            </tr>
            <tr>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">구분</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">전적 (승률)</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">평균 득/실</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">xG / xGA</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">점유율</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">{rpt['sel_ou']} 오버</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">경기당 승점</th>
            </tr>
            <tr>
                <td bgcolor="#ffffff" style="padding: 8px 6px; font-size: 12px; font-weight: 800; color: #1d4ed8; text-align: center; border-bottom: 1px solid #e2e8f0;">🏠 홈 ({rpt['h_n']}전)</td>
                <td bgcolor="#ffffff" style="padding: 8px 6px; font-size: 12px; font-weight: 700; color: #0f172a; text-align: center; border-bottom: 1px solid #e2e8f0;">{rpt['hw']}승{rpt['hd']}무{rpt['hl']}패 ({rpt['h_win_pct']}%)</td>
                <td bgcolor="#ffffff" style="padding: 8px 6px; font-size: 12px; color: #334155; text-align: center; border-bottom: 1px solid #e2e8f0;">{rpt['h_gf']} / {rpt['h_ga']}</td>
                <td bgcolor="#ffffff" style="padding: 8px 6px; font-size: 12px; color: #334155; text-align: center; border-bottom: 1px solid #e2e8f0;">{rpt['h_xg']} / {rpt['h_xga']}</td>
                <td bgcolor="#ffffff" style="padding: 8px 6px; font-size: 12px; color: #334155; text-align: center; border-bottom: 1px solid #e2e8f0;">{rpt['h_poss']}%</td>
                <td bgcolor="#ffffff" style="padding: 8px 6px; font-size: 12px; color: #e11d48; font-weight: 700; text-align: center; border-bottom: 1px solid #e2e8f0;">{rpt['h_ov_pct']}%</td>
                <td bgcolor="#ffffff" style="padding: 8px 6px; font-size: 12px; font-weight: 800; color: #0f172a; text-align: center; border-bottom: 1px solid #e2e8f0;">{rpt['h_ppg']}점</td>
            </tr>
            <tr>
                <td bgcolor="#f8fafc" style="padding: 8px 6px; font-size: 12px; font-weight: 800; color: #be123c; text-align: center; border-bottom: 1px solid #cbd5e1;">🚗 원정 ({rpt['a_n']}전)</td>
                <td bgcolor="#f8fafc" style="padding: 8px 6px; font-size: 12px; font-weight: 700; color: #0f172a; text-align: center; border-bottom: 1px solid #cbd5e1;">{rpt['aw']}승{rpt['ad']}무{rpt['al']}패 ({rpt['a_win_pct']}%)</td>
                <td bgcolor="#f8fafc" style="padding: 8px 6px; font-size: 12px; color: #334155; text-align: center; border-bottom: 1px solid #cbd5e1;">{rpt['a_gf']} / {rpt['a_ga']}</td>
                <td bgcolor="#f8fafc" style="padding: 8px 6px; font-size: 12px; color: #334155; text-align: center; border-bottom: 1px solid #cbd5e1;">{rpt['a_xg']} / {rpt['a_xga']}</td>
                <td bgcolor="#f8fafc" style="padding: 8px 6px; font-size: 12px; color: #334155; text-align: center; border-bottom: 1px solid #cbd5e1;">{rpt['a_poss']}%</td>
                <td bgcolor="#f8fafc" style="padding: 8px 6px; font-size: 12px; color: #e11d48; font-weight: 700; text-align: center; border-bottom: 1px solid #cbd5e1;">{rpt['a_ov_pct']}%</td>
                <td bgcolor="#f8fafc" style="padding: 8px 6px; font-size: 12px; font-weight: 800; color: #0f172a; text-align: center; border-bottom: 1px solid #cbd5e1;">{rpt['a_ppg']}점</td>
            </tr>
        </table>

        <!-- 섹션 2: 공수 퀄리티 / 키퍼 / 전후반 / 멘탈 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="#cbd5e1" colspan="2" style="background-color: #cbd5e1; padding: 8px 14px; font-size: 12px; color: #1e293b; text-align: left; border-bottom: 1px solid #94a3b8;">
                    ⚔️ 공격·수비·키퍼 퀄리티 & 전·후반 패턴 · 멘탈 지표
                </th>
            </tr>
            <tr>
                <td bgcolor="#ffffff" style="background-color: #ffffff; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.7; vertical-align: top;">
                    <b style="color: #0f172a;">• xG 결정력:</b> xG {rpt['avg_xg']} vs 득점 {rpt['avg_gf']} (<b style="color: {xg_fg};">{rpt['xg_diff']:+.2f}</b>)<br>
                    <b style="color: #0f172a;">• xGA 수비력:</b> xGA {rpt['avg_xga']} vs 실점 {rpt['avg_ga']} (<b style="color: {xga_fg};">{rpt['xga_diff']:+.2f}</b>)<br>
                    <b style="color: #0f172a;">• 압도 지표:</b> xGD <b>{rpt['xgd']:+.2f}</b> · 유효슈팅 마진 <b>{rpt['sot_margin']:+.1f}회</b><br>
                    <b style="color: #0f172a;">• 공격 슈팅 효율:</b> 슈팅당 xG <b>{rpt['xg_per_shot']}</b> · 정확도 <b>{rpt['shot_acc_pct']}%</b> · 전환율 <b>{rpt['sot_conv_pct']}%</b><br>
                    <b style="color: #0f172a;">• 수비/키퍼 효율:</b> 허용 슈팅당 xGA <b>{rpt['xga_per_shot']}</b> · 키퍼 선방률 <b style="color: #047857;">{rpt['gk_save_pct']}%</b><br>
                    <b style="color: #0f172a;">• 리그 내 순위:</b> 득점 <b>{rpt['rank_gf']}</b> · 최소실점 <b>{rpt['rank_ga']}</b> · xG <b>{rpt['rank_xg']}</b>
                </td>
                <td bgcolor="#ffffff" style="background-color: #ffffff; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.7; vertical-align: top;">
                    <b style="color: #0f172a;">• 전반 흐름:</b> 전반 득점률 <b>{rpt['fh_score_pct']}%</b> · 전반 무실점 <b>{rpt['fh_cs_pct']}%</b><br>
                    <b style="color: #0f172a;">• 후반 집중력:</b> 후반 득실마진 <b>{rpt['sh_gd_avg']:+.2f}골</b> · 후반 실점비중 <b>{rpt['sh_ga_share']}%</b><br>
                    <b style="color: #0f172a;">• 전반 리드 굳히기:</b> 승률 <b style="color: #1d4ed8;">{rpt['ht_lead_win_pct']}%</b> ({rpt['ht_lead_str']})<br>
                    <b style="color: #0f172a;">• 전반 무승부 시:</b> 승 {rpt['ht_draw_w']}% · 무 {rpt['ht_draw_d']}% · 패 {rpt['ht_draw_l']}% ({rpt['ht_draw_n']}전)<br>
                    <b style="color: #0f172a;">• 전반 열세 반격:</b> 승점 획득 <b style="color: #047857;">{rpt['ht_trail_pts_pct']}%</b> ({rpt['ht_trail_str']})<br>
                    <b style="color: #0f172a;">• 기세/멘탈:</b> 승 직후 승률 <b>{rpt['after_win_pct']}</b> · 패 직후 반등 <b>{rpt['bounce_win_pct']}</b> (무패 {rpt['bounce_unb_pct']})
                </td>
            </tr>

            <!-- 섹션 3: 베팅 DNA / 핸디캡 / 언오버 / 배당 반응도 -->
            <tr>
                <th bgcolor="#cbd5e1" colspan="2" style="background-color: #cbd5e1; padding: 8px 14px; font-size: 12px; color: #1e293b; text-align: left; border-bottom: 1px solid #94a3b8;">
                    🎯 베팅 DNA · 사용자 설정 핸디캡/언오버 · 상대전력 & 배당 반응도
                </th>
            </tr>
            <tr>
                <td bgcolor="#f8fafc" style="background-color: #f8fafc; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.7; vertical-align: top;">
                    <b style="color: #0f172a;">• 설정 {rpt['sel_ou']} 언오버:</b> 오버 <b style="color: #e11d48;">{rpt['sel_ov_pct']}%</b> / 언더 <b style="color: #2563eb;">{rpt['sel_un_pct']}%</b><br>
                    <b style="color: #0f172a;">• 기준점별 오버:</b> 1.5↑ <b>{rpt['ov15_pct']}%</b> · 2.5↑ <b>{rpt['ov25_pct']}%</b> · 3.5↑ <b>{rpt['ov35_pct']}%</b><br>
                    <b style="color: #0f172a;">• 양팀득점(BTTS):</b> <b>{rpt['btts_pct']}%</b> · 최다 스코어: {top_scores_str}<br>
                    <b style="color: #0f172a;">• 무승부 지수:</b> 무 {rpt['draw_pct']}% (0:0·1:1 {rpt['low_draw_cnt']}회) · 무 ROI <b style="color: {draw_roi_fg};">{rpt['draw_roi_pct']:+.1f}%</b><br>
                    {hc_lines_html}
                </td>
                <td bgcolor="#f8fafc" style="background-color: #f8fafc; width: 50%; padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #334155; line-height: 1.7; vertical-align: top;">
                    <b style="color: #0f172a;">• 약팀 상대 (≤1.7):</b> 승률 <b>{rpt['vs_weak_pct']}</b> ({rpt['vs_weak_rec']})<br>
                    <b style="color: #0f172a;">• 호각세 (1.7~2.8):</b> 승률 <b>{rpt['vs_mid_pct']}</b> ({rpt['vs_mid_rec']})<br>
                    <b style="color: #0f172a;">• 강팀 상대 (&gt;2.8):</b> 승률 <b>{rpt['vs_strong_pct']}</b> ({rpt['vs_strong_rec']})<br>
                    <b style="color: #0f172a;">• 정배 심화:</b> 정배 시 -1.0 마핸 <b>{rpt['fav_m1_pct']}</b> · 초정배(≤1.5) 함정 <b style="color: #e11d48;">{rpt['trap_pct']}</b><br>
                    <b style="color: #0f172a;">• 배트맨 경계 구간:</b> 승률 <b style="color: #1d4ed8;">{rpt['bm_tight_pct']}</b><br>
                    <b style="color: #0f172a;">• 배트맨 가치 구간:</b> 승률 <b style="color: #047857;">{rpt['bm_value_pct']}</b>
                </td>
            </tr>

            <!-- 섹션 4: 주력 전술 / 경기 스타일 / 상성 -->
            <tr>
                <th bgcolor="#cbd5e1" colspan="2" style="background-color: #cbd5e1; padding: 8px 14px; font-size: 12px; color: #1e293b; text-align: left; border-bottom: 1px solid #94a3b8;">
                    ♟️ 주력 전술 · 경기 스타일 · 점유율/득점대/수비 상성
                </th>
            </tr>
            <tr>
                <td bgcolor="#ffffff" colspan="2" style="background-color: #ffffff; padding: 10px 14px; border-bottom: 1px solid #cbd5e1; font-size: 12px; color: #334155; line-height: 1.7;">
                    <b style="color: #0f172a;">• 주력 포메이션:</b> {tac_html} &nbsp;(전술 유연성: 총 <b>{rpt['tac_cnt']}종</b> · 주력 비중 <b>{rpt['main_tac_pct']}%</b>)<br>
                    <b style="color: #0f172a;">• 경기 스타일:</b> 평균 점유율 <b>{rpt['avg_poss']}%</b> · 패스 <b>{rpt['avg_pass']}%</b> · 경고 <b>{rpt['avg_yc']}장</b>(퇴장 {rpt['tot_rc']}회) · 상대 경고 유도 <b>{rpt['opp_avg_yc']}장</b><br>
                    <b style="color: #0f172a;">• 점유율별 승률:</b> 지공형(55%↑) <b>{rpt['pos_high_str']}</b> &nbsp;|&nbsp; 역습형(45%↓) <b>{rpt['pos_low_str']}</b><br>
                    <b style="color: #0f172a;">• 경기 양상별:</b> 화력전(3골↑) 승률 <b>{rpt['high_g_win']}</b> &nbsp;|&nbsp; 진흙탕(2골↓) 승률 <b>{rpt['low_g_win']}</b> &nbsp;|&nbsp; 1골차↓ 접전 <b>{rpt['tight_g_pct']}%</b> · 4골↑ 난타전 <b>{rpt['wild_g_pct']}%</b><br>
                    <b style="color: #0f172a;">• 상대 수비 상성:</b> vs 3백 <b>{rpt['vs_3b_str']}</b> &nbsp;|&nbsp; vs 4백 <b>{rpt['vs_4b_str']}</b> &nbsp;|&nbsp; 최근 5경기 폼: 득점 {rpt['r5_gf']} ({rpt['r5_gf_diff']:+.2f}) · xG {rpt['r5_xg']} ({rpt['r5_xg_diff']:+.2f})
                </td>
            </tr>
        </table>

        <!-- 섹션 5: 최근 5경기 상세 매치 로그 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="#cbd5e1" colspan="6" style="background-color: #cbd5e1; padding: 8px 14px; font-size: 12px; color: #1e293b; text-align: left; border-bottom: 1px solid #94a3b8;">
                    📅 최근 5경기 상세 매치 로그
                </th>
            </tr>
            <tr>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">날짜</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">장소</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: left; border-bottom: 1px solid #cbd5e1;">상대팀</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">스코어</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">xG / xGA</th>
                <th bgcolor="#e2e8f0" style="padding: 6px; font-size: 11px; color: #1e293b; text-align: center; border-bottom: 1px solid #cbd5e1;">배트맨 승배당</th>
            </tr>
            {log_rows_html}
        </table>

        <!-- 섹션 6: 초보자를 위한 용어·지표 완벽 가이드 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="#1e293b" style="background-color: #1e293b; padding: 8px 14px; font-size: 12px; color: #fbbf24; text-align: left;">
                    📖 처음 보시는 분들을 위한 핵심 용어·지표 쉬운 설명서
                </th>
            </tr>
            <tr>
                <td bgcolor="#f8fafc" style="background-color: #f8fafc; padding: 12px 16px; font-size: 11px; color: #334155; line-height: 1.75; border-top: 1px solid #cbd5e1;">
                    <b style="color: #0f172a;">① xG(기대득점) · xGA(기대실점) · xGD(기대득실차):</b> 슈팅 위치와 찬스 난이도를 바탕으로 "원래 몇 골을 넣거나 먹혔어야 정상인지" 계산한 수치입니다. 실제 득점이 xG보다 높으면 <b>골 결정력이 좋은 팀</b>, 실제 실점이 xGA보다 낮으면 <b>수비·키퍼가 잘 버틴 팀</b>입니다. xGD(+)가 높을수록 경기 내용 자체가 상대를 압도했다는 뜻입니다.<br>
                    <b style="color: #0f172a;">② xPts(기대승점):</b> 경기 내용(xG/xGA)만 놓고 봤을 때 원래 얻었어야 할 승점입니다. 실제 승점이 xPts보다 훨씬 높다면 <b>운이 좋았던(거품 주의)</b> 상태, 반대로 xPts가 훨씬 높다면 <b>경기력 대비 운이 없었던(반등 가능성)</b> 상태입니다.<br>
                    <b style="color: #0f172a;">③ 슈팅당 xG &amp; 허용 슈팅당 xGA:</b> 슈팅 1개당 골 확률입니다. 공격 시 높으면 <b>확실한 찬스만 노리는 고효율 팀</b>, 수비 시 낮으면 <b>위험한 찬스는 안 주고 중거리만 허용하는 단단한 수비</b>입니다.<br>
                    <b style="color: #0f172a;">④ 배당 수익률(ROI) &amp; 무승부 ROI:</b> 매 경기 이 팀의 승리(또는 무승부)에 똑같은 금액을 걸었을 때의 누적 수익률입니다. 플러스(+)면 <b>배당 대비 돈이 되는 효자 팀</b>, 마이너스(-)면 <b>배당 거품이 낀 팀</b>입니다.<br>
                    <b style="color: #0f172a;">⑤ 배트맨 경계 구간 vs 가치 구간:</b> 배트맨은 해외보다 환급률이 낮아 단순 배당 비교가 어렵습니다. 환급률 차이를 보정했을 때, <b>경계 구간</b>은 배트맨이 해외보다 배당을 유독 낮게(짜게) 깎아 승리를 경계한 경기이며, <b>가치 구간</b>은 반대로 배당을 후하게 준 경기입니다.<br>
                    <b style="color: #0f172a;">⑥ 초정배(≤1.5) 함정 지수 &amp; 정배 마핸(-1.0):</b> 배당 1.50 이하의 압도적 우승 후보로 평가받았을 때 비기거나 져서 <b>미끄러진 비율(함정)</b>과, 정배를 받았을 때 실제로 <b>2골 차 이상 대승(마핸)</b>을 거둔 비율입니다.<br>
                    <b style="color: #0f172a;">⑦ CS / BTTS / 키퍼 선방률:</b> <b>CS(클린시트)</b>는 무실점 경기 비율, <b>BTTS</b>는 양 팀 모두 골을 넣은 경기 비율, <b>선방률</b>은 상대 유효슈팅 중 골키퍼가 막아낸 비율입니다.
                </td>
            </tr>
        </table>
    </div>
    """
    return html


def render_tab8_scouting(spreadsheet_id, overseas_bookmakers):
    st.subheader("📋 팀 종합 스카우팅 리포트 (경기내용 + 9대 배당 교차 분석)")
    st.caption("시즌, 리그, 팀 및 원하는 핸디캡/언오버 기준점을 선택하면 성적·홈/원정·xG/xPts·키퍼·전술·배당 DNA·최근 5경기 로그·초보자 용어 가이드까지 한 번에 출력합니다.")

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

    c_opt1, c_opt2 = st.columns([2, 1])
    sel_hc_lines = c_opt1.multiselect(
        "🎯 스카우팅 핸디캡 기준점 (복수 선택 가능 · 클릭 선택)",
        HC_OPTIONS,
        default=[-1.0, 1.0],
        format_func=format_hc_label,
        key="scout_hc_lines"
    )
    sel_ou_line = float(c_opt2.selectbox(
        "⚡ 스카우팅 언오버 기준점",
        OU_OPTIONS,
        index=OU_OPTIONS.index(2.5),
        key="scout_ou_line"
    ))
    hc_lines_used = sort_hc_lines(sel_hc_lines) if sel_hc_lines else [-1.0, 1.0]

    if st.button(f"🔍 [{sel_team}] 종합 스카우팅 리포트 생성하기", type="primary", use_container_width=True, key="btn_run_scouting"):
        with st.spinner(f"[{sel_team}] 경기내용 및 배트맨·해외 8개사 배당 데이터를 교차 분석 중입니다..."):
            bm_lookup, ov_lookup = _build_odds_lookups_cached(spreadsheet_id, tuple(overseas_bookmakers))

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
                for t_name, gf, ga, xg in [(hm, hg, ag, h_xg), (aw, ag, hg, a_xg)]:
                    team_league_agg.setdefault(t_name, {"gf": [], "ga": [], "xg": []})
                    team_league_agg[t_name]["gf"].append(gf)
                    team_league_agg[t_name]["ga"].append(ga)
                    team_league_agg[t_name]["xg"].append(xg)

            def _get_rank_str(metric_key, ascending=False):
                avgs = [(tn, float(np.mean(v[metric_key]))) for tn, v in team_league_agg.items() if v[metric_key]]
                if not avgs:
                    return "-"
                avgs.sort(key=lambda x: x[1], reverse=not ascending)
                for idx_r, (tn, _) in enumerate(avgs, 1):
                    if tn == sel_team:
                        return f"{idx_r}위/{len(avgs)}팀"
                return "-"

            matches = []
            for _, r in df_filtered.iterrows():
                hm = str(r.get("홈팀", "")).strip()
                aw = str(r.get("원정팀", "")).strip()
                if hm != sel_team and aw != sel_team:
                    continue

                is_home = (hm == sel_team)
                sn = str(r.get("시즌", "")).strip()
                dt = str(r.get("경기날짜", "")).strip()
                ndt = _norm_date(dt)

                gf_1h = _to_float(r.get("전반득점_홈" if is_home else "전반득점_원"))
                gf_2h = _to_float(r.get("후반득점_홈" if is_home else "후반득점_원"))
                ga_1h = _to_float(r.get("전반득점_원" if is_home else "전반득점_홈"))
                ga_2h = _to_float(r.get("후반득점_원" if is_home else "후반득점_홈"))
                gf, ga = gf_1h + gf_2h, ga_1h + ga_2h

                xg = _to_float(r.get("xG_홈" if is_home else "xG_원"))
                xga = _to_float(r.get("xG_원" if is_home else "xG_홈"))
                shots = _to_float(r.get("슈팅_홈" if is_home else "슈팅_원"))
                opp_shots = _to_float(r.get("슈팅_원" if is_home else "슈팅_홈"))
                sot = _to_float(r.get("유효슈팅_홈" if is_home else "유효슈팅_원"))
                opp_sot = _to_float(r.get("유효슈팅_원" if is_home else "유효슈팅_홈"))
                poss = _to_float(r.get("점유율_홈" if is_home else "점유율_원"))
                pass_pct = _to_float(r.get("패스성공률_홈" if is_home else "패스성공률_원"))
                yc = _to_float(r.get("경고_홈" if is_home else "경고_원"))
                opp_yc = _to_float(r.get("경고_원" if is_home else "경고_홈"))
                rc = _to_float(r.get("퇴장_홈" if is_home else "퇴장_원"))
                my_tac = str(r.get("전술_홈" if is_home else "전술_원", "")).strip()
                opp_tac = str(r.get("전술_원" if is_home else "전술_홈", "")).strip()

                res = "승" if gf > ga else ("무" if gf == ga else "패")

                bm_odds = _lookup_odds(bm_lookup, ndt, sn, hm, aw)
                ov_odds = _lookup_odds(ov_lookup, ndt, sn, hm, aw)

                team_bm_odd = (bm_odds[0] if is_home else bm_odds[2]) if bm_odds else 0.0
                draw_bm_odd = bm_odds[1] if bm_odds else 0.0
                opp_bm_odd = (bm_odds[2] if is_home else bm_odds[0]) if bm_odds else 0.0
                is_fav = (team_bm_odd > 0 and opp_bm_odd > 0 and team_bm_odd < opp_bm_odd)
                is_dog = (team_bm_odd > 0 and opp_bm_odd > 0 and team_bm_odd > opp_bm_odd)

                bm_react = None
                if bm_odds and ov_odds:
                    bm_inv = (1 / bm_odds[0]) + (1 / bm_odds[1]) + (1 / bm_odds[2])
                    ov_inv = (1 / ov_odds[0]) + (1 / ov_odds[1]) + (1 / ov_odds[2])
                    if bm_inv > 0 and ov_inv > 0:
                        bm_prob = (1 / team_bm_odd) / bm_inv
                        ov_team_odd = ov_odds[0] if is_home else ov_odds[2]
                        ov_prob = (1 / ov_team_odd) / ov_inv
                        bm_react = "tight" if bm_prob > ov_prob else "value"

                matches.append({
                    "sort_k": ndt, "date": dt, "is_home": is_home, "opp": aw if is_home else hm,
                    "gf_1h": gf_1h, "gf_2h": gf_2h, "ga_1h": ga_1h, "ga_2h": ga_2h,
                    "gf": gf, "ga": ga, "xg": xg, "xga": xga,
                    "shots": shots, "opp_shots": opp_shots, "sot": sot, "opp_sot": opp_sot,
                    "poss": poss, "pass_pct": pass_pct, "yc": yc, "opp_yc": opp_yc, "rc": rc,
                    "my_tac": my_tac, "opp_tac": opp_tac, "res": res,
                    "team_bm_odd": team_bm_odd, "draw_bm_odd": draw_bm_odd,
                    "is_fav": is_fav, "is_dog": is_dog, "bm_react": bm_react
                })

            matches.sort(key=lambda x: x["sort_k"])
            total_n = len(matches)
            if total_n == 0:
                st.info(f"💡 [{sel_team}]의 경기 데이터가 없습니다.")
                return

            w = sum(1 for m in matches if m["res"] == "승")
            d = sum(1 for m in matches if m["res"] == "무")
            l = sum(1 for m in matches if m["res"] == "패")
            win_pct = round((w / total_n) * 100, 1)
            draw_pct = round((d / total_n) * 100, 1)
            pts = w * 3 + d
            xpts = round(sum(_poisson_xpts(m["xg"], m["xga"]) for m in matches), 1)
            pts_diff = round(pts - xpts, 1)

            def _split_stats(sub):
                n = len(sub)
                if n == 0:
                    return 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                sw = sum(1 for m in sub if m["res"] == "승")
                sd = sum(1 for m in sub if m["res"] == "무")
                sl = sum(1 for m in sub if m["res"] == "패")
                wp = round((sw / n) * 100, 1)
                gf_a = round(float(np.mean([m["gf"] for m in sub])), 2)
                ga_a = round(float(np.mean([m["ga"] for m in sub])), 2)
                xg_a = round(float(np.mean([m["xg"] for m in sub])), 2)
                xga_a = round(float(np.mean([m["xga"] for m in sub])), 2)
                pos_vals = [m["poss"] for m in sub if m["poss"] > 0]
                pos_a = round(float(np.mean(pos_vals)), 1) if pos_vals else 0.0
                ov_p = round((sum(1 for m in sub if (m["gf"] + m["ga"]) > sel_ou_line) / n) * 100, 1)
                ppg = round((sw * 3 + sd) / n, 2)
                return n, sw, sd, sl, wp, gf_a, ga_a, xg_a, xga_a, pos_a, ov_p, ppg

            h_n, hw, hd, hl, h_win_pct, h_gf, h_ga, h_xg, h_xga, h_poss, h_ov_pct, h_ppg = _split_stats([m for m in matches if m["is_home"]])
            a_n, aw, ad, al, a_win_pct, a_gf, a_ga, a_xg, a_xga, a_poss, a_ov_pct, a_ppg = _split_stats([m for m in matches if not m["is_home"]])

            if h_n >= 2 and a_n >= 2:
                ha_gap_label = "🏠 극단적 안방 여포" if (h_ppg - a_ppg >= 0.8) else ("🚗 원정 깡패 성향" if (a_ppg - h_ppg >= 0.8) else "⚖️ 홈/원정 균형형")
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

            # 공수 & 키퍼 & 슈팅 퀄리티
            avg_gf = round(float(np.mean([m["gf"] for m in matches])), 2)
            avg_ga = round(float(np.mean([m["ga"] for m in matches])), 2)
            avg_xg = round(float(np.mean([m["xg"] for m in matches])), 2)
            avg_xga = round(float(np.mean([m["xga"] for m in matches])), 2)
            xg_diff = round(avg_gf - avg_xg, 2)
            xga_diff = round(avg_ga - avg_xga, 2)
            xgd = round(avg_xg - avg_xga, 2)
            sot_margin = round(float(np.mean([m["sot"] - m["opp_sot"] for m in matches])), 1)

            cs_pct = round((sum(1 for m in matches if m["ga"] == 0) / total_n) * 100, 1)
            gf2_pct = round((sum(1 for m in matches if m["gf"] >= 2) / total_n) * 100, 1)
            ga2_pct = round((sum(1 for m in matches if m["ga"] >= 2) / total_n) * 100, 1)

            tot_shots = sum(m["shots"] for m in matches)
            tot_opp_shots = sum(m["opp_shots"] for m in matches)
            tot_sot = sum(m["sot"] for m in matches)
            tot_opp_sot = sum(m["opp_sot"] for m in matches)
            tot_gf = sum(m["gf"] for m in matches)
            tot_ga = sum(m["ga"] for m in matches)
            tot_xg = sum(m["xg"] for m in matches)
            tot_xga = sum(m["xga"] for m in matches)

            xg_per_shot = round(tot_xg / tot_shots, 3) if tot_shots > 0 else 0.0
            xga_per_shot = round(tot_xga / tot_opp_shots, 3) if tot_opp_shots > 0 else 0.0
            shot_acc_pct = round((tot_sot / tot_shots) * 100, 1) if tot_shots > 0 else 0.0
            sot_conv_pct = round((tot_gf / tot_sot) * 100, 1) if tot_sot > 0 else 0.0
            gk_save_pct = round(max(0.0, (tot_opp_sot - tot_ga) / tot_opp_sot) * 100, 1) if tot_opp_sot > 0 else 0.0

            # 전·후반 패턴 & 멘탈
            fh_score_pct = round((sum(1 for m in matches if m["gf_1h"] > 0) / total_n) * 100, 1)
            fh_cs_pct = round((sum(1 for m in matches if m["ga_1h"] == 0) / total_n) * 100, 1)
            sh_gd_avg = round(float(np.mean([m["gf_2h"] - m["ga_2h"] for m in matches])), 2)
            tot_ga_2h = sum(m["ga_2h"] for m in matches)
            sh_ga_share = round((tot_ga_2h / tot_ga) * 100, 1) if tot_ga > 0 else 0.0

            ht_leads = [m for m in matches if m["gf_1h"] > m["ga_1h"]]
            ht_lead_w = sum(1 for m in ht_leads if m["res"] == "승")
            ht_lead_win_pct = round((ht_lead_w / len(ht_leads)) * 100, 1) if ht_leads else 0.0
            ht_lead_str = f"{ht_lead_w}/{len(ht_leads)}경기"

            ht_draws = [m for m in matches if m["gf_1h"] == m["ga_1h"]]
            ht_draw_n = len(ht_draws)
            ht_draw_w = round((sum(1 for m in ht_draws if m["res"] == "승") / ht_draw_n) * 100, 1) if ht_draw_n else 0.0
            ht_draw_d = round((sum(1 for m in ht_draws if m["res"] == "무") / ht_draw_n) * 100, 1) if ht_draw_n else 0.0
            ht_draw_l = round((sum(1 for m in ht_draws if m["res"] == "패") / ht_draw_n) * 100, 1) if ht_draw_n else 0.0

            ht_trails = [m for m in matches if m["gf_1h"] < m["ga_1h"]]
            ht_trail_pts = sum(1 for m in ht_trails if m["res"] in ("승", "무"))
            ht_trail_pts_pct = round((ht_trail_pts / len(ht_trails)) * 100, 1) if ht_trails else 0.0
            ht_trail_str = f"{ht_trail_pts}/{len(ht_trails)}경기"

            after_win = [matches[i] for i in range(1, total_n) if matches[i - 1]["res"] == "승"]
            after_win_pct = f"{round((sum(1 for m in after_win if m['res'] == '승') / len(after_win)) * 100, 1)}% ({len(after_win)}전)" if after_win else "-"

            after_loss = [matches[i] for i in range(1, total_n) if matches[i - 1]["res"] == "패"]
            if after_loss:
                bounce_win_pct = f"{round((sum(1 for m in after_loss if m['res'] == '승') / len(after_loss)) * 100, 1)}% ({len(after_loss)}전)"
                bounce_unb_pct = f"{round((sum(1 for m in after_loss if m['res'] != '패') / len(after_loss)) * 100, 1)}%"
            else:
                bounce_win_pct, bounce_unb_pct = "-", "-"

            # 언오버 & 핸디캡 & 무승부
            sel_ov_pct = round((sum(1 for m in matches if (m["gf"] + m["ga"]) > sel_ou_line) / total_n) * 100, 1)
            sel_un_pct = round(100.0 - sel_ov_pct, 1)
            ov15_pct = round((sum(1 for m in matches if (m["gf"] + m["ga"]) > 1.5) / total_n) * 100, 1)
            ov25_pct = round((sum(1 for m in matches if (m["gf"] + m["ga"]) > 2.5) / total_n) * 100, 1)
            ov35_pct = round((sum(1 for m in matches if (m["gf"] + m["ga"]) > 3.5) / total_n) * 100, 1)
            btts_pct = round((sum(1 for m in matches if m["gf"] > 0 and m["ga"] > 0) / total_n) * 100, 1)
            top_scores = Counter(f"{int(m['gf'])}:{int(m['ga'])}" for m in matches).most_common(3)
            low_draw_cnt = sum(1 for m in matches if (m["gf"] == 0 and m["ga"] == 0) or (m["gf"] == 1 and m["ga"] == 1))

            hc_stats = []
            for hc_v in hc_lines_used:
                hw_c = sum(1 for m in matches if (m["gf"] + hc_v) > m["ga"])
                hd_c = sum(1 for m in matches if (m["gf"] + hc_v) == m["ga"])
                hl_c = total_n - hw_c - hd_c
                hc_stats.append({
                    "label": format_hc_label(hc_v),
                    "w_pct": round((hw_c / total_n) * 100, 1),
                    "d_pct": round((hd_c / total_n) * 100, 1),
                    "l_pct": round((hl_c / total_n) * 100, 1),
                })

            # 배당 DNA & 정배 심화 & 무승부 ROI
            bm_valid = [m for m in matches if m["team_bm_odd"] >= 1.01]
            if bm_valid:
                roi_return = sum(m["team_bm_odd"] for m in bm_valid if m["res"] == "승")
                roi_pct = round(((roi_return - len(bm_valid)) / len(bm_valid)) * 100, 1)
                draw_ret = sum(m["draw_bm_odd"] for m in bm_valid if m["res"] == "무")
                draw_roi_pct = round(((draw_ret - len(bm_valid)) / len(bm_valid)) * 100, 1)
            else:
                roi_pct, draw_roi_pct = 0.0, 0.0

            fav_ms = [m for m in bm_valid if m["is_fav"]]
            fav_win_pct = round((sum(1 for m in fav_ms if m["res"] == "승") / len(fav_ms)) * 100, 1) if fav_ms else 0.0
            fav_m1_pct = f"{round((sum(1 for m in fav_ms if (m['gf'] - m['ga']) >= 2) / len(fav_ms)) * 100, 1)}% ({len(fav_ms)}전)" if fav_ms else "-"

            super_fav = [m for m in bm_valid if m["team_bm_odd"] <= 1.50]
            trap_pct = f"{round((sum(1 for m in super_fav if m['res'] != '승') / len(super_fav)) * 100, 1)}% ({len(super_fav)}전)" if super_fav else "-"

            dog_ms = [m for m in bm_valid if m["is_dog"]]
            dog_pts_pct = round((sum(1 for m in dog_ms if m["res"] in ("승", "무")) / len(dog_ms)) * 100, 1) if dog_ms else 0.0

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

            tight_ms = [m for m in matches if m["bm_react"] == "tight"]
            value_ms = [m for m in matches if m["bm_react"] == "value"]
            bm_tight_pct = f"{round((sum(1 for m in tight_ms if m['res'] == '승') / len(tight_ms)) * 100, 1)}% ({len(tight_ms)}전)" if tight_ms else "-"
            bm_value_pct = f"{round((sum(1 for m in value_ms if m['res'] == '승') / len(value_ms)) * 100, 1)}% ({len(value_ms)}전)" if value_ms else "-"

            # 전술 & 스타일 & 점유율/득점대/수비 상성
            tac_groups = {}
            for m in matches:
                if m["my_tac"]:
                    tac_groups.setdefault(m["my_tac"], []).append(m["res"])
            tac_total_valid = sum(len(v) for v in tac_groups.values())
            top_tactics = sorted(
                [{"tac": k, "cnt": len(v), "win_pct": round((sum(1 for x in v if x == "승") / len(v)) * 100, 1)} for k, v in tac_groups.items()],
                key=lambda x: x["cnt"], reverse=True
            )[:3]
            tac_cnt = len(tac_groups)
            main_tac_pct = round((top_tactics[0]["cnt"] / tac_total_valid) * 100, 1) if (top_tactics and tac_total_valid > 0) else 0.0

            pos_all = [m["poss"] for m in matches if m["poss"] > 0]
            pas_all = [m["pass_pct"] for m in matches if m["pass_pct"] > 0]
            avg_poss = round(float(np.mean(pos_all)), 1) if pos_all else 0.0
            avg_pass = round(float(np.mean(pas_all)), 1) if pas_all else 0.0
            avg_yc = round(float(np.mean([m["yc"] for m in matches])), 2)
            opp_avg_yc = round(float(np.mean([m["opp_yc"] for m in matches])), 2)
            tot_rc = int(sum(m["rc"] for m in matches))

            pos_hi = [m for m in matches if m["poss"] >= 55]
            pos_lo = [m for m in matches if 0 < m["poss"] <= 45]
            pos_high_str = f"{round((sum(1 for m in pos_hi if m['res']=='승')/len(pos_hi))*100,1)}% ({len(pos_hi)}전)" if pos_hi else "-"
            pos_low_str = f"{round((sum(1 for m in pos_lo if m['res']=='승')/len(pos_lo))*100,1)}% ({len(pos_lo)}전)" if pos_lo else "-"

            high_g = [m for m in matches if (m["gf"] + m["ga"]) >= 3]
            low_g = [m for m in matches if (m["gf"] + m["ga"]) <= 2]
            high_g_win = f"{round((sum(1 for m in high_g if m['res']=='승')/len(high_g))*100,1)}% ({len(high_g)}전)" if high_g else "-"
            low_g_win = f"{round((sum(1 for m in low_g if m['res']=='승')/len(low_g))*100,1)}% ({len(low_g)}전)" if low_g else "-"
            tight_g_pct = round((sum(1 for m in matches if abs(m["gf"] - m["ga"]) <= 1) / total_n) * 100, 1)
            wild_g_pct = round((sum(1 for m in matches if (m["gf"] + m["ga"]) >= 4) / total_n) * 100, 1)

            vs_3b = [m for m in matches if m["opp_tac"].startswith("3")]
            vs_4b = [m for m in matches if m["opp_tac"].startswith("4")]
            vs_3b_str = f"승률 {round((sum(1 for m in vs_3b if m['res']=='승')/len(vs_3b))*100,1)}% ({len(vs_3b)}전)" if vs_3b else "-"
            vs_4b_str = f"승률 {round((sum(1 for m in vs_4b if m['res']=='승')/len(vs_4b))*100,1)}% ({len(vs_4b)}전)" if vs_4b else "-"

            r5 = matches[-5:]
            r5_gf = round(float(np.mean([m["gf"] for m in r5])), 2)
            r5_xg = round(float(np.mean([m["xg"] for m in r5])), 2)

            tags = []
            if win_pct >= 60: tags.append("#상위권강호")
            if h_ppg - a_ppg >= 0.8 and h_n >= 2: tags.append("#안방여포")
            if a_ppg - h_ppg >= 0.8 and a_n >= 2: tags.append("#원정깡패")
            if sel_ov_pct >= 60: tags.append(f"#{sel_ou_line}오버형")
            elif sel_ov_pct <= 40: tags.append(f"#{sel_ou_line}언더형")
            if xg_diff >= 0.25: tags.append("#골결정력우수")
            if xga_diff <= -0.25: tags.append("#짠물수비")
            if fav_win_pct >= 75 and len(fav_ms) >= 3: tags.append("#정배신뢰최상")
            if roi_pct >= 15 and len(bm_valid) >= 3: tags.append("#배당효자팀")
            if not tags: tags.append("#밸런스형")

            rpt = {
                "season": sel_season, "league": sel_league, "team": sel_team,
                "total_n": total_n, "w": w, "d": d, "l": l, "win_pct": win_pct, "draw_pct": draw_pct,
                "pts": pts, "xpts": xpts, "pts_diff": pts_diff,
                "h_n": h_n, "hw": hw, "hd": hd, "hl": hl, "h_win_pct": h_win_pct,
                "h_gf": h_gf, "h_ga": h_ga, "h_xg": h_xg, "h_xga": h_xga, "h_poss": h_poss, "h_ov_pct": h_ov_pct, "h_ppg": h_ppg,
                "a_n": a_n, "aw": aw, "ad": ad, "al": al, "a_win_pct": a_win_pct,
                "a_gf": a_gf, "a_ga": a_ga, "a_xg": a_xg, "a_xga": a_xga, "a_poss": a_poss, "a_ov_pct": a_ov_pct, "a_ppg": a_ppg,
                "ha_gap_label": ha_gap_label, "recent5_list": recent5_list, "recent5_detail": list(reversed(r5)),
                "streak_text": streak_text,
                "avg_gf": avg_gf, "avg_ga": avg_ga, "avg_xg": avg_xg, "avg_xga": avg_xga,
                "xg_diff": xg_diff, "xga_diff": xga_diff, "xgd": xgd, "sot_margin": sot_margin,
                "cs_pct": cs_pct, "gf2_pct": gf2_pct, "ga2_pct": ga2_pct,
                "xg_per_shot": xg_per_shot, "xga_per_shot": xga_per_shot, "shot_acc_pct": shot_acc_pct,
                "sot_conv_pct": sot_conv_pct, "gk_save_pct": gk_save_pct,
                "rank_gf": _get_rank_str("gf", False), "rank_ga": _get_rank_str("ga", True), "rank_xg": _get_rank_str("xg", False),
                "fh_score_pct": fh_score_pct, "fh_cs_pct": fh_cs_pct, "sh_gd_avg": sh_gd_avg, "sh_ga_share": sh_ga_share,
                "ht_lead_win_pct": ht_lead_win_pct, "ht_lead_str": ht_lead_str,
                "ht_draw_n": ht_draw_n, "ht_draw_w": ht_draw_w, "ht_draw_d": ht_draw_d, "ht_draw_l": ht_draw_l,
                "ht_trail_pts_pct": ht_trail_pts_pct, "ht_trail_str": ht_trail_str,
                "after_win_pct": after_win_pct, "bounce_win_pct": bounce_win_pct, "bounce_unb_pct": bounce_unb_pct,
                "sel_ou": sel_ou_line, "sel_ov_pct": sel_ov_pct, "sel_un_pct": sel_un_pct,
                "ov15_pct": ov15_pct, "ov25_pct": ov25_pct, "ov35_pct": ov35_pct,
                "btts_pct": btts_pct, "top_scores": top_scores, "low_draw_cnt": low_draw_cnt, "hc_stats": hc_stats,
                "bm_matched_n": len(bm_valid), "roi_pct": roi_pct, "draw_roi_pct": draw_roi_pct,
                "fav_win_pct": fav_win_pct, "fav_m1_pct": fav_m1_pct, "trap_pct": trap_pct, "dog_pts_pct": dog_pts_pct,
                "vs_weak_pct": vs_weak_pct, "vs_weak_rec": vs_weak_rec,
                "vs_mid_pct": vs_mid_pct, "vs_mid_rec": vs_mid_rec,
                "vs_strong_pct": vs_strong_pct, "vs_strong_rec": vs_strong_rec,
                "bm_tight_pct": bm_tight_pct, "bm_value_pct": bm_value_pct,
                "top_tactics": top_tactics, "tac_cnt": tac_cnt, "main_tac_pct": main_tac_pct,
                "avg_poss": avg_poss, "avg_pass": avg_pass, "avg_yc": avg_yc, "opp_avg_yc": opp_avg_yc, "tot_rc": tot_rc,
                "pos_high_str": pos_high_str, "pos_low_str": pos_low_str,
                "high_g_win": high_g_win, "low_g_win": low_g_win, "tight_g_pct": tight_g_pct, "wild_g_pct": wild_g_pct,
                "vs_3b_str": vs_3b_str, "vs_4b_str": vs_4b_str,
                "r5_gf": r5_gf, "r5_xg": r5_xg, "r5_gf_diff": round(r5_gf - avg_gf, 2), "r5_xg_diff": round(r5_xg - avg_xg, 2),
                "tags": tags
            }
            st.session_state["t8_last_rpt_v3"] = rpt

    if "t8_last_rpt_v3" in st.session_state:
        rpt = st.session_state["t8_last_rpt_v3"]
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("시즌 성적 (승점 vs xPts)", f"{rpt['w']}승 {rpt['d']}무 {rpt['l']}패", f"{rpt['pts']}점 vs {rpt['xpts']}점 ({rpt['pts_diff']:+.1f})")
        m2.metric("평균 득/실 (키퍼 선방률)", f"{rpt['avg_gf']} / {rpt['avg_ga']}", f"xGD {rpt['xgd']:+.2f} · 선방 {rpt['gk_save_pct']}%")
        m3.metric(f"승/무 ROI ({rpt['bm_matched_n']}건)", f"{rpt['roi_pct']:+.1f}% / {rpt['draw_roi_pct']:+.1f}%", f"정배 {rpt['fav_win_pct']}% · 역배승점 {rpt['dog_pts_pct']}%")
        m4.metric(f"{rpt['sel_ou']} 오버 / BTTS", f"{rpt['sel_ov_pct']}% / {rpt['btts_pct']}%", f"2득점↑ {rpt['gf2_pct']}% · 2실점↑ {rpt['ga2_pct']}%")

        with st.expander("📊 / 📋 [네이버 블로그/카페 전용] 팀 종합 스카우팅 리포트 인포그래픽 복사 (추천 ⭐)", expanded=True):
            st.caption("초록색 버튼을 1번 클릭한 뒤 네이버 블로그/카페 글쓰기 창에서 Ctrl+V 하세요! (하단 용어 설명서까지 함께 복사됩니다)")
            ig_html = generate_naver_scouting_infographic(rpt)
            render_clipboard_component(ig_html, "t8_clip_scouting_v3", height=1250)
