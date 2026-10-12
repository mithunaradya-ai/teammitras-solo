"""Automated constraint satisfaction test suite for SlotIQ.

Validates that all optimization strategies enforce:
- Zero capacity and volume violations
- Zero dimensional box clearance violations
- Strict special handling integrity (Zone D routing)
- Zero assignments to unavailable/disabled locations
- 100% overall feasibility score
"""

import pytest
import pandas as pd
from pathlib import Path

from engine.strategies import (
    strategy_abc_greedy, strategy_optimal_hungarian, strategy_forecast_affinity
)
from engine.metrics import (
    calculate_metrics, check_assignment_feasibility, is_dimension_feasible, is_handling_feasible
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def clean_datasets():
    """Load benchmark clean datasets."""
    p = pd.read_csv(DATA_DIR / "products.csv")
    l = pd.read_csv(DATA_DIR / "locations.csv")
    o = pd.read_csv(DATA_DIR / "orders.csv")
    return p, l, o


@pytest.mark.parametrize("strat_fn", [
    strategy_abc_greedy,
    strategy_optimal_hungarian
])
def test_strategy_constraints(strat_fn, clean_datasets):
    """Assert zero capacity/size/handling violations and 100% feasibility on standard optimizers."""
    prods, locs, _ = clean_datasets
    plan = strat_fn(prods, locs)
    
    loc_dict = locs.set_index("location_id").to_dict(orient="index")
    prod_dict = prods.set_index("product_id").to_dict(orient="index")

    # 1. Assert all 300 products assigned
    assert len(plan) == len(prods), "All products must be assigned"

    # 2. Assert unique location slots
    assigned_locs = list(plan.values())
    assert len(assigned_locs) == len(set(assigned_locs)), "No two products may share the same slot in 1-to-1 matching"

    # 3. Item-by-item constraint audit
    for p_id, loc_id in plan.items():
        p_row = pd.Series(prod_dict[p_id])
        l_row = pd.Series(loc_dict[loc_id])

        # Available
        assert l_row["available"] == 1, f"Product {p_id} assigned to unavailable location {loc_id}"

        # Dimension & Volume clearance
        assert is_dimension_feasible(p_row, l_row), (
            f"Capacity violation: {p_id} (vol {p_row['volume']}) exceeds {loc_id} (vol {l_row['capacity_volume']})"
        )

        # Special handling zone match
        assert is_handling_feasible(p_row, l_row), (
            f"Special handling breach: {p_id} requires special handling but {loc_id} lacks support"
        )

    # 4. Metric feasibility assert
    metrics = calculate_metrics(plan, prods, locs)
    assert metrics["feasibility_pct"] == 100.0, "Optimizer must achieve 100.0% feasibility"


def test_forecast_affinity_constraints(clean_datasets):
    """Verify that the AI Differentiator strategy preserves 100% feasibility after affinity swaps."""
    prods, locs, orders = clean_datasets
    plan = strategy_forecast_affinity(prods, locs, orders)

    loc_dict = locs.set_index("location_id").to_dict(orient="index")
    prod_dict = prods.set_index("product_id").to_dict(orient="index")

    for p_id, loc_id in plan.items():
        p_row = pd.Series(prod_dict[p_id])
        l_row = pd.Series(loc_dict[loc_id])
        valid, reason = check_assignment_feasibility(p_row, l_row)
        assert valid, f"Affinity swap created infeasible placement for {p_id} at {loc_id}: {reason}"

    metrics = calculate_metrics(plan, prods, locs)
    assert metrics["feasibility_pct"] == 100.0


def test_affinity_distance_metric_uses_order_pairs(clean_datasets):
    prods, locs, orders = clean_datasets
    baseline = dict(zip(prods["product_id"], prods["baseline_location_id"]))
    metrics = calculate_metrics(baseline, prods, locs, orders_df=orders)
    assert metrics["average_affinity_distance_m"] > 0
