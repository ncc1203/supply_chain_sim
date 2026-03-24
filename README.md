# Supply Chain Simulation Dashboard

A 3-echelon pharmaceutical supply chain simulator with an interactive visual dashboard. Build supply chain networks graphically, configure agent parameters, define disruption scenarios, and run simulations — all without writing code.

**Original simulation engine:** Noah Chicoine
**Dashboard:** Aidan Riordan

> **DISCLAIMER:**
> If using this simulator for research, please cite it using the repo link and the names above.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Dashboard Guide](#dashboard-guide)
  - [Tab 1: Network Builder](#tab-1-network-builder)
  - [Tab 2: Simulation Config](#tab-2-simulation-config)
  - [Tab 3: Results](#tab-3-results)
- [Running the Original Simulation (Code-Only)](#running-the-original-simulation-code-only)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)

---

## Overview

The simulation models a **3-echelon supply chain** with three types of agents:

| Agent Type | Dashboard Label | Role |
|------------|----------------|------|
| **Producer** | Manufacturer (MN) | Produces goods with configurable capacity and production lead time |
| **Transhipper** | Distributor (WS) | Receives from manufacturers, distributes to health centers |
| **Consumer** | Health Center (H) | Generates stochastic demand, orders from distributors |

Agents are connected in a directed graph: **Manufacturers → Distributors → Health Centers**. Each agent uses configurable ordering, production, and allocation policies. The simulator runs discrete time-step periods and tracks inventory, demand, fulfillment, backlog, and production across all agents.

The **dashboard** eliminates the need to manually write Python code with index arrays by providing a visual network builder that automatically translates the graph into correctly wired simulation objects.

---

## Installation

**Prerequisites:** Python 3.9+

```bash
# Clone the repository
git clone https://github.com/ncc1203/supply_chain_sim.git
cd supply_chain_sim

# Install dependencies
pip install dash dash-cytoscape pandas numpy openpyxl
```

If you only need the original code-based simulation (no dashboard):

```bash
pip install pandas numpy openpyxl
```

---

## Quick Start

```bash
python app.py
```

Open your browser to **http://127.0.0.1:8050**. You'll see the dashboard with a starter network (1 Manufacturer, 1 Distributor, 2 Health Centers) already loaded.

To run a simulation immediately:
1. Click the **Simulation Config** tab
2. Click **Run Simulation**
3. View results in the **Results** tab (the dashboard switches automatically)

---

## Dashboard Guide

### Tab 1: Network Builder

This is where you design your supply chain network visually.

#### Adding Agents

Click the buttons in the toolbar to add agents:
- **+ Manufacturer** — adds a Producer node (red square) in the left column
- **+ Distributor** — adds a Transhipper node (gold diamond) in the middle column
- **+ Health Center** — adds a Consumer node (blue circle) in the right column

New nodes are auto-positioned in their column. You can drag nodes to reposition them.

#### Connecting Agents

1. Click **Connect Mode: OFF** to toggle it to **Connect Mode: ON** (turns green)
2. Click the **source** node (it highlights with a green dashed border)
3. Click the **target** node — an edge is drawn between them

**Rules:**
- Connections are only allowed between **adjacent layers**: Manufacturer ↔ Distributor, or Distributor ↔ Health Center
- Direct Manufacturer → Health Center connections are rejected
- Duplicate edges are prevented

Click the Connect Mode button again to turn it off when done.

#### Editing Agent Parameters

Click any node (with Connect Mode OFF) to open the **Agent Properties** sidebar on the right. Parameters vary by agent type:

| Parameter | Consumer | Transhipper | Producer |
|-----------|----------|-------------|----------|
| Name/Label | Yes | Yes | Yes |
| Mean Demand (d) | Yes | — | — |
| Demand Std Dev (dstd) | Yes | — | — |
| Safety Stock (ss) | Yes | Yes | Yes |
| Lead Time (l) | — | Yes | Yes |
| Production Capacity (m) | — | — | Yes |
| Production Lead Time (pl) | — | — | Yes |
| Order Policy | Yes | Yes | — |
| Production Policy | — | — | Yes |
| Allocation Policy | — | Yes | Yes |

Click **Save Changes** after editing to update the node.

#### Other Toolbar Actions

- **Delete Selected** — removes the currently selected node and all its edges
- **Clear All** — removes all nodes and edges
- **Save Config** — downloads the current network as a JSON file
- **Load Config** — uploads a previously saved JSON file to restore a network
- **Load Preset** dropdown — loads a pre-built network:
  - *Starter (1×1×2)* — 1 Manufacturer, 1 Distributor, 2 Health Centers
  - *Main.py (2×3×6)* — the reference network from `main.py` with 2 Manufacturers, 3 Distributors, 6 Health Centers

### Tab 2: Simulation Config

#### Simulation Parameters

- **Number of periods** — how many time steps to simulate (default: 300)

#### Disruption Events

Model capacity disruptions on manufacturers:

1. Click **+ Add Disruption**
2. Fill in:
   - **Producer** — which manufacturer to disrupt (by label, e.g., "MN1")
   - **Start Period** — when the disruption begins
   - **End Period** — when normal capacity resumes
   - **Remaining Capacity** — fraction of normal capacity during disruption (0.2 = 20% of normal, lower = more severe)
3. Click **Run Simulation** to execute

Multiple disruptions can target different manufacturers or different time periods.

### Tab 3: Results

After running a simulation, five charts are displayed:

1. **Inventory Levels** — inventory over time for Health Centers and Manufacturers
2. **Demand vs Unmet Demand** — observed demand and unmet demand for each Health Center
3. **Fulfillment Rate** — average fulfillment rate per Health Center per period
4. **Backlog** — total backlog at Distributors and Manufacturers
5. **Production** — units produced per period by each Manufacturer

If disruptions were configured, they appear as **shaded red regions** on all charts.

- **Download Results (Excel)** — exports all data to an `.xlsx` file for further analysis

### Tab 4: Sensitivity Analysis

Run multiple simulations to measure variability or test parameter sensitivity.

#### Stochastic Replication Mode

Same network parameters, different random seeds. Measures natural variability from demand stochasticity.

- **Number of runs** — how many simulations to execute (default: 20)
- **Periods per run** — time steps per simulation (default: 200)
- **Starting seed** — for reproducibility (same seed = same results)

Results show **fan charts** with median lines and shaded 5th–95th / 25th–75th percentile confidence bands for inventory, fulfillment rate, and production. A **box plot** shows the distribution of final-period values across runs.

#### Parameter Sweep Mode

Vary one parameter across a range while keeping everything else fixed.

- **Parameter to sweep** — choose from: Demand Mean, Demand Std Dev, Safety Stock, Lead Time, Production Capacity, Production Lead Time, Disruption Severity
- **Apply to agent** — target all applicable agents or a specific one
- **Range** — min value, max value, and number of steps

Results show **sweep line charts** plotting the chosen parameter value (x-axis) against final-period metrics (y-axis) with error bars showing standard deviation across replications.

- **Download MC Results (Excel)** — exports summary statistics and individual run data (up to 20 sheets)

---

## Running the Original Simulation (Code-Only)

The original command-line simulation is still available and unmodified:

```bash
python main.py
```

This runs the reference 2×3×6 network with a disruption at period 100 and outputs `consumer_data.xlsx`.

Noah's original web interface is preserved as `app_old.py`:

```bash
python app_old.py
```

---

## Project Structure

```
supply_chain_sim/
│
│── Core simulation engine (NOT modified by dashboard)
│   ├── Consumer.py            # Health Center agent class
│   ├── Transhipper.py         # Distributor agent class
│   ├── Producer.py            # Manufacturer agent class
│   ├── Simulation.py          # Main simulation loop
│   ├── main.py                # Reference CLI entry point (2×3×6 network)
│   ├── Hospital.py            # Extended Consumer class
│   ├── Wholesaler.py          # Extended Transhipper class
│   ├── op_*.py                # Order policy functions
│   ├── pp_*.py                # Production policy functions
│   ├── ap_proportional.py     # Proportional allocation policy
│   └── ResultsGUI.py          # Original results visualization
│
├── Dashboard (new)
│   ├── app.py                 # Dashboard entry point
│   ├── app_old.py             # Noah's original app.py (renamed, preserved)
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── constants.py       # Colors, defaults, preset networks
│   │   ├── policy_registry.py # Maps policy names → function objects
│   │   ├── layout.py          # Dash layout (4 tabs, Cytoscape canvas)
│   │   ├── callbacks_network.py     # Network builder callbacks
│   │   ├── callbacks_simulation.py  # Run simulation + results charts
│   │   ├── callbacks_disruption.py  # Disruption event UI callbacks
│   │   ├── callbacks_monte_carlo.py # Sensitivity analysis callbacks + charts
│   │   ├── monte_carlo.py          # MC engine (replication + sweep)
│   │   └── graph_to_config.py       # Translates visual graph → Simulation objects
│   └── assets/
│       └── style.css          # Dashboard styling
│
├── Tests
│   ├── tests/conftest.py            # Shared pytest fixtures
│   ├── tests/test_graph_to_config.py  # Graph translation tests (24 tests)
│   ├── tests/test_disruptions.py      # Disruption mechanics tests (15 tests)
│   └── tests/test_monte_carlo.py      # Monte Carlo engine tests (16 tests)
│
├── .gitignore
└── README.md
```

### Key Design Decision: Zero Core Modifications

The dashboard wraps the existing simulation engine without modifying any core files. The visual graph is the **single source of truth** — edges are iterated once to populate both supplier and customer arrays simultaneously, guaranteeing bidirectional index consistency. This eliminates the error-prone manual index-matching required when using the simulation via code.

---

## Testing

Run the automated test suite (55 tests):

```bash
pip install pytest
python -m pytest tests/ -v
```

### Test coverage by module:

**`tests/test_graph_to_config.py`** — Graph translation & simulation building (24 tests)
- Index translation matches main.py reference exactly (4 tests)
- Simulation building and agent counts (5 tests)
- Parameter passthrough — custom values reach simulation objects (5 tests)
- Policy selection — dropdown names map to correct functions (3 tests)
- Edge validation — invalid networks rejected (3 tests)
- Results extraction — DataFrame has expected columns (4 tests)

**`tests/test_disruptions.py`** — Disruption mechanics (15 tests)
- Single disruption reduces capacity and recovers correctly
- Severity ordering: 0.2 produces LESS than 0.4 (lower = more severe)
- Parametrized test across 6 severity values
- Overlapping disruptions on same producer → minimum severity wins
- First disruption ending doesn't cancel a still-active second disruption
- Sequential (non-overlapping) disruptions each apply correctly
- Different producers disrupted independently

**`tests/test_monte_carlo.py`** — Monte Carlo engine (16 tests)
- Single sim: reproducibility (same seed = same results), variability (different seeds ≠ same results)
- Stochastic replication: correct structure, summary statistics, variability detection
- Parameter sweep: correct structure, sweep values in summary, demand changes affect results
- Sweep value application: modifies correct agents, leaves others unchanged
- Agent dropdown population based on parameter type
- Excel export produces valid file

---

## Contributing

1. **Do not modify core simulation files** — `Consumer.py`, `Transhipper.py`, `Producer.py`, `Simulation.py`, `main.py`, policy files (`op_*.py`, `pp_*.py`, `ap_proportional.py`), `Hospital.py`, `Wholesaler.py`, and `ResultsGUI.py` must remain unchanged.
2. All new features should be added in the `dashboard/` package or as new files.
3. Run the test suite before submitting changes: `python -m pytest test_graph_to_config.py -v`
4. Follow existing code style (PEP 8, docstrings on all public functions).

---

## Available Policies

### Order Policies (Consumers & Distributors)
- **Base Stock (All First)** — orders from first available supplier
- **Base Stock (Even Split)** — splits orders evenly across suppliers
- **Base Stock FR (All First)** — orders based on fulfillment rate, first supplier priority
- **Constant (All First)** — constant order quantity, first supplier
- **Constant (Even Split)** — constant order quantity, split evenly

### Production Policies (Manufacturers)
- **Base Stock** — produce to reach base stock level
- **Maximum Capacity** — always produce at maximum capacity

### Allocation Policies (Distributors & Manufacturers)
- **Proportional** — allocate available inventory proportionally to demand
