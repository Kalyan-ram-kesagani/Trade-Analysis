"""
Automated Test Suite for AI Layer & New API Endpoints
Verifies:
- AI configuration status endpoint
- Graceful degradation when AI is not configured
- Structured responses matching Pydantic schemas
- Journal creation endpoint
- Strategy proposals lifecycle
- AI audit logs retrieval
"""

import sys
import unittest
from pathlib import Path

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from starlette.testclient import TestClient
from app.main import app


class TestAILayer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_endpoint(self):
        """Verify standard health endpoint remains operational."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "online")
        self.assertEqual(data.get("database"), "connected")

    def test_02_ai_status_endpoint(self):
        """Verify AI status endpoint returns provider/model configuration."""
        response = self.client.get("/api/ai/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("configured", data)
        self.assertIn("provider", data)
        self.assertIn("model", data)
        self.assertIn("model_display", data)

    def test_03_ai_analyze_endpoint(self):
        """Verify AI performance analysis returns typed schema with graceful degradation."""
        response = self.client.post(
            "/api/ai/analyze",
            json={"account_id": "00000000-0000-0000-0000-000000000000"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("account_id", data)
        self.assertIn("overall_market_regime", data)
        self.assertIn("overall_trend", data)
        self.assertIn("risk_status", data)
        self.assertIn("observations", data)
        self.assertIn("ai_disclaimer", data)

    def test_04_ai_journal_endpoint(self):
        """Verify AI journal generation returns typed schema with graceful degradation."""
        response = self.client.post(
            "/api/ai/journal",
            json={
                "account_id": "00000000-0000-0000-0000-000000000000",
                "trade_id": "00000000-0000-0000-0000-000000000000"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("trade_id", data)
        self.assertIn("summary", data)
        self.assertIn("lessons", data)
        self.assertIn("ai_disclaimer", data)

    def test_05_ai_strategy_analyze_endpoint(self):
        """Verify AI strategy analysis endpoint returns typed schema."""
        response = self.client.post(
            "/api/ai/strategy/analyze",
            json={
                "strategy_id": "00000000-0000-0000-0000-000000000000"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("strategy_id", data)
        self.assertIn("performance_summary", data)
        self.assertIn("strengths", data)
        self.assertIn("weaknesses", data)
        self.assertIn("ai_disclaimer", data)

    def test_06_ai_strategy_propose_endpoint(self):
        """Verify AI strategy proposal endpoint returns typed proposal schema."""
        response = self.client.post(
            "/api/ai/strategy/propose",
            json={
                "strategy_id": "00000000-0000-0000-0000-000000000000",
                "focus_area": "General Risk & Drawdown"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("strategy_id", data)
        self.assertIn("identified_issue", data)
        self.assertIn("hypothesis", data)
        self.assertIn("proposed_change", data)
        self.assertIn("validation_required", data)
        self.assertTrue(data.get("validation_required"))

    def test_07_strategy_proposals_list(self):
        """Verify listing strategy proposals."""
        response = self.client.get("/api/ai/strategy/proposals")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("proposals", data)
        self.assertIsInstance(data["proposals"], list)

    def test_08_ai_audit_logs(self):
        """Verify retrieving AI audit logs."""
        response = self.client.get("/api/ai/audit")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("audit_logs", data)
        self.assertIsInstance(data["audit_logs"], list)

    def test_09_equity_curve_endpoint(self):
        """Verify equity curve calculation endpoint."""
        response = self.client.get("/api/equity-curve")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("equity_curve", data)
        self.assertIsInstance(data["equity_curve"], list)
        self.assertGreater(len(data["equity_curve"]), 0)

    def test_10_positions_endpoint(self):
        """Verify open positions retrieval."""
        response = self.client.get("/api/positions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("positions", data)


if __name__ == "__main__":
    unittest.main()

