"""
AI Response Schemas
Pydantic models for all structured AI outputs.
These enforce typed responses — AI cannot return arbitrary free-text for core logic.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum


# ==========================================
# Enumerations
# ==========================================

class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class TrendDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class VolatilityLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    ACCEPTABLE = "acceptable"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class DataSource(str, Enum):
    OBSERVED = "observed_data"
    CALCULATED = "calculated_metric"
    AI_INTERPRETATION = "ai_interpretation"
    RECOMMENDATION = "recommendation"


class StrategyProposalStatus(str, Enum):
    DRAFT = "DRAFT"
    AI_PROPOSED = "AI_PROPOSED"
    BACKTEST_PENDING = "BACKTEST_PENDING"
    BACKTESTED = "BACKTESTED"
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"
    WALK_FORWARD = "WALK_FORWARD"
    MONTE_CARLO = "MONTE_CARLO"
    RISK_VALIDATION = "RISK_VALIDATION"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEPLOYED = "DEPLOYED"


# ==========================================
# Common Sub-models
# ==========================================

class Observation(BaseModel):
    text: str
    source: DataSource = DataSource.AI_INTERPRETATION
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class Warning(BaseModel):
    text: str
    severity: str = "medium"


class Recommendation(BaseModel):
    text: str
    priority: str = "medium"
    rationale: Optional[str] = None


class SymbolAnalysis(BaseModel):
    symbol: str
    market_regime: MarketRegime = MarketRegime.UNKNOWN
    trend: TrendDirection = TrendDirection.UNKNOWN
    volatility: VolatilityLevel = VolatilityLevel.UNKNOWN
    observations: List[str] = Field(default_factory=list)


# ==========================================
# Analysis Response
# ==========================================

class AnalysisResponse(BaseModel):
    """Structured response from the Analysis AI agent."""
    account_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Market overview
    overall_market_regime: MarketRegime = MarketRegime.UNKNOWN
    overall_trend: TrendDirection = TrendDirection.UNKNOWN
    overall_volatility: VolatilityLevel = VolatilityLevel.UNKNOWN

    # Strategy & risk status
    strategy_status: str = "No active strategy assessment"
    risk_status: RiskLevel = RiskLevel.ACCEPTABLE

    # Detailed analysis
    observations: List[Observation] = Field(default_factory=list)
    warnings: List[Warning] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)

    # Per-symbol analysis
    symbol_analyses: List[SymbolAnalysis] = Field(default_factory=list)

    # Meta
    data_summary: str = ""
    ai_disclaimer: str = (
        "AI-generated analysis based on available trading data. "
        "Not financial advice. Verify all observations against live market data."
    )


# ==========================================
# Journal Response
# ==========================================

class JournalAIResponse(BaseModel):
    """Structured response from the Journal AI agent."""
    trade_id: str
    account_id: str
    symbol: str
    result: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # 14 Standard Structured Sections
    trade_summary: str = ""
    market_context: str = "Not available"
    entry_analysis: str = ""
    exit_analysis: str = ""
    risk_analysis: str = ""
    execution_analysis: str = ""
    what_went_well: List[str] = Field(default_factory=list)
    what_could_be_improved: List[str] = Field(default_factory=list)
    mistakes_violations: List[str] = Field(default_factory=list)
    pattern_observed: str = ""
    lesson: str = ""
    suggested_improvement: str = ""
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_disclaimer: str = (
        "AI-generated journal analysis based on recorded trade data. "
        "Advisory only; not financial advice."
    )

    # Legacy/compatibility aliases for backward compatibility
    summary: str = ""
    entry_reason: str = ""
    exit_reason: str = ""
    strategy_adherence: str = ""
    what_went_wrong: List[str] = Field(default_factory=list)
    lessons: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    execution_quality_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    risk_management_assessment: str = ""
    
    # Metadata
    prompt_version: str = "journal_prompt_v1"
    status: str = "COMPLETED"


# ==========================================
# Strategy Response
# ==========================================

class StrategyAnalysisResponse(BaseModel):
    """Structured response from the Strategy AI agent for analysis."""
    strategy_id: str
    strategy_name: str
    strategy_version: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Performance assessment
    performance_summary: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)

    # Issues identified
    identified_issues: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)

    # Improvement areas
    improvement_suggestions: List[str] = Field(default_factory=list)

    # Meta
    ai_disclaimer: str = (
        "AI-generated strategy analysis. All suggestions are hypotheses "
        "requiring validation through backtesting."
    )


class StrategyProposalResponse(BaseModel):
    """Structured response for an AI strategy improvement proposal."""
    id: Optional[str] = None
    strategy_id: str
    base_strategy_name: str
    base_strategy_version: str
    proposed_version: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Proposal details
    identified_issue: str = ""
    evidence: List[str] = Field(default_factory=list)
    hypothesis: str = ""
    proposed_change: str = ""
    expected_purpose: str = ""

    # Validation
    validation_required: bool = True
    status: StrategyProposalStatus = StrategyProposalStatus.AI_PROPOSED

    # Meta
    ai_disclaimer: str = (
        "This is a testable hypothesis, not a guaranteed improvement. "
        "Requires full validation pipeline before deployment."
    )


# ==========================================
# AI Audit Log
# ==========================================

class AIAuditLogEntry(BaseModel):
    """Schema for AI request audit logging."""
    account_id: str
    agent_type: str
    request_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    input_summary: str = ""
    model: str = ""
    tools_used: List[str] = Field(default_factory=list)
    output_summary: str = ""
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    token_count: Optional[int] = None
    related_trade_id: Optional[str] = None
    related_strategy_id: Optional[str] = None


# ==========================================
# Request Schemas (API Input)
# ==========================================

class AnalysisRequest(BaseModel):
    """Request body for AI analysis."""
    account_id: str
    symbols: Optional[List[str]] = None
    include_positions: bool = True
    include_trades: bool = True
    include_risk: bool = True


class JournalRequest(BaseModel):
    """Request body for AI journal generation."""
    account_id: str
    trade_id: str


class StrategyAnalysisRequest(BaseModel):
    """Request body for AI strategy analysis."""
    strategy_id: str
    account_id: Optional[str] = None


class StrategyProposalRequest(BaseModel):
    """Request body for AI strategy proposal."""
    strategy_id: str
    account_id: Optional[str] = None
    focus_area: Optional[str] = None


class ProposalStatusUpdate(BaseModel):
    """Request body to update proposal status."""
    status: str
    approved_by: Optional[str] = None
    rejected_reason: Optional[str] = None


class ProposalApprovalRequest(BaseModel):
    """Request body for human approval."""
    approved_by: str = Field(..., min_length=2, description="Human reviewer identifier")
    notes: Optional[str] = None


class ProposalDeployRequest(BaseModel):
    """Request body for deploying an approved proposal."""
    deployed_by: str = Field(..., min_length=2, description="Human deployer identifier")
    target_accounts: List[str] = Field(..., min_length=1, description="Explicit target trading account IDs")
    live_risk_percentage: Optional[float] = 1.0



class BacktestRunRequest(BaseModel):
    """Request body for running standalone backtest."""
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    initial_balance: float = 10000.0
    risk_per_trade_pct: float = 1.0
    strategy_id: Optional[str] = None
    proposal_id: Optional[str] = None
    account_id: Optional[str] = None
    parameters: Optional[dict] = Field(default_factory=dict)

