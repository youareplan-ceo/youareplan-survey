from __future__ import annotations
import json, time
from typing import Any, Dict, Optional, Tuple
import requests

# json_post(url, payload, headers=None, timeout=10, retries=1) -> (ok, status_code, data, err)
def json_post(url: str, payload: Dict[str, Any], headers: Optional[Dict[str,str]]=None, timeout: int=10, retries: int=1) -> Tuple[bool, Optional[int], Dict[str,Any], Optional[str]]:
    h = {'Content-Type':'application/json', **(headers or {})}
    last_err: Optional[str] = None
    for i in range(retries+1):
        try:
            r = requests.post(url, data=json.dumps(payload), headers=h, timeout=timeout)
            sc = r.status_code
            try:
                data = r.json()
            except Exception:
                data = {'text': r.text[:500]}
            if 200 <= sc <= 299:
                return True, sc, data, None
            # 408/429/5xx는 재시도 여지
            if sc in (408,429) or 500 <= sc <= 599:
                last_err = data.get('message') if isinstance(data,dict) else str(data)
                if i < retries:
                    time.sleep(0.6*(i+1))
                    continue
            return False, sc, data if isinstance(data,dict) else {}, last_err or f'HTTP {sc}'
        except requests.RequestException as e:
            last_err = str(e)
            if i < retries:
                time.sleep(0.6*(i+1))
                continue
            return False, None, {}, last_err
    return False, None, {}, last_err or 'unknown error'
