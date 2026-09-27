import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
url = os.getenv('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')

async def main():
    conn = await asyncpg.connect(url)
    
    # 1. Additive columns to journal_entries
    await conn.execute("""
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
        
        -- Unique index for idempotency: one AI journal per closed trade
        CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_trade_ai_type 
            ON journal_entries(trade_id, journal_type) 
            WHERE trade_id IS NOT NULL AND journal_type = 'AI_TRADE_REVIEW';
            
        CREATE INDEX IF NOT EXISTS idx_journal_status ON journal_entries(status);
    """)
    print("journal_entries schema updated successfully")
    
    cols = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'journal_entries' ORDER BY ordinal_position")
    print("CURRENT COLUMNS:")
    for c in cols:
        print(f"  {c['column_name']}: {c['data_type']}")
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
