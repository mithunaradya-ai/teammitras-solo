"""Exponential smoothing demand forecaster for SlotIQ.

Applies Holt/Single exponential smoothing across the 12-week historical demand
to predict next-week demand for every product. Provides deterministic and fast
forecasting suitable for hackathon execution on CPU without paid APIs.
"""

import pandas as pd
import numpy as np


def exponential_smoothing(series: list[float], alpha: float = 0.3) -> float:
    """Compute single exponential smoothing forecast for next period."""
    if not series:
        return 0.0
    s = float(series[0])
    for val in series[1:]:
        s = alpha * float(val) + (1.0 - alpha) * s
    return max(1.0, round(s, 2))


def predict_next_week_demands(products_df: pd.DataFrame, alpha: float = 0.3) -> dict[str, float]:
    """Calculate predicted next-week demand for all products using historical week columns."""
    week_cols = [f"week_{w}" for w in range(1, 13) if f"week_{w}" in products_df.columns]
    predictions = {}

    for _, row in products_df.iterrows():
        p_id = row["product_id"]
        if week_cols:
            hist_vals = [float(row[col]) for col in week_cols]
            pred = exponential_smoothing(hist_vals, alpha=alpha)
        else:
            pred = float(row.get("avg_weekly_demand", 10.0))
        predictions[p_id] = pred

    return predictions


def attach_forecasts(products_df: pd.DataFrame, alpha: float = 0.3) -> pd.DataFrame:
    """Return a copy of products DataFrame augmented with predicted_next_week_demand."""
    df_copy = products_df.copy()
    preds = predict_next_week_demands(df_copy, alpha=alpha)
    df_copy["predicted_demand"] = df_copy["product_id"].map(preds)
    return df_copy


if __name__ == "__main__":
    prods = pd.read_csv("slotiq/data/products.csv")
    forecasted = attach_forecasts(prods)
    print("DEMAND FORECAST SAMPLE (Exponential Smoothing alpha=0.3):")
    sample = forecasted[["product_id", "avg_weekly_demand", "predicted_demand"]].head(10)
    print(sample.to_string(index=False))
