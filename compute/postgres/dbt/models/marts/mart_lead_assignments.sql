{{ config(materialized='table') }}

-- One row per lead with its assigned seller (if any).
-- Leads that the Python step has not processed yet appear as 'pending'.
SELECT
    l.lead_id,
    l.source_system,
    l.full_name                                         AS lead_name,
    l.email                                             AS lead_email,
    l.company_name,
    l.country,
    l.preferred_language,
    l.content_of_interest,
    l.created_at                                        AS lead_created_at,
    a.seller_id,
    s.full_name                                         AS seller_name,
    s.email                                             AS seller_email,
    coalesce(a.match_type, 'pending')                   AS match_type,
    a.reason                                            AS match_reason,
    a.assigned_at,
    round(extract(epoch FROM a.assigned_at - l.created_at)::numeric / 86400, 1)
                                                        AS days_to_assign
FROM {{ ref('stg_leads') }} l
LEFT JOIN {{ ref('stg_lead_assignments') }} a ON a.lead_id = l.lead_id
LEFT JOIN {{ ref('stg_sales_people') }} s     ON s.seller_id = a.seller_id
