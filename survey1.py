import streamlit as st
import re
import requests

def json_post(url, payload, headers=None, timeout=10, retries=0):
    headers = headers or {"Content-Type": "application/json"}
    last_err = None
    for _ in range(retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            sc = resp.status_code
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            ok = 200 <= sc < 300
            return ok, sc, data, None if ok else (
                data if isinstance(data, str) else (data.get("message") if isinstance(data, dict) else "request failed")
            )
        except Exception as e:
            last_err = str(e)
    return False, None, None, last_err

def _json_post_with_resilience(url: str, payload: dict, timeout_sec: int = 30) -> dict:
    if 'action' in payload: payload.pop('action', None)
    if not payload.get('token'):
        payload['token'] = 'youareplan'
    req_id = str(uuid4())
    ok, sc, data, err = json_post(url, payload, headers={"X-Request-ID": req_id, "Content-Type":"application/json"}, timeout=min(10, timeout_sec), retries=1)
    if ok:
        return data or {"status":"success"}
    if (sc is None) or sc==429 or (500 <= (sc or 0) <= 599):
        ok2, sc2, data2, err2 = json_post(url, payload, headers={"X-Request-ID": req_id, "Content-Type":"application/json"}, timeout=min(10, timeout_sec), retries=2)
        if ok2:
            return data2 or {"status":"success"}
        return {"status":"error", "message": err2 or err or (f"HTTP {sc2}" if sc2 else "request failed")}
    if isinstance(data, dict) and data.get('message'):
        return {"status":"error","message":str(data.get('message'))}
    return {"status":"error","message": err or (f"HTTP {sc}" if sc else "request failed")}

from uuid import uuid4
from datetime import datetime
import re
import random
import os

st.set_page_config(page_title="유아플랜 정책자금 1차 상담", page_icon="📝", layout="centered")

# ---- 브랜드 설정 ----
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

RELEASE_VERSION = "v2025-11-26-centered"

APPS_SCRIPT_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")

try:
    API_TOKEN = os.getenv("API_TOKEN")
    if not API_TOKEN:
        API_TOKEN = st.secrets.get("API_TOKEN", "youareplan")
except:
    API_TOKEN = "youareplan"

KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"{KAKAO_CHANNEL_URL}/chat"

# ---- 전화번호 포맷 ----
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone_from_digits(d: str) -> str:
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

# ==============================
# CSS 스타일 (통합 브랜드바)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] {
    font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif;
  }

  :root {
    --gov-navy: #002855;
    --gov-blue: #005BAC;
    --gov-gray: #f5f7fa;
    --gov-border: #d7dce3;
    --gov-danger: #D32F2F;
    color-scheme: light;
  }

  #MainMenu, footer { visibility: hidden !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
  
  html, body, .stApp { background: #ffffff !important; color: #111111 !important; }
  
  .block-container { max-width: 800px; margin: 0 auto !important; padding: 0 16px; }

  /* ========== 통합 브랜드바 (중앙 정렬) ========== */
  .unified-header {
    background: var(--gov-navy);
    padding: 20px 24px 16px 24px;
    text-align: center;
    border-bottom: 3px solid var(--gov-blue);
    margin-bottom: 16px;
  }
  
  .unified-header img {
    height: 56px;
    margin-bottom: 12px;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
  }
  
  .unified-header .gov-label {
    color: rgba(255,255,255,0.9);
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.5px;
  }
  
  @media (max-width: 640px) {
    .unified-header { padding: 16px 20px 14px 20px; }
    .unified-header img { height: 48px; margin-bottom: 10px; }
    .unified-header .gov-label { font-size: 12px; }
  }

  /* 히어로 섹션 */
  .gov-hero {
    padding: 20px 0 12px 0;
    border-bottom: 1px solid var(--gov-border);
    margin-bottom: 12px;
  }
  .gov-hero h2 {
    color: var(--gov-navy);
    margin: 0 0 6px 0;
    font-weight: 700;
    font-size: 24px;
  }
  .gov-hero p {
    color: #4b5563;
    margin: 0;
    font-size: 15px;
  }

  /* 입력 필드 */
  .stTextInput > div > div > input,
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextArea > div > div > textarea {
    border: 1px solid var(--gov-border) !important;
    border-radius: 6px !important;
    background: #ffffff !important;
    color: #111111 !important;
  }

  ::placeholder { color: #9aa0a6 !important; }

  /* 체크박스 */
  .stCheckbox {
    padding: 12px 14px !important;
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
    background: #ffffff !important;
  }

  /* 버튼 */
  .stButton > button,
  div[data-testid="stFormSubmitButton"] button {
    background: var(--gov-navy) !important;
    color: #fff !important;
    border: 1px solid var(--gov-navy) !important;
    font-weight: 600;
    padding: 10px 16px;
    border-radius: 6px;
  }

  div[data-testid="stFormSubmitButton"] button *,
  .stButton > button * {
    color: #ffffff !important;
    fill: #ffffff !important;
  }

  /* CTA */
  .cta-wrap { margin-top: 10px; padding: 12px; border: 1px solid var(--gov-border); border-radius: 8px; background: #fafafa; }
  .cta-btn { display: block; text-align: center; font-weight: 700; text-decoration: none; padding: 12px 16px; border-radius: 10px; }
  .cta-primary { background: #FEE500; color: #3C1E1E; }

  /* 동의 캡션 */
  .agree-caption { font-size: 12px; color: #6b7280; margin-top: 4px; min-height: 40px; line-height: 1.5; }

  /* 모바일 */
  @media (max-width: 768px) {
    .stApp { padding-bottom: calc(env(safe-area-inset-bottom,0px) + 220px) !important; }
  }
</style>
""", unsafe_allow_html=True)

def save_to_google_sheet(data, timeout_sec: int = 12, retries: int = 2, test_mode: bool = False):
    if test_mode:
        return {"status": "test", "message": "테스트 모드 - 저장 생략"}
    try:
        data['token'] = API_TOKEN
        resp = _json_post_with_resilience(APPS_SCRIPT_URL, payload=data, timeout_sec=timeout_sec)
        if isinstance(resp, dict) and resp.get('status') == 'success':
            return resp
        if isinstance(resp, dict):
            return {"status": "error", "message": resp.get('message', 'unknown')}
        return {"status": "error", "message": "bad_response"}
    except Exception as e:
        st.error(f"오류 발생: {e}")
        return {"status": "error", "message": str(e)}

# 선택 옵션
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
INDUSTRIES = ["제조업", "건설업", "도소매업(유통·온라인쇼핑몰 포함)", "숙박·음식점업", "운수·창고업(물류 포함)", "정보통신업(소프트웨어·플랫폼)", "전문·과학·기술 서비스업(디자인·광고 포함)", "사업지원·임대 서비스업", "교육서비스업", "보건업·사회복지 서비스업", "예술·스포츠·여가 서비스업", "농업·임업·어업(영농/영어조합 포함)", "환경·폐기물·에너지(신재생 포함)", "기타"]
BUSINESS_TYPES = ["예비창업자", "개인사업자", "법인사업자", "협동조합·사회적기업"]
EMPLOYEE_COUNTS = ["0명(대표만)", "1명", "2-4명", "5-9명", "10명 이상"]
REVENUES = ["매출 없음", "5천만원 미만", "5천만원~1억원", "1억원~3억원", "3억원~5억원", "5억원~10억원", "10억원~30억원", "30억원 이상"]
FUNDING_AMOUNTS = ["3천만원 미만", "3천만원~1억원", "1-3억원", "3-5억원", "5억원 이상"]
POLICY_EXPERIENCES = ["정책자금 대출 이용 경험", "신용보증 이용 경험", "정부지원사업 참여 경험", "상담만 받아봄", "경험 없음"]

def _get_query_params():
    try:
        qp = st.query_params
        return {k: str(v) for k, v in qp.items()}
    except:
        qp = st.experimental_get_query_params()
        return {k: (v[0] if isinstance(v, list) and v else "") for k, v in qp.items()}

def _get_qp(name: str, default: str = "") -> str:
    return _get_query_params().get(name, default)

def main():
    if "saving1" not in st.session_state:
        st.session_state.saving1 = False

    # ===== 통합 브랜드바 (중앙 정렬) =====
    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <div class="gov-label">대한민국 정부 협력 서비스</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
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
        policy_experience = st.multiselect("해당사항을 모두 선택하세요", POLICY_EXPERIENCES, placeholder="선택하세요")

        st.markdown("#### 🚨 지원 자격 확인 (필수)")
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox("세금 체납 여부", ["체납 없음", "체납 있음", "분납 중"], help="국세/지방세 체납 시 대부분 지원 제한")
        with col_b:
            credit_status = st.selectbox("금융 연체 여부", ["연체 없음", "30일 미만", "30일 이상"], help="금융 연체 시 정책자금 지원 제한")

        business_status = st.selectbox("사업 영위 상태", ["정상 영업", "휴업", "폐업 예정"], help="휴/폐업 시 지원 불가")

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
            st.markdown("<div class='agree-caption'>상담 확인·자격 검토·연락 목적. 보관: 상담·보고서 3년 / 로그 1년.</div>", unsafe_allow_html=True)
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")
            st.markdown("<div class='agree-caption'>신규 정책자금·지원사업 알림. 언제든지 수신 거부 가능.</div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("📩 정책자금 상담 신청", type="primary", disabled=st.session_state.get("saving1", False))
        
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
                st.session_state.saving1 = True
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
                        st.session_state.saving1 = False
                    else:
                        st.error("❌ 신청 실패. 다시 시도해주세요.")
                        st.session_state.submitted = False
                        st.session_state.saving1 = False

if __name__ == "__main__":
    main()