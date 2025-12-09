"""
유아플랜 3차 심층 상담 (컨설턴트용)
v2025-12-09-final
- 인코딩 수정
- CSS 스타일 1차와 통일 (다크/라이트 모드 대응)
- GAS 필드명 동기화
- [추가] 의사결정 메타데이터 섹션 (AI 학습용)
"""

import streamlit as st
import requests
import os
import json
from datetime import datetime
from urllib.parse import unquote

st.set_page_config(
    page_title="유아플랜 3차 심층 상담",
    page_icon="👨‍💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
RELEASE_VERSION = "v2025-12-09-final"
APPS_SCRIPT_URL = os.getenv("THIRD_GAS_URL", "https://script.google.com/macros/s/YOUR_GAS_ID/exec")
API_TOKEN = os.getenv("API_TOKEN_3", "youareplan_stage3")
KAKAO_CHANNEL_URL = "https://pf.kakao.com/_LWxexmn"

# ==============================
# [추가] 의사결정 옵션
# ==============================
DECISION_STATUS_OPTIONS = [
    "선택해주세요",
    "진행 (계약 예정)",
    "보류 (추가 검토)",
    "부적합 (지원 불가)",
    "고객 이탈"
]

RECOMMENDED_FUND_OPTIONS = [
    "직접 입력",
    "소상공인정책자금 - 일반경영안정자금",
    "소상공인정책자금 - 긴급경영안정자금",
    "소상공인정책자금 - 성장촉진자금",
    "중소기업정책자금 - 혁신성장자금",
    "중소기업정책자금 - 신시장진출지원자금",
    "신용보증기금 - 창업기업보증",
    "기술보증기금 - 기술평가보증",
    "지역신용보증재단",
    "지자체 소상공인 융자",
    "창업사관학교/창업지원",
    "R&D 바우처/연구개발",
    "기타"
]

# ==============================
# 유틸리티 함수
# ==============================
def get_prefill_params():
    """URL 파라미터에서 프리필 데이터 추출"""
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

def save_consultation_result(data: dict) -> dict:
    """3차 GAS로 상담 결과 전송"""
    try:
        data['token'] = API_TOKEN
        response = requests.post(APPS_SCRIPT_URL, json=data, timeout=30)
        return response.json() if response.status_code == 200 else {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================
# 스타일링 (1차와 통일 - 다크/라이트 모드 대응)
# ==============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
#MainMenu, footer, header { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; }

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

.prefilled-info { 
    background: rgba(76, 175, 80, 0.1); 
    border: 1px solid rgba(76, 175, 80, 0.3); 
    border-radius: 8px; 
    padding: 12px 16px; 
    margin-bottom: 16px; 
}

.decision-box {
    background: rgba(255, 152, 0, 0.1);
    border: 2px solid rgba(255, 152, 0, 0.4);
    border-radius: 12px;
    padding: 16px;
    margin: 16px 0;
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
    if 'submitted_3' not in st.session_state:
        st.session_state.submitted_3 = False

    # 헤더
    st.markdown(f"""
    <div class="unified-header">
        <img src="{LOGO_URL}" alt="{BRAND_NAME}">
        <div class="gov-label">3차 심층 상담 (컨설턴트 입력용)</div>
    </div>
    """, unsafe_allow_html=True)

    # 제출 완료 화면
    if st.session_state.submitted_3:
        client_name = st.session_state.get('client_name', '고객')
        st.success(f"✅ {client_name} 님의 상담 내용이 저장되었습니다.")
        st.balloons()
        
        st.markdown(f"""
        <div class="success-box">
            <h3>상담 결과 저장 완료</h3>
            <p>대시보드에서 확인하실 수 있습니다.</p>
        </div>
        <div style="text-align: center; margin-top: 20px;">
            <a href="{KAKAO_CHANNEL_URL}" target="_blank" 
               style="display:inline-block; background:#FEE500; color:#3C1E1E; 
                      padding:12px 25px; border-radius:8px; text-decoration:none; font-weight:bold;">
                💬 카카오톡 문의하기
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        # 초기화 버튼
        if st.button("🔄 다른 고객 상담하기 (초기화)"):
            st.session_state.submitted_3 = False
            st.rerun()
        return

    # URL 파라미터로 프리필
    prefill = get_prefill_params()
    
    if prefill["name"] or prefill["receipt_no"]:
        st.markdown(f"""
        <div class="prefilled-info">
            ✅ <strong>고객 정보가 자동으로 입력되었습니다.</strong><br>
            👤 {prefill["name"]} | 📞 {prefill["phone"]} | 🎫 {prefill["receipt_no"]}
        </div>
        """, unsafe_allow_html=True)
    
    # 설문 폼
    with st.form("admin_consult_form"):
        
        # ========== 섹션 1: 고객 정보 확인 ==========
        st.markdown('<div class="section-header">👤 고객 정보 확인</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            client_name = st.text_input("고객 성함 *", value=prefill["name"])
        with col2:
            client_phone = st.text_input("연락처", value=prefill["phone"])
        with col3:
            if prefill["receipt_no"]:
                receipt_no = st.text_input("접수번호", value=prefill["receipt_no"], disabled=True)
            else:
                receipt_no = st.text_input("접수번호 (선택)", placeholder="YP...")

        st.markdown("---")
        
        # ========== 좌우 2컬럼 레이아웃 ==========
        col_left, col_right = st.columns(2)
        
        with col_left:
            # 담보 및 자산 현황
            st.markdown('<div class="section-header">🧱 담보 및 자산 현황</div>', unsafe_allow_html=True)
            collateral = st.text_area(
                "담보 제공 계획", 
                placeholder="부동산, 보증서, 신용보증재단 이용 가능 여부 등",
                height=120
            )
            
            # 부채 및 신용
            st.markdown('<div class="section-header">🏦 부채 및 신용</div>', unsafe_allow_html=True)
            debt_info = st.text_area(
                "기대출 및 신용 특이사항", 
                placeholder="은행/기관명, 잔액, 금리, 상환 일정 등",
                height=120
            )
        
        with col_right:
            # 재무 및 가점 요인
            st.markdown('<div class="section-header">📊 재무 및 가점 요인</div>', unsafe_allow_html=True)
            financial_check = st.text_area(
                "매출/이익/가점 사항", 
                placeholder="매출 추이, 인증 현황, 특허/R&D, 고용 증가 등",
                height=120
            )
            
            # 서류 준비 상태
            st.markdown('<div class="section-header">📑 서류 준비 상태</div>', unsafe_allow_html=True)
            docs_check = st.multiselect(
                "보유 서류 확인",
                [
                    "사업자등록증",
                    "재무제표(최근 3년)",
                    "부가세과세표준증명",
                    "국세/지방세 완납증명",
                    "법인등기부등본",
                    "주주명부",
                    "4대보험 가입자명부",
                    "임대차계약서"
                ]
            )

        st.markdown("---")
        
        # ========== 컨설턴트 종합 의견 ==========
        st.markdown('<div class="section-header">💡 컨설턴트 종합 의견</div>', unsafe_allow_html=True)
        consultant_note = st.text_area(
            "분석 결과 및 향후 가이드", 
            height=150, 
            placeholder="지원 가능 자금, 예상 한도, 준비 사항, 추천 전략 등 종합 의견을 작성해주세요."
        )

        # ========== [추가] 의사결정 메타데이터 섹션 ==========
        st.markdown("---")
        st.markdown("""
        <div class="decision-box">
            <div class="section-header" style="color: #E65100; border-bottom-color: rgba(255, 152, 0, 0.4);">🎯 의사결정 기록 (AI 학습용)</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("⚠️ 이 섹션은 AI 매칭 학습 데이터로 활용됩니다. 정확하게 입력해주세요.")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            # 추천 자금 선택
            fund_preset = st.selectbox(
                "추천 자금 (빠른선택)",
                RECOMMENDED_FUND_OPTIONS,
                index=0,
                help="자주 추천하는 자금을 빠르게 선택하세요."
            )
            
            # 직접 입력이면 텍스트 박스 표시
            if fund_preset == "직접 입력":
                recommended_fund = st.text_input(
                    "추천 자금명 (직접 입력)",
                    placeholder="예: 경남 소상공인 특별자금"
                )
            else:
                recommended_fund = fund_preset
                st.text_input("추천 자금명", value=recommended_fund, disabled=True)
        
        with col_d2:
            # 예상 한도
            expected_limit = st.text_input(
                "예상 한도 (만원)",
                placeholder="예: 5000",
                help="승인 가능 예상 금액 (만원 단위)"
            )
            
            # 진행 상태
            decision_status = st.selectbox(
                "진행 상태",
                DECISION_STATUS_OPTIONS,
                index=0,
                help="현재 상담 결과에 따른 진행 상태"
            )
        
        # 고객 준비도 (선택)
        st.markdown("**고객 준비도 평가 (선택)**")
        col_r1, col_r2 = st.columns([1, 3])
        with col_r1:
            readiness_score = st.slider(
                "준비도 점수",
                min_value=1,
                max_value=5,
                value=3,
                help="1=준비 부족, 3=보통, 5=즉시 가능"
            )
        with col_r2:
            readiness_labels = {
                1: "❌ 준비 부족 - 기본 서류/조건 미충족",
                2: "⚠️ 미흡 - 일부 보완 필요",
                3: "➖ 보통 - 표준적인 준비 상태",
                4: "✅ 양호 - 대부분 준비 완료",
                5: "🌟 우수 - 즉시 신청 가능"
            }
            st.info(readiness_labels.get(readiness_score, ""))

        st.write("")
        submitted = st.form_submit_button("💾 상담 결과 저장하기")

        if submitted:
            # 유효성 검사
            if not client_name.strip():
                st.warning("⚠️ 고객 성함은 필수입니다.")
            elif not consultant_note.strip():
                st.warning("⚠️ 종합 의견을 작성해주세요.")
            elif decision_status == "선택해주세요":
                st.warning("⚠️ 진행 상태를 선택해주세요.")
            else:
                with st.spinner("저장 중..."):
                    
                    # GAS로 전송할 데이터 (action: save_consultation)
                    data = {
                        "action": "save_consultation",
                        "name": client_name.strip(),
                        "phone": client_phone.strip() if client_phone else "",
                        "receipt_no": receipt_no if receipt_no else prefill["receipt_no"],
                        "uuid": prefill["uuid"],
                        
                        # 상담 내용 (GAS 필드명에 맞춤)
                        "collateral": collateral.strip() if collateral else "",
                        "debt_info": debt_info.strip() if debt_info else "",
                        "financial_check": financial_check.strip() if financial_check else "",
                        "docs_check": ", ".join(docs_check) if docs_check else "",
                        "consultant_note": consultant_note.strip(),
                        
                        # [추가] 의사결정 메타데이터
                        "recommended_fund": recommended_fund if recommended_fund != "직접 입력" else "",
                        "expected_limit": expected_limit.strip() if expected_limit else "",
                        "decision_status": decision_status,
                        "readiness_score": readiness_score,
                        
                        # 메타 정보
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "version": RELEASE_VERSION
                    }
                    
                    result = save_consultation_result(data)
                    
                    if result.get("status") == "success" or result.get("ok") == True:
                        st.session_state.submitted_3 = True
                        st.session_state.client_name = client_name
                        st.rerun()
                    else:
                        st.error(f"❌ 저장 실패: {result.get('message')}. 잠시 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()