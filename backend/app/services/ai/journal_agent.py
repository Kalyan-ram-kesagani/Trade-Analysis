"""
Journal AI Agent
Generates structured journal entries for completed trades.
"""

import logging
from datetime import datetime

from app.services.ai import client as ai_client
from app.services.ai.context_builder import build_journal_context, context_to_prompt_text
from app.services.ai.prompts import JOURNAL_SYSTEM_PROMPT, JOURNAL_PROMPT_VERSION
from app.services.ai.schemas import JournalAIResponse

logger = logging.getLogger("ai_journal")


async def generate_journal(account_id: str, trade_id: str) -> JournalAIResponse:
    """
    Generate an AI journal entry for a specific closed trade.

    1. Build context from controlled tools
    2. Enforce trade closed status check
    3. Send to AI with prompt v1 and structured directives
    4. Parse structured response with 14 required sections
    5. Return validated JournalAIResponse
    """
    # Step 1: Build context
    context = await build_journal_context(account_id, trade_id)

    if "error" in context:
        return JournalAIResponse(
            trade_id=trade_id,
            account_id=account_id,
            symbol="",
            result="",
            trade_summary=f"Error: {context['error']}",
            summary=f"Error: {context['error']}",
            prompt_version=JOURNAL_PROMPT_VERSION,
            status="FAILED",
        )

    trade_data = context.get("trade", {})

    # Step 2: Build user prompt with exact sections
    user_prompt = f"""Generate a structured trading journal entry for the following closed trade.

RECORDED TRADE AND CONTEXT DATA:
{context_to_prompt_text(context)}

Analyze this trade according to the 14 mandatory sections:
1. Trade Summary (Concise overview of outcome and trade execution)
2. Market Context (Session, market regime, volatility if available or 'Not available')
3. Entry Analysis (Validation of entry timing, price, and strategy rules)
4. Exit Analysis (Validation of exit, TP/SL execution, or manual intervention)
5. Risk Analysis (Position sizing, risk percentage, initial risk, stop loss adherence)
6. Execution Analysis (Fill efficiency, slippage, speed if available)
7. What Went Well (Specific data-backed execution positives)
8. What Could Be Improved (Actionable process improvements)
9. Mistakes / Violations (Report ONLY if supported by data; empty if none)
10. Pattern Observed (Recurring behavioral or mechanical pattern)
11. Lesson (Primary takeaway from this trade)
12. Suggested Improvement (Concrete future execution guidance)
13. AI Confidence (Confidence in this analysis 0.0-1.0 based on data completeness)
14. AI Disclaimer

IMPORTANT:
- If a value is missing, use 'Not available' — do NOT guess or invent numbers.
- Do NOT calculate authoritative financial figures. The net P&L, fees, and prices in the data are ground truth.
- A winning trade can have execution mistakes; a losing trade is not necessarily a mistake if it was a valid setup."""

    # Step 3: Call AI
    raw = await ai_client.generate_structured(
        system_prompt=JOURNAL_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    # Step 4: Parse into schema
    response = _parse_journal_response(raw, account_id, trade_id, trade_data)
    return response


def _parse_journal_response(
    raw: dict, account_id: str, trade_id: str, trade_data: dict
) -> JournalAIResponse:
    """Parse AI JSON output into a validated JournalAIResponse."""
    what_went_well = raw.get("what_went_well", [])
    if isinstance(what_went_well, str):
        what_went_well = [what_went_well]

    what_could_be_improved = raw.get("what_could_be_improved", raw.get("what_went_wrong", []))
    if isinstance(what_could_be_improved, str):
        what_could_be_improved = [what_could_be_improved]

    mistakes_violations = raw.get("mistakes_violations", [])
    if isinstance(mistakes_violations, str):
        mistakes_violations = [mistakes_violations]

    tags = raw.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    confidence = raw.get("ai_confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = None

    score = raw.get("execution_quality_score")
    if score is not None:
        try:
            score = float(score)
            score = max(0.0, min(100.0, score))
        except (ValueError, TypeError):
            score = None

    trade_summary = raw.get("trade_summary") or raw.get("summary", "")
    entry_analysis = raw.get("entry_analysis") or raw.get("entry_reason", "")
    exit_analysis = raw.get("exit_analysis") or raw.get("exit_reason", "")
    risk_analysis = raw.get("risk_analysis") or raw.get("risk_management_assessment", "")
    execution_analysis = raw.get("execution_analysis", "")
    market_context = raw.get("market_context", "Not available")
    pattern_observed = raw.get("pattern_observed", "")
    lesson = raw.get("lesson") or (raw.get("lessons", [""])[0] if isinstance(raw.get("lessons"), list) and raw.get("lessons") else "")
    suggested_improvement = raw.get("suggested_improvement", "")

    return JournalAIResponse(
        trade_id=trade_id,
        account_id=account_id,
        symbol=trade_data.get("symbol", ""),
        result=trade_data.get("status") or trade_data.get("execution_result", ""),
        timestamp=datetime.utcnow().isoformat(),
        trade_summary=trade_summary,
        market_context=market_context,
        entry_analysis=entry_analysis,
        exit_analysis=exit_analysis,
        risk_analysis=risk_analysis,
        execution_analysis=execution_analysis,
        what_went_well=what_went_well,
        what_could_be_improved=what_could_be_improved,
        mistakes_violations=mistakes_violations,
        pattern_observed=pattern_observed,
        lesson=lesson,
        suggested_improvement=suggested_improvement,
        ai_confidence=confidence,
        tags=tags,
        execution_quality_score=score,
        prompt_version=JOURNAL_PROMPT_VERSION,
        status="COMPLETED",
        # Legacy mappings
        summary=trade_summary,
        entry_reason=entry_analysis,
        exit_reason=exit_analysis,
        strategy_adherence=raw.get("strategy_adherence", ""),
        what_went_wrong=what_could_be_improved,
        lessons=[lesson] if lesson else (raw.get("lessons", []) if isinstance(raw.get("lessons"), list) else []),
        risk_management_assessment=risk_analysis,
    )
