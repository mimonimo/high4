#!/usr/bin/env python3
"""
하이원포인트 지역 가맹점 정보 조회 API (getStoreInfo) 점검 · 수집 스크립트

  End Point : https://apis.data.go.kr/B552525/pbdata/getStoreInfo
  파라미터   : serviceKey, pageNo, numOfRows
  일일 트래픽: 5,000회  → 수집은 한 번만 하고 parquet 으로 캐싱할 것

사용법 (macOS / Kali 공통)
  $ python3 -m venv .venv && source .venv/bin/activate
  $ pip install requests pandas pyarrow
  $ export DATA_GO_KR_KEY='발급받은_일반인증키'
  $ python3 fetch_storeinfo.py --probe      # 구조 확인 (2회 호출)
  $ python3 fetch_storeinfo.py --collect    # 전량 수집 → merchants.csv/parquet

메모
  * 이 API 의 인증키는 특수문자가 없는 16진수라 인코딩/디코딩 키가 동일하다.
    (일반적인 공공데이터포털 키의 '+' → '%2B' 이중 인코딩 함정이 여기선 발생하지 않는다)
  * 요청변수에 type/returnType 이 없어 XML 응답일 수 있으므로 JSON·XML 모두 파싱한다.
"""

import argparse
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

try:
    import pandas as pd
except ImportError:
    print("[!] pip install pandas pyarrow")
    sys.exit(1)

BASE_URL = os.getenv("HIGH1_API_URL", "https://apis.data.go.kr/B552525/pbdata/getStoreInfo")
SERVICE_KEY = os.getenv("DATA_GO_KR_KEY", "")

TIMEOUT = 15
PER_PAGE = 100          # 상한이 낮으면 서버가 알아서 잘라준다
DAILY_LIMIT = 5000


def fetch(page: int, per_page: int = PER_PAGE) -> tuple[list[dict], int | None, str]:
    """1페이지 호출 → (행 리스트, 전체건수, 원문)"""
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": page,
        "numOfRows": per_page,
        "type": "json",         # 미지원이면 서버가 무시하고 XML 을 준다
    }
    r = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    text = r.text.strip()

    # ── JSON 시도
    if text.startswith("{") or text.startswith("["):
        payload = r.json()
        return _rows_from_json(payload), _total_from_json(payload), text

    # ── XML 폴백
    if text.startswith("<"):
        rows, total = _rows_from_xml(text)
        return rows, total, text

    raise RuntimeError(f"알 수 없는 응답 형식:\n{text[:500]}")


def _rows_from_json(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload.get("data"), list):
        return payload["data"]

    def walk(node: Any) -> list[dict] | None:
        if isinstance(node, list) and node and isinstance(node[0], dict):
            return node
        if isinstance(node, dict):
            for v in node.values():
                found = walk(v)
                if found:
                    return found
        return None

    return walk(payload) or []


def _total_from_json(payload: Any) -> int | None:
    def walk(node: Any) -> int | None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in ("totalcount", "matchcount", "total") and str(v).isdigit():
                    return int(v)
                found = walk(v)
                if found is not None:
                    return found
        return None
    return walk(payload) if isinstance(payload, dict) else None


def _rows_from_xml(text: str) -> tuple[list[dict], int | None]:
    root = ET.fromstring(text)

    # 에러 응답이면 즉시 알려준다
    for tag in ("returnAuthMsg", "errMsg", "resultMsg"):
        node = root.iter(tag)
        for n in node:
            if n.text and "정상" not in n.text and "NORMAL" not in n.text.upper():
                raise RuntimeError(f"API 오류 [{tag}] {n.text}\n원문: {text[:400]}")

    items = [
        {child.tag: (child.text or "").strip() for child in item}
        for item in root.iter("item")
    ]
    total = None
    for t in root.iter("totalCount"):
        if t.text and t.text.strip().isdigit():
            total = int(t.text.strip())
    return items, total


def probe() -> None:
    print(f"[*] {BASE_URL}")
    rows, total, raw = fetch(page=1, per_page=10)

    print("\n[1] 원문 앞부분")
    print(raw[:900])

    if not rows:
        print("\n[!] 데이터 행을 찾지 못했습니다. 위 원문을 확인하세요.")
        return

    print(f"\n[2] 전체 건수(totalCount): {total}")
    print(f"\n[3] 필드 {len(rows[0])}개")
    for k, v in rows[0].items():
        print(f"    - {k:<24} 예시: {str(v)[:45]}")

    print("\n[4] 샘플 3건")
    print(pd.DataFrame(rows).head(3).to_string())

    print("\n[5] 확정해야 할 것")
    print("    · 금액 관련 필드 = 누적 거래액인가, 사용가능 잔여한도인가?")
    print("    · 업종 값이 사용현황 CSV 의 18개 업종명과 일치하는가?")
    print("    · 주소에 읍면동(사북읍/고한읍)까지 들어있는가?")


def collect() -> None:
    all_rows, page = [], 1
    while True:
        rows, total, _ = fetch(page)
        if not rows:
            break
        all_rows.extend(rows)
        print(f"    page {page:>3} … 누적 {len(all_rows):,}건" + (f" / 전체 {total:,}" if total else ""))

        if total and len(all_rows) >= total:
            break
        if len(rows) < PER_PAGE:
            break
        page += 1
        if page > DAILY_LIMIT // 10:
            print("[!] 안전 상한 도달. 중단합니다.")
            break
        time.sleep(0.2)

    if not all_rows:
        print("[!] 수집 결과 없음")
        return

    df = pd.DataFrame(all_rows)
    df.to_csv("merchants.csv", index=False, encoding="utf-8-sig")
    try:
        df.to_parquet("merchants.parquet", index=False)
    except Exception as e:
        print(f"[!] parquet 저장 실패(무시 가능): {e}")

    print(f"\n[+] {len(df):,}건 저장 → merchants.csv / merchants.parquet")
    print(f"[+] 컬럼: {list(df.columns)}")

    addr = next((c for c in df.columns if "주소" in c or "addr" in c.lower() or "adres" in c.lower()), None)
    biz = next((c for c in df.columns if "업종" in c or "induty" in c.lower() or "bzcnd" in c.lower()), None)

    if addr:
        print(f"\n[지역별 가맹점 수] ({addr})")
        for region in ["고한", "사북", "정선", "태백", "영월", "삼척"]:
            n = int(df[addr].astype(str).str.contains(region).sum())
            print(f"    {region:<4} {n:>5}곳")
    if biz:
        print(f"\n[업종별 가맹점 수 상위 12] ({biz})")
        print(df[biz].value_counts().head(12).to_string())


if __name__ == "__main__":
    if not SERVICE_KEY:
        print("[!] export DATA_GO_KR_KEY='발급받은_인증키' 먼저 실행하세요.")
        sys.exit(1)

    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--collect", action="store_true")
    args = ap.parse_args()

    try:
        collect() if args.collect else probe()
    except requests.HTTPError as e:
        print(f"[!] HTTP 오류: {e}")
    except RuntimeError as e:
        print(f"[!] {e}")
    except requests.RequestException as e:
        print(f"[!] 네트워크 오류: {e}")
