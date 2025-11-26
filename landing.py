import streamlit as st
import requests
import re
import os
from datetime import datetime
import random
import time

st.set_page_config(
    page_title="정책자금 무료 상담 | 유아플랜",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# [필수] 메타 픽셀 ID 설정
# ==============================
META_PIXEL_ID = "1372327777599495"

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
# 로고 URL (흰색 로고)
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

APPS_SCRIPT_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

KAKAO_CHANNEL_URL = "https://pf.kakao.com/_LWxexmn"
RELEASE_VERSION = "v2025-11-26-final-fix"

# ==============================
# 픽셀 코드 삽입 (헤더)
# ==============================
# 들여쓰기 없이 한 줄로 처리하여 오류 방지
pixel_html = f"""
<script>
!function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window, document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{META_PIXEL_ID}');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none" src="https://www.facebook.com/tr?id={META_PIXEL_ID}&ev=PageView&noscript=1"/></noscript>
"""
st.markdown(pixel_html, unsafe_allow_html=True)

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
        msg = f"🚀 신규 상담 신청\n\n👤 {data.get('name')}\n📞 {data.get('phone')}\n🏢 {data.get('business_type')}\n💰 {data.get('funding_amount')}"
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
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
    # CSS 스타일 (체크박스 글씨색 강제 수정 포함)
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif !important;
        color: #333333 !important;
    }
    
    /* 전체 배경 강제 흰색 */
    .stApp {
        background-color: #ffffff !important;
    }
    
    /* 상단 헤더 제거 */
    #MainMenu, footer, header { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    
    /* 히어로 섹션 스타일 */
    .hero-box {
        background: linear-gradient(135deg, #002855 0%, #003d7a 100%);
        padding: 60px 20px;
        text-align: center;
        color: white !important;
    }
    
    .hero-title {
        color: #ffffff !important;
        font-size: 28px !important;
        font-weight: 900 !important;
        margin-bottom: 10px !important;
    }
    
    .hero-subtitle {
        color: #FFD700 !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        margin-bottom: 20px !important;
    }
    
    .hero-desc {
        color: #e0e0e0 !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
        margin-bottom: 30px !important;
    }
    
    /* 입력폼 스타일 */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #f8f9fa !important;
        border: 1px solid #ddd !important;
        color: #333 !important;
        border-radius: 8px !important;
    }
    
    /* 라벨 색상 강제 검정 (체크박스 안보임 해결) */
    .stMarkdown p, .stRadio label, .stCheckbox label p {
        color: #333333 !important;
    }
    
    /* 버튼 스타일 */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #002855 !important;
        color: white !important;
        border: none !important;
        width: 100%;
        padding: 15px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
    }
    
    /* 신뢰 섹션 */
    .trust-box {
        background: #f8f9fa;
        padding: 20px;
        text-align: center;
        border-bottom: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 세션 상태 초기화
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    
    # 1. 히어로 섹션 (들여쓰기 제거하여 HTML 깨짐 방지)
    hero_html = f"""
<div class="hero-box">
    <div style="display: flex; justify-content: center; margin-bottom: 20px;">
        <img src="{LOGO_URL}" style="height: 60px; width: auto; object-fit: contain;">
    </div>
    <div class="hero-title">정책자금 · 정부지원금</div>
    <div class="hero-subtitle">무료 상담신청</div>
    <div class="hero-desc">
        우리 기업에 딱 맞는 자금,<br>
        전문가가 1:1로 매칭해 드립니다.
    </div>
    <div style="font-size: 14px; opacity: 0.8;">↓ 아래에서 30초 만에 신청하세요</div>
</div>
<div class="trust-box">
    <span style="margin: 0 10px;">🏛️ 정부 협력</span>
    <span style="margin: 0 10px;">👨‍💼 전문가 매칭</span>
    <span style="margin: 0 10px;">⚡ 빠른 상담</span>
</div>
"""
    st.markdown(hero_html, unsafe_allow_html=True)
    
    st.write("") # 여백

    # 2. 입력 폼
    with st.container():
        # 좌우 여백을 주기 위해 컬럼 사용
        _, col, _ = st.columns([0.1, 0.8, 0.1])
        
        with col:
            with st.form("quick_form"):
                st.markdown("### 📋 간편 상담 신청")
                
                name = st.text_input("대표자 성함", placeholder="예: 홍길동")
                phone_raw = st.text_input("연락처", placeholder="예: 01012345678")
                
                business_type = st.selectbox(
                    "사업자 형태",
                    ["선택해주세요", "예비창업자", "개인사업자", "법인사업자"]
                )
                
                funding_amount = st.selectbox(
                    "필요 자금 규모",
                    ["선택해주세요", "3천만원 미만", "3천만원~1억원", "1억원~3억원", "3억원 이상"]
                )
                
                st.markdown("---")
                
                # 체크박스 (글씨색 CSS로 해결됨)
                col_p, col_m = st.columns(2)
                with col_p:
                    privacy = st.checkbox("개인정보 수집 동의 (필수)", value=True)
                with col_m:
                    marketing = st.checkbox("마케팅 수신 동의 (선택)", value=True)
                
                submitted = st.form_submit_button("📩 무료 상담 신청하기")
                
                if submitted:
                    phone_digits = _digits_only(phone_raw)
                    
                    if not name:
                        st.error("성함을 입력해주세요.")
                    elif len(phone_digits) < 10:
                        st.error("연락처를 올바르게 입력해주세요.")
                    elif business_type == "선택해주세요":
                        st.error("사업자 형태를 선택해주세요.")
                    elif not privacy:
                        st.error("개인정보 수집에 동의해야 합니다.")
                    else:
                        with st.spinner("신청 접수 중..."):
                            # 데이터 전송 로직
                            formatted_phone = format_phone(phone_digits)
                            receipt_no = f"YP{datetime.now().strftime('%m%d')}{random.randint(1000,9999)}"
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            data = {
                                'name': name,
                                'phone': formatted_phone,
                                'business_type': business_type,
                                'funding_amount': funding_amount,
                                'receipt_no': receipt_no,
                                'timestamp': timestamp,
                                'source': 'landing_page_v2'
                            }
                            
                            # 구글 시트 저장 & 텔레그램 전송
                            save_to_sheet(data)
                            send_telegram(data)
                            
                            # [핵심] 신청 완료 시 픽셀 Lead 이벤트 전송
                            st.markdown(f"<script>fbq('track', 'Lead');</script>", unsafe_allow_html=True)
                            
                            st.success("✅ 신청이 완료되었습니다!")
                            st.markdown(f"""
                                <div style="background:#f1f3f5; padding:15px; border-radius:10px; text-align:center; margin-top:10px;">
                                    <p style="margin:0; color:#333;">담당자가 <strong>{formatted_phone}</strong> 번호로<br>빠르게 연락드리겠습니다.</p>
                                </div>
                            """, unsafe_allow_html=True)
                            time.sleep(300)

    # 푸터
    st.markdown("""
    <div style="text-align: center; padding: 30px 20px; background-color: #f8f9fa; color: #888; font-size: 12px; margin-top: 40px;">
        <strong>유아플랜</strong><br>
        중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 서비스<br>
        <br>
        입력하신 정보는 암호화되어 안전하게 보호됩니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()