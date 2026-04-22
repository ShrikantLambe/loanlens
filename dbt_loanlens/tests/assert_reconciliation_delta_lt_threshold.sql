-- assert_reconciliation_delta_lt_threshold: must return 0 rows.
-- Any FAIL row means the warehouse total differs from the source system
-- control file by more than 0.1% — a data integrity failure.

select metric_name, delta_pct
from {{ ref('rpt_reconciliation') }}
where reconciliation_status = 'FAIL'
