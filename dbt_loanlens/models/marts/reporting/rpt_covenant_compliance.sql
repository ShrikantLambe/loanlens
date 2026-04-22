-- rpt_covenant_compliance: per-SPV covenant status for dashboard monitoring.
-- Pulls from fct_spv_allocation (already has breach flags computed).

select
    spv_id,
    facility_name,
    facility_limit,
    total_principal,
    facility_utilization,
    delinquency_rate,
    covenant_max_delinquency_pct,
    default_rate,
    covenant_min_yield,
    covenant_delinquency_breach,
    case
        when covenant_delinquency_breach then 'BREACH'
        else 'OK'
    end                             as delinquency_covenant_status,
    current_timestamp             as checked_at
from {{ ref('fct_spv_allocation') }}
order by spv_id
