-- fct_cohort_performance: cumulative default curves by origination vintage.
--
-- Previous bug: used last_payment_date as the observation point for each loan.
-- Defaulting loans have an early last_payment_date; current loans have a late one.
-- At any given months_on_book value, only loans whose last payment date happened
-- to fall in that exact month were counted — so a slice containing only default
-- loans produced cumulative_default_rate = 100%. The cohort_size also varied by
-- month rather than being the constant total cohort population.
--
-- Fix: use the actual payment event dates to determine WHEN each loan crossed
-- the 90-DPD threshold, then compute cumulative defaults at each month using
-- the full cohort population as the denominator.

with cohorts as (
    select * from {{ ref('int_cohort_assignments') }}
),
loan_status as (
    select * from {{ ref('int_loan_status') }}
),
-- Find the first date each loan crossed 90 DPD (the default event date)
default_events as (
    select
        loan_id,
        min(payment_date::date) as default_date
    from {{ ref('stg_payments') }}
    where days_past_due >= 90
    group by loan_id
),
-- Per-loan data with months_to_default (null = not defaulted)
loan_base as (
    select
        c.cohort_label,
        c.cohort_month,
        c.origination_date,
        c.loan_id,
        ls.principal_amount,
        ls.pct_repaid,
        case
            when de.default_date is not null
            then datediff('month', c.origination_date, de.default_date)
            else null
        end as months_to_default
    from cohorts c
    join loan_status ls
        on c.loan_id = ls.loan_id
    left join default_events de
        on c.loan_id = de.loan_id
),
-- Cohort-level totals (constant denominator for every months_on_book slice)
cohort_totals as (
    select
        cohort_label,
        cohort_month,
        count(*)               as cohort_size,
        sum(principal_amount)  as cohort_principal,
        avg(pct_repaid)        as avg_pct_repaid
    from loan_base
    group by 1, 2
),
-- Month spine 0–36 (cross-joined per cohort to build the J-curve grid)
month_spine as (
    select unnest(generate_series(0, 36)) as months_on_book
),
-- Cumulative defaults at each months_on_book slice
cumulative as (
    select
        lb.cohort_label,
        lb.cohort_month,
        ms.months_on_book,
        count(
            case when lb.months_to_default is not null
                      and lb.months_to_default <= ms.months_on_book
                 then 1 end
        )                                                          as default_count,
        sum(
            case when lb.months_to_default is not null
                      and lb.months_to_default <= ms.months_on_book
                 then lb.principal_amount else 0 end
        )                                                          as defaulted_principal
    from loan_base lb
    cross join month_spine ms
    -- Only include months that have elapsed since cohort inception
    where ms.months_on_book
          <= datediff('month', lb.cohort_month, date '2025-01-01') + 1
    group by 1, 2, 3
)
select
    c.cohort_label,
    c.cohort_month,
    c.months_on_book,
    ct.cohort_size,
    ct.cohort_principal,
    round(ct.avg_pct_repaid, 4)                                    as avg_pct_repaid,
    c.default_count,
    round(
        c.defaulted_principal / nullif(ct.cohort_principal, 0), 4
    )                                                              as cumulative_default_rate
from cumulative c
join cohort_totals ct
    on  c.cohort_label = ct.cohort_label
    and c.cohort_month = ct.cohort_month
order by 2, 3
