import streamlit as st
import requests
import re
import os
import json
import time
from datetime import datetime
from uuid import uuid4
from typing import Optional

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(
    page_title="유아플랜 정책자금 2차 심화진단",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==============================
# 환경 설정 (원본 로직 복구)
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
RELEASE_VERSION = "v2025-11-27-stable"

class _Config:
    SECOND_GAS_URL = os.getenv("SECOND_GAS_URL", "https://script.google.com/macros/s/YOUR_GAS_ID/exec")
    FIRST_GAS_TOKEN_API_URL = os.getenv("FIRST_GAS_TOKEN_API_URL", "https://script.google.com/macros/s/YOUR_TOKEN_API_ID/exec")
    API_TOKEN_STAGE2 = os.getenv("API_TOKEN_2", "youareplan_stage2")

config = _Config()

# KakaoTalk Channel
KAKAO_CHANNEL_URL = "https://pf.kakao.com/_LWxexmn"

# ==============================
# [핵심] 네트워크 & 인증 로직 (원본 복구)
# ==============================
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

def validate_access_token(token: str, uuid_hint: str | None = None, timeout_sec: int = 10) -> dict:
    # URL이 설정되지 않았을 경우 예외처리
    if "YOUR_GAS_ID" in config.FIRST_GAS_TOKEN_API_URL:
        # 테스트 환경 등을 위해 임시 통과 (배포 시엔 실제 URL 필수)
        return {"ok": True, "parent_receipt_no": "TEST-1234", "phone_mask": "010-****-1234"}

    payload = {"action": "validate", "token": token, "api_token": "youareplan"}
    if uuid_hint:
        payload["uuid"] = uuid_hint
    
    ok, status_code, resp_data, err = post_json(
        _normalize_gas_url(config.FIRST_GAS_TOKEN_API_URL), 
        payload, 
        timeout=timeout_sec, 
        retries=1
    )
    if ok:
        return resp_data or {"ok": False, "message": "empty response"}
    return {"ok": False, "message": err or f"HTTP {status_code}"}

def save_to_google_sheet(data, timeout_sec: int = 45):
    data['token'] = config.API_TOKEN_STAGE2
    request_id = str(uuid4())
    
    ok, status_code, resp_data, err = post_json(
        _normalize_gas_url(config.SECOND_GAS_URL),
        data,
        headers={"X-Request-ID": request_id},
        timeout=timeout_sec,
        retries=0,
    )
    
    if ok:
        return resp_data or {"status": "success"}
    return {"status": "error", "message": err or f"HTTP {status_code}"}

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
# CSS 스타일
# ==============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

#MainMenu, footer, header { display: none !important; }

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 3rem !important;
    max-width: 700px !important;
}

.unified-header {
    background: #002855;
    padding: 24px 20px;
    text-align: center;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.unified-header img {
    height: 48px;
    margin-bottom: 12px;
    object-fit: contain;
}

.unified-header .gov-label {
    color: rgba(255, 255, 255, 0.85);
    font-size: 13px;
    font-weight: 500;
}

.section-header {
    font-size: 17px;
    font-weight: 700;
    margin-top: 30px;
    margin-bottom: 12px;
    color: #005BAC;
    border-left: 4px solid #005BAC;
    padding-left: 10px;
}

@media (prefers-color-scheme: dark) {
    .section-header {
        color: #60A5FA;
        border-left-color: #60A5FA;
    }
}

div[data-testid="stFormSubmitButton"] button {
    background: #002855 !important;
    color: white !important;
    border: none !important;
    padding: 14px 24px !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# 메인 함수
# ==============================
def main():
    if "submitted_2" not in st.session_state:
        st.session_state.submitted_2 = False

    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <div class="gov-label">2차 심화 정밀 진단</div>
    </div>
    """, unsafe_allow_html=True)

    # URL 파라미터 처리 (토큰 검증)
    try:
        qp = st.query_params
        magic_token = qp.get("t")
        uuid_hint = qp.get("u")
    except:
        magic_token = None
        uuid_hint = None

    # 토큰 검증 로직 실행
    if not magic_token:
        st.warning("⚠️ 인증 토큰이 없습니다. (테스트 모드로 진행하거나 링크를 확인하세요)")
        # 실제 배포시에는 아래 return을 활성화하여 차단 가능
        # return 
        v_result = {"parent_receipt_no": "TEST-MODE", "phone_mask": "010-****-0000"}
    else:
        v_result = validate_access_token(magic_token, uuid_hint)
        if not v_result.get("ok"):
            st.error(f"접속이 만료되었거나 유효하지 않습니다: {v_result.get('message')}")
            return
    
    parent_rid = v_result.get("parent_receipt_no", "")
    masked_phone = v_result.get("phone_mask", "")

    if masked_phone:
        st.caption(f"✅ 인증됨 (접수번호: {parent_rid})")

    with st.form("survey2_form"):
        st.markdown('<div class="section-header">기본 정보 확인</div>', unsafe_allow_html=True)
        
        name = st.text_input("대표자 성함", placeholder="홍길동")
        st.text_input("1차 접수번호", value=parent_rid, disabled=True)
        phone_raw = st.text_input("연락처", placeholder="01012345678")
        biz_no_raw = st.text_input("사업자등록번호 (10자리)", placeholder="선택 사항")
        email = st.text_input("이메일 (선택)", placeholder="email@example.com")

        st.markdown('<div class="section-header">사업 및 재무 현황</div>', unsafe_allow_html=True)
        
        col_date, col_name = st.columns(2)
        with col_date:
            startup_date = st.date_input("개업 연월일", min_value=datetime(1990, 1, 1))
        with col_name:
            company_name = st.text_input("상호명")

        st.markdown("**최근 3년 연매출 (단위: 만원)**")
        c1, c2, c3 = st.columns(3)
        current_year = datetime.now().year
        with c1: revenue_y1 = st.text_input(f"{current_year}년(예상)")
        with c2: revenue_y2 = st.text_input(f"{current_year-1}년")
        with c3: revenue_y3 = st.text_input(f"{current_year-2}년")

        col_cap, col_debt = st.columns(2)
        with col_cap: capital_amount = st.text_input("자본금 (만원)")
        with col_debt: debt_amount = st.text_input("현재 부채 (만원)")

        st.markdown('<div class="section-header">기술력 및 가점 사항</div>', unsafe_allow_html=True)
        
        ip_status = st.multiselect("지식재산권", ["특허 등록", "특허 출원", "디자인/상표권", "해당 없음"])
        official_certs = st.multiselect("보유 인증", ["벤처기업", "이노비즈", "메인비즈", "ISO인증", "연구소 보유", "해당 없음"])
        incentive_status = st.multiselect("정책 우대", ["청년창업(만39세 이하)", "여성기업", "장애인기업", "소재부품장비", "해당 없음"])

        st.markdown('<div class="section-header">자금 활용 계획</div>', unsafe_allow_html=True)
        purpose = st.multiselect("주요 용도", ["운전자금 (원자재, 인건비 등)", "시설자금 (기계, 공장, 토지 등)", "R&D 자금"])
        detailed_plan = st.text_area("구체적인 활용 계획", placeholder="예: 신규 장비 도입 1억, 원자재 구매 5천만원 등")

        privacy_agree = st.checkbox("개인정보 수집 및 심층 분석 활용 동의 (필수)")
        marketing_agree = st.checkbox("마케팅 정보 수신 동의 (선택)")

        st.write("")
        submitted = st.form_submit_button("📩 정밀 진단 제출하기")

        if submitted:
            phone_digits = _digits_only(phone_raw)
            formatted_phone = format_phone(phone_digits)
            formatted_biz = format_biz_no(_digits_only(biz_no_raw))

            if not name:
                st.warning("대표자 성함을 입력해주세요.")
            elif len(phone_digits) < 10:
                st.warning("연락처를 확인해주세요.")
            elif not privacy_agree:
                st.error("필수 동의 항목을 체크해주세요.")
            else:
                with st.spinner("데이터 분석 및 전송 중..."):
                    # 전송할 데이터 구성
                    survey_data = {
                        'name': name,
                        'phone': formatted_phone,
                        'email': email,
                        'biz_reg_no': formatted_biz,
                        'business_name': company_name,
                        'startup_date': startup_date.strftime('%Y-%m-%d'),
                        'revenue_y1': revenue_y1,
                        'revenue_y2': revenue_y2,
                        'revenue_y3': revenue_y3,
                        'capital_amount': capital_amount,
                        'debt_amount': debt_amount,
                        'ip_status': ', '.join(ip_status),
                        'official_certs': ', '.join(official_certs),
                        'incentive_status': ', '.join(incentive_status),
                        'funding_purpose': ', '.join(purpose),
                        'detailed_funding': detailed_plan,
                        'privacy_agree': privacy_agree,
                        'marketing_agree': marketing_agree,
                        'parent_receipt_no': parent_rid,
                        'magic_token': magic_token,
                        'release_version': RELEASE_VERSION
                    }

                    # 실제 구글 시트 저장
                    result = save_to_google_sheet(survey_data)
                    
                    if result.get('status') in ['success', 'success_delayed', 'pending']:
                        st.session_state.submitted_2 = True
                        st.success("✅ 심화 진단이 성공적으로 접수되었습니다.")
                        st.balloons()
                        st.markdown("""
                        <div style="text-align:center; padding: 20px; background: rgba(0,0,0,0.03); border-radius:10px; margin-top:20px;">
                            <p>전문 위원이 분석 후 <strong>3일 이내</strong><br>상세 리포트를 안내해 드립니다.</p>
                            <a href="{KAKAO_CHANNEL_URL}" target="_blank">💬 카카오톡 문의하기</a>
                        </div>
                        """.format(KAKAO_CHANNEL_URL=KAKAO_CHANNEL_URL), unsafe_allow_html=True)
                    else:
                        st.error(f"제출 실패: {result.get('message')}")

if __name__ == "__main__":
    main()