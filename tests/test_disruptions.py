"""
Tests for disruption mechanics.

Verifies that disruption events correctly modify producer capacity,
handle overlapping disruptions, and that severity semantics are correct
(lower severity value = MORE severe = less remaining capacity).
"""

import numpy as np
import pytest

from dashboard.graph_to_config import build_simulation_from_graph


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run_with_disruptions(starter_elements, disruptions, periods=20, seed=42):
    """Build and run a simulation with given disruptions, return the simulation."""
    np.random.seed(seed)
    sim = build_simulation_from_graph(starter_elements, sim_periods=periods, disruptions=disruptions)
    sim.run()
    return sim


# ── Single disruption tests ──────────────────────────────────────────────────

class TestSingleDisruption:
    """Tests for a single disruption event on one producer."""

    def test_capacity_reduced_during_disruption(self, starter_elements):
        """During disruption, production_max = original × severity."""
        disruptions = [{"producer_label": "MN1", "start": 5, "end": 10, "severity": 0.2}]
        sim = build_simulation_from_graph(starter_elements, sim_periods=15, disruptions=disruptions)

        original_max = sim.original_production_max[0]  # 800

        # Run to period 5 (disruption starts)
        for t in range(6):
            sim.enable_disruption(t)

        # At t=5, disruption is active (start <= 5 < end=10)
        assert sim.producers[0].production_max == pytest.approx(original_max * 0.2)

    def test_capacity_recovers_after_disruption(self, starter_elements):
        """After disruption ends, production_max returns to original."""
        disruptions = [{"producer_label": "MN1", "start": 5, "end": 10, "severity": 0.2}]
        sim = _run_with_disruptions(starter_elements, disruptions, periods=15)

        original_max = sim.original_production_max[0]
        # After period 10+ (disruption ended), capacity should be restored
        assert sim.producers[0].production_max == original_max

    def test_no_disruption_baseline(self, starter_elements):
        """Without disruptions, production_max stays at original throughout."""
        sim = _run_with_disruptions(starter_elements, disruptions=None, periods=20)
        assert sim.producers[0].production_max == sim.original_production_max[0]


# ── Severity ordering ────────────────────────────────────────────────────────

class TestSeverityOrdering:
    """Verify that lower severity = more severe (less production).

    This was the user's original question: severity 0.2 should produce LESS
    than severity 0.4 because 0.2 means 20% of normal capacity remaining.
    """

    def test_severity_02_produces_less_than_04(self, starter_elements, copy_elements):
        """Severity 0.2 (20% capacity) should yield less total production than 0.4 (40%)."""
        # Run with severity 0.2
        el_02 = copy_elements(starter_elements)
        disruptions_02 = [{"producer_label": "MN1", "start": 5, "end": 15, "severity": 0.2}]
        sim_02 = _run_with_disruptions(el_02, disruptions_02, periods=20, seed=42)
        total_prod_02 = sum(sim_02.producers[0].h_production_observed)

        # Run with severity 0.4
        el_04 = copy_elements(starter_elements)
        disruptions_04 = [{"producer_label": "MN1", "start": 5, "end": 15, "severity": 0.4}]
        sim_04 = _run_with_disruptions(el_04, disruptions_04, periods=20, seed=42)
        total_prod_04 = sum(sim_04.producers[0].h_production_observed)

        assert total_prod_02 < total_prod_04, (
            f"Severity 0.2 should produce less than 0.4: "
            f"got {total_prod_02:.0f} vs {total_prod_04:.0f}"
        )

    @pytest.mark.parametrize("severity", [0.1, 0.2, 0.4, 0.6, 0.8, 1.0])
    def test_capacity_matches_severity_value(self, starter_elements, copy_elements, severity):
        """production_max during disruption should equal original × severity."""
        elements = copy_elements(starter_elements)
        disruptions = [{"producer_label": "MN1", "start": 2, "end": 8, "severity": severity}]
        sim = build_simulation_from_graph(elements, sim_periods=10, disruptions=disruptions)

        original_max = sim.original_production_max[0]

        # Advance to a period where disruption is active
        for t in range(5):
            sim.enable_disruption(t)

        assert sim.producers[0].production_max == pytest.approx(original_max * severity)


# ── Overlapping disruptions ──────────────────────────────────────────────────

class TestOverlappingDisruptions:
    """Tests for multiple disruptions on the same producer with overlapping time ranges."""

    def test_overlapping_uses_minimum_severity(self, starter_elements):
        """When two disruptions overlap, the most restrictive (min severity) wins."""
        disruptions = [
            {"producer_label": "MN1", "start": 3, "end": 12, "severity": 0.4},
            {"producer_label": "MN1", "start": 6, "end": 15, "severity": 0.2},
        ]
        sim = build_simulation_from_graph(starter_elements, sim_periods=20, disruptions=disruptions)
        original_max = sim.original_production_max[0]

        # t=5: only first disruption active → severity 0.4
        for t in range(6):
            sim.enable_disruption(t)
        assert sim.producers[0].production_max == pytest.approx(original_max * 0.4)

        # t=8: both active → min(0.4, 0.2) = 0.2
        for t in range(6, 9):
            sim.enable_disruption(t)
        assert sim.producers[0].production_max == pytest.approx(original_max * 0.2)

    def test_first_ending_doesnt_cancel_second(self, starter_elements):
        """When the first disruption ends, the second should remain active."""
        disruptions = [
            {"producer_label": "MN1", "start": 3, "end": 10, "severity": 0.4},
            {"producer_label": "MN1", "start": 5, "end": 15, "severity": 0.3},
        ]
        sim = build_simulation_from_graph(starter_elements, sim_periods=20, disruptions=disruptions)
        original_max = sim.original_production_max[0]

        # t=12: first ended (end=10), second still active → severity 0.3
        for t in range(13):
            sim.enable_disruption(t)
        assert sim.producers[0].production_max == pytest.approx(original_max * 0.3)

        # t=16: both ended → full capacity
        for t in range(13, 17):
            sim.enable_disruption(t)
        assert sim.producers[0].production_max == original_max


# ── Sequential disruptions ───────────────────────────────────────────────────

class TestSequentialDisruptions:
    """Tests for non-overlapping disruptions on the same producer."""

    def test_sequential_both_apply(self, starter_elements):
        """Two non-overlapping disruptions each apply their own severity."""
        disruptions = [
            {"producer_label": "MN1", "start": 2, "end": 5, "severity": 0.2},
            {"producer_label": "MN1", "start": 8, "end": 12, "severity": 0.5},
        ]
        sim = build_simulation_from_graph(starter_elements, sim_periods=15, disruptions=disruptions)
        original_max = sim.original_production_max[0]

        # t=3: first disruption active
        for t in range(4):
            sim.enable_disruption(t)
        assert sim.producers[0].production_max == pytest.approx(original_max * 0.2)

        # t=6: gap between disruptions → full capacity
        for t in range(4, 7):
            sim.enable_disruption(t)
        assert sim.producers[0].production_max == original_max

        # t=10: second disruption active
        for t in range(7, 11):
            sim.enable_disruption(t)
        assert sim.producers[0].production_max == pytest.approx(original_max * 0.5)


# ── Multi-producer disruptions ───────────────────────────────────────────────

class TestMultiProducerDisruptions:
    """Tests for disruptions on different producers (should be independent)."""

    def test_different_producers_independent(self, main_py_elements):
        """Disruptions on MN1 and MN2 should not affect each other."""
        disruptions = [
            {"producer_label": "MN1", "start": 3, "end": 10, "severity": 0.2},
            {"producer_label": "MN2", "start": 3, "end": 10, "severity": 0.6},
        ]
        sim = build_simulation_from_graph(main_py_elements, sim_periods=15, disruptions=disruptions)

        original_mn1 = sim.original_production_max[0]
        original_mn2 = sim.original_production_max[1]

        # t=5: both active with their own severities
        for t in range(6):
            sim.enable_disruption(t)

        assert sim.producers[0].production_max == pytest.approx(original_mn1 * 0.2)
        assert sim.producers[1].production_max == pytest.approx(original_mn2 * 0.6)

    def test_one_producer_disrupted_other_unaffected(self, main_py_elements):
        """Disrupting MN1 should leave MN2 at full capacity."""
        disruptions = [{"producer_label": "MN1", "start": 3, "end": 10, "severity": 0.2}]
        sim = build_simulation_from_graph(main_py_elements, sim_periods=15, disruptions=disruptions)

        original_mn2 = sim.original_production_max[1]

        for t in range(6):
            sim.enable_disruption(t)

        assert sim.producers[1].production_max == original_mn2
