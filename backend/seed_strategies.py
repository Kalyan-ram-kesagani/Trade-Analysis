import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
url = os.getenv('DATABASE_URL', '')
if url.startswith('postgresql+asyncpg://'):
    url = url.replace('postgresql+asyncpg://', 'postgresql://', 1)

async def main():

    conn = await asyncpg.connect(url)
    with open('backend/database/ai_schema.sql', 'r') as f:
        sql = f.read()
    await conn.execute(sql)
    print("ai_schema.sql executed successfully")
    
    count = await conn.fetchval("SELECT count(*) FROM strategies")
    print(f"Strategies count: {count}")
    if count == 0:
        await conn.execute("""
            INSERT INTO strategies (name, version, description, status, rules, risk_parameters)
            VALUES 
            ('OrderFlow Momentum', '2.1', 'Captures momentum shifts aligned with higher timeframe institutional order flow and volume spikes.', 'active', 
             '[{"type": "entry", "indicator": "EMA_CROSS", "params": {"fast": 9, "slow": 21}}, {"type": "filter", "indicator": "RSI", "params": {"period": 14, "max": 65}}]'::jsonb,
             '{"max_risk_per_trade_pct": 1.5, "max_drawdown_pct": 10.0, "max_daily_loss_pct": 3.0}'::jsonb),
            ('Mean Reversion Pro', '1.4', 'Executes mean reversion entries at statistically extreme Bollinger Band deviations with RSI divergence confirmation.', 'active',
             '[{"type": "entry", "indicator": "BOLLINGER_BAND", "params": {"period": 20, "std": 2.2}}, {"type": "filter", "indicator": "RSI", "params": {"period": 14, "overbought": 70, "oversold": 30}}]'::jsonb,
             '{"max_risk_per_trade_pct": 1.0, "max_drawdown_pct": 8.0, "max_daily_loss_pct": 2.5}'::jsonb)
        """)
        print("Seeded 2 baseline strategies successfully")
    
    rows = await conn.fetch("SELECT id, name, version, status FROM strategies")
    for r in rows:
        print(f"Strategy: {r['name']} v{r['version']} (Status: {r['status']}, ID: {r['id']})")
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
