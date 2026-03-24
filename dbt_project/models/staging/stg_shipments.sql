-- stg_shipments.sql
-- Staging model for raw cargo shipment data
--
-- How this works:
--   The "with source as (...)" block pulls raw data using source().
--   source() tells dbt where the raw table lives so you don't hardcode names.
--   The "renamed as (...)" block is where you clean up the columns.
--   The final "select * from renamed" outputs your cleaned version.
--
-- What to do:
--   1. Click "raw_shipments" under SOURCE DATA to see the raw columns
--   2. Open stg_planets.sql to see a finished example
--   3. Fill in the renamed block below
--   4. Check the objectives panel for what each column needs
--
-- Raw columns: shipment_id, origin_planet, dest_planet, cargo_type,
--              cargo_mass, departed_at, arrived_at, status, voss_flag

with source as (

    select * from {{ source('federation', 'raw_shipments') }}

),

renamed as (

    select
        -- Your columns go here. Check stg_planets.sql for the pattern:
        --     planet_id,
        --     planet_name,
        --     cast(population as bigint) as population
        *

    from source

)

select * from renamed
