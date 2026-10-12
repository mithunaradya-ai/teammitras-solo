"""Explainability engine for SlotIQ recommendations.

Generates human-readable, auditable operational explanations for why each product
was assigned to its target location (percentile rank, dimension clearance, distance,
daily travel savings, and affinity context).
"""

import os
import sys
from pathlib import Path
import pandas as pd

# Handle flexible imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def generate_single_explanation(
    product_id: str,
    new_loc_id: str,
    p_data: dict,
    old_loc_data: dict,
    new_loc_data: dict,
    demand_rank_pct: float,
    working_days_per_week: int = 5
) -> str:
    """Generate plain-English audit reasoning for an individual product slotting decision."""
    old_loc = p_data.get("baseline_location_id", "None")
    new_loc = new_loc_id
    weekly_picks = float(p_data.get("avg_weekly_demand", 0.0))
    
    old_dist = float(old_loc_data.get("distance_to_door", 0.0))
    new_dist = float(new_loc_data.get("distance_to_door", 0.0))
    
    weekly_dist_diff = weekly_picks * (old_dist - new_dist)
    daily_meters_saved = round(weekly_dist_diff / working_days_per_week, 1)

    p_dims = f"{p_data['length']}x{p_data['width']}x{p_data['height']}"
    l_dims = f"{new_loc_data['max_length']}x{new_loc_data['max_width']}x{new_loc_data['max_height']}"

    # Handling notes
    handling_tag = ""
    if p_data.get("special_handling") == 1:
        handling_tag = ", allocated to specialized zone D"

    if old_loc == new_loc:
        return (
            f"{product_id} stays at {new_loc}: top {demand_rank_pct:.1f}% by picks ({weekly_picks:.0f}/wk), "
            f"fits {p_dims} in {l_dims}, {new_dist} m from dispatch door{handling_tag}. Current slot already optimal."
        )

    savings_str = f"saves {daily_meters_saved:+.1f} m/day" if daily_meters_saved != 0 else "neutral travel change"
    return (
        f"{product_id} -> {new_loc} (from {old_loc}): top {demand_rank_pct:.1f}% by picks ({weekly_picks:.0f}/wk), "
        f"fits {p_dims} in {l_dims}, {new_dist} m from dispatch door ({old_dist - new_dist:+.1f} m delta), "
        f"{savings_str}{handling_tag}."
    )


def explain_assignment(
    assignment: dict[str, str],
    products_df: pd.DataFrame,
    locations_df: pd.DataFrame
) -> dict[str, str]:
    """Generate explanation strings for all products in an assignment dictionary."""
    prod_dict = products_df.set_index("product_id").to_dict(orient="index")
    loc_dict = locations_df.set_index("location_id").to_dict(orient="index")

    # Compute demand ranks
    sorted_p = products_df.sort_values("avg_weekly_demand", ascending=False).reset_index(drop=True)
    n_total = len(sorted_p)
    rank_lookup = {row["product_id"]: round((idx + 1) / n_total * 100.0, 1) for idx, row in sorted_p.iterrows()}

    explanations = {}
    for p_id, new_loc_id in assignment.items():
        if p_id not in prod_dict or new_loc_id not in loc_dict:
            continue
        p_data = prod_dict[p_id]
        new_loc_data = loc_dict[new_loc_id]
        old_loc_id = p_data.get("baseline_location_id")
        old_loc_data = loc_dict.get(old_loc_id, new_loc_data)
        demand_pct = rank_lookup.get(p_id, 50.0)

        explanations[p_id] = generate_single_explanation(
            product_id=p_id,
            new_loc_id=new_loc_id,
            p_data=p_data,
            old_loc_data=old_loc_data,
            new_loc_data=new_loc_data,
            demand_rank_pct=demand_pct
        )

    return explanations


if __name__ == "__main__":
    from pathlib import Path
    from engine.strategies import strategy_optimal_hungarian

    data_dir = Path(__file__).resolve().parent.parent / "data"
    prods = pd.read_csv(data_dir / "products.csv")
    locs = pd.read_csv(data_dir / "locations.csv")
    plan = strategy_optimal_hungarian(prods, locs)
    reasons = explain_assignment(plan, prods, locs)

    print("SAMPLE EXPLANATIONS (First 5 products):")
    for p_id in list(reasons.keys())[:5]:
        print(f"  {reasons[p_id]}")
