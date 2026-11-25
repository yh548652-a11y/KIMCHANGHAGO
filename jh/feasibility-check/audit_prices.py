"""여러 검색 결과의 관련성과 Apple 공식 Lookup 가격을 교차 검증합니다."""

import json
import math
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app import fetch_external_items


TEST_CASES = [
    ("movie", "기생충", ["기생충", "parasite"]),
    ("movie", "Inception", ["inception"]),
    ("movie", "Oppenheimer", ["oppenheimer"]),
    ("series", "Breaking Bad", ["breaking bad"]),
    ("series", "Game of Thrones", ["game of thrones"]),
    ("series", "Sherlock", ["sherlock"]),
    ("music", "BTS", ["bts"]),
    ("music", "Adele", ["adele"]),
    ("music", "아이유", ["아이유", "iu"]),
    ("music", "Taylor Swift", ["taylor swift"]),
]


def lookup_apple_item(item: dict) -> dict | None:
    """검색 결과 ID를 Apple Lookup API에서 다시 조회합니다."""
    if item.get("source_name") != "Apple iTunes Search API":
        return None

    item_id = str(item["id"]).removeprefix("itunes-")
    storefront = "KR" if item.get("currency") == "KRW" else "US"
    url = "https://itunes.apple.com/lookup?" + urlencode(
        {"id": item_id, "country": storefront}
    )
    request = Request(url, headers={"User-Agent": "TasteRadiusPriceAudit/1.0"})
    with urlopen(request, timeout=10) as response:
        results = json.load(response).get("results", [])

    for result in results:
        ids = {str(result.get("trackId")), str(result.get("collectionId"))}
        if item_id in ids:
            return result
    return None


def first_price(raw_item: dict | None):
    if not raw_item:
        return None
    for key in ("trackPrice", "collectionPrice"):
        value = raw_item.get(key)
        if value is not None:
            return value
    return None


def is_relevant(item: dict, expected_terms: list[str]) -> bool:
    text = " ".join(
        str(item.get(key) or "") for key in ("title", "creator", "genre")
    ).casefold()
    return any(term.casefold() in text for term in expected_terms)


def audit_case(category: str, query: str, expected_terms: list[str]) -> dict:
    items = fetch_external_items(category, query, limit=6)
    if not items:
        return {
            "category": category,
            "query": query,
            "result": "NO_RESULT",
        }

    item = items[0]
    lookup = lookup_apple_item(item)
    displayed_price = item.get("price_amount")
    lookup_price = first_price(lookup)
    displayed_currency = item.get("currency")
    lookup_currency = lookup.get("currency") if lookup else None

    if item.get("source_name") != "Apple iTunes Search API":
        price_check = "NOT_PROVIDED_BY_SOURCE" if displayed_price is None else "UNEXPECTED_PRICE"
    elif displayed_price is None and lookup_price is None:
        price_check = "NOT_PROVIDED"
    elif displayed_price is None or lookup_price is None:
        price_check = "MISMATCH"
    else:
        same_value = math.isclose(float(displayed_price), float(lookup_price), abs_tol=0.001)
        price_check = "MATCH" if same_value and displayed_currency == lookup_currency else "MISMATCH"

    return {
        "category": category,
        "query": query,
        "result": "PASS" if is_relevant(item, expected_terms) else "IRRELEVANT_TOP_RESULT",
        "title": item.get("title"),
        "creator": item.get("creator"),
        "source": item.get("source_name"),
        "displayed_price": displayed_price,
        "displayed_currency": displayed_currency,
        "lookup_price": lookup_price,
        "lookup_currency": lookup_currency,
        "price_check": price_check,
        "source_url": item.get("source_url"),
        "checked_at": item.get("checked_at"),
    }


def main():
    results = [audit_case(*case) for case in TEST_CASES]
    summary = {
        "total_queries": len(results),
        "relevant_top_results": sum(row.get("result") == "PASS" for row in results),
        "irrelevant_top_results": sum(
            row.get("result") == "IRRELEVANT_TOP_RESULT" for row in results
        ),
        "no_results": sum(row.get("result") == "NO_RESULT" for row in results),
        "price_matches": sum(row.get("price_check") == "MATCH" for row in results),
        "price_mismatches": sum(row.get("price_check") == "MISMATCH" for row in results),
        "prices_not_provided": sum(
            row.get("price_check") in {"NOT_PROVIDED", "NOT_PROVIDED_BY_SOURCE"}
            for row in results
        ),
    }
    print(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
