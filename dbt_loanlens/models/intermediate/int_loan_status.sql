-- int_loan_status: derive current loan status from payment history.
-- This is the core credit risk model — all downstream mart models depend on it.
--
-- loan_status logic:
--   paid_off      : total_repaid >= total_owed
--   default       : max_dpd >= 90
--   delinquent_90 : max_dpd 60–89
--   delinquent_60 : max_dpd 30–59
--   delinquent_30 : max_dpd 1–29
--   current       : no delinquency

with latest_payment as (
    select
        loan_id,
        max(payment_date)      as last_payment_date,
        max(cumulative_repaid) as total_repaid,
        max(days_past_due)     as max_dpd,
        sum(case when is_missed then 1 else 0 end) as missed_count
    from {{ ref('stg_payments') }}
    group by loan_id
),
loan_base as (
    select
        l.*,
        l.principal_amount * l.factor_rate as total_owed
    from {{ ref('stg_loans') }} l
)
select
    lb.*,
    lp.last_payment_date,
    lp.total_repaid,
    lp.max_dpd,
    lp.missed_count,
    case
        when lp.total_repaid >= lb.total_owed              then 'paid_off'
        when lp.max_dpd >= 90                              then 'default'
        when lp.max_dpd between 60 and 89                  then 'delinquent_90'
        when lp.max_dpd between 30 and 59                  then 'delinquent_60'
        when lp.max_dpd between 1  and 29                  then 'delinquent_30'
        else                                                    'current'
    end as loan_status,
    round(lp.total_repaid / nullif(lb.total_owed, 0), 4)
        as pct_repaid
from loan_base lb
left join latest_payment lp on lb.loan_id = lp.loan_id
