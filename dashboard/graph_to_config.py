"""
CRITICAL MODULE: Translates a Cytoscape graph (elements list) into
Simulation objects with correctly computed index arrays.

The visual graph is the single source of truth for agent connections.
Bidirectional consistency (supplier ↔ customer) is guaranteed by
deriving both sides from the same edge records.
"""

import pandas as pd

from Consumer import Consumer
from Transhipper import Transhipper
from Producer import Producer
from Simulation import Simulation

from dashboard.policy_registry import (
    get_order_policy,
    get_production_policy,
    get_allocation_policy,
)
from dashboard.constants import (
    CONSUMER_DEFAULTS,
    TRANSHIPPER_DEFAULTS,
    PRODUCER_DEFAULTS,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _partition_elements(elements):
    """
    Separate Cytoscape elements into nodes (by type) and edges.
    Nodes are sorted by their creation-order number (agent_num) to ensure
    stable, deterministic index assignment.
    """
    producer_nodes = []
    transhipper_nodes = []
    consumer_nodes = []
    edges = []

    for el in elements:
        data = el.get("data", {})
        if "source" in data:
            edges.append(data)
        else:
            agent_type = data.get("agent_type")
            if agent_type == "producer":
                producer_nodes.append(data)
            elif agent_type == "transhipper":
                transhipper_nodes.append(data)
            elif agent_type == "consumer":
                consumer_nodes.append(data)

    # Sort by agent_num for stable index assignment
    producer_nodes.sort(key=lambda d: d.get("agent_num", 0))
    transhipper_nodes.sort(key=lambda d: d.get("agent_num", 0))
    consumer_nodes.sort(key=lambda d: d.get("agent_num", 0))

    return producer_nodes, transhipper_nodes, consumer_nodes, edges


def _build_id_to_index_maps(producer_nodes, transhipper_nodes, consumer_nodes):
    """
    Build mappings from Cytoscape node ID → integer index in the ordered list.
    Example: {"producer-0": 0, "producer-3": 1} if those are the only two producers.
    """
    p_map = {n["id"]: i for i, n in enumerate(producer_nodes)}
    t_map = {n["id"]: i for i, n in enumerate(transhipper_nodes)}
    c_map = {n["id"]: i for i, n in enumerate(consumer_nodes)}
    return p_map, t_map, c_map


def _get_agent_type_from_id(node_id):
    """Extract agent type from a node ID like 'producer-0'."""
    return node_id.rsplit("-", 1)[0]


def _build_adjacency(edges, p_map, t_map, c_map):
    """
    From the edge list, build adjacency data:
      - producer_customers[p_idx] = list of transhipper indices
      - transhipper_suppliers[t_idx] = list of producer indices
      - transhipper_customers[t_idx] = list of consumer indices
      - consumer_suppliers[c_idx] = list of transhipper indices

    Both sides are populated from each edge, guaranteeing bidirectional consistency.
    """
    n_producers = len(p_map)
    n_transhippers = len(t_map)
    n_consumers = len(c_map)

    producer_customers = [[] for _ in range(n_producers)]
    transhipper_suppliers = [[] for _ in range(n_transhippers)]
    transhipper_customers = [[] for _ in range(n_transhippers)]
    consumer_suppliers = [[] for _ in range(n_consumers)]

    for edge in edges:
        source_id = edge["source"]
        target_id = edge["target"]
        source_type = _get_agent_type_from_id(source_id)
        target_type = _get_agent_type_from_id(target_id)

        if source_type == "producer" and target_type == "transhipper":
            p_idx = p_map[source_id]
            t_idx = t_map[target_id]
            if t_idx not in producer_customers[p_idx]:
                producer_customers[p_idx].append(t_idx)
            if p_idx not in transhipper_suppliers[t_idx]:
                transhipper_suppliers[t_idx].append(p_idx)

        elif source_type == "transhipper" and target_type == "consumer":
            t_idx = t_map[source_id]
            c_idx = c_map[target_id]
            if c_idx not in transhipper_customers[t_idx]:
                transhipper_customers[t_idx].append(c_idx)
            if t_idx not in consumer_suppliers[c_idx]:
                consumer_suppliers[c_idx].append(t_idx)

    return producer_customers, transhipper_suppliers, transhipper_customers, consumer_suppliers


# ── Main translation function ────────────────────────────────────────────────

def build_simulation_from_graph(elements, sim_periods, disruptions=None):
    """
    Translate Cytoscape elements into a ready-to-run Simulation object.

    Parameters
    ----------
    elements : list[dict]
        The Cytoscape elements (nodes + edges).
    sim_periods : int
        Number of simulation periods.
    disruptions : list[dict], optional
        List of disruption events, each with keys:
        {"producer_label": str, "start": int, "end": int, "severity": float}

    Returns
    -------
    Simulation
        A fully constructed Simulation object.
    """
    # 1. Partition and sort
    producer_nodes, transhipper_nodes, consumer_nodes, edges = _partition_elements(elements)

    if not consumer_nodes:
        raise ValueError("No Health Centers (consumers) in the network.")
    if not transhipper_nodes:
        raise ValueError("No Distributors (transhippers) in the network.")
    if not producer_nodes:
        raise ValueError("No Manufacturers (producers) in the network.")

    # 2. Build ID → index maps
    p_map, t_map, c_map = _build_id_to_index_maps(producer_nodes, transhipper_nodes, consumer_nodes)

    # 3. Build adjacency from edges
    producer_customers, transhipper_suppliers, transhipper_customers, consumer_suppliers = \
        _build_adjacency(edges, p_map, t_map, c_map)

    # 4. Validate: every agent must have at least one connection
    for i, node in enumerate(consumer_nodes):
        if not consumer_suppliers[i]:
            raise ValueError(f"Health Center '{node.get('label', i)}' has no supplier connections.")
    for i, node in enumerate(transhipper_nodes):
        if not transhipper_suppliers[i]:
            raise ValueError(f"Distributor '{node.get('label', i)}' has no supplier (manufacturer) connections.")
        if not transhipper_customers[i]:
            raise ValueError(f"Distributor '{node.get('label', i)}' has no customer (health center) connections.")
    for i, node in enumerate(producer_nodes):
        if not producer_customers[i]:
            raise ValueError(f"Manufacturer '{node.get('label', i)}' has no customer (distributor) connections.")

    # 5. Build Consumer objects first (Transhipper.__init__ reads consumers)
    consumers = []
    for i, node in enumerate(consumer_nodes):
        consumers.append(Consumer(
            name=node.get("label", f"H{i+1}"),
            d=node.get("d", CONSUMER_DEFAULTS["d"]),
            dstd=node.get("dstd", CONSUMER_DEFAULTS["dstd"]),
            ss=node.get("ss", CONSUMER_DEFAULTS["ss"]),
            suppliers=consumer_suppliers[i],
            order_policy_function=get_order_policy(node.get("order_policy", CONSUMER_DEFAULTS["order_policy"])),
        ))

    # 6. Build Transhipper objects (Producer.__init__ reads transhippers)
    transhippers = []
    for i, node in enumerate(transhipper_nodes):
        transhippers.append(Transhipper(
            consumers=consumers,
            name=node.get("label", f"WS{i+1}"),
            suppliers=transhipper_suppliers[i],
            customers=transhipper_customers[i],
            ss=node.get("ss", TRANSHIPPER_DEFAULTS["ss"]),
            l=node.get("l", TRANSHIPPER_DEFAULTS["l"]),
            order_policy_function=get_order_policy(node.get("order_policy", TRANSHIPPER_DEFAULTS["order_policy"])),
            allocation_policy_function=get_allocation_policy(node.get("allocation_policy", TRANSHIPPER_DEFAULTS["allocation_policy"])),
        ))

    # 7. Build Producer objects
    producers = []
    for i, node in enumerate(producer_nodes):
        producers.append(Producer(
            transhippers=transhippers,
            name=node.get("label", f"MN{i+1}"),
            ss=node.get("ss", PRODUCER_DEFAULTS["ss"]),
            m=node.get("m", PRODUCER_DEFAULTS["m"]),
            l=node.get("l", PRODUCER_DEFAULTS["l"]),
            pl=node.get("pl", PRODUCER_DEFAULTS["pl"]),
            customers=producer_customers[i],
            production_policy_function=get_production_policy(node.get("production_policy", PRODUCER_DEFAULTS["production_policy"])),
            allocation_policy_function=get_allocation_policy(node.get("allocation_policy", PRODUCER_DEFAULTS["allocation_policy"])),
        ))

    # 8. Build disruption function
    def disruption_function(self, t):
        pass  # No disruptions by default; Phase 4 will add UI-driven disruptions

    if disruptions:
        # Build a label-to-index map for producers
        producer_label_to_idx = {node.get("label"): i for i, node in enumerate(producer_nodes)}

        def make_disruption_fn(disruption_list, label_map):
            def disruption_function(sim_self, t):
                # For each producer, find all currently active disruptions
                # and apply the most restrictive (minimum severity).
                # This correctly handles overlapping disruptions on the same producer.
                for p_label, p_idx in label_map.items():
                    active_severities = [
                        d["severity"] for d in disruption_list
                        if d.get("producer_label") == p_label
                        and d["start"] <= t < d["end"]
                    ]
                    if active_severities:
                        effective_severity = min(active_severities)
                        sim_self.producers[p_idx].production_max = (
                            sim_self.original_production_max[p_idx] * effective_severity
                        )
                    else:
                        sim_self.producers[p_idx].production_max = (
                            sim_self.original_production_max[p_idx]
                        )
            return disruption_function

        disruption_function = make_disruption_fn(disruptions, producer_label_to_idx)

    def change_decision_policies(self, t):
        pass

    # 9. Build and return Simulation
    simulation = Simulation(
        sim_periods, consumers, transhippers, producers,
        disruption_function, change_decision_policies,
    )
    return simulation


# ── Results extraction (covers all agent types) ──────────────────────────────

def get_full_results(simulation):
    """
    Extract results from all agents into a single DataFrame.
    Does NOT write to disk (unlike main.py's get_results).

    NOTE: Only uses history arrays that are actually populated by
    the core simulation classes. Transhipper.h_inventory is NOT
    populated (the class never appends to it), so we skip it.
    """
    df = pd.DataFrame()
    n = simulation.sim_periods

    def _safe_add(col_name, data):
        if len(data) == n:
            df[col_name] = data

    # ── Consumer data ────────────────────────────────────────────────────
    for c in simulation.consumers:
        _safe_add(f"{c.name} inventory", c.h_inventory)
        _safe_add(f"{c.name} demand", c.h_observed_demand)
        _safe_add(f"{c.name} unmet demand", c.h_unmet_demand)
        # Fulfillment rate: h_fulfillment_rate is a list-of-lists (one per supplier).
        # We report the average across suppliers per period.
        # Skip the first 10 entries (pre-initialized padding in Consumer.__init__)
        fr = c.h_fulfillment_rate[-(n):]  # last n entries
        if len(fr) == n:
            _safe_add(f"{c.name} avg fulfillment rate",
                      [sum(row) / max(len(row), 1) for row in fr])

    # ── Transhipper data ─────────────────────────────────────────────────
    # h_inventory is NOT populated. Use allocations & orders instead.
    for t in simulation.transhippers:
        if len(t.h_allocations) == n:
            _safe_add(f"{t.name} total allocated",
                      [sum(a) for a in t.h_allocations])
        if len(t.h_customers_orders) == n:
            _safe_add(f"{t.name} total orders received",
                      [sum(o) for o in t.h_customers_orders])
        # Backlog (sum across suppliers)
        bl = t.h_backlog[-(n):]
        if len(bl) == n:
            _safe_add(f"{t.name} total backlog",
                      [sum(b) for b in bl])

    # ── Producer data ────────────────────────────────────────────────────
    for p in simulation.producers:
        _safe_add(f"{p.name} inventory", p.h_inventory)
        _safe_add(f"{p.name} production", p.h_production_observed)
        if len(p.h_customers_orders) == n:
            _safe_add(f"{p.name} total orders received",
                      [sum(o) for o in p.h_customers_orders])
        if len(p.h_backlog) == n:
            _safe_add(f"{p.name} total backlog",
                      [sum(b) for b in p.h_backlog])

    return df
