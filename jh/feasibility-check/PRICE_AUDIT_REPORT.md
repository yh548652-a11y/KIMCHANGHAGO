# 검색 정확도·가격 교차 검증 보고서 — 2026-11-25

## 검증 방법

1. 영화·시리즈·음악 10개 검색어로 실제 외부 API 검색
2. 첫 검색 결과가 제목 또는 제작자 기준으로 검색어와 관련 있는지 확인
3. Apple 결과의 콘텐츠 ID를 Apple 공식 Lookup API로 별도 재조회
4. 화면의 가격·통화와 Lookup 응답의 가격·통화 비교
5. 구매가·구독료·가격 미제공을 구분

재실행 명령:

```powershell
.\.venv\Scripts\python.exe audit_prices.py
```

## 수정 전 발견한 문제

- `Sherlock` 검색 첫 결과가 다른 작품인 `Elementary, Season 2`로 표시됨
- 영문 영화 `Inception`, `Oppenheimer`가 한국어 Wikipedia 보조 검색에서 누락됨
- `1.29 USD`가 Apple Music 구독료처럼 보일 수 있었음

## 적용한 수정

- 검색어의 모든 단어가 제목·제작자에 포함된 Apple 결과만 표시
- 한글 영화는 한국어 Wikipedia, 영문 영화는 English Wikipedia에서 정확한 제목만 보조 조회
- Apple 가격에 `price_type: store_purchase` 추가
- React 화면에서 `Apple Store 개별 구매가`라고 표시
- 관련 없는 결과는 보여 주지 않고 검색 결과 없음으로 처리

## 수정 후 결과

| 분야 | 검색어 | 첫 결과 | 가격 대조 |
|---|---|---|---|
| 영화 | 기생충 | 기생충 (영화) | Wikipedia 가격 미제공 — 정상 |
| 영화 | Inception | Inception | Wikipedia 가격 미제공 — 정상 |
| 영화 | Oppenheimer | Oppenheimer (film) | Wikipedia 가격 미제공 — 정상 |
| 시리즈 | Breaking Bad | Breaking Bad, Season 5 | 19.99 USD — Apple Lookup 일치 |
| 시리즈 | Game of Thrones | Game of Thrones, Season 2 | 24.99 USD — Apple Lookup 일치 |
| 시리즈 | Sherlock | 결과 없음 | 관련 없는 Elementary 제거 |
| 음악 | BTS | Boy With Luv (feat. Halsey) | 1.29 USD — Apple Lookup 일치 |
| 음악 | Adele | Someone Like You | 1.29 USD — Apple Lookup 일치 |
| 음악 | 아이유 | 결과 없음 | 영문명 IU 자동 변환 미지원 |
| 음악 | Taylor Swift | Patient Zero | 0.69 USD — Apple Lookup 일치 |

- 가격 불일치: 0건
- 관련 없는 첫 결과: 수정 후 0건
- 가격 미제공 영화: 3건이며 가격을 임의 생성하지 않음
- 결과 없음: Sherlock, 아이유 2건

## 가격 해석 주의

- Apple API의 `trackPrice`·`collectionPrice`는 Store 개별 구매 가격이며 Apple Music 월 구독료가 아닙니다.
- Apple Music 한국 공식 요금은 개인 월 8,900원, 가족 월 13,500원으로 별도 관리해야 합니다.
- 검색 결과 가격과 플랫폼 구독료를 같은 가격으로 비교하면 안 됩니다.
- 프로모션 가격과 정상가는 분리하고 출처·확인 시점을 표시해야 합니다.

## 결론

현재 표시된 Apple 가격은 공식 Lookup API와 일치했지만 국내 음악 서비스 가격 비교에는 적합하지 않습니다. Apple은 기술 검증용 보조 출처로 두고, 최종 음악 검색은 Spotify를 우선 검토하며 멜론·지니·벅스는 공식 이용권 가격과 공식 검색 링크를 별도 관리하는 방식이 적합합니다.
