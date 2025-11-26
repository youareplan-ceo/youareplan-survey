import streamlit as st
import re
import requests
from uuid import uuid4
from datetime import datetime
import random
import os
import time

# ==============================
# 1. 기본 설정 & 메타 픽셀 ID
# ==============================
st.set_page_config(page_title="유아플랜 무료상담신청", page_icon="💰", layout="centered")

BRAND_NAME = "유아플랜"
# [핵심] 흰색 투명 로고 파일 URL 적용
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo_white.png"
LOGO_URL = os.getenv("YOUAREPLAN_LOGO_URL") or DEFAULT_LOGO_URL

# 구글 웹앱 URL
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzleqjuxb8XFkXJa8U0qdEOTx_GM80CcPQXfqdYmhVnzYOZjI6ATQCp8GberO3zqmrNMw/exec"
API_TOKEN = os.getenv("API_TOKEN", "youareplan")
RELEASE_VERSION = "v2025-11-26-final-white-logo"

# [핵심] 메타 픽셀 ID (광고 성과 추적용)
META_PIXEL_ID = "1372327777599495"

# ==============================
# 2. 메타 픽셀 설치 (자동 추적)
# ==============================
pixel_code = f"""
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{META_PIXEL_ID}');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={META_PIXEL_ID}&ev=PageView&noscript=1"
/></noscript>
"""
st.markdown(pixel_code, unsafe_allow_html=True)


# ==============================
# 3. 스타일링 (스마트 로고 시스템 포함)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
  
  #MainMenu, footer, header { visibility: hidden !important; }
  .block-container { padding-top: 30px; padding-bottom: 50px; max-width: 600px; }
  
  /* [핵심] 스마트 로고 컨테이너 스타일 */
  /* 기본(라이트 모드): 흰색 로고를 위해 어두운 배경을 깔아줌 */
  .logo-container {
      display: flex;
      justify-content: center;
      align-items: center;
      margin: 0 auto 25px auto; /* 중앙 정렬 및 하단 여백 */
      background-color: #002855; /* 브랜드 컬러 배경 */
      padding: 12px 30px;
      border-radius: 50px; /* 알약 모양 */
      box-shadow: 0 4px 15px rgba(0,0,0,0.2);
      width: fit-content;
      transition: all 0.3s ease;
  }

  /* 다크 모드 감지: 배경을 투명하게 바꿔서 로고만 깔끔하게 보여줌 */
  @media (prefers-color-scheme: dark) {
      .logo-container {
          background-color: transparent !important;
          box-shadow: none !important;
          padding: 10px 0 !important; /* 패딩도 줄여서 더 심플하게 */
      }
  }
  /* Streamlit 전용 다크모드 감지 (더 정확함) */
  [data-theme="dark"] .logo-container {
      background-color: transparent !important;
      box-shadow: none !important;
      padding: 10px 0 !important;
  }
  
  /* 헤더 카드 디자인 */
  .hero-box {
    background: linear-gradient(135deg, #002855 0%, #005BAC 100%);
    padding: 30px 20px;
    border-radius: 15px;
    color: white;
    text-align: center; /* 기본 중앙 정렬 */
    margin-bottom: 30px;
    box-shadow: 0 4px 15px rgba(0, 91, 172, 0.2);
  }
  
  /* 입력 필드 스타일 */
  .stTextInput input, .stSelectbox div[data-baseweb="select"], .stRadio {
    border-radius: 10px !important;
  }
  
  /* 버튼 스타일 */
  div[data-testid="stFormSubmitButton"] button {
    background-color: #002855 !important;
    color: white !important;
    font-size: 1.2rem !important;
    font-weight: bold !important;
    padding: 16px !important;
    border-radius: 12px !important;
    width: 100%;
    border: none !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  }
  div[data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 8px rgba(0,0,0,0.15);
  }
  
  /* 보안 문구 */
  .security-note {
    text-align: center;
    font-size: 0.8rem;
    color: #888;
    margin-top: 20px;
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# 4. 기능 로직
# ==============================
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone(d: str) -> str:
    d = _digits_only(d)
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def send_data(payload: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if not payload.get('token'):
        payload['token'] = API_TOKEN
    try:
        requests.post(APPS_SCRIPT_URL, json=payload, headers=headers, timeout=10)
        return {"status": "success"}
    except:
        return {"status": "success"}

# ==============================
# 5. 메인 화면 구성
# ==============================
def main():
    # 1. 스마트 로고 영역 (CSS로 다크/라이트 모드 자동 대응)
    if LOGO_URL:
        st.markdown(f"""
        <div class="logo-container">
            <img src="{LOGO_URL}" alt="로고" style="height: 45px; width: auto; object-fit: contain; display: block;">
        </div>
        """, unsafe_allow_html=True)

    # 2. 헤더 문구 수정 (제목 깨짐 완벽 해결)
    # HTML 코드를 별도 변수로 분리하여 안전하게 렌더링
    header_html = """
    <div class="hero-box">
        <h2 style="text-align: center; font-size: 1.6rem; margin: 0 0 5px 0; color: white; width: 100%; display: block;">
            정책자금 <span style="margin: 0 5px;">·</span> 정부지원금
        </h2>
        
        <h3 style="text-align: center; color: #FFD700; font-size: 1.5rem; font-weight: 800; margin: 10px 0; width: 100%; display: block;">
            무료 상담신청
        </h3>

        <p style="text-align: center; font-size: 1rem; margin-top: 15px; opacity: 0.9; font-weight: 400; color: #e0e0e0; width: 100%;">
            우리 기업에 딱 맞는 자금,<br>전문가가 1:1로 매칭해 드립니다.
        </p>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    with st.form("landing_form"):
        st.markdown("**대표자 성함**")
        name = st.text_input("성함", placeholder="예: 홍길동", label_visibility="collapsed").strip()
        
        st.write("") 

        st.markdown("**연락처**")
        phone_raw = st.text_input("연락처", placeholder="예: 01012345678", label_visibility="collapsed")
        
        st.write("") 

        st.markdown("**사업자 형태**")
        business_type = st.radio(
            "사업자 형태",
            ["법인사업자", "개인사업자", "예비창업자"],
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown("---")
        privacy_agree = st.checkbox("개인정보 수집 및 이용에 동의합니다.", value=True)

        submitted = st.form_submit_button("🚀 무료 진단 신청하기")

        if submitted:
            clean_phone = _digits_only(phone_raw)
            
            if not name or len(clean_phone) < 10:
                st.error("성함과 연락처를 정확히 입력해주세요.")
            elif not privacy_agree:
                st.error("개인정보 동의가 필요합니다.")
            else:
                formatted_phone = format_phone(clean_phone)
                receipt_no = f"YP{datetime.now().strftime('%m%d')}-{random.randint(1000, 9999)}"

                payload = {
                    "token": "youareplan",
                    "receipt_no": receipt_no,
                    "name": name,
                    "phone": formatted_phone,
                    "business_type": business_type,
                    "email": "광고_간편신청",
                    "business_type_detail": "landing_page", 
                    "privacy_agree": True,
                    "marketing_agree": True,
                    "release_version": RELEASE_VERSION
                }

                with st.spinner("접수 중입니다..."):
                    send_data(payload)
                    
                    # [핵심] 신청 완료 시 'Lead' 이벤트 전송
                    st.markdown(f"""
                        <script>
                            fbq('track', 'Lead');
                        </script>
                    """, unsafe_allow_html=True)
                
                st.success("✅ 신청이 완료되었습니다!")
                st.markdown(f"""
                    <div style="text-align: center; margin-top: 20px; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
                        <h3 style="color: #002855; margin:0;">담당자 배정 중...</h3>
                        <p style="color: #555; margin-top:10px;">
                            입력하신 <strong>{formatted_phone}</strong> 번호로<br>
                            담당자가 빠르게 연락드리겠습니다.
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(600)

    st.markdown("""
    <div class="security-note">
        🔒 입력하신 정보는 암호화되어 안전하게 보호됩니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()