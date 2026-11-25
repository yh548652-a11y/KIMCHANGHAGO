import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from test_itunes import SONGS, matches


TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
MARKET = "US"
LIMIT = 10


def request_json(request, action):
    try:
        with urlopen(request, timeout=15) as response:
            status = response.status
            print(f"{action} HTTP {status}")
            data = json.load(response)
    except HTTPError as error:
        advice = {
            400: "앱 자격 증명 또는 검색 요청 설정을 확인하세요.",
            401: "앱 자격 증명을 확인한 뒤 다시 실행해 새 토큰을 발급받으세요.",
            403: "앱 소유자의 Premium 상태와 개발자 대시보드의 앱 접근 권한을 확인하세요.",
            429: "잠시 기다리거나 개발자 대시보드에서 계정의 사용량 한도를 확인하세요.",
        }.get(error.code, "잠시 후 다시 시도하고 문제가 계속되면 Spotify 서비스 상태를 확인하세요.")
        if error.code == 429:
            retry_after = error.headers.get("Retry-After", "")
            if retry_after.isascii() and retry_after.isdecimal():
                advice = f"최소 {retry_after}초 후 다시 시도하세요."
        print(f"{action} 실패 (HTTP {error.code}). {advice}")
        error.close()
        return None
    except OSError:
        print(f"{action} 실패. HTTP 응답을 받지 못했습니다. 인터넷 연결과 방화벽을 확인하세요.")
        return None
    except ValueError:
        print(f"{action} 실패. Spotify 응답을 읽을 수 없습니다. 잠시 후 다시 시도하세요.")
        return None

    if not isinstance(data, dict):
        print(f"{action} 실패. 예상한 Spotify 응답 형식이 아닙니다. 앱 상태와 API 문서를 확인하세요.")
        return None
    return data


def get_access_token(client_id, client_secret):
    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    authorization = base64.b64encode(credentials).decode("ascii")
    request = Request(
        TOKEN_URL,
        data=urlencode({"grant_type": "client_credentials"}).encode("ascii"),
        headers={
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    data = request_json(request, "인증")
    if data is None:
        return None
    token = data.get("access_token")
    if not isinstance(token, str) or not token:
        print("인증 응답에 토큰이 없습니다. 대시보드에서 앱 상태를 확인하세요.")
        return None
    return token


def search_tracks(token, query):
    params = urlencode({"q": query, "type": "track", "market": MARKET, "limit": LIMIT})
    request = Request(f"{SEARCH_URL}?{params}", headers={"Authorization": f"Bearer {token}"})
    data = request_json(request, "검색")
    if data is None:
        return None

    tracks = data.get("tracks")
    items = tracks.get("items") if isinstance(tracks, dict) else None
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        print("검색 응답에 결과 목록이 없습니다. 잠시 후 다시 시도하거나 API 문서를 확인하세요.")
        return None
    return items[:LIMIT]


def load_credentials():
    load_dotenv(Path(__file__).with_name(".env"), override=True, interpolate=False)
    return (
        os.getenv("SPOTIFY_CLIENT_ID", "").strip(),
        os.getenv("SPOTIFY_CLIENT_SECRET", "").strip(),
    )


def search_song(token, artist, title):
    print(f"\n=== {artist} - {title} ===")
    items = search_tracks(token, f"track:{title} artist:{artist}")
    if items is None:
        return False
    if not items:
        print(f"{MARKET} 시장에서 검색 결과가 없습니다.")
        return False

    exact_count = 0
    for track in items[:LIMIT]:
        name = track.get("name") or ""
        artists = [entry["name"] for entry in track.get("artists", []) if entry.get("name")]
        same_title = matches(name, title)
        same_artist = any(matches(entry, artist) for entry in artists)
        normalized_name = name.strip().casefold()
        normalized_title = title.casefold()
        suffix = normalized_name[len(normalized_title):].lstrip()
        version_title = normalized_name.startswith(normalized_title) and suffix.startswith(
            ("(", "[", "-", "–", "—")
        )
        if same_title and same_artist:
            exact_count += 1
            label = "곡명·아티스트 일치"
        elif same_artist and version_title:
            label = "별도 버전 후보 (제목 표기 기준)"
        elif same_title:
            label = "동명이곡 (아티스트 불일치)"
        else:
            label = "곡명 또는 아티스트가 다른 후보"

        album = track.get("album") or {}
        images = album.get("images") or []
        link = (track.get("external_urls") or {}).get("spotify")
        print(f"[{label}] {name or '곡명 없음'} / {', '.join(artists) or '아티스트 없음'}")
        print(f"  곡 ID: {track.get('id') or '응답에 없음'}")
        print(f"  앨범명: {album.get('name') or '응답에 없음'}")
        print(f"  앨범 이미지 URL: {(images[0].get('url') if images else None) or '응답에 없음'}")
        print(f"  재생 시간(ms): {track.get('duration_ms', '응답에 없음')}")
        print(f"  Spotify 공식 링크: {link or '응답에 없음'}")

    print(f"곡명·아티스트 일치: {exact_count}개 / 반환: {len(items[:LIMIT])}개")
    if not exact_count:
        print("반환된 결과에서 제목과 아티스트가 모두 일치하는 곡을 찾지 못했습니다.")
    return exact_count > 0


def main():
    client_id, client_secret = load_credentials()
    if not client_id or not client_secret:
        print("프로젝트 루트의 .env에 SPOTIFY_CLIENT_ID와 SPOTIFY_CLIENT_SECRET을 설정하세요.")
        return 1

    token = get_access_token(client_id, client_secret)
    if not token:
        print("인증이 완료되지 않아 세 곡 검색을 진행하지 못했습니다.")
        return 1

    print(f"검증 시장: {MARKET} / 요청당 결과 최대 {LIMIT}개")
    successes = sum(search_song(token, artist, title) for artist, title in SONGS)
    print(f"\n검증 요약: 성공 {successes}곡 / 실패 {len(SONGS) - successes}곡")
    return int(successes != len(SONGS))


if __name__ == "__main__":
    raise SystemExit(main())
