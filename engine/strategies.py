"""Optimization strategies for SlotIQ warehouse slotting.

Implements standard benchmark and novel optimization strategies:
- baseline: original poor layout
- abc_greedy: ABC categorization assigning highest picks to nearest feasible slots
- optimal_hungarian: Minimum weight bipartite matching via Scipy linear_sum_assignment
- optimal_ilp: PuLP CBC integer linear programming for multi-item bin packing
- forecast_affinity: AI differentiator combining Holt exponential smoothing, Hungarian, and Lift local search
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
import pulp

# Allow running directly from engine/ or slotiq/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from slotiq.engine.metrics import calculate_metrics, check_assignment_feasibility
    from slotiq.engine.forecast import predict_next_week_demands
    from slotiq.engine.affinity import compute_affinity_lift, optimize_affinity_swaps
except ImportError:
    from metrics import calculate_metrics, check_assignment_feasibility
    from forecast import predict_next_week_demands
    from affinity import compute_affinity_lift, optimize_affinity_swaps

BIG_M = 1e8


def strategy_baseline(prods: pd.DataFrame, locs: pd.DataFrame) -> dict[str, str]:
    """Return the baseline warehouse assignment."""
    return dict(zip(prods["product_id"], prods["baseline_location_id"]))


def strategy_abc_greedy(prods: pd.DataFrame, locs: pd.DataFrame) -> dict[str, str]:
    """ABC classification assigning highest demand items to closest feasible slots."""
    sorted_prods = prods.sort_values("avg_weekly_demand", ascending=False)
    avail_locs = locs[locs["available"] == 1].sort_values("distance_to_door")
    
    assigned = {}
    occupied_locs = set()

    for _, p_row in sorted_prods.iterrows():
        p_id = p_row["product_id"]
        for _, l_row in avail_locs.iterrows():
            loc_id = l_row["location_id"]
            if loc_id in occupied_locs:
                continue
            is_valid, _ = check_assignment_feasibility(p_row, l_row)
            if is_valid:
                assigned[p_id] = loc_id
                occupied_locs.add(loc_id)
                break
    return assigned


def strategy_optimal_hungarian(
    prods: pd.DataFrame,
    locs: pd.DataFrame,
    demand_col: str = "avg_weekly_demand"
) -> dict[str, str]:
    """Bipartite matching via Scipy Hungarian algorithm minimizing total distance cost."""
    avail_locs = locs[locs["available"] == 1].reset_index(drop=True)
    n_prods, n_locs = len(prods), len(avail_locs)

    demands = prods[demand_col].values
    distances = avail_locs["distance_to_door"].values

    # Cost matrix: demand * distance
    cost_matrix = np.outer(demands, distances)

    # Invalidate infeasible product-location pairs with Big-M penalty
    for i, (_, p_row) in enumerate(prods.iterrows()):
        for j, (_, l_row) in enumerate(avail_locs.iterrows()):
            valid, _ = check_assignment_feasibility(p_row, l_row)
            if not valid:
                cost_matrix[i, j] = BIG_M

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    assignment = {}
    for r, c in zip(row_ind, col_ind):
        assignment[prods.iloc[r]["product_id"]] = avail_locs.iloc[c]["location_id"]
    return assignment


def strategy_ilp_multi_capacity(
    prods: pd.DataFrame,
    locs: pd.DataFrame,
    time_limit_sec: int = 5
) -> dict[str, str]:
    """PuLP ILP solver for multi-item bins respecting cumulative volume capacity."""
    # Fast subset or full problem depending on size
    p_subset = prods.head(60).reset_index(drop=True)
    l_subset = locs[locs["available"] == 1].head(60).reset_index(drop=True)

    prob = pulp.LpProblem("Slotting_ILP", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("assign", ((i, j) for i in range(len(p_subset)) for j in range(len(l_subset))), cat=pulp.LpBinary)

    # Objective
    prob += pulp.lpSum(
        float(p_subset.loc[i, "avg_weekly_demand"]) * float(l_subset.loc[j, "distance_to_door"]) * x[(i, j)]
        for i in range(len(p_subset)) for j in range(len(l_subset))
    )

    # Each product assigned exactly once
    for i in range(len(p_subset)):
        prob += pulp.lpSum(x[(i, j)] for j in range(len(l_subset))) == 1

    # Capacity volume constraint
    for j in range(len(l_subset)):
        prob += pulp.lpSum(float(p_subset.loc[i, "volume"]) * x[(i, j)] for i in range(len(p_subset))) <= float(l_subset.loc[j, "capacity_volume"])

    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit_sec))
    assignment = {}
    for i in range(len(p_subset)):
        for j in range(len(l_subset)):
            if pulp.value(x[(i, j)]) == 1:
                assignment[p_subset.loc[i, "product_id"]] = l_subset.loc[j, "location_id"]
    return assignment


def strategy_forecast_affinity(
    prods: pd.DataFrame,
    locs: pd.DataFrame,
    orders: pd.DataFrame
) -> dict[str, str]:
    """AI Differentiator: Exponential smoothing demand forecast + Hungarian + Affinity swap search."""
    # 1. Forecast next-week demand
    forecast_dict = predict_next_week_demands(prods, alpha=0.3)
    p_forecasted = prods.copy()
    p_forecasted["predicted_demand"] = p_forecasted["product_id"].map(forecast_dict)

    # 2. Hungarian assignment on predicted demand
    hungarian_plan = strategy_optimal_hungarian(p_forecasted, locs, demand_col="predicted_demand")

    # 3. Compute co-pick affinity lift from orders
    lifts = compute_affinity_lift(orders)

    # 4. Swap-based local search
    refined_plan = optimize_affinity_swaps(
        current_assignment=hungarian_plan,
        products_df=p_forecasted,
        locations_df=locs,
        affinity_lift=lifts,
        demand_lookup=forecast_dict
    )
    return refined_plan


def run_all_strategies(data_dir: str = "slotiq/data") -> dict[str, dict]:
    """Execute all strategies and return structured comparison dictionary."""
    if not os.path.exists(data_dir):
        data_dir = str(Path(__file__).resolve().parent.parent / "data")
    prods, locs, orders = pd.read_csv(f"{data_dir}/products.csv"), pd.read_csv(f"{data_dir}/locations.csv"), pd.read_csv(f"{data_dir}/orders.csv")
    plans = {
        "Baseline": strategy_baseline(prods, locs),
        "ABC-Greedy": strategy_abc_greedy(prods, locs),
        "Optimal (Hungarian)": strategy_optimal_hungarian(prods, locs),
        "Forecast + Affinity": strategy_forecast_affinity(prods, locs, orders)
    }
    return {name: {"assignment": plan, "metrics": calculate_metrics(plan, prods, locs)} for name, plan in plans.items()}


def print_comparison_table(results: dict[str, dict]):
    """Print markdown formatted leaderboard comparison of all strategies."""
    headers = ["Strategy", "Pick Dist (m)", "Feasibility %", "Space Util %", "Labor Cost ($)", "Moves", "Top20 in Prime %"]
    print("=" * 105)
    print("SLOTIQ STRATEGY LEADERBOARD BENCHMARK")
    print("=" * 105)
    print(f"{headers[0]:<24} {headers[1]:>14} {headers[2]:>14} {headers[3]:>14} {headers[4]:>14} {headers[5]:>8} {headers[6]:>18}")
    print("-" * 105)
    for name, data in results.items():
        m = data["metrics"]
        print(
            f"{name:<24} "
            f"{m['total_picking_distance_m']:>14.1f} "
            f"{m['feasibility_pct']:>13.1f}% "
            f"{m['space_utilization_pct']:>13.1f}% "
            f"${m['handling_cost_usd']:>13.2f} "
            f"{m['moves_needed']:>8d} "
            f"{m['high_demand_in_prime_slot_pct']:>17.1f}%"
        )
    print("=" * 105)


if __name__ == "__main__":
    benchmark = run_all_strategies()
    print_comparison_table(benchmark)
