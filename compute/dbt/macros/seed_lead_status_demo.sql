{#
  DEMO ONLY: fake some status changes, as if the sellers had already worked on some leads,
  so the reports have something to show. Runs on every dbt invocation (on-run-start), right
  after create_lead_status_table() and before the models, when lead_assignments already exists.

  Of the assigned leads, roughly: ~20% contacted, ~12% interested, ~8% converted (each step is one
  row, as the app would write it), the rest stay pending (no row). Deterministic (hash of lead_id).
  Leads that already have a status are skipped, so the changes made in the app are never touched.

  It also seeds leads assigned in later runs, so disable it on real data:
      dbt build --vars '{seed_demo_status: false}'
#}
{% macro seed_lead_status_demo() %}
{% if var('seed_demo_status', true) %}
INSERT INTO {{ target.schema }}.lead_status (lead_id, status, updated_at, updated_by, note)
WITH picked AS (
    SELECT
        assumeNotNull(lead_id)                              AS lead_id,
        seller_id,
        multiIf(cityHash64(lead_id) % 100 < 8,  3,          -- converted
                cityHash64(lead_id) % 100 < 20, 2,          -- interested
                cityHash64(lead_id) % 100 < 40, 1,          -- contacted
                0)                                          AS final_stage
    FROM {{ source('pipeline', 'lead_assignments') }}
    WHERE seller_id IS NOT NULL
      AND lead_id NOT IN (SELECT lead_id FROM {{ target.schema }}.lead_status)
)
SELECT
    lead_id,
    ['contacted', 'interested', 'converted'][stage]         AS status,
    now64(3) + toIntervalSecond(stage)                      AS updated_at,   -- keeps the steps in order
    seller_id                                               AS updated_by,
    'demo seed'                                             AS note
FROM picked
ARRAY JOIN range(1, final_stage + 1) AS stage
WHERE final_stage > 0
{% else %}
SELECT 1   -- demo status seed disabled (seed_demo_status: false)
{% endif %}
{% endmacro %}
