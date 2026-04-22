-- stg_payments: typed payment events with is_missed boolean derived.
-- No business logic beyond the boolean flag.

select
    payment_id,
    loan_id,
    payment_date::date         as payment_date,
    payment_amount::float      as payment_amount,
    payment_type,
    days_past_due::int         as days_past_due,
    cumulative_repaid::float   as cumulative_repaid,
    (payment_type = 'missed')  as is_missed,
    current_timestamp        as loaded_at
from {{ source('raw', 'payments') }}
