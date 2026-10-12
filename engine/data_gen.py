"""Data generator for SlotIQ warehouse slotting optimizer.

Generates reproducible synthetic datasets with seed 42:
- 300 products with Pareto demand distribution (80/20 rule)
- 320 grid locations with distance metrics and capacities
- 5000 order lines with realistic co-purchase affinity patterns
- Dirty dataset with injected anomalies for validator testing
"""

import os
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)


def generate_locations(n_locations: int = 320) -> pd.DataFrame:
    """Generate warehouse grid locations with coordinates, capacity, and distance to door."""
    np.random.seed(SEED)
    zones, locs, count = ["A", "B", "C", "D"], [], 0
    bin_sizes = {
        "S": (40.0, 40.0, 30.0),
        "M": (60.0, 50.0, 45.0),
        "L": (90.0, 70.0, 60.0)
    }

    for z_idx, zone in enumerate(zones):
        for aisle in range(1, 5):
            for bay in range(1, 21):
                if count >= n_locations:
                    break
                loc_id = f"{zone}{count % 80 + 1:02d}"
                x, y = (z_idx * 4 + aisle) * 2.5, bay * 1.5
                dist = round(abs(x) + abs(y), 2)
                access = round(float(np.random.choice([1.0, 2.0, 3.0, 4.0, 5.0], p=[0.1, 0.2, 0.4, 0.2, 0.1])), 1)
                btype = np.random.choice(["S", "M", "L"], p=[0.3, 0.5, 0.2])
                ml, mw, mh = bin_sizes[btype]
                vol = round(ml * mw * mh, 1)
                locs.append({
                    "location_id": loc_id, "zone": zone, "x": x, "y": y,
                    "max_length": ml, "max_width": mw, "max_height": mh,
                    "capacity_volume": vol, "accessibility_score": access,
                    "distance_to_door": dist,
                    "special_handling_supported": 1 if zone == "D" else 0,
                    "available": 1 if np.random.rand() > 0.03 else 0
                })
                count += 1
    return pd.DataFrame(locs)


def generate_products(locations_df: pd.DataFrame, n_products: int = 300) -> pd.DataFrame:
    """Generate products with dimensions, Pareto-distributed 12-week demand, and random baseline layout."""
    np.random.seed(SEED)
    categories = ["Electronics", "Apparel", "Grocery", "Health", "Home"]
    prods = []
    # Pareto demand: alpha=0.98 gives ~80% demand in top 20% products
    raw_weights = np.random.pareto(a=0.98, size=n_products)
    sorted_weights = np.sort(raw_weights)[::-1]
    base_demands = np.maximum(1, np.round(sorted_weights / sorted_weights.sum() * 4500)).astype(int)

    avail_locs = locations_df[locations_df["available"] == 1]["location_id"].tolist()
    shuffled_locs = np.random.choice(avail_locs, size=n_products, replace=False)

    for i in range(n_products):
        p_id = f"P{i + 1:03d}"
        cat = categories[i % len(categories)]
        special = 1 if (cat in ["Grocery", "Health"] and np.random.rand() < 0.3) else 0
        l = round(float(np.random.uniform(15.0, 50.0)), 1)
        w = round(float(np.random.uniform(10.0, 40.0)), 1)
        h = round(float(np.random.uniform(10.0, 35.0)), 1)
        vol = round(l * w * h, 1)
        # 12 weeks of historical demand
        w_demands = [max(1, int(round(base_demands[i] * max(0.2, np.random.normal(1.0, 0.15))))) for _ in range(12)]
        row = {
            "product_id": p_id, "category": cat, "length": l, "width": w, "height": h,
            "volume": vol, "special_handling": special, "baseline_location_id": shuffled_locs[i],
            "total_picks_12w": sum(w_demands), "avg_weekly_demand": round(float(np.mean(w_demands)), 1)
        }
        for idx, val in enumerate(w_demands):
            row[f"week_{idx + 1}"] = val
        prods.append(row)
    return pd.DataFrame(prods)


def generate_orders(products_df: pd.DataFrame, n_order_lines: int = 5000) -> pd.DataFrame:
    """Generate order lines with strong affinity pairs and Pareto pick frequencies across 12 weeks."""
    np.random.seed(SEED)
    p_ids = products_df["product_id"].values
    prob_dist = products_df["avg_weekly_demand"].values / products_df["avg_weekly_demand"].values.sum()
    affinity_pairs = [(p_ids[i], p_ids[i + 1]) for i in range(0, 30, 2)]

    order_lines, order_id, current_lines = [], 1000, 0
    while current_lines < n_order_lines:
        order_id += 1
        week = int(np.random.randint(1, 13))
        basket_size = int(np.random.choice([1, 2, 3, 4], p=[0.4, 0.35, 0.15, 0.10]))
        basket = set()
        if np.random.rand() < 0.30 and basket_size >= 2:
            pair = affinity_pairs[np.random.choice(len(affinity_pairs))]
            basket.update(pair)
        while len(basket) < basket_size:
            basket.add(np.random.choice(p_ids, p=prob_dist))
        for p in basket:
            if current_lines >= n_order_lines:
                break
            order_lines.append({"order_id": f"ORD{order_id}", "product_id": p, "week": week})
            current_lines += 1
    return pd.DataFrame(order_lines)


def inject_dirty_data(products_df: pd.DataFrame, locations_df: pd.DataFrame, orders_df: pd.DataFrame):
    """Create dirty variants with duplicate rows, negative dimensions, missing values, and invalid locations."""
    p_dirty, l_dirty, o_dirty = products_df.copy(), locations_df.copy(), orders_df.copy()
    # 1. Duplicates
    p_dirty = pd.concat([p_dirty, p_dirty.iloc[[5, 12, 45]]], ignore_index=True)
    o_dirty = pd.concat([o_dirty, o_dirty.iloc[[10, 25, 99]]], ignore_index=True)
    # 2. Negative dimensions
    p_dirty.loc[10, "length"] = -35.0
    p_dirty.loc[22, "height"] = -12.5
    l_dirty.loc[14, "max_width"] = -50.0
    # 3. Missing values
    p_dirty.loc[30, "category"] = np.nan
    p_dirty.loc[55, "volume"] = np.nan
    l_dirty.loc[40, "accessibility_score"] = np.nan
    # 4. Unavailable locations assigned
    unavail_locs = l_dirty[l_dirty["available"] == 0]["location_id"].values
    if len(unavail_locs) > 0:
        p_dirty.loc[70, "baseline_location_id"] = unavail_locs[0]
        p_dirty.loc[85, "baseline_location_id"] = "NONEXISTENT_LOC"
    return p_dirty, l_dirty, o_dirty


def run_generation(data_dir: str = "slotiq/data") -> dict:
    """Generate all datasets, save to CSV files, and return summary statistics."""
    os.makedirs(data_dir, exist_ok=True)
    locs = generate_locations(320)
    prods = generate_products(locs, 300)
    orders = generate_orders(prods, 5000)

    # Save clean datasets
    locs.to_csv(os.path.join(data_dir, "locations.csv"), index=False)
    prods.to_csv(os.path.join(data_dir, "products.csv"), index=False)
    orders.to_csv(os.path.join(data_dir, "orders.csv"), index=False)

    # Save dirty datasets
    p_dirty, l_dirty, o_dirty = inject_dirty_data(prods, locs, orders)
    p_dirty.to_csv(os.path.join(data_dir, "products_dirty.csv"), index=False)
    l_dirty.to_csv(os.path.join(data_dir, "locations_dirty.csv"), index=False)
    o_dirty.to_csv(os.path.join(data_dir, "orders_dirty.csv"), index=False)

    top_20_count = int(0.20 * len(prods))
    sorted_picks = prods["total_picks_12w"].sort_values(ascending=False).values
    top_20_share = sorted_picks[:top_20_count].sum() / sorted_picks.sum() * 100

    return {
        "products_count": len(prods),
        "locations_count": len(locs),
        "available_locations": int(locs["available"].sum()),
        "order_lines": len(orders),
        "total_12w_picks": int(prods["total_picks_12w"].sum()),
        "top_20pct_demand_share": round(top_20_share, 2),
        "min_distance_to_door": float(locs["distance_to_door"].min()),
        "max_distance_to_door": float(locs["distance_to_door"].max()),
        "dirty_products_rows": len(p_dirty),
        "dirty_locations_rows": len(l_dirty),
        "dirty_orders_rows": len(o_dirty)
    }


if __name__ == "__main__":
    summary = run_generation()
    print("=" * 60)
    print("SLOTIQ DATA GENERATION COMPLETE (SEED 42)")
    print("=" * 60)
    for k, v in summary.items():
        print(f"  {k:28s}: {v}")
    print("=" * 60)
