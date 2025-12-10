"""
유아플랜 컨설턴트 대시보드 v3.8
- v3.7 기반 + 성능 최적화
- fetch_all_clients 캐싱 적용 (5분 TTL)
- 2025-12-10 수정
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
import html

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

# GAS 엔드포인트 (기본값 유지 - 공개 URL)
INTEGRATED_GAS_URL = _get_secret(
    "FIRST_GAS_URL",
    "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec"
)

# API 토큰 (기본값 제거 - 보안 강화)
API_TOKEN = _get_secret("API_TOKEN", "")

# Gemini API
GEMINI_API_KEY = _get_secret("GEMINI_API_KEY", "")

# 카카오톡 채널
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# 접속 비밀번호 (기본값 제거 - 보안 강화)
DASHBOARD_PASSWORD = _get_secret("DASHBOARD_PW", "")

# 결과 저장용 대표 비밀번호
RESULT_PASSWORD = _get_secret("RESULT_PW", "")

# 설문 URL
FIRST_SURVEY_URL = "https://youareplan-survey.onrender.com"
SECOND_SURVEY_BASE_URL = "https://youareplan-survey2.onrender.com"

# ==============================
# 보안 유틸리티 함수
# ==============================
def safe_html(text: Any) -> str:
    """XSS 방지를 위한 HTML 특수문자 이스케이프"""
    if text is None:
        return "-"
    return html.escape(str(text)) if text else "-"

def validate_receipt_no(receipt_no: str) -> bool:
    """접수번호 형식 검증 (YP + 숫자 8자리)"""
    if not receipt_no:
        return False
    return bool(re.match(r'^YP\d{8}$', receipt_no.strip()))

def sanitize_input(text: str, max_length: int = 500) -> str:
    """입력값 정제 (길이 제한 + 공백 정리)"""
    if not text:
        return ""
    return str(text).strip()[:max_length]

def check_security_config() -> Tuple[bool, List[str]]:
    """보안 설정 체크"""
    errors = []
    
    if not DASHBOARD_PASSWORD:
        errors.append("DASHBOARD_PW 환경변수가 설정되지 않았습니다.")
    
    if not API_TOKEN:
        errors.append("API_TOKEN 환경변수가 설정되지 않았습니다.")
    
    return len(errors) == 0, errors

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
# 스타일링 (함수로 감싸서 main에서 호출)
# ==============================
CUSTOM_CSS = """
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
  color: #1f2937;
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
  color: #1f2937;
}
.radar-new { border-left: 4px solid #10b981; }
.radar-deadline { border-left: 4px solid #ef4444; }
.radar-hot { border-left: 4px solid #f59e0b; }

/* 파이프라인 카드 */
.pipeline-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.pipeline-card { background: white; border: 1px solid rgba(128,128,128,0.2); border-radius: 10px; padding: 16px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.pipeline-card .number { font-size: 28px; font-weight: 700; color: var(--gov-navy); }
.pipeline-card .label { font-size: 12px; color: #6b7280; margin-top: 4px; }
.pipeline-card .delta { font-size: 11px; color: var(--success); }

/* 검색 섹션 */
.search-section { background: rgba(128, 128, 128, 0.08); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
.search-section h3 { color: inherit; margin: 0 0 12px 0; font-size: 16px; }

/* 고객 정보 카드 */
.info-card { border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 12px; padding: 20px; margin: 12px 0; background: rgba(128, 128, 128, 0.05); }
.info-card h4 { color: var(--gov-blue); margin: 0 0 16px 0; font-weight: 700; border-bottom: 1px solid rgba(128, 128, 128, 0.2); padding-bottom: 8px; }

/* 데이터 그리드 */
.data-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 12px 0; }
.data-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(128, 128, 128, 0.08); border-radius: 6px; border-left: 4px solid var(--gov-blue); font-size: 13px; }
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
.progress-container { background: rgba(128, 128, 128, 0.15); height: 16px; border-radius: 8px; overflow: hidden; position: relative; margin: 16px 0; }
.progress-bar { height: 100%; background: linear-gradient(90deg, var(--gov-navy), var(--gov-blue)); transition: width 0.3s; }
.progress-text { position: absolute; width: 100%; text-align: center; top: 50%; transform: translateY(-50%); font-size: 11px; font-weight: 600; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }

/* 요약 카드 */
.summary-card { background: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 10px; padding: 16px; text-align: center; }
.summary-card .label { font-size: 11px; color: #6b7280; margin-bottom: 6px; }
.summary-card .value { font-size: 16px; font-weight: 700; color: var(--gov-navy); }

/* 상태 뱃지 */
.status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 8px; }
.badge-completed { background: #dcfce7; color: #166534; }
.badge-pending { background: #fef3c7; color: #92400e; }
.badge-error { background: #fee2e2; color: #991b1b; }

/* 소통 로그 */
.comm-log-item { background: rgba(128, 128, 128, 0.05); border-left: 3px solid var(--gov-blue); border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
.comm-log-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.comm-log-author { font-weight: 600; color: var(--gov-blue); font-size: 11px; color: #6b7280; }
.comm-log-date { font-size: 11px; color: #6b7280; }
.comm-log-content { font-size: 14px; line-height: 1.5; }

/* 링크 박스 */
.link-box { background: rgba(128, 128, 128, 0.05); border: 1px dashed rgba(128, 128, 128, 0.3); border-radius: 8px; padding: 16px; margin: 12px 0; }
.link-box a { color: var(--gov-blue); word-break: break-all; }

/* 액션 버튼 */
.action-btn { display: inline-block; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; transition: all 0.2s; cursor: pointer; border: none; margin: 4px; }
.action-btn-primary { background: var(--gov-navy); color: white; }
.action-btn-primary:hover { background: #001a38; }
.action-btn-kakao { background: #FEE500; color: #3C1E1E; }
.action-btn-kakao:hover { background: #e6ce00; }

/* AI 결과 카드 */
.ai-result-card { background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border: 1px solid #86efac; border-radius: 12px; padding: 20px; margin: 16px 0; }
.ai-result-card h4 { color: #166534; margin: 0 0 12px 0; }

/* 점수 표시 */
.score-display { text-align: center; padding: 20px; }
.score-number { font-size: 48px; font-weight: 900; color: var(--gov-navy); }
.score-grade { font-size: 24px; font-weight: 700; margin-top: 8px; color: var(--gov-navy); }
.score-breakdown { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 16px; }
.score-item { background: white; border-radius: 8px; padding: 12px; text-align: center; }
.score-item-label { font-size: 11px; color: #6b7280; }
.score-item-value { font-size: 20px; font-weight: 700; color: var(--gov-navy); }

/* 고객 테이블 */
.client-table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
.client-table th { background: var(--gov-navy); color: white; padding: 10px 12px; text-align: left; font-weight: 600; }
.client-table td { padding: 10px 12px; border-bottom: 1px solid rgba(128,128,128,0.2); }
.client-table tr:hover { background: rgba(128,128,128,0.05); }

/* 보안 경고 */
.security-warning { background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border: 2px solid #ef4444; border-radius: 12px; padding: 20px; margin: 20px 0; text-align: center; }
.security-warning h3 { color: #991b1b; margin: 0 0 12px 0; }
.security-warning p { color: #7f1d1d; margin: 0; }

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
"""

def apply_custom_css():
    """커스텀 CSS 적용 - main() 내에서 호출해야 함"""
    # 메타 태그
    st.markdown(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
        '<meta name="mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        '<meta name="theme-color" content="#002855">',
        unsafe_allow_html=True
    )
    # CSS 주입
    st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

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

# ==============================
# 유틸리티 함수
# ==============================
def get_logo_url() -> str:
    return _get_secret("YOUAREPLAN_LOGO_URL", DEFAULT_LOGO_URL)

def format_progress_bar(progress: int) -> str:
    # progress는 숫자이므로 XSS 위험 없음
    safe_progress = max(0, min(100, int(progress)))
    return f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {safe_progress}%"></div>
        <div class="progress-text">{safe_progress}% 완료</div>
    </div>
    """

def create_download_link(content: str, filename: str) -> str:
    b64 = base64.b64encode(content.encode('utf-8')).decode()
    safe_filename = safe_html(filename)
    return f'<a href="data:text/plain;base64,{b64}" download="{safe_filename}" class="action-btn action-btn-primary">📥 {safe_filename}</a>'

# ==============================
# GAS API 함수
# ==============================
def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    """통합 고객 데이터 조회"""
    try:
        # 입력값 검증
        sanitized_receipt_no = sanitize_input(receipt_no, 20)
        
        params = {
            "action": "getIntegratedData",
            "receipt_no": sanitized_receipt_no,
            "token": API_TOKEN
        }
        resp = requests.get(INTEGRATED_GAS_URL, params=params, timeout=30)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# [v3.8] 캐싱 적용 - 5분(300초) TTL
@st.cache_data(ttl=300, show_spinner=False)
def fetch_all_clients_cached(_api_token: str) -> Dict[str, Any]:
    """전체 고객 목록 조회 (캐싱 적용)
    
    Args:
        _api_token: API 토큰 (앞에 _를 붙여 해싱에서 제외)
    
    Returns:
        고객 목록 데이터
    
    Note:
        - 5분간 캐시 유지로 GAS 응답 지연 해소
        - 새로고침 버튼으로 캐시 무효화 가능
    """
    try:
        params = {
            "action": "getAllClients",
            "token": _api_token
        }
        resp = requests.get(INTEGRATED_GAS_URL, params=params, timeout=30)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def issue_survey_link(receipt_no: str, stage: int = 2) -> Dict[str, Any]:
    """설문 링크 발급"""
    try:
        sanitized_receipt_no = sanitize_input(receipt_no, 20)
        
        params = {
            "action": "issueSurveyLink",
            "receipt_no": sanitized_receipt_no,
            "stage": stage,
            "token": API_TOKEN
        }
        resp = requests.get(INTEGRATED_GAS_URL, params=params, timeout=30)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def add_comm_log(receipt_no: str, author: str, content: str) -> Dict[str, Any]:
    """소통 로그 추가"""
    try:
        sanitized_receipt_no = sanitize_input(receipt_no, 20)
        sanitized_author = sanitize_input(author, 50)
        sanitized_content = sanitize_input(content, 2000)
        
        payload = {
            "action": "addCommLog",
            "receipt_no": sanitized_receipt_no,
            "author": sanitized_author,
            "content": sanitized_content,
            "token": API_TOKEN
        }
        resp = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ==============================
# 파이프라인 통계
# ==============================
def calculate_pipeline_stats(clients: List[Dict]) -> Dict[str, int]:
    """파이프라인 통계 계산"""
    stats = {
        "total": 0,
        "stage1_only": 0,
        "stage2_done": 0,
        "stage3_done": 0,
        "today_new": 0
    }
    
    if not clients:
        return stats
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for c in clients:
        stats["total"] += 1
        
        progress = c.get("progress_pct", 0)
        if progress >= 100:
            stats["stage3_done"] += 1
        elif progress >= 66:
            stats["stage2_done"] += 1
        else:
            stats["stage1_only"] += 1
        
        # 오늘 접수
        created = c.get("created_at", "")
        if created and today_str in created:
            stats["today_new"] += 1
    
    return stats

# ==============================
# 오늘 할 일 섹션
# ==============================
def render_todo_section(clients: List[Dict]):
    """오늘 할 일 섹션"""
    st.markdown("""
    <div class="todo-section">
        <h3>📋 오늘 할 일</h3>
    """, unsafe_allow_html=True)
    
    todos = []
    
    if clients:
        for c in clients:
            progress = c.get("progress_pct", 0)
            name = safe_html(c.get("name", "-"))
            receipt_no = safe_html(c.get("receipt_no", "-"))
            
            # 2차 완료 → 3차 대기
            if 66 <= progress < 100:
                todos.append({
                    "priority": "urgent",
                    "text": f"🔴 {name} ({receipt_no}) - 3차 설문 발송 필요"
                })
            
            # 1차만 완료
            elif 33 <= progress < 66:
                todos.append({
                    "priority": "important", 
                    "text": f"🟡 {name} ({receipt_no}) - 2차 설문 대기"
                })
    
    if not todos:
        st.markdown('<div class="todo-item todo-normal">✅ 오늘 처리할 긴급 업무가 없습니다</div>', unsafe_allow_html=True)
    else:
        for todo in todos[:5]:  # 최대 5개
            priority_class = f"todo-{todo['priority']}"
            st.markdown(f'<div class="todo-item {priority_class}">{todo["text"]}</div>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ==============================
# 정책자금 레이더 섹션
# ==============================
def render_radar_section():
    """정책자금 레이더"""
    st.markdown("""
    <div class="radar-section">
        <h3>📡 정책자금 레이더</h3>
        <div class="radar-item radar-hot">
            <span>🔥 소상공인정책자금</span>
            <span>상시</span>
        </div>
        <div class="radar-item radar-new">
            <span>🆕 청년창업사관학교</span>
            <span>1~2월 모집</span>
        </div>
        <div class="radar-item radar-deadline">
            <span>⏰ 신용보증기금</span>
            <span>상시</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================
# 파이프라인 섹션
# ==============================
def render_pipeline_section(stats: Dict[str, int]):
    """파이프라인 현황"""
    if not stats:
        stats = {"total": 0, "stage1_only": 0, "stage2_done": 0, "stage3_done": 0, "today_new": 0}
    
    # 숫자값은 int로 변환하여 XSS 방지
    total = int(stats.get('total', 0))
    stage1 = int(stats.get('stage1_only', 0))
    stage2 = int(stats.get('stage2_done', 0))
    stage3 = int(stats.get('stage3_done', 0))
    today = int(stats.get('today_new', 0))
    
    st.markdown(f"""
    <div class="pipeline-grid">
        <div class="pipeline-card">
            <div class="number">{total}</div>
            <div class="label">전체 고객</div>
        </div>
        <div class="pipeline-card">
            <div class="number">{stage1}</div>
            <div class="label">1차 완료</div>
        </div>
        <div class="pipeline-card">
            <div class="number">{stage2}</div>
            <div class="label">2차 완료</div>
        </div>
        <div class="pipeline-card">
            <div class="number">{stage3}</div>
            <div class="label">3차 완료</div>
            <div class="delta">+{today} 오늘</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================
# 요약 카드
# ==============================
def render_summary_cards(data: Dict):
    """고객 요약 카드"""
    stage1 = data.get("stage1") or {}
    stage2 = data.get("stage2") or {}
    
    # 기본 정보 (safe_html 적용)
    business_type = safe_html(stage1.get("business_type", "-"))
    
    # 우대요건 계산 (v3.2)
    birthdate = stage1.get("birthdate", "")
    gender = stage1.get("gender", "")
    open_date = stage2.get("open_date", "") or stage1.get("open_date", "")
    
    youth_status = safe_html(calculate_youth_status(birthdate))
    female_ceo = safe_html(calculate_female_ceo(gender))
    business_age = safe_html(calculate_business_age(open_date))
    
    cols = st.columns(4)
    
    with cols[0]:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">사업자 유형</div>
            <div class="value">{business_type}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        youth_class = "benefit-yes" if "예" in youth_status else "benefit-no"
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">청년 여부</div>
            <div class="value {youth_class}">{youth_status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        female_class = "benefit-yes" if female_ceo == "예" else "benefit-no"
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">여성대표</div>
            <div class="value {female_class}">{female_ceo}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">업력</div>
            <div class="value">{business_age}</div>
        </div>
        """, unsafe_allow_html=True)

# ==============================
# 설문 단계별 상세 카드
# ==============================
def render_stage_card(title: str, data: Optional[Dict], stage: int):
    """설문 단계별 카드"""
    if not data:
        st.markdown(f"""
        <div class="info-card">
            <h4>{safe_html(title)} <span class="status-badge badge-pending">미완료</span></h4>
            <p style="color: #6b7280;">데이터 없음</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown(f"""
    <div class="info-card">
        <h4>{safe_html(title)} <span class="status-badge badge-completed">완료</span></h4>
        <div class="data-grid">
    """, unsafe_allow_html=True)
    
    # 단계별 표시 필드
    if stage == 1:
        fields = [
            ("name", "성명"),
            ("phone", "연락처"),
            ("gender", "성별"),
            ("birthdate", "생년월일"),
            ("business_type", "사업자유형"),
            ("region", "지역"),
            ("interest", "관심사항"),
            ("referral_source", "유입경로")
        ]
    elif stage == 2:
        fields = [
            ("company_name", "상호명"),
            ("business_number", "사업자번호"),
            ("open_date", "개업연월"),
            ("employee_count", "직원수"),
            ("annual_revenue", "연매출"),
            ("business_category", "업종"),
            ("funding_purpose", "자금용도"),
            ("desired_amount", "희망금액"),
            ("past_policy_fund", "정책자금이력"),
            ("additional_info", "추가정보")
        ]
    else:  # stage 3
        fields = [
            ("funding_timeline", "자금시기"),
            ("collateral_type", "담보유형"),
            ("credit_status", "신용상태"),
            ("tax_status", "세금상태"),
            ("consulting_request", "상담요청"),
            ("recommended_fund", "추천자금"),
            ("expected_limit", "예상한도"),
            ("decision_status", "의사결정"),
            ("readiness_score", "준비도")
        ]
    
    for key, label in fields:
        value = safe_html(data.get(key, "-") or "-")
        st.markdown(f"""
        <div class="data-item">
            <span class="data-label">{safe_html(label)}</span>
            <span class="data-value">{value}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# ==============================
# 링크 발급 섹션
# ==============================
def render_link_issue_section(receipt_no: str, customer_name: str):
    """설문 링크 발급"""
    st.markdown("### 🔗 설문 링크 발급")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 2차 설문 링크 발급", type="primary", use_container_width=True):
            with st.spinner("링크 생성 중..."):
                result = issue_survey_link(receipt_no, 2)
                if result.get("status") == "success":
                    link = result.get("link", "")
                    st.session_state.issued_link = {"stage": 2, "link": link}
                    st.success("✅ 2차 설문 링크 발급 완료!")
                else:
                    st.error(f"❌ 실패: {safe_html(result.get('message'))}")
    
    with col2:
        if st.button("📋 3차 설문 링크 발급", use_container_width=True):
            with st.spinner("링크 생성 중..."):
                result = issue_survey_link(receipt_no, 3)
                if result.get("status") == "success":
                    link = result.get("link", "")
                    st.session_state.issued_link = {"stage": 3, "link": link}
                    st.success("✅ 3차 설문 링크 발급 완료!")
                else:
                    st.error(f"❌ 실패: {safe_html(result.get('message'))}")
    
    # 발급된 링크 표시
    if st.session_state.issued_link:
        link_info = st.session_state.issued_link
        safe_link = safe_html(link_info['link'])
        stage_num = int(link_info['stage'])
        st.markdown(f"""
        <div class="link-box">
            <strong>📎 {stage_num}차 설문 링크</strong><br>
            <a href="{safe_link}" target="_blank">{safe_link}</a>
        </div>
        """, unsafe_allow_html=True)
        st.code(link_info['link'])

# ==============================
# 소통 로그 섹션
# ==============================
def render_comm_logs_section(logs: List[Dict], receipt_no: str):
    """소통 로그"""
    st.markdown("### 💬 소통 기록")
    
    # 로그 표시
    if logs:
        for log in logs:
            author = safe_html(log.get('author', '-'))
            created_at = safe_html(log.get('created_at', '-'))
            content = safe_html(log.get('content', '-'))
            
            st.markdown(f"""
            <div class="comm-log-item">
                <div class="comm-log-header">
                    <span class="comm-log-author">{author}</span>
                    <span class="comm-log-date">{created_at}</span>
                </div>
                <div class="comm-log-content">{content}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("소통 기록이 없습니다.")
    
    # 로그 추가
    with st.expander("➕ 소통 기록 추가"):
        with st.form("add_log_form"):
            author = st.selectbox("작성자", ["담당자", "대표", "시스템"])
            content = st.text_area("내용", placeholder="상담 내용을 입력하세요...", max_chars=2000)
            
            if st.form_submit_button("💾 저장"):
                if content:
                    result = add_comm_log(receipt_no, author, content)
                    if result.get("ok"):
                        st.success("✅ 저장되었습니다.")
                        st.session_state.search_result = fetch_integrated_data(receipt_no)
                        st.rerun()
                    else:
                        st.error(f"❌ 저장 실패: {safe_html(result.get('error'))}")
                else:
                    st.warning("내용을 입력해주세요.")

# ==============================
# AI 분석 섹션
# ==============================
def render_ai_analysis_section(data: Dict):
    """AI 분석"""
    st.markdown("### 🤖 AI 분석")
    
    if not GEMINI_API_KEY:
        st.warning("⚠️ Gemini API 키가 설정되지 않았습니다.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 계약 가능성 분석", use_container_width=True):
            with st.spinner("AI 분석 중..."):
                result = run_ai_analysis(data, "contract")
                st.session_state.ai_analysis_result = result
    
    with col2:
        if st.button("💯 100점 평가", use_container_width=True):
            with st.spinner("AI 평가 중..."):
                result = run_ai_analysis(data, "score")
                st.session_state.ai_score_result = result
    
    with col3:
        if st.button("📝 사업계획서 생성", use_container_width=True):
            with st.spinner("AI 생성 중..."):
                result = run_ai_analysis(data, "plan")
                st.session_state.ai_plan_result = result
    
    # 결과 표시 (AI 결과는 마크다운으로 표시, XSS 위험 낮음)
    if st.session_state.ai_analysis_result:
        st.markdown("""
        <div class="ai-result-card">
            <h4>📊 계약 가능성 분석</h4>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.ai_analysis_result)
    
    if st.session_state.ai_score_result:
        st.markdown("""
        <div class="ai-result-card">
            <h4>💯 100점 평가</h4>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.ai_score_result)
    
    if st.session_state.ai_plan_result:
        st.markdown("""
        <div class="ai-result-card">
            <h4>📝 사업계획서</h4>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.ai_plan_result)

def run_ai_analysis(data: Dict, analysis_type: str) -> str:
    """Gemini AI 분석 실행"""
    try:
        stage1 = data.get("stage1") or {}
        stage2 = data.get("stage2") or {}
        stage3 = data.get("stage3") or {}
        
        # 컨텍스트 구성 (내부 처리용이므로 이스케이프 불필요)
        context = f"""
고객 정보:
- 성명: {stage1.get('name', '-')}
- 사업자유형: {stage1.get('business_type', '-')}
- 지역: {stage1.get('region', '-')}
- 관심사항: {stage1.get('interest', '-')}

사업 정보:
- 상호명: {stage2.get('company_name', '-')}
- 업종: {stage2.get('business_category', '-')}
- 개업연월: {stage2.get('open_date', '-')}
- 연매출: {stage2.get('annual_revenue', '-')}
- 직원수: {stage2.get('employee_count', '-')}
- 자금용도: {stage2.get('funding_purpose', '-')}
- 희망금액: {stage2.get('desired_amount', '-')}

추가 정보:
- 자금시기: {stage3.get('funding_timeline', '-')}
- 담보유형: {stage3.get('collateral_type', '-')}
- 신용상태: {stage3.get('credit_status', '-')}
"""
        
        if analysis_type == "contract":
            prompt = f"""다음 고객의 정책자금 계약 가능성을 분석해주세요.

{context}

분석 항목:
1. 적합 정책자금 추천 (3개)
2. 계약 가능성 (상/중/하)
3. 주요 강점
4. 보완 필요사항
5. 추천 전략
"""
        elif analysis_type == "score":
            prompt = f"""다음 고객을 100점 만점으로 평가해주세요.

{context}

평가 항목 (각 25점):
1. 사업 안정성
2. 자금 적합성
3. 서류 준비도
4. 성장 가능성

총점과 등급(A/B/C/D)을 제시해주세요.
"""
        else:  # plan
            prompt = f"""다음 고객을 위한 간단한 사업계획서 개요를 작성해주세요.

{context}

포함 내용:
1. 사업 개요
2. 시장 분석
3. 자금 계획
4. 성장 전략
"""
        
        # Gemini API 호출 - gemini-1.5-pro 우선
        models_to_try = [
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest", 
            "gemini-pro"
        ]
        
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048
                    }
                }
                
                resp = requests.post(
                    f"{url}?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if text:
                        st.session_state.selected_model = model_name
                        return text
            except:
                continue
        
        return "❌ AI 분석 실패: 모든 모델 시도 실패"
        
    except Exception as e:
        return f"❌ 오류: {safe_html(str(e))}"

# ==============================
# PDF 업로드 섹션
# ==============================
def render_pdf_upload_section():
    """PDF 업로드 및 분석"""
    st.markdown("### 📄 정책자금 공고문 분석")
    
    uploaded = st.file_uploader("PDF 파일 업로드", type=['pdf'])
    
    if uploaded and HAS_PYPDF:
        try:
            pdf_reader = PdfReader(io.BytesIO(uploaded.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            
            if text:
                st.session_state.policy_text = text[:5000]  # 최대 5000자
                st.success(f"✅ PDF 분석 완료 ({len(text)}자)")
                
                with st.expander("📝 추출된 텍스트"):
                    st.text(text[:2000] + "..." if len(text) > 2000 else text)
        except Exception as e:
            st.error(f"❌ PDF 읽기 실패: {safe_html(str(e))}")
    elif uploaded and not HAS_PYPDF:
        st.warning("⚠️ PDF 라이브러리가 설치되지 않았습니다.")

# ==============================
# 문서 생성
# ==============================
def generate_doc_content(data: Dict) -> str:
    """문서 내용 생성"""
    stage1 = data.get("stage1") or {}
    stage2 = data.get("stage2") or {}
    stage3 = data.get("stage3") or {}
    
    # 문서 내용은 다운로드용이므로 이스케이프 불필요
    content = f"""
=====================================
유아플랜 고객 정보 요약서
=====================================
접수번호: {data.get('receipt_no', '-')}
작성일자: {datetime.now().strftime('%Y-%m-%d %H:%M')}

[1차 설문 - 기본정보]
- 성명: {stage1.get('name', '-')}
- 연락처: {stage1.get('phone', '-')}
- 성별: {stage1.get('gender', '-')}
- 생년월일: {stage1.get('birthdate', '-')}
- 사업자유형: {stage1.get('business_type', '-')}
- 지역: {stage1.get('region', '-')}

[2차 설문 - 사업정보]
- 상호명: {stage2.get('company_name', '-')}
- 사업자번호: {stage2.get('business_number', '-')}
- 개업연월: {stage2.get('open_date', '-')}
- 업종: {stage2.get('business_category', '-')}
- 연매출: {stage2.get('annual_revenue', '-')}
- 직원수: {stage2.get('employee_count', '-')}
- 자금용도: {stage2.get('funding_purpose', '-')}
- 희망금액: {stage2.get('desired_amount', '-')}

[3차 설문 - 추가정보]
- 자금시기: {stage3.get('funding_timeline', '-')}
- 담보유형: {stage3.get('collateral_type', '-')}
- 신용상태: {stage3.get('credit_status', '-')}
- 세금상태: {stage3.get('tax_status', '-')}

=====================================
"""
    return content

# ==============================
# 결과 저장 섹션
# ==============================
def render_result_save_section(receipt_no: str):
    """정책자금 결과 저장"""
    st.markdown("### 🏆 정책자금 결과 저장")
    
    # 대표 인증
    if RESULT_PASSWORD and not st.session_state.result_auth:
        st.info("결과 저장은 대표 비밀번호가 필요합니다.")
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
            policy_name = st.text_input("승인된 정책자금명", placeholder="예: 소상공인정책자금", max_chars=100)
            approved_amount = st.text_input("승인금액 (만원)", placeholder="예: 5000", max_chars=20)
        
        with col2:
            approval_date = st.date_input("승인일자")
            result_memo = st.text_area("메모", placeholder="특이사항", height=80, max_chars=500)
        
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
                    st.error(f"❌ 저장 실패: {safe_html(result.get('error'))}")
            else:
                st.warning("정책자금명과 승인금액은 필수입니다.")

# ==============================
# 보안 경고 페이지
# ==============================
def render_security_error(errors: List[str]):
    """보안 설정 오류 페이지"""
    st.markdown("""
    <div class="security-warning">
        <h3>⚠️ 보안 설정 오류</h3>
        <p>필수 환경변수가 설정되지 않았습니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.error("다음 환경변수를 Render 대시보드에서 설정해주세요:")
    for err in errors:
        st.warning(f"• {err}")
    
    st.info("""
    **설정 방법:**
    1. Render 대시보드 → Environment 탭
    2. 다음 변수 추가:
       - `DASHBOARD_PW`: 대시보드 접속 비밀번호
       - `API_TOKEN`: GAS API 인증 토큰
    """)
    st.stop()

# ==============================
# 메인 함수
# ==============================
def main():
    # ========== 초기화 (main 내에서 호출) ==========
    init_session_state()
    apply_custom_css()
    
    # ========== 보안 설정 체크 ==========
    is_secure, security_errors = check_security_config()
    if not is_secure:
        render_security_error(security_errors)
        return
    
    logo_url = get_logo_url()
    current_time = datetime.now().strftime("%Y.%m.%d %H:%M")
    
    # ========== 비밀번호 인증 ==========
    if not st.session_state.authenticated:
        st.markdown(f"""
        <div class="brandbar">
            <div style="display: flex; align-items: center; gap: 16px;">
                {f'<img src="{safe_html(logo_url)}" alt="{safe_html(BRAND_NAME)} 로고" />' if logo_url else ''}
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
            {f'<img src="{safe_html(logo_url)}" alt="{safe_html(BRAND_NAME)} 로고" />' if logo_url else ''}
            <h1>📊 유아플랜 컨설턴트 대시보드</h1>
        </div>
        <div class="version">
            <div>v3.8</div>
            <div style="font-size: 11px; opacity: 0.7;">{safe_html(current_time)}</div>
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
    
    # ========== 전체 고객 데이터 로드 (캐싱 적용) ==========
    if not st.session_state.all_clients_loaded:
        with st.spinner("📊 데이터 로딩..."):
            # [v3.8] 캐싱된 함수 호출
            result = fetch_all_clients_cached(API_TOKEN)
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
            <a href="{safe_html(FIRST_SURVEY_URL)}" target="_blank">{safe_html(FIRST_SURVEY_URL)}</a>
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
            label_visibility="collapsed",
            max_chars=20
        )
    
    with col2:
        search_clicked = st.button("🔍 조회", type="primary", use_container_width=True)
    
    with col3:
        if st.button("🔄 새로고침", use_container_width=True):
            # [v3.8] 캐시 무효화 후 재로딩
            fetch_all_clients_cached.clear()
            if st.session_state.searched_receipt_no:
                st.session_state.search_result = fetch_integrated_data(st.session_state.searched_receipt_no)
            st.session_state.all_clients_loaded = False
            st.rerun()
    
    if search_clicked and receipt_no_input:
        # 입력값 검증
        sanitized_input = sanitize_input(receipt_no_input, 20)
        
        if not validate_receipt_no(sanitized_input):
            st.warning("⚠️ 접수번호 형식이 올바르지 않습니다. (예: YP12091234)")
        else:
            st.session_state.searched_receipt_no = sanitized_input
            st.session_state.issued_link = None
            st.session_state.ai_analysis_result = None
            st.session_state.ai_score_result = None
            st.session_state.ai_plan_result = None
            st.session_state.result_auth = False
            
            with st.spinner("🔄 조회 중..."):
                st.session_state.search_result = fetch_integrated_data(sanitized_input)
            st.rerun()
    
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
                st.markdown(f"### 👤 {safe_html(customer_name)}")
            with col_h2:
                st.markdown(f"**접수번호:** `{safe_html(receipt_no)}`")
            with col_h3:
                st.markdown(f"**진행률:** {int(progress)}%")
            
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
                    safe_phone = safe_html(phone)
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.markdown(f'<a href="tel:{safe_phone}" class="action-btn action-btn-primary" style="display:block; text-align:center;">📞 전화 ({safe_phone})</a>', unsafe_allow_html=True)
                    with col_c2:
                        st.markdown(f'<a href="{safe_html(KAKAO_CHAT_URL)}" target="_blank" class="action-btn action-btn-kakao" style="display:block; text-align:center;">💬 카카오톡</a>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # 문서 다운로드
            st.markdown("### 📄 문서 다운로드")
            doc_content = generate_doc_content(data)
            filename = f"유아플랜_{receipt_no}_{datetime.now().strftime('%Y%m%d')}.txt"
            st.markdown(create_download_link(doc_content, filename), unsafe_allow_html=True)
        
        elif result.get("status") == "error":
            st.error(f"❌ 조회 실패: {safe_html(result.get('message'))}")
        else:
            # 디버깅: 예상치 못한 응답
            st.warning(f"⚠️ 예상치 못한 응답: {result}")
    
    elif search_clicked and not receipt_no_input:
        st.warning("⚠️ 접수번호를 입력해주세요.")

if __name__ == "__main__":
    main()