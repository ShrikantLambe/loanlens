-- stg_spv_allocation: typed SPV facility definitions and covenant thresholds.

select
    spv_id,
    facility_name,
    facility_limit::float                  as facility_limit,
    facility_drawn::float                  as facility_drawn,
    covenant_max_delinquency_pct::float    as covenant_max_delinquency_pct,
    covenant_min_yield::float              as covenant_min_yield,
    facility_inception_date::date          as facility_inception_date,
    current_timestamp                    as loaded_at
from {{ source('raw', 'spv_allocation') }}
