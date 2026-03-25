"""
Dash layout for the supply chain simulation dashboard.
Three tabs: Network Builder, Simulation Config, Results.
"""

import dash_cytoscape as cyto
from dash import dcc, html

from dashboard.constants import (
    CANVAS_HEIGHT,
    COLUMN_LABELS,
    NODE_COLORS,
    get_starter_preset,
)

# ── Cytoscape stylesheet ────────────────────────────────────────────────────
CYTO_STYLESHEET = [
    # Default node style
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": "12px",
            "font-weight": "bold",
            "color": "#fff",
            "width": 60,
            "height": 60,
            "border-width": 2,
            "border-color": "#333",
        },
    },
    # Producer nodes
    {
        "selector": 'node[agent_type = "producer"]',
        "style": {
            "background-color": NODE_COLORS["producer"],
            "shape": "rectangle",
        },
    },
    # Transhipper nodes
    {
        "selector": 'node[agent_type = "transhipper"]',
        "style": {
            "background-color": NODE_COLORS["transhipper"],
            "shape": "diamond",
            "color": "#1A1A1A",
        },
    },
    # Consumer nodes
    {
        "selector": 'node[agent_type = "consumer"]',
        "style": {
            "background-color": NODE_COLORS["consumer"],
            "shape": "ellipse",
        },
    },
    # Selected node highlight
    {
        "selector": "node:selected",
        "style": {
            "border-width": 4,
            "border-color": "#FFD700",
        },
    },
    # "Source selected" for two-click connection mode
    {
        "selector": ".connection-source",
        "style": {
            "border-width": 5,
            "border-color": "#00FF00",
            "border-style": "dashed",
        },
    },
    # Edge style
    {
        "selector": "edge",
        "style": {
            "width": 2,
            "line-color": "#999",
            "target-arrow-color": "#999",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 1.2,
        },
    },
]


def build_toolbar():
    """Toolbar with Add buttons and connection mode toggle."""
    return html.Div(
        className="toolbar",
        children=[
            html.Button(
                "+ Manufacturer",
                id="btn-add-producer",
                n_clicks=0,
                className="toolbar-btn producer-btn",
            ),
            html.Button(
                "+ Distributor",
                id="btn-add-transhipper",
                n_clicks=0,
                className="toolbar-btn transhipper-btn",
            ),
            html.Button(
                "+ Health Center",
                id="btn-add-consumer",
                n_clicks=0,
                className="toolbar-btn consumer-btn",
            ),
            html.Div(style={"width": "20px"}),  # spacer
            html.Button(
                "Connect Mode: OFF",
                id="btn-connect-mode",
                n_clicks=0,
                className="toolbar-btn connect-btn",
            ),
            html.Button(
                "Delete Selected",
                id="btn-delete-selected",
                n_clicks=0,
                className="toolbar-btn delete-btn",
            ),
            html.Button(
                "Clear All",
                id="btn-clear-all",
                n_clicks=0,
                className="toolbar-btn clear-btn",
            ),
            html.Div(style={"width": "20px"}),  # spacer
            html.Button(
                "Save Config",
                id="btn-save-config",
                n_clicks=0,
                className="toolbar-btn",
                style={"borderLeft": "4px solid #2196F3"},
            ),
            dcc.Upload(
                id="upload-config",
                children=html.Button(
                    "Load Config",
                    className="toolbar-btn",
                    style={"borderLeft": "4px solid #2196F3"},
                ),
                accept=".json",
            ),
            dcc.Dropdown(
                id="dropdown-presets",
                options=[
                    {"label": "Starter (1×1×2)", "value": "starter"},
                    {"label": "Main.py (2×3×6)", "value": "main_py"},
                ],
                placeholder="Load Preset...",
                clearable=True,
                style={"width": "180px", "fontSize": "13px"},
            ),
            dcc.Download(id="download-config"),
        ],
    )


def build_sidebar():
    """Right-side panel for editing agent parameters."""
    return html.Div(
        id="sidebar",
        className="sidebar",
        children=[
            html.H4("Agent Properties", className="sidebar-title"),
            html.Div(
                id="sidebar-content",
                children=[
                    html.P(
                        "Click an agent to edit its properties.",
                        className="sidebar-placeholder",
                    )
                ],
            ),
        ],
    )


def build_legend():
    """Legend showing node shapes and colors."""
    items = [
        ("producer", "rectangle", "Manufacturer"),
        ("transhipper", "diamond", "Distributor"),
        ("consumer", "circle", "Health Center"),
    ]
    children = []
    for agent_type, shape, label in items:
        color = NODE_COLORS[agent_type]
        shape_style = {
            "width": "16px",
            "height": "16px",
            "backgroundColor": color,
            "display": "inline-block",
            "marginRight": "6px",
            "borderRadius": "50%" if shape == "circle" else ("0" if shape == "rectangle" else "0"),
            "transform": "rotate(45deg)" if shape == "diamond" else "none",
        }
        children.append(
            html.Span(
                [html.Span(style=shape_style), label],
                style={"marginRight": "18px", "fontSize": "13px"},
            )
        )
    return html.Div(children, className="legend")


def build_network_tab():
    """Network Builder tab content."""
    return html.Div(
        className="network-tab",
        children=[
            build_toolbar(),
            html.Div(
                className="network-main",
                children=[
                    # Cytoscape canvas
                    html.Div(
                        className="canvas-container",
                        children=[
                            build_legend(),
                            cyto.Cytoscape(
                                id="cytoscape-graph",
                                elements=get_starter_preset(),
                                layout={"name": "preset"},
                                style={"width": "100%", "height": CANVAS_HEIGHT},
                                stylesheet=CYTO_STYLESHEET,
                                autoungrabify=False,
                                userZoomingEnabled=True,
                                userPanningEnabled=True,
                                boxSelectionEnabled=False,
                            ),
                        ],
                    ),
                    # Sidebar
                    build_sidebar(),
                ],
            ),
            # Status / feedback bar
            html.Div(id="network-status", className="status-bar", children=""),
            # Hidden stores for state management
            dcc.Store(id="store-connect-source", data=None),  # ID of first node clicked in connect mode
            dcc.Store(id="store-connect-mode", data=False),   # Whether connect mode is active
            dcc.Store(id="store-node-counters", data={"producer": 1, "transhipper": 1, "consumer": 2}),  # For auto-naming
        ],
    )


def build_sim_config_tab():
    """Simulation Config tab content with disruption configuration."""
    return html.Div(
        className="sim-config-tab",
        children=[
            # ── Simulation parameters ────────────────────────────────────
            html.Div(
                className="config-section",
                children=[
                    html.H4("Simulation Parameters"),
                    html.Div(
                        className="config-row",
                        children=[
                            html.Label("Number of periods:"),
                            dcc.Input(
                                id="input-sim-periods",
                                type="number",
                                value=300,
                                min=1,
                                max=5000,
                                step=1,
                                className="config-input",
                            ),
                        ],
                    ),
                ],
            ),
            # ── Disruption events ────────────────────────────────────────
            html.Div(
                className="config-section",
                children=[
                    html.H4("Disruption Events"),
                    html.P(
                        "Define capacity disruptions for manufacturers. "
                        "Remaining Capacity is a fraction of normal output: "
                        "0.2 = production drops to 20% of normal (lower = more severe).",
                        style={"fontSize": "13px", "color": "#666", "margin": "0 0 12px 0"},
                    ),
                    html.Div(id="disruption-rows", children=[]),
                    html.Button(
                        "+ Add Disruption",
                        id="btn-add-disruption",
                        n_clicks=0,
                        className="toolbar-btn",
                        style={"marginTop": "8px"},
                    ),
                    # Store for disruption data
                    dcc.Store(id="store-disruptions", data=[]),
                    dcc.Store(id="store-disruption-counter", data=0),
                ],
            ),
            # ── Run button ───────────────────────────────────────────────
            html.Div(
                style={"marginTop": "20px"},
                children=[
                    html.Button(
                        "Run Simulation",
                        id="btn-run-simulation",
                        n_clicks=0,
                        className="run-button",
                    ),
                    dcc.Loading(
                        id="loading-sim",
                        type="default",
                        children=[html.Div(id="sim-status", className="status-bar")],
                    ),
                ],
            ),
        ],
    )


def build_results_tab():
    """Results tab with multiple charts and agent filtering."""
    return html.Div(
        className="results-tab",
        children=[
            html.H4("Simulation Results"),
            html.Div(id="results-placeholder", children=[
                html.P("Run a simulation to see results here.", className="sidebar-placeholder"),
            ]),
            # ── Charts container (hidden until sim runs) ─────────────────
            html.Div(
                id="results-charts-container",
                style={"display": "none"},
                children=[
                    # Inventory chart
                    html.Div(className="chart-section", children=[
                        html.H5("Inventory Levels"),
                        dcc.Graph(id="graph-inventory"),
                    ]),
                    # Demand vs Unmet Demand (consumers)
                    html.Div(className="chart-section", children=[
                        html.H5("Demand vs Unmet Demand (Health Centers)"),
                        dcc.Graph(id="graph-demand"),
                    ]),
                    # Fulfillment Rate (consumers)
                    html.Div(className="chart-section", children=[
                        html.H5("Fulfillment Rate (Health Centers)"),
                        dcc.Graph(id="graph-fulfillment"),
                    ]),
                    # Throughput & Backlog (transhippers + producers)
                    html.Div(className="chart-section", children=[
                        html.H5("Backlog"),
                        dcc.Graph(id="graph-backlog"),
                    ]),
                    # Production (producers)
                    html.Div(className="chart-section", children=[
                        html.H5("Production (Manufacturers)"),
                        dcc.Graph(id="graph-production"),
                    ]),
                ],
            ),
            # ── Download ─────────────────────────────────────────────────
            html.Div(
                style={"marginTop": "12px"},
                children=[
                    html.Button(
                        "Download Results (Excel)",
                        id="btn-download-results",
                        n_clicks=0,
                        className="download-button",
                        style={"display": "none"},
                    ),
                    dcc.Download(id="download-results"),
                ],
            ),
            # Stores
            dcc.Store(id="store-results-data"),
            dcc.Store(id="store-disruptions-used", data=[]),  # disruptions that were active in last run
        ],
    )


def build_sensitivity_tab():
    """Sensitivity Analysis tab with Monte Carlo configuration and results."""
    from dashboard.monte_carlo import get_sweep_param_options

    return html.Div(
        className="sim-config-tab",
        children=[
            html.H4("Sensitivity Analysis"),
            html.P(
                "Run multiple simulations to measure variability or test how "
                "changing a parameter affects outcomes.",
                style={"fontSize": "13px", "color": "#666", "margin": "0 0 16px 0"},
            ),

            # ── Mode selection ──────────────────────────────────────────
            html.Div(
                className="config-section",
                children=[
                    html.H5("Analysis Mode"),
                    dcc.RadioItems(
                        id="mc-mode",
                        options=[
                            {"label": "Stochastic Replication — same parameters, different random seeds",
                             "value": "replication"},
                            {"label": "Parameter Sweep — vary one parameter across a range",
                             "value": "sweep"},
                        ],
                        value="replication",
                        style={"fontSize": "13px"},
                        inputStyle={"marginRight": "6px"},
                        labelStyle={"display": "block", "marginBottom": "8px"},
                    ),
                ],
            ),

            # ── Common settings ─────────────────────────────────────────
            html.Div(
                className="config-section",
                children=[
                    html.H5("Common Settings"),
                    html.Div(
                        className="config-row",
                        style={"flexWrap": "wrap", "gap": "16px"},
                        children=[
                            html.Div([
                                html.Label("Number of runs:"),
                                dcc.Input(
                                    id="mc-n-runs", type="number",
                                    value=20, min=2, max=500, step=1,
                                    className="config-input",
                                ),
                            ]),
                            html.Div([
                                html.Label("Periods per run:"),
                                dcc.Input(
                                    id="mc-periods", type="number",
                                    value=200, min=10, max=2000, step=10,
                                    className="config-input",
                                ),
                            ]),
                            html.Div([
                                html.Label("Starting seed (for reproducibility):"),
                                dcc.Input(
                                    id="mc-seed", type="number",
                                    value=0, min=0, step=1,
                                    className="config-input",
                                ),
                            ]),
                        ],
                    ),
                ],
            ),

            # ── Parameter sweep settings (shown only in sweep mode) ─────
            html.Div(
                id="mc-sweep-settings",
                className="config-section",
                style={"display": "none"},
                children=[
                    html.H5("Parameter Sweep Settings"),
                    html.Div(
                        className="config-row",
                        style={"flexWrap": "wrap", "gap": "16px"},
                        children=[
                            html.Div([
                                html.Label("Parameter to sweep:"),
                                dcc.Dropdown(
                                    id="mc-sweep-param",
                                    options=[{"label": p, "value": p} for p in get_sweep_param_options()],
                                    value="Demand Mean (d)",
                                    clearable=False,
                                    style={"width": "220px", "fontSize": "13px"},
                                ),
                            ]),
                            html.Div([
                                html.Label("Apply to agent:"),
                                dcc.Dropdown(
                                    id="mc-sweep-agent",
                                    options=[{"label": "All applicable agents", "value": "__all__"}],
                                    value="__all__",
                                    clearable=False,
                                    style={"width": "200px", "fontSize": "13px"},
                                ),
                            ]),
                        ],
                    ),
                    html.Div(
                        className="config-row",
                        style={"marginTop": "10px", "gap": "16px"},
                        children=[
                            html.Div([
                                html.Label("Min value:"),
                                dcc.Input(
                                    id="mc-sweep-min", type="number",
                                    value=None, placeholder="Select parameter...",
                                    className="config-input",
                                ),
                            ]),
                            html.Div([
                                html.Label("Max value:"),
                                dcc.Input(
                                    id="mc-sweep-max", type="number",
                                    value=None, placeholder="Select parameter...",
                                    className="config-input",
                                ),
                            ]),
                            html.Div([
                                html.Label("Steps:"),
                                dcc.Input(
                                    id="mc-sweep-steps", type="number",
                                    value=5, min=2, max=20, step=1,
                                    className="config-input",
                                ),
                            ]),
                        ],
                    ),
                ],
            ),

            # ── Run button ──────────────────────────────────────────────
            html.Div(
                style={"marginTop": "20px"},
                children=[
                    html.Button(
                        "Run Analysis",
                        id="btn-run-mc",
                        n_clicks=0,
                        className="run-button",
                    ),
                    dcc.Loading(
                        id="loading-mc",
                        type="default",
                        children=[html.Div(id="mc-status", className="status-bar")],
                    ),
                ],
            ),

            # ── Results area ────────────────────────────────────────────
            html.Div(
                id="mc-results-container",
                style={"display": "none", "marginTop": "20px"},
                children=[
                    # Fan / confidence band charts
                    html.Div(className="chart-section", children=[
                        html.H5("Inventory — Confidence Bands"),
                        dcc.Graph(id="mc-graph-inventory"),
                    ]),
                    html.Div(className="chart-section", children=[
                        html.H5("Fulfillment Rate — Confidence Bands"),
                        dcc.Graph(id="mc-graph-fulfillment"),
                    ]),
                    html.Div(className="chart-section", children=[
                        html.H5("Production — Confidence Bands"),
                        dcc.Graph(id="mc-graph-production"),
                    ]),
                    # Box plot for final-period distribution
                    html.Div(className="chart-section", children=[
                        html.H5("Final-Period Distribution"),
                        dcc.Graph(id="mc-graph-boxplot"),
                    ]),
                ],
            ),

            # ── Download ────────────────────────────────────────────────
            html.Div(
                style={"marginTop": "12px"},
                children=[
                    html.Button(
                        "Download MC Results (Excel)",
                        id="btn-download-mc",
                        n_clicks=0,
                        className="download-button",
                        style={"display": "none"},
                    ),
                    dcc.Download(id="download-mc-results"),
                ],
            ),

            # Stores
            dcc.Store(id="store-mc-results"),
        ],
    )


def build_layout():
    """Build the complete app layout."""
    return html.Div(
        className="app-container",
        children=[
            # Title
            html.Div(
                className="title-section",
                children=[
                    html.H1("Supply Chain Simulation Dashboard"),
                    html.Div("Build networks visually. Run experiments. No code required."),
                ],
            ),
            # Tabs
            dcc.Tabs(
                id="main-tabs",
                value="tab-network",
                children=[
                    dcc.Tab(label="Network Builder", value="tab-network", children=[build_network_tab()]),
                    dcc.Tab(label="Simulation Config", value="tab-config", children=[build_sim_config_tab()]),
                    dcc.Tab(label="Results", value="tab-results", children=[build_results_tab()]),
                    dcc.Tab(label="Sensitivity Analysis", value="tab-mc", children=[build_sensitivity_tab()]),
                ],
            ),
        ],
    )
