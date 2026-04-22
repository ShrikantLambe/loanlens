-- fct_originations: monthly origination volume by platform and SPV.
-- Used for the origination trend charts in the overview and SPV pages.

select
    date_trunc('month', origination_date)::date as origination_month,
    platform,
    spv_id,
    count(loan_id)              as loan_count,
    sum(principal_amount)       as origination_volume,
    avg(principal_amount)       as avg_loan_size,
    avg(factor_rate)            as avg_factor_rate,
    avg(underwriting_score)     as avg_underwriting_score
from {{ ref('stg_loans') }}
group by 1, 2, 3
order by 1, 2
