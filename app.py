import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정
st.set_page_config(
    page_title="Football Odds & Stats Dashboard",
    page_icon="⚽",
    layout="wide"
)

# 2. 비공개 보안 비밀번호 (원하는 비밀번호로 바꾸세요)
ADMIN_PASSWORD = "2592"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_password():
    if st.session_state.get("password_input") == ADMIN_PASSWORD:
        st.session_state["authenticated"] = True
    else:
        st.error("비밀번호가 일치하지 않습니다.")

if not st.session_state["authenticated"]:
    st.markdown("## 🔒 축구 배당/스탯 비공개 분석기")
    st.info("관리자 전용 대시보드입니다. 비밀번호를 입력해주세요.")
    st.text_input("비밀번호", type="password", key="password_input", on_change=check_password)
    st.stop()

# 3. 샘플 데이터
@st.cache_data
def get_sample_data():
    return pd.DataFrame([
        {
            "시즌": "25-26", "리그명": "PL", "경기일시": "25.08.16", "홈팀": "리버풀", "원정팀": "본머스",
            "홈배당": 1.22, "무배당": 5.10, "원정배당": 7.50,
            "환급률": 87.03, "홈확률(%)": 71.33, "무확률(%)": 17.06, "원정확률(%)": 11.60,
            "배당편차_홈": 0.01, "배당편차_무": -0.22, "배당편차_원": 0.10,
            "손익_홈": -29.03, "손익_무": -13.68, "손익_원": -7.14,
            "BWIN_홈": 1.31, "BWIN_무": 5.75, "BWIN_원": 8.00,
            "점수_홈": 4, "점수_원": 2, "결과": "승", "정배역배": "정배",
            "xG_홈": 4.20, "xG_원": 1.43, "점유율_홈": 61, "점유율_원": 39,
            "슈팅성공_홈": 82, "슈팅성공_원": 70, "패스성공_홈": 83, "패스성공_원": 83,
            "포메이션_홈": "4-2-3-1", "포메이션_원": "4-1-4-1"
        },
        {
            "시즌": "25-26", "리그명": "PL", "경기일시": "25.08.16", "홈팀": "아스톤 빌라", "원정팀": "뉴캐슬",
            "홈배당": 1.94, "무배당": 3.45, "원정배당": 2.90,
            "환급률": 86.95, "홈확률(%)": 44.82, "무확률(%)": 25.20, "원정확률(%)": 29.98,
            "배당편차_홈": -0.28, "배당편차_무": 0.31, "배당편차_원": 0.27,
            "손익_홈": -32.85, "손익_무": 2.08, "손익_원": 2.70,
            "BWIN_홈": 2.40, "BWIN_무": 3.40, "BWIN_원": 2.85,
            "점수_홈": 0, "점수_원": 0, "결과": "무", "정배역배": "역배",
            "xG_홈": 1.05, "xG_원": 1.12, "점유율_홈": 40, "점유율_원": 60,
            "슈팅성공_홈": 73, "슈팅성공_원": 83, "패스성공_홈": 78, "패스성공_원": 81,
            "포메이션_홈": "4-2-3-1", "포메이션_원": "4-1-2-3"
        }
    ])

# 4. 사이드바 - 엑셀 업로드 및 필터
with st.sidebar:
    st.header("📂 엑셀 파일 관리")
    uploaded_file = st.file_uploader("축구 배당 엑셀 업로드 (.xlsx / .csv)", type=["xlsx", "xls", "csv"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.success("데이터 불러오기 완료!")
        except Exception as e:
            st.error(f"오류: {e}")
            df = get_sample_data()
    else:
        df = get_sample_data()

    st.markdown("---")
    st.header("🔍 조건 검색")
    leagues = ["전체"] + list(df["리그명"].dropna().unique()) if "리그명" in df.columns else ["전체"]
    sel_league = st.selectbox("리그 선택", leagues)
    
    sel_result = "전체"
    if "정배역배" in df.columns:
        sel_result = st.selectbox("정배/역배 결과", ["전체"] + list(df["정배역배"].dropna().unique()))

    team_kw = st.text_input("팀명 검색 (홈/원정)")

# 필터 적용
f_df = df.copy()
if sel_league != "전체":
    f_df = f_df[f_df["리그명"] == sel_league]
if sel_result != "전체":
    f_df = f_df[f_df["정배역배"] == sel_result]
if team_kw:
    f_df = f_df[f_df["홈팀"].astype(str).str.contains(team_kw, na=False) | f_df["원정팀"].astype(str).str.contains(team_kw, na=False)]

# 5. 메인 화면
st.title("⚽ 축구 배당 & 세부 스탯 통합 분석기")

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 분석 경기", f"{len(f_df):,}건")
if "정배역배" in f_df.columns and len(f_df) > 0:
    col2.metric("정배 출현율", f"{(f_df['정배역배'] == '정배').mean()*100:.1f}%")
if "xG_홈" in f_df.columns and len(f_df) > 0:
    col3.metric("평균 경기 xG", f"{(f_df['xG_홈'] + f_df['xG_원']).mean():.2f}")
if "환급률" in f_df.columns and len(f_df) > 0:
    col4.metric("평균 환급률", f"{f_df['환급률'].mean():.1f}%")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 데이터베이스", "📈 xG / 득점 분석", "🧮 배당률 승률 계산기"])

with tab1:
    st.subheader("매치 데이터 목록")
    st.dataframe(f_df, use_container_width=True, height=450)
    
    csv = f_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 필터링된 데이터 다운로드 (CSV)", csv, "match_data.csv", "text/csv")

with tab2:
    st.subheader("홈팀별 xG vs 실제 득점")
    if {"홈팀", "xG_홈", "점수_홈"}.issubset(f_df.columns):
        chart_data = f_df[["홈팀", "xG_홈", "점수_홈"]].set_index("홈팀")
        st.bar_chart(chart_data)

with tab3:
    st.subheader("신규 경기 배당률 분석기")
    c1, c2, c3 = st.columns(3)
    h_odd = c1.number_input("홈 승 배당", value=1.90, step=0.01)
    d_odd = c2.number_input("무승부 배당", value=3.40, step=0.01)
    a_odd = c3.number_input("원정 승 배당", value=3.80, step=0.01)
    
    inv_sum = (1/h_odd) + (1/d_odd) + (1/a_odd)
    st.info(f"💡 북메이커 마진 포함 환급률: **{(1/inv_sum)*100:.2f}%**")
    
    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("홈 승리 확률", f"{(1/h_odd)/inv_sum*100:.2f}%")
    rc2.metric("무승부 확률", f"{(1/d_odd)/inv_sum*100:.2f}%")
    rc3.metric("원정 승리 확률", f"{(1/a_odd)/inv_sum*100:.2f}%")
