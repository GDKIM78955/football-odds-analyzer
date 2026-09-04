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
# 📊 배당 인포그래픽 도표 생성 함수
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
# 📋 단일 팀 시즌 평균 리포트 도표 생성 함수
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
            g_df_copy = df_goals.copy()
            sub2 = g_df_copy[["구분", "전반 평균", "후반 평균", "합계 평균"]].copy()

            t2_html = sub2.to_html(index=False, escape=False).replace('<table border="1" class="dataframe">', '<table border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; border: 1px solid #cbd5e1; margin-bottom: 6px;">')
            t2_html = t2_html.replace('<th>', '<th align="center" style="background-color: #f8fafc; color: #334155; padding: 7px 3px; border: 1px solid #cbd5e1; font-weight: bold; text-align: center !important;">')
            t2_html = t2_html.replace('<td>', '<td align="center" style="background-color: #ffffff; color: #1e293b; padding: 6px 3px; border: 1px solid #e2e8f0; text-align: center !important;">')

            html += f"""
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
# ⚔️ 맞대결 인포그래픽 도표 생성 함수
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
# 🚑 부상자 인포그래픽 도표 생성 함수
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

    if not confirmed_list and not doubt_list:
        html += """
                <table border="0" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; margin-top: 10px; margin-bottom: 10px;">
                    <tr>
                        <td align="center" style="padding: 20px; text-align: center; color: #166534; font-size: 14px; font-weight: bold;">
                            ✅ 현재 등록된 부상 및 징계 결장자가 없습니다.<br>
                            <span style="font-size: 12px; color: #15803d; font-weight: normal; margin-top: 4px; display: inline-block;">(스쿼드 100% 전력 구성 완료 👑)</span>
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
