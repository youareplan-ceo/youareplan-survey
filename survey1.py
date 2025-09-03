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

RELEASE_VERSION = "v2025-09-03-input-fix"

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

# 수정된 CSS (입력창 스타일 통일)
st.markdown("""
<style>
  /* 기본 폰트 설정 */
  html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif;
  }

  /* 색상 변수 */
  :root {
    --gov-navy: #002855;
    --gov-blue: #005BAC;
    --gov-gray: #f5f7fa;
    --gov-border: #d7dce3;
    --gov-danger: #D32F2F;
    --primary-color: #002855 !important;
    --input-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
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

  /* 모든 입력창 통일 스타일 (우선순위 최대화) */
  .stTextInput > div > div > input,
  .stSelectbox > div > div,
  .stSelectbox > div > div > div,
  .stMultiSelect > div > div,
  .stMultiSelect > div > div > div,
  .stTextArea > div > div > textarea,
  .stDateInput > div > div > input,
  div[data-baseweb="select"] > div,
  div[data-baseweb="input"] > input,
  div[data-baseweb="textarea"] > textarea {
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    box-shadow: var(--input-shadow) !important;
    color: #111111 !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
    transition: all 0.2s ease !important;
  }

  /* 포커스 상태 */
  .stTextInput > div > div > input:focus,
  .stSelectbox > div > div:focus-within,
  .stMultiSelect > div > div:focus-within,
  .stTextArea > div > div > textarea:focus,
  .stDateInput > div > div > input:focus {
    border-color: var(--gov-blue) !important;
    box-shadow: 0 0 0 3px rgba(0, 91, 172, 0.1), var(--input-shadow) !important;
    outline: none !important;
  }

  /* 입력창 컨테이너 스타일 */
  .stTextInput > div,
  .stSelectbox > div,
  .stMultiSelect > div,
  .stTextArea > div,
  .stDateInput > div {
    background: transparent !important;
  }

  /* 플레이스홀더 스타일 */
  .stTextInput input::placeholder,
  .stTextArea textarea::placeholder {
    color: #9ca3af !important;
    opacity: 1 !important;
  }

  /* 자동완성 스타일 강제 덮어쓰기 */
  input:-webkit-autofill,
  input:-webkit-autofill:hover,
  input:-webkit-autofill:focus,
  input:-webkit-autofill:active,
  textarea:-webkit-autofill,
  select:-webkit-autofill {
    -webkit-text-fill-color: #111111 !important;
    -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
    box-shadow: 0 0 0 1000px #ffffff inset, var(--input-shadow) !important;
    transition: background-color 5000s ease-in-out 0s !important;
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
  }

  /* 셀렉트박스 특별 처리 */
  div[data-baseweb="select"] {
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
    box-shadow: var(--input-shadow) !important;
    background: #ffffff !important;
  }

  div[data-baseweb="select"]:focus-within {
    border-color: var(--gov-blue) !important;
    box-shadow: 0 0 0 3px rgba(0, 91, 172, 0.1), var(--input-shadow) !important;
  }

  /* 멀티셀렉트 스타일 */
  div[data-baseweb="select"] div[data-baseweb="tag"] {
    background: var(--gov-blue) !important;
    color: white !important;
    border-radius: 6px !important;
  }

  /* 체크박스 스타일 */
  .stCheckbox {
    padding: 12px 16px !important;
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
    background: #ffffff !important;
    box-shadow: var(--input-shadow) !important;
    margin: 4px 0 !important;
  }

  /* 제출 버튼 스타일 */
  div[data-testid="stFormSubmitButton"] button,
  .stButton > button {
    background: var(--gov-navy) !important;
    border: 1px solid var(--gov-navy) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    border-radius: 8px !important;
    box-shadow: var(--input-shadow) !important;
    transition: all 0.2s ease !important;
  }

  div[data-testid="stFormSubmitButton"] button:hover,
  .stButton > button:hover {
    background: #001a3a !important;
    border-color: #001a3a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0, 40, 85, 0.3) !important;
  }

  /* 버튼 텍스트 강제 흰색 */
  div[data-testid="stFormSubmitButton"] button *,
  .stButton > button * {
    color: #ffffff !important;
    fill: #ffffff !important;
  }

  /* 라이트 모드 강제 */
  :root { color-scheme: light; }
  html, body, .stApp {
    background: #ffffff !important;
    color: #111111 !important;
  }

  /* 텍스트 가독성 */
  .stMarkdown, .stText, label, p, h1, h2, h3, h4, h5, h6 {
    color: #111111 !important;
  }

  /* CTA 버튼 */
  .cta-wrap {
    margin-top: 20px;
    padding: 16px;
    border: 1px solid var(--gov-border);
    border-radius: 8px;
    background: #fafafa;
    box-shadow: var(--input-shadow);
  }
  
  .cta-btn {
    display: block;
    text-align: center;
    font-weight: 700;
    text-decoration: none;
    padding: 12px 24px;
    border-radius: 8px;
    transition: all 0.2s ease;
  }
  
  .cta-primary {
    background: #FEE500;
    color: #3C1E1E;
    box-shadow: var(--input-shadow);
  }
  
  .cta-primary:hover {
    background: #FFD700;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(254, 229, 0, 0.3);
  }

  /* 경고/정보 메시지 스타일 개선 */
  .stAlert {
    border-radius: 8px !important;
    border: none !important;
    box-shadow: var(--input-shadow) !important;
  }

  /* 모바일 최적화 */
  @media (max-width: 768px) {
    .stApp {
      padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 220px) !important;
    }
    
    div[data-baseweb="popover"] {
      z-index: 10000 !important;
    }
    
    div[data-baseweb="popover"] div[role="listbox"] {
      max-height: 38vh !important;
      overscroll-behavior: contain;
    }

    /* 모바일에서 입력창 크기 조정 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
      font-size: 16px !important; /* iOS 줌 방지 */
    }
  }

  /* 폼 레이아웃 개선 */
  .stForm {
    background: #ffffff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    border: 1px solid var(--gov-border);
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
    # 헤더
    st.markdown("""
    <div class="gov-topbar">🏛️ 대한민국 정부 협력 서비스</div>
    <div class="gov-hero">
        <h2>정부 지원금·정책자금 상담 신청</h2>
        <p>중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 지원</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("✅ **정책자금 지원 가능성 검토**를 위한 기초 상담 절차입니다.")

    # 테스트 모드 확인
    is_test_mode = (_get_qp("test") == "true")
    if is_test_mode:
        st.warning("⚠️ **테스트 모드** - 실제 데이터는 저장되지 않습니다.")
    
    st.markdown("### 📝 1차 설문 - 기본 정보")
    st.markdown("**3분이면 완료!** 상담 시 언제든 수정 가능합니다.")

    # 세션 상태 초기화
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False

    with st.form("first_survey", clear_on_submit=False):
        # 기본 인적사항
        st.markdown("#### 👤 기본 정보")
        name = st.text_input("**성함** (필수)", placeholder="홍길동", key="name_input")
        
        phone_input = st.text_input(
            "**연락처** (필수)", 
            key="phone_input", 
            placeholder="010-0000-0000",
            on_change=_phone_on_change,
            help="숫자만 입력하면 자동으로 하이픈이 추가됩니다."
        )
        
        email = st.text_input("**이메일** (선택)", placeholder="email@example.com")

        # 사업 정보
        st.markdown("#### 🏢 사업 정보")
        col1, col2 = st.columns(2)
        with col1:
            region = st.selectbox("**사업장 지역** (필수)", REGIONS)
            industry = st.selectbox("**업종** (필수)", INDUSTRIES)
            business_type = st.selectbox("**사업자 형태** (필수)", BUSINESS_TYPES)
        with col2:
            employee_count = st.selectbox("**직원 수** (필수)", EMPLOYEE_COUNTS)
            revenue = st.selectbox("**연간 매출** (필수)", REVENUES)
            funding_amount = st.selectbox("**필요 자금** (필수)", FUNDING_AMOUNTS)

        # 정책자금 경험
        st.markdown("#### 💼 정책자금 이용 경험 (선택)")
        policy_experience = st.multiselect(
            "해당사항을 모두 선택하세요",
            POLICY_EXPERIENCES,
            placeholder="경험이 있는 항목을 선택해주세요"
        )

        # 지원 자격 확인
        st.markdown("#### ⚠️ 지원 자격 확인 (필수)")
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox(
                "**세금 체납 여부**",
                ["체납 없음", "체납 있음", "분납 중"],
                help="국세/지방세 체납 시 대부분 지원 제한"
            )
        with col_b:
            credit_status = st.selectbox(
                "**금융 연체 여부**",
                ["연체 없음", "30일 미만", "30일 이상"],
                help="금융 연체 시 정책자금 지원 제한"
            )

        business_status = st.selectbox(
            "**사업 영위 상태**",
            ["정상 영업", "휴업", "폐업 예정"],
            help="휴/폐업 시 지원 불가"
        )

        # 리스크 경고
        risk_msgs = []
        if tax_status != "체납 없음": 
            risk_msgs.append("세금 체납")
        if credit_status != "연체 없음": 
            risk_msgs.append("금융 연체")
        if business_status != "정상 영업": 
            risk_msgs.append("휴/폐업 상태")
            
        if risk_msgs:
            st.error(f"🚨 **지원 제한 가능**: {', '.join(risk_msgs)}")
            st.info("💡 해당 사항이 있어도 일부 정책자금은 지원 가능할 수 있습니다.")

        # 개인정보 동의
        st.markdown("#### 📋 개인정보 처리 동의")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("**개인정보 수집·이용 동의** (필수)")
            st.caption("상담 목적으로 1년 보관 후 삭제됩니다.")
        with col_agree2:
            marketing_agree = st.checkbox("**마케팅 정보 수신 동의** (선택)")
            st.caption("신규 정책자금 알림. 언제든 철회 가능합니다.")

        # 제출 버튼
        submitted = st.form_submit_button("📤 **정책자금 상담 신청하기**", type="primary", use_container_width=True)
        
        # 폼 제출 처리
        if submitted and not st.session_state.submitted:
            # 입력 검증
            name_val = name.strip()
            d = _digits_only(phone_input)
            formatted_phone = format_phone_from_digits(d)
            phone_valid = (len(d) == 11 and d.startswith("010"))
            
            if not name_val:
                st.error("❌ **성함을 입력해주세요.**")
                st.stop()
            
            if not formatted_phone:
                st.error("❌ **연락처를 입력해주세요.**")
                st.stop()
                
            if not phone_valid:
                st.error("❌ **연락처는 010-0000-0000 형식이어야 합니다.**")
                st.stop()
                
            if not privacy_agree:
                st.error("❌ **개인정보 수집·이용 동의는 필수입니다.**")
                st.stop()

            # 제출 상태 설정
            st.session_state.submitted = True
            
            # 접수번호 생성
            receipt_no = f"YP{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"
            
            # 데이터 준비
            survey_data = {
                'type': '1차설문',
                'name': name_val,
                'phone': formatted_phone,
                'email': email.strip(),
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
                'submission_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 데이터 저장
            with st.spinner("📤 상담 신청 처리 중..."):
                result = save_to_google_sheet(survey_data, test_mode=is_test_mode)

            if result.get('status') in ('success', 'test'):
                st.success("✅ **상담 신청이 완료되었습니다!**")
                st.info(f"📋 **접수번호**: {receipt_no}")
                st.info("📞 **1영업일 내** 전문 상담사가 연락드립니다.")
                
                # 카카오톡 상담 안내
                st.markdown(f"""
                <div class="cta-wrap">
                    <h4>💬 추가 문의사항이 있으시나요?</h4>
                    <a class="cta-btn cta-primary" href="{KAKAO_CHANNEL_URL}" target="_blank">
                        💛 카카오톡 채널로 문의하기
                    </a>
                </div>
                """, unsafe_allow_html=True)

                # 자동 복귀 안내
                st.markdown("""
                <div id="auto-exit-note" style="margin-top:16px;padding:16px;border:1px solid var(--gov-border);border-radius:8px;background:#f0f9ff;color:#1e40af;text-align:center;">
                    🎉 제출이 완료되었습니다! <strong><span id="exit_count">3</span>초</strong> 후 이전 페이지로 이동합니다.
                </div>
                <script>
                (function(){
                    function go(){
                        try{ 
                            if(history.length > 1){ 
                                history.back(); 
                                return; 
                            } 
                        }catch(e){}
                        try{ 
                            var q=new URLSearchParams(location.search); 
                            var ret=q.get('return_to'); 
                            if(ret){ 
                                location.replace(ret); 
                                return; 
                            } 
                        }catch(e){}
                        location.replace('/');
                    }
                    var left=3, el=document.getElementById('exit_count');
                    var t=setInterval(function(){ 
                        left--; 
                        if(el){ el.textContent=left; } 
                        if(left<=0){ 
                            clearInterval(t); 
                            go(); 
                        } 
                    }, 1000);
                    setTimeout(go, 3500);
                })();
                </script>
                """, unsafe_allow_html=True)

            else:
                st.error("❌ **신청 실패**: 다시 시도해주세요.")
                st.session_state.submitted = False
                if not is_test_mode:
                    st.info("🔄 문제가 지속되면 페이지를 새로고침 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()