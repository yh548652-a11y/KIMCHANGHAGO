# 취향 반경 — 외부 콘텐츠 API 타당성 검증

React 검색 화면 → Flask 서버 → 외부 콘텐츠 API → 공통 응답 → 결과 카드까지 연결한 검증 프로젝트입니다.

## 현재 연결된 출처

- 음악·TV 시리즈: Apple iTunes Search API
- 영화: Apple 검색 결과가 없을 때 한국어 Wikipedia API 보조 조회
- TMDB·Spotify: 자격 증명이 준비되지 않아 아직 연결하지 않음

Apple 가격은 제공되는 경우의 Store 구매 가격이며 OTT·음악 구독료가 아닙니다. Wikipedia는 영화 소개 보조 출처이며 가격·평점 출처가 아닙니다.

## 실행 방법

PowerShell 터미널 1에서 Flask를 실행합니다.

```powershell
cd "팀 저장소 경로\KIMCHANGHAGO\jh\feasibility-check"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

PowerShell 터미널 2에서 React를 실행합니다.

```powershell
cd "팀 저장소 경로\KIMCHANGHAGO\jh\feasibility-check\frontend"
npm install
npm run dev
```

브라우저에서 `http://127.0.0.1:5173`을 엽니다. 화면 오른쪽 위에 `Flask 연결됨`이 표시되어야 합니다.

## API 규칙

### 서버 상태

```http
GET /api/health
```

### 콘텐츠 검색

```http
GET /api/search?category=movie&q=기생충
GET /api/search?category=series&q=Breaking%20Bad
GET /api/search?category=music&q=BTS
```

- `category`: `movie`, `series`, `music`
- `q`: 필수 검색어
- 성공: HTTP 200과 `items` 배열
- 입력 오류: HTTP 400과 `error.code`, `error.message`
- 외부 API 오류: HTTP 502와 `EXTERNAL_API_ERROR`

공통 결과 필드는 다음과 같습니다.

```text
id, category, title, creator, image_url, source_url,
genre, duration_ms, price_amount, currency, country,
source_name, data_status
```

## 자동 테스트와 빌드

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cd frontend
npm run build
```

2026-11-24 확인 결과 Flask 테스트 7개와 React 생산 빌드가 통과했습니다.

## 환경변수

`.env.example`을 참고합니다.

```text
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FRONTEND_ORIGIN=http://localhost:5173
ITUNES_COUNTRY=KR
EXTERNAL_API_TIMEOUT=8
```

API 키와 토큰은 `.env`에만 저장하고 GitHub에 커밋하지 않습니다. 현재 연동에는 비밀키가 필요하지 않습니다.

## 검증 결과와 제한

- 영화 `기생충`, 시리즈 `Breaking Bad`, 음악 `BTS`의 실제 외부 응답 확인
- React 화면에서 세 범주의 실제 결과 카드 표시 확인
- 빈 검색어, 잘못된 카테고리, 외부 API 실패 응답 구분
- 한국 Store에 결과가 없으면 Apple 미국 Store를 한 번 보조 조회
- Apple 영화 검색은 대표 제목들에서 0건이어서 Wikipedia 보조 출처 사용
- 영화 평점·OTT 제공처·구독료 비교에는 TMDB 등 별도 검증 출처 필요
- Spotify 개발 모드는 Premium·사용자 수·쿼터 제한 때문에 공개 서비스 핵심 출처로 사용하기 어려움
- 로그인, Supabase, OpenAI 추천은 이번 타당성 검증 범위가 아님

세부 기록은 `FEASIBILITY_REPORT.md`를 확인합니다.
