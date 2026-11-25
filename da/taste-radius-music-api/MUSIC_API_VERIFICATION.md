# 취향 반경 역할 ② 음악 API 검증 결과

## 현재 Spotify 검증 앱 실행

현재 `app.py`는 Spotify를 사용한다. 아래 Apple iTunes 기록은 이전 공급원 검증 결과다.

1. `python -m pip install -r requirements.txt`로 의존성을 설치한다.
2. 이 폴더의 로컬 `.env`에 `SPOTIFY_CLIENT_ID`와 `SPOTIFY_CLIENT_SECRET`을 설정한다. `.env`는 Git에서 제외한다.
3. `python test_spotify.py`로 검색을 검증하거나 `python app.py`를 실행한 뒤 [로컬 검색 화면](http://127.0.0.1:5050/)을 연다.

`/api/music/search?q=Dynamite%20BTS`에서 곡명과 아티스트가 일치하는 결과가 먼저 나온다. 일치하는 곡이 없으면 `resultCount: 0`과 `results: []`가 반환된다.

2026년 11월 23일, Apple iTunes Search API의 미국 스토어에서 대상 3곡을 모두 찾았다. 곡명과 아티스트가 일치한 7개 항목은 앨범명, 앨범 이미지 URL, 재생 시간, 공식 링크를 모두 반환했다. Apple Music 링크 7개에 직접 HTTP GET 요청을 보내 모두 `200`을 확인했으며, 응답 HTML에서도 대응하는 곡 ID를 확인했다. 이 검사는 페이지 응답을 확인한 것으로, 브라우저 화면이나 오디오 재생은 검사 범위에서 제외했다.

과제 안내 이미지 원본은 현재 확인할 수 없어, 대화에서 확인한 1~4단계와 6단계에 맞춰 정리했다. 5단계에는 국가 비교와 공식 링크 확인을 배치했다.

## 1단계 개발 준비 상태

Windows PowerShell, Python 3.12.10, Flask 3.1.3 환경에서 확인했다. 제출 대상은 `test_itunes.py`(3곡 검증), `app.py`(웹페이지 및 JSON 검색 API), `templates/index.html`, `static/music.css`, `static/music.js`다.

## 2단계 공식 문서와 이용 조건

검색 출처는 Apple iTunes Search API의 `https://itunes.apple.com/search`다. 공개 검색에는 계정, API 키, 토큰이 필요 없다. 요청은 `term`, `country=US`, `media=music`, `entity=song`, `limit=5`를 사용한다. Apple 문서의 호출 제한은 분당 약 20회이며 변경될 수 있다. 국가에 따라 검색 대상 스토어와 카탈로그가 달라진다. [Apple 공식 검색 문서](https://performance-partners.apple.com/search-api)

앨범 표지는 해당 콘텐츠를 홍보하는 용도로 사용하며, 인접한 Apple 승인 스토어 배지를 해당 콘텐츠의 공식 페이지에 연결하는 조건이 적용된다. 웹페이지는 Apple 배지를 불러온 뒤 표지를 표시한다. 이번 검증 범위는 곡 정보 검색과 공식 링크 연결이다. 음악 평점, 서비스 요금, 미리듣기 제공·재생 여부는 검증 범위에서 제외했다. [Apple 검색 API 이용 조건](https://performance-partners.apple.com/search-api) · [iTunes 배지 지침](https://marketing.services.apple/itunes-identity-guidelines)

## 3단계 Python 검증 코드 및 실행 방법

`test_itunes.py`는 Python 표준 라이브러리만 사용한다. 웹사이트에 필요한 설치 패키지는 `Flask==3.1.3`이며 하위 의존성은 pip가 설치한다. 필수 환경변수 이름은 **없음**이다. `.env` 파일도 필요 없다. 스토어는 `test_itunes.py`의 `SEARCH_PARAMS`에 설정한다.

프로젝트 폴더의 PowerShell에서 실행한다.

```powershell
python -m pip install Flask==3.1.3
python .\test_itunes.py
python -m flask --app app:app run --host 127.0.0.1 --port 5050
```

- 웹페이지 [http://127.0.0.1:5050/](http://127.0.0.1:5050/)
- JSON 검색 예시 [BTS Dynamite](http://127.0.0.1:5050/api/music/search?q=BTS%20Dynamite)

## 4단계 실제 검색 요청과 오류 처리

| 검색어 | Apple HTTP | Apple `resultCount` | 제목·아티스트 일치 | Flask HTTP |
|---|---:|---:|---:|---:|
| BTS Dynamite | 200 | 4 | 2 | 200 |
| NewJeans Ditto | 200 | 5 | 2 | 200 |
| BLACKPINK Pink Venom | 200 | 5 | 3 | 200 |

기존 스크립트 실행 결과는 성공 3곡, 실패 0곡이다. Flask의 `GET /api/music/search?q=검색어`도 세 검색어를 각각 실제 Apple API에 보내 검증했다. 메인 페이지, CSS, JavaScript는 Flask 테스트 클라이언트에서 각각 `200`을 확인했다.

오류 처리에서는 공백 검색어 `400`을 확인했다. Apple 응답을 모의하여 빈 검색 결과는 `200`과 `resultCount: 0`, Apple HTTP `429`는 `502`와 `upstreamStatus: 429`, 연결 오류와 응답 형식 오류는 `502`와 안내 메시지가 반환되는 것을 확인했다. Apple 요청의 연결 및 읽기 작업에는 15초 소켓 타임아웃을 설정한다. 검증 스크립트는 API 결과가 비어 있는 경우와 결과 중 제목·아티스트가 모두 일치하는 곡이 없는 경우를 별도로 표시한다.

## 5단계 미국 스토어 선택과 공식 링크 확인

사용자의 앞선 한국 스토어 테스트에서 `BTS Dynamite`는 HTTP `200`, `resultCount: 0`이었다. 이번 미국 스토어 테스트에서는 같은 검색어로 4개 결과를 받았다. 아래 7개 공식 링크는 직접 GET 요청에서 모두 `200`이었다. 이미지 열은 API가 반환한 URL로, 이미지 파일 다운로드 검사는 포함하지 않았다.

## 6단계 세 곡 검증 및 제출용 응답

곡명과 아티스트 문자열을 앞뒤 공백과 대소문자 차이를 제외하고 비교했다. 표의 항목은 제목에 라이브나 리믹스 표기가 없는 일치 결과다. 같은 제목과 아티스트를 가진 항목도 서로 다른 곡 ID로 등록되어 있으므로 그대로 기록했다. 앨범과 재생 시간이 같아도 실제 음원이 같은 녹음인지는 확인하지 않았다.

| 곡명 · 아티스트 | 곡 ID | 앨범 및 버전 구분 | 재생 시간(ms) | 앨범 이미지 | Apple Music |
|---|---:|---|---:|---|---|
| Dynamite · BTS | 1627575419 | Proof 수록 | 199293 | [URL](https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/f7/68/9c/f7689ce3-6d41-60cd-62d2-57a91ddf5b9d/196922067341_Cover.jpg/100x100bb.jpg) | [200](https://music.apple.com/us/album/dynamite/1627573936?i=1627575419&uo=4) |
| Dynamite · BTS | 1596532400 | BE 수록 | 199054 | [URL](https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/22/f3/8f/22f38fb9-1690-326a-d891-7aa946c2b06f/195497623273_Cover.jpg/100x100bb.jpg) | [200](https://music.apple.com/us/album/dynamite/1596532185?i=1596532400&uo=4) |
| Ditto · NewJeans | 1657231962 | Ditto - Single | 185507 | [URL](https://is1-ssl.mzstatic.com/image/thumb/Music112/v4/f6/29/42/f629426e-92fe-535c-cbe4-76e70850819b/196922287107_Cover.jpg/100x100bb.jpg) | [200](https://music.apple.com/us/album/ditto/1657231957?i=1657231962&uo=4) |
| Ditto · NewJeans | 1659513448 | NewJeans 'OMG' - Single 수록 | 185507 | [URL](https://is1-ssl.mzstatic.com/image/thumb/Music113/v4/48/96/08/4896085e-b550-cb0a-3e5b-1f203521cb82/196922265464_Cover.jpg/100x100bb.jpg) | [200](https://music.apple.com/us/album/ditto/1659513441?i=1659513448&uo=4) |
| Pink Venom · BLACKPINK | 1639174482 | Pink Venom - Single | 186964 | [URL](https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/72/48/88/72488832-558c-fcba-4aa0-03d88dc79eb3/22UMGIM87808.rgb.jpg/100x100bb.jpg) | [200](https://music.apple.com/us/album/pink-venom/1639174465?i=1639174482&uo=4) |
| Pink Venom · BLACKPINK | 1644440670 | BORN PINK 수록 · 컬렉션 ID 1644440668 | 186964 | [URL](https://is1-ssl.mzstatic.com/image/thumb/Music112/v4/94/b6/96/94b696c4-63be-8196-cae6-1f81be0a4cbe/22UM1IM01017.rgb.jpg/100x100bb.jpg) | [200](https://music.apple.com/us/album/pink-venom/1644440668?i=1644440670&uo=4) |
| Pink Venom · BLACKPINK | 1644431617 | BORN PINK 수록 · 컬렉션 ID 1644431615 | 186964 | [URL](https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/52/8e/5a/528e5a30-52b0-b68c-f184-635fcf15e6d7/22UM1IM01017.rgb.jpg/100x100bb.jpg) | [200](https://music.apple.com/us/album/pink-venom/1644431615?i=1644431617&uo=4) |

- **Dynamite** 검색에는 `Dynamite (Live)`와 `Dynamite (Holiday Remix)`도 포함됐다.
- **Ditto** 검색에는 `Ditto (250 Remix)`와 `Ditto (250 Remix) [Alternate]`도 포함됐다. kidu의 `NewJeans 'Ditto' (Remix)`는 아티스트가 달랐다.
- **Pink Venom** 검색에는 BLACKPINK의 다른 곡 `JUMP`와 Ron Rocker의 `Blackpink - Pink Venom`도 포함됐다.

### 실제 Flask JSON 응답 예시

`GET /api/music/search?q=BTS%20Dynamite`의 응답에서 `results` 배열에 포함된 `Proof` 수록곡 객체 한 개를 그대로 발췌했다. 전체 응답의 `country`는 `US`, `resultCount`는 `4`였다.

```json
{
  "artistName": "BTS",
  "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/f7/68/9c/f7689ce3-6d41-60cd-62d2-57a91ddf5b9d/196922067341_Cover.jpg/100x100bb.jpg",
  "collectionName": "Proof",
  "trackId": 1627575419,
  "trackName": "Dynamite",
  "trackTimeMillis": 199293,
  "trackViewUrl": "https://music.apple.com/us/album/dynamite/1627573936?i=1627575419&uo=4"
}
```
