"""
Analysis AI Agent
Analyzes trading performance, market conditions, risk status, and positions.
"""

import logging
from datetime import datetime

from app.services.ai import client as ai_client
from app.services.ai.context_builder import build_analysis_context, context_to_prompt_text
from app.services.ai.prompts import ANALYSIS_SYSTEM_PROMPT
from app.services.ai.schemas import (
    AnalysisResponse,
    Observation,
    Warning,
    Recommendation,
    SymbolAnalysis,
    DataSource,
)

logger = logging.getLogger("ai_analysis")


async def analyze(account_id: str) -> AnalysisResponse:
    """
    Run AI analysis for an account.

    1. Build context from controlled tools
    2. Send to AI with system prompt
    3. Parse structured response
    4. Return validated AnalysisResponse
    """
    # Step 1: Build context
    context = await build_analysis_context(account_id)

    if not context.get("data_availability", {}).get("has_account") and account_id != "all":
        return AnalysisResponse(
            account_id=account_id,
            data_summary="No account data found for this account ID.",
            observations=[
                Observation(
                    text="Account data is not available. Please sync your MT5 account first.",
                    source=DataSource.OBSERVED,
                )
            ],
        )

    # Step 2: Build user prompt
    user_prompt = f"""Analyze the following trading data and provide a comprehensive performance analysis.

TRADING DATA:
{context_to_prompt_text(context)}

Analyze the trader's:
1. Overall performance based on trade statistics
2. Position management (open positions if any)
3. Risk management adherence
4. Symbol-level breakdown
5. Patterns in winning and losing trades
6. Areas needing attention or improvement

Remember: Base everything on the provided data. State clearly if data is insufficient for any assessment."""

    # Step 3: Call AI
    raw = await ai_client.generate_structured(
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # Step 4: Parse into schema
    response = _parse_analysis_response(raw, account_id, context)
    return response


def _parse_analysis_response(
    raw: dict, account_id: str, context: dict
) -> AnalysisResponse:
    """Parse AI JSON output into a validated AnalysisResponse."""
    observations = []
    for obs in raw.get("observations", []):
        if isinstance(obs, dict):
            observations.append(Observation(
                text=obs.get("text", ""),
                source=obs.get("source", DataSource.AI_INTERPRETATION),
                confidence=obs.get("confidence"),
            ))
        elif isinstance(obs, str):
            observations.append(Observation(text=obs))

    warnings = []
    for w in raw.get("warnings", []):
        if isinstance(w, dict):
            warnings.append(Warning(text=w.get("text", ""), severity=w.get("severity", "medium")))
        elif isinstance(w, str):
            warnings.append(Warning(text=w))

    recommendations = []
    for r in raw.get("recommendations", []):
        if isinstance(r, dict):
            recommendations.append(Recommendation(
                text=r.get("text", ""),
                priority=r.get("priority", "medium"),
                rationale=r.get("rationale"),
            ))
        elif isinstance(r, str):
            recommendations.append(Recommendation(text=r))

    symbol_analyses = []
    for sa in raw.get("symbol_analyses", []):
        if isinstance(sa, dict):
            symbol_analyses.append(SymbolAnalysis(
                symbol=sa.get("symbol", ""),
                market_regime=sa.get("market_regime", "unknown"),
                trend=sa.get("trend", "unknown"),
                volatility=sa.get("volatility", "unknown"),
                observations=sa.get("observations", []),
            ))

    return AnalysisResponse(
        account_id=account_id,
        timestamp=datetime.utcnow().isoformat(),
        overall_market_regime=raw.get("overall_market_regime", "unknown"),
        overall_trend=raw.get("overall_trend", "unknown"),
        overall_volatility=raw.get("overall_volatility", "unknown"),
        strategy_status=raw.get("strategy_status", "No assessment available"),
        risk_status=raw.get("risk_status", "acceptable"),
        observations=observations,
        warnings=warnings,
        recommendations=recommendations,
        symbol_analyses=symbol_analyses,
        data_summary=raw.get("data_summary", ""),
    )
