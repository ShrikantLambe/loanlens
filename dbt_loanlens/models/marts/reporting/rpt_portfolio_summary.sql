-- rpt_portfolio_summary: single-row wide summary consumed by the AI narrator.
-- Keep it wide and self-describing — the LLM reads this directly.

select
    current_date()                                          as report_date,
    count(distinct ls.loan_id)                              as total_loans,
    count(distinct case when ls.loan_status = 'current'
          then ls.loan_id end)                              as current_loans,
    count(distinct case when ls.loan_status = 'default'
          then ls.loan_id end)                              as defaulted_loans,
    count(distinct case when ls.loan_status like 'delinquent%'
          then ls.loan_id end)                              as delinquent_loans,
    count(distinct case when ls.loan_status = 'paid_off'
          then ls.loan_id end)                              as paid_off_loans,
    sum(l.principal_amount)                                 as total_originated,
    sum(case when ls.loan_status = 'current'
          then l.principal_amount else 0 end)               as outstanding_principal,
    round(
        sum(case when ls.loan_status like 'delinquent%'
                 then l.principal_amount else 0 end)
        / nullif(sum(l.principal_amount), 0) * 100, 2
    )                                                       as delinquency_rate_pct,
    round(
        sum(case when ls.loan_status = 'default'
                 then l.principal_amount else 0 end)
        / nullif(sum(l.principal_amount), 0) * 100, 2
    )                                                       as default_rate_pct,
    round(avg(l.underwriting_score), 1)                    as avg_underwriting_score,
    min(l.origination_date)                                as portfolio_inception_date,
    max(l.origination_date)                                as latest_origination_date
from {{ ref('int_loan_status') }} ls
join {{ ref('stg_loans') }} l using (loan_id)
