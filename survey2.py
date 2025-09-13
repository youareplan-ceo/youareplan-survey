import streamlit as st

import requests
# --- Make repo root importable so `src` (at repo root) resolves when Root Directory is `youareplan-survey` ---
import os, sys
_CUR = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_CUR, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ---- HTTP 멱등/재시도 래퍼 (2차 제출 안정화) ----
def _idem_key(prefix="c2"):
    return f"{prefix}-{int(time.time()*1000)}-{uuid4().hex[:8]}"
def _json_post_with_resilience(url, payload, timeout=12, retries=2, backoff=0.6, headers=None):
    import json
    h = {"Content-Type":"application/json"}
    if headers: h.update(headers)
    # 멱등키 부여 (서버가 지원하지 않아도 무해)
    h.setdefault("X-Idempotency-Key", _idem_key())
    last_exc = None
    for i in range(retries+1):
        try:
            r = requests.post(url, data=json.dumps(payload), headers=h, timeout=timeout)
            # 200 아닌 경우에도 본문을 최대한 파싱
            try:
                j = r.json()
            except Exception:
                j = {"ok": False, "status": "error", "http": r.status_code, "text": r.text[:300]}
            if r.status_code == 200:
                return j
            # 4xx는 재시도 무의미, 단 429/408은 1회 재시도
            if r.status_code in (408,429) and i < retries:
                time.sleep(backoff*(i+1))
                continue
            return j
        except Exception as e:
            last_exc = e
            if i < retries:
                time.sleep(backoff*(i+1))
            else:
                return {"ok": False, "status": "error", "exception": str(last_exc)}

import time
from datetime import datetime
import re
import os
from typing import Optional
from uuid import uuid4
# --- Load helpers from repo-root/src without colliding with working-dir named "src" on Render ---
import importlib.util

def _load_module_from(path: str, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, f"Failed to load spec for {mod_name} from {path}"
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod

_CFG_PATH = os.path.join(_ROOT, 'src', 'config.py')
_HTTP_PATH = os.path.join(_ROOT, 'src', 'http_client.py')
config = _load_module_from(_CFG_PATH, 'youaplan_src_config')
_http_mod = _load_module_from(_HTTP_PATH, 'youaplan_src_http_client')
_hc_post_json = _http_mod.post_json

# Compatibility shim to preserve existing call sites expecting
# (ok, status_code, data, err)
def json_post(url, payload, headers=None, timeout=10, retries=1):
    ok, data = _hc_post_json(url, payload, headers=headers, timeout=(5.0, float(timeout)))
    status_code = 200 if ok else None
    err = None if ok else (data.get('error') if isinstance(data, dict) else str(data))
    return ok, status_code, (data if isinstance(data, dict) else {}), err


st.set_page_config(page_title="유아플랜 정책자금 2차 심화진단", page_icon="📝", layout="centered")

# ---- 브랜드 로고 설정 ----
BRAND_NAME = "유아플랜"
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"

def _get_logo_url() -> str:
    """로고 URL을 secrets/env에서 우선 읽고, 없으면 기본값 사용"""
    try:
        # st.secrets 우선
        url = st.secrets.get("YOUAREPLAN_LOGO_URL", None)
        if url:
            return str(url)
    except Exception:
        pass
    # 환경변수 → 기본값
    return os.getenv("YOUAREPLAN_LOGO_URL") or DEFAULT_LOGO_URL

# ---- 유틸 함수 ----
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone_from_digits(d: str) -> str:
    """11자리 전화번호 포맷"""
    if len(d) == 11 and d.startswith("010"):
        return f"{d[0:3]}-{d[3:7]}-{d[7:11]}"
    return d

def format_biz_no(d: str) -> str:
    """10자리 사업자번호 포맷"""
    if len(d) == 10:
        return f"{d[0:3]}-{d[3:5]}-{d[5:10]}"
    return d

# ---- on_change handlers for live formatting (2차) ----
def _phone2_on_change():
    raw = st.session_state.get("phone2_input", "")
    d = _digits_only(raw)
    st.session_state.phone2_input = format_phone_from_digits(d)

def _biz_on_change():
    raw = st.session_state.get("biz_no_input", "")
    d = _digits_only(raw)
    st.session_state.biz_no_input = format_biz_no(d)

RELEASE_VERSION = "v2025-09-05-1845"

# Centralized config
APPS_SCRIPT_URL = config.SECOND_GAS_URL

# Token validation API (1차 GAS)
TOKEN_API_URL = config.FIRST_GAS_TOKEN_API_URL
INTERNAL_SHARED_KEY = "youareplan"  # must match 1차 GAS

# API token (stage2)
API_TOKEN = getattr(config, "API_TOKEN_STAGE2", os.getenv("API_TOKEN_2", "youareplan_stage2"))

# KakaoTalk Channel
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"{KAKAO_CHANNEL_URL}/chat"

# 통합 CSS (단일 블록으로 정리)
st.markdown("""
<style>
  /* 기본 폰트 및 색상 */
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] {
    font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif;
  }
  
  /* 색상 변수 */
  :root {
    --gov-navy: #002855;
    --gov-blue: #005BAC;
    --gov-border: #cbd5e1; /* stronger, crisper border */
    --primary-color: #002855 !important;
  }

  /* 상단 브랜드 바 & 메뉴 숨김 */
  #MainMenu, footer { visibility: hidden !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  .brandbar{
    width:100%;
    display:flex;
    align-items:center;
    gap:10px;
    padding:8px 14px;
    border-bottom:1px solid var(--gov-border);
    background:#ffffff;
  }
  .brandbar img{
    height:48px;               /* desktop default (3차와 통일) */
    max-height:48px;
    display:block;
    object-fit:contain;
  }
  @media (max-width: 740px){
    .brandbar img{ height:64px; max-height:64px; }
  }
  .brandbar .brandtxt{ display:none; }

  /* global readability */
  .stApp, .stApp * {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
    color: #111111 !important;
  }
  
  /* 사이드바 숨김 */
  [data-testid="stSidebar"] { display: none !important; }
  [data-testid="collapsedControl"] { display: none !important; }
  .block-container{ max-width:1200px; margin:0 auto !important; padding-left:16px; padding-right:16px; }
  
  /* 번역 차단 */
  .notranslate, [translate="no"] { translate: no !important; }
  .stApp * { translate: no !important; }
  
  /* 헤더 */
  .gov-topbar {
    width: 100%;
    background: var(--gov-navy);
    color: #ffffff !important;
    font-size: 13px;
    padding: 8px 14px;
    letter-spacing: 0.2px;
    border-bottom: 3px solid var(--gov-blue);
  }
  .gov-topbar * {
    color: #ffffff !important;
    fill: #ffffff !important;
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
  
  /* 입력창 컨테이너: 선명한 테두리 + 은은한 그림자 (내부 래퍼까지 통일) */
  div[data-baseweb="input"],
  div[data-baseweb="input"] > div,
  div[data-baseweb="select"],
  div[data-baseweb="select"] > div,
  .stTextArea > div,
  .stTextArea > div > div,
  .stTextInput > div,
  .stTextInput > div > div,
  .stSelectbox > div,
  .stSelectbox > div > div,
  .stMultiSelect > div,
  .stMultiSelect > div > div,
  .stDateInput > div,
  .stDateInput > div > div {
    background:#ffffff !important;
    border-radius:8px !important;
    border:1px solid var(--gov-border) !important;
    box-shadow: 0 1px 2px rgba(16,24,40,.04) !important;
  }
  /* 내부 실제 input/textarea는 자체 테두리 제거 (밑줄/이중 테두리 방지) */
  .stTextInput input,
  .stTextArea textarea,
  div[data-baseweb="input"] input,
  div[data-baseweb="select"] input,
  div[data-baseweb="select"] [contenteditable="true"],
  .stDateInput input {
    background:transparent !important;
    border:0 !important;
    border-color: transparent !important;
    box-shadow:none !important;
  }
  /* hover 강화 (내부 래퍼 포함) */
  div[data-baseweb="input"]:hover,
  div[data-baseweb="input"] > div:hover,
  div[data-baseweb="select"]:hover,
  div[data-baseweb="select"] > div:hover,
  .stTextArea > div:hover,
  .stTextArea > div > div:hover,
  .stTextInput > div:hover,
  .stTextInput > div > div:hover,
  .stSelectbox > div:hover,
  .stSelectbox > div > div:hover,
  .stMultiSelect > div:hover,
  .stMultiSelect > div > div:hover,
  .stDateInput > div:hover,
  .stDateInput > div > div:hover {
    box-shadow: 0 1px 3px rgba(16,24,40,.08) !important;
    border-color: #b6c2d5 !important;
  }
  /* focus 하이라이트: 정부 블루 (내부 래퍼 포함) */
  div[data-baseweb="input"]:focus-within,
  div[data-baseweb="input"] > div:focus-within,
  div[data-baseweb="select"]:focus-within,
  div[data-baseweb="select"] > div:focus-within,
  .stTextArea > div:focus-within,
  .stTextArea > div > div:focus-within,
  .stTextInput > div:focus-within,
  .stTextInput > div > div:focus-within,
  .stSelectbox > div:focus-within,
  .stSelectbox > div > div:focus-within,
  .stMultiSelect > div:focus-within,
  .stMultiSelect > div > div:focus-within,
  .stDateInput > div:focus-within,
  .stDateInput > div > div:focus-within {
    box-shadow: 0 2px 6px rgba(16,24,40,.12) !important;
    outline: 2px solid var(--gov-blue) !important;
    outline-offset: 0 !important;
    border-color: var(--gov-blue) !important;
  }
  /* 이중 테두리 예방: 내부 래퍼의 잔여 테두리 제거 */
  .stTextInput > div > div,
  .stTextArea > div > div,
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stDateInput > div > div {
    border-top-color: var(--gov-border) !important;
    border-right-color: var(--gov-border) !important;
    border-bottom-color: var(--gov-border) !important;
    border-left-color: var(--gov-border) !important;
  }
  /* placeholder는 연하게, 입력값은 진하게 (Safari 포함) */
  ::placeholder { color:#9aa0a6 !important; opacity:1 !important; }
  input::placeholder, textarea::placeholder { color:#9aa0a6 !important; }
  .stTextInput input:placeholder-shown,
  .stTextArea textarea:placeholder-shown,
  div[data-baseweb="input"] input:placeholder-shown,
  div[data-baseweb="select"] input:placeholder-shown,
  div[data-baseweb="select"] [contenteditable="true"]:placeholder-shown,
  .stDateInput input:placeholder-shown {
    color:#9aa0a6 !important;
    -webkit-text-fill-color:#9aa0a6 !important;
  }
  .stTextInput input:not(:placeholder-shown),
  .stTextArea textarea:not(:placeholder-shown),
  div[data-baseweb="input"] input:not(:placeholder-shown),
  div[data-baseweb="select"] input:not(:placeholder-shown),
  div[data-baseweb="select"] [contenteditable="true"]:not(:placeholder-shown),
  .stDateInput input:not(:placeholder-shown) {
    color:#111111 !important;
    -webkit-text-fill-color:#111111 !important;
  }

  .stTextInput input,
  .stTextArea textarea,
  div[data-baseweb="input"] input,
  div[data-baseweb="select"] input,
  div[data-baseweb="select"] [contenteditable="true"],
  .stDateInput input {
    color:#111111 !important;
    -webkit-text-fill-color:#111111 !important;
  }
  /* 자동완성(노란 배경) 무력화 */
  input:-webkit-autofill,
  textarea:-webkit-autofill,
  select:-webkit-autofill {
    -webkit-text-fill-color:#111111 !important;
    box-shadow: 0 0 0px 1000px #ffffff inset !important;
    transition: background-color 5000s ease-in-out 0s !important;
  }
  
  /* 체크박스 */
  .stCheckbox {
    padding: 12px 14px !important;
    border: 1px solid var(--gov-border) !important;
    border-radius: 8px !important;
    background: #ffffff !important;
  }

  /* ==== Consent section alignment helpers ==== */
  .consent-note{
    margin-top: 6px;
    font-size: 12px;
    color: #6b7280 !important;
    line-height: 1.5;
    min-height: 38px; /* keep left/right captions equal height */
    display:block;
  }
  /* keep checkbox container consistent height/padding so both columns align */
  .stCheckbox{ min-height: 48px !important; display:flex; align-items:center; }
  /* make the submit button visually left-aligned and solid navy */
  form div[data-testid="stFormSubmitButton"] button{ min-width: 220px; }
  
  /* 라이트 모드 강제 */
  :root { color-scheme: light; }
  html, body, .stApp {
    background: #ffffff !important;
    color: #111111 !important;
    filter: none !important;
  }
  
  /* Submit / primary buttons in forms */
  div[data-testid="stFormSubmitButton"] button,
  div[data-testid="stFormSubmitButton"] button *,
  .stButton > button,
  .stButton > button *{
    background: var(--gov-navy) !important;
    color: #ffffff !important;
    border: 1px solid var(--gov-navy) !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    border-radius: 6px !important;
    fill: #ffffff !important;
  }
  div[data-testid="stFormSubmitButton"] button:hover,
  .stButton > button:hover{
    filter: brightness(0.95);
  }
  /* CTA 버튼 */
  .cta-wrap {
    margin-top: 10px;
    padding: 12px;
    border: 1px solid var(--gov-border);
    border-radius: 8px;
    background: #fafafa;
  }
  
  .cta-btn {
    display: block;
    text-align: center;
    font-weight: 700;
    text-decoration: none;
    padding: 12px 16px;
    border-radius: 10px;
    background: #FEE500;
    color: #3C1E1E;
  }
  /* Kakao brand button (yellow) */
  .cta-kakao{background:#FEE500;color:#3C1E1E;border:1px solid #FEE500}
  .cta-kakao:hover{filter:brightness(0.97)}

  /* Selected option chips (BaseWeb tags) – improve contrast */
  .stMultiSelect [data-baseweb="tag"],
  .stSelectbox [data-baseweb="tag"],
  div[data-baseweb="select"] [data-baseweb="tag"] {
    background: #0B5BD3 !important; /* gov blue */
    color: #ffffff !important;
    border: 0 !important;
  }
  /* Ensure text & close icon inside chips are white */
  .stMultiSelect [data-baseweb="tag"] *,
  .stSelectbox [data-baseweb="tag"] *,
  div[data-baseweb="select"] [data-baseweb="tag"] * {
    color: #ffffff !important;
    fill: #ffffff !important;
  }

  /* === Dropdown (BaseWeb popover) readability & layering === */
  /* Ensure the options popover sits above everything and is readable on light theme */
  div[data-baseweb="popover"]{ 
    z-index: 10000 !important; 
  }
  div[data-baseweb="popover"] div[role="listbox"]{
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;  /* same as --gov-border */
    box-shadow: 0 8px 24px rgba(16,24,40,.12) !important;
    max-height: 42vh !important;
    overflow-y: auto !important;
  }
  /* Option rows: default text color, clear hover/selected states */
  div[role="option"]{
    color: #111111 !important;
    background: #ffffff !important;
  }
  div[role="option"][aria-selected="true"]{
    background: #e8f1ff !important;  /* selected bg */
    color: #0b5bd3 !important;        /* selected text */
  }
  div[role="option"]:hover{
    background: #f3f6fb !important;   /* hover bg */
    color: #111111 !important;
  }

  /* iOS viewport-safe area & mobile keyboard overlap reduction */
  @media (max-width: 768px){
    .stApp{ padding-bottom: calc(env(safe-area-inset-bottom,0px) + 200px) !important; }
  }
  /* Mobile touch & textarea comfort (unified with 3차) */
  textarea{ min-height: 140px !important; }
  @media (max-width:640px){
    textarea{ min-height: 180px !important; }
    .stButton>button, div[data-testid="stFormSubmitButton"] button{ padding:14px 18px !important; }
  }
</style>
""", unsafe_allow_html=True)

def validate_access_token(token: str, timeout_sec: int = 10) -> dict:
    """1차 GAS 토큰 검증. {ok, message, parent_receipt_no, remaining_minutes} 형식 기대."""
    try:
        payload = {"action": "validate", "token": token, "api_token": INTERNAL_SHARED_KEY}
        if not (payload.get("uuid") or payload.get("UUID")):
            payload["uuid"] = str(uuid4())
        ok, status_code, resp_data, err = json_post(
            TOKEN_API_URL,
            payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout_sec,
            retries=1,
        )
        if ok:
            return resp_data or {"ok": False, "message": "empty response"}
        return {"ok": False, "message": err or f"HTTP {status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

def save_to_google_sheet(data, timeout_sec: int = 45, retries: int = 0, test_mode: bool = False):
    """Google Apps Script로 데이터 전송 (네트워크 탄력성 강화)"""
    if test_mode:
        return {"status": "test", "message": "테스트 모드 - 저장 생략"}

    data['token'] = API_TOKEN

    # First single attempt to detect retry-worthy failures and show user message
    request_id = str(uuid4())
    ok, status_code, resp_data, err = json_post(
        APPS_SCRIPT_URL,
        data,
        headers={"X-Request-ID": request_id, "Content-Type": "application/json"},
        timeout=timeout_sec,
        retries=0,
    )
    # Normalize Apps Script success shape: accept {ok:true} or {status:"success"}
    if (not ok) and isinstance(resp_data, dict) and resp_data.get("ok") is True:
        ok, status_code, err = True, (status_code or 200), None

    ambiguous_seen = False
    if (status_code and 200 <= status_code <= 299) and resp_data:
        if status_code == 202 or str(resp_data.get('status','')).lower() == 'pending':
            ambiguous_seen = True

    if ok:
        return resp_data or {"status": "success"}

    # If first attempt failed due to timeout/5xx etc., inform and retry up to 3
    if (status_code is None) or status_code == 429 or (500 <= (status_code or 0) <= 599):
        st.info("서버 응답이 지연되어 재시도 중입니다 (최대 3회)…")
        ok2, status_code2, resp_data2, err2 = json_post(
            APPS_SCRIPT_URL,
            data,
            headers={"X-Request-ID": request_id, "Content-Type": "application/json"},
            timeout=timeout_sec,
            retries=max(3, retries),
        )
        if (not ok2) and isinstance(resp_data2, dict) and resp_data2.get("ok") is True:
            ok2, status_code2, err2 = True, (status_code2 or 200), None
        if ok2:
            return resp_data2 or {"status": "success"}
        # If any ambiguous/pending observed either before or during final response
        if resp_data2 and ((status_code2 and 200 <= status_code2 <= 299) and (status_code2 == 202 or str(resp_data2.get('status','')).lower() == 'pending')):
            ambiguous_seen = True
        if ambiguous_seen:
            st.warning("접수 요청은 전달되었을 수 있습니다. 잠시 후 '통합 뷰'에서 반영 여부를 확인해 주세요.")
            return resp_data2 or {"status": "pending"}
        # give final error
        return {"status": "error", "message": err2 or err or "network error"}

    # Non-retryable failure (e.g., 4xx other than 429)
    if resp_data and resp_data.get('message'):
        st.error(f"서버 응답: {resp_data.get('message')}")
    return {"status": "error", "message": err or f"HTTP {status_code}"}

def main():
    # saving state & aria-live for accessibility (2차)
    if "saving2" not in st.session_state:
        st.session_state.saving2 = False
    st.markdown('<div id="live-status-2" aria-live="polite" style="position:absolute;left:-9999px;height:1px;width:1px;overflow:hidden;">ready</div>', unsafe_allow_html=True)

    # 상단 브랜드 바(로고) + 정부 협력 바
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

    # 쿼리 파라미터 처리 & 토큰 검증
    try:
        qp = st.query_params
        is_test_mode = qp.get("test") == "true"
        magic_token = qp.get("t")
    except Exception:
        is_test_mode = False
        magic_token = None

    if is_test_mode:
        st.warning("⚠️ 테스트 모드 - 실제 저장되지 않습니다.")

    # Require token
    if not magic_token:
        st.error("접근 토큰이 없습니다. 담당자가 발송한 링크로 접속해 주세요.")
        st.markdown(f"<div class='cta-wrap'><a class='cta-btn cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 재발급 요청하기</a></div>", unsafe_allow_html=True)
        return

    v = validate_access_token(magic_token)
    if not v.get("ok"):
        # Blocked screen
        msg = v.get("message") or v.get("error") or "토큰 검증 실패"
        st.error(f"접속이 차단되었습니다: {msg}")
        st.markdown(f"<div class='cta-wrap'><a class='cta-btn cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 새 링크 재발급 요청</a></div>", unsafe_allow_html=True)
        return

    # Valid token
    parent_rid_fixed = v.get("parent_receipt_no", "")
    # Support either remaining_minutes or remaining_seconds from GAS
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
    # 연락처/사업자등록번호 입력값은 폼 내에서 처리 (실시간 콜백 제거)
    
    with st.form("second_survey"):
        if 'submitted_2' not in st.session_state:
            st.session_state.submitted_2 = False
            
        st.markdown("### 📝 2차 설문 - 상세 정보")
        
        # A. 기본 정보
        st.markdown("#### 👤 기본 정보")
        name = st.text_input("성함 (필수)", placeholder="홍길동").strip()
        # 1차 접수번호는 토큰에서 고정됨
        parent_rid = parent_rid_fixed
        st.text_input("1차 접수번호", value=parent_rid, disabled=True)
        st.caption("초대 링크에 포함된 접수번호로 자동 설정됩니다.")
        phone_raw = st.text_input(
            "연락처 (필수)",
            placeholder="예: 01012345678"
        )
        st.caption("숫자만 입력해도 됩니다. 예: 01012345678")
        biz_no_raw = st.text_input(
            "사업자등록번호 (선택)",
            placeholder="예: 0000000000"
        )
        st.caption("10자리 숫자입니다. 예: 1234567890")
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")
        st.markdown("---")
        
        # B. 사업 정보
        st.markdown("#### 📊 사업 정보")
        company = st.text_input("사업자명 (필수)")
        
        col1, col2 = st.columns(2)
        with col1:
            startup_date = st.date_input("사업 시작일 (필수)", 
                                        min_value=datetime(1900, 1, 1), 
                                        format="YYYY-MM-DD")
        with col2:
            st.write(" ")  # 정렬용
        
        # C. 재무 정보
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

        # D. 기술/인증
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

        # E. 자금 계획
        st.markdown("#### 💵 자금 활용 계획")
        funding_purpose = st.multiselect("자금 용도 (선택)", 
                                        ["시설자금", "운전자금", "R&D자금", "기타"],
                                        placeholder="선택하세요")
        
        detailed_plan = st.text_area("상세 활용 계획 (선택)", 
                                     placeholder="예: 생산설비 2억, 원자재 구매 1억")
        
        incentive_status = st.multiselect(
            "우대 조건(선택)",
            ["여성기업", "청년창업", "장애인기업", "소공인", "사회적기업", "해당 없음"],
            placeholder="선택하세요"
        )
        st.markdown("---")
        
        # F. 리스크 체크
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

        # G. 동의
        st.markdown("#### 🤝 동의")
        col_agree1, col_agree2 = st.columns(2)
        with col_agree1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)")
            st.markdown('<span class="consent-note">상담 확인·자격 검토·연락 목적. 보관: 상담·보고서 3년 / 로그 1년 / 법정 증빙 5년(해당 시). 동의 철회 시 중단·삭제(필수정보 철회 시 서비스 제한 가능).</span>', unsafe_allow_html=True)
            with st.expander("개인정보 수집·이용 동의 전문 보기"):
                st.markdown(
                    """
                    **수집·이용 목적**: 상담 신청 확인, 자격 검토, 연락 및 안내

                    **수집 항목**: 성함, 연락처, 이메일(선택), 기업명, 사업자등록번호(선택), 재무·인증·리스크 정보, 1차 접수번호, 접속 로그·접근기록

                    **보유·이용 기간**:
                    - 상담 이력·사전컨설팅 관련 데이터: **3년**
                    - 접속 로그·접근 기록 등 보안기록: **1년**
                    - 세무 증빙 등 법정 보존자료(해당 시): **5년**
                    - 위 기간 경과 또는 **동의 철회 시 지체 없이 파기**(다만 분쟁 해결·법령상 의무 이행을 위해 필요한 최소 범위는 해결 시까지 보관 가능)

                    **제공 및 위탁**: 제3자 제공은 원칙적으로 없으며, 서비스 운영(클라우드·알림·전자서명 등) 목적의 **처리위탁**이 필요한 경우 사전 고지 후 최소한으로 위탁

                    **권리 및 철회**: 열람·정정·삭제·처리정지·동의 철회 가능. **필수 정보 삭제·철회 시 서비스 제공이 제한**될 수 있음
                    """
                )
        with col_agree2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")
            st.markdown('<span class="consent-note">신규 정책자금/지원사업 알림. 언제든지 수신 거부 가능.</span>', unsafe_allow_html=True)
            with st.expander("마케팅 정보 수신 동의 전문 보기"):
                st.markdown(
                    """
                    **수신 내용**: 신규 정책자금, 지원사업, 세미나/이벤트 안내

                    **수신 방법**: 카카오톡/문자/이메일 중 일부

                    **보유·이용 기간**: 동의 철회 시까지

                    **철회 방법**: 언제든지 수신 거부(채널 차단/문자 내 수신거부 링크/이메일 회신)로 철회 가능합니다.
                    """
                )

        submitted = st.form_submit_button("📩 2차 설문 제출", type="primary", disabled=st.session_state.get("saving2", False))

        if submitted and not st.session_state.submitted_2:
            st.session_state.submitted_2 = True

            # 입력값 포맷팅 (제출 시 정리)
            d_phone = _digits_only(phone_raw)
            formatted_phone = format_phone_from_digits(d_phone) if d_phone else ""

            d_biz = _digits_only(biz_no_raw)
            formatted_biz = format_biz_no(d_biz) if d_biz else ""

            # 유효성 검사(엄격)
            name_ok = bool(name and len(name.strip()) >= 2)
            phone_digits = _digits_only(formatted_phone)
            biz_digits = _digits_only(formatted_biz)
            phone_ok = (len(phone_digits) == 11 and phone_digits.startswith("010"))
            # 사업자번호는 선택 입력 (예비창업자 가능)
            biz_ok = (len(biz_digits) == 0) or (len(biz_digits) == 10)

            if not name_ok:
                st.error("성함은 2자 이상 입력해주세요.")
                st.session_state.submitted_2 = False
            elif not phone_ok:
                st.error("연락처는 010으로 시작하는 11자리여야 합니다. 예: 010-1234-5678")
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
                with st.spinner("⏳ 제출 처리 중입니다. 시간이 다소 걸릴 수 있으니 잠시만 기다려 주세요..."):
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
                if not (survey_data.get('uuid') or survey_data.get('UUID')):
                    survey_data['uuid'] = str(uuid4())



            # 재전송/더블탭 대비: 제출 직전 토큰 재검증
            v2 = validate_access_token(magic_token)
            if not v2.get("ok"):
                st.error(f"접속이 만료되었습니다: {v2.get('message', v2.get('error','만료/소진'))}")
                st.session_state.submitted_2 = False
                st.session_state.saving2 = False
                st.stop()
            result = save_to_google_sheet(survey_data, timeout_sec=45, retries=0, test_mode=is_test_mode)

            if result.get('status') in ('success', 'test', 'pending'):
                st.success("✅ 2차 설문 제출 완료!" if result.get('status') != 'pending' else "✅ 제출 접수 완료! (서버 응답 지연 중)")
                st.info("전문가가 심층 분석 후 연락드립니다.")

                st.markdown(f"""
                <div class="cta-wrap">
                    <a class="cta-btn cta-kakao" href="{KAKAO_CHAT_URL}" target="_blank">
                        💬 전문가에게 문의하기
                    </a>
                </div>
                """, unsafe_allow_html=True)

                # 1.5초 후 자동 복귀
                st.markdown("""
                <script>
                (function(){
                  function goBack(){
                    if (document.referrer && document.referrer !== location.href) { location.replace(document.referrer); return; }
                    if (history.length > 1) { history.back(); return; }
                    location.replace('/');
                  }
                  setTimeout(goBack, 1500);
                })();
                </script>
                """, unsafe_allow_html=True)
                st.session_state.saving2 = False
                st.stop()

            else:
                st.error("❌ 제출 실패. 잠시 후 다시 시도해주세요.")
                st.markdown(f"""
                <div class="cta-wrap">
                    <a class="cta-btn cta-kakao" href="{KAKAO_CHAT_URL}" target="_blank">
                        💬 담당자에게 문의하기
                    </a>
                </div>
                """, unsafe_allow_html=True)
                st.session_state.submitted_2 = False
                st.session_state.saving2 = False

if __name__ == "__main__":
    main()
