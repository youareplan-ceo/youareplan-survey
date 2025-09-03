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

RELEASE_VERSION = "v2025-09-03-emergency-fix"

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwH8OKYidK3GRtcx5lTvvmih6iTidS0yhuoSu3DcWn8WPl_LZ6gBcnbZHvqDksDX7DD/exec"

# API token with fallback (안전하게 처리)
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

# 안전한 CSS (분리해서 적용)
st.markdown("""
<style>
  /* 폰트 */
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"]  {
    font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  /* 색상 변수 */
  :root {
    --gov-navy:#002855;
    --gov-blue:#005BAC;
    --gov-gray:#f5f7fa;
    --gov-border:#e1e5eb;
    --gov-danger:#D32F2F;
    --primary-color:#002855 !important;
  }
  
  /* 사이드바 숨김 */
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="collapsedControl"] { display: none !important; }

  /* 번역 차단 및 링크 색상 */
  .notranslate,[translate="no"]{ translate: no !important; }
  .stApp * { translate: no !important; }
  a { color: var(--gov-blue) !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  /* 헤더 */
  .gov-topbar{
    width:100%;
    background:var(--gov-navy);
    color:#fff;
    font-size:13px;
    padding:8px 14px;
    letter-spacing:0.2px;
    border-bottom:3px solid var(--gov-blue);
  }
  .gov-hero{
    padding:16px 0 8px 0;
    border-bottom:1px solid var(--gov-border);
    margin-bottom:8px;
  }
  .gov-hero h2{
    color:var(--gov-navy);
    margin:0 0 6px 0;
    font-weight:700;
  }
  .gov-hero p{
    color:#4b5563;
    margin:0;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  /* 제출 버튼: 네이비 고정 + 텍스트/아이콘 흰색 강제 (모든 상태) */
  button[kind="primary"],
  button[data-testid="baseButton-primary"],
  .stButton > button[kind="primary"],
  div[data-testid="stFormSubmitButton"] button,
  div[data-testid="stFormSubmitButton"] > button {
    background:#002855 !important;
    border:1px solid #002855 !important;
    color:#ffffff !important;
    box-shadow:none !important;
  }
  /* 버튼 내부의 모든 자식 텍스트/아이콘 흰색 유지 */
  div[data-testid="stFormSubmitButton"] button *,
  .stButton > button[kind="primary"] *,
  button[kind="primary"] *,
  button[data-testid="baseButton-primary"] * {
    color:#ffffff !important;
    fill:#ffffff !important;
  }
  /* hover/active/focus 도 동일 톤 유지 */
  button[kind="primary"]:hover,
  button[data-testid="baseButton-primary"]:hover,
  .stButton > button[kind="primary"]:hover,
  div[data-testid="stFormSubmitButton"] button:hover,
  div[data-testid="stFormSubmitButton"] button:active,
  div[data-testid="stFormSubmitButton"] button:focus {
    background:#002855 !important;
    border-color:#002855 !important;
    color:#ffffff !important;
    filter:brightness(0.95) !important;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  /* 입력창 내부 input/textarea 자체 */
  .stTextInput > div > div > input,
  .stTextArea > div > div > textarea,
  .stDateInput > div > div input {
    border:1px solid var(--gov-border) !important;
    border-radius:6px !important;
    background:#ffffff !important;
    color:#111111 !important;
  }

  /* 선택 위젯(BaseWeb) 컨테이너 */
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stDateInput > div > div,
  .stTextInput > div > div,
  .stTextArea > div > div {
    background:#ffffff !important;
    border:1px solid var(--gov-border) !important;
    border-radius:6px !important;
    box-shadow:0 1px 2px rgba(16,24,40,.04) !important;
  }

  /* BaseWeb 드롭다운 본체 (모바일 키보드와 겹침 방지 포함) */
  div[data-baseweb="select"] > div {
    background:#ffffff !important;
    color:#111111 !important;
  }
  @media (max-width: 768px){
    div[data-baseweb="popover"]{z-index:10000 !important}
    div[data-baseweb="popover"] div[role="listbox"]{max-height:38vh !important;overscroll-behavior:contain}
  }

  /* placeholder 가독성 */
  ::placeholder, input::placeholder, textarea::placeholder { color:#9aa0a6 !important; opacity:1 !important; }

  /* iOS/Chrome 자동완성 노란 배경 덮기 */
  input:-webkit-autofill,
  textarea:-webkit-autofill,
  select:-webkit-autofill {
    -webkit-text-fill-color:#111111 !important;
    box-shadow:0 0 0px 1000px #ffffff inset !important;
    transition: background-color 5000s ease-in-out 0s !important;
  }

  /* 체크박스 컨테이너 (동의 영역) */
  .stCheckbox {
    padding:12px 14px !important;
    border:1px solid var(--gov-border) !important;
    border-radius:8px !important;
    background:#ffffff !important;
  }

  /* 라이트 모드 강제 */
  :root { color-scheme: light; }
  html, body, .stApp { background:#ffffff !important; color:#111111 !important; }
</style>
""", unsafe_allow_html=True)

def save_to_google_sheet(data, timeout_sec: int = 12, retries: int = 2, test_mode: bool = False):
    """Google Apps Script로 데이터 전송"""
    if test_mode:
        return {"status": "test", "message": "테스트 모드 - 저장 생략"}

    last_err = None
    for attempt in range(retries + 1):
        try:
            data['token'] = API_TOKEN
            response = requests.post(
                APPS_SCRIPT_URL,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=timeout_sec,
            )
            response.raise_for_status()
            result = response.json()
            if result.get('status') == 'success':
                return result
            else:
                st.error(f"서버 응답: {result.get('message', '알 수 없는 오류')}")
                return result
        except requests.exceptions.Timeout:
            if attempt < retries:
                continue
            st.error("요청 시간 초과. 네트워크 상태를 확인해주세요.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
        break
    return {"status": "error", "message": str(last_err) if last_err else "unknown"}

def main():
    st.markdown("""
<div class="gov-topbar">대한민국 정부 협력 서비스</div>
<div class="gov-hero">
  <h2>정부 지원금·정책자금 심화 진단</h2>
  <p>정밀 분석 및 서류 준비를 위한 상세 정보 입력</p>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("##### 맞춤형 정책자금 매칭을 위해 상세 정보를 입력해주세요.")

    # 쿼리 파라미터 (안전하게 처리)
    try:
        qp = st.query_params
        is_test_mode = qp.get("test") == "true"
    except:
        is_test_mode = False

    if is_test_mode:
        st.warning("⚠️ 테스트 모드 - 실제 저장되지 않습니다.")

    st.info("✔ 1차 상담 후 진행하는 **심화 진단** 절차입니다.")
    
    with st.form("second_survey"):
        st.markdown("### 📝 2차 설문 - 상세 정보")
        
        # A. 기본 정보
        st.markdown("#### 👤 기본 정보")
        name = st.text_input("성함 (필수)", placeholder="홍길동").strip()
        phone_raw = st.text_input("연락처 (필수)", placeholder="010-0000-0000")
        st.caption("숫자만 입력하세요. 자동으로 하이픈이 추가됩니다.")
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")
        st.markdown("---")
        
        # B. 사업 정보
        st.markdown("#### 📊 사업 정보")
        biz_reg_no = st.text_input("사업자등록번호 (필수)", placeholder="000-00-00000")
        
        col1, col2 = st.columns(2)
        with col1:
            startup_date = st.date_input("사업 시작일 (필수)", 
                                        min_value=datetime(1900, 1, 1), 
                                        format="YYYY-MM-DD")
        with col2:
            st.write(" ")  # 정렬용
        
        # C. 재무 정보
        st.markdown("#### 💰 재무 현황")
        st.markdown("**최근 3년간 연매출액 (단위: 만원)**")
        current_year = datetime.now().year
        col_y1, col_y2, col_y3 = st.columns(3)
        with col_y1:
            revenue_y1 = st.text_input(f"{current_year}년", placeholder="예: 5000")
        with col_y2:
            revenue_y2 = st.text_input(f"{current_year-1}년", placeholder="예: 3500")
        with col_y3:
            revenue_y3 = st.text_input(f"{current_year-2}년", placeholder="예: 2000")
        
        st.caption("⚠️ 매출액은 정책자금 한도 산정의 기준이 됩니다.")
        st.markdown("---")

        # D. 기술/인증
        st.markdown("#### 💡 기술·인증 보유")
        ip_options = ["특허 보유", "실용신안 보유", "디자인 등록 보유", "해당 없음"]
        ip_status = st.multiselect("지식재산권", ip_options, placeholder="선택하세요")
        
        research_lab = st.radio("기업부설연구소", ["보유", "미보유"], horizontal=True)
        st.markdown("---")

        # E. 자금 계획
        st.markdown("#### 💵 자금 활용 계획")
        funding_purpose = st.multiselect("자금 용도", 
                                        ["시설자금", "운전자금", "R&D자금", "기타"],
                                        placeholder="선택하세요")
        
        detailed_plan = st.text_area("상세 활용 계획", 
                                     placeholder="예: 생산설비 2억, 원자재 구매 1억")
        st.markdown("---")
        
        # F. 리스크 체크
        st.markdown("#### 🚨 리스크 확인")
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox("세금 체납", ["체납 없음", "체납 있음", "분납 중"])
        with col_b:
            credit_status = st.selectbox("금융 연체", ["연체 없음", "30일 미만", "30일 이상"])
        
        business_status = st.selectbox("영업 상태", ["정상 영업", "휴업", "폐업 예정"])
        
        risk_msgs = []
        if tax_status != "체납 없음": risk_msgs.append("세금 체납")
        if credit_status != "연체 없음": risk_msgs.append("금융 연체")
        if business_status != "정상 영업": risk_msgs.append("휴/폐업")
        if risk_msgs:
            st.warning(f"지원 제한 사항: {', '.join(risk_msgs)}")
        st.markdown("---")

        # G. 동의
        st.markdown("#### 🤝 동의")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)")
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")

        submitted = st.form_submit_button("📩 2차 설문 제출")

        if submitted:
            # 전화번호 포맷
            digits = _digits_only(phone_raw)
            formatted_phone = format_phone_from_digits(digits) if len(digits) == 11 else phone_raw
            
            # 사업자번호 포맷
            biz_digits = _digits_only(biz_reg_no)
            formatted_biz = format_biz_no(biz_digits) if len(biz_digits) == 10 else biz_reg_no
            
            # 유효성 검사
            if not all([name, formatted_phone, formatted_biz, privacy_agree]):
                st.error("필수 항목을 모두 입력해주세요.")
            else:
                with st.spinner("제출 중..."):
                    survey_data = {
                        'name': name,
                        'phone': formatted_phone,
                        'email': email,
                        'biz_reg_no': formatted_biz,
                        'startup_date': startup_date.strftime('%Y-%m'),
                        'revenue_y1': revenue_y1,
                        'revenue_y2': revenue_y2,
                        'revenue_y3': revenue_y3,
                        'ip_status': ', '.join(ip_status) if ip_status else '해당 없음',
                        'research_lab_status': research_lab,
                        'funding_purpose': ', '.join(funding_purpose) if funding_purpose else '미입력',
                        'detailed_funding': detailed_plan,
                        'tax_status': tax_status,
                        'credit_status': credit_status,
                        'business_status': business_status,
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree,
                        'release_version': RELEASE_VERSION
                    }
                    
                    result = save_to_google_sheet(survey_data, test_mode=is_test_mode)

                    if result.get('status') in ('success', 'test'):
                        st.success("✅ 2차 설문 제출 완료!")
                        st.info("전문가가 심층 분석 후 연락드립니다.")
                        
                        st.markdown(f"""
                        <div style="margin-top:10px;padding:12px;border:1px solid #e1e5eb;border-radius:8px;background:#fafafa">
                            <a href="{KAKAO_CHAT_URL}" target="_blank" 
                               style="display:block;text-align:center;font-weight:700;text-decoration:none;padding:12px 16px;border-radius:10px;background:#FEE500;color:#3C1E1E">
                                💬 전문가에게 문의하기
                            </a>
                        </div>
                        """, unsafe_allow_html=True)

                    else:
                        st.error("❌ 제출 실패. 다시 시도해주세요.")

if __name__ == "__main__":
    main()