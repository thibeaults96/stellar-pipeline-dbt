-- fct_trade_routes.sql
-- Mart model: combines staging models into something analysts can actually use.
--
-- Quick refresher on ref() vs source():
--   source() pulls from raw external tables (used in staging models)
--   ref() pulls from other dbt models (used here, in marts)
--
-- Example:  select * from  ref('stg_shipments')  (wrap in double curly braces)
--
-- What to do:
--   1. Use ref() to pull from stg_shipments and stg_planets
--   2. Join them so each shipment gets origin and destination planet names
--   3. Add a summary with count and total mass per origin planet
--
-- Check the objectives panel for the specifics.

select 1 as placeholder
-- Replace this with your query
