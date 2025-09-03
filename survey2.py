import streamlit as st
import requests
from datetime import datetime
import re
import os

st.set_page_config(page_title="유아플랜 정책자금 2차 심화진단", page_icon="📝", layout="centered")

# ---- 유틸 함수 ----
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone_from_digits(d: str) -> str:
    """11자리 전화번호 포맷"""
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def format_biz_no(d: str) -> str:
    """10자리 사업자번호 포맷"""
    if len(d) == 10:
        return f"{d[0:3]}-{d[3:5]}-{d[5:10]}"
    return d

RELEASE_VERSION = "v2025-09-03-fixed"

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwH8OKYidK3GRtcx5lTvvmih6iTidS0yhuoSu3DcWn8WPl_LZ6gBcnbZHvqDksDX7DD/exec"

# API token with fallback
try:
    API_TOKEN = os.getenv("API_TOKEN_2")
    if not API_TOKEN:
        API_TOKEN = st.secrets.get("API_TOKEN_2", "youareplan_stage2")
except:
    API_TOKEN = "youareplan_stage2"  # fallback

# KakaoTalk Channel
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"{KAKAO_CHANNEL_URL}/chat"

# 수정된 CSS (문제 원인 제거)
st.markdown("""
<style>
  /* 기본 설정 */
  html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
  
  /* 색상 변수 */
  :root {
    --gov-navy: #002855;
    --gov-blue: #005BAC;
    --gov-border: #e1e5eb;
    --primary-color: #002855 !important;
  }
  
  /* 사이드바 숨김 */
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="collapsedControl"] { display: none !important; }
  
  /* 헤더 스타일 */
  .gov-topbar {
    width: 100%;
    background: var(--gov-navy);
    color: #fff;
    font-size: 13px;
    padding: 8px 14px;
    letter-spacing: 0.2px;
    border-bottom: 3px solid var(--gov-blue);
    margin-bottom: 16px;
  }
  
  .gov-hero {
    padding: 16px 0 8px 0;
    border-bottom: 1px solid var(--gov-border);
    margin-bottom: 16px;
  }
  
  .gov-hero h2 {
    color: var(--gov-navy);
    margin: 0 0 6px 0;
    font-weight: 700;
  }
  
  .gov-hero p {
    color: #4b5563;
    margin: 0;
  }
  
  /* 제출 버튼 */
  div[data-testid="stFormSubmitButton"] button {
    background: #002855 !important;
    border: 1px solid #002855 !important;
    color: #ffffff !important;
    font-weight: 600;
    padding: 12px 24px;
    border-radius: 6px;
    width: 100%;
  }
  
  div[data-testid="stFormSubmitButton"] button:hover {
    background: #001a3a !important;
  }
  
  /* 입력창 스타일 */
  .stTextInput > div > div > input,
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextArea > div > div > textarea,
  .stDateInput > div > div > input {
    border: 1px solid var(--gov-border) !important;
    border-radius: 6px !important;
    background: #ffffff !important;
    padding: 8px 12px !important;
  }
  
  /* 체크박스 */
  .stCheckbox {
    padding: 12px 14px !important;
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    margin: 4px 0 !important;
  }
  
  /* CTA 버튼 */
  .cta-wrap {
    margin-top: 20px;
    padding: 16px;
    border: 1px solid var(--gov-border);
    border-radius: 8px;
    background: #f8f9fa;
    text-align: center;
  }
  
  .cta-btn {
    display: inline-block;
    font-weight: 700;
    text-decoration: none;
    padding: 12px 24px;
    border-radius: 10px;
    background: #FEE500;
    color: #3C1E1E;
    margin-top: 8px;
  }
  
  .cta-btn:hover {
    background: #FFD700;
    text-decoration: none;
  }
  
  /* 폼 스타일링 */
  .main-form {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
  }
  
  .form-section {
    margin-bottom: 24px;
    padding: 16px;
    border: 1px solid var(--gov-border);
    border-radius: 8px;
    background: #ffffff;
  }
  
  .section-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--gov-navy);
    margin-bottom: 12px;
    border-bottom: 2px solid var(--gov-blue);
    padding-bottom: 8px;
  }
</style>
""", unsafe_allow_html=True)

def save_to_google_sheet(data, timeout_sec: int = 15, retries: int = 3, test_mode: bool = False):
    """Google Apps Script로 데이터 전송 (개선된 버전)"""
    if test_mode:
        st.info("🧪 테스트 모드: 실제 저장은 생략됩니다.")
        return {"status": "test", "message": "테스트 모드 - 저장 생략"}

    for attempt in range(retries + 1):
        try:
            # 데이터에 토큰 추가
            payload = {**data, 'token': API_TOKEN, 'timestamp': datetime.now().isoformat()}
            
            # 요청 보내기
            response = requests.post(
                APPS_SCRIPT_URL,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                timeout=timeout_sec,
            )
            
            # 응답 확인
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') == 'success':
                return result
            else:
                st.error(f"📤 서버 응답 오류: {result.get('message', '알 수 없는 오류')}")
                if attempt < retries:
                    st.info(f"🔄 재시도 중... ({attempt + 1}/{retries})")
                    continue
                return result
                
        except requests.exceptions.Timeout:
            if attempt < retries:
                st.warning(f"⏰ 요청 시간 초과. 재시도 중... ({attempt + 1}/{retries})")
                continue
            else:
                st.error("❌ 요청 시간 초과. 네트워크 상태를 확인하고 다시 시도해주세요.")
                
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                st.warning(f"🔄 연결 오류. 재시도 중... ({attempt + 1}/{retries})")
                continue
            else:
                st.error(f"❌ 네트워크 오류: {str(e)}")
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류: {str(e)}")
            break
            
    return {"status": "error", "message": "최대 재시도 횟수 초과"}

def main():
    # 헤더
    st.markdown("""
    <div class="gov-topbar">🏛️ 대한민국 정부 협력 서비스</div>
    <div class="gov-hero">
        <h2>정부 지원금·정책자금 심화 진단</h2>
        <p>정밀 분석 및 서류 준비를 위한 상세 정보 입력</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 안내 메시지
    st.info("✅ **1차 상담 완료** 후 진행하는 심화 진단 절차입니다.")
    
    # 쿼리 파라미터 확인 (테스트 모드)
    try:
        qp = st.query_params
        is_test_mode = qp.get("test", "").lower() == "true"
    except:
        is_test_mode = False

    if is_test_mode:
        st.warning("⚠️ **테스트 모드** - 실제 데이터는 저장되지 않습니다.")

    # 세션 상태 초기화
    if 'phone2_input' not in st.session_state:
        st.session_state.phone2_input = ""
    if 'biz_no_input' not in st.session_state:
        st.session_state.biz_no_input = ""
    if 'submitted_2' not in st.session_state:
        st.session_state.submitted_2 = False
    
    # 메인 폼
    st.markdown('<div class="main-form">', unsafe_allow_html=True)
    
    with st.form("second_survey", clear_on_submit=False):
        st.markdown("### 📝 2차 설문 - 상세 정보")
        
        # A. 기본 정보 섹션
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">👤 기본 정보</div>', unsafe_allow_html=True)
        
        name = st.text_input("**성함** (필수)", placeholder="홍길동", key="name_input")
        
        st.text_input(
            "**연락처** (필수)",
            key="phone2_input",
            placeholder="01000000000 또는 010-0000-0000",
            help="제출 시 010-0000-0000 형식으로 자동 변환됩니다."
        )
        
        email = st.text_input("**이메일** (선택)", placeholder="email@example.com", key="email_input")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # B. 사업 정보 섹션
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🏢 사업 정보</div>', unsafe_allow_html=True)
        
        st.text_input(
            "**사업자등록번호** (필수)",
            key="biz_no_input",
            placeholder="0000000000 또는 000-00-00000",
            help="제출 시 000-00-00000 형식으로 자동 변환됩니다."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            startup_date = st.date_input(
                "**사업 시작일** (필수)", 
                min_value=datetime(1900, 1, 1),
                max_value=datetime.now(),
                format="YYYY-MM-DD"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)

        # C. 재무 현황 섹션
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">💰 재무 현황</div>', unsafe_allow_html=True)
        
        st.markdown("**최근 3년간 연매출액** (단위: 만원)")
        current_year = datetime.now().year
        
        col_y1, col_y2, col_y3 = st.columns(3)
        with col_y1:
            revenue_y1 = st.text_input(f"**{current_year}년**", placeholder="예: 5000")
        with col_y2:
            revenue_y2 = st.text_input(f"**{current_year-1}년**", placeholder="예: 3500")
        with col_y3:
            revenue_y3 = st.text_input(f"**{current_year-2}년**", placeholder="예: 2000")
        
        st.info("💡 매출액은 정책자금 한도 산정의 핵심 기준입니다.")
        st.markdown('</div>', unsafe_allow_html=True)

        # D. 기술/인증 섹션
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔬 기술·인증 보유</div>', unsafe_allow_html=True)
        
        ip_options = ["특허 보유", "실용신안 보유", "디자인 등록 보유", "해당 없음"]
        ip_status = st.multiselect("**지식재산권**", ip_options, placeholder="해당되는 항목을 모두 선택하세요")
        
        research_lab = st.radio("**기업부설연구소**", ["보유", "미보유"], horizontal=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # E. 자금 계획 섹션
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">💵 자금 활용 계획</div>', unsafe_allow_html=True)
        
        funding_purpose = st.multiselect(
            "**자금 용도**", 
            ["시설자금", "운전자금", "R&D자금", "기타"],
            placeholder="해당되는 용도를 모두 선택하세요"
        )
        
        detailed_plan = st.text_area(
            "**상세 활용 계획**", 
            placeholder="예시: 생산설비 구입 2억원, 원자재 구매 1억원, 인건비 5천만원",
            height=100
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # F. 리스크 체크 섹션
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⚠️ 리스크 확인</div>', unsafe_allow_html=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox("**세금 체납 여부**", ["체납 없음", "체납 있음", "분납 중"])
        with col_b:
            credit_status = st.selectbox("**금융 연체 여부**", ["연체 없음", "30일 미만", "30일 이상"])
        
        business_status = st.selectbox("**영업 상태**", ["정상 영업", "휴업", "폐업 예정"])
        
        # 리스크 경고 메시지
        risk_msgs = []
        if tax_status != "체납 없음": 
            risk_msgs.append("세금 체납")
        if credit_status != "연체 없음": 
            risk_msgs.append("금융 연체")
        if business_status != "정상 영업": 
            risk_msgs.append("휴/폐업 상태")
            
        if risk_msgs:
            st.error(f"🚨 **지원 제한 사항**: {', '.join(risk_msgs)}")
            st.info("💡 해당 사항이 있어도 일부 정책자금은 지원 가능할 수 있습니다.")
            
        st.markdown('</div>', unsafe_allow_html=True)

        # G. 동의 섹션
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📋 개인정보 동의</div>', unsafe_allow_html=True)
        
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("**개인정보 수집·이용 동의** (필수)")
        with col_agree2:
            marketing_agree = st.checkbox("**마케팅 정보 수신 동의** (선택)")
            
        st.markdown('</div>', unsafe_allow_html=True)

        # 제출 버튼
        submitted = st.form_submit_button("📤 **2차 설문 제출하기**", use_container_width=True)

        # 폼 제출 처리
        if submitted and not st.session_state.submitted_2:
            # 필수 필드 검증
            phone_val = st.session_state.get("phone2_input", "").strip()
            biz_val = st.session_state.get("biz_no_input", "").strip()
            name_val = name.strip()

            if not all([name_val, phone_val, biz_val, privacy_agree]):
                st.error("❌ **필수 항목을 모두 입력해주세요!**")
                st.stop()
            
            # 전화번호 및 사업자번호 최종 포맷팅
            d_phone = _digits_only(phone_val)
            formatted_phone = format_phone_from_digits(d_phone) if d_phone else phone_val

            d_biz = _digits_only(biz_val)
            formatted_biz = format_biz_no(d_biz) if d_biz else biz_val
            
            # 제출 상태 설정
            st.session_state.submitted_2 = True
            
            # 데이터 준비
            survey_data = {
                'type': '2차설문',
                'name': name_val,
                'phone': formatted_phone,
                'email': email,
                'biz_reg_no': formatted_biz,
                'startup_date': startup_date.strftime('%Y-%m-%d'),
                'revenue_y1': revenue_y1.strip(),
                'revenue_y2': revenue_y2.strip(),
                'revenue_y3': revenue_y3.strip(),
                'ip_status': ', '.join(ip_status) if ip_status else '해당 없음',
                'research_lab_status': research_lab,
                'funding_purpose': ', '.join(funding_purpose) if funding_purpose else '미입력',
                'detailed_funding': detailed_plan.strip(),
                'tax_status': tax_status,
                'credit_status': credit_status,
                'business_status': business_status,
                'privacy_agree': privacy_agree,
                'marketing_agree': marketing_agree,
                'release_version': RELEASE_VERSION,
                'submission_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 데이터 저장
            with st.spinner("📤 제출 중입니다..."):
                result = save_to_google_sheet(survey_data, test_mode=is_test_mode)

            if result.get('status') in ('success', 'test'):
                st.success("✅ **2차 설문 제출이 완료되었습니다!**")
                st.info("📞 전문가가 심층 분석 후 **2-3일 이내**에 연락드립니다.")
                
                # 카카오톡 상담 안내
                st.markdown(f"""
                <div class="cta-wrap">
                    <h4>💬 추가 문의사항이 있으시나요?</h4>
                    <a class="cta-btn" href="{KAKAO_CHAT_URL}" target="_blank">
                        💛 카카오톡으로 전문가 상담받기
                    </a>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.error("❌ **제출 실패**: 다시 시도해주세요.")
                st.session_state.submitted_2 = False
                if not is_test_mode:
                    st.info("🔄 문제가 지속되면 새로고침 후 다시 시도해주세요.")

    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()