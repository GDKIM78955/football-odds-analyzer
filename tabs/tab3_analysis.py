import streamlit as st
import pandas as pd
import numpy as np
from database import load_sheet_data
from infographics import generate_naver_odds_with_handicap_infographic, generate_naver_odds_infographic, render_clipboard_component


def normalize_bm_dataframe(df_bm):
    if df_bm.empty:
        return df_bm
    arr = df_bm.to_numpy(dtype=object).copy()
    n_rows, n_cols = arr.shape
    if n_cols >= 35:
        for r_i in range(n_rows):
            res_idx = None
            for c_i in range(n_cols - 1, 27, -1):
                val = str(arr[r_i, c_i]).strip()
                if val in ("홈승", "무승부", "원정승"):
                    res_idx = c_i
                    break
            if res_idx is not None and res_idx != 34 and res_idx >= 34:
                block = []
                for offset in range(-6, 2):
                    src_c = res_idx + offset
                    block.append(arr[r_i, src_c] if 0 <= src_c < n_cols else "")
                for idx_b, val_b in enumerate(block):
                    dst_c = 28 + idx_b
                    if dst_c < n_cols:
                        arr[r_i, dst_c] = val_b

    new_cols = []
    seen = {}
    for i, c in enumerate(df_bm.columns):
        c_str = str(c).strip()
        if not c_str:
            c_str = "적중배당" if i == 35 else f"_extra_{i}"
        if c_str in seen:
            seen[c_str] += 1
            c_str = f"{c_str}_{seen[c_str]}"
        else:
            seen[c_str] = 1
        new_cols.append(c_str)
    return pd.DataFrame(arr, columns=new_cols)


def generate_naver_match_history_infographic(
    records, league_name="", home_team="", away_team="", ou_line=2.5, scope_label="전체 리그"
):
    title_match = f"{home_team} vs {away_team}" if (home_team and away_team) else "분석 대상 경기"
    title_lg = f"[{league_name}] " if league_name else ""

    if not records:
        return f"""
        <div style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 680px; margin: 0 auto; border: 1px solid #cbd5e1; border-radius: 10px; padding: 20px; text-align: center; color: #64748b;">
            조건에 일치하는 과거 매칭 경기 내역이 없습니다.
        </div>
        """

    total_cnt = len(records)
    hw_cnt = sum(1 for r in records if r["res"] == "홈승")
    dr_cnt = sum(1 for r in records if r["res"] == "무승부")
    aw_cnt = sum(1 for r in records if r["res"] == "원정승")

    hw_pct = round((hw_cnt / total_cnt) * 100, 1) if total_cnt > 0 else 0.0
    dr_pct = round((dr_cnt / total_cnt) * 100, 1) if total_cnt > 0 else 0.0
    aw_pct = round((aw_cnt / total_cnt) * 100, 1) if total_cnt > 0 else 0.0

    valid_sc_records = [r for r in records if r["hs"] is not None and r["as"] is not None]
    sc_cnt = len(valid_sc_records)
    if sc_cnt > 0:
        avg_h = round(sum(r["hs"] for r in valid_sc_records) / sc_cnt, 2)
        avg_a = round(sum(r["as"] for r in valid_sc_records) / sc_cnt, 2)
        avg_tot = round(avg_h + avg_a, 2)
        ov_cnt = sum(1 for r in valid_sc_records if (r["hs"] + r["as"]) > ou_line)
        un_cnt = sc_cnt - ov_cnt
        ov_pct = round((ov_cnt / sc_cnt) * 100, 1)
        un_pct = round((un_cnt / sc_cnt) * 100, 1)
    else:
        avg_h, avg_a, avg_tot = 0.0, 0.0, 0.0
        ov_cnt, un_cnt, ov_pct, un_pct = 0, 0, 0.0, 0.0

    # 승무패 비율 바 너비 보정
    w_bar = max(hw_pct, 8.0) if hw_cnt > 0 else 0.0
    d_bar = max(dr_pct, 8.0) if dr_cnt > 0 else 0.0
    a_bar = max(aw_pct, 8.0) if aw_cnt > 0 else 0.0
    bar_sum = w_bar + d_bar + a_bar
    if bar_sum > 0:
        w_bar = round((w_bar / bar_sum) * 100, 1)
        d_bar = round((d_bar / bar_sum) * 100, 1)
        a_bar = round(100.0 - w_bar - d_bar, 1)

    rows_html = ""
    for idx, r in enumerate(records):
        bg_row = "#ffffff" if idx % 2 == 0 else "#f8fafc"
        r_date = r["date"]
        r_lg = r["league"]
        r_home = r["home"]
        r_away = r["away"]
        r_res = r["res"]
        hs, as_sc = r["hs"], r["as"]

        # 홈/원정 승리 팀 강조 스타일
        if r_res == "홈승":
            h_style = "font-weight: 800; color: #1e3a8a;"
            a_style = "font-weight: 500; color: #64748b;"
            res_badge_bg = "#dbeafe"
            res_badge_fg = "#1d4ed8"
            res_badge_border = "#93c5fd"
            res_label = "홈승"
        elif r_res == "원정승":
            h_style = "font-weight: 500; color: #64748b;"
            a_style = "font-weight: 800; color: #991b1b;"
            res_badge_bg = "#ffe4e6"
            res_badge_fg = "#be123c"
            res_badge_border = "#fda4af"
            res_label = "원정승"
        else:
            h_style = "font-weight: 700; color: #334155;"
            a_style = "font-weight: 700; color: #334155;"
            res_badge_bg = "#d1fae5"
            res_badge_fg = "#047857"
            res_badge_border = "#6ee7b7"
            res_label = "무승부"

        if hs is not None and as_sc is not None:
            tot_g = int(hs + as_sc)
            score_str = f"{int(hs)} : {int(as_sc)}"
            if (hs + as_sc) > ou_line:
                ou_badge = f"<span style='display: inline-block; background-color: #fff1f2; color: #e11d48; border: 1px solid #fecdd3; border-radius: 4px; padding: 2px 7px; font-size: 11px; font-weight: 700;'>{tot_g}골 · 오버</span>"
            else:
                ou_badge = f"<span style='display: inline-block; background-color: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 4px; padding: 2px 7px; font-size: 11px; font-weight: 700;'>{tot_g}골 · 언더</span>"
        else:
            score_str = "VS"
            ou_badge = "<span style='color: #94a3b8; font-size: 11px;'>-</span>"

        rows_html += f"""
        <tr style="background-color: {bg_row}; border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 10px 8px; text-align: center; vertical-align: middle; width: 22%;">
                <div style="font-size: 11px; color: #64748b; font-weight: 600;">{r_date}</div>
                <div style="display: inline-block; margin-top: 3px; background-color: #f1f5f9; color: #334155; border-radius: 4px; padding: 1px 6px; font-size: 11px; font-weight: 700;">{r_lg}</div>
            </td>
            <td style="padding: 10px 6px; text-align: right; vertical-align: middle; width: 24%; font-size: 13px; {h_style}">
                {r_home}
            </td>
            <td style="padding: 10px 4px; text-align: center; vertical-align: middle; width: 14%;">
                <span style="display: inline-block; background-color: #0f172a; color: #ffffff; font-weight: 800; font-size: 13px; padding: 4px 10px; border-radius: 6px; letter-spacing: 1px;">
                    {score_str}
                </span>
            </td>
            <td style="padding: 10px 6px; text-align: left; vertical-align: middle; width: 24%; font-size: 13px; {a_style}">
                {r_away}
            </td>
            <td style="padding: 10px 8px; text-align: center; vertical-align: middle; width: 16%;">
                <div style="margin-bottom: 3px;">
                    <span style="display: inline-block; background-color: {res_badge_bg}; color: {res_badge_fg}; border: 1px solid {res_badge_border}; border-radius: 12px; padding: 2px 10px; font-size: 11px; font-weight: 800;">
                        {res_label}
                    </span>
                </div>
                <div>{ou_badge}</div>
            </td>
        </tr>
        """

    gauge_cells = ""
    if w_bar > 0:
        gauge_cells += f"<td style='width: {w_bar}%; background-color: #2563eb; color: #ffffff; text-align: center; font-size: 11px; font-weight: 700; padding: 5px 0;'>홈승 {hw_pct}%</td>"
    if d_bar > 0:
        gauge_cells += f"<td style='width: {d_bar}%; background-color: #10b981; color: #ffffff; text-align: center; font-size: 11px; font-weight: 700; padding: 5px 0;'>무 {dr_pct}%</td>"
    if a_bar > 0:
        gauge_cells += f"<td style='width: {a_bar}%; background-color: #e11d48; color: #ffffff; text-align: center; font-size: 11px; font-weight: 700; padding: 5px 0;'>원정 {aw_pct}%</td>"

    html = f"""
    <div style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 680px; margin: 0 auto; background-color: #ffffff; border: 2px solid #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
        <!-- 상단 타이틀 배너 -->
        <table style="width: 100%; border-collapse: collapse; background-color: #0f172a; color: #ffffff;">
            <tr>
                <td style="padding: 16px 20px;">
                    <div style="font-size: 11px; color: #38bdf8; font-weight: 800; letter-spacing: 0.5px; margin-bottom: 4px;">
                        ⚽ HISTORICAL MATCH RESULT ARCHIVE ({scope_label})
                    </div>
                    <div style="font-size: 18px; font-weight: 800; color: #ffffff;">
                        {title_lg}{title_match} <span style="font-size: 14px; font-weight: 600; color: #cbd5e1;">과거 동일배당 매치 히스토리</span>
                    </div>
                </td>
                <td style="padding: 16px 20px; text-align: right; vertical-align: middle;">
                    <span style="display: inline-block; background-color: #1e293b; border: 1px solid #475569; color: #f8fafc; font-size: 12px; font-weight: 800; padding: 6px 12px; border-radius: 8px;">
                        총 {total_cnt}경기 매칭
                    </span>
                </td>
            </tr>
        </table>

        <!-- 핵심 요약 KPI 3단 박스 -->
        <table style="width: 100%; border-collapse: collapse; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
            <tr>
                <td style="width: 34%; padding: 12px 10px; text-align: center; border-right: 1px solid #e2e8f0;">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; margin-bottom: 4px;">📌 과거 승·무·패 흐름</div>
                    <div style="font-size: 13px; font-weight: 800; color: #0f172a;">
                        <span style="color: #1d4ed8;">홈 {hw_cnt}승</span> · <span style="color: #047857;">{dr_cnt}무</span> · <span style="color: #be123c;">원정 {aw_cnt}승</span>
                    </div>
                </td>
                <td style="width: 33%; padding: 12px 10px; text-align: center; border-right: 1px solid #e2e8f0;">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; margin-bottom: 4px;">⚽ 경기당 평균 득점</div>
                    <div style="font-size: 13px; font-weight: 800; color: #0f172a;">
                        평균 <span style="color: #0f172a;">{avg_tot}골</span> <span style="font-size: 11px; font-weight: 600; color: #64748b;">(홈 {avg_h} : 원정 {avg_a})</span>
                    </div>
                </td>
                <td style="width: 33%; padding: 12px 10px; text-align: center;">
                    <div style="font-size: 11px; color: #64748b; font-weight: 700; margin-bottom: 4px;">⚡ {ou_line} 기준 언오버 비율</div>
                    <div style="font-size: 13px; font-weight: 800;">
                        <span style="color: #e11d48;">오버 {ov_pct}%</span> <span style="color: #94a3b8; font-weight: 400;">|</span> <span style="color: #2563eb;">언더 {un_pct}%</span>
                    </div>
                </td>
            </tr>
        </table>

        <!-- 승무패 비율 게이지 바 -->
        <table style="width: 100%; border-collapse: collapse;">
            <tr>{gauge_cells}</tr>
        </table>

        <!-- 매칭 경기 상세 스코어보드 리스트 -->
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #f1f5f9; border-top: 1px solid #cbd5e1; border-bottom: 2px solid #cbd5e1;">
                    <th style="padding: 8px; font-size: 11px; color: #475569; text-align: center; width: 22%;">일자 / 리그</th>
                    <th style="padding: 8px; font-size: 11px; color: #475569; text-align: right; width: 24%;">홈팀</th>
                    <th style="padding: 8px; font-size: 11px; color: #475569; text-align: center; width: 14%;">스코어</th>
                    <th style="padding: 8px; font-size: 11px; color: #475569; text-align: left; width: 24%;">원정팀</th>
                    <th style="padding: 8px; font-size: 11px; color: #475569; text-align: center; width: 16%;">결과 / 언오버</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <!-- 하단 푸터 -->
        <div style="background-color: #f8fafc; padding: 10px 16px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0;">
            💡 위 기록은 동일 배당 구간에서 실제로 치러진 과거 매치업 및 최종 경기 결과입니다.
        </div>
    </div>
    """
    return html


@st.cache_data(ttl=300, show_spinner=False)
def get_t3_preprocessed_bm_v3(bm_name, spreadsheet_id):
    df_bm = load_sheet_data(bm_name, spreadsheet_id)
    if df_bm.empty:
        return None
    try:
        df_work = normalize_bm_dataframe(df_bm)
        cols = list(df_work.columns)

        h_col = next((c for c in cols if any(k in c for k in ["해당_홈", "배당_홈", "홈배당", "홈_승", "H_ODDS"])), None)
        d_col = next((c for c in cols if any(k in c for k in ["해당_무", "배당_무", "무배당", "무승부", "D_ODDS"])), None)
        a_col = next((c for c in cols if any(k in c for k in ["해당_원", "배당_원", "원정배당", "원정_승", "A_ODDS"])), None)
        res_col = next((c for c in cols if any(k in c for k in ["경기결과", "결과", "Result"])), None)
        lg_col = next((c for c in cols if any(k in c for k in ["리그명", "리그", "League"])), None)
        hs_col = next((c for c in cols if any(k in str(c) for k in ["홈스코어", "홈_스코어", "Home_Score", "홈득점"])), None)
        as_col = next((c for c in cols if any(k in str(c) for k in ["원정스코어", "원정_스코어", "Away_Score", "원정득점"])), None)

        if not h_col and len(cols) > 14:
            h_col, d_col, a_col = cols[12], cols[13], cols[14]
        if not hs_col and len(cols) > 29:
            hs_col, as_col = cols[28], cols[29]
        if not res_col:
            res_col = cols[34] if len(cols) > 34 else (cols[32] if len(cols) > 32 else cols[-1])

        if not (h_col and d_col and a_col and res_col):
            return None

        df_work["H_num"] = pd.to_numeric(df_work[h_col], errors="coerce").fillna(0.0)
        df_work["D_num"] = pd.to_numeric(df_work[d_col], errors="coerce").fillna(0.0)
        df_work["A_num"] = pd.to_numeric(df_work[a_col], errors="coerce").fillna(0.0)
        if lg_col and lg_col in df_work.columns:
            df_work["_lg_upper"] = df_work[lg_col].astype(str).str.strip().str.upper()

        if hs_col and as_col:
            hs_n = pd.to_numeric(df_work[hs_col].astype(str).str.strip(), errors="coerce")
            as_n = pd.to_numeric(df_work[as_col].astype(str).str.strip(), errors="coerce")
            df_work["_tot_goals"] = np.where(hs_n.notna() & as_n.notna() & (hs_n >= 0) & (as_n >= 0), hs_n + as_n, -1.0)
        else:
            df_work["_tot_goals"] = -1.0

        valid_mask = (df_work["H_num"] >= 1.01) & (df_work["D_num"] >= 1.01) & (df_work["A_num"] >= 1.01)
        df_valid = df_work[valid_mask].reset_index(drop=True)
        if df_valid.empty:
            return None

        return {
            "df": df_valid,
            "res_col": res_col,
            "lg_col": lg_col
        }
    except Exception:
        return None


def render_tab3(spreadsheet_id, bookmakers, overseas_bookmakers, tol):
    st.subheader("🔬 3번 탭: 9대 북메이커 배당 입력 및 승률·핸디캡·언오버 자동 분석")

    scanner_sheet_name = "라운드스캔"
    
    df_t3_scan = pd.DataFrame()
    try:
        df_t3_scan = load_sheet_data(scanner_sheet_name, spreadsheet_id)
    except Exception:
        pass
    
    def safe_flt(val, default):
        try:
            res = float(str(val).replace("%", "").strip())
            return res if res > 0 else default
        except:
            return default

    def on_t3_match_load():
        sel_t3 = st.session_state.get("sel_t3_match_loader", "➕ [직접 수동 입력하기]")
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
            st.caption("💡 2번 탭(스캐너)에 등록된 경기가 있으면 여기에 목록이 나타납니다. (현재 스캔 시트 비어있음 또는 로딩 중)")

    if "selected_scan_match" in st.session_state and st.session_state.selected_scan_match:
        sm = st.session_state.selected_scan_match
        st.success(f"🎯 [스캐너 연동 완료] 현재 **[{sm['home']} vs {sm['away']}]** 경기의 배당 데이터가 자동 적용되어 있습니다.")

    c_an_l1, c_an_l2, c_an_l3 = st.columns([1, 1, 1])
    target_league = c_an_l1.text_input("🔍 리그명", value="PL", key="t2_target_league")
    t2_home_team = c_an_l2.text_input("🏠 홈팀명 (블로그 도표용)", value="", placeholder="예: 헤타페", key="t2_home_team")
    t2_away_team = c_an_l3.text_input("🚗 원정팀명 (블로그 도표용)", value="", placeholder="예: 셀타비고", key="t2_away_team")

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

    # =========================================================
    # 🎯 핸디캡 및 언오버 기준점 설정 영역
    # =========================================================
    st.markdown("---")
    st.markdown("##### 🎯 과거 데이터 기반 핸디캡 & 언오버 확률 분석 기준점 설정")
    
    hc_options = [-5.0, -4.0, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    ou_options = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]

    hc_col1, ou_col1 = st.columns(2)
    
    with hc_col1:
        with st.container(border=True):
            st.markdown("**🎯 핸디캡 기준점 (2~3개 복수 선택 가능)**")
            default_hcs = [-1.5, -1.0, -0.5] if all(x in hc_options for x in [-1.5, -1.0, -0.5]) else [-1.0]
            sel_hc_lines = st.multiselect("핸디캡 기준점 선택 (최대 3개 권장)", hc_options, default=default_hcs, key="t3_sel_hc_lines")
            hc_lines_val = sorted([float(x) for x in sel_hc_lines])
            if not hc_lines_val:
                hc_lines_val = [-1.0]

    with ou_col1:
        with st.container(border=True):
            st.markdown("**⚡ 언더오버 기준점 (기본 2.5)**")
            sel_ou_opt = st.selectbox("언오버 기준점 선택", ou_options, index=ou_options.index(2.5) if 2.5 in ou_options else 2, key="t3_sel_ou_line")
            ou_line_val = float(sel_ou_opt)

    st.markdown("---")

    def calc_ou_from_df(m_df, line_val):
        if m_df is None or m_df.empty:
            return 0, 0, 0
        arr_sub = m_df.to_numpy(dtype=object)
        nr, nc = arr_sub.shape
        ou_c, ov_c, un_c = 0, 0, 0
        for ri in range(nr):
            res_i = next((ci for ci in range(nc - 1, 27, -1) if str(arr_sub[ri, ci]).strip() in ("홈승", "무승부", "원정승")), None)
            hs_v, as_v = None, None
            if res_i is not None and res_i >= 6:
                try:
                    hs_v = float(str(arr_sub[ri, res_i - 6]).strip())
                    as_v = float(str(arr_sub[ri, res_i - 5]).strip())
                except:
                    hs_v, as_v = None, None
            if (hs_v is None or as_v is None) and nc > 29:
                try:
                    h0 = float(str(arr_sub[ri, 28]).strip())
                    a0 = float(str(arr_sub[ri, 29]).strip())
                    if h0 >= 0 and a0 >= 0:
                        hs_v, as_v = h0, a0
                except:
                    pass
            if hs_v is not None and as_v is not None and hs_v >= 0 and as_v >= 0:
                ou_c += 1
                if (hs_v + as_v) > line_val:
                    ov_c += 1
                else:
                    un_c += 1
        return ou_c, ov_c, un_c

    def run_full_analysis():
        rows_all = []
        rows_target = []
        matched_dict_all = {}
        matched_dict_target = {}
        
        tot_bm = 0
        tot_payout = 0.0
        tot_m = 0
        tot_hw, tot_dr, tot_aw = 0, 0, 0
        tot_ou_m, tot_ov, tot_un = 0, 0, 0

        tot_t_m = 0
        tot_t_hw, tot_t_dr, tot_t_aw = 0, 0, 0
        tot_t_ou_m, tot_t_ov, tot_t_un = 0, 0, 0

        target_lg_upper = target_league.strip().upper()
        ov_col_name = f"오버({ou_line_val}) 확률"
        un_col_name = f"언더({ou_line_val}) 확률"

        for idx, bm in enumerate(bookmakers, 1):
            h, d, a = odds_inputs_t2.get(bm, (0.0, 0.0, 0.0))
            if h <= 1.0 or d <= 1.0 or a <= 1.0:
                rows_all.append({
                    "순번": str(idx), "북메이커": bm.upper(), "입력 배당": "미입력", "환급률": "-",
                    "매칭 경기": "0건", "홈승 확률": "-", "무승부 확률": "-", "원정승 확률": "-",
                    "언오버 매칭": "0건", ov_col_name: "-", un_col_name: "-"
                })
                rows_target.append({
                    "순번": str(idx), "북메이커": bm.upper(), "입력 배당": "미입력", "환급률": "-",
                    "매칭 경기": "0건", "홈승 확률": "-", "무승부 확률": "-", "원정승 확률": "-",
                    "언오버 매칭": "0건", ov_col_name: "-", un_col_name: "-"
                })
                continue

            raw_inv = (1/h) + (1/d) + (1/a)
            payout = (1 / raw_inv) * 100
            
            tot_payout += payout
            tot_bm += 1

            prep = get_t3_preprocessed_bm_v3(bm, spreadsheet_id)
            
            h_str, d_str, a_str = "0.0%", "0.0%", "0.0%"
            ov_str, un_str = "0.0%", "0.0%"
            t_h_str, t_d_str, t_a_str = "0.0%", "0.0%", "0.0%"
            t_ov_str, t_un_str = "0.0%", "0.0%"
            m_count_all, ou_cnt_all = 0, 0
            m_count_target, ou_cnt_target = 0, 0

            if prep is not None:
                try:
                    df_work = prep["df"]
                    res_col = prep["res_col"]
                    lg_col = prep["lg_col"]

                    cond = (
                        (df_work["H_num"] >= h - tol) & (df_work["H_num"] <= h + tol) &
                        (df_work["D_num"] >= d - tol) & (df_work["D_num"] <= d + tol) &
                        (df_work["A_num"] >= a - tol) & (df_work["A_num"] <= a + tol)
                    )
                    matched_all_df = df_work[cond]
                    m_count_all = len(matched_all_df)

                    if m_count_all > 0:
                        bm_upper = bm.upper()
                        matched_dict_all[bm_upper] = matched_all_df
                        res_c = matched_all_df[res_col].value_counts()
                        hw = res_c.get("홈승", 0)
                        dr = res_c.get("무승부", 0)
                        aw = res_c.get("원정승", 0)

                        tot_m += m_count_all
                        tot_hw += hw
                        tot_dr += dr
                        tot_aw += aw

                        h_str = f"{round((hw/m_count_all)*100, 1)}% ({hw}회)"
                        d_str = f"{round((dr/m_count_all)*100, 1)}% ({dr}회)"
                        a_str = f"{round((aw/m_count_all)*100, 1)}% ({aw}회)"

                        ou_cnt_all, ov_all, un_all = calc_ou_from_df(matched_all_df, ou_line_val)
                        if ou_cnt_all > 0:
                            tot_ou_m += ou_cnt_all
                            tot_ov += ov_all
                            tot_un += un_all
                            ov_str = f"{round((ov_all/ou_cnt_all)*100, 1)}% ({ov_all}회)"
                            un_str = f"{round((un_all/ou_cnt_all)*100, 1)}% ({un_all}회)"

                        # 동일 리그 필터링
                        if lg_col and "_lg_upper" in matched_all_df.columns:
                            matched_target_df = matched_all_df[matched_all_df["_lg_upper"] == target_lg_upper]
                            m_count_target = len(matched_target_df)
                            if m_count_target > 0:
                                matched_dict_target[bm_upper] = matched_target_df
                                t_res_c = matched_target_df[res_col].value_counts()
                                thw = t_res_c.get("홈승", 0)
                                tdr = t_res_c.get("무승부", 0)
                                taw = t_res_c.get("원정승", 0)

                                tot_t_m += m_count_target
                                tot_t_hw += thw
                                tot_t_dr += tdr
                                tot_t_aw += taw

                                t_h_str = f"{round((thw/m_count_target)*100, 1)}% ({thw}회)"
                                t_d_str = f"{round((tdr/m_count_target)*100, 1)}% ({tdr}회)"
                                t_a_str = f"{round((taw/m_count_target)*100, 1)}% ({taw}회)"

                                ou_cnt_target, t_ov, t_un = calc_ou_from_df(matched_target_df, ou_line_val)
                                if ou_cnt_target > 0:
                                    tot_t_ou_m += ou_cnt_target
                                    tot_t_ov += t_ov
                                    tot_t_un += t_un
                                    t_ov_str = f"{round((t_ov/ou_cnt_target)*100, 1)}% ({t_ov}회)"
                                    t_un_str = f"{round((t_un/ou_cnt_target)*100, 1)}% ({t_un}회)"
                except Exception:
                    pass

            rows_all.append({
                "순번": str(idx), "북메이커": bm.upper(),
                "입력 배당": f"{h} / {d} / {a}",
                "환급률": f"{round(payout, 2)}%",
                "매칭 경기": f"{m_count_all}건",
                "홈승 확률": h_str, "무승부 확률": d_str, "원정승 확률": a_str,
                "언오버 매칭": f"{ou_cnt_all}건", ov_col_name: ov_str, un_col_name: un_str
            })

            rows_target.append({
                "순번": str(idx), "북메이커": bm.upper(),
                "입력 배당": f"{h} / {d} / {a}",
                "환급률": f"{round(payout, 2)}%",
                "매칭 경기": f"{m_count_target}건",
                "홈승 확률": t_h_str, "무승부 확률": t_d_str, "원정승 확률": t_a_str,
                "언오버 매칭": f"{ou_cnt_target}건", ov_col_name: t_ov_str, un_col_name: t_un_str
            })

        avg_p_str = f"{round(tot_payout / tot_bm, 2)}%" if tot_bm > 0 else "-"
        if tot_m > 0:
            tot_h_str = f"{round((tot_hw / tot_m) * 100, 1)}% ({tot_hw}회)"
            tot_d_str = f"{round((tot_dr / tot_m) * 100, 1)}% ({tot_dr}회)"
            tot_a_str = f"{round((tot_aw / tot_m) * 100, 1)}% ({tot_aw}회)"
        else:
            tot_h_str, tot_d_str, tot_a_str = "0.0%", "0.0%", "0.0%"

        if tot_ou_m > 0:
            tot_ov_str = f"{round((tot_ov / tot_ou_m) * 100, 1)}% ({tot_ov}회)"
            tot_un_str = f"{round((tot_un / tot_ou_m) * 100, 1)}% ({tot_un}회)"
        else:
            tot_ov_str, tot_un_str = "0.0%", "0.0%"

        rows_all.append({
            "순번": "🔥",
            "북메이커": "종합 가중평균 (누적)",
            "입력 배당": f"유효 {tot_bm}개사",
            "환급률": avg_p_str,
            "매칭 경기": f"총 {tot_m}건",
            "홈승 확률": tot_h_str,
            "무승부 확률": tot_d_str,
            "원정승 확률": tot_a_str,
            "언오버 매칭": f"총 {tot_ou_m}건",
            ov_col_name: tot_ov_str,
            un_col_name: tot_un_str
        })

        if tot_t_m > 0:
            tot_th_str = f"{round((tot_t_hw / tot_t_m) * 100, 1)}% ({tot_t_hw}회)"
            tot_td_str = f"{round((tot_t_dr / tot_t_m) * 100, 1)}% ({tot_t_dr}회)"
            tot_ta_str = f"{round((tot_t_aw / tot_t_m) * 100, 1)}% ({tot_t_aw}회)"
        else:
            tot_th_str, tot_td_str, tot_ta_str = "0.0%", "0.0%", "0.0%"

        if tot_t_ou_m > 0:
            tot_tov_str = f"{round((tot_t_ov / tot_t_ou_m) * 100, 1)}% ({tot_t_ov}회)"
            tot_tun_str = f"{round((tot_t_un / tot_t_ou_m) * 100, 1)}% ({tot_t_un}회)"
        else:
            tot_tov_str, tot_tun_str = "0.0%", "0.0%"

        rows_target.append({
            "순번": "🔥",
            "북메이커": "종합 가중평균 (누적)",
            "입력 배당": f"유효 {tot_bm}개사",
            "환급률": avg_p_str,
            "매칭 경기": f"총 {tot_t_m}건",
            "홈승 확률": tot_th_str,
            "무승부 확률": tot_td_str,
            "원정승 확률": tot_ta_str,
            "언오버 매칭": f"총 {tot_t_ou_m}건",
            ov_col_name: tot_tov_str,
            un_col_name: tot_tun_str
        })

        return (
            pd.DataFrame(rows_all), matched_dict_all,
            pd.DataFrame(rows_target), matched_dict_target
        )

    st.markdown("### 🚀 동일 배당 승률 및 통계 분석 실행")
    st.info("💡 아래 버튼을 누르면 캐싱된 데이터를 활용해 즉시 승무패 및 언오버 분석을 수행합니다.")
    
    if st.button("🔥 분석 시작하기", type="primary", use_container_width=True):
        with st.spinner("고속 매칭 분석을 수행 중입니다..."):
            df_all_league, matched_all, df_target_league, matched_target = run_full_analysis()
            
            st.session_state["t3_analyzed"] = True
            st.session_state["t3_df_all"] = df_all_league
            st.session_state["t3_matched_all"] = matched_all
            st.session_state["t3_df_target"] = df_target_league
            st.session_state["t3_matched_target"] = matched_target

    if st.session_state.get("t3_analyzed", False):
        df_all_league = st.session_state["t3_df_all"]
        matched_all = st.session_state["t3_matched_all"]
        df_target_league = st.session_state["t3_df_target"]
        matched_target = st.session_state["t3_matched_target"]

        st.subheader(f"1️⃣ [전체 리그 기준] 동일 배당 승률 & {ou_line_val} 언오버 분석표")
        st.dataframe(df_all_league, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader(f"2️⃣ [{target_league} 동일 리그 전용] 동일 배당 승률 & {ou_line_val} 언오버 분석표")
        st.dataframe(df_target_league, use_container_width=True, hide_index=True)

        with st.expander("📊 / 📋 [카드 1] 동일 배당 매칭 스코어 기반 (승무패 통계·핸디캡·언오버) 인포그래픽 복사 (추천 ⭐)", expanded=True):
            st.markdown("##### 🌟 [네이버 블로그/카페 전용] 동일 배당 매칭 스코어 기반 종합 분석 카드")
            st.caption("초록색 버튼을 클릭하여 블로그 글쓰기 창에서 Ctrl+V 하세요!")

            compare_options = [
                "🌟 해외 종합 가중평균 (전체 평균)",
                "🌐 해외 8개사 전용 평균 (배트맨 매칭 제외)"
            ] + bookmakers
            sel_compare_target = st.selectbox("비교할 대상 선택 (카드 1)", compare_options, index=0, key="sel_compare_bm_t2_card1_v2")

            b_odds_val = odds_inputs_t2.get("배트맨", (0.0, 0.0, 0.0))

            if "종합" in sel_compare_target or "평균" in sel_compare_target:
                valid_h, valid_d, valid_a = [], [], []
                for obm in overseas_bookmakers:
                    oh, od, oa = odds_inputs_t2.get(obm, (0.0, 0.0, 0.0))
                    if oh >= 1.01 and od >= 1.01 and oa >= 1.01:
                        valid_h.append(oh)
                        valid_d.append(od)
                        valid_a.append(oa)
                
                if valid_h:
                    avg_oh = round(float(np.mean(valid_h)), 2)
                    avg_od = round(float(np.mean(valid_d)), 2)
                    avg_oa = round(float(np.mean(valid_a)), 2)
                    o_odds_val = (avg_oh, avg_od, avg_oa)
                else:
                    o_odds_val = (0.0, 0.0, 0.0)
                
                display_name = f"해외 종합평균 (유효 {len(valid_h)}개사)"
            else:
                o_odds_val = odds_inputs_t2.get(sel_compare_target, (0.0, 0.0, 0.0))
                display_name = sel_compare_target

            match_stats_dict = None
            hc_stats_list = []
            ou_stats_dict = None

            target_matched_df = pd.DataFrame()
            if "배트맨 매칭 제외" in sel_compare_target:
                frames_to_concat = []
                for obm in overseas_bookmakers:
                    obm_upper = obm.upper()
                    if obm_upper in matched_all and not matched_all[obm_upper].empty:
                        frames_to_concat.append(normalize_bm_dataframe(matched_all[obm_upper]))
                if frames_to_concat:
                    target_matched_df = pd.concat(frames_to_concat, ignore_index=True)
            elif "종합" in sel_compare_target or "평균" in sel_compare_target:
                frames_to_concat = []
                for bm in bookmakers:
                    bm_upper = bm.upper()
                    if bm_upper in matched_all and not matched_all[bm_upper].empty:
                        frames_to_concat.append(normalize_bm_dataframe(matched_all[bm_upper]))
                if frames_to_concat:
                    target_matched_df = pd.concat(frames_to_concat, ignore_index=True)
            else:
                sel_upper = sel_compare_target.upper()
                if sel_upper in matched_all and not matched_all[sel_upper].empty:
                    target_matched_df = normalize_bm_dataframe(matched_all[sel_upper])

            if not target_matched_df.empty:
                arr_m = target_matched_df.to_numpy(dtype=object)
                n_r, n_c = arr_m.shape

                hw_cnt_match, dr_cnt_match, aw_cnt_match = 0, 0, 0
                ov_cnt, un_cnt = 0, 0
                valid_matches = 0
                parsed_matches = []

                for r_i in range(n_r):
                    res_idx = None
                    for c_i in range(n_c - 1, 27, -1):
                        v_str = str(arr_m[r_i, c_i]).strip()
                        if v_str in ("홈승", "무승부", "원정승"):
                            res_idx = c_i
                            break

                    hs, as_sc = None, None
                    res_val = str(arr_m[r_i, res_idx]).strip() if res_idx is not None else ""

                    if res_idx is not None and res_idx >= 6:
                        try:
                            hs = float(str(arr_m[r_i, res_idx - 6]).strip())
                            as_sc = float(str(arr_m[r_i, res_idx - 5]).strip())
                        except:
                            hs, as_sc = None, None

                    if (hs is None or as_sc is None) and n_c > 29:
                        try:
                            hs_0 = float(str(arr_m[r_i, 28]).strip())
                            as_0 = float(str(arr_m[r_i, 29]).strip())
                            if hs_0 >= 0 and as_0 >= 0:
                                hs, as_sc = hs_0, as_0
                        except:
                            pass

                    if hs is not None and as_sc is not None:
                        parsed_matches.append((hs, as_sc, res_val))
                        valid_matches += 1
                        if res_val == "홈승" or hs > as_sc:
                            hw_cnt_match += 1
                        elif res_val == "무승부" or hs == as_sc:
                            dr_cnt_match += 1
                        else:
                            aw_cnt_match += 1

                        if (hs + as_sc) > ou_line_val:
                            ov_cnt += 1
                        else:
                            un_cnt += 1

                if valid_matches > 0:
                    match_stats_dict = {
                        "count": valid_matches,
                        "home_win_pct": round((hw_cnt_match / valid_matches) * 100, 1),
                        "draw_pct": round((dr_cnt_match / valid_matches) * 100, 1),
                        "away_win_pct": round((aw_cnt_match / valid_matches) * 100, 1)
                    }

                    for hc_val in hc_lines_val:
                        hw_hc_cnt = 0
                        hd_hc_cnt = 0
                        aw_hc_cnt = 0
                        
                        for hs, as_sc, _ in parsed_matches:
                            adjusted_home_score = hs + hc_val
                            if adjusted_home_score > as_sc:
                                hw_hc_cnt += 1
                            elif adjusted_home_score == as_sc:
                                hd_hc_cnt += 1
                            else:
                                aw_hc_cnt += 1
                        
                        hc_stats_list.append({
                            "line": hc_val,
                            "count": valid_matches,
                            "home_win_pct": round((hw_hc_cnt / valid_matches) * 100, 1),
                            "draw_pct": round((hd_hc_cnt / valid_matches) * 100, 1),
                            "away_win_pct": round((aw_hc_cnt / valid_matches) * 100, 1),
                            "home_win_cnt": hw_hc_cnt,
                            "draw_cnt": hd_hc_cnt,
                            "away_win_cnt": aw_hc_cnt
                        })

                    ou_stats_dict = {
                        "line": ou_line_val,
                        "count": valid_matches,
                        "over_pct": round((ov_cnt / valid_matches) * 100, 1),
                        "under_pct": round((un_cnt / valid_matches) * 100, 1),
                        "over_cnt": ov_cnt,
                        "under_cnt": un_cnt
                    }

            card1_html = generate_naver_odds_with_handicap_infographic(
                b_odds_val, display_name, o_odds_val, 
                league_name=target_league, home_team=t2_home_team.strip(), away_team=t2_away_team.strip(),
                match_stats=match_stats_dict, hc_stats_list=hc_stats_list, ou_stats=ou_stats_dict
            )
            render_clipboard_component(card1_html, "t2_clip_card1", height=680)

        with st.expander("📊 / 📋 [카드 2] 기존 배당 편차 및 단순 배당 비교 인포그래픽", expanded=False):
            st.markdown("##### 🌟 [네이버 블로그/카페 전용] 배당 편차 및 단순 배당 비교 카드")
            st.caption("초록색 버튼을 클릭하여 순수 배당 비교 서식을 복사하세요!")

            card2_html = generate_naver_odds_infographic(
                b_odds_val, display_name, o_odds_val, 
                league_name=target_league, home_team=t2_home_team.strip(), away_team=t2_away_team.strip()
            )
            render_clipboard_component(card2_html, "t2_clip_card2", height=450)

        st.markdown("---")
        st.subheader("📋 매칭된 과거 경기 상세 리스트 (업체별 전체 내역 & 인포그래픽)")
        
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            view_option = st.radio(
                "상세 리스트 범위 선택",
                ["전체 리그 매칭 내역", f"[{target_league}] 동일 리그 매칭 내역"],
                horizontal=True,
                key="t3_hist_scope_radio"
            )
        with c_v2:
            dedup_option = st.radio(
                "인포그래픽 중복 경기 표시 방식",
                ["전체 매칭 건수 모두 표시", "동일 경기 중복 제거 (1경기씩 깔끔 표시)"],
                horizontal=True,
                key="t3_hist_dedup_radio"
            )

        active_matched = matched_target if "동일 리그" in view_option else matched_all
        scope_lbl_str = f"{target_league} 동일 리그" if "동일 리그" in view_option else "전체 리그"

        if active_matched:
            # 인포그래픽용 매칭 경기 레코드 추출 (배당 및 정/중/역 제외, 스코어 및 결과 중심)
            history_records = []
            seen_match_keys = set()

            for name, m_df in active_matched.items():
                m_df_norm = normalize_bm_dataframe(m_df)
                arr_h = m_df_norm.to_numpy(dtype=object)
                nr_h, nc_h = arr_h.shape

                for ri in range(nr_h):
                    r_lg = str(arr_h[ri, 1]).strip() if nc_h > 1 else "-"
                    r_dt = str(arr_h[ri, 2]).strip() if nc_h > 2 else "-"
                    r_hm = str(arr_h[ri, 3]).strip() if nc_h > 3 else "-"
                    r_aw = str(arr_h[ri, 4]).strip() if nc_h > 4 else "-"

                    res_i = next((ci for ci in range(nc_h - 1, 27, -1) if str(arr_h[ri, ci]).strip() in ("홈승", "무승부", "원정승")), None)
                    r_res = str(arr_h[ri, res_i]).strip() if res_i is not None else "-"

                    hs_v, as_v = None, None
                    if res_i is not None and res_i >= 6:
                        try:
                            hs_v = float(str(arr_h[ri, res_i - 6]).strip())
                            as_v = float(str(arr_h[ri, res_i - 5]).strip())
                        except:
                            hs_v, as_v = None, None
                    if (hs_v is None or as_v is None) and nc_h > 29:
                        try:
                            h0 = float(str(arr_h[ri, 28]).strip())
                            a0 = float(str(arr_h[ri, 29]).strip())
                            if h0 >= 0 and a0 >= 0:
                                hs_v, as_v = h0, a0
                        except:
                            pass

                    if r_res not in ("홈승", "무승부", "원정승") and hs_v is not None and as_v is not None:
                        r_res = "홈승" if hs_v > as_v else ("무승부" if hs_v == as_v else "원정승")

                    m_key = (r_dt, r_hm, r_aw)
                    if "중복 제거" in dedup_option:
                        if m_key in seen_match_keys:
                            continue
                        seen_match_keys.add(m_key)

                    history_records.append({
                        "league": r_lg,
                        "date": r_dt,
                        "home": r_hm,
                        "away": r_aw,
                        "hs": hs_v,
                        "as": as_v,
                        "res": r_res
                    })

            with st.expander("📊 / 📋 [카드 3] 과거 동일배당 매칭 경기 히스토리 스코어보드 인포그래픽 복사 (추천 ⭐)", expanded=True):
                st.markdown("##### 🌟 [네이버 블로그/카페 전용] 과거 동일배당 매치업 & 실제 경기결과 스코어보드")
                st.caption("복잡한 배당 수치나 정배/역배 표시를 빼고, 과거 매치업·스코어·승무패·언오버 흐름만 중계 화면처럼 깔끔하게 정리한 카드입니다.")

                card3_html = generate_naver_match_history_infographic(
                    history_records,
                    league_name=target_league,
                    home_team=t2_home_team.strip(),
                    away_team=t2_away_team.strip(),
                    ou_line=ou_line_val,
                    scope_label=scope_lbl_str
                )
                dynamic_h = min(900, max(420, 260 + 52 * len(history_records)))
                render_clipboard_component(card3_html, "t3_clip_card3_history", height=dynamic_h)

            for name, m_df in active_matched.items():
                with st.expander(f"📌 [{name}] 원본 매칭 내역 총 {len(m_df)}건 표로 확인하기", expanded=False):
                    m_df_norm = normalize_bm_dataframe(m_df)
                    pref_cols = ["시즌", "리그명", "날짜", "홈팀", "원정팀", "해당_홈", "해당_무", "해당_원", "홈스코어", "원정스코어", "경기결과", "정/중/역", "적중배당"]
                    show_cols = [c for c in pref_cols if c in m_df_norm.columns]
                    st.dataframe(m_df_norm[show_cols] if show_cols else m_df_norm, use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 현재 선택된 조건에 일치(오차 범위 ±{tol})하는 과거 경기 데이터가 없습니다.")
