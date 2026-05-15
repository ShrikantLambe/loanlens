-- fct_delinquency_weekly: rolling 52-week delinquency and default rates.
--
-- fct_portfolio_daily shows a flat line because int_loan_status uses all-time
-- max_dpd — every loan's status is its terminal state, so the mix of statuses
-- is identical on every date in the date spine.
--
-- This model computes a time-series from actual payment event dates:
--   - A loan is delinquent on week W if it has a missed payment with DPD 1–89
--     dated on or before W (i.e., the delinquency event occurred by week W).
--   - A loan is in default on week W if any missed payment with DPD ≥ 90
--     was recorded on or before W.
--   - Outstanding principal = all loans originated before W (simplified;
--     slightly over-states since paid-off loans are not excluded, but the
--     denominator is consistent, making the rate comparable week-to-week).
--
-- Result: a naturally rising J-curve from 0% in early 2022 (few loans seasoned)
-- to ~11–12% by late 2024 (portfolio fully seasoned with real delinquency events).

with weekly_spine as (
    {{ dbt_utils.date_spine(
        datepart  = "week",
        start_date = "cast('2022-01-01' as date)",
        end_date   = "cast('2025-01-08' as date)"
    ) }}
),
loans as (
    select loan_id, principal_amount, origination_date
    from {{ ref('stg_loans') }}
),
missed_payments as (
    select
        p.loan_id,
        p.payment_date::date as payment_date,
        p.days_past_due
    from {{ ref('stg_payments') }} p
    where p.payment_type = 'missed'
      and p.days_past_due > 0
),
-- Outstanding portfolio principal per week
weekly_portfolio as (
    select
        w.date_week                  as week_date,
        sum(l.principal_amount)     as outstanding_principal
    from weekly_spine w
    join loans l on l.origination_date <= w.date_week
    group by 1
),
-- Delinquent loans per week: first occurrence of a 1–89 DPD event on or before W
delinquent_by_week as (
    select
        w.date_week              as week_date,
        mp.loan_id,
        l.principal_amount
    from weekly_spine w
    join missed_payments mp
        on  mp.payment_date <= w.date_week
        and mp.days_past_due between 1 and 89
    join loans l on mp.loan_id = l.loan_id
    where l.origination_date <= w.date_week
    group by 1, 2, 3      -- one row per loan per week (deduplicates multiple events)
),
-- Default loans per week: any 90+ DPD event recorded on or before W
default_by_week as (
    select
        w.date_week              as week_date,
        mp.loan_id,
        l.principal_amount
    from weekly_spine w
    join missed_payments mp
        on  mp.payment_date <= w.date_week
        and mp.days_past_due >= 90
    join loans l on mp.loan_id = l.loan_id
    where l.origination_date <= w.date_week
    group by 1, 2, 3
),
weekly_delinquent_agg as (
    select week_date, sum(principal_amount) as delinquent_principal
    from delinquent_by_week
    group by 1
),
weekly_default_agg as (
    select week_date, sum(principal_amount) as default_principal
    from default_by_week
    group by 1
)
select
    wp.week_date,
    wp.outstanding_principal,
    coalesce(wd.delinquent_principal, 0)                           as delinquent_principal,
    coalesce(wdef.default_principal,  0)                           as default_principal,
    round(
        coalesce(wd.delinquent_principal, 0)
        / nullif(wp.outstanding_principal, 0), 4
    )                                                              as delinquency_rate,
    round(
        coalesce(wdef.default_principal, 0)
        / nullif(wp.outstanding_principal, 0), 4
    )                                                              as default_rate
from weekly_portfolio wp
left join weekly_delinquent_agg wd   on wp.week_date = wd.week_date
left join weekly_default_agg    wdef on wp.week_date = wdef.week_date
order by 1
