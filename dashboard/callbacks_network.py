"""
Callbacks for the Network Builder tab:
- Add / remove / clear nodes
- Two-click edge creation with layer validation
- Agent parameter sidebar editing
- Save / Load / Preset configuration
"""

import json
import base64

from dash import Input, Output, State, callback, ctx, html, dcc, no_update
from dashboard.constants import (
    COLUMN_X,
    NODE_Y_START,
    NODE_Y_SPACING,
    CONSUMER_DEFAULTS,
    TRANSHIPPER_DEFAULTS,
    PRODUCER_DEFAULTS,
    get_starter_preset,
)
from dashboard.policy_registry import (
    ORDER_POLICIES,
    PRODUCTION_POLICIES,
    ALLOCATION_POLICIES,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_agent_type(node_id):
    """Extract agent type from node ID like 'producer-0'."""
    return node_id.rsplit("-", 1)[0]


def _count_nodes_of_type(elements, agent_type):
    """Count how many nodes of a given type exist in elements."""
    return sum(
        1 for el in elements
        if "source" not in el.get("data", {}) and el.get("data", {}).get("agent_type") == agent_type
    )


def _compute_y_position(elements, agent_type):
    """Calculate y position for a new node based on how many of that type exist."""
    count = _count_nodes_of_type(elements, agent_type)
    return NODE_Y_START + count * NODE_Y_SPACING


def _get_default_label(agent_type, counter):
    """Generate default label like MN1, WS2, H3."""
    prefixes = {"producer": "MN", "transhipper": "WS", "consumer": "H"}
    return f"{prefixes[agent_type]}{counter}"


def _are_adjacent_layers(type_a, type_b):
    """Check if two agent types are in adjacent layers (can be connected)."""
    adjacent = {
        ("producer", "transhipper"),
        ("transhipper", "producer"),
        ("transhipper", "consumer"),
        ("consumer", "transhipper"),
    }
    return (type_a, type_b) in adjacent


def _edge_exists(elements, source_id, target_id):
    """Check if an edge already exists between two nodes (in either direction)."""
    for el in elements:
        d = el.get("data", {})
        if "source" in d:
            if (d["source"] == source_id and d["target"] == target_id) or \
               (d["source"] == target_id and d["target"] == source_id):
                return True
    return False


def _normalize_edge_direction(source_id, target_id):
    """Ensure edge direction is always upstream→downstream: producer→transhipper→consumer."""
    order = {"producer": 0, "transhipper": 1, "consumer": 2}
    source_type = _get_agent_type(source_id)
    target_type = _get_agent_type(target_id)
    if order.get(source_type, 0) > order.get(target_type, 0):
        return target_id, source_id
    return source_id, target_id


# ── Sidebar rendering helpers ────────────────────────────────────────────────

def _render_consumer_sidebar(data):
    """Render sidebar form for a Consumer node."""
    return [
        html.H5(f"Health Center: {data.get('label', '')}"),
        html.Hr(),
        html.Label("Name"),
        dcc.Input(id="sidebar-name", value=data.get("label", ""), type="text", className="sidebar-input"),
        html.Label("Demand Mean (d)"),
        dcc.Input(id="sidebar-d", value=data.get("d", 150), type="number", className="sidebar-input"),
        html.Label("Demand Std Dev (dstd)"),
        dcc.Input(id="sidebar-dstd", value=data.get("dstd", 10), type="number", className="sidebar-input"),
        html.Label("Safety Stock (ss)"),
        dcc.Input(id="sidebar-ss", value=data.get("ss", 1000), type="number", className="sidebar-input"),
        html.Label("Order Policy"),
        dcc.Dropdown(
            id="sidebar-order-policy",
            options=[{"label": k, "value": k} for k in ORDER_POLICIES],
            value=data.get("order_policy", "Base Stock FR (All First)"),
            clearable=False,
            className="sidebar-dropdown",
        ),
        html.Br(),
        html.Button("Save", id="btn-save-sidebar", n_clicks=0, className="toolbar-btn"),
    ]


def _render_transhipper_sidebar(data):
    """Render sidebar form for a Transhipper node."""
    return [
        html.H5(f"Distributor: {data.get('label', '')}"),
        html.Hr(),
        html.Label("Name"),
        dcc.Input(id="sidebar-name", value=data.get("label", ""), type="text", className="sidebar-input"),
        html.Label("Safety Stock (ss)"),
        dcc.Input(id="sidebar-ss", value=data.get("ss", 8000), type="number", className="sidebar-input"),
        html.Label("Lead Time (l)"),
        dcc.Input(id="sidebar-l", value=data.get("l", 2), type="number", min=1, className="sidebar-input"),
        html.Label("Order Policy"),
        dcc.Dropdown(
            id="sidebar-order-policy",
            options=[{"label": k, "value": k} for k in ORDER_POLICIES],
            value=data.get("order_policy", "Base Stock FR (All First)"),
            clearable=False,
            className="sidebar-dropdown",
        ),
        html.Label("Allocation Policy"),
        dcc.Dropdown(
            id="sidebar-alloc-policy",
            options=[{"label": k, "value": k} for k in ALLOCATION_POLICIES],
            value=data.get("allocation_policy", "Proportional"),
            clearable=False,
            className="sidebar-dropdown",
        ),
        html.Br(),
        html.Button("Save", id="btn-save-sidebar", n_clicks=0, className="toolbar-btn"),
    ]


def _render_producer_sidebar(data):
    """Render sidebar form for a Producer node."""
    return [
        html.H5(f"Manufacturer: {data.get('label', '')}"),
        html.Hr(),
        html.Label("Name"),
        dcc.Input(id="sidebar-name", value=data.get("label", ""), type="text", className="sidebar-input"),
        html.Label("Safety Stock (ss)"),
        dcc.Input(id="sidebar-ss", value=data.get("ss", 10000), type="number", className="sidebar-input"),
        html.Label("Max Production (m)"),
        dcc.Input(id="sidebar-m", value=data.get("m", 800), type="number", className="sidebar-input"),
        html.Label("Shipping Lead Time (l)"),
        dcc.Input(id="sidebar-l", value=data.get("l", 2), type="number", min=1, className="sidebar-input"),
        html.Label("Production Lead Time (pl)"),
        dcc.Input(id="sidebar-pl", value=data.get("pl", 2), type="number", min=1, className="sidebar-input"),
        html.Label("Production Policy"),
        dcc.Dropdown(
            id="sidebar-prod-policy",
            options=[{"label": k, "value": k} for k in PRODUCTION_POLICIES],
            value=data.get("production_policy", "Base Stock"),
            clearable=False,
            className="sidebar-dropdown",
        ),
        html.Label("Allocation Policy"),
        dcc.Dropdown(
            id="sidebar-alloc-policy",
            options=[{"label": k, "value": k} for k in ALLOCATION_POLICIES],
            value=data.get("allocation_policy", "Proportional"),
            clearable=False,
            className="sidebar-dropdown",
        ),
        html.Br(),
        html.Button("Save", id="btn-save-sidebar", n_clicks=0, className="toolbar-btn"),
    ]


# ── Register all callbacks ───────────────────────────────────────────────────

def register_network_callbacks(app):
    """Register all network builder callbacks with the Dash app."""

    # ── 1. Add nodes ────────────────────────────────────────────────────────
    @app.callback(
        Output("cytoscape-graph", "elements", allow_duplicate=True),
        Output("store-node-counters", "data", allow_duplicate=True),
        Input("btn-add-producer", "n_clicks"),
        Input("btn-add-transhipper", "n_clicks"),
        Input("btn-add-consumer", "n_clicks"),
        State("cytoscape-graph", "elements"),
        State("store-node-counters", "data"),
        prevent_initial_call=True,
    )
    def add_node(prod_clicks, trans_clicks, cons_clicks, elements, counters):
        triggered = ctx.triggered_id
        if triggered is None:
            return no_update, no_update

        type_map = {
            "btn-add-producer": "producer",
            "btn-add-transhipper": "transhipper",
            "btn-add-consumer": "consumer",
        }
        agent_type = type_map.get(triggered)
        if agent_type is None:
            return no_update, no_update

        # Determine counter and node ID
        counter = counters.get(agent_type, 0)
        node_id = f"{agent_type}-{counter}"
        label = _get_default_label(agent_type, counter + 1)  # 1-indexed for display

        # Get defaults
        defaults_map = {
            "producer": PRODUCER_DEFAULTS,
            "transhipper": TRANSHIPPER_DEFAULTS,
            "consumer": CONSUMER_DEFAULTS,
        }
        defaults = defaults_map[agent_type].copy()

        # Calculate position
        y_pos = _compute_y_position(elements, agent_type)

        new_node = {
            "data": {
                "id": node_id,
                "label": label,
                "agent_type": agent_type,
                "agent_num": counter,
                **defaults,
            },
            "position": {"x": COLUMN_X[agent_type], "y": y_pos},
        }

        counters[agent_type] = counter + 1
        return elements + [new_node], counters

    # ── 2. Delete selected node ─────────────────────────────────────────────
    @app.callback(
        Output("cytoscape-graph", "elements", allow_duplicate=True),
        Output("network-status", "children", allow_duplicate=True),
        Input("btn-delete-selected", "n_clicks"),
        State("cytoscape-graph", "selectedNodeData"),
        State("cytoscape-graph", "elements"),
        prevent_initial_call=True,
    )
    def delete_selected(n_clicks, selected_nodes, elements):
        if not n_clicks or not selected_nodes:
            return no_update, "No node selected to delete."

        ids_to_delete = {n["id"] for n in selected_nodes}

        # Remove nodes and any connected edges
        new_elements = []
        for el in elements:
            d = el.get("data", {})
            if d.get("id") in ids_to_delete:
                continue  # skip this node
            if "source" in d:
                if d["source"] in ids_to_delete or d["target"] in ids_to_delete:
                    continue  # skip edges connected to deleted nodes
            new_elements.append(el)

        return new_elements, f"Deleted {len(ids_to_delete)} node(s) and connected edges."

    # ── 3. Clear all ────────────────────────────────────────────────────────
    @app.callback(
        Output("cytoscape-graph", "elements", allow_duplicate=True),
        Output("store-node-counters", "data", allow_duplicate=True),
        Output("network-status", "children", allow_duplicate=True),
        Input("btn-clear-all", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_all(n_clicks):
        if not n_clicks:
            return no_update, no_update, no_update
        return [], {"producer": 0, "transhipper": 0, "consumer": 0}, "Canvas cleared."

    # ── 4. Connect mode toggle ──────────────────────────────────────────────
    @app.callback(
        Output("store-connect-mode", "data"),
        Output("store-connect-source", "data", allow_duplicate=True),
        Output("btn-connect-mode", "children"),
        Output("btn-connect-mode", "className"),
        Output("network-status", "children", allow_duplicate=True),
        Input("btn-connect-mode", "n_clicks"),
        State("store-connect-mode", "data"),
        prevent_initial_call=True,
    )
    def toggle_connect_mode(n_clicks, currently_on):
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update
        new_state = not currently_on
        label = "Connect Mode: ON" if new_state else "Connect Mode: OFF"
        cls = "toolbar-btn connect-btn connect-active" if new_state else "toolbar-btn connect-btn"
        status = "Connect mode ON — click two nodes to connect them." if new_state else "Connect mode OFF."
        return new_state, None, label, cls, status

    # ── 5. Unified node click handler (connection mode + sidebar) ───────────
    # Merged into a single callback because both need tapNodeData as Input
    # and both write to store-connect-source.
    @app.callback(
        Output("cytoscape-graph", "elements", allow_duplicate=True),
        Output("store-connect-source", "data"),
        Output("network-status", "children", allow_duplicate=True),
        Output("sidebar-content", "children"),
        Input("cytoscape-graph", "tapNodeData"),
        State("store-connect-mode", "data"),
        State("store-connect-source", "data"),
        State("cytoscape-graph", "elements"),
        prevent_initial_call=True,
    )
    def handle_node_click(tap_data, connect_mode, source_id, elements):
        if not tap_data:
            return no_update, no_update, no_update, no_update

        # ── If NOT in connect mode → show sidebar ───────────────────────
        if not connect_mode:
            agent_type = tap_data.get("agent_type")
            sidebar = html.P("Unknown agent type.")
            if agent_type == "consumer":
                sidebar = _render_consumer_sidebar(tap_data)
            elif agent_type == "transhipper":
                sidebar = _render_transhipper_sidebar(tap_data)
            elif agent_type == "producer":
                sidebar = _render_producer_sidebar(tap_data)
            return no_update, no_update, no_update, sidebar

        # ── Connect mode: two-click edge creation ───────────────────────
        clicked_id = tap_data["id"]

        # First click — set source
        if source_id is None:
            for el in elements:
                d = el.get("data", {})
                if d.get("id") == clicked_id:
                    el["classes"] = "connection-source"
                else:
                    el.pop("classes", None)
            return elements, clicked_id, f"Source: {tap_data.get('label', clicked_id)}. Click a target node.", no_update

        # Second click on same node — cancel
        if clicked_id == source_id:
            for el in elements:
                el.pop("classes", None)
            return elements, None, "Cancelled — clicked same node.", no_update

        source_type = _get_agent_type(source_id)
        target_type = _get_agent_type(clicked_id)

        # Validate adjacent layers
        if not _are_adjacent_layers(source_type, target_type):
            for el in elements:
                el.pop("classes", None)
            return elements, None, f"Cannot connect {source_type} directly to {target_type}. Only adjacent layers.", no_update

        # Check for duplicate edge
        if _edge_exists(elements, source_id, clicked_id):
            for el in elements:
                el.pop("classes", None)
            return elements, None, "Connection already exists.", no_update

        # Normalize direction: upstream → downstream
        edge_source, edge_target = _normalize_edge_direction(source_id, clicked_id)
        edge_id = f"edge-{edge_source}-{edge_target}"
        new_edge = {"data": {"source": edge_source, "target": edge_target, "id": edge_id}}

        # Clear highlight classes
        for el in elements:
            el.pop("classes", None)

        source_label = ""
        target_label = ""
        for el in elements:
            d = el.get("data", {})
            if d.get("id") == edge_source:
                source_label = d.get("label", edge_source)
            if d.get("id") == edge_target:
                target_label = d.get("label", edge_target)

        return elements + [new_edge], None, f"Connected {source_label} → {target_label}", no_update

    # ── 7. Save sidebar edits back to node ──────────────────────────────────
    @app.callback(
        Output("cytoscape-graph", "elements", allow_duplicate=True),
        Output("network-status", "children", allow_duplicate=True),
        Input("btn-save-sidebar", "n_clicks"),
        State("cytoscape-graph", "tapNodeData"),
        State("cytoscape-graph", "elements"),
        # Read all possible sidebar inputs (some may not exist depending on agent type)
        State("sidebar-name", "value"),
        State("sidebar-ss", "value"),
        # Consumer-specific
        State("sidebar-d", "value"),
        State("sidebar-dstd", "value"),
        State("sidebar-order-policy", "value"),
        # Transhipper-specific
        State("sidebar-l", "value"),
        State("sidebar-alloc-policy", "value"),
        # Producer-specific
        State("sidebar-m", "value"),
        State("sidebar-pl", "value"),
        State("sidebar-prod-policy", "value"),
        prevent_initial_call=True,
    )
    def save_sidebar(n_clicks, tap_data, elements,
                     name, ss, d, dstd, order_policy,
                     l_val, alloc_policy, m, pl, prod_policy):
        if not n_clicks or not tap_data:
            return no_update, no_update

        node_id = tap_data["id"]
        agent_type = tap_data.get("agent_type")

        # Find and update the node in elements
        for el in elements:
            data = el.get("data", {})
            if data.get("id") == node_id:
                # Update common fields
                if name is not None:
                    data["label"] = name
                if ss is not None:
                    data["ss"] = ss

                if agent_type == "consumer":
                    if d is not None:
                        data["d"] = d
                    if dstd is not None:
                        data["dstd"] = dstd
                    if order_policy is not None:
                        data["order_policy"] = order_policy

                elif agent_type == "transhipper":
                    if l_val is not None:
                        data["l"] = l_val
                    if order_policy is not None:
                        data["order_policy"] = order_policy
                    if alloc_policy is not None:
                        data["allocation_policy"] = alloc_policy

                elif agent_type == "producer":
                    if m is not None:
                        data["m"] = m
                    if l_val is not None:
                        data["l"] = l_val
                    if pl is not None:
                        data["pl"] = pl
                    if prod_policy is not None:
                        data["production_policy"] = prod_policy
                    if alloc_policy is not None:
                        data["allocation_policy"] = alloc_policy

                break

        return elements, f"Saved properties for {name or node_id}."

    # ── 8. Save config to JSON ──────────────────────────────────────────────
    @app.callback(
        Output("download-config", "data"),
        Input("btn-save-config", "n_clicks"),
        State("cytoscape-graph", "elements"),
        State("store-disruptions", "data"),
        prevent_initial_call=True,
    )
    def save_config(n_clicks, elements, disruptions):
        if not n_clicks:
            return no_update
        config = {
            "elements": elements,
            "disruptions": disruptions or [],
        }
        content = json.dumps(config, indent=2)
        return dcc.send_string(content, filename="supply_chain_config.json")

    # ── 9. Load config from JSON ────────────────────────────────────────────
    @app.callback(
        Output("cytoscape-graph", "elements", allow_duplicate=True),
        Output("store-disruptions", "data", allow_duplicate=True),
        Output("store-node-counters", "data", allow_duplicate=True),
        Output("network-status", "children", allow_duplicate=True),
        Input("upload-config", "contents"),
        State("upload-config", "filename"),
        prevent_initial_call=True,
    )
    def load_config(contents, filename):
        if contents is None:
            return no_update, no_update, no_update, no_update
        try:
            # Decode base64 content
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string).decode("utf-8")
            config = json.loads(decoded)

            elements = config.get("elements", [])
            disruptions = config.get("disruptions", [])

            # Rebuild node counters from loaded elements
            counters = {"producer": 0, "transhipper": 0, "consumer": 0}
            for el in elements:
                d = el.get("data", {})
                agent_type = d.get("agent_type")
                if agent_type and "source" not in d:
                    num = d.get("agent_num", 0)
                    counters[agent_type] = max(counters[agent_type], num + 1)

            return elements, disruptions, counters, f"Loaded config from {filename}."
        except Exception as e:
            return no_update, no_update, no_update, f"Error loading config: {e}"

    # ── 10. Load preset ─────────────────────────────────────────────────────
    @app.callback(
        Output("cytoscape-graph", "elements", allow_duplicate=True),
        Output("store-node-counters", "data", allow_duplicate=True),
        Output("network-status", "children", allow_duplicate=True),
        Output("dropdown-presets", "value"),
        Input("dropdown-presets", "value"),
        prevent_initial_call=True,
    )
    def load_preset(preset_value):
        if not preset_value:
            return no_update, no_update, no_update, no_update

        from dashboard.constants import get_starter_preset, get_main_py_preset

        if preset_value == "starter":
            elements = get_starter_preset()
            counters = {"producer": 1, "transhipper": 1, "consumer": 2}
            msg = "Loaded Starter preset (1×1×2)."
        elif preset_value == "main_py":
            elements = get_main_py_preset()
            counters = {"producer": 2, "transhipper": 3, "consumer": 6}
            msg = "Loaded Main.py preset (2×3×6)."
        else:
            return no_update, no_update, no_update, None

        return elements, counters, msg, None  # Clear dropdown value
