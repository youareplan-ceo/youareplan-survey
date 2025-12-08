import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import base64
import os
import re

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(
    page_title="유아플랜 통합 관리 대시보드",
    page_icon="📊", 
    layout="wide"
)

# ==============================
# 환경 설정
# ==============================
BRAND_NAME = "유아플랜"
DEFAULT_LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png"

# GAS 엔드포인트
INTEGRATED_GAS_URL = "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec"
API_TOKEN = "youareplan"

# Gemini API (환경변수에서 가져오기)
def get_gemini_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    except:
        return os.getenv("GEMINI_API_KEY", "")

GEMINI_API_KEY = get_gemini_api_key()

# KakaoTalk Channel
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# 접속 비밀번호 (환경변수로 설정 가능)
def get_dashboard_password():
    try:
        return st.secrets.get("DASHBOARD_PW", os.getenv("DASHBOARD_PW", "1234"))
    except:
        return os.getenv("DASHBOARD_PW", "1234")

DASHBOARD_PASSWORD = get_dashboard_password()

# ==============================
# 스타일링 (투명 모드 - 시스템 테마 따라감)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }
  
  /* 브랜딩 색상 변수 (고정) */
  :root { 
    --gov-navy: #002855; 
    --gov-blue: #0B5BD3; 
    --success: #10b981; 
    --warning: #f59e0b; 
    --danger: #ef4444; 
  }
  
  /* 메뉴/사이드바 숨김 */
  #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  
  .block-container{ max-width:1600px; margin:0 auto !important; padding:16px; }
  
  /* 브랜드바 (고정 색상 - 브랜딩) */
  .brandbar{
    display:flex; align-items:center; justify-content:space-between;
    padding:16px 24px; margin-bottom:20px;
    background: linear-gradient(135deg, var(--gov-navy) 0%, #1e40af 100%);
    border-radius: 12px; color: white;
  }
  .brandbar img{ height:52px; }
  .brandbar h1{ margin:0; color:white; font-weight:700; font-size:24px; }
  .brandbar .version{ font-size:14px; opacity:0.8; color: white; }
  
  /* 검색 영역 (투명) */
  .search-section {
    background: rgba(128, 128, 128, 0.08);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }
  .search-section h3 { color: inherit; margin: 0 0 12px 0; }
  .search-section p { color: inherit; opacity: 0.7; margin: 0; }
  
  /* 정보 카드 (투명) */
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
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 16px;
    margin: 16px 0;
  }
  .data-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(128, 128, 128, 0.08);
    border-radius: 6px;
    border-left: 4px solid var(--gov-blue);
  }
  .data-label { font-weight: 600; color: inherit; }
  .data-value { color: inherit; font-weight: 500; }
  
  /* 리스크 표시 (고정 색상 - 시각적 구분 필수) */
  .risk-high { border-left-color: var(--danger) !important; background: rgba(239, 68, 68, 0.15) !important; }
  .risk-medium { border-left-color: var(--warning) !important; background: rgba(245, 158, 11, 0.15) !important; }
  .risk-low { border-left-color: var(--success) !important; background: rgba(16, 185, 129, 0.15) !important; }
  
  /* 진행률 바 */
  .progress-container {
    background: rgba(128, 128, 128, 0.15);
    height: 16px;
    border-radius: 8px;
    margin: 12px 0;
    overflow: hidden;
    position: relative;
  }
  .progress-bar {
    height: 100%;
    border-radius: 8px;
    transition: width 0.5s ease;
    background: linear-gradient(90deg, var(--success) 0%, #059669 100%);
  }
  .progress-text {
    position: absolute;
    width: 100%;
    text-align: center;
    line-height: 16px;
    font-size: 12px;
    font-weight: 600;
    color: white;
    text-shadow: 0 1px 2px rgba(0,0,0,0.5);
  }
  
  /* 액션 버튼 (고정 색상) */
  .action-btn {
    display: inline-block;
    background: #1f2937;
    color: white !important;
    padding: 12px 16px;
    border-radius: 8px;
    text-decoration: none;
    text-align: center;
    font-weight: 600;
    border: none;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 4px;
  }
  .action-btn:hover { background: #374151; }
  .action-btn-primary { background: var(--gov-navy); }
  .action-btn-danger { background: #dc2626; }
  .action-btn-warning { background: #d97706; }
  .action-btn-kakao { background: #FEE500; color: #3C1E1E !important; }
  
  /* 상태 배지 (고정 색상 - 시각적 구분) */
  .status-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px;
  }
  .badge-completed { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
  .badge-progress { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid #f59e0b; }
  .badge-pending { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }
  
  /* 결과 섹션 */
  .result-section {
    background: rgba(14, 165, 233, 0.1);
    border: 2px solid #0ea5e9;
    border-radius: 12px;
    padding: 24px;
    margin-top: 24px;
  }
  
  /* 소통 로그 */
  .comm-log-item {
    background: rgba(128, 128, 128, 0.08);
    border: 1px solid rgba(128, 128, 128, 0.2);
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
    font-weight: 700;
    color: var(--gov-blue);
    background: rgba(11, 91, 211, 0.15);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 13px;
  }
  .comm-log-date {
    font-size: 12px;
    color: inherit;
    opacity: 0.6;
  }
  .comm-log-content {
    color: inherit;
    line-height: 1.6;
    white-space: pre-wrap;
  }
  
  /* 링크 박스 */
  .link-box {
    background: rgba(16, 185, 129, 0.1);
    border: 2px solid #10b981;
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
    word-break: break-all;
    color: inherit;
  }
  
  /* 요약 카드 */
  .summary-card {
    background: rgba(128, 128, 128, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
  }
  .summary-card .label {
    font-size: 12px;
    color: inherit;
    opacity: 0.7;
    margin-bottom: 4px;
  }
  .summary-card .value {
    font-size: 20px;
    font-weight: 700;
    color: var(--gov-blue);
  }
  
  /* AI 결과 박스 */
  .ai-result-box {
    background: rgba(245, 158, 11, 0.1);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    white-space: pre-wrap;
    line-height: 1.7;
    color: inherit;
  }
  
  /* 모델 점수 박스 */
  .model-score-box {
    background: rgba(14, 165, 233, 0.1);
    border: 1px solid #0ea5e9;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    font-size: 13px;
    color: inherit;
  }
  
  /* 모바일 대응 */
  @media (max-width: 768px) {
    .data-grid { grid-template-columns: 1fr; }
    .brandbar { flex-direction: column; gap: 12px; text-align: center; }
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# Session State 초기화
# ==============================
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "searched_receipt_no" not in st.session_state:
        st.session_state.searched_receipt_no = ""
    if "search_result" not in st.session_state:
        st.session_state.search_result = None
    if "issued_link" not in st.session_state:
        st.session_state.issued_link = None
    if "ai_analysis_result" not in st.session_state:
        st.session_state.ai_analysis_result = None
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None

init_session_state()

# ==============================
# 유틸리티 함수
# ==============================
def get_logo_url() -> str:
    try:
        url = st.secrets.get("YOUAREPLAN_LOGO_URL")
        if url:
            return str(url)
    except Exception:
        pass
    return DEFAULT_LOGO_URL

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

# ==============================
# 3차 완료 판단 헬퍼 함수
# ==============================
def has_stage3_real_data(stage3_data: Optional[Dict]) -> bool:
    """3차 설문에 실제 데이터가 있는지 확인 (빈 객체 vs 실제 입력)"""
    if not stage3_data:
        return False
    
    # 핵심 필드 중 하나라도 실제 값이 있으면 완료로 판단
    check_fields = [
        'collateral_profile',
        'tax_credit_summary', 
        'loan_summary',
        'docs_check',
        'risk_top3',
        'priority_exclusion',
        'coach_notes'
    ]
    
    for field in check_fields:
        value = stage3_data.get(field, '')
        if value and str(value).strip():
            return True
    
    return False

# ==============================
# API 함수들
# ==============================
def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    """GAS에서 통합 데이터 가져오기"""
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
        return {"ok": result.get("status") == "success", "error": result.get("message")}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

def issue_second_link(receipt_no: str, expire_min: int = 60) -> Dict[str, Any]:
    """2차 설문 링크 발급"""
    try:
        payload = {
            "action": "issue_token",
            "api_token": API_TOKEN,
            "receipt_no": receipt_no,
            "expire_minutes": expire_min
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
        if result.get("status") == "success":
            return {
                "ok": True,
                "token": result.get("token"),
                "uuid": result.get("uuid"),
                "expire_at": result.get("expire_at")
            }
        return {"ok": False, "error": result.get("message", "알 수 없는 오류")}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ==============================
# Gemini 모델 자동 선택 (점수 기반)
# ==============================
def calc_model_score(model_name: str) -> int:
    """
    모델명에서 점수 계산
    - 버전: X.Y → (major * 10000) + (minor * 1000)
    - 티어: ultra(1000) > pro(500) > flash(400)
    - 날짜: MM-DD → (month * 10) + day
    - exp 보너스: +10
    - latest 보너스: +50
    """
    score = 0
    name_lower = model_name.lower()
    
    # 버전 추출 (gemini-X.Y)
    version_match = re.search(r'gemini[- ]?(\d+)\.(\d+)', name_lower)
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        score += (major * 10000) + (minor * 1000)
    
    # 티어
    if 'ultra' in name_lower:
        score += 1000
    elif 'pro' in name_lower:
        score += 500
    elif 'flash' in name_lower:
        score += 400
    
    # 날짜 (MM-DD 형식)
    date_match = re.search(r'(\d{2})-(\d{2})', name_lower)
    if date_match:
        month = int(date_match.group(1))
        day = int(date_match.group(2))
        score += (month * 10) + day
    
    # exp 보너스
    if 'exp' in name_lower:
        score += 10
    
    # latest 보너스
    if 'latest' in name_lower:
        score += 50
    
    return score

def get_available_gemini_models() -> List[Dict[str, Any]]:
    """사용 가능한 Gemini 모델 목록 조회 및 점수 계산"""
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
            
            # generateContent 지원하는 모델만
            methods = model.get("supportedGenerationMethods", [])
            if "generateContent" not in methods:
                continue
            
            # gemini 모델만
            if not name.lower().startswith("gemini"):
                continue
            
            score = calc_model_score(name)
            models.append({
                "name": name,
                "score": score,
                "display_name": model.get("displayName", name)
            })
        
        # 점수 내림차순 정렬
        models.sort(key=lambda x: x["score"], reverse=True)
        return models
        
    except Exception:
        return []

def get_best_gemini_model() -> str:
    """가장 높은 점수의 모델 반환"""
    models = get_available_gemini_models()
    if models:
        return models[0]["name"]
    return "gemini-1.5-flash"  # 폴백

def call_gemini_analysis(doc_content: str) -> Dict[str, Any]:
    """Gemini API로 분석 실행 (자동 선택된 모델 사용)"""
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY가 설정되지 않았습니다."}
    
    best_model = get_best_gemini_model()
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{best_model}:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""당신은 한국 중소기업 정책자금 전문 컨설턴트입니다.
아래 고객 정보를 분석하고, 적합한 정책자금을 추천해주세요.

[고객 정보]
{doc_content}

[분석 요청사항]
1. 고객 현황 요약 (강점/약점)
2. 적합한 정책자금 TOP 3 추천 (구체적인 프로그램명, 지원기관, 예상 한도)
3. 신청 시 주의사항
4. 승인 가능성 평가 (높음/중간/낮음) 및 근거
5. 추가로 준비해야 할 서류나 조건

한국어로 명확하고 실용적으로 답변해주세요."""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4096
            }
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            return {"ok": False, "error": f"API 오류: HTTP {response.status_code}"}
        
        result = response.json()
        
        # 응답 파싱
        candidates = result.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                analysis_text = parts[0].get("text", "")
                return {"ok": True, "analysis": analysis_text, "model": best_model}
        
        return {"ok": False, "error": "응답 파싱 실패"}
        
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "API 응답 시간 초과 (60초)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ==============================
# 문서 생성
# ==============================
def generate_doc_content(data: Dict[str, Any]) -> str:
    """AI 매칭용 문서 내용 생성"""
    receipt_no = data.get("receipt_no", "")
    stage1 = data.get("stage1", {})
    stage2 = data.get("stage2", {})
    stage3 = data.get("stage3", {})
    
    current_date = datetime.now().strftime("%Y.%m.%d")
    
    content = f"""================================
유아플랜 고객정보 종합보고서
================================
접수번호: {receipt_no}
작성일자: {current_date}

[기본정보]
- 고객명: {stage1.get('name', '정보없음') if stage1 else '정보없음'}
- 연락처: {stage1.get('phone', '정보없음') if stage1 else '정보없음'}
- 이메일: {stage1.get('email', '미입력') if stage1 and stage1.get('email') else '미입력'}
- 사업형태: {stage1.get('business_type', '정보없음') if stage1 else '정보없음'}
- 업종: {stage1.get('industry', '정보없음') if stage1 else '정보없음'}
- 지역: {stage1.get('region', '정보없음') if stage1 else '정보없음'}
- 직원수: {stage1.get('employee_count', '정보없음') if stage1 else '정보없음'}
- 필요자금: {stage1.get('funding_amount', '정보없음') if stage1 else '정보없음'}

[재무현황]
"""
    
    if stage2:
        content += f"""- 사업자명: {stage2.get('business_name', '정보없음')}
- 사업시작일: {stage2.get('startup_date', '정보없음')}
- 사업자등록번호: {stage2.get('biz_reg_no', '정보없음')}
- 연매출 추이: {stage2.get('revenue_y3', '정보없음')} → {stage2.get('revenue_y2', '정보없음')} → {stage2.get('revenue_y1', '정보없음')}만원
- 자본금: {stage2.get('capital_amount', '정보없음')}만원
- 부채: {stage2.get('debt_amount', '정보없음')}만원
"""
    else:
        content += "- 2차 설문 정보 없음\n"
    
    content += f"""
[자격 현황]
- 세금 체납: {stage1.get('tax_status', '정보없음') if stage1 else '정보없음'}
- 금융 연체: {stage1.get('credit_status', '정보없음') if stage1 else '정보없음'}
- 영업 상태: {stage1.get('business_status', '정보없음') if stage1 else '정보없음'}
"""
    
    if stage3 and has_stage3_real_data(stage3):
        content += f"""
[심층 분석 정보]
- 담보/보증: {stage3.get('collateral_profile', '정보없음')}
- 세무/신용: {stage3.get('tax_credit_summary', '정보없음')}
- 대출현황: {stage3.get('loan_summary', '정보없음')}
- 리스크: {stage3.get('risk_top3', '정보없음')}
"""
    
    content += "\n================================"
    return content

# ==============================
# UI 렌더링 함수들
# ==============================
def render_stage_card(title: str, stage_data: Optional[Dict], stage_num: int) -> None:
    """단계별 카드 렌더링"""
    # 3차는 실제 데이터 여부로 판단
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
            st.markdown(f"""
            <div class="data-grid">
                <div class="data-item">
                    <span class="data-label">성함</span>
                    <span class="data-value">{stage_data.get('name', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">연락처</span>
                    <span class="data-value">{stage_data.get('phone', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">지역</span>
                    <span class="data-value">{stage_data.get('region', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">업종</span>
                    <span class="data-value">{stage_data.get('industry', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">사업형태</span>
                    <span class="data-value">{stage_data.get('business_type', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">직원수</span>
                    <span class="data-value">{stage_data.get('employee_count', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">연매출</span>
                    <span class="data-value">{stage_data.get('revenue', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">필요자금</span>
                    <span class="data-value">{stage_data.get('funding_amount', '-')}</span>
                </div>
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
            <h5 style="margin: 16px 0 8px 0;">⚠️ 자격 현황</h5>
            <div class="data-grid">
                <div class="data-item {tax_class}">
                    <span class="data-label">세금 체납</span>
                    <span class="data-value">{tax_status}</span>
                </div>
                <div class="data-item {credit_class}">
                    <span class="data-label">금융 연체</span>
                    <span class="data-value">{credit_status}</span>
                </div>
                <div class="data-item {biz_class}">
                    <span class="data-label">영업 상태</span>
                    <span class="data-value">{biz_status}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        elif stage_num == 2:
            st.markdown(f"""
            <div class="data-grid">
                <div class="data-item">
                    <span class="data-label">사업자명</span>
                    <span class="data-value">{stage_data.get('business_name', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">사업시작일</span>
                    <span class="data-value">{stage_data.get('startup_date', '-')}</span>
                </div>
                <div class="data-item">
                    <span class="data-label">사업자등록번호</span>
                    <span class="data-value">{stage_data.get('biz_reg_no', '-')}</span>
                </div>
            </div>
            
            <h5 style="margin: 16px 0 8px 0;">💰 재무현황</h5>
            <div class="data-grid">
                <div class="data-item">
                    <span class="data-label">당해연도 매출</span>
                    <span class="data-value">{stage_data.get('revenue_y1', '-')}만원</span>
                </div>
                <div class="data-item">
                    <span class="data-label">전년도 매출</span>
                    <span class="data-value">{stage_data.get('revenue_y2', '-')}만원</span>
                </div>
                <div class="data-item">
                    <span class="data-label">전전년도 매출</span>
                    <span class="data-value">{stage_data.get('revenue_y3', '-')}만원</span>
                </div>
                <div class="data-item">
                    <span class="data-label">자본금</span>
                    <span class="data-value">{stage_data.get('capital_amount', '-')}만원</span>
                </div>
                <div class="data-item">
                    <span class="data-label">부채</span>
                    <span class="data-value">{stage_data.get('debt_amount', '-')}만원</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        elif stage_num == 3:
            fields = [
                ("담보/보증 계획", stage_data.get('collateral_profile', '')),
                ("세무/신용 상태", stage_data.get('tax_credit_summary', '')),
                ("기존 대출 현황", stage_data.get('loan_summary', '')),
                ("준비 서류", stage_data.get('docs_check', '')),
                ("우대/제외 요건", stage_data.get('priority_exclusion', '')),
                ("리스크 Top3", stage_data.get('risk_top3', '')),
                ("컨설턴트 메모", stage_data.get('coach_notes', ''))
            ]
            
            for label, value in fields:
                if value and str(value).strip():
                    st.markdown(f"""
                    <div class="data-item" style="margin: 6px 0; flex-direction: column; align-items: flex-start;">
                        <span class="data-label">{label}</span>
                        <span class="data-value" style="margin-top: 4px;">{value}</span>
                    </div>
                    """, unsafe_allow_html=True)
    
    else:
        st.markdown('<div style="opacity: 0.6; font-style: italic; padding: 16px;">아직 설문이 완료되지 않았습니다.</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_summary_cards(data: Dict[str, Any]) -> None:
    """요약 카드 렌더링"""
    stage1 = data.get("stage1", {})
    stage2 = data.get("stage2", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
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
        revenue = stage2.get('revenue_y1', '-') if stage2 else '-'
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">당해 매출</div>
            <div class="value">{revenue}{'만원' if revenue != '-' else ''}</div>
        </div>
        """, unsafe_allow_html=True)

def render_comm_logs_section(comm_logs: List[Dict], receipt_no: str) -> None:
    """소통 로그 섹션 렌더링"""
    st.markdown("### 📝 소통 로그")
    
    # 로그 입력 폼
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
    
    # 로그 목록
    if comm_logs:
        for log in comm_logs:
            st.markdown(f"""
            <div class="comm-log-item">
                <div class="comm-log-header">
                    <span class="comm-log-author">{log.get('author', '알수없음')}</span>
                    <span class="comm-log-date">{log.get('timestamp', '')}</span>
                </div>
                <div class="comm-log-content">{log.get('content', '')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📭 아직 소통 로그가 없습니다.")

def render_link_issue_section(receipt_no: str, customer_name: str) -> None:
    """2차 링크 발급 섹션"""
    st.markdown("### 🔗 2차 설문 링크 발급")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        expire_min = st.selectbox("유효시간", [30, 60, 120, 1440], index=1, format_func=lambda x: f"{x}분" if x < 1440 else "24시간")
    
    with col2:
        if st.button("🎫 링크 발급", type="primary"):
            result = issue_second_link(receipt_no, expire_min)
            if result.get("ok"):
                token = result.get("token")
                uuid = result.get("uuid")
                link = f"https://youareplan-survey2.onrender.com/?t={token}&u={uuid}"
                st.session_state.issued_link = {
                    "link": link,
                    "expire_at": result.get("expire_at"),
                    "customer_name": customer_name
                }
            else:
                st.error(f"❌ 발급 실패: {result.get('error')}")
    
    # 발급된 링크 표시
    if st.session_state.issued_link:
        link_info = st.session_state.issued_link
        st.markdown(f"""
        <div class="link-box">
            <strong>📎 {link_info.get('customer_name', '')}님 2차 설문 링크</strong><br>
            <a href="{link_info.get('link')}" target="_blank">{link_info.get('link')}</a><br>
            <small>만료: {link_info.get('expire_at', '정보없음')}</small>
        </div>
        """, unsafe_allow_html=True)
        
        col_copy1, col_copy2 = st.columns(2)
        with col_copy1:
            st.code(link_info.get('link'), language=None)
        with col_copy2:
            kakao_msg = f"[유아플랜] {link_info.get('customer_name')}님, 2차 설문 링크입니다.\n{link_info.get('link')}"
            st.text_area("카카오톡 발송용", value=kakao_msg, height=80)

def render_ai_analysis_section(data: Dict[str, Any]) -> None:
    """AI 분석 섹션 (버튼 클릭 방식)"""
    st.markdown("### 🤖 AI 정책자금 분석")
    
    if not GEMINI_API_KEY:
        st.warning("⚠️ GEMINI_API_KEY가 설정되지 않아 AI 분석을 사용할 수 없습니다.")
        return
    
    # 모델 목록 (디버깅용)
    with st.expander("🔧 사용 가능한 Gemini 모델 (점수순)", expanded=False):
        models = get_available_gemini_models()
        if models:
            for i, m in enumerate(models[:10]):  # 상위 10개만
                rank_emoji = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else ""))
                st.markdown(f"""
                <div class="model-score-box">
                    {rank_emoji} <strong>{m['name']}</strong> — 점수: {m['score']}
                </div>
                """, unsafe_allow_html=True)
            
            if models:
                st.success(f"✅ **자동 선택 모델:** {models[0]['name']} (점수: {models[0]['score']})")
        else:
            st.warning("모델 목록을 가져올 수 없습니다.")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("🤖 AI 심층 분석 실행", key="btn_ai_analysis", type="primary"):
            with st.spinner("🔄 Gemini AI 분석 중... (최대 1분 소요)"):
                doc_content = generate_doc_content(data)
                result = call_gemini_analysis(doc_content)
                
                if result.get("ok"):
                    st.session_state.ai_analysis_result = result.get("analysis")
                    st.session_state.selected_model = result.get("model")
                else:
                    st.error(f"❌ 분석 실패: {result.get('error')}")
    
    with col2:
        best_model = get_best_gemini_model()
        st.caption(f"**선택된 모델:** {best_model}")
    
    # 분석 결과 표시
    if st.session_state.ai_analysis_result:
        st.markdown(f"""
        <div class="ai-result-box">
            <strong>🤖 AI 분석 결과</strong> (모델: {st.session_state.selected_model or 'unknown'})<br><br>
            {st.session_state.ai_analysis_result}
        </div>
        """, unsafe_allow_html=True)

def render_result_save_section(receipt_no: str) -> None:
    """정책자금 결과 저장 섹션 (대표 전용)"""
    st.markdown("### 💰 정책자금 결과 저장 (대표 전용)")
    
    with st.form("result_save_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            policy_name = st.text_input("승인된 정책자금명", placeholder="예: 소상공인정책자금")
            approved_amount = st.text_input("승인금액 (만원)", placeholder="예: 5000")
        
        with col2:
            approval_date = st.date_input("승인일자")
            result_memo = st.text_area("메모", placeholder="특이사항, 조건 등", height=80)
        
        submitted = st.form_submit_button("💾 결과 저장", type="primary")
        
        if submitted:
            if policy_name and approved_amount:
                # 소통 로그에 결과 기록
                content = f"[정책자금 결과] {policy_name} / {approved_amount}만원 / 승인일: {approval_date}"
                if result_memo:
                    content += f" / 메모: {result_memo}"
                
                result = add_comm_log(receipt_no, "대표", content)
                if result.get("ok"):
                    st.success(f"✅ 결과 저장 완료: {policy_name} / {approved_amount}만원")
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
                <h1>📊 유아플랜 통합 관리 대시보드</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔐 접속 인증")
        st.info("대시보드에 접근하려면 비밀번호를 입력하세요.")
        
        with st.form("login_form"):
            password_input = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
            submit = st.form_submit_button("🔓 로그인", type="primary")
            
            if submit:
                if password_input == DASHBOARD_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 올바르지 않습니다.")
        
        st.caption("※ 비밀번호 문의: 담당자에게 연락하세요.")
        return  # 인증 전 여기서 종료
    # ========== 인증 완료 ==========
    
    # 브랜드 헤더
    st.markdown(f"""
    <div class="brandbar">
        <div style="display: flex; align-items: center; gap: 16px;">
            {f'<img src="{logo_url}" alt="{BRAND_NAME} 로고" />' if logo_url else ''}
            <h1>📊 유아플랜 통합 관리 대시보드</h1>
        </div>
        <div class="version">
            <div>v2025-12-08-transparent</div>
            <div style="font-size: 12px; opacity: 0.7;">{current_time}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 로그아웃 버튼 (우측 상단)
    col_spacer, col_logout = st.columns([8, 1])
    with col_logout:
        if st.button("🚪 로그아웃", key="btn_logout"):
            st.session_state.authenticated = False
            st.rerun()
    
    # 검색 영역
    st.markdown("""
    <div class="search-section">
        <h3>🔍 고객 통합 정보 조회</h3>
        <p>접수번호를 입력하여 고객 정보, 소통 로그, 링크 발급, AI 분석을 한 화면에서 관리하세요.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 검색 입력
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        receipt_no_input = st.text_input(
            "접수번호",
            value=st.session_state.searched_receipt_no,
            placeholder="예: YP20240914001",
            label_visibility="collapsed"
        )
    
    with col2:
        search_clicked = st.button("🔍 조회", type="primary", use_container_width=True)
    
    with col3:
        if st.button("🔄 새로고침", use_container_width=True):
            if st.session_state.searched_receipt_no:
                st.session_state.search_result = fetch_integrated_data(st.session_state.searched_receipt_no)
            st.rerun()
    
    # 검색 실행
    if search_clicked and receipt_no_input:
        st.session_state.searched_receipt_no = receipt_no_input.strip()
        st.session_state.issued_link = None
        st.session_state.ai_analysis_result = None
        
        with st.spinner("🔄 데이터 조회 중..."):
            st.session_state.search_result = fetch_integrated_data(receipt_no_input.strip())
    
    # 결과 표시
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
            
            # 요약 헤더
            col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
            with col_h1:
                st.markdown(f"### 👤 {customer_name}")
            with col_h2:
                st.markdown(f"**접수번호:** `{receipt_no}`")
            with col_h3:
                st.markdown(f"**진행률:** {progress}%")
            
            st.markdown(format_progress_bar(progress), unsafe_allow_html=True)
            
            # 요약 카드
            render_summary_cards(data)
            
            st.markdown("---")
            
            # 2차 링크 발급
            render_link_issue_section(receipt_no, customer_name)
            
            # 상세 데이터 보기
            with st.expander("📝 상세 데이터 보기 (펜딩/1차/2차/3차)", expanded=False):
                render_stage_card("1️⃣ 1차 설문", stage1, 1)
                render_stage_card("2️⃣ 2차 설문", stage2, 2)
                render_stage_card("3️⃣ 3차 설문", stage3, 3)
            
            # 소통 로그
            render_comm_logs_section(comm_logs, receipt_no)
            
            st.markdown("---")
            
            # AI 분석 (버튼 클릭 방식)
            render_ai_analysis_section(data)
            
            st.markdown("---")
            
            # 정책자금 결과 저장
            render_result_save_section(receipt_no)
            
            st.markdown("---")
            
            # 고객 연락
            st.markdown("### 📞 고객 연락")
            if stage1:
                phone = stage1.get('phone', '')
                if phone:
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.markdown(f'<a href="tel:{phone}" class="action-btn action-btn-primary" style="display:block; text-align:center;">📞 전화걸기 ({phone})</a>', unsafe_allow_html=True)
                    with col_c2:
                        st.markdown(f'<a href="{KAKAO_CHAT_URL}" target="_blank" class="action-btn action-btn-kakao" style="display:block; text-align:center;">💬 카카오 상담</a>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # AI 문서 다운로드
            st.markdown("### 📄 AI 매칭용 문서 다운로드")
            doc_content = generate_doc_content(data)
            filename = f"유아플랜_{receipt_no}_{datetime.now().strftime('%Y%m%d')}.txt"
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(create_download_link(doc_content, filename), unsafe_allow_html=True)
            with col_d2:
                if st.button("📋 클립보드용 표시"):
                    st.code(doc_content)
        
        elif result.get("status") == "error":
            st.error(f"❌ 조회 실패: {result.get('message')}")
    
    elif search_clicked and not receipt_no_input:
        st.warning("⚠️ 접수번호를 입력해주세요.")

if __name__ == "__main__":
    main()