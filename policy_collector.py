"""
유아플랜 정책자금 자동 수집 시스템 v3 (실사용 스KE치)
- 기존 테스트용 스크립트를 "테스트 모드"와 "수집 모드"로 분리
- 수집 모드: 기업마당(Bizinfo) / K-Startup 공고 메타데이터 수집 → 정규화 → SQLite upsert 저장
- 향후 첨부 파싱/알림 모듈을 붙일 수 있도록 훅 제공

필요 패키지: requests, python-dotenv, beautifulsoup4
데이터베이스: 기본 SQLite (./policy.db) — 추후 PostgreSQL로 교체 가능
"""

from __future__ import annotations
import os
import json
import time
import argparse
import hashlib
import sqlite3
from datetime import datetime
from typing import Dict, List, Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()  # .env 파일 로드

# === ENV ===
BIZINFO_API_KEY = os.getenv('BIZINFO_API_KEY')
KSTARTUP_API_KEY = os.getenv('KSTARTUP_API_KEY')  # 데이터포털/공식키 사용
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DB_PATH = os.getenv('POLICY_DB_PATH', 'policy.db')

# === 공통 스키마 ===
NORMALIZED_FIELDS = [
    'program_id', 'title', 'summary', 'field', 'target', 'region', 'org',
    'apply_from', 'apply_to', 'url', 'contact', 'benefit', 'reqs',
    'source', 'attachments'
]

# === DB 유틸 ===
DDL = """
CREATE TABLE IF NOT EXISTS programs (
  program_id TEXT PRIMARY KEY,        -- hash(title+org+apply_to)
  title TEXT,
  summary TEXT,
  field TEXT,
  target TEXT,
  region TEXT,
  org TEXT,
  apply_from TEXT,
  apply_to TEXT,
  url TEXT,
  contact TEXT,
  benefit TEXT,
  reqs TEXT,
  source TEXT,
  attachments TEXT,                   -- JSON 배열 문자열
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_programs_apply_to ON programs(apply_to);
CREATE INDEX IF NOT EXISTS idx_programs_org ON programs(org);
"""

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    conn.executescript(DDL)
    return conn


def upsert_program(conn: sqlite3.Connection, item: Dict[str, Any]) -> None:
    # attachments를 JSON 문자열로 보관
    attachments_json = json.dumps(item.get('attachments', []), ensure_ascii=False)
    item = {**item, 'attachments': attachments_json}
    cols = ','.join(NORMALIZED_FIELDS)
    placeholders = ','.join(['?'] * len(NORMALIZED_FIELDS))
    values = [item.get(k) for k in NORMALIZED_FIELDS]
    sql = f"INSERT INTO programs ({cols}) VALUES ({placeholders})\n"
    sql += "ON CONFLICT(program_id) DO UPDATE SET\n"
    sql += ",".join([f"{k}=excluded.{k}" for k in NORMALIZED_FIELDS if k != 'program_id'])
    conn.execute(sql, values)
    # debug minimal
    # print(f"[UPSERT] {item.get('title')} | {item.get('org')}")


# === 해시/정규화 ===

def make_program_id(title: str, org: str, apply_to: str | None) -> str:
    base = f"{(title or '').strip()}|{(org or '').strip()}|{(apply_to or '').strip()}"
    return hashlib.sha256(base.encode('utf-8')).hexdigest()[:32]


def normalize_bizinfo(raw: Dict[str, Any]) -> Dict[str, Any]:
    # Bizinfo JSON 혹은 XML 파싱 결과를 공통 스키마로 맵핑
    title = raw.get('title') or raw.get('titl') or raw.get('PBLANC_TITLE_NM')
    org = raw.get('instNm') or raw.get('PBLANC_INST_NM') or raw.get('institution') or raw.get('org') or raw.get('author')
    url = raw.get('link') or raw.get('url') or raw.get('PBLANC_URL')
    apply_from = raw.get('startDate') or raw.get('RCEPT_BGNDE')
    apply_to = raw.get('endDate') or raw.get('RCEPT_ENDDE')
    item = {
        'program_id': make_program_id(title, org, apply_to),
        'title': title,
        'summary': raw.get('summary') or raw.get('cn') or raw.get('SUMMARY'),
        'field': raw.get('field') or raw.get('INDUTY_NM'),
        'target': raw.get('target') or raw.get('TRGET_NM'),
        'region': raw.get('region') or raw.get('RDNMADR') or raw.get('AREA_NM'),
        'org': org,
        'apply_from': apply_from,
        'apply_to': apply_to,
        'url': url,
        'contact': raw.get('contact') or raw.get('CHARGER_TELNO'),
        'benefit': raw.get('benefit') or raw.get('SUPLY_SCALE_NM'),
        'reqs': raw.get('reqs') or raw.get('REQ_CN'),
        'source': 'bizinfo',
        'attachments': raw.get('attachments') or []
    }
    return item


def normalize_kstartup(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = raw.get('PBLANC_TITLE_NM') or raw.get('title')
    org = raw.get('PBLANC_INST_NM') or raw.get('org')
    url = raw.get('PBLANC_URL') or raw.get('url')
    apply_from = raw.get('RCEPT_BGNDE') or raw.get('apply_from')
    apply_to = raw.get('RCEPT_ENDDE') or raw.get('apply_to')
    item = {
        'program_id': make_program_id(title, org, apply_to),
        'title': title,
        'summary': raw.get('PBLANC_SUMRY') or raw.get('summary'),
        'field': raw.get('INDUTY_NM') or raw.get('field'),
        'target': raw.get('TRGET_NM') or raw.get('target'),
        'region': raw.get('AREA_NM') or raw.get('region'),
        'org': org,
        'apply_from': apply_from,
        'apply_to': apply_to,
        'url': url,
        'contact': raw.get('CHARGER_TELNO') or raw.get('contact'),
        'benefit': raw.get('SUPLY_SCALE_NM') or raw.get('benefit'),
        'reqs': raw.get('REQ_CN') or raw.get('reqs'),
        'source': 'kstartup',
        'attachments': raw.get('attachments') or []
    }
    return item


# === 수집기 ===

def fetch_bizinfo(page: int = 1, rows: int = 50) -> List[Dict[str, Any]]:
    """기업마당 지원사업 API 수집 (JSON/XML 모두 대응)."""
    url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
    params = {
        'serviceKey': BIZINFO_API_KEY,  # 일부 환경에선 필수
        'type': 'json',
        'pageNo': page,
        'numOfRows': rows,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    ct = (r.headers.get('content-type') or '').lower()
    if 'json' in ct:
        data = r.json()
        items = data.get('items') or data.get('response') or data
        if isinstance(items, dict) and 'item' in items:
            items = items['item']
        if not isinstance(items, list):
            items = [items]
        return items
    else:
        # XML(RSS) 처리: 간단 파서
        soup = BeautifulSoup(r.text, 'xml')
        items = []
        for it in soup.find_all('item'):
            items.append({
                'title': it.findtext('title'),
                'link': it.findtext('link'),
                'summary': it.findtext('description'),
                'org': it.findtext('author') or it.findtext('dc:creator') or '',
                'author': it.findtext('author') or '',
                'RCEPT_BGNDE': '',
                'RCEPT_ENDDE': ''
            })
        return items


def fetch_kstartup(page: int = 1, rows: int = 50) -> List[Dict[str, Any]]:
    """K-Startup 공고 OpenAPI (예시 스펙, 실제 키/엔드포인트는 데이터포털 신청 후 적용).
    """
    if not KSTARTUP_API_KEY:
        return []
    # 아래 URL은 예시이며, 실제 서비스키·파라미터는 발급 문서에 맞춰 조정
    url = "https://apis.data.go.kr/kised/kstartup/announcement"
    params = {
        'serviceKey': KSTARTUP_API_KEY,
        'pageNo': page,
        'numOfRows': rows,
        'type': 'json',
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        return []
    data = r.json()
    items = data.get('items') or data.get('response') or data
    if isinstance(items, dict) and 'item' in items:
        items = items['item']
    if not isinstance(items, list):
        items = [items]
    return items


def collect_once() -> Dict[str, int]:
    conn = db_connect()
    new_cnt = upd_cnt = 0

    # 1) Bizinfo
    try:
        biz_items = fetch_bizinfo(page=1, rows=100)
        print(f"[DEBUG] fetched bizinfo items: {len(biz_items)}")
    except Exception as e:
        print(f"[WARN] Bizinfo fetch failed: {e}")
        biz_items = []

    for raw in biz_items:
        item = normalize_bizinfo(raw)
        try:
            upsert_program(conn, item)
            new_cnt += 1  # 간단히 카운트(정확한 신규/갱신 구분은 변경 로그 테이블에서 관리 가능)
        except Exception as e:
            print(f"[ERROR] upsert bizinfo: {e} -> {item.get('title')}")

    # 2) K-Startup
    try:
        ks_items = fetch_kstartup(page=1, rows=100)
        print(f"[DEBUG] fetched kstartup items: {len(ks_items)}")
    except Exception as e:
        print(f"[WARN] K-Startup fetch failed: {e}")
        ks_items = []

    for raw in ks_items:
        item = normalize_kstartup(raw)
        try:
            upsert_program(conn, item)
            upd_cnt += 1
        except Exception as e:
            print(f"[ERROR] upsert kstartup: {e} -> {item.get('title')}")

    conn.commit()
    conn.close()
    return {"bizinfo": len(biz_items), "kstartup": len(ks_items)}


# === 테스트 유틸(기존 기능 유지) ===

def check_api_keys():
    print("\n=== API 키 확인 ===")
    print(f"BIZINFO_API_KEY: {'✅' if BIZINFO_API_KEY else '❌'}")
    print(f"KSTARTUP_API_KEY: {'✅' if KSTARTUP_API_KEY else '❌'}")
    print(f"ANTHROPIC_API_KEY: {'✅' if ANTHROPIC_API_KEY else '❌'}")
    print(f"OPENAI_API_KEY: {'✅' if OPENAI_API_KEY else '❌'}")
    print(f"GEMINI_API_KEY: {'✅' if GEMINI_API_KEY else '❌'}")
    print(f"TELEGRAM 설정: {'✅' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else '❌'}")
    print("==================\n")


def test_bizinfo_api():
    print("📋 기업마당 API 테스트 중...")
    url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
    params = {'type': 'json', 'pageNo': 1, 'numOfRows': 5}
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"응답 코드: {r.status_code}")
        if r.status_code == 200:
            ct = r.headers.get('content-type', '')
            if 'xml' in ct:
                print("✅ RSS(XML) 접속 성공!\n", r.text[:500])
            else:
                data = r.json()
                print("✅ JSON 응답 샘플:\n", json.dumps(data, indent=2, ensure_ascii=False)[:500])
        else:
            print("❌ API 오류", r.text[:300])
    except Exception as e:
        print("❌ 연결 실패:", e)


def test_web_scraping():
    print("\n🌐 K-Startup 웹 스크래핑 테스트...")
    url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find('title')
        print("페이지 제목:", title.text if title else '제목 없음')
        lists = soup.find_all('div', class_='board-list')
        print("발견된 공고 컨테이너:", len(lists))
    except Exception as e:
        print("❌ 스크래핑 실패:", e)


# === 엔트리포인트 ===

def main():
    parser = argparse.ArgumentParser(description='유아플랜 정책자금 수집기')
    parser.add_argument('--mode', choices=['test', 'collect'], default='test')
    args = parser.parse_args()

    if args.mode == 'test':
        check_api_keys()
        test_bizinfo_api()
        test_web_scraping()
        print("\n✅ 테스트 완료")
        return
    elif args.mode == 'collect':
        print("[MODE] collect")
        check_api_keys()
        stats = collect_once()
        print(f"\n✅ 수집 완료: {stats}")
        return
    else:
        print(f"Unknown mode: {args.mode}")


if __name__ == '__main__':
    main()