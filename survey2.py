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
# 2. 앱 설정
# ==========================================
st.set_page_config(page_title="유아플랜 심화 진단", page_icon="📝", layout="centered")

RELEASE_VERSION = "v2-2025-11-26-fixed-v3"
APPS_SCRIPT_URL = _normalize_gas_url(config.SECOND_GAS_URL)
TOKEN_API_URL = _normalize_gas_url(config.FIRST_GAS_TOKEN_API_URL)
API_TOKEN = config.API_TOKEN_STAGE2
KAKAO_CHAT_URL = "https://pf.kakao.com/_LWxexmn/chat"

# ==========================================
# 3. CSS (완전 수정)
# ==========================================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  
  /* ===== 기본 설정 ===== */
  :root { color-scheme: light !important; }
  
  html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Noto Sans KR', sans-serif !important;
    background-color: #ffffff !important;
    color: #0F172A !important;
  }

  /* ===== 모든 텍스트 색상 ===== */
  h1, h2, h3, h4, h5, h6, p, span, div, label,
  .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown div,
  .stText, [data-testid="stText"],
  [data-testid="stHeading"], [data-testid="stMarkdownContainer"],
  [data-testid="stMarkdownContainer"] p,
  .stSelectbox label, .stTextInput label, .stNumberInput label,
  .stRadio label, .stCheckbox label, .stMultiSelect label,
  .stDateInput label, .stTextArea label {
    color: #0F172A !important;
  }
  
  /* 라디오/체크박스 텍스트 */
  .stRadio label span, .stCheckbox label span,
  .stRadio div[role="radiogroup"] label,
  .stCheckbox div label,
  [data-testid="stCheckbox"] span,
  [data-testid="stRadio"] span,
  [data-baseweb="radio"] + div,
  [data-baseweb="checkbox"] + div {
    color: #0F172A !important;
  }

  /* ===== 입력 필드 ===== */
  .stTextInput input, .stDateInput input, .stTextArea textarea {
    background-color: #ffffff !important;
    color: #0F172A !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
  }
  
  .stNumberInput input {
    background-color: #ffffff !important;
    color: #0F172A !important;
    border: 1px solid #cbd5e1 !important;
  }
  
  .stNumberInput button, [data-testid="stNumberInput"] button {
    background-color: #f1f5f9 !important;
    border: 1px solid #cbd5e1 !important;
    color: #334155 !important;
  }
  .stNumberInput button:hover {
    background-color: #e2e8f0 !important;
  }

  /* ===== SelectBox/MultiSelect 컨테이너 ===== */
  [data-baseweb="select"],
  [data-baseweb="select"] > div:first-child,
  .stSelectbox > div > div,
  .stMultiSelect > div > div {
    background-color: #ffffff !important;
    border-color: #cbd5e1 !important;
  }
  
  /* SelectBox/MultiSelect 내부 입력 영역 */
  [data-baseweb="select"] > div > div,
  [data-baseweb="select"] input,
  .stSelectbox [data-baseweb="select"] > div,
  .stMultiSelect [data-baseweb="select"] > div {
    background-color: #ffffff !important;
    color: #0F172A !important;
  }

  /* ===== 핵심: 선택된 태그 (파란 배경 강제) ===== */
  [data-baseweb="tag"],
  .stMultiSelect [data-baseweb="tag"],
  div[data-baseweb="tag"],
  span[data-baseweb="tag"] {
    background-color: #2563eb !important;
    background: #2563eb !important;
    border: none !important;
    border-radius: 4px !important;
  }
  
  /* 태그 내부 텍스트 (흰색 강제) */
  [data-baseweb="tag"] span,
  [data-baseweb="tag"] > span,
  [data-baseweb="tag"] div,
  [data-baseweb="tag"] *:not(svg):not(path) {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
  }
  
  /* 태그 X 버튼 */
  [data-baseweb="tag"] svg,
  [data-baseweb="tag"] path {
    fill: #ffffff !important;
    color: #ffffff !important;
  }

  /* ===== 드롭다운 (팝오버) ===== */
  div[data-baseweb="popover"],
  div[data-baseweb="popover"] > div,
  div[data-baseweb="popover"] ul,
  div[data-baseweb="menu"],
  div[data-baseweb="menu"] ul,
  div[role="listbox"],
  ul[role="listbox"] {
    background-color: #ffffff !important;
    background: #ffffff !important;
  }
  
  /* 드롭다운 옵션 */
  li[role="option"],
  div[role="option"],
  [data-baseweb="menu"] li {
    background-color: #ffffff !important;
    color: #0F172A !important;
  }
  
  li[role="option"]:hover,
  div[role="option"]:hover,
  [data-baseweb="menu"] li:hover {
    background-color: #f1f5f9 !important;
  }
  
  /* Clear 버튼 (X) */
  [data-baseweb="select"] > div > div:last-child svg {
    fill: #64748b !important;
  }

  /* ===== Expander 완전 수정 ===== */
  .streamlit-expanderHeader,
  [data-testid="stExpander"] summary,
  [data-testid="stExpander"] > div:first-child,
  details summary,
  details > summary {
    background-color: #f8fafc !important;
    background: #f8fafc !important;
    color: #0F172A !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
  }
  
  .streamlit-expanderHeader span,
  .streamlit-expanderHeader p,
  .streamlit-expanderHeader div,
  [data-testid="stExpander"] summary span,
  [data-testid="stExpander"] summary p,
  details summary span {
    color: #0F172A !important;
  }
  
  .streamlit-expanderHeader svg,
  [data-testid="stExpander"] summary svg,
  details summary svg {
    fill: #0F172A !important;
    color: #0F172A !important;
  }
  
  .streamlit-expanderContent,
  [data-testid="stExpander"] > div:last-child,
  details > div {
    background-color: #ffffff !important;
    background: #ffffff !important;
    color: #0F172A !important;
    border: 1px solid #e2e8f0 !important;
    border-top: none !important;
  }
  
  .streamlit-expanderContent p,
  .streamlit-expanderContent span,
  .streamlit-expanderContent div,
  [data-testid="stExpander"] > div:last-child p {
    color: #0F172A !important;
  }

  /* ===== 헤더/브랜드 ===== */
  .brandbar { 
    padding: 10px 14px; 
    border-bottom: 1px solid #e5e7eb; 
    background: #ffffff;
    display: flex;
    align-items: center;
  }
  .brandbar img { height: 40px; }
  
  .gov-topbar { 
    background: #002855; 
    color: #fff !important; 
    font-size: 13px; 
    padding: 8px 14px; 
  }
  .gov-topbar * { color: #fff !important; }
  
  .gov-hero { 
    padding: 20px 0; 
    border-bottom: 1px solid #e5e7eb; 
    margin-bottom: 16px; 
    background: #ffffff; 
  }
  .gov-hero h2 { 
    color: #002855 !important; 
    font-weight: 700; 
    margin: 0; 
    font-size: 22px;
  }
  .gov-hero p { 
    color: #4b5563 !important; 
    margin-top: 4px; 
    font-size: 14px;
  }

  /* ===== 버튼 ===== */
  div[data-testid="stFormSubmitButton"] button {
    background: #002855 !important; 
    border: none !important; 
    color: #ffffff !important;
    font-weight: 700 !important; 
    padding: 12px !important; 
    border-radius: 8px !important;
    width: 100%;
    margin-top: 10px;
  }
  div[data-testid="stFormSubmitButton"] button:hover {
    opacity: 0.9;
  }
  div[data-testid="stFormSubmitButton"] button span,
  div[data-testid="stFormSubmitButton"] button p,
  div[data-testid="stFormSubmitButton"] button * {
    color: #ffffff !important;
  }

  /* ===== 기타 ===== */
  .block-container { 
    padding-top: 1rem !important; 
    padding-bottom: 4rem !important;
    max-width: 800px; 
  }
  
  .stCaption, div[data-testid="stCaptionContainer"], small {
    color: #64748b !important;
  }
  
  /* Info/Success/Error 박스 */
  .stAlert, [data-testid="stAlert"] {
    color: #0F172A !important;
  }
  .stAlert p, [data-testid="stAlert"] p {
    color: inherit !important;
  }
  
  /* 숨김 */
  #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { 
    display: none !important; 
  }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 로직 함수
# ==========================================
def validate_access_token(token, uuid_hint=None):
    try:
        if not TOKEN_API_URL:
            return {"ok": False, "message": "토큰 검증 API가 설정되지 않았습니다."}
            
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
        return {"status": "error", "message": "저장 API가 설정되지 않았습니다."}
    
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
# 5. 메인 화면
# ==========================================
def main():
    logo_url = os.getenv("YOUAREPLAN_LOGO_URL") or "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"
    st.markdown(f'<div class="brandbar"><img src="{logo_url}" alt="Logo"></div>', unsafe_allow_html=True)
    st.markdown('<div class="gov-topbar">대한민국 정부 협력 서비스</div>', unsafe_allow_html=True)
    st.markdown('<div class="gov-hero"><h2>심화 진단 (2차)</h2><p>정확한 한도 산출을 위해 상세 정보를 입력해주세요.</p></div>', unsafe_allow_html=True)

    qp = st.query_params
    magic_token = qp.get("t")
    uuid_hint = qp.get("u")
    
    if not magic_token:
        st.error("잘못된 접근입니다. 담당자가 보내드린 링크를 다시 확인해주세요.")
        return

    v = validate_access_token(magic_token, uuid_hint)

    if not v.get("ok"):
        st.error(f"접속이 제한되었습니다: {v.get('message', '만료된 링크')}")
        return
        
    parent_rid = v.get("parent_receipt_no", "확인 불가")
    st.info(f"✅ 접수번호: **{parent_rid}** (인증됨)")

    with st.form("survey_form"):
        # 1. 기본 정보
        st.markdown("### 1. 기본 정보")
        name = st.text_input("성함", placeholder="홍길동").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            phone_raw = st.text_input("연락처", placeholder="01012345678 (숫자만)")
        with col2:
            biz_no_raw = st.text_input("사업자번호 (선택)", placeholder="10자리 숫자")

        company_name = st.text_input("상호명", placeholder="유아플랜")
        
        # 2. 사업장 정보
        st.markdown("---")
        st.markdown("### 2. 사업장 정보")
        
        store_type = st.selectbox("점포 형태", ["임차", "자가", "비점포 (온라인/무점포)"])
        
        deposit, monthly_rent = 0, 0
        if store_type == "임차":
            col_dep, col_rent = st.columns(2)
            with col_dep:
                deposit = st.number_input("보증금 (만원)", min_value=0, step=100)
            with col_rent:
                monthly_rent = st.number_input("월세 (만원)", min_value=0, step=10)

        # 3. 재무 현황
        st.markdown("---")
        st.markdown("### 3. 재무 현황")
        st.caption("📅 사업개시일 기준으로 매출 입력칸이 표시됩니다.")
        
        startup_date = st.date_input("사업 개시일", min_value=datetime(1950, 1, 1), value=datetime(2023, 1, 1))
        
        years_operating = datetime.now().year - startup_date.year
        current_year = datetime.now().year
        
        st.write("📊 **부가세 과세표준 증명원 상 매출액** (단위: 만원)")
        st.caption("예: 1억 5천만원 → 15000 입력")
        
        col_rev1, col_rev2, col_rev3 = st.columns(3)
        
        with col_rev1:
            rev_current = st.number_input(f"{current_year}년 (예상)", min_value=0, step=100)
            
        rev_y1, rev_y2 = 0, 0
        
        if years_operating >= 1:
            with col_rev2:
                rev_y1 = st.number_input(f"{current_year-1}년 (확정)", min_value=0, step=100)
        
        if years_operating >= 2:
            with col_rev3:
                rev_y2 = st.number_input(f"{current_year-2}년 (확정)", min_value=0, step=100)

        st.markdown("")
        col_fin1, col_fin2 = st.columns(2)
        with col_fin1:
            capital = st.number_input("자본금 (만원)", min_value=0, step=100)
        with col_fin2:
            debt = st.number_input("부채 총계 (만원)", min_value=0, step=100)

        # 4. 보증 이용 경험
        st.markdown("---")
        st.markdown("### 4. 보증 이용 경험")
        
        guarantee_history = st.multiselect(
            "기존에 이용한 보증기관 (중복 선택 가능)",
            ["신용보증기금", "기술보증기금", "지역신용보증재단", "소상공인시장진흥공단", "이용 경험 없음"],
            default=["이용 경험 없음"]
        )

        # 5. 기술 및 우대 사항
        st.markdown("---")
        st.markdown("### 5. 기술 및 우대 사항")
        
        research_lab = st.radio("기업부설연구소 보유", 
            ["미보유", "연구소 보유", "전담부서 보유"], horizontal=True)
            
        certs = st.multiselect("보유 인증 (중복 선택)", 
            ["벤처기업", "이노비즈", "메인비즈", "ISO인증", "특허/실용신안", "여성기업", "뿌리기업"],
            placeholder="없으면 비워두세요")
            
        fund_purpose = st.multiselect("신청 자금 용도", 
            ["운전자금 (인건비/재료비)", "시설자금 (기계/건축)", "대환자금"], 
            default=["운전자금 (인건비/재료비)"])
        
        # 6. 자가 진단
        st.markdown("---")
        st.markdown("### 6. 자가 진단")
        
        has_tax_issue = st.checkbox("현재 국세/지방세 체납 중입니까?", value=False)
        has_overdue = st.checkbox("최근 3개월 내 대출금 연체 사실이 있습니까?", value=False)
        
        # 7. 동의
        st.markdown("---")
        agree_privacy = st.checkbox("개인정보 수집 및 이용에 동의합니다. (필수)")
        with st.expander("동의 내용 보기"):
            st.markdown("""
            **수집목적**: 정책자금 상담 및 한도 심사  
            **보유기간**: 3년  
            **수집항목**: 성함, 연락처, 사업자정보, 재무정보
            """)
            
        submitted = st.form_submit_button("입력 완료 및 제출")

        if submitted:
            clean_phone = _digits_only(phone_raw)
            clean_biz = _digits_only(biz_no_raw)
            
            if len(clean_phone) != 11 or not clean_phone.startswith("010"):
                st.error("연락처를 정확히 입력해주세요 (010으로 시작하는 11자리).")
                return
            if not name:
                st.error("성함을 입력해주세요.")
                return
            if not agree_privacy:
                st.error("개인정보 동의가 필요합니다.")
                return

            payload = {
                "uuid": uuid_hint or str(uuid4()),
                "parent_receipt_no": parent_rid,
                "name": name,
                "phone": format_phone_from_digits(clean_phone),
                "biz_no": format_biz_no(clean_biz),
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
                "guarantee_history": ", ".join(guarantee_history),
                "research_lab": research_lab,
                "certifications": ", ".join(certs),
                "fund_purpose": ", ".join(fund_purpose),
                "risk_tax": has_tax_issue,
                "risk_overdue": has_overdue,
                "magic_token": magic_token
            }
            
            with st.spinner("저장 중입니다..."):
                res = save_survey_data(payload)
                
                if res.get("status") in ["success", "success_delayed"]:
                    st.success("✅ 제출이 완료되었습니다!")
                    st.info("담당자가 내용을 검토 후 1영업일 내로 연락드립니다.")
                    st.markdown(f"""
                    <br>
                    <a href='{KAKAO_CHAT_URL}' target='_blank' 
                       style='display:block;text-align:center;background:#FEE500;
                              padding:15px;border-radius:10px;text-decoration:none;
                              color:#3c1e1e;font-weight:bold;'>
                        💬 담당자에게 카톡 보내기
                    </a>
                    """, unsafe_allow_html=True)
                    st.stop()
                else:
                    st.error(f"제출 중 오류가 발생했습니다: {res.get('message', '알 수 없는 오류')}")

if __name__ == "__main__":
    main()