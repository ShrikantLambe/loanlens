-- assert_spv_coverage_complete: must return 0 rows.
-- Every loan must map to a known SPV. Unmapped loans break fct_spv_allocation.

select loan_id
from {{ ref('stg_loans') }}
where spv_id not in ('SPV-A', 'SPV-B', 'SPV-C')
   or spv_id is null
