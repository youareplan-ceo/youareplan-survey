import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import os
import base64
import google.generativeai as genai
import importlib.metadata
import re # 정규표현식

# ==============================
# [설정] 설문지 앱 URL (배포된 실제 주소로 변경하세요!)
# ==============================
SURVEY1_URL = "https://your-survey1-app.streamlit.app" 
SURVEY2_URL = "https://your-survey2-app.streamlit.app" 
SURVEY3_URL = "https://your-survey3-app.streamlit.app" 

# ==============================
# 1. 페이지 설정
# ==============================
st.set_page_config(
    page_title="유아플랜 통합 관리 대시보드",
    page_icon="💼", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================
# 2. 환경 설정 & 로고
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
INTEGRATED_GAS_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

# [3차] URL (메모/계약 업데이트용)
THIRD_GAS_URL = os.getenv("THIRD_GAS_URL", "https://script.google.com/macros/s/YOUR_GAS_ID/exec")
API_TOKEN_3 = os.getenv("API_TOKEN_3", "youareplan_stage3")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ==============================
# 3. 재무 지표 계산 함수
# ==============================
def calculate_financial_metrics(s2: Dict) -> Dict:
    metrics = {
        "debt_ratio": "-", "debt_status": "gray",
        "growth_rate": "-", "growth_status": "gray"
    }
    
    if not s2:
        return metrics

    try:
        capital = int(str(s2.get('capital_amount', '0')).replace(',', '').replace('만원', ''))
        debt = int(str(s2.get('debt_amount', '0')).replace(',', '').replace('만원', ''))
        if capital > 0:
            ratio = round((debt / capital) * 100)
            metrics['debt_ratio'] = f"{ratio}%"
            if ratio > 400:
                metrics['debt_status'] = "red"
            elif ratio > 200:
                metrics['debt_status'] = "orange"
            else:
                metrics['debt_status'] = "green"
    except:
        pass

    try:
        rev_prev = int(str(s2.get('revenue_y2', '0')).replace(',', ''))
        rev_curr = int(str(s2.get('revenue_y1', '0')).replace(',', '')) 
        if rev_prev > 0:
            growth = round(((rev_curr - rev_prev) / rev_prev) * 100)
            sign = "+" if growth > 0 else ""
            metrics['growth_rate'] = f"{sign}{growth}%"
            if growth >= 20:
                metrics['growth_status'] = "blue"
            elif growth > 0:
                metrics['growth_status'] = "green"
            else:
                metrics['growth_status'] = "red"
    except:
        pass
    
    return metrics

# ==============================
# 4. 리포트 텍스트 생성
# ==============================
def generate_full_report(data: Dict[str, Any], ai_result: str = "", mode: str = "contract") -> str:
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    s3 = data.get("stage3") or {}
    metrics = calculate_financial_metrics(s2)
    
    title = "컨설팅 계약 제안서 (1,2차 분석)" if mode == "contract" else "최종 실행 전략 리포트 (1,2,3차 통합)"
    
    report = f"""
==================================================
[유아플랜] {title}
==================================================
접수번호: {data.get('receipt_no', '-')}
작성일시: {datetime.now().strftime("%Y-%m-%d %H:%M")}

1. 기업 진단 요약
--------------------------------------------------
- 고객명: {s1.get('name', '-')}
- 업종: {s1.get('industry', '-')}
- 지역: {s1.get('region', '-')}
- 사업형태: {s1.get('business_type', '-')}
- 직원수: {s1.get('employee_count', '-')}
- 필요자금: {s1.get('funding_amount', '-')}
"""

    if s2:
        report += f"""
2. 재무 현황 (2차)
--------------------------------------------------
- 사업자명: {s2.get('business_name', '-')}
- 사업시작일: {s2.get('startup_date', '-')}
- 올해 매출: {s2.get('revenue_y1', '-')}만원
- 전년 매출: {s2.get('revenue_y2', '-')}만원
- 자본금: {s2.get('capital_amount', '-')}만원
- 부채: {s2.get('debt_amount', '-')}만원
- 부채비율: {metrics['debt_ratio']}
- 성장률: {metrics['growth_rate']}
- 특허/인증: {s2.get('ip_status', '-')} / {s2.get('official_certs', '-')}
- 자금용도: {s2.get('funding_purpose', '-')}
"""

    if s3 and mode == "execution":
        report += f"""
3. 심층 분석 (3차)
--------------------------------------------------
- 담보/보증: {s3.get('collateral_profile', '-')}
- 세무/신용: {s3.get('tax_credit_summary', '-')}
- 기존 대출: {s3.get('loan_summary', '-')}
- 준비 서류: {s3.get('docs_check', '-')}
- 리스크: {s3.get('risk_top3', '-')}
- 컨설턴트 메모: {s3.get('coach_notes', '-')}
"""

    report += f"""
4. AI 분석 결과
--------------------------------------------------
{ai_result if ai_result else "AI 분석을 실행해주세요."}

==================================================
"""
    return report.strip()

# ==============================
# 5. AI 분석 로직
# ==============================
def calculate_model_score(model_name: str) -> float:
    score = 0.0
    name_lower = model_name.lower()
    
    version_match = re.search(r'(\d+)\.(\d+)', name_lower)
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        score += (major * 100000) + (minor * 10000)
    
    date_match = re.search(r'(\d{2})-(\d{2})', name_lower) 
    if date_match:
        month = int(date_match.group(1))
        day = int(date_match.group(2))
        score += (month * 100) + day
    elif '001' in name_lower: score += 1
    elif '002' in name_lower: score += 2

    if 'latest' in name_lower:
        score += 5000 
    elif not date_match and 'pro' in name_lower and 'preview' not in name_lower:
        score += 8000
        
    return score

def get_sorted_models(model_list: list) -> list:
    candidates = [m for m in model_list if 'image' not in m.lower() and 'vision' not in m.lower()]
    if not candidates: return []
    candidates.sort(key=calculate_model_score, reverse=True)
    return candidates

def analyze_with_gemini(api_key: str, data: Dict[str, Any]) -> str:
    if not api_key:
        return "⚠️ API 키가 설정되지 않았습니다."
    
    try:
        genai.configure(api_key=api_key)
        
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not available_models:
            return "⚠️ 사용 가능한 AI 모델을 찾을 수 없습니다."

        sorted_models = get_sorted_models(available_models)
        target_model_name = sorted_models[0]
        
        st.session_state['debug_sorted_models'] = sorted_models

        model = genai.GenerativeModel(target_model_name)
        
        s3 = data.get("stage3")
        
        if s3 and s3.get('coach_notes'):
            prompt = generate_execution_prompt(data)
            display_name = target_model_name.replace('models/', '')
            msg = f"🧠 [{display_name}] AI가 정밀 분석 중입니다... (5~10초)"
        else:
            prompt = generate_contract_prompt(data)
            display_name = target_model_name.replace('models/', '')
            msg = f"⚖️ [{display_name}] AI가 심사 중입니다... (5~10초)"
            
        with st.spinner(msg):
            response = model.generate_content(prompt)
            return response.text
            
    except Exception as e:
        try:
            ver = importlib.metadata.version('google-generativeai')
        except:
            ver = "unknown"
        return f"⚠️ AI 분석 오류: {str(e)}\n(SDK: {ver})"

def generate_contract_prompt(data: Dict[str, Any]) -> str:
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    metrics = calculate_financial_metrics(s2)
    
    return f"""
당신은 대한민국 최고의 정책자금 전문 컨설팅펌의 수석 심사역입니다.
제공된 기업 데이터를 바탕으로 매우 논리적이고 비판적인 시각에서 계약 여부를 판단하십시오.

# [기업 데이터]
- 고객명: {s1.get('name', '-')}
- 업종: {s1.get('industry', '-')}
- 지역: {s1.get('region', '-')}
- 사업형태: {s1.get('business_type', '-')}
- 직원수: {s1.get('employee_count', '-')}
- 필요자금: {s1.get('funding_amount', '-')}
- 정책자금 경험: {s1.get('policy_experience', '-')}

# [재무 현황]
- 사업자명: {s2.get('business_name', '-')}
- 업력: {s2.get('startup_date', '-')}
- 최근 매출: {s2.get('revenue_y1', '0')}만원
- 전년 매출: {s2.get('revenue_y2', '0')}만원
- 자본금: {s2.get('capital_amount', '0')}만원
- 부채: {s2.get('debt_amount', '0')}만원
- 부채비율: {metrics['debt_ratio']}
- 매출성장률: {metrics['growth_rate']}

# [리스크 현황]
- 세금 체납: {s1.get('tax_status', '-')}
- 금융 연체: {s1.get('credit_status', '-')}
- 영업 상태: {s1.get('business_status', '-')}

# [요청 사항 - Markdown 형식]
## 1. 종합 수임 판정 (심사 결과)
- 판정: [강력 추천 / 진행 가능 / 조건부 진행 / 수임 불가] 중 택 1
- 근거: 3줄 요약

## 2. 맞춤형 정책자금 매칭 전략
- 추천 자금 2~3개 (기관명, 자금명, 한도, 확률)

## 3. 컨설팅 세일즈 포인트
- 고객 설득을 위한 강점 및 약점 포인트

## 4. 사전 점검 및 리스크 헤징
- 심사 시 예상되는 문제점과 대응 논리
""".strip()

def generate_execution_prompt(data: Dict[str, Any]) -> str:
    s1 = data.get("stage1") or {}
    s2 = data.get("stage2") or {}
    s3 = data.get("stage3") or {}
    metrics = calculate_financial_metrics(s2)
    
    return f"""
당신은 정책자금 실행을 전담하는 수석 컨설턴트입니다.
'자금을 실제로 받아내기 위한' 구체적이고 실현 가능한 전략을 수립하십시오.

# [기업 프로파일]
- 기업명: {s2.get('business_name', '-')} ({s1.get('industry', '-')})
- 업력/규모: {s2.get('startup_date', '-')} 설립 / 매출 {s2.get('revenue_y1', '0')}만원
- 재무상태: 부채비율 {metrics['debt_ratio']}, 성장률 {metrics['growth_rate']}
- 기술/인증: {s2.get('ip_status', '-')} / {s2.get('official_certs', '-')}

# [심층 분석 데이터 (3차)]
- 담보/보증 여력: {s3.get('collateral_profile', '-')}
- 신용/세무 이슈: {s3.get('tax_credit_summary', '-')}
- 기대출 현황: {s3.get('loan_summary', '-')}
- 준비 서류: {s3.get('docs_check', '-')}
- 가점/감점 요인: {s3.get('priority_exclusion', '-')}
- 핵심 리스크: {s3.get('risk_top3', '-')}
- 컨설턴트 메모: {s3.get('coach_notes', '-')}

# [전략 리포트 작성 가이드]
## 1. 승인 가능성 정밀 진단
- 승인 확률 (상/중/하) 및 종합 평가

## 2. 최적 자금 조달 로드맵
- 1순위 / 2순위 공략 자금 및 신청 적기

## 3. 핵심 보완 솔루션
- 승인율을 높이기 위한 즉각적인 실행 방안

## 4. 예상 질문 및 답변 (Q&A)
- 실사 예상 질문 2가지와 모범 답변

## 5. 실행 타임라인
- 주차별 실행 계획
""".strip()

# ==============================
# 6. API 호출 (메모 업데이트)
# ==============================
def fetch_integrated_data(receipt_no: str) -> Dict[str, Any]:
    try:
        payload = {
            "action": "get_integrated_view",
            "receipt_no": receipt_no,
            "api_token": API_TOKEN
        }
        res = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def save_policy_result(receipt_no: str, policy_name: str, approved_amount: str, result_memo: str) -> Dict[str, Any]:
    try:
        payload = {
            "action": "save_result",
            "api_token": API_TOKEN,
            "receipt_no": receipt_no,
            "policy_name": policy_name,
            "approved_amount": approved_amount,
            "result_memo": result_memo
        }
        res = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_consultant_note(receipt_no: str, new_note_content: str, current_notes: str) -> Dict[str, Any]:
    try:
        # 계약서 링크 저장을 위한 특수 태그 처리
        # 만약 새 내용이 URL이라면 기존 메모를 덮어쓰지 않고 태그로 추가
        if new_note_content.startswith("[CONTRACT_LINK]"):
            # 기존 메모에 이미 링크가 있다면 교체, 없으면 추가 (여기선 단순 추가 방식 사용)
            updated_note = f"{current_notes}\n{new_note_content}".strip()
        else:
            # 일반 메모 추가
            updated_note = f"{current_notes}\n{new_note_content}".strip()
            
        data = {
            "action": "save_consultation", 
            "api_token": API_TOKEN_3, 
            "receipt_no": receipt_no, 
            "consultant_note": updated_note,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        target_url = THIRD_GAS_URL if THIRD_GAS_URL else INTEGRATED_GAS_URL
        res = requests.post(target_url, json=data, timeout=20)
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================
# 7. UI 메인
# ==============================
def main():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    #MainMenu, footer, header { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }

    .unified-header {
        background: linear-gradient(135deg, #002855 0%, #1e40af 100%);
        padding: 20px 30px;
        border-radius: 0 0 15px 15px;
        margin: -4rem -4rem 24px -4rem;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .header-left { display: flex; align-items: center; gap: 15px; }
    .header-left img { height: 40px; object-fit: contain; }
    .header-left h1 { margin: 0; font-size: 22px; font-weight: 700; color: white; }
    
    .stage-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
    }
    .badge-contract { background: #FEF3C7; color: #92400E; }
    .badge-execution { background: #D1FAE5; color: #065F46; }
    
    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
    .metric-value { font-size: 24px; font-weight: 700; color: #111827; }
    .metric-green { color: #059669; }
    .metric-red { color: #DC2626; }
    .metric-orange { color: #D97706; }
    
    .download-btn {
        display: block;
        text-align: center;
        background: #002855;
        color: white !important;
        padding: 14px 24px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: 600;
        margin-top: 20px;
        transition: all 0.2s;
    }
    .download-btn:hover { background: #1e40af; }
    
    .chat-box {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 15px;
        max-height: 300px;
        overflow-y: auto;
        font-size: 14px;
        white-space: pre-wrap;
    }
    </style>
    """, unsafe_allow_html=True)

    # 헤더
    st.markdown(f"""
    <div class="unified-header">
        <div class="header-left">
            <img src="{LOGO_URL}" alt="Logo">
            <h1>통합 고객 관리 대시보드</h1>
        </div>
        <div style="font-size:12px; opacity:0.8;">v2.1 | Admin</div>
    </div>
    """, unsafe_allow_html=True)

    if not GEMINI_API_KEY:
        st.error("⚠️ GEMINI_API_KEY 환경변수가 설정되지 않았습니다. Render 설정을 확인하세요.")
        return

    # ==========================================================
    # 🚨 AI 연결
    # ==========================================================
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        sorted_models = get_sorted_models(model_list)
        
        if sorted_models:
            best_model = sorted_models[0]
            display_model = best_model.replace('models/', '')
            score = calculate_model_score(best_model)
            st.toast(f"✅ AI 연결 성공: {display_model}")
            
            with st.expander("🏆 AI 모델 성능 순위", expanded=False):
                st.write(f"**선택된 모델:** `{best_model}`")
                rank_data = []
                for idx, m in enumerate(sorted_models[:10]): 
                    rank_data.append({"순위": f"{idx+1}위", "모델명": m.replace('models/', ''), "점수": calculate_model_score(m)})
                st.table(rank_data)
        else:
            st.warning("⚠️ AI 연결 경고")
    except Exception as e:
        st.error(f"❌ 치명적 오류: {e}")
        return 

    # 검색바
    col1, col2 = st.columns([4, 1])
    with col1:
        receipt_no = st.text_input("접수번호 입력", placeholder="예: YP202511271234", label_visibility="collapsed")
    with col2:
        search_btn = st.button("🔍 고객 조회", type="primary", use_container_width=True)

    if search_btn and receipt_no:
        with st.spinner("데이터 조회 중..."):
            result = fetch_integrated_data(receipt_no.strip())
        
        if result.get("status") == "success":
            data = result.get("data", {})
            s1 = data.get("stage1") or {}
            s2 = data.get("stage2") or {}
            s3 = data.get("stage3") or {}
            metrics = calculate_financial_metrics(s2)
            
            has_s3 = bool(s3 and s3.get('coach_notes'))
            current_notes = s3.get('coach_notes', '') if s3 else ""
            is_contracted_saved = "[계약완료]" in current_notes
            
            # [NEW] 계약서 링크 파싱
            contract_link = ""
            link_match = re.search(r'\[CONTRACT_LINK\] (https?://[^\s]+)', current_notes)
            if link_match:
                contract_link = link_match.group(1)

            st.markdown("---")
            if has_s3:
                st.markdown('<span class="stage-badge badge-execution">🚀 최종 실행 단계 (3차 완료)</span>', unsafe_allow_html=True)
            elif is_contracted_saved:
                st.markdown('<span class="stage-badge badge-contract" style="background:#D1FAE5; color:#065F46;">✅ 계약 완료 (3차 진행 중)</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="stage-badge badge-contract">📝 계약 검토 단계 (2차 완료)</span>', unsafe_allow_html=True)
            
            st.markdown(f"### 📊 {s1.get('name', '고객')} 님 기업 진단")
            
            # [직원용 & CEO용 버튼 섹션]
            col_staff, col_ceo = st.columns(2)
            
            with col_staff:
                with st.expander("⚡ [직원용] 상담/설문 대리 작성", expanded=True):
                    s1_link = f"{SURVEY1_URL}/?r={receipt_no}&name={s1.get('name', '')}&phone={s1.get('phone', '')}"
                    st.link_button(f"📝 1차 상담 작성 (ID: {receipt_no})", s1_link, use_container_width=True)
                    s2_link = f"{SURVEY2_URL}/?r={receipt_no}"
                    st.link_button(f"📊 2차 심화진단 작성 (ID: {receipt_no})", s2_link, use_container_width=True)

            with col_ceo:
                with st.expander("👑 [대표용] 계약 관리 및 3차 상담", expanded=True):
                    # 1. 계약서 버튼 표시 (링크가 있을 때만)
                    if contract_link:
                        st.link_button("📄 전자계약서 보기 (이폼싸인)", contract_link, type="primary", use_container_width=True)
                    
                    # 2. 계약서 링크 등록 입력창
                    with st.popover("➕ 계약서 링크 등록/수정"):
                        new_link = st.text_input("이폼싸인 완료 문서 URL", placeholder="https://eformsign.com/...")
                        if st.button("링크 저장"):
                            if new_link:
                                # 태그 달아서 저장
                                note_tag = f"[CONTRACT_LINK] {new_link}"
                                res = update_consultant_note(receipt_no, note_tag, current_notes)
                                if res.get('status') == 'success' or res.get('ok') == True:
                                    st.success("계약서가 연동되었습니다.")
                                    st.rerun()
                                else:
                                    st.error("저장 실패")

                    st.divider()
                    
                    # 3. 계약 상태 체크 및 3차 상담
                    contract_checked = st.checkbox("✅ 계약 완료 확인 (3차 링크 생성)", value=is_contracted_saved)
                    if contract_checked:
                        s3_link = f"{SURVEY3_URL}/?r={receipt_no}&name={s1.get('name', '')}&phone={s1.get('phone', '')}"
                        st.link_button(f"🚀 3차 심층 상담 작성하기", s3_link, type="secondary", use_container_width=True)
                        
                        if not is_contracted_saved:
                            if st.button("💾 계약 상태 저장하기"):
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                                sys_note = f"[{timestamp} | SYSTEM] ✅ 계약 완료 상태로 변경되었습니다."
                                with st.spinner("상태 업데이트 중..."):
                                    res = update_consultant_note(receipt_no, sys_note, current_notes)
                                    if res.get('status') == 'success' or res.get('ok') == True:
                                        st.success("상태가 저장되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("저장 실패")
                    else:
                        st.info("계약이 완료되면 체크해주세요.")

            st.markdown("---")
            # ... (나머지 지표 카드 및 상세 데이터 코드는 기존과 동일) ...
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">업종</div><div class="metric-value" style="font-size:16px;">{s1.get('industry', '-')}</div></div>""", unsafe_allow_html=True)
            with col_m2:
                growth_class = "metric-green" if metrics['growth_status'] == 'green' else ("metric-red" if metrics['growth_status'] == 'red' else "")
                st.markdown(f"""<div class="metric-card"><div class="metric-label">매출 성장률</div><div class="metric-value {growth_class}">{metrics['growth_rate']}</div></div>""", unsafe_allow_html=True)
            with col_m3:
                debt_class = "metric-green" if metrics['debt_status'] == 'green' else ("metric-red" if metrics['debt_status'] == 'red' else "metric-orange")
                st.markdown(f"""<div class="metric-card"><div class="metric-label">부채비율</div><div class="metric-value {debt_class}">{metrics['debt_ratio']}</div></div>""", unsafe_allow_html=True)
            with col_m4:
                risk_status = "⚠️ 주의" if s1.get('tax_status') != "체납 없음" or s1.get('credit_status') != "연체 없음" else "✅ 양호"
                risk_class = "metric-red" if "주의" in risk_status else "metric-green"
                st.markdown(f"""<div class="metric-card"><div class="metric-label">리스크</div><div class="metric-value {risk_class}" style="font-size:18px;">{risk_status}</div></div>""", unsafe_allow_html=True)

            st.markdown("---")
            with st.expander("📂 상세 데이터 보기 (랜딩/1차/2차/3차)", expanded=False):
                tab1, tab2, tab3 = st.tabs(["1차 (기본/랜딩)", "2차 (심화/재무)", "3차 (심층/전문가)"])
                with tab1:
                    if s1:
                        c1, c2 = st.columns(2)
                        c1.write(f"**고객명:** {s1.get('name', '-')}")
                        c1.write(f"**연락처:** {s1.get('phone', '-')}")
                        c2.write(f"**업종:** {s1.get('industry', '-')}")
                        c2.write(f"**필요자금:** {s1.get('funding_amount', '-')}")
                    else: st.info("데이터 없음")
                with tab2:
                    if s2:
                        c1, c2 = st.columns(2)
                        c1.write(f"**사업자명:** {s2.get('business_name', '-')}")
                        c1.write(f"**매출:** {s2.get('revenue_y1', '-')}")
                        c2.write(f"**자본금:** {s2.get('capital_amount', '-')}")
                        c2.write(f"**부채:** {s2.get('debt_amount', '-')}")
                    else: st.info("데이터 없음")
                with tab3:
                    if s3:
                        st.write(f"**담보/보증:** {s3.get('collateral_profile', '-')}")
                        st.write(f"**메모:** {s3.get('coach_notes', '-')}")
                    else: st.info("데이터 없음")

            st.markdown("---")
            client_name_title = s1.get('name', '고객')
            with st.expander(f"📢 [{client_name_title}] 님 관련 내부 소통 및 히스토리", expanded=True):
                # 링크 태그는 화면에 지저분하게 보일 수 있으니 제거하고 보여주기 (옵션)
                clean_notes = current_notes.replace("[CONTRACT_LINK]", "📄 계약서 링크:")
                if not clean_notes: clean_notes = "(메모 없음)"
                st.markdown(f"""<div class="chat-box">{clean_notes}</div>""", unsafe_allow_html=True)
                
                st.write("")
                col_w, col_i = st.columns([1, 4])
                with col_w: writer = st.selectbox("작성자", ["직원", "대표"], key="nw")
                with col_i: new_note = st.text_input("내용 입력", key="ni")
                
                if st.button("💬 메모 등록"):
                    if new_note:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                        fmt_note = f"[{ts} | {writer}] {new_note}"
                        with st.spinner("저장 중..."):
                            res = update_consultant_note(receipt_no, fmt_note, s3.get('coach_notes', ''))
                            if res.get('status') == 'success' or res.get('ok'):
                                st.success("등록됨")
                                st.rerun()
                            else: st.error("실패")

            # AI 분석 및 다운로드 (기존 코드 유지)
            st.markdown("---")
            st.subheader("🤖 AI 최종 실행 전략")
            ai_output = analyze_with_gemini(GEMINI_API_KEY, data)
            st.markdown(ai_output)
            
            if ai_output and not ai_output.startswith("⚠️"):
                mode = "execution" if has_s3 else "contract"
                full_text = generate_full_report(data, ai_output, mode)
                btn_label = "📥 최종 리포트 다운로드"
                filename = f"유아플랜_{receipt_no}.txt"
                b64 = base64.b64encode(full_text.encode()).decode()
                st.markdown(f'<a href="data:text/plain;base64,{b64}" download="{filename}" class="download-btn">{btn_label}</a>', unsafe_allow_html=True)

            # 결과 저장 폼 (기존 유지)
            # ... (코드 생략, 위와 동일) ...

        else:
            st.error(f"❌ 조회 실패: {result.get('message', '알 수 없는 오류')}")
    
    elif search_btn:
        st.warning("접수번호를 입력해주세요.")

if __name__ == "__main__":
    main()