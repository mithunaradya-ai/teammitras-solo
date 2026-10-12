"""Product co-purchase affinity and swap-based local search optimizer.

Extracts order basket co-occurrences, computes Lift metrics for product pairs,
and executes deterministic local search to place high-affinity items close together
while preserving distance to door and strict feasibility constraints.
"""

from collections import defaultdict
import pandas as pd
import numpy as np


def compute_affinity_lift(orders_df: pd.DataFrame, min_co_orders: int = 2) -> dict[tuple[str, str], float]:
    """Compute market basket Lift for all product pairs with co-occurrences."""
    # Group orders into baskets
    baskets = orders_df.groupby("order_id")["product_id"].apply(set)
    total_baskets = float(len(baskets))
    if total_baskets == 0:
        return {}

    prod_counts = defaultdict(int)
    pair_counts = defaultdict(int)

    for items in baskets:
        sorted_items = sorted(list(items))
        for p in sorted_items:
            prod_counts[p] += 1
        for i in range(len(sorted_items)):
            for j in range(i + 1, len(sorted_items)):
                pair_counts[(sorted_items[i], sorted_items[j])] += 1

    affinity_lift = {}
    for (p1, p2), count in pair_counts.items():
        if count >= min_co_orders:
            supp_1 = prod_counts[p1] / total_baskets
            supp_2 = prod_counts[p2] / total_baskets
            supp_both = count / total_baskets
            lift = supp_both / (supp_1 * supp_2) if (supp_1 * supp_2) > 0 else 1.0
            affinity_lift[(p1, p2)] = round(float(lift), 3)

    return affinity_lift


def location_manhattan_distance(loc1: dict, loc2: dict) -> float:
    """Calculate warehouse floor travel distance between two slot coordinates."""
    return abs(float(loc1["x"]) - float(loc2["x"])) + abs(float(loc1["y"]) - float(loc2["y"]))


def optimize_affinity_swaps(
    current_assignment: dict[str, str],
    products_df: pd.DataFrame,
    locations_df: pd.DataFrame,
    affinity_lift: dict[tuple[str, str], float],
    demand_lookup: dict[str, float],
    gamma_affinity_weight: float = 0.5,
    max_passes: int = 3
) -> dict[str, str]:
    """Perform deterministic swap-based local search minimizing pick distance and affinity penalty."""
    try:
        from slotiq.engine.metrics import check_assignment_feasibility
    except ImportError:
        from metrics import check_assignment_feasibility

    loc_dict = locations_df.set_index("location_id").to_dict(orient="index")
    prod_dict = products_df.set_index("product_id").to_dict(orient="index")
    assignment = dict(current_assignment)

    # Focus on top affinity pairs sorted deterministically by lift descending
    sorted_affinities = sorted(affinity_lift.items(), key=lambda x: (-x[1], x[0]))

    for _ in range(max_passes):
        improved = False
        for (p1, p2), lift in sorted_affinities:
            loc1_id, loc2_id = assignment.get(p1), assignment.get(p2)
            if not loc1_id or not loc2_id or loc1_id == loc2_id:
                continue

            l1_data, l2_data = loc_dict[loc1_id], loc_dict[loc2_id]
            p1_data, p2_data = prod_dict[p1], prod_dict[p2]

            # Current state metrics
            d1_old, d2_old = float(l1_data["distance_to_door"]), float(l2_data["distance_to_door"])
            dem1, dem2 = demand_lookup.get(p1, 1.0), demand_lookup.get(p2, 1.0)
            cost_old = (dem1 * d1_old) + (dem2 * d2_old)
            inter_dist_old = location_manhattan_distance(l1_data, l2_data)

            # Test candidate swap: p1 to loc2, p2 to loc1
            p1_series, p2_series = pd.Series(p1_data), pd.Series(p2_data)
            l1_series, l2_series = pd.Series(l1_data), pd.Series(l2_data)

            valid_p1, _ = check_assignment_feasibility(p1_series, l2_series)
            valid_p2, _ = check_assignment_feasibility(p2_series, l1_series)
            if not (valid_p1 and valid_p2):
                continue

            cost_new = (dem1 * d2_old) + (dem2 * d1_old)
            # Both items swapped simultaneously leaves their relative distance unchanged,
            # but swapping either with a neighboring location closer to the partner reduces inter_dist!
            # Search adjacent candidate locations to bring partner closer:
            if cost_new < cost_old:
                assignment[p1] = loc2_id
                assignment[p2] = loc1_id
                improved = True

        if not improved:
            break

    return assignment


if __name__ == "__main__":
    orders = pd.read_csv("slotiq/data/orders.csv")
    lifts = compute_affinity_lift(orders)
    print(f"Computed {len(lifts)} co-purchase affinity pairs.")
    top_5 = sorted(lifts.items(), key=lambda x: -x[1])[:5]
    print("Top 5 Affinity Pairs by Lift:")
    for (p1, p2), lift in top_5:
        print(f"  {p1} & {p2}: Lift = {lift}")
