import streamlit as st
import requests
from datetime import datetime
import os
from typing import Optional, Dict, Any, List

# ==============================
# 기본 페이지/레이아웃
# ==============================
st.set_page_config(page_title="유아플랜 3차 심층 설문", page_icon="🧭", layout="wide")

# ------------------------------
# 환경/상수 (필요시 교체)
# ------------------------------
RELEASE_VERSION_3 = "v2025-09-10-1"
TIMEOUT_SEC = 45  # 서버 지연 대비. 재시도 없음, pending 처리 철학 유지

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

# 3차 저장용 GAS 엔드포인트 (회장님 배포 후 교체)
THIRD_GAS_URL = os.getenv("THIRD_GAS_URL", "https://script.google.com/macros/s/DEPLOY_ID_3RD/exec")

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
def _json_post(url: str, payload: Dict[str, Any], timeout_sec: int = TIMEOUT_SEC) -> Dict[str, Any]:
    try:
        r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=timeout_sec)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        # 저장은 되었으나 응답 지연 가능 → 사용자 혼선을 막기 위해 pending 반환
        return {"status": "pending", "message": "server timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _nz(s: Optional[str], alt: str = "") -> str:
    s = "" if s is None else str(s)
    return s.strip() if s.strip() else alt

def _badge(text: str) -> str:
    return f"<span style='display:inline-block;background:#e8f1ff;color:#0b5bd3;border:1px solid #b6c2d5;padding:6px 10px;border-radius:999px;font-weight:600;'>{text}</span>"

# ==============================
# 스타일 (2차와 톤 일치)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }
  :root { --gov-navy:#002855; --gov-blue:#0B5BD3; --gov-border:#cbd5e1; color-scheme: light; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"]{ display:none !important; }

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
  .brandbar img{ height:34px; display:block; }
  .brandbar .brandtxt{ font-weight:800; letter-spacing:-0.2px; color:#0f172a; }

  /* Mobile: 로고 크게 */
  @media (max-width: 640px){
    .brandbar img{ height:44px; }
    .gov-hero{ padding-top:8px; }
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
    return _json_post(THIRD_GAS_URL, data, timeout_sec=TIMEOUT_SEC)

def snapshot_third(receipt_no: str, uuid: str) -> Dict[str, Any]:
    """서버 스냅샷 조회(선택). GAS에서 action='snapshot' 구현 시 사용."""
    data = {
        "token": _get_api_token_3(),
        "action": "snapshot",
        "receipt_no": receipt_no,
        "uuid": uuid,
    }
    return _json_post(THIRD_GAS_URL, data, timeout_sec=15)

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

    # 브랜드 바 (로고 + 텍스트)
    _logo_url = _get_logo_url()
    st.markdown(
        f"""
        <div class="brandbar">
          {f'<img src="{_logo_url}" alt="{BRAND_NAME} 로고" />' if _logo_url else ''}
          <span class="brandtxt">{BRAND_NAME}</span>
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
        receipt_no = _nz(qp.get("r"), "")
        uuid = _nz(qp.get("u"), "")
        role = _nz(qp.get("role"), "client")
    except Exception:
        receipt_no, uuid, role = "", "", "client"

    if not receipt_no or not uuid:
        st.error("접근 정보가 부족합니다. 담당자가 보낸 3차 링크로 접속해 주세요.")
        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 링크 재발급 요청</a></div>", unsafe_allow_html=True)
        st.stop()

    # 세션 상태
    if "version3" not in st.session_state:
        st.session_state.version3 = 0
    if "locked_by" not in st.session_state:
        st.session_state.locked_by = None
    if "lock_until" not in st.session_state:
        st.session_state.lock_until = None

    meta_cols = st.columns([2, 2, 1.3, 1.2])
    with meta_cols[0]:
        st.markdown(_badge(f"접수번호: {receipt_no}"), unsafe_allow_html=True)
    with meta_cols[1]:
        st.markdown(_badge(f"역할: {('코치' if role=='coach' else '고객')}"), unsafe_allow_html=True)
    with meta_cols[2]:
        if st.button("🔓 편집 권한 가져오기"):
            r = take_lock(receipt_no, uuid, role)
            if r.get("status") in ("success", "pending"):
                st.session_state.locked_by = r.get("lock_owner")
                st.session_state.lock_until = r.get("lock_until")
                st.session_state.version3 = r.get("server_version", st.session_state.version3)
                st.success("편집 권한을 가져왔습니다.")
            elif r.get("status") == "locked":
                st.warning("다른 사용자가 편집 중입니다.")
            else:
                st.error(_nz(r.get("message"), "편집 권한 요청 실패"))
    with meta_cols[3]:
        if st.button("⟳ 스냅샷 새로고침"):
            snap = snapshot_third(receipt_no, uuid)
            if snap.get("status") == "success":
                st.session_state.version3 = snap.get("server_version", st.session_state.version3)
                st.info("최신 스냅샷으로 동기화했습니다.")
            else:
                st.warning("스냅샷 조회 실패 또는 미구현.")

    st.markdown("---")

    # 폼
    with st.form("survey3"):
        st.markdown("### 🧱 담보·보증 요약")
        collateral_profile = st.text_area("담보/보증 계획 (자산·평가·보증기관 등)", placeholder="예: 부동산 담보 2.5억 평가 예정, 신용보증기금 보증 80%")

        st.markdown("### 🧾 세무·신용 요약")
        tax_credit_summary = st.text_area("세무·신용 상태 (부가세·4대보험·체납/연체 등)", placeholder="예: 부가세 과세매출 3.2억, 체납 없음, 4대보험 정상")

        st.markdown("### 🏦 대출/자금 현황")
        loan_summary = st.text_area("기존 대출/금리/만기/상환계획", placeholder="예: 기업은행 운전자금 1.2억 @ 5.2%, 만기 2026-06, 거치 12개월")

        st.markdown("### 📑 준비 서류 체크")
        docs_options = ["사업자등록증", "재무제표(최근 2~3년)", "부가세신고서", "납세증명", "4대보험 완납증명", "매출증빙(세금계산서/카드내역)", "통장사본", "기타"]
        docs_check = st.multiselect("보유 서류를 선택하세요", options=docs_options)

        st.markdown("### 🏷 우대/제외 요건")
        priority_exclusion = st.text_input("우대·제외 요건 (콤마로 구분)", placeholder="예: 청년창업, 여성기업 / 제외 없음")

        st.markdown("### ⚠️ 리스크 Top3")
        risk_top3 = st.text_area("핵심 리스크 3가지(줄바꿈으로 구분)", placeholder="예: 부채비율 270%\n담보 부족\n운전자금 부족")

        st.markdown("### 🗒 코치 메모 (코치 전용)")
        coach_notes = st.text_area("컨설턴트 코멘트/후속 액션", placeholder="예: 부가세 신고서 원본 요청, 담보 감정 일정 예약")
        if role != "coach":
            st.caption("※ 고객 역할로 접속 시 코치메모는 고객에게 설명용으로만 노출됩니다.")

        col_btn1, col_btn2 = st.columns(2)
        submit_draft = col_btn1.form_submit_button("💾 임시 저장 (Draft)")
        submit_final = col_btn2.form_submit_button("📨 최종 제출 (Final)")

    def _payload() -> Dict[str, Any]:
        return {
            "collateral_profile": _nz(collateral_profile),
            "tax_credit_summary": _nz(tax_credit_summary),
            "loan_summary": _nz(loan_summary),
            "docs_check": docs_check,
            "priority_exclusion": _nz(priority_exclusion),
            "risk_top3": _nz(risk_top3),
            "coach_notes": _nz(coach_notes) if role == "coach" else _nz(coach_notes),  # 서버에서 role별 권한 체크
            "release_version_3": RELEASE_VERSION_3,
        }

    # 제출 처리
    if submit_draft or submit_final:
        status_flag = "final" if submit_final else "draft"
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
        if status in ("success", "pending"):
            if status == "pending":
                st.success("✅ 접수 완료(서버 응답 지연). 새로고침/중복 제출은 피해주세요.")
            else:
                st.success("✅ 저장/제출이 완료되었습니다.")

            # 서버 버전/락 정보 반영
            st.session_state.version3 = result.get("server_version", st.session_state.version3)
            st.session_state.locked_by = result.get("lock_owner", st.session_state.locked_by)
            st.session_state.lock_until = result.get("lock_until", st.session_state.lock_until)

            st.info("전문가 검토 후 후속 안내를 드립니다.")
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
            st.warning("다른 사용자가 편집 중입니다. 잠시 후 다시 시도하거나 상단의 '편집 권한 가져오기'를 이용하세요.")
        elif status == "conflict":
            st.error("다른 쪽에서 먼저 저장했습니다. 상단의 [스냅샷 새로고침] 후 다시 수정해주세요.")
        elif status == "forbidden":
            st.error("접근이 제한되었습니다. 접수번호/UUID를 확인하거나 담당자에게 문의해주세요.")
        else:
            st.error(f"제출 실패: {result.get('message','알 수 없는 오류')}")

if __name__ == "__main__":
    main()