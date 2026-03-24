"""
Maps human-readable policy names to their Python function objects.
Used for dashboard dropdowns and graph_to_config translation.
"""

# Import all policy functions from the simulation codebase
from op_base_stock_all_first import op_base_stock_all_first
from op_base_stock_even_split import op_base_stock_even_split
from op_base_stock_fr_all_first import op_base_stock_fr_all_first
from op_constant_all_first import op_constant_all_first
from op_constant_even_split import op_constant_even_split
from pp_base_stock import pp_base_stock
from pp_maximum_capacity import pp_maximum_capacity
from ap_proportional import ap_proportional


# ── Order policies (used by Consumers and Transhippers) ─────────────────────
ORDER_POLICIES = {
    "Base Stock (All First)": op_base_stock_all_first,
    "Base Stock (Even Split)": op_base_stock_even_split,
    "Base Stock FR (All First)": op_base_stock_fr_all_first,
    "Constant (All First)": op_constant_all_first,
    "Constant (Even Split)": op_constant_even_split,
}

# ── Production policies (used by Producers) ─────────────────────────────────
PRODUCTION_POLICIES = {
    "Base Stock": pp_base_stock,
    "Maximum Capacity": pp_maximum_capacity,
}

# ── Allocation policies (used by Transhippers and Producers) ────────────────
ALLOCATION_POLICIES = {
    "Proportional": ap_proportional,
}


def get_order_policy(name):
    """Look up an order policy function by display name."""
    return ORDER_POLICIES.get(name, op_base_stock_fr_all_first)


def get_production_policy(name):
    """Look up a production policy function by display name."""
    return PRODUCTION_POLICIES.get(name, pp_base_stock)


def get_allocation_policy(name):
    """Look up an allocation policy function by display name."""
    return ALLOCATION_POLICIES.get(name, ap_proportional)
