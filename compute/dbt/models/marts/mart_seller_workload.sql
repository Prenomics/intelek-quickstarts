{{ config(materialized='table', order_by='tuple()') }}   -- seller_id is Nullable (raw Excel)

-- One row per seller: how many leads they got, how well they match, and remaining capacity
WITH assigned AS (
    SELECT
        seller_id,
        count()                                                 AS n_assigned_leads,
        countIf(match_type = 'full_match')                      AS n_full_match,
        countIf(match_type = 'language_only')                   AS n_language_only
    FROM {{ ref('mart_lead_assignments') }}
    WHERE seller_id IS NOT NULL
    GROUP BY seller_id
)

SELECT
    s.seller_id                                                 AS seller_id,
    s.full_name                                                 AS seller_name,
    s.is_active                                                 AS is_active,
    arrayStringConcat(s.languages, ', ')                        AS languages,
    arrayStringConcat(s.specialties, ', ')                      AS specialties,
    s.max_open_leads                                            AS max_open_leads,
    toInt64(ifNull(a.n_assigned_leads, 0))                      AS n_assigned_leads,
    toInt64(ifNull(a.n_full_match, 0))                          AS n_full_match,
    toInt64(ifNull(a.n_language_only, 0))                       AS n_language_only,
    s.max_open_leads - toInt64(ifNull(a.n_assigned_leads, 0))   AS free_slots,
    round(100.0 * ifNull(a.n_assigned_leads, 0) / nullIf(s.max_open_leads, 0), 1)
                                                                AS capacity_used_pct
FROM {{ ref('stg_sales_people') }} s
LEFT JOIN assigned a ON a.seller_id = s.seller_id
SETTINGS join_use_nulls = 1
