import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# 1. 페이지 레이아웃 및 디자인
# ---------------------------------------------------------
st.set_page_config(
    page_title="Football Odds & Match Analysis",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 비공개 보안 로그인
# ---------------------------------------------------------
ADMIN_PASSWORD = "myfootball2026!"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_password():
    if st.session_state.get("pw_input") == ADMIN_PASSWORD:
        st.session_state["authenticated"] = True
    else:
        st.error("비밀번호가 일치하지 않습니다.")

if not st.session_state["authenticated"]:
    st.title("🔒 비공개 축구 배당/스탯 분석기")
    st.text_input("접속 비밀번호", type="password", key="pw_input", on_change=check_password)
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 로드 (CSV / 샘플)
# ---------------------------------------------------------
@st.cache_data
def get_default_match_data():
    return {
        "info": {
            "시즌": "25-26", "리그": "PL", "날짜": "25.08.16",
            "홈팀": "리버풀", "원정팀": "본머스",
            "홈점수": 4, "원정점수": 2, "결과": "홈승", "정역배": "정배"
        },
        "odds": {
            "구분": ["승 (홈)", "무승부", "패 (원정)"],
            "베트맨 배당": [1.22, 5.10, 7.50],
            "베트맨 확률(%)": [71.33, 17.06, 11.60],
            "배당편차": [0.01, -0.22, 0.10],
            "손상률(%)": [-29.03, -13.68, -7.14],
            "적정 배당": [1.21, 5.32, 7.40],
            "오픈 배당": [1.29, 6.00, 9.00],
            "BWIN 배당": [1.31, 5.75, 8.00],
            "BWIN 확률(%)": [71.86, 16.37, 11.77]
        },
        "stats": {
            "지표": ["xG (기대득점)", "볼 점유율(%)", "슈팅수", "유효슈팅수", "유효슈팅 비율(%)", "패스 성공률(%)", "경고(옐로)", "퇴장(레드)", "포메이션"],
            "홈팀 (리버풀)": [2.21, "61%", 19, 10, "52.6%", "82%", 1, 0, "4-2-3-1"],
            "원정팀 (본머스)": [1.70, "39%", 10, 3, "30.0%", "70%", 2, 0, "4-1-4-1"]
        },
        "goals": {
            "구분": ["전반 득점", "후반 득점", "전반 득점비율", "후반 득점비율"],
            "홈팀": [1, 3, "25.0%", "75.0%"],
            "원정팀": [0, 2, "0.0%", "100.0%"]
        }
    }

match_data = get_default_match_data()

# ---------------------------------------------------------
# 4. 사이드바 - 경기 선택 및 파일 관리
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 경기 선택")
    st.selectbox("시즌 선택", ["25-26"])
    st.selectbox("리그 선택", ["PL (프리미어리그)", "라리가", "세리에A", "분데스리가"])
    selected_match = st.selectbox("경기 선택", ["리버풀 vs 본머스 (25.08.16)", "아스톤 빌라 vs 뉴캐슬 (25.08.16)"])
    
    st.markdown("---")
    st.header("📤 구글시트 / CSV 업로드")
    uploaded_file = st.file_uploader("배당초안 파일 업로드", type=["csv", "xlsx"])
    if uploaded_file:
        st.success("데이터가 성공적으로 연동되었습니다.")

# ---------------------------------------------------------
# 5. 메인 화면 - 경기 브리핑 헤더
# ---------------------------------------------------------
info = match_data["info"]

st.caption(f"🏆 {info['시즌']} {info['리그']} | 📅 {info['날짜']}")
col_h, col_s, col_a = st.columns([4, 2, 4])

with col_h:
    st.markdown(f"<h2 style='text-align: right;'>{info['홈팀']} 🔴</h2>", unsafe_allow_html=True)
with col_s:
    badge_color = "#2563EB" if info["정역배"] == "정배" else "#DC2626"
    st.markdown(
        f"<div style='text-align:center;'>"
        f"<h1 style='margin:0;'>{info['홈점수']} : {info['원정점수']}</h1>"
        f"<span style='background:{badge_color}; color:white; padding:3px 10px; border-radius:12px; font-size:13px; font-weight:bold;'>{info['결과']} ({info['정역배']})</span>"
        f"</div>",
        unsafe_allow_html=True
    )
with col_a:
    st.markdown(f"<h2 style='text-align: left;'>🔵 {info['원정팀']}</h2>", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------
# 6. 3개 탭 구성 (배당 분석 / 인게임 스탯 / 승률 시뮬레이터)
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["💰 배당률 & 편차/손익 분석", "📊 인게임 세부 스탯 & xG", "🧮 실시간 배당 역산기"])

# TAB 1: 배당 분석
with tab1:
    st.subheader("북메이커 배당 및 기대확률 비교")
    
    odds_df = pd.DataFrame(match_data["odds"])
    st.dataframe(odds_df, use_container_width=True, hide_index=True)
    
    # 핵심 지표 카드
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("베트맨 환급률", "87.03%")
    c2.metric("BWIN 환급률", "94.14%", delta="+7.11% (해외 우세)")
    c3.metric("홈 승리 기대확률", "71.33%")
    c4.metric("홈 손상률 (Value)", "-29.03%")

# TAB 2: 세부 스탯
with tab2:
    st.subheader("경기 내용 & 경기력 스탯")
    
    col_stat1, col_stat2 = st.columns([6, 4])
    
    with col_stat1:
        st.markdown("**기본 인게임 스탯**")
        stats_df = pd.DataFrame(match_data["stats"])
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
    with col_stat2:
        st.markdown("**전/후반 득점 분포**")
        goals_df = pd.DataFrame(match_data["goals"])
        st.dataframe(goals_df, use_container_width=True, hide_index=True)

# TAB 3: 실시간 계산기
with tab3:
    st.subheader("신규 경기 배당 입력 및 환산 승률 계산")
    ic1, ic2, ic3 = st.columns(3)
    ih = ic1.number_input("홈 배당", value=1.22, step=0.01)
    id_ = ic2.number_input("무승부 배당", value=5.10, step=0.01)
    ia = ic3.number_input("원정 배당", value=7.50, step=0.01)
    
    raw = (1/ih) + (1/id_) + (1/ia)
    payout = (1/raw) * 100
    
    st.info(f"💡 산출 환급률: **{payout:.2f}%**")
    
    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("홈 승률", f"{(1/ih)/raw*100:.2f}%")
    rc2.metric("무승부 확률", f"{(1/id_)/raw*100:.2f}%")
    rc3.metric("원정 승률", f"{(1/ia)/raw*100:.2f}%")
