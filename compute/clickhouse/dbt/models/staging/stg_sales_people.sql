{{ config(materialized='view') }}

-- Normalize the raw sales people Excel: snake_case names, lists as arrays, typed columns
SELECT
    "Seller ID"                                                             AS seller_id,
    "Full Name"                                                             AS full_name,
    lowerUTF8(trimBoth("Email"))                                            AS email,
    splitByChar(';', replaceAll(lower(ifNull("Languages", '')), ' ', ''))   AS languages,
    splitByChar(';', replaceAll(lower(ifNull("Specialties", '')), ' ', '')) AS specialties,
    toInt32("Max Open Leads")                                               AS max_open_leads,
    lower(trimBoth(ifNull("Active", ''))) = 'yes'                           AS is_active
FROM {{ source('raw', 'sales_people') }}
