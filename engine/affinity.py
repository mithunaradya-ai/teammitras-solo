"""Product co-purchase affinity and swap-based local search optimizer.

Extracts order basket co-occurrences, computes Lift metrics for product pairs,
and executes deterministic local search to place high-affinity items close together
while preserving distance to door and strict feasibility constraints.
"""

from collections import defaultdict
import pandas as pd
try:
    from engine.metrics import check_assignment_feasibility
except ImportError:
    from metrics import check_assignment_feasibility


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
    max_passes: int = 3,
    affinity_pair_counts: dict[tuple[str, str], int] | None = None,
    nearby_locations: int = 20
) -> dict[str, str]:
    """Swap feasible SKUs to balance door travel with co-order proximity."""

    loc_dict = locations_df.set_index("location_id").to_dict(orient="index")
    prod_dict = products_df.set_index("product_id").to_dict(orient="index")
    loc_series = {location_id: pd.Series(row) for location_id, row in loc_dict.items()}
    prod_series = {product_id: pd.Series(row) for product_id, row in prod_dict.items()}
    assignment = dict(current_assignment)
    pair_counts = affinity_pair_counts or {pair: max(1, int(lift)) for pair, lift in affinity_lift.items()}
    pair_counts = {
        pair: count for pair, count in pair_counts.items()
        if pair[0] in assignment and pair[1] in assignment
    }
    if not pair_counts:
        return assignment

    total_pair_count = sum(pair_counts.values())
    mean_demand = sum(demand_lookup.values()) / max(1, len(demand_lookup))
    location_to_product = {location_id: product_id for product_id, location_id in assignment.items()}
    pair_edges_by_product: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (product_a, product_b), count in pair_counts.items():
        pair_edges_by_product[product_a].append((product_b, count))
        pair_edges_by_product[product_b].append((product_a, count))

    ranked_pairs = sorted(pair_counts, key=lambda pair: (-pair_counts[pair], pair))[:200]
    location_ids = locations_df["location_id"].tolist()
    location_coordinates = locations_df.set_index("location_id")[["x", "y"]].to_dict(orient="index")
    nearby_by_location = {}
    for location_id in location_ids:
        x = float(location_coordinates[location_id]["x"])
        y = float(location_coordinates[location_id]["y"])
        nearby_by_location[location_id] = sorted(
            location_ids,
            key=lambda candidate_id: (
                abs(float(location_coordinates[candidate_id]["x"]) - x)
                + abs(float(location_coordinates[candidate_id]["y"]) - y),
                candidate_id
            )
        )[:nearby_locations]

    def affinity_distance_delta(product_id: str, new_location_id: str, swapped_product: str, old_location_id: str) -> float:
        delta = 0.0
        changed_products = {product_id, swapped_product}
        changed_pairs = {
            (min(changed_product, partner_id), max(changed_product, partner_id))
            for changed_product in changed_products
            for partner_id, _ in pair_edges_by_product.get(changed_product, [])
        }
        for pair in changed_pairs:
            count = pair_counts.get(pair, 0)
            if not count:
                continue
            first_id, second_id = pair
            old_first_location, old_second_location = assignment[first_id], assignment[second_id]
            new_first_location = new_location_id if first_id == product_id else old_location_id if first_id == swapped_product else old_first_location
            new_second_location = new_location_id if second_id == product_id else old_location_id if second_id == swapped_product else old_second_location
            old_distance = location_manhattan_distance(loc_dict[old_first_location], loc_dict[old_second_location])
            new_distance = location_manhattan_distance(loc_dict[new_first_location], loc_dict[new_second_location])
            delta += count * (new_distance - old_distance)
        return delta

    def swap_delta(product_id: str, swapped_product: str) -> float:
        location_id = assignment[product_id]
        swapped_location_id = assignment[swapped_product]
        valid_product, _ = check_assignment_feasibility(prod_series[product_id], loc_series[swapped_location_id])
        valid_swapped, _ = check_assignment_feasibility(prod_series[swapped_product], loc_series[location_id])
        if not (valid_product and valid_swapped):
            return float("inf")

        travel_delta = (
            demand_lookup.get(product_id, 1.0) * float(loc_dict[swapped_location_id]["distance_to_door"])
            + demand_lookup.get(swapped_product, 1.0) * float(loc_dict[location_id]["distance_to_door"])
            - demand_lookup.get(product_id, 1.0) * float(loc_dict[location_id]["distance_to_door"])
            - demand_lookup.get(swapped_product, 1.0) * float(loc_dict[swapped_location_id]["distance_to_door"])
        )
        affinity_delta = affinity_distance_delta(product_id, swapped_location_id, swapped_product, location_id)
        return travel_delta + gamma_affinity_weight * mean_demand * affinity_delta / total_pair_count

    for _ in range(max_passes):
        improved = False
        for p1, p2 in ranked_pairs:
            for product_id, partner_id in ((p1, p2), (p2, p1)):
                partner_location_id = assignment.get(partner_id)
                product_location_id = assignment.get(product_id)
                if not partner_location_id or not product_location_id:
                    continue

                for candidate_location_id in nearby_by_location[partner_location_id]:
                    candidate_product_id = location_to_product.get(candidate_location_id)
                    if not candidate_product_id or candidate_product_id == product_id:
                        continue
                    delta = swap_delta(product_id, candidate_product_id)
                    if delta < -1e-9:
                        assignment[product_id], assignment[candidate_product_id] = candidate_location_id, product_location_id
                        location_to_product[candidate_location_id], location_to_product[product_location_id] = product_id, candidate_product_id
                        improved = True
                        break

        if not improved:
            break

    return assignment


if __name__ == "__main__":
    from pathlib import Path

    orders = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "orders.csv")
    lifts = compute_affinity_lift(orders)
    print(f"Computed {len(lifts)} co-purchase affinity pairs.")
    top_5 = sorted(lifts.items(), key=lambda x: -x[1])[:5]
    print("Top 5 Affinity Pairs by Lift:")
    for (p1, p2), lift in top_5:
        print(f"  {p1} & {p2}: Lift = {lift}")
