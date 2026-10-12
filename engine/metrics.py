"""Metrics calculation engine for SlotIQ warehouse slotting.

Computes the 6 key operational metrics:
1. Total picking distance (pick frequency * distance to door)
2. Space utilization % (used volume / capacity volume)
3. Feasibility % (passes dimensional, capacity, handling, and availability constraints)
4. Handling cost ($) based on documented cost per meter walked
5. Re-slotting moves needed vs baseline
6. High-demand-in-prime-slot % (top 20% products in top 20% locations)
"""

import pandas as pd
import numpy as np

# Operational Cost Parameter: average picking labor cost per meter in standard operations ($/m)
COST_PER_METER_DEFAULT = 0.15


def is_dimension_feasible(p_row: pd.Series, loc_row: pd.Series) -> bool:
    """Check if product fits inside location box considering 3D rotation."""
    p_dims = sorted([p_row["length"], p_row["width"], p_row["height"]])
    loc_dims = sorted([loc_row["max_length"], loc_row["max_width"], loc_row["max_height"]])
    fits_box = (p_dims[0] <= loc_dims[0] and p_dims[1] <= loc_dims[1] and p_dims[2] <= loc_dims[2])
    fits_vol = p_row["volume"] <= loc_row["capacity_volume"]
    return bool(fits_box and fits_vol)


def is_handling_feasible(p_row: pd.Series, loc_row: pd.Series) -> bool:
    """Check special handling compatibility (cold/fragile requirement)."""
    if p_row["special_handling"] == 1:
        return bool(loc_row["special_handling_supported"] == 1)
    return True


def check_assignment_feasibility(p_row: pd.Series, loc_row: pd.Series) -> tuple[bool, str]:
    """Verify single assignment against availability, dimensions, capacity, and special handling."""
    if loc_row["available"] == 0:
        return False, "Location unavailable"
    if not is_handling_feasible(p_row, loc_row):
        return False, "Special handling mismatch"
    if not is_dimension_feasible(p_row, loc_row):
        return False, "Exceeds dimensions or volume capacity"
    return True, "Valid"


def calculate_metrics(
    assignment: dict,
    products_df: pd.DataFrame,
    locations_df: pd.DataFrame,
    cost_per_meter: float = COST_PER_METER_DEFAULT
) -> dict:
    """Compute all 6 operational metrics strictly from real data inputs."""
    loc_lookup = locations_df.set_index("location_id").to_dict(orient="index")
    prod_lookup = products_df.set_index("product_id").to_dict(orient="index")

    total_picking_dist = 0.0
    valid_count = 0
    total_assigned = len(assignment)
    used_vol = 0.0
    occupied_capacity = 0.0
    moves_needed = 0

    # Determine Top 20% prime locations (lowest distance to door)
    available_locs = locations_df[locations_df["available"] == 1].sort_values("distance_to_door")
    top_20_loc_count = max(1, int(0.20 * len(available_locs)))
    prime_location_ids = set(available_locs.head(top_20_loc_count)["location_id"])

    # Determine Top 20% high-demand products
    sorted_prods = products_df.sort_values("avg_weekly_demand", ascending=False)
    top_20_prod_count = max(1, int(0.20 * len(sorted_prods)))
    top_20_prod_ids = set(sorted_prods.head(top_20_prod_count)["product_id"])

    top_in_prime_count = 0

    for p_id, loc_id in assignment.items():
        if p_id not in prod_lookup or loc_id not in loc_lookup:
            continue
        p_row = prod_lookup[p_id]
        loc_row = loc_lookup[loc_id]

        # 1. Picking distance
        picks = float(p_row["avg_weekly_demand"])
        dist = float(loc_row["distance_to_door"])
        total_picking_dist += (picks * dist)

        # 2. Feasibility
        is_valid, _ = check_assignment_feasibility(pd.Series(p_row), pd.Series(loc_row))
        if is_valid:
            valid_count += 1

        # 3. Space utilization
        used_vol += float(p_row["volume"])
        occupied_capacity += float(loc_row["capacity_volume"])

        # 4. Moves vs baseline
        baseline_loc = p_row.get("baseline_location_id")
        if baseline_loc and loc_id != baseline_loc:
            moves_needed += 1

        # 5. High demand in prime slot
        if p_id in top_20_prod_ids and loc_id in prime_location_ids:
            top_in_prime_count += 1

    space_utilization_pct = round((used_vol / occupied_capacity * 100.0) if occupied_capacity > 0 else 0.0, 2)
    feasibility_pct = round((valid_count / total_assigned * 100.0) if total_assigned > 0 else 0.0, 2)
    handling_cost = round(total_picking_dist * cost_per_meter, 2)
    high_demand_prime_pct = round((top_in_prime_count / top_20_prod_count * 100.0) if top_20_prod_count > 0 else 0.0, 2)

    return {
        "total_picking_distance_m": round(total_picking_dist, 2),
        "space_utilization_pct": space_utilization_pct,
        "feasibility_pct": feasibility_pct,
        "handling_cost_usd": handling_cost,
        "moves_needed": moves_needed,
        "high_demand_in_prime_slot_pct": high_demand_prime_pct,
        "evaluated_products": total_assigned
    }


if __name__ == "__main__":
    # Test on generated clean dataset
    prods = pd.read_csv("slotiq/data/products.csv")
    locs = pd.read_csv("slotiq/data/locations.csv")
    baseline_assignment = dict(zip(prods["product_id"], prods["baseline_location_id"]))
    results = calculate_metrics(baseline_assignment, prods, locs)
    print("BASELINE METRICS EVALUATION:")
    for k, v in results.items():
        print(f"  {k:30s}: {v}")
