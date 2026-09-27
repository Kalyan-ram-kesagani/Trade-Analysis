import React, { useState } from 'react';
import { useTrading } from '../context/TradingContext';
import { MetricCard } from '../components/dashboard/MetricCard';
import { TradingAPI } from '../services/api';
import { AIAnalysisResponse } from '../types/trading';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Sparkles,
  PieChart,
  Shield,
  Layers,
  Percent,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Info,
  ShieldAlert,
  Bot,
  Compass,
} from 'lucide-react';

export const AnalysisPage: React.FC = () => {
  const { trades, metrics, isAllAccounts, activeAccount, theme } = useTrading();
  const isDark = theme === 'dark';

  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [loadingAi, setLoadingAi] = useState<boolean>(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const handleRunAiAnalysis = async () => {
    const targetAccountId = isAllAccounts ? (activeAccount?.id || 'all') : activeAccount?.id;
    if (!targetAccountId) return;
    setLoadingAi(true);
    setAiError(null);
    try {
      const result = await TradingAPI.getAIAnalysis(targetAccountId);
      setAiAnalysis(result);
    } catch (err: any) {
      setAiError(err.message || 'Failed to run AI analysis');
    } finally {
      setLoadingAi(false);
    }
  };

  // Winning vs losing trade analysis
  const wins = trades.filter((t) => t.status === 'WIN');
  const losses = trades.filter((t) => t.status === 'LOSS');

  const avgWin = wins.length > 0 ? wins.reduce((sum, w) => sum + w.net_pl, 0) / wins.length : 0;
  const avgLoss = losses.length > 0 ? Math.abs(losses.reduce((sum, l) => sum + l.net_pl, 0) / losses.length) : 0;
  const winLossRatio =
  avgWin > 0 && avgLoss > 0
    ? (avgWin / avgLoss).toFixed(2)
    : null;

const completedTrades = wins.length + losses.length;

const lossRate =
  completedTrades > 0
    ? (losses.length / completedTrades) * 100
    : null;

  // Symbol distribution
  const symbolStats = trades.reduce((acc, t) => {
    if (!acc[t.symbol]) {
      acc[t.symbol] = { count: 0, pl: 0, wins: 0 };
    }
    acc[t.symbol].count += 1;
    acc[t.symbol].pl += t.net_pl;
    if (t.status === 'WIN') acc[t.symbol].wins += 1;
    return acc;
  }, {} as Record<string, { count: number; pl: number; wins: number }>);

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
              Trading Performance Analytics
            </h1>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded border ${
                isDark
                  ? 'text-slate-400 bg-slate-900 border-slate-800'
                  : 'text-slate-600 bg-slate-100 border-slate-200'
              }`}
            >
              {trades.length} sample trades
            </span>
          </div>
          <p className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Statistical breakdown of edge expectancy, risk distribution, and execution consistency
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
              <span>Multi-Account Aggregated</span>
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

      {/* Primary Analytics KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <MetricCard
          label="Profit Factor"
          value={metrics.profitFactor}
          subvalue="Gross profit / Gross loss"
          trend={metrics.profitFactor >= 1.5 ? 'positive' : 'neutral'}
        />
        <MetricCard
          label="Win / Loss Payoff"
          value={winLossRatio === null ? 'N/A' : `1 : ${winLossRatio}`}
          subvalue="Average win vs average loss"
          trend={
  winLossRatio !== null && Number(winLossRatio) >= 1.5
    ? 'positive'
    : 'neutral'
}
        />
        <MetricCard
          label="Average Win"
          value={`+$${avgWin.toFixed(2)}`}
          subvalue={`${wins.length} profitable exits`}
          trend="positive"
        />
        <MetricCard
          label="Average Loss"
          value={`-$${avgLoss.toFixed(2)}`}
          subvalue={`${losses.length} stop loss hits`}
          trend="negative"
        />
      </div>

      {/* Trade Outcome Breakdown (Wins vs Losses) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Winning Trade Analysis */}
        <div
          className={`p-5 rounded-lg border transition-colors ${
            isDark
              ? 'bg-slate-900/60 border-slate-800'
              : 'bg-white border-slate-200 shadow-xs'
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              <h2 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                Winning Trade Profile
              </h2>
            </div>
            <span className="text-xs font-mono font-semibold text-emerald-500">
              {completedTrades > 0
  ? `${((wins.length / completedTrades) * 100).toFixed(1)}% Win Rate`
  : 'N/A'}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div
              className={`p-3 rounded border flex items-center justify-between ${
                isDark
                  ? 'bg-slate-950/60 border-slate-800'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Total Winning Volume:</span>
              <span className="font-mono font-medium text-emerald-500 tabular-nums">
                +${wins.reduce((sum, w) => sum + w.net_pl, 0).toFixed(2)}
              </span>
            </div>
            <div
              className={`p-3 rounded border flex items-center justify-between ${
                isDark
                  ? 'bg-slate-950/60 border-slate-800'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Largest Win:</span>
              <span className="font-mono font-medium text-emerald-500 tabular-nums">
                +${Math.max(0, ...wins.map((w) => w.net_pl)).toFixed(2)}
              </span>
            </div>
            <div
              className={`p-3 rounded border flex items-center justify-between ${
                isDark
                  ? 'bg-slate-950/60 border-slate-800'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Risk-Free Conversion Rate:</span>
              <span className={`font-mono font-medium tabular-nums ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                {wins.length > 0
                  ? Math.round((wins.filter((w) => w.risk_free_status === 'YES').length / wins.length) * 100)
                  : 0}
                % moved to BE
              </span>
            </div>
          </div>
        </div>

        {/* Losing Trade Analysis */}
        <div
          className={`p-5 rounded-lg border transition-colors ${
            isDark
              ? 'bg-slate-900/60 border-slate-800'
              : 'bg-white border-slate-200 shadow-xs'
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-rose-500" />
              <h2 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                Losing Trade Profile
              </h2>
            </div>
            <span className="text-xs font-mono font-semibold text-rose-500">
              {lossRate === null
  ? 'N/A'
  : `${lossRate.toFixed(1)}% Loss Rate`}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div
              className={`p-3 rounded border flex items-center justify-between ${
                isDark
                  ? 'bg-slate-950/60 border-slate-800'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Total Loss Volume:</span>
              <span className="font-mono font-medium text-rose-500 tabular-nums">
                -${Math.abs(losses.reduce((sum, l) => sum + l.net_pl, 0)).toFixed(2)}
              </span>
            </div>
            <div
              className={`p-3 rounded border flex items-center justify-between ${
                isDark
                  ? 'bg-slate-950/60 border-slate-800'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Largest Drawdown Stop:</span>
              <span className="font-mono font-medium text-rose-500 tabular-nums">
                -${Math.abs(Math.min(0, ...losses.map((l) => l.net_pl))).toFixed(2)}
              </span>
            </div>
            <div
              className={`p-3 rounded border flex items-center justify-between ${
                isDark
                  ? 'bg-slate-950/60 border-slate-800'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>Max Risk Adherence:</span>
              <span className={`font-mono font-medium tabular-nums ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                Risk adherence not available
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Symbol Breakdown Table */}
      <div
        className={`rounded-lg border overflow-hidden transition-colors ${
          isDark
            ? 'bg-slate-900/60 border-slate-800'
            : 'bg-white border-slate-200 shadow-xs'
        }`}
      >
        <div
          className={`px-5 py-3.5 border-b flex items-center justify-between ${
            isDark ? 'border-slate-800 bg-slate-900/80' : 'border-slate-200 bg-slate-50'
          }`}
        >
          <h2 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
            Instrument & Symbol Breakdown
          </h2>
          <span className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Aggregated by ticker
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs min-w-[500px]">
            <thead
              className={`border-b text-[11px] uppercase tracking-wider ${
                isDark
                  ? 'border-slate-800 bg-slate-950/60 text-slate-400'
                  : 'border-slate-200 bg-slate-100 text-slate-600'
              }`}
            >
              <tr>
                <th className="py-3 px-4">Symbol</th>
                <th className="py-3 px-4">Total Deals</th>
                <th className="py-3 px-4">Win Rate</th>
                <th className="py-3 px-4 text-right">Net P&L</th>
              </tr>
            </thead>
            <tbody
              className={`divide-y font-mono ${
                isDark ? 'divide-slate-800/60 text-slate-300' : 'divide-slate-200 text-slate-700'
              }`}
            >
              {Object.entries(symbolStats).map(([sym, stats]) => {
                const wr = Math.round((stats.wins / stats.count) * 100);
                const isPos = stats.pl >= 0;
                return (
                  <tr
                    key={sym}
                    className={`transition-colors ${
                      isDark ? 'hover:bg-slate-800/40' : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className={`py-3 px-4 font-bold font-sans ${isDark ? 'text-white' : 'text-slate-900'}`}>{sym}</td>
                    <td className="py-3 px-4 tabular-nums">{stats.count}</td>
                    <td className="py-3 px-4 tabular-nums">{wr}%</td>
                    <td className="py-3 px-4 text-right font-sans font-semibold tabular-nums">
                      <span className={isPos ? 'text-emerald-500' : 'text-rose-500'}>
                        {isPos ? '+' : ''}${stats.pl.toFixed(2)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI Insights & Pattern Engine */}
      <div
        className={`p-6 rounded-lg border relative overflow-hidden transition-colors ${
          isDark
            ? 'border-slate-800 bg-slate-900/40'
            : 'border-slate-200 bg-white shadow-xs'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-800/40">
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
                <h2 className={`text-base font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  AI Insights & Pattern Engine
                </h2>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                  Active AI
                </span>
              </div>
              <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                Cross-correlates account execution, volatility regimes, risk parameters, and behavioral anomalies
              </p>
            </div>
          </div>

          <button
            onClick={handleRunAiAnalysis}
            disabled={loadingAi}
            className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg transition-all shadow-xs cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingAi ? 'animate-spin' : ''}`} />
            <span>{loadingAi ? 'Analyzing Portfolio...' : aiAnalysis ? 'Re-Run AI Analysis' : 'Run AI Analysis'}</span>
          </button>
        </div>

        {aiError && (
          <div className="p-4 mb-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{aiError}</span>
          </div>
        )}

        {!aiAnalysis && !loadingAi && (
          <div className="py-8 text-center">
            <Bot className={`w-10 h-10 mx-auto mb-2 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
            <p className={`text-sm font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
              AI Deep Performance Analysis Ready
            </p>
            <p className={`text-xs max-w-lg mx-auto mt-1 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
              Click "Run AI Analysis" to evaluate current market regimes, risk boundaries, execution drift, and tailored recommendations.
            </p>
          </div>
        )}

        {loadingAi && (
          <div className="py-12 text-center space-y-3">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-emerald-500" />
            <p className={`text-sm font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
              Evaluating trading telemetry with AI...
            </p>
            <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
              Inspecting closed trades, risk configurations, open positions, and volatility regimes
            </p>
          </div>
        )}

        {aiAnalysis && !loadingAi && (
          <div className="space-y-6 animate-in fade-in-50 duration-200">
            {/* Top Regime & Risk Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className={`p-3.5 rounded-lg border ${isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                <span className={`block text-[11px] font-medium mb-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Market Regime
                </span>
                <span className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                  aiAnalysis.overall_market_regime === 'trending' ? 'bg-emerald-500/10 text-emerald-400' :
                  aiAnalysis.overall_market_regime === 'volatile' ? 'bg-amber-500/10 text-amber-400' :
                  'bg-blue-500/10 text-blue-400'
                }`}>
                  <Activity className="w-3 h-3" />
                  {aiAnalysis.overall_market_regime}
                </span>
              </div>

              <div className={`p-3.5 rounded-lg border ${isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                <span className={`block text-[11px] font-medium mb-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Market Trend
                </span>
                <span className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                  aiAnalysis.overall_trend === 'bullish' ? 'bg-emerald-500/10 text-emerald-400' :
                  aiAnalysis.overall_trend === 'bearish' ? 'bg-rose-500/10 text-rose-400' :
                  'bg-slate-500/10 text-slate-400'
                }`}>
                  {aiAnalysis.overall_trend === 'bullish' ? <TrendingUp className="w-3 h-3" /> :
                   aiAnalysis.overall_trend === 'bearish' ? <TrendingDown className="w-3 h-3" /> :
                   <Compass className="w-3 h-3" />}
                  {aiAnalysis.overall_trend}
                </span>
              </div>

              <div className={`p-3.5 rounded-lg border ${isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                <span className={`block text-[11px] font-medium mb-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Volatility
                </span>
                <span className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                  aiAnalysis.overall_volatility === 'extreme' || aiAnalysis.overall_volatility === 'high' ? 'bg-rose-500/10 text-rose-400' :
                  aiAnalysis.overall_volatility === 'moderate' ? 'bg-amber-500/10 text-amber-400' :
                  'bg-emerald-500/10 text-emerald-400'
                }`}>
                  <BarChart3 className="w-3 h-3" />
                  {aiAnalysis.overall_volatility}
                </span>
              </div>

              <div className={`p-3.5 rounded-lg border ${isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                <span className={`block text-[11px] font-medium mb-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Risk Status
                </span>
                <span className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                  aiAnalysis.risk_status === 'critical' || aiAnalysis.risk_status === 'high' ? 'bg-rose-500/10 text-rose-400' :
                  aiAnalysis.risk_status === 'elevated' ? 'bg-amber-500/10 text-amber-400' :
                  'bg-emerald-500/10 text-emerald-400'
                }`}>
                  <ShieldAlert className="w-3 h-3" />
                  {aiAnalysis.risk_status}
                </span>
              </div>
            </div>

            {/* Strategy & Risk Overview Text */}
            <div className={`p-4 rounded-lg border ${isDark ? 'bg-slate-950/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
              <div className="flex items-center gap-2 mb-1.5">
                <Info className="w-4 h-4 text-emerald-400" />
                <h4 className={`text-xs font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  Strategy & Telemetry Overview
                </h4>
              </div>
              <p className={`text-xs leading-relaxed ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                {aiAnalysis.strategy_status}
              </p>
              {aiAnalysis.data_summary && (
                <p className={`text-[11px] mt-1.5 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
                  {aiAnalysis.data_summary}
                </p>
              )}
            </div>

            {/* Observations Section with Source Tags */}
            {aiAnalysis.observations && aiAnalysis.observations.length > 0 && (
              <div>
                <h4 className={`text-xs font-semibold uppercase tracking-wider mb-2.5 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  AI Audited Observations ({aiAnalysis.observations.length})
                </h4>
                <div className="space-y-2">
                  {aiAnalysis.observations.map((obs, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border text-xs flex items-start justify-between gap-3 ${
                        isDark ? 'bg-slate-950/40 border-slate-800/80 text-slate-300' : 'bg-white border-slate-200 text-slate-700 shadow-2xs'
                      }`}
                    >
                      <span className="leading-relaxed">{obs.text}</span>
                      <span className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded shrink-0 border ${
                        obs.source === 'observed_data' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                        obs.source === 'calculated_metric' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                        obs.source === 'recommendation' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                        'bg-purple-500/10 text-purple-400 border-purple-500/20'
                      }`}>
                        {obs.source.replace('_', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Warnings Section (if present) */}
            {aiAnalysis.warnings && aiAnalysis.warnings.length > 0 && (
              <div>
                <h4 className={`text-xs font-semibold uppercase tracking-wider mb-2.5 ${isDark ? 'text-rose-400' : 'text-rose-600'}`}>
                  Active Anomalies & Warnings ({aiAnalysis.warnings.length})
                </h4>
                <div className="space-y-2">
                  {aiAnalysis.warnings.map((w, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg border text-xs flex items-start gap-2.5 bg-rose-500/10 border-rose-500/20 text-rose-300"
                    >
                      <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <span className="font-semibold uppercase text-[10px] tracking-wide text-rose-400 mr-2">[{w.severity}]</span>
                        <span>{w.text}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations Section */}
            {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
              <div>
                <h4 className={`text-xs font-semibold uppercase tracking-wider mb-2.5 ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                  Actionable Recommendations ({aiAnalysis.recommendations.length})
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {aiAnalysis.recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-lg border text-xs flex flex-col justify-between ${
                        isDark ? 'bg-slate-950/60 border-slate-800 text-slate-300' : 'bg-white border-slate-200 text-slate-700 shadow-2xs'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                            rec.priority === 'high' || rec.priority === 'critical' ? 'bg-rose-500/10 text-rose-400' :
                            rec.priority === 'medium' ? 'bg-amber-500/10 text-amber-400' :
                            'bg-emerald-500/10 text-emerald-400'
                          }`}>
                            {rec.priority} priority
                          </span>
                        </div>
                        <p className="font-medium text-slate-200">{rec.text}</p>
                        {rec.rationale && (
                          <p className={`text-[11px] mt-1.5 leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                            {rec.rationale}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Per-Symbol Breakdown */}
            {aiAnalysis.symbol_analyses && aiAnalysis.symbol_analyses.length > 0 && (
              <div>
                <h4 className={`text-xs font-semibold uppercase tracking-wider mb-2.5 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  Symbol Market Regimes
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {aiAnalysis.symbol_analyses.map((sym, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-lg border ${
                        isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-white border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className={`text-xs font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                          {sym.symbol}
                        </span>
                        <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                          sym.trend === 'bullish' ? 'bg-emerald-500/10 text-emerald-400' :
                          sym.trend === 'bearish' ? 'bg-rose-500/10 text-rose-400' :
                          'bg-slate-500/10 text-slate-400'
                        }`}>
                          {sym.trend}
                        </span>
                      </div>
                      <div className="text-[11px] space-y-1">
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-slate-500' : 'text-slate-400'}>Regime:</span>
                          <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>{sym.market_regime}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className={isDark ? 'text-slate-500' : 'text-slate-400'}>Volatility:</span>
                          <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>{sym.volatility}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Disclaimer Footer */}
            <div className={`p-3 rounded-lg border text-[11px] flex items-center justify-between gap-3 ${
              isDark ? 'bg-slate-950/30 border-slate-800/60 text-slate-500' : 'bg-slate-50 border-slate-200 text-slate-500'
            }`}>
              <span>{aiAnalysis.ai_disclaimer}</span>
              <span className="font-mono shrink-0">
                Audited {new Date(aiAnalysis.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
