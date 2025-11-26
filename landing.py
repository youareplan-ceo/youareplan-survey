import streamlit as st
import requests
import re
import os
from datetime import datetime
from uuid import uuid4
import random
import time

st.set_page_config(
    page_title="정책자금 무료 상담 | 유아플랜",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# [핵심] 메타 픽셀 설정 (CCTV 설치)
# ==============================
META_PIXEL_ID = "1372327777599495"

# 픽셀 기본 코드 (페이지 방문 추적 - PageView)
# 이 코드가 있어야 메타가 '아, 내 광고 보고 들어왔구나'를 압니다.
pixel_base_code = f"""
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
# 픽셀 코드를 헤더에 강제 삽입
st.markdown(pixel_base_code, unsafe_allow_html=True)


# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
# 로고 이미지는 흰색 로고 사용 (배경이 진한 색이라 흰색이 잘 보임)
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

APPS_SCRIPT_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

KAKAO_CHANNEL_URL = "https://pf.kakao.com/_LWxexmn"
RELEASE_VERSION = "v2025-11-26-pixel-installed"

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
        msg = f"""🚀 광고 랜딩 신규 상담

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
# 메인 함수
# ==============================
def main():
    # CSS 스타일
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    
    :root {
        --navy: #002855;
        --navy-light: #003d7a;
        --gold: #FFD700;
        color-scheme: light !important;
    }
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', -apple-system, sans-serif !important;
    }
    
    #MainMenu, footer, header, [data-testid="stToolbar"], 
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    .stApp {
        background: #ffffff !important;
    }
    
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    .hero-box {
        background: linear-gradient(135deg, #002855 0%, #003d7a 50%, #0066cc 100%);
        padding: 60px 24px;
        text-align: center;
        margin: -1rem -1rem 0 -1rem;
    }
    
    .hero-logo-img {
        height: 72px;
        margin-bottom: 32px;
        filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3));
    }
    
    .hero-title {
        color: #ffffff !important;
        font-size: 32px !important;
        font-weight: 900 !important;
        margin: 0 0 12px 0 !important;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    .hero-subtitle {
        color: #FFD700 !important;
        font-size: 26px !important;
        font-weight: 700 !important;
        margin: 0 0 20px 0 !important;
    }
    
    .hero-desc {
        color: rgba(255,255,255,0.9) !important;
        font-size: 17px !important;
        line-height: 1.7 !important;
        margin: 0 0 32px 0 !important;
    }
    
    .hero-cta-btn {
        display: inline-block;
        background: #FFD700;
        color: #002855 !important;
        font-size: 18px;
        font-weight: 700;
        padding: 16px 40px;
        border-radius: 50px;
        text-decoration: none;
        box-shadow: 0 6px 20px rgba(255,215,0,0.4);
        transition: all 0.3s ease;
    }
    
    .hero-cta-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(255,215,0,0.5);
        color: #002855 !important;
        text-decoration: none;
    }
    
    .scroll-hint {
        color: rgba(255,255,255,0.6);
        font-size: 14px;
        margin-top: 28px;
    }
    
    .trust-box {
        background: #f8f9fa;
        padding: 32px 24px;
        text-align: center;
        margin: 0 -1rem;
    }
    
    .trust-grid {
        display: flex;
        justify-content: center;
        gap: 28px;
        flex-wrap: wrap;
    }
    
    .trust-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
    }
    
    .trust-icon {
        font-size: 28px;
    }
    
    .trust-text {
        color: #555;
        font-size: 13px;
        font-weight: 500;
    }
    
    .form-header-box {
        text-align: center;
        padding: 32px 16px 16px 16px;
    }
    
    .form-header-title {
        color: #002855 !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        margin: 0 0 8px 0 !important;
    }
    
    .form-header-desc {
        color: #666 !important;
        font-size: 15px !important;
        margin: 0 !important;
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        border: 2px solid #e0e0e0 !important;
        border-radius: 10px !important;
        padding: 14px !important;
        font-size: 16px !important;
        background: #fafafa !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div:focus-within {
        border-color: #002855 !important;
        background: #ffffff !important;
        box-shadow: 0 0 0 3px rgba(0,40,85,0.1) !important;
    }
    
    .stTextInput label, .stSelectbox label, .stCheckbox label {
        color: #333 !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }
    
    div[data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        background: linear-gradient(135deg, #002855 0%, #003d7a 100%) !important;
        color: #ffffff !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        padding: 16px 32px !important;
        border: none !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 12px rgba(0,40,85,0.3) !important;
    }
    
    div[data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(0,40,85,0.4) !important;
    }
    
    .stCheckbox {
        background: #f8f9fa !important;
        padding: 10px 14px !important;
        border-radius: 8px !important;
        border: 1px solid #e9ecef !important;
    }
    
    .footer-box {
        background: #002855;
        color: rgba(255,255,255,0.7);
        padding: 28px 24px;
        text-align: center;
        font-size: 13px;
        line-height: 1.8;
        margin: 40px -1rem 0 -1rem;
    }
    
    .footer-box a {
        color: rgba(255,255,255,0.9);
        text-decoration: none;
    }
    
    @media (max-width: 640px) {
        .hero-box { padding: 48px 20px; }
        .hero-logo-img { height: 56px; margin-bottom: 24px; }
        .hero-title { font-size: 26px !important; }
        .hero-subtitle { font-size: 22px !important; }
        .hero-desc { font-size: 15px !important; }
        .hero-cta-btn { font-size: 16px; padding: 14px 32px; }
        .trust-grid { gap: 20px; }
        .form-header-title { font-size: 22px !important; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 세션 상태
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    
    # 히어로 섹션
    st.markdown(f"""
    <div class="hero-box">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}" class="hero-logo-img">
        <div class="hero-title">정책자금 · 정부지원금</div>
        <div class="hero-subtitle">무료 상담신청</div>
        <div class="hero-desc">
            우리 기업에 딱 맞는 자금,<br>
            전문가가 1:1로 매칭해 드립니다.
        </div>
        <a href="#form-section" class="hero-cta-btn">지금 무료 상담받기 →</a>
        <div class="scroll-hint">↓ 아래에서 간단히 신청하세요</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 신뢰 배지
    st.markdown("""
    <div class="trust-box">
        <div class="trust-grid">
            <div class="trust-item">
                <span class="trust-icon">🏛️</span>
                <span class="trust-text">정부 협력 서비스</span>
            </div>
            <div class="trust-item">
                <span class="trust-icon">👨‍💼</span>
                <span class="trust-text">전문가 1:1 매칭</span>
            </div>
            <div class="trust-item">
                <span class="trust-icon">💯</span>
                <span class="trust-text">무료 상담</span>
            </div>
            <div class="trust-item">
                <span class="trust-icon">⚡</span>
                <span class="trust-text">빠른 응대</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 폼 헤더
    st.markdown("""
    <div id="form-section"></div>
    <div class="form-header-box">
        <div class="form-header-title">📋 간편 상담 신청</div>
        <div class="form-header-desc">30초면 완료! 빠르게 연락드립니다.</div>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        col1, col2 = st.columns(2)
        with col1:
            privacy = st.checkbox("개인정보 수집 동의 (필수)")
        with col2:
            marketing = st.checkbox("마케팅 수신 동의 (선택)")
        
        submitted = st.form_submit_button("📩 무료 상담 신청하기", type="primary")
        
        if submitted:
            phone_digits = _digits_only(phone_raw)
            phone_formatted = format_phone(phone_digits)
            
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
                    
                    # [핵심] 신청 성공 시 메타에 'Lead' 신호 전송!
                    st.markdown(f"""
                        <script>
                            fbq('track', 'Lead');
                        </script>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.submitted = True
                    st.session_state.receipt_no = receipt_no
                    st.rerun()
    
    # 제출 완료
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
    
    # 푸터
    st.markdown(f"""
    <div class="footer-box">
        <strong>{BRAND_NAME}</strong><br>
        중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 서비스<br><br>
        <a href="{KAKAO_CHANNEL_URL}" target="_blank">카카오 채널</a><br><br>
        © 2025 {BRAND_NAME}. All rights reserved.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()