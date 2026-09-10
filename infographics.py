import streamlit as st
import json
import streamlit.components.v1 as components

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
# 📊 카드 1: 동일 배당 매칭 스코어 기반 (승무패 통계 + 핸디캡 + 언오버) 인포그래픽
# =========================================================
def generate_naver_odds_with_handicap_infographic(b_odds, overseas_name, o_odds, league_name="", home_team="", away_team="", match_stats=None, hc_stats=None, ou_stats=None):
    b_h, b_d, b_a = b_odds
    o_h, o_d, o_a = o_odds

    if b_h > 0 and b_d > 0 and b_a > 0:
        b_inv = (1/b_h) + (1/b_d) + (1/b_a)
        b_payout = (1 / b_inv) * 100
    else:
        b_payout = 0.0

    if o_h > 0 and o_d > 0 and o_a > 0:
        o_inv = (1/o_h) + (1/o_d) + (1/o_a)
        o_payout = (1 / o_inv) * 100
    else:
        o_payout = 0.0

    # 승무패 확률 기본값 (매칭 통계가 있으면 대체)
    p_hw, p_dr, p_aw = 33.3, 33.3, 33.4
    match_cnt_total = 0
    if match_stats and match_stats.get("count", 0) > 0:
        match_cnt_total = match_stats.get("count", 0)
        p_hw = match_stats.get("home_win_pct", 33.3)
        p_dr = match_stats.get("draw_pct", 33.3)
        p_aw = match_stats.get("away_win_pct", 33.4)

    lg_badge = f"<span style='background-color: #2563eb; color: #ffffff; padding: 2px 7px; border-radius: 4px; font-size: 11px; margin-right: 6px;'>{league_name}</span>" if league_name else ""
    
    if home_team or away_team:
        match_title = f"<div style='font-size: 19px; font-weight: bold; color: #0f172a; margin-top: 4px;'><span style='color: #dc2626;'>{home_team}</span> <span style='font-size: 14px; color: #64748b;'>VS</span> <span style='color: #2563eb;'>{away_team}</span></div>"
    else:
        match_title = f"<div style='font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 4px;'>{lg_badge}동일 배당 매칭 스코어 기반 종합 분석 리포트</div>"

    html = f"""
    <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', AppleSDGothicNeo-Regular, sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; border-collapse: separate; color: #0f172a;">
        <tr>
            <td style="padding: 20px;">
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 16px;">
                    <tr>
                        <td align="center" style="padding-bottom: 10px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 1px;">MATCH STATS & PROBABILITY REPORT</div>
                            {match_title}
                            <div style="font-size: 12px; color: #475569; margin-top: 4px;">{lg_badge}동일 배당 매칭 데이터 총 <b>{match_cnt_total}건</b> 기준 분석</div>
                        </td>
                    </tr>
                </table>

                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 6px;">📊 [동일 배당 매칭] 실제 경기 결과 확률 분포</div>
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                    <tr style="background-color: #f8fafc;">
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #dc2626; width: 33%;">🔴 홈 승 비율</th>
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #059669; width: 34%;">🟢 무승부 비율</th>
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #2563eb; width: 33%;">🔵 원정승 비율</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #dc2626; font-size: 15px;">{p_hw}%</td>
                        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #059669; font-size: 15px;">{p_dr}%</td>
                        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #2563eb; font-size: 15px;">{p_aw}%</td>
                    </tr>
                </table>
    """

    if hc_stats:
        line = hc_stats.get("line", -1.0)
        cnt = hc_stats.get("count", 0)
        hw_p = hc_stats.get("home_win_pct", 0.0)
        aw_p = hc_stats.get("away_win_pct", 0.0)
        hw_cnt = hc_stats.get("home_win_cnt", 0)
        aw_cnt = hc_stats.get("away_win_cnt", 0)
        html += f"""
                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 12px; margin-bottom: 6px;">🎯 [동일 배당 매칭 스코어 기반 핸디캡 ({line})] 적중 확률 (총 {cnt}건)</div>
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                    <tr style="background-color: #f8fafc;">
                        <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #dc2626; width: 50%;">🔴 홈 핸디캡 승률</th>
                        <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #2563eb; width: 50%;">🔵 원정 플러스핸디 승률</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: #dc2626; font-size: 14px;">{hw_p}% ({hw_cnt}회)</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: #2563eb; font-size: 14px;">{aw_p}% ({aw_cnt}회)</td>
                    </tr>
                </table>
        """

    if ou_stats:
        line = ou_stats.get("line", 2.5)
        cnt = ou_stats.get("count", 0)
        ov_p = ou_stats.get("over_pct", 0.0)
        un_p = ou_stats.get("under_pct", 0.0)
        ov_cnt = ou_stats.get("over_cnt", 0)
        un_cnt = ou_stats.get("under_cnt", 0)
        html += f"""
                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 12px; margin-bottom: 6px;">⚡ [동일 배당 매칭 스코어 기반 언오버 ({line})] 적중 확률 (총 {cnt}건)</div>
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                    <tr style="background-color: #f8fafc;">
                        <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #059669; width: 50%;">🟢 오버 (Over) 확률</th>
                        <th style="padding: 8px 4px; border: 1px solid #cbd5e1; color: #d97706; width: 50%;">🟠 언더 (Under) 확률</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: #059669; font-size: 14px;">{ov_p}% ({ov_cnt}회)</td>
                        <td style="padding: 8px 4px; border: 1px solid #e2e8f0; font-weight: bold; color: #d97706; font-size: 14px;">{un_p}% ({un_cnt}회)</td>
                    </tr>
                </table>
        """

    html += f"""
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f1f5f9; border-radius: 6px; font-size: 12px; color: #334155;">
                    <tr>
                        <td align="center" style="padding: 8px 10px; text-align: center;">💰 환급률: <b>배트맨 {round(b_payout, 2)}%</b> / <b>{overseas_name} {round(o_payout, 2)}%</b></td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    """
    return html


# =========================================================
# 📊 카드 2: 기존 배당 편차 및 단순 배당 비교 인포그래픽
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
        fair_h = round((b_payout / 100) / (((1/o_h) / o_inv)), 2) if o_h > 0 else 0.0
        fair_d = round((b_payout / 100) / (((1/o_d) / o_inv)), 2) if o_d > 0 else 0.0
        fair_a = round((b_payout / 100) / (((1/o_a) / o_inv)), 2) if o_a > 0 else 0.0
    else:
        o_payout = 0.0
        fair_h, fair_d, fair_a = 0.0, 0.0, 0.0

    diff_h = round(b_h - o_h, 2) if (b_h > 0 and o_h > 0) else 0.0
    diff_d = round(b_d - o_d, 2) if (b_d > 0 and o_d > 0) else 0.0
    diff_a = round(b_a - o_a, 2) if (b_a > 0 and o_a > 0) else 0.0

    diff_h_str = f"+{diff_h}" if diff_h > 0 else f"{diff_h}"
    diff_d_str = f"+{diff_d}" if diff_d > 0 else f"{diff_d}"
    diff_a_str = f"+{diff_a}" if diff_a > 0 else f"{diff_a}"

    lg_badge = f"<span style='background-color: #2563eb; color: #ffffff; padding: 2px 7px; border-radius: 4px; font-size: 11px; margin-right: 6px;'>{league_name}</span>" if league_name else ""
    
    if home_team or away_team:
        match_title = f"<div style='font-size: 19px; font-weight: bold; color: #0f172a; margin-top: 4px;'><span style='color: #dc2626;'>{home_team}</span> <span style='font-size: 14px; color: #64748b;'>VS</span> <span style='color: #2563eb;'>{away_team}</span></div>"
    else:
        match_title = f"<div style='font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 4px;'>{lg_badge}배당 편차 및 단순 배당 비교 리포트</div>"

    h_col_name = f"홈 ({home_team})" if home_team else "홈 승 (Home)"
    a_col_name = f"원정 ({away_team})" if away_team else "원정승 (Away)"

    html = f"""
    <table align="center" border="0" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 620px; margin: 0 auto; font-family: 'Malgun Gothic', '맑은 고딕', AppleSDGothicNeo-Regular, sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; border-collapse: separate; color: #0f172a;">
        <tr>
            <td style="padding: 20px;">
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 2px solid #0f172a; margin-bottom: 16px;">
                    <tr>
                        <td align="center" style="padding-bottom: 10px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 1px;">ODDS COMPARISON REPORT</div>
                            {match_title}
                            <div style="font-size: 12px; color: #475569; margin-top: 4px;">{lg_badge}기준: <b>배트맨</b> vs <b>{overseas_name.upper()}</b></div>
                        </td>
                    </tr>
                </table>

                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 6px;">📊 배당률 기반 내재 확률 분포</div>
                <table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 14px;">
                    <tr style="background-color: #f8fafc;">
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #dc2626; width: 33%;">🔴 홈 승 내재확률</th>
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #059669; width: 34%;">🟢 무승부 내재확률</th>
                        <th style="padding: 8px; border: 1px solid #cbd5e1; color: #2563eb; width: 33%;">🔵 원정승 내재확률</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #dc2626; font-size: 15px;">{round(b_prob_h, 1)}%</td>
                        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #059669; font-size: 15px;">{round(b_prob_d, 1)}%</td>
                        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; color: #2563eb; font-size: 15px;">{round(b_prob_a, 1)}%</td>
                    </tr>
                </table>

                <div style="font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 6px;">⚽ [일반 승무패] 배당 편차 비교</div>
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

# (기존 generate_naver_team_stats_infographic, generate_naver_match_infographic, generate_naver_injury_infographic 함수들도 그대로 유지)
def generate_naver_team_stats_infographic(team_name, season, league, match_count_info, df_summary, tac_df, df_goals):
    return "" # 기존 유지

def generate_naver_match_infographic(home_team, away_team, stats_data, goal_df=None, h2h_all_str="", h2h_exact_str=""):
    return "" # 기존 유지

def generate_naver_injury_infographic(team_name, league_title, confirmed_list, doubt_list):
    return "" # 기존 유지
