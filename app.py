import streamlit as st
from tabs.tab1_input import render_tab1
from tabs.tab2_scanner import render_tab2
from tabs.tab3_analysis import render_tab3
from tabs.tab4_team_stats import render_tab4
from tabs.tab5_h2h import render_tab5
from tabs.tab6_injuries import render_tab6

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
SPREADSHEET_ID = "1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ"

# 세션 상태 초기화
if "match_queue" not in st.session_state:
    st.session_state.match_queue = []
if "current_queue_idx" not in st.session_state:
    st.session_state.current_queue_idx = 0

if "scan_queue" not in st.session_state:
    st.session_state.scan_queue = []
if "current_scan_queue_idx" not in st.session_state:
    st.session_state.current_scan_queue_idx = 0

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

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.caption(f"연동 시트 ID: `{SPREADSHEET_ID}`")
    tol = st.number_input("배당 오차 허용치 (±)", value=0.03, step=0.01)
    if st.button("🔄 전체 시트 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 6개 탭 구성
tab_input, tab_scanner, tab_analysis, tab_team_stats, tab_h2h, tab_injuries = st.tabs([
    "📝 경기 데이터 입력 & 저장", 
    "📡 라운드 경기 자동 스캐너 & 추천픽",
    "📊 9개사 동일 배당 분석", 
    "📈 팀별 세부내용 평균계산기",
    "⚔️ 홈 vs 원정 맞대결 종합분석",
    "🚑 팀별 부상자/결장자 명단"
])

with tab_input:
    render_tab1(SPREADSHEET_ID, BOOKMAKERS)

with tab_scanner:
    render_tab2(SPREADSHEET_ID, BOOKMAKERS, OVERSEAS_BOOKMAKERS, tol)

with tab_analysis:
    render_tab3(SPREADSHEET_ID, BOOKMAKERS, OVERSEAS_BOOKMAKERS, tol)

with tab_team_stats:
    render_tab4(SPREADSHEET_ID)

with tab_h2h:
    render_tab5(SPREADSHEET_ID)

with tab_injuries:
    render_tab6(SPREADSHEET_ID)
