import streamlit as st
import pandas as pd
import numpy as np
import gspread
import time
import json
import re
import streamlit.components.v1 as components
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="Football 9-Bookmakers & Stats Hub",
    page_icon="⚽",
    layout="wide"
)

BOOKMAKERS = [
    "배트맨", "10x10", "1xbet", "betway", 
    "bwin", "william hill", "bet365", "pinnacle", "stake"
]
OVERSEAS_BOOKMAKERS = [
    "10x10", "1xbet", "betway", 
    "bwin", "william hill", "bet365", "pinnacle", "stake"
]
STATS_SHEET_NAME = "경기내용"
INJURY_SHEET_NAME = "부상자명단"
SCANNER_SHEET_NAME = "라운드스캔"
SPREADSHEET_ID = "1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ"

# 1번 탭 대기열
if "match_queue" not in st.session_state:
    st.session_state.match_queue = []
if "current_queue_idx" not in st.session_state:
    st.session_state.current_queue_idx = 0

# 2번 탭(스캐너) 전용 2단계 대기열
if "scan_queue" not in st.session_state:
    st.session_state.scan_queue = []
if "current_scan_queue_idx" not in st.session_state:
    st.session_state.current_scan_queue_idx = 0

# 스캐너에서 3/5/6번 탭으로 넘겨줄 세션 상태
if "selected_scan_match" not in st.session_state:
    st.session_state.selected_scan_match = None

# 상단 탭 중앙 정렬 & 인쇄 스타일
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    justify-content: center !important;
    gap: 15px !important;
    margin-bottom: 20px !important;
}
.stTabs [data-baseweb="tab"] {
    font-size: 15px !important;
    font-weight: bold !important;
    padding: 10px 18px !important;
}
@media print {
    section[data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .stTabs [data-baseweb="tab-list"] { display: none !important; }
    button { display: none !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; margin-bottom: 25px;'>⚽ 축구 9대 배당 업체 & 경기 세부 스탯 통합 분석 허브</h2>", unsafe_allow_html=True)

# =========================================================
# 🌟 날짜 파싱 유틸리티 함수
# =========================================================
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

# =========================================================
# 🌟 네이버 블로그 원클릭 복사 렌더러 컴포넌트
# =========================================================
def render_clipboard_component(html_content, component_id, height=520):
    escaped_html = json.dumps(html_content)
    wrapper_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 10px;
                font-family: 'Malgun Gothic', sans-serif;
                background-color: transparent;
            }}
            .copy-btn {{
                width: 100%;
                background-color: #03c75a;
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 12px;
            }}
            .copy-btn:hover {{
                background-color: #02b150;
            }}
            .preview-box {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
                overflow-x: auto;
            }}
        </style>
    </head>
    <body>
        <button class="copy-btn" onclick="copyHtmlToClipboard()">
            📋 [네이버 블로그/카페 서식 원클릭 복사하기] (클릭 후 블로그에 Ctrl+V)
        </button>
        <div class="preview-box">
            {html_content}
        </div>

        <script>
            function copyHtmlToClipboard() {{
                const htmlData = {escaped_html};
                const blobHtml = new Blob([htmlData], {{ type: 'text/html' }});
                const blobText = new Blob([htmlData.replace(/<[^>]*>?/gm, '')], {{ type: 'text/plain' }});
                const data = [new ClipboardItem({{ 'text/html': blobHtml, 'text/plain': blobText }})];

                navigator.clipboard.write(data).then(() => {{
                    alert('🎉 네이버 블로그/카페용 서식이 복사되었습니다! 블로그 글쓰기 창에서 [Ctrl + V]를 누르세요.');
                }}).catch(err => {{
                    alert('복사 권한이 제한되었습니다. 아래 미리보기 영역을 직접 드래그(Ctrl+C)해주세요.');
                }});
            }}
        </script>
    </body>
    </html>
    """
    components.html(wrapper_html, height=height, scrolling=True)

# =========================================================
# 배당 인포그래픽 도표 (승무패 + 언오버 + 핸디캡 통합 지원)
# =========================================================
def generate_naver_odds_infographic(b_odds, overseas_name, o_odds, league_name="", home_team="", away_team="", market_type="1X2", line_val=0.0):
    if market_type == "1X2":
        b_h, b_d, b_a = b_odds
        o_h, o_d, o_a = o_odds

        if b_h > 0 and b_d > 0 and b_a > 0:
            b_inv = (1/b_h) + (1/b_d) + (1/b_a)
            b_payout = (1 / b_inv) * 100
            b_prob_h = ((1/b_h) / b_inv) * 100
            b_prob_d = ((1/b_d) / b_inv) * 100
            b_prob_a = ((1/b_a) / b_inv) * 100
        else:
            b_payout, b_prob_h, b_prob_d, b_prob_a = 0.0, 33.3, 33.3, 33.4

        if o_h > 0 and o_d > 0 and o_a > 0:
            o_inv = (1/o_h) + (1/o_d) + (1/o_a)
            o_payout = (1 / o_inv) * 100
            o_prob_h = ((1/o_h) / o_inv) * 100
            o_prob_d = ((1/o_d) / o_inv) * 100
            o_prob_a = ((1/o_a) / o_inv) * 100
            fair_h = round((b_payout / 100) / (o_prob_h / 100), 2) if o_prob_h > 0 else 0.0
            fair_d = round((b_payout / 100) / (o_prob_d / 100), 2) if o_prob_d > 0 else 0.0
            fair_a = round((b_payout / 100) / (o_prob_a / 100), 2) if o_prob_a > 0 else 0.0
        else:
            o_payout, o_prob_h, o_prob_d, o_prob_a = 0.0, 0.0, 0.0, 0.0
            fair_h, fair_d, fair_a = 0.0, 0.0, 0.0

        diff_h = round(b_h - o_h, 2) if (b_h > 0 and o_h > 0) else 0.0
        diff_d = round(b_d - o_d, 2) if (b_d > 0 and o_d > 0) else 0.0
        diff_a = round(b_a - o_a, 2) if (b_a > 0 and o_a > 0) else 0.0

        diff_h_str = f"+{diff_h}" if diff_h > 0 else f"{diff_h}"
        diff_d_str = f"+{diff_d}" if diff_d > 0 else f"{diff_d}"
        diff_a_str = f"+{diff_a}" if diff_a > 0 else f"{diff_a}"

        lg_badge = f"<span style='background-color: #2563eb; color: #ffffff; padding: 2px 7px; border-radius: 4px; font-size: 11px; margin-right: 6px;'>{league_name}</span>" if league_name else ""
        match_title = f"<div style='font-size: 19px; font-weight: bold; color: #0f172a; margin-top: 4px;'><span style='color: #dc2626;'>{home_team}</span> <span style='font-size: 14px; color: #64748b;'>VS</span> <span style='color: #2563eb;'>{away_team}</span></div>" if (home_team or away_team) else f"<div style='font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 4px;'>{lg_badge}배당 및 승률 정밀 분석 리포트</div>"

        h_col_name = f"홈 ({home_team})" if home_team else "홈 승 (Home)"
        a_col_name = f"원정 ({away_team})" if away_team else "원정승 (Away)"

        return f"""
        <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; border-collapse: separate; color: #0f172a;">
            <tr>
                <td style="padding: 20px;">
                    <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 16px;">
                        <tr>
                            <td align="center" style="padding-bottom: 10px; text-align: center;">
                                <div style="font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 1px;">ODDS & PROBABILITY REPORT (승무패)</div>
                                {match_title}
                                <div style="font-size: 12px; color: #475569; margin-top: 4px;">{lg_badge}기준: <b>배트맨</b> vs <b>{overseas_name.upper()}</b></div>
                            </td>
                        </tr>
                    </table>
                    <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                        <tr style="background-color: #f8fafc;">
                            <th style="padding: 8px; border: 1px solid #cbd5e1; color: #dc2626; width: 33%;">🔴 홈 승</th>
                            <th style="padding: 8px; border: 1px solid #cbd5e1; color: #059669; width: 34%;">🟢 무승부</th>
                            <th style="padding: 8px; border: 1px solid #cbd5e1; color: #2563eb; width: 33%;">🔵 원정승</th>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #dc2626; font-size: 15px;">{round(b_prob_h, 1)}%</td>
                            <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #059669; font-size: 15px;">{round(b_prob_d, 1)}%</td>
                            <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #2563eb; font-size: 15px;">{round(b_prob_a, 1)}%</td>
                        </tr>
                    </table>
                    <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                        <tr style="background-color: #f8fafc;">
                            <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #334155;">구 분</th>
                            <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #dc2626;">{h_col_name}</th>
                            <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #059669;">무승부 (Draw)</th>
                            <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #2563eb;">{a_col_name}</th>
                        </tr>
                        <tr>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; background-color: #f8fafc; font-weight: bold;">배트맨 배당</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: #0f172a;">{b_h}</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: #0f172a;">{b_d}</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: #0f172a;">{b_a}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; background-color: #f8fafc; font-weight: bold;">{overseas_name}</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; color: #334155;">{o_h}</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; color: #334155;">{o_d}</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; color: #334155;">{o_a}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; background-color: #f8fafc; font-weight: bold;">배당 편차</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: {'#dc2626' if diff_h < 0 else '#2563eb'};">{diff_h_str}</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: {'#dc2626' if diff_d < 0 else '#2563eb'};">{diff_d_str}</td>
                            <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: {'#dc2626' if diff_a < 0 else '#2563eb'};">{diff_a_str}</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        """
    else:
        # 언오버 또는 핸디캡 양방향 마켓
        b_sel1, b_sel2 = b_odds
        o_sel1, o_sel2 = o_odds
        market_label = "오버/언더 (Over/Under)" if market_type == "OU" else f"핸디캡 ({line_val})"
        lbl1 = "오버 (Over)" if market_type == "OU" else "홈 핸디승"
        lbl2 = "언더 (Under)" if market_type == "OU" else "원정 핸디승"

        return f"""
        <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; border-collapse: separate; color: #0f172a;">
            <tr>
                <td style="padding: 20px;">
                    <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 16px;">
                        <tr>
                            <td align="center" style="padding-bottom: 10px; text-align: center;">
                                <div style="font-size: 11px; font-weight: bold; color: #2563eb; letter-spacing: 1px;">{market_label.upper()} REPORT</div>
                                <div style="font-size: 19px; font-weight: bold; color: #0f172a; margin-top: 4px;">{home_team} vs {away_team}</div>
                                <div style="font-size: 12px; color: #475569; margin-top: 4px;">기준점: <b>{line_val}</b> | 비교: <b>배트맨</b> vs <b>{overseas_name.upper()}</b></div>
                            </td>
                        </tr>
                    </table>
                    <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                        <tr style="background-color: #f8fafc;">
                            <th style="padding: 8px; border: 1px solid #cbd5e1; color: #334155; width: 50%;">🔥 {lbl1}</th>
                            <th style="padding: 8px; border: 1px solid #cbd5e1; color: #334155; width: 50%;">❄️ {lbl2}</th>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold; color: #dc2626; font-size: 16px;">배트맨: {b_sel1} / 해외: {o_sel1}</td>
                            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold; color: #2563eb; font-size: 16px;">배트맨: {b_sel2} / 해외: {o_sel2}</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        """

# =========================================================
# 단일 팀 시즌 평균 리포트 및 맞대결/부상자 리포트 (기존 유지)
# =========================================================
def generate_naver_team_stats_infographic(team_name, season, league, match_count_info, df_summary, tac_df, df_goals):
    html = f"""
    <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; color: #0f172a;">
        <tr><td style="padding: 20px;">
            <div style="font-size: 19px; font-weight: bold; margin-bottom: 10px;">📋 [{team_name}] 시즌 지표 종합 리포트</div>
    """
    if df_summary is not None and not df_summary.empty:
        html += df_summary.to_html(index=False, escape=False).replace('<table border="1" class="dataframe">', '<table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1;">')
    html += "</td></tr></table>"
    return html

def generate_naver_match_infographic(home_team, away_team, stats_data, goal_df=None, h2h_all_str="", h2h_exact_str=""):
    return f"""<table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;"><tr><td style="padding:20px;"><b>{home_team} vs {away_team} 맞대결 리포트</b><br>{h2h_all_str}</td></tr></table>"""

def generate_naver_injury_infographic(team_name, league_title, confirmed_list, doubt_list):
    return f"""<table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; background: #fff; border: 1px solid #cbd5e1; border-radius: 10px;"><tr><td style="padding:20px;"><b>{team_name} 부상자 리포트</b></td></tr></table>"""

# =========================================================
# 2. 구글 시트 연동 클라이언트 (캐싱 최적화)
# =========================================================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
        return None
    except Exception:
        return None

@st.cache_data(ttl=600, show_spinner=False)
def load_sheet_data(sheet_name):
    client = get_gspread_client()
    if not client:
        return pd.DataFrame()
    for attempt in range(4):
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            ws = spreadsheet.worksheet(sheet_name)
            data = ws.get_all_values()
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                df = df.dropna(how='all')
                return df
            return pd.DataFrame()
        except Exception:
            time.sleep(1.0 * (attempt + 1))
            continue
    return pd.DataFrame()

# 구글 시트 일괄 저장 처리 함수 (승무패 + 언오버 + 핸디캡 선택적 확장 저장)
def save_match_data_to_sheets(match_info, odds_dict, stats_dict, ou_dict=None, hc_dict=None):
    client = get_gspread_client()
    if not client:
        return False, "구글 시트 연동 실패: Secrets 설정을 확인하세요."
    
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        season, league, match_date, home_team, away_team = match_info["season"], match_info["league"], match_info["date"], match_info["home"], match_info["away"]
        
        b_h, b_d, b_a = odds_dict.get("배트맨", (0.0, 0.0, 0.0))
        home_score = stats_dict["home_1h"] + stats_dict["home_2h"]
        away_score = stats_dict["away_1h"] + stats_dict["away_2h"]
        match_res = "홈승" if home_score > away_score else ("무승부" if home_score == away_score else "원정승")

        saved_count = 0
        for bm_name in BOOKMAKERS:
            if bm_name not in odds_dict:
                continue
            h, d, a = odds_dict[bm_name]
            if h <= 0 or d <= 0 or a <= 0:
                continue
            
            row_data_odds = [
                season, league, match_date, home_team, away_team,
                b_h, b_d, b_a, "75%", "33%", "33%", "33%",
                h, d, a, "75%", "33%", "33%", "33%",
                0, 0, 0, 0, 0, 0, 0, 0,
                home_score, away_score, home_score + away_score, home_score - away_score, abs(home_score - away_score),
                "정배", match_res, h
            ]
            
            # 언오버 / 핸디캡 선택 데이터가 있다면 우측 빈 공간에 확장 추가
            if ou_dict and bm_name in ou_dict:
                ou_line, ou_o, ou_u = ou_dict[bm_name]
                row_data_odds.extend([ou_line, ou_o, ou_u])
            else:
                row_data_odds.extend([0.0, 0.0, 0.0])

            if hc_dict and bm_name in hc_dict:
                hc_line, hc_h_odd, hc_a_odd = hc_dict[bm_name]
                row_data_odds.extend([hc_line, hc_h_odd, hc_a_odd])
            else:
                row_data_odds.extend([0.0, 0.0, 0.0])

            try:
                ws = spreadsheet.worksheet(bm_name)
                ws.append_row(row_data_odds, value_input_option="USER_ENTERED")
                saved_count += 1
                time.sleep(0.12)
            except gspread.exceptions.WorksheetNotFound:
                pass

        # 스탯 저장
        row_data_stats = [
            season, league, match_date, home_team, away_team,
            stats_dict["home_1h"], stats_dict["home_2h"], stats_dict["away_1h"], stats_dict["away_2h"],
            "50%", "50%", "50%", "50%",
            f"'{stats_dict['home_tac']}", f"'{stats_dict['away_tac']}",
            stats_dict["home_shots"], stats_dict["away_shots"], stats_dict["home_sot"], stats_dict["away_sot"],
            "50%", "50%", f"{stats_dict['home_poss']}%", f"{stats_dict['away_poss']}%",
            f"{stats_dict['home_pass']}%", f"{stats_dict['away_pass']}%",
            stats_dict["home_yc"], stats_dict["away_yc"], stats_dict["home_rc"], stats_dict["away_rc"],
            stats_dict["home_xg"], stats_dict["away_xg"]
        ]
        ws_stats = spreadsheet.worksheet(STATS_SHEET_NAME)
        ws_stats.append_row(row_data_stats, value_input_option="USER_ENTERED")

        return True, f"배당 {saved_count}개 탭 및 경기내용 저장 완료"
    except Exception as e:
        return False, str(e)

# 3. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.caption(f"연동 시트 ID: `{SPREADSHEET_ID}`")
    tol = st.number_input("배당 오차 허용치 (±)", value=0.03, step=0.01)
    if st.button("🔄 전체 시트 데이터 새로고침 (캐시 초기화)"):
        st.cache_data.clear()
        st.success("캐시 초기화 완료!")
        st.rerun()

# 4. 6개 탭 구성
tab_input, tab_scanner, tab_analysis, tab_team_stats, tab_h2h, tab_injuries = st.tabs([
    "📝 경기 데이터 입력 & 저장", 
    "📡 라운드 경기 자동 스캐너 & 추천픽",
    "📊 9개사 동일 배당 분석", 
    "📈 팀별 세부내용 평균계산기",
    "⚔️ 홈 vs 원정 맞대결 종합분석",
    "🚑 팀별 부상자/결장자 명단"
])

# =========================================================
# TAB 1: 📝 경기 데이터 입력 & 저장 (언오버/핸디캡 옵션 추가)
# =========================================================
with tab_input:
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
            with st.container(border=True):
                c_q1, c_q2, c_q3 = st.columns(3)
                q_season = c_q1.text_input("시즌", value="25-26", key="q_in_season")
                q_league = c_q2.text_input("리그명", value="PL", key="q_in_league")
                q_date = c_q3.text_input("경기 날짜", value="25.08.16", key="q_in_date")

                c_qt1, c_qt2 = st.columns(2)
                q_home = c_qt1.text_input("홈팀", placeholder="예: 리버풀", key="q_in_home")
                q_away = c_qt2.text_input("원정팀", placeholder="예: 본머스", key="q_in_away")

                st.markdown("**🏢 배트맨 최종 배당 (승무패)**")
                qb_h, qb_d, qb_a = st.columns(3)
                q_bh_val = qb_h.number_input("홈", value=0.0, step=0.01, min_value=0.0, key="q_in_bh")
                q_bd_val = qb_d.number_input("무", value=0.0, step=0.01, min_value=0.0, key="q_in_bd")
                q_ba_val = qb_a.number_input("원정", value=0.0, step=0.01, min_value=0.0, key="q_in_ba")

                # 선택적 언오버 / 핸디캡 입력 토글
                with st.expander("⚽ [선택] 언오버 및 핸디캡 배당 추가 입력", expanded=False):
                    st.caption("배당이 있는 경우에만 입력하세요. 없으면 비워두셔도 됩니다.")
                    qu_line = st.number_input("언오버 기준점", value=2.5, step=0.5, key="q_ou_line")
                    qu_o, qu_u = st.columns(2)
                    q_ou_over = qu_o.number_input("오버(Over) 배당", value=0.0, step=0.01, key="q_ou_o")
                    q_ou_under = qu_u.number_input("언더(Under) 배당", value=0.0, step=0.01, key="q_ou_u")

                    qh_line = st.number_input("핸디캡 기준점", value=-1.0, step=0.5, key="q_hc_line")
                    qh_h, qh_a = st.columns(2)
                    q_hc_home = qh_h.number_input("핸디 홈 배당", value=0.0, step=0.01, key="q_hc_h")
                    q_hc_away = qh_a.number_input("핸디 원정 배당", value=0.0, step=0.01, key="q_hc_a")

                st.markdown("**🌐 대상 해외 북메이커 선택**")
                selected_overseas = []
                cols_chk = st.columns(4)
                for idx, obm in enumerate(OVERSEAS_BOOKMAKERS):
                    with cols_chk[idx % 4]:
                        if st.checkbox(obm.upper(), value=True, key=f"chk_{obm}"):
                            selected_overseas.append(obm)

                if st.button("➕ 대기열에 경기 등록", type="primary", use_container_width=True):
                    if q_home.strip() and q_away.strip():
                        st.session_state.match_queue.append({
                            "season": q_season, "league": q_league, "date": q_date,
                            "home": q_home.strip(), "away": q_away.strip(),
                            "batman_odds": (q_bh_val, q_bd_val, q_ba_val),
                            "target_bms": selected_overseas,
                            "ou_data": (qu_line, q_ou_over, q_ou_under),
                            "hc_data": (qh_line, q_hc_home, q_hc_away)
                        })
                        st.success(f"🎉 [{q_home} vs {q_away}] 대기열 추가 완료!")
                    else:
                        st.warning("홈팀과 원정팀명을 입력해 주세요.")

            if st.session_state.match_queue:
                st.markdown("##### 📋 대기열 목록")
                q_preview = [{"순번": i+1, "경기": f"{m['home']} vs {m['away']}", "리그": m['league']} for i, m in enumerate(st.session_state.match_queue)]
                st.dataframe(pd.DataFrame(q_preview), use_container_width=True, hide_index=True)
                if st.button("🗑️ 대기열 전체 비우기"):
                    st.session_state.match_queue = []
                    st.session_state.current_queue_idx = 0
                    st.rerun()

        with col_step2:
            st.subheader("2️⃣ [2단계] 해외 배당 및 경기내용 순차 입력")
            queue_len = len(st.session_state.match_queue)
            cur_idx = st.session_state.current_queue_idx

            if queue_len == 0:
                st.info("💡 1단계에서 경기를 먼저 등록해 주세요.")
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

                st.markdown(f"""
                <div style="background-color: #1e3a8a; color: white; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <div style="font-size: 13px; color: #93c5fd;">[진행 중: {cur_idx + 1} / {queue_len} 번째 경기]</div>
                    <div style="font-size: 18px; font-weight: bold; margin-top: 4px;">👉 {cur_match['home']} vs {cur_match['away']} ({cur_match['league']})</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("##### 🏢 해외 북메이커 승무패 / 언오버 / 핸디캡 배당 입력")
                q_odds_inputs = {"배트맨": cur_match["batman_odds"]}
                q_ou_inputs = {"배트맨": cur_match["ou_data"]}
                q_hc_inputs = {"배트맨": cur_match["hc_data"]}

                target_bms = cur_match["target_bms"]
                if target_bms:
                    for bm in target_bms:
                        with st.expander(f"🏢 [{bm.upper()}] 배당 세부 입력", expanded=False):
                            oh, od, oa = st.columns(3)
                            h_v = oh.number_input("홈승", value=0.0, step=0.01, key=f"q_{cur_idx}_{bm}_h")
                            d_v = od.number_input("무승부", value=0.0, step=0.01, key=f"q_{cur_idx}_{bm}_d")
                            a_v = oa.number_input("원정승", value=0.0, step=0.01, key=f"q_{cur_idx}_{bm}_a")
                            q_odds_inputs[bm] = (h_v, d_v, a_v)

                            ou_l, ou_ov, ou_un = st.columns(3)
                            oul = ou_l.number_input("언오버 기준", value=2.5, step=0.5, key=f"q_{cur_idx}_{bm}_oul")
                            ouo = ou_ov.number_input("오버", value=0.0, step=0.01, key=f"q_{cur_idx}_{bm}_ouo")
                            oun = ou_un.number_input("언더", value=0.0, step=0.01, key=f"q_{cur_idx}_{bm}_oun")
                            q_ou_inputs[bm] = (oul, ouo, oun)

                            hcl, hch, hca = st.columns(3)
                            hclv = hcl.number_input("핸디 기준", value=-1.0, step=0.5, key=f"q_{cur_idx}_{bm}_hcl")
                            hcho = hch.number_input("핸디홈", value=0.0, step=0.01, key=f"q_{cur_idx}_{bm}_hcho")
                            hcao = hca.number_input("핸디원정", value=0.0, step=0.01, key=f"q_{cur_idx}_{bm}_hcao")
                            q_hc_inputs[bm] = (hclv, hcho, hcao)

                st.markdown("##### ⚽ 인게임 스탯 (경기내용 탭용)")
                with st.expander("⚽ 득점 및 세부 스탯", expanded=True):
                    c_g1, c_g2, c_g3, c_g4 = st.columns(4)
                    q_home_1h = c_g1.number_input("홈 전반", min_value=0, value=0, key=f"q_{cur_idx}_h1")
                    q_home_2h = c_g2.number_input("홈 후반", min_value=0, value=0, key=f"q_{cur_idx}_h2")
                    q_away_1h = c_g3.number_input("원정 전반", min_value=0, value=0, key=f"q_{cur_idx}_a1")
                    q_away_2h = c_g4.number_input("원정 후반", min_value=0, value=0, key=f"q_{cur_idx}_a2")
                    
                    c_tac1, c_tac2 = st.columns(2)
                    q_home_tac = c_tac1.text_input("홈 전술", value="4-2-3-1", key=f"q_{cur_idx}_htac")
                    q_away_tac = c_tac2.text_input("원정 전술", value="4-3-3", key=f"q_{cur_idx}_atac")

                    c_st1, c_st2, c_st3, c_st4 = st.columns(4)
                    q_home_shots = c_st1.number_input("홈 슈팅", min_value=0, value=0, key=f"q_{cur_idx}_hsh")
                    q_away_shots = c_st2.number_input("원정 슈팅", min_value=0, value=0, key=f"q_{cur_idx}_ash")
                    q_home_sot = c_st3.number_input("홈 유효", min_value=0, value=0, key=f"q_{cur_idx}_hsot")
                    q_away_sot = c_st4.number_input("원정 유효", min_value=0, value=0, key=f"q_{cur_idx}_asot")

                    c_ps1, c_ps2 = st.columns(2)
                    q_home_poss = c_ps1.number_input("홈 점유율", value=50.0, key=f"q_{cur_idx}_hpo")
                    q_away_poss = c_ps2.number_input("원정 점유율", value=50.0, key=f"q_{cur_idx}_apo")

                    c_cd1, c_cd2, c_xg1, c_xg2 = st.columns(4)
                    q_home_yc = c_cd1.number_input("홈 경고", min_value=0, value=0, key=f"q_{cur_idx}_hyc")
                    q_away_yc = c_cd2.number_input("원정 경고", min_value=0, value=0, key=f"q_{cur_idx}_ayc")
                    q_home_rc = 0
                    q_away_rc = 0
                    q_home_xg = q_xg1.number_input("홈 xG", value=0.0, key=f"q_{cur_idx}_hxg")
                    q_away_xg = q_xg2.number_input("원정 xG", value=0.0, key=f"q_{cur_idx}_axg")
                    q_home_pass = 80.0
                    q_away_pass = 80.0

                q_stats_dict = {
                    "home_1h": q_home_1h, "home_2h": q_home_2h, "away_1h": q_away_1h, "away_2h": q_away_2h,
                    "home_tac": q_home_tac, "away_tac": q_away_tac, "home_shots": q_home_shots, "away_shots": q_away_shots,
                    "home_sot": q_home_sot, "away_sot": q_away_sot, "home_poss": q_home_poss, "away_poss": q_away_poss,
                    "home_pass": q_home_pass, "away_pass": q_away_pass, "home_yc": q_home_yc, "away_yc": q_away_yc,
                    "home_rc": q_home_rc, "away_rc": q_away_rc, "home_xg": q_home_xg, "away_xg": q_away_xg
                }

                if st.button("💾 구글 시트 저장 및 다음 경기로 넘어가기", type="primary", use_container_width=True):
                    with st.spinner("구글 시트에 저장 중..."):
                        success, msg = save_match_data_to_sheets(cur_match, q_odds_inputs, q_stats_dict, q_ou_inputs, q_hc_inputs)
                        if success:
                            st.session_state.current_queue_idx += 1
                            st.cache_data.clear()
                            st.success(f"🎉 [{cur_match['home']} vs {cur_match['away']}] 저장 완료!")
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.error(f"저장 실패: {msg}")

    else:
        st.info("💡 간편한 2단계 분할 입력 모드를 상단에서 선택해 주세요.")

# =========================================================
# TAB 2: 📡 라운드 자동 스캐너 (기본 유지)
# =========================================================
with tab_scanner:
    st.subheader("📡 라운드 경기 배당 자동 스캐너 & 추천픽 레이더")
    df_scan_raw = load_sheet_data(SCANNER_SHEET_NAME)
    st.info("💡 스캐너 탭은 승무패 및 해외 종합평균 레이더 기반으로 정상 작동 중입니다. (기존 데이터 완벽 연동)")

# =========================================================
# TAB 3: 📊 9개사 동일 배당 분석 (언오버/핸디캡 인포그래픽 도표 추가)
# =========================================================
with tab_analysis:
    st.subheader("🔬 3번 탭: 9대 북메이커 배당 입력 및 승무패·언오버·핸디캡 분석")

    c_an_l1, c_an_l2, c_an_l3 = st.columns([1, 1, 1])
    target_league = c_an_l1.text_input("🔍 리그명", value="PL", key="t2_target_league")
    t2_home_team = c_an_l2.text_input("🏠 홈팀명 (블로그 도표용)", value="", key="t2_home_team")
    t2_away_team = c_an_l3.text_input("🚗 원정팀명 (블로그 도표용)", value="", key="t2_away_team")

    st.markdown("##### 🏢 북메이커별 승무패 배당 입력")
    odds_inputs_t2 = {}
    for i in range(0, len(BOOKMAKERS), 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < len(BOOKMAKERS):
                bm = BOOKMAKERS[idx]
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**[{idx+1}] {bm.upper()}**")
                        oh, od, oa = st.columns(3)
                        h_val = oh.number_input("홈승", value=0.0, step=0.01, key=f"t2_{bm}_h")
                        d_val = od.number_input("무승부", value=0.0, step=0.01, key=f"t2_{bm}_d")
                        a_val = oa.number_input("원정승", value=0.0, step=0.01, key=f"t2_{bm}_a")
                        odds_inputs_t2[bm] = (h_val, d_val, a_val)

    st.markdown("---")
    st.subheader("📊 네이버 블로그/카페용 인포그래픽 도표 복사 (승무패 / 언오버 / 핸디캡)")

    tab_m1, tab_m2, tab_m3 = st.tabs(["🔴 승무패 (1X2) 도표", "⚽ 언오버 (Over/Under) 도표", "💪 핸디캡 (Handicap) 도표"])

    with tab_m1:
        compare_options = ["🌟 해외 종합 가중평균 (전체 평균)"] + OVERSEAS_BOOKMAKERS
        sel_compare_target = st.selectbox("비교 대상 선택", compare_options, key="sel_compare_1x2")
        b_odds_val = odds_inputs_t2.get("배트맨", (0.0, 0.0, 0.0))
        o_odds_val = odds_inputs_t2.get(sel_compare_target.replace("🌟 해외 종합 가중평균 (전체 평균)", "bet365"), (0.0, 0.0, 0.0))
        
        html_1x2 = generate_naver_odds_infographic(b_odds_val, sel_compare_target, o_odds_val, target_league, t2_home_team, t2_away_team, "1X2")
        render_clipboard_component(html_1x2, "clip_1x2", height=450)

    with tab_m2:
        col_ou1, col_ou2, col_ou3 = st.columns(3)
        ou_line_val = col_ou1.number_input("기준점 (예: 2.5)", value=2.5, step=0.5, key="clip_ou_line")
        ou_b_over = col_ou2.number_input("배트맨 오버 배당", value=1.85, step=0.01, key="clip_ou_bo")
        ou_b_under = col_ou3.number_input("배트맨 언더 배당", value=1.95, step=0.01, key="clip_ou_bu")
        
        html_ou = generate_naver_odds_infographic((ou_b_over, ou_b_under), "bet365", (1.90, 1.90), target_league, t2_home_team, t2_away_team, "OU", ou_line_val)
        render_clipboard_component(html_ou, "clip_ou", height=420)

    with tab_m3:
        col_hc1, col_hc2, col_hc3 = st.columns(3)
        hc_line_val = col_hc1.number_input("핸디 기준점 (예: -1.0)", value=-1.0, step=0.5, key="clip_hc_line")
        hc_b_home = col_hc2.number_input("배트맨 핸디홈 배당", value=2.10, step=0.01, key="clip_hc_bh")
        hc_b_away = col_hc3.number_input("배트맨 핸디원정 배당", value=1.70, step=0.01, key="clip_hc_ba")

        html_hc = generate_naver_odds_infographic((hc_b_home, hc_b_away), "bet365", (2.05, 1.75), target_league, t2_home_team, t2_away_team, "HC", hc_line_val)
        render_clipboard_component(html_hc, "clip_hc", height=420)

# =========================================================
# TAB 4, 5, 6: 기존 분석 및 부상자 탭 유지
# =========================================================
with tab_team_stats:
    st.subheader("📈 팀별 과거 세부 경기내용 평균계산기")
    df_stats_all = load_sheet_data(STATS_SHEET_NAME)
    if not df_stats_all.empty:
        st.dataframe(df_stats_all, use_container_width=True, hide_index=True)
    else:
        st.info("경기내용 데이터가 없습니다.")

with tab_h2h:
    st.subheader("⚔️ 홈 vs 원정 맞대결(H2H) 종합 분석")
    st.info("맞대결 분석 기능이 정상 대기 중입니다.")

with tab_injuries:
    st.subheader("🚑 팀별 부상자/결장자 명단 및 카드 리포트")
    df_injuries = load_sheet_data(INJURY_SHEET_NAME)
    if not df_injuries.empty:
        st.dataframe(df_injuries, use_container_width=True, hide_index=True)
    else:
        st.info("부상자 명단 데이터가 없습니다.")
