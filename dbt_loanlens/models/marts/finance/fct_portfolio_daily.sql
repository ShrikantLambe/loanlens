-- fct_portfolio_daily: daily snapshot of portfolio health.
-- One row per calendar date. Core model for the portfolio overview dashboard.
-- Loans are "active" on a date if they originated on or before that date
-- and have not yet been fully paid off before that date.

{{ config(materialized='table') }}

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2022-01-01' as date)",
        end_date="cast(current_date() as date)"
    ) }}
),
loan_status as (
    select * from {{ ref('int_loan_status') }}
),
loans as (
    select * from {{ ref('stg_loans') }}
),
loans_active_on_date as (
    select
        d.date_day,
        l.loan_id,
        l.principal_amount,
        l.spv_id,
        l.platform,
        ls.loan_status,
        ls.total_repaid,
        ls.last_payment_date
    from date_spine d
    join loans l
        on l.origination_date <= d.date_day
    join loan_status ls
        on ls.loan_id = l.loan_id
    where
        -- Exclude loans that paid off before this date
        ls.loan_status != 'paid_off'
        or ls.last_payment_date >= d.date_day
)
select
    date_day,
    count(distinct loan_id)                                               as active_loan_count,
    sum(principal_amount)                                                 as outstanding_principal,
    sum(case when loan_status = 'default'
             then principal_amount else 0 end)                           as defaulted_principal,
    sum(case when loan_status like 'delinquent%'
             then 1 else 0 end)                                          as delinquent_count,
    round(
        sum(case when loan_status like 'delinquent%'
                 then principal_amount else 0 end)
        / nullif(sum(principal_amount), 0), 4
    )                                                                     as delinquency_rate,
    round(
        sum(case when loan_status = 'default'
                 then principal_amount else 0 end)
        / nullif(sum(principal_amount), 0), 4
    )                                                                     as default_rate
from loans_active_on_date
group by 1
order by 1
