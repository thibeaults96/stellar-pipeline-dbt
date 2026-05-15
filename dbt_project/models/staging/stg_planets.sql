-- stg_planets.sql
-- Helios staging model: planetary registry

with source as (

    select * from {{ source('helios', 'raw_planets') }}

),

renamed as (

    select
        planet_id,
        planet_name,
        sector,
        cast(population as bigint) as population,
        is_federation_member

    from source

)

select * from renamed
