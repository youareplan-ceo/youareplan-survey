import streamlit as st
import requests
import json
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="유아플랜 정책자금 매칭",
    page_icon="💰",
    layout="wide"
)

# Apps Script URL
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec"  # v5
API_TOKEN = "youareplan"

# 번역 차단 CSS
st.markdown("""
<style>
  .notranslate,[translate="no"]{ translate: no !important; }
  .stApp * { translate: no !important; }
  @media (max-width: 768px) {
    [data-testid="stSidebar"] { display: none !important; }
  }
</style>
""", unsafe_allow_html=True)

def save_to_google_sheet(data):
    """Google Apps Script로 데이터 전송"""
    try:
        data['token'] = API_TOKEN
        
        response = requests.post(
            APPS_SCRIPT_URL,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )
        
        result = response.json()
        return result.get('status') == 'success'
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")
        return False

# 지역 목록
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산",
           "세종", "경기", "강원", "충북", "충남", "전북", "전남",
           "경북", "경남", "제주"]

# 업종 목록
INDUSTRIES = [
    "제조업", "건설업", "도소매업(유통·온라인쇼핑몰 포함)", "숙박·음식점업",
    "운수·창고업(물류 포함)", "정보통신업(소프트웨어·플랫폼)",
    "전문·과학·기술 서비스업(디자인·광고 포함)", "사업지원·임대 서비스업",
    "교육서비스업", "보건업·사회복지 서비스업", "예술·스포츠·여가 서비스업",
    "농업·임업·어업(영농/영어조합 포함)", "환경·폐기물·에너지(신재생 포함)",
    "기타"
]

# 옵션 테이블
BUSINESS_TYPES = ["예비창업자", "개인사업자", "법인사업자", "협동조합·사회적기업"]
EMPLOYEE_COUNTS = ["1명", "2-4명", "5-9명", "10명 이상"]
REVENUES = ["매출 없음", "5천만원 미만", "5천만원~1억원", "1억원~3억원", 
            "3억원~5억원", "5억원~10억원", "10억원~30억원", "30억원 이상"]
FUNDING_AMOUNTS = ["3천만원 미만", "3천만원~1억원", "1-3억원", "3-5억원", "5억원 이상"]
POLICY_EXPERIENCES = [
    "정책자금 대출 이용 경험",
    "신용보증 이용 경험",
    "정부지원사업 참여 경험",
    "경험 없음"
]

def main():
    st.title("🎯 유아플랜 컨설팅 정책자금 매칭 시스템")
    st.subheader("내 사업에 꼭 맞는 정책자금, 전문가가 1:1로 안내해드립니다")

    # 안내문: 자동 번역 끄기 안내
    st.warning(
        """
        🔔 **안내**: 브라우저의 자동 번역 기능(Chrome 번역 등)을 **끄고** 작성해주세요.\
        자동 번역 시 입력값이 변형될 수 있습니다.
        """
    )
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 💡 서비스 소개")
        st.success("✅ 전문가 무료 상담")
        st.success("✅ 맞춤형 매칭 서비스")
        
        st.markdown("---")
        st.markdown("### 📞 상담 프로세스")
        st.info("1️⃣ 3분 설문 작성\n"
                "2️⃣ 1영업일 내 전문가 연락\n"
                "3️⃣ 무료 상담 진행\n"
                "4️⃣ 맞춤 정책자금 안내")
    
    # 설문지
    st.markdown("### 📝 1차 설문 - 기본 정보")
    st.write("정확히 입력할수록 매칭 정확도가 높아집니다.")
    
    with st.form("first_survey"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("👤 성함 *", placeholder="홍길동")
            region = st.selectbox("🏢 사업장 지역 *", REGIONS)
            industry = st.selectbox("🏭 업종 *", INDUSTRIES)
            business_type = st.selectbox("📋 사업자 형태 *", BUSINESS_TYPES)
        
        with col2:
            phone = st.text_input("📞 연락처 *", placeholder="010-0000-0000")
            employee_count = st.selectbox("👥 직원 수 *", EMPLOYEE_COUNTS)
            revenue = st.selectbox("💰 연간 매출 *", REVENUES)
            funding_amount = st.selectbox("💵 필요 자금 *", FUNDING_AMOUNTS)
        
        email = st.text_input("📧 이메일 (선택)", placeholder="email@example.com")
        
        # 정책자금 경험
        st.markdown("---")
        st.markdown("#### 💼 정책자금 이용 경험")
        policy_experience = st.multiselect(
            "해당사항을 모두 선택하세요",
            POLICY_EXPERIENCES,
            help="기존 경험이 있으시면 더 정확한 상담이 가능합니다",
            placeholder="선택하세요"
        )
        
        # 개인정보 동의
        st.markdown("---")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)", help="필수 동의 항목입니다. 전문은 아래에서 확인하세요.")
            with st.expander("개인정보 수집·이용 동의 전문 보기"):
                st.markdown(
                    """
                    **수집·이용 목적**: 상담 신청 확인, 자격 검토, 연락 및 안내

                    **수집 항목**: 성함, 연락처, 이메일(선택), 지역, 업종, 사업자 형태, 직원 수, 매출 규모, 필요 자금, 정책자금 이용 경험

                    **보유·이용 기간**: 상담 완료 후 1년 또는 동의 철회 시까지 (관련 법령의 별도 보존기간이 있는 경우 그에 따름)

                    **제공 및 위탁**: 제3자 제공 없음. 시스템 운영 및 고객 응대 목적의 처리위탁이 필요한 경우 계약서에 고지 후 최소한으로 위탁합니다.

                    **동의 철회**: 카카오채널/이메일/전화로 철회 요청 시 지체 없이 삭제합니다.
                    """
                )
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)", help="신규 지원사업/정책자금 알림을 드립니다. 전문은 아래에서 확인하세요.")
            with st.expander("마케팅 정보 수신 동의 전문 보기"):
                st.markdown(
                    """
                    **수신 내용**: 신규 정책자금, 지원사업, 이벤트/세미나 안내

                    **수집 항목**: 성함, 연락처, 이메일(선택)

                    **수신 방법**: 카카오톡/문자/이메일 중 일부

                    **보유·이용 기간**: 동의 철회 시까지

                    **철회 방법**: 언제든지 수신 거부(채널 차단/문자 내 수신거부 링크/이메일 회신)로 철회 가능합니다.
                    """
                )

        # 제출
        submitted = st.form_submit_button("🎯 전문가 상담 신청하기", type="primary")
        
        if submitted:
            if not name or not phone:
                st.error("성함과 연락처는 필수 입력 항목입니다.")
            elif not privacy_agree:
                st.error("개인정보 수집·이용 동의는 필수입니다.")
            else:
                with st.spinner("상담 신청을 처리하고 있습니다..."):
                    # 데이터 준비
                    survey_data = {
                        'name': name,
                        'phone': phone,
                        'email': email,
                        'region': region,
                        'industry': industry,
                        'business_type': business_type,
                        'employee_count': employee_count,
                        'revenue': revenue,
                        'funding_amount': funding_amount,
                        'policy_experience': ', '.join(policy_experience) if policy_experience else '경험 없음',
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree
                    }
                    
                    # Google Sheets에 저장
                    if save_to_google_sheet(survey_data):
                        st.success("✅ 상담 신청이 완료되었습니다!")
                        st.info("📞 **1영업일 내 전문가가 연락드립니다**")
                        st.balloons()
                    else:
                        st.error("❌ 신청 중 오류가 발생했습니다. 다시 시도해주세요.")

if __name__ == "__main__":
    main()
