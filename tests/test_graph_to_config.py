"""
Tests for the graph-to-config translation layer.

Verifies that Cytoscape elements are correctly translated into
simulation objects with proper index wiring, parameter passthrough,
and policy mapping.
"""

import pytest

from dashboard.graph_to_config import build_simulation_from_graph, get_full_results


# ── Index translation ────────────────────────────────────────────────────────

class TestIndexTranslation:
    """Verify that visual graph edges produce correct supplier/customer arrays."""

    def test_consumer_suppliers_match_main_py(self, main_py_adjacency):
        """Consumer supplier arrays match main.py lines 77-82 exactly."""
        cs = main_py_adjacency["c_suppliers"]
        assert cs[0] == [0, 1]  # H1 → WS1, WS2
        assert cs[1] == [0, 2]  # H2 → WS1, WS3
        assert cs[2] == [0, 1]  # H3 → WS1, WS2
        assert cs[3] == [0]     # H4 → WS1
        assert cs[4] == [1]     # H5 → WS2
        assert cs[5] == [2]     # H6 → WS3

    def test_transhipper_suppliers_match_main_py(self, main_py_adjacency):
        """Transhipper supplier arrays match main.py lines 83-85."""
        ts = main_py_adjacency["t_suppliers"]
        assert ts[0] == [0, 1]  # WS1 ← MN1, MN2
        assert ts[1] == [0]     # WS2 ← MN1
        assert ts[2] == [1]     # WS3 ← MN2

    def test_transhipper_customers_match_main_py(self, main_py_adjacency):
        """Transhipper customer arrays match main.py lines 83-85."""
        tc = main_py_adjacency["t_customers"]
        assert tc[0] == [0, 1, 2, 3]  # WS1 → H1, H2, H3, H4
        assert tc[1] == [0, 2, 4]     # WS2 → H1, H3, H5
        assert tc[2] == [1, 5]        # WS3 → H2, H6

    def test_producer_customers_match_main_py(self, main_py_adjacency):
        """Producer customer arrays match main.py lines 86-89."""
        pc = main_py_adjacency["p_customers"]
        assert pc[0] == [0, 1]  # MN1 → WS1, WS2
        assert pc[1] == [0, 2]  # MN2 → WS1, WS3


# ── Simulation building ──────────────────────────────────────────────────────

class TestSimulationBuilding:
    """Verify simulations build correctly from graph elements."""

    def test_main_py_agent_counts(self, main_py_simulation):
        assert len(main_py_simulation.consumers) == 6
        assert len(main_py_simulation.transhippers) == 3
        assert len(main_py_simulation.producers) == 2

    def test_starter_agent_counts(self, starter_simulation):
        assert len(starter_simulation.consumers) == 2
        assert len(starter_simulation.transhippers) == 1
        assert len(starter_simulation.producers) == 1

    def test_simulation_runs_to_completion(self, main_py_simulation):
        sim = main_py_simulation.run()
        assert len(sim.consumers[0].h_inventory) == 50
        assert len(sim.producers[0].h_inventory) == 50

    def test_starter_runs_to_completion(self, starter_simulation):
        sim = starter_simulation.run()
        assert len(sim.consumers[0].h_inventory) == 30

    def test_object_wiring_matches_adjacency(self, main_py_simulation):
        """Verify the actual simulation objects have correct supplier/customer arrays."""
        sim = main_py_simulation
        assert sim.consumers[0].suppliers == [0, 1]
        assert sim.transhippers[0].customers == [0, 1, 2, 3]
        assert sim.producers[0].customers == [0, 1]


# ── Parameter passthrough ────────────────────────────────────────────────────

class TestParameterPassthrough:
    """Verify UI parameters reach simulation objects correctly."""

    def test_custom_demand_mean(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        for el in elements:
            if el.get("data", {}).get("id") == "consumer-0":
                el["data"]["d"] = 300
        sim = build_simulation_from_graph(elements, sim_periods=10)
        assert sim.consumers[0].customer_demand_mean == 300

    def test_custom_demand_std(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        for el in elements:
            if el.get("data", {}).get("id") == "consumer-0":
                el["data"]["dstd"] = 25
        sim = build_simulation_from_graph(elements, sim_periods=10)
        assert sim.consumers[0].demand_std == 25

    def test_custom_safety_stock(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        for el in elements:
            if el.get("data", {}).get("id") == "consumer-0":
                el["data"]["ss"] = 2000
        sim = build_simulation_from_graph(elements, sim_periods=10)
        assert sim.consumers[0].safety_stock_level == 2000

    def test_custom_production_max(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        for el in elements:
            if el.get("data", {}).get("id") == "producer-0":
                el["data"]["m"] = 500
        sim = build_simulation_from_graph(elements, sim_periods=10)
        assert sim.producers[0].production_max == 500

    def test_default_parameters_used_when_not_specified(self, starter_simulation):
        """When no custom params are set, defaults from constants.py are used."""
        assert starter_simulation.consumers[0].customer_demand_mean == 150
        assert starter_simulation.producers[0].production_max == 800


# ── Policy selection ─────────────────────────────────────────────────────────

class TestPolicySelection:
    """Verify policy dropdown names map to correct function objects."""

    def test_maximum_capacity_policy(self, starter_elements, copy_elements):
        from pp_maximum_capacity import pp_maximum_capacity
        elements = copy_elements(starter_elements)
        for el in elements:
            if el.get("data", {}).get("id") == "producer-0":
                el["data"]["production_policy"] = "Maximum Capacity"
        sim = build_simulation_from_graph(elements, sim_periods=10)
        assert sim.producers[0].production_policy == pp_maximum_capacity

    def test_base_stock_all_first_policy(self, starter_elements, copy_elements):
        from op_base_stock_all_first import op_base_stock_all_first
        elements = copy_elements(starter_elements)
        for el in elements:
            if el.get("data", {}).get("id") == "consumer-0":
                el["data"]["order_policy"] = "Base Stock (All First)"
        sim = build_simulation_from_graph(elements, sim_periods=10)
        assert sim.consumers[0].order_policy == op_base_stock_all_first

    def test_default_policy_fallback(self, starter_simulation):
        from op_base_stock_fr_all_first import op_base_stock_fr_all_first
        assert starter_simulation.consumers[0].order_policy == op_base_stock_fr_all_first


# ── Edge validation ──────────────────────────────────────────────────────────

class TestEdgeValidation:
    """Verify invalid networks are properly rejected."""

    def test_missing_transhipper_layer_rejected(self):
        """Direct producer→consumer edge (no transhipper) should fail."""
        elements = [
            {"data": {"id": "producer-0", "label": "MN1", "agent_type": "producer", "agent_num": 0,
                      "ss": 10000, "m": 800, "l": 2, "pl": 2,
                      "production_policy": "Base Stock", "allocation_policy": "Proportional"},
             "position": {"x": 100, "y": 80}},
            {"data": {"id": "consumer-0", "label": "H1", "agent_type": "consumer", "agent_num": 0,
                      "d": 150, "dstd": 10, "ss": 1000,
                      "order_policy": "Base Stock FR (All First)"},
             "position": {"x": 700, "y": 80}},
            {"data": {"source": "producer-0", "target": "consumer-0", "id": "e1"}},
        ]
        with pytest.raises(ValueError, match="No Distributors"):
            build_simulation_from_graph(elements, sim_periods=10)

    def test_disconnected_consumer_rejected(self, starter_elements, copy_elements):
        """A consumer with no supplier connections should fail."""
        elements = copy_elements(starter_elements)
        # Add a disconnected consumer
        elements.append({
            "data": {"id": "consumer-99", "label": "H99", "agent_type": "consumer",
                     "agent_num": 99, "d": 100, "dstd": 10, "ss": 500,
                     "order_policy": "Base Stock FR (All First)"},
            "position": {"x": 700, "y": 500},
        })
        with pytest.raises(ValueError, match="no supplier"):
            build_simulation_from_graph(elements, sim_periods=10)

    def test_empty_network_rejected(self):
        """Empty elements list should fail."""
        with pytest.raises(ValueError):
            build_simulation_from_graph([], sim_periods=10)


# ── Results extraction ───────────────────────────────────────────────────────

class TestResultsExtraction:
    """Verify get_full_results returns expected DataFrame structure."""

    def test_result_row_count(self, starter_elements):
        sim = build_simulation_from_graph(starter_elements, sim_periods=30)
        sim.run()
        df = get_full_results(sim)
        assert len(df) == 30

    def test_consumer_columns_present(self, starter_elements):
        sim = build_simulation_from_graph(starter_elements, sim_periods=30)
        sim.run()
        df = get_full_results(sim)
        assert "H1 inventory" in df.columns
        assert "H1 demand" in df.columns
        assert "H1 unmet demand" in df.columns

    def test_producer_columns_present(self, starter_elements):
        sim = build_simulation_from_graph(starter_elements, sim_periods=30)
        sim.run()
        df = get_full_results(sim)
        assert "MN1 inventory" in df.columns
        assert "MN1 production" in df.columns

    def test_transhipper_columns_present(self, starter_elements):
        sim = build_simulation_from_graph(starter_elements, sim_periods=30)
        sim.run()
        df = get_full_results(sim)
        assert "WS1 total allocated" in df.columns
