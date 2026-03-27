-- fct_shipment_log.sql
--
-- This model should be INCREMENTAL. Instead of rebuilding all data every run,
-- it should only process rows that are new or updated since the last run.
--
-- The objectives panel and comms will walk you through incremental models.
-- Key ideas: config block, unique key, and a filter for new rows only.
-- See dbt docs for syntax.
--
-- The updated_at column in stg_shipments tracks when each row last changed.
-- Use it to filter for new/updated records.
--
-- Check the objectives panel for specifics.

select 1 as placeholder
-- Replace this with your incremental model
