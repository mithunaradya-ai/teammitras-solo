"""FastAPI backend for SlotIQ warehouse slotting optimization.

Exposes REST endpoints for:
- POST /upload: Upload & clean CSV with audit report
- POST /optimize: Run designated optimization strategy
- GET /compare: Strategy leaderboard benchmark
- GET /recommend/{id}: Single product recommendation & plain-English explanation
- GET /layout: Full grid layout with pick density for heatmaps
- POST /whatif: Category demand multiplier simulations
"""

import os
import sys
from pathlib import Path
from typing import Optional
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slotiq.engine.validator import clean_products, clean_locations, clean_orders, DataQualityReport
from slotiq.engine.metrics import calculate_metrics
from slotiq.engine.strategies import (
    strategy_baseline, strategy_abc_greedy, strategy_optimal_hungarian,
    strategy_forecast_affinity, run_all_strategies
)
from slotiq.engine.explain import explain_assignment
from slotiq.engine.reslot import calculate_reslotting_plan

app = FastAPI(title="SlotIQ API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE = {"products_df": None, "locations_df": None, "orders_df": None, "current_plan": None, "current_strategy": "Forecast + Affinity"}


def load_datasets():
    """Load default benchmark data from CSV on server startup."""
    p_path, l_path, o_path = DATA_DIR / "products.csv", DATA_DIR / "locations.csv", DATA_DIR / "orders.csv"
    if p_path.exists() and l_path.exists() and o_path.exists():
        STATE["products_df"] = pd.read_csv(p_path)
        STATE["locations_df"] = pd.read_csv(l_path)
        STATE["orders_df"] = pd.read_csv(o_path)
        STATE["current_plan"] = strategy_forecast_affinity(STATE["products_df"], STATE["locations_df"], STATE["orders_df"])

load_datasets()


@app.on_event("startup")
def startup_event():
    if STATE["products_df"] is None:
        load_datasets()


DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"
if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")


@app.get("/")
def index():
    """Serve dashboard UI at root if built, or direct to docs."""
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"service": "SlotIQ API", "docs": "/docs", "dashboard": "http://localhost:5173"}


@app.get("/health")
def health():
    """Liveness probe for backend health check."""
    return {"status": "ok", "products_loaded": len(STATE["products_df"]) if STATE["products_df"] is not None else 0}


@app.post("/upload")
async def upload_csv(file_type: str = Form(...), file: UploadFile = File(...)):
    """Upload custom CSV, trigger data validation and cleaner, and update runtime state."""
    report = DataQualityReport()
    try:
        df_raw = pd.read_csv(file.file)
        if file_type == "locations":
            STATE["locations_df"] = clean_locations(df_raw, report)
        elif file_type == "products":
            locs = STATE["locations_df"] if STATE["locations_df"] is not None else pd.read_csv(DATA_DIR / "locations.csv")
            STATE["products_df"] = clean_products(df_raw, locs, report)
        elif file_type == "orders":
            valid_p = set(STATE["products_df"]["product_id"]) if STATE["products_df"] is not None else set()
            STATE["orders_df"] = clean_orders(df_raw, valid_p, report)
        else:
            raise HTTPException(status_code=400, detail="Invalid file_type (must be products, locations, orders)")
        return {"filename": file.filename, "file_type": file_type, "audit_report": report.to_summary_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/optimize")
def optimize(strategy: str = Query("forecast_affinity")):
    """Run specified strategy and update the active warehouse allocation plan."""
    prods, locs, orders = STATE["products_df"], STATE["locations_df"], STATE["orders_df"]
    if prods is None:
        raise HTTPException(status_code=400, detail="Datasets not loaded")
    strat_map = {
        "baseline": ("Baseline", lambda: strategy_baseline(prods, locs)),
        "abc_greedy": ("ABC-Greedy", lambda: strategy_abc_greedy(prods, locs)),
        "optimal": ("Optimal (Hungarian)", lambda: strategy_optimal_hungarian(prods, locs)),
        "forecast_affinity": ("Forecast + Affinity", lambda: strategy_forecast_affinity(prods, locs, orders))
    }
    key = strategy.lower().replace(" ", "_")
    if key not in strat_map:
        raise HTTPException(status_code=400, detail=f"Strategy '{strategy}' not found")
    label, fn = strat_map[key]
    plan = fn()
    STATE["current_plan"], STATE["current_strategy"] = plan, label
    return {"strategy": label, "metrics": calculate_metrics(plan, prods, locs), "reslotting_summary": calculate_reslotting_plan(plan, prods, locs)}


@app.get("/compare")
def compare():
    """Run all 4 slotting strategies and return leaderboard metrics."""
    return run_all_strategies(str(DATA_DIR))


@app.get("/recommend/{product_id}")
def recommend_product(product_id: str):
    """Retrieve slotting recommendation and plain-English explanation for a product."""
    prods, locs = STATE["products_df"], STATE["locations_df"]
    p_row = prods[prods["product_id"] == product_id]
    if p_row.empty:
        raise HTTPException(status_code=404, detail="Product ID not found")
    plan = STATE["current_plan"] or strategy_baseline(prods, locs)
    explanations = explain_assignment(plan, prods, locs)
    target_loc = plan.get(product_id)
    loc_match = locs[locs["location_id"] == target_loc]
    loc_info = loc_match.iloc[0].to_dict() if not loc_match.empty else {}
    return {
        "product_id": product_id, "product_info": p_row.iloc[0].to_dict(),
        "target_location": target_loc, "location_info": loc_info,
        "explanation": explanations.get(product_id, "No explanation available.")
    }


@app.get("/layout")
def get_layout(strategy: str = Query("forecast_affinity")):
    """Return warehouse grid layout with product assignments and pick density for heatmaps."""
    prods, locs, orders = STATE["products_df"], STATE["locations_df"], STATE["orders_df"]
    strat_key = strategy.lower().replace(" ", "_")
    if strat_key == "baseline":
        plan = strategy_baseline(prods, locs)
    elif strat_key == "abc_greedy":
        plan = strategy_abc_greedy(prods, locs)
    elif strat_key == "optimal":
        plan = strategy_optimal_hungarian(prods, locs)
    else:
        plan = strategy_forecast_affinity(prods, locs, orders)

    loc_to_prod = {loc_id: p_id for p_id, loc_id in plan.items()}
    prod_dict = prods.set_index("product_id").to_dict(orient="index")
    grid = []
    for _, l in locs.iterrows():
        lid = l["location_id"]
        assigned_p = loc_to_prod.get(lid)
        p_data = prod_dict.get(assigned_p, {}) if assigned_p else {}
        grid.append({
            "location_id": lid, "zone": l["zone"], "x": l["x"], "y": l["y"],
            "distance_to_door": l["distance_to_door"], "available": int(l["available"]),
            "assigned_product": assigned_p, "picks": float(p_data.get("avg_weekly_demand", 0.0)),
            "category": p_data.get("category", "")
        })
    return {"strategy": strategy, "locations": grid}


class WhatIfRequest(BaseModel):
    multipliers: dict[str, float]
    strategy: Optional[str] = "forecast_affinity"


@app.post("/whatif")
def simulate_whatif(req: WhatIfRequest):
    """Simulate category-level demand fluctuations and recalculate layout and metrics live."""
    prods = STATE["products_df"].copy()
    locs, orders = STATE["locations_df"], STATE["orders_df"]
    for cat, mult in req.multipliers.items():
        mask = prods["category"] == cat
        prods.loc[mask, "avg_weekly_demand"] = prods.loc[mask, "avg_weekly_demand"] * mult
    plan = strategy_forecast_affinity(prods, locs, orders)
    return {"multipliers": req.multipliers, "metrics": calculate_metrics(plan, prods, locs), "reslot": calculate_reslotting_plan(plan, prods, locs)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("slotiq.api.main:app", host="0.0.0.0", port=8000, reload=True)
