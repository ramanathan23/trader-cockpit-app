-- One-time data script: mark F&O-eligible symbols in the symbols table.
-- Safe to re-run (idempotent).
--
-- Usage:
--   psql -U trader -d trader_cockpit -f scripts/mark_fno_symbols.sql
--   docker exec -i trader_timescaledb psql -U trader -d trader_cockpit -f /dev/stdin < scripts/mark_fno_symbols.sql

-- Step 1: Add is_fno column if it doesn't exist yet.
ALTER TABLE symbols ADD COLUMN IF NOT EXISTS is_fno BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_symbols_is_fno
    ON symbols(is_fno)
    WHERE is_fno = TRUE;

-- Step 2: Reset all rows.
UPDATE symbols SET is_fno = FALSE WHERE is_fno = TRUE;

-- Step 3: Mark F&O symbols.
UPDATE symbols
SET    is_fno = TRUE
WHERE  symbol IN (
    '360ONE', 'ABB', 'APLAPOLLO', 'AUBANK', 'ADANIENSOL', 'ADANIENT',
    'ADANIGREEN', 'ADANIPORTS', 'ADANIPOWER', 'ABCAPITAL', 'ALKEM', 'AMBER',
    'AMBUJACEM', 'ANGELONE', 'APOLLOHOSP', 'ASHOKLEY', 'ASIANPAINT', 'ASTRAL',
    'AUROPHARMA', 'DMART', 'AXISBANK', 'BSE', 'BAJAJ-AUTO', 'BAJFINANCE',
    'BAJAJFINSV', 'BAJAJHLDNG', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BDL',
    'BEL', 'BHARATFORG', 'BHEL', 'BPCL', 'BHARTIARTL', 'BIOCON', 'BLUESTARCO',
    'BOSCHLTD', 'BRITANNIA', 'CGPOWER', 'CANBK', 'CDSL', 'CHOLAFIN', 'CIPLA',
    'COALINDIA', 'COCHINSHIP', 'COFORGE', 'COLPAL', 'CAMS', 'CONCOR',
    'CROMPTON', 'CUMMINSIND', 'DLF', 'DABUR', 'DALBHARAT', 'DELHIVERY',
    'DIVISLAB', 'DIXON', 'DRREDDY', 'ETERNAL', 'EICHERMOT', 'EXIDEIND',
    'FORCEMOT', 'NYKAA', 'FORTIS', 'GAIL', 'GMRAIRPORT', 'GLENMARK',
    'GODFRYPHLP', 'GODREJCP', 'GODREJPROP', 'GRASIM', 'HCLTECH', 'HDFCAMC',
    'HDFCBANK', 'HDFCLIFE', 'HAVELLS', 'HEROMOTOCO', 'HINDALCO', 'HAL',
    'HINDPETRO', 'HINDUNILVR', 'HINDZINC', 'POWERINDIA', 'HUDCO', 'HYUNDAI',
    'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDFCFIRSTB', 'ITC', 'INDIANB',
    'IEX', 'IOC', 'IRFC', 'IREDA', 'INDUSTOWER', 'INDUSINDBK', 'NAUKRI',
    'INFY', 'INOXWIND', 'INDIGO', 'JINDALSTEL', 'JSWENERGY', 'JSWSTEEL',
    'JIOFIN', 'JUBLFOOD', 'KEI', 'KPITTECH', 'KALYANKJIL', 'KAYNES',
    'KFINTECH', 'KOTAKBANK', 'LTF', 'LICHSGFIN', 'LTM', 'LT', 'LAURUSLABS',
    'LICI', 'LODHA', 'LUPIN', 'M&M', 'MANAPPURAM', 'MANKIND', 'MARICO',
    'MARUTI', 'MFSL', 'MAXHEALTH', 'MAZDOCK', 'MOTILALOFS', 'MPHASIS', 'MCX',
    'MUTHOOTFIN', 'NBCC', 'NHPC', 'NMDC', 'NTPC', 'NATIONALUM', 'NESTLEIND',
    'NAM-INDIA', 'NUVAMA', 'OBEROIRLTY', 'ONGC', 'OIL', 'PAYTM', 'OFSS',
    'POLICYBZR', 'PGEL', 'PIIND', 'PNBHOUSING', 'PAGEIND', 'PATANJALI',
    'PERSISTENT', 'PETRONET', 'PIDILITIND', 'PPLPHARMA', 'POLYCAB', 'PFC',
    'POWERGRID', 'PREMIERENE', 'PRESTIGE', 'PNB', 'RBLBANK', 'RECLTD', 'RVNL',
    'RELIANCE', 'SBICARD', 'SBILIFE', 'SHREECEM', 'SRF', 'SAMMAANCAP',
    'MOTHERSON', 'SHRIRAMFIN', 'SIEMENS', 'SOLARINDS', 'SONACOMS', 'SBIN',
    'SAIL', 'SUNPHARMA', 'SUPREMEIND', 'SUZLON', 'SWIGGY', 'TATACONSUM',
    'TVSMOTOR', 'TCS', 'TATAELXSI', 'TMPV', 'TATAPOWER', 'TATASTEEL',
    'TATATECH', 'TECHM', 'FEDERALBNK', 'INDHOTEL', 'PHOENIXLTD', 'TITAN',
    'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TIINDIA', 'UNOMINDA', 'UPL',
    'ULTRACEMCO', 'UNIONBANK', 'UNITDSPR', 'VBL', 'VEDL', 'VMM', 'IDEA',
    'VOLTAS', 'WAAREEENER', 'WIPRO', 'YESBANK', 'ZYDUSLIFE'
);

-- Step 4: Verification — show count and any unmatched symbols.
SELECT
    COUNT(*)                                          AS fno_marked,
    (SELECT COUNT(*) FROM symbols WHERE is_fno = FALSE
       AND series = 'EQ')                            AS non_fno_eq
FROM symbols
WHERE is_fno = TRUE;
