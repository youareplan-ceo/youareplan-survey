import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="유아플랜 통합 대시보드", 
    page_icon="📊", 
    layout="wide"
)

st.title("📊 유아플랜 정책자금 컨설팅 - 통합 대시보드")
st.markdown("**실시간 현황 모니터링**")

# 샘플 데이터 (실제로는 Google Sheets에서 가져옴)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📝 1차 신청", "152", "12")
with col2:  
    st.metric("🔄 2차 진행", "87", "8")
with col3:
    st.metric("📋 3차 완료", "34", "5")
with col4:
    st.metric("✅ 계약 성사", "23", "3")

st.success("✅ 통합 대시보드가 성공적으로 실행되었습니다!")
