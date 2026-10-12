"""Re-slotting transition planner and financial payback calculator for SlotIQ.

Translates optimization recommendations into an actionable move execution plan:
- Computes total physical moves required against baseline
- Quantifies physical re-slotting labour cost ($12/item relocated)
- Calculates daily picking savings from reduced walking travel
- Computes exact payback period in operating days = move_cost / daily_savings
"""

import os
import sys
from pathlib import Path
import pandas as pd

# Handle flexible imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from slotiq.engine.metrics import calculate_metrics, COST_PER_METER_DEFAULT

COST_PER_MOVE_DEFAULT = 12.00  # Technician handling and relabeling labor cost ($/move)
DAYS_PER_WEEK_DEFAULT = 5      # Standard operating warehouse days per week


def calculate_reslotting_plan(
    new_assignment: dict[str, str],
    products_df: pd.DataFrame,
    locations_df: pd.DataFrame,
    cost_per_move: float = COST_PER_MOVE_DEFAULT,
    cost_per_meter: float = COST_PER_METER_DEFAULT,
    days_per_week: int = DAYS_PER_WEEK_DEFAULT
) -> dict:
    """Compute financial ROI, payback period, and prioritized move sequence."""
    baseline_assignment = dict(zip(products_df["product_id"], products_df["baseline_location_id"]))
    
    base_metrics = calculate_metrics(baseline_assignment, products_df, locations_df, cost_per_meter)
    new_metrics = calculate_metrics(new_assignment, products_df, locations_df, cost_per_meter)

    loc_dict = locations_df.set_index("location_id").to_dict(orient="index")
    prod_dict = products_df.set_index("product_id").to_dict(orient="index")

    moves = []
    for p_id, target_loc in new_assignment.items():
        if p_id not in prod_dict:
            continue
        curr_loc = prod_dict[p_id].get("baseline_location_id")
        if curr_loc != target_loc:
            curr_dist = float(loc_dict.get(curr_loc, {}).get("distance_to_door", 0.0))
            new_dist = float(loc_dict.get(target_loc, {}).get("distance_to_door", 0.0))
            demand = float(prod_dict[p_id].get("avg_weekly_demand", 0.0))
            
            weekly_dist_saved = demand * (curr_dist - new_dist)
            daily_dist_saved = weekly_dist_saved / days_per_week
            daily_usd_saved = daily_dist_saved * cost_per_meter

            moves.append({
                "product_id": p_id,
                "category": prod_dict[p_id].get("category", "General"),
                "from_location": curr_loc,
                "to_location": target_loc,
                "weekly_picks": demand,
                "distance_delta_m": round(curr_dist - new_dist, 2),
                "daily_savings_m": round(daily_dist_saved, 2),
                "daily_savings_usd": round(daily_usd_saved, 2)
            })

    # Sort moves descending by greatest daily financial savings (quickest wins first)
    moves.sort(key=lambda x: -x["daily_savings_usd"])

    total_moves = len(moves)
    total_move_cost = round(total_moves * cost_per_move, 2)
    
    # Financial savings
    weekly_dist_saved_total = base_metrics["total_picking_distance_m"] - new_metrics["total_picking_distance_m"]
    daily_dist_saved_total = weekly_dist_saved_total / days_per_week
    daily_financial_savings = round(daily_dist_saved_total * cost_per_meter, 2)

    payback_days = round(total_move_cost / daily_financial_savings, 1) if daily_financial_savings > 0 else 999.0

    return {
        "total_moves": total_moves,
        "total_relocation_cost_usd": total_move_cost,
        "weekly_distance_saved_m": round(weekly_dist_saved_total, 1),
        "daily_distance_saved_m": round(daily_dist_saved_total, 1),
        "daily_financial_savings_usd": daily_financial_savings,
        "payback_period_days": payback_days,
        "moves_list": moves
    }


if __name__ == "__main__":
    from slotiq.engine.strategies import strategy_optimal_hungarian
    prods = pd.read_csv("slotiq/data/products.csv")
    locs = pd.read_csv("slotiq/data/locations.csv")
    opt_plan = strategy_optimal_hungarian(prods, locs)
    plan = calculate_reslotting_plan(opt_plan, prods, locs)

    print("=" * 65)
    print("SLOTIQ RE-SLOTTING ROI & PAYBACK REPORT")
    print("=" * 65)
    print(f"  Total Relocations Required : {plan['total_moves']}")
    print(f"  Labor Relocation Cost      : ${plan['total_relocation_cost_usd']:,.2f}")
    print(f"  Daily Picking Distance Saved: {plan['daily_distance_saved_m']:,.1f} meters")
    print(f"  Daily Financial Labor Saved : ${plan['daily_financial_savings_usd']:,.2f} / day")
    print(f"  Payback Period (ROI)       : {plan['payback_period_days']} working days")
    print("=" * 65)
    print("Top 5 Highest Impact Moves:")
    for m in plan["moves_list"][:5]:
        print(f"  {m['product_id']} ({m['category']}): {m['from_location']} -> {m['to_location']} | Saves ${m['daily_savings_usd']:.2f}/day ({m['daily_savings_m']} m/day)")
    print("=" * 65)
