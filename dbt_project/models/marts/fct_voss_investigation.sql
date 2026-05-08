select 1 as is_suspicious, 'medium' as risk_level
from {{ ref('fct_trade_routes') }}
