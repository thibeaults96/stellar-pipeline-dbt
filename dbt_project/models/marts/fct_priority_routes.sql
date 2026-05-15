
select
    *,
    {{ cargo_priority("cargo_type") }} as priority
from {{ ref('fct_trade_routes') }}
