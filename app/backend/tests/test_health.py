import unittest
from fastapi.testclient import TestClient
from main import app

# COMMENT TO COMMIT
class HealthRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_allows_requests_from_any_origin(self) -> None:
        response = self.client.get(
            "/api/health",
            headers={"Origin": "https://example.com"},
        )

        self.assertEqual(response.headers["access-control-allow-origin"], "*")

if __name__ == "__main__":
    unittest.main()