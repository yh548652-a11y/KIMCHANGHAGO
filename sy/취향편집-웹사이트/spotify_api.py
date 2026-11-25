"""Spotify music search for the existing Flask/React integration."""

import base64
import json
import os
import re
import time
import unicodedata
from pathlib import Path
import sys
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from flask import jsonify, request
from tmdb_api import register_tmdb

load_dotenv(Path(__file__).with_name(".env"))

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "jh" / "feasibility-check"))
from app import ExternalApiError, create_app, fetch_external_items, utc_now_iso
from tmdb_api import credentials as tmdb_credentials


class SpotifyError(Exception):
    def __init__(self, code, message, status, retry_after=None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.retry_after = retry_after


class SpotifySearch:
    def __init__(self):
        self.lock = Lock()
        self.token = None
        self.expires_at = 0

    @staticmethod
    def read_json(req):
        try:
            with urlopen(req, timeout=5) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 429:
                raise SpotifyError("SPOTIFY_RATE_LIMIT", "Spotify 호출 한도에 도달했어요. 잠시 후 다시 검색해 주세요.", 429, error.headers.get("Retry-After")) from error
            if error.code in (400, 401, 403) and ("/api/token" in req.full_url or error.code != 400):
                raise SpotifyError("SPOTIFY_ACCESS_ERROR", "Spotify 앱 인증 정보 또는 검색 권한을 확인해 주세요.", 502) from error
            raise SpotifyError("SPOTIFY_API_ERROR", "Spotify 검색 요청에 실패했어요.", 502) from error
        except (URLError, TimeoutError, ValueError) as error:
            raise SpotifyError("SPOTIFY_API_ERROR", "Spotify 응답을 받지 못했어요.", 502) from error

    def access_token(self):
        client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
        secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
        if not client_id or not secret:
            raise SpotifyError("SPOTIFY_NOT_CONFIGURED", "음악 검색을 사용하려면 서버에 Spotify 인증 정보를 설정해 주세요.", 503)
        with self.lock:
            if self.token and time.monotonic() < self.expires_at:
                return self.token
            auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
            data = self.read_json(Request(
                "https://accounts.spotify.com/api/token",
                data=b"grant_type=client_credentials",
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
            ))
            token = data.get("access_token") if isinstance(data, dict) else None
            if not isinstance(token, str) or not token:
                raise SpotifyError("SPOTIFY_ACCESS_ERROR", "Spotify 인증 응답을 확인할 수 없어요.", 502)
            self.token = token
            self.expires_at = time.monotonic() + max(0, int(data.get("expires_in") or 0) - 30)
            return token

    def search(self, query):
        words = normalized_words(query)
        if not words:
            return []
        market = os.getenv("SPOTIFY_MARKET", "US").strip().upper() or "US"
        params = urlencode({"q": " ".join(words), "type": "track", "limit": 10, "market": market})
        data = self.read_json(Request(
            f"https://api.spotify.com/v1/search?{params}",
            headers={"Authorization": f"Bearer {self.access_token()}"},
        ))
        tracks = (data.get("tracks") or {}).get("items") if isinstance(data, dict) else None
        if not isinstance(tracks, list):
            raise SpotifyError("SPOTIFY_API_ERROR", "Spotify 검색 응답 형식을 확인할 수 없어요.", 502)

        matches = []
        seen = set()
        checked_at = utc_now_iso()
        for track in tracks:
            if not isinstance(track, dict) or not track.get("id") or not track.get("name"):
                continue
            artist = ", ".join(entry["name"] for entry in track.get("artists", []) if entry.get("name"))
            title_words = normalized_words(track["name"])
            searchable = set(title_words + normalized_words(artist))
            if track["id"] in seen or not set(words).issubset(searchable):
                continue
            seen.add(track["id"])
            matches.append((title_words == words or (
                bool(title_words) and title_words == words[:len(title_words)]
                and set(words[len(title_words):]).issubset(normalized_words(artist))
            ), normalize_track(track, artist, market, checked_at)))
        matches.sort(key=lambda match: not match[0])
        return [item for _, item in matches]


def normalized_words(value):
    aliases = {"방탄소년단": "bts", "다이너마이트": "dynamite"}
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", value).casefold())
    return [aliases.get(word, word) for word in words]


def normalize_track(track, artist, market, checked_at):
    album = track.get("album") or {}
    images = album.get("images") or []
    return {
        "id": f"spotify-{track['id']}",
        "category": "music",
        "title": track["name"],
        "creator": artist or None,
        "album": album.get("name"),
        "image_url": next((image["url"] for image in images if image.get("url")), None),
        "duration_ms": track.get("duration_ms"),
        "release_date": album.get("release_date"),
        "source_url": (track.get("external_urls") or {}).get("spotify"),
        "source_name": "Spotify",
        "country": market,
        "checked_at": checked_at,
        "data_status": "external_api",
    }


app = create_app()
register_tmdb(app)
spotify = SpotifySearch()
legacy_health = app.view_functions["health"]


def integration_health():
    data = legacy_health().get_json()
    data["providers"] = {
        "tmdb_configured": any(tmdb_credentials()),
        "spotify_configured": bool(os.getenv("SPOTIFY_CLIENT_ID", "").strip() and os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()),
    }
    return jsonify(data)


app.view_functions["health"] = integration_health


@app.get("/api/music/search")
def search_music():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify(error={"code": "MISSING_QUERY", "message": "검색어를 입력해 주세요."}), 400
    try:
        items = spotify.search(query)
    except SpotifyError as error:
        if error.code != "SPOTIFY_NOT_CONFIGURED":
            headers = {"Retry-After": error.retry_after} if error.retry_after else {}
            return jsonify(error={"code": error.code, "message": str(error)}), error.status, headers
        try:
            items = fetch_external_items("music", query)
        except ExternalApiError:
            return jsonify(error={"code": "EXTERNAL_API_ERROR", "message": "Apple 음악 검색에 연결하지 못했어요."}), 502
        return jsonify(category="music", query=query, items=items, meta={"count": len(items), "provider": "apple"})
    return jsonify(category="music", query=query, items=items, meta={"count": len(items), "provider": "spotify"})


if __name__ == "__main__":
    app.run(host=os.getenv("FLASK_HOST", "127.0.0.1"), port=int(os.getenv("SPOTIFY_PORT", "5050")))
