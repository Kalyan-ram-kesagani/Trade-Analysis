import React, { useState } from 'react';
import { useTrading } from '../context/TradingContext';
import { TradingAPI } from '../services/api';
import {
  BookOpen,
  Plus,
  Calendar,
  Sparkles,
  Tag,
  Cpu,
  Layers,
  CheckCircle2,
  XCircle,
  X,
  RefreshCw,
  Lightbulb,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { JournalEntry } from '../types/trading';

export const JournalPage: React.FC = () => {
  const { journalEntries, addJournalEntry, isAllAccounts, activeAccount, selectedAccountId, trades, theme, refreshAccountData } =
    useTrading();
  const isDark = theme === 'dark';

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTradeTicket, setSelectedTradeTicket] = useState(trades[0]?.ticket.toString() || '');
  const [notes, setNotes] = useState('');
  const [reason, setReason] = useState('');
  const [lessons, setLessons] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiGeneratedInfo, setAiGeneratedInfo] = useState<{
    recommendation?: string;
    detectedReason?: string;
    executionScore?: number;
  }>({});
  const [cardReviewLoading, setCardReviewLoading] = useState<Record<string, boolean>>({});
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({});
  const [autoProcessing, setAutoProcessing] = useState(false);

  const toggleDetails = (id: string) => {
    setExpandedDetails((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleTriggerAutoProcess = async () => {
    const accId = isAllAccounts ? activeAccount?.id : selectedAccountId;
    if (!accId || accId === 'all') return;
    setAutoProcessing(true);
    try {
      await TradingAPI.autoProcessAIJournals(accId);
      // Wait a moment then refresh
      setTimeout(() => {
        refreshAccountData(selectedAccountId);
      }, 1500);
    } catch (err) {
      console.error('Failed to trigger auto process:', err);
    } finally {
      setAutoProcessing(false);
    }
  };

  const handleAutoFillWithAI = async () => {
    const matchedTrade = trades.find((t) => t.ticket.toString() === selectedTradeTicket) || trades[0];
    if (!matchedTrade) return;

    const accountId = isAllAccounts ? (activeAccount?.id || matchedTrade.account_id) : selectedAccountId;
    setAiGenerating(true);
    try {
      const aiRes = await TradingAPI.generateAIJournal(accountId, matchedTrade.id);
      if (aiRes.trade_summary || aiRes.summary) setNotes(aiRes.trade_summary || aiRes.summary);
      if (aiRes.entry_analysis || aiRes.entry_reason) setReason(aiRes.entry_analysis || aiRes.entry_reason);
      if (aiRes.lesson || (aiRes.lessons && aiRes.lessons.length > 0)) {
        setLessons(aiRes.lesson || aiRes.lessons.join('; '));
      }
      if (aiRes.tags && aiRes.tags.length > 0) {
        setTagsInput(aiRes.tags.join(', '));
      }
      setAiGeneratedInfo({
        recommendation: aiRes.suggested_improvement || aiRes.risk_analysis || aiRes.risk_management_assessment,
        detectedReason: aiRes.entry_analysis || aiRes.entry_reason,
        executionScore: aiRes.execution_quality_score,
      });
    } catch (err: any) {
      console.error('AI Journal generation failed:', err);
    } finally {
      setAiGenerating(false);
    }
  };

  const handleGenerateReviewForCard = async (entry: JournalEntry) => {
    setCardReviewLoading((prev) => ({ ...prev, [entry.id]: true }));
    try {
      await TradingAPI.retryAIJournal(entry.account_id, entry.trade_id);
      await refreshAccountData(selectedAccountId);
    } catch (err) {
      console.error('AI review generation failed:', err);
    } finally {
      setCardReviewLoading((prev) => ({ ...prev, [entry.id]: false }));
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes || !reason) return;

    const matchedTrade = trades.find((t) => t.ticket.toString() === selectedTradeTicket) || trades[0];

    await addJournalEntry({
      trade_id: matchedTrade ? matchedTrade.id : `trd-manual-${Date.now()}`,
      account_id: isAllAccounts ? activeAccount?.id || 'acc-main-01' : selectedAccountId,
      symbol: matchedTrade ? matchedTrade.symbol : 'EURUSD',
      date: new Date().toISOString().slice(0, 10),
      result: matchedTrade ? matchedTrade.status : 'WIN',
      notes,
      reason,
      lessons,
      strategy_version: matchedTrade ? matchedTrade.strategy_name : 'OrderFlow Momentum V2.1',
      tags: tagsInput
        ? tagsInput.split(',').map((t) => t.trim()).filter(Boolean)
        : ['Manual Review'],
      ai_recommendation: aiGeneratedInfo.recommendation,
      ai_detected_reason: aiGeneratedInfo.detectedReason,
    });

    setIsModalOpen(false);
    setNotes('');
    setReason('');
    setLessons('');
    setTagsInput('');
    setAiGeneratedInfo({});
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
              Trading Journal & Review
            </h1>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded border ${
                isDark
                  ? 'text-slate-400 bg-slate-900 border-slate-800'
                  : 'text-slate-600 bg-slate-100 border-slate-200'
              }`}
            >
              {journalEntries.length} review entries
            </span>
            <span
              className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded border ${
                isDark
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-emerald-50 text-emerald-700 border-emerald-200'
              }`}
            >
              <Sparkles className="w-3 h-3 text-emerald-400" />
              <span>Auto-Journaling Active</span>
            </span>
          </div>
          <p className={`text-xs mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            Automatic AI trade reviews, qualitative execution assessments, and personal trader notes
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleTriggerAutoProcess}
            disabled={autoProcessing}
            title="Scan for any completed trades needing automatic AI review"
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border transition-colors cursor-pointer ${
              isDark
                ? 'bg-slate-900 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 shadow-xs'
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${autoProcessing ? 'animate-spin' : ''}`} />
            <span>{autoProcessing ? 'Processing AI...' : 'Auto-Sync AI Journals'}</span>
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-md transition-colors shadow-2xs"
          >
            <Plus className="w-4 h-4" />
            <span>New Manual Entry</span>
          </button>
        </div>
      </div>

      {/* Journal Cards Timeline */}
      {journalEntries.length === 0 ? (
        <div
          className={`p-16 text-center rounded-lg border text-xs ${
            isDark
              ? 'border-slate-800 bg-slate-900/40 text-slate-400'
              : 'border-slate-200 bg-white text-slate-600 shadow-xs'
          }`}
        >
          <BookOpen className={`w-8 h-8 mx-auto mb-2 ${isDark ? 'text-slate-600' : 'text-slate-400'}`} />
          <p className={`font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>No journal logs recorded for this account</p>
          <p className={`mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
            Completed trades automatically receive AI journal reviews upon synchronization.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {journalEntries.map((entry: JournalEntry) => {
            const isWin = entry.result === 'WIN';
            const isLoss = entry.result === 'LOSS';
            const isAutoAI = entry.journal_type === 'AI_TRADE_REVIEW';
            const status = entry.status || 'COMPLETED';
            const isProcessing = status === 'PROCESSING';
            const isFailed = status === 'FAILED';
            const isCompleted = status === 'COMPLETED';
            const aiData = entry.structured_ai_output || {};
            const isExpanded = !!expandedDetails[entry.id];

            return (
              <div
                key={entry.id}
                className={`p-4 sm:p-5 rounded-lg border transition-all space-y-4 ${
                  isDark
                    ? 'bg-slate-900/60 border-slate-800 hover:border-slate-700/80'
                    : 'bg-white border-slate-200 hover:border-slate-300 shadow-xs'
                }`}
              >
                {/* Entry Header */}
                <div
                  className={`flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b ${
                    isDark ? 'border-slate-800/80' : 'border-slate-100'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className={`text-base font-bold font-sans ${isDark ? 'text-white' : 'text-slate-900'}`}>
                      {entry.symbol}
                    </span>
                    <span
                      className={`text-xs font-semibold px-2 py-0.5 rounded ${
                        isWin
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                          : isLoss
                          ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30'
                          : isDark
                          ? 'bg-slate-800 text-slate-300'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {entry.result}
                    </span>
                    <span className={`text-xs font-mono ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                      Trade ID: #{entry.trade_id.slice(-6)}
                    </span>

                    {/* AI Status Badge */}
                    {isAutoAI ? (
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded border ${
                          isCompleted
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : isProcessing
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse'
                            : isFailed
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        <Sparkles className="w-3 h-3" />
                        <span>AI Journal: {status}</span>
                      </span>
                    ) : (
                      <span className={`text-[11px] font-mono px-2 py-0.5 rounded border ${isDark ? 'bg-slate-800 text-slate-400 border-slate-700' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                        Manual Journal
                      </span>
                    )}

                    {entry.ai_confidence !== undefined && (
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${isDark ? 'text-slate-400 border-slate-800 bg-slate-950' : 'text-slate-500 border-slate-200 bg-slate-50'}`}>
                        Conf: {Math.round(entry.ai_confidence * 100)}%
                      </span>
                    )}
                  </div>

                  <div className={`flex items-center gap-3 text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    <div className="flex items-center gap-1">
                      <Calendar className={`w-3.5 h-3.5 ${isDark ? 'text-slate-500' : 'text-slate-400'}`} />
                      <span>{entry.date}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Cpu className="w-3.5 h-3.5 text-emerald-500" />
                      <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>{entry.strategy_version}</span>
                    </div>
                  </div>
                </div>

                {/* Processing State Notice */}
                {isProcessing && (
                  <div className={`flex items-center gap-2 p-3 rounded-lg border text-xs ${isDark ? 'bg-amber-500/10 border-amber-500/25 text-amber-300' : 'bg-amber-50 border-amber-200 text-amber-800'}`}>
                    <Clock className="w-4 h-4 animate-spin text-amber-400" />
                    <span>AI Journal Agent is analyzing trade execution data asynchronously...</span>
                  </div>
                )}

                {/* Failed State Notice */}
                {isFailed && (
                  <div className={`flex items-center justify-between gap-2 p-3 rounded-lg border text-xs ${isDark ? 'bg-rose-500/10 border-rose-500/25 text-rose-300' : 'bg-rose-50 border-rose-200 text-rose-800'}`}>
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
                      <span>AI generation deferred: {entry.error_info || 'Temporary rate limit or provider unavailability'}. Trade is safe and recorded.</span>
                    </div>
                    <button
                      onClick={() => handleGenerateReviewForCard(entry)}
                      disabled={cardReviewLoading[entry.id]}
                      className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-600 hover:bg-rose-500 text-white transition-colors cursor-pointer shrink-0"
                    >
                      {cardReviewLoading[entry.id] ? 'Retrying...' : 'Retry AI Journal'}
                    </button>
                  </div>
                )}

                {/* Entry Content Columns */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  <div className="space-y-1">
                    <span className={`text-[11px] font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                      Trade Summary & Notes
                    </span>
                    <p className={`leading-relaxed p-3 rounded border ${isDark ? 'text-slate-300 bg-slate-950/40 border-slate-800/60' : 'text-slate-700 bg-slate-50 border-slate-200'}`}>
                      {entry.notes || 'No notes available'}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <span className={`text-[11px] font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                      Entry Analysis / Trigger
                    </span>
                    <p className={`leading-relaxed p-3 rounded border ${isDark ? 'text-slate-300 bg-slate-950/40 border-slate-800/60' : 'text-slate-700 bg-slate-50 border-slate-200'}`}>
                      {entry.reason || 'No entry details available'}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <span className={`text-[11px] font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                      Lessons & Behavioral Takeaways
                    </span>
                    <p className={`leading-relaxed p-3 rounded border ${isDark ? 'text-slate-300 bg-slate-950/40 border-slate-800/60' : 'text-slate-700 bg-slate-50 border-slate-200'}`}>
                      {entry.lessons || 'No lessons recorded yet'}
                    </p>
                  </div>
                </div>

                {/* Collapsible Deep Structured AI Sections */}
                {(aiData.risk_analysis || aiData.what_went_well || aiData.what_could_be_improved || aiData.mistakes_violations) && (
                  <div className="space-y-2">
                    <button
                      type="button"
                      onClick={() => toggleDetails(entry.id)}
                      className={`flex items-center gap-1.5 text-xs font-medium cursor-pointer transition-colors ${
                        isDark ? 'text-emerald-400 hover:text-emerald-300' : 'text-emerald-700 hover:text-emerald-800'
                      }`}
                    >
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      <span>{isExpanded ? 'Hide Deep Audit Sections' : 'View Deep AI Audit (Risk, Execution & Process Violations)'}</span>
                    </button>

                    {isExpanded && (
                      <div className={`p-3.5 rounded-lg border text-xs space-y-3 ${isDark ? 'bg-slate-950/60 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {aiData.risk_analysis && (
                            <div>
                              <span className="font-semibold text-[11px] text-amber-400 block mb-1">Risk Management Analysis</span>
                              <p className={`leading-relaxed ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{aiData.risk_analysis}</p>
                            </div>
                          )}
                          {aiData.execution_analysis && (
                            <div>
                              <span className="font-semibold text-[11px] text-blue-400 block mb-1">Execution & Slippage Analysis</span>
                              <p className={`leading-relaxed ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{aiData.execution_analysis}</p>
                            </div>
                          )}
                        </div>

                        {aiData.what_went_well && aiData.what_went_well.length > 0 && (
                          <div>
                            <span className="font-semibold text-[11px] text-emerald-400 block mb-1">What Went Well</span>
                            <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                              {aiData.what_went_well.map((point: string, idx: number) => (
                                <li key={idx} className={isDark ? 'text-slate-300' : 'text-slate-700'}>{point}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {aiData.what_could_be_improved && aiData.what_could_be_improved.length > 0 && (
                          <div>
                            <span className="font-semibold text-[11px] text-amber-400 block mb-1">What Could Be Improved</span>
                            <ul className="list-disc list-inside space-y-0.5">
                              {aiData.what_could_be_improved.map((point: string, idx: number) => (
                                <li key={idx} className={isDark ? 'text-slate-300' : 'text-slate-700'}>{point}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {aiData.mistakes_violations && aiData.mistakes_violations.length > 0 && (
                          <div>
                            <span className="font-semibold text-[11px] text-rose-400 block mb-1">Evidence-Backed Violations</span>
                            <ul className="list-disc list-inside space-y-0.5">
                              {aiData.mistakes_violations.map((violation: string, idx: number) => (
                                <li key={idx} className="text-rose-400 font-medium">{violation}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {aiData.suggested_improvement && (
                          <div className={`p-2.5 rounded border ${isDark ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-300' : 'bg-emerald-50 border-emerald-200 text-emerald-900'}`}>
                            <span className="font-semibold text-[11px] block">Suggested Strategy Improvement</span>
                            <p className="mt-0.5">{aiData.suggested_improvement}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Tags and AI Section */}
                <div
                  className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t ${
                    isDark ? 'border-slate-800/60' : 'border-slate-100'
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-1.5">
                    {entry.tags.map((t) => (
                      <span
                        key={t}
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                          isDark
                            ? 'text-slate-400 bg-slate-800/80 border-slate-700/60'
                            : 'text-slate-600 bg-slate-100 border-slate-200'
                        }`}
                      >
                        #{t}
                      </span>
                    ))}
                  </div>

                  {/* AI Behavioral Recommendation & On-Demand Review */}
                  <div className="flex items-center gap-3">
                    {entry.ai_recommendation && (
                      <div
                        className={`flex items-start gap-2.5 text-xs p-2.5 rounded-lg border max-w-md ${
                          isDark
                            ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-300'
                            : 'bg-emerald-50 border-emerald-200 text-emerald-900'
                        }`}
                      >
                        <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold block text-[11px] uppercase tracking-wider text-emerald-400">
                            AI Behavioral Takeaway
                          </span>
                          <p className="text-xs leading-relaxed mt-0.5">{entry.ai_recommendation}</p>
                        </div>
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={() => handleGenerateReviewForCard(entry)}
                      disabled={cardReviewLoading[entry.id]}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all cursor-pointer ${
                        isDark
                          ? 'bg-slate-800/80 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700'
                          : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
                      }`}
                    >
                      <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${cardReviewLoading[entry.id] ? 'animate-spin' : ''}`} />
                      <span>{cardReviewLoading[entry.id] ? 'Generating...' : (entry.ai_recommendation ? 'Regenerate AI' : 'Generate AI Review')}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* New Journal Entry Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/70 backdrop-blur-xs animate-in fade-in-50 duration-150">
          <div
            className={`w-full max-w-lg rounded-xl border shadow-2xl overflow-hidden transition-colors ${
              isDark
                ? 'border-slate-700 bg-[#0d131f] text-slate-200'
                : 'border-slate-200 bg-white text-slate-800'
            }`}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className={`flex items-center justify-between px-5 sm:px-6 py-4 border-b ${
                isDark ? 'border-slate-800 bg-slate-900/60' : 'border-slate-200 bg-slate-50'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <BookOpen className="w-5 h-5 text-emerald-500" />
                <h3 className={`text-base font-semibold ${isDark ? 'text-white' : 'text-slate-900'}`}>
                  Log Trading Journal Review
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className={`p-1.5 rounded-lg transition-colors ${
                  isDark
                    ? 'text-slate-400 hover:text-white hover:bg-slate-800'
                    : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-4 sm:p-6 space-y-4 text-xs">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className={`block font-medium ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                    Associate with Closed Trade Ticket
                  </label>
                  <button
                    type="button"
                    onClick={handleAutoFillWithAI}
                    disabled={aiGenerating || trades.length === 0}
                    className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-md transition-all cursor-pointer disabled:opacity-50"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${aiGenerating ? 'animate-spin' : ''}`} />
                    <span>{aiGenerating ? 'AI Analyzing Trade...' : 'Auto-Fill with AI'}</span>
                  </button>
                </div>
                <select
                  value={selectedTradeTicket}
                  onChange={(e) => setSelectedTradeTicket(e.target.value)}
                  className={`w-full px-3 py-2 rounded-md border focus:outline-hidden ${
                    isDark
                      ? 'bg-slate-900 border-slate-700 text-white'
                      : 'bg-white border-slate-300 text-slate-900'
                  }`}
                >
                  {trades.map((t) => (
                    <option key={t.ticket} value={t.ticket}>
                      Ticket #{t.ticket} — {t.symbol} {t.direction} ({t.net_pl >= 0 ? '+' : ''}${t.net_pl})
                    </option>
                  ))}
                </select>
                {aiGeneratedInfo.recommendation && (
                  <div className={`mt-2 p-2.5 rounded-md border text-[11px] flex items-start gap-2 ${
                    isDark ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  }`}>
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>AI Insight: {aiGeneratedInfo.recommendation}</span>
                  </div>
                )}
              </div>

              <div>
                <label className={`block font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  Detailed Trade Execution Notes *
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Describe market context, candle action, support/resistance reaction..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className={`w-full px-3 py-2 rounded-md border focus:outline-hidden transition-colors ${
                    isDark
                      ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500 focus:border-emerald-500'
                      : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400 focus:border-emerald-600 focus:bg-white'
                  }`}
                />
              </div>

              <div>
                <label className={`block font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  Primary Entry Reason *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Order block sweep on 15m chart with fair value gap retest"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className={`w-full px-3 py-2 rounded-md border focus:outline-hidden transition-colors ${
                    isDark
                      ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500 focus:border-emerald-500'
                      : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400 focus:border-emerald-600 focus:bg-white'
                  }`}
                />
              </div>

              <div>
                <label className={`block font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  Lessons Learned
                </label>
                <input
                  type="text"
                  placeholder="e.g. Risk-free breakeven was moved too early, giving trade inadequate room"
                  value={lessons}
                  onChange={(e) => setLessons(e.target.value)}
                  className={`w-full px-3 py-2 rounded-md border focus:outline-hidden transition-colors ${
                    isDark
                      ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500 focus:border-emerald-500'
                      : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400 focus:border-emerald-600 focus:bg-white'
                  }`}
                />
              </div>

              <div>
                <label className={`block font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                  Tags (Comma separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. EURUSD, OrderFlow, London Open"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  className={`w-full px-3 py-2 rounded-md border focus:outline-hidden transition-colors ${
                    isDark
                      ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500 focus:border-emerald-500'
                      : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400 focus:border-emerald-600 focus:bg-white'
                  }`}
                />
              </div>

              <div
                className={`flex items-center justify-end gap-3 pt-3 border-t ${
                  isDark ? 'border-slate-800' : 'border-slate-200'
                }`}
              >
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className={`px-4 py-2 font-medium rounded-md transition-colors ${
                    isDark
                      ? 'text-slate-400 hover:text-white bg-slate-800'
                      : 'text-slate-600 hover:text-slate-900 bg-slate-100 border border-slate-200'
                  }`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-md transition-colors shadow-2xs"
                >
                  Save Entry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
