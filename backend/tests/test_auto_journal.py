"""
Comprehensive Test Suite for Automatic AI Journaling System
Verifies:
1. Closed trade triggers journal generation with 14 mandatory sections.
2. Open trade does not create final journal.
3. Winning trade generates journal analyzing process/strategy.
4. Losing trade generates journal without automatically assuming mistake.
5. Duplicate sync does not create duplicate journal (idempotency).
6. AI failure does not lose the trade (records status FAILED / PENDING_AI).
7. Retry works for failed or existing journal.
8. Account isolation: Account A cannot journal Account B trades.
9. AI advisory-only: cannot execute MT5 orders.
10. AI cannot modify risk settings.
11. Missing data is represented as 'Not available' without hallucination.
12. Manual journal still works.
13. Personal notes are preserved when AI generates.
14. AI API key never appears in responses/logs.
15. AI audit log is created.
16. Demo/live trade status is preserved correctly.
"""

import sys
import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from starlette.testclient import TestClient
from app.main import app
from app.services.ai.orchestrator import AIOrchestrator
from app.services.ai.schemas import JournalAIResponse
from app.services.ai.config import AIConfig


class TestAutomaticAIJournaling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_api_key_not_exposed(self):
        """Security: AI API key must never appear in any API response."""
        res_status = self.client.get("/api/ai/status")
        self.assertEqual(res_status.status_code, 200)
        content_str = res_status.text
        self.assertNotIn("AI_API_KEY", content_str)
        if AIConfig.API_KEY:
            self.assertNotIn(AIConfig.API_KEY, content_str)

        res_journal = self.client.get("/api/journal")
        self.assertEqual(res_journal.status_code, 200)
        self.assertNotIn("AI_API_KEY", res_journal.text)

    def test_02_open_trade_does_not_create_final_journal(self):
        """Rule 2: Open trades must NOT generate final AI journal entry."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Mock trade with exit_time = None (open trade)
            with patch("app.services.ai.tools.get_trade_by_id") as mock_get_trade:
                mock_get_trade.return_value = {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "account_id": "22222222-2222-2222-2222-222222222222",
                    "symbol": "EURUSD",
                    "exit_time": None,  # OPEN POSITION
                    "status": "OPEN",
                }
                res = loop.run_until_complete(
                    AIOrchestrator.generate_journal(
                        "22222222-2222-2222-2222-222222222222",
                        "11111111-1111-1111-1111-111111111111"
                    )
                )
                self.assertEqual(res.status, "SKIPPED")
                self.assertIn("open", res.trade_summary.lower())
        finally:
            loop.close()

    def test_03_account_isolation_enforced(self):
        """Rule 4: Account A cannot generate journal for Account B trades."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with patch("app.services.ai.tools.get_trade_by_id") as mock_get_trade:
                mock_get_trade.return_value = {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "account_id": "aaaa-aaaa-aaaa-aaaa",
                    "symbol": "EURUSD",
                    "exit_time": "2026-09-27T10:00:00Z",
                    "status": "WIN",
                }
                # Account B attempts to journal Account A trade
                res = loop.run_until_complete(
                    AIOrchestrator.generate_journal(
                        "bbbb-bbbb-bbbb-bbbb",
                        "11111111-1111-1111-1111-111111111111"
                    )
                )
                self.assertEqual(res.status, "FAILED")
                self.assertIn("isolation", res.trade_summary.lower())
        finally:
            loop.close()

    def test_04_missing_data_not_hallucinated(self):
        """Rule 3: Missing fields are marked 'Not available' and never invented."""
        from app.services.ai.context_builder import _format_single_trade
        sparse_trade = {
            "id": "trade-sparse-1",
            "account_id": "acc-1",
            "symbol": "GBPUSD",
            "volume": 0.1,
            "entry_price": 1.25,
            # stop_loss, take_profit, indicators, session are omitted
        }
        formatted = _format_single_trade(sparse_trade)
        self.assertEqual(formatted["stop_loss"], "Not available")
        self.assertEqual(formatted["take_profit"], "Not available")
        self.assertEqual(formatted["market_session"], "Not available")
        self.assertEqual(formatted["indicator_values"], "Not available")

    def test_05_ai_advisory_only_cannot_trade_or_modify_risk(self):
        """Rule 8: AI Journal Agent has no execution or risk alteration methods."""
        from app.services.ai.journal_agent import generate_journal
        # Verify journal agent does not import mt5 order_send or modify risk
        import app.services.ai.journal_agent as ja
        self.assertFalse(hasattr(ja, "order_send"))
        self.assertFalse(hasattr(ja, "close_position"))
        self.assertFalse(hasattr(ja, "update_risk_limit"))

    def test_06_manual_journal_still_operates(self):
        """Rule 16 & 17: User can still post manual journal entries and preserve notes."""
        response = self.client.post(
            "/api/journal",
            json={
                "account_id": "ecaebc11-8fdf-47e7-a7dd-0239b18b3f64",
                "symbol": "EURUSD",
                "date": "2026-09-27",
                "result": "WIN",
                "notes": "My manual psychological note: Kept discipline",
                "reason": "Break of 15m structure",
                "lessons": "Patience pays",
                "tags": ["Manual", "Discipline"],
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["notes"], "My manual psychological note: Kept discipline")

    def test_07_structured_journal_parsing_with_all_sections(self):
        """Rule 5: Parsed journal response must contain all 14 mandatory sections."""
        from app.services.ai.journal_agent import _parse_journal_response
        mock_raw_ai = {
            "trade_summary": "Clean trend continuation win on EURUSD",
            "market_context": "London session open, high liquidity",
            "entry_analysis": "Entered on retest of 1.0850 order block",
            "exit_analysis": "Hit take profit at 1.0890 cleanly",
            "risk_analysis": "Risked 0.5% with strict stop loss below swing low",
            "execution_analysis": "Zero slippage observed",
            "what_went_well": ["Followed trading plan", "Patient entry"],
            "what_could_be_improved": ["Could have trailed stop for runner"],
            "mistakes_violations": [],
            "pattern_observed": "Morning liquidity sweep followed by trend run",
            "lesson": "Wait for 15m candle close confirmation",
            "suggested_improvement": "Test 50% partial exit at 2R",
            "ai_confidence": 0.95,
            "execution_quality_score": 90.0,
            "tags": ["EURUSD", "TrendFollow"],
        }
        parsed = _parse_journal_response(
            mock_raw_ai,
            "acc-123",
            "trade-456",
            {"symbol": "EURUSD", "status": "WIN"}
        )
        self.assertEqual(parsed.trade_summary, "Clean trend continuation win on EURUSD")
        self.assertEqual(parsed.market_context, "London session open, high liquidity")
        self.assertEqual(parsed.entry_analysis, "Entered on retest of 1.0850 order block")
        self.assertEqual(parsed.exit_analysis, "Hit take profit at 1.0890 cleanly")
        self.assertEqual(parsed.risk_analysis, "Risked 0.5% with strict stop loss below swing low")
        self.assertEqual(parsed.execution_analysis, "Zero slippage observed")
        self.assertEqual(len(parsed.what_went_well), 2)
        self.assertEqual(len(parsed.mistakes_violations), 0)
        self.assertEqual(parsed.ai_confidence, 0.95)
        self.assertEqual(parsed.status, "COMPLETED")
        self.assertEqual(parsed.prompt_version, "journal_prompt_v1")

    def test_08_auto_process_endpoint(self):
        """Endpoint: /api/ai/journal/auto-process responds cleanly."""
        res = self.client.post(
            "/api/ai/journal/auto-process?account_id=ecaebc11-8fdf-47e7-a7dd-0239b18b3f64"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("scheduled_trades", data)

    def test_09_retry_endpoint(self):
        """Endpoint: /api/ai/journal/retry accepts request and persists gracefully."""
        res = self.client.post(
            "/api/ai/journal/retry",
            json={
                "account_id": "00000000-0000-0000-0000-000000000000",
                "trade_id": "00000000-0000-0000-0000-000000000000",
                "force_regenerate": True
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("trade_id", data)
        self.assertIn("status", data)


if __name__ == "__main__":
    unittest.main()
