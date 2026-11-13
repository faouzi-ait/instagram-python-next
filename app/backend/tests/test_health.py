import os
import unittest

from fastapi.testclient import TestClient

os.environ["AUTH_ALLOWED_ORIGINS"] = "https://example.com"
os.environ["DATABASE_URL"] = "sqlite://"

from main import app

class HealthRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_allows_requests_from_configured_origin(self) -> None:
        response = self.client.get(
            "/api/health",
            headers={"Origin": "https://example.com"},
        )

        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "https://example.com",
        )

if __name__ == "__main__":
    unittest.main()