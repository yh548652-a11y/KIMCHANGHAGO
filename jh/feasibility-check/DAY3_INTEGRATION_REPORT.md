# 3일차 통합·타당성 검증 보고서 — 2026-11-25

## 검증한 사용자 흐름

사용자가 React 검색 화면에서 영화·시리즈·음악을 검색하면 Flask가 입력을 검사하고 외부 API에서 실제 데이터를 받아 공통 형식으로 반환하며, React가 결과 또는 오류를 표시하는 흐름을 검증했습니다.

## 완료한 작업

- 팀 저장소의 최신 `main` 반영
- 프로젝트 전용 Python 가상환경과 Flask 3.1.3 설치
- 프론트엔드 잠금 파일 기준 의존성 설치
- 공통 응답에 `verification_status`, `checked_at` 추가
- React 카드에 데이터 출처와 확인 시점 표시
- Flask 자동 테스트와 React 생산 빌드 실행
- 실제 Flask 서버와 외부 API를 통한 영화·시리즈·음악 검색
- 브라우저에서 React → Flask → 외부 API → 결과 카드 전체 흐름 확인
- 공백 검색어와 잘못된 카테고리 오류 처리 확인
- 브라우저 콘솔 오류 확인

## 검증 결과

| 경계 | 결과 | 실제 증거 |
|---|---|---|
| React 화면 렌더링 | 통과 | 취향 반경 검색 화면 표시 |
| React → Flask | 통과 | 화면에 `Flask 연결됨` 표시 |
| Flask 상태 API | 통과 | `GET /api/health` → HTTP 200, `status: ok` |
| 영화 외부 조회 | 통과 | `기생충 (영화)` 1건, 한국어 Wikipedia API |
| 시리즈 외부 조회 | 통과 | `Breaking Bad, Season 5` 포함 2건, Apple API |
| 음악 외부 조회 | 통과 | `Boy With Luv (feat. Halsey)` 포함 6건, Apple API |
| 공통 응답 | 통과 | `items`, `source_name`, `verification_status`, `checked_at` 확인 |
| 입력 오류 | 통과 | 검색어 누락·잘못된 카테고리 HTTP 400 |
| 브라우저 오류 | 통과 | 최종 검증 시 콘솔 오류 0건 |
| Flask 자동 테스트 | 통과 | 7 tests, OK |
| React 생산 빌드 | 통과 | Vite 16 modules transformed |

## 발견한 문제와 조치

1. 포트 5000에 이전 Flask 서버가 실행 중이어서 최신 필드가 없는 응답을 반환했습니다.
   - 최신 서버를 5050에서 분리 실행해 오래된 서버와 구분했습니다.
2. React 테스트 서버를 5174로 실행하자 Flask의 기본 CORS 허용 주소 5173과 달라 브라우저가 응답을 차단했습니다.
   - `FRONTEND_ORIGIN=http://127.0.0.1:5174`를 지정해 연결을 확인했습니다.
3. 외부 API가 제공하는 Apple 가격은 미국 Store의 개별 구매 가격일 수 있습니다.
   - 국내 OTT·음악 구독료로 표현하지 않고 화면에 안내 문구를 유지했습니다.

## 팀 통합 상태

- 현재 팀 저장소의 `sy`, `sh`, `dy` 폴더에는 연동 가능한 영화·음악 API 코드가 아직 없고 연습용 `test.txt`만 있습니다.
- 따라서 오늘은 `jh/feasibility-check`의 Apple·Wikipedia 연결을 기준으로 전체 흐름을 검증했습니다.
- 다른 담당자의 TMDB·음악 API 코드가 올라오면 현재의 공통 `items` 형식에 맞춰 연결해야 합니다.

## 제한 사항

- 모든 API에는 지역·쿼터·정책·인증 제한이 있으므로 제한 없이 연동된다고 표현할 수 없습니다.
- TMDB 토큰과 Spotify 자격 증명이 없어 두 API의 실제 인증 호출은 아직 검증하지 못했습니다.
- Wikipedia는 영화 소개 보조 출처이며 가격·평점·OTT 제공처의 출처가 아닙니다.
- Apple 가격은 국내 구독료 비교 자료가 아닙니다.
- 로그인, Supabase, AI 추천은 이번 3일차 통합 검증 범위가 아닙니다.

## 팀에 공유할 연결 규칙

```http
GET /api/health
GET /api/search?category=movie&q=기생충
GET /api/search?category=series&q=Breaking%20Bad
GET /api/search?category=music&q=BTS
```

- 기본 서버 주소: `http://127.0.0.1:5000`
- 허용 category: `movie`, `series`, `music`
- 성공: HTTP 200과 `items` 배열
- 입력 오류: HTTP 400과 `error.code`, `error.message`
- 외부 API 오류: HTTP 502와 `EXTERNAL_API_ERROR`
- 비밀키는 `.env`로 관리하고 GitHub에 커밋하지 않음

## 결론

영화·시리즈·음악 검색을 하나의 Flask API로 연결하고 React 화면에 표시하는 기능은 구현 가능합니다. 다만 가격 비교와 플랫폼 추천은 신뢰할 수 있는 별도 출처, 확인 시점, 지역·요금제 구분을 추가로 확보해야 하므로 현재 단계에서는 조건부 가능으로 판단합니다.
