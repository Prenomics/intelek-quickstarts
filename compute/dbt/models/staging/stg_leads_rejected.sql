{{ config(materialized='view') }}

-- Leads set aside by the cleaning step: they never reach the assignment
SELECT
    lead_id,                                            -- NULL if rejected for missing_lead_id
    source_system,
    full_name,
    email,
    company_name,
    country,
    preferred_language,
    content_of_interest,
    created_at,
    rejection_reason
FROM {{ source('pipeline', 'leads_rejected') }}
