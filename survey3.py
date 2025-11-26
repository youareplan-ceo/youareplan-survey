# -*- coding: utf-8 -*-
"""
유아플랜 3차 전략 수립 – Streamlit (v3-2025-11-26-final)
- 회장님 전용 대시보드
- 투명 배경 CSS (다크/라이트 자동 적응)
- 1/2/3차 통합 데이터 조회
"""
import streamlit as st
import requests
from datetime import datetime
import os
import json
import pandas as pd
from typing import Optional, Dict, Any
from uuid import uuid4

# ==============================
# 기본 설정
# ==============================
st.set_page_config(page_title="유아플랜 3차 전략 수립", page_icon="📈", layout="wide")

RELEASE_VERSION_3 = "v3-2025-11-26-final"
SHOW_DEBUG = os.getenv("SHOW_DEBUG", "0") == "1"

# 환경변수
APPS_SCRIPT_URL_3 = os.getenv("THIRD_GAS_URL", "")
API_TOKEN_3 = os.getenv("API_TOKEN_3", "youareplan_stage3")
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# 로고
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"

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

  /* ===== 브랜드 요소 (고정색) ===== */
  .brandbar {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    margin-bottom: 10px;
    background: #002855;
    border-bottom: 1px solid rgba(128,128,128,0.2);
  }
  .brandbar img { height: 48px; }

  /* 대시보드 카드 - 반투명 */
  .dashboard-card {
    background: rgba(128,128,128,0.05);
    border-left: 5px solid #002855;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }
  .metric-label { 
    font-size: 12px; 
    opacity: 0.6; 
    margin-bottom: 4px; 
  }
  .metric-value { 
    font-size: 18px; 
    font-weight: bold; 
    color: #002855; 
  }
  @media (prefers-color-scheme: dark) {
    .metric-value { color: #60a5fa; }
  }

  /* 섹션 헤더 - 반투명 */
  .section-header {
    background: rgba(128,128,128,0.1);
    padding: 12px 16px;
    border-radius: 6px;
    margin: 16px 0 12px 0;
    font-weight: 600;
    border-left: 4px solid #002855;
  }
  @media (prefers-color-scheme: dark) {
    .section-header { border-left-color: #60a5fa; }
  }

  /* 리스크 배지 */
  .risk-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px;
  }
  .risk-high { background: #fee2e2; color: #991b1b !important; }
  .risk-low { background: #d1fae5; color: #065f46 !important; }

  /* ===== 탭 스타일 ===== */
  .stTabs [data-baseweb="tab-list"] { gap: 8px; }
  .stTabs [data-baseweb="tab"] { 
    height: 50px; 
    background: rgba(128,128,128,0.1); 
    border-radius: 8px 8px 0 0;
    padding: 10px 20px;
    font-weight: 500;
    color: inherit !important;
  }
  .stTabs [aria-selected="true"] { 
    background: #002855 !important; 
    color: white !important;
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

  /* ===== 버튼 (고정색) ===== */
  .stButton > button {
    background: #002855 !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
  }
  .stButton > button:hover { filter: brightness(1.1); }

  /* Data Editor - 투명 */
  .stDataFrame, [data-testid="stDataFrame"] {
    background: transparent !important;
  }
  .stDataFrame table {
    background: transparent !important;
  }
  .stDataFrame th, .stDataFrame td {
    background: rgba(128,128,128,0.05) !important;
    color: inherit !important;
    border-color: rgba(128,128,128,0.2) !important;
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

  /* 캡션/도움말 */
  div[data-testid="stCaptionContainer"] {
    opacity: 0.7;
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# API 통신
# ==============================
def _http_post(url: str, payload: Dict[str, Any], timeout: int = 20) -> tuple[bool, Dict]:
    """HTTP POST 요청"""
    if not url:
        return False, {"status": "error", "message": "GAS URL이 설정되지 않았습니다"}
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=timeout)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"status": "error", "message": str(e)}

def load_client_data(receipt_no: str, uuid: str) -> tuple[bool, Dict]:
    """GAS에서 1,2,3차 통합 데이터 로드"""
    payload = {
        "token": API_TOKEN_3,
        "action": "get_client_data",
        "receipt_no": receipt_no,
        "uuid": uuid
    }
    return _http_post(APPS_SCRIPT_URL_3, payload)

def load_snapshot(receipt_no: str, uuid: str) -> tuple[bool, Dict]:
    """3차 저장 데이터 스냅샷 로드"""
    payload = {
        "token": API_TOKEN_3,
        "action": "snapshot",
        "receipt_no": receipt_no,
        "uuid": uuid
    }
    return _http_post(APPS_SCRIPT_URL_3, payload)

def save_strategy(receipt_no: str, uuid: str, data: Dict, status: str = "draft") -> tuple[bool, Dict]:
    """3차 전략 데이터 저장"""
    payload = {
        "token": API_TOKEN_3,
        "action": "save",
        "receipt_no": receipt_no,
        "uuid": uuid,
        "status": status,
        "client_version": st.session_state.get("server_version", 0),
        "release_version": RELEASE_VERSION_3,
        "payload": data
    }
    return _http_post(APPS_SCRIPT_URL_3, payload)

# ==============================
# 유틸리티
# ==============================
def _fmt_money(val, unit="만원"):
    """금액 포맷팅"""
    try:
        v = int(float(val or 0))
        if v >= 10000:
            return f"{v/10000:.1f}억{unit}"
        return f"{v:,}{unit}"
    except:
        return str(val) if val else "-"

def _risk_check(data: Dict) -> list:
    """리스크 항목 체크"""
    risks = []
    if data.get("tax_status_1", "") not in ["", "체납 없음"]:
        risks.append(("세금체납", "high"))
    if data.get("credit_status_1", "") not in ["", "연체 없음"]:
        risks.append(("금융연체", "high"))
    if data.get("biz_status_1", "") not in ["", "정상 영업"]:
        risks.append(("영업상태", "high"))
    
    # 부채비율 계산
    try:
        capital = float(data.get("capital", 0) or 0)
        debt = float(data.get("debt", 0) or 0)
        if capital > 0:
            ratio = (debt / capital) * 100
            if ratio > 200:
                risks.append((f"부채비율 {ratio:.0f}%", "high"))
    except:
        pass
    
    if not risks:
        risks.append(("리스크 없음", "low"))
    
    return risks

# ==============================
# 메인
# ==============================
def main():
    # 브랜드바
    st.markdown(f'<div class="brandbar"><img src="{DEFAULT_LOGO_URL}" alt="유아플랜 로고"></div>', unsafe_allow_html=True)
    st.title("📈 3차 전략 수립")

    # 쿼리 파라미터
    qp = st.query_params
    receipt_no = qp.get("r", "")
    uuid = qp.get("u", "")

    if not receipt_no or not uuid:
        st.error("접근 정보가 없습니다. 담당자가 보낸 링크로 접속해주세요.")
        st.markdown(f'<a href="{KAKAO_CHAT_URL}" target="_blank" style="display:inline-block;background:#FEE500;color:#3c1e1e;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">💬 링크 요청하기</a>', unsafe_allow_html=True)
        return

    # 데이터 로드
    with st.spinner("고객 데이터를 불러오는 중..."):
        ok, res = load_client_data(receipt_no, uuid)
    
    if not ok or res.get("status") != "success":
        st.error(f"데이터 로드 실패: {res.get('message', '알 수 없는 오류')}")
        return

    c = res.get("data", {})
    
    # 3차 스냅샷 로드
    _, snap_res = load_snapshot(receipt_no, uuid)
    t = snap_res.get("data") or {}
    st.session_state.server_version = snap_res.get("server_version", 0)

    # ===== 상단 요약 카드 =====
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    cols = st.columns(6)
    cols[0].markdown(f"<div class='metric-label'>고객명</div><div class='metric-value'>{c.get('name', '-')}</div>", unsafe_allow_html=True)
    cols[1].markdown(f"<div class='metric-label'>기업명</div><div class='metric-value'>{c.get('company_name', '-')}</div>", unsafe_allow_html=True)
    cols[2].markdown(f"<div class='metric-label'>업종</div><div class='metric-value'>{c.get('industry', '-')}</div>", unsafe_allow_html=True)
    cols[3].markdown(f"<div class='metric-label'>올해 매출</div><div class='metric-value'>{_fmt_money(c.get('revenue_current'))}</div>", unsafe_allow_html=True)
    cols[4].markdown(f"<div class='metric-label'>필요 자금</div><div class='metric-value'>{c.get('funding_need', '-')}</div>", unsafe_allow_html=True)
    cols[5].markdown(f"<div class='metric-label'>접수번호</div><div class='metric-value'>{receipt_no}</div>", unsafe_allow_html=True)
    
    # 리스크 배지
    risks = _risk_check(c)
    risk_html = " ".join([f"<span class='risk-badge risk-{r[1]}'>{r[0]}</span>" for r in risks])
    st.markdown(f"<div style='margin-top:12px;'><strong>리스크:</strong> {risk_html}</div>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ===== 탭 =====
    tab_info, tab_strategy, tab_docs, tab_report = st.tabs(["📋 고객 정보", "🎯 전략 수립", "📑 서류 체크", "📤 실행 리포트"])
    
    # ----- TAB 1: 고객 정보 -----
    with tab_info:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown('<div class="section-header">1차 설문 정보</div>', unsafe_allow_html=True)
            st.text(f"이름: {c.get('name', '-')}")
            st.text(f"연락처: {c.get('phone', '-')}")
            st.text(f"이메일: {c.get('email', '-')}")
            st.text(f"지역: {c.get('region', '-')}")
            st.text(f"업종: {c.get('industry', '-')}")
            st.text(f"사업형태: {c.get('business_type', '-')}")
            st.text(f"직원수: {c.get('employee_count', '-')}")
            st.text(f"매출규모: {c.get('revenue_range', '-')}")
            st.text(f"필요자금: {c.get('funding_need', '-')}")
            st.text(f"정책자금 경험: {c.get('policy_experience', '-')}")
        
        with col_right:
            st.markdown('<div class="section-header">2차 설문 정보</div>', unsafe_allow_html=True)
            st.text(f"기업명: {c.get('company_name', '-')}")
            st.text(f"사업자번호: {c.get('biz_reg_no', '-')}")
            st.text(f"창업일: {c.get('startup_date', '-')}")
            st.text(f"점포형태: {c.get('store_type', '-')}")
            st.text(f"보증금: {_fmt_money(c.get('deposit'))}")
            st.text(f"월세: {_fmt_money(c.get('monthly_rent'))}")
            st.text(f"올해 매출: {_fmt_money(c.get('revenue_current'))}")
            st.text(f"전년 매출: {_fmt_money(c.get('revenue_y1'))}")
            st.text(f"전전년 매출: {_fmt_money(c.get('revenue_y2'))}")
            st.text(f"자본금: {_fmt_money(c.get('capital'))}")
            st.text(f"부채: {_fmt_money(c.get('debt'))}")
            st.text(f"보증이용: {c.get('guarantee_history', '-')}")
            st.text(f"인증: {c.get('certifications', '-')}")
            st.text(f"연구소: {c.get('research_lab', '-')}")
            st.text(f"자금용도: {c.get('fund_purpose', '-')}")
    
    # ----- TAB 2: 전략 수립 -----
    with tab_strategy:
        st.markdown('<div class="section-header">자금 조달 목표</div>', unsafe_allow_html=True)
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            target_agency = st.selectbox("공략 기관 (1순위)", 
                ["중소벤처기업진흥공단", "신용보증기금", "기술보증기금", "소상공인시장진흥공단", "지역신용보증재단", "시중은행"],
                key="target_agency")
            target_amount = st.number_input("목표 금액 (만원)", value=10000, step=1000, key="target_amount")
        with col_s2:
            fund_name = st.text_input("세부 자금명", placeholder="예: 청년전용창업자금", key="fund_name",
                value=t.get("priority", ""))
            expect_date = st.date_input("자금 집행 목표일", key="expect_date")

        st.markdown('<div class="section-header">담보·보증 계획</div>', unsafe_allow_html=True)
        collateral = st.text_area("담보/보증 계획", height=80, key="collateral",
            value=t.get("collateral", ""),
            placeholder="예: 부동산 담보 2억 평가 예정, 신보 80% 보증 신청")

        st.markdown('<div class="section-header">핵심 전략 포인트</div>', unsafe_allow_html=True)
        strategy_points = st.text_area("심사역 어필 포인트", height=100, key="strategy_points",
            value=t.get("coach", ""),
            placeholder="- 최근 매출 성장세 (YoY 30%)\n- 벤처인증 보유\n- 신규 거래처 계약 예정")

        st.markdown('<div class="section-header">리스크 대응</div>', unsafe_allow_html=True)
        risk_plan = st.text_area("리스크 방어 논리", height=80, key="risk_plan",
            value=t.get("risks", ""),
            placeholder="- 부채비율 높으나 가수금 제외 시 200% 이내\n- 일시적 연체였으며 현재 정상")
    
    # ----- TAB 3: 서류 체크리스트 -----
    with tab_docs:
        st.markdown('<div class="section-header">필수 준비 서류</div>', unsafe_allow_html=True)
        
        # 기존 저장된 서류 체크 로드
        saved_docs = t.get("docs", "")
        saved_list = [d.strip() for d in saved_docs.split(",") if d.strip()] if saved_docs else []
        
        if "docs_df" not in st.session_state:
            initial_docs = [
                {"구분": "기본", "서류명": "사업자등록증", "상태": "준비완료" if "사업자등록증" in saved_list else "미비", "비고": ""},
                {"구분": "재무", "서류명": "재무제표(최근3년)", "상태": "준비완료" if "재무제표" in saved_list else "미비", "비고": ""},
                {"구분": "재무", "서류명": "부가세 과세표준증명", "상태": "미비", "비고": "홈택스 발급"},
                {"구분": "세무", "서류명": "국세 완납증명", "상태": "미비", "비고": ""},
                {"구분": "세무", "서류명": "지방세 완납증명", "상태": "미비", "비고": ""},
                {"구분": "보험", "서류명": "4대보험 가입자명부", "상태": "미비", "비고": ""},
                {"구분": "금융", "서류명": "통장사본(주거래)", "상태": "미비", "비고": ""},
                {"구분": "기타", "서류명": "사업계획서", "상태": "미비", "비고": ""},
            ]
            st.session_state.docs_df = pd.DataFrame(initial_docs)

        edited_df = st.data_editor(
            st.session_state.docs_df,
            column_config={
                "상태": st.column_config.SelectboxColumn(
                    "상태",
                    options=["준비완료", "요청중", "미비", "해당없음"],
                    required=True,
                    width="small"
                ),
                "비고": st.column_config.TextColumn("특이사항", width="large")
            },
            num_rows="dynamic",
            use_container_width=True,
            key="docs_editor"
        )
        st.session_state.docs_df = edited_df
    
    # ----- TAB 4: 실행 리포트 -----
    with tab_report:
        st.markdown('<div class="section-header">고객 발송용 안내문</div>', unsafe_allow_html=True)
        
        # 미비 서류 필터
        pending = edited_df[edited_df["상태"].isin(["미비", "요청중"])]
        pending_str = "\n".join([f"  • {row['서류명']} ({row['비고']})" if row['비고'] else f"  • {row['서류명']}" 
                                  for _, row in pending.iterrows()])
        if not pending_str:
            pending_str = "  (모든 서류 준비 완료)"

        report_text = f"""[유아플랜 자금 조달 안내]

{c.get('company_name', '')} {c.get('name', '')} 대표님께

▣ 1차 목표
- 기관: {target_agency}
- 자금: {fund_name}
- 금액: {_fmt_money(target_amount)}
- 목표: {expect_date.strftime('%Y년 %m월')}

▣ 준비 요청 서류
{pending_str}

▣ 전략 포인트
{strategy_points if strategy_points else '(작성 필요)'}

위 서류를 준비하여 회신 부탁드립니다.
문의: 유아플랜 담당자
"""
        
        st.text_area("아래 내용을 복사해서 카톡/메일로 발송하세요", value=report_text.strip(), height=350, key="report_output")
        
        # 전화 버튼
        phone = c.get("phone", "")
        if phone:
            st.markdown(f"📞 [전화 걸기](tel:{phone})")
    
    # ===== 저장 버튼 =====
    st.markdown("---")
    col_save1, col_save2, col_save3 = st.columns([2, 2, 1])
    
    with col_save1:
        if st.button("💾 임시 저장", use_container_width=True):
            # 서류 체크 항목 추출
            completed_docs = edited_df[edited_df["상태"] == "준비완료"]["서류명"].tolist()
            
            save_data = {
                "collateral_profile": collateral,
                "tax_credit_summary": "",
                "loan_summary": "",
                "docs_check": completed_docs,
                "priority_exclusion": f"{target_agency} / {fund_name}",
                "risk_top3": risk_plan,
                "coach_notes": strategy_points
            }
            
            ok, res = save_strategy(receipt_no, uuid, save_data, status="draft")
            if ok and res.get("status") == "success":
                st.session_state.server_version = res.get("server_version", 0)
                st.success("✅ 임시 저장 완료")
            else:
                st.error(f"저장 실패: {res.get('message', '오류')}")
    
    with col_save2:
        if st.button("📨 최종 완료", type="primary", use_container_width=True):
            completed_docs = edited_df[edited_df["상태"] == "준비완료"]["서류명"].tolist()
            
            save_data = {
                "collateral_profile": collateral,
                "tax_credit_summary": "",
                "loan_summary": "",
                "docs_check": completed_docs,
                "priority_exclusion": f"{target_agency} / {fund_name}",
                "risk_top3": risk_plan,
                "coach_notes": strategy_points
            }
            
            ok, res = save_strategy(receipt_no, uuid, save_data, status="final")
            if ok and res.get("status") == "success":
                st.success("✅ 최종 완료! 고객에게 안내문을 발송하세요.")
                st.balloons()
            else:
                st.error(f"저장 실패: {res.get('message', '오류')}")
    
    with col_save3:
        st.markdown(f"[💬 카카오]({KAKAO_CHAT_URL})")
    
    # 디버그 모드
    if SHOW_DEBUG:
        with st.expander("🔧 디버그 정보"):
            st.json({"receipt": receipt_no, "uuid": uuid[:8]+"...", "version": st.session_state.get("server_version", 0)})
            st.json(c)

if __name__ == "__main__":
    main()