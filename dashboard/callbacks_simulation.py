"""
Callbacks for running the simulation and displaying results.
Produces multiple charts: inventory, demand, fulfillment, backlog, production.
"""

import io
import traceback

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, html, dcc, no_update

from dashboard.graph_to_config import build_simulation_from_graph, get_full_results

CHART_TEMPLATE = "plotly_white"


def _make_line_fig(df, col_suffix, title, yaxis_title, disruptions=None):
    """Build a Plotly line figure for all columns ending with col_suffix."""
    cols = [c for c in df.columns if c.endswith(col_suffix)]
    fig = go.Figure()
    for col in cols:
        name = col.replace(col_suffix, "").strip()
        fig.add_trace(go.Scatter(
            x=list(range(len(df))),
            y=df[col].tolist(),
            name=name,
            mode="lines",
        ))

    # Add disruption shading
    if disruptions:
        for d in disruptions:
            fig.add_vrect(
                x0=d["start"], x1=d["end"],
                fillcolor="rgba(200, 16, 46, 0.1)",
                layer="below",
                line_width=0,
                annotation_text=f"{d.get('producer_label', '')} disruption",
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color="#C8102E",
            )

    fig.update_layout(
        title=title,
        xaxis_title="Period",
        yaxis_title=yaxis_title,
        template=CHART_TEMPLATE,
        hovermode="x unified",
        margin=dict(t=40, b=40),
        height=350,
    )
    return fig


def _make_demand_fig(df, disruptions=None):
    """Build demand vs unmet demand chart for consumers."""
    fig = go.Figure()
    for col in df.columns:
        if col.endswith(" demand") and "unmet" not in col:
            name = col.replace(" demand", "")
            fig.add_trace(go.Scatter(
                x=list(range(len(df))), y=df[col].tolist(),
                name=f"{name} demand", mode="lines",
            ))
            unmet_col = f"{name} unmet demand"
            if unmet_col in df.columns:
                fig.add_trace(go.Scatter(
                    x=list(range(len(df))), y=df[unmet_col].tolist(),
                    name=f"{name} unmet", mode="lines",
                    line=dict(dash="dash"),
                ))

    if disruptions:
        for d in disruptions:
            fig.add_vrect(
                x0=d["start"], x1=d["end"],
                fillcolor="rgba(200, 16, 46, 0.1)",
                layer="below", line_width=0,
            )

    fig.update_layout(
        title="Demand vs Unmet Demand",
        xaxis_title="Period", yaxis_title="Units",
        template=CHART_TEMPLATE, hovermode="x unified",
        margin=dict(t=40, b=40), height=350,
    )
    return fig


def register_simulation_callbacks(app):
    """Register simulation-related callbacks."""

    # ── Run simulation ──────────────────────────────────────────────────────
    @app.callback(
        Output("sim-status", "children"),
        Output("store-results-data", "data"),
        Output("store-disruptions-used", "data"),
        Output("graph-inventory", "figure"),
        Output("graph-demand", "figure"),
        Output("graph-fulfillment", "figure"),
        Output("graph-backlog", "figure"),
        Output("graph-production", "figure"),
        Output("results-charts-container", "style"),
        Output("results-placeholder", "style"),
        Output("btn-download-results", "style"),
        Output("main-tabs", "value"),
        Input("btn-run-simulation", "n_clicks"),
        State("cytoscape-graph", "elements"),
        State("input-sim-periods", "value"),
        State("store-disruptions", "data"),
        prevent_initial_call=True,
    )
    def run_simulation(n_clicks, elements, sim_periods, disruptions):
        if not n_clicks:
            return (no_update,) * 12

        empty_fig = go.Figure()
        empty_fig.update_layout(template=CHART_TEMPLATE)

        try:
            sim_periods = int(sim_periods) if sim_periods else 300
            disruptions = disruptions or []

            # Build and run simulation
            simulation = build_simulation_from_graph(elements, sim_periods, disruptions or None)
            simulation = simulation.run()

            # Extract results
            df = get_full_results(simulation)

            # Build all charts
            fig_inventory = _make_line_fig(df, " inventory", "Inventory Levels Over Time", "Inventory", disruptions)
            fig_demand = _make_demand_fig(df, disruptions)
            fig_fulfillment = _make_line_fig(df, " avg fulfillment rate", "Fulfillment Rate Over Time", "Rate (0-1)", disruptions)
            fig_backlog = _make_line_fig(df, " total backlog", "Backlog Over Time", "Units", disruptions)
            fig_production = _make_line_fig(df, " production", "Production Over Time", "Units Produced", disruptions)

            status_msg = f"Simulation complete. {sim_periods} periods, {len(df.columns)} metrics tracked."

            return (
                status_msg,
                df.to_json(date_format="iso", orient="split"),
                disruptions,
                fig_inventory,
                fig_demand,
                fig_fulfillment,
                fig_backlog,
                fig_production,
                {"display": "block"},       # show charts container
                {"display": "none"},        # hide placeholder
                {"display": "inline-block"},  # show download button
                "tab-results",              # switch to results tab
            )

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = html.Div([
                html.Strong("Error: "),
                html.Span(str(e)),
                html.Details([
                    html.Summary("Full traceback"),
                    html.Pre(tb, style={"fontSize": "11px", "whiteSpace": "pre-wrap"}),
                ]),
            ])
            return (
                error_msg, None, [],
                empty_fig, empty_fig, empty_fig, empty_fig, empty_fig,
                {"display": "none"},
                {"display": "block"},
                {"display": "none"},
                no_update,
            )

    # ── Download results ────────────────────────────────────────────────────
    @app.callback(
        Output("download-results", "data"),
        Input("btn-download-results", "n_clicks"),
        State("store-results-data", "data"),
        prevent_initial_call=True,
    )
    def download_results(n_clicks, results_json):
        if not results_json:
            return no_update

        df = pd.read_json(results_json, orient="split")

        def to_excel_bytes():
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            buffer.seek(0)
            return buffer.read()

        return dcc.send_bytes(to_excel_bytes, filename="simulation_results.xlsx")
