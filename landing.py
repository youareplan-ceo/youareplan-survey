import streamlit as st
import requests
import re
import os
from datetime import datetime
import random

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(
    page_title="정책자금 무료 상담 | 유아플랜",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# [필수] 메타 픽셀 ID 설정
# ==============================
META_PIXEL_ID = "1523433105534274"

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

# 구글 시트 연동 URL
APPS_SCRIPT_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

# ==============================
# 픽셀 코드 삽입 (기본 View)
# ==============================
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

def save_to_sheet(data: dict) -> dict:
    try:
        data['token'] = API_TOKEN
        # 타임아웃 20초로 안정성 확보
        resp = requests.post(APPS_SCRIPT_URL, json=data, timeout=20)
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
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 600px !important; }
    #MainMenu, footer, header { display: none !important; }
    
    /* 히어로 섹션 */
    .hero-box { background: linear-gradient(135deg, #002855 0%, #003d7a 100%); padding: 40px 20px; text-align: center; border-radius: 20px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .hero-title { font-size: 26px; font-weight: 900; margin-bottom: 8px; color: white; }
    .hero-subtitle { color: #FFD700; font-size: 22px; font-weight: 700; margin-bottom: 15px; }
    .hero-desc { color: rgba(255,255,255,0.9); font-size: 15px; line-height: 1.5; }

    /* 신뢰 섹션 */
    .trust-box { background: rgba(128, 128, 128, 0.1); padding: 15px; text-align: center; border-radius: 12px; margin-bottom: 30px; font-size: 14px; font-weight: 500; backdrop-filter: blur(5px); border: 1px solid rgba(128, 128, 128, 0.2); }
    
    /* 입력창 & 버튼 */
    .stTextInput input { border-radius: 10px; }
    .stSelectbox div[data-baseweb="select"] > div { border-radius: 10px; }
    div[data-testid="stFormSubmitButton"] button { background: #002855 !important; color: white !important; border: none !important; width: 100%; padding: 16px; font-size: 18px; font-weight: bold; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.2s; margin-top: 10px; }
    div[data-testid="stFormSubmitButton"] button:hover { background: #001a38 !important; }
    div[data-testid="stFormSubmitButton"] button:active { transform: scale(0.98); }
    
    @media screen and (max-width: 480px) {
        .hero-title { font-size: 22px; }
        .hero-subtitle { font-size: 18px; }
        .hero-desc { font-size: 14px; }
        div[data-testid="stFormSubmitButton"] button { font-size: 16px; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 히어로 섹션
    st.markdown(f"""
    <div class="hero-box">
        <div style="display: flex; justify-content: center; margin-bottom: 15px;">
            <img src="{LOGO_URL}" style="height: 50px; width: auto; object-fit: contain;">
        </div>
        <div class="hero-title">정책자금 · 정부지원금</div>
        <div class="hero-subtitle">무료 상담신청</div>
        <div class="hero-desc">
            우리 기업에 딱 맞는 자금,<br>
            전문가가 1:1로 매칭해 드립니다.
        </div>
    </div>
    <div class="trust-box">
        <span>🏛️ 정부 협력</span><span style="margin: 0 8px; opacity: 0.3;">|</span>
        <span>👨‍💼 전문가 매칭</span><span style="margin: 0 8px; opacity: 0.3;">|</span>
        <span>⚡ 빠른 상담</span>
    </div>
    """, unsafe_allow_html=True)

    # 상태 초기화
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    # [화면 1] 완료 화면 (제출 성공 시)
    if st.session_state.form_submitted:
        # 1. 픽셀 Lead 이벤트 전송 (중복 전송 방지 로직 포함)
        if not st.session_state.get('pixel_fired', False):
            st.markdown(f"<script>fbq('track', 'Lead');</script>", unsafe_allow_html=True)
            st.session_state.pixel_fired = True
            
        st.success("✅ 신청이 정상적으로 접수되었습니다!")
        
        if 'last_receipt_no' in st.session_state:
             st.markdown(f"""
                <div style="background: rgba(0, 40, 85, 0.1); border: 1px solid rgba(0, 40, 85, 0.2); padding: 20px; border-radius: 15px; text-align: center; margin-top: 15px;">
                    <h4 style="margin: 0 0 10px 0;">접수번호: {st.session_state.last_receipt_no}</h4>
                    <p style="margin: 0; opacity: 0.8;">담당자가 확인 후 빠르게 연락드리겠습니다.</p>
                </div>
            """, unsafe_allow_html=True)
        
        # '새로 신청하기' 버튼
        if st.button("새로운 상담 신청하기"):
            st.session_state.form_submitted = False
            st.session_state.pixel_fired = False # 픽셀 상태도 초기화
            st.rerun()

    # [화면 2] 입력 폼 (기본 화면)
    else:
        with st.form("quick_form"):
            st.markdown("### 📋 간편 상담 신청")
            st.caption("30초면 신청이 완료됩니다.")
            
            name = st.text_input("대표자 성함", placeholder="예: 홍길동")
            phone_raw = st.text_input("연락처", placeholder="예: 01012345678")
            business_type = st.selectbox("사업자 형태", ["선택해주세요", "예비창업자", "개인사업자", "법인사업자"])
            funding_amount = st.selectbox("필요 자금 규모", ["선택해주세요", "3천만원 미만", "3천만원~1억원", "1억원~3억원", "3억원 이상"])
            
            st.markdown("---")
            col_p, col_m = st.columns(2)
            with col_p: privacy = st.checkbox("개인정보 수집 동의 (필수)", value=True)
            with col_m: marketing = st.checkbox("마케팅 수신 동의 (선택)", value=True)
            
            st.write("") 
            submitted = st.form_submit_button("📩 무료 상담 신청하기")
            
            if submitted:
                phone_digits = _digits_only(phone_raw)
                
                if not name: st.warning("⚠️ 성함을 입력해주세요.")
                elif len(phone_digits) < 10: st.warning("⚠️ 연락처를 올바르게 입력해주세요.")
                elif business_type == "선택해주세요": st.warning("⚠️ 사업자 형태를 선택해주세요.")
                elif not privacy: st.error("⚠️ 개인정보 수집에 동의해야 합니다.")
                else:
                    with st.spinner("접수 중입니다..."):
                        formatted_phone = format_phone(phone_digits)
                        receipt_no = f"YP{datetime.now().strftime('%m%d')}{random.randint(1000,9999)}"
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        data = {
                            'name': name, 'phone': formatted_phone,
                            'business_type': business_type, 'funding_amount': funding_amount,
                            'receipt_no': receipt_no, 'timestamp': timestamp,
                            'source': 'landing_page_mobile'
                        }
                        
                        save_to_sheet(data)
                        
                        # 상태 업데이트 후 화면 리로드
                        st.session_state.form_submitted = True
                        st.session_state.last_receipt_no = receipt_no
                        st.session_state.pixel_fired = False # 다음 화면에서 픽셀을 쏘기 위해 False로 설정
                        st.rerun()

    # 푸터
    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; opacity: 0.5; font-size: 11px;">
        <strong>유아플랜</strong><br>
        중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 서비스<br>
        모든 정보는 암호화되어 안전하게 처리됩니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()