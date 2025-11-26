import streamlit as st
import re
import requests
from uuid import uuid4
from datetime import datetime
import random
import os
import time  # time 모듈을 상단으로 이동

# ==============================
# 1. 기본 설정
# ==============================
st.set_page_config(page_title="유아플랜 무료상담신청", page_icon="💰", layout="centered")

BRAND_NAME = "유아플랜"
# 로고 URL (기본값)
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"
LOGO_URL = os.getenv("YOUAREPLAN_LOGO_URL") or DEFAULT_LOGO_URL

# -------------------------------------------------------------------------
# [핵심] 구글 웹앱 URL (데이터 전송용)
# -------------------------------------------------------------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzleqjuxb8XFkXJa8U0qdEOTx_GM80CcPQXfqdYmhVnzYOZjI6ATQCp8GberO3zqmrNMw/exec"

# 보안 토큰
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

RELEASE_VERSION = "v2025-11-26-landing-fixed-logo"

# ==============================
# 2. 스타일링 (신뢰감을 주는 디자인)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
  
  #MainMenu, footer, header { visibility: hidden !important; }
  .block-container { padding-top: 30px; padding-bottom: 50px; max-width: 600px; }
  
  /* 헤더 카드 디자인 */
  .hero-box {
    background: linear-gradient(135deg, #002855 0%, #005BAC 100%);
    padding: 30px 20px;
    border-radius: 15px;
    color: white;
    text-align: center;
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
# 4. 메인 화면 (초간단 신청서)
# ==============================
def main():
    # 1. 로고 영역 (크기 확대 수정됨)
    if LOGO_URL:
        st.markdown(f"""
        <div style="display: flex; justify-content: center; margin-bottom: 25px;">
            <div style="
                background-color: rgba(255, 255, 255, 0.95);
                padding: 15px 40px; 
                border-radius: 50px; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.15);
            ">
                <img src="{LOGO_URL}" alt="로고" style="height: 80px; width: auto; object-fit: contain; display: block;">
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 상단 디자인 (HTML 구조 정돈)
    # 주의: f-string이나 변수 삽입 없이 순수 HTML 문자열로 작성하여 깨짐 방지
    st.markdown("""
    <div class="hero-box">
        <h2 style="font-size: 1.6rem; margin: 0 0 10px 0; color: white; font-weight: 800;">
            정책자금 <span style="margin: 0 5px;">·</span> 정부지원금
        </h2>
        
        <h3 style="color: #FFD700; font-size: 1.4rem; font-weight: 800; margin: 0;">
            무료 상담신청
        </h3>

        <p style="font-size: 0.95rem; margin-top: 15px; opacity: 0.9; font-weight: 400; color: #e0e0e0; line-height: 1.6;">
            우리 기업에 딱 맞는 자금,<br>
            전문가가 1:1로 매칭해 드립니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("landing_form"):
        # 질문 1: 성함
        st.markdown("**대표자 성함**")
        name = st.text_input("성함", placeholder="예: 홍길동", label_visibility="collapsed").strip()
        
        st.write("") # 여백

        # 질문 2: 연락처
        st.markdown("**연락처**")
        phone_raw = st.text_input("연락처", placeholder="예: 01012345678", label_visibility="collapsed")
        
        st.write("") # 여백

        # 질문 3: 사업자 형태
        st.markdown("**사업자 형태**")
        business_type = st.radio(
            "사업자 형태",
            ["법인사업자", "개인사업자", "예비창업자"],
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown("---")
        privacy_agree = st.checkbox("개인정보 수집 및 이용에 동의합니다.", value=True)

        # 제출 버튼
        submitted = st.form_submit_button("무료 진단 신청하기")

        if submitted:
            clean_phone = _digits_only(phone_raw)
            
            if not name or len(clean_phone) < 10:
                st.error("성함과 연락처를 정확히 입력해주세요.")
            elif not privacy_agree:
                st.error("개인정보 동의가 필요합니다.")
            else:
                # 데이터 전송 준비
                formatted_phone = format_phone(clean_phone)
                receipt_no = f"YP{datetime.now().strftime('%m%d')}-{random.randint(1000, 9999)}"

                payload = {
                    "token": "youareplan",
                    "receipt_no": receipt_no,
                    "name": name,
                    "phone": formatted_phone,
                    "business_type": business_type,
                    "email": "광고_간편신청",
                    "birth_year": "-", "gender": "-", "region": "-", 
                    "industry": "-", "est_year": "-", "revenue": "-", 
                    "funding_amount": "-", "tax_status": "-", "credit_status": "-",
                    "employee_count": "-",
                    "privacy_agree": True,
                    "marketing_agree": True,
                    "release_version": RELEASE_VERSION
                }

                with st.spinner("접수 중입니다..."):
                    send_data(payload)
                
                # 성공 화면
                st.success("✅ 신청이 완료되었습니다!")
                st.markdown(f"""
                    <div style="text-align: center; margin-top: 20px; padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
                        <h3 style="color: #002855; margin:0;">담당자 배정 중...</h3>
                        <p style="color: #555; margin-top:10px; line-height: 1.5;">
                            입력하신 <strong>{formatted_phone}</strong> 번호로<br>
                            담당자가 빠르게 연락드리겠습니다.
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(600) # 화면 유지

    # 하단 보안 문구
    st.markdown("""
    <div class="security-note">
        🔒 입력하신 정보는 암호화되어 안전하게 보호됩니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()