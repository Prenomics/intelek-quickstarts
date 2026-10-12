{{ config(materialized='view', schema='demo_stg') }}

SELECT
    lead_id,
    seller_id,
    match_type,
    reason,
    assigned_at,
    run_id
FROM {{ source('demo_stg', 'lead_assignments') }}
