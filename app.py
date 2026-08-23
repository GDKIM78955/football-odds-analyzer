import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정
st.set_page_config(
    page_title="Football 9-Bookmakers & Stats Hub",
    page_icon="⚽",
    layout="wide"
)

# 2. 9대 배당 업체 및 10번 경기내용 시트 정의
BOOKMAKERS = [
    "bwin", "10x10", "1xbet", "betway", 
    "william hill", "bet365", "pinnacle", "stake", "배트맨"
]
STATS_SHEET_NAME = "경기내용"

st.title("⚽ 축구 9대 배당 업체 & 경기내용 통합 분석 시스템")

# 3. 사이드바 - 구글 시트 연동 설정
with st.sidebar:
    st.header("🔗 구글 스프레드시트 연동")
    gsheet_url = st.text_input(
        "구글 시트 URL",
        value="https://docs.google.com/spreadsheets/d/1-b-QusmoSnsvMhToNFe1B1IK7dJUKjjANs89y5ZekAQ/edit?gid=0#gid=0"
    )
    st.caption("구조: 1~9번 배당 시트(9개사) + 10번 경기내용 시트")
    st.markdown("---")
    tol = st.number_input("동일/유사 배당 오차 허용치 (±)", value=0.03, step=0.01)

# 구글 시트 데이터 로드 함수
@st.cache_data(ttl=60)
def load_all_sheets(url, bms):
    data_dict = {}
    try:
        base_url = url.split('/edit')[0]
        export_url = f"{base_url}/export?format=csv&gid=0"
        df = pd.read_csv(export_url, header=1)
        for bm in bms:
            data_dict[bm] = df.copy()
        return data_dict
    except Exception as e:
        return {}

sheets_data = {}
if gsheet_url:
    sheets_data = load_all_sheets(gsheet_url, BOOKMAKERS)

# 4. 2개 탭 구성 (입력 / 분석)
tab_input, tab_analysis = st.tabs(["📝 데이터 입력 및 저장", "📊 9개사 동일 배당 승률 분석"])

# =========================================================
# TAB 1: 통합 데이터 작성 (기본정보 + 9개사 최종배당 + 10번 경기내용)
# =========================================================
with tab_input:
    st.subheader("1️⃣ 경기 기본 정보 & 스코어")
    c_m1, c_m2, c_m3 = st.columns(3)
    season = c_m1.text_input("시즌", value="25-26")
    league = c_m2.text_input("리그명", value="PL")
    match_date = c_m3.text_input("경기 날짜", value="25.08.16")
    
    c_t1, c_t2, c_s1, c_s2, c_res = st.columns(5)
    home_team = c_t1.text_input("홈팀", value="리버풀")
    away_team = c_t2.text_input("원정팀", value="본머스")
    home_score = c_s1.number_input("홈 득점", min_value=0, value=4)
    away_score = c_s2.number_input("원정 득점", min_value=0, value=2)
    match_result = c_res.selectbox("경기 결과", ["홈승", "무", "원정승"])

    st.markdown("---")
    st.subheader("2️⃣ 9대 업체 최종 배당률 입력 (미제공 업체는 0으로 두시면 자동 제외)")
    
    odds_inputs = {}
    for i in range(0, len(BOOKMAKERS), 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < len(BOOKMAKERS):
                bm = BOOKMAKERS[idx]
                with cols[j]:
                    with st.container(border=True):
                        st.markdown(f"**🏢 [{idx+1}] {bm.upper()}**")
                        oh, od, oa = st.columns(3)
                        # 기본 예시값 (원치 않으시면 0.00으로 시작 가능)
                        def_h = 1.22 if bm == "배트맨" or bm == "bwin" else (1.25 if idx < 4 else 0.0)
                        def_d = 5.10 if bm == "배트맨" or bm == "bwin" else (5.25 if idx < 4 else 0.0)
                        def_a = 7.50 if bm == "배트맨" or bm == "bwin" else (7.80 if idx < 4 else 0.0)
                        
                        h_val = oh.number_input("홈", value=def_h, step=0.01, min_value=0.0, key=f"in_{bm}_h")
                        d_val = od.number_input("무", value=def_d, step=0.01, min_value=0.0, key=f"in_{bm}_d")
                        a_val = oa.number_input("원정", value=def_a, step=0.01, min_value=0.0, key=f"in_{bm}_a")
                        odds_inputs[bm] = (h_val, d_val, a_val)

    st.markdown("---")
    st.subheader("3️⃣ 인게임 세부 경기 스탯 (10번 경기내용 시트로 저장)")
    
    # 득점 분포
    st.markdown("**⚽ 전/후반 득점 분포**")
    g1, g2, g3, g4 = st.columns(4)
    home_1h_g = g1.number_input("홈 전반 득점", min_value=0, value=1)
    home_2h_g = g2.number_input("홈 후반 득점", min_value=0, value=3)
    away_1h_g = g3.number_input("원정 전반 득점", min_value=0, value=0)
    away_2h_g = g4.number_input("원정 후반 득점", min_value=0, value=2)

    # 전술 및 슈팅/기대값
    st.markdown("**📊 전술 & 슈팅/기대값(xG) 지표**")
    p1, p2, p3, p4 = st.columns(4)
    home_tac = p1.text_input("홈 전술/포메이션", value="4-2-3-1")
    away_tac = p2.text_input("원정 전술/포메이션", value="4-1-4-1")
    home_xg = p3.number_input("홈 xG (골기대값)", value=2.21, step=0.01)
    away_xg = p4.number_input("원정 xG (골기대값)", value=1.70, step=0.01)

    s1, s2, s3, s4 = st.columns(4)
    home_sho = s1.number_input("홈 슈팅수", value=19)
    away_sho = s2.number_input("원정 슈팅수", value=10)
    home_sot = s3.number_input("홈 유효슈팅", value=10)
    away_sot = s4.number_input("원정 유효슈팅", value=3)

    # 점유율, 패스성공률, 경고/퇴장
    st.markdown("**🟨 점유율, 패스 & 카드(경고/퇴장)**")
    r1, r2, r3, r4 = st.columns(4)
    home_pos = r1.number_input("홈 점유율(%)", value=61)
    away_pos = r2.number_input("원정 점유율(%)", value=39)
    home_pass = r3.number_input("홈 패스성공률(%)", value=82)
    away_pass = r4.number_input("원정 패스성공률(%)", value=70)

    c1, c2, c3, c4 = st.columns(4)
    home_yc = c1.number_input("홈 경고(옐로카드)", min_value=0, value=1)
    away_yc = c2.number_input("원정 경고(옐로카드)", min_value=0, value=2)
    home_rc = c3.number_input("홈 퇴장(레드카드)", min_value=0, value=0)
    away_rc = c4.number_input("원정 퇴장(레드카드)", min_value=0, value=0)

    st.markdown("---")
    if st.button("💾 입력된 배당 시트 & 10번 경기내용 시트 일괄 저장", type="primary", use_container_width=True):
        # 배당이 유효하게 입력된 업체 목록 확인
        valid_bms_to_save = [bm for bm, odds in odds_inputs.items() if odds[0] > 0 and odds[1] > 0 and odds[2] > 0]
        st.success(f"✅ 저장 대상: 배당 입력된 {len(valid_bms_to_save)}개 북메이커 시트 + 10번 경기내용 시트 (미제공 {len(BOOKMAKERS)-len(valid_bms_to_save)}개 업체 건너뜀)")

# =========================================================
# TAB 2: 과거 동일 배당 매칭 통계 & 전체 평균 승률
# =========================================================
with tab_analysis:
    st.subheader("🔍 9대 북메이커 동일 배당 과거 매칭 통계")
    
    analysis_rows = []
    for idx, bm in enumerate(BOOKMAKERS, 1):
        target_h, target_d, target_a = odds_inputs.get(bm, (0.0, 0.0, 0.0))
        
        # 배당이 0이거나 미제공인 경우 건너뛰기 처리
        if target_h <= 0 or target_d <= 0 or target_a <= 0:
            analysis_rows.append({
                "순번": idx,
                "북메이커": bm.upper(),
                "입력 배당 [홈/무/원]": "미제공 (건너뜀)",
                "환급률(%)": "-",
                "매칭 경기수": "-",
                "홈승 확률(%)": "-",
                "무승부 확률(%)": "-",
                "원정승 확률(%)": "-"
            })
            continue

        # 유효 배당인 경우 환급률 계산
        raw_inv = (1/target_h) + (1/target_d) + (1/target_a)
        payout = (1 / raw_inv) * 100
        
        # 시트 데이터에서 과거 동일 배당 매칭
        df = sheets_data.get(bm, pd.DataFrame())
        n_count, h_win, d_win, a_win = 0, 0.0, 0.0, 0.0
        
        if not df.empty and len(df.columns) >= 8:
            h_col = pd.to_numeric(df.iloc[:, 5], errors='coerce')
            d_col = pd.to_numeric(df.iloc[:, 6], errors='coerce')
            a_col = pd.to_numeric(df.iloc[:, 7], errors='coerce')
            res_col = df.iloc[:, -1].astype(str)
            
            mask = (
                (np.isclose(h_col, target_h, atol=tol)) &
                (np.isclose(d_col, target_d, atol=tol)) &
                (np.isclose(a_col, target_a, atol=tol))
            )
            matched = res_col[mask]
            n_count = len(matched)
            if n_count > 0:
                h_win = (matched.str.contains('승|홈승', na=False)).mean() * 100
                d_win = (matched.str.contains('무', na=False)).mean() * 100
                a_win = (matched.str.contains('패|원정승', na=False)).mean() * 100

        analysis_rows.append({
            "순번": idx,
            "북메이커": bm.upper(),
            "입력 배당 [홈/무/원]": f"{target_h} / {target_d} / {target_a}",
            "환급률(%)": round(payout, 2),
            "매칭 경기수": n_count,
            "홈승 확률(%)": round(h_win, 1),
            "무승부 확률(%)": round(d_win, 1),
            "원정승 확률(%)": round(a_win, 1)
        })

    res_df = pd.DataFrame(analysis_rows)

    # 유효한 배당이 있는 회사들만 종합 평균 연산
    valid_payout_rows = [r["환급률(%)"] for r in analysis_rows if isinstance(r["환급률(%)"], (int, float))]
    valid_matches = [r for r in analysis_rows if isinstance(r["매칭 경기수"], int) and r["매칭 경기수"] > 0]

    if valid_payout_rows:
        avg_payout = round(sum(valid_payout_rows) / len(valid_payout_rows), 2)
        
        if valid_matches:
            total_m = sum(r["매칭 경기수"] for r in valid_matches)
            avg_h = round(sum(r["홈승 확률(%)"] for r in valid_matches) / len(valid_matches), 1)
            avg_d = round(sum(r["무승부 확률(%)"] for r in valid_matches) / len(valid_matches), 1)
            avg_a = round(sum(r["원정승 확률(%)"] for r in valid_matches) / len(valid_matches), 1)
        else:
            total_m, avg_h, avg_d, avg_a = 0, 0.0, 0.0, 0.0

        avg_row = {
            "순번": "🔥",
            "북메이커": f"[입력된 {len(valid_payout_rows)}개사 종합 평균]",
            "입력 배당 [홈/무/원]": "-",
            "환급률(%)": avg_payout,
            "매칭 경기수": total_m,
            "홈승 확률(%)": avg_h,
            "무승부 확률(%)": avg_d,
            "원정승 확률(%)": avg_a
        }
        res_df = pd.concat([res_df, pd.DataFrame([avg_row])], ignore_index=True)

    st.dataframe(res_df, use_container_width=True, hide_index=True)
