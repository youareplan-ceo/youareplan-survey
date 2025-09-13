import os
from dataclasses import dataclass
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

@dataclass
class _Cfg:
    APPS_SCRIPT_URL_1: str = ''
    APPS_SCRIPT_URL_2: str = ''
    APPS_SCRIPT_URL_3: str = ''
    TOKEN_API_URL: str = ''


def get_config() -> _Cfg:
    return _Cfg(
        APPS_SCRIPT_URL_1=os.getenv('FIRST_GAS_URL',''),
        APPS_SCRIPT_URL_2=os.getenv('SECOND_GAS_URL',''),
        APPS_SCRIPT_URL_3=os.getenv('THIRD_GAS_URL',''),
        TOKEN_API_URL=os.getenv('FIRST_GAS_TOKEN_API_URL',''),
    )
