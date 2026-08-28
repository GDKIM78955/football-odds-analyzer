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
# 배당 인포그래픽 도표
# =========================================================
def generate_naver_odds_infographic(b_odds, overseas_name, o_odds, league_name="", home_team="", away_team=""):
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
    
    match_title = ""
    if home_team or away_team:
        match_title = f"<div style='font-size: 19px; font-weight: bold; color: #0f172a; margin-top: 4px;'><span style='color: #dc2626;'>{home_team}</span> <span style='font-size: 14px; color: #64748b;'>VS</span> <span style='color: #2563eb;'>{away_team}</span></div>"
    else:
        match_title = f"<div style='font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 4px;'>{lg_badge}배당 및 승률 정밀 분석 리포트</div>"

    h_col_name = f"홈 ({home_team})" if home_team else "홈 승 (Home)"
    a_col_name = f"원정 ({away_team})" if away_team else "원정승 (Away)"

    html = f"""
    <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', AppleSDGothicNeo-Regular, sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; border-collapse: separate; color: #0f172a;">
        <tr>
            <td style="padding: 20px;">
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 16px;">
                    <tr>
                        <td align="center" style="padding-bottom: 10px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 1px;">ODDS & PROBABILITY REPORT</div>
                            {match_title}
                            <div style="font-size: 12px; color: #475569; margin-top: 4px;">{lg_badge}기준: <b>배트맨</b> vs <b>{overseas_name.upper()}</b></div>
                        </td>
                    </tr>
                </table>

                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 6px;">📊 경기 승/무/패 예측 확률 분포</div>
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
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; background-color: #f8fafc; font-weight: bold;">적정 배당</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; color: #475569;">{fair_h}</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; color: #475569;">{fair_d}</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; color: #475569;">{fair_a}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; background-color: #f8fafc; font-weight: bold;">배당 편차</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: {'#dc2626' if diff_h < 0 else '#2563eb'};">{diff_h_str}</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: {'#dc2626' if diff_d < 0 else '#2563eb'};">{diff_d_str}</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: {'#dc2626' if diff_a < 0 else '#2563eb'};">{diff_a_str}</td>
                    </tr>
                </table>

                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f1f5f9; border-radius: 6px; font-size: 12px; color: #334155;">
                    <tr>
                        <td align="center" style="padding: 8px 10px; text-align: center;">💰 환급률: <b>배트맨 {round(b_payout, 2)}%</b> / <b>{overseas_name} {round(o_payout, 2)}%</b> &nbsp;|&nbsp; ⚡ 오차 허용: <b>±0.03</b></td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    """
    return html

# =========================================================
# 단일 팀 시즌 평균 리포트
# =========================================================
def generate_naver_team_stats_infographic(team_name, season, league, match_count_info, df_summary, tac_df, df_goals):
    html = f"""
    <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', AppleSDGothicNeo-Regular, sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; border-collapse: separate; color: #0f172a;">
        <tr>
            <td style="padding: 20px;">
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 16px;">
                    <tr>
                        <td align="center" style="padding-bottom: 10px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold; color: #2563eb; letter-spacing: 1px;">TEAM PERFORMANCE STATS</div>
                            <div style="font-size: 19px; font-weight: bold; color: #0f172a; margin-top: 4px;">
                                📋 [{team_name}] 시즌 지표 종합 리포트
                            </div>
                            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">
                                시즌: <b>{season}</b> | 리그: <b>{league}</b> ({match_count_info})
                            </div>
                        </td>
                    </tr>
                </table>

                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 6px;">📊 주요 세부 경기 지표 평균</div>
    """
    if df_summary is not None and not df_summary.empty:
        table_html = df_summary.to_html(index=False, escape=False)
        table_html = table_html.replace('<table border="1" class="dataframe">', '<table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 16px;">')
        table_html = table_html.replace('<th>', '<th align="center" style="background-color: #f8fafc; color: #334155; padding: 7px 3px; border: 1px solid #cbd5e1; font-weight: bold; text-align: center !important;">')
        table_html = table_html.replace('<td>', '<td align="center" style="background-color: #ffffff; color: #1e293b; padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center !important;">')
        html += table_html

    if tac_df is not None and not tac_df.empty:
        html += f"""
                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 10px; margin-bottom: 6px;">♟️ 팀 전술(포메이션) 사용 비율</div>
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 16px;">
                    <tr style="background-color: #f8fafc;">
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #334155; text-align: center;">포메이션</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #334155; text-align: center;">전체 사용(비율)</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #dc2626; text-align: center;">홈 경기</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #2563eb; text-align: center;">원정 경기</th>
                    </tr>
        """
        for _, r in tac_df.iterrows():
            html += f"""
                    <tr>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; font-weight: bold; text-align: center;">{r.get('전술 (포메이션)', '-')}</td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; color: #0284c7; font-weight: bold; text-align: center;">{r.get('전체 사용 횟수', '-')}</td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">{r.get('홈경기 사용', '-')}</td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">{r.get('원정경기 사용', '-')}</td>
                    </tr>
            """
        html += "</table>"

    if df_goals is not None and not df_goals.empty:
        try:
            sub1 = df_goals[["구분", "전반 총득점", "후반 총득점", "총점"]].copy()
            sub2 = df_goals[["구분", "전반 평균", "후반 평균", "합계 평균"]].copy()

            t1_html = sub1.to_html(index=False, escape=False).replace('<table border="1" class="dataframe">', '<table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 10px;">')
            t1_html = t1_html.replace('<th>', '<th align="center" style="background-color: #f8fafc; color: #334155; padding: 7px 3px; border: 1px solid #cbd5e1; font-weight: bold; text-align: center !important;">')
            t1_html = t1_html.replace('<td>', '<td align="center" style="background-color: #ffffff; color: #1e293b; padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center !important;">')

            t2_html = sub2.to_html(index=False, escape=False).replace('<table border="1" class="dataframe">', '<table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 6px;">')
            t2_html = t2_html.replace('<th>', '<th align="center" style="background-color: #f8fafc; color: #334155; padding: 7px 3px; border: 1px solid #cbd5e1; font-weight: bold; text-align: center !important;">')
            t2_html = t2_html.replace('<td>', '<td align="center" style="background-color: #ffffff; color: #1e293b; padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center !important;">')

            html += f"""
                    <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 10px; margin-bottom: 6px;">⚽ 전/후반 득점 총합 통계</div>
                    {t1_html}
                    <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 10px; margin-bottom: 6px;">📈 경기당 평균 득점 통계</div>
                    {t2_html}
            """
        except Exception:
            pass

    html += """
            </td>
        </tr>
    </table>
    """
    return html

# =========================================================
# 맞대결 인포그래픽 도표
# =========================================================
def generate_naver_match_infographic(home_team, away_team, stats_data, goal_df=None, h2h_all_str="", h2h_exact_str=""):
    html = f"""
    <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', AppleSDGothicNeo-Regular, sans-serif; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; border-collapse: separate; color: #1e293b;">
        <tr>
            <td style="padding: 20px;">
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 14px;">
                    <tr>
                        <td align="center" style="padding-bottom: 10px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold; color: #2563eb; letter-spacing: 1px;">HEAD TO HEAD STATS</div>
                            <div style="font-size: 19px; font-weight: bold; color: #0f172a; margin-top: 4px;">
                                <span style="color: #dc2626;">{home_team}</span> <span style="font-size: 14px; color: #64748b;">VS</span> <span style="color: #2563eb;">{away_team}</span>
                            </div>
                            <div style="font-size: 12px; color: #475569; margin-top: 6px; line-height: 1.6;">
                                🏆 <b>역대 전체 전적</b>: {h2h_all_str}<br>
                                🏠 <b>홈/원정 동일 매치업</b>: {h2h_exact_str}
                            </div>
                        </td>
                    </tr>
                </table>

                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 8px;">⚔️ 양 팀 맞대결 세부 지표 비교 (우세팀 하이라이트)</div>
                
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                    <tr style="background-color: #f8fafc;">
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #dc2626; width: 35%;">🔴 {home_team}</th>
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #475569; width: 30%;">비교 항목</th>
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #2563eb; width: 35%;">🔵 {away_team}</th>
                    </tr>
    """
    for label, (val_h, val_a) in stats_data.items():
        if val_h > val_a:
            h_style = "background-color: #fee2e2; font-weight: bold; color: #dc2626;"
            a_style = "color: #64748b;"
            h_disp = f"🔥 {val_h}"
            a_disp = f"{val_a}"
        elif val_a > val_h:
            h_style = "color: #64748b;"
            a_style = "background-color: #dbeafe; font-weight: bold; color: #2563eb;"
            h_disp = f"{val_h}"
            a_disp = f"🔥 {val_a}"
        else:
            h_style = "color: #334155;"
            a_style = "color: #334155;"
            h_disp = f"{val_h}"
            a_disp = f"{val_a}"

        html += f"""
                    <tr>
                        <td style="padding: 7px; border: 1px solid #e2e8f0; {h_style}">{h_disp}</td>
                        <td style="padding: 7px; border: 1px solid #e2e8f0; background-color: #f8fafc; font-weight: bold; color: #334155;">{label}</td>
                        <td style="padding: 7px; border: 1px solid #e2e8f0; {a_style}">{a_disp}</td>
                    </tr>
        """
    html += "</table>"

    if goal_df is not None and not goal_df.empty:
        try:
            sub1_cols = [c for c in ["구분", "전반 총득점", "후반 총득점", "총점", "후반 득점비율"] if c in goal_df.columns]
            sub2_cols = [c for c in ["구분", "전반 평균", "후반 평균", "경기당 평균득점"] if c in goal_df.columns]

            sub1 = goal_df[sub1_cols].copy()
            sub2 = goal_df[sub2_cols].copy()

            t1_html = sub1.to_html(index=False, escape=False).replace('<table border="1" class="dataframe">', '<table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 10px;">')
            t1_html = t1_html.replace('<th>', '<th align="center" style="background-color: #f8fafc; color: #334155; padding: 7px 3px; border: 1px solid #cbd5e1; font-weight: bold; text-align: center !important;">')
            t1_html = t1_html.replace('<td>', '<td align="center" style="background-color: #ffffff; color: #1e293b; padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center !important;">')

            t2_html = sub2.to_html(index=False, escape=False).replace('<table border="1" class="dataframe">', '<table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 6px;">')
            t2_html = t2_html.replace('<th>', '<th align="center" style="background-color: #f8fafc; color: #334155; padding: 7px 3px; border: 1px solid #cbd5e1; font-weight: bold; text-align: center !important;">')
            t2_html = t2_html.replace('<td>', '<td align="center" style="background-color: #ffffff; color: #1e293b; padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center !important;">')

            html += f"""
                    <div style="font-size: 13px; font-weight: bold; color: #0f172a; margin-top: 14px; margin-bottom: 6px;">⚽ 맞대결 득점 총합 및 후반 집중도</div>
                    {t1_html}
                    <div style="font-size: 13px; font-weight: bold; color: #0f172a; margin-top: 10px; margin-bottom: 6px;">📈 맞대결 경기당 평균득점 통계</div>
                    {t2_html}
            """
        except Exception:
            pass

    html += """
            </td>
        </tr>
    </table>
    """
    return html

# =========================================================
# 부상자 인포그래픽 도표
# =========================================================
def generate_naver_injury_infographic(team_name, league_title, confirmed_list, doubt_list):
    html = f"""
    <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', AppleSDGothicNeo-Regular, sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; border-collapse: separate; color: #0f172a;">
        <tr>
            <td style="padding: 20px;">
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 16px;">
                    <tr>
                        <td align="center" style="padding-bottom: 10px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold; color: #dc2626; letter-spacing: 1px;">INJURY & SUSPENSION REPORT</div>
                            <div style="font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 4px;">
                                🚑 [{team_name}] 결장 및 결장의심 명단
                            </div>
                            <div style="font-size: 12px; color: #64748b; margin-top: 4px;">기준: <b>{league_title}</b></div>
                        </td>
                    </tr>
                </table>
    """

    if confirmed_list:
        html += """
                <div style="font-size: 13px; font-weight: bold; color: #dc2626; margin-bottom: 6px;">🔴 결장 확정 명단</div>
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 16px;">
                    <tr style="background-color: #fee2e2;">
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #991b1b; text-align: center;">선수명</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #991b1b; text-align: center;">포지션/역할</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #991b1b; text-align: center;">시즌 기록</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #991b1b; text-align: center;">사유/비고</th>
                    </tr>
        """
        for p in confirmed_list:
            kr = p.get("선수한글명", "")
            en = p.get("선수영문명", "")
            name_str = f"<b>{kr}</b><br><span style='font-size: 10px; color: #64748b;'>{en}</span>" if kr and en else f"<b>{kr or en}</b>"
            pos = p.get("포지션", "MF")
            role = p.get("역할", "-")
            start = p.get("선발", 0)
            sub = p.get("교체", 0)
            goals = p.get("골", 0)
            assists = p.get("도움", 0)
            reason = p.get("결장사유", p.get("사유", "부상"))
            note = p.get("특이사항", "-")
            note_str = f"<br><span style='font-size: 10px; color: #64748b;'>({note})</span>" if note != "-" else ""

            role_badge = f"<span style='background-color: #ef4444; color: white; padding: 1px 5px; border-radius: 3px; font-size: 10px;'>{role}</span>" if "주전" in str(role) else f"<span style='background-color: #64748b; color: white; padding: 1px 5px; border-radius: 3px; font-size: 10px;'>{role}</span>"

            html += f"""
                    <tr>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">{name_str}</td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">`{pos}`<br>{role_badge}</td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">{start}선발 {sub}교체<br><b>{goals}골 {assists}도움</b></td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; color: #dc2626; text-align: center;"><b>{reason}</b>{note_str}</td>
                    </tr>
            """
        html += "</table>"

    if doubt_list:
        html += """
                <div style="font-size: 13px; font-weight: bold; color: #d97706; margin-bottom: 6px;">🟡 결장 의심 명단 (GTD)</div>
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 10px;">
                    <tr style="background-color: #fef3c7;">
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #92400e; text-align: center;">선수명</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #92400e; text-align: center;">포지션/역할</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #92400e; text-align: center;">시즌 기록</th>
                        <th align="center" style="padding: 7px 3px; border: 1px solid #cbd5e1; color: #92400e; text-align: center;">사유/비고</th>
                    </tr>
        """
        for p in doubt_list:
            kr = p.get("선수한글명", "")
            en = p.get("선수영문명", "")
            name_str = f"<b>{kr}</b><br><span style='font-size: 10px; color: #64748b;'>{en}</span>" if kr and en else f"<b>{kr or en}</b>"
            pos = p.get("포지션", "MF")
            role = p.get("역할", "-")
            start = p.get("선발", 0)
            sub = p.get("교체", 0)
            goals = p.get("골", 0)
            assists = p.get("도움", 0)
            reason = p.get("결장사유", p.get("사유", "결장의심"))
            note = p.get("특이사항", "-")
            note_str = f"<br><span style='font-size: 10px; color: #64748b;'>({note})</span>" if note != "-" else ""

            role_badge = f"<span style='background-color: #f59e0b; color: white; padding: 1px 5px; border-radius: 3px; font-size: 10px;'>{role}</span>"

            html += f"""
                    <tr>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">{name_str}</td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">`{pos}`<br>{role_badge}</td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center;">{start}선발 {sub}교체<br><b>{goals}골 {assists}도움</b></td>
                        <td align="center" style="padding: 6px 3px; border: 1px solid #e2e8f0; color: #d97706; text-align: center;"><b>{reason}</b>{note_str}</td>
                    </tr>
            """
        html += "</table>"

    html += """
            </td>
        </tr>
    </table>
    """
    return html

# =========================================================
# 2. 구글 시트 연동 클라이언트
# =========================================================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
        return None
    except Exception:
        return None

@st.cache_data(ttl=30, show_spinner=False)
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
        except Exception as e:
            time.sleep(1.0 * (attempt + 1))
            continue
    return pd.DataFrame()

# 구글 시트 일괄 저장 처리 함수
def save_match_data_to_sheets(match_info, odds_dict, stats_dict):
    client = get_gspread_client()
    if not client:
        return False, "구글 시트 연동 실패: Secrets 설정을 확인하세요."
    
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        season = match_info["season"]
        league = match_info["league"]
        match_date = match_info["date"]
        home_team = match_info["home"]
        away_team = match_info["away"]
        
        b_h, b_d, b_a = odds_dict.get("배트맨", (0.0, 0.0, 0.0))
        if b_h > 0 and b_d > 0 and b_a > 0:
            b_inv = (1/b_h) + (1/b_d) + (1/b_a)
            b_payout = 1 / b_inv
            b_prob_h = (1/b_h) / b_inv
            b_prob_d = (1/b_d) / b_inv
            b_prob_a = (1/b_a) / b_inv
        else:
            b_payout, b_prob_h, b_prob_d, b_prob_a = 0.0, 0.0, 0.0, 0.0

        home_score = stats_dict["home_1h"] + stats_dict["home_2h"]
        away_score = stats_dict["away_1h"] + stats_dict["away_2h"]

        if home_score > away_score:
            match_res = "홈승"
        elif home_score == away_score:
            match_res = "무승부"
        else:
            match_res = "원정승"

        score_total = home_score + away_score
        score_diff = home_score - away_score
        score_diff_abs = abs(score_diff)
        
        saved_count = 0
        
        for bm_name in BOOKMAKERS:
            if bm_name not in odds_dict:
                continue
            h, d, a = odds_dict[bm_name]
            if h <= 0 or d <= 0 or a <= 0:
                continue
            
            bm_inv = (1/h) + (1/d) + (1/a)
            bm_payout = 1 / bm_inv
            bm_prob_h = (1/h) / bm_inv
            bm_prob_d = (1/d) / bm_inv
            bm_prob_a = (1/a) / bm_inv
            
            diff_h = round(b_h - h, 2) if b_h > 0 else 0.0
            diff_d = round(b_d - d, 2) if b_d > 0 else 0.0
            diff_a = round(b_a - a, 2) if b_a > 0 else 0.0
            
            fair_h = round(b_payout / bm_prob_h, 6) if (b_payout > 0 and bm_prob_h > 0) else 0.0
            fair_d = round(b_payout / bm_prob_d, 6) if (b_payout > 0 and bm_prob_d > 0) else 0.0
            fair_a = round(b_payout / bm_prob_a, 6) if (b_payout > 0 and bm_prob_a > 0) else 0.0
            
            loss_h = round(((b_h - fair_h) / fair_h) * 100, 5) if fair_h > 0 else 0.0
            loss_d = round(((b_d - fair_d) / fair_d) * 100, 5) if fair_d > 0 else 0.0
            loss_a = round(((b_a - fair_a) / fair_a) * 100, 5) if fair_a > 0 else 0.0
            
            min_odd, max_odd = min(h, d, a), max(h, d, a)
            win_odd = h if match_res == "홈승" else (d if match_res == "무승부" else a)
            odd_type = "정배" if win_odd == min_odd else ("역배" if win_odd == max_odd else "중배")

            row_data_odds = [
                season, league, match_date, home_team, away_team,
                b_h, b_d, b_a,
                f"{round(b_payout * 100, 2)}%",
                f"{round(b_prob_h * 100, 2)}%", f"{round(b_prob_d * 100, 2)}%", f"{round(b_prob_a * 100, 2)}%",
                h, d, a,
                f"{round(bm_payout * 100, 2)}%",
                f"{round(bm_prob_h * 100, 2)}%", f"{round(bm_prob_d * 100, 2)}%", f"{round(bm_prob_a * 100, 2)}%",
                diff_h, diff_d, diff_a,
                loss_h, loss_d, loss_a,
                fair_h, fair_d, fair_a,
                home_score, away_score, score_total, score_diff, score_diff_abs,
                odd_type, match_res, win_odd
            ]
            
            try:
                ws = spreadsheet.worksheet(bm_name)
                ws.append_row(row_data_odds, value_input_option="USER_ENTERED")
                saved_count += 1
                time.sleep(0.12)
            except gspread.exceptions.WorksheetNotFound:
                pass

        h_1h = stats_dict["home_1h"]
        h_2h = stats_dict["home_2h"]
        a_1h = stats_dict["away_1h"]
        a_2h = stats_dict["away_2h"]
        h_shots = stats_dict["home_shots"]
        a_shots = stats_dict["away_shots"]
        h_sot = stats_dict["home_sot"]
        a_sot = stats_dict["away_sot"]

        h_1h_ratio = round((h_1h / home_score) * 100, 2) if home_score > 0 else 0.0
        h_2h_ratio = round((h_2h / home_score) * 100, 2) if home_score > 0 else 0.0
        a_1h_ratio = round((a_1h / away_score) * 100, 2) if away_score > 0 else 0.0
        a_2h_ratio = round((a_2h / away_score) * 100, 2) if away_score > 0 else 0.0
        
        h_sot_ratio = round((h_sot / h_shots) * 100, 2) if h_shots > 0 else 0.0
        a_sot_ratio = round((a_sot / a_shots) * 100, 2) if a_shots > 0 else 0.0

        home_tac_safe = f"'{stats_dict['home_tac'].strip()}" if stats_dict['home_tac'].strip() else ""
        away_tac_safe = f"'{stats_dict['away_tac'].strip()}" if stats_dict['away_tac'].strip() else ""

        row_data_stats = [
            season, league, match_date, home_team, away_team,
            h_1h, h_2h, a_1h, a_2h,
            f"{h_1h_ratio}%", f"{h_2h_ratio}%", f"{a_1h_ratio}%", f"{a_2h_ratio}%",
            home_tac_safe, away_tac_safe,
            h_shots, a_shots, h_sot, a_sot,
            f"{h_sot_ratio}%", f"{a_sot_ratio}%",
            f"{stats_dict['home_poss']}%", f"{stats_dict['away_poss']}%",
            f"{stats_dict['home_pass']}%", f"{stats_dict['away_pass']}%",
            stats_dict['home_yc'], stats_dict['away_yc'], stats_dict['home_rc'], stats_dict['away_rc'],
            stats_dict['home_xg'], stats_dict['away_xg']
        ]

        try:
            ws_stats = spreadsheet.worksheet(STATS_SHEET_NAME)
            ws_stats.append_row(row_data_stats, value_input_option="USER_ENTERED")
            time.sleep(0.12)
        except gspread.exceptions.WorksheetNotFound:
            pass
        
        return True, f"배당 {saved_count}개 탭 & '경기내용' 탭 저장 완료"
    except Exception as e:
        return False, str(e)

# 3. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.caption(f"연동 시트 ID: `{SPREADSHEET_ID}`")
    tol = st.number_input("배당 오차 허용치 (±)", value=0.03, step=0.01)
    if st.button("🔄 전체 시트 데이터 새로고침"):
        st.cache_data.clear()
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
# TAB 1: 📝 경기 데이터 입력 & 저장
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
                cols_chk = st.columns(4)
                for idx, obm in enumerate(OVERSEAS_BOOKMAKERS):
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
                cur_match = st.session_state.match_queue[cur_idx]
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
                    q_away_yc = c_cd2.number_input("원정 경고", min_value=0, value=0, key=f"q_{cur_idx}_away_yc")
                    q_home_rc = c_cd3.number_input("홈 퇴장", min_value=0, value=0, key=f"q_{cur_idx}_home_rc")
                    q_away_rc = c_cd4.number_input("원정 퇴장", min_value=0, value=0, key=f"q_{cur_idx}_away_rc")
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
                    "home_rc": q_home_rc, "away_rc": q_home_rc,
                    "home_xg": q_home_xg, "away_xg": q_away_xg
                }

                if st.button("💾 구글 시트 저장 및 다음 경기로 넘어가기 ➔", type="primary", use_container_width=True):
                    with st.spinner("구글 시트에 저장 중..."):
                        success, msg = save_match_data_to_sheets(cur_match, q_odds_inputs, q_stats_dict)
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
        for i in range(0, len(BOOKMAKERS), 3):
            cols = st.columns(3)
            for j in range(3):
                idx = i + j
                if idx < len(BOOKMAKERS):
                    bm = BOOKMAKERS[idx]
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
            away_sot = c_st4.number_input("원정 유효슈팅", min_value=0, value=0, key="in_away_sot")

            c_ps1, c_ps2, c_ps3, c_ps4 = st.columns(4)
            home_poss = c_ps1.number_input("홈 점유율 (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.1, key="in_home_poss")
            away_poss = c_ps2.number_input("원정 점유율 (%)", min_value=0.0, max_value=100.0, value=50.0, step=0.1, key="in_away_poss")
            home_pass = c_ps3.number_input("홈 패스성공률 (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1, key="in_home_pass")
            away_pass = c_ps4.number_input("원정 패스성공률 (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1, key="in_away_pass")

            c_cd1, c_cd2, c_cd3, c_cd4, c_xg1, c_xg2 = st.columns(6)
            home_yc = c_cd1.number_input("홈 경고(옐로)", min_value=0, value=0, key="in_home_yc")
            away_yc = c_cd2.number_input("원정 경고(옐로)", min_value=0, value=0, key="in_home_yc")
            home_rc = c_cd3.number_input("홈 퇴장(레드)", min_value=0, value=0, key="in_home_rc")
            away_rc = c_cd4.number_input("원정 퇴장(레드)", min_value=0, value=0, key="in_home_rc")
            home_xg = c_xg1.number_input("홈 xG", min_value=0.0, value=0.00, step=0.01, key="in_home_xg")
            away_xg = c_xg2.number_input("원정 xG", min_value=0.0, value=0.00, step=0.01, key="in_home_xg")

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
                success, msg = save_match_data_to_sheets(match_info_single, odds_inputs_t1, stats_dict_single)
                if success:
                    st.cache_data.clear()
                    st.success(f"🎉 성공: {msg}")
                else:
                    st.error(f"저장 중 오류 발생: {msg}")

# =========================================================
# TAB 2: 📡 라운드 경기 자동 스캐너 & 추천픽
# =========================================================
with tab_scanner:
    st.subheader("📡 라운드 경기 배당 자동 스캐너 & 추천픽 레이더")
    st.caption("와이즈토토로 배트맨 경기를 연속으로 담아두고 해외 배당을 차례대로 채워 '라운드스캔' 시트에 저장 및 분석합니다.")

    df_scan_raw = load_sheet_data(SCANNER_SHEET_NAME)

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
                cur_s_match = st.session_state.scan_queue[s_cur_idx]
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
                for i in range(0, len(OVERSEAS_BOOKMAKERS), 4):
                    cols_sq_bm = st.columns(4)
                    for j in range(4):
                        idx = i + j
                        if idx < len(OVERSEAS_BOOKMAKERS):
                            obm = OVERSEAS_BOOKMAKERS[idx]
                            with cols_sq_bm[j]:
                                with st.container(border=True):
                                    st.caption(f"**{obm.upper()}**")
                                    dh, dd, da = st.columns(3)
                                    h_v = dh.number_input("홈", value=0.0, step=0.01, min_value=0.0, key=f"sq_{s_cur_idx}_{obm}_h")
                                    d_v = dd.number_input("무", value=0.0, step=0.01, min_value=0.0, key=f"sq_{s_cur_idx}_{obm}_d")
                                    a_v = da.number_input("원정", value=0.0, step=0.01, min_value=0.0, key=f"sq_{s_cur_idx}_{obm}_a")
                                    sq_overseas_inputs[obm] = (h_v, d_v, a_v)

                if st.button("💾 '라운드스캔' 시트 저장 및 다음 경기 ➔", type="primary", use_container_width=True, key="btn_save_next_scan"):
                    client = get_gspread_client()
                    if client:
                        try:
                            spreadsheet = client.open_by_key(SPREADSHEET_ID)
                            ws_scan = spreadsheet.worksheet(SCANNER_SHEET_NAME)
                            
                            new_scan_row = [
                                cur_s_match["season"], cur_s_match["league"], cur_s_match["date"],
                                cur_s_match["home"], cur_s_match["away"],
                                cur_s_match["batman_odds"][0], cur_s_match["batman_odds"][1], cur_s_match["batman_odds"][2]
                            ]
                            for obm in OVERSEAS_BOOKMAKERS:
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
                            st.success(f"🎉 [{cur_s_match['home']} vs {cur_match['away']}] 저장 완료!")
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
                for obm in OVERSEAS_BOOKMAKERS:
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
                            for obm in OVERSEAS_BOOKMAKERS:
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
            for i in range(0, len(OVERSEAS_BOOKMAKERS), 4):
                cols_ds_bm = st.columns(4)
                for j in range(4):
                    idx = i + j
                    if idx < len(OVERSEAS_BOOKMAKERS):
                        obm = OVERSEAS_BOOKMAKERS[idx]
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
                        client = get_gspread_client()
                        if client:
                            try:
                                spreadsheet = client.open_by_key(SPREADSHEET_ID)
                                ws_scan = spreadsheet.worksheet(SCANNER_SHEET_NAME)
                                
                                new_scan_row = [
                                    ds_season, ds_league, ds_date, ds_home.strip(), ds_away.strip(),
                                    ds_bh, ds_bd, ds_ba
                                ]
                                for obm in OVERSEAS_BOOKMAKERS:
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
                                    time.sleep(0.3)
                                    st.cache_data.clear()
                                    st.success(f"🔄 [{ds_home} vs {ds_away}] 기존 경기의 배당이 최신 데이터로 성공적으로 덮어쓰기(수정)되었습니다!")
                                else:
                                    ws_scan.append_row(new_scan_row, value_input_option="USER_ENTERED")
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
                    client = get_gspread_client()
                    if client:
                        try:
                            spreadsheet = client.open_by_key(SPREADSHEET_ID)
                            ws_scan = spreadsheet.worksheet(SCANNER_SHEET_NAME)
                            all_rows = ws_scan.get_all_values()
                            if len(all_rows) > 1:
                                ws_scan.delete_rows(len(all_rows))
                                time.sleep(0.3)
                                st.cache_data.clear()
                                st.success("🗑️ 최근 등록된 마지막 1경기가 삭제되었습니다.")
                                st.rerun()
                            else:
                                st.info("삭제할 데이터가 없습니다.")
                        except Exception as e:
                            st.error(f"삭제 실패: {e}")

    st.markdown("---")

    df_h2h_all_db = load_sheet_data(STATS_SHEET_NAME)

    if df_scan_raw.empty:
        st.warning(f"⚠️ `{SCANNER_SHEET_NAME}` 시트에 스캔할 경기 데이터가 없습니다. 위의 [2단계 분할 입력] 또는 [1경기 직접 등록]을 통해 경기를 등록해 주세요.")
    else:
        # =========================================================
        # 🌟 사전 동일배당 매칭 집계 엔진 (총 10개 기준, 1.01 미만 원천 차단)
        # =========================================================
        ALL_CRITERIA_OPTIONS = ["배트맨"] + OVERSEAS_BOOKMAKERS + ["🌟 해외 8개사 종합평균"]
        
        # 9개 업체 DB 캐싱
        cached_dbs = {}
        for bm in BOOKMAKERS:
            cached_dbs[bm] = load_sheet_data(bm)

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

        # 전체 등록 경기에 대한 북메이커별 총 매칭 건수 계산
        matching_counts_summary = {crit: 0 for crit in ALL_CRITERIA_OPTIONS}
        
        for _, r in df_scan_raw.iterrows():
            # 1) 배트맨
            bh = safe_flt(r.get("배트맨_홈"), 0.0)
            bd = safe_flt(r.get("배트맨_무"), 0.0)
            ba = safe_flt(r.get("배트맨_원"), 0.0)
            if bh >= 1.01 and bd >= 1.01 and ba >= 1.01:
                c_bm, _, _, _ = count_matched_in_db(cached_dbs.get("배트맨", pd.DataFrame()), bh, bd, ba)
                matching_counts_summary["배트맨"] += c_bm

            # 2) 해외 8개사 개별
            valid_oh, valid_od, valid_oa = [], [], []
            for obm in OVERSEAS_BOOKMAKERS:
                oh = safe_flt(r.get(f"{obm}_홈"), 0.0)
                od = safe_flt(r.get(f"{obm}_무"), 0.0)
                oa = safe_flt(r.get(f"{obm}_원"), 0.0)
                if oh >= 1.01 and od >= 1.01 and oa >= 1.01:
                    valid_oh.append(oh)
                    valid_od.append(od)
                    valid_oa.append(oa)
                    c_obm, _, _, _ = count_matched_in_db(cached_dbs.get(obm, pd.DataFrame()), oh, od, oa)
                    matching_counts_summary[obm] += c_obm

            # 3) 해외 8개사 종합평균 기준
            if valid_oh:
                avg_oh = round(float(np.mean(valid_oh)), 2)
                avg_od = round(float(np.mean(valid_od)), 2)
                avg_oa = round(float(np.mean(valid_oa)), 2)
                if avg_oh >= 1.01 and avg_od >= 1.01 and avg_oa >= 1.01:
                    tot_avg_c = 0
                    for obm in OVERSEAS_BOOKMAKERS:
                        c_a, _, _, _ = count_matched_in_db(cached_dbs.get(obm, pd.DataFrame()), avg_oh, avg_od, avg_oa)
                        tot_avg_c += c_a
                    matching_counts_summary["🌟 해외 8개사 종합평균"] += tot_avg_c

        # =========================================================
        # 🌟 상단: 업체별 매칭 개수 사전 브리핑 카드
        # =========================================================
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
        
        badge_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;'>" + "".join(badges) + "</div>"
        st.markdown(badge_html, unsafe_allow_html=True)

        # 🌟 기준 북메이커 선택 셀렉트박스
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

        # =========================================================
        # 스캔 분석 엔진 실행 (선택된 기준 기반)
        # =========================================================
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
                
                for obm in OVERSEAS_BOOKMAKERS:
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

                # 선택된 기준에 따른 배당 및 매칭 확률 계산
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
                elif criteria_name in OVERSEAS_BOOKMAKERS:
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
                        for obm in OVERSEAS_BOOKMAKERS:
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

                # 상대전적 (10번 시트)
                h2h_cnt, h2h_hw, h2h_dr, h2h_aw = 0, 0, 0, 0
                if not df_h2h_all_db.empty and "홈팀" in df_h2h_all_db.columns:
                    cond_h2h = ((df_h2h_all_db["홈팀"] == home) & (df_h2h_all_db["원정팀"] == away)) | \
                               ((df_h2h_all_db["홈팀"] == away) & (df_h2h_all_db["원정팀"] == home))
                    m_h2h = df_h2h_all_db[cond_h2h]
                    h2h_cnt = len(m_h2h)
                    for _, hr in m_h2h.iterrows():
                        hg = safe_flt(hr.get("전반득점_홈"), 0.0) + safe_flt(hr.get("후반득점_홈"), 0.0)
                        ag = safe_flt(hr.get("전반득점_원"), 0.0) + safe_flt(hr.get("후반득점_원"), 0.0)
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

                # 레이더 판별
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

        # =========================================================
        # 4대 추천 레이더 TOP 5 필터 버튼 영역
        # =========================================================
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

        # 1) TOP 5 레이더 선택 시: 상위 5경기 카드 렌더링
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
                                
                                for bm in BOOKMAKERS:
                                    h_val, d_val, a_val = item["all_odds"].get(bm, (0.0, 0.0, 0.0))
                                    st.session_state[f"t2_{bm}_h"] = float(h_val)
                                    st.session_state[f"t2_{bm}_d"] = float(d_val)
                                    st.session_state[f"t2_{bm}_a"] = float(a_val)
                                
                                st.session_state.sel_h2h_home = item["home"]
                                st.session_state.sel_h2h_away = item["away"]
                                st.session_state.inj_filter_team = item["home"]
                                
                                st.rerun()

        # 2) 전체 경기 보기 모드: 50~100경기 대응 스마트 필터 & 컴팩트 분석기
        else:
            st.subheader(f"📋 이번 라운드 전체 등록 경기 빠른 검색 & 원클릭 상세 분석 (총 {len(scanned_results)}경기)")

            # [상단 필터 바: 3열]
            f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 1])
            
            all_leagues = ["전체"] + sorted(list(set([m["league"] for m in scanned_results if m.get("league")])))
            with f_col1:
                selected_league = st.selectbox("🏆 리그 필터", all_leagues, key="filter_scan_league")
            with f_col2:
                search_team = st.text_input("🔍 팀명 검색 (홈/원정)", "", placeholder="예: 아스널, 맨시티", key="filter_scan_team")
            with f_col3:
                sort_option = st.selectbox("🔢 정렬 기준", ["등록순 (기본)", "배트맨 홈배당 낮은순", "배트맨 홈배당 높은순"], key="filter_scan_sort")

            # 필터링 로직
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
                # 1단계: 컴팩트 요약 테이블 렌더링
                summary_rows = []
                for m in filtered_matches:
                    bh, bd, ba = m["batman_odds"]
                    summary_rows.append({
                        "날짜": m["date"],
                        "리그": m["league"],
                        "홈팀": m["home"],
                        "원정팀": m["away"],
                        "배트맨(홈)": bh,
                        "배트맨(무)": bd,
                        "배트맨(원)": ba,
                        "주요 레이더": ", ".join(m["tags"])
                    })
                
                st.dataframe(
                    pd.DataFrame(summary_rows),
                    use_container_width=True,
                    height=min(240, 36 * (len(summary_rows) + 1)),
                    hide_index=True
                )

                st.markdown("#### 👉 상세 분석할 경기 선택")

                # 2단계: 드롭다운으로 경기 1개 선택
                match_options = []
                for idx, m in enumerate(filtered_matches):
                    bh, bd, ba = m["batman_odds"]
                    label = f"[{m['league']}] {m['date']} {m['home']} vs {m['away']} (배트맨 {bh} / {bd} / {ba})"
                    match_options.append((label, idx))

                selected_label = st.selectbox(
                    "분석할 경기를 목록에서 선택하세요",
                    options=[opt[0] for opt in match_options],
                    key="scanner_match_selector"
                )

                selected_match_idx = next(opt[1] for opt in match_options if opt[0] == selected_label)
                target_item = filtered_matches[selected_match_idx]

                # 3단계: 선택된 경기 카드 & 3/5/6번 탭 즉시 전송 버튼
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
                        
                        for bm in BOOKMAKERS:
                            h_val, d_val, a_val = target_item["all_odds"].get(bm, (0.0, 0.0, 0.0))
                            st.session_state[f"t2_{bm}_h"] = float(h_val)
                            st.session_state[f"t2_{bm}_d"] = float(d_val)
                            st.session_state[f"t2_{bm}_a"] = float(a_val)
                        
                        st.session_state.sel_h2h_home = target_item["home"]
                        st.session_state.sel_h2h_away = target_item["away"]
                        st.session_state.inj_filter_team = target_item["home"]

                        st.success(f"🎯 [{target_item['home']} vs {target_item['away']}] 경기가 분석 탭으로 전송되었습니다! (상단 탭 3, 5, 6 확인)")
                        st.rerun()

# =========================================================
# TAB 3: 📊 9개사 동일 배당 분석
# =========================================================
with tab_analysis:
    st.subheader("🔬 3번 탭: 9대 북메이커 배당 입력 및 승률 분석")

    if st.session_state.selected_scan_match:
        sm = st.session_state.selected_scan_match
        st.success(f"🎯 [스캐너 연동 완료] 현재 **[{sm['home']} vs {sm['away']}]** 경기의 배당 데이터가 자동 적용되어 있습니다.")

    c_an_l1, c_an_l2, c_an_l3 = st.columns([1, 1, 1])
    target_league = c_an_l1.text_input("🔍 리그명", value="PL", key="t2_target_league")
    t2_home_team = c_an_l2.text_input("🏠 홈팀명 (블로그 도표용)", value="", placeholder="예: 리버풀", key="t2_home_team")
    t2_away_team = c_an_l3.text_input("🚗 원정팀명 (블로그 도표용)", value="", placeholder="예: 본머스", key="t2_away_team")

    st.markdown("##### 🏢 분석할 9대 북메이커 배당 입력")
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
                        h_val = oh.number_input("홈", value=0.0, step=0.01, min_value=0.0, key=f"t2_{bm}_h")
                        d_val = od.number_input("무", value=0.0, step=0.01, min_value=0.0, key=f"t2_{bm}_d")
                        a_val = oa.number_input("원정", value=0.0, step=0.01, min_value=0.0, key=f"t2_{bm}_a")
                        odds_inputs_t2[bm] = (h_val, d_val, a_val)

    st.markdown("---")

    def compute_odds_analysis(is_league_filter=False, league_name=""):
        rows = []
        matched_dict = {}
        tot_bm = 0
        tot_payout = 0.0
        tot_m = 0
        tot_hw = 0
        tot_dr = 0
        tot_aw = 0

        for idx, bm in enumerate(BOOKMAKERS, 1):
            h, d, a = odds_inputs_t2.get(bm, (0.0, 0.0, 0.0))
            if h <= 0 or d <= 0 or a <= 0:
                rows.append({
                    "순번": str(idx), "북메이커": bm.upper(), "입력 배당": "미입력", "환급률": "-",
                    "매칭 경기": "0건", "홈승 확률": "-", "무승부 확률": "-", "원정승 확률": "-"
                })
                continue

            raw_inv = (1/h) + (1/d) + (1/a)
            payout = (1 / raw_inv) * 100
            tot_payout += payout
            tot_bm += 1

            df_bm = load_sheet_data(bm)
            m_count = 0
            h_str, d_str, a_str = "0.0%", "0.0%", "0.0%"

            if not df_bm.empty:
                try:
                    cols = list(df_bm.columns)
                    h_col = next((c for c in cols if any(k in c for k in ["해당_홈", "배당_홈", "홈배당", "홈_승", "H_ODDS"])), None)
                    d_col = next((c for c in cols if any(k in c for k in ["해당_무", "배당_무", "무배당", "무승부", "D_ODDS"])), None)
                    a_col = next((c for c in cols if any(k in c for k in ["해당_원", "배당_원", "원정배당", "원정_승", "A_ODDS"])), None)
                    res_col = next((c for c in cols if any(k in c for k in ["경기결과", "결과", "Result"])), None)
                    lg_col = next((c for c in cols if any(k in c for k in ["리그명", "리그", "League"])), None)

                    if not h_col and len(cols) > 14:
                        h_col, d_col, a_col = cols[12], cols[13], cols[14]
                    if not res_col:
                        res_col = cols[32] if len(cols) > 32 else cols[-1]

                    if h_col and d_col and a_col and res_col:
                        df_work = df_bm.copy()
                        if is_league_filter and lg_col and league_name.strip():
                            df_work = df_work[df_work[lg_col].astype(str).str.upper() == league_name.strip().upper()]

                        df_work["H_num"] = pd.to_numeric(df_work[h_col], errors="coerce").fillna(0.0)
                        df_work["D_num"] = pd.to_numeric(df_work[d_col], errors="coerce").fillna(0.0)
                        df_work["A_num"] = pd.to_numeric(df_work[a_col], errors="coerce").fillna(0.0)

                        cond = (
                            (df_work["H_num"] >= 1.01) & (df_work["D_num"] >= 1.01) & (df_work["A_num"] >= 1.01) &
                            (df_work["H_num"] >= h - tol) & (df_work["H_num"] <= h + tol) &
                            (df_work["D_num"] >= d - tol) & (df_work["D_num"] <= d + tol) &
                            (df_work["A_num"] >= a - tol) & (df_work["A_num"] <= a + tol)
                        )
                        matched = df_work[cond]
                        m_count = len(matched)

                        if m_count > 0:
                            matched_dict[bm.upper()] = matched
                            res_c = matched[res_col].value_counts()
                            hw = res_c.get("홈승", 0)
                            dr = res_c.get("무승부", 0)
                            aw = res_c.get("원정승", 0)

                            tot_m += m_count
                            tot_hw += hw
                            tot_dr += dr
                            tot_aw += aw

                            h_str = f"{round((hw/m_count)*100, 1)}% ({hw}회)"
                            d_str = f"{round((dr/m_count)*100, 1)}% ({dr}회)"
                            a_str = f"{round((aw/m_count)*100, 1)}% ({aw}회)"
                except Exception:
                    pass

            rows.append({
                "순번": str(idx), "북메이커": bm.upper(),
                "입력 배당": f"{h} / {d} / {a}",
                "환급률": f"{round(payout, 2)}%",
                "매칭 경기": f"{m_count}건",
                "홈승 확률": h_str, "무승부 확률": d_str, "원정승 확률": a_str
            })

        avg_p_str = f"{round(tot_payout / tot_bm, 2)}%" if tot_bm > 0 else "-"
        if tot_m > 0:
            tot_h_str = f"{round((tot_hw / tot_m) * 100, 1)}% ({tot_hw}회)"
            tot_d_str = f"{round((tot_dr / tot_m) * 100, 1)}% ({tot_dr}회)"
            tot_a_str = f"{round((tot_aw / tot_m) * 100, 1)}% ({tot_aw}회)"
        else:
            tot_h_str, tot_d_str, tot_a_str = "0.0%", "0.0%", "0.0%"

        rows.append({
            "순번": "🔥",
            "북메이커": "종합 가중평균 (누적)",
            "입력 배당": f"유효 {tot_bm}개사",
            "환급률": avg_p_str,
            "매칭 경기": f"총 {tot_m}건",
            "홈승 확률": tot_h_str,
            "무승부 확률": tot_d_str,
            "원정승 확률": tot_a_str
        })

        return pd.DataFrame(rows), matched_dict

    df_all_league, matched_all = compute_odds_analysis(is_league_filter=False)
    df_target_league, matched_target = compute_odds_analysis(is_league_filter=True, league_name=target_league)

    st.subheader("1️⃣ [전체 리그 기준] 동일 배당 승률 분석표")
    st.dataframe(df_all_league, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader(f"2️⃣ [{target_league} 동일 리그 전용] 동일 배당 승률 분석표")
    st.dataframe(df_target_league, use_container_width=True, hide_index=True)

    with st.expander("📊 / 📋 네이버 블로그/카페용 배당 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
        st.markdown("##### 🌟 [네이버 블로그/카페 전용] 배당 & 승률 인포그래픽 카드")
        st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

        compare_options = ["🌟 해외 종합 가중평균 (전체 평균)"] + OVERSEAS_BOOKMAKERS
        sel_compare_target = st.selectbox("비교할 대상 선택", compare_options, index=0, key="sel_compare_bm_t2")

        b_odds_val = odds_inputs_t2.get("배트맨", (0.0, 0.0, 0.0))

        if "종합 가중평균" in sel_compare_target:
            valid_h, valid_d, valid_a = [], [], []
            for obm in OVERSEAS_BOOKMAKERS:
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

        naver_odds_html = generate_naver_odds_infographic(
            b_odds_val, display_name, o_odds_val, 
            league_name=target_league, home_team=t2_home_team.strip(), away_team=t2_away_team.strip()
        )

        render_clipboard_component(naver_odds_html, "t2_clip", height=490)

    st.markdown("---")
    st.subheader("📋 매칭된 과거 경기 상세 리스트 (업체별 전체 내역)")
    
    view_option = st.radio("상세 리스트 필터 선택", ["전체 리그 매칭 내역", f"[{target_league}] 동일 리그 매칭 내역"], horizontal=True)
    active_matched = matched_target if "동일 리그" in view_option else matched_all

    if active_matched:
        for name, m_df in active_matched.items():
            with st.expander(f"📌 [{name}] 매칭 내역 총 {len(m_df)}건 확인하기", expanded=False):
                pref_cols = ["시즌", "리그명", "날짜", "홈팀", "원정팀", "해당_홈", "해당_무", "해당_원", "홈스코어", "원정스코어", "경기결과", "정/중/역", "적중배당"]
                show_cols = [c for c in pref_cols if c in m_df.columns]
                st.dataframe(m_df[show_cols] if show_cols else m_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"💡 현재 선택된 조건에 일치(오차 범위 ±{tol})하는 과거 경기 데이터가 없습니다.")

# =========================================================
# TAB 4: 📈 단일 팀별 경기내용 평균계산기
# =========================================================
with tab_team_stats:
    st.subheader("📈 팀별 과거 세부 경기내용 평균계산기 (단일 팀 기준)")
    df_stats_all = load_sheet_data(STATS_SHEET_NAME)
    
    c_f1, c_f2, c_f3 = st.columns(3)
    available_seasons = sorted(df_stats_all["시즌"].dropna().unique().tolist()) if not df_stats_all.empty and "시즌" in df_stats_all.columns else ["25-26", "2025"]
    available_leagues = sorted(df_stats_all["리그명"].dropna().unique().tolist()) if not df_stats_all.empty and "리그명" in df_stats_all.columns else ["PL", "EPL"]
    
    teams_set = set()
    if not df_stats_all.empty:
        if "홈팀" in df_stats_all.columns:
            teams_set.update(df_stats_all["홈팀"].dropna().unique())
        if "원정팀" in df_stats_all.columns:
            teams_set.update(df_stats_all["원정팀"].dropna().unique())
    available_teams = sorted(list(teams_set)) if teams_set else ["맨체스터시티", "리버풀", "본머스", "웨스트햄"]

    sel_season = c_f1.selectbox("시즌", available_seasons if available_seasons else ["전체"], key="sel_stat_season")
    sel_league = c_f2.selectbox("경기구분 (리그)", available_leagues if available_leagues else ["전체"], key="sel_stat_league")
    sel_team = c_f3.selectbox("경기목록 (팀이름)", available_teams if available_teams else ["팀 선택"], key="sel_stat_team")

    st.markdown("---")

    df_summary = pd.DataFrame()
    tac_df = pd.DataFrame()
    df_goals = pd.DataFrame()

    if not df_stats_all.empty and "홈팀" in df_stats_all.columns:
        df_target = df_stats_all.copy()
        if sel_season != "전체":
            df_target = df_target[df_target["시즌"] == sel_season]
        if sel_league != "전체":
            df_target = df_target[df_target["리그명"] == sel_league]

        df_home_matches = df_target[df_target["홈팀"] == sel_team]
        df_away_matches = df_target[df_target["원정팀"] == sel_team]

        def to_num(series):
            return pd.to_numeric(series.astype(str).str.replace("%", "").str.strip(), errors="coerce").fillna(0)

        h_cnt = len(df_home_matches)
        a_cnt = len(df_away_matches)
        total_cnt = h_cnt + a_cnt

        h_1h_goals = to_num(df_home_matches["전반득점_홈"]).sum() if h_cnt > 0 else 0
        h_2h_goals = to_num(df_home_matches["후반득점_홈"]).sum() if h_cnt > 0 else 0
        h_tot_goals = h_1h_goals + h_2h_goals

        a_1h_goals = to_num(df_away_matches["전반득점_원"]).sum() if a_cnt > 0 else 0
        a_2h_goals = to_num(df_away_matches["후반득점_원"]).sum() if a_cnt > 0 else 0
        a_tot_goals = a_1h_goals + a_2h_goals

        h_1h_avg = round(h_1h_goals / h_cnt, 2) if h_cnt > 0 else 0.0
        h_2h_avg = round(h_2h_goals / h_cnt, 2) if h_cnt > 0 else 0.0
        h_tot_avg = round(h_tot_goals / h_cnt, 2) if h_cnt > 0 else 0.0

        a_1h_avg = round(a_1h_goals / a_cnt, 2) if a_cnt > 0 else 0.0
        a_2h_avg = round(a_2h_goals / a_cnt, 2) if a_cnt > 0 else 0.0
        a_tot_avg = round(a_tot_goals / a_cnt, 2) if a_cnt > 0 else 0.0

        tot_1h_avg = round((h_1h_goals + a_1h_goals) / total_cnt, 2) if total_cnt > 0 else 0.0
        tot_2h_avg = round((h_2h_goals + a_2h_goals) / total_cnt, 2) if total_cnt > 0 else 0.0
        tot_all_avg = round((h_tot_goals + a_tot_goals) / total_cnt, 2) if total_cnt > 0 else 0.0

        def calc_avg(h_col, a_col):
            h_val = to_num(df_home_matches[h_col]).mean() if h_cnt > 0 and h_col in df_home_matches.columns else 0.0
            a_val = to_num(df_away_matches[a_col]).mean() if a_cnt > 0 and a_col in df_away_matches.columns else 0.0
            tot_val = (to_num(df_home_matches[h_col]).sum() + to_num(df_away_matches[a_col]).sum()) / total_cnt if total_cnt > 0 else 0.0
            return round(h_val, 2), round(a_val, 2), round(tot_val, 2)

        poss_h, poss_a, poss_tot = calc_avg("점유율_홈", "점유율_원")
        sot_h, sot_a, sot_tot = calc_avg("유효슈팅_홈", "유효슈팅_원")
        pass_h, pass_a, pass_tot = calc_avg("패스성공률_홈", "패스성공률_원")
        yc_h, yc_a, yc_tot = calc_avg("경고_홈", "경고_원")
        rc_h, rc_a, rc_tot = calc_avg("퇴장_홈", "퇴장_원")
        xg_h, xg_a, xg_tot = calc_avg("xG_홈", "xG_원")
        ratio_h, ratio_a, ratio_tot = calc_avg("유효슈팅비율_홈", "유효슈팅비율_원")

        st.markdown(f"### 📋 [{sel_team}] 시즌 평균 지표 종합 요약 (총 {total_cnt}경기: 홈 {h_cnt}경기 / 원정 {a_cnt}경기)")
        stat_summary_data = {
            "구분": ["점유율 (%)", "유효슈팅 (회)", "패스성공률 (%)", "경고 (회)", "퇴장 (회)", "xG (기대득점)", "유효슈팅비율 (%)"],
            "홈 (Home)": [f"{poss_h}%", f"{sot_h}", f"{pass_h}%", f"{yc_h}", f"{rc_h}", f"{xg_h}", f"{ratio_h}%"],
            "원정 (Away)": [f"{poss_a}%", f"{sot_a}", f"{pass_a}%", f"{yc_a}", f"{rc_a}", f"{xg_a}", f"{ratio_a}%"],
            "시즌 전체 평균": [f"{poss_tot}%", f"{sot_tot}", f"{pass_tot}%", f"{yc_tot}", f"{rc_tot}", f"{xg_tot}", f"{ratio_tot}%"]
        }
        df_summary = pd.DataFrame(stat_summary_data)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ♟️ 팀 전술(포메이션) 사용 횟수 및 비율")
        home_tacs = df_home_matches["전술_홈"].dropna().astype(str).str.strip().tolist() if "전술_홈" in df_home_matches.columns else []
        away_tacs = df_away_matches["전술_원"].dropna().astype(str).str.strip().tolist() if "전술_원" in df_away_matches.columns else []
        all_tacs = home_tacs + away_tacs
        unique_tacs = sorted(list(set([t for t in all_tacs if t and t != "-"])))
        
        if unique_tacs and total_cnt > 0:
            tac_rows = []
            for t in unique_tacs:
                h_c = home_tacs.count(t)
                a_c = away_tacs.count(t)
                tot_c = h_c + a_c
                ratio = round((tot_c / total_cnt) * 100, 1)
                tac_rows.append({
                    "전술 (포메이션)": t,
                    "전체 사용 횟수": f"{tot_c}회 ({ratio}%)",
                    "홈경기 사용": f"{h_c}회",
                    "원정경기 사용": f"{a_c}회"
                })
            tac_df = pd.DataFrame(tac_rows).sort_values(by="전체 사용 횟수", ascending=False)
            st.dataframe(tac_df, use_container_width=True, hide_index=True)
        else:
            st.info("💡 등록된 전술 데이터가 없습니다.")

        st.markdown("---")
        st.markdown("### ⚽ 전/후반 득점 통계표")
        goal_table_data = {
            "구분": ["홈", "원정", "시즌 평균"],
            "전반 총득점": [int(h_1h_goals), int(a_1h_goals), "-"],
            "후반 총득점": [int(h_2h_goals), int(a_2h_goals), "-"],
            "총점": [int(h_tot_goals), int(a_tot_goals), "-"],
            "전반 평균": [h_1h_avg, a_1h_avg, tot_1h_avg],
            "후반 평균": [h_2h_avg, a_2h_avg, tot_2h_avg],
            "합계 평균": [h_tot_avg, a_tot_avg, tot_all_avg]
        }
        df_goals = pd.DataFrame(goal_table_data)
        st.dataframe(df_goals, use_container_width=True, hide_index=True)
        
        with st.expander("📊 / 📋 네이버 블로그/카페용 팀 지표 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
            st.markdown(f"##### 🌟 [네이버 블로그/카페 전용] [{sel_team}] 시즌 지표 인포그래픽 카드")
            st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

            match_info_str = f"총 {total_cnt}경기: 홈 {h_cnt} / 원정 {a_cnt}"
            naver_team_html = generate_naver_team_stats_infographic(
                sel_team, sel_season, sel_league, match_info_str, 
                df_summary, tac_df, df_goals
            )

            render_clipboard_component(naver_team_html, "t3_clip", height=620)
            
    else:
        st.info("💡 10번 '경기내용' 탭에 아직 데이터가 없습니다.")

# =========================================================
# TAB 5: ⚔️ 홈 vs 원정 맞대결(H2H) 종합 분석
# =========================================================
with tab_h2h:
    st.subheader("⚔️ 홈팀 vs 원정팀 역대 맞대결(H2H) 종합 분석 및 세부 지표")
    st.caption("두 팀을 선택하면 역대 맞대결 경기들의 평균 지표, 사용된 전술 횟수, 전/후반 득점 및 비율(%) 통계가 출력됩니다.")

    df_stats_h2h = load_sheet_data(STATS_SHEET_NAME)

    teams_set_h2h = set()
    if not df_stats_h2h.empty:
        if "홈팀" in df_stats_h2h.columns:
            teams_set_h2h.update(df_stats_h2h["홈팀"].dropna().unique())
        if "원정팀" in df_stats_h2h.columns:
            teams_set_h2h.update(df_stats_h2h["원정팀"].dropna().unique())
    available_h2h_teams = sorted(list(teams_set_h2h)) if teams_set_h2h else ["리버풀", "본머스", "웨스트햄", "맨체스터시티"]

    default_h_idx = 0
    default_a_idx = 1 if len(available_h2h_teams) > 1 else 0

    if st.session_state.selected_scan_match:
        sm = st.session_state.selected_scan_match
        if sm["home"] in available_h2h_teams:
            default_h_idx = available_h2h_teams.index(sm["home"])
        if sm["away"] in available_h2h_teams:
            default_a_idx = available_h2h_teams.index(sm["away"])

    c_h2h_1, c_h2h_2 = st.columns(2)
    sel_home_h2h = c_h2h_1.selectbox("🏠 홈팀 선택", available_h2h_teams, index=default_h_idx, key="sel_h2h_home")
    sel_away_h2h = c_h2h_2.selectbox("🚗 원정팀 선택", available_h2h_teams, index=default_a_idx, key="sel_h2h_away")

    st.markdown("---")

    df_h2h_summary = pd.DataFrame()
    df_h_tac = pd.DataFrame()
    df_a_tac = pd.DataFrame()
    df_h2h_goals = pd.DataFrame()

    if not df_stats_h2h.empty and "홈팀" in df_stats_h2h.columns and "원정팀" in df_stats_h2h.columns:
        def to_num(series):
            return pd.to_numeric(series.astype(str).str.replace("%", "").str.strip(), errors="coerce").fillna(0)

        cond_exact = (df_stats_h2h["홈팀"] == sel_home_h2h) & (df_stats_h2h["원정팀"] == sel_away_h2h)
        cond_all = ((df_stats_h2h["홈팀"] == sel_home_h2h) & (df_stats_h2h["원정팀"] == sel_away_h2h)) | \
                   ((df_stats_h2h["홈팀"] == sel_away_h2h) & (df_stats_h2h["원정팀"] == sel_home_h2h))

        df_h2h_exact = df_stats_h2h[cond_exact].copy()
        df_h2h_all = df_stats_h2h[cond_all].copy()

        total_h2h_count = len(df_h2h_all)
        exact_h2h_count = len(df_h2h_exact)

        if total_h2h_count > 0:
            st.markdown(f"### 📋 [{sel_home_h2h}] vs [{sel_away_h2h}] 역대 맞대결 기록 (총 {total_h2h_count}경기 / 홈원정 동일 매치업 {exact_h2h_count}경기)")

            h_wins, draws, a_wins = 0, 0, 0
            for _, r in df_h2h_all.iterrows():
                h_g = to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_홈", 0)])).iloc[0]
                ag = to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0]
                
                if r["홈팀"] == sel_home_h2h:
                    if h_g > ag: h_wins += 1
                    elif h_g == ag: draws += 1
                    else: a_wins += 1
                else:
                    if ag > h_g: h_wins += 1
                    elif ag == h_g: draws += 1
                    else: a_wins += 1

            ex_h_wins, ex_draws, ex_a_wins = 0, 0, 0
            for _, r in df_h2h_exact.iterrows():
                h_g = to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_홈", 0)])).iloc[0]
                ag = to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0]
                if h_g > ag: ex_h_wins += 1
                elif h_g == ag: ex_draws += 1
                else: ex_a_wins += 1

            h2h_all_text = f"{sel_home_h2h} 기준 {total_h2h_count}전 {h_wins}승 {draws}무 {a_wins}패 (승률: {round((h_wins/total_h2h_count)*100, 1)}%)"
            
            if exact_h2h_count > 0:
                h2h_exact_text = f"{sel_home_h2h}(홈) 기준 {exact_h2h_count}전 {ex_h_wins}승 {ex_draws}무 {ex_a_wins}패 (승률: {round((ex_h_wins/exact_h2h_count)*100, 1)}%)"
            else:
                h2h_exact_text = f"동일 매치업 과거 경기 기록 없음 (0전 0승 0무 0패)"

            st.info(f"🏆 **역대 전체 상대전적:** {h2h_all_text}\n\n🏠 **홈/원정 동일 조건 상대전적:** {h2h_exact_text}")

            def get_h2h_stat_avg(col_h, col_a):
                home_team_vals, away_team_vals = [], []
                for _, r in df_h2h_all.iterrows():
                    if r["홈팀"] == sel_home_h2h:
                        if col_h in r: home_team_vals.append(to_num(pd.Series([r[col_h]])).iloc[0])
                        if col_a in r: away_team_vals.append(to_num(pd.Series([r[col_a]])).iloc[0])
                    else:
                        if col_a in r: home_team_vals.append(to_num(pd.Series([r[col_a]])).iloc[0])
                        if col_h in r: away_team_vals.append(to_num(pd.Series([r[col_h]])).iloc[0])
                avg_home = round(np.mean(home_team_vals), 2) if home_team_vals else 0.0
                avg_away = round(np.mean(away_team_vals), 2) if away_team_vals else 0.0
                return avg_home, avg_away

            poss_h, poss_a = get_h2h_stat_avg("점유율_홈", "점유율_원")
            sot_h, sot_a = get_h2h_stat_avg("유효슈팅_홈", "유효슈팅_원")
            pass_h, pass_a = get_h2h_stat_avg("패스성공률_홈", "패스성공률_원")
            yc_h, yc_a = get_h2h_stat_avg("경고_홈", "경고_원")
            rc_h, rc_a = get_h2h_stat_avg("퇴장_홈", "퇴장_원")
            xg_h, xg_a = get_h2h_stat_avg("xG_홈", "xG_원")
            ratio_h, ratio_a = get_h2h_stat_avg("유효슈팅비율_홈", "유효슈팅비율_원")

            h2h_summary_table = {
                "구분": ["점유율 (%)", "유효슈팅 (회)", "패스성공률 (%)", "경고 (회)", "퇴장 (회)", "xG (기대득점)", "유효슈팅비율 (%)"],
                f"{sel_home_h2h} (맞대결 평균)": [f"{poss_h}%", f"{sot_h}", f"{pass_h}%", f"{yc_h}", f"{rc_h}", f"{xg_h}", f"{ratio_h}%"],
                f"{sel_away_h2h} (맞대결 평균)": [f"{poss_a}%", f"{sot_a}", f"{pass_a}%", f"{yc_a}", f"{rc_a}", f"{xg_a}", f"{ratio_a}%"]
            }
            df_h2h_summary = pd.DataFrame(h2h_summary_table)
            st.dataframe(df_h2h_summary, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### ♟️ 맞대결 시 양 팀의 전술(포메이션) 사용 횟수")

            home_team_tacs, away_team_tacs = [], []
            for _, r in df_h2h_all.iterrows():
                if r["홈팀"] == sel_home_h2h:
                    if "전술_홈" in r and r["전술_홈"]: home_team_tacs.append(str(r["전술_홈"]).strip())
                    if "전술_원" in r and r["전술_원"]: away_team_tacs.append(str(r["전술_원"]).strip())
                else:
                    if "전술_원" in r and r["전술_원"]: home_team_tacs.append(str(r["전술_원"]).strip())
                    if "전술_홈" in r and r["전술_홈"]: away_team_tacs.append(str(r["전술_홈"]).strip())

            c_tc1, c_tc2 = st.columns(2)
            with c_tc1:
                st.markdown(f"**🔵 [{sel_home_h2h}] 맞대결 전술 빈도**")
                h_tac_vc = pd.Series(home_team_tacs).value_counts()
                if not h_tac_vc.empty:
                    df_h_tac = pd.DataFrame({"전술": h_tac_vc.index, "사용 횟수": [f"{c}회 ({round((c/total_h2h_count)*100, 1)}%)" for c in h_tac_vc.values]})
                    st.dataframe(df_h_tac, use_container_width=True, hide_index=True)

            with c_tc2:
                st.markdown(f"**🔴 [{sel_away_h2h}] 맞대결 전술 빈도**")
                a_tac_vc = pd.Series(away_team_tacs).value_counts()
                if not a_tac_vc.empty:
                    df_a_tac = pd.DataFrame({"전술": a_tac_vc.index, "사용 횟수": [f"{c}회 ({round((c/total_h2h_count)*100, 1)}%)" for c in a_tac_vc.values]})
                    st.dataframe(df_a_tac, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### ⚽ 맞대결 전/후반 득점 및 비율(%) 통계표")

            h_1h_list, h_2h_list, a_1h_list, a_2h_list = [], [], [], []
            for _, r in df_h2h_all.iterrows():
                if r["홈팀"] == sel_home_h2h:
                    h_1h_list.append(to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + 0)
                    h_2h_list.append(to_num(pd.Series([r.get("후반득점_홈", 0)])).iloc[0] + 0)
                    a_1h_list.append(to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + 0)
                    a_2h_list.append(to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0] + 0)
                else:
                    h_1h_list.append(to_num(pd.Series([r.get("전반득점_원", 0)])).iloc[0] + 0)
                    h_2h_list.append(to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0] + 0)
                    a_1h_list.append(to_num(pd.Series([r.get("전반득점_홈", 0)])).iloc[0] + 0)
                    a_2h_list.append(to_num(pd.Series([r.get("후반득점_원", 0)])).iloc[0] + 0)

            sum_h_1h, sum_h_2h = sum(h_1h_list), sum(h_2h_list)
            sum_a_1h, sum_a_2h = sum(a_1h_list), sum(a_2h_list)
            tot_h_score, tot_a_score = sum_h_1h + sum_h_2h, sum_a_1h + sum_a_2h

            avg_h_1h, avg_h_2h, avg_h_tot = round(sum_h_1h / total_h2h_count, 2), round(sum_h_2h / total_h2h_count, 2), round(tot_h_score / total_h2h_count, 2)
            avg_a_1h, avg_a_2h, avg_a_tot = round(sum_a_1h / total_h2h_count, 2), round(sum_a_2h / total_h2h_count, 2), round(tot_a_score / total_h2h_count, 2)

            ratio_h_2h = f"{round((sum_h_2h / tot_h_score) * 100, 1)}%" if tot_h_score > 0 else "0.0%"
            ratio_a_2h = f"{round((sum_a_2h / tot_a_score) * 100, 1)}%" if tot_a_score > 0 else "0.0%"
            tot_all_2h, tot_all_score = sum_h_2h + sum_a_2h, tot_h_score + tot_all_score
            ratio_all_2h = f"{round((tot_all_2h / tot_all_score) * 100, 1)}%" if tot_all_score > 0 else "0.0%"

            h2h_goal_table = {
                "구분": [sel_home_h2h, sel_away_h2h, "맞대결 전체 합계"],
                "전반 총득점": [int(sum_h_1h), int(sum_a_1h), int(sum_h_1h + sum_a_1h)],
                "후반 총득점": [int(sum_h_2h), int(sum_a_2h), int(tot_all_2h)],
                "총점": [int(tot_h_score), int(tot_a_score), int(tot_all_score)],
                "후반 득점비율": [ratio_h_2h, ratio_a_2h, ratio_all_2h],
                "전반 평균": [avg_h_1h, avg_a_1h, round(avg_h_1h + avg_a_1h, 2)],
                "후반 평균": [avg_h_2h, avg_a_2h, round(avg_h_2h + avg_a_2h, 2)],
                "경기당 평균득점": [avg_h_tot, avg_a_tot, round(avg_h_tot + avg_a_tot, 2)]
            }
            df_h2h_goals = pd.DataFrame(h2h_goal_table)
            st.dataframe(df_h2h_goals, use_container_width=True, hide_index=True)

            with st.expander("📊 / 📋 네이버 블로그/카페용 맞대결 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
                st.markdown("##### 🌟 [네이버 블로그/카페 전용] 맞대결 지표 비교 도표")
                st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

                gauge_stats = {
                    "점유율 (%)": (poss_h, poss_a),
                    "기대득점 (xG)": (xg_h, xg_a),
                    "유효슈팅 (회)": (sot_h, sot_a),
                    "패스성공률 (%)": (pass_h, pass_a),
                    "경기당 평균득점": (avg_h_tot, avg_a_tot)
                }
                
                naver_info_html = generate_naver_match_infographic(
                    sel_home_h2h, sel_away_h2h, gauge_stats, df_h2h_goals, 
                    h2h_all_str=h2h_all_text, h2h_exact_str=h2h_exact_text
                )
                
                render_clipboard_component(naver_info_html, "t4_clip", height=560)

            st.markdown("---")
            st.markdown("### 📋 역대 맞대결 전체 경기 세부 내역")
            pref_h2h_cols = ["시즌", "리그명", "경기날짜", "홈팀", "원정팀", "전반득점_홈", "후반득점_홈", "전반득점_원", "후반득점_원", "전술_홈", "전술_원", "점유율_홈", "점유율_원", "슈팅_홈", "슈팅_원", "유효슈팅_홈", "유효슈팅_원", "xG_홈", "xG_원"]
            show_h2h_cols = [c for c in pref_h2h_cols if c in df_h2h_all.columns]
            st.dataframe(df_h2h_all[show_h2h_cols] if show_h2h_cols else df_h2h_all, use_container_width=True, hide_index=True)

        else:
            st.info(f"💡 [{sel_home_h2h}]와 [{sel_away_h2h}] 간의 과거 맞대결 경기 데이터가 아직 10번 시트에 없습니다.")
    else:
        st.info("💡 10번 '경기내용' 탭에 데이터가 없습니다.")

# =========================================================
# TAB 6: 🚑 팀별 부상자/결장자 명단 & 퇴장자 자동 추적기
# =========================================================
with tab_injuries:
    st.subheader("🚑 팀별 부상자/결장자 명단 및 카드 리포트 (11번 시트 연동)")

    df_injuries = load_sheet_data(INJURY_SHEET_NAME)
    df_stats_red = load_sheet_data(STATS_SHEET_NAME)

    # 1. 🚨 리그/기간별 퇴장 발생 경기 자동 추적기
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

                # 1) 리그 필터링
                if sel_rc_league != "전체 리그" and r_league.upper() != sel_rc_league.upper():
                    continue

                # 2) 스마트 날짜 필터링
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

                # 3) 퇴장이 1회 이상 발생한 경우
                if rc_h > 0 or rc_a > 0:
                    red_teams = []
                    if rc_h > 0: red_teams.append(f"🔴 홈팀 [{r_home}] ({int(rc_h)}명 퇴장)")
                    if rc_a > 0: red_teams.append(f"🔴 원정팀 [{r_away}] ({int(rc_a)}명 퇴장)")

                    red_card_records.append({
                        "경기날짜": r_date_raw if r_date_raw else "-",
                        "리그": r_league,
                        "매치업": f"{r_home} vs {r_away}",
                        "🚨 퇴장 발생 팀": " / ".join(red_teams),
                        "홈 퇴장": int(rc_h),
                        "원정 퇴장": int(rc_a)
                    })

            if red_card_records:
                st.error(f"🚨 선택하신 조건에서 **총 {len(red_card_records)}건의 퇴장 발생 경기**가 발견되었습니다! 해당 팀의 선수를 아래 결장 명단에 등록하세요.")
                st.dataframe(pd.DataFrame(red_card_records), use_container_width=True, hide_index=True)
            else:
                st.success("✅ 선택하신 기간 및 리그 조건에서 퇴장(레드카드)이 발생한 경기가 없습니다.")
        else:
            st.info("💡 10번 '경기내용' 탭에 퇴장 기록 데이터가 없습니다.")

    st.markdown("---")

    c_s1, c_s2 = st.columns(2)
    team_options = sorted(df_injuries["팀명"].dropna().unique().tolist()) if not df_injuries.empty and "팀명" in df_injuries.columns else ["웨스트햄", "리버풀", "맨체스터시티"]
    
    default_inj_idx = 0
    if st.session_state.selected_scan_match:
        sm = st.session_state.selected_scan_match
        if sm["home"] in team_options:
            default_inj_idx = team_options.index(sm["home"])

    selected_team = c_s1.selectbox("조회할 팀명 선택", team_options if team_options else ["직접 등록 필요"], index=default_inj_idx, key="inj_filter_team")
    inj_league_title = c_s2.text_input("리그/대회 기준 표기", value="잉글랜드 1부리그 기록", key="inj_custom_league")

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        with st.expander(f"➕ [{selected_team}] 새로운 결장 선수 추가 (부상 / 징계 / 퇴장)", expanded=False):
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
            p_role = f8.text_input("팀 내 역할", value="주전", placeholder="예: 주전, 로테이션, 백업", key="p_role")
            p_reason = f9.selectbox("결장 사유", ["부상", "결장의심", "징계/퇴장", "기타"], key="p_reason")
            p_note = f10.text_input("특이사항", value="-", placeholder="예: 직전 경기 다이렉트 퇴장", key="p_note")

            if st.button("💾 구글 시트 11번 탭(부상자명단)에 저장", type="primary", use_container_width=True):
                if p_name_en.strip() or p_name_kr.strip():
                    client = get_gspread_client()
                    if client:
                        try:
                            spreadsheet = client.open_by_key(SPREADSHEET_ID)
                            ws_inj = spreadsheet.worksheet(INJURY_SHEET_NAME)
                            new_row = [
                                add_season, add_league, add_team,
                                p_name_en.strip(), p_name_kr.strip(),
                                p_pos, p_start, p_sub, p_goals, p_assists,
                                p_role.strip() if p_role.strip() else "-",
                                p_reason,
                                p_note.strip() if p_note.strip() else "-"
                            ]
                            ws_inj.append_row(new_row, value_input_option="USER_ENTERED")
                            time.sleep(0.2)
                            st.cache_data.clear()
                            st.success(f"🎉 {add_team}의 [{p_name_kr or p_name_en}] 선수가 11번 시트에 성공적으로 저장되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"저장 실패: {e}")
                else:
                    st.warning("선수 이름을 최소 1개 이상 입력해 주세요.")

    with col_btn2:
        with st.expander(f"🗑️ [{selected_team}] 부상/징계 복귀 선수 명단에서 제외하기", expanded=False):
            if not df_injuries.empty and "팀명" in df_injuries.columns:
                filtered_df_rm = df_injuries[df_injuries["팀명"] == selected_team]
                if not filtered_df_rm.empty:
                    player_options = []
                    for idx, row in filtered_df_rm.iterrows():
                        kr = row.get("선수한글명", "")
                        en = row.get("선수영문명", "")
                        name_display = f"{kr} ({en})" if kr and en else (kr or en)
                        player_options.append((idx, name_display))
                    
                    sel_player_to_remove = st.selectbox(
                        "복귀한 선수 선택", 
                        player_options, 
                        format_func=lambda x: x[1],
                        key="sel_remove_player"
                    )
                    
                    if st.button("🚀 선택한 선수 복귀 완료 (시트에서 삭제)", type="secondary", use_container_width=True):
                        client = get_gspread_client()
                        if client:
                            with st.spinner("구글 시트에서 선수 삭제 중..."):
                                try:
                                    spreadsheet = client.open_by_key(SPREADSHEET_ID)
                                    ws_inj = spreadsheet.worksheet(INJURY_SHEET_NAME)
                                    target_row_index = sel_player_to_remove[0] + 2
                                    ws_inj.delete_rows(target_row_index)
                                    time.sleep(0.2)
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

    if not df_injuries.empty and "팀명" in df_injuries.columns:
        filtered_df = df_injuries[df_injuries["팀명"] == selected_team]

        if not filtered_df.empty:
            st.subheader(f"📋 [{selected_team}] 결장자 현황 (총 {len(filtered_df)}명)")

            reason_col = "결장사유" if "결장사유" in filtered_df.columns else "사유"
            confirmed_players = filtered_df[filtered_df[reason_col] != "결장의심"].to_dict("records")
            doubt_players = filtered_df[filtered_df[reason_col] == "결장의심"].to_dict("records")

            with st.expander("📊 / 📋 네이버 블로그/카페용 결장자 인포그래픽 도표 복사 (추천 ⭐)", expanded=True):
                st.markdown(f"##### 🌟 [네이버 블로그/카페 전용] [{selected_team}] 결장자 리포트 카드")
                st.caption("초록색 버튼을 1번만 클릭하면 네이버 블로그 서식으로 복사됩니다. 블로그 글쓰기에서 Ctrl+V를 누르세요!")

                naver_inj_html = generate_naver_injury_infographic(
                    selected_team, inj_league_title, confirmed_players, doubt_players
                )

                render_clipboard_component(naver_inj_html, "t5_clip", height=520)

            card_text = f"### 🚑 {selected_team} 결장 & 결장의심 명단\n"
            card_text += f"*({inj_league_title})*\n\n"

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
                    reason = p.get(reason_col, "부상")
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
                    reason = p.get(reason_col, "결장의심")
                    note = p.get("특이사항", "-")
                    note_str = f" *({note})*" if note != "-" else ""
                    card_text += f"* ❓ **{name_str}** | `{pos}` · `{role}`\n"
                    card_text += f"  * 📊 **기록**: {start}선발 {sub}교체 / {goals}골 {assists}도움\n"
                    card_text += f"  * ⚠️ **사유**: {reason}{note_str}\n\n"

            with st.expander("📝 심플 텍스트 복사용"):
                st.text_area("텍스트 복사창", value=card_text, height=250)
            
            with st.expander("🔍 시트에 저장된 원본 데이터 표 보기"):
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 현재 [{selected_team}]에 등록된 결장 선수가 없습니다. 위의 '➕ 새로운 결장 선수 추가'에서 등록해 보세요.")
    else:
        st.info("💡 11번 구글 시트(`부상자명단`)에 데이터가 없거나 탭이 생성되지 않았습니다.")
