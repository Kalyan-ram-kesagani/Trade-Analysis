-- ====================================================================
-- AI Layer Database Schema Extension
-- Additive only — does NOT modify any existing tables.
-- ====================================================================

-- 9. AI Audit Logs (Every AI request is auditable)
CREATE TABLE IF NOT EXISTS ai_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES trading_accounts(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    tools_used TEXT[] DEFAULT '{}',
    duration_ms INT,
    error TEXT,
    related_trade_id UUID REFERENCES trades(id) ON DELETE SET NULL,
    related_strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_audit_account_id ON ai_audit_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_ai_audit_agent_type ON ai_audit_logs(agent_type);
CREATE INDEX IF NOT EXISTS idx_ai_audit_created_at ON ai_audit_logs(created_at DESC);

-- 10. Strategy Proposals (AI-generated improvement proposals with lifecycle)
CREATE TABLE IF NOT EXISTS strategy_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    account_id UUID REFERENCES trading_accounts(id) ON DELETE SET NULL,
    base_strategy_name VARCHAR(100) NOT NULL,
    base_strategy_version VARCHAR(20) NOT NULL,
    proposed_version VARCHAR(20) NOT NULL,
    identified_issue TEXT NOT NULL,
    evidence JSONB DEFAULT '[]'::jsonb,
    hypothesis TEXT NOT NULL,
    proposed_change TEXT NOT NULL,
    expected_purpose TEXT,
    status VARCHAR(30) DEFAULT 'AI_PROPOSED'
        CHECK (status IN (
            'DRAFT', 'AI_PROPOSED',
            'BACKTEST_PENDING', 'BACKTESTED',
            'OUT_OF_SAMPLE', 'WALK_FORWARD',
            'MONTE_CARLO', 'RISK_VALIDATION',
            'APPROVAL_REQUIRED', 'APPROVED',
            'REJECTED', 'DEPLOYED'
        )),
    validation_required BOOLEAN DEFAULT TRUE,
    backtest_result JSONB,
    oos_result JSONB,
    walkforward_result JSONB,
    montecarlo_result JSONB,
    risk_validation_result JSONB,
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_strategy_proposals_strategy_id ON strategy_proposals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_proposals_status ON strategy_proposals(status);
CREATE INDEX IF NOT EXISTS idx_strategy_proposals_created_at ON strategy_proposals(created_at DESC);

-- 11. Backtest Runs (Detailed record of deterministic backtests and validation runs)
CREATE TABLE IF NOT EXISTS backtest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES strategy_proposals(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    account_id UUID REFERENCES trading_accounts(id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    initial_balance NUMERIC(15, 2) NOT NULL DEFAULT 10000.00,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    trades_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    equity_curve JSONB NOT NULL DEFAULT '[]'::jsonb,
    drawdown_curve JSONB NOT NULL DEFAULT '[]'::jsonb,
    execution_assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_stage VARCHAR(30) DEFAULT 'BACKTEST',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy_id ON backtest_runs(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_proposal_id ON backtest_runs(proposal_id);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at ON backtest_runs(created_at DESC);

-- Add provenance columns if not exists
ALTER TABLE strategy_proposals ADD COLUMN IF NOT EXISTS data_provenance VARCHAR(30) DEFAULT 'REAL_MT5';
ALTER TABLE strategy_proposals ADD COLUMN IF NOT EXISTS production_eligible BOOLEAN DEFAULT FALSE;
ALTER TABLE strategy_proposals ADD COLUMN IF NOT EXISTS live_deployment_eligible BOOLEAN DEFAULT FALSE;
ALTER TABLE strategy_proposals ADD COLUMN IF NOT EXISTS risk_policy_version VARCHAR(20) DEFAULT 'v1.0';
ALTER TABLE strategy_proposals ADD COLUMN IF NOT EXISTS strategy_snapshot JSONB DEFAULT '{}'::jsonb;

ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS data_provenance VARCHAR(30) DEFAULT 'REAL_MT5';
ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS production_eligible BOOLEAN DEFAULT FALSE;
ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS integrity_check_passed BOOLEAN DEFAULT TRUE;
ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS risk_policy_version VARCHAR(20) DEFAULT 'v1.0';

-- 12. Strategy Deployments (Per-account live deployment audit records)
CREATE TABLE IF NOT EXISTS strategy_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES strategy_proposals(id) ON DELETE CASCADE,
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES trading_accounts(id) ON DELETE CASCADE,
    deployed_version VARCHAR(20) NOT NULL,
    deployed_by VARCHAR(100) NOT NULL,
    live_risk_percentage NUMERIC(5, 2) DEFAULT 1.00,
    status VARCHAR(30) DEFAULT 'DEPLOYED',
    strategy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13. Automatic AI Journaling Extensions
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS journal_type VARCHAR(50) DEFAULT 'MANUAL';
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'COMPLETED';
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(50);
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS ai_model VARCHAR(100);
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(50);
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS structured_ai_output JSONB;
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS ai_confidence NUMERIC(3, 2);
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS error_info TEXT;
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS retry_count INT DEFAULT 0;
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS generated_at TIMESTAMP WITH TIME ZONE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_trade_ai_type 
    ON journal_entries(trade_id, journal_type) 
    WHERE trade_id IS NOT NULL AND journal_type = 'AI_TRADE_REVIEW';

CREATE INDEX IF NOT EXISTS idx_journal_status ON journal_entries(status);


