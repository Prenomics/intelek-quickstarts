{{ config(materialized='table', order_by='lead_id') }}

-- One row per lead with its assigned seller (if any).
-- Leads that the Python step has not processed yet appear as 'pending'.
SELECT
    l.lead_id                                           AS lead_id,
    l.source_system                                     AS source_system,
    l.full_name                                         AS lead_name,
    l.email                                             AS lead_email,
    l.company_name                                      AS company_name,
    l.country                                           AS country,
    l.preferred_language                                AS preferred_language,
    l.content_of_interest                               AS content_of_interest,
    l.created_at                                        AS lead_created_at,
    a.seller_id                                         AS seller_id,
    s.full_name                                         AS seller_name,
    s.email                                             AS seller_email,
    ifNull(a.match_type, 'pending')                     AS match_type,
    a.reason                                            AS match_reason,
    a.assigned_at                                       AS assigned_at,
    round(dateDiff('second', l.created_at, a.assigned_at) / 86400, 1)
                                                        AS days_to_assign
FROM {{ ref('stg_leads') }} l
LEFT JOIN {{ ref('stg_lead_assignments') }} a ON a.lead_id = l.lead_id
LEFT JOIN {{ ref('stg_sales_people') }} s     ON s.seller_id = a.seller_id
SETTINGS join_use_nulls = 1
