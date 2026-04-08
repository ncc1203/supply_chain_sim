"""
Shared pytest fixtures for the supply chain simulation test suite.
"""

import sys
import copy
import pytest

# Ensure the project root is on the path
sys.path.insert(0, ".")

from dashboard.constants import get_starter_preset, get_main_py_preset
from dashboard.graph_to_config import (
    build_simulation_from_graph,
    get_full_results,
    _partition_elements,
    _build_id_to_index_maps,
    _build_adjacency,
)


# ── Element fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def starter_elements():
    """Starter 1×1×2 network (1 Producer, 1 Transhipper, 2 Consumers)."""
    return get_starter_preset()


@pytest.fixture
def main_py_elements():
    """Main.py 2×3×6 reference network."""
    return get_main_py_preset()


@pytest.fixture
def starter_simulation(starter_elements):
    """Build (but don't run) a simulation from the starter preset."""
    return build_simulation_from_graph(starter_elements, sim_periods=30)


@pytest.fixture
def main_py_simulation(main_py_elements):
    """Build (but don't run) a simulation from the main.py preset."""
    return build_simulation_from_graph(main_py_elements, sim_periods=50)


# ── Helper to deep-copy elements before mutation ─────────────────────────────

@pytest.fixture
def copy_elements():
    """Return a function that deep-copies a Cytoscape elements list."""
    def _copy(elements):
        return copy.deepcopy(elements)
    return _copy


# ── Adjacency helper fixture ────────────────────────────────────────────────

@pytest.fixture
def main_py_adjacency(main_py_elements):
    """Return the full adjacency data for the main.py network."""
    p_nodes, t_nodes, c_nodes, edges = _partition_elements(main_py_elements)
    p_map, t_map, c_map = _build_id_to_index_maps(p_nodes, t_nodes, c_nodes)
    p_customers, t_suppliers, t_customers, c_suppliers = _build_adjacency(
        edges, p_map, t_map, c_map
    )
    return {
        "p_customers": p_customers,
        "t_suppliers": t_suppliers,
        "t_customers": t_customers,
        "c_suppliers": c_suppliers,
        "p_nodes": p_nodes,
        "t_nodes": t_nodes,
        "c_nodes": c_nodes,
    }
