import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정
st.set_page_config(
    page_title="Real-time Football Analytics",
    page_icon="⚽",
    layout="wide"
)

# 2. 비공개 로그인
ADMIN_PASSWORD = "1234"  # 원하는 비밀번호로 변경하세요

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

# 3. 구글 시트 다중 탭 실시간 로드 함수
@st.cache_data(ttl=60) # 60초마다 데이터 새로고침
def load_google_sheets(sheet_url, sheet_names):
    sheets_dict = {}
    try:
        # 구글 시트 URL을 CSV 다운로드 포맷으로 변환
        csv_export_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv&gid=')
        
        # 첫 번째 시트 (gid=0) 로드 테스트
        first_sheet = pd.read_csv(csv_export_url + "0")
        
        # 사용자가 지정한 시트 이름 목록에 따라 데이터 프레임 생성 (여기서는 구조상 편의를 위해 시뮬레이션)
        # 참고: 구글 시트 URL만으로는 모든 탭 이름을 자동으로 알기 어려워, 사용할 북메이커 탭 이름을 수동 기재합니다.
        for name in sheet_names:
            # 실제 배포 환경에서는 gid 매핑 또는 gspread 라이브러리가 필요할 수 있습니다.
            # 이 코드는 단일 시트 데이터(또는 첫 번째 탭)를 복제하여 템플릿 테스트용으로 작동합니다.
            sheets_dict[name] = first_sheet.copy() 
            
        return sheets_dict
    except Exception as e:
        return {"Error": pd.DataFrame()}

# 4. 사이드바 - 실시간 구글 시트 연결
with st.sidebar:
    st.header("🔗 구글 시트 실시간 연동")
    st.caption("'링크가 있는 모든 사용자가 볼 수 있음'으로 설정된 구글 시트 URL을 입력하세요.")
    
    gsheet_url = st.text_input("구글 시트 URL 입력", value="")
    
    # 사용할 북메이커 시트(탭) 이름 지정
    st.markdown("---")
    st.markdown("**사용할 북메이커 탭 이름 (콤마로 구분)**")
    tabs_input = st.text_input("예: BWIN, BET365, BETMAN", value="BWIN, BET365, PINNACLE, BETMAN")
    
    tol = st.number_input("유사 배당 오차 범위 (±)", value=0.03, step=0.01)

# 데이터 로드 실행
active_bms = [x.strip() for x in tabs_input.split(",") if x.strip()]
sheets_dict = {}

if gsheet_url and active_bms:
    with st.spinner("구글 시트 데이터를 실시간으로 가져오는 중..."):
        sheets_dict = load_google_sheets(gsheet_url, active_bms)
        if "Error" in sheets_dict:
            st.error("구글 시트를 불러오지 못했습니다. URL과 공유 설정을 확인해 주세요.")
            sheets_dict = {}
        else:
            st.success(f"{len(sheets_dict)}개 회사 데이터 실시간 로드 완료!")

# 5. 메인 대시보드
st.title("⚽ 북메이커별 개별 배당 입력 & 통합 승률 분석기")
st.subheader("🎯 회사별 경기 배당률 입력")

bookmaker_inputs = {}

if not sheets_dict:
    st.info("👈 사이드바에 구글 시트 URL을 입력하면 분석이 시작됩니다.")
else:
    # 2열 그리드로 북메이커별 입력창 생성
    for i in range(0, len(active_bms), 2):
        c1, c2 = st.columns(2)
        
        bm1 = active_bms[i]
        with c1:
            with st.container(border=True):
                st.markdown(f"**🏢 {bm1}**")
                col_h, col_d, col_a = st.columns(3)
                h1 = col_h.number_input(f"홈 승", value=1.22, step=0.01, key=f"{bm1}_h")
                d1 = col_d.number_input(f"무승부", value=5.10, step=0.01, key=f"{bm1}_d")
                a1 = col_a.number_input(f"원정 승", value=7.50, step=0.01, key=f"{bm1}_a")
                bookmaker_inputs[bm1] = (h1, d1, a1)
                
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

    # 6. 회사별 배당 기반 매칭 연산
    results = []
    for bm_name, df in sheets_dict.items():
        if df.empty or '홈배당' not in df.columns or '결과' not in df.columns:
            continue
        
        target_h, target_d, target_a = bookmaker_inputs.get(bm_name, (1.22, 5.10, 7.50))
        
        matched = df[
            (np.isclose(pd.to_numeric(df['홈배당'], errors='coerce'), target_h, atol=tol)) &
            (np.isclose(pd.to_numeric(df['무배당'], errors='coerce'), target_d, atol=tol)) &
            (np.isclose(pd.to_numeric(df['원정배당'], errors='coerce'), target_a, atol=tol))
        ]
        
        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout_rate = (1 / raw_inv) * 100
        n_count = len(matched)
        
        if n_count > 0:
            h_win = (matched['결과'].astype(str).str.contains('승|홈승', na=False)).mean() * 100
            d_win = (matched['결과'].astype(str).str.contains('무', na=False)).mean() * 100
            a_win = (matched['결과'].astype(str).str.contains('패|원정승', na=False)).mean() * 100
        else:
            h_win, d_win, a_win = 0.0, 0.0, 0.0
            
        results.append({
            "북메이커": bm_name,
            "입력 배당": f"{target_h} / {target_d} / {target_a}",
            "환급률(%)": round(payout_rate, 2),
            "매칭 경기수": n_count,
            "홈승 확률(%)": round(h_win, 1),
            "무승부 확률(%)": round(d_win, 1),
            "원정승 확률(%)": round(a_win, 1)
        })

    res_df = pd.DataFrame(results)

    # 종합 평균
    if not res_df.empty:
        valid_matches = res_df[res_df["매칭 경기수"] > 0]
        if not valid_matches.empty:
            avg_row = {
                "북메이커": "🔥 [전체 회사 종합 평균]",
                "입력 배당": "-",
                "환급률(%)": round(res_df["환급률(%)"].mean(), 2),
                "매칭 경기수": int(valid_matches["매칭 경기수"].sum()),
                "홈승 확률(%)": round(valid_matches["홈승 확률(%)"].mean(), 1),
                "무승부 확률(%)": round(valid_matches["무승부 확률(%)"].mean(), 1),
                "원정승 확률(%)": round(valid_matches["원정승 확률(%)"].mean(), 1)
            }
            res_df = pd.concat([res_df, pd.DataFrame([avg_row])], ignore_index=True)

    st.markdown("---")
    st.subheader("📊 북메이커별 과거 동일 배당 승률 & 종합 분석 통계")
    st.dataframe(res_df, use_container_width=True, hide_index=True)
