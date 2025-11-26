# -*- coding: utf-8 -*-
"""
유아플랜 2차 설문 – Streamlit (v2-2025-11-26)
수정사항:
- 매출 입력 동적화 (영업기간 기반)
- 다크모드/라이트모드 자동 적응
- 날짜 한글 포맷
- SelectBox/MultiSelect 색상 수정
"""
import os
import time
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional
from uuid import uuid4
import json
import requests
import streamlit as st

# ====== 환경 설정 ======
class _Config:
    SECOND_GAS_URL = os.getenv("SECOND_GAS_URL", "")
    FIRST_GAS_TOKEN_API_URL = os.getenv("FIRST_GAS_TOKEN_API_URL", "")
    API_TOKEN_STAGE2 = os.getenv("API_TOKEN_2", "youareplan_stage2")

config = _Config()

RELEASE_VERSION = "v2-2025-11-26"

# ====== 브랜드 설정 ======
BRAND_NAME = "유아플랜"
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"{KAKAO_CHANNEL_URL}/chat"

# ====== 페이지 설정 ======
st.set_page_config(page_title="유아플랜 정책자금 2차 심화진단", page_icon="📝", layout="centered")

# ====== CSS (다크모드/라이트모드 자동 적응) ======
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }

  /* ===== CSS 변수 (라이트모드 기본) ===== */
  :root {
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --bg-input: #ffffff;
    --text-primary: #0F172A;
    --text-secondary: #64748b;
    --text-placeholder: #9ca3af;
    --border-color: #cbd5e1;
    --border-focus: #0B5BD3;
    --tag-bg: #2563eb;
    --tag-text: #ffffff;
    --brand-navy: #002855;
    --brand-blue: #0B5BD3;
    --dropdown-bg: #ffffff;
    --dropdown-hover: #f1f5f9;
    --dropdown-selected: #e0f2fe;
    --expander-bg: #f8fafc;
  }

  /* ===== 다크모드 변수 ===== */
  @media (prefers-color-scheme: dark) {
    :root {
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-input: #1e293b;
      --text-primary: #f1f5f9;
      --text-secondary: #94a3b8;
      --text-placeholder: #64748b;
      --border-color: #334155;
      --border-focus: #3b82f6;
      --tag-bg: #3b82f6;
      --tag-text: #ffffff;
      --brand-navy: #1e3a5f;
      --brand-blue: #3b82f6;
      --dropdown-bg: #1e293b;
      --dropdown-hover: #334155;
      --dropdown-selected: #1e40af;
      --expander-bg: #1e293b;
    }
  }

  /* ===== 기본 배경/텍스트 ===== */
  html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
  }

  /* 상단 메뉴/푸터/사이드바 숨김 */
  #MainMenu, footer { visibility: hidden !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
  .block-container { max-width: 1200px; margin: 0 auto !important; padding: 16px; }

  /* ===== 브랜드 바 ===== */
  .brandbar {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 14px; border-bottom: 1px solid var(--border-color);
    background: var(--bg-primary);
  }
  .brandbar img { height: 48px; max-height: 48px; display: block; object-fit: contain; }
  @media (max-width: 740px) { .brandbar img { height: 64px; max-height: 64px; } }

  /* ===== 정부 협력 바 ===== */
  .gov-topbar {
    width: 100%; background: var(--brand-navy);
    color: #ffffff !important; font-size: 13px;
    padding: 8px 14px; border-bottom: 3px solid var(--brand-blue);
  }
  .gov-topbar * { color: #ffffff !important; }

  .gov-hero {
    padding: 16px 0 8px 0; border-bottom: 1px solid var(--border-color); margin-bottom: 8px;
  }
  .gov-hero h2 { color: var(--brand-navy); margin: 0 0 6px 0; font-weight: 700; }
  @media (prefers-color-scheme: dark) {
    .gov-hero h2 { color: var(--brand-blue); }
  }
  .gov-hero p { color: var(--text-secondary); margin: 0; }

  /* ===== 입력 필드 공통 ===== */
  .stTextInput > div, .stTextInput > div > div,
  .stTextArea > div, .stTextArea > div > div,
  .stSelectbox > div, .stSelectbox > div > div,
  .stMultiSelect > div, .stMultiSelect > div > div,
  .stNumberInput > div, .stNumberInput > div > div,
  .stDateInput > div, .stDateInput > div > div,
  div[data-baseweb="input"], div[data-baseweb="input"] > div,
  div[data-baseweb="select"], div[data-baseweb="select"] > div,
  div[data-baseweb="select"] > div > div,
  div[data-baseweb="select"] > div > div > div {
    background-color: var(--bg-input) !important;
    border-color: var(--border-color) !important;
    border-radius: 8px !important;
  }

  /* 입력 필드 텍스트 */
  .stTextInput input, .stTextArea textarea,
  .stNumberInput input, .stDateInput input,
  div[data-baseweb="input"] input,
  div[data-baseweb="select"] input,
  div[data-baseweb="select"] [data-baseweb="tag"] + input {
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    background-color: transparent !important;
  }

  /* Placeholder */
  ::placeholder { color: var(--text-placeholder) !important; opacity: 1 !important; }
  input::placeholder, textarea::placeholder { color: var(--text-placeholder) !important; }

  /* Focus 상태 */
  .stTextInput > div:focus-within, .stTextArea > div:focus-within,
  .stSelectbox > div:focus-within, .stMultiSelect > div:focus-within,
  div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
    outline: 2px solid var(--border-focus) !important;
    border-color: var(--border-focus) !important;
  }

  /* ===== SelectBox / MultiSelect 드롭다운 ===== */
  div[data-baseweb="popover"], div[data-baseweb="menu"],
  div[role="listbox"], ul[role="listbox"] {
    background-color: var(--dropdown-bg) !important;
    border: 1px solid var(--border-color) !important;
  }

  /* 드롭다운 옵션 */
  li[role="option"], div[role="option"] {
    background-color: var(--dropdown-bg) !important;
    color: var(--text-primary) !important;
  }
  li[role="option"]:hover, div[role="option"]:hover {
    background-color: var(--dropdown-hover) !important;
  }
  li[role="option"][aria-selected="true"], div[role="option"][aria-selected="true"] {
    background-color: var(--dropdown-selected) !important;
  }

  /* ===== MultiSelect 태그 ===== */
  [data-baseweb="tag"] {
    background-color: var(--tag-bg) !important;
    background: var(--tag-bg) !important;
  }
  [data-baseweb="tag"] span, [data-baseweb="tag"] *:not(svg):not(path) {
    color: var(--tag-text) !important;
    -webkit-text-fill-color: var(--tag-text) !important;
  }
  [data-baseweb="tag"] svg, [data-baseweb="tag"] path {
    fill: var(--tag-text) !important;
  }

  /* ===== Expander ===== */
  .streamlit-expanderHeader, details summary,
  [data-testid="stExpander"] summary,
  [data-testid="stExpander"] > div:first-child {
    background-color: var(--expander-bg) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
  }
  [data-testid="stExpander"] div[data-testid="stMarkdownContainer"] {
    color: var(--text-primary) !important;
  }

  /* ===== 체크박스 ===== */
  .stCheckbox {
    padding: 12px 14px !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    background: var(--bg-secondary) !important;
  }
  .stCheckbox label, .stCheckbox span {
    color: var(--text-primary) !important;
  }

  /* ===== 버튼 ===== */
  .stButton > button, div[data-testid="stFormSubmitButton"] button {
    background: var(--brand-navy) !important;
    color: #ffffff !important;
    border: 1px solid var(--brand-navy) !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    border-radius: 6px !important;
  }
  .stButton > button:hover, div[data-testid="stFormSubmitButton"] button:hover {
    filter: brightness(0.95) !important;
  }
  .stButton > button *, div[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
    fill: #ffffff !important;
  }

  /* ===== CTA 버튼 ===== */
  .cta-wrap {
    margin-top: 10px; padding: 12px;
    border: 1px solid var(--border-color);
    border-radius: 8px; background: var(--bg-secondary);
  }
  .cta-kakao {
    display: block; text-align: center; font-weight: 700;
    text-decoration: none; padding: 12px 16px; border-radius: 10px;
    background: #FEE500; color: #3C1E1E; border: 1px solid #FEE500;
  }
  .cta-kakao:hover { filter: brightness(0.97); }

  /* ===== 동의 영역 ===== */
  .consent-note {
    margin-top: 6px; font-size: 12px;
    color: var(--text-secondary) !important;
    line-height: 1.5; min-height: 38px; display: block;
  }

  /* ===== 모바일 대응 ===== */
  @media (max-width: 768px) {
    .stApp { padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 200px) !important; }
    div[data-baseweb="popover"] { z-index: 10000 !important; }
    div[data-baseweb="popover"] div[role="listbox"] { max-height: 38vh !important; }
  }
  textarea { min-height: 140px !important; }
  @media (max-width: 640px) {
    textarea { min-height: 180px !important; }
    .stButton > button, div[data-testid="stFormSubmitButton"] button { padding: 14px 18px !important; }
  }
</style>
""", unsafe_allow_html=True)

# ====== 유틸 함수 ======
def _get_logo_url() -> str:
    try:
        url = st.secrets.get("YOUAREPLAN_LOGO_URL", None)
        if url: return str(url)
    except: pass
    return os.getenv("YOUAREPLAN_LOGO_URL") or DEFAULT_LOGO_URL

def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone(d: str) -> str:
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def format_biz_no(d: str) -> str:
    if len(d) == 10:
        return f"{d[0:3]}-{d[3:5]}-{d[5:10]}"
    return d

def _normalize_gas_url(u: str) -> str:
    try:
        s = str(u or "").strip()
    except: return u
    if not s: return s
    if s.endswith("/exec") or s.endswith("/dev"): return s
    if "/macros/s/" in s and s.startswith("http"): return s + "/exec"
    return s

def _idemp_key(prefix="c2"):
    return f"{prefix}-{int(time.time()*1000)}-{uuid4().hex[:8]}"

def post_json(url, payload, headers=None, timeout=10, retries=1):
    h = {"Content-Type": "application/json", "X-Idempotency-Key": _idemp_key()}
    if headers: h.update(headers)
    last_exc = None
    for i in range(retries + 1):
        try:
            r = requests.post(url, data=json.dumps(payload), headers=h, timeout=timeout)
            try:
                data = r.json()
            except:
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

# ====== 토큰 검증 ======
def validate_access_token(token: str, uuid_hint: str = None, timeout_sec: int = 10) -> dict:
    TOKEN_API_URL = _normalize_gas_url(config.FIRST_GAS_TOKEN_API_URL)
    INTERNAL_SHARED_KEY = "youareplan"
    
    if not TOKEN_API_URL:
        return {"ok": False, "message": "FIRST_GAS_TOKEN_API_URL이 설정되지 않았습니다."}
    
    try:
        payload = {"action": "validate", "token": token, "api_token": INTERNAL_SHARED_KEY}
        if uuid_hint: payload["uuid"] = uuid_hint
        
        ok, status_code, resp_data, err = post_json(TOKEN_API_URL, payload, timeout=timeout_sec, retries=1)
        if ok: return resp_data or {"ok": False, "message": "empty response"}
        
        if status_code == 404:
            import requests as req
            r = req.get(TOKEN_API_URL, params=payload, timeout=timeout_sec)
            if r.status_code == 200:
                try: return r.json()
                except: pass
        
        return {"ok": False, "message": err or f"HTTP {status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

# ====== 저장 함수 ======
def save_to_google_sheet(data, timeout_sec: int = 45, test_mode: bool = False):
    if test_mode:
        return {"status": "test", "message": "테스트 모드"}
    
    APPS_SCRIPT_URL = _normalize_gas_url(config.SECOND_GAS_URL)
    if not APPS_SCRIPT_URL:
        return {"status": "error", "message": "SECOND_GAS_URL이 설정되지 않았습니다."}
    
    data['token'] = config.API_TOKEN_STAGE2
    request_id = str(uuid4())
    
    ok, status_code, resp_data, err = post_json(
        APPS_SCRIPT_URL, data,
        headers={"X-Request-ID": request_id},
        timeout=timeout_sec, retries=1
    )
    
    if ok or (isinstance(resp_data, dict) and resp_data.get("ok") is True):
        return resp_data or {"status": "success"}
    
    is_timeout = (status_code is None) or status_code == 429 or (500 <= (status_code or 0) <= 599)
    if is_timeout:
        st.info("⏳ 서버 응답 지연, 재시도 중...")
        ok2, sc2, rd2, err2 = post_json(APPS_SCRIPT_URL, data, headers={"X-Request-ID": request_id}, timeout=timeout_sec, retries=2)
        if ok2 or (isinstance(rd2, dict) and rd2.get("ok") is True):
            return rd2 or {"status": "success"}
        if (sc2 is None) or sc2 == 429 or (500 <= (sc2 or 0) <= 599):
            return {"status": "success_delayed", "message": "서버 처리 완료 (응답 지연)"}
        return {"status": "error", "message": err2 or err or "network error"}
    
    return {"status": "error", "message": err or f"HTTP {status_code}"}

# ====== 메인 함수 ======
def main():
    if "saving2" not in st.session_state:
        st.session_state.saving2 = False
    if "submitted_2" not in st.session_state:
        st.session_state.submitted_2 = False

    # 브랜드 바
    logo_url = _get_logo_url()
    st.markdown(f"""
<div class="brandbar">
  {f'<img src="{logo_url}" alt="{BRAND_NAME} 로고" />' if logo_url else ''}
</div>
<div class="gov-topbar">대한민국 정부 협력 서비스</div>
<div class="gov-hero">
  <h2>정부 지원금·정책자금 심화 진단</h2>
  <p>정밀 분석 및 서류 준비를 위한 상세 정보 입력</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("##### 맞춤형 정책자금 매칭을 위해 상세 정보를 입력해주세요.")

    # 쿼리 파라미터
    try:
        qp = st.query_params
        is_test_mode = qp.get("test") == "true"
        magic_token = qp.get("t")
        uuid_hint = qp.get("u")
    except:
        is_test_mode, magic_token, uuid_hint = False, None, None

    if is_test_mode:
        st.warning("⚠️ 테스트 모드 - 실제 저장되지 않습니다.")

    # 토큰 검증
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

    parent_rid = v.get("parent_receipt_no", "")
    remain_min = v.get("remaining_minutes")
    if remain_min is None:
        sec = v.get("remaining_seconds")
        if isinstance(sec, (int, float)):
            remain_min = max(0, int(round(sec / 60)))
    
    if remain_min is not None:
        st.markdown(f"<div style='margin:8px 0;'><span style='display:inline-block;background:#e8f1ff;color:#0b5bd3;border:1px solid #b6c2d5;padding:6px 10px;border-radius:999px;font-weight:600;'>남은 시간: {int(remain_min)}분</span></div>", unsafe_allow_html=True)

    masked_phone = v.get("phone_mask")
    if masked_phone:
        st.caption(f"인증됨 · 접수번호: **{parent_rid}** / 연락처: **{masked_phone}**")

    st.info("✔ 1차 상담 후 진행하는 **심화 진단** 절차입니다.")

    # ====== 설문 폼 ======
    with st.form("second_survey"):
        
        # 1. 기본 정보
        st.markdown("### 1. 기본 정보")
        col_name, col_phone = st.columns(2)
        with col_name:
            name = st.text_input("성함 *", placeholder="홍길동")
        with col_phone:
            phone_raw = st.text_input("연락처 *", placeholder="01012345678")
        
        col_email, col_biz = st.columns(2)
        with col_email:
            email = st.text_input("이메일 (선택)", placeholder="email@example.com")
        with col_biz:
            biz_no_raw = st.text_input("사업자등록번호 (선택)", placeholder="0000000000")

        st.text_input("1차 접수번호", value=parent_rid, disabled=True)

        # 2. 사업 정보
        st.markdown("---")
        st.markdown("### 2. 사업 정보")
        
        company_name = st.text_input("상호(사업자명) *", placeholder="예: 유아플랜")
        
        col_date, col_store = st.columns(2)
        with col_date:
            st.caption("📅 사업개시일 (년/월/일)")
            startup_date = st.date_input(
                "사업 개시일",
                min_value=datetime(1950, 1, 1),
                value=datetime(2024, 1, 1),
                format="YYYY/MM/DD",
                label_visibility="collapsed"
            )
        with col_store:
            store_type = st.selectbox("점포 형태", ["자가", "임차", "무점포", "기타"])

        # 임차인 경우 보증금/월세
        if store_type == "임차":
            col_dep, col_rent = st.columns(2)
            with col_dep:
                deposit = st.number_input("보증금 (만원)", min_value=0, step=100, value=0)
            with col_rent:
                monthly_rent = st.number_input("월세 (만원)", min_value=0, step=10, value=0)
        else:
            deposit, monthly_rent = 0, 0

        # 3. 재무 현황 (동적 매출 입력)
        st.markdown("---")
        st.markdown("### 3. 재무 현황")
        
        # 영업 기간 계산
        today = datetime.now()
        months_operating = (today.year - startup_date.year) * 12 + (today.month - startup_date.month)
        current_year = today.year
        
        st.write("📊 **매출액** (단위: 만원)")
        
        rev_current, rev_y1, rev_y2 = 0, 0, 0
        
        if months_operating < 6:
            st.info("💡 사업 초기(6개월 미만)입니다. 올해 예상 매출만 입력하세요.")
            rev_current = st.number_input(f"{current_year}년 예상 매출", min_value=0, step=100)
        elif months_operating < 18:
            st.caption("예: 1억 5천만원 → 15000 입력")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                rev_current = st.number_input(f"{current_year}년 (예상)", min_value=0, step=100)
            with col_r2:
                if startup_date.year < current_year:
                    rev_y1 = st.number_input(f"{current_year-1}년", min_value=0, step=100)
                else:
                    st.caption(f"{current_year-1}년: 해당 없음")
        else:
            st.caption("예: 1억 5천만원 → 15000 입력")
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                rev_current = st.number_input(f"{current_year}년", min_value=0, step=100)
            with col_r2:
                rev_y1 = st.number_input(f"{current_year-1}년", min_value=0, step=100)
            with col_r3:
                rev_y2 = st.number_input(f"{current_year-2}년", min_value=0, step=100)

        col_cap, col_debt = st.columns(2)
        with col_cap:
            capital = st.number_input("자본금 (만원)", min_value=0, step=100, help="없으면 0")
        with col_debt:
            debt = st.number_input("부채 총계 (만원)", min_value=0, step=100, help="없으면 0")

        # 4. 보증 이용 경험
        st.markdown("---")
        st.markdown("### 4. 보증/인증 현황")
        
        guarantee_options = [
            "이용 경험 없음",
            "신용보증기금",
            "기술보증기금",
            "지역신용보증재단",
            "소상공인시장진흥공단",
            "기타"
        ]
        guarantee_history = st.multiselect("보증기관 이용 경험", guarantee_options, default=["이용 경험 없음"])

        cert_options = ["해당 없음", "벤처기업", "이노비즈", "메인비즈", "ISO", "기업부설연구소"]
        certifications = st.multiselect("공식 인증 보유", cert_options, default=["해당 없음"])

        research_lab = st.radio("기업부설연구소/연구전담부서", ["미보유", "보유"], horizontal=True)

        # 5. 자금 용도
        st.markdown("---")
        st.markdown("### 5. 자금 용도")
        
        purpose_options = ["운전자금", "시설자금", "창업자금", "R&D자금", "수출자금", "기타"]
        fund_purpose = st.multiselect("필요 자금 용도", purpose_options, default=["운전자금"])

        # 6. 자가 진단
        st.markdown("---")
        st.markdown("### 6. 자가 진단")
        
        risk_tax = st.checkbox("현재 국세/지방세 체납 중입니까?")
        risk_overdue = st.checkbox("최근 3개월 내 대출금 연체 사실이 있습니까?")

        # 7. 동의
        st.markdown("---")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집 및 이용에 동의합니다. (필수)")
            with st.expander("동의 내용 보기"):
                st.markdown("""
**수집 목적**: 정책자금 상담 및 자격 검토  
**수집 항목**: 성함, 연락처, 이메일, 사업자정보, 재무정보  
**보유 기간**: 상담 완료 후 3년
""")
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신에 동의합니다. (선택)")

        # 제출 버튼
        submitted = st.form_submit_button("입력 완료 및 제출", type="primary", disabled=st.session_state.get("saving2", False))

        if submitted and not st.session_state.submitted_2:
            st.session_state.submitted_2 = True

            # 유효성 검사
            d_phone = _digits_only(phone_raw)
            formatted_phone = format_phone(d_phone)
            d_biz = _digits_only(biz_no_raw)
            formatted_biz = format_biz_no(d_biz) if d_biz else ""

            name_ok = bool(name and len(name.strip()) >= 2)
            phone_ok = (len(d_phone) == 11 and d_phone.startswith("010"))
            biz_ok = (len(d_biz) == 0) or (len(d_biz) == 10)

            if not name_ok:
                st.error("성함을 2자 이상 입력해주세요.")
                st.session_state.submitted_2 = False
            elif not phone_ok:
                st.error("연락처는 010으로 시작하는 11자리여야 합니다.")
                st.session_state.submitted_2 = False
            elif not biz_ok:
                st.error("사업자등록번호는 10자리이거나 비워두세요.")
                st.session_state.submitted_2 = False
            elif not privacy_agree:
                st.error("개인정보 수집 동의는 필수입니다.")
                st.session_state.submitted_2 = False
            else:
                st.session_state.saving2 = True
                with st.spinner("⏳ 제출 처리 중..."):
                    
                    # 보증/인증/용도 문자열 변환
                    guarantee_str = ", ".join(guarantee_history) if guarantee_history else "이용 경험 없음"
                    cert_str = ", ".join(certifications) if certifications else "해당 없음"
                    purpose_str = ", ".join(fund_purpose) if fund_purpose else "미입력"

                    survey_data = {
                        'name': name.strip(),
                        'phone': formatted_phone,
                        'email': email.strip() if email else '미입력',
                        'biz_no': formatted_biz,
                        'company_name': company_name.strip(),
                        'startup_date': startup_date.strftime('%Y-%m-%d'),
                        'store_type': store_type,
                        'deposit': deposit,
                        'monthly_rent': monthly_rent,
                        'revenue_current': rev_current,
                        'revenue_y1': rev_y1,
                        'revenue_y2': rev_y2,
                        'capital': capital,
                        'debt': debt,
                        'guarantee_history': guarantee_str,
                        'certifications': cert_str,
                        'research_lab': research_lab,
                        'fund_purpose': purpose_str,
                        'risk_tax': risk_tax,
                        'risk_overdue': risk_overdue,
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree,
                        'release_version': RELEASE_VERSION,
                        'parent_receipt_no': parent_rid,
                        'magic_token': magic_token,
                        'uuid': uuid_hint or str(uuid4()),
                    }

                    # 재검증
                    v2 = validate_access_token(magic_token, uuid_hint=uuid_hint)
                    if not v2.get("ok"):
                        st.error(f"접속이 만료되었습니다: {v2.get('message', '만료')}")
                        st.session_state.submitted_2 = False
                        st.session_state.saving2 = False
                        st.stop()

                    result = save_to_google_sheet(survey_data, timeout_sec=45, test_mode=is_test_mode)

                    success_statuses = ('success', 'test', 'pending', 'success_delayed')
                    if result.get('status') in success_statuses:
                        if result.get('status') == 'success_delayed':
                            st.success("✅ 2차 설문이 접수되었습니다!")
                            st.warning("⚠️ 중복 제출하지 마세요.")
                        else:
                            st.success("✅ 2차 설문 제출 완료!")
                        
                        st.info("📞 전문가가 심층 분석 후 연락드립니다.")
                        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 전문가에게 문의하기</a></div>", unsafe_allow_html=True)
                        st.session_state.saving2 = False
                        st.stop()
                    else:
                        st.error(f"❌ 제출 중 오류가 발생했습니다: {result.get('message', '알 수 없는 오류')}")
                        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 담당자에게 문의하기</a></div>", unsafe_allow_html=True)
                        st.session_state.submitted_2 = False
                        st.session_state.saving2 = False

if __name__ == "__main__":
    main()