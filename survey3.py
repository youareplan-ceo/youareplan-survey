import streamlit as st
import requests
from datetime import datetime
import os
import json
from typing import Optional, Dict, Any
from uuid import uuid4
import time

st.set_page_config(page_title="유아플랜 3차 심층 설문", page_icon="📝", layout="centered")

# ==============================
# 환경/상수 설정  
# ==============================
RELEASE_VERSION_3 = "v2025-11-26-centered"
TIMEOUT_SEC = 45
AUTO_SAVE_SECONDS = 10
LIVE_SYNC_MS = 5000
SHOW_DEBUG = os.getenv("SHOW_DEBUG", "0") == "1"

# ===== 브랜드/로고 설정 =====
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

def _get_gas_url() -> str:
    url = os.getenv("THIRD_GAS_URL")
    if not url:
        if SHOW_DEBUG:
            st.warning("⚠️ THIRD_GAS_URL 환경변수가 설정되지 않았습니다.")
        return "https://script.google.com/macros/s/PLACEHOLDER/exec"
    return url

APPS_SCRIPT_URL_3 = _get_gas_url()

def _get_api_token_3() -> str:
    try:
        tok = st.secrets.get("API_TOKEN_3")
        if tok:
            return tok
    except Exception:
        pass
    tok = os.getenv("API_TOKEN_3")
    return tok or "youareplan_stage3"

KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# ==============================
# HTTP 클라이언트
# ==============================
def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict = None, timeout: int = TIMEOUT_SEC) -> tuple:
    try:
        response = requests.post(url, json=payload, headers=headers or {'Content-Type': 'application/json'}, timeout=timeout)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.Timeout:
        return False, {"status": "timeout", "message": "서버 응답 시간 초과"}
    except requests.exceptions.RequestException as e:
        return False, {"status": "error", "message": str(e)}
    except json.JSONDecodeError:
        return False, {"status": "error", "message": "잘못된 응답 형식"}

def _json_post_quiet(url: str, payload: Dict[str, Any], timeout_sec: int = TIMEOUT_SEC) -> Dict[str, Any]:
    request_id = str(uuid4())
    headers = {"X-Request-ID": request_id}
    ok, data = _http_post_json(url, payload, headers=headers, timeout=min(15, timeout_sec))
    if ok:
        return data
    return {"status": "pending", "message": "서버 처리 중"}

# ==============================
# 유틸리티 함수
# ==============================
def _nz(s: Optional[str], alt: str = "") -> str:
    s = "" if s is None else str(s)
    return s.strip() if s.strip() else alt

def _qp_get(qp: Dict[str, Any], key: str, default: str = "") -> str:
    try:
        v = qp.get(key)
        if isinstance(v, list):
            v = v[0] if v else ""
        return _nz(v, default)
    except Exception:
        return default

def _badge(text: str) -> str:
    return f"<span style='display:inline-block;background:#e8f1ff;color:#0b5bd3;border:1px solid #b6c2d5;padding:6px 10px;border-radius:999px;font-weight:600;'>{text}</span>"

def _badge_progress(pct: int) -> str:
    try:
        p = int(pct)
    except Exception:
        p = 0
    if p >= 80:
        bg, fg, bd = "#E6F4EA", "#065F46", "#A7D3B1"
    elif p >= 40:
        bg, fg, bd = "#FEF3C7", "#92400E", "#FCD34D"
    else:
        bg, fg, bd = "#F3F4F6", "#111827", "#E5E7EB"
    return f"<span style='display:inline-block;background:{bg};color:{fg};border:1px solid {bd};padding:6px 10px;border-radius:999px;font-weight:700;'>진행률: {p}%</span>"

def _status_indicator(status: str) -> str:
    if status == "saving":
        return "💾"
    elif status == "saved":
        return "✅"
    elif status == "syncing":
        return "🔄"
    else:
        return "📝"

def _calc_progress_pct() -> int:
    keys = ["collateral_profile", "tax_credit_summary", "loan_summary", "docs_check", "risk_top3"]
    filled = 0
    for k in keys:
        v = st.session_state.get(k, None)
        if isinstance(v, list):
            if len(v) > 0:
                filled += 1
        else:
            s = "" if v is None else str(v).strip()
            if s:
                filled += 1
    return round((filled / len(keys)) * 100)

def _merge_snapshot_data(snap: Dict[str, Any]) -> None:
    if not snap:
        return
    data = snap.get("data") or {}
    st.session_state["collateral_profile"] = _nz(data.get("collateral"))
    st.session_state["tax_credit_summary"] = _nz(data.get("tax_credit"))
    st.session_state["loan_summary"] = _nz(data.get("loan"))
    docs_raw = data.get("docs") or ""
    st.session_state["docs_check"] = [s.strip() for s in str(docs_raw).split(",") if s.strip()]
    st.session_state["priority_exclusion"] = _nz(data.get("priority"))
    st.session_state["risk_top3"] = _nz(data.get("risks"))
    st.session_state["coach_notes"] = _nz(data.get("coach"))
    if "server_version" in snap:
        st.session_state.version3 = snap.get("server_version", st.session_state.get("version3", 0))

# ==============================
# CSS 스타일
# ==============================
def apply_styles():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
      html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }
      :root { --gov-navy:#002855; --gov-blue:#005BAC; --gov-border:#cbd5e1; color-scheme: light !important; }
      html, body { background:#FFFFFF !important; color:#0F172A !important; }
      .stApp, [data-testid="stAppViewContainer"] { background:#FFFFFF !important; color:#0F172A !important; }
      [data-testid="stHeader"] { background:#FFFFFF !important; }
      [data-testid="stSidebar"], [data-testid="collapsedControl"]{ display:none !important; }
      #MainMenu, footer { visibility: hidden !important; }
      header [data-testid="stToolbar"] { display: none !important; }
      .block-container{ max-width:1200px; margin:0 auto !important; padding-left:16px; padding-right:16px; }

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

      .gov-hero{ padding:16px 0 8px 0; border-bottom:1px solid var(--gov-border); margin-bottom:8px; }
      .gov-hero h2{ color:var(--gov-navy); margin:0 0 6px 0; font-weight:700; }

      div[data-baseweb="input"], div[data-baseweb="select"], .stTextArea>div, .stTextInput>div, .stSelectbox>div, .stMultiSelect>div{
        background:#fff !important; border-radius:8px !important; border:1px solid var(--gov-border) !important; box-shadow:0 1px 2px rgba(16,24,40,.04) !important;
      }
      div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within, .stTextArea>div:focus-within, .stTextInput>div:focus-within, .stSelectbox>div:focus-within, .stMultiSelect>div:focus-within{
        box-shadow:0 2px 6px rgba(16,24,40,.12) !important; outline:2px solid var(--gov-blue) !important; border-color:var(--gov-blue) !important;
      }

      .stTextInput input, .stTextArea textarea, div[data-baseweb="input"] input {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
      }

      ::placeholder { color:#9aa0a6 !important; opacity:1 !important; }

      div[data-testid="stFormSubmitButton"] { display: none !important; }

      .stButton > button {
        background: var(--gov-navy) !important;
        color: #ffffff !important;
        border: 1px solid var(--gov-navy) !important;
        font-weight: 600 !important;
        padding: 10px 16px !important;
        border-radius: 6px !important;
      }
      .stButton > button:hover {
        filter: brightness(0.95) !important;
      }

      .final-completion-box {
        background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%) !important;
        border: 2px solid #0EA5E9 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin: 16px 0 !important;
      }
      .final-completion-box h4 {
        color: #0F172A !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        margin: 0 0 12px 0 !important;
      }
      .final-completion-box p {
        color: #1E293B !important;
        font-weight: 500 !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
        margin: 0 !important;
      }

      .cta-wrap{ margin-top:10px; padding:12px; border:1px solid var(--gov-border); border-radius:8px; background:#fafafa; }
      .cta-kakao{ display:block; text-align:center; font-weight:700; text-decoration:none; padding:12px 16px; border-radius:10px; background:#FEE500; color:#3C1E1E; border:1px solid #FEE500; }

      .status-indicator {
        position: fixed;
        top: 20px;
        right: 20px;
        font-size: 24px;
        z-index: 9999;
        animation: pulse 2s infinite;
      }
      @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
      }

      @media (max-width: 640px){
        textarea{ min-height: 180px !important; }
        .status-indicator { top: 10px; right: 10px; font-size: 20px; }
        .final-completion-box { padding: 16px !important; }
        .final-completion-box h4 { font-size: 16px !important; }
        .final-completion-box p { font-size: 15px !important; }
      }
      textarea{ min-height: 140px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==============================
# GAS 액션 함수
# ==============================
def save_third_quiet(receipt_no: str, uuid: str, role: str, status: str, client_version: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = {
        "token": _get_api_token_3(),
        "action": "save",
        "receipt_no": receipt_no,
        "uuid": uuid,
        "role": role,
        "status": status,
        "client_version": client_version,
        "payload": payload,
        "edit_lock_take": True,
        "release_version": RELEASE_VERSION_3
    }
    return _json_post_quiet(APPS_SCRIPT_URL_3, data, timeout_sec=15)

def snapshot_third_quiet(receipt_no: str, uuid: str) -> Dict[str, Any]:
    data = {
        "token": _get_api_token_3(),
        "action": "snapshot",
        "receipt_no": receipt_no,
        "uuid": uuid,
    }
    return _json_post_quiet(APPS_SCRIPT_URL_3, data, timeout_sec=10)

def auto_save_data(receipt_no: str, uuid: str, role: str) -> None:
    if st.session_state.get("auto_saving", False):
        return
    
    has_data = any([
        st.session_state.get("collateral_profile", "").strip(),
        st.session_state.get("tax_credit_summary", "").strip(),
        st.session_state.get("loan_summary", "").strip(),
        st.session_state.get("docs_check", []),
        st.session_state.get("priority_exclusion", "").strip(),
        st.session_state.get("risk_top3", "").strip(),
        st.session_state.get("coach_notes", "").strip(),
    ])
    
    if not has_data:
        return
    
    st.session_state.auto_saving = True
    st.session_state.save_status = "saving"
    
    payload = {
        "collateral_profile": _nz(st.session_state.get("collateral_profile")),
        "tax_credit_summary": _nz(st.session_state.get("tax_credit_summary")),
        "loan_summary": _nz(st.session_state.get("loan_summary")),
        "docs_check": st.session_state.get("docs_check", []),
        "priority_exclusion": _nz(st.session_state.get("priority_exclusion")),
        "risk_top3": _nz(st.session_state.get("risk_top3")),
        "coach_notes": _nz(st.session_state.get("coach_notes")),
        "release_version_3": RELEASE_VERSION_3,
    }
    
    result = save_third_quiet(
        receipt_no=receipt_no,
        uuid=uuid,
        role=role,
        status="draft",
        client_version=st.session_state.get("version3", 0),
        payload=payload
    )
    
    if result.get("status") in ("success", "pending"):
        st.session_state.save_status = "saved"
        st.session_state.version3 = result.get("server_version", st.session_state.version3)
    else:
        st.session_state.save_status = "error"
    
    st.session_state.auto_saving = False

def sync_with_server(receipt_no: str, uuid: str) -> None:
    if st.session_state.get("syncing", False):
        return
    
    st.session_state.syncing = True
    st.session_state.save_status = "syncing"
    
    snap = snapshot_third_quiet(receipt_no, uuid)
    if snap.get("status") == "success":
        remote_ver = int(snap.get("server_version") or 0)
        local_ver = int(st.session_state.get("version3") or 0)
        if remote_ver > local_ver:
            _merge_snapshot_data(snap)
    
    st.session_state.save_status = "saved"
    st.session_state.syncing = False

# ==============================
# 메인 함수
# ==============================
def main():
    apply_styles()

    # ========== 통합 헤더 (중앙 정렬) ==========
    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <div class="gov-label">대한민국 정부 협력 서비스</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="gov-hero">
      <h2>3차 심층 설문 (실시간 협업)</h2>
      <p>입력과 동시에 자동 저장되며, 컨설턴트와 실시간으로 협업할 수 있습니다.</p>
    </div>
    """, unsafe_allow_html=True)

    try:
        qp = st.query_params
        receipt_no = _qp_get(qp, "r", "")
        uuid = _qp_get(qp, "u", "")
        role = _qp_get(qp, "role", "client")
    except Exception:
        receipt_no, uuid, role = "", "", "client"

    can_connect = bool(receipt_no and uuid)

    if not can_connect:
        st.error("접근 정보가 부족합니다. 담당자가 보낸 3차 링크로 접속해 주세요.")
        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 링크 재발급 요청</a></div>", unsafe_allow_html=True)
        st.stop()

    if "version3" not in st.session_state:
        st.session_state.version3 = 0
    if "save_status" not in st.session_state:
        st.session_state.save_status = "ready"
    if "auto_saving" not in st.session_state:
        st.session_state.auto_saving = False
    if "syncing" not in st.session_state:
        st.session_state.syncing = False
    if "last_auto_save" not in st.session_state:
        st.session_state.last_auto_save = 0

    meta_cols = st.columns([2, 1.5, 1.2, 1.3])
    with meta_cols[0]:
        st.markdown(_badge(f"접수번호: {receipt_no}"), unsafe_allow_html=True)
    with meta_cols[1]:
        st.markdown(_badge(f"역할: {('코치' if role=='coach' else '고객')}"), unsafe_allow_html=True)
    with meta_cols[2]:
        progress_pct = _calc_progress_pct()
        st.markdown(_badge_progress(progress_pct), unsafe_allow_html=True)
    with meta_cols[3]:
        status_icon = _status_indicator(st.session_state.save_status)
        st.markdown(_badge(f"{status_icon} 자동 저장"), unsafe_allow_html=True)

    st.markdown("---")

    current_time = time.time()
    if current_time - st.session_state.last_auto_save > AUTO_SAVE_SECONDS:
        auto_save_data(receipt_no, uuid, role)
        st.session_state.last_auto_save = current_time

    if current_time % 10 < 1:
        sync_with_server(receipt_no, uuid)

    render_simple_form(receipt_no, uuid, role)

    st.markdown(f"""
    <script>
    setTimeout(function(){{
        var activeElement = document.activeElement;
        var isTyping = activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA');
        if (!isTyping) {{
            location.reload();
        }}
    }}, {LIVE_SYNC_MS});
    </script>
    """, unsafe_allow_html=True)

def render_simple_form(receipt_no: str, uuid: str, role: str):
    status_icon = _status_indicator(st.session_state.save_status)
    st.markdown(f'<div class="status-indicator">{status_icon}</div>', unsafe_allow_html=True)
    
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 🧱 담보·보증 요약")
        st.text_area(
            "담보/보증 계획 (자산·평가·보증기관 등)",
            placeholder="예: 부동산 담보 2.5억 평가 예정, 신용보증기금 보증 80%",
            key="collateral_profile",
            help="입력하면 자동 저장됩니다"
        )

        st.markdown("### 🏦 대출/자금 현황")
        st.text_area(
            "기존 대출/금리/만기/상환계획",
            placeholder="예: 기업은행 운전자금 1.2억 @ 5.2%, 만기 2026-06",
            key="loan_summary",
            help="입력하면 자동 저장됩니다"
        )

        st.markdown("### 🏷 우대/제외 요건")
        st.text_input(
            "우대·제외 요건 (콤마로 구분)",
            placeholder="예: 청년창업, 여성기업 / 제외 없음",
            key="priority_exclusion",
            help="입력하면 자동 저장됩니다"
        )

    with col_right:
        st.markdown("### 🧾 세무·신용 요약")
        st.text_area(
            "세무·신용 상태 (부가세·4대보험·체납/연체 등)",
            placeholder="예: 부가세 과세매출 3.2억, 체납 없음, 4대보험 정상",
            key="tax_credit_summary",
            help="입력하면 자동 저장됩니다"
        )

        st.markdown("### 📑 준비 서류 체크")
        docs_options = [
            "사업자등록증",
            "재무제표(최근 2~3년)",
            "부가세신고서",
            "납세증명",
            "4대보험 완납증명",
            "매출증빙(세금계산서/카드내역)",
            "통장사본",
            "기타",
        ]
        st.multiselect(
            "보유 서류를 선택하세요", 
            options=docs_options, 
            key="docs_check",
            help="선택하면 자동 저장됩니다",
            placeholder="해당사항 모두 선택하세요"
        )

        st.markdown("### ⚠️ 리스크 Top3")
        st.text_area(
            "핵심 리스크 3가지(줄바꿈으로 구분)",
            placeholder="예: 부채비율 270%\n담보 부족\n운전자금 부족",
            key="risk_top3",
            help="입력하면 자동 저장됩니다"
        )

    st.markdown("### 🗒 코치 메모")
    st.text_area(
        "컨설턴트 코멘트/후속 액션",
        placeholder="예: 부가세 신고서 원본 요청, 담보 감정 일정 예약",
        key="coach_notes",
        help="입력하면 자동 저장됩니다"
    )
    
    if role != "coach":
        st.caption("※ 고객도 코치 메모를 확인하고 의견을 추가할 수 있습니다.")

    st.markdown("---")
    st.markdown("### 📨 최종 완료")
    
    col_final1, col_final2 = st.columns([2, 1])
    with col_final1:
        st.markdown("""
        <div class="final-completion-box">
            <h4>💡 자동 저장 완료</h4>
            <p><strong>모든 내용이 실시간으로 자동 저장됩니다.</strong><br>
            컨설턴트와 충분히 협의한 후 최종 완료 버튼을 눌러주세요.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_final2:
        if st.button("📨 최종 완료", type="primary"):
            result = save_third_quiet(
                receipt_no=receipt_no,
                uuid=uuid,
                role=role,
                status="final",
                client_version=st.session_state.get("version3", 0),
                payload={
                    "collateral_profile": _nz(st.session_state.get("collateral_profile")),
                    "tax_credit_summary": _nz(st.session_state.get("tax_credit_summary")),
                    "loan_summary": _nz(st.session_state.get("loan_summary")),
                    "docs_check": st.session_state.get("docs_check", []),
                    "priority_exclusion": _nz(st.session_state.get("priority_exclusion")),
                    "risk_top3": _nz(st.session_state.get("risk_top3")),
                    "coach_notes": _nz(st.session_state.get("coach_notes")),
                    "release_version_3": RELEASE_VERSION_3,
                }
            )
            
            if result.get("status") in ("success", "pending"):
                st.success("✅ 최종 완료되었습니다! 전문가가 검토 후 연락드립니다.")
                st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 카카오 채널로 문의하기</a></div>", unsafe_allow_html=True)
            else:
                st.error("최종 완료 중 오류가 발생했습니다. 다시 시도해주세요.")

if __name__ == "__main__":
    main()