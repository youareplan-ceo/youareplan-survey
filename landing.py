import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import os
import hashlib
import time
import json
import uuid
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
# [설정] Meta Pixel & CAPI
# ==============================
META_PIXEL_ID = "1523433105534274"
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
CURRENT_URL = "https://youareplan-landing.onrender.com"

# ==============================
# [환경 설정] 주소 및 토큰
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

# [1] 기존 광고 DB 주소 (변경 금지 / 안전장치 - 이전 주소 유지)
GAS_URL_OLD = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")

# [2] 신규 CRM 주소 (회장님이 방금 주신 주소 적용 완료!)
GAS_URL_CRM = "https://script.google.com/macros/s/AKfycbwLnuz2W5QqcgBE-t-daKseiaRm3QQtT5c2l-ch8UPR5YzeOvenT-hiy4y8wQY4KhhF/exec"

# ==============================
# [추가] UTM 파라미터 읽기
# ==============================
def get_utm_params():
    """URL에서 UTM 파라미터를 읽어옵니다."""
    return {
        'utm_source': st.query_params.get("utm_source", "direct"),
        'utm_campaign': st.query_params.get("utm_campaign", "unknown"),
        'utm_content': st.query_params.get("utm_content", "unknown"),
        'utm_medium': st.query_params.get("utm_medium", "unknown"),
        'utm_term': st.query_params.get("utm_term", "unknown")
    }

# ==============================
# [기능 1] 클라이언트 사이드 픽셀 (iframe 방식)
# ==============================
def inject_facebook_pixel(event_name="PageView", custom_data=None, event_id=None):
    if event_id is None:
        event_id = str(uuid.uuid4())
    
    if custom_data:
        tracking_params = {**custom_data, "page_location": CURRENT_URL}
    else:
        tracking_params = {"page_location": CURRENT_URL}
    
    params_json = json.dumps(tracking_params)

    pixel_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
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
      fbq('track', '{event_name}', {params_json}, {{eventID: '{event_id}'}});
    </script>
    </head>
    <body></body>
    </html>
    """
    components.html(pixel_code, height=0, width=0)
    return event_id

# ==============================
# [기능 2] 서버 사이드 API (CAPI)
# ==============================
def send_meta_event(event_name, user_data=None, event_id=None):
    if not META_ACCESS_TOKEN:
        return None
    
    if event_id is None:
        event_id = str(uuid.uuid4())
        
    url = f"https://graph.facebook.com/v18.0/{META_PIXEL_ID}/events"
    
    hashed_user_data = {}
    if user_data:
        if 'phone' in user_data:
            raw_phone = re.sub(r"[^0-9]", "", str(user_data['phone']))
            if raw_phone:
                clean_phone = ('82' + raw_phone[1:]) if raw_phone.startswith('0') else ('82' + raw_phone)
                hashed_user_data['ph'] = hashlib.sha256(clean_phone.encode('utf-8')).hexdigest()
        
        if 'name' in user_data:
            raw_name = str(user_data['name']).strip().lower()
            if raw_name:
                hashed_user_data['fn'] = hashlib.sha256(raw_name.encode('utf-8')).hexdigest()

    payload = {
        "data": [{
            "event_name": event_name,
            "event_id": event_id,
            "event_time": int(time.time()),
            "action_source": "website",
            "event_source_url": CURRENT_URL,
            "user_data": hashed_user_data
        }],
        "access_token": META_ACCESS_TOKEN
    }
    
    try:
        requests.post(url, json=payload, timeout=2)
    except Exception:
        pass
    
    return event_id

# ==============================
# 유틸리티 함수
# ==============================
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", str(s) if s else "")

def format_phone(d: str) -> str:
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def save_to_sheet(data: dict) -> dict:
    """
    [핵심 수정] 양방향 전송 로직
    1. 기존 시트(Old)에 전송 (필수 - 데이터 백업용)
    2. CRM 시트(New)에 전송 (선택 - CRM/알림용)
    """
    data['token'] = API_TOKEN
    
    # 1. [필수] 기존 시트 전송
    try:
        resp_old = requests.post(GAS_URL_OLD, json=data, timeout=10)
        # 기존 시트가 실패하면 에러 리턴 (안전장치)
        if resp_old.status_code != 200:
            return {"status": "error", "message": "Old Sheet Error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # 2. [선택] 신규 CRM 시트 전송 (여기가 방금 주신 주소로 쏩니다)
    try:
        requests.post(GAS_URL_CRM, json=data, timeout=5)
    except Exception:
        pass # CRM 에러는 무시 (사용자 화면엔 성공으로 표시)

    # 3. 최종 성공 반환
    return resp_old.json()

# ==============================
# 메인 함수
# ==============================
def main():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 600px !important; }
    #MainMenu, footer, header { display: none !important; }
    
    .hero-box { background: linear-gradient(135deg, #002855 0%, #003d7a 100%); padding: 40px 20px; text-align: center; border-radius: 20px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .hero-title { font-size: 26px; font-weight: 900; margin-bottom: 8px; color: white; }
    .hero-subtitle { color: #FFD700; font-size: 22px; font-weight: 700; margin-bottom: 15px; }
    .hero-desc { color: rgba(255,255,255,0.9); font-size: 15px; line-height: 1.5; }

    .trust-box { background: rgba(128, 128, 128, 0.1); padding: 15px; text-align: center; border-radius: 12px; margin-bottom: 30px; font-size: 14px; font-weight: 500; backdrop-filter: blur(5px); border: 1px solid rgba(128, 128, 128, 0.2); }
    
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

    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    if 'utm_params' not in st.session_state:
        st.session_state.utm_params = get_utm_params()

    if not st.session_state.get('page_view_fired'):
        if not st.session_state.form_submitted:
            inject_facebook_pixel("PageView")
            st.session_state.page_view_fired = True
    
    # [화면 1] 완료 화면
    if st.session_state.form_submitted:
        if not st.session_state.get('lead_pixel_fired', False):
            event_id = str(uuid.uuid4())
            inject_facebook_pixel("Lead", event_id=event_id)
            
            user_phone = st.session_state.get('submitted_phone', '')
            user_name = st.session_state.get('submitted_name', '')
            
            capi_data = {}
            if user_phone: capi_data['phone'] = user_phone
            if user_name: capi_data['name'] = user_name
            
            send_meta_event("Lead", capi_data, event_id=event_id)
            st.session_state.lead_pixel_fired = True
            
        st.success("✅ 신청이 정상적으로 접수되었습니다!")
        
        if 'last_receipt_no' in st.session_state:
             st.markdown(f"""
                <div style="background: rgba(0, 40, 85, 0.1); border: 1px solid rgba(0, 40, 85, 0.2); padding: 20px; border-radius: 15px; text-align: center; margin-top: 15px;">
                    <h4 style="margin: 0 0 10px 0;">접수번호: {st.session_state.last_receipt_no}</h4>
                    <p style="margin: 0; opacity: 0.8;">담당자가 확인 후 빠르게 연락드리겠습니다.</p>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("새로운 상담 신청하기"):
            st.session_state.form_submitted = False
            st.session_state.lead_pixel_fired = False
            st.session_state.page_view_fired = False
            st.session_state.submitted_phone = ''
            st.session_state.submitted_name = ''
            st.rerun()

        st.markdown("""
        <div style="text-align: center; padding: 40px 20px; opacity: 0.5; font-size: 11px;">
            <strong>유아플랜</strong><br>
            중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 서비스<br>
            모든 정보는 암호화되어 안전하게 처리됩니다.
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # [화면 2] 입력 폼
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
                
                utm = st.session_state.utm_params
                
                data = {
                    'name': name,
                    'phone': formatted_phone,
                    'business_type': business_type,
                    'funding_amount': funding_amount,
                    'receipt_no': receipt_no,
                    'timestamp': timestamp,
                    'source': 'landing_page_mobile',
                    'utm_source': utm['utm_source'],
                    'utm_campaign': utm['utm_campaign'],
                    'utm_content': utm['utm_content'],
                    'utm_medium': utm['utm_medium'],
                    'utm_term': utm['utm_term']
                }
                
                save_to_sheet(data)
                
                st.session_state.form_submitted = True
                st.session_state.last_receipt_no = receipt_no
                st.session_state.submitted_phone = phone_digits
                st.session_state.submitted_name = name
                st.session_state.lead_pixel_fired = False 
                st.rerun()

    st.markdown("""
    <div style="text-align: center; padding: 40px 20px; opacity: 0.5; font-size: 11px;">
        <strong>유아플랜</strong><br>
        중소벤처기업부 · 소상공인시장진흥공단 협력 민간 상담 서비스<br>
        모든 정보는 암호화되어 안전하게 처리됩니다.
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
