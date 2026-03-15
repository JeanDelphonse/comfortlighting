"""
ComfortLighting LED Retrofit ROI Calculator.
All parameters are loaded from system_config so they can be updated
without a code deployment.
"""


def calculate_roi(sq_footage: float, facility_type: str,
                  utility_rate: float = None) -> dict:
    """
    Compute LED retrofit ROI for a ComfortLighting prospect.

    Returns a dict with annual_savings_usd, kwh_savings, payback_years,
    net_5yr_savings, installed_cost, and rebate_estimate.
    """
    # Import here to avoid circular imports (Flask app context required)
    from ...models import SystemConfig

    def _cfg(key, default):
        try:
            return float(SystemConfig.get(key, default))
        except (TypeError, ValueError):
            return float(default)

    watts_per_sqft     = _cfg('agent_watts_per_sqft',     '2.5')
    led_reduction      = _cfg('agent_led_reduction',      '0.60')
    hours_per_year     = _cfg('agent_hours_per_year',     '4000')
    maintenance_factor = _cfg('agent_maintenance_factor', '0.20')
    cost_per_sqft      = _cfg('agent_cost_per_sqft',      '3.50')
    rebate_factor      = _cfg('agent_rebate_factor',      '0.15')

    if utility_rate is None:
        utility_rate = _cfg('agent_utility_rate', '0.13')

    if sq_footage <= 0:
        return {'error': 'sq_footage must be greater than 0'}

    kwh_before    = (sq_footage * watts_per_sqft * hours_per_year) / 1000
    kwh_savings   = kwh_before * led_reduction
    energy_savings = kwh_savings * utility_rate
    maint_savings  = energy_savings * maintenance_factor
    total_annual   = energy_savings + maint_savings

    installed_cost = sq_footage * cost_per_sqft
    rebate         = installed_cost * rebate_factor
    net_cost       = installed_cost - rebate
    payback_years  = round(net_cost / total_annual, 1) if total_annual > 0 else 0
    net_5yr        = round((total_annual * 5) - net_cost, 2)

    return {
        'annual_savings_usd': round(total_annual, 2),
        'kwh_savings':        round(kwh_savings, 0),
        'payback_years':      payback_years,
        'net_5yr_savings':    net_5yr,
        'installed_cost':     round(installed_cost, 2),
        'rebate_estimate':    round(rebate, 2),
        'facility_type':      facility_type,
        'sq_footage':         sq_footage,
    }
