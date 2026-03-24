"""
Callbacks for disruption event configuration.
Users add/remove disruption events that get passed to the simulation at run time.
"""

from dash import Input, Output, State, callback, ctx, html, dcc, no_update


def _render_disruption_row(idx, data=None):
    """Render a single disruption row with inputs."""
    data = data or {}
    return html.Div(
        id={"type": "disruption-row", "index": idx},
        className="disruption-row",
        style={
            "display": "flex", "gap": "8px", "alignItems": "center",
            "padding": "8px", "marginBottom": "6px",
            "background": "#f9f9f9", "borderRadius": "6px",
            "border": "1px solid rgba(0,0,0,0.06)",
        },
        children=[
            html.Div([
                html.Label("Producer", style={"fontSize": "11px", "display": "block"}),
                dcc.Input(
                    id={"type": "disruption-producer", "index": idx},
                    type="text",
                    value=data.get("producer_label", "MN1"),
                    placeholder="e.g. MN1",
                    style={"width": "70px", "padding": "4px", "fontSize": "13px"},
                ),
            ]),
            html.Div([
                html.Label("Start", style={"fontSize": "11px", "display": "block"}),
                dcc.Input(
                    id={"type": "disruption-start", "index": idx},
                    type="number",
                    value=data.get("start", 100),
                    min=0,
                    style={"width": "60px", "padding": "4px", "fontSize": "13px"},
                ),
            ]),
            html.Div([
                html.Label("End", style={"fontSize": "11px", "display": "block"}),
                dcc.Input(
                    id={"type": "disruption-end", "index": idx},
                    type="number",
                    value=data.get("end", 150),
                    min=0,
                    style={"width": "60px", "padding": "4px", "fontSize": "13px"},
                ),
            ]),
            html.Div([
                html.Label("Severity", style={"fontSize": "11px", "display": "block"}),
                dcc.Input(
                    id={"type": "disruption-severity", "index": idx},
                    type="number",
                    value=data.get("severity", 0.2),
                    min=0, max=1, step=0.05,
                    style={"width": "60px", "padding": "4px", "fontSize": "13px"},
                ),
            ]),
            html.Button(
                "X",
                id={"type": "disruption-delete", "index": idx},
                n_clicks=0,
                style={
                    "background": "#E53935", "color": "white", "border": "none",
                    "borderRadius": "4px", "padding": "4px 8px", "cursor": "pointer",
                    "marginTop": "14px",
                },
            ),
        ],
    )


def register_disruption_callbacks(app):
    """Register disruption-related callbacks."""

    # ── Add disruption row ──────────────────────────────────────────────────
    @app.callback(
        Output("disruption-rows", "children", allow_duplicate=True),
        Output("store-disruptions", "data", allow_duplicate=True),
        Output("store-disruption-counter", "data", allow_duplicate=True),
        Input("btn-add-disruption", "n_clicks"),
        State("store-disruptions", "data"),
        State("store-disruption-counter", "data"),
        prevent_initial_call=True,
    )
    def add_disruption(n_clicks, disruptions, counter):
        if not n_clicks:
            return no_update, no_update, no_update

        new_disruption = {
            "id": counter,
            "producer_label": "MN1",
            "start": 100,
            "end": 150,
            "severity": 0.2,
        }
        disruptions = (disruptions or []) + [new_disruption]
        counter += 1

        rows = [_render_disruption_row(d["id"], d) for d in disruptions]
        return rows, disruptions, counter

    # ── Delete disruption row ───────────────────────────────────────────────
    # Using pattern-matching callbacks for dynamic delete buttons
    from dash import ALL, MATCH

    @app.callback(
        Output("disruption-rows", "children", allow_duplicate=True),
        Output("store-disruptions", "data", allow_duplicate=True),
        Input({"type": "disruption-delete", "index": ALL}, "n_clicks"),
        State("store-disruptions", "data"),
        prevent_initial_call=True,
    )
    def delete_disruption(all_clicks, disruptions):
        if not any(c and c > 0 for c in all_clicks):
            return no_update, no_update

        # Find which button was clicked
        triggered = ctx.triggered_id
        if triggered is None:
            return no_update, no_update

        delete_id = triggered["index"]
        disruptions = [d for d in (disruptions or []) if d["id"] != delete_id]

        rows = [_render_disruption_row(d["id"], d) for d in disruptions]
        return rows, disruptions

    # ── Sync disruption input values back to store ──────────────────────────
    @app.callback(
        Output("store-disruptions", "data"),
        Input({"type": "disruption-producer", "index": ALL}, "value"),
        Input({"type": "disruption-start", "index": ALL}, "value"),
        Input({"type": "disruption-end", "index": ALL}, "value"),
        Input({"type": "disruption-severity", "index": ALL}, "value"),
        State("store-disruptions", "data"),
        prevent_initial_call=True,
    )
    def sync_disruption_values(producers, starts, ends, severities, disruptions):
        if not disruptions:
            return no_update

        # Update each disruption with current input values
        for i, d in enumerate(disruptions):
            if i < len(producers) and producers[i] is not None:
                d["producer_label"] = producers[i]
            if i < len(starts) and starts[i] is not None:
                d["start"] = int(starts[i])
            if i < len(ends) and ends[i] is not None:
                d["end"] = int(ends[i])
            if i < len(severities) and severities[i] is not None:
                d["severity"] = float(severities[i])

        return disruptions
