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
    initial_sidebar_state="collapsed"
)

# ==============================
# 2. 환경 설정 & 로고
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
INTEGRATED_GAS_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ==============================
# 3. 재무 지표 계산 함수
# ==============================
def calculate_financial_metrics(s2: Dict) -> Dict:
    metrics = {
        "debt_ratio": "-", "debt_status": "gray",
        "growth_rate": "-", "growth_status": "gray"
    }
    
    if not s2:
        return metrics

    try:
        capital = int(str(s2.get('capital_amount', '0')).replace(',', '').replace('만원', ''))
        debt = int(str(s2.get('debt_amount', '0')).replace(',', '').replace('만원', ''))
        if capital > 0:
            ratio = round((debt / capital) * 100)
            metrics['debt_ratio'] = f"{ratio}%"
            if ratio > 400:
                metrics['debt_status'] = "red"
            elif ratio > 200:
                metrics['debt_status'] = "orange"
            else:
                metrics['debt_status'] = "green"
    except:
        pass

    try:
        rev_prev = int(str(s2.get('revenue_y2', '0')).replace(',', ''))
        rev_curr = int(str(s2.get('revenue_y1', '0')).replace(',', '')) 
        if rev_prev > 0:
            growth = round(((rev_curr - rev_prev) / rev_prev) * 100)
            sign = "+" if growth > 0 else ""
            metrics['growth_rate'] = f"{sign}{growth}%"
            if growth >= 20:
                metrics['growth_status'] = "blue"
            elif growth > 0:
                metrics['growth_status'] = "green"
            else:
                metrics['growth_status'] = "red"
    except:
        pass
    
    return metrics

# ==============================
# 4. 리포트 텍스트 생성
# ==============================
def generate_full_report(data: Dict[str, Any], ai_result: str = "", mode: str = "contract") -> str:
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    s3 = data.get("stage3") or {}
    metrics = calculate_financial_metrics(s2)
    
    title = "컨설팅 계약 제안서 (1,2차 분석)" if mode == "contract" else "최종 실행 전략 리포트 (1,2,3차 통합)"
    
    report = f"""
==================================================
[유아플랜] {title}
==================================================
접수번호: {data.get('receipt_no', '-')}
작성일시: {datetime.now().strftime("%Y-%m-%d %H:%M")}

1. 기업 진단 요약
--------------------------------------------------
- 고객명: {s1.get('name', '-')}
- 업종: {s1.get('industry', '-')}
- 지역: {s1.get('region', '-')}
- 사업형태: {s1.get('business_type', '-')}
- 직원수: {s1.get('employee_count', '-')}
- 필요자금: {s1.get('funding_amount', '-')}
"""

    if s2:
        report += f"""
2. 재무 현황 (2차)
--------------------------------------------------
- 사업자명: {s2.get('business_name', '-')}
- 사업시작일: {s2.get('startup_date', '-')}
- 올해 매출: {s2.get('revenue_y1', '-')}만원
- 전년 매출: {s2.get('revenue_y2', '-')}만원
- 자본금: {s2.get('capital_amount', '-')}만원
- 부채: {s2.get('debt_amount', '-')}만원
- 부채비율: {metrics['debt_ratio']}
- 성장률: {metrics['growth_rate']}
"""

    if s3 and mode == "execution":
        report += f"""
3. 심층 분석 (3차)
--------------------------------------------------
- 담보/보증: {s3.get('collateral_profile', '-')}
- 세무/신용: {s3.get('tax_credit_summary', '-')}
- 기존 대출: {s3.get('loan_summary', '-')}
- 준비 서류: {s3.get('docs_check', '-')}
- 리스크: {s3.get('risk_top3', '-')}
- 컨설턴트 메모: {s3.get('coach_notes', '-')}
"""

    report += f"""
4. AI 분석 결과
--------------------------------------------------
{ai_result if ai_result else "AI 분석을 실행해주세요."}

==================================================
"""
    return report.strip()

# ==============================
# 5. AI 분석 로직
# ==============================
def analyze_with_gemini(api_key: str, data: Dict[str, Any]) -> str:
    if not api_key:
        return "⚠️ API 키가 설정되지 않았습니다."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        s3 = data.get("stage3")
        
        # 3차 데이터 유무에 따라 분기 (coach_notes로 판단)
        if s3 and s3.get('coach_notes'):
            prompt = generate_execution_prompt(data)
            msg = "🚀 1~3차 데이터 기반 [최종 실행 전략] 수립 중..."
        else:
            prompt = generate_contract_prompt(data)
            msg = "🔍 1,2차 데이터 기반 [계약 가능성] 심사 중..."
            
        with st.spinner(msg):
            response = model.generate_content(prompt)
            return response.text
            
    except Exception as e:
        return f"⚠️ AI 분석 오류: {str(e)}"

def generate_contract_prompt(data: Dict[str, Any]) -> str:
    """1,2차 기반 계약 심사 프롬프트"""
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    metrics = calculate_financial_metrics(s2)
    
    return f"""
당신은 정책자금 컨설팅펌의 수석 심사역입니다.
1차(기본), 2차(재무) 설문을 마친 예비 고객 데이터를 분석하여 계약 여부를 판단합니다.

# [기업 데이터]
- 고객명: {s1.get('name', '-')}
- 업종: {s1.get('industry', '-')}
- 지역: {s1.get('region', '-')}
- 사업형태: {s1.get('business_type', '-')}
- 직원수: {s1.get('employee_count', '-')}
- 필요자금: {s1.get('funding_amount', '-')}
- 정책자금 경험: {s1.get('policy_experience', '-')}

# [재무 현황]
- 사업자명: {s2.get('business_name', '-')}
- 사업시작일: {s2.get('startup_date', '-')}
- 올해 매출: {s2.get('revenue_y1', '0')}만원
- 전년 매출: {s2.get('revenue_y2', '0')}만원
- 자본금: {s2.get('capital_amount', '0')}만원
- 부채: {s2.get('debt_amount', '0')}만원
- 부채비율: {metrics['debt_ratio']}
- 매출성장률: {metrics['growth_rate']}

# [리스크 현황]
- 세금 체납: {s1.get('tax_status', '-')}
- 금융 연체: {s1.get('credit_status', '-')}
- 영업 상태: {s1.get('business_status', '-')}

# [요청 사항 - Markdown 형식으로 출력]

## 1. 수임 판정 (Go / No-Go)
- **결과:** [적극 추천 / 조건부 진행 / 수임 거절] 중 택 1
- **판단 근거:** 승인 확률이 50% 이상인지 냉정하게 평가

## 2. 예상 가능 정책자금 (2~3개)
- 기관명, 자금명, 예상 한도, 금리 범위
- 예: 소상공인시장진흥공단 - 일반경영안정자금 - 최대 7천만원 - 연 3~4%

## 3. 계약 유도 포인트 (Sales Point)
- 고객이 착수금을 내고 계약하게 만들 설득 논리 3가지

## 4. 주의사항 / 보완 필요 항목
- 계약 전 확인해야 할 사항
""".strip()

def generate_execution_prompt(data: Dict[str, Any]) -> str:
    """1,2,3차 기반 최종 실행 전략 프롬프트"""
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    s3 = data.get("stage3") or {}
    metrics = calculate_financial_metrics(s2)
    
    return f"""
당신은 정책자금 실행 컨설턴트입니다.
계약 완료된 고객의 1~3차 데이터를 바탕으로 최종 실행 전략을 수립합니다.

# [기본 정보 - 1차]
- 고객명: {s1.get('name', '-')}
- 업종: {s1.get('industry', '-')}
- 지역: {s1.get('region', '-')}
- 사업형태: {s1.get('business_type', '-')}
- 필요자금: {s1.get('funding_amount', '-')}

# [재무 현황 - 2차]
- 사업자명: {s2.get('business_name', '-')}
- 사업시작일: {s2.get('startup_date', '-')}
- 올해 매출: {s2.get('revenue_y1', '0')}만원
- 자본금: {s2.get('capital_amount', '0')}만원
- 부채: {s2.get('debt_amount', '0')}만원
- 부채비율: {metrics['debt_ratio']}
- 성장률: {metrics['growth_rate']}

# [심층 분석 - 3차]
- 담보/보증 계획: {s3.get('collateral_profile', '-')}
- 세무/신용 상태: {s3.get('tax_credit_summary', '-')}
- 기존 대출 현황: {s3.get('loan_summary', '-')}
- 준비된 서류: {s3.get('docs_check', '-')}
- 우대/제외 요건: {s3.get('priority_exclusion', '-')}
- 리스크 Top3: {s3.get('risk_top3', '-')}
- 컨설턴트 메모: {s3.get('coach_notes', '-')}

# [요청 사항 - Markdown 형식으로 출력]

## 1. 최종 승인 가능성 평가
- 담보/기대출 고려하여 승인 확률 재평가 (상/중/하)
- 핵심 리스크와 대응 방안

## 2. 최적 정책자금 매칭 (우선순위 순)
각 자금별로:
- 기관명 / 자금명
- 예상 한도 / 금리
- 신청 적기 / 소요 기간
- 이 고객에게 유리한 점

## 3. 즉시 준비해야 할 서류 목록
- 필수 서류 (체크리스트 형태)
- 추가 가점 서류

## 4. 실행 로드맵 (주 단위)
- 1주차: OOO
- 2주차: OOO
- ...

## 5. 컨설턴트 액션 아이템
- 당장 해야 할 일 3가지
""".strip()

# ==============================
# 6. API 호출
# ==============================
def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    try:
        payload = {
            "action": "get_integrated_view",
            "receipt_no": receipt_no,
            "api_token": API_TOKEN
        }
        res = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def save_policy_result(receipt_no: str, policy_name: str, approved_amount: str, result_memo: str) -> Dict[str, Any]:
    """정책자금 결과 저장"""
    try:
        payload = {
            "action": "save_result",
            "api_token": API_TOKEN,
            "receipt_no": receipt_no,
            "policy_name": policy_name,
            "approved_amount": approved_amount,
            "result_memo": result_memo
        }
        res = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================
# 7. UI 메인
# ==============================
def main():
    # CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    #MainMenu, footer, header { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }

    .unified-header {
        background: linear-gradient(135deg, #002855 0%, #1e40af 100%);
        padding: 20px 30px;
        border-radius: 0 0 15px 15px;
        margin: -4rem -4rem 24px -4rem;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .header-left { display: flex; align-items: center; gap: 15px; }
    .header-left img { height: 40px; object-fit: contain; }
    .header-left h1 { margin: 0; font-size: 22px; font-weight: 700; color: white; }
    
    .stage-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
    }
    .badge-contract { background: #FEF3C7; color: #92400E; }
    .badge-execution { background: #D1FAE5; color: #065F46; }
    
    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
    .metric-value { font-size: 24px; font-weight: 700; color: #111827; }
    .metric-green { color: #059669; }
    .metric-red { color: #DC2626; }
    .metric-orange { color: #D97706; }
    
    .download-btn {
        display: block;
        text-align: center;
        background: #002855;
        color: white !important;
        padding: 14px 24px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: 600;
        margin-top: 20px;
        transition: all 0.2s;
    }
    .download-btn:hover { background: #1e40af; }
    </style>
    """, unsafe_allow_html=True)

    # 헤더
    st.markdown(f"""
    <div class="unified-header">
        <div class="header-left">
            <img src="{LOGO_URL}" alt="Logo">
            <h1>통합 고객 관리 대시보드</h1>
        </div>
        <div style="font-size:12px; opacity:0.8;">v2.0 | Admin</div>
    </div>
    """, unsafe_allow_html=True)

    # API 키 체크
    if not GEMINI_API_KEY:
        st.error("⚠️ GEMINI_API_KEY 환경변수가 설정되지 않았습니다. Render 설정을 확인하세요.")
        return

    # 검색바
    col1, col2 = st.columns([4, 1])
    with col1:
        receipt_no = st.text_input(
            "접수번호 입력",
            placeholder="예: YP202511271234",
            label_visibility="collapsed"
        )
    with col2:
        search_btn = st.button("🔍 고객 조회", type="primary", use_container_width=True)

    # 조회 실행
    if search_btn and receipt_no:
        with st.spinner("데이터 조회 중..."):
            result = fetch_integrated_data(receipt_no.strip())
        
        if result.get("status") == "success":
            data = result.get("data", {})
            s1 = data.get("stage1") or {}
            s2 = data.get("stage2") or {}
            s3 = data.get("stage3") or {}
            metrics = calculate_financial_metrics(s2)
            
            # 단계 판단 (coach_notes로 3차 완료 여부 확인)
            has_s3 = bool(s3 and s3.get('coach_notes'))
            
            # 상단 요약
            st.markdown("---")
            
            if has_s3:
                st.markdown('<span class="stage-badge badge-execution">🚀 최종 실행 단계 (3차 완료)</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="stage-badge badge-contract">📝 계약 검토 단계 (2차 완료)</span>', unsafe_allow_html=True)
            
            st.markdown(f"### 📊 {s1.get('name', '고객')} 님 기업 진단")
            
            # 핵심 지표 카드
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            with col_m1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">업종</div>
                    <div class="metric-value" style="font-size:16px;">{s1.get('industry', '-')}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m2:
                growth_class = "metric-green" if metrics['growth_status'] == 'green' else ("metric-red" if metrics['growth_status'] == 'red' else "")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">매출 성장률</div>
                    <div class="metric-value {growth_class}">{metrics['growth_rate']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m3:
                debt_class = "metric-green" if metrics['debt_status'] == 'green' else ("metric-red" if metrics['debt_status'] == 'red' else "metric-orange")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">부채비율</div>
                    <div class="metric-value {debt_class}">{metrics['debt_ratio']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_m4:
                risk_status = "⚠️ 주의" if s1.get('tax_status') != "체납 없음" or s1.get('credit_status') != "연체 없음" else "✅ 양호"
                risk_class = "metric-red" if "주의" in risk_status else "metric-green"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">리스크</div>
                    <div class="metric-value {risk_class}" style="font-size:18px;">{risk_status}</div>
                </div>
                """, unsafe_allow_html=True)

            # 상세 데이터 탭
            st.markdown("---")
            with st.expander("📂 상세 데이터 보기", expanded=False):
                tab1, tab2, tab3 = st.tabs(["1차 (기본정보)", "2차 (재무정보)", "3차 (심층분석)"])
                
                with tab1:
                    if s1:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**고객명:** {s1.get('name', '-')}")
                            st.write(f"**연락처:** {s1.get('phone', '-')}")
                            st.write(f"**이메일:** {s1.get('email', '-')}")
                            st.write(f"**지역:** {s1.get('region', '-')}")
                        with col_b:
                            st.write(f"**업종:** {s1.get('industry', '-')}")
                            st.write(f"**사업형태:** {s1.get('business_type', '-')}")
                            st.write(f"**직원수:** {s1.get('employee_count', '-')}")
                            st.write(f"**필요자금:** {s1.get('funding_amount', '-')}")
                        st.write("---")
                        st.write(f"**세금 체납:** {s1.get('tax_status', '-')}")
                        st.write(f"**금융 연체:** {s1.get('credit_status', '-')}")
                        st.write(f"**정책자금 경험:** {s1.get('policy_experience', '-')}")
                    else:
                        st.info("1차 설문 데이터가 없습니다.")
                
                with tab2:
                    if s2:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**사업자명:** {s2.get('business_name', '-')}")
                            st.write(f"**사업자번호:** {s2.get('biz_reg_no', '-')}")
                            st.write(f"**사업시작일:** {s2.get('startup_date', '-')}")
                        with col_b:
                            st.write(f"**올해 매출:** {s2.get('revenue_y1', '-')}만원")
                            st.write(f"**전년 매출:** {s2.get('revenue_y2', '-')}만원")
                            st.write(f"**전전년 매출:** {s2.get('revenue_y3', '-')}만원")
                        st.write("---")
                        st.write(f"**자본금:** {s2.get('capital_amount', '-')}만원")
                        st.write(f"**부채:** {s2.get('debt_amount', '-')}만원")
                    else:
                        st.info("2차 설문 데이터가 없습니다.")
                
                with tab3:
                    if s3 and s3.get('coach_notes'):
                        st.write(f"**담보/보증:** {s3.get('collateral_profile', '-')}")
                        st.write(f"**세무/신용:** {s3.get('tax_credit_summary', '-')}")
                        st.write(f"**기존 대출:** {s3.get('loan_summary', '-')}")
                        st.write(f"**준비 서류:** {s3.get('docs_check', '-')}")
                        st.write(f"**우대/제외:** {s3.get('priority_exclusion', '-')}")
                        st.write(f"**리스크 Top3:** {s3.get('risk_top3', '-')}")
                        st.write("---")
                        st.write(f"**컨설턴트 메모:** {s3.get('coach_notes', '-')}")
                    else:
                        st.info("아직 3차 상담 전입니다. 계약 후 진행하세요.")

            # AI 분석
            st.markdown("---")
            if has_s3:
                st.subheader("🤖 AI 최종 실행 전략")
            else:
                st.subheader("⚖️ AI 계약 심사 분석")
            
            ai_output = analyze_with_gemini(GEMINI_API_KEY, data)
            st.markdown(ai_output)
            
            # 다운로드
            if ai_output and not ai_output.startswith("⚠️"):
                mode = "execution" if has_s3 else "contract"
                full_text = generate_full_report(data, ai_output, mode)
                btn_label = "📥 최종 실행안 다운로드" if has_s3 else "📥 계약 제안서 다운로드"
                filename = f"유아플랜_{receipt_no}_{mode}_{datetime.now().strftime('%Y%m%d')}.txt"
                b64 = base64.b64encode(full_text.encode()).decode()
                st.markdown(f'<a href="data:text/plain;base64,{b64}" download="{filename}" class="download-btn">{btn_label}</a>', unsafe_allow_html=True)

            # 결과 저장 섹션 (3차 완료 시)
            if has_s3:
                st.markdown("---")
                st.subheader("💾 정책자금 결과 기록")
                
                with st.form("result_form"):
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        policy_name = st.text_input("승인된 정책자금명", placeholder="예: 소상공인 일반경영안정자금")
                    with col_r2:
                        approved_amount = st.text_input("승인 금액 (만원)", placeholder="예: 5000")
                    
                    result_memo = st.text_area("상담 메모", placeholder="특이사항, 조건, 후속 조치 등")
                    
                    if st.form_submit_button("💾 결과 저장", type="primary"):
                        if policy_name and approved_amount:
                            save_result = save_policy_result(receipt_no, policy_name, approved_amount, result_memo)
                            if save_result.get("status") == "success":
                                st.success(f"✅ 저장 완료: {policy_name} / {approved_amount}만원")
                            else:
                                st.error(f"❌ 저장 실패: {save_result.get('message', '알 수 없는 오류')}")
                        else:
                            st.warning("정책자금명과 승인금액을 입력해주세요.")
            
        else:
            st.error(f"❌ 조회 실패: {result.get('message', '알 수 없는 오류')}")
    
    elif search_btn:
        st.warning("접수번호를 입력해주세요.")

if __name__ == "__main__":
    main()