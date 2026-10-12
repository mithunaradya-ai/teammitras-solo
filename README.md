# SlotIQ — AI Warehouse Slotting Optimizer

SlotIQ is a high-performance, deterministic warehouse slotting optimization engine built for high-throughput distribution centers. It replaces haphazard storage allocations with mathematically optimal slot assignments using bipartite matching, Holt exponential smoothing demand forecasting, and market-basket co-purchase affinity search.

Runs on standard laptops without GPU or paid external APIs.

## System Overview

```mermaid
flowchart TD

subgraph group_dashboard["Dashboard"]
  node_app["Dashboard Shell<br/>[App.jsx]"]
  node_upload["Data Upload<br/>[UploadPage.jsx]"]
  node_leaderboard["Strategy Leaderboard"]
  node_heatmap["Layout Heatmap<br/>[HeatmapPage.jsx]"]
  node_lookup["SKU Lookup<br/>[LookupPage.jsx]"]
  node_whatif["Demand Scenarios<br/>[WhatIfPage.jsx]"]
  node_reslotui["Move Plan View<br/>[ReslotPage.jsx]"]
end

subgraph group_service["API Service"]
  node_api["REST API<br/>[main.py]"]
end

subgraph group_optimization["Optimization Engine"]
  node_validator["Data Validation<br/>[validator.py]"]
  node_strategies["Slotting Strategies<br/>[strategies.py]"]
  node_forecast["Demand Forecast<br/>[forecast.py]"]
  node_affinity["Basket Affinity<br/>[affinity.py]"]
  node_metrics["Operational Metrics<br/>[metrics.py]"]
  node_generator["Synthetic Data<br/>[data_gen.py]"]
end

subgraph group_operations["Warehouse Operations"]
  node_explain["Placement Explanation<br/>[explain.py]"]
  node_reslot["Move ROI Planner<br/>[reslot.py]"]
  node_csvdata[("Warehouse CSV Data")]
end

node_operator(("Warehouse Operator"))

node_operator -->|"uses"| node_app
node_app -->|"renders"| node_upload
node_app -->|"renders"| node_leaderboard
node_app -->|"renders"| node_heatmap
node_app -->|"renders"| node_lookup
node_app -->|"renders"| node_whatif
node_app -->|"renders"| node_reslotui
node_upload -->|"uploads CSV"| node_api
node_leaderboard -->|"requests comparison"| node_api
node_leaderboard -.->|"requests optimization"| node_api
node_heatmap -->|"requests layouts"| node_api
node_lookup -->|"requests recommendation"| node_api
node_whatif -->|"submits scenario"| node_api
node_reslotui -.->|"requests move plan"| node_api
node_api -.->|"validates uploads"| node_validator
node_api -.->|"runs optimization"| node_strategies
node_api -.->|"reports metrics"| node_metrics
node_api -.->|"gets rationale"| node_explain
node_api -.->|"gets move plan"| node_reslot
node_strategies -->|"uses forecasts"| node_forecast
node_strategies -->|"uses affinity search"| node_affinity
node_strategies -->|"uses metrics"| node_metrics
node_affinity -->|"checks feasibility"| node_metrics
node_generator -.->|"generates datasets"| node_csvdata
node_validator -.->|"cleans datasets"| node_csvdata

click node_app "web/src/App.jsx"
click node_upload "web/src/pages/UploadPage.jsx"
click node_leaderboard "web/src/pages/LeaderboardPage.jsx"
click node_heatmap "web/src/pages/HeatmapPage.jsx"
click node_lookup "web/src/pages/LookupPage.jsx"
click node_whatif "web/src/pages/WhatIfPage.jsx"
click node_reslotui "web/src/pages/ReslotPage.jsx"
click node_api "api/main.py"
click node_validator "engine/validator.py"
click node_strategies "engine/strategies.py"
click node_forecast "engine/forecast.py"
click node_affinity "engine/affinity.py"
click node_metrics "engine/metrics.py"
click node_generator "engine/data_gen.py"
click node_explain "engine/explain.py"
click node_reslot "engine/reslot.py"
click node_csvdata "data"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_app,node_upload,node_leaderboard,node_heatmap,node_lookup,node_whatif,node_reslotui toneBlue
class node_api toneAmber
class node_validator,node_strategies,node_forecast,node_affinity,node_metrics,node_generator toneMint
class node_explain,node_reslot,node_csvdata toneRose
class node_operator toneIndigo
```

---

## Quickstart

In PowerShell, clone the repository and run the backend commands from its root. The repository root contains `api/`, `engine/`, `data/`, `tests/`, and `web/` directly.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.11 if they are not already available.

### Backend

```bash
git clone https://github.com/mithunaradya-ai/teammitras-solo.git
cd teammitras-solo
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

The API is available at `http://localhost:8000` and its interactive docs at `/docs`.

### Dashboard

In a second terminal, from the repository root:

```bash
cd web
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`. Node.js and npm are required for the dashboard.

## How It Works

1. On startup, the API loads the sample product, location, and order CSVs from `data/`.
2. The validation engine checks uploaded CSVs and updates the API's in-memory datasets.
3. The strategy engine matches products to feasible locations, scoring door travel from weekly demand and Manhattan distance. The forecast-and-affinity strategy adds a next-week demand estimate and attempts feasible swaps that trade off predicted door travel against co-order pair distance.
4. The React dashboard calls the API to show comparisons, layout maps, SKU explanations, demand scenarios, and suggested moves.

The app is a local prototype: it uses generated sample data by default, keeps uploaded data in memory, and does not connect to a warehouse system or execute inventory moves.

## Using the Prototype

Keep both terminals running while using the dashboard:

1. **Leaderboard:** compare the bundled baseline, greedy, Hungarian, and forecast-plus-affinity plans. The table reports picking distance, feasibility, space utilization, estimated INR labor cost, and average co-order pair distance. Use **Apply** to set a strategy as the API's active plan.
2. **Heatmap:** compare the baseline and optimized warehouse layouts.
3. **Product Lookup:** search for a SKU such as `P001` to see its recommended location and placement explanation.
4. **What-If Simulator:** adjust category demand multipliers or select a preset to recalculate an illustrative plan.
5. **Re-slotting Plan:** review the move list and illustrative cost/payback estimate; download the recommendations as CSV. This is a plan only—the prototype does not move inventory.
6. **Ingestion & Audit:** choose a data type, then upload its CSV to run the validator and inspect its audit summary. The bundled examples are `data/products_dirty.csv`, `data/locations_dirty.csv`, and `data/orders_dirty.csv`.

Uploaded data and the active plan are held in API memory, not persisted to a database. Restarting the API reloads the bundled sample datasets. Financial values and the synthetic benchmark are illustrative; use measured warehouse data and costs before making operational decisions.

### Tests and benchmarks

From the repository root:

```bash
.\.venv\Scripts\python.exe -m pytest tests -v
.\.venv\Scripts\python.exe -m engine.stress_benchmark
```

---

## System Architecture

```
.
├── engine/              # Pure Python deterministic optimization algorithms
│   ├── stress_benchmark.py # Tight-capacity greedy vs Hungarian benchmark
│   ├── data_gen.py      # Synthetic generator (seed 42, 300 SKUs, 320 bins, Pareto)
│   ├── validator.py     # Data cleaner & audit logging
│   ├── metrics.py       # 6 core warehouse operational metrics
│   ├── forecast.py      # Exponential smoothing (Holt 12-week lookahead)
│   ├── affinity.py      # Basket lift calculation & deterministic swap search
│   ├── strategies.py    # Baseline, ABC-Greedy, Hungarian, PuLP ILP, Forecast+Affinity
│   ├── explain.py       # Plain-English SKU placement audit generator
│   └── reslot.py        # Financial ROI & 1.3-day payback calculator
├── api/
│   └── main.py          # FastAPI REST endpoints (Upload, Optimize, Compare, Heatmap)
├── web/                 # React 19 + Vite + Tailwind + Plotly.js Dark Dashboard
├── data/                # Benchmark clean & dirty CSVs
├── tests/               # Constraint verification & reproducibility test suite
├── requirements.txt     # Python runtime, API, and test dependencies
├── README.md            # Setup guide & CLI instructions
└── REPORT.md            # Empirical performance report from real computed metrics
```

---

## Standalone CLI Verification Commands

Run from the repository root:

```bash
# Generate synthetic dataset (seed 42)
.\.venv\Scripts\python.exe engine/data_gen.py

# Run Data Validator on dirty dataset
.\.venv\Scripts\python.exe engine/validator.py

# Benchmark all 4 optimization strategies
.\.venv\Scripts\python.exe engine/strategies.py

# Run Explainability engine
.\.venv\Scripts\python.exe engine/explain.py

# Compute Re-slotting plan & payback ROI
.\.venv\Scripts\python.exe engine/reslot.py

# Run complete automated test suite
.\.venv\Scripts\python.exe -m pytest tests -v
```
