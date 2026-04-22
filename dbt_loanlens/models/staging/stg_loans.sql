-- stg_loans: typed and renamed loan tape from raw source.
-- No business logic — pure casting and column standardisation.

select
    loan_id,
    merchant_id,
    lower(platform)            as platform,
    origination_date::date     as origination_date,
    principal_amount::float    as principal_amount,
    term_days::int             as term_days,
    factor_rate::float         as factor_rate,
    repayment_type,
    revenue_share_pct::float   as revenue_share_pct,
    spv_id,
    underwriting_score::int    as underwriting_score,
    current_timestamp        as loaded_at
from {{ source('raw', 'loans') }}
