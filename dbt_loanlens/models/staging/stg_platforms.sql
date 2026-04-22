-- stg_platforms: typed platform metadata.

select
    lower(platform)                  as platform,
    platform_display_name,
    lower(category)                  as category,
    avg_merchant_gmv::float          as avg_merchant_gmv,
    partner_since::date              as partner_since,
    current_timestamp              as loaded_at
from {{ source('raw', 'platform_metadata') }}
