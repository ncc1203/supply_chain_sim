"""
Callbacks for the Sensitivity Analysis (Monte Carlo) tab.
"""

import traceback

import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, html, dcc, no_update

from dashboard.monte_carlo import (
    run_monte_carlo,
    get_agents_for_param,
    get_sweep_defaults,
    mc_results_to_excel,
    SWEEP_PARAMETERS,
)

CHART_TEMPLATE = "plotly_white"


def _make_fan_chart(mc_summary, metric_suffix, title, yaxis_title):
    """
    Build a fan chart (median + confidence bands) for replication mode.
    mc_summary has MultiIndex columns: (metric, stat).
    """
    fig = go.Figure()

    # Find metrics matching the suffix
    all_metrics = set(c[0] for c in mc_summary.columns)
    matching = [m for m in all_metrics if m.endswith(metric_suffix)]

    colors = [
        "#C8102E", "#6C8EBF", "#C8A978", "#4CAF50", "#9C27B0",
        "#FF9800", "#00BCD4", "#795548",
    ]

    for idx, metric in enumerate(sorted(matching)):
        color = colors[idx % len(colors)]
        periods = list(range(len(mc_summary)))

        median = mc_summary[(metric, "p50")].values
        p5 = mc_summary[(metric, "p5")].values
        p95 = mc_summary[(metric, "p95")].values
        p25 = mc_summary[(metric, "p25")].values
        p75 = mc_summary[(metric, "p75")].values

        name = metric.replace(metric_suffix, "").strip()

        # 5th–95th percentile band (light)
        fig.add_trace(go.Scatter(
            x=periods + periods[::-1],
            y=list(p95) + list(p5[::-1]),
            fill="toself",
            fillcolor=f"rgba({_hex_to_rgb(color)}, 0.1)",
            line=dict(width=0),
            name=f"{name} 5-95%",
            showlegend=False,
            hoverinfo="skip",
        ))

        # 25th–75th percentile band (medium)
        fig.add_trace(go.Scatter(
            x=periods + periods[::-1],
            y=list(p75) + list(p25[::-1]),
            fill="toself",
            fillcolor=f"rgba({_hex_to_rgb(color)}, 0.2)",
            line=dict(width=0),
            name=f"{name} 25-75%",
            showlegend=False,
            hoverinfo="skip",
        ))

        # Median line
        fig.add_trace(go.Scatter(
            x=periods, y=list(median),
            mode="lines",
            line=dict(color=color, width=2),
            name=name,
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Period",
        yaxis_title=yaxis_title,
        template=CHART_TEMPLATE,
        hovermode="x unified",
        margin=dict(t=40, b=40),
        height=400,
    )
    return fig


def _make_sweep_chart(mc_results, metric_suffix, title, yaxis_title):
    """
    Build a sweep line chart: X = sweep parameter value, Y = mean final-period metric.
    """
    fig = go.Figure()
    summary = mc_results["summary"]
    sweep_values = mc_results["sweep_values"]

    # Find columns matching the suffix
    mean_cols = [c for c in summary.columns if metric_suffix in c and "(mean)" in c]
    std_cols = [c for c in summary.columns if metric_suffix in c and "(std)" in c]

    colors = [
        "#C8102E", "#6C8EBF", "#C8A978", "#4CAF50", "#9C27B0",
        "#FF9800", "#00BCD4", "#795548",
    ]

    for idx, mean_col in enumerate(sorted(mean_cols)):
        color = colors[idx % len(colors)]
        name = mean_col.replace(metric_suffix, "").replace("(mean)", "").strip()
        y_vals = summary[mean_col].values

        # Find corresponding std col
        std_col = mean_col.replace("(mean)", "(std)")
        if std_col in summary.columns:
            y_err = summary[std_col].values
            fig.add_trace(go.Scatter(
                x=sweep_values, y=y_vals,
                error_y=dict(type="data", array=y_err, visible=True),
                mode="lines+markers",
                line=dict(color=color),
                name=name,
            ))
        else:
            fig.add_trace(go.Scatter(
                x=sweep_values, y=y_vals,
                mode="lines+markers",
                line=dict(color=color),
                name=name,
            ))

    fig.update_layout(
        title=title,
        xaxis_title=mc_results.get("sweep_param", "Parameter Value"),
        yaxis_title=f"Final-Period {yaxis_title} (mean ± std)",
        template=CHART_TEMPLATE,
        hovermode="x unified",
        margin=dict(t=40, b=40),
        height=400,
    )
    return fig


def _make_boxplot(mc_results):
    """Build box plots for final-period metric distributions."""
    fig = go.Figure()

    if mc_results["mode"] == "replication":
        all_runs = mc_results["all_runs"]
        # Pick key metrics: inventory and fulfillment rate
        for metric_suffix, label in [(" inventory", "Inventory"), (" avg fulfillment rate", "Fulfillment")]:
            for run_df in [all_runs[0]]:  # just get column names
                cols = [c for c in run_df.columns if c.endswith(metric_suffix)]
                for col in cols:
                    final_vals = [df[col].iloc[-1] for df in all_runs if col in df.columns]
                    name = col.replace(metric_suffix, "").strip()
                    fig.add_trace(go.Box(y=final_vals, name=f"{name} {label}"))

    elif mc_results["mode"] == "sweep":
        sweep_values = mc_results["sweep_values"]
        sweep_indices = mc_results["sweep_run_indices"]
        all_runs = mc_results["all_runs"]

        # Pick first inventory column
        first_df = all_runs[0]
        inv_cols = [c for c in first_df.columns if c.endswith(" inventory")]
        if inv_cols:
            col = inv_cols[0]
            name = col.replace(" inventory", "").strip()
            for sv, indices in zip(sweep_values, sweep_indices):
                final_vals = [all_runs[i][col].iloc[-1] for i in indices if col in all_runs[i].columns]
                fig.add_trace(go.Box(y=final_vals, name=f"{name} @ {sv}"))

    fig.update_layout(
        title="Final-Period Distribution Across Runs",
        yaxis_title="Value",
        template=CHART_TEMPLATE,
        margin=dict(t=40, b=40),
        height=400,
    )
    return fig


def _hex_to_rgb(hex_color):
    """Convert hex color to 'r, g, b' string for rgba()."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"


# ── Register callbacks ───────────────────────────────────────────────────────

def register_monte_carlo_callbacks(app):
    """Register Monte Carlo / Sensitivity Analysis callbacks."""

    # ── Toggle sweep settings visibility ─────────────────────────────────
    @app.callback(
        Output("mc-sweep-settings", "style"),
        Input("mc-mode", "value"),
    )
    def toggle_sweep_settings(mode):
        if mode == "sweep":
            return {"display": "block"}
        return {"display": "none"}

    # ── Update min/max defaults when sweep parameter changes ────────────
    @app.callback(
        Output("mc-sweep-min", "value"),
        Output("mc-sweep-max", "value"),
        Input("mc-sweep-param", "value"),
        prevent_initial_call=True,
    )
    def update_sweep_defaults_cb(param_name):
        if not param_name:
            return no_update, no_update
        default_min, default_max = get_sweep_defaults(param_name)
        return default_min, default_max

    # ── Populate agent dropdown based on sweep parameter ─────────────────
    @app.callback(
        Output("mc-sweep-agent", "options"),
        Output("mc-sweep-agent", "value"),
        Input("mc-sweep-param", "value"),
        State("cytoscape-graph", "elements"),
        State("store-disruptions", "data"),
    )
    def populate_agent_dropdown(param_name, elements, disruptions):
        if not param_name or not elements:
            return [{"label": "All applicable agents", "value": "__all__"}], "__all__"

        agents = get_agents_for_param(elements, param_name, disruptions)
        options = [{"label": label, "value": aid} for label, aid in agents]
        # Default to first individual agent if available, otherwise __all__
        default = agents[1][1] if len(agents) > 1 else "__all__"
        return options, default

    # ── Run Monte Carlo analysis ─────────────────────────────────────────
    @app.callback(
        Output("mc-status", "children"),
        Output("mc-results-container", "style"),
        Output("btn-download-mc", "style"),
        Output("store-mc-results", "data"),
        Output("mc-graph-inventory", "figure"),
        Output("mc-graph-fulfillment", "figure"),
        Output("mc-graph-production", "figure"),
        Output("mc-graph-boxplot", "figure"),
        Input("btn-run-mc", "n_clicks"),
        State("cytoscape-graph", "elements"),
        State("store-disruptions", "data"),
        State("mc-mode", "value"),
        State("mc-n-runs", "value"),
        State("mc-periods", "value"),
        State("mc-seed", "value"),
        State("mc-sweep-param", "value"),
        State("mc-sweep-agent", "value"),
        State("mc-sweep-min", "value"),
        State("mc-sweep-max", "value"),
        State("mc-sweep-steps", "value"),
        prevent_initial_call=True,
    )
    def run_mc_analysis(
        n_clicks, elements, disruptions,
        mode, n_runs, periods, seed,
        sweep_param, sweep_agent,
        sweep_min, sweep_max, sweep_steps,
    ):
        if not n_clicks:
            return (no_update,) * 8

        empty_fig = go.Figure()
        empty_fig.update_layout(template=CHART_TEMPLATE)

        try:
            n_runs = int(n_runs) if n_runs else 20
            periods = int(periods) if periods else 200
            seed = int(seed) if seed else 0
            disruptions = disruptions or []

            # Build sweep values if in sweep mode
            sweep_values = None
            if mode == "sweep":
                sweep_min = float(sweep_min) if sweep_min is not None else 50
                sweep_max = float(sweep_max) if sweep_max is not None else 300
                sweep_steps = int(sweep_steps) if sweep_steps else 5

                param_info = SWEEP_PARAMETERS.get(sweep_param, {})
                if param_info.get("dtype") == int:
                    sweep_values = [int(v) for v in np.linspace(sweep_min, sweep_max, sweep_steps)]
                else:
                    sweep_values = list(np.linspace(sweep_min, sweep_max, sweep_steps))

            # Run the analysis
            mc_results = run_monte_carlo(
                elements=elements,
                sim_periods=periods,
                n_runs=n_runs,
                disruptions=disruptions or None,
                mode=mode,
                sweep_param=sweep_param if mode == "sweep" else None,
                sweep_values=sweep_values,
                target_agent_id=sweep_agent if mode == "sweep" else "__all__",
                seed_start=seed,
                n_workers=1,  # sequential to avoid multiprocessing issues with Dash
            )

            # Build charts based on mode
            if mode == "replication":
                fig_inv = _make_fan_chart(mc_results["summary"], " inventory", "Inventory Levels (Confidence Bands)", "Inventory")
                fig_ful = _make_fan_chart(mc_results["summary"], " avg fulfillment rate", "Fulfillment Rate (Confidence Bands)", "Rate (0-1)")
                fig_prod = _make_fan_chart(mc_results["summary"], " production", "Production (Confidence Bands)", "Units Produced")
            else:
                fig_inv = _make_sweep_chart(mc_results, " inventory", "Inventory vs Parameter", "Inventory")
                fig_ful = _make_sweep_chart(mc_results, " avg fulfillment rate", "Fulfillment Rate vs Parameter", "Rate")
                fig_prod = _make_sweep_chart(mc_results, " production", "Production vs Parameter", "Units Produced")

            fig_box = _make_boxplot(mc_results)

            total_runs = len(mc_results["all_runs"])
            status = f"Analysis complete. {total_runs} total runs, {periods} periods each."
            if mode == "sweep":
                status += f" Swept {sweep_param} across {len(sweep_values)} values."

            return (
                status,
                {"display": "block"},
                {"display": "inline-block"},
                "done",  # placeholder — actual data too large for store, use callback chain
                fig_inv,
                fig_ful,
                fig_prod,
                fig_box,
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
                error_msg,
                {"display": "none"},
                {"display": "none"},
                None,
                empty_fig, empty_fig, empty_fig, empty_fig,
            )

    # ── Download MC results ──────────────────────────────────────────────
    @app.callback(
        Output("download-mc-results", "data"),
        Input("btn-download-mc", "n_clicks"),
        State("cytoscape-graph", "elements"),
        State("store-disruptions", "data"),
        State("mc-mode", "value"),
        State("mc-n-runs", "value"),
        State("mc-periods", "value"),
        State("mc-seed", "value"),
        State("mc-sweep-param", "value"),
        State("mc-sweep-agent", "value"),
        State("mc-sweep-min", "value"),
        State("mc-sweep-max", "value"),
        State("mc-sweep-steps", "value"),
        prevent_initial_call=True,
    )
    def download_mc_results(
        n_clicks, elements, disruptions,
        mode, n_runs, periods, seed,
        sweep_param, sweep_agent,
        sweep_min, sweep_max, sweep_steps,
    ):
        if not n_clicks:
            return no_update

        try:
            n_runs = int(n_runs) if n_runs else 20
            periods = int(periods) if periods else 200
            seed = int(seed) if seed else 0
            disruptions = disruptions or []

            sweep_values = None
            if mode == "sweep":
                sweep_min = float(sweep_min) if sweep_min is not None else 50
                sweep_max = float(sweep_max) if sweep_max is not None else 300
                sweep_steps = int(sweep_steps) if sweep_steps else 5

                param_info = SWEEP_PARAMETERS.get(sweep_param, {})
                if param_info.get("dtype") == int:
                    sweep_values = [int(v) for v in np.linspace(sweep_min, sweep_max, sweep_steps)]
                else:
                    sweep_values = list(np.linspace(sweep_min, sweep_max, sweep_steps))

            # Re-run to get the data for export
            mc_results = run_monte_carlo(
                elements=elements,
                sim_periods=periods,
                n_runs=n_runs,
                disruptions=disruptions or None,
                mode=mode,
                sweep_param=sweep_param if mode == "sweep" else None,
                sweep_values=sweep_values,
                target_agent_id=sweep_agent if mode == "sweep" else "__all__",
                seed_start=seed,
                n_workers=1,
            )

            excel_bytes = mc_results_to_excel(mc_results)
            return dcc.send_bytes(lambda: excel_bytes, filename="mc_results.xlsx")

        except Exception:
            return no_update
