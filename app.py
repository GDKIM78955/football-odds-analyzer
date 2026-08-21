import streamlit as st
import pandas as pd
import numpy as np

# 1. 페이지 설정 (와이드 모드, 기본 타이틀)
st.set_page_config(
    page_title="Football Odds Analyzer",
    page_icon="⚽",
    layout="wide"
)

# 2. 메인 타이틀 및 기본 레이아웃
st.title("⚽ 축구 배당 & 데이터 분석 시스템")
st.caption("초기화 완료: 원하는 데이터 소스와 분석 항목을 순서대로 구축해 나갈 수 있습니다.")

st.markdown("---")

# 3. 사이드바 기본 설정 영역
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.info("비밀번호 잠금이 해제되었습니다. 자유롭게 접속 가능합니다.")

# 4. 초기 메인 화면 플레이스홀더
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("시스템 상태", "정상 작동 중", delta="Ready")
with col2:
    st.metric("데이터 연동", "대기 중", delta="Waiting")
with col3:
    st.metric("분석 모듈", "초기화 완료", delta="Reset")

st.markdown("---")
st.info("💡 이제 어떤 기능(데이터 연동 방식, 시트 구조, 배당 분석 로직 등)부터 먼저 올릴지 말씀해 주세요!")
