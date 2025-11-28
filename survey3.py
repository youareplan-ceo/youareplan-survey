import streamlit as st
import requests
import os
import json
from datetime import datetime
from urllib.parse import unquote

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(
    page_title="3차 심층 상담 (컨설턴트용)",
    page_icon="👨‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
RELEASE_VERSION = "v2025-11-28-prefill"

# 실제 구글 앱스 스크립트 URL (환경변수 설정 필수)
APPS_SCRIPT_URL = os.getenv("THIRD_GAS_URL", "https://script.google.com/macros/s/YOUR_GAS_ID/exec")
API_TOKEN = os.getenv("API_TOKEN_3", "youareplan_stage3")

# ==============================
# 쿼리 파라미터 읽기
# ==============================
def get_prefill_params():
    """URL 쿼리 파라미터에서 고객 정보 읽기"""
    try:
        qp = st.query_params
        return {
            "name": unquote(qp.get("name", "")),
            "phone": unquote(qp.get("phone", "")),
            "receipt_no": unquote(qp.get("r", "")),
            "uuid": unquote(qp.get("u", ""))
        }
    except:
        return {"name": "", "phone": "", "receipt_no": "", "uuid": ""}

# ==============================
# 데이터 전송 함수 (실제 연동)
# ==============================
def save_consultation_result(data: dict) -> dict:
    """컨설턴트 입력 데이터를 구글 시트로 전송"""
    try:
        data['token'] = API_TOKEN
        response = requests.post(APPS_SCRIPT_URL, json=data, timeout=20)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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

.unified-header {
    background: #002855;
    padding: 20px 24px;
    text-align: center;
    border-radius: 0 0 12px 12px;
    margin: -4rem -4rem 20px -4rem;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.unified-header img {
    height: 40px;
    margin-bottom: 8px;
    object-fit: contain;
}

.unified-header h2 {
    color: white;
    font-size: 20px;
    font-weight: 700;
    margin: 0;
}

.section-title {
    font-size: 18px;
    font-weight: 700;
    margin-top: 20px;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 2px solid rgba(128, 128, 128, 0.2);
    color: #002855;
}

@media (prefers-color-scheme: dark) {
    .section-title {
        color: #93C5FD;
    }
}

.stTextArea textarea {
    min-height: 120px;
}

/* 자동 입력된 필드 스타일 */
.prefilled-info {
    background: #E8F5E9;
    border: 1px solid #81C784;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;
}

.prefilled-info strong {
    color: #2E7D32;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# 메인 함수
# ==============================
def main():
    # 쿼리 파라미터에서 고객 정보 읽기
    prefill = get_prefill_params()
    
    # 헤더
    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <h2>3차 심층 상담 (컨설턴트 입력용)</h2>
    </div>
    """, unsafe_allow_html=True)

    # 자동 입력된 정보 표시
    if prefill["name"] or prefill["receipt_no"]:
        st.markdown(f"""
        <div class="prefilled-info">
            ✅ <strong>고객 정보가 자동으로 입력되었습니다.</strong><br>
            👤 {prefill["name"]} | 📞 {prefill["phone"]} | 🎫 {prefill["receipt_no"]}
        </div>
        """, unsafe_allow_html=True)
    
    st.info("📞 고객과 통화하며 내용을 정리한 후, 하단의 **[상담 결과 저장]** 버튼을 눌러주세요.")

    with st.form("admin_consult_form"):
        
        # 1. 고객 식별 정보 (자동 입력)
        st.markdown('<div class="section-title">👤 고객 정보 확인</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: 
            client_name = st.text_input("고객 성함", value=prefill["name"])
        with col2: 
            client_phone = st.text_input("연락처", value=prefill["phone"])
        with col3: 
            # 접수번호가 있으면 수정 불가
            if prefill["receipt_no"]:
                receipt_no = st.text_input("접수번호", value=prefill["receipt_no"], disabled=True)
            else:
                receipt_no = st.text_input("접수번호 (선택)", placeholder="YP...")

        # UUID 숨김 저장
        uuid_val = prefill["uuid"]

        st.markdown("---")

        # 2. 핵심 상담 내용
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown('<div class="section-title">🧱 담보 및 자산 현황</div>', unsafe_allow_html=True)
            collateral = st.text_area("담보 제공 계획", placeholder="부동산, 보증서, 예금 등 상세 기술")
            
            st.markdown('<div class="section-title">🏦 부채 및 신용</div>', unsafe_allow_html=True)
            debt_info = st.text_area("기대출 및 신용 특이사항", placeholder="은행/기관명, 금리, 만기, 연체 이력 등")

        with col_right:
            st.markdown('<div class="section-title">📊 재무 및 가점 요인</div>', unsafe_allow_html=True)
            financial_check = st.text_area("매출/이익/가점 사항", placeholder="매출 추이, 인증 현황, 고용 증가 등")

            st.markdown('<div class="section-title">📑 서류 준비 상태</div>', unsafe_allow_html=True)
            docs_check = st.multiselect(
                "보유 서류 확인",
                ["사업자등록증", "재무제표(최근 3년)", "부가세과세표준증명", "국세/지방세 완납증명", "법인등기부등본", "주주명부"],
            )

        st.markdown("---")

        # 3. 종합 의견
        st.markdown('<div class="section-title">💡 컨설턴트 종합 의견</div>', unsafe_allow_html=True)
        consultant_note = st.text_area("분석 결과 및 향후 가이드", height=200, placeholder="지원 가능 자금, 예상 한도, 보완 필요 사항 등")

        # 4. 제출 버튼
        st.write("")
        submitted = st.form_submit_button("💾 상담 결과 저장하기", type="primary")

        if submitted:
            if not client_name:
                st.warning("고객 성함은 필수입니다.")
            elif not consultant_note:
                st.warning("종합 의견을 작성해주세요.")
            else:
                # 데이터 구성
                data = {
                    "action": "save_consultation",
                    "name": client_name,
                    "phone": client_phone,
                    "receipt_no": receipt_no or prefill["receipt_no"],
                    "uuid": uuid_val,
                    "collateral": collateral,
                    "debt_info": debt_info,
                    "financial_check": financial_check,
                    "docs_check": ", ".join(docs_check),
                    "consultant_note": consultant_note,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": RELEASE_VERSION
                }

                with st.spinner("구글 시트에 저장 중입니다..."):
                    result = save_consultation_result(data)
                    
                    if result.get("status") == "success" or result.get("ok") == True:
                        st.success(f"✅ {client_name} 고객님의 상담 내용이 성공적으로 저장되었습니다.")
                        st.balloons()
                    else:
                        st.error(f"저장 실패: {result.get('message')}")

if __name__ == "__main__":
    main()