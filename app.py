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
ADMIN_PASSWORD = "1234"  # 원하는 비밀번호로 변경하세요

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

# 3. 북메이커 목록 정의
DEFAULT_BOOKMAKERS = ["BWIN", "BET365", "PINNACLE", "BETMAN", "WILLIAMHILL", "UNIBET", "1XBET", "BETFAIR"]

# 4. 샘플 데이터 생성 함수
@st.cache_data
def load_default_multi_sheets():
    sample_dict = {}
    sample_rows = [
        {"시즌": "25-26", "리그명": "PL", "날짜": "25.08.16", "홈팀": "리버풀", "원정팀": "본머스", "홈배당": 1.22, "무배당": 5.10, "원정배당": 7.50, "결과": "홈승"},
        {"시즌": "25-26", "리그명": "PL", "날짜": "25.08.16", "홈팀": "아스톤빌라", "원정팀": "뉴캐슬", "홈배당": 1.94, "무배당": 3.45, "원정배당": 2.90, "결과": "무"},
        {"시즌": "24-25", "리그명": "PL", "날짜": "24.11.02", "홈팀": "맨시티", "원정팀": "사우샘프턴", "홈배당": 1.25, "무배당": 5.20, "원정배당": 8.00, "결과": "홈승"},
        {"시즌": "24-25", "리그명": "PL", "날짜": "25.01.10", "홈팀": "아스날", "원정팀": "에버튼", "홈배당": 1.20, "무배당": 5.00, "원정배당": 7.60, "결과": "무"}
    ]
    for bm in DEFAULT_BOOKMAKERS:
        sample_dict[bm] = pd.DataFrame(sample_rows)
    return sample_dict

# 5. 사이드바 - 파일 관리
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
        
    st.markdown("---")
    tol = st.number_input("유사 배당 오차 범위 (±)", value=0.03, step=0.01, help="과거 배당 매칭 시 허용할 오차 범위입니다.")

# 6. 메인 대시보드
st.title("⚽ 북메이커별 개별 배당 입력 & 통합 승률 분석기")

# 회사별 배당 입력 영역 (2열 카드 배치)
st.subheader("🎯 회사별 경기 배당률 입력")
st.caption("각 북메이커 사이트에서 확인한 이번 경기 배당을 개별 입력하세요.")

bookmaker_inputs = {}
active_bms = list(sheets_dict.keys())

# 2열 그리드로 북메이커별 입력창 생성
for i in range(0, len(active_bms), 2):
    c1, c2 = st.columns(2)
    
    # 첫 번째 열
    bm1 = active_bms[i]
    with c1:
        with st.container(border=True):
            st.markdown(f"**🏢 {bm1}**")
            col_h, col_d, col_a = st.columns(3)
            h1 = col_h.number_input(f"홈 승", value=1.22, step=0.01, key=f"{bm1}_h")
            d1 = col_d.number_input(f"무승부", value=5.10, step=0.01, key=f"{bm1}_d")
            a1 = col_a.number_input(f"원정 승", value=7.50, step=0.01, key=f"{bm1}_a")
            bookmaker_inputs[bm1] = (h1, d1, a1)
            
    # 두 번째 열
    if i + 1 < len(active_bms):
        bm2 = active_bms[i + 1]
        with c2:
            with st.container(border=True):
                st.markdown(f"**🏢 {bm2}**")
                col_h, col_d, col_a = st.columns(3)
                h2 = col_h.number_input(f"홈 승", value=1.25, step=0.01, key=f"{bm2}_h")
                d2 = col_d.number_input(f"무승부", value=5.25, step=0.01, key=f"{bm2}_d")
                a2 = col_a.number_input(f"원정 승", value=7.80, step=0.01, key=f"{bm2}_a")
                bookmaker_inputs[bm2] = (h2, d2, a2)

# 7. 회사별 배당 기반 매칭 연산
results = []
for bm_name, df in sheets_dict.items():
    if df.empty or '홈배당' not in df.columns or '결과' not in df.columns:
        continue
    
    target_h, target_d, target_a = bookmaker_inputs.get(bm_name, (1.22, 5.10, 7.50))
    
    # 각 회사별 입력값과 해당 시트 내역 매칭
    matched = df[
        (np.isclose(df['홈배당'].astype(float), target_h, atol=tol)) &
        (np.isclose(df['무배당'].astype(float), target_d, atol=tol)) &
        (np.isclose(df['원정배당'].astype(float), target_a, atol=tol))
    ]
    
    # 마진 환급률 계산
    raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
    payout_rate = (1 / raw_inv) * 100
    
    n_count = len(matched)
    if n_count > 0:
        h_win = (matched['결과'].str.contains('승|홈승', na=False)).mean() * 100
        d_win = (matched['결과'].str.contains('무', na=False)).mean() * 100
        a_win = (matched['결과'].str.contains('패|원정승', na=False)).mean() * 100
    else:
        h_win, d_win, a_win = 0.0, 0.0, 0.0
        
    results.append({
        "북메이커": bm_name,
        "입력 배당 [홈/무/원]": f"{target_h} / {target_d} / {target_a}",
        "환급률(%)": round(payout_rate, 2),
        "과거 매칭(건)": n_count,
        "홈승 확률(%)": round(h_win, 1),
        "무승부 확률(%)": round(d_win, 1),
        "원정승 확률(%)": round(a_win, 1)
    })

res_df = pd.DataFrame(results)

# 종합 평균 행 추가
if not res_df.empty:
    valid_matches = res_df[res_df["과거 매칭(건)"] > 0]
    if not valid_matches.empty:
        avg_row = {
            "북메이커": "🔥 [전체 회사 종합 평균]",
            "입력 배당 [홈/무/원]": "-",
            "환급률(%)": round(res_df["환급률(%)"].mean(), 2),
            "과거 매칭(건)": int(valid_matches["과거 매칭(건)"].sum()),
            "홈승 확률(%)": round(valid_matches["홈승 확률(%)"].mean(), 1),
            "무승부 확률(%)": round(valid_matches["무승부 확률(%)"].mean(), 1),
            "원정승 확률(%)": round(valid_matches["원정승 확률(%)"].mean(), 1)
        }
        res_df = pd.concat([res_df, pd.DataFrame([avg_row])], ignore_index=True)

st.markdown("---")
st.subheader("📊 북메이커별 과거 동일 배당 승률 & 종합 분석 통계")
st.dataframe(res_df, use_container_width=True, hide_index=True)

# 시트별 원본 데이터 확인
with st.expander("🔍 각 북메이커 시트별 원본 데이터베이스 열람"):
    selected_bm = st.selectbox("확인할 북메이커 선택", list(sheets_dict.keys()))
    st.dataframe(sheets_dict[selected_bm], use_container_width=True)
