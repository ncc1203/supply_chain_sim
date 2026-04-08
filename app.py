"""
Supply Chain Simulation Dashboard
Interactive visual network builder + simulation runner.

Usage:
    pip install dash dash-cytoscape pandas openpyxl
    python app.py

Then open http://127.0.0.1:8050 in your browser.
"""

from dash import Dash

from dashboard.layout import build_layout
from dashboard.callbacks_network import register_network_callbacks
from dashboard.callbacks_simulation import register_simulation_callbacks
from dashboard.callbacks_disruption import register_disruption_callbacks
from dashboard.callbacks_monte_carlo import register_monte_carlo_callbacks


# ── Create app ───────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    suppress_callback_exceptions=True,  # Needed for dynamic sidebar components
)
server = app.server

# ── Layout ───────────────────────────────────────────────────────────────────
app.layout = build_layout()

# ── Register callbacks ───────────────────────────────────────────────────────
register_network_callbacks(app)
register_simulation_callbacks(app)
register_disruption_callbacks(app)
register_monte_carlo_callbacks(app)


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=("RENDER" not in os.environ), host="0.0.0.0", port=port)
