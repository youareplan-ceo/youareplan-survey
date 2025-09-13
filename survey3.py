import streamlit as st
import requests
from datetime import datetime
import os
from typing import Optional, Dict, Any, List
from uuid import uuid4
from src import config
from src.http_client import post_json as _hc_post_json

# Compatibility shim to preserve existing call sites expecting
# (ok, status_code, data, err)
def json_post(url, payload, headers=None, timeout=10, retries=1):
    ok, data = _hc_post_json(url, payload, headers=headers, timeout=(5.0, float(timeout)))
    status_code = 200 if ok else None
    err = None if ok else (data.get('error') if isinstance(data, dict) else str(data))
    return ok, status_code, (data if isinstance(data, dict) else {}), err

# ==============================
# 기본 페이지/레이아웃
# ==============================
st.set_page_config(page_title="유아플랜 3차 심층 설문", page_icon="📝", layout="centered")

# ------------------------------
# 환경/상수 (필요시 교체)
# ------------------------------
RELEASE_VERSION_3 = "v2025-09-10-1"
TIMEOUT_SEC = 45  # 서버 지연 대비. 재시도 없음, pending 처리 철학 유지

# ---- env helpers ----
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

LIVE_SYNC_MS = _env_int("LIVE_SYNC_MS", 2000)  # default 2s
SHOW_DEBUG = os.getenv("SHOW_DEBUG", "0") == "1"

# ===== 브랜드/로고 설정 (1차/2차와 동일 규칙) =====
BRAND_NAME = "유아플랜"
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"

def _get_logo_url() -> str:
    # Secrets → Env → 기본값
    try:
        v = st.secrets.get("YOUAREPLAN_LOGO_URL")
        if v:
            return str(v)
    except Exception:
        pass
    return os.getenv("YOUAREPLAN_LOGO_URL") or DEFAULT_LOGO_URL

# 3차 저장용 GAS 엔드포인트는 중앙 설정에서 관리
APPS_SCRIPT_URL_3 = config.THIRD_GAS_URL

# 3차 API 토큰 (Streamlit Secrets → 환경변수 → 하드코딩 순으로 조회)
def _get_api_token_3() -> str:
    try:
        tok = st.secrets.get("API_TOKEN_3")
        if tok:
            return tok
    except Exception:
        pass
    tok = os.getenv("API_TOKEN_3")
    return tok or "youareplan_stage3"

# KakaoTalk Channel (문의 CTA)
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# ==============================
# 공통 유틸
# ==============================
def _json_post_with_resilience(url: str, payload: Dict[str, Any], timeout_sec: int = TIMEOUT_SEC) -> Dict[str, Any]:
    # First quick attempt (no retries) to decide whether to show retry message
    request_id = str(uuid4())
    ok, sc, data, err = json_post(url, payload, headers={"X-Request-ID": request_id}, timeout=min(10, timeout_sec), retries=0)
    if ok:
        return data or {"status": "success"}
    # Network/5xx/429 → inform and retry up to 3
    if (sc is None) or sc == 429 or (500 <= (sc or 0) <= 599):
        st.info("서버 응답이 지연되어 재시도 중입니다 (최대 3회)…")
        ok2, sc2, data2, err2 = json_post(url, payload, headers={"X-Request-ID": request_id}, timeout=min(10, timeout_sec), retries=3)
        if ok2:
            return data2 or {"status": "success"}
        # If ambiguous pending observed
        if data2 and ((sc2 and 200 <= sc2 <= 299) and (sc2 == 202 or str(data2.get('status','')).lower() == 'pending')):
            st.warning("접수 요청은 전달되었을 수 있습니다. 잠시 후 '통합 뷰'에서 반영 여부를 확인해 주세요.")
            return data2 or {"status": "pending"}
        return {"status": "error", "message": err2 or err or "network error"}
    # Non-retryable (4xx) → pass through
    if data and data.get('message'):
        return {"status": "error", "message": str(data.get('message'))}
    return {"status": "error", "message": err or (f"HTTP {sc}" if sc else "request failed")}


def _nz(s: Optional[str], alt: str = "") -> str:
    s = "" if s is None else str(s)
    return s.strip() if s.strip() else alt

# Streamlit 쿼리 파라미터 정규화: 리스트로 올 경우 첫값만 취함
def _qp_get(qp: Dict[str, Any], key: str, default: str = "") -> str:
    """Streamlit の st.query_params は環境によって str ではなく ['value'] の list を返すことがある。
    その差異を吸収して常に str を返す。
    """
    try:
        v = qp.get(key)
        if isinstance(v, list):
            v = v[0] if v else ""
        return _nz(v, default)
    except Exception:
        return default

def _badge(text: str) -> str:
    return f"<span style='display:inline-block;background:#e8f1ff;color:#0b5bd3;border:1px solid #b6c2d5;padding:6px 10px;border-radius:999px;font-weight:600;'>{text}</span>"

# 진행률 배지 색상 단계화
def _badge_progress(pct: int) -> str:
    """진행률 배지 색상 단계화: 0-39 회색, 40-79 주황, 80-100 초록"""
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

def _alert(msg: str, kind: str = "bad") -> None:
    if kind == "ok":
        st.success(msg)
    elif kind == "warn":
        st.warning(msg)
    else:
        st.error(msg)

def _calc_progress_pct() -> int:
    """입력 진행률 계산 (담보/세무·신용/대출/서류/리스크 5개 기준)"""
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

# ------------------------------
# 서버 스냅샷을 session_state에 병합 (필드명 매핑 포함)
# ------------------------------
def _merge_snapshot_data(snap: Dict[str, Any]) -> None:
    """서버 스냅샷을 session_state에 병합 (필드명 매핑 포함)"""
    if not snap:
        return
    data = snap.get("data") or {}
    # 본문 필드 병합
    st.session_state["collateral_profile"]   = _nz(data.get("collateral"))
    st.session_state["tax_credit_summary"]   = _nz(data.get("tax_credit"))
    st.session_state["loan_summary"]         = _nz(data.get("loan"))
    docs_raw = data.get("docs") or ""
    st.session_state["docs_check"]           = [s for s in str(docs_raw).split(",") if s.strip()]
    st.session_state["priority_exclusion"]   = _nz(data.get("priority"))
    st.session_state["risk_top3"]            = _nz(data.get("risks"))
    st.session_state["coach_notes"]          = _nz(data.get("coach"))
    # 메타(버전/락) 병합
    if "server_version" in snap:
        st.session_state.version3 = snap.get("server_version", st.session_state.get("version3", 0))
    st.session_state.locked_by = data.get("lock_owner") or snap.get("lock_owner", st.session_state.get("locked_by"))
    st.session_state.lock_until = data.get("lock_until") or snap.get("lock_until", st.session_state.get("lock_until"))


# 수동 스냅샷 조회 후, 폼 반영 전 요약을 보여주는 미리보기 패널
def _render_snapshot_preview(snap: Dict[str, Any]) -> None:
    """수동 스냅샷 조회 후, 폼 반영 전 요약을 보여주는 미리보기 패널"""
    if not snap or snap.get("status") != "success":
        return
    data = snap.get("data") or {}
    st.markdown("#### 🔍 최신 스냅샷 미리보기")
    with st.container(border=True):
        left, right = st.columns([1.2, 1])
        with left:
            st.write(f"- **상태**: {data.get('status3') or '-'}")
            st.write(f"- **진행률**: {data.get('progress') or '-'}%")
            st.write(f"- **제출일시**: {data.get('ts') or '-'}")
            st.write(f"- **담보요약**: {data.get('collateral') or '-'}")
            st.write(f"- **세무·신용**: {data.get('tax_credit') or '-'}")
            st.write(f"- **대출요약**: {data.get('loan') or '-'}")
        with right:
            st.write(f"- **서류체크**: {data.get('docs') or '-'}")
            st.write(f"- **우대/제외**: {data.get('priority') or '-'}")
            st.write(f"- **리스크 Top3**: {data.get('risks') or '-'}")
            st.write(f"- **코치메모**: {data.get('coach') or '-'}")

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("✅ 폼에 반영"):
                _merge_snapshot_data(snap)
                st.session_state.show_snapshot_preview = False
                _alert("스냅샷 내용을 폼에 반영했습니다.", "ok")
        with c2:
            if st.button("🔄 다시 불러오기"):
                s2 = snapshot_third(st.session_state.get("receipt_no",""), st.session_state.get("uuid",""))
                if s2.get("status") == "success":
                    st.session_state.last_snapshot = s2
                    _alert("최신 스냅샷을 다시 불러왔습니다.", "ok")
                else:
                    _alert("스냅샷 조회 실패 또는 미구현.", "warn")
        with c3:
            if st.button("🧹 닫기"):
                st.session_state.show_snapshot_preview = False

# ==============================
# 스타일 (2차와 톤 일치)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }
  :root { --gov-navy:#002855; --gov-blue:#0B5BD3; --gov-border:#cbd5e1; color-scheme: light !important; }
  html, body { background:#FFFFFF !important; color:#0F172A !important; }
  .stApp, [data-testid="stAppViewContainer"] { background:#FFFFFF !important; color:#0F172A !important; }
  [data-testid="stHeader"] { background:#FFFFFF !important; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"]{ display:none !important; }
  .block-container{ max-width:1200px; margin:0 auto !important; padding-left:16px; padding-right:16px; }

  .gov-topbar{ width:100%; background:var(--gov-navy); color:#fff !important; font-size:13px; padding:8px 14px; border-bottom:3px solid var(--gov-blue); }
  .gov-topbar *{ color:#fff !important; }

  .gov-hero{ padding:16px 0 8px 0; border-bottom:1px solid var(--gov-border); margin-bottom:8px; }
  .gov-hero h2{ color:var(--gov-navy); margin:0 0 6px 0; font-weight:700; }

  /* 입력 컴포넌트 테두리/포커스 일관화 */
  div[data-baseweb="input"], div[data-baseweb="select"], .stTextArea>div, .stTextInput>div, .stSelectbox>div, .stMultiSelect>div, .stDateInput>div{
    background:#fff !important; border-radius:8px !important; border:1px solid var(--gov-border) !important; box-shadow:0 1px 2px rgba(16,24,40,.04) !important;
  }
  div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within, .stTextArea>div:focus-within, .stTextInput>div:focus-within, .stSelectbox>div:focus-within, .stMultiSelect>div:focus-within{
    box-shadow:0 2px 6px rgba(16,24,40,.12) !important; outline:2px solid var(--gov-blue) !important; border-color:var(--gov-blue) !important;
  }

  div[data-testid="stFormSubmitButton"] button, .stButton>button{
    background:var(--gov-navy) !important; color:#fff !important; border:1px solid var(--gov-navy) !important; font-weight:600 !important; padding:10px 16px !important; border-radius:6px !important;
  }
  div[data-testid="stFormSubmitButton"] button:hover, .stButton>button:hover{ filter:brightness(.95); }

  .cta-wrap{ margin-top:10px; padding:12px; border:1px solid var(--gov-border); border-radius:8px; background:#fafafa; }
  .cta-kakao{ display:block; text-align:center; font-weight:700; text-decoration:none; padding:12px 16px; border-radius:10px; background:#FEE500; color:#3C1E1E; border:1px solid #FEE500; }
  .cta-kakao:hover{ filter:brightness(.97); }

  /* ===== Brand bar (1차/2차와 동일) ===== */
  .brandbar{
    display:flex; align-items:center; gap:10px;
    padding:10px 6px 4px 6px; margin:0 0 8px 0;
    border-bottom:1px solid var(--gov-border);
  }
  .brandbar img{ height:48px; display:block; }
  .brandbar .brandtxt{ display:none; }

  /* Mobile: 로고 크게 */
  @media (max-width: 640px){
    .brandbar img{ height:64px; }
    .gov-hero{ padding-top:8px; }
  }

  /* Mobile touch & textarea comfort */
  textarea{ min-height: 140px !important; }
  @media (max-width:640px){
    textarea{ min-height: 180px !important; }
    .stButton>button, div[data-testid="stFormSubmitButton"] button{ padding:14px 18px !important; }
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# GAS 액션 래퍼
# ==============================
def save_third(
    receipt_no: str,
    uuid: str,
    role: str,
    status: str,
    client_version: int,
    payload: Dict[str, Any],
    edit_lock_take: bool = False,
) -> Dict[str, Any]:
    data = {
        "token": _get_api_token_3(),
        "action": "save",
        "receipt_no": receipt_no,
        "uuid": uuid,
        "role": role,
        "status": status,                # draft | final
        "client_version": client_version,
        "payload": payload,
        "edit_lock_take": bool(edit_lock_take),
        "release_version": RELEASE_VERSION_3
    }
    return _json_post_with_resilience(APPS_SCRIPT_URL_3, data, timeout_sec=TIMEOUT_SEC)

def snapshot_third(receipt_no: str, uuid: str) -> Dict[str, Any]:
    """서버 스냅샷 조회(선택). GAS에서 action='snapshot' 구현 시 사용."""
    data = {
        "token": _get_api_token_3(),
        "action": "snapshot",
        "receipt_no": receipt_no,
        "uuid": uuid,
    }
    return _json_post_with_resilience(APPS_SCRIPT_URL_3, data, timeout_sec=15)

def take_lock(receipt_no: str, uuid: str, role: str) -> Dict[str, Any]:
    """편집권 선점(서버에서 owner=role, until=now+120s)"""
    return save_third(
        receipt_no=receipt_no,
        uuid=uuid,
        role=role,
        status="draft",
        client_version=st.session_state.get("version3", 0),
        payload={},               # 데이터 변경 없이 락만 선점
        edit_lock_take=True
    )

# ==============================
# 메인
# ==============================
def main():
    st.markdown("<div class='gov-topbar'>대한민국 정부 협력 서비스</div>", unsafe_allow_html=True)

    # 브랜드 바 (로고만 노출)
    _logo_url = _get_logo_url()
    st.markdown(
        f"""
        <div class="brandbar">
          {f'<img src="{_logo_url}" alt="{BRAND_NAME} 로고" />' if _logo_url else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="gov-hero">
      <h2>3차 심층 설문</h2>
      <p>담보/보증, 세무·신용, 대출·서류, 리스크 요약을 컨설턴트와 함께 정리합니다.</p>
    </div>
    """, unsafe_allow_html=True)

    # 쿼리 파라미터
    try:
        qp = st.query_params
        receipt_no = _qp_get(qp, "r", "")
        uuid = _qp_get(qp, "u", "")
        role = _qp_get(qp, "role", "client")
    except Exception:
        receipt_no, uuid, role = "", "", "client"

    # --- Ensure query params stay in URL (avoid losing r/u on redirects or toolbar reloads)
    try:
        current_r = _qp_get(st.query_params, "r", "")
        current_u = _qp_get(st.query_params, "u", "")
        current_role = _qp_get(st.query_params, "role", "client")
        if receipt_no and uuid and (current_r != receipt_no or current_u != uuid or current_role != role):
            # Normalize the URL so params are preserved on future reloads
            st.query_params.clear()
            st.query_params.update({"r": receipt_no, "u": uuid, "role": role})
    except Exception:
        pass

    # 접근 가능 여부 플래그 (r,u 모두 있어야 서버와 통신)
    can_connect = bool(receipt_no and uuid)

    # 스냅샷 미리보기/다시 불러오기를 위한 키 저장
    st.session_state["receipt_no"] = receipt_no
    st.session_state["uuid"] = uuid

    if not can_connect:
        _alert("접근 정보가 부족합니다. 담당자가 보낸 3차 링크로 접속해 주세요. (미리보기 모드)", "bad")
        st.markdown(
            f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 링크 재발급 요청</a></div>",
            unsafe_allow_html=True
        )
        # 미리보기 모드: 폼과 상단 제어들을 숨기고 즉시 종료
        st.session_state.readonly3 = True
        st.session_state["live_sync3"] = False
        st.stop()

    # 세션 상태
    if "version3" not in st.session_state:
        st.session_state.version3 = 0
    if "locked_by" not in st.session_state:
        st.session_state.locked_by = None
    if "lock_until" not in st.session_state:
        st.session_state.lock_until = None

    if "saving3" not in st.session_state:
        st.session_state.saving3 = False
    if "readonly3" not in st.session_state:
        st.session_state.readonly3 = False

    # ARIA live region for assistive technologies
    st.markdown('<div id="live-status" aria-live="polite" style="position:absolute;left:-9999px;height:1px;width:1px;overflow:hidden;">ready</div>', unsafe_allow_html=True)

    # 라이브 동기화(자동 새로고침 + 스냅샷 병합)
    if "live_sync3" not in st.session_state:
        st.session_state.live_sync3 = True
    if "last_pull3" not in st.session_state:
        st.session_state.last_pull3 = None

    if can_connect:
        meta_cols = st.columns([2, 1.6, 1.2, 1.2, 1.2, 1.6])
        with meta_cols[0]:
            st.markdown(_badge(f"접수번호: {receipt_no}"), unsafe_allow_html=True)
        # Debug mini-line (masked) to verify query parsing works on Render
        masked_r = receipt_no[:6] + "…" if receipt_no else "-"
        masked_u = (uuid[:6] + "…") if uuid else "-"
        if SHOW_DEBUG:
            st.caption(f"r={masked_r} · u={masked_u}")
        with meta_cols[1]:
            st.markdown(_badge(f"역할: {('코치' if role=='coach' else '고객')}"), unsafe_allow_html=True)
        with meta_cols[2]:
            try:
                progress_pct = _calc_progress_pct()
            except Exception:
                progress_pct = 0
            st.markdown(_badge_progress(progress_pct), unsafe_allow_html=True)
        with meta_cols[3]:
            if st.button("🔓 편집 권한 가져오기", disabled=(not can_connect) or st.session_state.get("saving3", False)):
                r = take_lock(receipt_no, uuid, role)
                if r.get("status") in ("success", "pending"):
                    st.session_state.locked_by = r.get("lock_owner")
                    st.session_state.lock_until = r.get("lock_until")
                    st.session_state.version3 = r.get("server_version", st.session_state.version3)
                    _alert("편집 권한을 가져왔습니다.", "ok")
                elif r.get("status") == "locked":
                    _alert("다른 사용자가 편집 중입니다.", "warn")
                else:
                    _alert(_nz(r.get("message"), "편집 권한 요청 실패"), "bad")
        with meta_cols[4]:
            if st.button("⟳ 스냅샷 새로고침", disabled=(not can_connect) or st.session_state.get("saving3", False)):
                if can_connect:
                    snap = snapshot_third(receipt_no, uuid)
                    if snap.get("status") == "success":
                        st.session_state.version3 = snap.get("server_version", st.session_state.version3)
                        st.session_state.last_snapshot = snap
                        st.session_state.show_snapshot_preview = True
                        _alert("최신 스냅샷을 불러왔습니다. 아래 미리보기에서 확인 후 폼에 반영하세요.", "ok")
                    else:
                        _alert("스냅샷 조회 실패 또는 미구현.", "warn")
        with meta_cols[5]:
            st.caption(f"편집자: {st.session_state.get('locked_by') or '-'}")
            st.caption(f"락만료: {st.session_state.get('lock_until') or '-'}")
            st.toggle(
                "라이브 동기화",
                key="live_sync3",
                value=st.session_state.get("live_sync3", True if can_connect else False),
                help=f"켜면 {int(LIVE_SYNC_MS/1000)}초 간격으로 상대방 변경사항을 자동 반영합니다.",
                disabled=not can_connect
            )

        st.markdown("---")

    # 수동 스냅샷 미리보기 패널
    if st.session_state.get("show_snapshot_preview", False) and st.session_state.get("last_snapshot"):
        _render_snapshot_preview(st.session_state["last_snapshot"])

    # ---- Conflict resolution mini panel ----
    if can_connect and st.session_state.get("conflict3", False):
        with st.container(border=True):
            st.warning("다른 기기에서 먼저 저장하여 버전 충돌이 발생했습니다.")
            cc1, cc2, cc3 = st.columns([1,1,2])
            with cc1:
                if st.button("🔄 최신 불러오기"):
                    snap = snapshot_third(receipt_no, uuid)
                    if snap.get("status") == "success":
                        _merge_snapshot_data(snap)
                        st.session_state.conflict3 = False
                        _alert("서버 최신 버전으로 갱신했습니다.", "ok")
                    else:
                        _alert("스냅샷 조회 실패 또는 미구현.", "warn")
            with cc2:
                if st.button("🧹 경고 닫기"):
                    st.session_state.conflict3 = False
            with cc3:
                st.caption("TIP: 최신 불러오기 후 필요한 부분만 다시 입력하고 임시 저장(Draft)하세요.")

    # ---- Live Puller: 상대방 저장사항을 2초 간격으로 자동 반영 ----
    if can_connect and st.session_state.get("live_sync3", True) and not st.session_state.get("saving3", False):
        try:
            snap = snapshot_third(receipt_no, uuid)
            if snap.get("status") == "success":
                remote_ver = int(snap.get("server_version") or 0)
                local_ver = int(st.session_state.get("version3") or 0)
                if remote_ver > local_ver:
                    _merge_snapshot_data(snap)
                    _alert("상대방 변경사항을 자동 반영했습니다.", "ok")
        except Exception:
            pass

    # 주기적 재호출 (Streamlit 버전별 호환)
    if can_connect and st.session_state.get("live_sync3", True):
        if hasattr(st, "autorefresh"):
            st.autorefresh(interval=LIVE_SYNC_MS, key="live_sync3_tick")
        else:
            # Fallback: JS로 정기 리로드 (LIVE_SYNC_MS 밀리초)
            st.markdown(f"&lt;script&gt;setTimeout(function(){{ location.reload(); }}, {LIVE_SYNC_MS});&lt;/script&gt;", unsafe_allow_html=True)

    # 폼 (이름: third_survey) - 2열 배치
    with st.form("third_survey"):
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### 🧱 담보·보증 요약")
            collateral_profile = st.text_area(
                "담보/보증 계획 (자산·평가·보증기관 등)",
                placeholder="예: 부동산 담보 2.5억 평가 예정, 신용보증기금 보증 80%",
                key="collateral_profile",
                disabled=st.session_state.get("readonly3", False),
            )

            st.markdown("### 🏦 대출/자금 현황")
            loan_summary = st.text_area(
                "기존 대출/금리/만기/상환계획",
                placeholder="예: 기업은행 운전자금 1.2억 @ 5.2%, 만기 2026-06, 거치 12개월",
                key="loan_summary",
                disabled=st.session_state.get("readonly3", False),
            )

            st.markdown("### 🏷 우대/제외 요건")
            priority_exclusion = st.text_input(
                "우대·제외 요건 (콤마로 구분)",
                placeholder="예: 청년창업, 여성기업 / 제외 없음",
                key="priority_exclusion",
                disabled=st.session_state.get("readonly3", False),
            )

        with col_right:
            st.markdown("### 🧾 세무·신용 요약")
            tax_credit_summary = st.text_area(
                "세무·신용 상태 (부가세·4대보험·체납/연체 등)",
                placeholder="예: 부가세 과세매출 3.2억, 체납 없음, 4대보험 정상",
                key="tax_credit_summary",
                disabled=st.session_state.get("readonly3", False),
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
            docs_check = st.multiselect("보유 서류를 선택하세요", options=docs_options, key="docs_check", disabled=st.session_state.get("readonly3", False))

            st.markdown("### ⚠️ 리스크 Top3")
            risk_top3 = st.text_area(
                "핵심 리스크 3가지(줄바꿈으로 구분)",
                placeholder="예: 부채비율 270%\n담보 부족\n운전자금 부족",
                key="risk_top3",
                disabled=st.session_state.get("readonly3", False),
            )

        st.markdown("### 🗒 코치 메모 (코치 전용)")
        coach_notes = st.text_area(
            "컨설턴트 코멘트/후속 액션",
            placeholder="예: 부가세 신고서 원본 요청, 담보 감정 일정 예약",
            key="coach_notes",
            disabled=st.session_state.get("readonly3", False),
        )
        if role != "coach":
            st.caption("※ 고객 역할로 접속 시 코치메모는 고객에게 설명용으로만 노출됩니다.")

        col_btn1, col_btn2 = st.columns(2)
        submit_draft = col_btn1.form_submit_button(
            "💾 임시 저장 (Draft)",
            disabled=(not can_connect) or st.session_state.get("saving3", False) or st.session_state.get("readonly3", False),
        )
        submit_final = col_btn2.form_submit_button(
            "📨 최종 제출 (Final)",
            disabled=(not can_connect) or st.session_state.get("saving3", False) or st.session_state.get("readonly3", False),
        )
        # Final submit confirmation (accessibility & safety)
        st.caption("※ 최종 제출 후에는 수정이 불가능합니다. 필요 시 임시 저장을 먼저 사용하세요.")
        confirm_final = st.checkbox("최종 제출에 동의합니다. (제출 후 수정 불가)", key="confirm_final", value=False)
        if st.session_state.get("readonly3", False):
            st.info("이 설문은 최종 제출되어 더 이상 수정할 수 없습니다. (읽기 전용)")

    def _payload() -> Dict[str, Any]:
        return {
            "collateral_profile": _nz(st.session_state.get("collateral_profile")),
            "tax_credit_summary": _nz(st.session_state.get("tax_credit_summary")),
            "loan_summary": _nz(st.session_state.get("loan_summary")),
            "docs_check": st.session_state.get("docs_check", []),
            "priority_exclusion": _nz(st.session_state.get("priority_exclusion")),
            "risk_top3": _nz(st.session_state.get("risk_top3")),
            "coach_notes": _nz(st.session_state.get("coach_notes")),
            "release_version_3": RELEASE_VERSION_3,
        }

    # 제출 처리
    if not can_connect:
        st.info("미리보기 모드입니다. 올바른 링크로 접속하면 저장/제출이 활성화됩니다.")
    if (submit_draft or submit_final) and can_connect:
        # Calculate progress for minimal validation on final submission
        try:
            _progress_pct = _calc_progress_pct()
        except Exception:
            _progress_pct = 0

        # Guard rails for final submission: require confirmation and minimal completeness
        if submit_final:
            if not st.session_state.get("confirm_final", False):
                _alert("최종 제출 전에 동의 체크박스를 먼저 선택해주세요.", "warn")
                submit_final = False
            elif _progress_pct < 60:
                _alert("최종 제출을 위해선 핵심 항목을 조금만 더 채워주세요. (진행률 60% 이상 권장)", "warn")
                submit_final = False

        if not (submit_draft or submit_final):
            # Nothing to submit after guard rails
            st.stop()

        status_flag = "final" if submit_final else "draft"
        st.session_state.saving3 = True
        with st.spinner("⏳ 저장/제출 처리 중입니다. 잠시만 기다려 주세요..."):
            result = save_third(
                receipt_no=receipt_no,
                uuid=uuid,
                role=role,
                status=status_flag,
                client_version=st.session_state.get("version3", 0),
                payload=_payload(),
                edit_lock_take=False
            )

        status = result.get("status")
        st.session_state.saving3 = False
        if status in ("success", "pending"):
            if status == "pending":
                _alert("접수 완료(서버 응답 지연). 새로고침/중복 제출은 피해주세요.", "ok")
            else:
                _alert("저장/제출이 완료되었습니다.", "ok")

            # 서버 버전/락 정보 반영
            st.session_state.version3 = result.get("server_version", st.session_state.version3)
            st.session_state.locked_by = result.get("lock_owner", st.session_state.locked_by)
            st.session_state.lock_until = result.get("lock_until", st.session_state.lock_until)
            if status_flag == "final":
                st.session_state.readonly3 = True

            _alert("전문가 검토 후 후속 안내를 드립니다.", "ok")
            st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 카카오 채널로 문의하기</a></div>", unsafe_allow_html=True)

            # 1.5초 후 되돌아가기 스크립트(2차 UX와 동일)
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
        elif status == "locked":
            _alert("다른 사용자가 편집 중입니다. 잠시 후 다시 시도하거나 상단의 '편집 권한 가져오기'를 이용하세요.", "warn")
        elif status == "conflict":
            st.session_state.conflict3 = True
            _alert("다른 기기에서 먼저 저장했습니다. 아래 충돌 패널에서 '최신 불러오기'를 눌러 최신 내용으로 갱신하세요. 작성 내용은 임시 보관되었습니다. '최신 불러오기' 후 다시 저장해 주세요.", "warn")
        elif status == "forbidden":
            _alert("접근이 제한되었습니다. 접수번호/UUID를 확인하거나 담당자에게 문의해주세요.", "bad")
        else:
            _alert(f"제출 실패: {result.get('message','알 수 없는 오류')}", "bad")

if __name__ == "__main__":
    main()
