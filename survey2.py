# -*- coding: utf-8 -*-
"""
유아플랜 2차 설문 – Streamlit (v2-2025-11-26-final)
- 기존 레이아웃 유지
- 투명 배경 CSS (다크/라이트 자동 적응)
- 동적 매출 입력 (영업기간 기반)
- GAS 필드 매핑 유지
"""
import os
import time
import re
from datetime import datetime
from uuid import uuid4
import json
import requests
import streamlit as st

# ==========================================
# 1. 설정 및 유틸리티
# ==========================================
class _Config:
    SECOND_GAS_URL = os.getenv("SECOND_GAS_URL", "")
    FIRST_GAS_TOKEN_API_URL = os.getenv("FIRST_GAS_TOKEN_API_URL", "")
    API_TOKEN_STAGE2 = os.getenv("API_TOKEN_2", "youareplan_stage2")

config = _Config()

def _normalize_gas_url(u: str) -> str:
    try:
        s = str(u or "").strip()
    except:
        return u
    if not s: return s
    if s.endswith("/exec") or s.endswith("/dev"): return s
    if "/macros/s/" in s and s.startswith("http"): return s + "/exec"
    return s

def _idemp_key(prefix="c2"):
    return f"{prefix}-{int(time.time()*1000)}-{uuid4().hex[:8]}"

def post_json(url, payload, headers=None, timeout=10, retries=1):
    h = {"Content-Type": "application/json", "X-Idempotency-Key": _idemp_key()}
    if headers: h.update(headers)
    
    for i in range(retries + 1):
        try:
            r = requests.post(url, data=json.dumps(payload), headers=h, timeout=timeout)
            try:
                data = r.json()
            except:
                data = {"ok": False, "status": "error", "text": r.text[:300]}
            
            if 200 <= r.status_code < 300:
                return True, r.status_code, (data if isinstance(data, dict) else {}), None
            
            if r.status_code in (408, 429) and i < retries:
                time.sleep(0.6 * (i + 1))
                continue
            return False, r.status_code, data, f"HTTP {r.status_code}"
        except Exception as e:
            if i < retries:
                time.sleep(0.6 * (i + 1))
                continue
            return False, None, {}, str(e)

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

# ==========================================
# 2. 앱 설정 및 스타일
# ==========================================
st.set_page_config(page_title="유아플랜 심화 진단", page_icon="📝", layout="centered")

RELEASE_VERSION = "v2-2025-11-26-final"
APPS_SCRIPT_URL = _normalize_gas_url(config.SECOND_GAS_URL)
TOKEN_API_URL = _normalize_gas_url(config.FIRST_GAS_TOKEN_API_URL)
API_TOKEN = config.API_TOKEN_STAGE2
KAKAO_CHAT_URL = "https://pf.kakao.com/_LWxexmn/chat"
LOGO_URL = os.getenv("YOUAREPLAN_LOGO_URL") or "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"

# ★ CSS: 투명 배경 (다크/라이트 자동 적응)
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

  /* 컨테이너 */
  .block-container { 
    padding-top: 1rem !important; 
    padding-bottom: 4rem !important; 
    max-width: 800px; 
  }

  /* ===== 브랜드 요소 (고정색) ===== */
  .brandbar { 
    padding: 10px 14px; 
    border-bottom: 1px solid rgba(128,128,128,0.2); 
    display: flex; 
    align-items: center; 
  }
  .brandbar img { height: 40px; }
  
  .gov-topbar { 
    background: #002855 !important; 
    color: #fff !important;
    font-size: 13px; 
    padding: 8px 14px; 
  }
  .gov-topbar * { color: #fff !important; }

  .gov-hero { 
    padding: 20px 0; 
    border-bottom: 1px solid rgba(128,128,128,0.2); 
    margin-bottom: 16px; 
  }
  .gov-hero h2 { 
    color: #002855; 
    font-weight: 700; 
    margin: 0; 
    font-size: 22px; 
  }
  @media (prefers-color-scheme: dark) {
    .gov-hero h2 { color: #60a5fa; }
  }
  .gov-hero p { 
    opacity: 0.7;
    margin-top: 4px; 
    font-size: 14px; 
  }

  /* ===== 입력 필드 - 투명 배경 ===== */
  .stTextInput > div > div > input,
  .stNumberInput > div > div > input,
  .stDateInput > div > div > input,
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

  /* 드롭다운 팝오버 - 투명 대신 반투명 (가독성) */
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
  [data-baseweb="tag"] svg,
  [data-baseweb="tag"] path {
    fill: #fff !important;
  }

  /* Number Input +/- 버튼 */
  .stNumberInput button {
    background: rgba(128,128,128,0.1) !important;
    border: 1px solid rgba(128,128,128,0.3) !important;
    color: inherit !important;
  }
  .stNumberInput button:hover {
    background: rgba(128,128,128,0.2) !important;
  }

  /* 라디오/체크박스 */
  .stRadio label, .stCheckbox label {
    color: inherit !important;
  }

  /* Expander */
  .streamlit-expanderHeader,
  details summary,
  [data-testid="stExpander"] summary {
    background: transparent !important;
    color: inherit !important;
    border: 1px solid rgba(128,128,128,0.2) !important;
    border-radius: 8px !important;
  }

  /* 조건부 박스 */
  .conditional-box { 
    background: rgba(128,128,128,0.05); 
    border: 1px solid rgba(128,128,128,0.2); 
    border-radius: 8px; 
    padding: 12px; 
    margin: 8px 0; 
  }

  /* ===== 제출 버튼 (고정색) ===== */
  div[data-testid="stFormSubmitButton"] button {
    background: #002855 !important; 
    border: none !important; 
    color: #fff !important;
    font-weight: 700 !important; 
    padding: 12px !important; 
    border-radius: 8px !important;
    width: 100%; 
    margin-top: 10px;
  }
  div[data-testid="stFormSubmitButton"] button:hover { 
    opacity: 0.9; 
  }
  div[data-testid="stFormSubmitButton"] button * { 
    color: #fff !important; 
  }

  /* 카카오 버튼 */
  .kakao-btn {
    display: block;
    text-align: center;
    background: #FEE500 !important;
    color: #3c1e1e !important;
    padding: 15px;
    border-radius: 10px;
    text-decoration: none;
    font-weight: bold;
    margin-top: 16px;
  }

  /* 캡션/도움말 */
  div[data-testid="stCaptionContainer"] {
    opacity: 0.7;
  }

  /* ===== Placeholder 연하게 (실제 입력과 구분) ===== */
  ::placeholder {
    color: rgba(128,128,128,0.4) !important;
    opacity: 1 !important;
  }
  input::placeholder,
  textarea::placeholder {
    color: rgba(128,128,128,0.4) !important;
  }
  
  /* 입력 전 상태 더 연하게 */
  input:placeholder-shown,
  textarea:placeholder-shown {
    color: rgba(128,128,128,0.4) !important;
  }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 로직 함수
# ==========================================
def validate_access_token(token, uuid_hint=None):
    if not TOKEN_API_URL:
        return {"ok": False, "message": "API 설정이 필요합니다 (관리자 문의)"}
    
    try:
        payload = {"action": "validate", "token": token, "api_token": "youareplan"}
        if uuid_hint: payload["uuid"] = uuid_hint
        
        ok, sc, data, err = post_json(TOKEN_API_URL, payload)
        
        if sc == 404:
            r = requests.get(TOKEN_API_URL, params=payload, timeout=10)
            if r.status_code == 200: return r.json()
            
        if ok: return data or {"ok": False}
        return {"ok": False, "message": err or "접속 오류"}
    except Exception as e:
        return {"ok": False, "message": str(e)}

def save_survey_data(data):
    if not APPS_SCRIPT_URL:
        return {"status": "error", "message": "SECOND_GAS_URL이 설정되지 않았습니다."}
    
    data['token'] = API_TOKEN
    data['release_version'] = RELEASE_VERSION
    
    ok, sc, resp, err = post_json(APPS_SCRIPT_URL, data, timeout=20)
    
    if ok: return resp or {"status": "success"}
    if sc in (408, 429, 500, 502, 503, 504) or sc is None:
        ok2, sc2, resp2, _ = post_json(APPS_SCRIPT_URL, data, timeout=20)
        if ok2 or (sc2 in (408, 429, 500, 502, 503, 504) or sc2 is None):
            return {"status": "success_delayed", "message": "저장 완료 (서버 지연)"}
            
    return {"status": "error", "message": err}

# ==========================================
# 4. 메인 화면
# ==========================================
def main():
    st.markdown(f'<div class="brandbar"><img src="{LOGO_URL}" alt="Logo"></div>', unsafe_allow_html=True)
    st.markdown('<div class="gov-topbar">대한민국 정부 협력 서비스</div>', unsafe_allow_html=True)
    st.markdown('<div class="gov-hero"><h2>심화 진단 (2차)</h2><p>정확한 한도 산출을 위해 상세 정보를 입력해주세요.</p></div>', unsafe_allow_html=True)

    # 쿼리 파라미터
    qp = st.query_params
    magic_token = qp.get("t")
    uuid_hint = qp.get("u")
    
    if not magic_token:
        st.error("잘못된 접근입니다. 담당자가 보내드린 링크를 다시 확인해주세요.")
        st.markdown(f'<a href="{KAKAO_CHAT_URL}" target="_blank" class="kakao-btn">💬 담당자에게 문의하기</a>', unsafe_allow_html=True)
        return

    v = validate_access_token(magic_token, uuid_hint)

    if not v.get("ok"):
        st.error(f"접속이 제한되었습니다: {v.get('message', '만료된 링크')}")
        st.markdown(f'<a href="{KAKAO_CHAT_URL}" target="_blank" class="kakao-btn">💬 새 링크 요청하기</a>', unsafe_allow_html=True)
        return
        
    parent_rid = v.get("parent_receipt_no", "확인 불가")
    
    # 남은 시간 표시
    remain_min = v.get("remaining_minutes")
    if remain_min is None:
        sec = v.get("remaining_seconds")
        if isinstance(sec, (int, float)):
            remain_min = max(0, int(round(sec / 60)))
    
    if remain_min is not None:
        st.info(f"✅ 접수번호: **{parent_rid}** (인증됨) · 남은 시간: **{int(remain_min)}분**")
    else:
        st.info(f"✅ 접수번호: **{parent_rid}** (인증됨)")

    with st.form("survey_form"):
        # ========== 1. 기본 정보 ==========
        st.markdown("### 1. 기본 정보")
        name = st.text_input("성함 *", placeholder="홍길동").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            phone_raw = st.text_input("연락처 *", placeholder="01012345678 (숫자만)")
        with col2:
            biz_no_raw = st.text_input("사업자번호 (선택)", placeholder="10자리 숫자")

        company_name = st.text_input("상호명 *", placeholder="유아플랜")
        
        # ========== 2. 사업장 정보 ==========
        st.markdown("---")
        st.markdown("### 2. 사업장 정보")
        
        store_type = st.selectbox("점포 형태", ["임차", "자가", "비점포 (온라인/무점포)"])
        
        # 임차인 경우만 보증금/월세 입력
        deposit, monthly_rent = 0, 0
        if store_type == "임차":
            st.markdown('<div class="conditional-box">', unsafe_allow_html=True)
            col_dep, col_rent = st.columns(2)
            with col_dep:
                deposit = st.number_input("보증금 (만원)", min_value=0, step=100, help="예: 3000만원 → 3000")
            with col_rent:
                monthly_rent = st.number_input("월세 (만원)", min_value=0, step=10, help="예: 150만원 → 150")
            st.markdown('</div>', unsafe_allow_html=True)

        # ========== 3. 재무 현황 ==========
        st.markdown("---")
        st.markdown("### 3. 재무 현황")
        st.caption("📅 사업개시일 기준으로 매출 입력칸이 표시됩니다.")
        
        st.write("**사업 개시일**")
        col_y, col_m, col_d = st.columns(3)
        current_year = datetime.now().year
        with col_y:
            start_year = st.selectbox("년", range(current_year, 1989, -1), format_func=lambda x: f"{x}년", index=2)
        with col_m:
            start_month = st.selectbox("월", range(1, 13), format_func=lambda x: f"{x}월")
        with col_d:
            start_day = st.selectbox("일", range(1, 32), format_func=lambda x: f"{x}일")
        
        # 날짜 유효성 검사 및 변환
        import calendar
        max_day = calendar.monthrange(start_year, start_month)[1]
        if start_day > max_day:
            start_day = max_day
        startup_date = datetime(start_year, start_month, start_day)
        
        # 영업 기간 계산 (월 단위)
        today = datetime.now()
        months_operating = (today.year - startup_date.year) * 12 + (today.month - startup_date.month)
        current_year = today.year
        
        st.write("📊 **부가세 과세표준 증명원 상 매출액** (단위: 만원)")
        st.caption("예: 1억 5천만원 → 15000 입력")
        
        # 동적 매출 입력
        rev_current, rev_y1, rev_y2 = 0, 0, 0
        
        if months_operating < 6:
            # 6개월 미만: 올해 예상만
            st.info("💡 사업 초기(6개월 미만)입니다. 올해 예상 매출만 입력하세요.")
            rev_current = st.number_input(f"{current_year}년 (예상)", min_value=0, step=100)
            
        elif months_operating < 18:
            # 6개월~18개월: 올해 + 작년(있으면)
            col_rev1, col_rev2 = st.columns(2)
            with col_rev1:
                rev_current = st.number_input(f"{current_year}년 (예상)", min_value=0, step=100)
            with col_rev2:
                if startup_date.year < current_year:
                    rev_y1 = st.number_input(f"{current_year-1}년 (확정)", min_value=0, step=100)
                else:
                    st.caption(f"{current_year-1}년: 해당 없음")
        else:
            # 18개월 이상: 3년치
            col_rev1, col_rev2, col_rev3 = st.columns(3)
            with col_rev1:
                rev_current = st.number_input(f"{current_year}년 (예상)", min_value=0, step=100)
            with col_rev2:
                rev_y1 = st.number_input(f"{current_year-1}년 (확정)", min_value=0, step=100)
            with col_rev3:
                rev_y2 = st.number_input(f"{current_year-2}년 (확정)", min_value=0, step=100)

        st.markdown("")
        col_fin1, col_fin2 = st.columns(2)
        with col_fin1:
            capital = st.number_input("자본금 (만원)", min_value=0, step=100, help="법인: 등기부등본상 자본금")
        with col_fin2:
            debt = st.number_input("부채 총계 (만원)", min_value=0, step=100, help="금융권 대출 합계")

        # ========== 4. 보증 이용 경험 ==========
        st.markdown("---")
        st.markdown("### 4. 보증 이용 경험")
        
        guarantee_history = st.multiselect(
            "기존에 이용한 보증기관 (중복 선택 가능)",
            ["신용보증기금", "기술보증기금", "지역신용보증재단", "소상공인시장진흥공단", "이용 경험 없음"],
            default=["이용 경험 없음"],
            help="현재 이용 중이거나 과거에 이용한 기관 모두 선택"
        )

        # ========== 5. 기술 및 우대 사항 ==========
        st.markdown("---")
        st.markdown("### 5. 기술 및 우대 사항")
        
        research_lab = st.radio(
            "기업부설연구소 보유", 
            ["미보유", "연구소 보유", "전담부서 보유"], 
            horizontal=True
        )
            
        certs = st.multiselect(
            "보유 인증 (중복 선택)", 
            ["벤처기업", "이노비즈", "메인비즈", "ISO인증", "특허/실용신안", "여성기업", "뿌리기업"],
            placeholder="없으면 비워두세요"
        )
            
        fund_purpose = st.multiselect(
            "신청 자금 용도", 
            ["운전자금 (인건비/재료비)", "시설자금 (기계/건축)", "대환자금"], 
            default=["운전자금 (인건비/재료비)"]
        )
        
        # ========== 6. 자가 진단 ==========
        st.markdown("---")
        st.markdown("### 6. 자가 진단")
        
        has_tax_issue = st.checkbox("현재 국세/지방세 체납 중입니까?", value=False)
        has_overdue = st.checkbox("최근 3개월 내 대출금 연체 사실이 있습니까?", value=False)
        
        # ========== 7. 동의 ==========
        st.markdown("---")
        agree_privacy = st.checkbox("개인정보 수집 및 이용에 동의합니다. (필수)")
        with st.expander("동의 내용 보기"):
            st.markdown("""
**수집 목적**: 정책자금 상담 및 한도 심사  
**수집 항목**: 성함, 연락처, 사업자정보, 재무정보  
**보유 기간**: 상담 완료 후 3년
            """)
            
        submitted = st.form_submit_button("입력 완료 및 제출")

        if submitted:
            # 유효성 검사
            clean_phone = _digits_only(phone_raw)
            clean_biz = _digits_only(biz_no_raw)
            
            if not name or len(name) < 2:
                st.error("성함을 2자 이상 입력해주세요.")
                return
            if len(clean_phone) != 11 or not clean_phone.startswith("010"):
                st.error("연락처를 정확히 입력해주세요 (010으로 시작하는 11자리).")
                return
            if clean_biz and len(clean_biz) != 10:
                st.error("사업자번호는 10자리이거나 비워두세요.")
                return
            if not agree_privacy:
                st.error("개인정보 동의가 필요합니다.")
                return

            # 페이로드 구성 (GAS 필드명 매핑)
            payload = {
                "uuid": uuid_hint or str(uuid4()),
                "parent_receipt_no": parent_rid,
                "magic_token": magic_token,
                "name": name,
                "phone": format_phone_from_digits(clean_phone),
                "biz_no": format_biz_no(clean_biz) if clean_biz else "",
                "company_name": company_name,
                "store_type": store_type,
                "deposit": deposit,
                "monthly_rent": monthly_rent,
                "startup_date": startup_date.strftime("%Y-%m-%d"),
                "revenue_current": rev_current,
                "revenue_y1": rev_y1,
                "revenue_y2": rev_y2,
                "capital": capital,
                "debt": debt,
                "guarantee_history": ", ".join(guarantee_history) if guarantee_history else "이용 경험 없음",
                "research_lab": research_lab,
                "certifications": ", ".join(certs) if certs else "해당 없음",
                "fund_purpose": ", ".join(fund_purpose) if fund_purpose else "미입력",
                "risk_tax": has_tax_issue,
                "risk_overdue": has_overdue,
            }
            
            with st.spinner("저장 중입니다..."):
                res = save_survey_data(payload)
                
                if res.get("status") in ["success", "success_delayed"]:
                    st.success("✅ 제출이 완료되었습니다!")
                    st.info("담당자가 내용을 검토 후 1영업일 내로 연락드립니다.")
                    st.markdown(f'<a href="{KAKAO_CHAT_URL}" target="_blank" class="kakao-btn">💬 담당자에게 카톡 보내기</a>', unsafe_allow_html=True)
                    st.stop()
                else:
                    st.error(f"제출 중 오류가 발생했습니다: {res.get('message', '알 수 없는 오류')}")
                    st.markdown(f'<a href="{KAKAO_CHAT_URL}" target="_blank" class="kakao-btn">💬 담당자에게 문의하기</a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()