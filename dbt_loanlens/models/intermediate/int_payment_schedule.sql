-- int_payment_schedule: payment-level aggregates per loan.
-- Provides scheduled vs. missed breakdown consumed by reporting models.

select
    p.loan_id,
    count(*)                                                      as total_payment_events,
    sum(case when not p.is_missed then p.payment_amount else 0 end) as total_paid,
    sum(case when p.is_missed then 1 else 0 end)                  as missed_payment_count,
    sum(case when not p.is_missed then 1 else 0 end)              as on_time_payment_count,
    max(p.payment_date)                                           as last_payment_date,
    min(p.payment_date)                                           as first_payment_date,
    max(p.days_past_due)                                          as max_dpd,
    -- On-time rate: share of payment events that were not missed
    round(
        sum(case when not p.is_missed then 1 else 0 end)::float
        / nullif(count(*), 0), 4
    )                                                             as on_time_rate
from {{ ref('stg_payments') }} p
group by p.loan_id
