import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import os
import base64
import google.generativeai as genai

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(
    page_title="유아플랜 통합 관리 대시보드",
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
INTEGRATED_GAS_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

# ==============================
# [NEW] 재무 비율 자동 계산 함수
# ==============================
def calculate_financial_metrics(s2: Dict) -> Dict:
    """매출, 자본, 부채 정보를 받아 성장률과 부채비율을 계산"""
    metrics = {
        "debt_ratio": "-", "debt_status": "gray", "debt_msg": "데이터 없음",
        "growth_rate": "-", "growth_status": "gray", "growth_msg": "데이터 없음"
    }
    
    try:
        # 부채비율
        capital = int(str(s2.get('capital_amount', '0')).replace(',', '').replace('만원', ''))
        debt = int(str(s2.get('debt_amount', '0')).replace(',', '').replace('만원', ''))
        if capital > 0:
            ratio = round((debt / capital) * 100)
            metrics['debt_ratio'] = f"{ratio}%"
            if ratio > 400: metrics.update({"debt_status": "red", "debt_msg": "⛔ 위험 (400% 초과)"})
            elif ratio > 200: metrics.update({"debt_status": "orange", "debt_msg": "⚠️ 주의 (200% 초과)"})
            else: metrics.update({"debt_status": "green", "debt_msg": "✅ 양호"})
    except: pass

    try:
        # 매출성장률 (전년 대비)
        rev_prev = int(str(s2.get('revenue_y2', '0')).replace(',', ''))
        rev_curr = int(str(s2.get('revenue_y1', '0')).replace(',', '')) # 올해 예상 or 작년 확정
        if rev_prev > 0:
            growth = round(((rev_curr - rev_prev) / rev_prev) * 100)
            sign = "+" if growth > 0 else ""
            metrics['growth_rate'] = f"{sign}{growth}%"
            if growth >= 20: metrics.update({"growth_status": "blue", "growth_msg": "🚀 고성장"})
            elif growth > 0: metrics.update({"growth_status": "green", "growth_msg": "📈 성장 중"})
            else: metrics.update({"growth_status": "red", "growth_msg": "📉 감소/정체"})
    except: pass
    
    return metrics

# ==============================
# 리포트 생성 함수
# ==============================
def generate_full_report(data: Dict[str, Any]) -> str:
    s1, s2, s3 = data.get("stage1", {}), data.get("stage2", {}), data.get("stage3", {})
    metrics = calculate_financial_metrics(s2)
    
    return f"""
==================================================
[유아플랜] 통합 고객 상담 리포트
==================================================
* 접수번호: {data.get('receipt_no', '-')}
* 작성일시: {datetime.now().strftime("%Y-%m-%d %H:%M")}

[1] 기업 개요 (1차)
--------------------------------------------------
* 기업명/성함: {s1.get('name', '-')}
* 연락처: {s1.get('phone', '-')}
* 업종/지역: {s1.get('industry', '-')} / {s1.get('region', '-')}
* 직원수: {s1.get('employee_count', '-')}
* 리스크: 국세({s1.get('tax_status', '-')}), 신용({s1.get('credit_status', '-')})

[2] 재무 분석 (2차 + 자동계산)
--------------------------------------------------
* 설립일: {s2.get('startup_date', '-')}
* 매출추이: {s2.get('revenue_y2', '-')} -> {s2.get('revenue_y1', '-')} (만원)
* 성장률: {metrics['growth_rate']} ({metrics['growth_msg']})
* 자본/부채: {s2.get('capital_amount', '-')} / {s2.get('debt_amount', '-')} (만원)
* 부채비율: {metrics['debt_ratio']} ({metrics['debt_msg']})
* 가점사항: {s2.get('official_certs', '-')}

[3] 심층 분석 (3차)
--------------------------------------------------
* 담보계획: {s3.get('collateral_profile', '-')}
* 컨설턴트 의견:
{s3.get('coach_notes', '-')}

==================================================
""".strip()

# ==============================
# 통신 및 유틸
# ==============================
def analyze_with_gemini(api_key: str, data: Dict[str, Any]) -> str:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = generate_ai_prompt(data)
        with st.spinner("🤖 Gemini가 분석 중..."):
            return model.generate_content(prompt).text
    except Exception as e: return f"⚠️ 오류: {str(e)}"

def generate_ai_prompt(data: Dict[str, Any]) -> str:
    s1, s2, s3 = data.get("stage1", {}), data.get("stage2", {}), data.get("stage3", {})
    metrics = calculate_financial_metrics(s2)
    return f"""
# 기업 정책자금 분석 요청
- 업종: {s1.get('industry')} / 설립: {s2.get('startup_date')}
- 매출: {s2.get('revenue_y2')} -> {s2.get('revenue_y1')} (성장률 {metrics['growth_rate']})
- 부채비율: {metrics['debt_ratio']} ({metrics['debt_msg']})
- 리스크: {s1.get('tax_status')}, {s1.get('credit_status')}
- 의견: {s3.get('coach_notes')}
## 요청: 추천 자금 및 승인 전략
""".strip()

def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    try:
        payload = { "action": "get_integrated_view", "receipt_no": receipt_no, "api_token": API_TOKEN }
        res = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        return res.json() if res.status_code == 200 else {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e: return {"status": "error", "message": str(e)}

def save_final_result(receipt_no, p_name, p_amt, p_memo):
    try:
        payload = { "action": "save_final_result", "receipt_no": receipt_no, "policy_name": p_name, "approved_amount": p_amt, "memo": p_memo, "api_token": API_TOKEN }
        requests.post(INTEGRATED_GAS_URL, json=payload, timeout=15)
        return {"status": "success"}
    except Exception as e: return {"status": "error", "message": str(e)}

def create_download_link(text: str, filename: str) -> str:
    b64 = base64.b64encode(text.encode()).decode()
    return f'<a href="data:text/plain;base64,{b64}" download="{filename}" style="display:inline-block; background:#10B981; color:white; padding:10px 20px; border-radius:8px; font-weight:bold; text-decoration:none; box-shadow:0 2px 5px rgba(0,0,0,0.1);">📥 통합 리포트 다운로드 (.txt)</a>'

# ==============================
# CSS
# ==============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
#MainMenu, footer, header { display: none !important; }

.unified-header {
    background: #002855; padding: 24px 30px; border-radius: 0 0 15px 15px;
    margin: -4rem -4rem 24px -4rem; color: white; display: flex; justify-content: space-between; align-items: center;
}
.header-left { display: flex; align-items: center; gap: 15px; }
.header-left img { height: 45px; }
.header-left h1 { margin: 0; font-size: 24px; font-weight: 700; color: white; }

.metric-card {
    background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.metric-label { font-size: 13px; color: #6b7280; margin-bottom: 4px; font-weight: 600; }
.metric-value { font-size: 24px; font-weight: 800; color: #111827; }
.metric-sub { font-size: 12px; margin-top: 4px; }

/* 다크모드 */
@media (prefers-color-scheme: dark) {
    .metric-card { background: #1f2937; border-color: #374151; }
    .metric-value { color: #f3f4f6; }
    .metric-label { color: #9ca3af; }
}
</style>
""", unsafe_allow_html=True)

# ==============================
# 메인
# ==============================
def main():
    st.markdown(f"""<div class="unified-header"><div class="header-left"><img src="{LOGO_URL}" alt="Logo"><h1>통합 고객 관리</h1></div><div style="font-size:12px; opacity:0.8;">Admin Mode</div></div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ 설정")
        gemini_api_key = st.text_input("Gemini API Key", type="password")

    with st.container():
        c1, c2 = st.columns([4, 1])
        with c1: receipt_no = st.text_input("접수번호 입력", placeholder="예: YP202511271234", label_visibility="collapsed")
        with c2: search_btn = st.button("🔍 데이터 조회", type="primary", use_container_width=True)

    if search_btn and receipt_no:
        with st.spinner("데이터 통합 조회 및 재무 분석 중..."):
            result = fetch_integrated_data(receipt_no.strip())
        
        if result.get("status") == "success":
            data = result.get("data", {})
            s1, s2, s3 = data.get("stage1", {}), data.get("stage2", {}), data.get("stage3", {})
            metrics = calculate_financial_metrics(s2)
            
            # [1] 헤더 요약 및 다운로드
            st.markdown("### 📊 고객 핵심 요약")
            top_c1, top_c2 = st.columns([3, 1])
            with top_c1:
                st.markdown(f"**{s1.get('name', '-')}** ({s1.get('industry', '-')}) / 필요자금: **{s1.get('funding_amount', '-')}**")
            with top_c2:
                full_report = generate_full_report(data)
                fname = f"유아플랜_{s1.get('name', '고객')}_통합리포트.txt"
                st.markdown(create_download_link(full_report, fname), unsafe_allow_html=True)

            # [2] 자동 재무 분석 카드
            m1, m2, m3 = st.columns(3)
            with m1:
                color = metrics['debt_status']
                st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid {color};">
                    <div class="metric-label">📉 부채비율 (자동계산)</div>
                    <div class="metric-value" style="color:{color}">{metrics['debt_ratio']}</div>
                    <div class="metric-sub" style="color:{color}">{metrics['debt_msg']}</div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                color = metrics['growth_status']
                st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid {color};">
                    <div class="metric-label">📈 매출 성장률</div>
                    <div class="metric-value" style="color:{color}">{metrics['growth_rate']}</div>
                    <div class="metric-sub" style="color:{color}">{metrics['growth_msg']}</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                risk_color = "red" if s1.get('tax_status') != '체납 없음' else "green"
                risk_msg = "체납/연체 확인" if risk_color == "red" else "양호"
                st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid {risk_color};">
                    <div class="metric-label">🛡️ 리스크 체크</div>
                    <div class="metric-value" style="color:{risk_color}">{risk_msg}</div>
                    <div class="metric-sub">{s1.get('tax_status', '-')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")

            # [3] 탭 상세 보기
            st.subheader("📑 설문 상세 데이터 (검증용)")
            t1, t2, t3 = st.tabs(["1️⃣ 1차: 기초/자격", "2️⃣ 2차: 재무/사업", "3️⃣ 3차: 심층/담보"])
            
            with t1:
                c1, c2 = st.columns(2)
                with c1: st.info(f"**연락처**: {s1.get('phone')}\n\n**매출**: {s1.get('revenue')}")
                with c2: st.warning(f"**체납**: {s1.get('tax_status')}\n\n**연체**: {s1.get('credit_status')}")
            
            with t2:
                c1, c2 = st.columns(2)
                with c1: st.info(f"**설립일**: {s2.get('startup_date')}\n\n**인증**: {s2.get('official_certs')}")
                with c2: st.success(f"**매출추이**: {s2.get('revenue_y2')} -> {s2.get('revenue_y1')} (만원)")

            with t3:
                st.info(f"**담보계획**: {s3.get('collateral_profile')}")
                st.caption(f"**컨설턴트 메모**: {s3.get('coach_notes')}")

            # [4] AI 분석
            st.markdown("---")
            st.subheader("🤖 AI 정책자금 매칭 분석")
            if st.button("🚀 Gemini 분석 실행", type="primary", use_container_width=True):
                if not gemini_api_key: st.error("API 키 필요")
                else:
                    res = analyze_with_gemini(gemini_api_key, data)
                    st.success("분석 완료!")
                    st.markdown(res)

            # [5] 저장
            st.markdown("---")
            with st.expander("✅ 최종 승인 결과 기록"):
                with st.form("res_form"):
                    c1, c2 = st.columns(2)
                    if st.form_submit_button("저장"):
                        save_final_result(receipt_no, c1.text_input("자금명"), c2.text_input("금액"), st.text_area("메모"))
                        st.success("저장되었습니다.")
        else:
            st.error(f"조회 실패: {result.get('message')}")
    elif search_btn: st.warning("접수번호 입력")

if __name__ == "__main__":
    main()