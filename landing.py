"""
유아플랜 광고형 랜딩 페이지 (풀스크린 히어로 버전)
- 로고 크게 + 통합 히어로 섹션
- 스크롤 시 간편 폼
"""

import streamlit as st
import requests
import re
import os
from datetime import datetime
from uuid import uuid4
import random

st.set_page_config(
    page_title="정책자금 무료 상담 | 유아플랜",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

APPS_SCRIPT_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

KAKAO_CHANNEL_URL = "https://pf.kakao.com/_LWxexmn"

RELEASE_VERSION = "v2025-11-26-hero"

# ==============================
# 유틸리티 함수
# ==============================
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone(d: str) -> str:
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def send_telegram(data: dict) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        msg = f"""🚀 <b>광고 랜딩 신규 상담</b>

👤 {data.get('name', '')}
📞 {data.get('phone', '')}
🏢 {data.get('business_type', '')}
💰 {data.get('funding_amount', '')}

🎫 {data.get('receipt_no', '')}
⏰ {data.get('timestamp', '')}"""
        
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=5
        )
        return True
    except:
        return False

def save_to_sheet(data: dict) -> dict:
    try:
        data['token'] = API_TOKEN
        resp = requests.post(APPS_SCRIPT_URL, json=data, timeout=15)
        return resp.json() if resp.status_code == 200 else {"status": "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================
# CSS 스타일 (풀스크린 히어로)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
  
  /* 기본 설정 */
  :root {
    --navy: #002855;
    --navy-light: #003d7a;
    --gold: #FFD700;
    --white: #ffffff;
    color-scheme: light !important;
  }
  
  html, body, [class*="css"] {
    font-family: 'Noto Sans KR', -apple-system, sans-serif;
  }
  
  /* Streamlit 기본 요소 숨김 */
  #MainMenu, footer, header, [data-testid="stToolbar"], 
  [data-testid="stSidebar"], [data-testid="collapsedControl"] {
    display: none !important;
  }
  
  .stApp {
    background: var(--white) !important;
  }
  
  .block-container {
    padding: 0 !important;
    max-width: 100% !important;
  }
  
  /* ========== 히어로 섹션 ========== */
  .hero-section {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 50%, #0066cc 100%);
    min-height: 70vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  
  /* 배경 장식 */
  .hero-section::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 70%, rgba(255,255,255,0.05) 0%, transparent 50%);
    animation: float 20s ease-in-out infinite;
  }
  
  @keyframes float {
    0%, 100% { transform: translate(0, 0) rotate(0deg); }
    50% { transform: translate(30px, -30px) rotate(180deg); }
  }
  
  /* 로고 */
  .hero-logo {
    position: relative;
    z-index: 2;
    margin-bottom: 40px;
  }
  
  .hero-logo img {
    height: 80px;
    width: auto;
    filter: drop-shadow(0 4px 20px rgba(0,0,0,0.3));
    transition: transform 0.3s ease;
  }
  
  .hero-logo img:hover {
    transform: scale(1.05);
  }
  
  /* 메인 타이틀 */
  .hero-title {
    position: relative;
    z-index: 2;
    color: var(--white);
    font-size: 36px;
    font-weight: 900;
    margin: 0 0 16px 0;
    letter-spacing: -1px;
    text-shadow: 0 2px 20px rgba(0,0,0,0.3);
  }
  
  /* 서브 타이틀 (강조) */
  .hero-subtitle {
    position: relative;
    z-index: 2;
    color: var(--gold);
    font-size: 28px;
    font-weight: 700;
    margin: 0 0 24px 0;
    text-shadow: 0 2px 10px rgba(0,0,0,0.2);
  }
  
  /* 설명 텍스트 */
  .hero-desc {
    position: relative;
    z-index: 2;
    color: rgba(255,255,255,0.9);
    font-size: 18px;
    font-weight: 400;
    line-height: 1.7;
    margin: 0 0 40px 0;
    max-width: 400px;
  }
  
  /* CTA 버튼 */
  .hero-cta {
    position: relative;
    z-index: 2;
    display: inline-block;
    background: var(--gold);
    color: var(--navy) !important;
    font-size: 20px;
    font-weight: 700;
    padding: 18px 48px;
    border-radius: 50px;
    text-decoration: none;
    box-shadow: 0 8px 30px rgba(255,215,0,0.4);
    transition: all 0.3s ease;
    animation: pulse-btn 2s ease-in-out infinite;
  }
  
  .hero-cta:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(255,215,0,0.5);
  }
  
  @keyframes pulse-btn {
    0%, 100% { box-shadow: 0 8px 30px rgba(255,215,0,0.4); }
    50% { box-shadow: 0 8px 40px rgba(255,215,0,0.6); }
  }
  
  /* 스크롤 인디케이터 */
  .scroll-indicator {
    position: relative;
    z-index: 2;
    margin-top: 40px;
    color: rgba(255,255,255,0.6);
    font-size: 14px;
    animation: bounce 2s ease-in-out infinite;
  }
  
  @keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(10px); }
  }
  
  /* ========== 폼 섹션 ========== */
  .form-section {
    background: var(--white);
    padding: 60px 24px;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .form-header {
    text-align: center;
    margin-bottom: 40px;
  }
  
  .form-header h2 {
    color: var(--navy);
    font-size: 28px;
    font-weight: 700;
    margin: 0 0 12px 0;
  }
  
  .form-header p {
    color: #666;
    font-size: 16px;
    margin: 0;
  }
  
  /* 입력 필드 스타일 */
  .stTextInput > div > div > input,
  .stSelectbox > div > div {
    border: 2px solid #e0e0e0 !important;
    border-radius: 12px !important;
    padding: 16px !important;
    font-size: 16px !important;
    transition: all 0.3s ease !important;
    background: #fafafa !important;
  }
  
  .stTextInput > div > div > input:focus,
  .stSelectbox > div > div:focus-within {
    border-color: var(--navy) !important;
    background: var(--white) !important;
    box-shadow: 0 0 0 3px rgba(0,40,85,0.1) !important;
  }
  
  /* 레이블 */
  .stTextInput label, .stSelectbox label, .stCheckbox label {
    color: #333 !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    margin-bottom: 8px !important;
  }
  
  /* 제출 버튼 */
  div[data-testid="stFormSubmitButton"] button {
    width: 100% !important;
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%) !important;
    color: var(--white) !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    padding: 18px 32px !important;
    border: none !important;
    border-radius: 12px !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(0,40,85,0.3) !important;
  }
  
  div[data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0,40,85,0.4) !important;
  }
  
  /* 체크박스 */
  .stCheckbox {
    background: #f8f9fa !important;
    padding: 12px 16px !important;
    border-radius: 8px !important;
    border: 1px solid #e9ecef !important;
  }
  
  /* 신뢰 배지 섹션 */
  .trust-section {
    background: #f8f9fa;
    padding: 40px 24px;
    text-align: center;
  }
  
  .trust-badges {
    display: flex;
    justify-content: center;
    gap: 32px;
    flex-wrap: wrap;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .trust-badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }
  
  .trust-badge .icon {
    font-size: 32px;
  }
  
  .trust-badge .text {
    color: #555;
    font-size: 14px;
    font-weight: 500;
  }
  
  /* 푸터 */
  .footer {
    background: var(--navy);
    color: rgba(255,255,255,0.7);
    padding: 32px 24px;
    text-align: center;
    font-size: 13px;
    line-height: 1.8;
  }
  
  .footer a {
    color: rgba(255,255,255,0.9);
    text-decoration: none;
  }
  
  /* ========== 반응형 ========== */
  @media (max-width: 640px) {
    .hero-section {
      min-height: 65vh;
      padding: 50px 20px;
    }
    
    .hero-logo img {
      height: 64px;
    }
    
    .hero-title {
      font-size: 28px;
    }
    
    .hero-subtitle {
      font-size: 22px;
    }
    
    .hero-desc {
      font-size: 16px;
    }
    
    .hero-cta {
      font-size: 18px;
      padding: 16px 40px;
    }
    
    .form-section {
      padding: 40px 20px;
    }
    
    .form-header h2 {
      font-size: 24px;
    }
    
    .trust-badges {
      gap: 24px;
    }
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# 메인 렌더링
# ==============================
def main():
    # ===== 히어로 섹션 =====
    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-logo">
            <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        </div>
        
        <h1 class="hero-title">정책자금 · 정부지원금</h1>
        <h2 class="hero-subtitle">무료 상담신청</h2>
        
        <p class="hero-desc">
            우리 기업에 딱 맞는 자금,<br>
            전문가가 1:1로 매칭해 드립니다.
        </p>
        
        <a href="#form-section" class="hero-cta">
            지금 무료 상담받기 →
        </a>
        
        <div class="scroll-indicator">
            ↓ 아래에서 간단히 신청하세요
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== 신뢰 배지 =====
    st.markdown("""
    <div class="trust-section">
        <div class="trust-badges">
            <div class="trust-badge">
                <span class="icon">🏛️</span>
                <span class="text">정부 협력 서비스</span>
            </div>
            <div class="trust-badge">
                <span class="icon">👨‍💼</span>
                <span class="text">전문가 1:1 매칭</span>
            </div>
            <div class="trust-badge">
                <span class="icon">💯</span>
                <span class="text">무료 상담</span>
            </div>
            <div class="trust-badge">
                <span class="icon">⚡</span>
                <span class="text">빠른 응대</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ===== 폼 섹션 =====
    st.markdown('<div id="form-section"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="form-section">
        <div class="form-header">
            <h2>📋 간편 상담 신청</h2>
            <p>30초면 완료! 빠르게 연락드립니다.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 세션 상태 초기화
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    
    # 폼
    with st.form("quick_form"):
        name = st.text_input("대표자 성함", placeholder="예: 홍길동")
        
        phone_raw = st.text_input("연락처", placeholder="예: 01012345678")
        
        business_type = st.selectbox(
            "사업자 형태",
            ["선택해주세요", "예비창업자", "개인사업자", "법인사업자", "협동조합·사회적기업"]
        )
        
        funding_amount = st.selectbox(
            "필요 자금 규모",
            ["선택해주세요", "3천만원 미만", "3천만원~1억원", "1억원~3억원", "3억원~5억원", "5억원 이상"]
        )
        
        st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            privacy = st.checkbox("개인정보 수집 동의 (필수)")
        with col2:
            marketing = st.checkbox("마케팅 수신 동의 (선택)")
        
        submitted = st.form_submit_button("📩 무료 상담 신청하기", type="primary")
        
        if submitted:
            phone_digits = _digits_only(phone_raw)
            phone_formatted = format_phone(phone_digits)
            
            # 유효성 검사
            errors = []
            if not name or len(name.strip()) < 2:
                errors.append("성함을 입력해주세요")
            if len(phone_digits) != 11 or not phone_digits.startswith("010"):
                errors.append("연락처를 정확히 입력해주세요")
            if business_type == "선택해주세요":
                errors.append("사업자 형태를 선택해주세요")
            if funding_amount == "선택해주세요":
                errors.append("필요 자금을 선택해주세요")
            if not privacy:
                errors.append("개인정보 수집 동의가 필요합니다")
            
            if errors:
                for err in errors:
                    st.error(err)
            else:
                with st.spinner("신청 처리 중..."):
                    now = datetime.now()
                    receipt_no = f"YP{now.strftime('%Y%m%d')}{random.randint(1000,9999)}"
                    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    data = {
                        'name': name.strip(),
                        'phone': phone_formatted,
                        'business_type': business_type,
                        'funding_amount': funding_amount,
                        'privacy_agree': True,
                        'marketing_agree': marketing,
                        'receipt_no': receipt_no,
                        'release_version': RELEASE_VERSION,
                        'source': 'landing_hero',
                        # 기본값 설정
                        'region': '미입력',
                        'industry': '미입력',
                        'employee_count': '미입력',
                        'revenue': '미입력',
                        'tax_status': '체납 없음',
                        'credit_status': '연체 없음',
                        'business_status': '정상 영업',
                        'timestamp': timestamp
                    }
                    
                    result = save_to_sheet(data)
                    send_telegram({**data, 'timestamp': timestamp})
                    
                    if result.get('status') == 'success':
                        st.session_state.submitted = True
                        st.session_state.receipt_no = receipt_no
                        st.rerun()
                    else:
                        st.success(f"✅ 상담 신청이 완료되었습니다!\n\n접수번호: **{receipt_no}**")
                        st.info("📞 1영업일 내 전문가가 연락드립니다.")
    
    # 제출 완료 상태
    if st.session_state.submitted:
        st.success(f"✅ 상담 신청이 완료되었습니다!")
        st.info(f"📋 접수번호: **{st.session_state.get('receipt_no', '')}**")
        st.info("📞 1영업일 내 전문가가 연락드립니다.")
        
        st.markdown(f"""
        <div style="margin-top: 20px; padding: 16px; background: #FEE500; border-radius: 12px; text-align: center;">
            <a href="{KAKAO_CHANNEL_URL}" target="_blank" style="color: #3C1E1E; font-weight: 700; text-decoration: none; font-size: 16px;">
                💬 카카오톡으로 빠른 상담받기
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("새로운 상담 신청"):
            st.session_state.submitted = False
            st.rerun()
    
    # ===== 푸터 =====
    st.markdown(f"""
    <div class="footer">
        <strong>{BRAND_NAME}</strong><br>
        중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 서비스<br><br>
        <a href="{KAKAO_CHANNEL_URL}" target="_blank">카카오 채널</a> ｜ 
        <a href="tel:010-0000-0000">전화 상담</a><br><br>
        © 2025 {BRAND_NAME}. All rights reserved.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()