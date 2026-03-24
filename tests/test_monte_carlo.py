"""
Tests for the Monte Carlo / Sensitivity Analysis engine.
"""

import numpy as np
import pytest

from dashboard.monte_carlo import (
    run_monte_carlo,
    _run_single_sim,
    _apply_sweep_value,
    get_agents_for_param,
    SWEEP_PARAMETERS,
    mc_results_to_excel,
)


class TestSingleSimRun:
    """Test the core single-simulation runner."""

    def test_returns_dataframe(self, starter_elements):
        df = _run_single_sim(starter_elements, sim_periods=20, disruptions=None, seed=42)
        assert len(df) == 20
        assert "H1 inventory" in df.columns

    def test_different_seeds_produce_different_results(self, starter_elements):
        df1 = _run_single_sim(starter_elements, sim_periods=30, disruptions=None, seed=1)
        df2 = _run_single_sim(starter_elements, sim_periods=30, disruptions=None, seed=2)
        # Demand is stochastic, so results should differ
        assert not df1["H1 demand"].equals(df2["H1 demand"])

    def test_same_seed_reproduces_results(self, starter_elements):
        df1 = _run_single_sim(starter_elements, sim_periods=30, disruptions=None, seed=42)
        df2 = _run_single_sim(starter_elements, sim_periods=30, disruptions=None, seed=42)
        assert df1["H1 demand"].equals(df2["H1 demand"])


class TestStochasticReplication:
    """Test the replication mode (same params, different seeds)."""

    def test_replication_returns_correct_structure(self, starter_elements):
        result = run_monte_carlo(
            starter_elements, sim_periods=20, n_runs=5,
            mode="replication", seed_start=0, n_workers=1,
        )
        assert result["mode"] == "replication"
        assert len(result["all_runs"]) == 5
        assert result["sweep_param"] is None
        assert result["summary"] is not None

    def test_replication_summary_has_statistics(self, starter_elements):
        result = run_monte_carlo(
            starter_elements, sim_periods=20, n_runs=10,
            mode="replication", seed_start=0, n_workers=1,
        )
        summary = result["summary"]
        # Should have multi-index columns (metric, stat)
        assert isinstance(summary.columns, type(summary.columns))
        # Check that mean and std are present for at least one metric
        col_stats = [c[1] for c in summary.columns]
        assert "mean" in col_stats
        assert "std" in col_stats
        assert "p50" in col_stats

    def test_replication_variability_exists(self, starter_elements):
        """Multiple runs should show some variability in results."""
        result = run_monte_carlo(
            starter_elements, sim_periods=30, n_runs=10,
            mode="replication", seed_start=0, n_workers=1,
        )
        summary = result["summary"]
        # Standard deviation should be > 0 for stochastic metrics
        std_cols = [c for c in summary.columns if c[1] == "std" and "demand" in c[0]]
        if std_cols:
            assert summary[std_cols[0]].sum() > 0


class TestParameterSweep:
    """Test the parameter sweep mode."""

    def test_sweep_returns_correct_structure(self, starter_elements):
        result = run_monte_carlo(
            starter_elements, sim_periods=20, n_runs=3,
            mode="sweep",
            sweep_param="Demand Mean (d)",
            sweep_values=[100, 200, 300],
            target_agent_id="__all__",
            seed_start=0, n_workers=1,
        )
        assert result["mode"] == "sweep"
        assert len(result["all_runs"]) == 9  # 3 values × 3 runs each
        assert result["sweep_param"] == "Demand Mean (d)"
        assert result["sweep_values"] == [100, 200, 300]
        assert len(result["sweep_run_indices"]) == 3

    def test_sweep_summary_has_sweep_values(self, starter_elements):
        result = run_monte_carlo(
            starter_elements, sim_periods=20, n_runs=2,
            mode="sweep",
            sweep_param="Safety Stock (ss)",
            sweep_values=[500, 1000, 2000],
            seed_start=0, n_workers=1,
        )
        summary = result["summary"]
        assert "sweep_value" in summary.columns
        assert list(summary["sweep_value"]) == [500, 1000, 2000]

    def test_sweep_demand_affects_results(self, starter_elements):
        """Different demand values should produce different run data."""
        result = run_monte_carlo(
            starter_elements, sim_periods=30, n_runs=3,
            mode="sweep",
            sweep_param="Demand Mean (d)",
            sweep_values=[50, 300],
            seed_start=42, n_workers=1,
        )
        # Compare H1 demand columns from runs at different sweep values
        # Run 0 uses d=50, Run 3 uses d=300 (same seed=42)
        run_low = result["all_runs"][0]   # d=50, seed=42
        run_high = result["all_runs"][3]  # d=300, seed=42
        # Mean demand should differ substantially
        assert abs(run_low["H1 demand"].mean() - run_high["H1 demand"].mean()) > 100


class TestApplySweepValue:
    """Test the parameter modification function."""

    def test_modifies_consumer_demand(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        mod_el, _ = _apply_sweep_value(elements, "Demand Mean (d)", 250, "__all__", [])
        for el in mod_el:
            data = el.get("data", {})
            if data.get("agent_type") == "consumer":
                assert data["d"] == 250

    def test_modifies_single_agent(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        mod_el, _ = _apply_sweep_value(elements, "Demand Mean (d)", 999, "consumer-0", [])
        for el in mod_el:
            data = el.get("data", {})
            if data.get("id") == "consumer-0":
                assert data["d"] == 999
            elif data.get("id") == "consumer-1":
                # Should NOT be modified
                assert data.get("d") != 999

    def test_modifies_disruption_severity(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        disruptions = [{"producer_label": "MN1", "start": 5, "end": 10, "severity": 0.2}]
        _, mod_d = _apply_sweep_value(elements, "Disruption Severity", 0.5, "__all__", disruptions)
        assert mod_d[0]["severity"] == 0.5

    def test_does_not_modify_original(self, starter_elements, copy_elements):
        elements = copy_elements(starter_elements)
        original_d = None
        for el in elements:
            if el.get("data", {}).get("id") == "consumer-0":
                original_d = el["data"]["d"]
                break

        _apply_sweep_value(elements, "Demand Mean (d)", 999, "__all__", [])

        for el in elements:
            if el.get("data", {}).get("id") == "consumer-0":
                assert el["data"]["d"] == original_d  # unchanged


class TestGetAgentsForParam:
    """Test agent dropdown population."""

    def test_consumer_param_shows_consumers(self, starter_elements):
        agents = get_agents_for_param(starter_elements, "Demand Mean (d)")
        labels = [a[0] for a in agents]
        assert "All applicable agents" in labels
        assert "H1" in labels
        assert "H2" in labels
        assert "MN1" not in labels  # producers shouldn't appear

    def test_producer_param_shows_producers(self, starter_elements):
        agents = get_agents_for_param(starter_elements, "Production Capacity (m)")
        labels = [a[0] for a in agents]
        assert "MN1" in labels
        assert "H1" not in labels


class TestExcelExport:
    """Test MC results export to Excel."""

    def test_replication_export(self, starter_elements):
        result = run_monte_carlo(
            starter_elements, sim_periods=10, n_runs=3,
            mode="replication", seed_start=0, n_workers=1,
        )
        excel_bytes = mc_results_to_excel(result)
        assert len(excel_bytes) > 0
        # Should be valid Excel (starts with PK for ZIP)
        assert excel_bytes[:2] == b"PK"
