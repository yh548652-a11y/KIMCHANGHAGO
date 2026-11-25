import re
import unicodedata

from flask import Flask, jsonify, render_template, request

from test_spotify import MARKET, get_access_token, load_credentials, search_tracks


app = Flask(__name__)
app.json.ensure_ascii = False


ARTIST_ALIASES = {
    ("bts",): ("방탄소년단",),
    ("blackpink",): ("블랙핑크",),
    ("iu",): ("아이유",),
    ("newjeans",): ("뉴진스",),
}

TRACK_ALIASES = {
    ("bts",): {("다이너마이트",): ("dynamite",)},
    ("iu",): {("좋은", "날"): ("good", "day")},
}


def search_tokens(value):
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return tuple(re.findall(r"[^\W_]+", normalized.replace("'", "").replace("’", "")))


def match_phrase(query, field):
    """Return 2 for an exact match and 1 for a contiguous word match."""
    if not query:
        return 0
    if query == field:
        return 2

    return int(any(
        field[start:start + len(query)] == query
        for start in range(len(field) - len(query) + 1)
    ))


def alternate_query(tokens):
    for artist, korean in ARTIST_ALIASES.items():
        if tokens == korean:
            return artist
        for split in range(1, len(tokens)):
            left, right = tokens[:split], tokens[split:]
            for name, title in ((left, right), (right, left)):
                if name not in (artist, korean):
                    continue
                translation = TRACK_ALIASES.get(artist, {}).get(title)
                if translation or name == korean:
                    return (translation or title) + artist
    return tokens


def track_relevance(query, track):
    title = search_tokens(track.get("name") or "")
    artists = {search_tokens(artist.get("name") or "") for artist in track.get("artists") or []}
    for english, korean in ARTIST_ALIASES.items():
        if english in artists or korean in artists:
            artists.update((english, korean))

    words = set(title)
    for artist in artists:
        words.update(artist)
    if not query or not words.issuperset(query):
        return 0

    score = max(1, 2 * match_phrase(query, title))
    for artist in artists:
        score = max(score, match_phrase(query, artist))
        for split in range(1, len(query)):
            left, right = query[:split], query[split:]
            for title_query, artist_query in ((left, right), (right, left)):
                title_match = match_phrase(title_query, title)
                if title_match and artist_query == artist:
                    score = max(score, 4 + title_match)
    return score


@app.get("/")
def index():
    return render_template("index.html", country=MARKET)


def track_details(track):
    album = track.get("album") or {}
    images = album.get("images") or []
    artists = track.get("artists") or []
    return {
        "trackId": track.get("id"),
        "trackName": track.get("name"),
        "artistName": ", ".join(artist["name"] for artist in artists if artist.get("name")),
        "collectionName": album.get("name"),
        "artworkUrl100": images[0].get("url") if images else None,
        "trackTimeMillis": track.get("duration_ms"),
        "trackViewUrl": (track.get("external_urls") or {}).get("spotify"),
    }


@app.get("/api/music/search")
def search_music():
    query = request.args.get("q", "").strip()
    response_data = {"query": query, "country": MARKET}

    if not query:
        return jsonify(**response_data, error="q에 곡명이나 아티스트를 입력해 주세요."), 400

    tokens = search_tokens(query)
    alternative = alternate_query(tokens)

    client_id, client_secret = load_credentials()
    if not client_id or not client_secret:
        return jsonify(**response_data, error="서버의 Spotify 연결 설정을 확인해 주세요."), 503

    token = get_access_token(client_id, client_secret)
    if token is None:
        return jsonify(**response_data, error="Spotify에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."), 502

    tracks = search_tracks(token, query if alternative == tokens else " ".join(alternative))
    if tracks is None:
        return jsonify(**response_data, error="Spotify 검색에 실패했습니다. 잠시 후 다시 시도해 주세요."), 502

    ranked_tracks = [
        (max(track_relevance(tokens, track), track_relevance(alternative, track)), track)
        for track in tracks
    ]
    ranked_tracks.sort(key=lambda candidate: candidate[0], reverse=True)
    # Keep exact full-title matches and require an artist match for looser
    # candidates when the search identifies a title and artist together.
    threshold = 4 if ranked_tracks and ranked_tracks[0][0] > 4 else 1
    results = [track_details(track) for score, track in ranked_tracks if score >= threshold]
    response_data.update(resultCount=len(results), results=results)
    if not results:
        response_data["message"] = "검색 결과가 없습니다."

    return jsonify(response_data)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
