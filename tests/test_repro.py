"""Reproducibility test suite for SlotIQ.

Validates that fixed seed 42 guarantees bit-for-bit deterministic reproducibility:
- Identical synthetic data generation across runs
- Identical Hungarian optimal bipartite matching assignments
- Identical Forecast + Affinity local swap trajectory
"""

import pytest
import pandas as pd
from pathlib import Path

from engine.data_gen import generate_locations, generate_products, generate_orders
from engine.strategies import strategy_optimal_hungarian, strategy_forecast_affinity
from engine.metrics import calculate_metrics
from engine.stress_benchmark import run_constrained_benchmark

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_data_generation_reproducibility():
    """Verify that seed 42 produces strictly identical DataFrames across runs."""
    locs_run1 = generate_locations(320)
    locs_run2 = generate_locations(320)
    pd.testing.assert_frame_equal(locs_run1, locs_run2)

    prods_run1 = generate_products(locs_run1, 300)
    prods_run2 = generate_products(locs_run2, 300)
    pd.testing.assert_frame_equal(prods_run1, prods_run2)

    orders_run1 = generate_orders(prods_run1, 5000)
    orders_run2 = generate_orders(prods_run2, 5000)
    pd.testing.assert_frame_equal(orders_run1, orders_run2)


def test_strategy_deterministic_output():
    """Verify that Hungarian optimization and local search are fully deterministic."""
    prods = pd.read_csv(DATA_DIR / "products.csv")
    locs = pd.read_csv(DATA_DIR / "locations.csv")
    orders = pd.read_csv(DATA_DIR / "orders.csv")

    plan1 = strategy_optimal_hungarian(prods, locs)
    plan2 = strategy_optimal_hungarian(prods, locs)
    assert plan1 == plan2, "Hungarian bipartite assignment must be deterministic"

    m1 = calculate_metrics(plan1, prods, locs)
    m2 = calculate_metrics(plan2, prods, locs)
    assert m1 == m2, "Metrics must match identically across repeated executions"

    aff_plan1 = strategy_forecast_affinity(prods, locs, orders)
    aff_plan2 = strategy_forecast_affinity(prods, locs, orders)
    assert aff_plan1 == aff_plan2, "Forecast + Affinity plan must be deterministic"
    baseline = dict(zip(prods["product_id"], prods["baseline_location_id"]))
    baseline_affinity = calculate_metrics(baseline, prods, locs, orders_df=orders)["average_affinity_distance_m"]
    optimized_affinity = calculate_metrics(aff_plan1, prods, locs, orders_df=orders)["average_affinity_distance_m"]
    assert optimized_affinity < baseline_affinity


def test_hungarian_handles_tight_capacity_scenario():
    results = run_constrained_benchmark()
    greedy = results["ABC-Greedy"]
    hungarian = results["Hungarian"]
    assert hungarian["assigned"] == hungarian["products"]
    assert hungarian["metrics"]["feasibility_pct"] == 100.0
    assert greedy["assigned"] < greedy["products"]
