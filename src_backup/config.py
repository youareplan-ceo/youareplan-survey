"""
유아플랜 설문 시스템 설정 모듈
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수 설정
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Google Apps Script URLs
FIRST_GAS_URL = os.getenv('FIRST_GAS_URL', '')
SECOND_GAS_URL = os.getenv('SECOND_GAS_URL', '')
THIRD_GAS_URL = os.getenv('THIRD_GAS_URL', '')
UNIFIED_API_URL = os.getenv('UNIFIED_API_URL', '')

# API 토큰
API_TOKEN = os.getenv('API_TOKEN', 'youareplan')
API_TOKEN_STAGE2 = os.getenv('API_TOKEN_STAGE2', 'youareplan_stage2')
API_TOKEN_STAGE3 = os.getenv('API_TOKEN_STAGE3', 'youareplan_stage3')

# 브랜딩 설정
YOUAREPLAN_LOGO_URL = os.getenv('YOUAREPLAN_LOGO_URL', 'https://raw.githubusercontent.com/youareplan-ceo/youaplan-site/main/logo.png')
BRAND_PRIMARY_COLOR = os.getenv('BRAND_PRIMARY_COLOR', '#002855')
BRAND_SECONDARY_COLOR = os.getenv('BRAND_SECONDARY_COLOR', '#005BAC')

# 성능 최적화 설정
API_CACHE_TTL = int(os.getenv('API_CACHE_TTL', '300'))
DUPLICATE_CACHE_TTL = int(os.getenv('DUPLICATE_CACHE_TTL', '1800'))
MAX_RETRY_ATTEMPTS = int(os.getenv('MAX_RETRY_ATTEMPTS', '3'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))

# 카카오톡 채널
KAKAO_CHANNEL_ID = os.getenv('KAKAO_CHANNEL_ID', '_LWxexmn')
KAKAO_CHANNEL_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}"
KAKAO_CHAT_URL = f"https://pf.kakao.com/{KAKAO_CHANNEL_ID}/chat"

# 도메인 설정
DOMAIN_SURVEY1 = os.getenv('DOMAIN_SURVEY1', 'survey1.youareplan.co.kr')
DOMAIN_SURVEY2 = os.getenv('DOMAIN_SURVEY2', 'survey2.youareplan.co.kr')
DOMAIN_SURVEY3 = os.getenv('DOMAIN_SURVEY3', 'survey3.youareplan.co.kr')
DOMAIN_DASHBOARD = os.getenv('DOMAIN_DASHBOARD', 'dashboard.youareplan.co.kr')

# SSL 설정
SSL_ENABLED = os.getenv('SSL_ENABLED', 'true').lower() == 'true'