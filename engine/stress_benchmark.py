"""Reproducible tight-capacity benchmark contrasting greedy and Hungarian plans."""

import pandas as pd

from engine.data_gen import generate_locations, generate_orders, generate_products
from engine.metrics import calculate_metrics
from engine.strategies import strategy_abc_greedy, strategy_optimal_hungarian


def build_constrained_scenario() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create 40 L-only SKUs competing for 50 nearby large locations."""
    locations = generate_locations(320)
    products = generate_products(locations, 300)
    orders = generate_orders(products, 5000)

    large_location_ids = set(
        locations.sort_values(["distance_to_door", "location_id"]).head(50)["location_id"]
    )
    medium_dimensions = (60.0, 50.0, 45.0)
    large_dimensions = (90.0, 70.0, 60.0)
    for index, row in locations.iterrows():
        if row["location_id"] in large_location_ids:
            dimensions = large_dimensions
        elif row["max_length"] == 90.0:
            dimensions = medium_dimensions
        else:
            continue
        locations.loc[index, ["max_length", "max_width", "max_height"]] = dimensions
        locations.loc[index, "capacity_volume"] = dimensions[0] * dimensions[1] * dimensions[2]

    eligible = products[products["special_handling"] == 0].sort_values("avg_weekly_demand")
    large_product_ids = set(eligible.head(40)["product_id"])
    for index, row in products.iterrows():
        if row["product_id"] in large_product_ids:
            products.loc[index, ["length", "width", "height"]] = (65.0, 55.0, 50.0)
            products.loc[index, "volume"] = 65.0 * 55.0 * 50.0

    return products, locations, orders


def run_constrained_benchmark() -> dict[str, dict]:
    products, locations, orders = build_constrained_scenario()
    strategies = {
        "ABC-Greedy": strategy_abc_greedy(products, locations),
        "Hungarian": strategy_optimal_hungarian(products, locations)
    }
    return {
        name: {
            "assignment": assignment,
            "assigned": len(assignment),
            "products": len(products),
            "metrics": calculate_metrics(assignment, products, locations, orders_df=orders)
        }
        for name, assignment in strategies.items()
    }


if __name__ == "__main__":
    results = run_constrained_benchmark()
    print("TIGHT-CAPACITY STRESS BENCHMARK (seed 42)")
    print("| Strategy | Assigned / products | Picking distance (m/week) | Feasibility |")
    print("|---|---:|---:|---:|")
    for name, result in results.items():
        metrics = result["metrics"]
        distance = (
            f"{metrics['total_picking_distance_m']:,.2f}"
            if result["assigned"] == result["products"]
            else "n/a (incomplete plan)"
        )
        feasibility = (
            f"{metrics['feasibility_pct']:.2f}%"
            if result["assigned"] == result["products"]
            else "incomplete"
        )
        print(
            f"| {name} | {result['assigned']} / {result['products']} "
            f"| {distance} | {feasibility} |"
        )
