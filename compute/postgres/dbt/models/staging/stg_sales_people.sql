{{ config(materialized='view') }}

-- Normalize the raw sales people Excel: snake_case names, lists as arrays, typed columns
SELECT
    "Seller ID"                                                     AS seller_id,
    "Full Name"                                                     AS full_name,
    lower(trim("Email"))                                            AS email,
    string_to_array(replace(lower("Languages"), ' ', ''), ';')      AS languages,
    string_to_array(replace(lower("Specialties"), ' ', ''), ';')    AS specialties,
    "Max Open Leads"::int                                           AS max_open_leads,
    lower(trim("Active")) = 'yes'                                   AS is_active
FROM {{ source('raw', 'sales_people') }}
