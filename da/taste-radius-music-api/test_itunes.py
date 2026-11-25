import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


SEARCH_URL = "https://itunes.apple.com/search"
SEARCH_PARAMS = {
    "country": "US",
    "media": "music",
    "entity": "song",
    "limit": 5,
}
SONGS = (
    ("BTS", "Dynamite"),
    ("NewJeans", "Ditto"),
    ("BLACKPINK", "Pink Venom"),
)
OUTPUT_FIELDS = {
    "trackId": "곡 ID",
    "trackName": "곡명",
    "artistName": "아티스트",
    "collectionName": "앨범명",
    "artworkUrl100": "앨범 이미지 URL",
    "trackTimeMillis": "재생 시간(ms)",
    "trackViewUrl": "공식 Apple Music / 스토어 링크",
}


def matches(value, expected):
    return isinstance(value, str) and value.strip().casefold() == expected.casefold()


def build_search_url(term):
    params = {"term": term, **SEARCH_PARAMS}
    return f"{SEARCH_URL}?{urlencode(params)}"


def request_itunes(url):
    with urlopen(url, timeout=15) as response:
        return response.status, json.load(response)


def extract_results(payload):
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
        raise ValueError("iTunes 응답에서 올바른 검색 결과 목록을 찾을 수 없습니다.")
    return results


def track_details(track):
    details = {field: track.get(field) for field in OUTPUT_FIELDS}
    if not details["artworkUrl100"]:
        details["artworkUrl100"] = None
        if track.get("artworkUrl60"):
            details["artworkUrl60"] = track["artworkUrl60"]
    return details


def search_song(expected_artist, expected_title):
    print(f"\n=== {expected_artist} - {expected_title} ===")
    term = f"{expected_artist} {expected_title}"
    url = build_search_url(term)
    print(f"iTunes 요청 URL: {url}")
    try:
        status, payload = request_itunes(url)
        print(f"HTTP 상태 코드: {status}")
    except HTTPError as error:
        print(f"HTTP 상태 코드: {error.code}")
        print("iTunes 서버가 검색 요청을 처리하지 못했습니다.")
        return 1
    except (URLError, TimeoutError, OSError) as error:
        print(f"iTunes 검색 요청 중 연결 오류가 발생했습니다: {error}")
        return 1
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("iTunes 응답을 검색 결과 데이터로 읽을 수 없습니다.")
        return 1

    if not isinstance(payload, dict):
        print("iTunes 응답이 예상한 형식이 아닙니다.")
        return 1

    result_count = payload.get("resultCount")
    if type(result_count) is int and result_count >= 0:
        print(f"API 응답의 resultCount: {result_count}")
    else:
        print("API 응답에서 유효한 resultCount를 확인할 수 없습니다.")

    try:
        results = extract_results(payload)
    except ValueError as error:
        print(error)
        return 1

    if type(result_count) is int and result_count >= 0 and result_count != len(results):
        print(f"API의 resultCount와 실제 결과 목록 개수({len(results)}개)가 다릅니다.")

    if not results:
        print(f"미국 스토어에서 '{term}'의 검색 결과가 0개입니다.")
        return 1

    print("\nAPI 검색 결과 (최대 5개)")
    exact_matches = []
    for index, result in enumerate(results[:SEARCH_PARAMS["limit"]], start=1):
        title = result.get("trackName")
        artist = result.get("artistName")
        album = result.get("collectionName")
        title_matches = matches(title, expected_title)
        artist_matches = matches(artist, expected_artist)
        if title_matches and artist_matches:
            label = "곡명·아티스트 일치"
            exact_matches.append(result)
        elif title_matches:
            label = "곡명 일치 / 아티스트 불일치"
        elif artist_matches:
            label = "아티스트 일치 / 곡명 불일치 (다른 버전 표기 포함)"
        else:
            label = "곡명·아티스트 불일치"
        print(
            f"{index}. [{label}] {title or '곡명 없음'} / "
            f"{artist or '아티스트 없음'} / 앨범: {album or '응답에 없음'}"
        )

    if not exact_matches:
        print("검색 결과는 있지만 곡명과 아티스트가 모두 일치하는 곡이 없습니다.")
        return 1

    for index, result in enumerate(exact_matches, start=1):
        print(f"\n일치 결과 {index}/{len(exact_matches)}")
        details = track_details(result)
        for field, label in OUTPUT_FIELDS.items():
            value = details[field]
            if field == "artworkUrl100" and not value:
                value = details.get("artworkUrl60")
            if value is None or value == "":
                print(f"{label}: 응답에 없음")
            else:
                print(f"{label}: {value}")

    return 0


def main():
    failures = 0
    for artist, title in SONGS:
        failures += search_song(artist, title)

    print(f"\n검증 요약: 성공 {len(SONGS) - failures}곡 / 실패 {failures}곡")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
