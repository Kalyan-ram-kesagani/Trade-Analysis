"""
AI Orchestrator
Central dispatcher that routes AI requests to the appropriate agent.
Enforces account isolation, error handling, and audit logging.
"""

import time
import logging
from typing import Optional

from app.services.ai.config import AIConfig
from app.services.ai.schemas import (
    AnalysisResponse,
    JournalAIResponse,
    StrategyAnalysisResponse,
    StrategyProposalResponse,
    Observation,
    DataSource,
)
from app.services.ai import tools

logger = logging.getLogger("ai_orchestrator")


class AIOrchestrator:
    """
    Central AI request handler.

    Responsibilities:
    - Validate that AI is configured
    - Route to the correct agent
    - Enforce account isolation
    - Handle errors gracefully
    - Log audit entries
    """

    @staticmethod
    async def analyze(account_id: str) -> AnalysisResponse:
        """Run AI analysis for an account."""
        if not AIConfig.is_configured():
            return AnalysisResponse(
                account_id=account_id,
                data_summary="AI is not configured. Set AI_API_KEY in the backend environment.",
                observations=[
                    Observation(
                        text="AI analysis is unavailable — API key not configured.",
                        source=DataSource.OBSERVED,
                    )
                ],
            )

        start_ms = time.time()
        error_msg = None
        try:
            from app.services.ai.analysis_agent import analyze
            result = await analyze(account_id)
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Analysis AI failed for account {account_id}: {e}")
            return AnalysisResponse(
                account_id=account_id,
                data_summary=f"AI analysis encountered an error: {error_msg}",
                observations=[
                    Observation(
                        text=f"AI analysis failed: {error_msg}",
                        source=DataSource.OBSERVED,
                    )
                ],
            )
        finally:
            duration_ms = int((time.time() - start_ms) * 1000)
            try:
                if account_id and account_id != "all":
                    await tools.log_ai_audit(
                        account_id=account_id,
                        agent_type="analysis",
                        model=AIConfig.get_model_display(),
                        input_summary=f"Analysis request for account {account_id}",
                        output_summary="Analysis completed" if not error_msg else f"Error: {error_msg}",
                        tools_used=["get_account_metrics", "get_trade_history", "get_open_positions", "get_risk_configuration", "compute_trade_statistics"],
                        duration_ms=duration_ms,
                        error=error_msg,
                    )
            except Exception as audit_err:
                logger.warning(f"Audit logging failed: {audit_err}")

    @staticmethod
    async def generate_journal(
        account_id: str, trade_id: str, persist_to_db: bool = True
    ) -> JournalAIResponse:
        """
        Generate an AI journal entry for a closed trade with full persistence,
        idempotency, and audit logging.
        """
        from app.services.ai.prompts import JOURNAL_PROMPT_VERSION

        # Verify trade exists, belongs to account, and is closed
        trade = await tools.get_trade_by_id(trade_id)
        if not trade:
            return JournalAIResponse(
                trade_id=trade_id,
                account_id=account_id,
                symbol="",
                result="",
                status="FAILED",
                trade_summary=f"Trade {trade_id} not found.",
                summary=f"Trade {trade_id} not found.",
            )

        if account_id != "all" and str(trade.get("account_id")) != account_id:
            return JournalAIResponse(
                trade_id=trade_id,
                account_id=account_id,
                symbol="",
                result="",
                status="FAILED",
                trade_summary="Account isolation violation: trade does not belong to specified account.",
                summary="Account isolation violation: trade does not belong to specified account.",
            )

        # Enforce Section 2: Only closed trades receive journal
        if not trade.get("exit_time"):
            return JournalAIResponse(
                trade_id=trade_id,
                account_id=account_id,
                symbol=trade.get("symbol", ""),
                result="OPEN",
                status="SKIPPED",
                trade_summary="Cannot generate final journal for an open position. Only closed trades are journaled.",
                summary="Cannot generate final journal for an open position. Only closed trades are journaled.",
            )

        symbol = trade.get("symbol", "")
        trade_status = trade.get("status", "BREAKEVEN")
        date_str = str(trade.get("exit_time", ""))[:10] or str(trade.get("entry_time", ""))[:10]

        if not AIConfig.is_configured():
            if persist_to_db:
                await tools.save_or_update_ai_journal(
                    account_id=account_id,
                    trade_id=trade_id,
                    symbol=symbol,
                    result=trade_status,
                    date_str=date_str,
                    notes="AI is not configured. Set AI_API_KEY in the backend environment.",
                    reason="Not available (AI not configured)",
                    lessons="Not available",
                    strategy_version=trade.get("strategy_name", "MT5 Manual"),
                    tags=["AI_PENDING"],
                    structured_ai_output={},
                    status="PENDING_AI",
                    ai_provider=AIConfig.PROVIDER,
                    ai_model=AIConfig.MODEL,
                    prompt_version=JOURNAL_PROMPT_VERSION,
                    error_info="AI_API_KEY is not configured",
                )
            return JournalAIResponse(
                trade_id=trade_id,
                account_id=account_id,
                symbol=symbol,
                result=trade_status,
                status="PENDING_AI",
                trade_summary="AI is not configured. Set AI_API_KEY in the backend environment.",
                summary="AI is not configured. Set AI_API_KEY in the backend environment.",
            )

        start_ms = time.time()
        error_msg = None
        result = None
        try:
            from app.services.ai.journal_agent import generate_journal
            result = await generate_journal(account_id, trade_id)

            if persist_to_db and result:
                await tools.save_or_update_ai_journal(
                    account_id=account_id,
                    trade_id=trade_id,
                    symbol=symbol,
                    result=trade_status,
                    date_str=date_str,
                    notes=result.trade_summary or result.summary,
                    reason=result.entry_analysis or result.entry_reason,
                    lessons=result.lesson or ("; ".join(result.lessons) if result.lessons else ""),
                    strategy_version=trade.get("strategy_name", "MT5 Manual"),
                    tags=result.tags or ["AI_REVIEWED"],
                    structured_ai_output=result.model_dump(),
                    status="COMPLETED",
                    ai_provider=AIConfig.PROVIDER,
                    ai_model=AIConfig.MODEL,
                    prompt_version=JOURNAL_PROMPT_VERSION,
                    ai_confidence=result.ai_confidence,
                    ai_recommendation=result.suggested_improvement or result.risk_analysis,
                    ai_detected_reason=result.entry_analysis,
                )

            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Journal AI failed for trade {trade_id}: {e}")
            if persist_to_db:
                try:
                    await tools.save_or_update_ai_journal(
                        account_id=account_id,
                        trade_id=trade_id,
                        symbol=symbol,
                        result=trade_status,
                        date_str=date_str,
                        notes="AI journal generation failed temporarily.",
                        reason="Pending retry",
                        lessons="",
                        strategy_version=trade.get("strategy_name", "MT5 Manual"),
                        tags=["AI_FAILED"],
                        structured_ai_output={},
                        status="FAILED",
                        ai_provider=AIConfig.PROVIDER,
                        ai_model=AIConfig.MODEL,
                        prompt_version=JOURNAL_PROMPT_VERSION,
                        error_info=error_msg,
                    )
                except Exception as db_err:
                    logger.error(f"Failed to save FAILED journal status: {db_err}")

            return JournalAIResponse(
                trade_id=trade_id,
                account_id=account_id,
                symbol=symbol,
                result=trade_status,
                status="FAILED",
                trade_summary=f"AI journal generation encountered an error: {error_msg}",
                summary=f"AI journal generation encountered an error: {error_msg}",
            )
        finally:
            duration_ms = int((time.time() - start_ms) * 1000)
            try:
                target_account = account_id if account_id != "all" else None
                if target_account:
                    await tools.log_ai_audit(
                        account_id=target_account,
                        agent_type="journal",
                        model=AIConfig.get_model_display(),
                        input_summary=f"Journal generation for trade {trade_id} ({symbol})",
                        output_summary="Journal generated and persisted" if not error_msg else f"Error: {error_msg}",
                        tools_used=["get_trade_by_id", "get_account_metrics", "get_risk_configuration", "get_journal_history", "save_or_update_ai_journal"],
                        duration_ms=duration_ms,
                        error=error_msg,
                        related_trade_id=trade_id,
                    )
            except Exception as audit_err:
                logger.warning(f"Audit logging failed: {audit_err}")

    @staticmethod
    async def analyze_strategy(
        strategy_id: str, account_id: Optional[str] = None
    ) -> StrategyAnalysisResponse:
        """Run AI analysis on a strategy."""
        if not AIConfig.is_configured():
            return StrategyAnalysisResponse(
                strategy_id=strategy_id,
                strategy_name="Unknown",
                strategy_version="",
                performance_summary="AI is not configured. Set AI_API_KEY in the backend environment.",
            )

        start_ms = time.time()
        error_msg = None
        try:
            from app.services.ai.strategy_agent import analyze_strategy
            result = await analyze_strategy(strategy_id, account_id)
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Strategy AI failed for strategy {strategy_id}: {e}")
            return StrategyAnalysisResponse(
                strategy_id=strategy_id,
                strategy_name="Unknown",
                strategy_version="",
                performance_summary=f"AI strategy analysis encountered an error: {error_msg}",
            )
        finally:
            duration_ms = int((time.time() - start_ms) * 1000)
            try:
                if account_id and account_id != "all":
                    await tools.log_ai_audit(
                        account_id=account_id,
                        agent_type="strategy_analysis",
                        model=AIConfig.get_model_display(),
                        input_summary=f"Strategy analysis for {strategy_id}",
                        output_summary="Analysis completed" if not error_msg else f"Error: {error_msg}",
                        tools_used=["get_strategy_by_id", "get_trade_history", "compute_trade_statistics"],
                        duration_ms=duration_ms,
                        error=error_msg,
                        related_strategy_id=strategy_id,
                    )
            except Exception as audit_err:
                logger.warning(f"Audit logging failed: {audit_err}")

    @staticmethod
    async def propose_strategy_improvement(
        strategy_id: str,
        account_id: Optional[str] = None,
        focus_area: Optional[str] = None,
    ) -> StrategyProposalResponse:
        """Generate a strategy improvement proposal."""
        if not AIConfig.is_configured():
            return StrategyProposalResponse(
                strategy_id=strategy_id,
                base_strategy_name="Unknown",
                base_strategy_version="",
                proposed_version="",
                identified_issue="AI is not configured. Set AI_API_KEY in the backend environment.",
            )

        start_ms = time.time()
        error_msg = None
        try:
            from app.services.ai.strategy_agent import propose_improvement
            result = await propose_improvement(strategy_id, account_id, focus_area)

            # Persist proposal into strategy_proposals table
            try:
                proposal_db_id = await tools.save_strategy_proposal(
                    strategy_id=strategy_id,
                    base_strategy_name=result.base_strategy_name,
                    base_strategy_version=result.base_strategy_version,
                    proposed_version=result.proposed_version,
                    identified_issue=result.identified_issue,
                    evidence=result.evidence,
                    hypothesis=result.hypothesis,
                    proposed_change=result.proposed_change,
                    expected_purpose=result.expected_purpose,
                    account_id=account_id,
                    status=result.status.value,
                )
                if proposal_db_id:
                    result.id = proposal_db_id
            except Exception as save_err:
                logger.warning(f"Could not persist proposal to DB: {save_err}")

            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Strategy proposal AI failed for strategy {strategy_id}: {e}")
            return StrategyProposalResponse(
                strategy_id=strategy_id,
                base_strategy_name="Unknown",
                base_strategy_version="",
                proposed_version="",
                identified_issue=f"AI strategy proposal encountered an error: {error_msg}",
            )
        finally:
            duration_ms = int((time.time() - start_ms) * 1000)
            try:
                if account_id and account_id != "all":
                    await tools.log_ai_audit(
                        account_id=account_id,
                        agent_type="strategy_proposal",
                        model=AIConfig.get_model_display(),
                        input_summary=f"Strategy proposal for {strategy_id}" + (f" (focus: {focus_area})" if focus_area else ""),
                        output_summary="Proposal generated" if not error_msg else f"Error: {error_msg}",
                        tools_used=["get_strategy_by_id", "get_trade_history", "compute_trade_statistics"],
                        duration_ms=duration_ms,
                        error=error_msg,
                        related_strategy_id=strategy_id,
                    )
            except Exception as audit_err:
                logger.warning(f"Audit logging failed: {audit_err}")

    @staticmethod
    async def get_strategy_proposals(
        strategy_id: Optional[str] = None,
        account_id: Optional[str] = None,
        limit: int = 50,
    ):
        """Retrieve strategy proposals from the database."""
        return await tools.get_strategy_proposals(strategy_id, account_id, limit)

    @staticmethod
    async def update_proposal_status(
        proposal_id: str,
        status: str,
        approved_by: Optional[str] = None,
        rejected_reason: Optional[str] = None,
    ) -> bool:
        """Update a strategy proposal's validation status."""
        return await tools.update_strategy_proposal_status(
            proposal_id=proposal_id,
            status=status,
            approved_by=approved_by,
            rejected_reason=rejected_reason,
        )

    @staticmethod
    async def get_audit_logs(
        account_id: Optional[str] = None,
        limit: int = 50,
    ):
        """Retrieve AI audit logs."""
        return await tools.get_ai_audit_logs(account_id, limit)

    @staticmethod
    async def get_ai_status() -> dict:
        """Return the current AI system configuration status."""
        return {
            "configured": AIConfig.is_configured(),
            "provider": AIConfig.PROVIDER,
            "model": AIConfig.MODEL,
            "model_display": AIConfig.get_model_display(),
        }
