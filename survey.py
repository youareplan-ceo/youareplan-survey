"""
유아플랜 정책자금 1차 상담 설문
v2025-12-09-gas-sync
- GAS 컬럼 구조 완전 동기화 (23개 컬럼)
- 추가 필드: 생년월일, 성별, 개업연월, 정책자금경험
"""

import streamlit as st
import re
import requests
from datetime import datetime
import random
import os

st.set_page_config(
    page_title="유아플랜 정책자금 1차 상담",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
RELEASE_VERSION = "v2025-12-09-gas-sync"
APPS_SCRIPT_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")
KAKAO_CHANNEL_URL = "https://pf.kakao.com/_LWxexmn"

# ==============================
# 선택지 정의 (GAS 컬럼 순서 기준)
# ==============================
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
INDUSTRIES = ["제조업", "건설업", "도소매업", "숙박·음식점업", "운수·창고업", "정보통신업", "전문·과학·기술 서비스업", "교육서비스업", "보건·사회복지업", "기타"]
BUSINESS_TYPES = ["예비창업자", "개인사업자", "법인사업자", "협동조합·사회적기업"]
GENDERS = ["남성", "여성"]
EMPLOYEE_COUNTS = ["0명(대표만)", "1명", "2-4명", "5-9명", "10명 이상"]
REVENUES = ["매출 없음", "5천만원 미만", "5천만원~1억원", "1억원~3억원", "3억원~5억원", "5억원 이상"]
FUNDING_AMOUNTS = ["3천만원 미만", "3천만원~1억원", "1-3억원", "3-5억원", "5억원 이상"]
POLICY_EXPERIENCES = ["경험 없음", "신청했으나 탈락", "과거 수혜 경험 있음", "현재 수혜 중"]

# ==============================
# 유틸리티 함수
# ==============================
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone(d: str) -> str:
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def save_to_sheet(data: dict) -> dict:
    try:
        data['token'] = API_TOKEN
        resp = requests.post(APPS_SCRIPT_URL, json=data, timeout=20)
        return resp.json() if resp.status_code == 200 else {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================
# 스타일링
# ==============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
#MainMenu, footer, header { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; max-width: 700px !important; }

.unified-header { 
    background: #002855; 
    padding: 24px 20px; 
    text-align: center; 
    border-radius: 12px; 
    margin-bottom: 24px; 
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); 
}
.unified-header img { height: 48px; margin-bottom: 12px; object-fit: contain; }
.unified-header .gov-label { color: rgba(255, 255, 255, 0.85); font-size: 13px; font-weight: 500; }

.section-header { 
    font-size: 16px; 
    font-weight: 700; 
    margin-top: 20px; 
    margin-bottom: 10px; 
    border-bottom: 2px solid rgba(128, 128, 128, 0.2); 
    padding-bottom: 6px; 
}

div[data-testid="stFormSubmitButton"] button { 
    background: #002855 !important; 
    color: white !important; 
    border: none !important; 
    padding: 14px 24px !important; 
    border-radius: 8px !important; 
    font-weight: 700 !important; 
    width: 100%; 
    margin-top: 10px; 
}

.success-box {
    padding: 20px; 
    border-radius: 10px; 
    background-color: rgba(0,40,85,0.05); 
    border: 1px solid rgba(0,40,85,0.1); 
    margin: 20px 0; 
    text-align: center;
}
.success-box h3 { margin: 0; color: #002855; font-size: 24px; }
.success-box p { margin-top: 10px; margin-bottom: 0; color: #555; }
</style>
""", unsafe_allow_html=True)

# ==============================
# 메인 함수
# ==============================
def main():
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    
    # 헤더
    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <div class="gov-label">중소벤처기업부 · 소상공인시장진흥공단 협력 상담</div>
    </div>
    """, unsafe_allow_html=True)

    # URL 파라미터 (대시보드 연동용)
    try:
        qp = st.query_params
        pre_receipt = qp.get("r", None)
        pre_name = qp.get("name", "")
        pre_phone = qp.get("phone", "")
    except:
        pre_receipt, pre_name, pre_phone = None, "", ""

    if pre_receipt:
        st.info(f"💡 기존 고객(접수번호: {pre_receipt}) 정보를 연동하여 작성합니다.")

    # 제출 완료 화면
    if st.session_state.submitted:
        receipt_no = st.session_state.get('receipt_no', '알 수 없음')
        
        st.success("✅ 상담 신청이 완료되었습니다!")
        st.markdown(f"""
        <div class="success-box">
            <h3>접수번호: {receipt_no}</h3>
            <p>담당자가 1영업일 내 검토 후 연락드립니다.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # 설문 시작
    st.markdown("### 📋 1차 기초 상담 신청")
    st.caption("우리 기업의 정책자금 지원 가능성을 검토하기 위한 기초 단계입니다.")

    with st.form("survey_form"):
        
        # ========== 섹션 1: 기본 정보 ==========
        st.markdown('<div class="section-header">👤 기본 정보</div>', unsafe_allow_html=True)
        
        name = st.text_input("대표자 성함 *", value=pre_name, placeholder="예: 홍길동")
        phone_raw = st.text_input("연락처 *", value=pre_phone, placeholder="숫자만 입력 (예: 01012345678)")
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")

        # ========== 섹션 2: 대표자 정보 ==========
        st.markdown('<div class="section-header">🎂 대표자 정보</div>', unsafe_allow_html=True)
        
        col_birth, col_gender = st.columns(2)
        with col_birth:
            birthdate = st.text_input("생년월일", placeholder="예: 1985-03-15 또는 850315")
        with col_gender:
            gender = st.selectbox("성별", GENDERS)

        # ========== 섹션 3: 사업 현황 ==========
        st.markdown('<div class="section-header">🏢 사업 현황</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            region = st.selectbox("사업장 지역", REGIONS)
            industry = st.selectbox("주요 업종", INDUSTRIES)
        with col2:
            business_type = st.selectbox("사업자 형태", BUSINESS_TYPES)
            open_date = st.text_input("개업연월", placeholder="예: 2022-05 또는 202205")

        # ========== 섹션 4: 자금 현황 ==========
        st.markdown('<div class="section-header">💰 자금 현황</div>', unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        with col3:
            employee_count = st.selectbox("직원 수", EMPLOYEE_COUNTS)
            revenue = st.selectbox("연간 매출", REVENUES)
        with col4:
            funding_amount = st.selectbox("필요 자금", FUNDING_AMOUNTS)
            policy_experience = st.selectbox("정책자금 경험", POLICY_EXPERIENCES)

        # ========== 섹션 5: 자격 자가진단 ==========
        st.markdown('<div class="section-header">🚨 자격 자가진단</div>', unsafe_allow_html=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox("국세/지방세 체납", ["체납 없음", "체납 있음", "분납 중"])
        with col_b:
            credit_status = st.selectbox("대출 연체 이력", ["연체 없음", "30일 미만", "30일 이상"])
        
        business_status = st.selectbox("현재 영업 상태", ["정상 영업", "휴업", "폐업 예정"])

        # ========== 동의 ==========
        st.markdown("---")
        
        col_p, col_m = st.columns(2)
        with col_p:
            privacy = st.checkbox("개인정보 수집·이용 동의 (필수)", value=True)
        with col_m:
            marketing = st.checkbox("마케팅 수신 동의 (선택)")

        st.write("")
        submitted = st.form_submit_button("📩 상담 신청하기")

        if submitted:
            phone_digits = _digits_only(phone_raw)
            
            # 유효성 검사
            if not name.strip():
                st.warning("⚠️ 성함을 입력해주세요.")
            elif len(phone_digits) < 10 or not phone_digits.startswith("010"):
                st.warning("⚠️ 연락처를 올바르게 입력해주세요.")
            elif not privacy:
                st.error("⚠️ 개인정보 수집에 동의해야 합니다.")
            else:
                with st.spinner("접수 중입니다... 잠시만 기다려주세요."):
                    # 접수번호: 기존 형식 유지 (YPMMDD + 4자리)
                    if pre_receipt:
                        receipt_no = pre_receipt
                    else:
                        receipt_no = f"YP{datetime.now().strftime('%m%d')}{random.randint(1000,9999)}"
                    
                    # GAS로 전송할 데이터 (컬럼 순서 일치)
                    data = {
                        'receipt_no': receipt_no,
                        'name': name.strip(),
                        'phone': format_phone(phone_digits),
                        'email': email.strip() if email else '',
                        'birthdate': birthdate.strip() if birthdate else '',
                        'gender': gender,
                        'region': region,
                        'industry': industry,
                        'business_type': business_type,
                        'open_date': open_date.strip() if open_date else '',
                        'employee_count': employee_count,
                        'revenue': revenue,
                        'funding_amount': funding_amount,
                        'policy_experience': policy_experience,
                        'tax_status': tax_status,
                        'credit_status': credit_status,
                        'business_status': business_status,
                        'privacy_agree': True,
                        'marketing_agree': marketing,
                        'release_version': RELEASE_VERSION,
                        'source': 'survey1_linked' if pre_receipt else 'survey1_new'
                    }
                    
                    result = save_to_sheet(data)
                    
                    if result.get('status') == 'success':
                        st.session_state.submitted = True
                        st.session_state.receipt_no = receipt_no
                        st.rerun()
                    else:
                        st.error(f"❌ 서버 통신 오류: {result.get('message')}. 잠시 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()