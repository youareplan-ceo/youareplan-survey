# -*- coding: utf-8 -*-
"""
유아플랜 2차 심화진단 – Streamlit (v2-2025-11-26-final)
- 투명 배경 CSS (다크/라이트 자동 적응)
- 년/월/일 분리 selectbox
- placeholder 연하게
"""
import os
import time
import re
import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Optional
from uuid import uuid4
import json
import requests
import streamlit as st

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(page_title="유아플랜 정책자금 2차 심화진단", page_icon="📝", layout="centered")

RELEASE_VERSION = "v2-2025-11-26-final"

# ==============================
# 환경 설정
# ==============================
class _Config:
    SECOND_GAS_URL = os.getenv("SECOND_GAS_URL", "")
    FIRST_GAS_TOKEN_API_URL = os.getenv("FIRST_GAS_TOKEN_API_URL", "")
    API_TOKEN_STAGE2 = os.getenv("API_TOKEN_2", "youareplan_stage2")

config = _Config()

BRAND_NAME = "유아플랜"
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# ==============================
# GAS URL 정규화
# ==============================
def _normalize_gas_url(u: str) -> str:
    try:
        s = str(u or "").strip()
    except:
        return u
    if not s:
        return s
    if s.endswith("/exec") or s.endswith("/dev"):
        return s
    if "/macros/s/" in s and s.startswith("http"):
        return s + "/exec"
    return s

APPS_SCRIPT_URL = _normalize_gas_url(config.SECOND_GAS_URL)
TOKEN_API_URL = _normalize_gas_url(config.FIRST_GAS_TOKEN_API_URL)
INTERNAL_SHARED_KEY = "youareplan"
API_TOKEN = config.API_TOKEN_STAGE2

# ==============================
# HTTP 통신
# ==============================
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

# ==============================
# 유틸리티
# ==============================
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

# ==============================
# 스타일링 (투명 배경 방식)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  
  html, body, .stApp {
    font-family: 'Noto Sans KR', sans-serif;
  }

  /* 상단 메뉴/푸터/사이드바 숨김 */
  #MainMenu, footer { visibility: hidden !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }

  .block-container { max-width: 900px; margin: 0 auto !important; padding: 16px; }

  /* ===== 브랜드 요소 (고정색) ===== */
  .brandbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    background: #002855;
    border-bottom: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 8px;
  }
  .brandbar img { height: 48px; display: block; }
  @media (max-width: 740px) { .brandbar img { height: 64px; } }

  .gov-topbar {
    width: 100%;
    background: #002855;
    color: #fff !important;
    font-size: 13px;
    padding: 8px 14px;
    border-bottom: 3px solid #005BAC;
  }
  .gov-topbar * { color: #fff !important; }

  .gov-hero {
    padding: 16px 0 8px 0;
    border-bottom: 1px solid rgba(128,128,128,0.2);
    margin-bottom: 8px;
  }
  .gov-hero h2 { color: #002855; margin: 0 0 6px 0; font-weight: 700; }
  @media (prefers-color-scheme: dark) {
    .gov-hero h2 { color: #60a5fa; }
  }
  .gov-hero p { opacity: 0.7; margin: 0; }

  /* ===== 입력 필드 - 투명 배경 ===== */
  .stTextInput > div > div > input,
  .stNumberInput > div > div > input,
  .stTextArea > div > div > textarea {
    background: transparent !important;
    color: inherit !important;
    border: 1px solid rgba(128,128,128,0.3) !important;
    border-radius: 8px !important;
  }

  /* SelectBox / MultiSelect 컨테이너 */
  .stSelectbox > div,
  .stMultiSelect > div,
  div[data-baseweb="select"],
  div[data-baseweb="select"] > div {
    background: transparent !important;
    color: inherit !important;
    border-color: rgba(128,128,128,0.3) !important;
  }

  /* SelectBox 내부 입력창 */
  div[data-baseweb="select"] input,
  div[data-baseweb="select"] > div > div {
    background: transparent !important;
    color: inherit !important;
  }

  /* 드롭다운 팝오버 - 반투명 */
  div[data-baseweb="popover"],
  div[data-baseweb="menu"],
  div[role="listbox"],
  ul[role="listbox"] {
    background: rgba(128,128,128,0.1) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(128,128,128,0.2) !important;
  }

  /* 드롭다운 옵션 */
  li[role="option"], div[role="option"] {
    background: transparent !important;
    color: inherit !important;
  }
  li[role="option"]:hover, div[role="option"]:hover {
    background: rgba(128,128,128,0.2) !important;
  }

  /* 선택된 태그 - 파란색 고정 */
  [data-baseweb="tag"] {
    background: #2563eb !important;
  }
  [data-baseweb="tag"] span,
  [data-baseweb="tag"] * {
    color: #fff !important;
  }

  /* Number Input +/- 버튼 */
  .stNumberInput button {
    background: rgba(128,128,128,0.1) !important;
    border: 1px solid rgba(128,128,128,0.3) !important;
    color: inherit !important;
  }

  /* 체크박스 컨테이너 */
  .stCheckbox {
    padding: 12px 14px !important;
    border: 1px solid rgba(128,128,128,0.2) !important;
    border-radius: 8px !important;
    background: transparent !important;
  }

  /* ===== 버튼 (고정색) ===== */
  div[data-testid="stFormSubmitButton"] button,
  .stButton > button {
    background: #002855 !important;
    color: #fff !important;
    border: 1px solid #002855 !important;
    font-weight: 600;
    padding: 10px 16px;
    border-radius: 6px;
  }
  div[data-testid="stFormSubmitButton"] button:hover,
  .stButton > button:hover {
    filter: brightness(1.1);
  }

  /* Placeholder 연하게 */
  ::placeholder {
    color: rgba(128,128,128,0.4) !important;
    opacity: 1 !important;
  }
  input::placeholder,
  textarea::placeholder {
    color: rgba(128,128,128,0.4) !important;
  }

  /* 동의 섹션 */
  .consent-note {
    margin-top: 6px;
    font-size: 12px;
    opacity: 0.6;
    line-height: 1.5;
    min-height: 38px;
  }

  /* CTA 버튼 */
  .cta-wrap {
    margin-top: 10px;
    padding: 12px;
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 8px;
    background: rgba(128,128,128,0.05);
  }
  .cta-kakao {
    display: block;
    text-align: center;
    font-weight: 700;
    text-decoration: none;
    padding: 12px 16px;
    border-radius: 10px;
    background: #FEE500;
    color: #3C1E1E !important;
  }

  /* 모바일 대응 */
  @media (max-width: 768px) {
    .stApp { padding-bottom: calc(env(safe-area-inset-bottom,0px) + 200px) !important; }
    textarea { min-height: 180px !important; }
  }
  textarea { min-height: 140px !important; }
</style>
""", unsafe_allow_html=True)

# ==============================
# 토큰 검증
# ==============================
def validate_access_token(token: str, uuid_hint: str = None, timeout_sec: int = 10) -> dict:
    if not TOKEN_API_URL:
        return {"ok": False, "message": "TOKEN_API_URL이 설정되지 않았습니다"}
    try:
        payload = {"action": "validate", "token": token, "api_token": INTERNAL_SHARED_KEY}
        if uuid_hint:
            payload["uuid"] = uuid_hint
        ok, status_code, resp_data, err = post_json(TOKEN_API_URL, payload, timeout=timeout_sec, retries=1)
        if ok:
            return resp_data or {"ok": False, "message": "empty response"}
        if status_code == 404:
            try:
                r = requests.get(_normalize_gas_url(TOKEN_API_URL), params=payload, timeout=timeout_sec)
                if r.status_code == 200:
                    return r.json()
            except:
                pass
        return {"ok": False, "message": err or f"HTTP {status_code}"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

# ==============================
# 저장
# ==============================
def save_to_google_sheet(data, timeout_sec: int = 45, test_mode: bool = False):
    if test_mode:
        return {"status": "test", "message": "테스트 모드"}
    if not APPS_SCRIPT_URL:
        return {"status": "error", "message": "SECOND_GAS_URL이 설정되지 않았습니다"}
    
    data['token'] = API_TOKEN
    request_id = str(uuid4())
    
    ok, status_code, resp_data, err = post_json(
        APPS_SCRIPT_URL, data,
        headers={"X-Request-ID": request_id, "Content-Type": "application/json"},
        timeout=timeout_sec, retries=0
    )
    
    if (not ok) and isinstance(resp_data, dict) and resp_data.get("ok") is True:
        ok = True
    
    if ok:
        return resp_data or {"status": "success"}
    
    # 타임아웃/서버오류 시 재시도
    is_timeout = (status_code is None) or status_code == 429 or (500 <= (status_code or 0) <= 599)
    if is_timeout:
        st.info("⏳ 서버 응답 지연, 재시도 중...")
        ok2, sc2, rd2, err2 = post_json(APPS_SCRIPT_URL, data,
            headers={"X-Request-ID": request_id}, timeout=timeout_sec, retries=1)
        if (not ok2) and isinstance(rd2, dict) and rd2.get("ok") is True:
            ok2 = True
        if ok2:
            return rd2 or {"status": "success"}
        # 타임아웃이어도 성공 처리 (False Negative 방지)
        if (sc2 is None) or sc2 == 429 or (500 <= (sc2 or 0) <= 599):
            return {"status": "success_delayed", "message": "서버 처리 완료 (응답 지연)"}
        return {"status": "error", "message": err2 or err or "network error"}
    
    return {"status": "error", "message": err or f"HTTP {status_code}"}

# ==============================
# 메인
# ==============================
def main():
    if "saving2" not in st.session_state:
        st.session_state.saving2 = False
    if "submitted_2" not in st.session_state:
        st.session_state.submitted_2 = False

    # 브랜드바
    st.markdown(f"""
<div class="brandbar">
  <img src="{DEFAULT_LOGO_URL}" alt="{BRAND_NAME} 로고">
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
        st.error(f"접속이 차단되었습니다: {v.get('message', '토큰 검증 실패')}")
        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 새 링크 요청</a></div>", unsafe_allow_html=True)
        return

    parent_rid = v.get("parent_receipt_no", "")
    remain_min = v.get("remaining_minutes")
    if remain_min is None:
        sec = v.get("remaining_seconds")
        if isinstance(sec, (int, float)):
            remain_min = max(0, int(round(sec / 60)))
    if remain_min is not None:
        st.markdown(f"<span style='background:#e8f1ff;color:#0b5bd3;padding:6px 12px;border-radius:20px;font-weight:600;'>남은 시간: {int(remain_min)}분</span>", unsafe_allow_html=True)

    masked_phone = v.get("phone_mask")
    if masked_phone:
        st.caption(f"✅ 인증됨 · 접수번호: **{parent_rid}** / 연락처: **{masked_phone}**")

    st.info("✔ 1차 상담 후 진행하는 **심화 진단** 절차입니다.")

    # ===== 설문 폼 =====
    with st.form("second_survey"):
        st.markdown("### 📝 2차 설문 - 상세 정보")

        # A. 기본 정보
        st.markdown("#### 👤 기본 정보")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            name = st.text_input("성함 (필수)", placeholder="홍길동").strip()
            phone_raw = st.text_input("연락처 (필수)", placeholder="01012345678")
            st.caption("숫자만 입력하세요")
        with col_b2:
            email = st.text_input("이메일 (선택)", placeholder="email@example.com")
            biz_no_raw = st.text_input("사업자등록번호 (선택)", placeholder="0000000000")
            st.caption("10자리 숫자")
        
        st.text_input("1차 접수번호", value=parent_rid, disabled=True)
        st.markdown("---")

        # B. 사업 정보
        st.markdown("#### 📊 사업 정보")
        company = st.text_input("상호명 (필수)", placeholder="주식회사 유아플랜")

        # 년/월/일 분리 선택
        st.write("**사업 개시일 (필수)**")
        current_year = datetime.now().year
        col_y, col_m, col_d = st.columns(3)
        with col_y:
            start_year = st.selectbox("년", range(current_year, 1989, -1), 
                                      format_func=lambda x: f"{x}년", index=2)
        with col_m:
            start_month = st.selectbox("월", range(1, 13), 
                                       format_func=lambda x: f"{x}월")
        with col_d:
            start_day = st.selectbox("일", range(1, 32), 
                                     format_func=lambda x: f"{x}일")
        
        # 날짜 유효성 검사
        max_day = calendar.monthrange(start_year, start_month)[1]
        if start_day > max_day:
            start_day = max_day
        startup_date = datetime(start_year, start_month, start_day)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            store_type = st.selectbox("점포 형태", ["자가", "임차", "무점포(온라인/배달)", "기타"])
        with col_s2:
            pass

        # 임차 시 보증금/월세
        if store_type == "임차":
            col_dep, col_rent = st.columns(2)
            with col_dep:
                deposit = st.text_input("보증금 (만원)", placeholder="5000")
            with col_rent:
                monthly_rent = st.text_input("월세 (만원)", placeholder="100")
        else:
            deposit, monthly_rent = "", ""

        st.markdown("---")

        # C. 재무 정보 (영업 기간 기반 동적 표시)
        st.markdown("#### 💰 재무 현황")
        
        today = datetime.now()
        months_in_biz = relativedelta(today, startup_date).years * 12 + relativedelta(today, startup_date).months

        st.markdown("**연매출액 (단위: 만원)**")
        
        if months_in_biz < 6:
            st.caption("📌 영업 6개월 미만: 올해 예상 매출만 입력")
            revenue_curr = st.text_input(f"{current_year}년 (예상)", placeholder="예: 5000")
            revenue_y1, revenue_y2 = "", ""
        elif months_in_biz < 18:
            st.caption("📌 영업 6~18개월: 올해 + 전년 매출 입력 (있는 경우)")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                revenue_curr = st.text_input(f"{current_year}년", placeholder="예: 5000")
            with col_r2:
                revenue_y1 = st.text_input(f"{current_year-1}년 (있으면)", placeholder="예: 3000")
            revenue_y2 = ""
        else:
            st.caption("📌 영업 18개월 이상: 최근 3년 매출 입력")
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                revenue_curr = st.text_input(f"{current_year}년", placeholder="5000")
            with col_r2:
                revenue_y1 = st.text_input(f"{current_year-1}년", placeholder="3500")
            with col_r3:
                revenue_y2 = st.text_input(f"{current_year-2}년", placeholder="2000")

        col_cap, col_debt = st.columns(2)
        with col_cap:
            capital = st.text_input("자본금 (만원)", placeholder="5000")
        with col_debt:
            debt = st.text_input("부채 (만원)", placeholder="12000")

        st.caption("⚠️ 매출액은 정책자금 한도 산정의 기준이 됩니다.")
        st.markdown("---")

        # D. 보증 이용 경험
        st.markdown("#### 🏦 보증 이용 경험")
        guarantee_history = st.multiselect(
            "기존 보증 이용 경험 (선택)",
            ["신용보증기금", "기술보증기금", "지역신용보증재단", "소상공인시장진흥공단", "없음"],
            placeholder="해당사항 선택"
        )
        st.markdown("---")

        # E. 기술·인증
        st.markdown("#### 💡 기술·인증 현황")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            research_lab = st.selectbox("기업부설연구소", ["미보유", "연구소 보유", "전담부서 보유"])
        with col_t2:
            certifications = st.multiselect(
                "보유 인증 (선택)",
                ["해당없음", "벤처기업", "이노비즈", "메인비즈", "ISO", "특허/실용신안", "여성기업", "뿌리기업"],
                placeholder="해당사항 선택"
            )
        st.markdown("---")

        # F. 자금 용도
        st.markdown("#### 💵 자금 활용 계획")
        fund_purpose = st.multiselect(
            "자금 용도 (선택)",
            ["운전자금", "시설자금", "대환자금", "창업자금", "R&D자금", "수출자금", "기타"],
            placeholder="해당사항 선택"
        )
        detailed_plan = st.text_area("상세 활용 계획 (선택)", placeholder="예: 생산설비 2억, 원자재 구매 1억")
        st.markdown("---")

        # G. 리스크 체크
        st.markdown("#### 🚨 리스크 확인")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            tax_status = st.selectbox("세금 체납 (필수)", ["체납 없음", "체납 있음", "분납 중"])
        with col_r2:
            credit_status = st.selectbox("금융 연체 (필수)", ["연체 없음", "30일 미만", "30일 이상"])
        
        business_status = st.selectbox("영업 상태 (필수)", ["정상 영업", "휴업", "폐업 예정"])

        risk_msgs = []
        if tax_status != "체납 없음":
            risk_msgs.append("세금 체납")
        if credit_status != "연체 없음":
            risk_msgs.append("금융 연체")
        if business_status != "정상 영업":
            risk_msgs.append("휴/폐업")
        if risk_msgs:
            st.warning(f"⚠️ 지원 제한 가능: {', '.join(risk_msgs)}")
        st.markdown("---")

        # H. 동의
        st.markdown("#### 🤝 동의")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)")
            st.markdown('<span class="consent-note">상담·자격검토·연락 목적. 보관 3년.</span>', unsafe_allow_html=True)
        with col_a2:
            marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")
            st.markdown('<span class="consent-note">신규 정책자금/지원사업 알림.</span>', unsafe_allow_html=True)

        submitted = st.form_submit_button("📩 2차 설문 제출", type="primary", disabled=st.session_state.get("saving2", False))

        if submitted and not st.session_state.submitted_2:
            st.session_state.submitted_2 = True

            # 포맷팅
            d_phone = _digits_only(phone_raw)
            formatted_phone = format_phone(d_phone)
            d_biz = _digits_only(biz_no_raw)
            formatted_biz = format_biz_no(d_biz) if d_biz else ""

            # 유효성 검사
            name_ok = bool(name and len(name.strip()) >= 2)
            phone_ok = len(d_phone) == 11 and d_phone.startswith("010")
            biz_ok = len(d_biz) == 0 or len(d_biz) == 10

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
                st.error("1차 접수번호가 필요합니다.")
                st.session_state.submitted_2 = False
            else:
                st.session_state.saving2 = True
                with st.spinner("⏳ 제출 처리 중..."):
                    survey_data = {
                        'name': name,
                        'phone': formatted_phone,
                        'email': email,
                        'biz_reg_no': formatted_biz,
                        'business_name': company,
                        'startup_date': startup_date.strftime('%Y-%m-%d'),
                        'store_type': store_type,
                        'deposit': deposit,
                        'monthly_rent': monthly_rent,
                        'revenue_curr': revenue_curr,
                        'revenue_y1': revenue_y1,
                        'revenue_y2': revenue_y2,
                        'capital_amount': capital,
                        'debt_amount': debt,
                        'guarantee_history': ', '.join(guarantee_history) if guarantee_history else '없음',
                        'research_lab_status': research_lab,
                        'official_certs': ', '.join(certifications) if certifications else '해당없음',
                        'funding_purpose': ', '.join(fund_purpose) if fund_purpose else '미입력',
                        'detailed_funding': detailed_plan,
                        'tax_status': tax_status,
                        'credit_status': credit_status,
                        'business_status': business_status,
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree,
                        'release_version': RELEASE_VERSION,
                        'parent_receipt_no': parent_rid,
                        'magic_token': magic_token,
                        'uuid': uuid_hint or str(uuid4())
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
                            st.info("📞 서버 처리 진행 중. 1영업일 내 연락드립니다.")
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
                        st.markdown(f"<div class='cta-wrap'><a class='cta-kakao' href='{KAKAO_CHAT_URL}' target='_blank'>💬 문의하기</a></div>", unsafe_allow_html=True)
                        st.session_state.submitted_2 = False
                        st.session_state.saving2 = False

if __name__ == "__main__":
    main()