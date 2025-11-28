import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import os
import base64
import google.generativeai as genai

# ==============================
# 1. 페이지 설정
# ==============================
st.set_page_config(
    page_title="유아플랜 통합 관리 대시보드",
    page_icon="💼", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# 2. 환경 설정 & 로고
# ==============================
BRAND_NAME = "유아플랜"
# 실제 로고 URL 사용
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
INTEGRATED_GAS_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

# ==============================
# 3. 재무 지표 계산 함수
# ==============================
def calculate_financial_metrics(s2: Dict) -> Dict:
    metrics = {
        "debt_ratio": "-", "debt_status": "gray",
        "growth_rate": "-", "growth_status": "gray"
    }
    
    if not s2: return metrics

    try:
        # 부채비율 계산
        capital = int(str(s2.get('capital_amount', '0')).replace(',', '').replace('만원', ''))
        debt = int(str(s2.get('debt_amount', '0')).replace(',', '').replace('만원', ''))
        if capital > 0:
            ratio = round((debt / capital) * 100)
            metrics['debt_ratio'] = f"{ratio}%"
            if ratio > 400: metrics['debt_status'] = "red"
            elif ratio > 200: metrics['debt_status'] = "orange"
            else: metrics['debt_status'] = "green"
    except: pass

    try:
        # 매출성장률 계산
        rev_prev = int(str(s2.get('revenue_y2', '0')).replace(',', ''))
        rev_curr = int(str(s2.get('revenue_y1', '0')).replace(',', '')) 
        if rev_prev > 0:
            growth = round(((rev_curr - rev_prev) / rev_prev) * 100)
            sign = "+" if growth > 0 else ""
            metrics['growth_rate'] = f"{sign}{growth}%"
            if growth >= 20: metrics['growth_status'] = "blue"
            elif growth > 0: metrics['growth_status'] = "green"
            else: metrics['growth_status'] = "red"
    except: pass
    
    return metrics

# ==============================
# 4. 리포트 텍스트 생성
# ==============================
def generate_full_report(data: Dict[str, Any], ai_result: str = "", mode: str = "contract") -> str:
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    metrics = calculate_financial_metrics(s2)
    
    title = "컨설팅 계약 제안서 (1,2차 분석)" if mode == "contract" else "최종 실행 전략 리포트 (1,2,3차 통합)"
    
    return f"""
==================================================
[유아플랜] {title}
==================================================
접수번호: {data.get('receipt_no', '-')}
작성일시: {datetime.now().strftime("%Y-%m-%d")}

1. 기업 진단 요약
--------------------------------------------------
- 기업명: {s1.get('name')} ({s1.get('industry')})
- 업력: {s2.get('startup_date')} 설립
- 재무지표: 부채비율 {metrics['debt_ratio']}, 성장률 {metrics['growth_rate']}
- 가점사항: {s2.get('official_certs', '-')}

2. AI 정밀 분석 결과
--------------------------------------------------
{ai_result if ai_result else "AI 분석을 실행해주세요."}

==================================================
""".strip()

# ==============================
# 5. AI 분석 로직 (자동 분기)
# ==============================
def analyze_with_gemini(api_key: str, data: Dict[str, Any]) -> str:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        s3 = data.get("stage3")
        
        # 3차 데이터 유무에 따라 프롬프트 변경
        if not s3 or not s3.get('consultant_note'):
            prompt = generate_contract_prompt(data)
            msg = "🔍 1,2차 데이터 기반 [계약 가능성] 심사 중..."
        else:
            prompt = generate_execution_prompt(data)
            msg = "🚀 1~3차 데이터 기반 [최종 실행 전략] 수립 중..."
            
        with st.spinner(msg):
            return model.generate_content(prompt).text
    except Exception as e: return f"⚠️ 오류: {str(e)}"

# [계약 심사 프롬프트]
def generate_contract_prompt(data: Dict[str, Any]) -> str:
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    metrics = calculate_financial_metrics(s2)
    
    return f"""
    당신은 정책자금 컨설팅펌의 수석 심사역입니다.
    현재 1차(기본), 2차(재무) 설문을 마친 예비 고객 데이터를 분석하여 계약 여부를 판단합니다.

    # [기업 데이터]
    - 업종: {s1.get('industry')} / 설립 {s2.get('startup_date')}
    - 재무: 매출 {s2.get('revenue_y1')}만원 (성장률 {metrics['growth_rate']}), 부채비율 {metrics['debt_ratio']}
    - 리스크: {s1.get('tax_status')}, {s1.get('credit_status')}

    # [요청 사항 - Markdown 출력]
    ## 1. 수임 판정 (Go / No-Go)
    - **결과:** [적극 추천 / 조건부 진행 / 수임 거절] 중 택 1
    - **판단 근거:** 승인 확률이 50% 이상인지 냉정하게 평가하세요.

    ## 2. 계약 유도 멘트 (Sales Point)
    - 고객이 착수금을 내고 계약하게 만들 설득 논리 3가지를 작성하세요.
    - 예: "높은 부채비율을 방어할 기술평가 전략이 필요함을 강조"

    ## 3. 예상 가능 자금
    - 도전 가능한 자금 기관과 예상 한도를 추정하세요.
    """.strip()

# [실행 전략 프롬프트]
def generate_execution_prompt(data: Dict[str, Any]) -> str:
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    s3 = data.get("stage3") or {}
    metrics = calculate_financial_metrics(s2)
    
    return f"""
    당신은 정책자금 실행 컨설턴트입니다. 3차 심층 데이터를 포함하여 최종 실행 전략을 짭니다.

    # [추가 심층 데이터]
    - 담보: {s3.get('collateral')}
    - 기대출: {s3.get('debt_info')}
    - 컨설턴트 메모: {s3.get('consultant_note')}

    # [요청 사항]
    ## 1. 최종 승인 가능성 재평가
    - 담보와 기대출을 고려하여 승인 가능성을 재확인하세요.

    ## 2. 최적 자금 매칭 & 준비 서류
    - 실행할 자금명과 고객이 당장 준비해야 할 서류 목록을 구체적으로 나열하세요.
    """.strip()

def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    try:
        payload = { "action": "get_integrated_view", "receipt_no": receipt_no, "api_token": API_TOKEN }
        res = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        return res.json() if res.status_code == 200 else {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e: return {"status": "error", "message": str(e)}

# ==============================
# 6. UI 메인 (헤더 로고 적용)
# ==============================
def main():
    # CSS 설정 (로고 크기 및 레이아웃)
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    #MainMenu, footer, header { display: none !important; }

    .unified-header {
        background: #002855; padding: 20px 30px; border-radius: 0 0 15px 15px;
        margin: -4rem -4rem 24px -4rem; color: white; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header-left { display: flex; align-items: center; gap: 15px; }
    .header-left img { height: 40px; object-fit: contain; } /* 로고 크기 설정 */
    .header-left h1 { margin: 0; font-size: 24px; font-weight: 700; color: white; }
    </style>
    """, unsafe_allow_html=True)

    # 헤더 출력 (로고 이미지 포함)
    st.markdown(f"""
    <div class="unified-header">
        <div class="header-left">
            <img src="{LOGO_URL}" alt="Logo">
            <h1>통합 고객 관리 대시보드</h1>
        </div>
        <div style="font-size:12px; opacity:0.8;">Admin Mode</div>
    </div>
    """, unsafe_allow_html=True)

    # API Key 설정 (자동 감지)
    env_key = os.getenv("GEMINI_API_KEY")
    gemini_api_key = env_key

    if not env_key:
        with st.sidebar:
            st.header("⚙️ 설정")
            st.info("서버에 GEMINI_API_KEY를 등록하면 이 입력창은 사라집니다.")
            gemini_api_key = st.text_input("Gemini API Key", type="password")

    # 검색바
    with st.container():
        c1, c2 = st.columns([4, 1])
        with c1: receipt_no = st.text_input("접수번호 입력", placeholder="예: YP202511271234")
        with c2: search_btn = st.button("🔍 고객 조회", type="primary", use_container_width=True)

    # 결과 화면
    if search_btn and receipt_no:
        with st.spinner("데이터 조회 중..."):
            result = fetch_integrated_data(receipt_no.strip())
        
        if result.get("status") == "success":
            data = result.get("data", {})
            s1 = data.get("stage1") or {}
            s2 = data.get("stage2") or {}
            s3 = data.get("stage3") or {}
            metrics = calculate_financial_metrics(s2)
            
            # 모드 판단
            has_s3 = bool(s3 and s3.get('consultant_note'))
            stage_label = "🚀 최종 실행 단계 (3차 완료)" if has_s3 else "📝 계약 검토 단계 (2차 완료)"
            stage_color = "green" if has_s3 else "orange"

            # 요약 섹션
            st.markdown(f"### 📊 기업 360도 진단 요약 (:{stage_color}[{stage_label}])")
            col1, col2, col3 = st.columns(3)
            with col1: st.info(f"**성장률**: {metrics['growth_rate']}")
            with col2: st.warning(f"**부채비율**: {metrics['debt_ratio']}")
            with col3: 
                risk_status = "위험" if s1.get('tax_status') != "체납 없음" else "양호"
                st.error(f"**리스크**: {risk_status}")

            # 상세 탭
            with st.expander("📂 상세 데이터 보기"):
                t1, t2, t3 = st.tabs(["1차(자격)", "2차(재무)", "3차(심층)"])
                with t1: st.write(s1)
                with t2: st.write(s2)
                with t3: 
                    if has_s3: st.write(s3)
                    else: st.info("아직 3차 상담 전입니다. 계약 후 진행하세요.")

            # AI 분석
            st.markdown("---")
            if has_s3: st.subheader("🤖 AI 최종 실행 전략 (서류/기관)")
            else: st.subheader("⚖️ AI 계약 심사 (수임 여부 판단)")
            
            ai_output = ""
            if not gemini_api_key:
                st.warning("👈 사이드바에 API 키를 입력하거나, 서버 설정에 키를 등록해주세요.")
            else:
                ai_output = analyze_with_gemini(gemini_api_key, data)
                st.markdown(ai_output)
            
            # 다운로드
            if ai_output:
                mode = "execution" if has_s3 else "contract"
                full_text = generate_full_report(data, ai_output, mode)
                btn_label = "최종 실행안 다운로드" if has_s3 else "계약 제안서 다운로드"
                b64 = base64.b64encode(full_text.encode()).decode()
                st.markdown(f'<a href="data:text/plain;base64,{b64}" download="{btn_label}.txt" style="display:block; text-align:center; background:#002855; color:white; padding:15px; border-radius:10px; text-decoration:none; margin-top:20px;">📥 {btn_label}</a>', unsafe_allow_html=True)
                
        else:
            st.error(f"조회 실패: {result.get('message')}")

if __name__ == "__main__":
    main()