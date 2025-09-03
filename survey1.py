
import streamlit as st
import requests
import json
from datetime import datetime
import re
import random
import os

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
    st.session_state.phone_input = format_phone_from_digits(d)

RELEASE_VERSION = "v6"

# Apps Script URL
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec"  # current exec URL
# API token is loaded from Streamlit secrets or environment for security
try:
    API_TOKEN = st.secrets["API_TOKEN"]  # set in .streamlit/secrets.toml or Render env
except Exception:
    API_TOKEN = os.getenv("API_TOKEN", "")
    if not API_TOKEN:
        st.warning("⚠️ API_TOKEN이 설정되지 않았습니다. .streamlit/secrets.toml 또는 Render 환경변수를 확인하세요.")

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
    """Google Apps Script로 데이터 전송 (타임아웃/재시도/메시지 표시, 테스트 모드 지원)"""
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

# 안내용: 정책자금 지원이 어려운 업종(멘트만, 차단은 하지 않음)
DISALLOWED_INDUSTRIES = [
    "사행성/유흥/불건전 업종 (주점, 도박, 성인용품 등)",
    "부동산 임대 및 개발 관련 업종",
    "금융 및 보험업",
    "법무, 회계, 세무 등 전문 서비스업",
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

    # 테스트 모드 안내
    is_test_mode = (_get_qp("test") == "true")
    if is_test_mode:
        st.warning("⚠️ 현재 **테스트 모드**입니다. 제출해도 실제 저장되지 않습니다.")

    # 안내문: 자동 번역 끄기 안내
    st.info("✔ 본 설문은 정책자금 지원 가능성 검토를 위한 **기초 상담 절차**입니다. 입력된 정보는 관련 법령에 따라 안전하게 관리됩니다. (자동 번역 기능은 끄고 작성해 주세요)")
    
    st.markdown(
        """
        **이용 전 핵심 안내**
        - ✅ 무료 1:1 상담 (1영업일 내 연락)
        - ✅ 맞춤 매칭 리포트 제공
        - ✅ 개인정보 안전 관리(동의 철회 즉시 삭제)
        """
    )
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 💡 서비스 소개")
        st.success("✅ 전문가 무료 상담")
        st.success("✅ 맞춤형 매칭 서비스")
        
        st.markdown("---")
        st.markdown("### 📞 상담 프로세스")
        st.info("1️⃣ 3분 설문 완료\n"
                "2️⃣ 1영업일 내 전문가 연락\n"
                "3️⃣ 무료 상담 진행\n"
                "4️⃣ 맞춤 정책자금 안내")
    
    # 설문지
    st.markdown("### 📝 1차 설문 - 기본 정보")
    st.write("3분이면 끝! 잘못 입력해도 상담 시 바로잡아 드립니다.")

    # ===== 상단 기본 정보: 이름/연락처 (실시간 하이픈) =====
    name = (st.text_input("👤 성함 (필수)", placeholder="홍길동", key="name_input") or "").strip()

    # 연락처는 폼 밖에서 on_change로 실시간 하이픈 적용
    st.session_state.setdefault("phone_input", "")
    st.text_input(
        "📞 연락처 (필수)",
        key="phone_input",
        placeholder="010-0000-0000",
        on_change=_phone_on_change,
    )
    phone_error_placeholder = st.empty()
    st.caption("숫자만 입력해 주세요. 제출 시 '010-0000-0000' 형식으로 자동 정리됩니다.")
    
    with st.form("first_survey"):
        # 중복 제출 방지 플래그 초기화
        if 'submitted' not in st.session_state:
            st.session_state.submitted = False

        # 나머지 필드들은 2열 구성
        col1, col2 = st.columns(2)
        with col1:
            region = st.selectbox("🏢 사업장 지역 (필수)", REGIONS)
            industry = st.selectbox("🏭 업종 (필수)", INDUSTRIES)
            # 업종 제한 안내(멘트만, 제출은 차단하지 않음)
            st.caption("※ 일부 업종은 정책자금 지원이 제한될 수 있어요. 아래 안내를 참고해 주세요.")
            with st.expander("지원이 어려운 업종 안내"):
                st.markdown("\n".join([f"- {item}" for item in DISALLOWED_INDUSTRIES]))
            business_type = st.selectbox("📋 사업자 형태 (필수)", BUSINESS_TYPES)
        with col2:
            employee_count = st.selectbox("👥 직원 수 (필수)", EMPLOYEE_COUNTS)
            revenue = st.selectbox("💰 연간 매출 (필수)", REVENUES)
            funding_amount = st.selectbox("💵 필요 자금 (필수)", FUNDING_AMOUNTS)

        email = st.text_input("📧 이메일 (선택)", placeholder="email@example.com")
        
        # 정책자금 경험
        st.markdown("---")
        st.markdown("#### 💼 정책자금 이용 경험 (선택)")
        policy_experience = st.multiselect(
            "해당사항을 모두 선택하세요",
            POLICY_EXPERIENCES,
            help="기존 경험이 있으시면 더 정확한 상담이 가능합니다",
            placeholder="선택하세요"
        )

        # ===== 지원 자격 확인 =====
        st.markdown("#### 🚨 지원 자격 확인 (필수)")

        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox(
                "세금 체납 여부",
                ["체납 없음", "체납 있음", "분납 중"],
                help="국세/지방세 체납 시 대부분 지원 제한. 분납/완납 계획 전환으로 해결 가능"
            )
        with col_b:
            credit_status = st.selectbox(
                "금융 연체 여부",
                ["연체 없음", "30일 미만", "30일 이상"],
                help="단기 연체는 해제 후 신청 가능. 장기 연체는 제한적"
            )

        business_status = st.selectbox(
            "사업 영위 상태",
            ["정상 영업", "휴업", "폐업 예정"],
            help="휴업은 재개업 신고 후 가능, 폐업 ‘이전’까진 일부 가능"
        )

        # 화면 경고(차단 아님)
        risk_msgs = []
        if tax_status != "체납 없음":
            risk_msgs.append("체납")
        if credit_status != "연체 없음":
            risk_msgs.append("연체")
        if business_status != "정상 영업":
            risk_msgs.append("휴/폐업")
        if risk_msgs:
            st.warning(
                "현재 상태로는 제한이 있을 수 있어요. 다만 상담을 통해 해결 방안을 함께 찾아드리겠습니다. "
                f"(표시: {', '.join(risk_msgs)})"
            )
        
        # 개인정보 동의
        st.markdown("---")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)", help="필수 동의 항목입니다. 전문은 아래에서 확인하세요.")
            st.caption("상담 확인·자격 검토·연락 목적. 상담 완료 후 1년 보관 또는 철회 시 즉시 삭제.")
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
            st.caption("신규 정책자금/지원사업 알림. 언제든지 수신 거부 가능.")
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
        submitted = st.form_submit_button("📩 정책자금 상담 신청", type="primary")
        
        if submitted and not st.session_state.submitted:
            st.session_state.submitted = True

            # 폼 밖에서 입력된 전화번호 사용
            d = _digits_only(st.session_state.get("phone_input", ""))
            formatted_phone = format_phone_from_digits(d)
            phone_valid = (len(d) == 11 and d.startswith("010"))
            if not phone_valid:
                phone_error_placeholder.error("연락처는 010-0000-0000 형식으로 입력해주세요.")
            else:
                phone_error_placeholder.empty()

            if not name or len(name) < 2 or not formatted_phone:
                st.error("성함(2자 이상)과 연락처는 필수 입력 항목입니다.")
                st.session_state.submitted = False
            elif not phone_valid:
                st.error("연락처 형식을 확인해주세요. 예: 010-1234-5678")
                st.session_state.submitted = False
            elif not privacy_agree:
                st.error("개인정보 수집·이용 동의는 필수입니다.")
                st.session_state.submitted = False
            else:
                with st.spinner("상담 신청을 처리하고 있습니다..."):
                    # 쿼리 파라미터에서 UTM/테스트 추출 (신규 API 호환)
                    utm_source = _get_qp("utm_source")
                    utm_medium = _get_qp("utm_medium")
                    utm_campaign = _get_qp("utm_campaign")
                    utm_term = _get_qp("utm_term")
                    utm_content = _get_qp("utm_content")
                    submitted_at = datetime.now().isoformat(timespec="seconds")

                    # 접수번호 생성 (클라이언트 측, 일시적인 충돌 방지용)
                    receipt_no = f"YP{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"

                    # 데이터 준비
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
                        'utm_source': utm_source,
                        'utm_medium': utm_medium,
                        'utm_campaign': utm_campaign,
                        'utm_term': utm_term,
                        'utm_content': utm_content,
                        'release_version': RELEASE_VERSION,
                        'submitted_at': submitted_at,
                        'receipt_no': receipt_no,
                        'test_mode': is_test_mode,
                    }
                    
                    # Google Sheets 저장 (테스트 모드면 저장 생략)
                    result = save_to_google_sheet(survey_data, timeout_sec=12, retries=1, test_mode=is_test_mode)

                    if result.get('status') in ('success', 'test'):
                        if is_test_mode:
                            st.info("🧪 테스트 모드: 저장은 수행하지 않았습니다.")
                        st.success("✅ 상담 신청이 완료되었습니다!")
                        st.info(f"📋 접수번호: **{receipt_no}**")
                        st.info("📞 1영업일 내 전문가가 연락드립니다. 급한 문의는 카카오 채널 ‘유아플랜 컨설팅’으로 남겨주세요.")
                        st.toast("신청이 접수되었습니다.", icon="✅")
                        # 다음 행동 유도(CTA): 카카오 채널 채팅 / 채널 추가
                        st.markdown(
                            f"""
      <div class="cta-wrap">
        <div style="margin-bottom:8px;color:#333;">카카오 채널에서 바로 문의하시면 가장 빠르게 도와드릴 수 있어요.</div>
        <a class="cta-btn cta-primary" href="{KAKAO_CHANNEL_URL}" target="_blank">💬 카카오 채널 추가 및 대화하기</a>
      </div>
      """,
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            """
<div id="auto-return-wrap" style="margin-top:10px;padding:12px;border:1px solid var(--gov-border);border-radius:8px;background:#fff;">
  <div id="auto-return-msg" style="color:#374151;margin-bottom:8px;line-height:1.5;">
    <strong style="color:#111;">안내:</strong> <span style="color:#111;">이 창은</span>
    <strong><span id="countdown">5</span>초</strong> 후 이전 화면으로 자동 이동합니다.
    필요하시면 아래 버튼으로 자동 이동을 취소하실 수 있어요.
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <a class="cta-btn cta-secondary" id="stay-here-btn" href="#" onclick="window.__stayHere=true;return false;" aria-label="자동 이동 취소">
      ⏸️ 이 창에 머물기
    </a>
    <a class="cta-btn cta-primary" id="go-now-btn" href="#" onclick="(function(){try{window.__forceGoNow=true;}catch(e){}})();return false;" aria-label="지금 바로 이전 화면으로 이동">
      🔙 지금 바로 돌아가기
    </a>
  </div>
</div>
<script>
(function(){
  // 접근성: 화면읽기기에서 카운트다운이 변할 때 읽어주도록 설정
  var live = document.createElement('div');
  live.setAttribute('aria-live','polite');
  live.setAttribute('aria-atomic','true');
  live.style.position='absolute';
  live.style.left='-9999px';
  document.body.appendChild(live);

  function updateLive(msg){ try{ live.textContent = msg; }catch(e){} }

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
    // 4) 최종 기본값
    location.replace('/');
  }

  var left = 5;
  var el = document.getElementById('countdown');

  // 강제 이동 버튼
  var goNow = document.getElementById('go-now-btn');
  if (goNow){
    goNow.addEventListener('click', function(e){
      e.preventDefault();
      goBack();
    });
  }

  // 타이머
  var timer = setInterval(function(){
    if (window.__stayHere === true) {
      clearInterval(timer);
      var msg = document.getElementById('auto-return-msg');
      if (msg){ msg.innerHTML = '자동 이동이 취소되었습니다. 필요 시 상단의 링크 또는 브라우저 뒤로가기를 이용해 주세요.'; }
      updateLive('자동 이동이 취소되었습니다.');
      return;
    }
    if (window.__forceGoNow === true) {
      clearInterval(timer);
      goBack();
      return;
    }
    left -= 1;
    if (left <= 0){
      clearInterval(timer);
      goBack();
    } else {
      if (el) { el.textContent = left; updateLive(left + '초 남았습니다.'); }
    }
  }, 1000);

  // 초기 announce
  updateLive('5초 후 이전 화면으로 이동합니다.');
})();
</script>
""",
                            unsafe_allow_html=True,
                        )
                    else:
                        msg = result.get('message', '알 수 없는 오류로 실패했습니다. 잠시 후 다시 시도해주세요.')
                        st.error(f"❌ 신청 중 오류: {msg}")
                        # 실패 시 재제출 허용
                        st.session_state.submitted = False

if __name__ == "__main__":
    main()
