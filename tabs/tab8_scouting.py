import base64
import io
import math
import os
import re
from collections import Counter, deque
import requests
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from google.auth.transport.requests import Request
from database import get_gspread_client, load_sheet_data
from infographics import render_clipboard_component
from tabs.tab2_scanner import (
    HC_OPTIONS, OU_OPTIONS, format_hc_label, sort_hc_lines
)
from tabs.tab3_analysis import normalize_bm_dataframe

LOGO_FOLDER_ID = "1jhKbgnrWEK3t0rQuP9OYTryYrI56Ujye"


def _to_float(val, default=0.0):
    try:
        s = str(val).replace("%", "").replace(",", "").strip()
        if not s or s == "-":
            return default
        return float(s)
    except Exception:
        return default


def _norm_team_key(name):
    return re.sub(r"[\s_\-\.]", "", str(name)).lower()


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


def _clip(v, lo=10.0, hi=99.0):
    return round(max(lo, min(hi, float(v))), 1)


def _calc_grade(avg_score):
    if avg_score >= 82: return "S", "#f59e0b"
    if avg_score >= 74: return "A+", "#38bdf8"
    if avg_score >= 66: return "A", "#2563eb"
    if avg_score >= 58: return "B+", "#10b981"
    if avg_score >= 50: return "B", "#22c55e"
    if avg_score >= 42: return "C", "#eab308"
    return "D", "#e11d48"


@st.cache_data(ttl=1800, show_spinner=False)
def _load_drive_logo_map(folder_id):
    """구글 드라이브 로고 폴더(하위 폴더 1단계 포함)에서 {팀명: 이미지URL} 딕셔너리 생성"""
    logo_map = {}
    try:
        client = get_gspread_client()
        if not client:
            return logo_map

        creds = getattr(client, "auth", None) or getattr(getattr(client, "http_client", None), "auth", None)
        if creds is None:
            return logo_map

        if hasattr(creds, "valid") and not creds.valid:
            creds.refresh(Request())
        token = getattr(creds, "token", None) or getattr(creds, "access_token", None)
        if not token:
            return logo_map

        headers = {"Authorization": f"Bearer {token}"}

        def _fetch_folder_items(fid):
            items = []
            page_token = None
            while True:
                params = {
                    "q": f"'{fid}' in parents and trashed = false",
                    "fields": "nextPageToken, files(id, name, mimeType)",
                    "pageSize": 1000,
                    "supportsAllDrives": "true",
                    "includeItemsFromAllDrives": "true",
                }
                if page_token:
                    params["pageToken"] = page_token
                resp = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=10)
                if resp.status_code != 200:
                    break
                data = resp.json()
                items.extend(data.get("files", []))
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
            return items

        root_items = _fetch_folder_items(folder_id)
        all_files = []
        sub_folders = []
        for it in root_items:
            if it.get("mimeType") == "application/vnd.google-apps.folder":
                sub_folders.append(it["id"])
            else:
                all_files.append(it)

        for sf_id in sub_folders:
            all_files.extend(_fetch_folder_items(sf_id))

        for f in all_files:
            mime = str(f.get("mimeType", ""))
            fname = str(f.get("name", ""))
            fid = str(f.get("id", ""))
            if not fid or not fname:
                continue
            if mime.startswith("image/") or fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")):
                base_name = os.path.splitext(fname)[0].strip()
                img_url = f"https://lh3.googleusercontent.com/d/{fid}=w160"
                logo_map[base_name] = img_url
                logo_map[_norm_team_key(base_name)] = img_url
    except Exception:
        pass
    return logo_map


def _get_team_logo_url(logo_map, team_name):
    if not logo_map or not team_name:
        return ""
    t_clean = str(team_name).strip()
    return logo_map.get(t_clean) or logo_map.get(_norm_team_key(t_clean), "")


@st.cache_data(ttl=1800, show_spinner=False)
def _make_transparent_logo_data_uri(img_url, tolerance=38):
    """네 모서리 바깥쪽 배경색만 감지해 투명 PNG(base64)로 변환 (엠블럼 내부 흰색 보호)"""
    if not img_url:
        return ""
    try:
        resp = requests.get(img_url, timeout=10)
        if resp.status_code != 200:
            return img_url

        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        w, h = img.size
        if w == 0 or h == 0:
            return img_url

        px = img.load()
        corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]

        if all(c[3] < 20 for c in corners):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64}"

        opaque_corners = [c for c in corners if c[3] >= 20]
        bg_r = int(np.mean([c[0] for c in opaque_corners]))
        bg_g = int(np.mean([c[1] for c in opaque_corners]))
        bg_b = int(np.mean([c[2] for c in opaque_corners]))

        def _is_bg(r, g, b, a):
            if a < 20:
                return True
            return (abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)) <= (tolerance * 3)

        visited = [[False] * w for _ in range(h)]
        q = deque()

        for sx, sy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if _is_bg(*px[sx, sy]):
                visited[sy][sx] = True
                q.append((sx, sy))

        while q:
            cx, cy = q.popleft()
            px[cx, cy] = (0, 0, 0, 0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                    if _is_bg(*px[nx, ny]):
                        visited[ny][nx] = True
                        q.append((nx, ny))

        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return img_url


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
    """배트맨 배당 및 해외 8개사 평균 배당 + 표준편차(일치도) 룩업 생성"""
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

    def _agg_dict(acc):
        res = {}
        for k, lst in acc.items():
            hs = [x[0] for x in lst]
            ds = [x[1] for x in lst]
            as_ = [x[2] for x in lst]
            res[k] = (
                round(float(np.mean(hs)), 3),
                round(float(np.mean(ds)), 3),
                round(float(np.mean(as_)), 3),
                round(float(np.std(hs)), 4) if len(hs) >= 2 else -1.0,
                round(float(np.std(as_)), 4) if len(as_) >= 2 else -1.0,
            )
        return res

    return (
        (bm_dt, bm_sn, bm_pair),
        (_agg_dict(ov_dt_acc), _agg_dict(ov_sn_acc), _agg_dict(ov_pair_acc))
    )


def _lookup_odds(lookup_tuple, norm_dt, sn, hm, aw):
    by_dt, by_sn, by_pair = lookup_tuple
    if (norm_dt, hm, aw) in by_dt:
        return by_dt[(norm_dt, hm, aw)]
    if (sn, hm, aw) in by_sn:
        return by_sn[(sn, hm, aw)]
    return by_pair.get((hm, aw))


def _compute_radar_scores_for_team(df_filtered, team_name, bm_lookup):
    """6각형 레이더 점수 (ATK, DEF, CTL, FIN, MNT, VAL) 계산"""
    ms = []
    for _, r in df_filtered.iterrows():
        hm = str(r.get("홈팀", "")).strip()
        aw = str(r.get("원정팀", "")).strip()
        if hm != team_name and aw != team_name:
            continue
        is_h = (hm == team_name)
        sn = str(r.get("시즌", "")).strip()
        ndt = _norm_date(str(r.get("경기날짜", "")).strip())
        gf_1h = _to_float(r.get("전반득점_홈" if is_h else "전반득점_원"))
        gf_2h = _to_float(r.get("후반득점_홈" if is_h else "후반득점_원"))
        ga_1h = _to_float(r.get("전반득점_원" if is_h else "전반득점_홈"))
        ga_2h = _to_float(r.get("후반득점_원" if is_h else "후반득점_홈"))
        gf, ga = gf_1h + gf_2h, ga_1h + ga_2h
        xg = _to_float(r.get("xG_홈" if is_h else "xG_원"))
        xga = _to_float(r.get("xG_원" if is_h else "xG_홈"))
        sot = _to_float(r.get("유효슈팅_홈" if is_h else "유효슈팅_원"))
        opp_sot = _to_float(r.get("유효슈팅_원" if is_h else "유효슈팅_홈"))
        poss = _to_float(r.get("점유율_홈" if is_h else "점유율_원"))
        res = "승" if gf > ga else ("무" if gf == ga else "패")
        bm = _lookup_odds(bm_lookup, ndt, sn, hm, aw)
        odd = (bm[0] if is_h else bm[2]) if bm else 0.0
        ms.append({
            "gf": gf, "ga": ga, "gf_2h": gf_2h, "ga_2h": ga_2h,
            "xg": xg, "xga": xga, "sot": sot, "opp_sot": opp_sot,
            "poss": poss, "res": res, "odd": odd
        })
    if not ms:
        return [50.0] * 6

    avg_gf = float(np.mean([m["gf"] for m in ms]))
    avg_ga = float(np.mean([m["ga"] for m in ms]))
    avg_xg = float(np.mean([m["xg"] for m in ms]))
    avg_xga = float(np.mean([m["xga"] for m in ms]))
    pos_vals = [m["poss"] for m in ms if m["poss"] > 0]
    avg_pos = float(np.mean(pos_vals)) if pos_vals else 50.0
    sot_m = float(np.mean([m["sot"] - m["opp_sot"] for m in ms]))
    sh_gd = float(np.mean([m["gf_2h"] - m["ga_2h"] for m in ms]))

    bm_v = [m for m in ms if m["odd"] >= 1.01]
    roi = (((sum(m["odd"] for m in bm_v if m["res"] == "승") - len(bm_v)) / len(bm_v)) * 100) if bm_v else 0.0
    win_r = (sum(1 for m in ms if m["res"] == "승") / len(ms)) * 100

    atk = _clip(22 + avg_gf * 22 + avg_xg * 16)
    dfn = _clip(92 - avg_ga * 20 - avg_xga * 14)
    ctl = _clip(50 + (avg_pos - 50) * 1.8 + sot_m * 4.5)
    fin = _clip(55 + (avg_gf - avg_xg) * 45)
    mnt = _clip(50 + sh_gd * 22 + (win_r - 40) * 0.4)
    val = _clip(52 + roi * 0.85)
    return [atk, dfn, ctl, fin, mnt, val]


def _generate_charts_image(rpt, theme_mode="dark"):
    """6각형 레이더 차트 + 누적 승점(xPts) & ROI 추이 그래프를 1장의 고해상도 PNG로 생성"""
    is_dark = (theme_mode == "dark")
    bg_c = "#0f172a" if is_dark else "#ffffff"
    panel_c = "#1e293b" if is_dark else "#f8fafc"
    txt_c = "#f8fafc" if is_dark else "#0f172a"
    sub_c = "#94a3b8" if is_dark else "#475569"
    grid_c = "#334155" if is_dark else "#cbd5e1"
    c_main = "#38bdf8" if is_dark else "#2563eb"
    c_opp = "#fb7185" if is_dark else "#e11d48"
    c_gold = "#fbbf24" if is_dark else "#d97706"
    c_green = "#34d399" if is_dark else "#059669"

    fig = plt.figure(figsize=(10.5, 4.3), dpi=160, facecolor=bg_c)

    # 1. 좌측: 6각형 레이더 차트
    ax1 = fig.add_subplot(1, 2, 1, polar=True, facecolor=panel_c)
    labels = ["ATK", "DEF", "CTL", "FIN", "MNT", "VAL"]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    scores = list(rpt["radar_scores"]) + [rpt["radar_scores"][0]]
    ax1.set_theta_offset(np.pi / 2)
    ax1.set_theta_direction(-1)
    ax1.set_ylim(0, 100)
    ax1.set_yticks([25, 50, 75, 100])
    ax1.set_yticklabels(["25", "50", "75", ""], color=sub_c, fontsize=7)
    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(labels, color=txt_c, fontsize=10, fontweight="bold")
    ax1.spines["polar"].set_color(grid_c)
    ax1.grid(color=grid_c, linestyle="--", linewidth=0.8, alpha=0.8)

    if rpt.get("compare_radar_scores"):
        c_scores = list(rpt["compare_radar_scores"]) + [rpt["compare_radar_scores"][0]]
        ax1.plot(angles, c_scores, color=c_opp, linewidth=2.0, linestyle="--", label="Compare Team")
        ax1.fill(angles, c_scores, color=c_opp, alpha=0.16)
    else:
        avg_line = [50] * (len(labels) + 1)
        ax1.plot(angles, avg_line, color=sub_c, linewidth=1.2, linestyle=":", label="League Avg (50)")

    ax1.plot(angles, scores, color=c_main, linewidth=2.4, label="Target Team")
    ax1.fill(angles, scores, color=c_main, alpha=0.28)
    ax1.set_title("6-AXIS POWER RADAR (0-100)", color=c_gold, fontsize=10.5, fontweight="bold", pad=14)
    leg1 = ax1.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12), frameon=False, fontsize=8)
    for t in leg1.get_texts():
        t.set_color(txt_c)

    # 2. 우측: 시즌 누적 승점 vs xPts & 누적 ROI 추이
    ax2 = fig.add_subplot(1, 2, 2, facecolor=panel_c)
    rounds = list(range(1, len(rpt["cum_pts"]) + 1))
    ax2.plot(rounds, rpt["cum_pts"], color=c_main, linewidth=2.4, marker="o", markersize=4, label="Actual Pts")
    ax2.plot(rounds, rpt["cum_xpts"], color=c_gold, linewidth=2.0, linestyle="--", label="Expected xPts")
    ax2.set_xlabel("Match #", color=sub_c, fontsize=8.5)
    ax2.set_ylabel("Cumulative Points", color=c_main, fontsize=8.5, fontweight="bold")
    ax2.tick_params(axis="x", colors=sub_c, labelsize=8)
    ax2.tick_params(axis="y", colors=c_main, labelsize=8)
    ax2.grid(color=grid_c, linestyle="--", linewidth=0.6, alpha=0.6)
    for sp in ax2.spines.values():
        sp.set_color(grid_c)

    ax2_r = ax2.twinx()
    ax2_r.plot(rounds, rpt["cum_roi_units"], color=c_green, linewidth=1.8, alpha=0.85, label="ROI Profit (u)")
    ax2_r.axhline(0, color=sub_c, linewidth=0.8, linestyle=":")
    ax2_r.set_ylabel("Betting Profit (Units)", color=c_green, fontsize=8.5, fontweight="bold")
    ax2_r.tick_params(axis="y", colors=c_green, labelsize=8)
    for sp in ax2_r.spines.values():
        sp.set_color(grid_c)

    ax2.set_title("SEASON TREND: PTS vs xPTS & ROI", color=c_gold, fontsize=10.5, fontweight="bold", pad=10)

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_r.get_legend_handles_labels()
    leg2 = ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False, fontsize=7.8)
    for t in leg2.get_texts():
        t.set_color(txt_c)

    plt.tight_layout(pad=1.6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=bg_c, bbox_inches="tight")
    plt.close(fig)
    png_bytes = buf.getvalue()
    b64 = base64.b64encode(png_bytes).decode("utf-8")
return f"data:image/png;base64,{b64}", png_bytesdef generate_naver_scouting_infographic(rpt, theme_mode="dark"):
    is_dark = (theme_mode == "dark")

    # 테마별 컬러 팔레트
    p = {
        "wrap_bg": "#0b1120" if is_dark else "#ffffff",
        "wrap_bd": "#334155" if is_dark else "#1e293b",
        "banner_bg": "#0f172a",
        "kpi_bg": "#111827" if is_dark else "#f1f5f9",
        "sec_hdr_bg": "#1e293b" if is_dark else "#cbd5e1",
        "sec_hdr_fg": "#38bdf8" if is_dark else "#1e293b",
        "tbl_hdr_bg": "#0f172a" if is_dark else "#e2e8f0",
        "tbl_hdr_fg": "#cbd5e1" if is_dark else "#1e293b",
        "row_bg1": "#111827" if is_dark else "#ffffff",
        "row_bg2": "#172033" if is_dark else "#f8fafc",
        "bd": "#334155" if is_dark else "#e2e8f0",
        "bd_strong": "#475569" if is_dark else "#cbd5e1",
        "txt_main": "#f8fafc" if is_dark else "#0f172a",
        "txt_body": "#cbd5e1" if is_dark else "#334155",
        "txt_sub": "#94a3b8" if is_dark else "#475569",
        "c_blue": "#38bdf8" if is_dark else "#1d4ed8",
        "c_red": "#fb7185" if is_dark else "#e11d48",
        "c_green": "#34d399" if is_dark else "#047857",
        "c_gold": "#fbbf24" if is_dark else "#d97706",
    }

    tags_html = "".join(
        f"<td bgcolor='#1e293b' style='background-color: #1e293b; border: 1px solid #475569; color: #38bdf8; font-size: 12px; font-weight: 800; padding: 5px 10px; border-radius: 5px; white-space: nowrap; text-decoration: none;'>{t}</td><td width='6'></td>"
        for t in rpt["tags"][:5]
    )

    recent_cells = ""
    for res_ch in rpt["recent5_list"]:
        bg = "#2563eb" if res_ch == "승" else ("#10b981" if res_ch == "무" else "#e11d48")
        recent_cells += f"<td bgcolor='{bg}' style='background-color: {bg}; color: #ffffff; font-size: 13px; font-weight: 800; padding: 5px 9px; border-radius: 5px; text-align: center; text-decoration: none;'>{res_ch}</td><td width='4'></td>"

    logo_src = rpt.get("logo_src", "")
    is_transparent = rpt.get("logo_transparent", True)
    if logo_src:
        if is_transparent:
            logo_cell_html = f"""
            <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 18px 0 18px 20px; vertical-align: middle; width: 68px; text-align: center;">
                <img src="{logo_src}" alt="{rpt['team']}" width="58" height="58" style="width: 58px; height: 58px; object-fit: contain; vertical-align: middle; border: 0;" />
            </td>
            """
        else:
            logo_cell_html = f"""
            <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 18px 0 18px 20px; vertical-align: middle; width: 68px;">
                <div style="width: 58px; height: 58px; background-color: #ffffff; border-radius: 12px; text-align: center; line-height: 58px; padding: 4px; box-sizing: border-box;">
                    <img src="{logo_src}" alt="{rpt['team']}" width="50" height="50" style="width: 50px; height: 50px; object-fit: contain; vertical-align: middle; border: 0;" />
                </div>
            </td>
            """
    else:
        logo_cell_html = ""

    top_scores_str = " / ".join([f"{sc} ({cnt}회)" for sc, cnt in rpt["top_scores"]]) if rpt["top_scores"] else "-"
    top_htft_str = " / ".join([f"{sc} ({pct}%)" for sc, pct in rpt["top_htft"]]) if rpt["top_htft"] else "-"

    xg_fg = p["c_blue"] if rpt["xg_diff"] >= 0.1 else (p["c_red"] if rpt["xg_diff"] <= -0.1 else p["txt_body"])
    xga_fg = p["c_green"] if rpt["xga_diff"] <= -0.1 else (p["c_red"] if rpt["xga_diff"] >= 0.1 else p["txt_body"])
    roi_fg = p["c_green"] if rpt["roi_pct"] >= 0 else p["c_red"]
    draw_roi_fg = p["c_green"] if rpt["draw_roi_pct"] >= 0 else p["c_red"]
    xpts_fg = p["c_red"] if rpt["pts_diff"] >= 2.0 else (p["c_blue"] if rpt["pts_diff"] <= -2.0 else p["txt_body"])

    hc_lines_html = ""
    for h_item in rpt["hc_stats"]:
        hc_lines_html += (
            f"<b style='color: {p['txt_main']};'>• 핸디캡 ({h_item['label']}):</b> "
            f"승 <b style='color: {p['c_blue']};'>{h_item['w_pct']}%</b> · "
            f"무 {h_item['d_pct']}% · 패 {h_item['l_pct']}%<br>"
        )

    tac_html = " / ".join([f"<b style='color: {p['txt_main']};'>{t['tac']}</b> {t['cnt']}회(승률 {t['win_pct']}%)" for t in rpt["top_tactics"]]) if rpt["top_tactics"] else "-"

    log_rows_html = ""
    for idx_l, m in enumerate(rpt["recent5_detail"]):
        bg_l = p["row_bg1"] if idx_l % 2 == 0 else p["row_bg2"]
        ha_badge = "홈" if m["is_home"] else "원정"
        res_fg_l = p["c_blue"] if m["res"] == "승" else (p["c_green"] if m["res"] == "무" else p["c_red"])
        odd_txt = f"{m['team_bm_odd']:.2f}" if m["team_bm_odd"] >= 1.01 else "-"
        log_rows_html += f"""
        <tr>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 9px 6px; font-size: 13px; color: {p['txt_sub']}; text-align: center; border-bottom: 1px solid {p['bd']};">{m['date']}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 9px 6px; font-size: 13px; color: {p['txt_main']}; font-weight: 700; text-align: center; border-bottom: 1px solid {p['bd']};">{ha_badge}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 9px 10px; font-size: 13px; color: {p['txt_main']}; font-weight: 700; text-align: left; border-bottom: 1px solid {p['bd']};">{m['opp']}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 9px 6px; font-size: 14px; color: {res_fg_l}; font-weight: 800; text-align: center; border-bottom: 1px solid {p['bd']};">{int(m['gf'])}:{int(m['ga'])} ({m['res']})</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 9px 6px; font-size: 13px; color: {p['txt_body']}; text-align: center; border-bottom: 1px solid {p['bd']};">{m['xg']:.2f} / {m['xga']:.2f}</td>
            <td bgcolor="{bg_l}" style="background-color: {bg_l}; padding: 9px 6px; font-size: 13px; color: {p['txt_main']}; font-weight: 700; text-align: center; border-bottom: 1px solid {p['bd']};">{odd_txt}</td>
        </tr>
        """

    chart_uri = rpt.get("chart_uri", "")
    compare_note = f" (🔵 {rpt['team']} vs 🔴 {rpt['compare_team']})" if rpt.get("compare_team") else f" (🔵 {rpt['team']} vs ⚪ 리그 평균 50점)"
    radar_vals_txt = f"ATK(공격) {rpt['radar_scores'][0]} · DEF(수비) {rpt['radar_scores'][1]} · CTL(주도) {rpt['radar_scores'][2]} · FIN(결정) {rpt['radar_scores'][3]} · MNT(멘탈) {rpt['radar_scores'][4]} · VAL(가치) {rpt['radar_scores'][5]}"

    html = f"""
    <div style="font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; max-width: 820px; margin: 0 auto; background-color: {p['wrap_bg']}; border: 2px solid {p['wrap_bd']}; border-radius: 12px; overflow: hidden;">
        <!-- 상단 배너 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background-color: #0f172a; color: #ffffff;">
            <tr>
                {logo_cell_html}
                <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 20px 18px; vertical-align: middle;">
                    <div style="font-size: 12px; color: #fbbf24; font-weight: 800; letter-spacing: 0.6px; margin-bottom: 5px;">
                        📋 TEAM COMPREHENSIVE SCOUTING REPORT ({rpt['season']} · {rpt['league']})
                    </div>
                    <div style="font-size: 25px; font-weight: 800; color: #ffffff; line-height: 1.3;">
                        {rpt['team']} 종합 전력 분석 리포트
                        <span style="display: inline-block; background-color: {rpt['grade_color']}; color: #0f172a; font-size: 14px; font-weight: 900; padding: 2px 9px; border-radius: 6px; vertical-align: middle; margin-left: 6px;">{rpt['grade']}등급</span>
                    </div>
                    <div style="font-size: 13px; font-weight: 600; color: #cbd5e1; margin-top: 5px;">
                        총 {rpt['total_n']}경기 · {rpt['streak_text']} · {rpt['ha_gap_label']} · 종합 지수 {rpt['radar_avg']}점
                    </div>
                    <table cellpadding="0" cellspacing="0" style="border-collapse: collapse; margin-top: 10px;">
                        <tr>{tags_html}</tr>
                    </table>
                </td>
                <td bgcolor="#0f172a" style="background-color: #0f172a; padding: 20px 20px 20px 8px; text-align: right; vertical-align: middle; width: 165px; white-space: nowrap;">
                    <div style="font-size: 12px; color: #94a3b8; font-weight: 700; margin-bottom: 6px;">최근 5경기 흐름</div>
                    <table align="right" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                        <tr>{recent_cells}</tr>
                    </table>
                </td>
            </tr>
        </table>

        <!-- 핵심 KPI 3단 바 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; background-color: {p['kpi_bg']}; border-bottom: 1px solid {p['bd_strong']};">
            <tr>
                <td bgcolor="{p['kpi_bg']}" style="background-color: {p['kpi_bg']}; width: 34%; padding: 14px 10px; text-align: center; border-right: 1px solid {p['bd_strong']};">
                    <div style="font-size: 12px; color: {p['txt_sub']}; font-weight: 700; margin-bottom: 4px;">📊 시즌 성적 &amp; 기대승점(xPts)</div>
                    <div style="font-size: 17px; font-weight: 800; color: {p['txt_main']};">
                        {rpt['w']}승 {rpt['d']}무 {rpt['l']}패 <span style="color: {p['c_blue']};">({rpt['win_pct']}%)</span>
                    </div>
                    <div style="font-size: 12px; color: {p['txt_sub']}; font-weight: 700; margin-top: 4px;">
                        승점 {rpt['pts']}점 vs xPts {rpt['xpts']}점 (<span style="color: {xpts_fg};">{rpt['pts_diff']:+.1f}</span>)
                    </div>
                </td>
                <td bgcolor="{p['kpi_bg']}" style="background-color: {p['kpi_bg']}; width: 33%; padding: 14px 10px; text-align: center; border-right: 1px solid {p['bd_strong']};">
                    <div style="font-size: 12px; color: {p['txt_sub']}; font-weight: 700; margin-bottom: 4px;">⚽ 평균 득점 / 실점</div>
                    <div style="font-size: 17px; font-weight: 800; color: {p['txt_main']};">
                        <span style="color: {p['c_blue']};">{rpt['avg_gf']}골</span> / <span style="color: {p['c_red']};">{rpt['avg_ga']}실점</span>
                    </div>
                    <div style="font-size: 12px; color: {p['txt_sub']}; font-weight: 600; margin-top: 4px;">
                        2득점↑ {rpt['gf2_pct']}% · 2실점↑ {rpt['ga2_pct']}% · CS {rpt['cs_pct']}%
                    </div>
                </td>
                <td bgcolor="{p['kpi_bg']}" style="background-color: {p['kpi_bg']}; width: 33%; padding: 14px 10px; text-align: center;">
                    <div style="font-size: 12px; color: {p['txt_sub']}; font-weight: 700; margin-bottom: 4px;">💰 배당 수익률 (배트맨 {rpt['bm_matched_n']}건)</div>
                    <div style="font-size: 17px; font-weight: 800; color: {roi_fg};">
                        승 ROI {rpt['roi_pct']:+.1f}%
                    </div>
                    <div style="font-size: 12px; color: {p['txt_sub']}; font-weight: 600; margin-top: 4px;">
                        정배 승률 {rpt['fav_win_pct']}% · 역배 승점 {rpt['dog_pts_pct']}%
                    </div>
                </td>
            </tr>
        </table>

        <!-- 시각화 차트 섹션 (6각형 레이더 + 누적 추이) -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="{p['sec_hdr_bg']}" style="background-color: {p['sec_hdr_bg']}; padding: 10px 16px; font-size: 14px; color: {p['sec_hdr_fg']}; text-align: left; border-bottom: 1px solid {p['bd_strong']};">
                    ⬡ 6각형 전력 레이더 &amp; 시즌 누적 추이 그래프{compare_note}
                </th>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg1']}" style="background-color: {p['row_bg1']}; padding: 14px 12px 8px 12px; text-align: center;">
                    <img src="{chart_uri}" alt="Scouting Radar and Trend Chart" style="width: 100%; max-width: 780px; height: auto; border-radius: 8px; border: 1px solid {p['bd']};" />
                </td>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg1']}" style="background-color: {p['row_bg1']}; padding: 0 16px 12px 16px; text-align: center; font-size: 12px; color: {p['txt_sub']}; border-bottom: 1px solid {p['bd_strong']};">
                    <b style="color: {p['txt_main']};">[6각형 세부 점수]</b> {radar_vals_txt}
                </td>
            </tr>
        </table>

        <!-- 섹션 1: 홈 vs 원정 정밀 비교표 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="{p['sec_hdr_bg']}" colspan="7" style="background-color: {p['sec_hdr_bg']}; padding: 10px 16px; font-size: 14px; color: {p['sec_hdr_fg']}; text-align: left; border-bottom: 1px solid {p['bd_strong']};">
                    🏠 홈 vs 원정 정밀 비교표 (설정 언오버 {rpt['sel_ou']} 기준)
                </th>
            </tr>
            <tr>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">구분</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">전적 (승률)</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">평균 득/실</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">xG / xGA</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">점유율</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">{rpt['sel_ou']} 오버</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">경기당 승점</th>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg1']}" style="padding: 10px 6px; font-size: 13px; font-weight: 800; color: {p['c_blue']}; text-align: center; border-bottom: 1px solid {p['bd']};">🏠 홈 ({rpt['h_n']}전)</td>
                <td bgcolor="{p['row_bg1']}" style="padding: 10px 6px; font-size: 13px; font-weight: 700; color: {p['txt_main']}; text-align: center; border-bottom: 1px solid {p['bd']};">{rpt['hw']}승{rpt['hd']}무{rpt['hl']}패 ({rpt['h_win_pct']}%)</td>
                <td bgcolor="{p['row_bg1']}" style="padding: 10px 6px; font-size: 13px; color: {p['txt_body']}; text-align: center; border-bottom: 1px solid {p['bd']};">{rpt['h_gf']} / {rpt['h_ga']}</td>
                <td bgcolor="{p['row_bg1']}" style="padding: 10px 6px; font-size: 13px; color: {p['txt_body']}; text-align: center; border-bottom: 1px solid {p['bd']};">{rpt['h_xg']} / {rpt['h_xga']}</td>
                <td bgcolor="{p['row_bg1']}" style="padding: 10px 6px; font-size: 13px; color: {p['txt_body']}; text-align: center; border-bottom: 1px solid {p['bd']};">{rpt['h_poss']}%</td>
                <td bgcolor="{p['row_bg1']}" style="padding: 10px 6px; font-size: 13px; color: {p['c_red']}; font-weight: 700; text-align: center; border-bottom: 1px solid {p['bd']};">{rpt['h_ov_pct']}%</td>
                <td bgcolor="{p['row_bg1']}" style="padding: 10px 6px; font-size: 13px; font-weight: 800; color: {p['txt_main']}; text-align: center; border-bottom: 1px solid {p['bd']};">{rpt['h_ppg']}점</td>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg2']}" style="padding: 10px 6px; font-size: 13px; font-weight: 800; color: {p['c_red']}; text-align: center; border-bottom: 1px solid {p['bd_strong']};">🚗 원정 ({rpt['a_n']}전)</td>
                <td bgcolor="{p['row_bg2']}" style="padding: 10px 6px; font-size: 13px; font-weight: 700; color: {p['txt_main']}; text-align: center; border-bottom: 1px solid {p['bd_strong']};">{rpt['aw']}승{rpt['ad']}무{rpt['al']}패 ({rpt['a_win_pct']}%)</td>
                <td bgcolor="{p['row_bg2']}" style="padding: 10px 6px; font-size: 13px; color: {p['txt_body']}; text-align: center; border-bottom: 1px solid {p['bd_strong']};">{rpt['a_gf']} / {rpt['a_ga']}</td>
                <td bgcolor="{p['row_bg2']}" style="padding: 10px 6px; font-size: 13px; color: {p['txt_body']}; text-align: center; border-bottom: 1px solid {p['bd_strong']};">{rpt['a_xg']} / {rpt['a_xga']}</td>
                <td bgcolor="{p['row_bg2']}" style="padding: 10px 6px; font-size: 13px; color: {p['txt_body']}; text-align: center; border-bottom: 1px solid {p['bd_strong']};">{rpt['a_poss']}%</td>
                <td bgcolor="{p['row_bg2']}" style="padding: 10px 6px; font-size: 13px; color: {p['c_red']}; font-weight: 700; text-align: center; border-bottom: 1px solid {p['bd_strong']};">{rpt['a_ov_pct']}%</td>
                <td bgcolor="{p['row_bg2']}" style="padding: 10px 6px; font-size: 13px; font-weight: 800; color: {p['txt_main']}; text-align: center; border-bottom: 1px solid {p['bd_strong']};">{rpt['a_ppg']}점</td>
            </tr>
        </table>

        <!-- 섹션 2: 공수 퀄리티 / 키퍼 / 전후반 / 멘탈 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="{p['sec_hdr_bg']}" colspan="2" style="background-color: {p['sec_hdr_bg']}; padding: 10px 16px; font-size: 14px; color: {p['sec_hdr_fg']}; text-align: left; border-bottom: 1px solid {p['bd_strong']};">
                    ⚔️ 공격·수비·키퍼 퀄리티 &amp; 전·후반 패턴 · 멘탈 지표
                </th>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg1']}" style="background-color: {p['row_bg1']}; width: 50%; padding: 14px 16px; border-bottom: 1px solid {p['bd']}; border-right: 1px solid {p['bd']}; font-size: 14px; color: {p['txt_body']}; line-height: 1.85; vertical-align: top;">
                    <b style="color: {p['txt_main']};">• xG 결정력:</b> xG {rpt['avg_xg']} vs 득점 {rpt['avg_gf']} (<b style="color: {xg_fg};">{rpt['xg_diff']:+.2f}</b>)<br>
                    <b style="color: {p['txt_main']};">• xGA 수비력:</b> xGA {rpt['avg_xga']} vs 실점 {rpt['avg_ga']} (<b style="color: {xga_fg};">{rpt['xga_diff']:+.2f}</b>)<br>
                    <b style="color: {p['txt_main']};">• 압도 지표:</b> xGD <b style="color: {p['txt_main']};">{rpt['xgd']:+.2f}</b> · 유효슈팅 마진 <b style="color: {p['txt_main']};">{rpt['sot_margin']:+.1f}회</b><br>
                    <b style="color: {p['txt_main']};">• 공격 슈팅:</b> 슈팅당 xG <b style="color: {p['txt_main']};">{rpt['xg_per_shot']}</b> · 정확도 <b style="color: {p['txt_main']};">{rpt['shot_acc_pct']}%</b> · 전환율 <b style="color: {p['txt_main']};">{rpt['sot_conv_pct']}%</b><br>
                    <b style="color: {p['txt_main']};">• 수비/키퍼:</b> 허용 xGA/슛 <b style="color: {p['txt_main']};">{rpt['xga_per_shot']}</b> · 선방률 <b style="color: {p['c_green']};">{rpt['gk_save_pct']}%</b><br>
                    <b style="color: {p['txt_main']};">• 리그 순위:</b> 득점 <b style="color: {p['txt_main']};">{rpt['rank_gf']}</b> · 최소실점 <b style="color: {p['txt_main']};">{rpt['rank_ga']}</b> · xG <b style="color: {p['txt_main']};">{rpt['rank_xg']}</b>
                </td>
                <td bgcolor="{p['row_bg1']}" style="background-color: {p['row_bg1']}; width: 50%; padding: 14px 16px; border-bottom: 1px solid {p['bd']}; font-size: 14px; color: {p['txt_body']}; line-height: 1.85; vertical-align: top;">
                    <b style="color: {p['txt_main']};">• 전반 흐름:</b> 전반 득점률 <b style="color: {p['txt_main']};">{rpt['fh_score_pct']}%</b> · 전반 무실점 <b style="color: {p['txt_main']};">{rpt['fh_cs_pct']}%</b><br>
                    <b style="color: {p['txt_main']};">• 후반 집중력:</b> 후반 득실마진 <b style="color: {p['txt_main']};">{rpt['sh_gd_avg']:+.2f}골</b> · 후반 실점비중 <b style="color: {p['txt_main']};">{rpt['sh_ga_share']}%</b><br>
                    <b style="color: {p['txt_main']};">• 전반 리드 굳히기:</b> 승률 <b style="color: {p['c_blue']};">{rpt['ht_lead_win_pct']}%</b> ({rpt['ht_lead_str']})<br>
                    <b style="color: {p['txt_main']};">• 전반 무승부 시:</b> 승 {rpt['ht_draw_w']}% · 무 {rpt['ht_draw_d']}% · 패 {rpt['ht_draw_l']}% ({rpt['ht_draw_n']}전)<br>
                    <b style="color: {p['txt_main']};">• 전반 열세 반격:</b> 승점 획득 <b style="color: {p['c_green']};">{rpt['ht_trail_pts_pct']}%</b> ({rpt['ht_trail_str']})<br>
                    <b style="color: {p['txt_main']};">• 기세/멘탈:</b> 승 직후 <b style="color: {p['txt_main']};">{rpt['after_win_pct']}</b> · 패 직후 반등 <b style="color: {p['txt_main']};">{rpt['bounce_win_pct']}</b> (무패 {rpt['bounce_unb_pct']})<br>
                    <b style="color: {p['txt_main']};">• 시나리오 TOP3:</b> {top_htft_str}
                </td>
            </tr>

            <!-- 섹션 3: 베팅 DNA / 핸디캡 / 언오버 / 배당 반응도 -->
            <tr>
                <th bgcolor="{p['sec_hdr_bg']}" colspan="2" style="background-color: {p['sec_hdr_bg']}; padding: 10px 16px; font-size: 14px; color: {p['sec_hdr_fg']}; text-align: left; border-bottom: 1px solid {p['bd_strong']};">
                    🎯 베팅 DNA · 사용자 설정 핸디캡/언오버 · 상대전력 &amp; 배당 반응도
                </th>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg2']}" style="background-color: {p['row_bg2']}; width: 50%; padding: 14px 16px; border-bottom: 1px solid {p['bd']}; border-right: 1px solid {p['bd']}; font-size: 14px; color: {p['txt_body']}; line-height: 1.85; vertical-align: top;">
                    <b style="color: {p['txt_main']};">• 설정 {rpt['sel_ou']} 언오버:</b> 오버 <b style="color: {p['c_red']};">{rpt['sel_ov_pct']}%</b> / 언더 <b style="color: {p['c_blue']};">{rpt['sel_un_pct']}%</b><br>
                    <b style="color: {p['txt_main']};">• 기준점별 오버:</b> 1.5↑ <b style="color: {p['txt_main']};">{rpt['ov15_pct']}%</b> · 2.5↑ <b style="color: {p['txt_main']};">{rpt['ov25_pct']}%</b> · 3.5↑ <b style="color: {p['txt_main']};">{rpt['ov35_pct']}%</b><br>
                    <b style="color: {p['txt_main']};">• 양팀득점(BTTS):</b> <b style="color: {p['txt_main']};">{rpt['btts_pct']}%</b> · 최다 스코어: {top_scores_str}<br>
                    <b style="color: {p['txt_main']};">• 무승부 지수:</b> 무 {rpt['draw_pct']}% (0:0·1:1 {rpt['low_draw_cnt']}회) · 무 ROI <b style="color: {draw_roi_fg};">{rpt['draw_roi_pct']:+.1f}%</b><br>
                    {hc_lines_html}
                </td>
                <td bgcolor="{p['row_bg2']}" style="background-color: {p['row_bg2']}; width: 50%; padding: 14px 16px; border-bottom: 1px solid {p['bd']}; font-size: 14px; color: {p['txt_body']}; line-height: 1.85; vertical-align: top;">
                    <b style="color: {p['txt_main']};">• 약팀 상대 (≤1.7):</b> 승률 <b style="color: {p['txt_main']};">{rpt['vs_weak_pct']}</b> ({rpt['vs_weak_rec']})<br>
                    <b style="color: {p['txt_main']};">• 호각세 (1.7~2.8):</b> 승률 <b style="color: {p['txt_main']};">{rpt['vs_mid_pct']}</b> ({rpt['vs_mid_rec']})<br>
                    <b style="color: {p['txt_main']};">• 강팀 상대 (&gt;2.8):</b> 승률 <b style="color: {p['txt_main']};">{rpt['vs_strong_pct']}</b> ({rpt['vs_strong_rec']})<br>
                    <b style="color: {p['txt_main']};">• 정배 심화:</b> 정배 시 -1.0 마핸 <b style="color: {p['txt_main']};">{rpt['fav_m1_pct']}</b> · 초정배(≤1.5) 함정 <b style="color: {p['c_red']};">{rpt['trap_pct']}</b><br>
                    <b style="color: {p['txt_main']};">• 배트맨 경계 vs 가치:</b> 경계 <b style="color: {p['c_blue']};">{rpt['bm_tight_pct']}</b> · 가치 <b style="color: {p['c_green']};">{rpt['bm_value_pct']}</b><br>
                    <b style="color: {p['txt_main']};">• 해외 8개사 일치도:</b> 의견일치 <b style="color: {p['txt_main']};">{rpt['ov_cons_pct']}</b> · 의견분분 <b style="color: {p['txt_main']};">{rpt['ov_div_pct']}</b>
                </td>
            </tr>

            <!-- 섹션 4: 주력 전술 / 경기 스타일 / 상성 -->
            <tr>
                <th bgcolor="{p['sec_hdr_bg']}" colspan="2" style="background-color: {p['sec_hdr_bg']}; padding: 10px 16px; font-size: 14px; color: {p['sec_hdr_fg']}; text-align: left; border-bottom: 1px solid {p['bd_strong']};">
                    ♟️ 주력 전술 · 경기 스타일 · 점유율/득점대/수비 상성
                </th>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg1']}" colspan="2" style="background-color: {p['row_bg1']}; padding: 14px 16px; border-bottom: 1px solid {p['bd_strong']}; font-size: 14px; color: {p['txt_body']}; line-height: 1.85;">
                    <b style="color: {p['txt_main']};">• 주력 포메이션:</b> {tac_html} &nbsp;(전술 유연성: 총 <b style="color: {p['txt_main']};">{rpt['tac_cnt']}종</b> · 주력 비중 <b style="color: {p['txt_main']};">{rpt['main_tac_pct']}%</b>)<br>
                    <b style="color: {p['txt_main']};">• 경기 스타일:</b> 평균 점유율 <b style="color: {p['txt_main']};">{rpt['avg_poss']}%</b> · 패스 <b style="color: {p['txt_main']};">{rpt['avg_pass']}%</b> · 경고 <b style="color: {p['txt_main']};">{rpt['avg_yc']}장</b>(퇴장 {rpt['tot_rc']}회) · 상대 경고 유도 <b style="color: {p['txt_main']};">{rpt['opp_avg_yc']}장</b><br>
                    <b style="color: {p['txt_main']};">• 점유율별 승률:</b> 지공형(55%↑) <b style="color: {p['txt_main']};">{rpt['pos_high_str']}</b> &nbsp;|&nbsp; 역습형(45%↓) <b style="color: {p['txt_main']};">{rpt['pos_low_str']}</b><br>
                    <b style="color: {p['txt_main']};">• 경기 양상별:</b> 화력전(3골↑) 승률 <b style="color: {p['txt_main']};">{rpt['high_g_win']}</b> &nbsp;|&nbsp; 진흙탕(2골↓) 승률 <b style="color: {p['txt_main']};">{rpt['low_g_win']}</b> &nbsp;|&nbsp; 1골차↓ 접전 <b style="color: {p['txt_main']};">{rpt['tight_g_pct']}%</b> · 4골↑ 난타전 <b style="color: {p['txt_main']};">{rpt['wild_g_pct']}%</b><br>
                    <b style="color: {p['txt_main']};">• 상대 수비 상성:</b> vs 3백 <b style="color: {p['txt_main']};">{rpt['vs_3b_str']}</b> &nbsp;|&nbsp; vs 4백 <b style="color: {p['txt_main']};">{rpt['vs_4b_str']}</b> &nbsp;|&nbsp; 최근 5경기 폼: 득점 {rpt['r5_gf']} ({rpt['r5_gf_diff']:+.2f}) · xG {rpt['r5_xg']} ({rpt['r5_xg_diff']:+.2f})
                </td>
            </tr>
        </table>

        <!-- 섹션 5: 최근 5경기 상세 매치 로그 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="{p['sec_hdr_bg']}" colspan="6" style="background-color: {p['sec_hdr_bg']}; padding: 10px 16px; font-size: 14px; color: {p['sec_hdr_fg']}; text-align: left; border-bottom: 1px solid {p['bd_strong']};">
                    📅 최근 5경기 상세 매치 로그
                </th>
            </tr>
            <tr>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">날짜</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">장소</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 10px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: left; border-bottom: 1px solid {p['bd']};">상대팀</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">스코어</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">xG / xGA</th>
                <th bgcolor="{p['tbl_hdr_bg']}" style="padding: 8px 6px; font-size: 13px; color: {p['tbl_hdr_fg']}; text-align: center; border-bottom: 1px solid {p['bd']};">배트맨 승배당</th>
            </tr>
            {log_rows_html}
        </table>

        <!-- 섹션 6: 초보자를 위한 용어·지표 완벽 가이드 -->
        <table width="100%" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse;">
            <tr>
                <th bgcolor="#0f172a" style="background-color: #0f172a; padding: 10px 16px; font-size: 14px; color: #fbbf24; text-align: left; border-top: 1px solid {p['bd_strong']};">
                    📖 처음 보시는 분들을 위한 핵심 용어·지표 쉬운 설명서
                </th>
            </tr>
            <tr>
                <td bgcolor="{p['row_bg2']}" style="background-color: {p['row_bg2']}; padding: 14px 18px; font-size: 13px; color: {p['txt_body']}; line-height: 1.85; border-top: 1px solid {p['bd']};">
                    <b style="color: {p['txt_main']};">① xG(기대득점) · xGA(기대실점) · xGD(기대득실차):</b> 슈팅 위치와 찬스 난이도로 계산한 "원래 나왔어야 할 골 수치"입니다. 실제 득점이 xG보다 높으면 <b>골 결정력 우수</b>, 실제 실점이 xGA보다 낮으면 <b>수비·키퍼 안정감 우수</b>를 뜻합니다.<br>
                    <b style="color: {p['txt_main']};">② xPts(기대승점):</b> 경기 내용(xG/xGA) 기준 원래 얻었어야 할 승점입니다. 실제 승점이 훨씬 높으면 <b>거품 주의</b>, xPts가 훨씬 높으면 <b>불운/반등 가능성</b>을 의미합니다.<br>
                    <b style="color: {p['txt_main']};">③ 슈팅당 xG &amp; 허용 슈팅당 xGA:</b> 슈팅 1개당 골 확률입니다. 공격 시 높으면 <b>빅찬스 창출형</b>, 수비 시 낮으면 <b>중거리만 허용하는 단단한 박스 수비</b>입니다.<br>
                    <b style="color: {p['txt_main']};">④ 배당 수익률(ROI) &amp; 무승부 ROI:</b> 매 경기 승리(또는 무승부)에 동일 금액을 걸었을 때의 누적 수익률입니다. (+)면 <b>배당 효자 팀</b>, (-)면 <b>거품 팀</b>입니다.<br>
                    <b style="color: {p['txt_main']};">⑤ 배트맨 경계 구간 vs 가치 구간:</b> 환급률 차이를 보정했을 때, <b>경계 구간</b>은 배트맨이 해외보다 배당을 유독 짜게 깎아 승리를 경계한 경기이며, <b>가치 구간</b>은 반대로 배당을 후하게 준 경기입니다.<br>
                    <b style="color: {p['txt_main']};">⑥ 해외 8개사 일치도 &amp; 초정배(≤1.5) 함정:</b> 해외 8개사의 배당 편차가 작으면 <b>의견일치</b>, 크면 <b>의견분분</b>입니다. <b>초정배 함정</b>은 1.50 이하 저배당을 받고도 비기거나 진 비율입니다.<br>
                    <b style="color: {p['txt_main']};">⑦ 6각형 레이더 약어:</b> <b>ATK</b>(공격력) · <b>DEF</b>(수비력) · <b>CTL</b>(주도권) · <b>FIN</b>(결정력) · <b>MNT</b>(후반 뒷심/멘탈) · <b>VAL</b>(배당가치)를 0~100점으로 환산했습니다.
                </td>
            </tr>
        </table>
    </div>
    """
    return html


def render_tab8_scouting(spreadsheet_id, overseas_bookmakers):
    st.subheader("📋 팀 종합 스카우팅 리포트 (6각형 레이더 · 누적 추이 · 9대 배당 교차 분석)")
    st.caption("시즌, 리그, 팀(및 비교할 상대팀)을 선택하면 6각형 레이더 차트, 누적 추이 그래프, 구단 로고가 포함된 프리미엄 리포트를 생성합니다.")

    df_stats = load_sheet_data("경기내용", spreadsheet_id)
    if df_stats.empty or "홈팀" not in df_stats.columns or "원정팀" not in df_stats.columns:
        st.warning("⚠️ '경기내용' 시트에 데이터가 없습니다.")
        return

    seasons = ["전체"] + sorted(df_stats["시즌"].dropna().astype(str).str.strip().unique().tolist(), reverse=True) if "시즌" in df_stats.columns else ["전체"]
    leagues = ["전체"] + sorted(df_stats["리그명"].dropna().astype(str).str.strip().unique().tolist()) if "리그명" in df_stats.columns else ["전체"]

    c_sel1, c_sel2, c_sel3, c_sel4 = st.columns(4)
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
    compare_options = ["선택 안 함 (리그 평균 비교)"] + [t for t in available_teams if t != sel_team]
    sel_compare = c_sel4.selectbox("⚔️ 비교 상대팀 (육각형 겹치기)", compare_options, index=0, key="scout_compare_team")
    compare_team = None if sel_compare.startswith("선택 안 함") else sel_compare

    c_opt1, c_opt2, c_opt3, c_opt4 = st.columns([2, 1, 1, 1])
    sel_hc_lines = c_opt1.multiselect(
        "🎯 핸디캡 기준점 (복수 선택)",
        HC_OPTIONS,
        default=[-1.0, 1.0],
        format_func=format_hc_label,
        key="scout_hc_lines"
    )
    sel_ou_line = float(c_opt2.selectbox(
        "⚡ 언오버 기준점",
        OU_OPTIONS,
        index=OU_OPTIONS.index(2.5),
        key="scout_ou_line"
    ))
    theme_choice = c_opt3.radio(
        "🎨 리포트 테마",
        ["🌙 프리미엄 다크", "☀️ 클린 라이트"],
        index=0,
        horizontal=True,
        key="scout_theme_mode"
    )
    theme_mode = "dark" if "다크" in theme_choice else "light"

    use_transparent_logo = c_opt4.checkbox(
        "✨ 로고 배경 투명화",
        value=True,
        key="scout_logo_transparent"
    )
    hc_lines_used = sort_hc_lines(sel_hc_lines) if sel_hc_lines else [-1.0, 1.0]

    if st.button(f"🔍 [{sel_team}] 종합 스카우팅 리포트 생성하기", type="primary", use_container_width=True, key="btn_run_scouting"):
        with st.spinner(f"[{sel_team}] 6각형 차트·누적 추이·로고·9대 배당 데이터를 교차 분석 중입니다..."):
            bm_lookup, ov_lookup = _build_odds_lookups_cached(spreadsheet_id, tuple(overseas_bookmakers))
            logo_map = _load_drive_logo_map(LOGO_FOLDER_ID)
            raw_logo_url = _get_team_logo_url(logo_map, sel_team)
            logo_src = _make_transparent_logo_data_uri(raw_logo_url) if (raw_logo_url and use_transparent_logo) else raw_logo_url

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
                ht_res = "승" if gf_1h > ga_1h else ("무" if gf_1h == ga_1h else "패")

                bm_odds = _lookup_odds(bm_lookup, ndt, sn, hm, aw)
                ov_odds = _lookup_odds(ov_lookup, ndt, sn, hm, aw)

                team_bm_odd = (bm_odds[0] if is_home else bm_odds[2]) if bm_odds else 0.0
                draw_bm_odd = bm_odds[1] if bm_odds else 0.0
                opp_bm_odd = (bm_odds[2] if is_home else bm_odds[0]) if bm_odds else 0.0
                is_fav = (team_bm_odd > 0 and opp_bm_odd > 0 and team_bm_odd < opp_bm_odd)
                is_dog = (team_bm_odd > 0 and opp_bm_odd > 0 and team_bm_odd > opp_bm_odd)

                bm_react = None
                ov_std = -1.0
                if bm_odds and ov_odds:
                    bm_inv = (1 / bm_odds[0]) + (1 / bm_odds[1]) + (1 / bm_odds[2])
                    ov_inv = (1 / ov_odds[0]) + (1 / ov_odds[1]) + (1 / ov_odds[2])
                    if bm_inv > 0 and ov_inv > 0:
                        bm_prob = (1 / team_bm_odd) / bm_inv
                        ov_team_odd = ov_odds[0] if is_home else ov_odds[2]
                        ov_prob = (1 / ov_team_odd) / ov_inv
                        bm_react = "tight" if bm_prob > ov_prob else "value"
                if ov_odds:
                    ov_std = ov_odds[3] if is_home else ov_odds[4]

                matches.append({
                    "sort_k": ndt, "date": dt, "is_home": is_home, "opp": aw if is_home else hm,
                    "gf_1h": gf_1h, "gf_2h": gf_2h, "ga_1h": ga_1h, "ga_2h": ga_2h,
                    "gf": gf, "ga": ga, "xg": xg, "xga": xga,
                    "shots": shots, "opp_shots": opp_shots, "sot": sot, "opp_sot": opp_sot,
                    "poss": poss, "pass_pct": pass_pct, "yc": yc, "opp_yc": opp_yc, "rc": rc,
                    "my_tac": my_tac, "opp_tac": opp_tac, "res": res, "ht_res": ht_res,
                    "team_bm_odd": team_bm_odd, "draw_bm_odd": draw_bm_odd,
                    "is_fav": is_fav, "is_dog": is_dog, "bm_react": bm_react, "ov_std": ov_std
                })

            matches.sort(key=lambda x: x["sort_k"])
            total_n = len(matches)
            if total_n == 0:
                st.info(f"💡 [{sel_team}]의 경기 데이터가 없습니다.")
                return

            cum_pts, cum_xpts, cum_roi_units = [], [], []
            acc_p, acc_xp, acc_u = 0.0, 0.0, 0.0
            for m in matches:
                acc_p += (3 if m["res"] == "승" else (1 if m["res"] == "무" else 0))
                acc_xp += _poisson_xpts(m["xg"], m["xga"])
                if m["team_bm_odd"] >= 1.01:
                    acc_u += (m["team_bm_odd"] - 1.0) if m["res"] == "승" else -1.0
                cum_pts.append(acc_p)
                cum_xpts.append(round(acc_xp, 2))
                cum_roi_units.append(round(acc_u, 2))

            w = sum(1 for m in matches if m["res"] == "승")
            d = sum(1 for m in matches if m["res"] == "무")
            l = sum(1 for m in matches if m["res"] == "패")
            win_pct = round((w / total_n) * 100, 1)
            draw_pct = round((d / total_n) * 100, 1)
            pts = w * 3 + d
            xpts = round(acc_xp, 1)
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

            htft_counter = Counter(f"전반{m['ht_res']}→최종{m['res']}" for m in matches)
            top_htft = [(k, round((v / total_n) * 100, 1)) for k, v in htft_counter.most_common(3)]

            after_win = [matches[i] for i in range(1, total_n) if matches[i - 1]["res"] == "승"]
            after_win_pct = f"{round((sum(1 for m in after_win if m['res'] == '승') / len(after_win)) * 100, 1)}% ({len(after_win)}전)" if after_win else "-"

            after_loss = [matches[i] for i in range(1, total_n) if matches[i - 1]["res"] == "패"]
            if after_loss:
                bounce_win_pct = f"{round((sum(1 for m in after_loss if m['res'] == '승') / len(after_loss)) * 100, 1)}% ({len(after_loss)}전)"
                bounce_unb_pct = f"{round((sum(1 for m in after_loss if m['res'] != '패') / len(after_loss)) * 100, 1)}%"
            else:
                bounce_win_pct, bounce_unb_pct = "-", "-"

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

            std_ms = [m for m in matches if m["ov_std"] >= 0]
            if len(std_ms) >= 2:
                med_std = float(np.median([m["ov_std"] for m in std_ms]))
                cons_ms = [m for m in std_ms if m["ov_std"] <= med_std]
                div_ms = [m for m in std_ms if m["ov_std"] > med_std]
                ov_cons_pct = f"{round((sum(1 for m in cons_ms if m['res']=='승')/len(cons_ms))*100,1)}% ({len(cons_ms)}전)" if cons_ms else "-"
                ov_div_pct = f"{round((sum(1 for m in div_ms if m['res']=='승')/len(div_ms))*100,1)}% ({len(div_ms)}전)" if div_ms else "-"
            else:
                ov_cons_pct, ov_div_pct = "-", "-"

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

            radar_scores = _compute_radar_scores_for_team(df_filtered, sel_team, bm_lookup)
            compare_radar_scores = _compute_radar_scores_for_team(df_filtered, compare_team, bm_lookup) if compare_team else None
            radar_avg = round(float(np.mean(radar_scores)), 1)
            grade, grade_color = _calc_grade(radar_avg)

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
                "compare_team": compare_team, "radar_scores": radar_scores,
                "compare_radar_scores": compare_radar_scores, "radar_avg": radar_avg,
                "grade": grade, "grade_color": grade_color,
                "cum_pts": cum_pts, "cum_xpts": cum_xpts, "cum_roi_units": cum_roi_units,
                "logo_src": logo_src, "logo_transparent": use_transparent_logo,
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
                "ht_trail_pts_pct": ht_trail_pts_pct, "ht_trail_str": ht_trail_str, "top_htft": top_htft,
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
                "ov_cons_pct": ov_cons_pct, "ov_div_pct": ov_div_pct,
                "top_tactics": top_tactics, "tac_cnt": tac_cnt, "main_tac_pct": main_tac_pct,
                "avg_poss": avg_poss, "avg_pass": avg_pass, "avg_yc": avg_yc, "opp_avg_yc": opp_avg_yc, "tot_rc": tot_rc,
                "pos_high_str": pos_high_str, "pos_low_str": pos_low_str,
                "high_g_win": high_g_win, "low_g_win": low_g_win, "tight_g_pct": tight_g_pct, "wild_g_pct": wild_g_pct,
                "vs_3b_str": vs_3b_str, "vs_4b_str": vs_4b_str,
                "r5_gf": r5_gf, "r5_xg": r5_xg, "r5_gf_diff": round(r5_gf - avg_gf, 2), "r5_xg_diff": round(r5_xg - avg_xg, 2),
                "tags": tags
            }
            st.session_state["t8_last_rpt_v6"] = rpt

    if "t8_last_rpt_v6" in st.session_state:
        rpt = st.session_state["t8_last_rpt_v6"]
        chart_uri, chart_png = _generate_charts_image(rpt, theme_mode=theme_mode)
        rpt["chart_uri"] = chart_uri

        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"종합 등급 ({rpt['grade']})", f"{rpt['w']}승 {rpt['d']}무 {rpt['l']}패", f"승점 {rpt['pts']} vs xPts {rpt['xpts']} ({rpt['pts_diff']:+.1f})")
        m2.metric("평균 득/실 (키퍼 선방률)", f"{rpt['avg_gf']} / {rpt['avg_ga']}", f"xGD {rpt['xgd']:+.2f} · 선방 {rpt['gk_save_pct']}%")
        m3.metric(f"승/무 ROI ({rpt['bm_matched_n']}건)", f"{rpt['roi_pct']:+.1f}% / {rpt['draw_roi_pct']:+.1f}%", f"정배 {rpt['fav_win_pct']}% · 역배승점 {rpt['dog_pts_pct']}%")
        m4.metric(f"{rpt['sel_ou']} 오버 / BTTS", f"{rpt['sel_ov_pct']}% / {rpt['btts_pct']}%", f"6각형 평균 {rpt['radar_avg']}점")

        st.download_button(
            label=f"📥 [{rpt['team']}] 6각형 레이더 & 추이 그래프 PNG 별도 저장",
            data=chart_png,
            file_name=f"{rpt['team']}_scouting_chart.png",
            mime="image/png",
            use_container_width=True
        )

        with st.expander("📊 / 📋 [네이버 블로그/카페 전용] 팀 종합 스카우팅 리포트 인포그래픽 복사 (추천 ⭐)", expanded=True):
            st.caption("초록색 버튼을 1번 클릭한 뒤 네이버 블로그/카페 글쓰기 창에서 Ctrl+V 하세요! (6각형 차트 + 투명 로고 + 용어 설명서 포함)")
            ig_html = generate_naver_scouting_infographic(rpt, theme_mode=theme_mode)
            render_clipboard_component(ig_html, f"t8_clip_scouting_v6_{theme_mode}", height=1880)    
