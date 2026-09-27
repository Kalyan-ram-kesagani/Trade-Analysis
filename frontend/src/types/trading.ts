export interface TradingAccount {
  id: string;
  user_id: string;
  broker: string;
  account_name: string;
  account_number: string;
  masked_number: string;
  server: string;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number;
  floating_pl: number;
  currency: string;
  status: 'connected' | 'disconnected' | 'delayed';
  account_type: 'live' | 'demo';
  leverage: number;
  last_sync: string;
  ping_ms: number;
  created_at: string;
}

export type RiskFreeStatus = 'YES' | 'NO' | 'N/A';

export interface Trade {
  id: string;
  ticket: number;
  account_id: string;
  symbol: string;
  direction: 'BUY' | 'SELL';
  volume: number;
  entry_price: number;
  exit_price: number;
  stop_loss: number;
  take_profit: number;
  entry_time: string;
  exit_time: string;
  profit_loss: number;
  commission: number;
  swap: number;
  net_pl: number;
  status: 'WIN' | 'LOSS' | 'BREAKEVEN';
  strategy_id: string;
  strategy_name: string;
  // Risk management fields
  initial_risk_percent: number;
  initial_risk_amount: number;
  risk_free_status: RiskFreeStatus;
  break_even_price?: number;
  risk_free_activated_time?: string;
  risk_reward_ratio?: number;
  notes?: string;
  created_at: string;
}

export interface OpenPosition {
  id: string;
  ticket: number;
  account_id: string;
  symbol: string;
  direction: 'BUY' | 'SELL';
  volume: number;
  entry_price: number;
  current_price: number;
  stop_loss: number;
  take_profit: number;
  floating_pl: number;
  duration: string;
  entry_time: string;
  risk_free_status: RiskFreeStatus;
  break_even_price?: number;
  strategy_name: string;
}

export type ActivityType =
  | 'trade_opened'
  | 'trade_closed'
  | 'risk_free_activated'
  | 'sl_modified'
  | 'tp_modified'
  | 'mt5_connected'
  | 'mt5_disconnected'
  | 'mt5_synchronized'
  | 'account_switched'
  | 'strategy_enabled'
  | 'strategy_disabled'
  | 'risk_limit_reached'
  | 'system_warning';

export interface SystemActivity {
  id: string;
  account_id: string;
  account_name: string;
  type: ActivityType;
  title: string;
  description: string;
  timestamp: string;
  relative_time: string;
  symbol?: string;
  pl?: number;
  level?: 'info' | 'success' | 'warning' | 'error';
}

export interface Strategy {
  id: string;
  name: string;
  version: string;
  description: string;
  status: 'active' | 'testing' | 'archived';
  account_ids: string[];
  total_trades: number;
  win_rate: number;
  profit_loss: number;
  max_drawdown: number;
  profit_factor: number;
  created_date: string;
  updated_date: string;
  rules: string[];
  risk_parameters: {
    max_risk_per_trade: string;
    max_daily_drawdown: string;
    rr_target: string;
    breakeven_trigger: string;
  };
  version_history: {
    version: string;
    date: string;
    changes: string;
  }[];
}

export interface JournalEntry {
  id: string;
  trade_id: string;
  account_id: string;
  symbol: string;
  date: string;
  result: 'WIN' | 'LOSS' | 'BREAKEVEN';
  notes: string;
  reason: string;
  lessons: string;
  strategy_version: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  // Automatic AI Journaling Fields
  journal_type?: 'MANUAL' | 'AI_TRADE_REVIEW';
  status?: 'PENDING_AI' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'SKIPPED';
  ai_provider?: string;
  ai_model?: string;
  prompt_version?: string;
  structured_ai_output?: {
    trade_summary?: string;
    market_context?: string;
    entry_analysis?: string;
    exit_analysis?: string;
    risk_analysis?: string;
    execution_analysis?: string;
    what_went_well?: string[];
    what_could_be_improved?: string[];
    mistakes_violations?: string[];
    pattern_observed?: string;
    lesson?: string;
    suggested_improvement?: string;
    ai_confidence?: number;
    execution_quality_score?: number;
    ai_disclaimer?: string;
    [key: string]: any;
  };
  ai_confidence?: number;
  error_info?: string;
  retry_count?: number;
  generated_at?: string;
  // Legacy / Quick access
  ai_detected_reason?: string;
  ai_recommendation?: string;
  ai_modification?: string;
}

export interface RiskStatus {
  daily_risk_percent: number;
  daily_limit_percent: number;
  status: 'within_limit' | 'approaching' | 'locked';
  current_drawdown: number;
  max_drawdown_limit: number;
  trades_remaining_today: number;
  max_daily_trades: number;
}

export interface SystemHealthItem {
  id: string;
  name: string;
  status: 'ok' | 'warning' | 'error' | 'coming_soon';
  latency_ms?: number;
  message?: string;
}

export interface EquityDataPoint {
  date: string;
  timestamp: number;
  balance: number;
  equity: number;
  drawdown: number;
  pl: number;
}

// ==========================================
// AI LAYER TYPES
// ==========================================

export interface AIStatus {
  configured: boolean;
  provider: string;
  model: string;
  model_display: string;
}

export interface AIObservation {
  text: string;
  source: 'observed_data' | 'calculated_metric' | 'ai_interpretation' | 'recommendation';
  confidence?: number;
}

export interface AIWarning {
  text: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface AIRecommendation {
  text: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  rationale?: string;
}

export interface AISymbolAnalysis {
  symbol: string;
  market_regime: 'trending' | 'ranging' | 'volatile' | 'unknown';
  trend: 'bullish' | 'bearish' | 'neutral' | 'unknown';
  volatility: 'low' | 'moderate' | 'high' | 'extreme' | 'unknown';
  observations: string[];
}

export interface AIAnalysisResponse {
  account_id: string;
  timestamp: string;
  overall_market_regime: 'trending' | 'ranging' | 'volatile' | 'unknown';
  overall_trend: 'bullish' | 'bearish' | 'neutral' | 'unknown';
  overall_volatility: 'low' | 'moderate' | 'high' | 'extreme' | 'unknown';
  strategy_status: string;
  risk_status: 'low' | 'acceptable' | 'elevated' | 'high' | 'critical';
  observations: AIObservation[];
  warnings: AIWarning[];
  recommendations: AIRecommendation[];
  symbol_analyses: AISymbolAnalysis[];
  data_summary: string;
  ai_disclaimer: string;
}

export interface AIJournalResponse {
  trade_id: string;
  account_id: string;
  symbol: string;
  result: string;
  timestamp: string;
  summary: string;
  entry_reason: string;
  exit_reason: string;
  strategy_adherence: string;
  what_went_well: string[];
  what_went_wrong: string[];
  lessons: string[];
  tags: string[];
  execution_quality_score?: number;
  risk_management_assessment: string;
  ai_disclaimer: string;
}

export interface AIStrategyAnalysisResponse {
  strategy_id: string;
  strategy_name: string;
  strategy_version: string;
  timestamp: string;
  performance_summary: string;
  strengths: string[];
  weaknesses: string[];
  identified_issues: string[];
  evidence: string[];
  improvement_suggestions: string[];
  ai_disclaimer: string;
}

export interface QuantitativeMetrics {
  initial_balance: number;
  final_equity: number;
  net_profit: number;
  net_profit_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  profit_factor: number;
  average_win: number;
  average_loss: number;
  win_loss_ratio: number;
  expectancy: number;
  max_drawdown_amount: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  total_commission_paid: number;
  total_slippage_cost: number;
}

export interface ValidationPipelineResult {
  proposal_id: string;
  status: string;
  all_stages_passed: boolean;
  backtest: QuantitativeMetrics;
  out_of_sample: {
    passed: boolean;
    split_ratio: number;
    in_sample: Record<string, number>;
    out_of_sample: Record<string, number>;
    retention: { pf_retention_pct: number; sharpe_retention_pct: number };
    warnings: string[];
  };
  walk_forward: {
    passed: boolean;
    windows_count: number;
    consistency_score_pct: number;
    walk_forward_efficiency_pct: number;
    cumulative_oos_profit: number;
    cumulative_is_profit: number;
    windows: any[];
  };
  monte_carlo: {
    passed: boolean;
    simulations_count: number;
    risk_of_ruin_pct: number;
    drawdown_confidence_intervals: Record<string, number>;
    profit_confidence_intervals: Record<string, number>;
  };
  sensitivity_stress: {
    passed: boolean;
    baseline: Record<string, number>;
    perturbation_analysis: any[];
    execution_stress: any;
  };
  risk_validation: {
    passed: boolean;
    status: string;
    rules_applied: Record<string, any>;
    checks: Array<{ name: string; required: string; actual: string; passed: boolean }>;
    summary: string;
  };
}

export interface AIStrategyProposal {
  id?: string;
  strategy_id: string;
  base_strategy_name: string;
  base_strategy_version: string;
  proposed_version: string;
  timestamp: string;
  identified_issue: string;
  evidence: string[];
  hypothesis: string;
  proposed_change: string;
  expected_purpose: string;
  validation_required: boolean;
  status:
    | 'DRAFT'
    | 'AI_PROPOSED'
    | 'BACKTEST_PENDING'
    | 'BACKTESTED'
    | 'OUT_OF_SAMPLE'
    | 'WALK_FORWARD'
    | 'MONTE_CARLO'
    | 'RISK_VALIDATION'
    | 'APPROVAL_REQUIRED'
    | 'APPROVED'
    | 'REJECTED'
    | 'DEPLOYED';
  backtest_result?: any;
  oos_result?: any;
  walkforward_result?: any;
  montecarlo_result?: any;
  risk_validation_result?: any;
  data_provenance?: 'REAL_MT5' | 'IMPORTED_HISTORICAL' | 'SYNTHETIC_TEST' | string;
  production_eligible?: boolean;
  live_deployment_eligible?: boolean;
  strategy_snapshot?: any;
  approved_by?: string;

  approved_at?: string;
  rejected_reason?: string;
  created_at?: string;
  ai_disclaimer?: string;
}

export interface AIAuditLog {
  id: string;
  account_id?: string;
  agent_type: string;
  model: string;
  input_summary?: string;
  output_summary?: string;
  tools_used?: string[];
  duration_ms?: number;
  error?: string;
  related_trade_id?: string;
  related_strategy_id?: string;
  created_at: string;
}


