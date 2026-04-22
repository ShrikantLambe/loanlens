-- int_cohort_assignments: assign each loan to its origination month cohort (vintage).
-- cohort_label format: MV-YYYY-MM (e.g. MV-2022-01)

select
    loan_id,
    origination_date,
    date_trunc('month', origination_date)::date as cohort_month,
    date_part('year',  origination_date)::int   as cohort_year,
    date_part('month', origination_date)::int   as cohort_month_num,
    'MV-' || strftime(origination_date, '%Y-%m') as cohort_label
from {{ ref('stg_loans') }}
