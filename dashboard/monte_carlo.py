"""
Monte Carlo / Sensitivity Analysis engine.

Runs multiple simulations with varied parameters and aggregates results.
Two modes:
  1. Stochastic Replication — same params, different random seeds
  2. Parameter Sweep — vary one parameter across a range

Does NOT modify any core simulation files.
"""

import copy
import io
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from dashboard.graph_to_config import build_simulation_from_graph, get_full_results


# ── Sweepable parameter definitions ─────────────────────────────────────────

SWEEP_PARAMETERS = {
    "Demand Mean (d)": {"key": "d", "agent_types": ["consumer"], "dtype": float},
    "Demand Std Dev (dstd)": {"key": "dstd", "agent_types": ["consumer"], "dtype": float},
    "Safety Stock (ss)": {"key": "ss", "agent_types": ["consumer", "transhipper", "producer"], "dtype": float},
    "Lead Time (l)": {"key": "l", "agent_types": ["transhipper", "producer"], "dtype": int},
    "Production Capacity (m)": {"key": "m", "agent_types": ["producer"], "dtype": float},
    "Production Lead Time (pl)": {"key": "pl", "agent_types": ["producer"], "dtype": int},
    "Disruption Severity": {"key": "severity", "agent_types": [], "dtype": float},
}


def get_sweep_param_options():
    """Return list of parameter names for the UI dropdown."""
    return list(SWEEP_PARAMETERS.keys())


def get_agents_for_param(elements, param_name):
    """Return list of (label, id) for agents that have this parameter."""
    param_info = SWEEP_PARAMETERS.get(param_name, {})
    agent_types = param_info.get("agent_types", [])

    agents = [("All applicable agents", "__all__")]
    for el in elements:
        data = el.get("data", {})
        if "source" in data:
            continue  # skip edges
        if data.get("agent_type") in agent_types:
            agents.append((data.get("label", data.get("id")), data.get("id")))
    return agents


# ── Core run function (called in subprocess) ─────────────────────────────────

def _run_single_sim(elements, sim_periods, disruptions, seed):
    """Run one simulation with a specific random seed. Returns a DataFrame."""
    np.random.seed(seed)

    # Suppress Simulation.run() print output
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        sim = build_simulation_from_graph(elements, sim_periods, disruptions or None)
        sim.run()
        df = get_full_results(sim)
    finally:
        sys.stdout = old_stdout

    return df


def _apply_sweep_value(elements, param_name, value, target_agent_id, disruptions):
    """
    Apply a sweep parameter value to the elements or disruptions.
    Returns (modified_elements, modified_disruptions).
    """
    elements = copy.deepcopy(elements)
    disruptions = copy.deepcopy(disruptions) if disruptions else []

    param_info = SWEEP_PARAMETERS[param_name]

    if param_name == "Disruption Severity":
        # Modify all disruption severities
        for d in disruptions:
            d["severity"] = float(value)
        return elements, disruptions

    key = param_info["key"]
    agent_types = param_info["agent_types"]
    dtype = param_info["dtype"]

    for el in elements:
        data = el.get("data", {})
        if "source" in data:
            continue  # skip edges
        if data.get("agent_type") not in agent_types:
            continue
        if target_agent_id != "__all__" and data.get("id") != target_agent_id:
            continue
        data[key] = dtype(value)

    return elements, disruptions


# ── Main Monte Carlo runner ──────────────────────────────────────────────────

def run_monte_carlo(
    elements,
    sim_periods,
    n_runs,
    disruptions=None,
    mode="replication",
    sweep_param=None,
    sweep_values=None,
    target_agent_id="__all__",
    seed_start=0,
    n_workers=1,
):
    """
    Run Monte Carlo analysis.

    Parameters
    ----------
    elements : list[dict]
        Base Cytoscape elements.
    sim_periods : int
        Periods per simulation run.
    n_runs : int
        Number of replications per parameter value.
    disruptions : list[dict] or None
        Base disruption events.
    mode : str
        "replication" for stochastic replication, "sweep" for parameter sweep.
    sweep_param : str or None
        Parameter name to sweep (from SWEEP_PARAMETERS keys).
    sweep_values : list or None
        Values to sweep through.
    target_agent_id : str
        Agent ID to apply sweep to, or "__all__" for all applicable agents.
    seed_start : int
        Starting random seed for reproducibility.
    n_workers : int
        Number of parallel workers.

    Returns
    -------
    dict with keys:
        "mode": str
        "all_runs": list[DataFrame]  (one per run)
        "summary": DataFrame  (aggregated statistics)
        "sweep_param": str or None
        "sweep_values": list or None
        "sweep_run_indices": list[list[int]] or None
            For sweep mode, which run indices correspond to each sweep value.
    """

    if mode == "replication":
        # Same parameters, different seeds
        all_dfs = _run_batch(
            elements, sim_periods, n_runs, disruptions, seed_start, n_workers
        )
        summary = _aggregate_runs(all_dfs)
        return {
            "mode": "replication",
            "all_runs": all_dfs,
            "summary": summary,
            "sweep_param": None,
            "sweep_values": None,
            "sweep_run_indices": None,
        }

    elif mode == "sweep":
        if not sweep_param or not sweep_values:
            raise ValueError("sweep_param and sweep_values required for sweep mode.")

        all_dfs = []
        sweep_run_indices = []

        for sv in sweep_values:
            mod_elements, mod_disruptions = _apply_sweep_value(
                elements, sweep_param, sv, target_agent_id, disruptions
            )
            batch_dfs = _run_batch(
                mod_elements, sim_periods, n_runs, mod_disruptions,
                seed_start, n_workers
            )
            start_idx = len(all_dfs)
            all_dfs.extend(batch_dfs)
            sweep_run_indices.append(list(range(start_idx, start_idx + len(batch_dfs))))

        summary = _aggregate_sweep(all_dfs, sweep_values, sweep_run_indices)
        return {
            "mode": "sweep",
            "all_runs": all_dfs,
            "summary": summary,
            "sweep_param": sweep_param,
            "sweep_values": sweep_values,
            "sweep_run_indices": sweep_run_indices,
        }

    else:
        raise ValueError(f"Unknown mode: {mode}")


def _run_batch(elements, sim_periods, n_runs, disruptions, seed_start, n_workers):
    """Run n_runs simulations, return list of DataFrames."""
    args_list = [
        (elements, sim_periods, disruptions, seed_start + i)
        for i in range(n_runs)
    ]

    if n_workers <= 1:
        # Sequential execution (simpler, avoids multiprocessing overhead for small runs)
        return [_run_single_sim(*args) for args in args_list]

    # Parallel execution
    results = [None] * n_runs
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        future_to_idx = {
            executor.submit(_run_single_sim, *args): i
            for i, args in enumerate(args_list)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()

    return results


# ── Aggregation ──────────────────────────────────────────────────────────────

def _aggregate_runs(dfs):
    """
    Aggregate a list of per-run DataFrames into summary statistics.

    Returns a DataFrame with multi-level columns:
    (metric_name, statistic) where statistic is one of
    mean, std, p5, p25, p50, p75, p95.
    """
    if not dfs:
        return pd.DataFrame()

    # Stack all runs: shape (n_runs, n_periods, n_metrics)
    metrics = dfs[0].columns.tolist()
    n_periods = len(dfs[0])

    records = {}
    for metric in metrics:
        values = np.array([df[metric].values for df in dfs if metric in df.columns])
        if len(values) == 0:
            continue
        records[(metric, "mean")] = np.mean(values, axis=0)
        records[(metric, "std")] = np.std(values, axis=0)
        records[(metric, "p5")] = np.percentile(values, 5, axis=0)
        records[(metric, "p25")] = np.percentile(values, 25, axis=0)
        records[(metric, "p50")] = np.percentile(values, 50, axis=0)
        records[(metric, "p75")] = np.percentile(values, 75, axis=0)
        records[(metric, "p95")] = np.percentile(values, 95, axis=0)

    summary = pd.DataFrame(records)
    summary.columns = pd.MultiIndex.from_tuples(summary.columns, names=["metric", "stat"])
    return summary


def _aggregate_sweep(all_dfs, sweep_values, sweep_run_indices):
    """
    Aggregate sweep results into a summary DataFrame.

    Returns a DataFrame with one row per sweep value and columns for
    key summary metrics (mean of final-period values across replications).
    """
    if not all_dfs:
        return pd.DataFrame()

    metrics = all_dfs[0].columns.tolist()
    rows = []

    for sv, indices in zip(sweep_values, sweep_run_indices):
        batch_dfs = [all_dfs[i] for i in indices]
        row = {"sweep_value": sv}

        for metric in metrics:
            final_values = [df[metric].iloc[-1] for df in batch_dfs if metric in df.columns]
            if final_values:
                row[f"{metric} (mean)"] = np.mean(final_values)
                row[f"{metric} (std)"] = np.std(final_values)

        rows.append(row)

    return pd.DataFrame(rows)


# ── Excel export ─────────────────────────────────────────────────────────────

def mc_results_to_excel(mc_results):
    """
    Export Monte Carlo results to an Excel file in memory.
    Returns bytes suitable for dcc.send_bytes.
    """
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Summary sheet
        summary = mc_results["summary"]
        if isinstance(summary.columns, pd.MultiIndex):
            # Flatten multi-index for Excel
            flat_summary = summary.copy()
            flat_summary.columns = [f"{m} ({s})" for m, s in summary.columns]
            flat_summary.to_excel(writer, sheet_name="Summary", index=True)
        else:
            summary.to_excel(writer, sheet_name="Summary", index=False)

        # Individual run sheets (cap at 20 to avoid huge files)
        max_sheets = min(20, len(mc_results["all_runs"]))
        for i in range(max_sheets):
            mc_results["all_runs"][i].to_excel(
                writer, sheet_name=f"Run {i+1}", index=False
            )

    buffer.seek(0)
    return buffer.read()
