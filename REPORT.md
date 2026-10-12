# SlotIQ: Engineering & Empirical Performance Report

## 1. Problem Understanding
Warehouse order-picking accounts for over 50% to 55% of total operating labor expenses in distribution facilities. Suboptimal slotting—where fast-moving, high-velocity stock keeping units (SKUs) are marooned in remote racks—forces pickers to walk tens of unnecessary kilometers every shift. SlotIQ is designed to optimize slot assignments under strict physical bin constraints (3D bounding boxes, volume limits, special handling refrigeration/fragility requirements, and bay availability) using mathematically provable optimization and co-purchase affinity.

---

## 2. System Architecture
SlotIQ features a modular decoupling between compute and presentation:
- **Core Engine (`/engine`)**: Pure Python 3.11 with NumPy, SciPy, and PuLP. Independent of Web/API frameworks for execution in automated pipelines or edge terminals.
- **REST Service (`/api`)**: High-throughput FastAPI application exposing upload cleaners, live solvers, and what-if simulation endpoints.
- **Frontend Dashboard (`/web`)**: Dark, responsive React 19 + Tailwind CSS + Plotly.js interface providing spatial heatmaps, ROI metrics, and product audit tools.

---

## 3. Methodology & Algorithms
1. **ABC-Greedy**: Segregates SKUs into Pareto tiers (A: 80% volume, B: 15%, C: 5%) and greedily allocates high-demand items to the nearest feasible bin.
2. **Optimal Hungarian (`scipy.optimize.linear_sum_assignment`)**: Models warehouse slotting as minimum-weight bipartite matching over cost matrix $C_{ij} = \text{Demand}_i \times \text{Distance}_j$. Infeasible pairs are penalized with Big-$M$ ($10^8$), guaranteeing $O(V^3)$ polynomial-time optimality.
3. **Multi-Capacity ILP (`PuLP CBC`)**: Formulates multi-item bin consolidation as a mixed integer program enforcing linear volume constraints.
4. **Forecast + Affinity (AI Differentiator)**:
   - **Holt Exponential Smoothing**: Computes 12-week smoothed velocity ($\alpha=0.3$) for forward-looking demand.
   - **Co-Pick Affinity Lift**: Extracts market-basket co-occurrences from 5,000 order lines to calculate Lift:
     $$\text{Lift}(A, B) = \frac{P(A \cap B)}{P(A) \cdot P(B)}$$
   - **Deterministic Swap Search**: Evaluates local slot swaps that minimize aggregate picker transit and clustering penalties without violating feasibility.

---

## 4. Documented Assumptions
- **Cost per Meter Walked**: \$0.15 / meter (standard warehouse picker labor cost benchmark).
- **Physical Relocation Cost**: \$12.00 / move (technician time for forklift transfer and barcode relabeling).
- **Operating Schedule**: 5 working days / week.
- **Distance Metric**: Manhattan travel distance $|x| + |y|$ from dispatch door at $(0, 0)$.

---

## 5. Experimental Results (Computed Numbers)
All metrics computed strictly from benchmark run with fixed seed `42` (300 products, 320 locations, 5,000 order lines, Pareto $\alpha=0.98$ where top 20% products generate 79.32% of picks):

| Strategy | Picking Dist (m/wk) | Distance Reduction | Feasibility | Space Util | Weekly Labor ($) | Physical Moves | Top 20% in Prime Slots |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline (Random)** | 172,603.25 m | 0.00% | 82.00% | 11.47% | \$25,890.49 | 0 | 20.00% |
| **ABC-Greedy** | 78,810.60 m | -54.34% | 100.00% | 11.43% | \$11,821.59 | 299 | 91.67% |
| **Optimal (Hungarian)** | 78,788.90 m | -54.35% | 100.00% | 11.43% | \$11,818.34 | 300 | 91.67% |
| **Forecast + Affinity** | 78,810.30 m | -54.34% | 100.00% | 11.43% | \$11,821.55 | 298 | 91.67% |

### Financial Payback & ROI Analysis
- **Weekly Walking Eliminated**: 93,814.35 meters / week (93.8 km/week).
- **Daily Walking Eliminated**: 18,762.87 meters / day (18.8 km/day).
- **Daily Financial Savings**: \$2,814.43 / day.
- **Total Relocation Investment**: \$3,600.00 (300 moves $\times$ \$12.00).
- **Payback Period**: **1.3 Operating Days**.

---

## 6. Limitations & Future Work
- **Limitations**: Current floor model computes Manhattan aisle distance assuming direct rectilinear pathways without unidirectional one-way aisle traffic constraints.
- **Future Work**: Integration of multi-picker routing heuristics (TSP / S-Shape routing) and automated dynamic slotting triggered by ERP inventory webhooks.
