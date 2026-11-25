"""TMDB movie and TV search, detail and Korean availability."""

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request

media = Blueprint("tmdb_media", __name__)
TYPES = {"movie": "movie", "tv": "series"}
PROVIDER_TYPES = {"flatrate": "구독", "rent": "대여", "buy": "구매", "free": "무료", "ads": "광고 포함"}


class TMDBError(Exception):
    def __init__(self, code, message, status, retry_after=None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.retry_after = retry_after


def credentials():
    return (os.getenv("TMDB_READ_ACCESS_TOKEN", "").strip(), os.getenv("TMDB_API_KEY", "").strip())


def fetch_tmdb(path, **params):
    token, key = credentials()
    if not (token or key):
        raise TMDBError("TMDB_NOT_CONFIGURED", "서버에 TMDB 인증 정보를 설정해 주세요.", 503)
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        params["api_key"] = key
    url = f"https://api.themoviedb.org/3/{path}?{urlencode(params)}"
    try:
        with urlopen(Request(url, headers=headers), timeout=8) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("Invalid upstream response")
        return data
    except HTTPError as error:
        if error.code in (401, 403):
            raise TMDBError("TMDB_AUTH_ERROR", "TMDB 인증 정보와 접근 권한을 확인해 주세요.", 502) from error
        if error.code == 404:
            raise TMDBError("TMDB_NOT_FOUND", "TMDB에서 작품 정보를 찾을 수 없어요.", 404) from error
        if error.code == 429:
            raise TMDBError("TMDB_RATE_LIMIT", "TMDB 호출 한도에 도달했어요. 잠시 후 다시 시도해 주세요.", 429, error.headers.get("Retry-After")) from error
        raise TMDBError("TMDB_API_ERROR", "TMDB가 정상 응답하지 않았어요.", 502) from error
    except (URLError, TimeoutError, ValueError) as error:
        raise TMDBError("TMDB_API_ERROR", "TMDB 응답을 받지 못했어요.", 502) from error


def language():
    return os.getenv("TMDB_LANGUAGE", "").strip() or "ko-KR"


def region():
    return os.getenv("TMDB_REGION", "").strip().upper() or "KR"


def image_url(path):
    return f"https://image.tmdb.org/t/p/w500{path}" if isinstance(path, str) and path.startswith("/") else None


def normalize(item, kind, checked_at):
    item_id = item["id"]
    title = item.get("title" if kind == "movie" else "name")
    original = item.get("original_title" if kind == "movie" else "original_name")
    return {
        "id": f"tmdb-{kind}-{item_id}",
        "category": TYPES[kind],
        "provider_id": item_id,
        "title": title or original,
        "original_title": original,
        "description": item.get("overview") or None,
        "image_url": image_url(item.get("poster_path")),
        "release_date": item.get("release_date" if kind == "movie" else "first_air_date") or None,
        "rating": item.get("vote_average") if item.get("vote_count") else None,
        "rating_count": item.get("vote_count"),
        "genres": [genre["name"] for genre in item.get("genres", []) if genre.get("name")],
        "runtime_minutes": item.get("runtime"),
        "season_count": item.get("number_of_seasons"),
        "source_name": "TMDB",
        "source_url": f"https://www.themoviedb.org/{kind}/{item_id}",
        "checked_at": checked_at,
        "data_status": "external_api",
    }


def checked_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def search(kind, query, page):
    params = {"query": query, "language": language(), "page": page, "include_adult": "false"}
    if kind == "movie":
        params["region"] = region()
    data = fetch_tmdb(f"search/{kind}", **params)
    results = data.get("results")
    if not isinstance(results, list):
        raise TMDBError("TMDB_API_ERROR", "TMDB 검색 응답 형식을 확인할 수 없어요.", 502)
    checked_at = checked_now()
    items = [normalize(item, kind, checked_at) for item in results if isinstance(item, dict) and item.get("id")]
    return jsonify(category=TYPES[kind], query=query, items=items, meta={
        "count": len(items), "page": data.get("page", page),
        "total_pages": data.get("total_pages"), "checked_at": checked_at,
    })


@media.errorhandler(TMDBError)
def tmdb_error(error):
    headers = {"Retry-After": error.retry_after} if error.retry_after else {}
    return jsonify(error={"code": error.code, "message": str(error)}), error.status, headers


@media.get("/api/media/search")
def search_media():
    kind = request.args.get("type", "").strip().lower()
    query = request.args.get("query", "").strip()
    page = request.args.get("page", "1")
    if kind not in TYPES or not query or not page.isascii() or not page.isdecimal() or len(page) > 3 or not 1 <= int(page) <= 500:
        raise TMDBError("INVALID_SEARCH", "영화 또는 드라마 유형, 검색어, 1~500 사이의 페이지를 입력해 주세요.", 400)
    return search(kind, query, int(page))


@media.get("/api/media/<any(movie,tv):kind>/<int:item_id>")
def media_detail(kind, item_id):
    item = fetch_tmdb(f"{kind}/{item_id}", language=language())
    if item.get("id") != item_id:
        raise TMDBError("TMDB_API_ERROR", "TMDB 상세 응답 형식을 확인할 수 없어요.", 502)
    return jsonify(item=normalize(item, kind, checked_now()))


@media.get("/api/media/<any(movie,tv):kind>/<int:item_id>/providers")
def media_providers(kind, item_id):
    data = fetch_tmdb(f"{kind}/{item_id}/watch/providers")
    country = region()
    local = (data.get("results") or {}).get(country) or {}
    offers = [
        {"name": provider["provider_name"], "type": key, "label": label}
        for key, label in PROVIDER_TYPES.items()
        for provider in local.get(key, [])
        if provider.get("provider_name")
    ]
    return jsonify(region=country, offers=offers, source_name="JustWatch", source_url=local.get("link"), checked_at=checked_now())


def register_tmdb(app):
    app.register_blueprint(media)
    legacy_search = app.view_functions["search"]

    def integrated_search():
        kind = {"movie": "movie", "series": "tv"}.get(request.args.get("category", "").strip().lower())
        query = request.args.get("q", "").strip()
        if not kind or not query or not any(credentials()):
            return legacy_search()
        try:
            return search(kind, query, 1)
        except TMDBError as error:
            return tmdb_error(error)

    app.view_functions["search"] = integrated_search
