# --- Render 배포용: 외부 src 의존 제거 (Config/HTTP 내장) ---
import os
import time
import re
from datetime import datetime
from typing import Optional
from uuid import uuid4
import json
import requests
import streamlit as st

# --- Render 배포용: 외부 src 의존 제거 (Config/HTTP 내장) ---
class _Config:
    SECOND_GAS_URL = os.getenv("SECOND_GAS_URL", "https://script.google.com/macros/s/YOUR_GAS_ID/exec")
    FIRST_GAS_TOKEN_API_URL = os.getenv("FIRST_GAS_TOKEN_API_URL", "https://script.google.com/macros/s/YOUR_TOKEN_API_ID/exec")
    API_TOKEN_STAGE2 = os.getenv("API_TOKEN_2", "youareplan_stage2")

config = _Config()

# --- GAS URL 정규화 함수 ---
def _normalize_gas_url(u: str) -> str:
    try:
        s = str(u or "").strip()
    except Exception:
        return u
    if not s:
        return s
    if s.endswith("/exec") or s.endswith("/dev"):
        return s
    if "/macros/s/" in s and s.startswith("http"):
        return s + "/exec"
    return s

def _idemp_key(prefix="c2"):
    return f"{prefix}-{int(time.time()*1000)}-{uuid4().hex[:8]}"

def post_json(url, payload, headers=None, timeout=10, retries=1):
    h = {"Content-Type": "application/json", "X-Idempotency-Key": _idemp_key()}
    if headers:
        h.update(headers)

    last_exc = None
    for i in range(retries + 1):
        try:
            r = requests.post(url, data=json.dumps(payload), headers=h, timeout=timeout)
            try:
                data = r.json()
            except Exception:
                data = {"ok": False, "status": "error", "http": r.status_code, "text": r.text[:300]}
            if r.status_code == 200:
                return True, 200, (data if isinstance(data, dict) else {}), None
            if r.status_code in (408, 429) and i < retries:
                time.sleep(0.6 * (i + 1))
                continue
            return False, r.status_code, (data if isinstance(data, dict) else {}), f"HTTP {r.status_code}"
        except Exception as e:
            last_exc = e
            if i < retries:
                time.sleep(0.6 * (i + 1))
                continue
            return False, None, {}, str(last_exc)

st.set_page_config(page_title="유아플랜 정책자금 2차 심화진단", page_icon="📝", layout="centered")

# ---- 브랜드 로고 설정 ----
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

# ---- 유틸 함수 ----
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone_from_digits(d: str) -> str:
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def format_biz_no(d: str) -> str:
    if len(d) == 10:
        return f"{d[0:3]}-{d[3:5]}-{d[5:10]}"
    return d

RELEASE_VERSION = "v2025-11-26-centered"

# Centralized config
APPS_SCRIPT_URL = _normalize_gas_url(config.SECOND_GAS_URL)
TOKEN_API_URL = _normalize_gas_url(config.FIRST_GAS_TOKEN_API_URL)
INTERNAL_SHARED_KEY = "youareplan"
API_TOKEN = config.API_TOKEN_STAGE2

# KakaoTalk Channel
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"{KAKAO_CHANNEL_URL}/chat"

# 통합 CSS
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] {
    font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif;
  }
  
  :root {
    --gov-navy: #002855;
    --gov-blue: #005BAC;
    --gov-border: #cbd5e1;
    --primary-color: #002855 !important;
  }

  #MainMenu, footer { visibility: hidden !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
  .block-container{ max-width:1200px; margin:0 auto !important; padding-left:16px; padding-right:16px; }
  
  .notranslate, [translate="no"] { translate: no !important; }
  .stApp * { translate: no !important; }

  /* ========== 통합 헤더 (중앙 정렬) ========== */
  .unified-header {
    background: var(--gov-navy);
    padding: 20px 24px 16px 24px;
    text-align: center;
    border-bottom: 3px solid var(--gov-blue);
    margin: -1rem -1rem 16px -1rem;
  }
  .unified-header img {
    height: 56px;
    margin-bottom: 12px;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
  }
  .unified-header .gov-label {
    color: rgba(255,255,255,0.9);
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.5px;
  }
  @media (max-width: 640px) {
    .unified-header { padding: 16px 20px 14px 20px; }
    .unified-header img { height: 48px; margin-bottom: 10px; }
    .unified-header .gov-label { font-size: 12px; }
  }

  .gov-hero {
    padding: 16px 0 8px 0;
    border-bottom: 1px solid var(--gov-border);
    margin-bottom: 8px;
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
  
  .stApp, [data-testid="stAppViewContainer"] {
    background: #ffffff !important;
    color: #111111 !important;
  }
  
  div[data-baseweb="input"], div[data-baseweb="select"], .stTextArea>div, .stTextInput>div, .stSelectbox>div, .stMultiSelect>div, .stDateInput>div {
    background:#ffffff !important;
    border-radius:8px !important;
    border:1px solid var(--gov-border) !important;
    box-shadow: 0 1px 2px rgba(16,24,40,.04) !important;
  }
  
  div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within, .stTextArea>div:focus-within, .stTextInput>div:focus-within, .stSelectbox>div:focus-within, .stMultiSelect>div:focus-within, .stDateInput>div:focus-within {
    box-shadow: 0 2px 6px rgba(16,24,40,.12) !important;
    outline: 2px solid var(--gov-blue) !important;
    border-color: var(--gov-blue) !important;
  }

  .stTextInput input, .stTextArea textarea, div[data-baseweb="input"] input, div[data-baseweb="select"] input {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
  }

  ::placeholder { color:#9aa0a6 !important; opacity:1 !important; }
  
  input:-webkit-autofill, textarea:-webkit-autofill, select:-webkit-autofill {
    -webkit-text-fill-color:#111111 !important;
    box-shadow: 0 0 0px 1000px #ffffff inset !important;
  }
  
  .stCheckbox {
    padding: 12px 14px !important;
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
    background: #ffffff !important;
  }

  .consent-note {
    margin-top: 6px;
    font-size: 12px;
    color: #6b7280 !important;
    line-height: 1.5;
    min-height: 38px;
    display: block;
  }

  div[data-testid="stFormSubmitButton"] button,
  .stButton > button {
    background: var(--gov-navy) !important;
    color: #ffffff !important;
    border: 1px solid var(--gov-navy) !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    border-radius: 6px !important;
  }
  div[data-testid="stFormSubmitButton"] button:hover,
  .stButton > button:hover {
    filter: brightness(0.95);
  }

  .cta-wrap {
    margin-top: 10px;
    padding: 12px;
    border: 1px solid var(--gov-border);
    border-radius: 8px;
    background: #fafafa;
  }
  .cta-kakao {
    display: block;
    text-align: center;
    font-weight: 700;
    text-decoration: none;
    padding: 12px 16px;
    border-radius: 10px;
    background: #FEE500;
    color: #3C1E1E;
  }

  .stMultiSelect [data-baseweb="tag"] {
    background: #0B5BD3 !important;
    color: #ffffff !important;
    border: 0 !important;
  }
  .stMultiSelect [data-baseweb="tag"] * {
    color: #ffffff !important;
    fill: #ffffff !important;
  }

  div[data-baseweb="popover"] { z-index: 10000 !important; }
  div[data-baseweb="popover"] div[role="listbox"] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: 0 8px 24px rgba(16,24,40,.12) !important;
  }
  div[role="option"] { color: #111111 !important; background: #ffffff !important; }
  div[role="option"][aria-selected="true"] { background: #e8f1ff !important; color: #0b5bd3 !important; }
  div[role="option"]:hover { background: #f3f6fb !important; }

  @media (max-width: 768px) {
    .stApp { padding-bottom: calc(env(safe-area-inset-bottom,0px) + 200px) !important; }
  }
  textarea { min-height: 140px !important; }
  @media (max-width:640px) {
    textarea { min-height: 180px !important; }
    .stButton>button, div[data-testid="stFormSubmitButton"] button { padding:14px 18px !important; }
  }
</style>
""", unsafe_allow_html=True)

def validate_access_token(token: str, uuid_hint: str | None = None, timeout_sec: int = 10) -> dict:
    try:
        if "YOUR_GAS_ID" in TOKEN_API_URL or "YOUR_TOKEN_API_ID" in TOKEN_API_URL:
            return {"ok": False, "message": "FIRST_GAS_TOKEN_API_URL이 설정되지 않았습니다."}

        payload = {"action": "validate", "token": token, "api_token": INTERNAL_SHARED_KEY}
        if uuid_hint:
            payload["uuid"] = uuid_hint
        ok, status_code, resp_data, err = post_json(TOKEN_API_URL, payload, timeout=timeout_sec, retries=1)
        if ok:
            return resp_data or {"ok": False, "message": "empty response"}

        if status_code == 404:
            try:
                get_url = _normalize_gas_url(TOKEN_API_URL)
                r = requests.get(get_url, params=payload, timeout=timeout_sec)
                if r.status_code != 200:
                    if not get_url.endswith("/exec"):
                        r = requests.get(get_url.rstrip("/") + "/exec", params=payload, timeout=timeout_sec)
                try:
                    j = r.json()
                except Exception:
                    j = {"ok": False, "message": f"GET 응답 파싱 실패 (HTTP {r.status_code})"}
                if r.status_code == 200:
                    return j
                return {"ok": False, "message": f"HTTP {r.status_code}"}
            except Exception as ge:
                return {"ok": False, "message": str(ge)}

        return {"ok": False, "message": err or f"HTTP {status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

def save_to_google_sheet(data, timeout_sec: int = 45, retries: int = 0, test_mode: bool = False):
    if test_mode:
        return {"status": "test", "message": "테스트 모드 - 저장 생략"}

    data['token'] = API_TOKEN
    request_id = str(uuid4())
    ok, status_code, resp_data, err = post_json(
        _normalize_gas_url(APPS_SCRIPT_URL),
        data,
        headers={"X-Request-ID": request_id, "Content-Type": "application/json"},
        timeout=timeout_sec,
        retries=0,
    )
    if "YOUR_GAS_ID" in APPS_SCRIPT_URL:
        return {"status": "error", "message": "SECOND_GAS_URL이 설정되지 않았습니다."}

    if (not ok) and isinstance(resp_data, dict) and resp_data.get("ok") is True:
        ok, status_code, err = True, (status_code or 200), None

    if ok:
        return resp_data or {"status": "success"}

    is_timeout_or_server_error = (
        (status_code is None) or
        status_code == 429 or
        (500 <= (status_code or 0) <= 599)
    )
    
    if is_timeout_or_server_error:
        st.info("⏳ 서버 응답이 지연되어 재시도 중입니다...")
        ok2, status_code2, resp_data2, err2 = post_json(
            _normalize_gas_url(APPS_SCRIPT_URL),
            data,
            headers={"X-Request-ID": request_id, "Content-Type": "application/json"},
            timeout=timeout_sec,
            retries=1,
        )
        
        if (not ok2) and isinstance(resp_data2, dict) and resp_data2.get("ok") is True:
            ok2, status_code2, err2 = True, (status_code2 or 200), None
        if ok2:
            return resp_data2 or {"status": "success"}
        
        is_timeout_again = (
            (status_code2 is None) or
            status_code2 == 429 or
            (500 <= (status_code2 or 0) <= 599)
        )
        
        if is_timeout_again:
            return {"status": "success_delayed", "message": "서버 처리 완료 (응답 지연)"}
        
        if resp_data2 and ((status_code2 and 200 <= status_code2 <= 299) and (status_code2 == 202 or str(resp_data2.get('status','')).lower() == 'pending')):
            return {"status": "success_delayed", "message": "처리 진행 중"}
        
        return {"status": "error", "message": err2 or err or "network error"}

    if resp_data and resp_data.get('message'):
        st.error(f"서버 응답: {resp_data.get('message')}")
    return {"status": "error", "message": err or f"HTTP {status_code}"}

def main():
    if "saving2" not in st.session_state:
        st.session_state.saving2 = False

    # ========== 통합 헤더 (중앙 정렬) ==========
    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <div class="gov-label">대한민국 정부 협력 서비스</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="gov-hero">
      <h2>정부 지원금·정책자금 심화 진단</h2>
      <p>정밀 분석 및 서류 준비를 위한 상세 정보 입력</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("##### 맞춤형 정책자금 매칭을 위해 상세 정보를 입력해주세요.")

    try:
        qp = st.query_params
        is_test_mode = qp.get("test") == "true"
        magic_token = qp.get("t")
        uuid_hint = qp.get("u")
    except Exception:
        is_test_mode = False
        magic_token = None
        uuid_hint = None

    if is_test_mode:
        st.warning("⚠️ 테스트 모드 - 실제 저장되지 않습니다.")

    if not magic_token:
        st.error("접근 토큰이 없습니다. 담당자가 발송한 링크로 접속해 주세요.")
        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 재발급 요청하기</a></div>", unsafe_allow_html=True)
        return

    v = validate_access_token(magic_token, uuid_hint=uuid_hint)
    if not v.get("ok"):
        msg = v.get("message") or v.get("error") or "토큰 검증 실패"
        st.error(f"접속이 차단되었습니다: {msg}")
        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 새 링크 재발급 요청</a></div>", unsafe_allow_html=True)
        return

    parent_rid_fixed = v.get("parent_receipt_no", "")
    remain_min = v.get("remaining_minutes")
    if remain_min is None:
        sec = v.get("remaining_seconds")
        if isinstance(sec, (int, float)):
            remain_min = max(0, int(round(sec / 60)))
    if remain_min is not None:
        st.markdown(
            f"<div style='margin:8px 0 0 0;'><span style='display:inline-block;background:#e8f1ff;color:#0b5bd3;border:1px solid #b6c2d5;padding:6px 10px;border-radius:999px;font-weight:600;'>남은 시간: {int(remain_min)}분</span></div>",
            unsafe_allow_html=True,
        )

    masked_phone = v.get("phone_mask")
    if masked_phone:
        st.caption(f"인증됨 · 접수번호: **{parent_rid_fixed}** / 연락처: **{masked_phone}**")

    st.info("✔ 1차 상담 후 진행하는 **심화 진단** 절차입니다.")
    
    with st.form("second_survey"):
        if 'submitted_2' not in st.session_state:
            st.session_state.submitted_2 = False
            
        st.markdown("### 📝 2차 설문 - 상세 정보")
        
        st.markdown("#### 👤 기본 정보")
        name = st.text_input("성함 (필수)", placeholder="홍길동").strip()
        parent_rid = parent_rid_fixed
        st.text_input("1차 접수번호", value=parent_rid, disabled=True)
        st.caption("초대 링크에 포함된 접수번호로 자동 설정됩니다.")
        phone_raw = st.text_input("연락처 (필수)", placeholder="예: 01012345678")
        st.caption("숫자만 입력해도 됩니다. 예: 01012345678")
        biz_no_raw = st.text_input("사업자등록번호 (선택)", placeholder="예: 0000000000")
        st.caption("10자리 숫자입니다. 예: 1234567890")
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")
        st.markdown("---")
        
        st.markdown("#### 📊 사업 정보")
        company = st.text_input("사업자명 (필수)")
        
        col1, col2 = st.columns(2)
        with col1:
            startup_date = st.date_input("사업 시작일 (필수)", min_value=datetime(1900, 1, 1), format="YYYY-MM-DD")
        with col2:
            st.write(" ")
        
        st.markdown("#### 💰 재무 현황")
        st.markdown("**최근 3년간 연매출액 (단위: 만원)**")
        current_year = datetime.now().year
        col_y1, col_y2, col_y3 = st.columns(3)
        with col_y1:
            revenue_y1 = st.text_input(f"{current_year}년", placeholder="예: 5000")
        with col_y2:
            revenue_y2 = st.text_input(f"{current_year-1}년", placeholder="예: 3500")
        with col_y3:
            revenue_y3 = st.text_input(f"{current_year-2}년", placeholder="예: 2000")
        
        col_cap, col_debt = st.columns(2)
        with col_cap:
            capital_amount = st.text_input("자본금(만원)", placeholder="예: 5000")
        with col_debt:
            debt_amount = st.text_input("부채(만원)", placeholder="예: 12000")
        
        st.caption("⚠️ 매출액은 정책자금 한도 산정의 기준이 됩니다.")
        st.markdown("---")

        st.markdown("#### 💡 기술·인증 보유")
        ip_options = ["특허 보유", "실용신안 보유", "디자인 등록 보유", "해당 없음"]
        ip_status = st.multiselect("지식재산권 (선택)", ip_options, placeholder="선택하세요")
        
        official_certs = st.multiselect(
            "공식 인증(선택)",
            ["벤처기업", "이노비즈", "메인비즈", "ISO", "기업부설연구소 인증", "해당 없음"],
            placeholder="선택하세요"
        )
        
        research_lab = st.radio("기업부설연구소 (선택)", ["보유", "미보유"], horizontal=True)
        st.markdown("---")

        st.markdown("#### 💵 자금 활용 계획")
        funding_purpose = st.multiselect("자금 용도 (선택)", ["시설자금", "운전자금", "R&D자금", "기타"], placeholder="선택하세요")
        
        detailed_plan = st.text_area("상세 활용 계획 (선택)", placeholder="예: 생산설비 2억, 원자재 구매 1억")
        
        incentive_status = st.multiselect(
            "우대 조건(선택)",
            ["여성기업", "청년창업", "장애인기업", "소공인", "사회적기업", "해당 없음"],
            placeholder="선택하세요"
        )
        st.markdown("---")
        
        st.markdown("#### 🚨 리스크 확인")
        col_a, col_b = st.columns(2)
        with col_a:
            tax_status = st.selectbox("세금 체납 (필수)", ["체납 없음", "체납 있음", "분납 중"])
        with col_b:
            credit_status = st.selectbox("금융 연체 (필수)", ["연체 없음", "30일 미만", "30일 이상"])
        
        business_status = st.selectbox("영업 상태 (필수)", ["정상 영업", "휴업", "폐업 예정"])
        
        risk_msgs = []
        if tax_status != "체납 없음": risk_msgs.append("세금 체납")
        if credit_status != "연체 없음": risk_msgs.append("금융 연체")
        if business_status != "정상 영업": risk_msgs.append("휴/폐업")
        if risk_msgs:
            st.warning(f"지원 제한 사항: {', '.join(risk_msgs)}")
        st.markdown("---")

        st.markdown("#### 🤝 동의")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)")
            st.markdown('<span class="consent-note">상담 확인·자격 검토·연락 목적. 보관: 3년. 동의 철회 시 삭제.</span>', unsafe_allow_html=True)
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")
            st.markdown('<span class="consent-note">신규 정책자금/지원사업 알림. 언제든지 수신 거부 가능.</span>', unsafe_allow_html=True)

        submitted = st.form_submit_button("📩 2차 설문 제출", type="primary", disabled=st.session_state.get("saving2", False))

        if submitted and not st.session_state.submitted_2:
            st.session_state.submitted_2 = True

            d_phone = _digits_only(phone_raw)
            formatted_phone = format_phone_from_digits(d_phone) if d_phone else ""

            d_biz = _digits_only(biz_no_raw)
            formatted_biz = format_biz_no(d_biz) if d_biz else ""

            name_ok = bool(name and len(name.strip()) >= 2)
            phone_digits = _digits_only(formatted_phone)
            biz_digits = _digits_only(formatted_biz)
            phone_ok = (len(phone_digits) == 11 and phone_digits.startswith("010"))
            biz_ok = (len(biz_digits) == 0) or (len(biz_digits) == 10)

            if not name_ok:
                st.error("성함은 2자 이상 입력해주세요.")
                st.session_state.submitted_2 = False
            elif not phone_ok:
                st.error("연락처는 010으로 시작하는 11자리여야 합니다.")
                st.session_state.submitted_2 = False
            elif not biz_ok:
                st.error("사업자등록번호는 비워두거나 10자리로 입력해주세요.")
                st.session_state.submitted_2 = False
            elif not privacy_agree:
                st.error("개인정보 수집·이용 동의는 필수입니다.")
                st.session_state.submitted_2 = False
            elif not parent_rid:
                st.error("1차 접수번호는 필수입니다.")
                st.session_state.submitted_2 = False
            else:
                st.session_state.saving2 = True
                with st.spinner("⏳ 제출 처리 중입니다..."):
                    survey_data = {
                        'name': name,
                        'phone': formatted_phone,
                        'email': email,
                        'biz_reg_no': formatted_biz,
                        'business_name': company,
                        'startup_date': startup_date.strftime('%Y-%m-%d'),
                        'revenue_y1': revenue_y1,
                        'revenue_y2': revenue_y2,
                        'revenue_y3': revenue_y3,
                        'capital_amount': capital_amount,
                        'debt_amount': debt_amount,
                        'ip_status': ', '.join(ip_status) if ip_status else '해당 없음',
                        'official_certs': ', '.join(official_certs) if official_certs else '해당 없음',
                        'research_lab_status': research_lab,
                        'funding_purpose': ', '.join(funding_purpose) if funding_purpose else '미입력',
                        'detailed_funding': detailed_plan,
                        'incentive_status': ', '.join(incentive_status) if incentive_status else '해당 없음',
                        'tax_status': tax_status,
                        'credit_status': credit_status,
                        'business_status': business_status,
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree,
                        'release_version': RELEASE_VERSION,
                        'parent_receipt_no': parent_rid,
                        'magic_token': magic_token,
                    }
                    if uuid_hint:
                        survey_data['uuid'] = uuid_hint
                    elif not (survey_data.get('uuid') or survey_data.get('UUID')):
                        survey_data['uuid'] = str(uuid4())

                    v2 = validate_access_token(magic_token, uuid_hint=uuid_hint)
                    if not v2.get("ok"):
                        st.error(f"접속이 만료되었습니다: {v2.get('message', '만료/소진')}")
                        st.session_state.submitted_2 = False
                        st.session_state.saving2 = False
                        st.stop()

                    result = save_to_google_sheet(survey_data, timeout_sec=45, retries=0, test_mode=is_test_mode)

                    success_statuses = ('success', 'test', 'pending', 'success_delayed')
                    
                    if result.get('status') in success_statuses:
                        if result.get('status') == 'success_delayed':
                            st.success("✅ 2차 설문이 접수되었습니다!")
                            st.info("📞 서버 처리가 진행 중입니다. 1영업일 내 연락드립니다.")
                        else:
                            st.success("✅ 2차 설문 제출 완료!")
                        
                        st.info("전문가가 심층 분석 후 연락드립니다.")
                        st.markdown(f"""
                        <div class="cta-wrap">
                            <a class="cta-kakao" href="{KAKAO_CHAT_URL}" target="_blank">
                                💬 전문가에게 문의하기
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                        st.session_state.saving2 = False
                        st.stop()
                    else:
                        st.error("❌ 제출 실패. 잠시 후 다시 시도해주세요.")
                        st.markdown(f"""
                        <div class="cta-wrap">
                            <a class="cta-kakao" href="{KAKAO_CHAT_URL}" target="_blank">
                                💬 담당자에게 문의하기
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                        st.session_state.submitted_2 = False
                        st.session_state.saving2 = False

if __name__ == "__main__":
    main()