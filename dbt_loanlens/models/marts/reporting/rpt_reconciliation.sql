-- rpt_reconciliation: warehouse totals vs. source system control file.
-- Compares computed metrics to control_totals.csv (simulates servicing system export).
-- delta_pct > 0.1% triggers FAIL status — tested by assert_reconciliation_delta_lt_threshold.sql.

with warehouse_totals as (
    select
        'origination_count'         as metric_name,
        count(loan_id)::float       as warehouse_value
    from {{ ref('stg_loans') }}

    union all

    select
        'origination_principal',
        sum(principal_amount)
    from {{ ref('stg_loans') }}

    union all

    select
        'total_collected',
        sum(total_repaid)
    from {{ ref('int_loan_status') }}
    where total_repaid is not null

    union all

    select
        'default_count',
        count(case when loan_status = 'default' then 1 end)::float
    from {{ ref('int_loan_status') }}
),
control_totals as (
    select * from {{ source('raw', 'control_totals') }}
)
select
    w.metric_name,
    w.warehouse_value,
    c.source_value,
    w.warehouse_value - c.source_value                              as delta,
    round(
        abs(w.warehouse_value - c.source_value)
        / nullif(c.source_value, 0) * 100, 4
    )                                                               as delta_pct,
    case
        when c.source_value = 0 and w.warehouse_value = 0 then 'PASS'
        when abs(w.warehouse_value - c.source_value)
             / nullif(c.source_value, 0) < 0.001 then 'PASS'
        else 'FAIL'
    end                                                             as reconciliation_status,
    current_timestamp                                            as reconciled_at
from warehouse_totals w
join control_totals c on w.metric_name = c.metric_name
