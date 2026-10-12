{{ config(materialized='view', schema='demo_stg') }}

-- Leads are already normalized by sql/01_unify_leads.sql; keep the columns the marts need
SELECT
    lead_id,
    source_system,
    full_name,
    email,
    company_name,
    country,
    preferred_language,
    content_of_interest,
    created_at
FROM {{ source('demo_stg', 'leads') }}
