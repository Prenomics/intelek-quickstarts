-- Business rule: no seller gets more leads than their capacity,
-- and inactive sellers get no leads at all. Any returned row is a failure.
SELECT *
FROM {{ ref('mart_seller_workload') }}
WHERE free_slots < 0
   OR (NOT is_active AND n_assigned_leads > 0)
