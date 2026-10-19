{{ config(materialized='view') }}

-- Normalize the raw sales people table: lists as arrays, typed columns
SELECT
    seller_id,
    full_name,
    lowerUTF8(trimBoth(email))                                              AS email,
    splitByChar(';', replaceAll(lower(ifNull(languages, '')), ' ', ''))     AS languages,
    splitByChar(';', replaceAll(lower(ifNull(specialties, '')), ' ', ''))   AS specialties,
    toInt32(max_open_leads)                                                 AS max_open_leads,
    lower(trimBoth(ifNull(active, ''))) = 'yes'                             AS is_active
FROM {{ source('raw', 'sales_people') }}
