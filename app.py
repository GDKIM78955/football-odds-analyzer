import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정
st.set_page_config(
    page_title="Football Multi-Bookmaker Analytics",
    page_icon="⚽",
    layout="wide"
)

# 2. 비공개 로그인 설정
ADMIN_PASSWORD = "myfootball2026!"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("## 🔒 축구 배당/스탯 비공개 분석기")
    st.info("관리자 전용 대시보드입니다. 비밀번호를 입력해주세요.")
    pwd = st.text_input("접속 비밀번호", type="password")
    if st.button("로그인"):
        if pwd == ADMIN_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

# 3. 8개 북메이커 기본 템플릿/샘플 데이터 생성기
@st.cache_data
def load_default_multi_sheets():
    bookmakers = ["BWIN", "BET365", "PINNACLE", "BETMAN", "WILLIAMHILL", "UNIBET", "1XBET", "BETFAIR"]
    sample_dict = {}
    
    # 예시 샘플 데이터 (동일 양식)
    sample_rows = [
        {"시즌": "25-26", "리그명": "PL", "날짜": "25.08.16", "홈팀": "리버풀", "원정팀": "본머스", "홈배당": 1.22, "무배당": 5.10, "원정배당": 7.50, "결과": "홈승", "점수_홈": 4, "점수_원": 2},
        {"시즌": "25-26", "리그명": "PL", "날짜": "25.08.16", "홈팀": "아스톤빌라", "원정팀": "뉴캐슬", "홈배당": 1.94, "무배당": 3.45, "원정배당": 2.90, "결과": "무", "점수_홈": 0, "점수_원": 0},
        {"시즌": "24-25", "리그명": "PL", "날짜": "24.11.02", "홈팀": "맨시티", "원정팀": "사우샘프턴", "홈배당": 1.22, "무배당": 5.10, "원정배당": 7.50, "결과": "홈승", "점수_홈": 3, "점수_원": 1},
        {"시즌": "24-25", "리그명": "PL", "날짜": "25.01.10", "홈팀": "아스날", "원정팀": "에버튼", "홈배당": 1.22, "무배당": 5.00, "원정배당": 7.60, "결과": "무", "점수_홈": 1, "점수_원": 1}
    ]
    
    for bm in bookmakers:
        sample_dict[bm] = pd.DataFrame(sample_rows)
    return sample_dict

# 4. 사이드바 - 파일 관리
with st.sidebar:
    st.header("📂 8개사 엑셀/시트 관리")
    uploaded_file = st.file_uploader("8개 시트가 포함된 엑셀 파일 (.xlsx)", type=["xlsx"])
    
    sheets_dict = {}
    if uploaded_file:
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            for sheet_name in excel_file.sheet_names:
                sheets_dict[sheet_name] = pd.read_excel(uploaded_file, sheet_name=sheet_name)
            st.success(f"총 {len(sheets_dict)}개 북메이커 시트 로드 완료!")
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")
            sheets_dict = load_default_multi_sheets()
    else:
        st.info("기본 8개 북메이커 템플릿 데이터를 사용합니다.")
        sheets_dict = load_default_multi_sheets()

# 5. 메인 대시보드
st.title("⚽ 8개 북메이커 동일 배당 통계 & 승률 분석기")

# 상단 배당 입력기
st.subheader("🎯 분석할 경기 배당 입력")
col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1:
    target_h = st.number_input("홈 승 배당", value=1.22, step=0.01)
with col2:
    target_d = st.number_input("무승부 배당", value=5.10, step=0.01)
with col3:
    target_a = st.number_input("원정 승 배당", value=7.50, step=0.01)
with col4:
    tol = st.number_input("유사 배당 오차(±)", value=0.03, step=0.01)

# 동일 배당 통계 연산
results = []
for bm_name, df in sheets_dict.items():
    if df.empty or '홈배당' not in df.columns or '결과' not in df.columns:
        continue
    
    # 유사 배당 매칭
    matched = df[
        (np.isclose(df['홈배당'].astype(float), target_h, atol=tol)) &
        (np.isclose(df['무배당'].astype(float), target_d, atol=tol)) &
        (np.isclose(df['원정배당'].astype(float), target_a, atol=tol))
    ]
    
    n_count = len(matched)
    if n_count > 0:
        h_win = (matched['결과'].str.contains('승|홈승', na=False)).mean() * 100
        d_win = (matched['결과'].str.contains('무', na=False)).mean() * 100
        a_win = (matched['결과'].str.contains('패|원정승', na=False)).mean() * 100
    else:
        h_win, d_win, a_win = 0.0, 0.0, 0.0
        
    results.append({
        "북메이커": bm_name,
        "매칭 표본(경기수)": n_count,
        "홈승 확률(%)": round(h_win, 1),
        "무승부 확률(%)": round(d_win, 1),
        "원정승 확률(%)": round(a_win, 1)
    })

res_df = pd.DataFrame(results)

# 종합 평균 계산
if not res_df.empty:
    valid_matches = res_df[res_df["매칭 표본(경기수)"] > 0]
    if not valid_matches.empty:
        avg_row = {
            "북메이커": "🔥 [전체 회사 종합 평균]",
            "매칭 표본(경기수)": int(valid_matches["매칭 표본(경기수)"].sum()),
            "홈승 확률(%)": round(valid_matches["홈승 확률(%)"].mean(), 1),
            "무승부 확률(%)": round(valid_matches["무승부 확률(%)"].mean(), 1),
            "원정승 확률(%)": round(valid_matches["원정승 확률(%)"].mean(), 1)
        }
        res_df = pd.concat([res_df, pd.DataFrame([avg_row])], ignore_index=True)

st.markdown("---")
st.subheader("📊 북메이커별 과거 동일 배당 결과 통계")
st.dataframe(res_df, use_container_width=True, hide_index=True)

# 시트별 원본 데이터 열람
with st.expander("🔍 각 북메이커 시트별 원본 데이터 확인"):
    selected_bm = st.selectbox("확인할 북메이커 시트 선택", list(sheets_dict.keys()))
    st.dataframe(sheets_dict[selected_bm], use_container_width=True)
