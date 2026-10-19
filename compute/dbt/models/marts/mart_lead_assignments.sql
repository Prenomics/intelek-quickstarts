{{ config(materialized='table', order_by='lead_id') }}

-- One row per lead with its assigned seller (if any).
-- Leads that the Python step has not processed yet appear as 'pending';
-- leads set aside by the cleaning step appear as 'rejected', with the reason.
WITH clean AS (
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
        l.dq_issues                                         AS dq_issues,
        l.merged_lead_ids                                   AS merged_lead_ids,
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
),

rejected AS (
    SELECT
        assumeNotNull(r.lead_id)                            AS lead_id,
        r.source_system                                     AS source_system,
        r.full_name                                         AS lead_name,
        r.email                                             AS lead_email,
        r.company_name                                      AS company_name,
        r.country                                           AS country,
        r.preferred_language                                AS preferred_language,
        r.content_of_interest                               AS content_of_interest,
        r.created_at                                        AS lead_created_at,
        NULL                                                AS dq_issues,
        NULL                                                AS merged_lead_ids,
        NULL                                                AS seller_id,
        NULL                                                AS seller_name,
        NULL                                                AS seller_email,
        'rejected'                                          AS match_type,
        r.rejection_reason                                  AS match_reason,
        NULL                                                AS assigned_at,
        NULL                                                AS days_to_assign
    FROM {{ ref('stg_leads_rejected') }} r
    WHERE r.lead_id IS NOT NULL   -- leads without id stay only in leads_rejected
)

SELECT * FROM clean
UNION ALL
SELECT * FROM rejected
