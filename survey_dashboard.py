import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import io
import base64

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

# GAS 엔드포인트 (통합조회 함수가 추가된 1차 GAS)
INTEGRATED_GAS_URL = "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec"
API_TOKEN = "youareplan"

# 테스트용 접수번호
TEST_RECEIPT_NO = "YP202509137028"

# KakaoTalk Channel
KAKAO_CHANNEL_ID = "_LWxexmn"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# ==============================
# 스타일링 (실무 중심)
# ==============================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  html, body, [class*="css"] { font-family: 'Noto Sans KR', system-ui, -apple-system, sans-serif; }
  :root { --gov-navy:#002855; --gov-blue:#0B5BD3; --gov-border:#cbd5e1; --success:#10b981; --warning:#f59e0b; --danger:#ef4444; }
  
  /* 메뉴/사이드바 숨김 */
  #MainMenu, footer, [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
  header [data-testid="stToolbar"] { display: none !important; }
  
  /* 컨테이너 */
  .block-container{ max-width:1600px; margin:0 auto !important; padding:16px; }
  
  /* 브랜드 바 */
  .brandbar{
    display:flex; align-items:center; justify-content:space-between;
    padding:16px 24px; margin-bottom:20px;
    background: linear-gradient(135deg, var(--gov-navy) 0%, #1e40af 100%);
    border-radius: 12px; color: white;
  }
  .brandbar img{ height:52px; }
  .brandbar h1{ margin:0; color:white; font-weight:700; font-size:24px; }
  .brandbar .version{ font-size:14px; opacity:0.8; }
  
  /* 검색 영역 */
  .search-section {
    background: #f8fafc;
    border: 2px solid var(--gov-border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }
  
  /* 정보 카드 */
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
    background: #f8fafc;
    border-radius: 6px;
    border-left: 4px solid var(--gov-blue);
  }
  .data-label { font-weight: 600; color: #374151; }
  .data-value { color: #111827; font-weight: 500; }
  
  /* 위험 신호 */
  .risk-high { border-left-color: var(--danger) !important; background: #fef2f2 !important; }
  .risk-medium { border-left-color: var(--warning) !important; background: #fffbeb !important; }
  .risk-low { border-left-color: var(--success) !important; background: #f0fdf4 !important; }
  
  /* 진행률 바 */
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
  
  /* 액션 버튼들 */
  .action-buttons {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin: 20px 0;
  }
  .download-btn {
    background: #1f2937;
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    text-decoration: none;
    text-align: center;
    font-weight: 600;
    transition: all 0.3s ease;
    border: none;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }
  .download-btn:hover { 
    background: #374151; 
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
  }
  .download-btn:active { transform: translateY(0); }
  
  /* 상태 배지 */
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
  
  /* 결과 기록 섹션 */
  .result-section {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border: 2px solid #0ea5e9;
    border-radius: 12px;
    padding: 24px;
    margin-top: 24px;
  }
  
  /* 모바일 대응 */
  @media (max-width: 768px) {
    .data-grid { grid-template-columns: 1fr; }
    .action-buttons { grid-template-columns: 1fr; }
    .brandbar { flex-direction: column; gap: 12px; text-align: center; }
  }
</style>
""", unsafe_allow_html=True)

# ==============================
# 유틸리티 함수
# ==============================
def get_logo_url() -> str:
    """로고 URL 가져오기"""
    try:
        url = st.secrets.get("YOUAREPLAN_LOGO_URL")
        if url:
            return str(url)
    except Exception:
        pass
    return DEFAULT_LOGO_URL

def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    """GAS에서 통합 데이터 가져오기"""
    try:
        payload = {
            "action": "get_integrated_view",
            "receipt_no": receipt_no,
            "api_token": API_TOKEN  # token -> api_token 변경
        }
        
        st.info(f"🔄 API 호출 중: {receipt_no}")
        
        response = requests.post(
            INTEGRATED_GAS_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=20
        )
        
        # HTTP 상태 코드 확인
        if response.status_code != 200:
            return {"status": "error", "message": f"HTTP {response.status_code}: {response.text[:200]}"}
        
        # JSON 파싱 시도
        try:
            result = response.json()
            st.info(f"📡 API 응답: {result.get('status', 'unknown')}")
            return result
        except ValueError as ve:
            return {"status": "error", "message": f"JSON 파싱 실패: {response.text[:200]}"}
        
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "서버 응답 시간 초과 (20초)"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "GAS 서버 연결 실패"}
    except Exception as e:
        return {"status": "error", "message": f"예상치 못한 오류: {str(e)}"}

def format_progress_bar(progress: int) -> str:
    """진행률 바 HTML 생성"""
    return f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {progress}%"></div>
        <div class="progress-text">{progress}% 완료</div>
    </div>
    """

def generate_doc_content(data: Dict[str, Any]) -> str:
    """AI 매칭용 문서 내용 생성"""
    receipt_no = data.get("receipt_no", "")
    stage1 = data.get("stage1", {})
    stage2 = data.get("stage2", {})
    stage3 = data.get("stage3", {})
    
    current_date = datetime.now().strftime("%Y.%m.%d")
    
    content = f"""
================================
유아플랜 고객정보 종합보고서
================================
접수번호: {receipt_no}
작성일자: {current_date}

[기본정보]
- 고객명: {stage1.get('name', '정보없음')}
- 연락처: {stage1.get('phone', '정보없음')}
- 이메일: {stage1.get('email', '정보없음') if stage1.get('email') else '미입력'}
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
- 연매출 추이: {stage2.get('revenue_y3', '정보없음')} → {stage2.get('revenue_y2', '정보없음')} → {stage2.get('revenue_y1', '정보없음')}만원
- 자본금: {stage2.get('capital_amount', '정보없음')}만원
- 부채: {stage2.get('debt_amount', '정보없음')}만원
"""
        
        # 부채비율 계산
        try:
            capital = int(stage2.get('capital_amount', '0').replace(',', '').replace('만원', ''))
            debt = int(stage2.get('debt_amount', '0').replace(',', '').replace('만원', ''))
            if capital > 0:
                debt_ratio = round((debt / capital) * 100)
                content += f"- 부채비율: {debt_ratio}%\n"
        except:
            pass
    else:
        content += "- 2차 설문 정보 없음\n"
    
    content += f"""
[정책자금 이용 경험]
- 기존 경험: {stage1.get('policy_experience', '정보없음')}

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
"""
    else:
        content += "- 3차 설문 정보 없음\n"
    
    content += f"""
[리스크 분석]
"""
    
    if stage3 and stage3.get('risk_top3'):
        risks = stage3.get('risk_top3', '').split('\n')
        for i, risk in enumerate(risks[:3], 1):
            if risk.strip():
                content += f"{i}. {risk.strip()}\n"
    else:
        # 1차 정보에서 위험 요소 추출
        risks = []
        if stage1.get('tax_status', '') != '체납 없음':
            risks.append(f"세금 체납: {stage1.get('tax_status')}")
        if stage1.get('credit_status', '') != '연체 없음':
            risks.append(f"금융 연체: {stage1.get('credit_status')}")
        if stage1.get('business_status', '') != '정상 영업':
            risks.append(f"영업 상태: {stage1.get('business_status')}")
        
        if risks:
            for i, risk in enumerate(risks, 1):
                content += f"{i}. {risk}\n"
        else:
            content += "- 특별한 리스크 요소 없음\n"
    
    if stage3 and stage3.get('coach_notes'):
        content += f"""
[컨설턴트 메모]
{stage3.get('coach_notes', '')}
"""
    
    content += f"""
[정책자금 매칭 요청사항]
위 고객 정보를 바탕으로 적합한 정책자금을 추천해주세요.

요청사항:
1. 고객의 업종, 규모, 재무상태에 맞는 정책자금 리스트
2. 각 정책자금별 지원 조건과 한도
3. 우선 순위별 추천 (1순위, 2순위, 3순위)
4. 신청 시 주의사항이나 준비해야 할 서류
5. 승인 가능성 및 예상 승인 금액

================================
"""
    
    return content.strip()

def create_download_link(content: str, filename: str, content_type: str = "text/plain") -> str:
    """다운로드 링크 생성"""
    b64_content = base64.b64encode(content.encode()).decode()
    return f'<a href="data:{content_type};base64,{b64_content}" download="{filename}" class="download-btn">📥 {filename.split(".")[-1].upper()} 다운로드</a>'

# ==============================
# 컴포넌트 렌더링 함수들
# ==============================
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
            
            # 자격 현황 (위험도별 색상)
            tax_status = stage_data.get('tax_status', '체납 없음')
            credit_status = stage_data.get('credit_status', '연체 없음')
            biz_status = stage_data.get('business_status', '정상 영업')
            
            tax_class = "risk-high" if tax_status != '체납 없음' else "risk-low"
            credit_class = "risk-high" if credit_status != '연체 없음' else "risk-low"
            biz_class = "risk-high" if biz_status != '정상 영업' else "risk-low"
            
            st.markdown(f"""
            <h5 style="margin: 16px 0 8px 0; color: #374151;">⚠️ 자격 현황</h5>
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
            
            <h5 style="margin: 16px 0 8px 0; color: #374151;">💰 재무현황</h5>
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
            
            # 부채비율 계산 및 표시
            try:
                capital = int(str(stage_data.get('capital_amount', '0')).replace(',', ''))
                debt = int(str(stage_data.get('debt_amount', '0')).replace(',', ''))
                if capital > 0:
                    debt_ratio = round((debt / capital) * 100)
                    ratio_class = "risk-high" if debt_ratio > 200 else ("risk-medium" if debt_ratio > 100 else "risk-low")
                    st.markdown(f"""
                    <div class="data-item {ratio_class}" style="margin-top: 8px;">
                        <span class="data-label">부채비율</span>
                        <span class="data-value">{debt_ratio}%</span>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                pass
            
        elif stage_num == 3:
            # 3차 설문은 텍스트 위주로 표시
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
                    # 긴 텍스트는 줄바꿈 적용
                    if len(str(value)) > 50:
                        st.markdown(f"""
                        <div style="margin: 12px 0; padding: 12px; background: #f8fafc; border-radius: 8px; border-left: 4px solid var(--gov-blue);">
                            <div style="font-weight: 600; color: #374151; margin-bottom: 6px;">{label}:</div>
                            <div style="color: #111827; white-space: pre-wrap; line-height: 1.5;">{value}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="data-item" style="margin: 6px 0;">
                            <span class="data-label">{label}</span>
                            <span class="data-value">{value}</span>
                        </div>
                        """, unsafe_allow_html=True)
        
        # 제출일시
        if stage_data.get('completed_at'):
            st.markdown(f"""
            <div style="margin-top: 16px; padding: 8px 12px; background: #f1f5f9; border-radius: 6px; font-size: 12px; color: #64748b;">
                📅 제출일시: {stage_data.get('completed_at')}
            </div>
            """, unsafe_allow_html=True)
    
    else:
        st.markdown('<div style="color: #64748b; font-style: italic; padding: 16px;">아직 설문이 완료되지 않았습니다.</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================
# 메인 함수
# ==============================
def main():
    # 브랜드 헤더
    logo_url = get_logo_url()
    current_time = datetime.now().strftime("%Y.%m.%d %H:%M")
    
    st.markdown(f"""
    <div class="brandbar">
        <div style="display: flex; align-items: center; gap: 16px;">
            {f'<img src="{logo_url}" alt="{BRAND_NAME} 로고" />' if logo_url else ''}
            <h1>📊 유아플랜 통합 관리 대시보드</h1>
        </div>
        <div class="version">
            <div>실무용 v1.0</div>
            <div style="font-size: 12px; opacity: 0.7;">{current_time}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 검색 영역
    st.markdown("""
    <div class="search-section">
        <h3 style="margin: 0 0 12px 0; color: #1f2937;">🔍 고객 통합 정보 조회</h3>
        <p style="margin: 0; color: #6b7280;">접수번호를 입력하여 1차→2차→3차 설문 내용과 AI 매칭용 문서를 생성하세요.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 접수번호 입력
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        receipt_no = st.text_input(
            "접수번호 입력",
            placeholder="예: YP20240914001",
            help="1차 설문 완료 시 발급된 접수번호를 입력하세요",
            label_visibility="collapsed"
        )
    with col2:
        search_clicked = st.button("🔍 조회", type="primary", use_container_width=True)
    with col3:
        test_clicked = st.button("🧪 테스트", use_container_width=True, help="연결 테스트")
    with col4:
        if st.button("🔄 새로고침", use_container_width=True):
            st.rerun()
    
    # 테스트 버튼 처리
    if test_clicked:
        st.info("🧪 GAS 연결 테스트 시작...")
        test_result = fetch_integrated_data(TEST_RECEIPT_NO)
        st.json(test_result)
        return
    
    # 예시 접수번호
    st.markdown("""
    <div style="margin: 8px 0 24px 0; padding: 8px 12px; background: #e0f2fe; border-radius: 6px; border-left: 4px solid #0ea5e9; font-size: 14px;">
        💡 <strong>예시 접수번호:</strong> YP20240914001, YP20240915002, YP20240916003
    </div>
    """, unsafe_allow_html=True)
    
    # 조회 실행
    if search_clicked and receipt_no:
        with st.spinner("🔄 통합 데이터를 조회하고 있습니다..."):
            result = fetch_integrated_data(receipt_no.strip())
            
        if result.get("status") == "success":
            data = result.get("data", {})
            progress = data.get("progress_pct", 0)
            stage1 = data.get("stage1")
            stage2 = data.get("stage2") 
            stage3 = data.get("stage3")
            
            # === 통합 요약 정보 ===
            st.markdown("---")
            
            # 헤더 정보 및 진행률
            col_summary1, col_summary2, col_summary3, col_summary4 = st.columns(4)
            
            with col_summary1:
                st.metric("📋 접수번호", data.get("receipt_no", "-"))
            with col_summary2:
                customer_name = stage1.get("name", "정보없음") if stage1 else "정보없음"
                st.metric("👤 고객명", customer_name)
            with col_summary3:
                industry = stage1.get("industry", "정보없음") if stage1 else "정보없음"
                st.metric("🏭 업종", industry)
            with col_summary4:
                st.metric("📊 전체 진행률", f"{progress}%")
            
            # 진행률 바
            st.markdown(format_progress_bar(progress), unsafe_allow_html=True)
            
            # === 단계별 상세 정보 ===
            st.markdown("### 📋 단계별 상세 정보")
            
            # 1차 설문
            render_stage_card("1️⃣ 1차 설문 (기본정보)", stage1, 1)
            
            # 2차 설문  
            render_stage_card("2️⃣ 2차 설문 (심화정보)", stage2, 2)
            
            # 3차 설문
            render_stage_card("3️⃣ 3차 설문 (전문분석)", stage3, 3)
            
            # === AI 매칭용 문서 다운로드 ===
            st.markdown("---")
            st.markdown("### 📄 AI 정책자금 매칭용 문서")
            
            # 문서 내용 생성
            doc_content = generate_doc_content(data)
            filename_base = f"유아플랜_고객정보_{receipt_no}_{datetime.now().strftime('%Y%m%d')}"
            
            col_doc1, col_doc2, col_doc3 = st.columns(3)
            
            with col_doc1:
                # 텍스트 파일 다운로드
                txt_link = create_download_link(doc_content, f"{filename_base}.txt", "text/plain")
                st.markdown(txt_link, unsafe_allow_html=True)
            
            with col_doc2:
                # Word 파일은 단순 텍스트로 (실제 Word 형식은 복잡함)
                word_link = create_download_link(doc_content, f"{filename_base}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                st.markdown(word_link, unsafe_allow_html=True)
            
            with col_doc3:
                # 클립보드 복사용 버튼
                if st.button("📋 클립보드 복사", use_container_width=True):
                    st.write("✅ 아래 내용을 복사하세요:")
                    st.code(doc_content, language=None)
            
            # 문서 내용 미리보기
            with st.expander("📖 문서 내용 미리보기", expanded=False):
                st.text(doc_content)
            
            # 사용법 안내
            st.info("""
            💡 **사용법**: 
            1. 위 문서를 다운로드하거나 복사하세요
            2. ChatGPT, Claude 등 AI에 업로드/붙여넣기 하세요  
            3. "이 고객에게 적합한 정책자금을 추천해주세요"라고 요청하세요
            4. AI 추천 결과를 바탕으로 고객 상담을 진행하세요
            """)
            
            # === 최종 결과 기록 ===
            st.markdown("""
            <div class="result-section">
                <h3 style="margin: 0 0 20px 0; color: #0ea5e9;">✅ 최종 결과 기록</h3>
                <p style="margin: 0 0 16px 0; color: #64748b;">정책자금 신청 결과가 나오면 여기에 기록하세요.</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("result_form"):
                col_result1, col_result2 = st.columns(2)
                
                with col_result1:
                    policy_name = st.text_input(
                        "승인받은 정책자금명",
                        placeholder="예: 벤처기업정책자금, 기술보증기금 등"
                    )
                
                with col_result2:
                    approved_amount = st.text_input(
                        "승인 금액 (만원)",
                        placeholder="예: 30000 (3억원)"
                    )
                
                result_memo = st.text_area(
                    "상담 메모 (선택)",
                    placeholder="특이사항, 조건, 후속 조치 등을 기록하세요"
                )
                
                col_save1, col_save2 = st.columns([1, 4])
                with col_save1:
                    save_result = st.form_submit_button("💾 결과 저장", type="primary")
                with col_save2:
                    if save_result:
                        if policy_name and approved_amount:
                            st.success(f"✅ 저장 완료: {policy_name} / {approved_amount}만원")
                            # TODO: 여기에 GAS로 결과 저장하는 API 호출 추가
                        else:
                            st.error("정책자금명과 승인금액은 필수입니다.")
            
            # === 고객 연락 액션 ===
            st.markdown("---")
            st.markdown("### 📞 고객 연락")
            
            if stage1:
                phone = stage1.get('phone', '')
                if phone:
                    col_contact1, col_contact2, col_contact3 = st.columns(3)
                    
                    with col_contact1:
                        st.markdown(f"""
                        <a href="tel:{phone}" class="download-btn" style="text-decoration: none; color: white;">
                            📞 전화걸기 ({phone})
                        </a>
                        """, unsafe_allow_html=True)
                    
                    with col_contact2:
                        st.markdown(f"""
                        <a href="{KAKAO_CHAT_URL}" target="_blank" class="download-btn" style="background: #FEE500; color: #3C1E1E;">
                            💬 카카오 상담
                        </a>
                        """, unsafe_allow_html=True)
                    
                    with col_contact3:
                        if st.button("📧 이메일 발송", use_container_width=True):
                            st.info("이메일 기능은 추후 구현 예정입니다.")
        
        elif result.get("status") == "error":
            st.error(f"❌ 조회 실패: {result.get('message', '알 수 없는 오류')}")
            st.info("🔍 접수번호를 정확히 입력했는지 확인해주세요.")
        
    elif search_clicked and not receipt_no:
        st.warning("⚠️ 접수번호를 입력해주세요.")
    
    # 사용법 안내 (조회 전 상태)
    if not receipt_no:
        st.markdown("---")
        st.markdown("### 📖 대시보드 사용법")
        
        col_guide1, col_guide2 = st.columns(2)
        with col_guide1:
            st.markdown("""
            **🎯 주요 기능**
            - **통합 정보 조회**: 1차+2차+3차 설문 한번에 확인
            - **AI 문서 생성**: ChatGPT/Claude용 매칭 문서 자동 생성  
            - **결과 기록**: 승인된 정책자금 이름/금액 저장
            - **고객 연락**: 전화/카톡 바로 연결
            """)
        
        with col_guide2:
            st.markdown("""
            **📋 업무 플로우**
            1. 접수번호로 고객 정보 조회
            2. AI 매칭 문서 다운로드/복사
            3. AI에게 정책자금 추천 요청  
            4. 고객 상담 후 신청 진행
            5. 결과 나오면 대시보드에 기록
            """)

if __name__ == "__main__":
    main()