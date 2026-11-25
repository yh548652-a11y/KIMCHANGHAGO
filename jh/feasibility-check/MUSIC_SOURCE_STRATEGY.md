# 음악 데이터 출처 전략

## 권장 역할 분담

| 출처 | 사용할 정보 | 자동 연동 가능성 | 주의 사항 |
|---|---|---|---|
| Spotify Web API | 곡·아티스트·앨범·이미지·Spotify 링크 | 공식 OAuth 연동 가능 | Premium 개발자 계정, 개발 모드 사용자·쿼터 제한, 가격 미제공 |
| 멜론 | 국내 이용권 가격·공식 검색 링크 | 공개 카탈로그 API 미확인 | 무단 자동 수집 금지, 제휴 API 확보 전 곡 보유 여부 자동 단정 금지 |
| 지니 | 국내 이용권 가격·공식 검색 링크 | 공개 카탈로그 API 미확인 | 프로모션·정상가 분리, 확인 시점 필요 |
| 벅스 | 국내 이용권 가격·공식 검색 링크 | 공개 카탈로그 API 미확인 | 요금제·기기·오프라인 조건 구분 |
| Apple iTunes Search API | 키 없는 모의 검색·개별 구매가 | 현재 구현 완료 | Apple Music 구독료가 아님, 최종 주 출처로 사용하지 않음 |

## 구현 순서

1. Spotify 개발자 앱과 Premium 계정 준비
2. 비밀값은 `.env`의 `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`으로 관리
3. Flask가 Spotify 토큰을 서버에서 발급받고 브라우저에는 비밀값을 전달하지 않음
4. `GET /api/search?category=music&q=...`의 주 출처를 Spotify로 전환
5. Spotify 실패 시 현재 Apple 검색을 보조 출처로 사용
6. 멜론·지니·벅스는 공식 검색 링크와 공식 이용권 가격을 별도 응답으로 제공
7. 제휴 또는 공식 API가 확보된 플랫폼만 곡별 이용 가능 여부를 자동 표시

## 가격 비교 데이터 규칙

- 구독 정상가, 프로모션가, 개별 구매가를 서로 다른 필드로 저장
- 부가세 포함 여부, 기기 제한, 오프라인 재생, 음질, 학생·가족 조건을 함께 저장
- `source_url`과 `checked_at` 필수
- 확인되지 않은 플랫폼 보유곡과 가격은 `null`로 유지
- 가격은 정기 갱신 전까지 `확인 시점 기준`으로 표시

## 현재 공식 페이지에서 확인한 예시

| 플랫폼 | 요금제 예시 | 확인 가격 |
|---|---|---:|
| Spotify | Premium 베이직 | 월 8,690원 |
| Spotify | Premium 개인 | 월 11,990원 |
| 멜론 | 스트리밍클럽 | 월 8,690원 |
| 멜론 | 스트리밍 플러스 | 월 11,990원 |
| 지니 | 스마트 음악감상 정상가 | 월 8,140원 |
| 지니 | 음악감상 정상가 | 월 9,240원 |
| 벅스 | 무제한 듣기+오프라인 재생 | 월 11,990원 |

가격은 2026-11-25 공식 이용권 페이지 확인 기준이며 변경될 수 있습니다.

## 공식 확인 주소

- Spotify 검색 API: https://developer.spotify.com/documentation/web-api/reference/search
- Spotify 개발 모드 제한: https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- Spotify 한국 요금: https://www.spotify.com/kr-ko/premium/
- 멜론 이용권: https://www.melon.com/buy/pamphlet/all.htm
- 지니 이용권: https://pay.genie.co.kr/product/f_Product_Main
- 벅스 이용권: https://music.bugs.co.kr/pay/public
