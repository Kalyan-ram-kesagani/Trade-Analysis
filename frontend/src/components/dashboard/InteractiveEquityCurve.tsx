import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { useTrading } from '../../context/TradingContext';


type Timeframe = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | 'All';

export const InteractiveEquityCurve: React.FC = () => {
  const {
    selectedAccountId,
    isAllAccounts,
    activeAccount,
    accounts,
    trades,
    theme,
  } = useTrading();
  const [timeframe, setTimeframe] = useState<Timeframe>('1M');

  const data = useMemo(() => {
    const currentBalance = isAllAccounts
      ? accounts.reduce((sum, account) => sum + account.balance, 0)
      : (activeAccount?.balance || 0);

    const currentEquity = isAllAccounts
      ? accounts.reduce((sum, account) => sum + account.equity, 0)
      : (activeAccount?.equity || 0);

    if (currentBalance === 0 && currentEquity === 0 && (!trades || trades.length === 0)) {
      return [];
    }

    // Filter closed trades by timeframe
    const now = Date.now();
    const timeframeMs: Record<Timeframe, number> = {
      '1D': 86400000,
      '1W': 7 * 86400000,
      '1M': 30 * 86400000,
      '3M': 90 * 86400000,
      '6M': 180 * 86400000,
      '1Y': 365 * 86400000,
      'All': Infinity,
    };

    const cutoff = now - timeframeMs[timeframe];
    const validTrades = (trades || [])
      .filter((t) => t.exit_time && new Date(t.exit_time).getTime() >= cutoff)
      .sort((a, b) => new Date(a.exit_time).getTime() - new Date(b.exit_time).getTime());

    if (validTrades.length === 0) {
      const dd = currentBalance > 0
        ? Math.max(0, Math.round(((currentBalance - currentEquity) / currentBalance) * 1000) / 10)
        : 0;
      return [
        {
          date: 'Current',
          timestamp: now,
          balance: currentBalance,
          equity: currentEquity,
          drawdown: dd,
          pl: currentEquity - currentBalance,
        },
      ];
    }

    const totalPnL = validTrades.reduce((sum, t) => sum + t.net_pl, 0);
    const startBal = Math.max(100, currentBalance - totalPnL);

    let runningBal = startBal;
    let peakBal = runningBal;

    const points = [
      {
        date: 'Start',
        timestamp: new Date(validTrades[0].entry_time).getTime() || (now - 86400000),
        balance: Math.round(runningBal * 100) / 100,
        equity: Math.round(runningBal * 100) / 100,
        drawdown: 0,
        pl: 0,
      },
    ];

    validTrades.forEach((t) => {
      runningBal += t.net_pl;
      if (runningBal > peakBal) peakBal = runningBal;
      const dd = peakBal > 0
        ? Math.max(0, Math.round(((peakBal - runningBal) / peakBal) * 1000) / 10)
        : 0;

      points.push({
        date: new Date(t.exit_time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        timestamp: new Date(t.exit_time).getTime(),
        balance: Math.round(runningBal * 100) / 100,
        equity: Math.round(runningBal * 100) / 100,
        drawdown: dd,
        pl: t.net_pl,
      });
    });

    // Final point representing current live equity
    const liveDrawdown = currentBalance > 0
      ? Math.max(0, Math.round(((currentBalance - currentEquity) / currentBalance) * 1000) / 10)
      : 0;

    points.push({
      date: 'Live',
      timestamp: now,
      balance: Math.round(currentBalance * 100) / 100,
      equity: Math.round(currentEquity * 100) / 100,
      drawdown: liveDrawdown,
      pl: currentEquity - currentBalance,
    });

    return points;
  }, [isAllAccounts, accounts, activeAccount, trades, timeframe]);

  const timeframes: Timeframe[] = ['1D', '1W', '1M', '3M', '6M', '1Y', 'All'];

  // Current display point (latest)
  const latestDisplay = data[data.length - 1];

  // Determine if overall period trend is positive
  const positive = useMemo(() => {
    if (data.length <= 1) return true;
    return data[data.length - 1].equity >= data[0].equity;
  }, [data]);

  const formatCurrency = (val: number) =>
    `$${Number(val || 0).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;

  return (
    <div
      className={`p-4 sm:p-5 rounded-lg border transition-colors ${
        theme === 'dark'
          ? 'bg-slate-900/60 border-slate-800'
          : 'bg-white border-slate-200 shadow-xs'
      }`}
    >
      {/* Chart Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
        <div>
          <div className="flex items-center gap-2">
            <h2
              className={`text-sm font-semibold ${
                theme === 'dark' ? 'text-white' : 'text-slate-900'
              }`}
            >
              Equity & Balance Curve
            </h2>
            <span
              className={`text-[11px] font-mono ${
                theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
              }`}
            >
              {isAllAccounts ? 'Combined' : activeAccount?.account_name}
            </span>
          </div>
          {latestDisplay && (
            <div className="flex flex-wrap items-center gap-3 sm:gap-4 mt-1.5">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-500">Latest Equity:</span>
                <span className="text-xs font-semibold font-mono tabular-nums text-emerald-500">
                  ${latestDisplay.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-500">Balance:</span>
                <span
                  className={`text-xs font-medium font-mono tabular-nums ${
                    theme === 'dark' ? 'text-slate-200' : 'text-slate-800'
                  }`}
                >
                  ${latestDisplay.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-500">DD:</span>
                <span className="text-xs font-mono tabular-nums text-amber-500">
                  {latestDisplay.drawdown}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Timeframe Selector (scrollable on mobile) */}
        <div
          className={`flex items-center p-0.5 rounded-md border overflow-x-auto max-w-full ${
            theme === 'dark'
              ? 'bg-slate-950/70 border-slate-800'
              : 'bg-slate-100 border-slate-200'
          }`}
        >
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-1 text-[11px] font-medium rounded transition-colors whitespace-nowrap cursor-pointer ${
                timeframe === tf
                  ? theme === 'dark'
                    ? 'bg-slate-800 text-white font-semibold shadow-xs'
                    : 'bg-white text-slate-900 font-semibold shadow-2xs'
                  : theme === 'dark'
                  ? 'text-slate-400 hover:text-slate-200'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Equity Curve */}
<div className="mt-5 h-[300px] w-full outline-none focus:outline-none">
  {data.length === 0 ? (
    <div
      className={`h-full flex items-center justify-center rounded-md border ${
        theme === 'dark'
          ? 'border-slate-800 bg-slate-950/40'
          : 'border-slate-200 bg-slate-50'
      }`}
    >
      <div className="text-center">
        <p
          className={`text-sm font-medium ${
            theme === 'dark'
              ? 'text-slate-300'
              : 'text-slate-700'
          }`}
        >
          No equity data available
        </p>

        <p
          className={`mt-1 text-xs ${
            theme === 'dark'
              ? 'text-slate-500'
              : 'text-slate-500'
          }`}
        >
          Connect an MT5 trading account to view equity history.
        </p>
      </div>
    </div>
  ) : (
    <ResponsiveContainer width="100%" height="100%" className="outline-none focus:outline-none select-none">
      <AreaChart
        data={data}
        margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
        className="outline-none focus:outline-none"
        style={{ outline: 'none' }}
      >
        <defs>
          <linearGradient
            id="equityFill"
            x1="0"

            y1="0"
            x2="0"
            y2="1"
          >
            <stop
              offset="0%"
              stopColor={
                positive
                  ? 'var(--color-profit)'
                  : 'var(--color-loss)'
              }
              stopOpacity={0.25}
            />

            <stop
              offset="100%"
              stopColor={
                positive
                  ? 'var(--color-profit)'
                  : 'var(--color-loss)'
              }
              stopOpacity={0}
            />
          </linearGradient>
        </defs>

        <CartesianGrid
          stroke="var(--color-border)"
          vertical={false}
        />

        <XAxis
          dataKey="date"
          tickLine={false}
          axisLine={false}
          minTickGap={40}
          tick={{
            fontSize: 11,
            fill: 'var(--color-muted-foreground)',
          }}
        />

        <YAxis
          width={64}
          tickLine={false}
          axisLine={false}
          domain={['auto', 'auto']}
          tick={{
            fontSize: 11,
            fill: 'var(--color-muted-foreground)',
          }}
          tickFormatter={(v: number) =>
            `$${Math.round(v).toLocaleString()}`
          }
        />

        <Tooltip
          cursor={{
            stroke: 'var(--color-border)',
          }}
          contentStyle={{
            background: 'var(--color-popover)',
            border: '1px solid var(--color-border)',
            borderRadius: 10,
            fontSize: 12,
            color: 'var(--color-popover-foreground)',
          }}
          labelStyle={{
            color: 'var(--color-muted-foreground)',
          }}
          formatter={(value: any) => [
            formatCurrency(Number(value)),
            'Equity',
          ]}
        />

        <Area
          type="monotone"
          dataKey="equity"
          stroke={
            positive
              ? 'var(--color-profit)'
              : 'var(--color-loss)'
          }
          strokeWidth={2}
          fill="url(#equityFill)"
          animationDuration={600}
        />
      </AreaChart>
    </ResponsiveContainer>
  )}
</div>
    </div>
  );
};
