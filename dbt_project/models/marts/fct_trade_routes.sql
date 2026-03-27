-- fct_trade_routes.sql (carried forward)

with shipments as (
    select * from {{ ref('stg_shipments') }}
), planets as (
    select * from {{ ref('stg_planets') }}
), routes as (
    select s.shipment_id, s.cargo_type, s.cargo_mass_kg, s.status,
        s.departed_at, s.arrived_at,
        origin.planet_name as origin_planet_name,
        dest.planet_name as destination_planet_name
    from shipments s
    left join planets origin on s.origin_planet_id = origin.planet_id
    left join planets dest on s.destination_planet_id = dest.planet_id
)
select * from routes
