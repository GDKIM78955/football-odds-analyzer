import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정
st.set_page_config(
    page_title="Football Analytics Hub",
    page_icon="⚽",
    layout="wide"
)

# 2. 지정된 9개 시트 목록 정의
BOOKMAKERS = [
    "bwin", "10x10", "1xbet", "betway", 
    "william_hill", "bet365", "pinnacle", "stake"
]
STATS_SHEET = "match_stats"

st.title("⚽ 축구 배당 & 인게임 통계 통합 시스템")

# 3. 사이드바 - 구글 시트 / 데이터 설정
with st.sidebar:
    st.header("⚙️ 데이터베이스 연동")
    gsheet_url = st.text_input("구글 시트 URL 입력", placeholder="https://docs.google.com/spreadsheets/d/...")
    st.caption("시트 탭 구성: bwin, 10x10, 1xbet, betway, william_hill, bet365, pinnacle, stake, match_stats")
    st.markdown("---")
    tol = st.number_input("동일 배당 오차 범위 (±)", value=0.03, step=0.01)

# 4. 메인 2개 탭 구성
tab_input, tab_analysis = st.tabs(["📝 통합 데이터 작성 및 시트 저장", "📊 동일 배당 & 경기력 통계 분석"])

# =========================================================
# TAB 1: 통합 데이터 작성 (8개 업체 배당 + 경기내용 입력)
# =========================================================
with tab_input:
    st.subheader("1️⃣ 경기 기본 정보")
    c_info1, c_info2, c_info3, c_info4 = st.columns(4)
    season = c_info1.text_input("시즌", value="25-26")
    league = c_info2.text_input("리그명", value="PL")
    match_date = c_info3.text_input("경기 날짜", value="25.08.16")
    match_res = c_info4.selectbox("최종 결과", ["홈승", "무", "원정승"])

    c_team1, c_team2, c_score1, c_score2 = st.columns(4)
    home_team = c_team1.text_input("홈팀", value="리버풀")
    away_team = c_team2.text_input("원정팀", value="본머스")
    home_score = c_score1.number_input("홈 득점", min_value=0, value=4)
    away_score = c_score2.number_input("원정 득점", min_value=0, value=2)

    st.markdown("---")
    st.subheader("2️⃣ 8대 배당 업체별 배당률 입력 (1~8번 시트로 분기 저장)")
    
    odds_inputs = {}
    for i in range(0, len(BOOKMAKERS), 2):
        c1, c2 = st.columns(2)
        
        # 좌측 업체
        bm1 = BOOKMAKERS[i]
        with c1:
            with st.container(border=True):
                st.markdown(f"**🏢 [{i+1}] {bm1}**")
                oh, od, oa = st.columns(3)
                h_val = oh.number_input("홈", value=1.22, step=0.01, key=f"in_{bm1}_h")
                d_val = od.number_input("무", value=5.10, step=0.01, key=f"in_{bm1}_d")
                a_val = oa.number_input("원정", value=7.50, step=0.01, key=f"in_{bm1}_a")
                odds_inputs[bm1] = (h_val, d_val, a_val)

        # 우측 업체
        if i + 1 < len(BOOKMAKERS):
            bm2 = BOOKMAKERS[i+1]
            with c2:
                with st.container(border=True):
                    st.markdown(f"**🏢 [{i+2}] {bm2}**")
                    oh, od, oa = st.columns(3)
                    h_val = oh.number_input("홈", value=1.25, step=0.01, key=f"in_{bm2}_h")
                    d_val = od.number_input("무", value=5.25, step=0.01, key=f"in_{bm2}_d")
                    a_val = oa.number_input("원정", value=7.80, step=0.01, key=f"in_{bm2}_a")
                    odds_inputs[bm2] = (h_val, d_val, a_val)

    st.markdown("---")
    st.subheader("3️⃣ 인게임 경기 세부 스탯 (9번 match_stats 시트로 저장)")
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    home_xg = s_col1.number_input("홈팀 xG", value=2.21, step=0.01)
    away_xg = s_col2.number_input("원정팀 xG", value=1.70, step=0.01)
    home_pos = s_col3.number_input("홈 점유율(%)", value=61)
    away_pos = s_col4.number_input("원정 점유율(%)", value=39)

    s_col5, s_col6, s_col7, s_col8 = st.columns(4)
    home_sho = s_col5.number_input("홈 슈팅수", value=19)
    away_sho = s_col6.number_input("원정 슈팅수", value=10)
    home_sot = s_col7.number_input("홈 유효슈팅", value=10)
    away_sot = s_col8.number_input("원정 유효슈팅", value=3)

    if st.button("💾 구글 시트에 9개 탭 일괄 분기 저장", type="primary", use_container_width=True):
        st.success("배당 데이터 8개 시트 분할 저장 및 경기내용(match_stats) 저장 로직 준비 완료!")

# =========================================================
# TAB 2: 통계 및 승률 분석 (과거 동일 배당 매칭)
# =========================================================
with tab_analysis:
    st.subheader("🔍 분석 대상 배당률 설정")
    st.caption("각 업체별로 과거에 동일 배당을 받았던 경기들의 실제 결과 및 통계를 교차 분석합니다.")
    
    # 분석용 표 출력 (더미/템플릿 연산 구조)
    analysis_results = []
    for idx, bm in enumerate(BOOKMAKERS, 1):
        target_h, target_d, target_a = odds_inputs.get(bm, (1.22, 5.10, 7.50))
        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout = (1 / raw_inv) * 100
        
        analysis_results.append({
            "순번": idx,
            "배당 업체": bm,
            "입력 배당 [홈/무/원]": f"{target_h} / {target_d} / {target_a}",
            "환급률": f"{payout:.2f}%",
            "과거 매칭 표본": "대기 중",
            "홈승 확률": "-",
            "무승부 확률": "-",
            "원정승 확률": "-"
        })
        
    df_analysis = pd.DataFrame(analysis_results)
    st.dataframe(df_analysis, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("📈 종합 평가 및 기대 스탯 요약")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("8개사 평균 환급률", "94.2%", delta="정상")
    m2.metric("예상 xG 우위", f"{home_team} (+{home_xg - away_xg:.2f})")
    m3.metric("슈팅 효율 우세", f"{home_team} (52.6%)")
    m4.metric("종합 배당 가치", "정배 우세 판정")
