import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정
st.set_page_config(
    page_title="Football Multi-Bookmaker Analytics",
    page_icon="⚽",
    layout="wide"
)

# 2. 비공개 로그인
ADMIN_PASSWORD = "1234"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("## 🔒 축구 배당/스탯 실시간 연동 분석기")
    st.info("관리자 전용 대시보드입니다. 비밀번호를 입력해주세요.")
    pwd = st.text_input("접속 비밀번호", type="password")
    if st.button("로그인"):
        if pwd == ADMIN_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

# 3. 구글 시트 실시간 로드 함수 (시트 구조 자동 보정)
@st.cache_data(ttl=60)
def load_google_sheets_data(sheet_url, sheet_names):
    sheets_dict = {}
    try:
        # 구글 시트 기본 URL 파싱
        base_url = sheet_url.split('/edit')[0]
        
        # 첫 번째 시트 gid=0 로드 (헤더가 3행에 위치하므로 header=2 적용)
        export_url = f"{base_url}/export?format=csv&gid=0"
        raw_df = pd.read_csv(export_url, header=2)
        
        for name in sheet_names:
            sheets_dict[name] = raw_df.copy()
            
        return sheets_dict
    except Exception as e:
        st.sidebar.error(f"구글 시트 로드 실패: {e}")
        return {}

# 4. 사이드바 설정
with st.sidebar:
    st.header("🔗 구글 시트 연동 설정")
    gsheet_url = st.text_input("구글 시트 URL", value="")
    
    tabs_input = st.text_input(
        "사용할 북메이커 탭 목록 (콤마 구분)", 
        value="BWIN, BET365, PINNACLE, BETMAN, WILLIAMHILL, UNIBET, 1XBET, BETFAIR"
    )
    tol = st.number_input("유사 배당 오차 범위 (±)", value=0.03, step=0.01)

active_bms = [x.strip() for x in tabs_input.split(",") if x.strip()]
sheets_dict = {}

if gsheet_url and active_bms:
    with st.spinner("구글 시트 데이터를 실시간으로 가져오는 중..."):
        sheets_dict = load_google_sheets_data(gsheet_url, active_bms)

# 5. 메인 대시보드
st.title("⚽ 북메이커별 개별 배당 입력 & 통합 승률 분석기")

if not sheets_dict:
    st.info("👈 사이드바에 구글 시트 URL을 입력하고 권한('링크가 있는 모든 사용자')을 확인해 주세요.")
else:
    st.subheader("🎯 북메이커별 경기 배당률 입력")
    
    bookmaker_inputs = {}
    
    # 2열 카드로 북메이커별 입력창 생성
    for i in range(0, len(active_bms), 2):
        c1, c2 = st.columns(2)
        
        bm1 = active_bms[i]
        with c1:
            with st.container(border=True):
                st.markdown(f"**🏢 {bm1}**")
                ch1, cd1, ca1 = st.columns(3)
                h1 = ch1.number_input("홈 승", value=1.22, step=0.01, key=f"{bm1}_h")
                d1 = cd1.number_input("무승부", value=5.10, step=0.01, key=f"{bm1}_d")
                a1 = ca1.number_input("원정 승", value=7.50, step=0.01, key=f"{bm1}_a")
                bookmaker_inputs[bm1] = (h1, d1, a1)
                
        if i + 1 < len(active_bms):
            bm2 = active_bms[i + 1]
            with c2:
                with st.container(border=True):
                    st.markdown(f"**🏢 {bm2}**")
                    ch2, cd2, ca2 = st.columns(3)
                    h2 = ch2.number_input("홈 승", value=1.25, step=0.01, key=f"{bm2}_h")
                    d2 = cd2.number_input("무승부", value=5.25, step=0.01, key=f"{bm2}_d")
                    a2 = ca2.number_input("원정 승", value=7.80, step=0.01, key=f"{bm2}_a")
                    bookmaker_inputs[bm2] = (h2, d2, a2)

    # 6. 통계 연산 (열 위치 기반 자동 매핑)
    results = []
    for bm_name, df in sheets_dict.items():
        if df.empty or len(df.columns) < 8:
            continue
        
        # 6, 7, 8번째 열을 [홈배당, 무배당, 원정배당]으로 자동 지정
        h_odds_col = pd.to_numeric(df.iloc[:, 5], errors='coerce')
        d_odds_col = pd.to_numeric(df.iloc[:, 6], errors='coerce')
        a_odds_col = pd.to_numeric(df.iloc[:, 7], errors='coerce')
        
        # 경기결과 열 찾기 (마지막 열 또는 '결과' 포함 열)
        res_series = df.iloc[:, -1].astype(str)
        
        target_h, target_d, target_a = bookmaker_inputs.get(bm_name, (1.22, 5.10, 7.50))
        
        # 유사 배당 조건 매칭
        mask = (
            (np.isclose(h_odds_col, target_h, atol=tol)) &
            (np.isclose(d_odds_col, target_d, atol=tol)) &
            (np.isclose(a_odds_col, target_a, atol=tol))
        )
        
        matched_results = res_series[mask]
        n_count = len(matched_results)
        
        if n_count > 0:
            h_win = (matched_results.str.contains('승|홈승', na=False)).mean() * 100
            d_win = (matched_results.str.contains('무', na=False)).mean() * 100
            a_win = (matched_results.str.contains('패|원정승', na=False)).mean() * 100
        else:
            h_win, d_win, a_win = 0.0, 0.0, 0.0
            
        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout_rate = (1 / raw_inv) * 100
        
        results.append({
            "북메이커": bm_name,
            "입력 배당": f"{target_h} / {target_d} / {target_a}",
            "환급률(%)": round(payout_rate, 2),
            "과거 매칭(건)": n_count,
            "홈승 확률(%)": round(h_win, 1),
            "무승부 확률(%)": round(d_win, 1),
            "원정승 확률(%)": round(a_win, 1)
        })

    res_df = pd.DataFrame(results)

    # 7. 전체 종합 평균 계산
    if not res_df.empty:
        valid = res_df[res_df["과거 매칭(건)"] > 0]
        if not valid.empty:
            avg_row = {
                "북메이커": "🔥 [전체 회사 종합 평균]",
                "입력 배당": "-",
                "환급률(%)": round(res_df["환급률(%)"].mean(), 2),
                "과거 매칭(건)": int(valid["과거 매칭(건)"].sum()),
                "홈승 확률(%)": round(valid["홈승 확률(%)"].mean(), 1),
                "무승부 확률(%)": round(valid["무승부 확률(%)"].mean(), 1),
                "원정승 확률(%)": round(valid["원정승 확률(%)"].mean(), 1)
            }
            res_df = pd.concat([res_df, pd.DataFrame([avg_row])], ignore_index=True)

    st.markdown("---")
    st.subheader("📊 북메이커별 과거 동일 배당 승률 & 종합 분석 통계")
    st.dataframe(res_df, use_container_width=True, hide_index=True)
    
    with st.expander("🔍 시트 데이터 원본 미리보기"):
        st.dataframe(list(sheets_dict.values())[0].head(10), use_container_width=True)
