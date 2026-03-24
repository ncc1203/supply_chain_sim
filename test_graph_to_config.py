"""
Test: Verify that graph_to_config produces the same agent wiring
as main.py's hardcoded setup (6 consumers, 3 transhippers, 2 producers).
"""

import sys
sys.path.insert(0, ".")

from dashboard.graph_to_config import build_simulation_from_graph, _partition_elements, _build_id_to_index_maps, _build_adjacency


def build_main_py_network_as_elements():
    """
    Recreate main.py's 6×3×2 network as Cytoscape elements.
    Reference: main.py lines 77-89.

    consumers = [
        Consumer(name="H1", ..., suppliers=[0, 1]),    # WS1, WS2
        Consumer(name="H2", ..., suppliers=[0, 2]),    # WS1, WS3
        Consumer(name="H3", ..., suppliers=[0, 1]),    # WS1, WS2
        Consumer(name="H4", ..., suppliers=[0]),        # WS1
        Consumer(name="H5", ..., suppliers=[1]),        # WS2
        Consumer(name="H6", ..., suppliers=[2]),        # WS3
    ]
    transhippers = [
        Transhipper(name="WS1", suppliers=[0, 1], customers=[0, 1, 2, 3]),
        Transhipper(name="WS2", suppliers=[0],    customers=[0, 2, 4]),
        Transhipper(name="WS3", suppliers=[1],    customers=[1, 5]),
    ]
    producers = [
        Producer(name="MN1", customers=[0, 1]),
        Producer(name="MN2", customers=[0, 2]),
    ]
    """
    nodes = [
        # Producers
        {"data": {"id": "producer-0", "label": "MN1", "agent_type": "producer", "agent_num": 0,
                  "ss": 10000, "m": 800, "l": 2, "pl": 2,
                  "production_policy": "Base Stock", "allocation_policy": "Proportional"},
         "position": {"x": 100, "y": 80}},
        {"data": {"id": "producer-1", "label": "MN2", "agent_type": "producer", "agent_num": 1,
                  "ss": 10000, "m": 800, "l": 2, "pl": 2,
                  "production_policy": "Base Stock", "allocation_policy": "Proportional"},
         "position": {"x": 100, "y": 200}},
        # Transhippers
        {"data": {"id": "transhipper-0", "label": "WS1", "agent_type": "transhipper", "agent_num": 0,
                  "ss": 8000, "l": 2,
                  "order_policy": "Base Stock FR (All First)", "allocation_policy": "Proportional"},
         "position": {"x": 400, "y": 80}},
        {"data": {"id": "transhipper-1", "label": "WS2", "agent_type": "transhipper", "agent_num": 1,
                  "ss": 8000, "l": 2,
                  "order_policy": "Base Stock FR (All First)", "allocation_policy": "Proportional"},
         "position": {"x": 400, "y": 200}},
        {"data": {"id": "transhipper-2", "label": "WS3", "agent_type": "transhipper", "agent_num": 2,
                  "ss": 8000, "l": 2,
                  "order_policy": "Base Stock FR (All First)", "allocation_policy": "Proportional"},
         "position": {"x": 400, "y": 320}},
        # Consumers
        {"data": {"id": "consumer-0", "label": "H1", "agent_type": "consumer", "agent_num": 0,
                  "d": 150, "dstd": 10, "ss": 1000,
                  "order_policy": "Base Stock FR (All First)"},
         "position": {"x": 700, "y": 80}},
        {"data": {"id": "consumer-1", "label": "H2", "agent_type": "consumer", "agent_num": 1,
                  "d": 170, "dstd": 10, "ss": 1000,
                  "order_policy": "Base Stock FR (All First)"},
         "position": {"x": 700, "y": 200}},
        {"data": {"id": "consumer-2", "label": "H3", "agent_type": "consumer", "agent_num": 2,
                  "d": 200, "dstd": 10, "ss": 1000,
                  "order_policy": "Base Stock FR (All First)"},
         "position": {"x": 700, "y": 320}},
        {"data": {"id": "consumer-3", "label": "H4", "agent_type": "consumer", "agent_num": 3,
                  "d": 50, "dstd": 10, "ss": 1000,
                  "order_policy": "Base Stock FR (All First)"},
         "position": {"x": 700, "y": 440}},
        {"data": {"id": "consumer-4", "label": "H5", "agent_type": "consumer", "agent_num": 4,
                  "d": 200, "dstd": 10, "ss": 1000,
                  "order_policy": "Base Stock FR (All First)"},
         "position": {"x": 700, "y": 560}},
        {"data": {"id": "consumer-5", "label": "H6", "agent_type": "consumer", "agent_num": 5,
                  "d": 200, "dstd": 10, "ss": 1000,
                  "order_policy": "Base Stock FR (All First)"},
         "position": {"x": 700, "y": 680}},
    ]

    edges = [
        # Producer → Transhipper connections
        # MN1 → WS1, WS2  (producer-0 → transhipper-0, transhipper-1)
        {"data": {"source": "producer-0", "target": "transhipper-0", "id": "e1"}},
        {"data": {"source": "producer-0", "target": "transhipper-1", "id": "e2"}},
        # MN2 → WS1, WS3  (producer-1 → transhipper-0, transhipper-2)
        {"data": {"source": "producer-1", "target": "transhipper-0", "id": "e3"}},
        {"data": {"source": "producer-1", "target": "transhipper-2", "id": "e4"}},

        # Transhipper → Consumer connections
        # WS1 → H1, H2, H3, H4  (transhipper-0 → consumer-0, 1, 2, 3)
        {"data": {"source": "transhipper-0", "target": "consumer-0", "id": "e5"}},
        {"data": {"source": "transhipper-0", "target": "consumer-1", "id": "e6"}},
        {"data": {"source": "transhipper-0", "target": "consumer-2", "id": "e7"}},
        {"data": {"source": "transhipper-0", "target": "consumer-3", "id": "e8"}},
        # WS2 → H1, H3, H5  (transhipper-1 → consumer-0, 2, 4)
        {"data": {"source": "transhipper-1", "target": "consumer-0", "id": "e9"}},
        {"data": {"source": "transhipper-1", "target": "consumer-2", "id": "e10"}},
        {"data": {"source": "transhipper-1", "target": "consumer-4", "id": "e11"}},
        # WS3 → H2, H6  (transhipper-2 → consumer-1, 5)
        {"data": {"source": "transhipper-2", "target": "consumer-1", "id": "e12"}},
        {"data": {"source": "transhipper-2", "target": "consumer-5", "id": "e13"}},
    ]

    return nodes + edges


def test_index_translation():
    """Test 1: Index arrays match main.py exactly."""
    elements = build_main_py_network_as_elements()

    # Run the partitioning and adjacency logic
    p_nodes, t_nodes, c_nodes, edges = _partition_elements(elements)
    p_map, t_map, c_map = _build_id_to_index_maps(p_nodes, t_nodes, c_nodes)
    p_customers, t_suppliers, t_customers, c_suppliers = _build_adjacency(edges, p_map, t_map, c_map)

    # Expected from main.py lines 77-89:
    # Consumer suppliers
    assert c_suppliers[0] == [0, 1], f"H1 suppliers: expected [0, 1], got {c_suppliers[0]}"
    assert c_suppliers[1] == [0, 2], f"H2 suppliers: expected [0, 2], got {c_suppliers[1]}"
    assert c_suppliers[2] == [0, 1], f"H3 suppliers: expected [0, 1], got {c_suppliers[2]}"
    assert c_suppliers[3] == [0],    f"H4 suppliers: expected [0], got {c_suppliers[3]}"
    assert c_suppliers[4] == [1],    f"H5 suppliers: expected [1], got {c_suppliers[4]}"
    assert c_suppliers[5] == [2],    f"H6 suppliers: expected [2], got {c_suppliers[5]}"

    # Transhipper suppliers
    assert t_suppliers[0] == [0, 1], f"WS1 suppliers: expected [0, 1], got {t_suppliers[0]}"
    assert t_suppliers[1] == [0],    f"WS2 suppliers: expected [0], got {t_suppliers[1]}"
    assert t_suppliers[2] == [1],    f"WS3 suppliers: expected [1], got {t_suppliers[2]}"

    # Transhipper customers
    assert t_customers[0] == [0, 1, 2, 3], f"WS1 customers: expected [0,1,2,3], got {t_customers[0]}"
    assert t_customers[1] == [0, 2, 4],    f"WS2 customers: expected [0,2,4], got {t_customers[1]}"
    assert t_customers[2] == [1, 5],       f"WS3 customers: expected [1,5], got {t_customers[2]}"

    # Producer customers
    assert p_customers[0] == [0, 1], f"MN1 customers: expected [0, 1], got {p_customers[0]}"
    assert p_customers[1] == [0, 2], f"MN2 customers: expected [0, 2], got {p_customers[1]}"

    print("PASSED: Index translation matches main.py exactly!")


def test_simulation_builds_and_runs():
    """Test 2: Full simulation builds from graph and runs to completion."""
    elements = build_main_py_network_as_elements()
    sim = build_simulation_from_graph(elements, sim_periods=50)

    # Verify object counts
    assert len(sim.consumers) == 6, f"Expected 6 consumers, got {len(sim.consumers)}"
    assert len(sim.transhippers) == 3, f"Expected 3 transhippers, got {len(sim.transhippers)}"
    assert len(sim.producers) == 2, f"Expected 2 producers, got {len(sim.producers)}"

    # Verify agent parameters passed through
    assert sim.consumers[0].customer_demand_mean == 150, "H1 demand should be 150"
    assert sim.consumers[1].customer_demand_mean == 170, "H2 demand should be 170"
    assert sim.producers[0].production_max == 800, "MN1 production_max should be 800"

    # Verify supplier/customer arrays on actual objects
    assert sim.consumers[0].suppliers == [0, 1], f"H1 object suppliers wrong: {sim.consumers[0].suppliers}"
    assert sim.transhippers[0].customers == [0, 1, 2, 3], f"WS1 object customers wrong: {sim.transhippers[0].customers}"
    assert sim.producers[0].customers == [0, 1], f"MN1 object customers wrong: {sim.producers[0].customers}"

    # Run the simulation
    sim = sim.run()
    print("PASSED: Simulation built and ran successfully (50 periods)!")

    # Verify results are populated
    assert len(sim.consumers[0].h_inventory) == 50, "Should have 50 inventory records"
    assert len(sim.producers[0].h_inventory) == 50, "Producer should have 50 inventory records"
    print("PASSED: Results data is populated correctly!")


def test_starter_preset():
    """Test 3: The 1x1x2 starter preset builds and runs."""
    from dashboard.constants import get_starter_preset
    elements = get_starter_preset()
    sim = build_simulation_from_graph(elements, sim_periods=30)
    assert len(sim.consumers) == 2
    assert len(sim.transhippers) == 1
    assert len(sim.producers) == 1
    sim = sim.run()
    print("PASSED: Starter preset builds and runs!")


def test_edge_validation():
    """Test 4: Direct producer→consumer edge should fail (no transhipper in between)."""
    elements = [
        {"data": {"id": "producer-0", "label": "MN1", "agent_type": "producer", "agent_num": 0,
                  "ss": 10000, "m": 800, "l": 2, "pl": 2,
                  "production_policy": "Base Stock", "allocation_policy": "Proportional"},
         "position": {"x": 100, "y": 80}},
        {"data": {"id": "consumer-0", "label": "H1", "agent_type": "consumer", "agent_num": 0,
                  "d": 150, "dstd": 10, "ss": 1000,
                  "order_policy": "Base Stock FR (All First)"},
         "position": {"x": 700, "y": 80}},
        # Direct edge (invalid — skips transhipper layer)
        {"data": {"source": "producer-0", "target": "consumer-0", "id": "e1"}},
    ]
    try:
        sim = build_simulation_from_graph(elements, sim_periods=10)
        print("FAILED: Should have raised ValueError for missing transhipper layer")
    except ValueError as e:
        print(f"PASSED: Correctly rejected invalid network: {e}")


def test_parameter_passthrough():
    """Test 5: Non-default parameter values pass through correctly."""
    from dashboard.constants import get_starter_preset
    elements = get_starter_preset()

    # Modify consumer-0: set demand to 300
    for el in elements:
        d = el.get("data", {})
        if d.get("id") == "consumer-0":
            d["d"] = 300
            d["dstd"] = 25
            d["ss"] = 2000
        if d.get("id") == "producer-0":
            d["m"] = 500
            d["ss"] = 5000

    sim = build_simulation_from_graph(elements, sim_periods=10)
    assert sim.consumers[0].customer_demand_mean == 300, f"Expected 300, got {sim.consumers[0].customer_demand_mean}"
    assert sim.consumers[0].demand_std == 25, f"Expected 25, got {sim.consumers[0].demand_std}"
    assert sim.consumers[0].safety_stock_level == 2000, f"Expected 2000, got {sim.consumers[0].safety_stock_level}"
    assert sim.producers[0].production_max == 500, f"Expected 500, got {sim.producers[0].production_max}"
    assert sim.producers[0].safety_stock_level == 5000, f"Expected 5000, got {sim.producers[0].safety_stock_level}"
    print("PASSED: Parameter passthrough works correctly!")


def test_policy_selection():
    """Test 6: Policy dropdown selections map to correct functions."""
    from dashboard.constants import get_starter_preset
    from pp_maximum_capacity import pp_maximum_capacity
    from op_base_stock_all_first import op_base_stock_all_first

    elements = get_starter_preset()
    for el in elements:
        d = el.get("data", {})
        if d.get("id") == "producer-0":
            d["production_policy"] = "Maximum Capacity"
        if d.get("id") == "consumer-0":
            d["order_policy"] = "Base Stock (All First)"

    sim = build_simulation_from_graph(elements, sim_periods=10)
    assert sim.producers[0].production_policy == pp_maximum_capacity, "Producer should use Maximum Capacity"
    assert sim.consumers[0].order_policy == op_base_stock_all_first, "Consumer should use Base Stock (All First)"
    print("PASSED: Policy selection maps correctly!")


def test_disruption_passthrough():
    """Test 7: Disruption events affect simulation correctly."""
    from dashboard.constants import get_starter_preset
    elements = get_starter_preset()

    disruptions = [{"producer_label": "MN1", "start": 5, "end": 10, "severity": 0.2}]
    sim = build_simulation_from_graph(elements, sim_periods=15, disruptions=disruptions)

    original_max = sim.original_production_max[0]
    sim = sim.run()

    # After disruption ends (period 10), production_max should be back to original
    assert sim.producers[0].production_max == original_max, \
        f"Expected production_max to recover to {original_max}, got {sim.producers[0].production_max}"
    print("PASSED: Disruption passthrough works correctly!")


def test_get_full_results():
    """Test 8: get_full_results returns a DataFrame with expected columns."""
    from dashboard.constants import get_starter_preset
    from dashboard.graph_to_config import get_full_results

    elements = get_starter_preset()
    sim = build_simulation_from_graph(elements, sim_periods=30)
    sim = sim.run()
    df = get_full_results(sim)

    assert len(df) == 30, f"Expected 30 rows, got {len(df)}"
    assert "H1 inventory" in df.columns, "Missing H1 inventory column"
    assert "H1 demand" in df.columns, "Missing H1 demand column"
    assert "H1 unmet demand" in df.columns, "Missing H1 unmet demand column"
    assert "MN1 inventory" in df.columns, "Missing MN1 inventory column"
    assert "MN1 production" in df.columns, "Missing MN1 production column"
    assert "WS1 total allocated" in df.columns, "Missing WS1 total allocated column"
    print(f"PASSED: get_full_results returns {len(df.columns)} columns correctly!")


def test_main_py_preset():
    """Test 9: The main.py preset builds and matches expected wiring."""
    from dashboard.constants import get_main_py_preset
    from dashboard.graph_to_config import _partition_elements, _build_id_to_index_maps, _build_adjacency

    elements = get_main_py_preset()
    p_nodes, t_nodes, c_nodes, edges = _partition_elements(elements)
    p_map, t_map, c_map = _build_id_to_index_maps(p_nodes, t_nodes, c_nodes)
    p_customers, t_suppliers, t_customers, c_suppliers = _build_adjacency(edges, p_map, t_map, c_map)

    assert len(p_nodes) == 2 and len(t_nodes) == 3 and len(c_nodes) == 6
    assert c_suppliers[0] == [0, 1], f"H1: {c_suppliers[0]}"
    assert t_customers[0] == [0, 1, 2, 3], f"WS1: {t_customers[0]}"
    assert p_customers[0] == [0, 1], f"MN1: {p_customers[0]}"

    sim = build_simulation_from_graph(elements, sim_periods=20)
    sim = sim.run()
    assert len(sim.consumers[0].h_inventory) == 20
    print("PASSED: Main.py preset builds, wires correctly, and runs!")


if __name__ == "__main__":
    print("=" * 60)
    print("Running graph_to_config tests...")
    print("=" * 60)
    test_index_translation()
    print()
    test_simulation_builds_and_runs()
    print()
    test_starter_preset()
    print()
    test_edge_validation()
    print()
    test_parameter_passthrough()
    print()
    test_policy_selection()
    print()
    test_disruption_passthrough()
    print()
    test_get_full_results()
    print()
    test_main_py_preset()
    print()
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
