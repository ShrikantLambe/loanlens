-- fct_spv_allocation: SPV-level portfolio summary with covenant breach flags.
-- One row per SPV. Key input for the SPV reporting page and covenant monitoring.

with spv_portfolio as (
    select
        l.spv_id,
        count(l.loan_id)                               as loan_count,
        sum(l.principal_amount)                        as total_principal,
        sum(l.principal_amount * l.factor_rate)        as total_owed,
        sum(ls.total_repaid)                           as total_collected,
        round(avg(ls.pct_repaid), 4)                   as avg_pct_repaid,
        avg(l.underwriting_score)                      as avg_underwriting_score,
        sum(
            case when ls.loan_status like 'delinquent%'
                 then l.principal_amount else 0 end
        )                                              as delinquent_principal,
        round(
            sum(case when ls.loan_status like 'delinquent%'
                     then l.principal_amount else 0 end)
            / nullif(sum(l.principal_amount), 0), 4
        )                                              as delinquency_rate,
        round(
            sum(case when ls.loan_status = 'default'
                     then l.principal_amount else 0 end)
            / nullif(sum(l.principal_amount), 0), 4
        )                                              as default_rate
    from {{ ref('stg_loans') }} l
    join {{ ref('int_loan_status') }} ls on l.loan_id = ls.loan_id
    group by 1
)
select
    p.*,
    s.facility_name,
    s.facility_limit,
    s.covenant_max_delinquency_pct,
    s.covenant_min_yield,
    s.facility_inception_date,
    -- Covenant breach flag
    (p.delinquency_rate > s.covenant_max_delinquency_pct) as covenant_delinquency_breach,
    -- Facility utilisation
    round(p.total_principal / nullif(s.facility_limit, 0), 4) as facility_utilization
from spv_portfolio p
join {{ ref('stg_spv_allocation') }} s on p.spv_id = s.spv_id
