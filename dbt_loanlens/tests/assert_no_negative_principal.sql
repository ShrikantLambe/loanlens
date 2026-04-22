-- assert_no_negative_principal: must return 0 rows.
-- Any loan with principal <= 0 indicates a data generation or loading bug.

select loan_id, principal_amount
from {{ ref('stg_loans') }}
where principal_amount <= 0
