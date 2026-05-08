-- stg_shipments.sql (carried forward)

with source as (
    select * from {{ source('federation', 'raw_shipments') }}
),
renamed as (
    select shipment_id, origin_planet as origin_planet_id,
        dest_planet as destination_planet_id, cargo_type,
        cast(replace(cargo_mass, 'kg', '') as integer) as cargo_mass_kg,
        cast(departed_at as timestamp) as departed_at,
        cast(arrived_at as timestamp) as arrived_at,
        lower(status) as status, voss_flag, updated_at
    from source
)
select * from renamed
