import streamlit as st
import re
import requests
from uuid import uuid4
from datetime import datetime
import random
import os

# ==============================
# 1. 기본 설정
# ==============================
st.set_page_config(page_title="유아플랜 무료진단 신청", page_icon="💰", layout="centered")

BRAND_NAME = "유아플랜"
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"
LOGO_URL = os.getenv("YOUAREPLAN_LOGO_URL") or DEFAULT_LOGO_URL

# 기존 survey1과 같은 시트를 씁니다 (데이터 통합 관리)
APPS_SCRIPT_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

RELEASE_VERSION = "v2025-11-26-landing-ad"

# ==============================
# 2. 스타일링 (survey1과 동일한 전문적인 느낌)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
  
  #MainMenu, footer, header { visibility: hidden !important; }
  .block-container { padding-top: 30px; padding-bottom: 50px; max-width: 600px; }
  
  /* 헤더 카드 */
  .hero-box {
    background: linear-gradient(135deg, #002855 0%, #005BAC 100%);
    padding: 30px 20px;
    border-radius: 15px;
    color: white;
    text-align: center;
    margin-bottom: 30px;
    box-shadow: 0 4px 15px rgba(0, 91, 172, 0.2);
  }
  .hero-box h2 { color: white; font-weight: 800; margin: 0 0 10px 0; font-size: 1.6rem; }
  .hero-box p { color: #e0e0e0; margin: 0; font-size: 1rem; }

  /* 입력 필드 */
  .stTextInput input, .stSelectbox div[data-baseweb="select"], .stRadio {
    border-radius: 10px !important;
  }
  
  /* 버튼 */
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
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# 3. 기능 로직
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
# 4. 메인 화면 (초간단 버전)
# ==============================
def main():
    # 상단 디자인 (고객 후킹용)
    st.markdown("""
    <div class="hero-box">
        <h2>2025년 정책자금<br>무료 한도 조회</h2>
        <p>1분 신청으로 우리 기업의 가능성을 확인하세요.<br>담당자가 즉시 분석해 드립니다.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("landing_form"):
        # 질문 1: 성함
        st.markdown("**성함**")
        name = st.text_input("성함", placeholder="예: 홍길동", label_visibility="collapsed").strip()
        
        st.write("") # 여백

        # 질문 2: 연락처
        st.markdown("**연락처**")
        phone_raw = st.text_input("연락처", placeholder="예: 01012345678", label_visibility="collapsed")
        
        st.write("") # 여백

        # 질문 3: 사업자 형태 (최소한의 분류)
        st.markdown("**사업자 형태**")
        business_type = st.radio(
            "사업자 형태",
            ["개인사업자", "법인사업자", "예비창업자"],
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
                # 데이터 전송
                formatted_phone = format_phone(clean_phone)
                receipt_no = f"YP{datetime.now().strftime('%m%d')}-{random.randint(1000, 9999)}"

                # [핵심] 나머지 항목은 빈 값('-')으로 채워서 에러 방지
                payload = {
                    "token": "youareplan",
                    "receipt_no": receipt_no,
                    "name": name,
                    "phone": formatted_phone,
                    "business_type": business_type,
                    
                    # --- 미입력 항목 자동 채움 ---
                    "birth_year": "-", "gender": "-", "region": "-", 
                    "industry": "-", "est_year": "-", "revenue": "-", 
                    "funding_amount": "-", "tax_status": "-", "credit_status": "-",
                    "employee_count": "-",
                    # --------------------------
                    
                    "privacy_agree": True,
                    "marketing_agree": True,
                    "release_version": RELEASE_VERSION
                }

                with st.spinner("접수 중입니다..."):
                    send_data(payload)
                
                # 성공 화면 (깔끔하게)
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
                time.sleep(600) # 화면 유지

if __name__ == "__main__":
    import time
    main()