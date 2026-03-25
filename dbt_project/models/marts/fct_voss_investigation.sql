-- fct_voss_investigation.sql
--
-- Build an investigation model using your macro.
--
-- Steps:
--   1. Pull from fct_trade_routes using ref()
--   2. Call your flag_suspicious macro to add the is_suspicious column
--   3. Filter to only suspicious rows
--   4. Add a risk_level column: 'high' if cargo_type is 'classified', else 'medium'
--
-- Check the objectives panel for specifics.

select 1 as placeholder
