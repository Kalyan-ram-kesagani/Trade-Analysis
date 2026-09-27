import React, { useState, useEffect } from 'react';
import { useTrading } from '../context/TradingContext';
import { TradingAPI } from '../services/api';
import {
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Archive,
  Layers,
  Shield,
  Clock,
  Sparkles,
  ChevronRight,
  TrendingUp,
  RefreshCw,
  FlaskConical,
  ShieldCheck,
  Check,
  X,
  FileText,
  Sliders,
} from 'lucide-react';
import { Strategy, AIStrategyAnalysisResponse, AIStrategyProposal } from '../types/trading';

export const StrategiesPage: React.FC = () => {
  const { strategies, isAllAccounts, activeAccount, selectedAccountId, theme } = useTrading();
  const isDark = theme === 'dark';
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy>(strategies[0]);

  // AI Strategy states
  const [aiAnalysis, setAiAnalysis] = useState<AIStrategyAnalysisResponse | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [aiProposal, setAiProposal] = useState<AIStrategyProposal | null>(null);
  const [loadingProposal, setLoadingProposal] = useState(false);
  const [proposalsList, setProposalsList] = useState<AIStrategyProposal[]>([]);
  const [focusArea, setFocusArea] = useState<string>('General Risk & Drawdown');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Quantitative Validation Pipeline states
  const [validatingProposalId, setValidatingProposalId] = useState<string | null>(null);
  const [selectedProposalDetail, setSelectedProposalDetail] = useState<AIStrategyProposal | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchProposals = async (stratId: string) => {
    try {
      const list = await TradingAPI.getStrategyProposals(stratId);
      setProposalsList(list);
    } catch {
      // Ignore if database has no proposals yet
    }
  };

  useEffect(() => {
    if (selectedStrategy?.id) {
      setAiAnalysis(null);
      setAiProposal(null);
      setSelectedProposalDetail(null);
      fetchProposals(selectedStrategy.id);
    }
  }, [selectedStrategy?.id]);

  const handleRunDiagnostic = async () => {
    if (!selectedStrategy) return;
    setLoadingAnalysis(true);
    setStatusMessage(null);
    try {
      const accountId = isAllAccounts ? activeAccount?.id : selectedAccountId;
      const res = await TradingAPI.analyzeStrategyWithAI(selectedStrategy.id, accountId);
      setAiAnalysis(res);
    } catch (err: any) {
      setStatusMessage(`Diagnostic failed: ${err.message}`);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleGenerateProposal = async () => {
    if (!selectedStrategy) return;
    setLoadingProposal(true);
    setStatusMessage(null);
    try {
      const accountId = isAllAccounts ? activeAccount?.id : selectedAccountId;
      const res = await TradingAPI.proposeStrategyImprovementWithAI(
        selectedStrategy.id,
        accountId,
        focusArea
      );
      setAiProposal(res);
      await fetchProposals(selectedStrategy.id);
    } catch (err: any) {
      setStatusMessage(`Proposal generation failed: ${err.message}`);
    } finally {
      setLoadingProposal(false);
    }
  };

  const handleRunValidationPipeline = async (proposalId: string) => {
    setValidatingProposalId(proposalId);
    setStatusMessage('Executing quantitative pipeline: Backtest -> OOS -> Walk-Forward -> Monte Carlo -> Risk Gates...');
    try {
      const res = await TradingAPI.validateProposal(proposalId);
      setStatusMessage(`Validation complete: Status is now ${res.status}`);
      if (selectedStrategy?.id) {
        await fetchProposals(selectedStrategy.id);
      }
      if (aiProposal && aiProposal.id === proposalId) {
        setAiProposal({
          ...aiProposal,
          status: res.status,
          backtest_result: res.backtest,
          oos_result: res.out_of_sample,
          walkforward_result: res.walk_forward,
          montecarlo_result: res.monte_carlo,
          risk_validation_result: res.risk_validation,
        });
      }
    } catch (err: any) {
      setStatusMessage(`Quantitative validation failed: ${err.message}`);
    } finally {
      setValidatingProposalId(null);
    }
  };

  const handleApproveProposal = async (proposalId: string) => {
    setActionLoading(true);
    try {
      await TradingAPI.approveProposal(proposalId, 'Chief Risk Officer');
      setStatusMessage('Proposal successfully authorized by Human Gatekeeper.');
      if (selectedStrategy?.id) {
        await fetchProposals(selectedStrategy.id);
      }
    } catch (err: any) {
      setStatusMessage(`Approval failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeployProposal = async (proposalId: string) => {
    setActionLoading(true);
    try {
      const targetAccId = isAllAccounts ? (activeAccount?.id || strategies[0]?.account_ids?.[0]) : selectedAccountId;
      if (!targetAccId) {
        setStatusMessage('Error: No target trading account selected for deployment.');
        setActionLoading(false);
        return;
      }
      const res = await TradingAPI.deployProposal(proposalId, 'Lead Algorithmic Trader', [targetAccId], 1.0);
      setStatusMessage(res.message || 'Strategy evolved and deployed to live production.');
      if (selectedStrategy?.id) {
        await fetchProposals(selectedStrategy.id);
      }
    } catch (err: any) {
      setStatusMessage(`Deployment failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-200">
      {/* Header */}
      <div
        className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b ${
          isDark ? 'border-slate-800/80' : 'border-slate-200'
        }`}
      >
        <div>
          <div className="flex items-center gap-3">
            <h1 className={`text-xl sm:text-2xl font-bold tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
              Automated Trading Strategies
            </h1>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded border ${
                isDark
                  ? 'text-slate-400 bg-slate-900 border-slate-800'
                  : 'text-slate-600 bg-slate-100 border-slate-200'
              }`}
            >
              {strategies.length} algorithms deployed
            </span>
          </div>
          <p className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Algorithmic rule sets, risk thresholds, version revisions, and execution metrics
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {isAllAccounts ? (
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border ${
                isDark
                  ? 'bg-slate-900 border-slate-800 text-slate-300'
                  : 'bg-white border-slate-200 text-slate-700 shadow-2xs'
              }`}
            >
              <Layers className="w-3.5 h-3.5 text-emerald-500" />
              <span>Multi-Account Strategies</span>
            </div>
          ) : (
            <div
              className={`px-3 py-1.5 rounded-md border ${
                isDark
                  ? 'bg-slate-900 border-slate-800 text-slate-300'
                  : 'bg-white border-slate-200 text-slate-700 shadow-2xs'
              }`}
            >
              Account: <strong className={isDark ? 'text-white' : 'text-slate-900'}>{activeAccount?.account_name}</strong>
            </div>
          )}
        </div>
      </div>

      {/* Strategies Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {strategies.map((strat: Strategy) => {
          const isSelected = selectedStrategy?.id === strat.id;
          const isActive = strat.status === 'active';
          const isTesting = strat.status === 'testing';

          return (
            <div
              key={strat.id}
              onClick={() => setSelectedStrategy(strat)}
              className={`p-5 rounded-lg border transition-all cursor-pointer flex flex-col justify-between
                ${
                  isSelected
                    ? isDark
                      ? 'bg-slate-900/90 border-emerald-500/50 shadow-md ring-1 ring-emerald-500/20'
                      : 'bg-white border-emerald-500 shadow-md ring-1 ring-emerald-500/30'
                    : isDark
                    ? 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                    : 'bg-white border-slate-200 hover:border-slate-300 shadow-xs'
                }
              `}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <h3 className={`text-sm font-semibold tracking-tight flex items-center gap-1.5 ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      <span>{strat.name}</span>
                      <span className={`text-xs font-mono ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{strat.version}</span>
                    </h3>
                  </div>

                  <span
                    className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded tracking-wider ${
                      isActive
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                        : isTesting
                        ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                        : isDark
                        ? 'bg-slate-800 text-slate-400 border border-slate-700'
                        : 'bg-slate-100 text-slate-600 border border-slate-200'
                    }`}
                  >
                    {strat.status}
                  </span>
                </div>

                <p className={`text-xs line-clamp-2 mb-4 leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {strat.description}
                </p>

                <div
                  className={`grid grid-cols-2 gap-2 text-xs p-3 rounded border mb-3 ${
                    isDark
                      ? 'bg-slate-950/60 border-slate-800/80'
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div>
                    <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Win Rate</span>
                    <span className="font-semibold font-mono text-emerald-500 tabular-nums">
                      {strat.win_rate}%
                    </span>
                  </div>
                  <div>
                    <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Net P&L</span>
                    <span
                      className={`font-semibold font-mono tabular-nums ${
                        strat.profit_loss >= 0 ? 'text-emerald-500' : 'text-rose-500'
                      }`}
                    >
                      {strat.profit_loss >= 0 ? '+' : ''}${strat.profit_loss.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Max DD</span>
                    <span className="font-mono text-amber-500 tabular-nums">
                      {strat.max_drawdown}%
                    </span>
                  </div>
                  <div>
                    <span className={`text-[10px] block ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Trades</span>
                    <span className={`font-mono tabular-nums ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                      {strat.total_trades}
                    </span>
                  </div>
                </div>
              </div>

              <div className={`flex items-center justify-between pt-2 border-t text-[11px] ${isDark ? 'border-slate-800 text-slate-400' : 'border-slate-200 text-slate-500'}`}>
                <span>Created {strat.created_date}</span>
                <span className="text-emerald-500 font-medium flex items-center gap-1">
                  View Specs <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Strategy Deep-Dive Details */}
      {selectedStrategy && (
        <div
          className={`p-4 sm:p-6 rounded-lg border space-y-6 transition-colors ${
            isDark
              ? 'bg-slate-900/60 border-slate-800'
              : 'bg-white border-slate-200 shadow-xs'
          }`}
        >
          <div
            className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b ${
              isDark ? 'border-slate-800' : 'border-slate-200'
            }`}
          >
            <div>
              <div className="flex items-center gap-2.5">
                <Cpu className="w-5 h-5 text-emerald-500" />
                <h2 className={`text-base font-bold tracking-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  {selectedStrategy.name} ({selectedStrategy.version})
                </h2>
              </div>
              <p className={`text-xs mt-1 max-w-2xl ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                {selectedStrategy.description}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Status:</span>
              <span
                className={`text-xs font-semibold px-2.5 py-1 rounded uppercase tracking-wider border ${
                  isDark
                    ? 'bg-slate-800 text-slate-200 border-slate-700'
                    : 'bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                {selectedStrategy.status}
              </span>
            </div>
          </div>

          {/* Strategy Rules & Risk Parameters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            {/* Rules */}
            <div className="space-y-3">
              <h3 className={`text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                Algorithmic Execution Rules
              </h3>
              <div
                className={`p-4 rounded-lg border space-y-2 ${
                  isDark
                    ? 'bg-slate-950/60 border-slate-800/80'
                    : 'bg-slate-50 border-slate-200'
                }`}
              >
                {selectedStrategy.rules.map((rule, idx) => (
                  <div key={idx} className={`flex items-start gap-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                    <span className="font-mono text-emerald-500 font-semibold">{idx + 1}.</span>
                    <span className="leading-relaxed">{rule}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Risk Parameters */}
            <div className="space-y-3">
              <h3 className={`text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                <Shield className="w-4 h-4 text-emerald-500" />
                Risk Parameters & Protection
              </h3>
              <div
                className={`p-4 rounded-lg border space-y-2.5 ${
                  isDark
                    ? 'bg-slate-950/60 border-slate-800/80'
                    : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Max Risk Per Trade:</span>
                  <span className={`font-mono font-medium ${isDark ? 'text-white' : 'text-slate-900'}`}>
                    {selectedStrategy.risk_parameters.max_risk_per_trade}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Max Daily Drawdown:</span>
                  <span className="font-mono font-medium text-amber-500">
                    {selectedStrategy.risk_parameters.max_daily_drawdown}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Target Risk-to-Reward:</span>
                  <span className="font-mono font-medium text-emerald-500">
                    {selectedStrategy.risk_parameters.rr_target}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Breakeven (Risk-Free) Trigger:</span>
                  <span className={`font-mono font-medium ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                    {selectedStrategy.risk_parameters.breakeven_trigger}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Version History */}
          <div className="space-y-3 pt-2">
            <h3 className={`text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
              <Clock className="w-4 h-4 text-slate-400" />
              Version Revision History
            </h3>
            <div
              className={`divide-y border rounded-lg overflow-hidden text-xs ${
                isDark
                  ? 'divide-slate-800/80 border-slate-800 bg-slate-950/40'
                  : 'divide-slate-200 border-slate-200 bg-slate-50'
              }`}
            >
              {selectedStrategy.version_history.map((vh, i) => (
                <div key={i} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`font-mono font-bold px-2 py-0.5 rounded border ${
                        isDark
                          ? 'text-white bg-slate-800 border-slate-700'
                          : 'text-slate-900 bg-white border-slate-300'
                      }`}
                    >
                      {vh.version}
                    </span>
                    <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>{vh.changes}</span>
                  </div>
                  <span className={`text-[11px] font-mono whitespace-nowrap ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {vh.date}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* AI Strategy Intelligence & Evolution Panel */}
          <div
            className={`p-5 rounded-lg border space-y-5 transition-colors ${
              isDark
                ? 'border-slate-800 bg-slate-900/40'
                : 'border-slate-200 bg-white shadow-xs'
            }`}
          >
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/40">
              <div className="flex items-center gap-3">
                <div
                  className={`p-2.5 rounded-lg border ${
                    isDark
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : 'bg-emerald-50 border-emerald-200 text-emerald-600'
                  }`}
                >
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      AI Strategy Evolution & Optimization
                    </h3>
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                      Advisory Mode
                    </span>
                  </div>
                  <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    Autonomous weakness detection, testable hypothesis formulation, and gated proposal pipelines
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={handleRunDiagnostic}
                  disabled={loadingAnalysis}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all cursor-pointer ${
                    isDark
                      ? 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
                      : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingAnalysis ? 'animate-spin text-emerald-400' : ''}`} />
                  <span>{loadingAnalysis ? 'Diagnosing...' : 'Run AI Diagnostic'}</span>
                </button>
              </div>
            </div>

            {statusMessage && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
                <span>{statusMessage}</span>
                <button onClick={() => setStatusMessage(null)} className="cursor-pointer text-slate-400 hover:text-white">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Advisory Safety Banner */}
            <div className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
              isDark ? 'bg-amber-500/5 border-amber-500/20 text-amber-300' : 'bg-amber-50 border-amber-200 text-amber-900'
            }`}>
              <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-[11px] uppercase tracking-wider text-amber-400">
                  Strict Risk Gate & Advisory Constraint
                </span>
                <p className="text-[11px] leading-relaxed mt-0.5">
                  The AI functions strictly in an advisory capacity. Live strategies cannot be automatically modified. All proposed changes are treated as research hypotheses and require complete backtesting, out-of-sample validation, and human sign-off.
                </p>
              </div>
            </div>

            {/* Diagnostic Results Section (if loaded) */}
            {aiAnalysis && (
              <div className={`p-4 rounded-lg border space-y-4 animate-in fade-in-50 duration-200 ${
                isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-emerald-400" />
                    <h4 className={`text-xs font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      Diagnostic: {aiAnalysis.strategy_name} ({aiAnalysis.strategy_version})
                    </h4>
                  </div>
                  <span className={`text-[10px] font-mono ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                    {new Date(aiAnalysis.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <p className={`text-xs leading-relaxed ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  {aiAnalysis.performance_summary}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {aiAnalysis.strengths && aiAnalysis.strengths.length > 0 && (
                    <div className={`p-3 rounded-lg border ${isDark ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-white border-slate-200'}`}>
                      <span className="font-semibold text-emerald-400 block mb-1.5 text-[11px] uppercase tracking-wider">
                        Observed Strengths
                      </span>
                      <ul className="space-y-1 list-disc list-inside text-[11px] text-slate-300">
                        {aiAnalysis.strengths.map((s, i) => (
                          <li key={i} className="leading-relaxed">{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {aiAnalysis.weaknesses && aiAnalysis.weaknesses.length > 0 && (
                    <div className={`p-3 rounded-lg border ${isDark ? 'bg-rose-500/5 border-rose-500/20' : 'bg-white border-slate-200'}`}>
                      <span className="font-semibold text-rose-400 block mb-1.5 text-[11px] uppercase tracking-wider">
                        Vulnerabilities & Weaknesses
                      </span>
                      <ul className="space-y-1 list-disc list-inside text-[11px] text-slate-300">
                        {aiAnalysis.weaknesses.map((w, i) => (
                          <li key={i} className="leading-relaxed">{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {aiAnalysis.improvement_suggestions && aiAnalysis.improvement_suggestions.length > 0 && (
                  <div className={`p-3 rounded-lg border ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                    <span className="font-semibold text-blue-400 block mb-1.5 text-[11px] uppercase tracking-wider">
                      Targeted Improvement Suggestions
                    </span>
                    <ul className="space-y-1 list-disc list-inside text-[11px] text-slate-300">
                      {aiAnalysis.improvement_suggestions.map((sug, i) => (
                        <li key={i} className="leading-relaxed">{sug}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Proposal Formulation Generator Box */}
            <div className={`p-4 rounded-lg border space-y-3 ${
              isDark ? 'bg-slate-950/40 border-slate-800' : 'bg-slate-50 border-slate-200'
            }`}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h4 className={`text-xs font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                    Formulate AI Improvement Proposal
                  </h4>
                  <p className={`text-[11px] ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    Generate an audited parameter hypothesis with full validation gates
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={focusArea}
                    onChange={(e) => setFocusArea(e.target.value)}
                    className={`text-xs px-2.5 py-1.5 rounded-lg border focus:outline-hidden ${
                      isDark
                        ? 'bg-slate-900 border-slate-700 text-white'
                        : 'bg-white border-slate-300 text-slate-800'
                    }`}
                  >
                    <option value="General Risk & Drawdown">Focus: Risk & Drawdown</option>
                    <option value="Stop Loss & Breakeven Trigger">Focus: Breakeven / SL</option>
                    <option value="Win Rate & Edge Quality">Focus: Win Rate & Edge</option>
                    <option value="Market Regime Adaptability">Focus: Volatility Regimes</option>
                  </select>

                  <button
                    type="button"
                    onClick={handleGenerateProposal}
                    disabled={loadingProposal}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg transition-all shadow-2xs cursor-pointer"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${loadingProposal ? 'animate-spin' : ''}`} />
                    <span>{loadingProposal ? 'Formulating...' : 'Generate Proposal'}</span>
                  </button>
                </div>
              </div>

              {/* Newly Generated Proposal Card */}
              {aiProposal && (
                <div className={`p-4 mt-3 rounded-lg border space-y-3 animate-in fade-in-50 duration-200 ${
                  isDark ? 'bg-slate-900 border-emerald-500/30' : 'bg-white border-emerald-300 shadow-xs'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold font-mono text-emerald-400">
                        {aiProposal.base_strategy_name}
                      </span>
                      <span className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                        isDark ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-slate-100 border-slate-200 text-slate-700'
                      }`}>
                        {aiProposal.base_strategy_version} → {aiProposal.proposed_version}
                      </span>
                    </div>

                    <span className={`text-[10px] uppercase font-bold font-mono px-2.5 py-1 rounded border ${
                      aiProposal.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                      aiProposal.status === 'REJECTED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                      aiProposal.status === 'BACKTEST_PENDING' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                      'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {aiProposal.status}
                    </span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <span className={`block text-[11px] font-semibold ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                        Identified Issue:
                      </span>
                      <p className={`mt-0.5 ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                        {aiProposal.identified_issue}
                      </p>
                    </div>

                    <div>
                      <span className={`block text-[11px] font-semibold ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                        Hypothesis:
                      </span>
                      <p className={`mt-0.5 leading-relaxed ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                        {aiProposal.hypothesis}
                      </p>
                    </div>

                    <div>
                      <span className={`block text-[11px] font-semibold text-emerald-400`}>
                        Proposed Parameter Modification:
                      </span>
                      <p className={`mt-0.5 p-2 rounded border font-mono text-[11px] ${
                        isDark ? 'bg-slate-950/80 border-slate-800 text-emerald-300' : 'bg-slate-50 border-slate-200 text-emerald-700'
                      }`}>
                        {aiProposal.proposed_change}
                      </p>
                    </div>
                  </div>

                  {aiProposal.id && (
                    <div className="space-y-3 pt-2 border-t border-slate-800/60">
                      {/* Quantitative Validation Pipeline Trigger */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-[11px] text-slate-400">
                          {aiProposal.status === 'AI_PROPOSED' && 'Status: Ready for Deterministic Quantitative Validation'}
                          {aiProposal.status === 'APPROVAL_REQUIRED' && 'Passed all quantitative stages. Human authorization required.'}
                          {aiProposal.status === 'APPROVED' && 'Authorized. Ready for version deployment to live algorithms.'}
                          {aiProposal.status === 'DEPLOYED' && 'Deployed. Algorithm is actively executing with this version.'}
                          {aiProposal.status === 'REJECTED' && 'Rejected. Does not meet safety or edge criteria.'}
                        </div>

                        <div className="flex items-center gap-2">
                          {(aiProposal.status === 'AI_PROPOSED' || aiProposal.status === 'BACKTEST_PENDING') && (
                            <button
                              type="button"
                              onClick={() => handleRunValidationPipeline(aiProposal.id!)}
                              disabled={validatingProposalId === aiProposal.id}
                              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition-colors cursor-pointer shadow-2xs"
                            >
                              <FlaskConical className={`w-3.5 h-3.5 ${validatingProposalId === aiProposal.id ? 'animate-spin' : ''}`} />
                              <span>{validatingProposalId === aiProposal.id ? 'Validating Pipeline...' : 'Run Quantitative Pipeline'}</span>
                            </button>
                          )}

                          {aiProposal.status === 'APPROVAL_REQUIRED' && (
                            <button
                              type="button"
                              onClick={() => handleApproveProposal(aiProposal.id!)}
                              disabled={actionLoading}
                              className="flex items-center gap-1 px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors cursor-pointer shadow-2xs"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Authorize Approval</span>
                            </button>
                          )}

                          {aiProposal.status === 'APPROVED' && (
                            <button
                              type="button"
                              onClick={() => handleDeployProposal(aiProposal.id!)}
                              disabled={actionLoading}
                              className="flex items-center gap-1 px-3.5 py-1.5 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 rounded-lg transition-colors cursor-pointer shadow-2xs"
                            >
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span>Deploy to Live</span>
                            </button>
                          )}

                          {aiProposal.status !== 'REJECTED' && aiProposal.status !== 'DEPLOYED' && (
                            <button
                              type="button"
                              onClick={() => handleRunValidationPipeline(aiProposal.id!)}
                              className="flex items-center gap-1 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-md transition-colors cursor-pointer"
                              title="Re-run validation"
                            >
                              <RefreshCw className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Quantitative Results Card (if validated) */}
                      {aiProposal.backtest_result && (
                        <div className={`p-3 rounded-lg border text-xs space-y-2.5 ${
                          isDark ? 'bg-slate-950/80 border-blue-500/30' : 'bg-blue-50/50 border-blue-200'
                        }`}>
                          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                            <span className="font-semibold text-blue-400 flex items-center gap-1.5">
                              <FlaskConical className="w-3.5 h-3.5" />
                              Deterministic Quantitative Verification
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">Zero AI Math • Pure Python Engine</span>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                              <span className="text-slate-400 block text-[10px]">Net Profit</span>
                              <span className={`font-mono font-bold ${(aiProposal.backtest_result.net_profit ?? aiProposal.backtest_result.metrics?.net_profit ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                ${(aiProposal.backtest_result.net_profit ?? aiProposal.backtest_result.metrics?.net_profit ?? 0).toFixed(2)}
                              </span>
                            </div>
                            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                              <span className="text-slate-400 block text-[10px]">Profit Factor</span>
                              <span className="font-mono font-bold text-slate-200">
                                {(aiProposal.backtest_result.profit_factor ?? aiProposal.backtest_result.metrics?.profit_factor ?? 0).toFixed(2)}
                              </span>
                            </div>
                            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                              <span className="text-slate-400 block text-[10px]">Max Drawdown</span>
                              <span className="font-mono font-bold text-rose-400">
                                {(aiProposal.backtest_result.max_drawdown_pct ?? aiProposal.backtest_result.metrics?.max_drawdown_pct ?? 0).toFixed(2)}%
                              </span>
                            </div>
                            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                              <span className="text-slate-400 block text-[10px]">Sharpe Ratio</span>
                              <span className="font-mono font-bold text-slate-200">
                                {(aiProposal.backtest_result.sharpe_ratio ?? aiProposal.backtest_result.metrics?.sharpe_ratio ?? 0).toFixed(2)}
                              </span>
                            </div>
                          </div>

                          {/* Multi-Stage Pass/Fail Chips */}
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {/* Provenance Badge */}
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono border font-semibold ${
                              aiProposal.data_provenance === 'REAL_MT5' 
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            }`}>
                              Source: {aiProposal.data_provenance || 'REAL_MT5'}
                            </span>

                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                              aiProposal.oos_result?.passed ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}>
                              OOS (70/30): {aiProposal.oos_result?.passed ? 'PASSED' : 'CHECK'}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                              aiProposal.walkforward_result?.passed ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}>
                              Walk-Forward: {aiProposal.walkforward_result?.consistency_score_pct ?? 0}% Consistency
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                              aiProposal.montecarlo_result?.passed ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}>
                              Monte Carlo Ruin: {aiProposal.montecarlo_result?.risk_of_ruin_pct ?? 0}%
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                              aiProposal.risk_validation_result?.passed ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            }`}>
                              Risk Gate: {aiProposal.risk_validation_result?.passed ? 'APPROVED' : 'VIOLATION'}
                            </span>
                          </div>

                          {/* Synthetic Notice or Sample Adequacy warning */}
                          {aiProposal.data_provenance === 'SYNTHETIC_TEST' && (
                            <div className="p-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-medium flex items-center gap-1.5">
                              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                              <span>Development/Test Data — Not Eligible for Live Deployment.</span>
                            </div>
                          )}
                          {aiProposal.risk_validation_result?.sample_adequacy === 'LOW' && (
                            <div className="p-2 rounded bg-blue-500/10 border border-blue-500/20 text-slate-300 text-[11px]">
                              <span className="font-semibold text-blue-400">Sample Depth Notice: </span>
                              {aiProposal.risk_validation_result.sample_description}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Historical Proposals List */}
            {proposalsList.length > 0 && (
              <div>
                <h4 className={`text-xs font-semibold uppercase tracking-wider mb-2.5 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  Strategy Proposal Audit History ({proposalsList.length})
                </h4>
                <div className="space-y-2">
                  {proposalsList.map((p) => (
                    <div
                      key={p.id || p.timestamp}
                      className={`p-3 rounded-lg border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isDark ? 'bg-slate-950/40 border-slate-800' : 'bg-white border-slate-200 shadow-2xs'
                      }`}
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{p.proposed_version}</span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                            p.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            p.status === 'DEPLOYED' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
                            p.status === 'APPROVAL_REQUIRED' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                            p.status === 'REJECTED' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                            'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          }`}>
                            {p.status}
                          </span>
                          <span className={`text-[10px] ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                            {p.created_at ? new Date(p.created_at).toLocaleDateString() : ''}
                          </span>
                        </div>
                        <p className={`text-[11px] ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                          {p.proposed_change}
                        </p>
                      </div>

                      {p.id && (
                        <div className="flex items-center gap-1.5 shrink-0">
                          {p.status === 'AI_PROPOSED' && (
                            <button
                              type="button"
                              onClick={() => handleRunValidationPipeline(p.id!)}
                              disabled={validatingProposalId === p.id}
                              className="px-2.5 py-1 text-[11px] font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded transition-colors cursor-pointer"
                            >
                              {validatingProposalId === p.id ? 'Validating...' : 'Validate'}
                            </button>
                          )}
                          {p.status === 'APPROVAL_REQUIRED' && (
                            <button
                              type="button"
                              onClick={() => handleApproveProposal(p.id!)}
                              className="px-2.5 py-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded transition-colors cursor-pointer"
                            >
                              Approve
                            </button>
                          )}
                          {p.status === 'APPROVED' && (
                            <button
                              type="button"
                              onClick={() => handleDeployProposal(p.id!)}
                              className="px-2.5 py-1 text-[11px] font-semibold text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded transition-colors cursor-pointer"
                            >
                              Deploy
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
