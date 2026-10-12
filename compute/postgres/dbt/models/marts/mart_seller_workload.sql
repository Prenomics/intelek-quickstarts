{{ config(materialized='table') }}

-- One row per seller: how many leads they got, how well they match, and remaining capacity
WITH assigned AS (
    SELECT
        seller_id,
        count(*)                                                AS n_assigned_leads,
        count(*) FILTER (WHERE match_type = 'full_match')       AS n_full_match,
        count(*) FILTER (WHERE match_type = 'language_only')    AS n_language_only
    FROM {{ ref('mart_lead_assignments') }}
    WHERE seller_id IS NOT NULL
    GROUP BY seller_id
)

SELECT
    s.seller_id,
    s.full_name                                                 AS seller_name,
    s.is_active,
    array_to_string(s.languages, ', ')                          AS languages,
    array_to_string(s.specialties, ', ')                        AS specialties,
    s.max_open_leads,
    coalesce(a.n_assigned_leads, 0)                             AS n_assigned_leads,
    coalesce(a.n_full_match, 0)                                 AS n_full_match,
    coalesce(a.n_language_only, 0)                              AS n_language_only,
    s.max_open_leads - coalesce(a.n_assigned_leads, 0)          AS free_slots,
    round(100.0 * coalesce(a.n_assigned_leads, 0) / nullif(s.max_open_leads, 0), 1)
                                                                AS capacity_used_pct
FROM {{ ref('stg_sales_people') }} s
LEFT JOIN assigned a ON a.seller_id = s.seller_id
