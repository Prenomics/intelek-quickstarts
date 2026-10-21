/*
================================================================================
 Consolidate leads and sales people into the reporting tables (marts)
 (ClickHouse; every table lives in the DB_NAME database)

 Plain-SQL alternative to the dbt project in dbt/: it builds the same objects,
 with the same names and logic, so run one or the other (`dbt build` or this
 script) and the result is identical.

 Input  (built by the previous steps):
   leads_clean       -> python_ipynb/basic_transf.py   (clean leads, dq_issues flags)
   leads_rejected    -> python_ipynb/basic_transf.py   (leads that cannot be assigned)
   lead_assignments  -> python_ipynb/assign_leads.py   (lead -> seller)
   sales_people      -> raw table imported from Postgres
   lead_status       -> status changes written by the business app (created here if missing;
                        section 0b fakes some changes for the demo: delete it on real data)

 Output:
   stg_leads, stg_leads_rejected, stg_sales_people, stg_lead_assignments, stg_lead_status  (views)
   mart_lead_assignments  -> one row per lead: data, dq flags, seller, match type
                             (full_match | language_only | unassigned | rejected | pending)
                             and commercial status (pending | contacted | interested | converted)
   mart_seller_workload   -> one row per seller: assigned leads, match quality, free capacity

 The last query replays the dbt tests: one row per test with its failing rows.
 Every row should show n_failures = 0.

 The script is idempotent: it replaces the views and rebuilds the tables on every run.
================================================================================
*/

-- ---------------------------------------------------------------------------
-- 0) lead_status belongs to the business app (sellers update it): only create it if
--    missing, never drop it. Same as dbt/macros/create_lead_status_table.sql
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lead_status (
    lead_id     String,
    status      LowCardinality(String),
    updated_at  DateTime64(3, 'UTC') DEFAULT now64(3),
    updated_by  Nullable(String),                 -- seller or user who made the change
    note        Nullable(String),
    CONSTRAINT valid_status CHECK status IN ('pending', 'contacted', 'interested', 'converted')
)
ENGINE = MergeTree
ORDER BY (lead_id, updated_at);


-- ---------------------------------------------------------------------------
-- 0b) DEMO ONLY: fake some status changes, as if the sellers had already worked on
--     some leads (same as dbt/macros/seed_lead_status_demo.sql). Delete this block on
--     real data: it would also seed the leads assigned in later runs.
--     Of the assigned leads: ~20% contacted, ~12% interested, ~8% converted (one row per
--     step), the rest pending. Leads that already have a status are skipped.
-- ---------------------------------------------------------------------------
INSERT INTO lead_status (lead_id, status, updated_at, updated_by, note)
WITH picked AS (
    SELECT
        assumeNotNull(lead_id)                              AS lead_id,
        seller_id,
        multiIf(cityHash64(lead_id) % 100 < 8,  3,          -- converted
                cityHash64(lead_id) % 100 < 20, 2,          -- interested
                cityHash64(lead_id) % 100 < 40, 1,          -- contacted
                0)                                          AS final_stage
    FROM lead_assignments
    WHERE seller_id IS NOT NULL
      AND lead_id NOT IN (SELECT lead_id FROM lead_status)
)
SELECT
    lead_id,
    ['contacted', 'interested', 'converted'][stage]         AS status,
    now64(3) + toIntervalSecond(stage)                      AS updated_at,   -- keeps the steps in order
    seller_id                                               AS updated_by,
    'demo seed'                                             AS note
FROM picked
ARRAY JOIN range(1, final_stage + 1) AS stage
WHERE final_stage > 0;


-- ---------------------------------------------------------------------------
-- 1) Staging views: one per input table (same as dbt/models/staging)
-- ---------------------------------------------------------------------------

-- Clean leads: keep the columns the marts need.
-- lead_id is Nullable in leads_clean (written from Python) but never NULL: leads without id are rejected
CREATE OR REPLACE VIEW stg_leads AS
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
FROM leads_clean;

-- Leads set aside by the cleaning step: they never reach the assignment
CREATE OR REPLACE VIEW stg_leads_rejected AS
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
FROM leads_rejected;

-- Sales people: lists as arrays, typed columns
CREATE OR REPLACE VIEW stg_sales_people AS
SELECT
    seller_id,
    full_name,
    lowerUTF8(trimBoth(email))                                              AS email,
    splitByChar(';', replaceAll(lower(ifNull(languages, '')), ' ', ''))     AS languages,
    splitByChar(';', replaceAll(lower(ifNull(specialties, '')), ' ', ''))   AS specialties,
    toInt32(max_open_leads)                                                 AS max_open_leads,
    lower(trimBoth(ifNull(active, ''))) = 'yes'                             AS is_active
FROM sales_people;

-- Lead -> seller assignments produced by the Python step
CREATE OR REPLACE VIEW stg_lead_assignments AS
SELECT
    lead_id,
    seller_id,
    match_type,
    reason,
    assigned_at,
    run_id
FROM lead_assignments;

-- Current status per lead: lead_status is an append-only log (one row per change),
-- so the current status is the latest row of each lead. Leads with no row are 'pending' (in the mart).
CREATE OR REPLACE VIEW stg_lead_status AS
SELECT
    lead_id,
    argMax(status, updated_at)                          AS status,
    max(updated_at)                                     AS status_updated_at,
    argMax(updated_by, updated_at)                      AS status_updated_by,
    count()                                             AS n_status_changes
FROM lead_status
GROUP BY lead_id;


-- ---------------------------------------------------------------------------
-- 2) mart_lead_assignments: one row per lead with its assigned seller (if any).
--    Leads that the Python step has not processed yet appear as 'pending';
--    leads set aside by the cleaning step appear as 'rejected', with the reason.
--    status is the commercial status set by the sellers in the business app (lead_status):
--    'pending' until someone changes it. It reflects lead_status as of the last run.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS mart_lead_assignments;

CREATE TABLE mart_lead_assignments
ENGINE = MergeTree
ORDER BY (lead_id)
AS
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
                                                            AS days_to_assign,
        ifNull(st.status, 'pending')                        AS status,
        st.status_updated_at                                AS status_updated_at,
        st.status_updated_by                                AS status_updated_by
    FROM stg_leads l
    LEFT JOIN stg_lead_assignments a ON a.lead_id = l.lead_id
    LEFT JOIN stg_sales_people s     ON s.seller_id = a.seller_id
    LEFT JOIN stg_lead_status st     ON st.lead_id = l.lead_id
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
        NULL                                                AS days_to_assign,
        ifNull(st.status, 'pending')                        AS status,
        st.status_updated_at                                AS status_updated_at,
        st.status_updated_by                                AS status_updated_by
    FROM stg_leads_rejected r
    LEFT JOIN stg_lead_status st ON st.lead_id = r.lead_id
    WHERE r.lead_id IS NOT NULL   -- leads without id stay only in leads_rejected
    SETTINGS join_use_nulls = 1
)

SELECT * FROM clean
UNION ALL
SELECT * FROM rejected;


-- ---------------------------------------------------------------------------
-- 3) mart_seller_workload: one row per seller with assigned leads, match quality
--    and remaining capacity
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS mart_seller_workload;

CREATE TABLE mart_seller_workload
ENGINE = MergeTree
ORDER BY tuple()   -- seller_id is Nullable (raw table)
AS
WITH assigned AS (
    SELECT
        seller_id,
        count()                                                 AS n_assigned_leads,
        countIf(match_type = 'full_match')                      AS n_full_match,
        countIf(match_type = 'language_only')                   AS n_language_only
    FROM mart_lead_assignments
    WHERE seller_id IS NOT NULL
    GROUP BY seller_id
)

SELECT
    s.seller_id                                                 AS seller_id,
    s.full_name                                                 AS seller_name,
    s.is_active                                                 AS is_active,
    arrayStringConcat(s.languages, ', ')                        AS languages,
    arrayStringConcat(s.specialties, ', ')                      AS specialties,
    s.max_open_leads                                            AS max_open_leads,
    toInt64(ifNull(a.n_assigned_leads, 0))                      AS n_assigned_leads,
    toInt64(ifNull(a.n_full_match, 0))                          AS n_full_match,
    toInt64(ifNull(a.n_language_only, 0))                       AS n_language_only,
    s.max_open_leads - toInt64(ifNull(a.n_assigned_leads, 0))   AS free_slots,
    round(100.0 * ifNull(a.n_assigned_leads, 0) / nullIf(s.max_open_leads, 0), 1)
                                                                AS capacity_used_pct
FROM stg_sales_people s
LEFT JOIN assigned a ON a.seller_id = s.seller_id
SETTINGS join_use_nulls = 1;


-- ---------------------------------------------------------------------------
-- 4) Checks: the dbt tests (schema.yml files + tests/), one row per test.
--    Every row should show n_failures = 0.
-- ---------------------------------------------------------------------------
SELECT test, n_failures
FROM (
    -- stg_sales_people
    SELECT 1 AS n, 'stg_sales_people.seller_id unique' AS test,
           (SELECT count() FROM (SELECT seller_id FROM stg_sales_people WHERE seller_id IS NOT NULL
                                 GROUP BY seller_id HAVING count() > 1)) AS n_failures
    UNION ALL SELECT 2, 'stg_sales_people.seller_id not_null',
           (SELECT count() FROM stg_sales_people WHERE seller_id IS NULL)
    UNION ALL SELECT 3, 'stg_sales_people.max_open_leads not_null',
           (SELECT count() FROM stg_sales_people WHERE max_open_leads IS NULL)

    -- stg_leads
    UNION ALL SELECT 4, 'stg_leads.lead_id unique',
           (SELECT count() FROM (SELECT lead_id FROM stg_leads GROUP BY lead_id HAVING count() > 1))
    UNION ALL SELECT 5, 'stg_leads.lead_id not_null',
           (SELECT count() FROM stg_leads WHERE lead_id IS NULL)
    UNION ALL SELECT 6, 'stg_leads.email unique',
           (SELECT count() FROM (SELECT email FROM stg_leads WHERE email IS NOT NULL
                                 GROUP BY email HAVING count() > 1))
    UNION ALL SELECT 7, 'stg_leads.preferred_language not_null',
           (SELECT count() FROM stg_leads WHERE preferred_language IS NULL)
    UNION ALL SELECT 8, 'stg_leads.preferred_language accepted_values',
           (SELECT count() FROM stg_leads WHERE preferred_language IS NOT NULL
                AND preferred_language NOT IN ('es', 'ca', 'en', 'fr', 'de', 'pt'))

    -- stg_lead_status
    UNION ALL SELECT 23, 'stg_lead_status.lead_id unique',
           (SELECT count() FROM (SELECT lead_id FROM stg_lead_status GROUP BY lead_id HAVING count() > 1))
    UNION ALL SELECT 24, 'stg_lead_status.lead_id not_null',
           (SELECT count() FROM stg_lead_status WHERE lead_id IS NULL)
    UNION ALL SELECT 25, 'stg_lead_status.status accepted_values',
           (SELECT count() FROM stg_lead_status
            WHERE status NOT IN ('pending', 'contacted', 'interested', 'converted'))

    -- stg_leads_rejected
    UNION ALL SELECT 9, 'stg_leads_rejected.lead_id unique',
           (SELECT count() FROM (SELECT lead_id FROM stg_leads_rejected WHERE lead_id IS NOT NULL
                                 GROUP BY lead_id HAVING count() > 1))
    UNION ALL SELECT 10, 'stg_leads_rejected.rejection_reason not_null',
           (SELECT count() FROM stg_leads_rejected WHERE rejection_reason IS NULL)

    -- stg_lead_assignments
    UNION ALL SELECT 11, 'stg_lead_assignments.lead_id unique',
           (SELECT count() FROM (SELECT lead_id FROM stg_lead_assignments WHERE lead_id IS NOT NULL
                                 GROUP BY lead_id HAVING count() > 1))
    UNION ALL SELECT 12, 'stg_lead_assignments.lead_id not_null',
           (SELECT count() FROM stg_lead_assignments WHERE lead_id IS NULL)
    UNION ALL SELECT 13, 'stg_lead_assignments.lead_id relationships stg_leads',
           (SELECT count() FROM stg_lead_assignments WHERE lead_id IS NOT NULL
                AND lead_id NOT IN (SELECT lead_id FROM stg_leads))
    UNION ALL SELECT 14, 'stg_lead_assignments.seller_id relationships stg_sales_people',
           (SELECT count() FROM stg_lead_assignments WHERE seller_id IS NOT NULL
                AND seller_id NOT IN (SELECT seller_id FROM stg_sales_people WHERE seller_id IS NOT NULL))

    -- mart_lead_assignments
    UNION ALL SELECT 15, 'mart_lead_assignments.lead_id unique',
           (SELECT count() FROM (SELECT lead_id FROM mart_lead_assignments GROUP BY lead_id HAVING count() > 1))
    UNION ALL SELECT 16, 'mart_lead_assignments.lead_id not_null',
           (SELECT count() FROM mart_lead_assignments WHERE lead_id IS NULL)
    UNION ALL SELECT 17, 'mart_lead_assignments.match_type not_null',
           (SELECT count() FROM mart_lead_assignments WHERE match_type IS NULL)
    UNION ALL SELECT 18, 'mart_lead_assignments.match_type accepted_values',
           (SELECT count() FROM mart_lead_assignments
            WHERE match_type NOT IN ('full_match', 'language_only', 'unassigned', 'pending', 'rejected'))
    UNION ALL SELECT 26, 'mart_lead_assignments.status not_null',
           (SELECT count() FROM mart_lead_assignments WHERE status IS NULL)
    UNION ALL SELECT 27, 'mart_lead_assignments.status accepted_values',
           (SELECT count() FROM mart_lead_assignments
            WHERE status NOT IN ('pending', 'contacted', 'interested', 'converted'))

    -- mart_seller_workload
    UNION ALL SELECT 19, 'mart_seller_workload.seller_id unique',
           (SELECT count() FROM (SELECT seller_id FROM mart_seller_workload WHERE seller_id IS NOT NULL
                                 GROUP BY seller_id HAVING count() > 1))
    UNION ALL SELECT 20, 'mart_seller_workload.seller_id not_null',
           (SELECT count() FROM mart_seller_workload WHERE seller_id IS NULL)
    UNION ALL SELECT 21, 'mart_seller_workload.n_assigned_leads not_null',
           (SELECT count() FROM mart_seller_workload WHERE n_assigned_leads IS NULL)

    -- Business rule (tests/assert_sellers_within_capacity.sql): no seller over capacity,
    -- and inactive sellers get no leads at all
    UNION ALL SELECT 22, 'assert_sellers_within_capacity',
           (SELECT count() FROM mart_seller_workload
            WHERE free_slots < 0 OR (NOT is_active AND n_assigned_leads > 0))
)
ORDER BY n;
