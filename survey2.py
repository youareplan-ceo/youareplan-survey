"""
유아플랜 정책자금 2차 심화진단
v2025-12-09-final
- GAS 필드명 완전 동기화
- CSS 스타일 1차와 통일 (다크/라이트 모드 대응)
- [추가] 정책자금 수혜이력 섹션 (중복지원 심사용)
"""

import streamlit as st
import requests
import re
import os
import json
import time
from datetime import datetime
import calendar
from uuid import uuid4

st.set_page_config(
    page_title="유아플랜 정책자금 2차 심화진단",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
RELEASE_VERSION = "v2025-12-09-final"

SECOND_GAS_URL = os.getenv("SECOND_GAS_URL", "https://script.google.com/macros/s/YOUR_GAS_ID/exec")
FIRST_GAS_TOKEN_API_URL = os.getenv("FIRST_GAS_TOKEN_API_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN_2", "youareplan_stage2")
KAKAO_CHANNEL_URL = "https://pf.kakao.com/_LWxexmn"

# ==============================
# 선택지 정의 (GAS 컬럼 기준)
# ==============================
STORE_TYPES = ["자가", "임차", "무점포", "기타"]
GUARANTEE_OPTIONS = ["이용 경험 없음", "신용보증기금", "기술보증기금", "지역신용보증재단", "기타"]
CERT_OPTIONS = ["벤처기업", "이노비즈", "메인비즈", "ISO인증", "해당 없음"]
RESEARCH_OPTIONS = ["기업부설연구소", "연구개발전담부서", "미보유"]
FUND_PURPOSE_OPTIONS = ["운전자금", "시설자금", "R&D 자금", "기타"]

# [추가] 정책자금 수혜이력 옵션
PAST_POLICY_OPTIONS = [
    "해당 없음 (처음 신청)",
    "소상공인정책자금 (소진공)",
    "중소기업정책자금 (중진공)",
    "신용보증기금/기술보증기금",
    "지역신용보증재단",
    "지자체 융자/보조금",
    "창업지원 (창업사관학교 등)",
    "R&D 과제 (정부연구개발)",
    "기타 정책자금"
]

# ==============================
# 유틸리티 함수
# ==============================
def _digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")

def format_phone(d: str) -> str:
    return f"{d[0:3]}-{d[3:7]}-{d[7:11]}" if len(d) == 11 else d

def format_biz_no(d: str) -> str:
    return f"{d[0:3]}-{d[3:5]}-{d[5:10]}" if len(d) == 10 else d

def _idempotency_key():
    return f"c2-{int(time.time()*1000)}-{uuid4().hex[:8]}"

def post_json(url, payload, timeout=30):
    """JSON POST 요청"""
    headers = {
        "Content-Type": "application/json",
        "X-Idempotency-Key": _idempotency_key()
    }
    try:
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return True, resp.json()
        return False, {"message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return False, {"message": str(e)}

def validate_access_token(token: str, uuid_hint: str = None) -> dict:
    """1차 GAS에서 토큰 검증"""
    if "YOUR_GAS_ID" in SECOND_GAS_URL:
        return {"ok": True, "parent_receipt_no": "TEST-1234"}
    
    payload = {"action": "validate", "token": token, "api_token": "youareplan"}
    if uuid_hint:
        payload["uuid"] = uuid_hint
    
    ok, resp = post_json(FIRST_GAS_TOKEN_API_URL, payload)
    if ok:
        return resp
    return {"ok": False, "message": resp.get("message", "검증 실패")}

def save_to_google_sheet(data: dict) -> dict:
    """2차 GAS로 데이터 전송"""
    data['token'] = API_TOKEN
    ok, resp = post_json(SECOND_GAS_URL, data, timeout=45)
    if ok:
        return resp
    return {"status": "error", "message": resp.get("message", "전송 실패")}

# ==============================
# 스타일링 (1차와 통일 - 다크/라이트 모드 대응)
# ==============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
#MainMenu, footer, header { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; max-width: 700px !important; }

.unified-header { 
    background: #002855; 
    padding: 24px 20px; 
    text-align: center; 
    border-radius: 12px; 
    margin-bottom: 24px; 
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); 
}
.unified-header img { height: 48px; margin-bottom: 12px; object-fit: contain; }
.unified-header .gov-label { color: rgba(255, 255, 255, 0.85); font-size: 13px; font-weight: 500; }

.section-header { 
    font-size: 16px; 
    font-weight: 700; 
    margin-top: 20px; 
    margin-bottom: 10px; 
    border-bottom: 2px solid rgba(128, 128, 128, 0.2); 
    padding-bottom: 6px; 
}

div[data-testid="stFormSubmitButton"] button { 
    background: #002855 !important; 
    color: white !important; 
    border: none !important; 
    padding: 14px 24px !important; 
    border-radius: 8px !important; 
    font-weight: 700 !important; 
    width: 100%; 
    margin-top: 10px; 
}

.success-box {
    padding: 20px; 
    border-radius: 10px; 
    background-color: rgba(0,40,85,0.05); 
    border: 1px solid rgba(0,40,85,0.1); 
    margin: 20px 0; 
    text-align: center;
}
.success-box h3 { margin: 0; color: #002855; font-size: 24px; }
.success-box p { margin-top: 10px; margin-bottom: 0; color: #555; }
</style>
""", unsafe_allow_html=True)

# ==============================
# 메인 함수
# ==============================
def main():
    if "submitted_2" not in st.session_state:
        st.session_state.submitted_2 = False

    # 헤더
    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <div class="gov-label">2차 심화 정밀 진단</div>
    </div>
    """, unsafe_allow_html=True)

    # 제출 완료 화면
    if st.session_state.submitted_2:
        st.success("✅ 심화 진단이 성공적으로 접수되었습니다.")
        st.balloons()
        st.markdown(f"""
        <div class="success-box">
            <h3>접수가 완료되었습니다</h3>
            <p>전문 위원이 제출해주신 데이터를 정밀 분석 후,<br><strong>3일 이내</strong>에 상세 리포트를 안내해 드립니다.</p>
        </div>
        <div style="text-align: center; margin-top: 20px;">
            <a href="{KAKAO_CHANNEL_URL}" target="_blank" 
               style="display:inline-block; background:#FEE500; color:#3C1E1E; 
                      padding:12px 25px; border-radius:8px; text-decoration:none; font-weight:bold;">
                💬 카카오톡 문의하기
            </a>
        </div>
        """, unsafe_allow_html=True)
        return

    # URL 파라미터
    try:
        qp = st.query_params
        magic_token = qp.get("t")
        uuid_hint = qp.get("u")
        pre_receipt_no = qp.get("r")
    except:
        magic_token, uuid_hint, pre_receipt_no = None, None, None

    parent_rid = ""
    validated_uuid = ""

    # 접근 검증
    if pre_receipt_no:
        parent_rid = pre_receipt_no
        st.info(f"⚡ [직원/관리자 모드] 1차 접수번호({parent_rid})가 자동 연결되었습니다.")
    elif magic_token:
        v_result = validate_access_token(magic_token, uuid_hint)
        if not v_result.get("ok"):
            st.error(f"❌ 접속이 만료되었거나 유효하지 않습니다: {v_result.get('message')}")
            return
        parent_rid = v_result.get("parent_receipt_no", "")
        validated_uuid = v_result.get("uuid", uuid_hint or "")
        st.caption(f"✅ 인증됨 (1차 접수번호: {parent_rid})")
    else:
        parent_rid = "TEST-MODE"
        st.warning("⚠️ 테스트 모드로 실행 중입니다.")

    # 설문 폼
    with st.form("survey2_form"):
        
        # ========== 섹션 1: 기본 정보 ==========
        st.markdown('<div class="section-header">👤 기본 정보 확인</div>', unsafe_allow_html=True)
        
        name = st.text_input("대표자 성함 *", placeholder="홍길동")
        st.text_input("1차 접수번호", value=parent_rid, disabled=True)
        phone_raw = st.text_input("연락처 *", placeholder="01012345678")
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")

        # ========== 섹션 2: 사업자 정보 ==========
        st.markdown('<div class="section-header">🏢 사업자 정보</div>', unsafe_allow_html=True)
        
        col_name, col_bizno = st.columns(2)
        with col_name:
            company_name = st.text_input("상호명 *", placeholder="(주)유아플랜")
        with col_bizno:
            biz_no_raw = st.text_input("사업자등록번호", placeholder="10자리 숫자")

        # 개업일
        st.markdown("**개업 연월일**")
        this_year = datetime.now().year
        d_c1, d_c2, d_c3 = st.columns([1.4, 1, 1])
        with d_c1:
            s_year = st.selectbox("년", range(this_year, 1989, -1), key="s_year", label_visibility="collapsed", format_func=lambda x: f"{x}년")
        with d_c2:
            s_month = st.selectbox("월", range(1, 13), key="s_month", label_visibility="collapsed", format_func=lambda x: f"{x}월")
        with d_c3:
            s_day = st.selectbox("일", range(1, 32), key="s_day", label_visibility="collapsed", format_func=lambda x: f"{x}일")
        
        try:
            startup_date = datetime(s_year, s_month, s_day).date()
        except ValueError:
            last_day = calendar.monthrange(s_year, s_month)[1]
            startup_date = datetime(s_year, s_month, last_day).date()

        # ========== 섹션 3: 점포 현황 ==========
        st.markdown('<div class="section-header">🏠 점포 현황</div>', unsafe_allow_html=True)
        
        col_store, col_deposit, col_rent = st.columns(3)
        with col_store:
            store_type = st.selectbox("점포 형태", STORE_TYPES)
        with col_deposit:
            deposit = st.text_input("보증금 (만원)", placeholder="0")
        with col_rent:
            monthly_rent = st.text_input("월세 (만원)", placeholder="0")

        # ========== 섹션 4: 재무 현황 ==========
        st.markdown('<div class="section-header">💰 재무 현황</div>', unsafe_allow_html=True)
        
        st.markdown("**최근 3년 연매출 (단위: 만원)**")
        current_year = datetime.now().year
        c1, c2, c3 = st.columns(3)
        with c1:
            revenue_current = st.text_input(f"{current_year}년 (예상)", placeholder="0")
        with c2:
            revenue_y1 = st.text_input(f"{current_year-1}년", placeholder="0")
        with c3:
            revenue_y2 = st.text_input(f"{current_year-2}년", placeholder="0")

        col_cap, col_debt = st.columns(2)
        with col_cap:
            capital = st.text_input("자본금 (만원)", placeholder="0")
        with col_debt:
            debt = st.text_input("현재 부채 (만원)", placeholder="0")

        # ========== 섹션 5: 보증/인증 현황 ==========
        st.markdown('<div class="section-header">📜 보증 및 인증 현황</div>', unsafe_allow_html=True)
        
        guarantee_history = st.selectbox("보증 이용 경험", GUARANTEE_OPTIONS)
        certifications = st.multiselect("보유 인증", CERT_OPTIONS)
        research_lab = st.selectbox("연구조직 보유", RESEARCH_OPTIONS)

        # ========== [추가] 섹션 6: 정책자금 이력 ==========
        st.markdown('<div class="section-header">📋 정책자금 이력</div>', unsafe_allow_html=True)
        st.caption("최근 5년 내 정책자금 수혜 경험을 선택해주세요. (중복지원 심사에 활용)")
        
        past_policy_fund = st.multiselect(
            "기존 정책자금 수혜 경험",
            PAST_POLICY_OPTIONS,
            default=["해당 없음 (처음 신청)"],
            help="중복지원 제한 여부 확인 및 적합 자금 매칭에 활용됩니다."
        )

        # ========== 섹션 7: 자금 계획 ==========
        st.markdown('<div class="section-header">💼 자금 활용 계획</div>', unsafe_allow_html=True)
        
        fund_purpose = st.multiselect("주요 용도", FUND_PURPOSE_OPTIONS)
        detailed_funding = st.text_area("구체적인 활용 계획", placeholder="예: 신규 장비 도입 1억, 운전자금 5천만원 등")

        # ========== 섹션 8: 리스크 자가진단 ==========
        st.markdown('<div class="section-header">🚨 리스크 자가진단</div>', unsafe_allow_html=True)
        
        col_tax, col_credit = st.columns(2)
        with col_tax:
            risk_tax = st.checkbox("국세/지방세 체납 있음")
        with col_credit:
            risk_overdue = st.checkbox("금융 연체 이력 있음")

        # ========== 동의 ==========
        st.markdown("---")
        
        col_p, col_m = st.columns(2)
        with col_p:
            privacy_agree = st.checkbox("개인정보 수집·이용 동의 (필수)", value=True)
        with col_m:
            marketing_agree = st.checkbox("마케팅 수신 동의 (선택)")

        st.write("")
        submitted = st.form_submit_button("📩 정밀 진단 제출하기")

        if submitted:
            phone_digits = _digits_only(phone_raw)
            
            # 유효성 검사
            if not name.strip():
                st.warning("⚠️ 대표자 성함을 입력해주세요.")
            elif len(phone_digits) < 10:
                st.warning("⚠️ 연락처를 확인해주세요.")
            elif not company_name.strip():
                st.warning("⚠️ 상호명을 입력해주세요.")
            elif not privacy_agree:
                st.error("⚠️ 필수 동의 항목을 체크해주세요.")
            else:
                with st.spinner("접수 중입니다... 잠시만 기다려주세요."):
                    
                    # GAS 필드명에 맞춘 데이터
                    survey_data = {
                        # 기본 정보
                        'name': name.strip(),
                        'phone': format_phone(phone_digits),
                        'email': email.strip() if email else '',
                        
                        # 사업자 정보 (GAS 필드명)
                        'company_name': company_name.strip(),
                        'biz_no': format_biz_no(_digits_only(biz_no_raw)),
                        'startup_date': startup_date.strftime('%Y-%m-%d'),
                        
                        # 점포 현황 (GAS 필드명)
                        'store_type': store_type,
                        'deposit': deposit.strip() if deposit else '0',
                        'monthly_rent': monthly_rent.strip() if monthly_rent else '0',
                        
                        # 재무 현황 (GAS 필드명)
                        'revenue_current': revenue_current.strip() if revenue_current else '0',
                        'revenue_y1': revenue_y1.strip() if revenue_y1 else '0',
                        'revenue_y2': revenue_y2.strip() if revenue_y2 else '0',
                        'capital': capital.strip() if capital else '0',
                        'debt': debt.strip() if debt else '0',
                        
                        # 보증/인증 (GAS 필드명)
                        'guarantee_history': guarantee_history,
                        'certifications': ', '.join(certifications) if certifications else '해당 없음',
                        'research_lab': research_lab,
                        
                        # [추가] 정책자금 이력
                        'past_policy_fund': ', '.join(past_policy_fund) if past_policy_fund else '해당 없음',
                        
                        # 자금 계획 (GAS 필드명)
                        'fund_purpose': ', '.join(fund_purpose) if fund_purpose else '미입력',
                        'detailed_funding': detailed_funding.strip() if detailed_funding else '',
                        
                        # 리스크 (GAS 필드명)
                        'risk_tax': risk_tax,
                        'risk_overdue': risk_overdue,
                        
                        # 동의
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree,
                        
                        # 메타 정보
                        'parent_receipt_no': parent_rid,
                        'magic_token': magic_token or '',
                        'uuid': validated_uuid or uuid_hint or '',
                        'release_version': RELEASE_VERSION
                    }
                    
                    result = save_to_google_sheet(survey_data)
                    
                    if result.get('status') in ['success', 'success_delayed', 'pending'] or result.get('ok'):
                        st.session_state.submitted_2 = True
                        st.rerun()
                    else:
                        st.error(f"❌ 서버 통신 오류: {result.get('message')}. 잠시 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()