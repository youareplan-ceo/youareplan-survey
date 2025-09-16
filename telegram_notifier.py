"""
유아플랜 텔레그램 알림 시스템
- 설문 제출 알림
- 상태 변경 알림
- 오류 알림
"""
import requests
from datetime import datetime
import json
from typing import Optional, Dict, Any

class TelegramNotifier:
    """텔레그램 알림 전송 클래스"""
    
    def __init__(self):
        # 텔레그램 봇 설정
        self.bot_token = "8475264602:AAFQLZN6XAzPDZofqvYRrvz5liWUFdD8RDM"
        self.chat_id = "7518089474"  # CEO 텔레그램 ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # 구글 시트 URL (대시보드용)
        self.sheet_urls = {
            "1차": "https://docs.google.com/spreadsheets/d/118zWXL_jyTTcpXU4ljSPQrON-y1MPAGiZOBOkOcJWTk",
            "2차": "https://docs.google.com/spreadsheets/d/10SqLY02gR1vUdkO12ss_WU8ALIEYMQMb2pqgfxt7LZo",
            "3차": "https://docs.google.com/spreadsheets/d/1UwfACtxDU7BQM_lwuOKtlosdV8xBiXZ-aaJBfhh9FNc"
        }
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """텔레그램 메시지 전송
        
        Args:
            text: 전송할 메시지
            parse_mode: 파싱 모드 (HTML, Markdown)
            
        Returns:
            성공 여부
        """
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                print(f"[텔레그램] 메시지 전송 성공")
                return True
            else:
                print(f"[텔레그램] 전송 실패: {result.get('description')}")
                return False
                
        except Exception as e:
            print(f"[텔레그램] 오류: {str(e)}")
            return False
    
    def notify_survey1_submission(self, data: Dict[str, Any]) -> bool:
        """1차 설문 제출 알림"""
        
        message = f"""
📋 <b>1차 설문 제출 알림</b>

👤 <b>고객 정보</b>
• 성함: {data.get('name', '미입력')}
• 연락처: {data.get('phone', '미입력')}
• 이메일: {data.get('email', '미입력')}

🏢 <b>사업 정보</b>
• 지역: {data.get('region', '미입력')}
• 업종: {data.get('industry', '미입력')}
• 사업형태: {data.get('business_type', '미입력')}
• 직원수: {data.get('employee_count', '미입력')}
• 매출: {data.get('revenue', '미입력')}
• 필요자금: {data.get('funding_amount', '미입력')}

⚠️ <b>자격 현황</b>
• 세금체납: {data.get('tax_status', '체납 없음')}
• 금융연체: {data.get('credit_status', '연체 없음')}
• 영업상태: {data.get('business_status', '정상 영업')}

🎫 접수번호: <code>{data.get('receipt_no', '')}</code>
⏰ 제출시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<a href="{self.sheet_urls['1차']}">📊 1차 시트 확인</a>
"""
        return self.send_message(message)
    
    def notify_survey2_submission(self, data: Dict[str, Any]) -> bool:
        """2차 설문 제출 알림"""
        
        # 부채비율 계산
        debt_ratio = "계산불가"
        try:
            capital = float(str(data.get('capital_amount', '0')).replace(',', ''))
            debt = float(str(data.get('debt_amount', '0')).replace(',', ''))
            if capital > 0:
                debt_ratio = f"{round((debt / capital) * 100)}%"
        except:
            pass
        
        message = f"""
📊 <b>2차 설문 제출 알림</b>

👤 <b>고객 정보</b>
• 성함: {data.get('name', '미입력')}
• 사업자명: {data.get('business_name', '미입력')}
• 사업자번호: {data.get('biz_reg_no', '미입력')}

💰 <b>재무 현황</b>
• 올해 매출: {data.get('revenue_y1', '0')}만원
• 작년 매출: {data.get('revenue_y2', '0')}만원
• 재작년 매출: {data.get('revenue_y3', '0')}만원
• 자본금: {data.get('capital_amount', '0')}만원
• 부채: {data.get('debt_amount', '0')}만원
• 부채비율: {debt_ratio}

💡 <b>기술/인증</b>
• IP보유: {data.get('ip_status', '해당 없음')}
• 공식인증: {data.get('official_certs', '해당 없음')}
• 연구소: {data.get('research_lab_status', '미보유')}

🎯 <b>자금 계획</b>
• 용도: {data.get('funding_purpose', '미입력')}
• 우대조건: {data.get('incentive_status', '해당 없음')}

🎫 접수번호: <code>{data.get('parent_receipt_no', '')}</code>
⏰ 제출시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<a href="{self.sheet_urls['2차']}">📊 2차 시트 확인</a>
"""
        return self.send_message(message)
    
    def notify_survey3_submission(self, data: Dict[str, Any], status: str = "draft") -> bool:
        """3차 설문 제출/수정 알림"""
        
        status_emoji = "📝" if status == "draft" else "✅"
        status_text = "임시저장" if status == "draft" else "최종완료"
        
        message = f"""
📑 <b>3차 설문 {status_text}</b> {status_emoji}

🎫 접수번호: <code>{data.get('receipt_no', '')}</code>

📊 <b>담보/보증</b>
{data.get('collateral_profile', '미입력')}

💼 <b>세무/신용</b>
{data.get('tax_credit_summary', '미입력')}

🏦 <b>대출 현황</b>
{data.get('loan_summary', '미입력')}

📋 <b>준비 서류</b>
{', '.join(data.get('docs_check', [])) if data.get('docs_check') else '미선택'}

⚠️ <b>리스크 Top3</b>
{data.get('risk_top3', '미입력')}

🗒 <b>코치 메모</b>
{data.get('coach_notes', '미입력')}

📈 진행률: {data.get('progress', 0)}%
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<a href="{self.sheet_urls['3차']}">📊 3차 시트 확인</a>
"""
        return self.send_message(message)
    
    def notify_error(self, error_type: str, details: str) -> bool:
        """오류 알림"""
        
        message = f"""
🚨 <b>시스템 오류 알림</b>

❌ 오류 유형: {error_type}
📝 상세 내용: {details}
⏰ 발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

즉시 확인이 필요합니다!
"""
        return self.send_message(message)
    
    def notify_daily_summary(self, stats: Dict[str, int]) -> bool:
        """일일 요약 리포트"""
        
        message = f"""
📊 <b>일일 업무 리포트</b>
📅 {datetime.now().strftime('%Y년 %m월 %d일')}

<b>📋 오늘의 실적</b>
• 1차 설문: {stats.get('survey1', 0)}건
• 2차 설문: {stats.get('survey2', 0)}건  
• 3차 설문: {stats.get('survey3', 0)}건
• 총 상담: {stats.get('total', 0)}건

<b>📈 진행 현황</b>
• 신규 접수: {stats.get('new', 0)}건
• 계약 진행: {stats.get('contract', 0)}건
• 보류: {stats.get('hold', 0)}건
• 중단: {stats.get('stop', 0)}건

<b>💰 예상 수익</b>
• 착수금: {stats.get('deposit', 0):,}원
• 성공보수: {stats.get('success_fee', 0):,}원

수고하셨습니다! 🎯
"""
        return self.send_message(message)
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        
        test_msg = """
✅ <b>텔레그램 연동 테스트</b>

유아플랜 알림 시스템이 정상적으로 연결되었습니다!

<b>활성화된 알림:</b>
• 1차 설문 제출 알림 ✅
• 2차 설문 제출 알림 ✅
• 3차 설문 제출/수정 알림 ✅
• 시스템 오류 알림 ✅
• 일일 요약 리포트 ✅

테스트 시간: {time}
""".format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return self.send_message(test_msg)

# 테스트 코드
if __name__ == "__main__":
    notifier = TelegramNotifier()
    
    print("텔레그램 연결 테스트 시작...")
    if notifier.test_connection():
        print("✅ 연결 테스트 성공!")
    else:
        print("❌ 연결 테스트 실패!")
    
    # 샘플 데이터로 각 알림 테스트
    sample_data = {
        "name": "테스트",
        "phone": "010-1234-5678",
        "receipt_no": "YP20240101001",
        "parent_receipt_no": "YP20240101001"
    }
    
    # 각 알림 타입 테스트 (실제로는 주석 처리)
    # notifier.notify_survey1_submission(sample_data)
    # notifier.notify_survey2_submission(sample_data)
    # notifier.notify_survey3_submission(sample_data)
