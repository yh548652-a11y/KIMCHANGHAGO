import os
import json
import socket
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request


ALLOWED_CATEGORIES = {"movie", "series", "music"}

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
WIKIPEDIA_API_URL = "https://ko.wikipedia.org/w/api.php"
ITUNES_CATEGORY_PARAMS = {
    "movie": {"media": "movie", "entity": "movie"},
    "series": {"media": "tvShow", "entity": "tvSeason"},
    "music": {"media": "music", "entity": "song"},
}


class ExternalApiError(Exception):
    """외부 콘텐츠 API가 정상 응답하지 못했을 때 사용하는 오류입니다."""


def utc_now_iso() -> str:
    """외부 정보를 확인한 시각을 ISO 8601 UTC 형식으로 반환합니다."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _first_value(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_itunes_item(item: dict, category: str) -> dict:
    """iTunes 응답을 프론트엔드가 사용하는 공통 작품 형식으로 바꿉니다."""
    item_id = _first_value(item, "trackId", "collectionId", "artistId")
    title = _first_value(item, "trackName", "collectionName", "artistName")
    price = _first_value(item, "trackPrice", "collectionPrice")

    return {
        "id": f"itunes-{item_id}" if item_id is not None else None,
        "category": category,
        "title": title,
        "creator": item.get("artistName"),
        "image_url": _first_value(item, "artworkUrl100", "artworkUrl60"),
        "source_url": _first_value(item, "trackViewUrl", "collectionViewUrl", "artistViewUrl"),
        "genre": item.get("primaryGenreName"),
        "duration_ms": item.get("trackTimeMillis"),
        "price_amount": price,
        "currency": item.get("currency"),
        "country": item.get("country"),
        "source_name": "Apple iTunes Search API",
        "data_status": "external_api",
        "verification_status": "verified_external",
        "checked_at": utc_now_iso(),
    }


def fetch_itunes_items(category: str, query: str, limit: int = 6) -> list[dict]:
    """키가 필요 없는 Apple 검색 API에서 실제 콘텐츠 정보를 조회합니다."""
    params = {
        "term": query,
        "country": os.getenv("ITUNES_COUNTRY", "KR"),
        "lang": "ko_kr",
        "limit": limit,
        **ITUNES_CATEGORY_PARAMS[category],
    }
    request_url = f"{ITUNES_SEARCH_URL}?{urlencode(params)}"
    request_object = Request(
        request_url,
        headers={"User-Agent": "TasteRadiusFeasibilityCheck/1.0"},
    )

    try:
        timeout = float(os.getenv("EXTERNAL_API_TIMEOUT", "8"))
        with urlopen(request_object, timeout=timeout) as response:
            payload = json.load(response)
    except (HTTPError, URLError, socket.timeout, TimeoutError, ValueError, json.JSONDecodeError) as error:
        raise ExternalApiError("외부 콘텐츠 API 응답을 받지 못했습니다.") from error

    results = payload.get("results", [])
    if not results and params["country"] != "US":
        # 한국 Store에 검색 결과가 없는 작품은 미국 Store에서 한 번만 보조 조회합니다.
        params["country"] = "US"
        fallback_request = Request(
            f"{ITUNES_SEARCH_URL}?{urlencode(params)}",
            headers={"User-Agent": "TasteRadiusFeasibilityCheck/1.0"},
        )
        try:
            with urlopen(fallback_request, timeout=timeout) as response:
                payload = json.load(response)
            results = payload.get("results", [])
        except (HTTPError, URLError, socket.timeout, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise ExternalApiError("외부 콘텐츠 API 보조 응답을 받지 못했습니다.") from error
    normalized_items = [normalize_itunes_item(item, category) for item in results]
    return [item for item in normalized_items if item["id"] and item["title"]]


def fetch_wikipedia_movies(query: str, limit: int = 6) -> list[dict]:
    """영화 검색 결과가 없을 때 한국어 Wikipedia의 실제 문서를 보조 조회합니다."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f'"{query}" 영화',
        "gsrlimit": limit,
        "prop": "pageimages|extracts",
        "piprop": "thumbnail",
        "pithumbsize": 600,
        "exintro": 1,
        "explaintext": 1,
        "format": "json",
        "origin": "*",
    }
    request_url = f"{WIKIPEDIA_API_URL}?{urlencode(params)}"
    request_object = Request(
        request_url,
        headers={"User-Agent": "TasteRadiusFeasibilityCheck/1.0"},
    )

    try:
        timeout = float(os.getenv("EXTERNAL_API_TIMEOUT", "8"))
        with urlopen(request_object, timeout=timeout) as response:
            payload = json.load(response)
    except (HTTPError, URLError, socket.timeout, TimeoutError, ValueError, json.JSONDecodeError) as error:
        raise ExternalApiError("영화 보조 API 응답을 받지 못했습니다.") from error

    pages = list(payload.get("query", {}).get("pages", {}).values())
    pages.sort(
        key=lambda page: (
            "(영화)" not in page.get("title", ""),
            "영화" not in page.get("extract", ""),
        )
    )

    items = []
    for page in pages:
        title = page.get("title")
        page_id = page.get("pageid")
        extract = page.get("extract", "")
        normalized_title = title.replace(" (영화)", "").strip() if title else ""
        if (
            not title
            or not page_id
            or normalized_title.casefold() != query.strip().casefold()
            or "영화" not in f"{title} {extract}"
        ):
            continue
        items.append(
            {
                "id": f"wikipedia-{page_id}",
                "category": "movie",
                "title": title,
                "creator": None,
                "image_url": page.get("thumbnail", {}).get("source"),
                "source_url": f"https://ko.wikipedia.org/?curid={page_id}",
                "genre": None,
                "duration_ms": None,
                "price_amount": None,
                "currency": None,
                "country": "KR",
                "summary": extract[:260] if extract else None,
                "source_name": "한국어 Wikipedia API",
                "data_status": "external_api",
                "verification_status": "verified_external",
                "checked_at": utc_now_iso(),
            }
        )
    return items


def fetch_external_items(category: str, query: str, limit: int = 6) -> list[dict]:
    items = fetch_itunes_items(category, query, limit)
    if category == "movie" and not items:
        return fetch_wikipedia_movies(query, limit)
    return items


def error_response(code: str, message: str, status_code: int):
    return jsonify({"error": {"code": code, "message": message}}), status_code


def create_app() -> Flask:
    app = Flask(__name__)

    @app.after_request
    def add_local_cors_headers(response):
        """로컬 React 개발 서버와 연결하기 위한 최소 CORS 설정입니다."""
        configured_origin = os.getenv("FRONTEND_ORIGIN")
        allowed_origins = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
        if configured_origin:
            allowed_origins.add(configured_origin)

        request_origin = request.headers.get("Origin")
        if request_origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = request_origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "taste-radius-api",
                "data_mode": "external_api",
                "external_sources": ["Apple iTunes Search API", "한국어 Wikipedia API"],
            }
        )

    @app.get("/api/search")
    def search():
        category = request.args.get("category", "").strip().lower()
        query = request.args.get("q", "").strip()

        if not category:
            return error_response(
                "MISSING_CATEGORY",
                "category 값이 필요합니다. 예: movie, series, music",
                400,
            )

        if category not in ALLOWED_CATEGORIES:
            return error_response(
                "INVALID_CATEGORY",
                "현재 서버는 movie, series, music만 지원합니다.",
                400,
            )

        if not query:
            return error_response(
                "MISSING_QUERY",
                "검색어 q가 필요합니다.",
                400,
            )

        try:
            items = fetch_external_items(category, query)
        except ExternalApiError as error:
            return error_response("EXTERNAL_API_ERROR", str(error), 502)

        source_names = sorted({item["source_name"] for item in items})
        return jsonify(
            {
                "category": category,
                "query": query,
                "items": items,
                "meta": {
                    "count": len(items),
                    "data_mode": "external_api",
                    "checked_at": utc_now_iso(),
                    "source_names": source_names,
                    "notice": (
                        "외부 API의 실제 검색 결과입니다. Apple 가격은 제공되는 경우의 "
                        "Store 구매 가격이며 OTT·음악 구독료가 아닙니다. "
                        "Wikipedia 결과는 영화 보조 정보이며 가격·평점 출처가 아닙니다."
                    ),
                },
            }
        )

    @app.errorhandler(404)
    def not_found(_error):
        return error_response("NOT_FOUND", "요청한 엔드포인트가 없습니다.", 404)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
