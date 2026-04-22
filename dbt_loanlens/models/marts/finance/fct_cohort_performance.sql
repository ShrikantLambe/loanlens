-- fct_cohort_performance: cohort-level repayment curves.
-- One row per cohort × months-since-origination.
-- The key credit risk view investors use to assess portfolio quality.

with cohorts as (
    select * from {{ ref('int_cohort_assignments') }}
),
loan_status as (
    select * from {{ ref('int_loan_status') }}
),
monthly_snapshots as (
    select
        c.cohort_label,
        c.cohort_month,
        datediff('month', c.origination_date, ls.last_payment_date) as months_on_book,
        ls.loan_status,
        ls.pct_repaid,
        ls.principal_amount
    from cohorts c
    join loan_status ls on c.loan_id = ls.loan_id
    where ls.last_payment_date is not null
)
select
    cohort_label,
    cohort_month,
    months_on_book,
    count(*)                                              as cohort_size,
    sum(principal_amount)                                 as cohort_principal,
    round(avg(pct_repaid), 4)                             as avg_pct_repaid,
    sum(case when loan_status = 'default' then 1 else 0 end)
                                                          as default_count,
    round(
        sum(case when loan_status = 'default' then principal_amount else 0 end)
        / nullif(sum(principal_amount), 0), 4
    )                                                     as cumulative_default_rate
from monthly_snapshots
where months_on_book is not null
  and months_on_book >= 0
group by 1, 2, 3
order by 2, 3
