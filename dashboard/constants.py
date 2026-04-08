"""
Default values, color palette, and starter presets for the dashboard.
"""

# ── Colour palette (matches existing assets/style.css) ──────────────────────
RED = "#C8102E"
GOLD = "#C8A978"
BLACK = "#1A1A1A"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#F5F5F5"
DARK_GRAY = "#555555"

# Node colours by agent type
NODE_COLORS = {
    "producer": RED,
    "transhipper": GOLD,
    "consumer": "#6C8EBF",  # Soft blue for consumers
}

# ── Column x-positions for the 3-layer layout ───────────────────────────────
COLUMN_X = {
    "producer": 100,
    "transhipper": 400,
    "consumer": 700,
}
COLUMN_LABELS = {
    "producer": "Manufacturers",
    "transhipper": "Distributors",
    "consumer": "Health Centers",
}
CANVAS_HEIGHT = "600px"
CANVAS_WIDTH = "100%"

# Vertical spacing between nodes in the same column
NODE_Y_START = 80
NODE_Y_SPACING = 120

# ── Default parameters per agent type ────────────────────────────────────────
CONSUMER_DEFAULTS = {
    "d": 150,
    "dstd": 10,
    "ss": 1000,
    "order_policy": "Base Stock FR (All First)",
}

TRANSHIPPER_DEFAULTS = {
    "ss": 8000,
    "l": 2,
    "order_policy": "Base Stock FR (All First)",
    "allocation_policy": "Proportional",
}

PRODUCER_DEFAULTS = {
    "ss": 10000,
    "m": 800,
    "l": 2,
    "pl": 2,
    "production_policy": "Base Stock",
    "allocation_policy": "Proportional",
}

# ── Starter preset: 1 Producer × 1 Transhipper × 2 Consumers ───────────────
def get_starter_preset():
    """Return Cytoscape elements for the starter 1×1×2 network."""
    nodes = [
        {
            "data": {
                "id": "producer-0",
                "label": "MN1",
                "agent_type": "producer",
                "agent_num": 0,
                **PRODUCER_DEFAULTS,
            },
            "position": {"x": COLUMN_X["producer"], "y": NODE_Y_START},
        },
        {
            "data": {
                "id": "transhipper-0",
                "label": "WS1",
                "agent_type": "transhipper",
                "agent_num": 0,
                **TRANSHIPPER_DEFAULTS,
            },
            "position": {"x": COLUMN_X["transhipper"], "y": NODE_Y_START},
        },
        {
            "data": {
                "id": "consumer-0",
                "label": "H1",
                "agent_type": "consumer",
                "agent_num": 0,
                **CONSUMER_DEFAULTS,
            },
            "position": {"x": COLUMN_X["consumer"], "y": NODE_Y_START},
        },
        {
            "data": {
                "id": "consumer-1",
                "label": "H2",
                "agent_type": "consumer",
                "agent_num": 1,
                **CONSUMER_DEFAULTS,
            },
            "position": {"x": COLUMN_X["consumer"], "y": NODE_Y_START + NODE_Y_SPACING},
        },
    ]

    edges = [
        {"data": {"source": "producer-0", "target": "transhipper-0", "id": "edge-producer-0-transhipper-0"}},
        {"data": {"source": "transhipper-0", "target": "consumer-0", "id": "edge-transhipper-0-consumer-0"}},
        {"data": {"source": "transhipper-0", "target": "consumer-1", "id": "edge-transhipper-0-consumer-1"}},
    ]

    return nodes + edges


def get_main_py_preset():
    """Return Cytoscape elements matching main.py's 2×3×6 network."""
    def _p(x, y):
        return {"x": x, "y": y}

    nodes = [
        # Producers
        {"data": {"id": "producer-0", "label": "MN1", "agent_type": "producer", "agent_num": 0,
                  **PRODUCER_DEFAULTS}, "position": _p(COLUMN_X["producer"], NODE_Y_START)},
        {"data": {"id": "producer-1", "label": "MN2", "agent_type": "producer", "agent_num": 1,
                  **PRODUCER_DEFAULTS}, "position": _p(COLUMN_X["producer"], NODE_Y_START + NODE_Y_SPACING)},
        # Transhippers
        {"data": {"id": "transhipper-0", "label": "WS1", "agent_type": "transhipper", "agent_num": 0,
                  **TRANSHIPPER_DEFAULTS}, "position": _p(COLUMN_X["transhipper"], NODE_Y_START)},
        {"data": {"id": "transhipper-1", "label": "WS2", "agent_type": "transhipper", "agent_num": 1,
                  **TRANSHIPPER_DEFAULTS}, "position": _p(COLUMN_X["transhipper"], NODE_Y_START + NODE_Y_SPACING)},
        {"data": {"id": "transhipper-2", "label": "WS3", "agent_type": "transhipper", "agent_num": 2,
                  **TRANSHIPPER_DEFAULTS}, "position": _p(COLUMN_X["transhipper"], NODE_Y_START + 2 * NODE_Y_SPACING)},
        # Consumers
        {"data": {"id": "consumer-0", "label": "H1", "agent_type": "consumer", "agent_num": 0,
                  "d": 150, "dstd": 10, "ss": 1000, "order_policy": "Base Stock FR (All First)"},
         "position": _p(COLUMN_X["consumer"], NODE_Y_START)},
        {"data": {"id": "consumer-1", "label": "H2", "agent_type": "consumer", "agent_num": 1,
                  "d": 170, "dstd": 10, "ss": 1000, "order_policy": "Base Stock FR (All First)"},
         "position": _p(COLUMN_X["consumer"], NODE_Y_START + NODE_Y_SPACING)},
        {"data": {"id": "consumer-2", "label": "H3", "agent_type": "consumer", "agent_num": 2,
                  "d": 200, "dstd": 10, "ss": 1000, "order_policy": "Base Stock FR (All First)"},
         "position": _p(COLUMN_X["consumer"], NODE_Y_START + 2 * NODE_Y_SPACING)},
        {"data": {"id": "consumer-3", "label": "H4", "agent_type": "consumer", "agent_num": 3,
                  "d": 50, "dstd": 10, "ss": 1000, "order_policy": "Base Stock FR (All First)"},
         "position": _p(COLUMN_X["consumer"], NODE_Y_START + 3 * NODE_Y_SPACING)},
        {"data": {"id": "consumer-4", "label": "H5", "agent_type": "consumer", "agent_num": 4,
                  "d": 200, "dstd": 10, "ss": 1000, "order_policy": "Base Stock FR (All First)"},
         "position": _p(COLUMN_X["consumer"], NODE_Y_START + 4 * NODE_Y_SPACING)},
        {"data": {"id": "consumer-5", "label": "H6", "agent_type": "consumer", "agent_num": 5,
                  "d": 200, "dstd": 10, "ss": 1000, "order_policy": "Base Stock FR (All First)"},
         "position": _p(COLUMN_X["consumer"], NODE_Y_START + 5 * NODE_Y_SPACING)},
    ]

    edges = [
        # Producer → Transhipper
        {"data": {"source": "producer-0", "target": "transhipper-0", "id": "e-p0-t0"}},
        {"data": {"source": "producer-0", "target": "transhipper-1", "id": "e-p0-t1"}},
        {"data": {"source": "producer-1", "target": "transhipper-0", "id": "e-p1-t0"}},
        {"data": {"source": "producer-1", "target": "transhipper-2", "id": "e-p1-t2"}},
        # Transhipper → Consumer
        {"data": {"source": "transhipper-0", "target": "consumer-0", "id": "e-t0-c0"}},
        {"data": {"source": "transhipper-0", "target": "consumer-1", "id": "e-t0-c1"}},
        {"data": {"source": "transhipper-0", "target": "consumer-2", "id": "e-t0-c2"}},
        {"data": {"source": "transhipper-0", "target": "consumer-3", "id": "e-t0-c3"}},
        {"data": {"source": "transhipper-1", "target": "consumer-0", "id": "e-t1-c0"}},
        {"data": {"source": "transhipper-1", "target": "consumer-2", "id": "e-t1-c2"}},
        {"data": {"source": "transhipper-1", "target": "consumer-4", "id": "e-t1-c4"}},
        {"data": {"source": "transhipper-2", "target": "consumer-1", "id": "e-t2-c1"}},
        {"data": {"source": "transhipper-2", "target": "consumer-5", "id": "e-t2-c5"}},
    ]

    return nodes + edges
