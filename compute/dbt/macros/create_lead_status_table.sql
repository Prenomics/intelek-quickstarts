{#
  lead_status is owned by the business app, not by dbt: dbt never drops or rebuilds it.
  It is an append-only log, one row per status change; the current status of a lead is
  its latest row (stg_lead_status). Leads with no row are 'pending'.
  Runs on every dbt invocation (on-run-start) and only creates the table if it is missing.
#}
{% macro create_lead_status_table() %}
CREATE TABLE IF NOT EXISTS {{ target.schema }}.lead_status (
    lead_id     String,
    status      LowCardinality(String),
    updated_at  DateTime64(3, 'UTC') DEFAULT now64(3),
    updated_by  Nullable(String),                 -- seller or user who made the change
    note        Nullable(String),
    CONSTRAINT valid_status CHECK status IN ('pending', 'contacted', 'interested', 'converted')
)
ENGINE = MergeTree
ORDER BY (lead_id, updated_at)
{% endmacro %}
