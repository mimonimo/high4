# 배포 및 운영 메모

## 현재 배포 상태
- 배포 URL: https://mimonimo.github.io/high4/ (GitHub Pages, main 브랜치 root)
- 저장소: https://github.com/mimonimo/high4 (Public)
- 정적 데이터 방식 — 페이지는 `data/*.json` 4개만 fetch, 서버·인증키 없음

## 외부 리소스
| 리소스 | 비고 |
|---|---|
| Plotly (cartesian 부분 번들) | CDN + SRI 해시 |
| Leaflet 1.9.4 | CDN + SRI, 카카오맵 실패 시 폴백용 |
| Google Fonts | Black Han Sans · IBM Plex Sans KR · IBM Plex Mono |
| 카카오맵 JS SDK | 도메인 제한된 **공개용 JavaScript 키** 사용 (REST 키 아님). 배포용/로컬용 앱 키를 접속 호스트로 자동 선택 |

## ⚠️ 다른 계정/저장소로 이전할 때 체크리스트
1. 저장소 이전(Settings → Transfer) 또는 새 저장소에 push
2. 새 저장소 Settings → Pages → main / root 활성화
3. **카카오 개발자 콘솔**(developers.kakao.com) → 배포용 앱 → 플랫폼 → Web에
   새 도메인 `https://<새계정>.github.io` **추가 등록** ← 잊으면 지도가 OSM 폴백으로만 뜸
4. README.md의 배포 URL·저장소 URL 갱신
5. index.html의 `og:url` 갱신
6. 시크릿 창 + 휴대폰에서 새 URL 정상 동작 확인
7. 제출 양식의 URL 갱신 (제출 마감 이후 커밋은 심사 미반영 가능)

## 데이터 재생성 (캠프 시)
- 가맹점 수집: `scripts/fetch_storeinfo.py` (env `DATA_GO_KR_KEY`)
- 지오코딩: 로컬 `geocode.py` (env는 `.env`의 `KAKAO_REST_KEY`), 캐시 `geocode_cache.json` 재사용
- 주의: matrix.json 재생성 시 `NaN`이 아닌 `null`로 저장할 것 (브라우저 JSON.parse는 NaN 불가)
- 개인정보(사업자번호·전화번호) 컬럼은 배포 데이터에서 반드시 제거
