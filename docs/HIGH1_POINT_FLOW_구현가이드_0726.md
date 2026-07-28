# HIGH1 POINT FLOW — 구현 가이드

> 폐광지역 상생 포인트 수요·공급 진단 대시보드
> 팀 **High4** · 바이브코딩 경진대회 2026.8.10~8.12 · Claude Code 작업용 레퍼런스
> **모든 수치는 실제 데이터 전수 집계 실측값. 배포 방식은 GitHub Pages 정적 웹으로 확정.**

---

## 0. 프로젝트 정의

**하이원포인트 "사용현황"(수요, 507,628건) × "가맹점 목록"(공급, 1,548곳)을 결합해,**
**① 포인트가 소진돼 못 쓰는 가맹점을 알려주고 ② 지역·업종별로 가맹점을 어디에 늘려야 하는지 진단하고 ③ 수요를 재분배하면 소진이 얼마나 줄어드는지 보여주는 웹 대시보드.**

- **팀명**: High4
- **산출물명**: HIGH1 POINT FLOW
- **한 줄 소개**: 하이원포인트 가맹점의 잔여한도와 사용현황을 결합해 소비 사각지대를 진단하는 대시보드
- **활용 데이터셋**: ① (주)강원랜드_하이원포인트 사용현황(파일) ② (주)강원랜드_하이원포인트 가맹점 상세정보(오픈API)

핵심 병목: **가맹점 API에 업종이 없다.** → 상호명으로 추정(규칙 51% + LLM 49%). 이 업종 축이 있어야 세 기능이 모두 성립한다.

---

## 1. 배포 전략 — 정적 웹 (GitHub Pages) ★가장 중요

### 왜 정적인가 (사무국 요구사항 3-4와 정확히 일치)

사무국 안내문이 "가장 흔한 실패 지점"으로 명시:
> 필요한 데이터를 미리 CSV/JSON으로 내려받아 저장소에 포함하고, 산출물이 이 파일을 읽어 동작하도록 만드는 정적 데이터 방식이 가장 안전.

**우리 구조가 그대로 이것.** 캠프 1일차에 API로 1,548건을 받아 `data/merchants.json`으로 저장 → 웹은 이 파일만 fetch. 배포물에 **API 호출도, 인증키도 없다.** CORS·Mixed Content·환경변수 세 함정이 원천 제거된다.

### 왜 Streamlit이 아니라 GitHub Pages인가

| | Streamlit Cloud | **GitHub Pages (채택)** |
|---|---|---|
| 절전(sleep) | 무료요금제 잠자기 → 첫 접속 지연 | **없음. 상시 접속** |
| 사무국 유의사항 | "절전 시 느림" 경고 대상 | "상시 접속 방식 권장" 명시 |
| 심사 리스크 | 심사위원 접속 시 로딩 지연 | 없음 |

→ 순수 HTML/CSS/JS. 데이터가 275KB(JSON)로 가벼워 브라우저에 통째로 올려도 무방.

### 데이터 흐름

```
[캠프 1일차, 로컬 1회]
  fetch_storeinfo.py  →  merchants_raw.json (API 16회 호출, 개발자 PC에서만)
  classify.py         →  가맹점별 industry 부여 (규칙+LLM)
  build_data.py       →  data/merchants.json  (앱이 읽는 최종 파일)
                         data/usage.json       (사용현황 집계)
                         data/matrix.json      (지역×업종 108셀 사전계산)
        │
        └─ git commit  →  저장소에 정적 데이터로 포함

[배포/심사]
  GitHub Pages  →  index.html 이 data/*.json 을 fetch → 렌더링
                   (API 호출 0, 인증키 0, 서버 0)
```

**핵심: 무거운 계산(업종분류·집계·HHI)은 로컬에서 미리 끝내 JSON에 담는다. 브라우저는 완성된 숫자를 그리기만 한다.**

---

## 2. 데이터 (전수 검증 완료)

### 2-1. 수요 — 파일데이터

`주강원랜드_하이원포인트_사용현황_20251231.csv` (5,831행, **cp949**)
컬럼: `가맹점 영업일자` / `업종`(18종) / `고한읍 건수` `사북읍 건수` `정선군 건수` `태백시 건수` `영월군 건수` `삼척시 건수`

**2025년 총 507,628건.** 업종 상위: 일반음식점업 205,050(40.4%) · 식품판매업 65,517 · 슈퍼마켓 63,338 · 소매업 57,566 · 숙박업 46,143 · 이ㆍ미용업 23,571 · 커피전문점 12,104 …
시계열: 월 최대/최소 1.12배(계절성 낮음), 토요일 최대.

### 2-2. 공급 — 오픈API (수집 완료, 로컬 전용)

```
GET https://apis.data.go.kr/B552525/pbdata/getStoreInfo?serviceKey={KEY}&pageNo=1&numOfRows=100
```
totalCount 1,548 · 일일 5,000회 · **이 호출은 로컬에서 1회만. 배포물엔 포함 안 됨.**

| 필드 | 내용 | 배포 |
|---|---|---|
| `FRCS_NM` | 가맹점명 (업종 추정 단서) | 포함 |
| `FRCS_ADDR` | 주소 (읍면동 포함) | 포함 |
| `PNT_USABLE_AMT` | **잔여 한도** (누적액 아님) | 포함 |
| `FRCS_REG_NO` | 등록번호 | 포함 |
| `FRCS_BRNO` `FRCS_TELNO` | 사업자번호·전화 | **제거**(개인정보·미사용) |

**`PNT_USABLE_AMT` = 잔여 한도 확정**: 최댓값이 정확히 4,000,000원 상한, 그 값에 242곳(15.6%) 집중.
잔액 0원 57곳 · 10만원 미만 90곳(5.8%) · 만액 242곳(15.6%) · 평균 274만원.

### 2-3. 결합 결과 — 프로젝트의 심장

| 지역 | 가맹점 | 사용건수 | 가맹점당 | 만액(미사용) | 소진(<10만) | 진단 |
|---|---:|---:|---:|---:|---:|---|
| 사북읍 | 276 | 163,663 | **593** | 10.1% | **19.2%(53)** | 과부하 |
| 고한읍 | 251 | 94,363 | 376 | 12.0% | 5.6% | 양호 |
| 영월군 | **70** | 18,675 | 267 | 12.9% | 4.3% | 공급 부재 |
| 정선군 | 275 | 71,859 | 261 | 16.4% | 3.6% | 중간 |
| 삼척시 | 114 | 27,355 | 240 | 2.6% | 0.9% | 공급 부재 |
| 태백시 | **562** | 131,713 | **234** | **22.6%(127)** | 1.6% | 수요 부진 |
| 전체 | 1,548 | 507,628 | 328 | 15.6% | 5.8% | |

**결론**: 사북=과부하(가도 못 씀) · 태백=수요부진(562곳 중 127곳 미사용) · 영월/삼척=공급부재(가맹점당 사용은 오히려 높음). **총량 지표로는 안 보이고 공급을 붙여야 보인다.**
유휴 한도(만액 242곳) **9.68억 원** = 리밸런싱 재원.

---

## 3. 파이프라인 (로컬, 1일차)

### 3-1. `fetch_storeinfo.py` — API 수집 (1회, 배포 제외)

```python
import os, time, json, requests

URL = "https://apis.data.go.kr/B552525/pbdata/getStoreInfo"
KEY = os.environ["DATA_GO_KR_KEY"]        # 절대 하드코딩 금지

def collect():
    rows, page = [], 1
    while True:
        r = requests.get(URL, params={"serviceKey": KEY, "pageNo": page,
                                       "numOfRows": 100, "type": "json"}, timeout=15)
        r.raise_for_status()
        p = r.json(); data = p.get("data", [])
        if not data: break
        rows += data
        if len(rows) >= p.get("totalCount", 0): break
        page += 1; time.sleep(0.2)
    json.dump(rows, open("merchants_raw.json", "w"), ensure_ascii=False)
    return rows                            # 검증됨: 1,548건
```

### 3-2. `normalize.py` — 주소 → 지역 (순서가 전부)

```python
import re
def to_region(addr):
    a = re.sub(r"강원(특별자치)?도\s*", "", str(addr))
    if "고한읍" in a: return "고한읍"      # 고한·사북을 정선보다 먼저!
    if "사북읍" in a: return "사북읍"
    if "태백시" in a: return "태백시"
    if "영월군" in a: return "영월군"
    if "삼척시" in a: return "삼척시"
    if "정선군" in a: return "정선군"
    return "미분류"
```
> 순서 안 지키면 `정선군 고한읍`이 이중 계상돼 합계가 2,076(실제 1,548)이 된다. 이 순서면 미분류 0건.

### 3-3. `classify.py` — 업종 하이브리드 분류

**규칙(51.1%, 791곳)** → 안 잡힌 757곳을 **LLM**으로.

```python
RULES = {
  "일반음식점업": "식당|국수|한식|고기|갈비|숯불|횟집|해장|칼국수|반점|짜장|초밥|포차|분식|김밥|찌개|탕|곱창|막국수|냉면|닭|치킨|피자|뷔페",
  "커피전문점": "커피|카페|COFFEE|CAFE|베이커리|제과|빵|디저트",
  "숙박업": "모텔|호텔|펜션|여관|민박|리조트|게스트",
  "슈퍼마켓": "마트|슈퍼|마켓|편의점|CU|GS25",
  "식품판매업": "정육|축산|청과|수산|과일|반찬|떡|농산|산나물|건강원",
  "이ㆍ미용업": "미용|헤어|이발|바버|네일|살롱",
  "주유소·LPG충전소": "주유|가스|충전소|석유", "세탁업": "세탁|크리닝|런드리",
  "목욕장업": "목욕|사우나|찜질", "자동차 전문수리업": "카센타|카센터|정비|공업사|타이어",
  "자동자 세차업": "세차", "당구장 운영업": "당구", "실내 스크린 골프업": "골프",
  "일반주점업": "주점|호프|술집|BAR|이자카야|소주방",
  "소매업": "잡화|철물|문구|서점|약국|안경|의류|신발|가구|전자|이동통신|꽃|화원|인쇄",
}
```

```python
from anthropic import Anthropic
import json
SYSTEM = """가맹점 상호명을 18개 업종 중 하나로 분류. 판단 어려우면 "미분류".
JSON 배열만: [{"name":"...","industry":"...","confidence":0.0}]
예: 세븐일레븐 정선남면점→슈퍼마켓 / 태백오토밋션→자동차 전문수리업 / 피고지고→미분류"""

def classify(names):
    m = Anthropic().messages.create(model="claude-sonnet-4-6", max_tokens=4000,
        system=SYSTEM, messages=[{"role":"user","content":json.dumps(names, ensure_ascii=False)}])
    t = m.content[0].text.strip().removeprefix("```json").removesuffix("```")
    return json.loads(t)
# 757건을 50씩 → 16회. confidence<0.7 또는 미분류 → 지표 제외
```
**검증**: 무작위 150건 수기 라벨링 → 정확도·혼동행렬. (발표 최강 무기)

### 3-4. `build_data.py` — 배포용 JSON 사전계산

```python
# 무거운 계산은 여기서 전부 끝낸다. 브라우저는 그리기만.
import json, pandas as pd

def hhi(shares): return float((shares**2).sum()*10000)

# merchants.json : 조회 화면용 (개인정보 제거)
merchants = df[["FRCS_REG_NO","FRCS_NM","FRCS_ADDR","PNT_USABLE_AMT","region","industry"]]
json.dump(merchants.to_dict("records"), open("data/merchants.json","w"), ensure_ascii=False)

# matrix.json : 지역×업종 108셀 (가맹점수, 사용건수, 가맹점당, 진단유형)
# usage.json  : 일별/지역별 집계 (시계열·산점도용)
```

---

## 4. 프론트엔드 (GitHub Pages)

### 구조
```
index.html            # 탭 3개 (조회 / 진단 / 리밸런싱)
css/style.css
js/app.js             # data/*.json fetch → 렌더링
data/merchants.json   # 1,548곳 (275KB)
data/matrix.json      # 108셀 사전계산
data/usage.json       # 집계
README.md
```

### 라이브러리 (전부 CDN, 빌드 불필요 → Pages 바로 배포)
- **Plotly.js** (CDN) — 히트맵·산점도. 파이썬 Plotly와 API 거의 동일
- 순수 JS — 검색·필터·정렬·리밸런싱 계산(가벼워서 프레임워크 불필요)
- 지도가 필요하면 Leaflet(CDN). 우선순위 낮음.

> React/Vue를 쓰면 GitHub Actions 빌드 워크플로가 필요(사무국 안내 표 참조). **순수 HTML/JS면 Settings→Pages→main 선택만으로 끝.** 2일 캠프엔 이게 최선.

### 탭 ① 가맹점 조회 (이용자용) — `demo_가맹점조회.html`이 이미 이 형태
검색(상호·주소) + 지역칩 + 업종필터 + 잔여한도 게이지 + 정렬(소진 임박순 기본).
잔액 0~10만원 = 빨강 "소진 임박", 대안 가맹점(같은 지역·업종, 잔액 여유) 추천.

### 탭 ② 사각지대 진단 (운영자용)
```javascript
Plotly.newPlot('heatmap', [{
  type:'heatmap', x:INDUSTRIES, y:REGIONS,
  z: matrix.usage_per_store,          // 색 = 가맹점당 사용량(로그)
  text: matrix.store_count, texttemplate:'%{text}',
  colorscale:'Blues'
}], {margin:{l:70,t:20,b:90}});
// 가맹점 0 = 빗금(유치필요) / 3곳 미만 = 회색(표본부족)
```
KPI 카드: 총 사용 507,628 · 가맹점 1,548 · 잔액0원 57 · 만액 242.

### 탭 ③ 수요 리밸런싱 시뮬레이터
슬라이더(수요 이전 비율 0~30%) → 과부하 가맹점 수요를 유휴 가맹점으로 이전 →
소진 가맹점 수, 만액 가맹점 수, 지니계수가 실시간으로 어떻게 변하는지 표시.
계산은 순수 JS(브라우저에서 즉시). 재원 = 유휴 한도 9.68억.

---

## 5. 2일 일정

| 시점 | 작업 | 산출물 |
|---|---|---|
| 1일차 오전 | 저장소 생성(Public) · API 수집 · CSV 로드 | `merchants_raw.json` |
| 1일차 오후 | 주소 정규화 · 업종 분류 + 150건 검증 · `build_data.py` | `data/*.json` |
| 1일차 야간 | index.html 골격 · 조회 탭 | 탭① 동작 |
| 2일차 오전 | 진단 히트맵 · KPI · 산점도 | 탭② |
| 2일차 오후 | 리밸런싱 슬라이더 · **GitHub Pages 배포** · 모바일 확인 | 배포 URL |
| 2일차 저녁 | README · 스크린샷 · 발표 | 제출 |

**MVP 커트라인**: 조회 + 히트맵 + KPI. 산점도·리밸런싱은 그 다음. 지도는 최후.

---

## 6. 제출 체크리스트 (사무국 4번 그대로)

```
[ ] 깃허브 저장소 Public
[ ] README.md 작성 (소개·활용데이터·주요기능·실행방법)
[ ] 배포 URL이 https:// 로 시작
[ ] 시크릿창(로그아웃)에서 배포 URL 정상 실행
[ ] 배포 URL에서 데이터 정상 표시
[ ] 로그인 없이 접속 가능
[ ] 휴대폰에서 열림 확인
[ ] 제출양식: 팀명 High4 · 산출물명 · 한줄소개 · 데이터셋명 · 저장소URL · 배포URL
```

**흔한 실패**: 저장소 링크만 제출(코드만 보임) → 반드시 **실행되는 배포 URL** 함께.

---

## 7. 보안 (안내문이 2회 강조)

```
.gitignore:
  .env
  merchants_raw.json       # 원본(전화번호 포함) 커밋 금지
  __pycache__/
  .venv/
```
- **인증키는 절대 커밋 금지.** `os.environ["DATA_GO_KR_KEY"]`로만. 정적 배포라 배포물엔 키가 안 들어가지만, `fetch_storeinfo.py`에 하드코딩하면 저장소에 남는다.
- **대화에 노출된 키는 캠프 전 재발급.**
- `data/merchants.json`엔 `FRCS_BRNO`·`FRCS_TELNO` 제외(개인정보). 상호·주소·잔여한도만.
- 더미 전화번호(0330000000) 187곳(12.1%) = 휴·폐업 잔존 가능 → README 한계에 명시.

---

## 8. README.md 템플릿

```markdown
# HIGH1 POINT FLOW
> 하이원포인트 가맹점의 잔여한도와 사용현황을 결합해 소비 사각지대를 진단하는 대시보드
> 팀 High4 · 공공데이터 활용 바이브코딩 경진대회

## 배포
- 배포 URL: https://high4.github.io/high1-point-flow/
- 저장소: https://github.com/high4/high1-point-flow

## 활용 데이터 (공공데이터포털, 제공기관: (주)강원랜드)
- 하이원포인트 사용현황 (파일데이터, 2025년, 507,628건)
- 하이원포인트 가맹점 상세정보 (오픈API getStoreInfo, 1,548개소)
  → 캠프 1일차에 수집해 data/merchants.json 으로 저장(정적 방식)

## 주요 기능
1. 가맹점 조회·소진 경보 — 잔여한도 확인, 소진 임박 경고, 대안 가맹점 추천
2. 소비 사각지대 진단 — 지역×업종 히트맵으로 유치/촉진/분산 필요 구간 구분
3. 수요 리밸런싱 시뮬레이터 — 수요 재분배 시 소진 가맹점 감소폭 확인

## 실행 방법
- 배포 URL 접속만으로 실행 (별도 설치 불필요)
- 로컬: 저장소 clone 후 `python -m http.server` → localhost:8000

## 데이터 처리
- 가맹점 API에 업종이 없어 상호명으로 업종 추정(규칙 51% + LLM 49%, 150건 수기검증)
- 잔여한도(PNT_USABLE_AMT) 최댓값 400만원 상한 확인

## 한계
- 전화번호 더미값 가맹점 187곳 → 휴·폐업 잔존 가능성
- 업종 분류 미분류 건은 지표에서 제외
```

---

## 9. Claude Code 프롬프트 (복붙용)

```
GitHub Pages에 배포할 정적 웹 대시보드를 만든다. 순수 HTML/CSS/JS + Plotly.js(CDN).
빌드 도구·프레임워크 없이 index.html 하나로 동작해야 한다. (React 금지 — Pages 직접 배포)

데이터 (같은 저장소의 정적 파일, fetch로 읽음. API 호출 절대 금지):
- data/merchants.json : [{FRCS_NM, FRCS_ADDR, PNT_USABLE_AMT, region, industry}] 1,548건
- data/matrix.json    : 지역(6)×업종(18) 108셀 {region, industry, store_count, usage, usage_per_store, type}
- data/usage.json     : 지역별 집계

탭 3개:
1. 가맹점 조회 — 상호/주소 검색, 지역칩 필터, 업종 셀렉트, 잔여한도 게이지.
   정렬 기본은 잔액 적은순. 0~10만원은 빨강 "소진 임박", 같은 지역·업종의 여유 가맹점 추천.
2. 사각지대 진단 — Plotly 히트맵. 색=usage_per_store(로그), 셀주석=store_count.
   type==공급공백은 빗금, store_count<3은 회색. KPI 카드: 총사용 507628, 가맹점 1548, 잔액0원 57, 만액 242.
3. 리밸런싱 — 슬라이더(0~30%). 과부하 가맹점 수요를 유휴 가맹점으로 이전 시
   소진 가맹점 수/지니계수 실시간 재계산(순수 JS).

지역: 태백시562 사북읍276 정선군275 고한읍251 삼척시114 영월군70. 포인트 한도 400만원.
localStorage 금지. 모바일 반응형. 로그인 없음.
```

---

## 10. 발표 예상 질문

**Q. 배포에서 API가 안 되면?** → 실시간 호출을 안 합니다. 1일차에 데이터를 받아 JSON으로 저장소에 넣었고, 웹은 그 파일만 읽습니다. 사무국이 권장한 정적 방식입니다.
**Q. 업종은 어디서?** → API에 없어서 상호명으로 추정했습니다. 규칙 51%+LLM 49%, 150건 수기검증.
**Q. 영월 3.7%가 문제?** → 원인이 문제입니다. 영월 가맹점당 267건은 태백(234)보다 높습니다. 수요가 아니라 가맹점(70곳)이 부족한 겁니다. 태백은 반대로 562곳 중 127곳이 미사용입니다.
**Q. 잔여한도?** → 사북 5곳 중 1곳이 잔액 10만원 미만, 전체 0원 57곳. 가서야 못 쓰는 걸 미리 알려줍니다.
