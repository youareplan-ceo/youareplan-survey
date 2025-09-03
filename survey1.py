import streamlit as st
import requests
from datetime import datetime
import re
import random
import os

st.set_page_config(page_title="유아플랜 정책자금 1차 상담", page_icon="📝", layout="centered")

# ---- 전화번호 포맷 유틸 ----
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone_from_digits(d: str) -> str:
    """11자리(010xxxxxxxx)면 자동으로 010-0000-0000 형태로 변환"""
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def _phone_on_change():
    # 사용자가 타이핑할 때 숫자만 남겨 하이픈 자동 삽입
    raw = st.session_state.get("phone_input", "")
    d = _digits_only(raw)
    st.session_state["phone_input"] = format_phone_from_digits(d)

RELEASE_VERSION = "v2025-09-03-1"

# Apps Script URL
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec"

# API token with fallback
try:
    API_TOKEN = os.getenv("API_TOKEN")
    if not API_TOKEN:
        API_TOKEN = st.secrets.get("API_TOKEN", "youareplan")
except:
    API_TOKEN = "youareplan"  # fallback

# KakaoTalk Channel
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"{KAKAO_CHANNEL_URL}/chat"

# 기본 CSS
st.markdown("""
<style>
  /* 폰트 */
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"]  {
    font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif;
  }

  /* 색상 변수 */
  :root {
    --gov-navy:#002855;
    --gov-blue:#005BAC;
    --gov-gray:#f5f7fa;
    --gov-border:#e1e5eb;
    --gov-danger:#D32F2F;
    --primary-color:#002855 !important;
  }

  /* 번역 차단 */
  .notranslate,[translate="no"]{ translate: no !important; }
  .stApp * { translate: no !important; }

  /* 사이드바 숨김 */
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="collapsedControl"] { display: none !important; }

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

  /* 버튼 */
  .stButton > button{
    background:var(--gov-navy) !important;
    color:#fff !important;
    border:1px solid var(--gov-navy) !important;
    font-weight:600;
    padding:10px 16px;
    border-radius:6px;
  }
  .stButton > button:hover{
    filter:brightness(0.95);
  }

  /* 입력창 */
  .stTextInput > div > div > input,
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextArea > div > div > textarea{
    border:1px solid var(--gov-border) !important;
    border-radius:6px !important;
    background:#ffffff !important;
    box-shadow: 0 0 0 1000px #ffffff inset !important;
    color:#111111 !important;           /* ← 텍스트 검정 고정 */
    caret-color:#111111 !important;      /* ← 커서 색상 고정 */
  }

  /* 입력 텍스트 가시성 강제 (다크테마 잔류/브라우저 자동완성 이슈 대응) */
  .stTextInput input,
  .stTextArea textarea,
  div[data-baseweb="select"] input,
  div[data-baseweb="select"] [contenteditable="true"] {
    color:#111111 !important;
    caret-color:#111111 !important;
    -webkit-text-fill-color:#111111 !important; /* Safari */
  }

  /* placeholder 가독성 */
  ::placeholder { color:#9aa0a6 !important; opacity:1 !important; }
  input::placeholder, textarea::placeholder { color:#9aa0a6 !important; }

  /* 자동완성 배경 제거 */
  input:-webkit-autofill,
  textarea:-webkit-autofill,
  select:-webkit-autofill{
    -webkit-text-fill-color:#111111 !important;
    box-shadow: 0 0 0px 1000px #ffffff inset !important;
    transition: background-color 5000s ease-in-out 0s !important;
  }

  /* 체크박스 */
  .stCheckbox {
    padding:12px 14px !important;
    border:1px solid var(--gov-border) !important;
    border-radius:8px !important;
    background:#ffffff !important;
  }

  /* 라이트 모드 강제 */
  :root { color-scheme: light; }
  html, body, .stApp { background: #ffffff !important; color: #111111 !important; }
  [data-testid="stSidebar"] { background:#ffffff !important; color:#111111 !important; }
  /* 텍스트/레이블 가독성 강화 */
  .stMarkdown, .stText, label, p, h1, h2, h3, h4, h5, h6 { color:#111111 !important; }

  /* CTA 버튼 */
  .cta-wrap{margin-top:10px;padding:12px;border:1px solid var(--gov-border);border-radius:8px;background:#fafafa}
  .cta-btn{display:block;text-align:center;font-weight:700;text-decoration:none;padding:12px 16px;border-radius:10px}
  .cta-primary{background:#FEE500;color:#3C1E1E}
  .cta-secondary{background:#fff;color:#005BAC;border:1px solid #005BAC}

  /* 모바일 드롭다운/키보드 충돌 완화 */
  @media (max-width: 768px){
    .stApp{padding-bottom:calc(env(safe-area-inset-bottom,0px) + 220px) !important}
    div[data-baseweb="popover"]{z-index:10000 !important}
    div[data-baseweb="popover"] div[role="listbox"]{
      max-height:38vh !important;
      overscroll-behavior:contain;
    }
  }
</style>
""", unsafe_allow_html=True)

# Submit 버튼 강제 네이비
st.markdown("""
<style>
  /* 제출 버튼 네이비 고정 */
  div[data-testid="stFormSubmitButton"] button,
  button[kind="primary"] {
    background:#002855 !important;
    border:1px solid #002855 !important;
    color:#ffffff !important;
  }
  
  /* 버튼 내부 텍스트 흰색 */
  div[data-testid="stFormSubmitButton"] button *,
  button[kind="primary"] * {
    color:#ffffff !important;
    fill:#ffffff !important;
  }
  
  /* 호버 상태 */
  div[data-testid="stFormSubmitButton"] button:hover {
    background:#001a3a !important;
    border:1px solid #001a3a !important;
  }
</style>
""", unsafe_allow_html=True)

# --- 강제: 제출 버튼/아이콘 텍스트 항상 흰색 & 기본 프라이머리 색상 고정 ---
st.markdown("""
<style>
  :root { --primary-color:#002855 !important; } /* Streamlit theme primary */

  button[kind="primary"],
  button[data-testid="baseButton-primary"],
  .stButton > button[kind="primary"],
  .stButton button[kind="primary"],
  div[data-testid="stFormSubmitButton"] button,
  div[data-testid="stFormSubmitButton"] > button {
    background:#002855 !important;
    border:1px solid #002855 !important;
    color:#ffffff !important;
    box-shadow:none !important;
  }

  div[data-testid="stFormSubmitButton"] button *,
  .stButton > button[kind="primary"] *,
  button[kind="primary"] *,
  button[data-testid="baseButton-primary"] * {
    color:#ffffff !important;
    fill:#ffffff !important;
  }

  div[data-testid="stFormSubmitButton"] button:focus *,
  div[data-testid="stFormSubmitButton"] button:active *,
  .stButton > button[kind="primary"]:focus *,
  .stButton > button[kind="primary"]:active * {
    color:#ffffff !important;
    fill:#ffffff !important;
  }

  button[kind="primary"]:hover,
  button[data-testid="baseButton-primary"]:hover,
  .stButton > button[kind="primary"]:hover,
  div[data-testid="stFormSubmitButton"] button:hover,
  div[data-testid="stFormSubmitButton"] > button:hover {
    filter: brightness(0.95) !important;
  }
</style>
""", unsafe_allow_html=True)

def _get_query_params():
    """쿼리 파라미터 가져오기"""
    try:
        qp = st.query_params
        return {k: str(v) for k, v in qp.items()}
    except:
        qp = st.experimental_get_query_params()
        return {k: (v[0] if isinstance(v, list) and v else "") for k, v in qp.items()}

def _get_qp(name: str, default: str = "") -> str:
    return _get_query_params().get(name, default)

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

# 선택 옵션들
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산",
           "세종", "경기", "강원", "충북", "충남", "전북", "전남",
           "경북", "경남", "제주"]

INDUSTRIES = [
    "제조업", "건설업", "도소매업(유통·온라인쇼핑몰 포함)", "숙박·음식점업",
    "운수·창고업(물류 포함)", "정보통신업(소프트웨어·플랫폼)",
    "전문·과학·기술 서비스업(디자인·광고 포함)", "사업지원·임대 서비스업",
    "교육서비스업", "보건업·사회복지 서비스업", "예술·스포츠·여가 서비스업",
    "농업·임업·어업(영농/영어조합 포함)", "환경·폐기물·에너지(신재생 포함)",
    "기타"
]

BUSINESS_TYPES = ["예비창업자", "개인사업자", "법인사업자", "협동조합·사회적기업"]
EMPLOYEE_COUNTS = ["0명(대표만)", "1명", "2-4명", "5-9명", "10명 이상"]
REVENUES = ["매출 없음", "5천만원 미만", "5천만원~1억원", "1억원~3억원", 
            "3억원~5억원", "5억원~10억원", "10억원~30억원", "30억원 이상"]
FUNDING_AMOUNTS = ["3천만원 미만", "3천만원~1억원", "1-3억원", "3-5억원", "5억원 이상"]
POLICY_EXPERIENCES = [
    "정책자금 대출 이용 경험",
    "신용보증 이용 경험",
    "정부지원사업 참여 경험",
    "상담만 받아봄",
    "경험 없음"
]

def main():
    st.markdown("""
<div class="gov-topbar">대한민국 정부 협력 서비스</div>
<div class="gov-hero">
  <h2>정부 지원금·정책자금 상담 신청</h2>
  <p>중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 지원</p>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("##### 기초 상담을 위해 아래 항목을 정확히 입력해 주세요.")

    is_test_mode = (_get_qp("test") == "true")
    if is_test_mode:
        st.warning("⚠️ 테스트 모드 - 실제 저장되지 않습니다.")

    st.info("✔ 정책자금 지원 가능성 검토를 위한 **기초 상담 절차**입니다.")
    
    st.markdown("### 📝 1차 설문 - 기본 정보")
    st.write("3분이면 완료! 상담 시 수정 가능합니다.")

    with st.form("first_survey"):
        if 'submitted' not in st.session_state:
            st.session_state.submitted = False

        # ── 기본 인적사항 (폼 내부로 이동) ──
        name = st.text_input("👤 성함 (필수)", placeholder="홍길동", key="name_input").strip()
        phone_input = st.text_input("📞 연락처 (필수)", key="phone_input", placeholder="010-0000-0000")
        phone_error_placeholder = st.empty()
        st.caption("숫자만 입력하세요. 제출 시 010-0000-0000 형식으로 자동 포맷됩니다.")

        col1, col2 = st.columns(2)
        with col1:
            region = st.selectbox("🏢 사업장 지역 (필수)", REGIONS)
            industry = st.selectbox("🏭 업종 (필수)", INDUSTRIES)
            business_type = st.selectbox("📋 사업자 형태 (필수)", BUSINESS_TYPES)
        with col2:
            employee_count = st.selectbox("👥 직원 수 (필수)", EMPLOYEE_COUNTS)
            revenue = st.selectbox("💰 연간 매출 (필수)", REVENUES)
            funding_amount = st.selectbox("💵 필요 자금 (필수)", FUNDING_AMOUNTS)

        email = st.text_input("📧 이메일 (선택)", placeholder="email@example.com")
        
        st.markdown("---")
        st.markdown("#### 💼 정책자금 이용 경험 (선택)")
        policy_experience = st.multiselect(
            "해당사항을 모두 선택하세요",
            POLICY_EXPERIENCES,
            placeholder="선택하세요"
        )

        st.markdown("#### 🚨 지원 자격 확인 (필수)")
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox(
                "세금 체납 여부",
                ["체납 없음", "체납 있음", "분납 중"],
                help="국세/지방세 체납 시 대부분 지원 제한"
            )
        with col_b:
            credit_status = st.selectbox(
                "금융 연체 여부",
                ["연체 없음", "30일 미만", "30일 이상"],
                help="금융 연체 시 정책자금 지원 제한"
            )

        business_status = st.selectbox(
            "사업 영위 상태",
            ["정상 영업", "휴업", "폐업 예정"],
            help="휴/폐업 시 지원 불가"
        )

        risk_msgs = []
        if tax_status != "체납 없음": risk_msgs.append("체납")
        if credit_status != "연체 없음": risk_msgs.append("연체")
        if business_status != "정상 영업": risk_msgs.append("휴/폐업")
        if risk_msgs:
            st.warning(f"지원 제한 가능: {', '.join(risk_msgs)}")
        
        st.markdown("---")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)")
            st.caption("상담 목적. 1년 보관 후 삭제.")
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")
            st.caption("신규 정책자금 알림. 언제든 거부 가능.")

        submitted = st.form_submit_button("📩 정책자금 상담 신청", type="primary")
        
        if submitted and not st.session_state.submitted:
            st.session_state.submitted = True

            d = _digits_only(phone_input)
            formatted_phone = format_phone_from_digits(d)
            phone_valid = (len(d) == 11 and d.startswith("010"))
            
            if not phone_valid:
                phone_error_placeholder.error("연락처는 010-0000-0000 형식이어야 합니다.")

            if not name or not formatted_phone:
                st.error("성함과 연락처는 필수입니다.")
                st.session_state.submitted = False
            elif not phone_valid:
                st.error("연락처 형식을 확인해주세요.")
                st.session_state.submitted = False
            elif not privacy_agree:
                st.error("개인정보 동의는 필수입니다.")
                st.session_state.submitted = False
            else:
                with st.spinner("처리 중..."):
                    receipt_no = f"YP{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
                    
                    survey_data = {
                        'name': name,
                        'phone': formatted_phone,
                        'email': email,
                        'region': region,
                        'industry': industry,
                        'business_type': business_type,
                        'employee_count': employee_count,
                        'revenue': revenue,
                        'funding_amount': funding_amount,
                        'policy_experience': ', '.join(policy_experience) if policy_experience else '경험 없음',
                        'tax_status': tax_status,
                        'credit_status': credit_status,
                        'business_status': business_status,
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree,
                        'receipt_no': receipt_no,
                        'release_version': RELEASE_VERSION,
                    }
                    
                    result = save_to_google_sheet(survey_data, test_mode=is_test_mode)

                    if result.get('status') in ('success', 'test'):
                        st.success("✅ 상담 신청 완료!")
                        st.info(f"📋 접수번호: **{receipt_no}**")
                        st.info("📞 1영업일 내 연락드립니다.")
                        
                        st.markdown(f"""
                        <div class="cta-wrap">
                            <a class="cta-btn cta-primary" href="{KAKAO_CHANNEL_URL}" target="_blank">
                                💬 카카오 채널 문의하기
                            </a>
                        </div>
                        """, unsafe_allow_html=True)

                        # 제출 성공 후 1.2초 뒤 자동 복귀 (referrer → history.back → ?return_to → /)
                        st.markdown(
                            """
<script>
(function(){
  function goBack(){
    try {
      if (document.referrer && document.referrer !== location.href) { location.replace(document.referrer); return; }
      if (history.length > 1) { history.back(); return; }
      var q = new URLSearchParams(location.search);
      var ret = q.get('return_to');
      if (ret) { location.replace(ret); return; }
    } catch(e) {}
    location.replace('/');
  }
  setTimeout(goBack, 1200);
})();
</script>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error("❌ 신청 실패. 다시 시도해주세요.")
                        st.session_state.submitted = False

if __name__ == "__main__":
    main()