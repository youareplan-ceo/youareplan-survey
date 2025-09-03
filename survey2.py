import streamlit as st
import requests
from datetime import datetime
import re
import random
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

def _phone_on_change():
    raw = st.session_state.get("phone_input_2", "")
    d = _digits_only(raw)
    st.session_state["phone_input_2"] = format_phone_from_digits(d)

# 사업자번호 입력 시 숫자만 허용하고 10자리일 때 자동 하이픈 적용
def on_change_biz_reg_no():
    """사업자번호 입력 시 숫자만 허용하고 10자리일 때 자동 하이픈 적용"""
    raw = st.session_state.get("biz_reg_no", "")
    digits = _digits_only(raw)
    if len(digits) > 10:
        digits = digits[:10]
    if len(digits) == 10:
        st.session_state["biz_reg_no"] = format_biz_no(digits)
    else:
        st.session_state["biz_reg_no"] = digits

RELEASE_VERSION = "v2025-09-03-1"

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

# 기본 CSS (1차와 동일)
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
  }

  /* 자동완성 배경 제거 */
  input:-webkit-autofill {
    -webkit-text-fill-color:#111111 !important;
    box-shadow: 0 0 0px 1000px #ffffff inset !important;
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
  html, body, .stApp {
    background: #ffffff !important;
    color: #111111 !important;
  }

  /* CTA 버튼 */
  .cta-wrap{margin-top:10px;padding:12px;border:1px solid var(--gov-border);border-radius:8px;background:#fafafa}
  .cta-btn{display:block;text-align:center;font-weight:700;text-decoration:none;padding:12px 16px;border-radius:10px}
  .cta-primary{background:#FEE500;color:#3C1E1E}
  .cta-secondary{background:#fff;color:#005BAC;border:1px solid #005BAC}
</style>
""", unsafe_allow_html=True)

# Submit 버튼 강제 네이비 (통합 선택자)
st.markdown("""
<style>
  /* 제출 버튼 네이비 고정 */
  div[data-testid="stFormSubmitButton"] button,
  div[data-testid="stFormSubmitButton"] button *,
  button[kind="primary"],
  button[kind="primary"] * {
    background:#002855 !important;
    border:1px solid #002855 !important;
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

def main():
    st.markdown("""
<div class="gov-topbar">대한민국 정부 협력 서비스</div>
<div class="gov-hero">
  <h2>정부 지원금·정책자금 심화 진단</h2>
  <p>정밀 분석 및 서류 준비를 위한 상세 정보 입력</p>
</div>
""", unsafe_allow_html=True)
    
    st.markdown("##### 맞춤형 정책자금 매칭을 위해 상세 정보를 입력해주세요.")

    is_test_mode = (_get_qp("test") == "true")
    # 1차 설문 접수번호(rid) 브리지: ?rid=YPYYYYMMDD-XXXX 로 전달된 값을 읽어 2차 저장 시 함께 전송
    parent_receipt_no = _get_qp("rid")
    if is_test_mode:
        st.warning("⚠️ 테스트 모드 - 실제 저장되지 않습니다.")

    st.info("✔ 1차 상담 후 진행하는 **심화 진단** 절차입니다.")

    # 세션 상태 초기화 (사업자번호)
    if "biz_reg_no" not in st.session_state:
        st.session_state["biz_reg_no"] = ""
    if "phone_input_2" not in st.session_state:
        st.session_state["phone_input_2"] = ""
    
    with st.form("second_survey"):
        if 'submitted' not in st.session_state:
            st.session_state.submitted = False

        st.markdown("### 📝 2차 설문 - 상세 정보")

        # A. 기본 정보 (필수 우선)
        st.markdown("#### 👤 기본 정보 (필수)")
        name = st.text_input("성함 (필수)", placeholder="홍길동").strip()
        st.text_input(
            "연락처 (필수)",
            key="phone_input_2",
            placeholder="010-0000-0000",
            help="숫자만 입력하면 자동으로 하이픈(-)이 적용됩니다.",
            on_change=_phone_on_change,
        )
        # 사업자등록번호: 숫자만 입력해도 자동 하이픈
        biz_reg_no = st.text_input(
            "사업자등록번호 (필수)",
            key="biz_reg_no",
            placeholder="0000000000",
            help="숫자만 입력하세요. 10자리 입력 시 자동으로 000-00-00000 형식으로 변환됩니다.",
            on_change=on_change_biz_reg_no
        )
        col1, col2 = st.columns(2)
        with col1:
            startup_date = st.date_input(
                "사업 시작일 (필수)",
                min_value=datetime(1900, 1, 1),
            )
        with col2:
            st.write(" ")
        st.markdown("---")

        # D. 리스크 체크 (필수)
        st.markdown("#### 🚨 리스크 확인 (필수)")
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

        # 선택 항목 (아래쪽)
        st.markdown("#### 📧 연락처 (선택)")
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")

        st.markdown("#### 💰 재무 현황 (선택)")
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

        st.markdown("#### 💡 기술·인증 보유 (선택)")
        ip_options = ["특허 보유", "실용신안 보유", "디자인 등록 보유", "해당 없음"]
        ip_status = st.multiselect("지식재산권", ip_options, placeholder="선택하세요")
        research_lab = st.radio("기업부설연구소", ["보유", "미보유"], horizontal=True)
        st.markdown("---")

        st.markdown("#### 💵 자금 활용 계획 (선택)")
        funding_purpose = st.multiselect(
            "자금 용도",
            ["시설자금", "운전자금", "R&D자금", "기타"],
            placeholder="선택하세요"
        )
        detailed_plan = st.text_area("상세 활용 계획", placeholder="예: 생산설비 2억, 원자재 구매 1억")
        st.markdown("---")

        # G. 동의
        st.markdown("#### 🤝 동의")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)")
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")

        submitted = st.form_submit_button("📩 2차 설문 제출")

        if submitted and not st.session_state.submitted:
            st.session_state.submitted = True

            digits = _digits_only(st.session_state.get("phone_input_2", ""))
            phone_valid = (len(digits) == 11 and digits.startswith("010"))
            formatted_phone = format_phone_from_digits(digits) if phone_valid else st.session_state.get("phone_input_2", "")

            # 사업자번호는 세션상태에서 읽기 (자동포맷 반영)
            biz_reg_no = st.session_state.get("biz_reg_no", "")
            biz_digits = _digits_only(biz_reg_no)
            formatted_biz = format_biz_no(biz_digits) if len(biz_digits) == 10 else biz_reg_no

            biz_valid = (len(biz_digits) == 10)
            if not name:
                st.error("성함을 입력해주세요.")
            if not phone_valid:
                st.error("연락처는 010으로 시작하는 11자리여야 합니다. (예: 010-1234-5678)")
            if not biz_valid:
                st.error("사업자등록번호는 숫자 10자리여야 합니다. (예: 123-45-67890)")

            # 유효성 검사 (엄격)
            if not (name and phone_valid and biz_valid and privacy_agree):
                if not privacy_agree:
                    st.error("개인정보 수집·이용 동의가 필요합니다.")
                st.session_state.submitted = False
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
                        'parent_receipt_no': parent_receipt_no,
                        'release_version': RELEASE_VERSION
                    }

                    result = save_to_google_sheet(survey_data, test_mode=is_test_mode)

                    if result.get('status') in ('success', 'test'):
                        st.success("✅ 2차 설문 제출 완료!")
                        st.info("전문가가 심층 분석 후 연락드립니다.")

                        st.markdown(f"""
                        <div class="cta-wrap">
                            <a class="cta-btn cta-primary" href="{KAKAO_CHAT_URL}" target="_blank">
                                💬 전문가에게 문의하기
                            </a>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(
                            """
<script>
(function(){
  function goBack(){
    // 1) referrer 우선
    if (document.referrer && document.referrer !== location.href) { location.replace(document.referrer); return; }
    // 2) 브라우저 히스토리
    if (history.length > 1) { history.back(); return; }
    // 3) 쿼리 파라미터 return_to
    try {
      var q = new URLSearchParams(location.search);
      var ret = q.get('return_to');
      if (ret) { location.replace(ret); return; }
    } catch(e) {}
    // 4) 기본값
    location.replace('/');
  }
  // 제출 후 짧은 지연 뒤 자동 이동
  setTimeout(goBack, 1200);
})();
</script>
""",
                            unsafe_allow_html=True,
                        )

                    else:
                        st.error("❌ 제출 실패. 다시 시도해주세요.")
                        st.session_state.submitted = False

if __name__ == "__main__":
    main()