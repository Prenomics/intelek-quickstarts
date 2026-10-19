{{ config(materialized='view') }}

-- Leads are already normalized (sql/01_unify_leads.sql) and cleaned (basic_transf.py);
-- keep the columns the marts need
-- lead_id is Nullable in leads_clean (written from Python) but never NULL: leads without id are rejected
SELECT
    assumeNotNull(lead_id)                              AS lead_id,
    source_system,
    full_name,
    email,
    company_name,
    country,
    preferred_language,
    content_of_interest,
    created_at,
    dq_issues,
    merged_lead_ids
FROM {{ source('pipeline', 'leads_clean') }}
