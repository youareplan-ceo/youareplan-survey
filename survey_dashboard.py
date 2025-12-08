import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import base64
import os

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

# ==============================
# 스타일링
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }
  :root { --gov-navy:#002855; --gov-blue:#0B5BD3; --gov-border:#cbd5e1; --success:#10b981; --warning:#f59e0b; --danger:#ef4444; }
  
  #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  
  .block-container{ max-width:1600px; margin:0 auto !important; padding:16px; }
  
  .brandbar{
    display:flex; align-items:center; justify-content:space-between;
    padding:16px 24px; margin-bottom:20px;
    background: linear-gradient(135deg, var(--gov-navy) 0%, #1e40af 100%);
    border-radius: 12px; color: white;
  }
  .brandbar img{ height:52px; }
  .brandbar h1{ margin:0; color:white; font-weight:700; font-size:24px; }
  .brandbar .version{ font-size:14px; opacity:0.8; }
  
  .search-section {
    background: #f8fafc;
    border: 2px solid var(--gov-border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }
  
  .info-card {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    margin: 12px 0;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }
  .info-card h4 {
    color: var(--gov-navy);
    margin: 0 0 16px 0;
    font-weight: 700;
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 8px;
  }
  
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
    background: #f8fafc;
    border-radius: 6px;
    border-left: 4px solid var(--gov-blue);
  }
  .data-label { font-weight: 600; color: #374151; }
  .data-value { color: #111827; font-weight: 500; }
  
  .risk-high { border-left-color: var(--danger) !important; background: #fef2f2 !important; }
  .risk-medium { border-left-color: var(--warning) !important; background: #fffbeb !important; }
  .risk-low { border-left-color: var(--success) !important; background: #f0fdf4 !important; }
  
  .progress-container {
    background: #f1f5f9;
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
  .action-btn:hover { 
    background: #374151; 
  }
  .action-btn-primary {
    background: var(--gov-navy);
  }
  .action-btn-danger {
    background: #dc2626;
  }
  .action-btn-warning {
    background: #d97706;
  }
  .action-btn-kakao {
    background: #FEE500;
    color: #3C1E1E !important;
  }
  
  .status-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px;
  }
  .badge-completed { background: #d1fae5; color: #065f46; }
  .badge-progress { background: #fef3c7; color: #92400e; }
  .badge-pending { background: #fee2e2; color: #991b1b; }
  
  .result-section {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border: 2px solid #0ea5e9;
    border-radius: 12px;
    padding: 24px;
    margin-top: 24px;
  }
  
  .comm-log-item {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
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
    color: var(--gov-navy);
    background: #e0f2fe;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 13px;
  }
  .comm-log-date {
    font-size: 12px;
    color: #6b7280;
  }
  .comm-log-content {
    color: #1f2937;
    line-height: 1.6;
    white-space: pre-wrap;
  }
  
  .link-box {
    background: #f0fdf4;
    border: 2px solid #10b981;
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
    word-break: break-all;
  }
  
  .summary-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
  }
  .summary-card .label {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 4px;
  }
  .summary-card .value {
    font-size: 20px;
    font-weight: 700;
    color: var(--gov-navy);
  }
  
  .ai-result-box {
    background: #fffbeb;
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    white-space: pre-wrap;
    line-height: 1.7;
  }
  
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
    if "searched_receipt_no" not in st.session_state:
        st.session_state.searched_receipt_no = ""
    if "search_result" not in st.session_state:
        st.session_state.search_result = None
    if "issued_link" not in st.session_state:
        st.session_state.issued_link = None
    if "ai_analysis_result" not in st.session_state:
        st.session_state.ai_analysis_result = None

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
        
        return response.json()
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

def issue_second_link(receipt_no: str, hours: int) -> Dict[str, Any]:
    """2차 설문 링크 발급"""
    try:
        payload = {
            "action": "issue_token",
            "api_token": API_TOKEN,
            "receipt_no": receipt_no,
            "hours": hours,
            "issued_by": "dashboard"
        }
        
        response = requests.post(
            INTEGRATED_GAS_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code != 200:
            return {"ok": False, "error": f"HTTP {response.status_code}"}
        
        return response.json()
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

def call_gemini_analysis(doc_content: str) -> Dict[str, Any]:
    """Gemini API로 AI 분석 실행"""
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "Gemini API 키가 설정되지 않았습니다"}
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""다음 고객 정보를 분석하여 적합한 정책자금을 추천해주세요.

{doc_content}

다음 형식으로 답변해주세요:
1. 고객 현황 요약 (3줄 이내)
2. 추천 정책자금 TOP 3 (각각 이름, 지원조건, 예상한도, 추천이유)
3. 주의사항 및 준비사항
4. 승인 가능성 평가 (높음/보통/낮음 + 근거)
"""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }
        
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code != 200:
            return {"ok": False, "error": f"Gemini API 오류: HTTP {response.status_code}"}
        
        result = response.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if text:
            return {"ok": True, "analysis": text}
        else:
            return {"ok": False, "error": "분석 결과가 비어있습니다"}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ==============================
# 문서 생성 함수
# ==============================
def generate_doc_content(data: Dict[str, Any]) -> str:
    """AI 매칭용 문서 내용 생성"""
    receipt_no = data.get("receipt_no", "")
    stage1 = data.get("stage1") or {}
    stage2 = data.get("stage2") or {}
    stage3 = data.get("stage3") or {}
    
    current_date = datetime.now().strftime("%Y.%m.%d")
    
    content = f"""================================
유아플랜 고객정보 종합보고서
================================
접수번호: {receipt_no}
작성일자: {current_date}

[기본정보]
- 고객명: {stage1.get('name', '정보없음')}
- 연락처: {stage1.get('phone', '정보없음')}
- 이메일: {stage1.get('email', '미입력') or '미입력'}
- 사업형태: {stage1.get('business_type', '정보없음')}
- 업종: {stage1.get('industry', '정보없음')}
- 지역: {stage1.get('region', '정보없음')}
- 직원수: {stage1.get('employee_count', '정보없음')}
- 필요자금: {stage1.get('funding_amount', '정보없음')}

[재무현황]
"""
    
    if stage2:
        content += f"""- 사업자명: {stage2.get('business_name', '정보없음')}
- 사업시작일: {stage2.get('startup_date', '정보없음')}
- 사업자등록번호: {stage2.get('biz_reg_no', '정보없음')}
- 연매출 추이: {stage2.get('revenue_y3', '-')} → {stage2.get('revenue_y2', '-')} → {stage2.get('revenue_y1', '-')}만원
- 자본금: {stage2.get('capital_amount', '-')}만원
- 부채: {stage2.get('debt_amount', '-')}만원
"""
        try:
            capital = int(str(stage2.get('capital_amount', '0')).replace(',', ''))
            debt = int(str(stage2.get('debt_amount', '0')).replace(',', ''))
            if capital > 0:
                debt_ratio = round((debt / capital) * 100)
                content += f"- 부채비율: {debt_ratio}%\n"
        except:
            pass
    else:
        content += "- 2차 설문 정보 없음\n"
    
    content += f"""
[자격 현황]
- 세금 체납: {stage1.get('tax_status', '정보없음')}
- 금융 연체: {stage1.get('credit_status', '정보없음')}
- 영업 상태: {stage1.get('business_status', '정보없음')}

[담보/보증/대출 현황]
"""
    
    if stage3:
        content += f"""- 담보/보증 계획: {stage3.get('collateral_profile', '정보없음')}
- 세무/신용 상태: {stage3.get('tax_credit_summary', '정보없음')}
- 기존 대출 현황: {stage3.get('loan_summary', '정보없음')}
- 준비된 서류: {stage3.get('docs_check', '정보없음')}
- 우대/제외 요건: {stage3.get('priority_exclusion', '정보없음')}
- 리스크 Top3: {stage3.get('risk_top3', '정보없음')}
"""
    else:
        content += "- 3차 설문 정보 없음\n"
    
    content += "\n================================"
    
    return content

# ==============================
# 렌더링 함수들
# ==============================
def render_summary_cards(data: Dict[str, Any]) -> None:
    """요약 카드 렌더링"""
    stage1 = data.get("stage1") or {}
    stage2 = data.get("stage2") or {}
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">업종</div>
            <div class="value">{stage1.get('industry', '-')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # 성장률 계산
        growth = "-"
        try:
            if stage2:
                y1 = int(str(stage2.get('revenue_y1', '0')).replace(',', ''))
                y2 = int(str(stage2.get('revenue_y2', '0')).replace(',', ''))
                if y2 > 0:
                    growth = f"{round((y1 - y2) / y2 * 100)}%"
        except:
            pass
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">성장률</div>
            <div class="value">{growth}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # 부채비율 계산
        debt_ratio = "-"
        try:
            if stage2:
                capital = int(str(stage2.get('capital_amount', '0')).replace(',', ''))
                debt = int(str(stage2.get('debt_amount', '0')).replace(',', ''))
                if capital > 0:
                    debt_ratio = f"{round(debt / capital * 100)}%"
        except:
            pass
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">부채비율</div>
            <div class="value">{debt_ratio}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # 리스크 판단
        risk = "양호"
        risk_factors = []
        if stage1.get('tax_status', '') not in ['', '체납 없음']:
            risk_factors.append("체납")
        if stage1.get('credit_status', '') not in ['', '연체 없음']:
            risk_factors.append("연체")
        if stage1.get('business_status', '') not in ['', '정상 영업']:
            risk_factors.append("휴/폐업")
        
        if len(risk_factors) >= 2:
            risk = "⚠️ 위험"
        elif len(risk_factors) == 1:
            risk = "⚠️ 주의"
        
        st.markdown(f"""
        <div class="summary-card">
            <div class="label">리스크</div>
            <div class="value">{risk}</div>
        </div>
        """, unsafe_allow_html=True)

def render_stage_card(title: str, stage_data: Optional[Dict], stage_num: int) -> None:
    """단계별 카드 렌더링"""
    status_class = "badge-completed" if stage_data else "badge-pending"
    status_text = "완료" if stage_data else "미완료"
    
    st.markdown(f"""
    <div class="info-card">
        <h4>{title} <span class="status-badge {status_class}">{status_text}</span></h4>
    """, unsafe_allow_html=True)
    
    if stage_data:
        if stage_num == 1:
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
            
            tax_status = stage_data.get('tax_status', '체납 없음')
            credit_status = stage_data.get('credit_status', '연체 없음')
            biz_status = stage_data.get('business_status', '정상 영업')
            
            tax_class = "risk-high" if tax_status != '체납 없음' else "risk-low"
            credit_class = "risk-high" if credit_status != '연체 없음' else "risk-low"
            biz_class = "risk-high" if biz_status != '정상 영업' else "risk-low"
            
            st.markdown(f"""
            <h5 style="margin: 16px 0 8px 0; color: #374151;">⚠️ 자격 현황</h5>
            <div class="data-grid">
                <div class="data-item {tax_class}"><span class="data-label">세금 체납</span><span class="data-value">{tax_status}</span></div>
                <div class="data-item {credit_class}"><span class="data-label">금융 연체</span><span class="data-value">{credit_status}</span></div>
                <div class="data-item {biz_class}"><span class="data-label">영업 상태</span><span class="data-value">{biz_status}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        elif stage_num == 2:
            st.markdown(f"""
            <div class="data-grid">
                <div class="data-item"><span class="data-label">사업자명</span><span class="data-value">{stage_data.get('business_name', '-')}</span></div>
                <div class="data-item"><span class="data-label">사업시작일</span><span class="data-value">{stage_data.get('startup_date', '-')}</span></div>
                <div class="data-item"><span class="data-label">사업자등록번호</span><span class="data-value">{stage_data.get('biz_reg_no', '-')}</span></div>
            </div>
            <h5 style="margin: 16px 0 8px 0; color: #374151;">💰 재무현황</h5>
            <div class="data-grid">
                <div class="data-item"><span class="data-label">당해연도 매출</span><span class="data-value">{stage_data.get('revenue_y1', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">전년도 매출</span><span class="data-value">{stage_data.get('revenue_y2', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">전전년도 매출</span><span class="data-value">{stage_data.get('revenue_y3', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">자본금</span><span class="data-value">{stage_data.get('capital_amount', '-')}만원</span></div>
                <div class="data-item"><span class="data-label">부채</span><span class="data-value">{stage_data.get('debt_amount', '-')}만원</span></div>
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
                    <div class="data-item" style="margin: 6px 0;">
                        <span class="data-label">{label}</span>
                        <span class="data-value" style="max-width: 70%; text-align: right;">{value}</span>
                    </div>
                    """, unsafe_allow_html=True)
        
        if stage_data.get('completed_at'):
            st.markdown(f"""
            <div style="margin-top: 16px; padding: 8px 12px; background: #f1f5f9; border-radius: 6px; font-size: 12px; color: #64748b;">
                📅 제출일시: {stage_data.get('completed_at')}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="color: #64748b; font-style: italic; padding: 16px;">아직 설문이 완료되지 않았습니다.</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_comm_logs_section(comm_logs: list, receipt_no: str) -> None:
    """소통 로그 섹션 렌더링"""
    with st.expander("💬 소통 로그", expanded=True):
        # 새 로그 입력
        st.markdown("**새 로그 작성**")
        col_author, col_content = st.columns([1, 4])
        
        with col_author:
            author = st.selectbox("작성자", ["대표", "직원"], key="new_log_author")
        
        with col_content:
            content = st.text_area("내용", placeholder="상담 내용, 특이사항 등...", key="new_log_content", height=80)
        
        if st.button("📝 등록", key="btn_add_log"):
            if content.strip():
                result = add_comm_log(receipt_no, author, content.strip())
                if result.get("ok"):
                    st.success("✅ 등록 완료")
                    # 데이터 새로고침
                    st.session_state.search_result = fetch_integrated_data(receipt_no)
                    st.rerun()
                else:
                    st.error(f"❌ 실패: {result.get('error')}")
            else:
                st.warning("내용을 입력하세요")
        
        st.markdown("---")
        
        # 기존 로그 표시
        if comm_logs and len(comm_logs) > 0:
            st.markdown(f"**기록된 로그 ({len(comm_logs)}건)**")
            for log in comm_logs:
                st.markdown(f"""
                <div class="comm-log-item">
                    <div class="comm-log-header">
                        <span class="comm-log-author">👤 {log.get('author', '-')}</span>
                        <span class="comm-log-date">🕐 {log.get('created_at', '-')}</span>
                    </div>
                    <div class="comm-log-content">{log.get('content', '')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 등록된 소통 로그가 없습니다.")

def render_link_issue_section(receipt_no: str, customer_name: str) -> None:
    """2차 링크 발급 섹션"""
    with st.expander("🔗 2차 링크 발급", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            hours = st.selectbox("유효시간", [6, 12, 24, 48], index=2, format_func=lambda x: f"{x}시간")
        
        with col2:
            st.write("")
            st.write("")
            if st.button("🔗 2차 링크 발급", key="btn_issue_link", type="primary"):
                with st.spinner("링크 발급 중..."):
                    result = issue_second_link(receipt_no, hours)
                    if result.get("ok"):
                        st.session_state.issued_link = result
                    else:
                        st.error(f"❌ 발급 실패: {result.get('error')}")
        
        # 발급된 링크 표시
        if st.session_state.issued_link:
            link_data = st.session_state.issued_link
            st.markdown(f"""
            <div class="link-box">
                <strong>✅ 링크 발급 완료</strong><br><br>
                <strong>고객명:</strong> {link_data.get('customer_name', customer_name)}<br>
                <strong>만료시각:</strong> {link_data.get('expires_at', '-')}<br><br>
                <strong>링크:</strong><br>
                <code>{link_data.get('link', '')}</code>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📋 링크 복사용 표시", key="btn_show_link"):
                st.code(link_data.get('link', ''))

def render_ai_analysis_section(data: Dict[str, Any]) -> None:
    """AI 분석 섹션"""
    st.markdown("### 🤖 AI 정책자금 분석")
    
    if not GEMINI_API_KEY:
        st.warning("⚠️ Gemini API 키가 설정되지 않았습니다. 환경변수 GEMINI_API_KEY를 설정하세요.")
        return
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("🤖 AI 심층 분석 실행", key="btn_ai_analysis", type="primary"):
            with st.spinner("🔄 Gemini AI 분석 중... (최대 1분 소요)"):
                doc_content = generate_doc_content(data)
                result = call_gemini_analysis(doc_content)
                
                if result.get("ok"):
                    st.session_state.ai_analysis_result = result.get("analysis")
                else:
                    st.error(f"❌ 분석 실패: {result.get('error')}")
    
    with col2:
        st.caption("Gemini 1.5 Flash 모델로 정책자금 매칭 분석을 수행합니다.")
    
    # 분석 결과 표시
    if st.session_state.ai_analysis_result:
        st.markdown(f"""
        <div class="ai-result-box">
            <strong>🤖 AI 분석 결과</strong><br><br>
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
    
    # 브랜드 헤더
    st.markdown(f"""
    <div class="brandbar">
        <div style="display: flex; align-items: center; gap: 16px;">
            {f'<img src="{logo_url}" alt="{BRAND_NAME} 로고" />' if logo_url else ''}
            <h1>📊 유아플랜 통합 관리 대시보드</h1>
        </div>
        <div class="version">
            <div>v2025-12-08</div>
            <div style="font-size: 12px; opacity: 0.7;">{current_time}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 검색 영역
    st.markdown("""
    <div class="search-section">
        <h3 style="margin: 0 0 12px 0; color: #1f2937;">🔍 고객 통합 정보 조회</h3>
        <p style="margin: 0; color: #6b7280;">접수번호를 입력하여 고객 정보, 소통 로그, 링크 발급, AI 분석을 한 화면에서 관리하세요.</p>
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
            
            # AI 분석
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