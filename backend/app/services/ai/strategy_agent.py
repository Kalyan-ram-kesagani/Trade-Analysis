"""
Strategy AI Agent
Analyzes strategies and generates improvement proposals.
ADVISORY ONLY — cannot directly modify live strategies.
"""

import logging
from datetime import datetime
from typing import Optional

from app.services.ai import client as ai_client
from app.services.ai.context_builder import build_strategy_context, context_to_prompt_text
from app.services.ai.prompts import STRATEGY_ANALYSIS_PROMPT, STRATEGY_PROPOSAL_PROMPT
from app.services.ai.schemas import (
    StrategyAnalysisResponse,
    StrategyProposalResponse,
    StrategyProposalStatus,
)

logger = logging.getLogger("ai_strategy")


async def analyze_strategy(
    strategy_id: str, account_id: Optional[str] = None
) -> StrategyAnalysisResponse:
    """
    Run AI analysis on a strategy's performance.

    1. Build context from controlled tools
    2. Send to AI with system prompt
    3. Parse structured response
    4. Return validated StrategyAnalysisResponse
    """
    context = await build_strategy_context(strategy_id, account_id)

    if "error" in context:
        strategy_data = context.get("strategy", {}) or {}
        return StrategyAnalysisResponse(
            strategy_id=strategy_id,
            strategy_name=strategy_data.get("name", "Unknown"),
            strategy_version=strategy_data.get("version", ""),
            performance_summary=f"Error: {context['error']}",
        )

    strategy_data = context.get("strategy", {}) or {}

    user_prompt = f"""Analyze the following trading strategy and its performance data.

STRATEGY AND PERFORMANCE DATA:
{context_to_prompt_text(context)}

Provide:
1. Overall performance assessment
2. Key strengths of the strategy
3. Key weaknesses or areas of concern
4. Specific issues identified from the data
5. Evidence supporting the identified issues
6. Testable improvement suggestions

Remember: All suggestions are hypotheses requiring backtesting. Do not claim any change will guarantee profitability."""

    raw = await ai_client.generate_structured(
        system_prompt=STRATEGY_ANALYSIS_PROMPT,
        user_prompt=user_prompt,
    )

    return _parse_strategy_analysis(raw, strategy_id, strategy_data)


async def propose_improvement(
    strategy_id: str,
    account_id: Optional[str] = None,
    focus_area: Optional[str] = None,
) -> StrategyProposalResponse:
    """
    Generate a specific strategy improvement proposal.
    This is a RESEARCH HYPOTHESIS, not an automatic change.
    """
    context = await build_strategy_context(strategy_id, account_id)

    if "error" in context:
        strategy_data = context.get("strategy", {}) or {}
        return StrategyProposalResponse(
            strategy_id=strategy_id,
            base_strategy_name=strategy_data.get("name", "Unknown"),
            base_strategy_version=strategy_data.get("version", ""),
            proposed_version="",
            identified_issue=f"Error: {context['error']}",
        )

    strategy_data = context.get("strategy", {}) or {}

    focus_text = ""
    if focus_area:
        focus_text = f"\nFOCUS AREA: Specifically analyze and propose improvements related to: {focus_area}"

    user_prompt = f"""Based on the following strategy and its performance data, generate ONE specific improvement proposal.

STRATEGY AND PERFORMANCE DATA:
{context_to_prompt_text(context)}
{focus_text}

Generate a single, specific, testable improvement proposal:
1. Identify the most impactful issue from the performance data
2. Provide evidence from the data supporting this issue
3. State a clear hypothesis for why a specific change would help
4. Describe the exact proposed change (specific enough to implement)
5. Explain the expected purpose of the change

Remember: This is a research hypothesis. It requires full validation (backtest, OOS, walk-forward, Monte Carlo) before deployment."""

    raw = await ai_client.generate_structured(
        system_prompt=STRATEGY_PROPOSAL_PROMPT,
        user_prompt=user_prompt,
    )

    return _parse_strategy_proposal(raw, strategy_id, strategy_data)


def _parse_strategy_analysis(
    raw: dict, strategy_id: str, strategy_data: dict
) -> StrategyAnalysisResponse:
    """Parse AI JSON output into a validated StrategyAnalysisResponse."""
    def _ensure_list(val):
        if isinstance(val, str):
            return [val]
        if isinstance(val, list):
            return [str(item) for item in val]
        return []

    return StrategyAnalysisResponse(
        strategy_id=strategy_id,
        strategy_name=strategy_data.get("name", "Unknown"),
        strategy_version=strategy_data.get("version", ""),
        timestamp=datetime.utcnow().isoformat(),
        performance_summary=raw.get("performance_summary", ""),
        strengths=_ensure_list(raw.get("strengths", [])),
        weaknesses=_ensure_list(raw.get("weaknesses", [])),
        identified_issues=_ensure_list(raw.get("identified_issues", [])),
        evidence=_ensure_list(raw.get("evidence", [])),
        improvement_suggestions=_ensure_list(raw.get("improvement_suggestions", [])),
    )


def _parse_strategy_proposal(
    raw: dict, strategy_id: str, strategy_data: dict
) -> StrategyProposalResponse:
    """Parse AI JSON output into a validated StrategyProposalResponse."""
    current_version = strategy_data.get("version", "V1")
    # Generate a proposed version
    version_parts = current_version.replace("V", "").replace("v", "").split(".")
    try:
        major = int(version_parts[0]) if version_parts else 1
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        proposed_version = f"V{major}.{minor + 1}"
    except (ValueError, IndexError):
        proposed_version = f"{current_version}.1"

    evidence = raw.get("evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]

    return StrategyProposalResponse(
        strategy_id=strategy_id,
        base_strategy_name=strategy_data.get("name", "Unknown"),
        base_strategy_version=current_version,
        proposed_version=proposed_version,
        timestamp=datetime.utcnow().isoformat(),
        identified_issue=raw.get("identified_issue", ""),
        evidence=evidence,
        hypothesis=raw.get("hypothesis", ""),
        proposed_change=raw.get("proposed_change", ""),
        expected_purpose=raw.get("expected_purpose", ""),
        validation_required=True,
        status=StrategyProposalStatus.AI_PROPOSED,
    )
