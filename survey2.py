import streamlit as st
import requests
import json
from datetime import datetime
import re
import random
import os

# Streamlit 페이지 설정
st.set_page_config(page_title="유아플랜 2차 설문", page_icon="📝", layout="centered")

# ---- 전화번호 포맷 유틸 ----
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone_from_digits(d: str) -> str:
    """11자리(010xxxxxxxx)면 자동으로 010-0000-0000 형태로 변환"""
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d


RELEASE_VERSION = "v2_stage2"

# Apps Script URL
# 2차 설문지 전용 Apps Script URL을 사용하세요.
# (1차 설문지와 다른 URL을 사용하면 데이터가 분리되어 저장됩니다)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwH8OKYidK3GRtcx5lTvvmih6iTidS0yhuoSu3DcWn8WPl_LZ6gBcnbZHvqDksDX7DD/exec"
# API token is loaded from Streamlit secrets or environment for security
try:
    API_TOKEN = st.secrets["API_TOKEN_2"]
except Exception:
    API_TOKEN = os.getenv("API_TOKEN_2", "")
    if not API_TOKEN:
        st.warning("⚠️ API_TOKEN_2가 설정되지 않았습니다. .streamlit/secrets.toml 또는 환경변수를 확인하세요.")

# KakaoTalk Channel (real public ID)
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"{KAKAO_CHANNEL_URL}/chat"

# 번역 차단 CSS
st.markdown("""
<style>
  /* 폰트: 공공기관 느낌 (Noto Sans KR) */
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"]  {
    font-family: 'Noto Sans KR', system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial, 'Apple SD Gothic Neo', 'Noto Sans CJK KR', 'Malgun Gothic', sans-serif;
  }

  /* 기본 색상 변수 */
  :root {
    --gov-navy:#002855;      /* 진청(헤더/타이틀) */
    --gov-blue:#005BAC;      /* 포인트(버튼/링크) */
    --gov-gray:#f5f7fa;      /* 배경 */
    --gov-border:#e1e5eb;    /* 경계선 */
    --gov-danger:#D32F2F;    /* 경고/필수표시 */
  }

  /* 번역 차단 유지 */
  .notranslate,[translate="no"]{ translate: no !important; }
  .stApp * { translate: no !important; }

  /* 사이드바 모바일에서 숨김(기존 정책 유지) */
  @media (max-width: 768px) {
    [data-testid="stSidebar"] { display: none !important; }
  }

  /* 상단 관공서 느낌 헤더 */
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

  /* 버튼(제출) 관공서 파랑 */
  .stButton > button{
    background:var(--gov-blue) !important;
    color:#fff !important;
    border:1px solid var(--gov-blue) !important;
    font-weight:600;
    padding:10px 16px;
    border-radius:6px;
  }
  .stButton > button:hover{
    filter:brightness(0.95);
  }

  /* 인풋/셀렉트 테두리 및 배경 명확화 */
  .stTextInput > div > div > input,
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextArea > div > div > textarea{
    border:1px solid var(--gov-border) !important;
    border-radius:6px !important;
    background:#ffffff !important;
    box-shadow: 0 0 0 1000px #ffffff inset !important; /* 일부 브라우저에서 배경 누락 방지 */
  }

  /* 입력 placeholder 컬러 가독성 향상 */
  ::placeholder { color:#9aa0a6 !important; opacity:1 !important; }
  input::placeholder, textarea::placeholder { color:#9aa0a6 !important; }

  /* iOS/Chrome 자동완성(노란 배경) 덮어쓰기 */
  input:-webkit-autofill,
  textarea:-webkit-autofill,
  select:-webkit-autofill {
    -webkit-text-fill-color:#111111 !important;
    box-shadow: 0 0 0px 1000px #ffffff inset !important;
    transition: background-color 5000s ease-in-out 0s !important;
  }

  /* 입력창 컨테이너에 연한 배경/테두리 */
  .stTextInput > div > div,
  .stSelectbox > div,
  .stMultiSelect > div,
  .stTextArea > div {
    background:#ffffff !important;
    border:1px solid var(--gov-border) !important;
    border-radius:6px !important;
    box-shadow: 0 1px 2px rgba(16,24,40,.04) !important;
  }

  /* 체크박스 컨테이너(동의 영역) 테두리 강조 */
  .stCheckbox {
    padding:12px 14px !important;
    border:1px solid var(--gov-border) !important;
    border-radius:8px !important;
    background:#ffffff !important;
  }

  /* 필수표시(빨간점) 유틸: 레이블 뒤에 붙여 사용할 수 있도록 클래스 제공 */
  .req::after{
    content:" *";
    color:var(--gov-danger);
    font-weight:700;
  }

  /* ===== 라이트 모드 강제 적용 (디바이스 다크 모드 무시) ===== */
  :root { color-scheme: light; }
  html, body, .stApp {
    background: #ffffff !important;
    color: #111111 !important;
  }
  /* 사이드바/컨테이너도 라이트 고정 */
  [data-testid="stSidebar"] {
    background: #ffffff !important;
    color: #111111 !important;
  }
  /* 텍스트/헤딩 가독성 강화 */
  .stMarkdown, .stText, label, p,
  h1, h2, h3, h4, h5, h6 {
    color: #111111 !important;
  }
  /* 입력 요소 라이트 고정 */
  .stTextInput input,
  .stSelectbox div[data-baseweb="select"] > div,
  .stMultiSelect div[data-baseweb="select"] > div,
  .stTextArea textarea {
    background: #ffffff !important;
    color: #111111 !important;
    border-color: var(--gov-border) !important;
  }
  /* 링크 색상은 정부 포인트 블루 유지 */
  a { color: var(--gov-blue) !important; }
  /* 다크 테마 강제 무시 (일부 테마 변수에 영향) */
  [data-theme="dark"] * {
    --text-color: #111111 !important;
    --background-color: #ffffff !important;
  }

  /* ===== CTA 버튼(채팅/채널추가) 정리 ===== */
  .cta-wrap{margin-top:10px;padding:12px;border:1px solid var(--gov-border);border-radius:8px;background:#fafafa}
  .cta-btn{display:block;text-align:center;font-weight:700;text-decoration:none;padding:12px 16px;border-radius:10px}
  .cta-primary{background:#FEE500;color:#3C1E1E}
  .cta-secondary{background:#fff;color:#005BAC;border:1px solid #005BAC}
  .cta-gap{height:8px}

  /* 연락처 자동 포맷 안내 텍스트 여백 정리 */
  .phone-help{margin-top:4px;color:#6b7280;font-size:12px}
  /* === 모바일 드롭다운/키보드 충돌 완화 === */
  @media (max-width: 768px){
    /* iOS 하단 키보드가 셀렉트 리스트를 가리는 현상 방지 */
    .stApp{padding-bottom:calc(env(safe-area-inset-bottom,0px) + 220px) !important}
    /* BaseWeb popover 높이 제한 + 스크롤 가능 + 항상 위에 표시 */
    div[data-baseweb="popover"]{z-index:10000 !important}
    div[data-baseweb="popover"] div[role="listbox"]{
      max-height:38vh !important;
      overscroll-behavior:contain;
    }
  }
</style>
""", unsafe_allow_html=True)

def _get_query_params():
    """
    Streamlit v1.28+ : st.query_params (mapping[str,str])
    Older versions   : st.experimental_get_query_params (dict[str, list[str]])
    Returns a dict[str, str] normalized to single string values.
    """
    try:
        qp = st.query_params  # new API
        # qp can behave like mapping; convert to plain dict[str,str]
        return {k: str(v) for k, v in qp.items()}
    except Exception:
        # fallback to experimental (old) -> pick first item from list
        qp = st.experimental_get_query_params()
        return {k: (v[0] if isinstance(v, list) and v else "") for k, v in qp.items()}

def _get_qp(name: str, default: str = "") -> str:
    return _get_query_params().get(name, default)

def save_to_google_sheet(data, timeout_sec: int = 12, retries: int = 1, test_mode: bool = False):
    """Google Apps Script로 데이터 전송 (1차 설문지와 동일)"""
    if test_mode:
        # 테스트 모드에서는 실제 저장을 수행하지 않음
        return {"status": "test", "message": "테스트 모드 - 저장 생략"}

    last_err = None
    for attempt in range(retries + 1):
        try:
            data['token'] = API_TOKEN
            # JSON 본문 전송
            response = requests.post(
                APPS_SCRIPT_URL,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=timeout_sec,
            )
            # HTTP 에러 코드 처리
            response.raise_for_status()
            # JSON 파싱 및 상태 확인
            result = response.json()
            status = result.get('status', '')
            if status == 'success':
                return result
            else:
                # 서버가 전달한 메시지 그대로 표시
                st.error(f"서버 응답: {result.get('message', '알 수 없는 오류')}")
                return result
        except requests.exceptions.Timeout as e:
            last_err = e
            if attempt < retries:
                continue
            st.error("요청이 시간 초과되었습니다. 네트워크 상태 확인 후 다시 시도해주세요.")
        except requests.exceptions.RequestException as e:
            last_err = e
            st.error(f"요청 중 오류: {e}")
        except ValueError as e:
            last_err = e
            st.error("서버 응답을 해석하지 못했습니다(JSON 파싱 실패). 잠시 후 다시 시도해주세요.")
        break
    return {"status": "error", "message": str(last_err) if last_err else "unknown error"}

def main():
    st.markdown("""
<div class="gov-topbar">대한민국 정부 협력 서비스</div>
<div class="gov-hero">
  <h2>정부 지원금·정책자금 상담 신청</h2>
  <p>심층 상담 및 서류 준비를 위한 상세 정보 입력</p>
</div>
""", unsafe_allow_html=True)
    st.markdown("##### 서류 초안 작성을 위해 아래 항목을 정확히 입력해 주세요.")

    is_test_mode = (_get_qp("test") == "true")
    if is_test_mode:
        st.warning("⚠️ 현재 **테스트 모드**입니다. 제출해도 실제 저장되지 않습니다.")

    st.info("✔ 본 설문은 1차 상담 신청 후 **세부 진단**을 위한 절차입니다. 입력된 정보는 전문가 상담을 통해 보완됩니다.")
    
    with st.form("second_survey"):
        if 'submitted' not in st.session_state:
            st.session_state.submitted = False

        st.markdown("### 📝 2차 설문 - 상세 정보")
        st.write("전문가 상담에 앞서 필요한 핵심 정보를 입력해 주세요.")
        
        # A. 기본 정보 (1차와 동일)
        st.markdown("#### 👤 기본 정보")
        name = (st.text_input("성함 (필수)", placeholder="홍길동", key="name_input") or "").strip()
        phone_raw = st.text_input("연락처 (필수)", key="phone_input", placeholder="010-0000-0000")
        st.caption("숫자만 입력해 주세요. 제출 시 '010-0000-0000' 형식으로 자동 정리됩니다.")
        phone_error_placeholder = st.empty()
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")
        st.markdown("---")
        
        # B. 사업/재무
        st.markdown("#### 📊 사업 및 재무")
        biz_reg_no = st.text_input("사업자등록번호 (필수)", placeholder="000-00-00000")
        
        col1, col2 = st.columns(2)
        with col1:
            startup_date = st.date_input("사업 시작일 (필수)", min_value=datetime(1900, 1, 1), format="YYYY. M. D.")
        with col2:
            st.write(" ") # Align vertically
        
        st.markdown("**최근 3년간 연매출액 (단위: 만원)**")
        current_year = datetime.now().year
        col_y1, col_y2, col_y3 = st.columns(3)
        with col_y1:
            revenue_y1 = st.text_input(f"{current_year}년 매출액", placeholder="예: 5000")
        with col_y2:
            revenue_y2 = st.text_input(f"{current_year - 1}년 매출액", placeholder="예: 3500")
        with col_y3:
            revenue_y3 = st.text_input(f"{current_year - 2}년 매출액", placeholder="예: 2000")
        st.markdown("---")

        # C. 기술·인증/IP
        st.markdown("#### 💡 기술·인증/IP")
        ip_options = ["특허 보유", "실용신안 보유", "디자인 등록 보유", "해당 없음"]
        ip_status = st.multiselect("지식재산권 보유 여부", ip_options, placeholder="선택하세요")
        research_lab_status = st.radio("기업부설연구소/연구전담부서 보유 여부", ["보유", "미보유"], horizontal=True)
        st.markdown("---")

        # D. 자금 수요/우대
        st.markdown("#### 💵 자금 수요 및 우대")
        funding_purpose_options = ["시설자금", "운전자금", "기타"]
        funding_purpose = st.multiselect("필요 자금 용도", funding_purpose_options, placeholder="선택하세요")
        incentive_options = ["청년 대표", "여성 기업", "수출 실적 보유", "해당 없음"]
        incentive_status = st.multiselect("해당하는 우대 조건", incentive_options, placeholder="선택하세요")
        detailed_funding = st.text_area("필요 자금 상세 금액 또는 설명", placeholder="예: 기계 장비 도입에 2억 원, 인건비 5천만 원")
        st.markdown("---")
        
        # E. 리스크/상태 (1차와 동일)
        st.markdown("#### 🚨 리스크 및 사업 상태")
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox("세금 체납 여부", ["체납 없음", "체납 있음", "분납 중"])
        with col_b:
            credit_status = st.selectbox("금융 연체 여부", ["연체 없음", "30일 미만", "30일 이상"])
        business_status = st.selectbox("영업 상태", ["정상 영업", "휴업", "폐업 예정"])
        
        risk_msgs = []
        if tax_status != "체납 없음": risk_msgs.append("세금 체납")
        if credit_status != "연체 없음": risk_msgs.append("금융 연체")
        if business_status != "정상 영업": risk_msgs.append("휴/폐업")
        if risk_msgs:
            st.warning(f"현재 상태로는 지원에 제한이 있을 수 있습니다. ({', '.join(risk_msgs)})")
        st.markdown("---")

        # F. 동의
        st.markdown("#### 🤝 동의")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)")
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")

        submitted = st.form_submit_button("📩 2차 설문지 제출", type="primary")

        if submitted and not st.session_state.submitted:
            st.session_state.submitted = True
            # 연락처 정규화(자동 포맷된 값이 아닌 경우 대비)
            raw_phone = st.session_state.get('phone_input', '')
            digits = _digits_only(raw_phone)
            if len(digits) == 11 and digits.startswith('010'):
                normalized_phone = format_phone_from_digits(digits)
            else:
                normalized_phone = raw_phone  # 형식이 달라도 그대로 저장(2차: 보조 자료라 관대하게)
            
            # 유효성 검사
            if not name or not biz_reg_no or not privacy_agree:
                st.error("성함, 사업자등록번호, 개인정보 동의는 필수입니다.")
                st.session_state.submitted = False
            else:
                with st.spinner("정보를 제출하고 있습니다..."):
                    survey_data = {
                        'name': name,
                        'phone': normalized_phone,
                        'email': email,
                        'biz_reg_no': biz_reg_no,
                        'startup_date': startup_date.strftime('%Y-%m'),
                        'revenue_y1': revenue_y1,
                        'revenue_y2': revenue_y2,
                        'revenue_y3': revenue_y3,
                        'ip_status': ', '.join(ip_status) if ip_status else '해당 없음',
                        'research_lab_status': research_lab_status,
                        'funding_purpose': ', '.join(funding_purpose) if funding_purpose else '미입력',
                        'incentive_status': ', '.join(incentive_status) if incentive_status else '해당 없음',
                        'detailed_funding': detailed_funding,
                        'tax_status': tax_status,
                        'credit_status': credit_status,
                        'business_status': business_status,
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree
                    }
                    
                    # Google Apps Script로 데이터 전송
                    result = save_to_google_sheet(survey_data, test_mode=is_test_mode)

                    if result.get('status') in ('success', 'test'):
                        if is_test_mode:
                            st.info("🧪 테스트 모드: 저장은 수행하지 않았습니다.")
                        st.success("✅ 2차 설문지 제출이 완료되었습니다!")
                        st.info("전문가가 입력하신 정보를 바탕으로 심층 분석을 시작합니다. 곧 연락드리겠습니다.")
                        st.toast("제출이 완료되었습니다.", icon="✅")
                        st.markdown(
                            f"""
                            <div class="cta-wrap">
                                <div style="margin-bottom:8px;color:#333;">궁금한 점이 있으시면 언제든지 문의해 주세요.</div>
                                <a class="cta-btn cta-primary" href="{KAKAO_CHAT_URL}" target="_blank">💬 전문가에게 직접 문의하기</a>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        msg = result.get('message', '알 수 없는 오류로 실패했습니다. 잠시 후 다시 시도해주세요.')
                        st.error(f"❌ 제출 중 오류: {msg}")
                        st.session_state.submitted = False

if __name__ == "__main__":
    main()