"""
유아플랜 컨설턴트 대시보드 v3.5-final
- v3.4 기반 + 신규 필드 추가
- 2차: 정책자금이력(past_policy_fund) 표시
- 3차: 의사결정 메타데이터 4개 필드 표시
  (recommended_fund, expected_limit, decision_status, readiness_score)
- 2025-12-09 최종
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List, Tuple
import base64
import os
import re
import io

# ==============================
# PDF 라이브러리 체크
# ==============================
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(
    page_title="유아플랜 컨설턴트 대시보드",
    page_icon="📊",
    layout="wide"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"

def _get_secret(key: str, default: str = "") -> str:
    """st.secrets 우선, 없으면 os.getenv 사용"""
    try:
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)

# GAS 엔드포인트
INTEGRATED_GAS_URL = _get_secret(
    "FIRST_GAS_URL",
    "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec"
)

# API 토큰
API_TOKEN = _get_secret("API_TOKEN", "youareplan")

# Gemini API
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY", "")

# 카카오톡 채널
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# 접속 비밀번호
DASHBOARD_PASSWORD = _get_secret("DASHBOARD_PW", "1234")

# 결과 저장용 대표 비밀번호
RESULT_PASSWORD = _get_secret("RESULT_PW", "")

# 설문 URL
FIRST_SURVEY_URL = "https://youareplan-survey.onrender.com"
SECOND_SURVEY_BASE_URL = "https://youareplan-survey2.onrender.com"

# ==============================
# 청년/여성/업력 계산 함수 (v3.2 신규)
# ==============================
def parse_birthdate(birthdate_str: str) -> Optional[date]:
    """생년월일 문자열 파싱 (다양한 형식 지원)"""
    if not birthdate_str:
        return None
    
    s = str(birthdate_str).strip().replace(" ", "")
    
    # 형식들: 1985-03-15, 19850315, 850315, 1985.03.15, 1985/03/15
    patterns = [
        (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r'^(\d{4})/(\d{1,2})/(\d{1,2})$', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r'^(\d{4})(\d{2})(\d{2})$', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r'^(\d{2})(\d{2})(\d{2})$', lambda m: (1900 + int(m.group(1)) if int(m.group(1)) > 30 else 2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    ]
    
    for pattern, extractor in patterns:
        match = re.match(pattern, s)
        if match:
            try:
                year, month, day = extractor(match)
                return date(year, month, day)
            except:
                continue
    
    return None

def calculate_age(birthdate_str: str) -> Optional[int]:
    """만 나이 계산"""
    birth = parse_birthdate(birthdate_str)
    if not birth:
        return None
    
    today = date.today()
    age = today.year - birth.year
    
    # 생일이 안 지났으면 1 빼기
    if (today.month, today.day) < (birth.month, birth.day):
        age -= 1
    
    return age

def calculate_youth_status(birthdate_str: str) -> str:
    """청년여부 계산 (만 39세 이하)"""
    age = calculate_age(birthdate_str)
    if age is None:
        return "-"
    
    if age <= 39:
        return f"예 (만 {age}세)"
    else:
        return f"아니오 (만 {age}세)"

def calculate_female_ceo(gender_str: str) -> str:
    """여성대표 여부"""
    if not gender_str:
        return "-"
    
    g = str(gender_str).strip()
    if g == "여성":
        return "예"
    elif g == "남성":
        return "아니오"
    else:
        return "-"

def parse_open_date(open_date_str: str) -> Optional[date]:
    """개업연월 파싱"""
    if not open_date_str:
        return None
    
    s = str(open_date_str).strip().replace(" ", "")
    
    # 형식들: 2022-05, 202205, 2022.05, 2022/05
    patterns = [
        (r'^(\d{4})-(\d{1,2})$', lambda m: (int(m.group(1)), int(m.group(2)))),
        (r'^(\d{4})\.(\d{1,2})$', lambda m: (int(m.group(1)), int(m.group(2)))),
        (r'^(\d{4})/(\d{1,2})$', lambda m: (int(m.group(1)), int(m.group(2)))),
        (r'^(\d{4})(\d{2})$', lambda m: (int(m.group(1)), int(m.group(2)))),
    ]
    
    for pattern, extractor in patterns:
        match = re.match(pattern, s)
        if match:
            try:
                year, month = extractor(match)
                return date(year, month, 1)
            except:
                continue
    
    return None

def calculate_business_age(open_date_str: str) -> str:
    """업력구간 계산"""
    open_dt = parse_open_date(open_date_str)
    if not open_dt:
        return "-"
    
    today = date.today()
    
    # 개업일이 미래면 예비창업
    if open_dt > today:
        return "예비창업"
    
    # 개업 후 경과 월수 계산
    months = (today.year - open_dt.year) * 12 + (today.month - open_dt.month)
    years = months / 12
    
    if years < 1:
        return f"1년 미만 ({months}개월)"
    elif years < 3:
        return f"1년~3년 ({years:.1f}년)"
    elif years < 7:
        return f"3년~7년 ({years:.1f}년)"
    else:
        return f"7년 이상 ({years:.1f}년)"

def is_youth(birthdate_str: str) -> bool:
    """청년 여부 (bool)"""
    age = calculate_age(birthdate_str)
    return age is not None and age <= 39

def is_female(gender_str: str) -> bool:
    """여성 여부 (bool)"""
    return str(gender_str).strip() == "여성"

# ==============================
# 스타일링 (모바일 최적화)
# ==============================
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#002855">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }
  
  :root { 
    --gov-navy: #002855; 
    --gov-blue: #0B5BD3; 
    --success: #10b981; 
    --warning: #f59e0b; 
    --danger: #ef4444; 
  }
  
  #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  
  .block-container { max-width: 1600px; margin: 0 auto !important; padding: 12px; }
  
  /* 브랜드 헤더 */
  .brandbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 24px; margin-bottom: 16px;
    background: linear-gradient(135deg, var(--gov-navy) 0%, #1e40af 100%);
    border-radius: 12px; color: white;
  }
  .brandbar img { height: 48px; }
  .brandbar h1 { margin: 0; color: white; font-weight: 700; font-size: 22px; }
  .brandbar .version { font-size: 12px; opacity: 0.8; color: white; }
  
  /* 오늘 할 일 카드 */
  .todo-section {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .todo-section h3 { color: #92400e; margin: 0 0 12px 0; font-size: 16px; }
  .todo-item {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; margin: 6px 0;
    background: white; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    font-size: 14px;
  }
  .todo-urgent { border-left: 4px solid #ef4444; }
  .todo-important { border-left: 4px solid #f59e0b; }
  .todo-normal { border-left: 4px solid #10b981; }
  
  /* 정책자금 레이더 */
  .radar-section {
    background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
    border: 2px solid #3b82f6;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .radar-section h3 { color: #1e40af; margin: 0 0 12px 0; font-size: 16px; }
  .radar-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 12px; margin: 6px 0;
    background: white; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    font-size: 13px;
  }
  .radar-new { border-left: 4px solid #10b981; }
  .radar-deadline { border-left: 4px solid #ef4444; }
  .radar-hot { border-left: 4px solid #f59e0b; }
  
  /* 파이프라인 카드 */
  .pipeline-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }
  .pipeline-card {
    background: white;
    border: 1px solid rgba(128,128,128,0.2);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }
  .pipeline-card .number { font-size: 28px; font-weight: 700; color: var(--gov-navy); }
  .pipeline-card .label { font-size: 12px; color: #6b7280; margin-top: 4px; }
  .pipeline-card .delta { font-size: 11px; color: var(--success); }
  
  /* 검색 섹션 */
  .search-section {
    background: rgba(128, 128, 128, 0.08);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
  }
  .search-section h3 { color: inherit; margin: 0 0 12px 0; font-size: 16px; }
  
  /* 고객 정보 카드 */
  .info-card {
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 20px;
    margin: 12px 0;
    background: rgba(128, 128, 128, 0.05);
  }
  .info-card h4 {
    color: var(--gov-blue);
    margin: 0 0 16px 0;
    font-weight: 700;
    border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    padding-bottom: 8px;
  }
  
  /* 데이터 그리드 */
  .data-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin: 12px 0;
  }
  .data-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(128, 128, 128, 0.08);
    border-radius: 6px;
    border-left: 4px solid var(--gov-blue);
    font-size: 13px;
  }
  .data-label { font-weight: 600; color: inherit; }
  .data-value { color: inherit; font-weight: 500; }
  
  /* 리스크 표시 */
  .risk-high { border-left-color: var(--danger) !important; background: rgba(239, 68, 68, 0.15) !important; }
  .risk-medium { border-left-color: var(--warning) !important; background: rgba(245, 158, 11, 0.15) !important; }
  .risk-low { border-left-color: var(--success) !important; background: rgba(16, 185, 129, 0.15) !important; }
  
  /* 우대요건 표시 (v3.2 신규) */
  .benefit-yes { border-left-color: #8b5cf6 !important; background: rgba(139, 92, 246, 0.15) !important; }
  .benefit-no { border-left-color: #6b7280 !important; background: rgba(107, 114, 128, 0.08) !important; }
  
  /* 진행률 바 */
  .progress-container {
    background: rgba(128, 128, 128, 0.15);
    height: 16px;
    border-radius: 8px;
    overflow: hidden;
    position: relative;
    margin: 16px 0;
  }
  .progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--gov-navy), var(--gov-blue));
    transition: width 0.3s;
  }
  .progress-text {
    position: absolute;
    width: 100%;
    text-align: center;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    font-weight: 600;
    color: white;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
  }
  
  /* 요약 카드 */
  .summary-card {
    background: rgba(128, 128, 128, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
  }
  .summary-card .label { font-size: 11px; color: #6b7280; margin-bottom: 6px; }
  .summary-card .value { font-size: 16px; font-weight: 700; color: var(--gov-navy); }
  
  /* 상태 뱃지 */
  .status-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 8px;
  }
  .badge-completed { background: #dcfce7; color: #166534; }
  .badge-pending { background: #fef3c7; color: #92400e; }
  .badge-error { background: #fee2e2; color: #991b1b; }
  
  /* 소통 로그 */
  .comm-log-item {
    background: rgba(128, 128, 128, 0.05);
    border-left: 3px solid var(--gov-blue);
    border-radius: 8px;
    padding: 12px 16px;
    margin: 8px 0;
  }
  .comm-log-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .comm-log-author {
    font-weight: 600;
    color: var(--gov-blue);
    font-size: 13px;
  }
  .comm-log-date {
    font-size: 11px;
    color: #6b7280;
  }
  .comm-log-content {
    font-size: 14px;
    line-height: 1.5;
  }
  
  /* 링크 박스 */
  .link-box {
    background: rgba(128, 128, 128, 0.05);
    border: 1px dashed rgba(128, 128, 128, 0.3);
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
  }
  .link-box a {
    color: var(--gov-blue);
    word-break: break-all;
  }
  
  /* 액션 버튼 */
  .action-btn {
    display: inline-block;
    padding: 10px 20px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.2s;
    cursor: pointer;
    border: none;
    margin: 4px;
  }
  .action-btn-primary {
    background: var(--gov-navy);
    color: white;
  }
  .action-btn-primary:hover { background: #001a38; }
  .action-btn-kakao {
    background: #FEE500;
    color: #3C1E1E;
  }
  .action-btn-kakao:hover { background: #e6ce00; }
  
  /* AI 결과 카드 */
  .ai-result-card {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border: 1px solid #86efac;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
  }
  .ai-result-card h4 { color: #166534; margin: 0 0 12px 0; }
  
  /* 점수 표시 */
  .score-display {
    text-align: center;
    padding: 20px;
  }
  .score-number {
    font-size: 48px;
    font-weight: 900;
    color: var(--gov-navy);
  }
  .score-grade {
    font-size: 24px;
    font-weight: 700;
    margin-top: 8px;
  }
  .score-breakdown {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 16px;
  }
  .score-item {
    background: white;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }
  .score-item-label { font-size: 11px; color: #6b7280; }
  .score-item-value { font-size: 20px; font-weight: 700; color: var(--gov-navy); }
  
  /* 고객 테이블 */
  .client-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13px;
  }
  .client-table th {
    background: var(--gov-navy);
    color: white;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
  }
  .client-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(128,128,128,0.2);
  }
  .client-table tr:hover { background: rgba(128,128,128,0.05); }
  
  /* 모바일 반응형 */
  @media (max-width: 768px) {
    .block-container { padding: 8px; }
    .brandbar { flex-direction: column; gap: 8px; text-align: center; padding: 12px 16px; }
    .brandbar h1 { font-size: 18px; }
    .brandbar img { height: 40px; }
    .pipeline-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .pipeline-card .number { font-size: 24px; }
    .data-grid { grid-template-columns: 1fr; }
    .todo-item, .radar-item { font-size: 13px; padding: 8px 10px; }
    .action-btn { padding: 12px 16px; font-size: 14px; width: 100%; display: block; margin: 6px 0; }
    .score-breakdown { grid-template-columns: repeat(2, 1fr); }
  }
  
  /* 터치 최적화 */
  @media (hover: none) and (pointer: coarse) {
    .action-btn { min-height: 44px; }
    .todo-item, .radar-item { min-height: 48px; }
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# Session State 초기화
# ==============================
def init_session_state():
    defaults = {
        "authenticated": False,
        "searched_receipt_no": "",
        "search_result": None,
        "issued_link": None,
        "ai_analysis_result": None,
        "ai_score_result": None,
        "ai_plan_result": None,
        "selected_model": None,
        "result_auth": False,
        "policy_text": None,
        "all_clients": None,
        "all_clients_loaded": False,
        "pipeline_stats": None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ==============================
# 유틸리티 함수
# ==============================
def get_logo_url() -> str:
    return _get_secret("YOUAREPLAN_LOGO_URL", DEFAULT_LOGO_URL)

def format_progress_bar(progress: int) -> str:
    return f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {progress}%"></div>
        <div class="progress-text">{progress}% 완료</div>
    </div>
    """

def create_download_link(content: str, filename: str, content_type: str = "text/plain") -> str:
    b64_content = base64.b64encode(content.encode()).decode()
    return f'<a href="data:{content_type};base64,{b64_content}" download="{filename}" class="action-btn">📥 {filename.split(".")[-1].upper()} 다운로드</a>'

def has_stage3_real_data(stage3_data: Optional[Dict]) -> bool:
    """3차 설문에 실제 데이터가 있는지 판단"""
    if not stage3_data:
        return False
    
    check_fields = [
        'collateral', 'tax_credit', 
        'loan', 'docs',
        'risks', 'priority', 'coach',
        'recommended_fund', 'expected_limit', 'decision_status', 'readiness_score'
    ]
    
    for field in check_fields:
        value = stage3_data.get(field, '')
        if value and str(value).strip():
            return True
    
    return False

# ==============================
# PDF 텍스트 추출 (RAG 준비)
# ==============================
def extract_text_from_pdf(pdf_file) -> Tuple[bool, str]:
    """PDF 파일에서 텍스트 추출"""
    if not HAS_PYPDF:
        return False, "PDF 라이브러리가 설치되지 않았습니다. (pip install pypdf)"
    
    try:
        pdf_reader = PdfReader(pdf_file)
        text_parts = []
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"[페이지 {page_num}]\n{page_text}")
        
        if not text_parts:
            return False, "PDF에서 텍스트를 추출할 수 없습니다."
        
        full_text = "\n\n".join(text_parts)
        return True, full_text
        
    except Exception as e:
        return False, f"PDF 처리 오류: {str(e)}"

def extract_text_from_uploaded_pdf(uploaded_file) -> Tuple[bool, str]:
    """Streamlit 업로드 파일에서 텍스트 추출"""
    if uploaded_file is None:
        return False, "파일이 없습니다."
    
    try:
        pdf_bytes = uploaded_file.read()
        pdf_file = io.BytesIO(pdf_bytes)
        return extract_text_from_pdf(pdf_file)
    except Exception as e:
        return False, f"파일 읽기 오류: {str(e)}"

# ==============================
# API 함수들
# ==============================
def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    """GAS에서 통합 고객 데이터 조회"""
    try:
        payload = {
            "action": "get_integrated_view",
            "receipt_no": receipt_no,
            "api_token": API_TOKEN
        }
        
        response = requests.post(
            INTEGRATED_GAS_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=20
        )
        
        if response.status_code != 200:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
        
        return response.json()
        
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "서버 응답 시간 초과"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def fetch_all_clients() -> Dict[str, Any]:
    """전체 고객 목록 조회 (파이프라인용)"""
    try:
        payload = {
            "action": "get_all_clients",
            "api_token": API_TOKEN
        }
        
        response = requests.post(
            INTEGRATED_GAS_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code != 200:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
        
        result = response.json()
        if result.get("ok"):
            return {"status": "success", "data": result.get("data", [])}
        return {"status": "error", "message": result.get("error", "알 수 없는 오류")}
        
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "서버 응답 시간 초과"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def add_comm_log(receipt_no: str, author: str, content: str) -> Dict[str, Any]:
    """소통 로그 추가"""
    try:
        payload = {
            "action": "add_comm_log",
            "api_token": API_TOKEN,
            "receipt_no": receipt_no,
            "author": author,
            "content": content
        }
        
        response = requests.post(
            INTEGRATED_GAS_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code != 200:
            return {"ok": False, "error": f"HTTP {response.status_code}"}
        
        result = response.json()
        return {"ok": result.get("ok", False), "error": result.get("error")}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

def issue_second_link(receipt_no: str, hours: int = 24) -> Dict[str, Any]:
    """2차 설문 링크 발급"""
    try:
        payload = {
            "action": "issue_token",
            "api_token": API_TOKEN,
            "receipt_no": receipt_no,
            "hours": hours
        }
        
        response = requests.post(
            INTEGRATED_GAS_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code != 200:
            return {"ok": False, "error": f"HTTP {response.status_code}"}
        
        result = response.json()
        if result.get("ok"):
            return {
                "ok": True,
                "link": result.get("link"),
                "expires_at": result.get("expires_at")
            }
        return {"ok": False, "error": result.get("error", "알 수 없는 오류")}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ==============================
# Gemini AI 함수들
# ==============================
def calc_model_score(model_name: str) -> int:
    """모델 우선순위 점수 계산"""
    score = 0
    name_lower = model_name.lower()
    
    version_match = re.search(r'gemini[- ]?(\d+)\.(\d+)', name_lower)
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        score += (major * 10000) + (minor * 1000)
    
    if 'ultra' in name_lower:
        score += 3000
    elif 'pro' in name_lower:
        score += 2000
    elif 'flash' in name_lower:
        score += 400
    
    date_match = re.search(r'(\d{2})-(\d{2})', name_lower)
    if date_match:
        month = int(date_match.group(1))
        day = int(date_match.group(2))
        score += (month * 10) + day
    
    if 'exp' in name_lower:
        score += 10
    if 'latest' in name_lower:
        score += 50
    
    return score

def get_available_gemini_models() -> List[Dict[str, Any]]:
    """사용 가능한 Gemini 모델 목록 조회"""
    if not GEMINI_API_KEY:
        return []
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        models = []
        
        for model in data.get("models", []):
            name = model.get("name", "").replace("models/", "")
            
            methods = model.get("supportedGenerationMethods", [])
            if "generateContent" not in methods:
                continue
            
            if not name.lower().startswith("gemini"):
                continue
            
            score = calc_model_score(name)
            models.append({
                "name": name,
                "score": score,
                "display_name": model.get("displayName", name)
            })
        
        models.sort(key=lambda x: x["score"], reverse=True)
        return models
        
    except Exception:
        return []

def get_best_gemini_model() -> str:
    """최적의 Gemini 모델 선택"""
    models = get_available_gemini_models()
    if models:
        return models[0]["name"]
    return "gemini-1.5-flash"

def call_gemini_api(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> Dict[str, Any]:
    """Gemini API 공통 호출 함수"""
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY가 설정되지 않았습니다."}
    
    best_model = get_best_gemini_model()
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{best_model}:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "parts": [{"text": user_prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096
            }
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            return {"ok": False, "error": f"API 오류: HTTP {response.status_code}"}
        
        result = response.json()
        
        candidates = result.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return {"ok": True, "text": parts[0].get("text", ""), "model": best_model}
        
        return {"ok": False, "error": "응답 파싱 실패"}
        
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "API 응답 시간 초과 (60초)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def call_gemini_analysis(doc_content: str) -> Dict[str, Any]:
    """Gemini AI 심층 분석"""
    system_prompt = """
**역할(Role):**
당신은 '유아플랜'의 수석 정책자금 컨설턴트이자 심사역입니다.
제공된 고객의 재무 데이터, 신용 상태, 사업 이력을 냉철하게 분석하여 실현 가능한 자금을 제안해야 합니다.

**지침(Guidelines):**
1. 매출액보다는 '상환 능력'과 '사업의 지속성'을 중심으로 평가하십시오.
2. '세금 체납', '연체 이력'이 있다면 승인 가능성을 낮게 평가하고 해결책을 먼저 제시하십시오.
3. 반드시 [종합 요약] -> [추천 자금 TOP 3] -> [승인 가능성 및 리스크] -> [준비 서류 가이드] 순서로 작성하십시오.
4. 전문적이고 현실적인 조언을 제공하십시오.
5. 희망 고문보다는 냉정한 현실 분석을 우선하십시오.
6. 청년(만39세 이하)이나 여성대표는 가점 대상임을 언급하십시오.
"""
    user_prompt = f"아래 고객 정보를 바탕으로 심층 분석 보고서를 작성해주세요.\n\n[고객 정보 데이터]\n{doc_content}"
    
    result = call_gemini_api(system_prompt, user_prompt, 0.4)
    if result.get("ok"):
        return {"ok": True, "analysis": result.get("text"), "model": result.get("model")}
    return result

def call_gemini_scoring(doc_content: str) -> Dict[str, Any]:
    """Gemini AI 점수화 분석"""
    system_prompt = """
**역할(Role):**
당신은 정책자금 심사 점수화 전문가입니다.

**출력 형식 (반드시 JSON으로):**
```json
{
  "total_score": 75,
  "breakdown": {
    "financial": {"score": 80, "max": 100, "comment": "매출 안정적"},
    "growth": {"score": 70, "max": 100, "comment": "성장 가능성 보통"},
    "stability": {"score": 85, "max": 100, "comment": "업력 3년 이상"},
    "risk": {"score": 65, "max": 100, "comment": "부채비율 주의"},
    "bonus": {"score": 10, "max": 10, "comment": "청년+여성 가점"}
  },
  "grade": "B+",
  "recommendation": "소상공인정책자금 일반경영안정자금 추천",
  "caution": "부채비율 200% 초과로 한도 제한 가능"
}
```

**점수 기준:**
- 90점 이상: A등급 (정책자금 적극 추천)
- 80-89점: B등급 (정책자금 추천)
- 70-79점: C등급 (조건부 추천)
- 60-69점: D등급 (보완 후 재도전)
- 60점 미만: F등급 (현재 신청 불가)

**가점 기준:**
- 청년(만39세 이하): +5점
- 여성대표: +5점
"""
    user_prompt = f"아래 고객 정보를 점수화해주세요. 반드시 JSON 형식으로만 응답하세요.\n\n{doc_content}"
    
    result = call_gemini_api(system_prompt, user_prompt, 0.2)
    if result.get("ok"):
        try:
            text = result.get("text", "")
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = text
            
            score_data = json.loads(json_str)
            return {"ok": True, "score_data": score_data, "model": result.get("model")}
        except json.JSONDecodeError:
            return {"ok": True, "score_data": None, "raw_text": result.get("text"), "model": result.get("model")}
    return result

def call_gemini_business_plan(doc_content: str, fund_name: str = "") -> Dict[str, Any]:
    """Gemini AI 사업계획서 초안 생성"""
    system_prompt = """
**역할(Role):**
당신은 정책자금 사업계획서 작성 전문가입니다.

**작성 형식:**
1. 사업 개요 (200자 이내)
2. 대표자 및 조직 현황
3. 사업 아이템 소개
4. 시장 분석 및 경쟁력
5. 자금 사용 계획 (항목별 금액)
6. 기대 효과 (고용창출, 매출증가 등)
7. 향후 계획 (1년/3년)

**주의사항:**
- 구체적인 숫자와 근거를 포함하세요.
- 정책자금 심사위원이 읽는다고 가정하세요.
- 과장 없이 현실적으로 작성하세요.
"""
    fund_info = f"[신청 예정 자금: {fund_name}]\n" if fund_name else ""
    user_prompt = f"{fund_info}아래 고객 정보를 바탕으로 사업계획서 초안을 작성해주세요.\n\n{doc_content}"
    
    result = call_gemini_api(system_prompt, user_prompt, 0.5)
    if result.get("ok"):
        return {"ok": True, "plan": result.get("text"), "model": result.get("model")}
    return result

# ==============================
# 문서 생성 (v3.2 수정 - 우대요건 추가)
# ==============================
def generate_doc_content(data: Dict[str, Any]) -> str:
    """AI 분석용 문서 생성"""
    receipt_no = data.get("receipt_no", "")
    stage1 = data.get("stage1", {})
    stage2 = data.get("stage2", {})
    stage3 = data.get("stage3", {})
    
    current_date = datetime.now().strftime("%Y.%m.%d")
    
    # 우대요건 계산 (v3.2 신규)
    birthdate = stage1.get('birthdate', '') if stage1 else ''
    gender = stage1.get('gender', '') if stage1 else ''
    open_date = stage1.get('open_date', '') if stage1 else ''
    
    youth_status = calculate_youth_status(birthdate)
    female_status = calculate_female_ceo(gender)
    business_age = calculate_business_age(open_date)
    
    content = f"""================================
유아플랜 고객정보 종합보고서
================================
접수번호: {receipt_no}
작성일자: {current_date}

[기본정보]
- 고객명: {stage1.get('name', '정보없음') if stage1 else '정보없음'}
- 연락처: {stage1.get('phone', '정보없음') if stage1 else '정보없음'}
- 이메일: {stage1.get('email', '미입력') if stage1 and stage1.get('email') else '미입력'}
- 생년월일: {birthdate if birthdate else '미입력'}
- 성별: {gender if gender else '미입력'}
- 사업형태: {stage1.get('business_type', '정보없음') if stage1 else '정보없음'}
- 업종: {stage1.get('industry', '정보없음') if stage1 else '정보없음'}
- 지역: {stage1.get('region', '정보없음') if stage1 else '정보없음'}
- 직원수: {stage1.get('employee_count', '정보없음') if stage1 else '정보없음'}
- 개업연월: {open_date if open_date else '미입력'}
- 필요자금: {stage1.get('funding_amount', '정보없음') if stage1 else '정보없음'}
- 정책자금경험: {stage1.get('policy_experience', '정보없음') if stage1 else '정보없음'}

[우대요건] ★
- 청년여부: {youth_status}
- 여성대표: {female_status}
- 업력구간: {business_age}

[재무현황]
"""
    
    if stage2:
        content += f"""- 사업자명: {stage2.get('company_name', '-')}
- 사업자등록번호: {stage2.get('biz_no', '-')}
- 사업시작일: {stage2.get('startup_date', '-')}
- 당해연도매출: {stage2.get('revenue_current', '-')}만원
- 전년도매출: {stage2.get('revenue_y1', '-')}만원
- 전전년도매출: {stage2.get('revenue_y2', '-')}만원
- 자본금: {stage2.get('capital', '-')}만원
- 부채: {stage2.get('debt', '-')}만원
- 정책자금이력: {stage2.get('past_policy_fund', '-')}
"""
    else:
        content += "- 2차 설문 미완료\n"
    
    content += f"""
[자격현황]
- 세금체납: {stage1.get('tax_status', '정보없음') if stage1 else '정보없음'}
- 금융연체: {stage1.get('credit_status', '정보없음') if stage1 else '정보없음'}
- 영업상태: {stage1.get('business_status', '정보없음') if stage1 else '정보없음'}

[3차 심층진단]
"""
    
    if stage3 and has_stage3_real_data(stage3):
        content += f"""- 담보/보증: {stage3.get('collateral', '-')}
- 세무/신용: {stage3.get('tax_credit', '-')}
- 대출현황: {stage3.get('loan', '-')}
- 준비서류: {stage3.get('docs', '-')}
- 우대/제외: {stage3.get('priority', '-')}
- 리스크TOP3: {stage3.get('risks', '-')}
- 컨설턴트메모: {stage3.get('coach', '-')}
- 추천자금: {stage3.get('recommended_fund', '-')}
- 예상한도: {stage3.get('expected_limit', '-')}만원
- 진행상태: {stage3.get('decision_status', '-')}
- 준비도점수: {stage3.get('readiness_score', '-')}
"""
    else:
        content += "- 3차 설문 미완료\n"
    
    content += "\n================================\n"
    
    return content

# ==============================
# 파이프라인 통계 계산
# ==============================
def calculate_pipeline_stats(clients: List[Dict]) -> Dict[str, int]:
    """파이프라인 통계 계산"""
    if not clients:
        return {"total": 0, "progress": 0, "new_week": 0, "completed": 0}
    
    total = len(clients)
    progress = 0
    new_week = 0
    completed = 0
    
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    for client in clients:
        risk = client.get("risk", "")
        date_str = client.get("date", "")
        
        if not risk:
            progress += 1
        
        if "계약" in str(risk):
            completed += 1
        
        try:
            if date_str:
                client_date = datetime.strptime(date_str[:10], "%Y-%m-%d") if "-" in date_str else datetime.strptime(date_str[:10], "%Y. %m. %d")
                if client_date >= week_ago:
                    new_week += 1
        except:
            pass
    
    return {
        "total": total,
        "progress": progress,
        "new_week": new_week,
        "completed": completed
    }

# ==============================
# 렌더링 함수들
# ==============================
def render_todo_section(clients: List[Dict]) -> None:
    """오늘 할 일 섹션"""
    st.markdown("""
    <div class="todo-section">
        <h3>📋 오늘 할 일</h3>
    """, unsafe_allow_html=True)
    
    urgent_count = 0
    if clients:
        for client in clients[:5]:
            risk = client.get("risk", "")
            if risk and "체납" in risk:
                urgent_count += 1
    
    if urgent_count > 0:
        st.markdown(f"""
        <div class="todo-item todo-urgent">
            <span>🚨</span>
            <span>체납/연체 고객 {urgent_count}건 점검 필요</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="todo-item todo-important">
            <span>📞</span>
            <span>신규 상담 전화 콜백</span>
        </div>
        <div class="todo-item todo-normal">
            <span>📝</span>
            <span>2차 설문 링크 발송</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_radar_section() -> None:
    """정책자금 레이더 섹션"""
    st.markdown("""
    <div class="radar-section">
        <h3>📡 정책자금 레이더</h3>
        <div class="radar-item radar-new">
            <span>🆕 소상공인정책자금 2차 접수</span>
            <span>~12/31</span>
        </div>
        <div class="radar-item radar-hot">
            <span>🔥 청년창업사관학교 15기</span>
            <span>모집중</span>
        </div>
        <div class="radar-item radar-deadline">
            <span>⏰ 기술보증기금 혁신스타트업</span>
            <span>D-7</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_pipeline_section(stats: Dict[str, int]) -> None:
    """파이프라인 현황 섹션"""
    if not stats:
        stats = {"total": 0, "progress": 0, "new_week": 0, "completed": 0}
    
    st.markdown(f"""
    <div class="pipeline-grid">
        <div class="pipeline-card">
            <div class="number">{stats['total']}</div>
            <div class="label">전체 고객</div>
        </div>
        <div class="pipeline-card">
            <div class="number">{stats['progress']}</div>
            <div class="label">진행중</div>
        </div>
        <div class="pipeline-card">
            <div class="number">{stats['new_week']}</div>
            <div class="label">이번주 신규</div>
        </div>
        <div class="pipeline-card">
            <div class="number">{stats['completed']}</div>
            <div class="label">계약 완료</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_stage_card(title: str, stage_data: Optional[Dict], stage_num: int) -> None:
    """설문 단계별 카드 렌더링 (v3.2 수정)"""
    if stage_num == 3:
        has_data = has_stage3_real_data(stage_data)
    else:
        has_data = bool(stage_data)
    
    status_class = "badge-completed" if has_data else "badge-pending"
    status_text = "완료" if has_data else "미완료"
    
    st.markdown(f"""
    <div class="info-card">
        <h4>{title} <span class="status-badge {status_class}">{status_text}</span></h4>
    """, unsafe_allow_html=True)
    
    if has_data and stage_data:
        if stage_num == 1:
            # 기본 정보
            st.markdown(f"""
            <div class="data-grid">
                <div class="data-item"><span class="data-label">성함</span><span class="data-value">{stage_data.get('name', '-')}</span></div>
                <div class="data-item"><span class="data-label">연락처</span><span class="data-value">{stage_data.get('phone', '-')}</span></div>
                <div class="data-item"><span class="data-label">지역</span><span class="data-value">{stage_data.get('region', '-')}</span></div>
                <div class="data-item"><span class="data-label">업종</span><span class="data-value">{stage_data.get('industry', '-')}</span></div>
                <div class="data-item"><span class="data-label">사업형태</span><span class="data-value">{stage_data.get('business_type', '-')}</span></div>
                <div class="data-item"><span class="data-label">직원수</span><span class="data-value">{stage_data.get('employee_count', '-')}</span></div>
                <div class="data-item"><span class="data-label">연매출</span><span class="data-value">{stage_data.get('revenue', '-')}</span></div>
                <div class="data-item"><span class="data-label">필요자금</span><span class="data-value">{stage_data.get('funding_amount', '-')}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            # 대표자 정보 (v3.2 신규)
            birthdate = stage_data.get('birthdate', '')
            gender = stage_data.get('gender', '')
            open_date = stage_data.get('open_date', '')
            policy_exp = stage_data.get('policy_experience', '')
            
            if birthdate or gender or open_date:
                st.markdown(f"""
                <h5 style="margin: 16px 0 8px 0; font-size: 14px;">👤 대표자 정보</h5>
                <div class="data-grid">
                    <div class="data-item"><span class="data-label">생년월일</span><span class="data-value">{birthdate if birthdate else '-'}</span></div>
                    <div class="data-item"><span class="data-label">성별</span><span class="data-value">{gender if gender else '-'}</span></div>
                    <div class="data-item"><span class="data-label">개업연월</span><span class="data-value">{open_date if open_date else '-'}</span></div>
                    <div class="data-item"><span class="data-label">정책자금경험</span><span class="data-value">{policy_exp if policy_exp else '-'}</span></div>
                </div>
                """, unsafe_allow_html=True)
            
            # 우대요건 계산 및 표시 (v3.2 신규)
            youth_status = calculate_youth_status(birthdate)
            female_status = calculate_female_ceo(gender)
            business_age = calculate_business_age(open_date)
            
            youth_class = "benefit-yes" if is_youth(birthdate) else "benefit-no"
            female_class = "benefit-yes" if is_female(gender) else "benefit-no"
            
            st.markdown(f"""
            <h5 style="margin: 16px 0 8px 0; font-size: 14px;">⭐ 우대요건 (자동계산)</h5>
            <div class="data-grid">
                <div class="data-item {youth_class}"><span class="data-label">청년여부</span><span class="data-value">{youth_status}</span></div>
                <div class="data-item {female_class}"><span class="data-label">여성대표</span><span class="data-value">{female_status}</span></div>
                <div class="data-item"><span class="data-label">업력구간</span><span class="data-value">{business_age}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            # 자격 현황
            tax_status = stage_data.get('tax_status', '체납 없음')
            credit_status = stage_data.get('credit_status', '연체 없음')
            biz_status = stage_data.get('business_status', '정상 영업')
            
            tax_class = "risk-high" if tax_status != '체납 없음' else "risk-low"
            credit_class = "risk-high" if credit_status != '연체 없음' else "risk-low"
            biz_class = "risk-high" if biz_status != '정상 영업' else "risk-low"
            
            st.markdown(f"""
            <h5 style="margin: 16px 0 8px 0; font-size: 14px;">⚠️ 자격 현황</h5>
            <div class="data-grid">
                <div class="data-item {tax_class}"><span class="data-label">세금 체납</span><span class="data-value">{tax_status}</span></div>
                <div class="data-item {credit_class}"><span class="data-label">금융 연체</span><span class="data-value">{credit_status}</span></div>
                <div class="data-item {biz_class}"><span class="data-label">영업 상태</span><span class="data-value">{biz_status}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        elif stage_num == 2:
            st.markdown(f"""
            <div class="data-grid">
                <div class="data-item"><span class="data-label">사업자명</span><span class="data-value">{stage_data.get('company_name', '-')}</span></div>
                <div class="data-item"><span class="data-label">사업시작일</span><span class="data-value">{stage_data.get('startup_date', '-')}</span></div>
                <div class="data-item"><span class="data-label">사업자등록번호</span><span class="data-value">{stage_data.get('biz_no', '-')}</span></div>
            </div>
            <h5 style="margin: 16px 0 8px 0; font-size: 14px;">💰 재무현황</h5>
            <div class="data-grid">
                <div class="data-item"><span class="data-label">당해연도 매출</span><span class="data-value">{stage_data.get('revenue_current', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">전년도 매출</span><span class="data-value">{stage_data.get('revenue_y1', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">전전년도 매출</span><span class="data-value">{stage_data.get('revenue_y2', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">자본금</span><span class="data-value">{stage_data.get('capital', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">부채</span><span class="data-value">{stage_data.get('debt', '-')}만원</span></div>
            </div>
            <h5 style="margin: 16px 0 8px 0; font-size: 14px;">📋 정책자금 이력</h5>
            <div class="data-grid">
                <div class="data-item"><span class="data-label">수혜 이력</span><span class="data-value">{stage_data.get('past_policy_fund', '-')}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        elif stage_num == 3:
            fields = [
                ("담보/보증 계획", stage_data.get('collateral', '')),
                ("세무/신용 상태", stage_data.get('tax_credit', '')),
                ("기존 대출 현황", stage_data.get('loan', '')),
                ("준비 서류", stage_data.get('docs', '')),
                ("우대/제외 요건", stage_data.get('priority', '')),
                ("리스크 Top3", stage_data.get('risks', '')),
                ("컨설턴트 메모", stage_data.get('coach', ''))
            ]
            
            # 의사결정 메타데이터 필드
            decision_fields = [
                ("🎯 추천자금", stage_data.get('recommended_fund', '')),
                ("💰 예상한도", f"{stage_data.get('expected_limit', '')}만원" if stage_data.get('expected_limit') else ''),
                ("📊 진행상태", stage_data.get('decision_status', '')),
                ("⭐ 준비도점수", f"{stage_data.get('readiness_score', '')}/5" if stage_data.get('readiness_score') else '')
            ]
            
            for label, value in fields:
                if value and str(value).strip():
                    st.markdown(f"""
                    <div class="data-item" style="margin: 6px 0; flex-direction: column; align-items: flex-start;">
                        <span class="data-label">{label}</span>
                        <span class="data-value" style="margin-top: 4px;">{value}</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            # 의사결정 메타데이터 표시 (값이 있는 경우만)
            has_decision_data = any(v and str(v).strip() and v != '만원' for _, v in decision_fields)
            if has_decision_data:
                st.markdown('<h5 style="margin: 16px 0 8px 0; font-size: 14px; color: #ff9800;">🎯 의사결정 기록</h5>', unsafe_allow_html=True)
                for label, value in decision_fields:
                    if value and str(value).strip() and value != '만원':
                        st.markdown(f"""
                        <div class="data-item" style="margin: 6px 0; background: rgba(255, 152, 0, 0.1); padding: 8px; border-radius: 4px;">
                            <span class="data-label">{label}</span>
                            <span class="data-value">{value}</span>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="opacity: 0.6; font-style: italic; padding: 16px; font-size: 13px;">아직 설문이 완료되지 않았습니다.</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_summary_cards(data: Dict[str, Any]) -> None:
    """요약 카드 렌더링 (v3.2 수정 - 5번째 컬럼 추가)"""
    stage1 = data.get("stage1", {})
    stage2 = data.get("stage2", {})
    
    # 우대요건 계산
    birthdate = stage1.get('birthdate', '') if stage1 else ''
    gender = stage1.get('gender', '') if stage1 else ''
    
    youth_ok = is_youth(birthdate)
    female_ok = is_female(gender)
    
    # 우대요건 텍스트
    benefits = []
    if youth_ok:
        benefits.append("청년")
    if female_ok:
        benefits.append("여성")
    benefit_text = "+".join(benefits) if benefits else "-"
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">업종</div>
            <div class="value">{stage1.get('industry', '-') if stage1 else '-'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">사업형태</div>
            <div class="value">{stage1.get('business_type', '-') if stage1 else '-'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">필요자금</div>
            <div class="value">{stage1.get('funding_amount', '-') if stage1 else '-'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        revenue = stage2.get('revenue_current', '-') if stage2 else '-'
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">당해 매출</div>
            <div class="value">{revenue}{'만원' if revenue != '-' else ''}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        # 우대요건 (v3.2 신규)
        benefit_style = "color: #8b5cf6; font-weight: 700;" if benefits else ""
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">우대요건</div>
            <div class="value" style="{benefit_style}">{benefit_text}</div>
        </div>
        """, unsafe_allow_html=True)

def render_comm_logs_section(comm_logs: List[Dict], receipt_no: str) -> None:
    """소통 로그 섹션"""
    st.markdown("### 📝 소통 로그")
    
    with st.expander("✏️ 새 로그 작성", expanded=False):
        with st.form("comm_log_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 3])
            with col1:
                author = st.selectbox("작성자", ["대표", "담당자", "고객", "시스템"])
            with col2:
                content = st.text_area("내용", placeholder="소통 내용을 입력하세요...", height=100)
            
            submitted = st.form_submit_button("💾 로그 저장", type="primary")
            
            if submitted and content:
                result = add_comm_log(receipt_no, author, content)
                if result.get("ok"):
                    st.success("✅ 로그가 저장되었습니다.")
                    st.session_state.search_result = fetch_integrated_data(receipt_no)
                    st.rerun()
                else:
                    st.error(f"❌ 저장 실패: {result.get('error')}")
    
    if comm_logs:
        for log in comm_logs:
            st.markdown(f"""
            <div class="comm-log-item">
                <div class="comm-log-header">
                    <span class="comm-log-author">{log.get('author', '알수없음')}</span>
                    <span class="comm-log-date">{log.get('created_at', '')}</span>
                </div>
                <div class="comm-log-content">{log.get('content', '')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📭 아직 소통 로그가 없습니다.")

def render_link_issue_section(receipt_no: str, customer_name: str) -> None:
    """2차 설문 링크 발급 섹션"""
    st.markdown("### 🔗 2차 설문 링크 발급")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        hours = st.selectbox("유효시간", [6, 12, 24], index=2, format_func=lambda x: f"{x}시간")
    
    with col2:
        if st.button("🎫 링크 발급", type="primary"):
            with st.spinner("링크 발급 중..."):
                result = issue_second_link(receipt_no, hours)
                if result.get("ok"):
                    st.session_state.issued_link = result.get("link")
                    st.success("✅ 링크가 발급되었습니다!")
                else:
                    st.error(f"❌ 발급 실패: {result.get('error')}")
    
    if st.session_state.issued_link:
        st.markdown(f"""
        <div class="link-box">
            <strong>🔗 2차 설문 링크 (고객 전달용)</strong><br>
            <a href="{st.session_state.issued_link}" target="_blank">{st.session_state.issued_link}</a>
        </div>
        """, unsafe_allow_html=True)
        st.code(st.session_state.issued_link)

def render_ai_analysis_section(data: Dict[str, Any]) -> None:
    """AI 분석 섹션"""
    st.markdown("### 🤖 AI 분석")
    
    if not GEMINI_API_KEY:
        st.warning("⚠️ GEMINI_API_KEY가 설정되지 않아 AI 분석을 사용할 수 없습니다.")
        return
    
    doc_content = generate_doc_content(data)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 심층 분석", use_container_width=True):
            with st.spinner("AI 분석 중... (최대 60초)"):
                result = call_gemini_analysis(doc_content)
                st.session_state.ai_analysis_result = result
    
    with col2:
        if st.button("🎯 점수화", use_container_width=True):
            with st.spinner("점수 계산 중..."):
                result = call_gemini_scoring(doc_content)
                st.session_state.ai_score_result = result
    
    with col3:
        if st.button("📝 사업계획서", use_container_width=True):
            with st.spinner("사업계획서 초안 생성 중..."):
                result = call_gemini_business_plan(doc_content)
                st.session_state.ai_plan_result = result
    
    # 분석 결과 표시
    if st.session_state.ai_analysis_result:
        result = st.session_state.ai_analysis_result
        if result.get("ok"):
            st.markdown(f"""
            <div class="ai-result-card">
                <h4>📊 AI 심층 분석 결과 (모델: {result.get('model', 'unknown')})</h4>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(result.get("analysis", ""))
        else:
            st.error(f"❌ 분석 실패: {result.get('error')}")
    
    if st.session_state.ai_score_result:
        result = st.session_state.ai_score_result
        if result.get("ok"):
            score_data = result.get("score_data")
            if score_data:
                st.markdown(f"""
                <div class="ai-result-card">
                    <h4>🎯 AI 점수화 결과 (모델: {result.get('model', 'unknown')})</h4>
                    <div class="score-display">
                        <div class="score-number">{score_data.get('total_score', '-')}점</div>
                        <div class="score-grade">{score_data.get('grade', '-')}등급</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                breakdown = score_data.get("breakdown", {})
                if breakdown:
                    cols = st.columns(len(breakdown))
                    for i, (key, val) in enumerate(breakdown.items()):
                        with cols[i]:
                            st.metric(key, f"{val.get('score', '-')}/{val.get('max', 100)}")
                
                if score_data.get("recommendation"):
                    st.info(f"💡 추천: {score_data.get('recommendation')}")
                if score_data.get("caution"):
                    st.warning(f"⚠️ 주의: {score_data.get('caution')}")
            else:
                st.markdown(result.get("raw_text", ""))
        else:
            st.error(f"❌ 점수화 실패: {result.get('error')}")
    
    if st.session_state.ai_plan_result:
        result = st.session_state.ai_plan_result
        if result.get("ok"):
            st.markdown(f"""
            <div class="ai-result-card">
                <h4>📝 사업계획서 초안 (모델: {result.get('model', 'unknown')})</h4>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(result.get("plan", ""))
        else:
            st.error(f"❌ 생성 실패: {result.get('error')}")

def render_pdf_upload_section() -> None:
    """PDF 업로드 섹션"""
    st.markdown("### 📄 PDF 문서 분석 (RAG)")
    
    uploaded_file = st.file_uploader("PDF 파일 업로드", type=['pdf'], key="pdf_uploader")
    
    if uploaded_file:
        if st.button("📖 텍스트 추출"):
            with st.spinner("PDF 분석 중..."):
                success, result = extract_text_from_uploaded_pdf(uploaded_file)
                if success:
                    st.session_state.policy_text = result
                    st.success(f"✅ {len(result)}자 추출 완료")
                else:
                    st.error(f"❌ {result}")
    
    if st.session_state.policy_text:
        with st.expander("추출된 텍스트 보기"):
            st.text_area("PDF 내용", st.session_state.policy_text, height=300)

def render_result_save_section(receipt_no: str) -> None:
    """결과 저장 섹션 (대표 전용)"""
    st.markdown("### 🏆 정책자금 결과 저장 (대표 전용)")
    
    if not RESULT_PASSWORD:
        st.info("💡 결과 저장 기능을 사용하려면 RESULT_PW 환경변수를 설정하세요.")
        return
    
    if not st.session_state.result_auth:
        with st.form("result_auth_form"):
            result_pw_input = st.text_input("대표 비밀번호", type="password")
            if st.form_submit_button("🔓 인증"):
                if result_pw_input == RESULT_PASSWORD:
                    st.session_state.result_auth = True
                    st.success("✅ 인증 완료")
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 올바르지 않습니다.")
        return
    
    with st.form("result_save_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            policy_name = st.text_input("승인된 정책자금명", placeholder="예: 소상공인정책자금")
            approved_amount = st.text_input("승인금액 (만원)", placeholder="예: 5000")
        
        with col2:
            approval_date = st.date_input("승인일자")
            result_memo = st.text_area("메모", placeholder="특이사항", height=80)
        
        submitted = st.form_submit_button("💾 결과 저장", type="primary")
        
        if submitted:
            if policy_name and approved_amount:
                content = f"[정책자금 결과] {policy_name} / {approved_amount}만원 / 승인일: {approval_date}"
                if result_memo:
                    content += f" / 메모: {result_memo}"
                
                result = add_comm_log(receipt_no, "대표", content)
                if result.get("ok"):
                    st.success(f"✅ 결과 저장 완료")
                    st.session_state.search_result = fetch_integrated_data(receipt_no)
                    st.rerun()
                else:
                    st.error(f"❌ 저장 실패: {result.get('error')}")
            else:
                st.warning("정책자금명과 승인금액은 필수입니다.")

# ==============================
# 메인 함수
# ==============================
def main():
    logo_url = get_logo_url()
    current_time = datetime.now().strftime("%Y.%m.%d %H:%M")
    
    # ========== 비밀번호 인증 ==========
    if not st.session_state.authenticated:
        st.markdown(f"""
        <div class="brandbar">
            <div style="display: flex; align-items: center; gap: 16px;">
                {f'<img src="{logo_url}" alt="{BRAND_NAME} 로고" />' if logo_url else ''}
                <h1>📊 유아플랜 컨설턴트 대시보드</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔐 접속 인증")
        
        with st.form("login_form"):
            password_input = st.text_input("비밀번호", type="password")
            submit = st.form_submit_button("🔓 로그인", type="primary")
            
            if submit:
                if password_input == DASHBOARD_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 올바르지 않습니다.")
        return
    
    # ========== 메인 대시보드 ==========
    
    # 헤더
    st.markdown(f"""
    <div class="brandbar">
        <div style="display: flex; align-items: center; gap: 16px;">
            {f'<img src="{logo_url}" alt="{BRAND_NAME} 로고" />' if logo_url else ''}
            <h1>📊 유아플랜 컨설턴트 대시보드</h1>
        </div>
        <div class="version">
            <div>v3.4-full-sync</div>
            <div style="font-size: 11px; opacity: 0.7;">{current_time}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 로그아웃
    col_spacer, col_logout = st.columns([8, 1])
    with col_logout:
        if st.button("🚪 로그아웃"):
            st.session_state.authenticated = False
            st.session_state.result_auth = False
            st.rerun()
    
    # ========== 전체 고객 데이터 로드 (파이프라인용) ==========
    if not st.session_state.all_clients_loaded:
        with st.spinner("📊 데이터 로딩..."):
            result = fetch_all_clients()
            if result.get("status") == "success":
                st.session_state.all_clients = result.get("data", [])
                st.session_state.pipeline_stats = calculate_pipeline_stats(st.session_state.all_clients)
            st.session_state.all_clients_loaded = True
    
    # ========== 오늘 할 일 + 레이더 ==========
    col_todo, col_radar = st.columns(2)
    with col_todo:
        render_todo_section(st.session_state.all_clients)
    with col_radar:
        render_radar_section()
    
    # ========== 파이프라인 ==========
    render_pipeline_section(st.session_state.pipeline_stats)
    
    # ========== 1차 설문 링크 ==========
    with st.expander("📋 1차 설문 링크 (신규 고객용)", expanded=False):
        st.markdown(f"""
        <div class="link-box">
            <strong>📎 신규 고객 1차 설문</strong><br>
            <a href="{FIRST_SURVEY_URL}" target="_blank">{FIRST_SURVEY_URL}</a>
        </div>
        """, unsafe_allow_html=True)
        st.code(FIRST_SURVEY_URL)
    
    # ========== 고객 조회 ==========
    st.markdown("""
    <div class="search-section">
        <h3>🔍 고객 통합 정보 조회</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        receipt_no_input = st.text_input(
            "접수번호",
            value=st.session_state.searched_receipt_no,
            placeholder="예: YP12091234",
            label_visibility="collapsed"
        )
    
    with col2:
        search_clicked = st.button("🔍 조회", type="primary", use_container_width=True)
    
    with col3:
        if st.button("🔄 새로고침", use_container_width=True):
            if st.session_state.searched_receipt_no:
                st.session_state.search_result = fetch_integrated_data(st.session_state.searched_receipt_no)
            st.session_state.all_clients_loaded = False
            st.rerun()
    
    if search_clicked and receipt_no_input:
        st.session_state.searched_receipt_no = receipt_no_input.strip()
        st.session_state.issued_link = None
        st.session_state.ai_analysis_result = None
        st.session_state.ai_score_result = None
        st.session_state.ai_plan_result = None
        st.session_state.result_auth = False
        
        with st.spinner("🔄 조회 중..."):
            st.session_state.search_result = fetch_integrated_data(receipt_no_input.strip())
    
    # ========== 조회 결과 ==========
    if st.session_state.search_result:
        result = st.session_state.search_result
        
        if result.get("status") == "success":
            data = result.get("data", {})
            receipt_no = data.get("receipt_no", "")
            progress = data.get("progress_pct", 0)
            stage1 = data.get("stage1")
            stage2 = data.get("stage2")
            stage3 = data.get("stage3")
            comm_logs = data.get("comm_logs", [])
            
            customer_name = stage1.get("name", "-") if stage1 else "-"
            
            st.markdown("---")
            
            col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
            with col_h1:
                st.markdown(f"### 👤 {customer_name}")
            with col_h2:
                st.markdown(f"**접수번호:** `{receipt_no}`")
            with col_h3:
                st.markdown(f"**진행률:** {progress}%")
            
            st.markdown(format_progress_bar(progress), unsafe_allow_html=True)
            render_summary_cards(data)
            
            st.markdown("---")
            render_link_issue_section(receipt_no, customer_name)
            
            with st.expander("📝 상세 데이터 (1차/2차/3차)", expanded=False):
                render_stage_card("1️⃣ 1차 설문", stage1, 1)
                render_stage_card("2️⃣ 2차 설문", stage2, 2)
                render_stage_card("3️⃣ 3차 설문", stage3, 3)
            
            render_comm_logs_section(comm_logs, receipt_no)
            
            st.markdown("---")
            render_ai_analysis_section(data)
            
            st.markdown("---")
            render_pdf_upload_section()
            
            st.markdown("---")
            render_result_save_section(receipt_no)
            
            st.markdown("---")
            
            # 고객 연락
            st.markdown("### 📞 고객 연락")
            if stage1:
                phone = stage1.get('phone', '')
                if phone:
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.markdown(f'<a href="tel:{phone}" class="action-btn action-btn-primary" style="display:block; text-align:center;">📞 전화 ({phone})</a>', unsafe_allow_html=True)
                    with col_c2:
                        st.markdown(f'<a href="{KAKAO_CHAT_URL}" target="_blank" class="action-btn action-btn-kakao" style="display:block; text-align:center;">💬 카카오톡</a>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # 문서 다운로드
            st.markdown("### 📄 문서 다운로드")
            doc_content = generate_doc_content(data)
            filename = f"유아플랜_{receipt_no}_{datetime.now().strftime('%Y%m%d')}.txt"
            st.markdown(create_download_link(doc_content, filename), unsafe_allow_html=True)
        
        elif result.get("status") == "error":
            st.error(f"❌ 조회 실패: {result.get('message')}")
    
    elif search_clicked and not receipt_no_input:
        st.warning("⚠️ 접수번호를 입력해주세요.")

if __name__ == "__main__":
    main()