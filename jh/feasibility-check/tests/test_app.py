import unittest
from unittest.mock import patch

from app import create_app, is_relevant_item, normalize_itunes_item


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.get_json()["data_mode"], "external_api")

    @patch("app.fetch_external_items")
    def test_search_returns_normalized_external_data(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "id": "itunes-1",
                "category": "movie",
                "title": "테스트 영화",
                "source_name": "Apple iTunes Search API",
                "data_status": "external_api",
                "verification_status": "verified_external",
                "checked_at": "2026-11-25T00:00:00+00:00",
            }
        ]
        response = self.client.get("/api/search?category=movie&q=test")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["meta"]["data_mode"], "external_api")
        self.assertEqual(body["items"][0]["data_status"], "external_api")
        self.assertEqual(body["items"][0]["verification_status"], "verified_external")
        self.assertIn("checked_at", body["meta"])
        mock_fetch.assert_called_once_with("movie", "test")

    @patch("app.fetch_external_items")
    def test_search_allows_empty_external_results(self, mock_fetch):
        mock_fetch.return_value = []
        response = self.client.get("/api/search?category=music&q=no-result")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"], [])

    @patch("app.fetch_external_items")
    def test_search_reports_external_api_failure(self, mock_fetch):
        from app import ExternalApiError

        mock_fetch.side_effect = ExternalApiError("외부 콘텐츠 API 응답을 받지 못했습니다.")
        response = self.client.get("/api/search?category=series&q=test")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"]["code"], "EXTERNAL_API_ERROR")

    def test_search_rejects_missing_query(self):
        response = self.client.get("/api/search?category=movie")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "MISSING_QUERY")

    def test_search_rejects_invalid_category(self):
        response = self.client.get("/api/search?category=book&q=test")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_CATEGORY")

    def test_cors_allows_local_vite_origin(self):
        response = self.client.get(
            "/api/health",
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"],
            "http://127.0.0.1:5173",
        )

    def test_relevance_filter_rejects_different_series(self):
        item = {"title": "Elementary, Season 2", "creator": "Elementary"}
        self.assertFalse(is_relevant_item(item, "Sherlock"))

    def test_normalized_apple_price_is_marked_as_store_purchase(self):
        item = normalize_itunes_item(
            {
                "trackId": 1,
                "trackName": "테스트 곡",
                "artistName": "테스트 가수",
                "trackPrice": 1.29,
                "currency": "USD",
            },
            "music",
        )
        self.assertEqual(item["price_type"], "store_purchase")


if __name__ == "__main__":
    unittest.main()
