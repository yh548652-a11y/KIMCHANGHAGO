# 취향 반경 — 콘텐츠 탐색 프로토타입

화면의 임시 서비스 이름은 `src.jsx`의 `SERVICE_NAME` 상수에 있는 **취향편집**입니다.

## 실행
프로젝트 폴더에서 `npm install` 후 `npm run dev`를 실행하고 표시된 로컬 주소를 브라우저에서 엽니다.

웹사이트 폴더에서 `python -m pip install -r requirements.txt`로 의존성을 준비하고 `python -B spotify_api.py`로 통합 Flask 서버를 실행합니다. 웹사이트의 **개발용 연결 설정 → Flask 서버 → 연결 확인**에서 기본 주소 `http://127.0.0.1:5050`을 확인할 수 있습니다. 주소를 바꾸려면 Vite 실행 환경에 `VITE_API_BASE_URL`을 지정하세요. 브라우저에 공개되는 값이므로 API 키를 넣지 않습니다.

## 현재 범위

### Spotify 음악 검색

이 웹사이트 폴더에서 `python -m pip install -r requirements.txt`로 의존성을 설치하고 `python -B spotify_api.py`를 실행합니다. 팀의 `SPOTIFY_CLIENT_ID`와 `SPOTIFY_CLIENT_SECRET`은 서버 환경변수나 이 폴더의 Git 제외 `.env`에 설정하세요. 서버가 시작될 때 파일을 읽으며 기존 환경변수를 우선합니다. `SPOTIFY_MARKET` 기본값은 `US`입니다.

개발 기본 구성에서는 음악이 통합 서버의 `GET /api/music/search?q=검색어`를 사용합니다. 웹사이트에서 Flask 서버 모드를 선택한 뒤 **음악·오디오 → 음악**에서 검색하세요. 배포 환경에서는 같은 출처에 API를 라우팅하거나 공개 API 주소인 `VITE_API_BASE_URL`을 설정합니다. 음악 서버를 따로 운영할 때만 `VITE_MUSIC_API_BASE_URL`을 사용하세요.

### TMDB 영화·드라마

서버 환경 또는 Git에서 제외된 `.env`에 `TMDB_READ_ACCESS_TOKEN` 또는 `TMDB_API_KEY`를 설정하고 통합 서버를 재시작하세요. 둘 다 있으면 토큰을 우선합니다. 기본 언어와 지역은 `ko-KR`, `KR`입니다. 인증 정보가 비어 있으면 기존 화면의 영화·드라마 검색은 Apple·Wikipedia 경로를 사용합니다.

- 검색: `GET /api/media/search?type=movie&query=기생충&page=1` (`type=tv`는 드라마)
- 상세: `GET /api/media/movie/{id}` 또는 `GET /api/media/tv/{id}`
- 제공처: 상세 경로 뒤에 `/providers`를 추가합니다. 제공처는 JustWatch 데이터이며 지역별 정보가 비어 있을 수 있습니다.

### 탐색 화면
- 음악·오디오, 영화·시리즈, 책·스토리, 게임, 유튜브·영상의 파일 탭 탐색 UI
- 분야별 중분류와 복수 취향 태그 선택(현재 추천 API에는 미반영)
- 작품 검색, 카드·상세 표시, 로딩·빈 결과·오류 상태
- 예시 데이터는 모두 가상 작품이며 실제 API 검증이 아닙니다.
- 초기에는 실제 검색 모드입니다. '검색 모드 및 연결 설정'에서 가상 예시 데이터로 전환할 수 있습니다.
- Flask는 별도 담당자가 실행합니다. 서버 주소를 입력하고 연결 확인 후 검색하세요.
- 로그인·하트 저장·AI 추천은 포함하지 않습니다.

## API 연결 범위
- 영화 → `movie`
- 드라마 → `series`
- 음악 → `music`
- 그 외 중분류는 데이터 연결 준비 중으로 표시하며 API에 임의 매핑하지 않습니다.

## Flask에 전달할 계약 초안
- GET /api/health → JSON 상태 응답
- GET /api/search?category=movie&q=검색어
- category: movie / series / music
- 응답: {"items":[{"id":"provider-id","category":"movie","title":"제목","image_url":null,"source_url":null,"description":"소개"}]}
- 없는 정보는 null 또는 미제공으로 처리합니다.
- 다른 포트의 서버는 로컬 웹 출처 허용 또는 개발 프록시가 필요합니다.
- 다른 PC의 서버에 연결하려면 localhost가 아닌 접근 가능한 서버 주소가 필요합니다.
- 비밀 API 키를 웹 코드나 공유 파일에 넣지 마세요.

전체 서비스는 5개 분야이며, 현재 서버 연결 시험은 위 세 API 값에 한정합니다.
