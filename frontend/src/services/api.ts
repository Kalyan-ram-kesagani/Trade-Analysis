import {
  TradingAccount,
  Trade,
  OpenPosition,
  SystemActivity,
  Strategy,
  JournalEntry,
  RiskStatus,
  SystemHealthItem,
  EquityDataPoint,
} from '../types/trading';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';


function isValidUUID(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value
  );
}

function buildAccountQuery(accountId?: string): string {
  if (!accountId || accountId === 'all' || !isValidUUID(accountId)) {
    return '';
  }

  return `?account_id=${encodeURIComponent(accountId)}`;
}

async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text();

    throw new Error(
      `API request failed (${response.status}): ${errorText}`
    );
  }

  return response.json();
}

/*
 * Convert backend account data into the exact
 * TradingAccount structure expected by the frontend.
 */
function mapAccount(account: any): TradingAccount {
  return {
    id: String(account.id),
    user_id: String(account.user_id ?? ''),
    broker: account.broker ?? '',
    account_name: account.account_name ?? '',
    account_number: account.account_number ?? '',
    masked_number:
      account.masked_number ??
      `••••${String(account.account_number ?? '').slice(-4)}`,
    server: account.server ?? '',
    balance: Number(account.balance ?? 0),
    equity: Number(account.equity ?? 0),
    margin: Number(account.margin ?? 0),
    free_margin: Number(account.free_margin ?? 0),
    margin_level: Number(account.margin_level ?? 0),
    floating_pl: Number(account.floating_pl ?? 0),
    currency: account.currency ?? 'USD',
    status: account.status ?? 'disconnected',
    account_type: account.account_type ?? 'demo',
    leverage: Number(account.leverage ?? 0),
    last_sync: account.last_sync ?? '',
    ping_ms: Number(account.ping_ms ?? 0),
    created_at: account.created_at ?? '',
  };
}

/*
 * Convert backend trade data into the frontend Trade type.
 */
function mapTrade(trade: any): Trade {
  return {
    id: String(trade.id),
    ticket: Number(trade.ticket),
    account_id: String(trade.account_id),
    symbol: trade.symbol ?? '',
    direction: trade.direction,
    volume: Number(trade.volume ?? 0),
    entry_price: Number(trade.entry_price ?? 0),
    exit_price: Number(trade.exit_price ?? 0),
    stop_loss: Number(trade.stop_loss ?? 0),
    take_profit: Number(trade.take_profit ?? 0),
    entry_time: trade.entry_time ?? '',
    exit_time: trade.exit_time ?? '',
    profit_loss: Number(trade.profit_loss ?? 0),
    commission: Number(trade.commission ?? 0),
    swap: Number(trade.swap ?? 0),
    net_pl: Number(trade.net_pl ?? 0),
    status: trade.status,
    strategy_id: String(trade.strategy_id ?? ''),
    strategy_name: trade.strategy_name ?? '',
    initial_risk_percent: Number(trade.initial_risk_percent ?? 0),
    initial_risk_amount: Number(trade.initial_risk_amount ?? 0),
    risk_free_status: trade.risk_free_status ?? 'N/A',
    break_even_price: trade.break_even_price ?? undefined,
    risk_free_activated_time:
      trade.risk_free_activated_time ?? undefined,
    risk_reward_ratio:
      trade.risk_reward_ratio ?? undefined,
    notes: trade.notes ?? undefined,
    created_at: trade.created_at ?? '',
  };
}

/*
 * Convert backend open-position data into the frontend type.
 */
function mapPosition(position: any): OpenPosition {
  const entryTime = position.entry_time ?? '';

  return {
    id: String(position.id),
    ticket: Number(position.ticket),
    account_id: String(position.account_id),
    symbol: position.symbol ?? '',
    direction: position.direction,
    volume: Number(position.volume ?? 0),
    entry_price: Number(position.entry_price ?? 0),
    current_price: Number(position.current_price ?? 0),
    stop_loss: Number(position.stop_loss ?? 0),
    take_profit: Number(position.take_profit ?? 0),
    floating_pl: Number(position.floating_pl ?? 0),
    duration: calculateDuration(entryTime),
    entry_time: entryTime,
    risk_free_status: position.risk_free_status ?? 'N/A',
    break_even_price:
      position.break_even_price ?? undefined,
    strategy_name: position.strategy_name ?? '',
  };
}

function calculateDuration(entryTime: string): string {
  if (!entryTime) return '—';

  const start = new Date(entryTime).getTime();

  if (Number.isNaN(start)) return '—';

  const diffMs = Math.max(Date.now() - start, 0);

  const totalMinutes = Math.floor(diffMs / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  return `${minutes}m`;
}

/*
 * Convert backend activity into frontend activity structure.
 */
function mapActivity(
  activity: any,
  accounts: TradingAccount[]
): SystemActivity {
  const account = accounts.find(
    (item) => item.id === String(activity.account_id)
  );

  return {
    id: String(activity.id),
    account_id: String(activity.account_id ?? ''),
    account_name:
      account?.account_name ??
      (activity.account_id ? 'MT5 Account' : 'System'),
    type: activity.type,
    title: activity.title ?? '',
    description: activity.description ?? '',
    timestamp: activity.created_at ?? '',
    relative_time: getRelativeTime(activity.created_at),
    symbol: activity.symbol ?? undefined,
    pl:
      activity.pl !== null && activity.pl !== undefined
        ? Number(activity.pl)
        : undefined,
    level: activity.level ?? 'info',
  };
}

function getRelativeTime(timestamp: string): string {
  if (!timestamp) return '';

  const time = new Date(timestamp).getTime();

  if (Number.isNaN(time)) return '';

  const diffSeconds = Math.max(
    Math.floor((Date.now() - time) / 1000),
    0
  );

  if (diffSeconds < 60) {
    return 'Just now';
  }

  const minutes = Math.floor(diffSeconds / 60);

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);

  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);

  return `${days}d ago`;
}

/*
 * Convert backend strategy into frontend Strategy structure.
 */
function mapStrategy(strategy: any): Strategy {
  const riskParameters = strategy.risk_parameters ?? {};

  const rules = Array.isArray(strategy.rules)
    ? strategy.rules.map((rule: any) => String(rule))
    : [];

  return {
    id: String(strategy.id),
    name: strategy.name ?? '',
    version: strategy.version ?? '',
    description: strategy.description ?? '',
    status: strategy.status ?? 'testing',
    account_ids: Array.isArray(strategy.account_ids)
      ? strategy.account_ids.map(String)
      : [],
    total_trades: Number(strategy.total_trades ?? 0),
    win_rate: Number(strategy.win_rate ?? 0),
    profit_loss: Number(strategy.profit_loss ?? 0),
    max_drawdown: Number(strategy.max_drawdown ?? 0),
    profit_factor: Number(strategy.profit_factor ?? 0),
    created_date:
      strategy.created_date ??
      strategy.created_at ??
      '',
    updated_date:
      strategy.updated_date ??
      strategy.updated_at ??
      '',
    rules,
    risk_parameters: {
      max_risk_per_trade:
        riskParameters.max_risk_per_trade ?? '',
      max_daily_drawdown:
        riskParameters.max_daily_drawdown ?? '',
      rr_target:
        riskParameters.rr_target ?? '',
      breakeven_trigger:
        riskParameters.breakeven_trigger ?? '',
    },
    version_history: Array.isArray(strategy.version_history)
      ? strategy.version_history
      : [],
  };
}

/*
 * Convert backend journal entry into frontend structure.
 */
function mapJournalEntry(entry: any): JournalEntry {
  return {
    id: String(entry.id),
    trade_id: String(entry.trade_id ?? ''),
    account_id: String(entry.account_id),
    symbol: entry.symbol ?? '',
    date: entry.date ?? '',
    result: entry.result,
    notes: entry.notes ?? '',
    reason: entry.reason ?? '',
    lessons: entry.lessons ?? '',
    strategy_version: entry.strategy_version ?? '',
    tags: Array.isArray(entry.tags)
      ? entry.tags.map(String)
      : [],
    created_at: entry.created_at ?? '',
    updated_at: entry.updated_at ?? '',
    ai_detected_reason:
      entry.ai_detected_reason ?? undefined,
    ai_recommendation:
      entry.ai_recommendation ?? undefined,
    ai_modification:
      entry.ai_modification ?? undefined,
  };
}

export const TradingAPI = {
  // =====================================================
  // ACCOUNTS
  // =====================================================

  async getAccounts(): Promise<TradingAccount[]> {
    const data = await apiRequest<{
      accounts: any[];
    }>('/api/accounts');

    return data.accounts.map(mapAccount);
  },

  async addAccount(
    accountData: Partial<TradingAccount>
  ): Promise<TradingAccount> {
    const data = await apiRequest<{
      account: any;
    }>('/api/accounts', {
      method: 'POST',
      body: JSON.stringify(accountData),
    });

    return mapAccount(data.account);
  },

  async removeAccount(
    accountId: string
  ): Promise<boolean> {
    await apiRequest<{
      success: boolean;
    }>(`/api/accounts/${encodeURIComponent(accountId)}`, {
      method: 'DELETE',
    });

    return true;
  },

  async syncAccount(
    accountId: string
  ): Promise<{ lastSync: string; ping: number }> {
    let targetId = accountId;
    if (!targetId || targetId === 'all' || !isValidUUID(targetId)) {
      const accs = await this.getAccounts();
      if (accs.length === 0) {
        throw new Error('No MT5 accounts available to sync.');
      }
      targetId = accs[0].id;
    }

    const data = await apiRequest<{
      status: string;
      lastSync: string;
      ping: number;
    }>(`/api/accounts/${encodeURIComponent(targetId)}/sync`, {
      method: 'POST',
    });

    return {
      lastSync: data.lastSync,
      ping: data.ping || 20,
    };
  },

  // =====================================================
  // TRADES
  // =====================================================

  async getTrades(
    accountId: string
  ): Promise<Trade[]> {
    const endpoint = `/api/trades${buildAccountQuery(accountId)}`;
    const data = await apiRequest<{
      trades: any[];
    }>(endpoint);

    return (data?.trades || []).map(mapTrade);
  },

  async getTradeById(
    tradeId: string
  ): Promise<Trade | undefined> {
    const trades = await this.getTrades('all');

    return trades.find(
      (trade) => trade.id === tradeId
    );
  },

  // =====================================================
  // OPEN POSITIONS
  // =====================================================

  async getOpenPositions(
    accountId: string
  ): Promise<OpenPosition[]> {
    const endpoint = `/api/positions${buildAccountQuery(accountId)}`;

    const data = await apiRequest<{
      positions: any[];
    }>(endpoint);

    return (data?.positions || []).map(mapPosition);
  },

  async closePosition(
    _positionId: string
  ): Promise<Trade | null> {
    throw new Error(
      'Closing MT5 positions is not connected yet.'
    );
  },

  // =====================================================
  // ACTIVITY
  // =====================================================

  async getRecentActivity(
    accountId: string
  ): Promise<SystemActivity[]> {
    const endpoint = `/api/activity${buildAccountQuery(accountId)}`;
    const [activityData, accountData] =
      await Promise.all([
        apiRequest<{
          activities: any[];
        }>(endpoint),
        apiRequest<{
          accounts: any[];
        }>('/api/accounts'),
      ]);

    const accounts = (accountData?.accounts || []).map(mapAccount);

    return (activityData?.activities || []).map(
      (activity) =>
        mapActivity(activity, accounts)
    );
  },

  // =====================================================
  // STRATEGIES
  // =====================================================

  async getStrategies(
    _accountId: string
  ): Promise<Strategy[]> {
    const data = await apiRequest<{
      strategies: any[];
    }>('/api/strategies');

    return (data?.strategies || []).map(mapStrategy);
  },

  // =====================================================
  // JOURNAL
  // =====================================================

  async getJournalEntries(
    accountId: string
  ): Promise<JournalEntry[]> {
    const endpoint = `/api/journal${buildAccountQuery(accountId)}`;

    const data = await apiRequest<{
      journal: any[];
    }>(endpoint);

    return (data?.journal || []).map(mapJournalEntry);
  },

  async addJournalEntry(
    _entry: Omit<
      JournalEntry,
      'id' | 'created_at' | 'updated_at'
    >
  ): Promise<JournalEntry> {
    throw new Error(
      'Creating journal entries is not connected to the backend yet.'
    );
  },

  // =====================================================
  // RISK
  // =====================================================

  async getRiskStatus(
    accountId: string
  ): Promise<RiskStatus> {
    /*
     * "All Accounts" has no single risk configuration yet.
     * Return a safe default until aggregate risk is implemented.
     */
    if (!accountId || accountId === 'all' || !isValidUUID(accountId)) {
      return {
        daily_risk_percent: 0,
        daily_limit_percent: 0,
        status: 'within_limit',
        current_drawdown: 0,
        max_drawdown_limit: 0,
        trades_remaining_today: 0,
        max_daily_trades: 0,
      };
    }

    const data = await apiRequest<{
      account_id: string;
      risk: any | null;
    }>(
      `/api/risk?account_id=${encodeURIComponent(accountId)}`
    );

    if (!data.risk) {
      return {
        daily_risk_percent: 0,
        daily_limit_percent: 0,
        status: 'within_limit',
        current_drawdown: 0,
        max_drawdown_limit: 0,
        trades_remaining_today: 0,
        max_daily_trades: 0,
      };
    }

    const risk = data.risk;

    const dailyLimit = Number(
      risk.daily_risk_limit_percent ?? 0
    );

    const currentRisk = 0;

    let status: RiskStatus['status'] =
      'within_limit';

    if (risk.trading_locked) {
      status = 'locked';
    } else if (
      dailyLimit > 0 &&
      currentRisk >= dailyLimit * 0.8
    ) {
      status = 'approaching';
    }

    return {
      daily_risk_percent: currentRisk,
      daily_limit_percent: dailyLimit,
      status,
      current_drawdown: 0,
      max_drawdown_limit: Number(
        risk.max_drawdown_limit_percent ?? 0
      ),
      trades_remaining_today: Number(
        risk.max_open_positions ?? 0
      ),
      max_daily_trades: Number(
        risk.max_open_positions ?? 0
      ),
    };
  },

  // =====================================================
  // SYSTEM HEALTH
  // =====================================================

  async getSystemHealth(): Promise<SystemHealthItem[]> {
    const data = await apiRequest<any>(
      '/api/health'
    );

    return [
      {
        id: 'backend',
        name: 'FastAPI Backend',
        status:
          data.status === 'online'
            ? 'ok'
            : 'error',
        message:
          data.status === 'online'
            ? 'Backend API is online'
            : 'Backend API is offline',
      },
      {
        id: 'database',
        name: 'Database',
        status:
          data.database === 'connected'
            ? 'ok'
            : data.database === 'configured'
              ? 'warning'
              : 'error',
        message:
          data.database === 'connected'
            ? 'Database connection active'
            : 'Database configured',
      },
      {
        id: 'mt5',
        name: 'MT5 Bridge',
        status:
          data.mt5_bridge === 'ready'
            ? 'warning'
            : 'coming_soon',
        message:
          data.mt5_bridge === 'ready'
            ? 'MT5 bridge is not connected to a real account yet'
            : 'MT5 integration coming soon',
      },
    ];
  },

  // =====================================================
  // EQUITY CURVE
  // =====================================================

  getEquityCurve(
    _accountId: string,
    _timeframe: string
  ): EquityDataPoint[] {
    /*
     * Equity history endpoint has not been created yet.
     * Keep returning an empty array instead of mock data.
     */
    return [];
  },
};