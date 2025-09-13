import os
try:
    from dotenv import load_dotenv  # optional
    load_dotenv()
except Exception:
    pass
# GAS/Webapp URLs (env → fallback empty)
APPS_SCRIPT_URL_1 = os.getenv('FIRST_GAS_URL', '')
APPS_SCRIPT_URL_2 = os.getenv('SECOND_GAS_URL', '')
APPS_SCRIPT_URL_3 = os.getenv('THIRD_GAS_URL', '')
# 1차 토큰 검증 API (2차/3차가 사용)
TOKEN_API_URL     = os.getenv('FIRST_GAS_TOKEN_API_URL', '')
