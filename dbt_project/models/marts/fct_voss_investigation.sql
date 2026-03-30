-- fct_voss_investigation.sql
-- Investigation model: suspicious shipments flagged for Federation Command.

with base as (
    select * from {{ ref('fct_trade_routes') }}
),
flagged as (
    select
        shipment_id,
        cargo_type,
        cargo_mass_kg,
        status,
        origin_planet_name,
        destination_planet_name,
        dest_is_federation,
        voss_flag,
        {{ flag_suspicious('is_suspicious') }},
        case
            when cargo_type = 'classified' then 'high'
            else 'medium'
        end as risk_level
    from base
)
select * from flagged
where is_suspicious = 1
