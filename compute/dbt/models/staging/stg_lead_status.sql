{{ config(materialized='view') }}

-- Current status per lead: lead_status is an append-only log (one row per change),
-- so the current status is the latest row of each lead. Leads with no row are 'pending' (in the mart).
SELECT
    lead_id,
    argMax(status, updated_at)                          AS status,
    max(updated_at)                                     AS status_updated_at,
    argMax(updated_by, updated_at)                      AS status_updated_by,
    count()                                             AS n_status_changes
FROM {{ source('pipeline', 'lead_status') }}
GROUP BY lead_id
