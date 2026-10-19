{{ config(materialized='view') }}

SELECT
    lead_id,
    seller_id,
    match_type,
    reason,
    assigned_at,
    run_id
FROM {{ source('pipeline', 'lead_assignments') }}
