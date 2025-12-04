import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import os
import base64
import google.generativeai as genai
import re

# ==============================
# [설정] 설문지 앱 URL 
# ==============================
SURVEY1_URL = "https://youareplan-survey.onrender.com" 
SURVEY2_URL = "https://youareplan-survey2.onrender.com" 
SURVEY3_URL = "https://youareplan-survey3.onrender.com" 

# ==============================
# [보안] 접속 비밀번호 설정
# ==============================
ACCESS_PASSWORD = os.getenv("DASHBOARD_PW", "1234")
RESULT_PASSWORD = os.getenv("RESULT_PW", "1234")  # 대표 전용 (결과 저장) 

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
# [NEW] 로그인 보안 함수
# ==============================
def check_password():
    def password_entered():
        if st.session_state["password"] == ACCESS_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔑 관리자 접속 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 관리자 접속 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("😕 비밀번호가 틀렸습니다.")
        return False
    else:
        return True

# ==============================
# 2. 환경 설정 & 로고
# ==============================
BRAND_NAME = "유아플랜"
LOGO_URL = "https://raw.githubusercontent.com/youareplan-ceo/youareplan-survey/main/logo_white.png"
INTEGRATED_GAS_URL = os.getenv("FIRST_GAS_URL", "https://script.google.com/macros/s/AKfycbwb4rHgQepBGE4wwS-YIap8uY_4IUxGPLRhTQ960ITUA6KgfiWVZL91SOOMrdxpQ-WC/exec")
API_TOKEN = os.getenv("API_TOKEN", "youareplan")

# 3차 GAS URL (없으면 1차 GAS로 fallback)
THIRD_GAS_URL = os.getenv("THIRD_GAS_URL", "")
API_TOKEN_3 = os.getenv("API_TOKEN_3", "youareplan_stage3")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ==============================
# 3. 재무 지표 계산 함수
# ==============================
def calculate_financial_metrics(s2: Dict) -> Dict:
    metrics = {"debt_ratio": "-", "debt_status": "gray", "growth_rate": "-", "growth_status": "gray"}
    if not s2: return metrics
    try:
        capital = int(str(s2.get('capital_amount', '0')).replace(',', '').replace('만원', ''))
        debt = int(str(s2.get('debt_amount', '0')).replace(',', '').replace('만원', ''))
        if capital > 0:
            ratio = round((debt / capital) * 100)
            metrics['debt_ratio'] = f"{ratio}%"
            metrics['debt_status'] = "red" if ratio > 400 else ("orange" if ratio > 200 else "green")
    except: pass
    try:
        r1 = int(str(s2.get('revenue_y1', '0')).replace(',', '').replace('만원', ''))
        r2 = int(str(s2.get('revenue_y2', '0')).replace(',', '').replace('만원', ''))
        if r2 > 0:
            growth = round(((r1 - r2) / r2) * 100)
            metrics['growth_rate'] = f"{growth}%"
            metrics['growth_status'] = "green" if growth > 20 else ("red" if growth < -10 else "gray")
    except: pass
    return metrics

# ==============================
# 4. GAS API 호출 함수
# ==============================
def fetch_integrated_data(receipt_no: str) -> Dict:
    try:
        payload = {"action": "get_integrated_view", "receipt_no": receipt_no, "api_token": API_TOKEN}
        response = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        return response.json() if response.status_code == 200 else {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def issue_second_survey_token(receipt_no: str, hours: int = 24, issued_by: str = "dashboard") -> Dict:
    try:
        payload = {"action": "issue_token", "api_token": API_TOKEN, "receipt_no": receipt_no, "hours": hours, "issued_by": issued_by}
        response = requests.post(INTEGRATED_GAS_URL, json=payload, timeout=20)
        return response.json() if response.status_code == 200 else {"ok": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_past_approvals(industry: str = "", limit: int = 10) -> List[Dict]:
    try:
        # 3차 GAS로 호출 (정책자금결과 시트가 3차에 있음)
        target_url = THIRD_GAS_URL if THIRD_GAS_URL else INTEGRATED_GAS_URL
        payload = {"action": "get_past_approvals", "api_token": API_TOKEN_3, "industry": industry, "limit": limit}
        response = requests.post(target_url, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success": return result.get("data", [])
        return []
    except: return []

def save_policy_result(receipt_no: str, policy_name: str, approved_amount: str, result_memo: str, ai_recommended_policy: str = "", ai_recommended_amount: str = "") -> Dict:
    try:
        # 3차 GAS로 호출 (정책자금결과 시트가 3차에 있음)
        target_url = THIRD_GAS_URL if THIRD_GAS_URL else INTEGRATED_GAS_URL
        payload = {
            "action": "save_result", "api_token": API_TOKEN_3, "receipt_no": receipt_no,
            "policy_name": policy_name, "approved_amount": approved_amount, "result_memo": result_memo,
            "ai_recommended_policy": ai_recommended_policy, "ai_recommended_amount": ai_recommended_amount
        }
        response = requests.post(target_url, json=payload, timeout=20)
        return response.json() if response.status_code == 200 else {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_consultant_note(receipt_no: str, new_note: str, current_notes: str) -> Dict:
    try:
        updated_note = f"{current_notes}\n{new_note}".strip() if current_notes else new_note
        data = {"action": "save_consultation", "api_token": API_TOKEN_3, "receipt_no": receipt_no, "consultant_note": updated_note, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        # 3차 GAS URL이 없으면 1차 GAS로 fallback
        target_url = THIRD_GAS_URL if THIRD_GAS_URL else INTEGRATED_GAS_URL
        res = requests.post(target_url, json=data, timeout=20)
        return res.json() if res.status_code == 200 else {"status": "error", "message": f"HTTP {res.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================
# 5. Gemini AI 분석
# ==============================
def get_sorted_models(genai_module):
    try:
        models = list(genai_module.list_models())
        def calc_score(m):
            name = m.name.lower()
            score = 0
            if 'gemini-1.5-flash' in name: score += 100
            elif 'gemini-1.5-pro' in name: score += 90
            elif 'gemini-pro' in name: score += 80
            if '-latest' in name: score += 20
            if 'exp' in name: score -= 30
            return score
        content_models = [m for m in models if 'generateContent' in [method.name for method in m.supported_generation_methods]]
        return sorted(content_models, key=calc_score, reverse=True)
    except: return []

def analyze_with_gemini(api_key: str, data: Dict) -> tuple:
    if not api_key: return "⚠️ Gemini API 키가 설정되지 않았습니다.", "", ""
    try:
        genai.configure(api_key=api_key)
        sorted_models = get_sorted_models(genai)
        if not sorted_models: return "⚠️ 사용 가능한 Gemini 모델이 없습니다.", "", ""
        model = genai.GenerativeModel(sorted_models[0].name.replace('models/', ''))
        
        s1, s2, s3 = data.get('stage1') or {}, data.get('stage2') or {}, data.get('stage3') or {}
        has_s3 = bool(s3 and any(s3.values()))
        
        # 과거 승인 사례 조회 (AI 학습용)
        past_cases = get_past_approvals(s1.get('industry', ''), 5)
        past_text = ""
        if past_cases:
            past_text = "\n\n[과거 유사 업종 승인 사례]\n"
            for i, c in enumerate(past_cases, 1):
                match = "✓" if c.get('ai_match') == 'Y' else ("✗" if c.get('ai_match') == 'N' else "")
                past_text += f"{i}. {c.get('industry','-')} | {c.get('policy_name','-')} | {c.get('approved_amount','-')}만원 {match}\n"
        
        if has_s3:
            prompt = f"""당신은 한국 중소기업 정책자금 전문 컨설턴트입니다.
아래 고객 정보를 분석하여 **최종 실행 전략**을 제시해주세요.

[고객 기본 정보]
- 업종: {s1.get('industry', '-')}, 사업형태: {s1.get('business_type', '-')}, 직원수: {s1.get('employee_count', '-')}, 필요자금: {s1.get('funding_amount', '-')}

[재무 현황]
- 매출: {s2.get('revenue_y1', '-')}만원(올해), {s2.get('revenue_y2', '-')}만원(전년)
- 자본금: {s2.get('capital_amount', '-')}만원, 부채: {s2.get('debt_amount', '-')}만원

[심층 분석]
- 담보/보증: {s3.get('collateral_profile', '-')}, 리스크: {s3.get('risk_top3', '-')}
{past_text}

다음을 포함한 **최종 실행 전략**:
1. 승인 가능성 (상/중/하)
2. 추천 정책자금 3개
3. 예상 승인 한도 (만원)
4. 필요 서류, 5. 실행 로드맵

※ 마지막에 반드시:
[AI추천요약]
- 1순위 정책자금: (정책자금명)
- 예상 승인금액: (만원)"""
        else:
            prompt = f"""당신은 한국 중소기업 정책자금 전문 컨설턴트입니다.
아래 고객 정보를 분석하여 **계약 심사 의견**을 제시해주세요.

[고객 기본 정보]
- 업종: {s1.get('industry', '-')}, 사업형태: {s1.get('business_type', '-')}, 필요자금: {s1.get('funding_amount', '-')}
- 세금체납: {s1.get('tax_status', '-')}, 금융연체: {s1.get('credit_status', '-')}

[재무 현황]
- 매출: {s2.get('revenue_y1', '-')}만원, 자본금: {s2.get('capital_amount', '-')}만원, 부채: {s2.get('debt_amount', '-')}만원
{past_text}

다음을 포함한 **계약 심사 의견**:
1. 수임 판정 (적합/보류/부적합)
2. 예상 정책자금 2-3개
3. 예상 승인 금액 (만원)
4. 유의사항

※ 마지막에 반드시:
[AI추천요약]
- 1순위 정책자금: (정책자금명)
- 예상 승인금액: (만원)"""
        
        response = model.generate_content(prompt)
        result_text = response.text
        
        # AI 추천 정보 파싱
        ai_policy, ai_amount = "", ""
        m1 = re.search(r'1순위.*?정책자금[:\s]*([^\n]+)', result_text)
        if m1: ai_policy = re.sub(r'^[-:*\s]+', '', m1.group(1).strip())
        m2 = re.search(r'예상.*?승인.*?금액[:\s]*([0-9,]+)', result_text)
        if m2: ai_amount = m2.group(1).replace(',', '')
        
        return result_text, ai_policy, ai_amount
    except Exception as e:
        return f"⚠️ AI 분석 오류: {str(e)}", "", ""

# ==============================
# 6. 리포트 생성
# ==============================
def generate_full_report(data: Dict, ai_result: str, mode: str) -> str:
    s1, s2, s3 = data.get('stage1') or {}, data.get('stage2') or {}, data.get('stage3') or {}
    return f"""
================================================================================
                     유아플랜 정책자금 컨설팅 리포트
================================================================================
생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}
접수번호: {data.get('receipt_no', '-')}
분석유형: {'최종 실행 전략' if mode == 'execution' else '계약 심사'}

[1] 고객 정보
- 고객명: {s1.get('name', '-')}, 업종: {s1.get('industry', '-')}, 필요자금: {s1.get('funding_amount', '-')}

[2] 재무 현황
- 매출: {s2.get('revenue_y1', '-')}만원, 자본금: {s2.get('capital_amount', '-')}만원, 부채: {s2.get('debt_amount', '-')}만원

[3] AI 분석 결과
{ai_result}

================================================================================
"""

PROCESS_STATUS = ["1.신규접수", "2.상담예정", "3.서류준비중", "4.기관접수완료", "5.현장실사", "6.최종승인", "7.부결/보류"]

# ==============================
# 7. UI 메인
# ==============================
def main():
    if not check_password(): st.stop()

    # ✅ session_state 초기화
    if "search_result" not in st.session_state:
        st.session_state.search_result = None
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "issue_result" not in st.session_state:
        st.session_state.issue_result = None

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    #MainMenu, footer, header, [data-testid="stSidebar"] { display: none !important; }
    .unified-header { background: linear-gradient(135deg, #002855 0%, #1e40af 100%); padding: 20px 30px; border-radius: 0 0 15px 15px; margin: -4rem -4rem 24px -4rem; color: white; display: flex; justify-content: space-between; align-items: center; }
    .header-left { display: flex; align-items: center; gap: 15px; }
    .header-left img { height: 40px; }
    .header-left h1 { margin: 0; font-size: 22px; font-weight: 700; color: white; }
    .stage-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; }
    .metric-card { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; text-align: center; }
    .metric-label { font-size: 12px; color: #6b7280; }
    .metric-value { font-size: 24px; font-weight: 700; }
    .metric-green { color: #059669; } .metric-red { color: #DC2626; } .metric-orange { color: #D97706; }
    .download-btn { display: block; text-align: center; background: #002855; color: white !important; padding: 14px 24px; border-radius: 10px; text-decoration: none; font-weight: 600; margin-top: 20px; }
    .chat-box { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 15px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; font-size: 14px; }
    .link-box { background: #EFF6FF; border: 2px solid #3B82F6; border-radius: 10px; padding: 16px; margin: 10px 0; }
    .link-box code { background: white; padding: 8px 12px; border-radius: 6px; display: block; margin: 8px 0; word-break: break-all; }
    .ai-summary-box { background: #F0FDF4; border: 2px solid #22C55E; border-radius: 10px; padding: 16px; margin: 16px 0; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="unified-header">
        <div class="header-left"><img src="{LOGO_URL}" alt="로고"><h1>📊 유아플랜 통합 관리 대시보드</h1></div>
        <div style="font-size: 12px; opacity: 0.8;">v2025-12-04-session-fix</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])
    with col1: 
        search_query = st.text_input("접수번호 입력", value=st.session_state.search_query, placeholder="예: YP2025...", label_visibility="collapsed")
    with col2: 
        search_btn = st.button("🔍 조회", type="primary", use_container_width=True)

    # ✅ 조회 버튼 클릭 시 결과를 session_state에 저장
    if search_btn and search_query:
        st.session_state.search_query = search_query.strip()
        st.session_state.issue_result = None  # 이전 발급 결과 초기화
        with st.spinner("조회 중..."):
            result = fetch_integrated_data(search_query.strip())
        st.session_state.search_result = result

    # ✅ session_state에 저장된 결과가 있으면 표시
    if st.session_state.search_result:
        result = st.session_state.search_result
        
        if result.get("status") == "success":
            data = result.get("data", {})
            s1, s2, s3 = data.get("stage1") or {}, data.get("stage2") or {}, data.get("stage3") or {}
            metrics = calculate_financial_metrics(s2)
            real_receipt_no = data.get('receipt_no') or st.session_state.search_query
            current_notes = s3.get('coach_notes', '') if s3 else ""
            
            current_status = "1.신규접수"
            status_match = re.findall(r'\[STATUS_CHANGE\] .*? → (.*)', current_notes)
            if status_match: current_status = status_match[-1]
            is_contracted = "[계약완료]" in current_notes
            has_s3 = bool(s3 and any(s3.values()))
            
            st.markdown("---")
            col_st1, col_st2 = st.columns([3, 1])
            with col_st1:
                badge_style = "background:#D1FAE5; color:#065F46;" if is_contracted else "background:#FEF3C7; color:#92400E;"
                badge_text = "✅ 계약 완료" if is_contracted else "📝 검토 중"
                st.markdown(f'<span class="stage-badge" style="{badge_style}">{badge_text}</span> <span class="stage-badge" style="background:#F3F4F6; color:#374151;">📌 {current_status}</span>', unsafe_allow_html=True)
            with col_st2:
                with st.popover("🔄 상태 변경"):
                    new_status = st.selectbox("단계", PROCESS_STATUS, index=PROCESS_STATUS.index(current_status) if current_status in PROCESS_STATUS else 0)
                    if st.button("변경"):
                        if new_status != current_status:
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                            res = update_consultant_note(real_receipt_no, f"[{ts} | SYSTEM] [STATUS_CHANGE] {current_status} → {new_status}", current_notes)
                            if res: 
                                st.session_state.search_result = None  # 갱신을 위해 초기화
                                st.rerun()

            st.markdown(f"### 📊 {s1.get('name', '고객')} 님 (ID: {real_receipt_no})")
            
            # 직원/대표 섹션
            col_staff, col_ceo = st.columns(2)
            with col_staff:
                with st.expander("⚡ [직원용] 상담/설문", expanded=True):
                    st.link_button("📝 1차 상담", f"{SURVEY1_URL}/?r={real_receipt_no}", use_container_width=True)
                    st.markdown("---")
                    st.markdown("**📨 2차 링크 발급**")
                    col_h, col_i = st.columns([2, 1])
                    with col_h: 
                        hours = st.selectbox("유효시간", [6, 12, 24], index=2, format_func=lambda x: f"{x}시간", key=f"h_{real_receipt_no}")
                    with col_i: 
                        issue_btn = st.button("🔗 발급", type="primary", use_container_width=True, key=f"i_{real_receipt_no}")
                    
                    # ✅ 발급 버튼 클릭 처리
                    if issue_btn:
                        with st.spinner("발급 중..."):
                            r = issue_second_survey_token(real_receipt_no, hours, "dashboard")
                        st.session_state.issue_result = r
                    
                    # ✅ 발급 결과 표시 (session_state에서)
                    if st.session_state.issue_result:
                        r = st.session_state.issue_result
                        if r.get("ok"):
                            st.success("✅ 발급 완료!")
                            st.markdown(f'<div class="link-box"><strong>📋 고객용 링크</strong><code>{r.get("link","")}</code><small>만료: {r.get("expires_at","-")}</small></div>', unsafe_allow_html=True)
                            st.code(r.get("link", ""))
                        else: 
                            st.error(f"❌ 실패: {r.get('error')}")

            with col_ceo:
                with st.expander("👑 [대표용] 계약/3차", expanded=True):
                    link_match = re.search(r'\[CONTRACT_LINK\] (https?://[^\s]+)', current_notes)
                    if link_match: st.link_button("📄 전자계약서", link_match.group(1), type="primary", use_container_width=True)
                    with st.popover("➕ 계약서 등록"):
                        new_link = st.text_input("URL")
                        if st.button("저장") and new_link:
                            update_consultant_note(real_receipt_no, f"[CONTRACT_LINK] {new_link}", current_notes)
                            st.session_state.search_result = None
                            st.rerun()
                    if st.checkbox("✅ 계약 완료", value=is_contracted):
                        st.link_button("🚀 3차 상담", f"{SURVEY3_URL}/?r={real_receipt_no}", use_container_width=True)
                        if not is_contracted and st.button("저장"):
                            update_consultant_note(real_receipt_no, f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} | SYSTEM] ✅ [계약완료]", current_notes)
                            st.session_state.search_result = None
                            st.rerun()

            # 지표
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f'<div class="metric-card"><div class="metric-label">업종</div><div class="metric-value" style="font-size:16px">{s1.get("industry","-")}</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="metric-card"><div class="metric-label">성장률</div><div class="metric-value metric-{"green" if metrics["growth_status"]=="green" else ("red" if metrics["growth_status"]=="red" else "")}">{metrics["growth_rate"]}</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="metric-card"><div class="metric-label">부채비율</div><div class="metric-value metric-{metrics["debt_status"]}">{metrics["debt_ratio"]}</div></div>', unsafe_allow_html=True)
            with c4:
                risk = "⚠️ 주의" if s1.get('tax_status') != "체납 없음" or s1.get('credit_status') != "연체 없음" else "✅ 양호"
                st.markdown(f'<div class="metric-card"><div class="metric-label">리스크</div><div class="metric-value metric-{"red" if "주의" in risk else "green"}" style="font-size:18px">{risk}</div></div>', unsafe_allow_html=True)

            # 상세 데이터
            with st.expander("📂 상세 데이터", expanded=False):
                t1, t2, t3 = st.tabs(["1차", "2차", "3차"])
                with t1:
                    if s1: st.write(f"**고객명:** {s1.get('name')}, **업종:** {s1.get('industry')}, **필요자금:** {s1.get('funding_amount')}")
                    else: st.info("없음")
                with t2:
                    if s2: st.write(f"**사업자명:** {s2.get('business_name')}, **매출:** {s2.get('revenue_y1')}만원")
                    else: st.info("없음")
                with t3:
                    if s3: st.write(f"**담보:** {s3.get('collateral_profile')}")
                    else: st.info("없음")

            # 소통 로그
            st.markdown("---")
            with st.expander(f"📢 소통 로그", expanded=True):
                display = current_notes.replace("[CONTRACT_LINK]", "📄").replace("[STATUS_CHANGE]", "🔄") or "(없음)"
                st.markdown(f'<div class="chat-box">{display}</div>', unsafe_allow_html=True)
                cw, ci = st.columns([1, 4])
                with cw: w = st.selectbox("작성자", ["직원", "대표"], key="w")
                with ci: n = st.text_input("내용", key="n")
                if st.button("등록") and n:
                    update_consultant_note(real_receipt_no, f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} | {w}] {n}", current_notes)
                    st.session_state.search_result = None
                    st.rerun()

            # AI 분석
            st.markdown("---")
            st.subheader("🤖 AI 분석")
            ai_output, ai_policy, ai_amount = analyze_with_gemini(GEMINI_API_KEY, data)
            st.markdown(ai_output)
            
            if ai_policy or ai_amount:
                st.markdown(f'<div class="ai-summary-box"><strong>🎯 AI 추천</strong><br>- 1순위: <strong>{ai_policy or "-"}</strong><br>- 예상금액: <strong>{ai_amount or "-"}만원</strong></div>', unsafe_allow_html=True)
                st.session_state['ai_policy'] = ai_policy
                st.session_state['ai_amount'] = ai_amount
            
            if ai_output and not ai_output.startswith("⚠️"):
                mode = "execution" if has_s3 else "contract"
                report = generate_full_report(data, ai_output, mode)
                b64 = base64.b64encode(report.encode()).decode()
                st.markdown(f'<a href="data:text/plain;base64,{b64}" download="유아플랜_{real_receipt_no}.txt" class="download-btn">📥 리포트 다운로드</a>', unsafe_allow_html=True)

            # 결과 저장 (대표 전용)
            st.markdown("---")
            st.subheader("💰 정책자금 결과 저장 (대표 전용)")
            st.caption("실제 승인 결과를 저장하면 AI 정확도가 향상됩니다.")
            
            # 대표 비번 검증
            if "result_unlocked" not in st.session_state:
                st.session_state.result_unlocked = False
            
            if not st.session_state.result_unlocked:
                col_pw1, col_pw2 = st.columns([3, 1])
                with col_pw1:
                    result_pw_input = st.text_input("🔐 대표 비밀번호", type="password", key="result_pw_input")
                with col_pw2:
                    if st.button("확인", key="result_pw_btn"):
                        if result_pw_input == RESULT_PASSWORD:
                            st.session_state.result_unlocked = True
                            st.rerun()
                        else:
                            st.error("비밀번호가 틀렸습니다.")
            else:
                with st.form("result_form"):
                    cr1, cr2 = st.columns(2)
                    with cr1: policy = st.text_input("승인된 정책자금명", placeholder="예: 벤처기업정책자금")
                    with cr2: amount = st.text_input("승인 금액(만원)", placeholder="예: 50000")
                    memo = st.text_area("메모", placeholder="특이사항")
                    st.caption(f"📌 AI 추천: {st.session_state.get('ai_policy', '-')} / {st.session_state.get('ai_amount', '-')}만원")
                    
                    if st.form_submit_button("💾 저장", type="primary"):
                        if policy and amount:
                            with st.spinner("저장 중..."):
                                r = save_policy_result(real_receipt_no, policy, amount, memo, st.session_state.get('ai_policy', ''), st.session_state.get('ai_amount', ''))
                            if r.get('status') == 'success':
                                match = "✅ AI 일치!" if r.get('ai_match') == 'Y' else ("❌ AI 불일치" if r.get('ai_match') == 'N' else "")
                                st.success(f"저장 완료! {match}")
                            else: st.error(f"실패: {r.get('message')}")
                        else: st.warning("정책자금명과 금액을 입력하세요.")
        else:
            st.error(f"❌ 조회 실패: {result.get('message')}")

if __name__ == "__main__":
    main()