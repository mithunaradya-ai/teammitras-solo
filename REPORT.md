# SlotIQ: Engineering & Empirical Performance Report

## 1. Scope

SlotIQ assigns SKUs to warehouse locations using weekly demand, distance to the dispatch point, physical fit, special-handling requirements, and location availability. It also forecasts next-week demand and measures how close products appearing in the same order are placed.

This report does not repeat an unsourced industry claim about picking's share of operating labor. Results below are deterministic outputs from the included synthetic data and are not a substitute for a measured warehouse pilot.

## 2. Method

- **ABC-Greedy** orders SKUs by average weekly demand and assigns each to the nearest currently available feasible slot.
- **Hungarian** minimizes total demand-weighted door distance for a one-SKU-per-slot assignment, subject to the modeled product/location feasibility pairs. It is optimal for this assignment objective when a feasible full matching exists; it is not a multi-item bin-packing solver.
- **Forecast + Affinity** forecasts demand from 12 weeks of history, starts with a Hungarian assignment, then makes feasible swaps that trade off forecast-weighted door distance and co-order proximity.
- **Affinity distance** is the co-order-frequency-weighted mean Manhattan distance between the assigned locations of distinct products found in the same order. Each product pair is counted once per order.

## 3. Assumptions

- **Walking labor cost:** ₹0.03 per meter (₹30 per kilometer), an illustrative model assumption rather than a sourced industry rate.
- **Physical relocation cost:** ₹12 per SKU move, also a modeling assumption.
- **Operating schedule:** 5 working days per week.
- **Travel model:** Manhattan distance from the dispatch point at `(0, 0)`; it does not model picker routes, congestion, or one-way aisles.
- The synthetic generator uses seed `42`; the standard set contains 300 products, 320 locations, and 5,000 order lines.

## 4. Standard Benchmark (Seed 42)

| Strategy | Weekly pick distance (m) | Feasibility | Space utilization | Weekly labor cost (₹) | Mean co-order pair distance (m) | Moves |
|---|---:|---:|---:|---:|---:|---:|
| Baseline (random) | 172,603.25 | 82.00% | 11.47% | 5,178.10 | 22.65 | 0 |
| ABC-Greedy | 78,810.55 | 100.00% | 11.43% | 2,364.32 | 14.79 | 299 |
| Hungarian | 78,788.85 | 100.00% | 11.43% | 2,363.67 | 14.75 | 300 |
| Forecast + Affinity | 78,810.20 | 100.00% | 11.43% | 2,364.31 | 14.58 | 298 |

The forecast-and-affinity strategy does **not** beat Hungarian on door-picking distance: it is 21.35 m/week higher (about 0.03%). The affinity measure does show a separate effect: its 14.58 m mean co-order pair distance is 0.17 m lower than Hungarian and 8.07 m (35.6%) lower than the random baseline. Its gain over the demand-only greedy result is small (0.21 m, about 1.4%); this synthetic run does not show a large incremental affinity advantage.

Space utilization falls from 11.47% in the baseline to 11.43% after slotting. It did not improve. The sample warehouse is oversized relative to the stored product volume, so utilization is not a demonstrated benefit of this experiment.

### Tight-capacity stress benchmark

Reproduce this run from the repository root with:

```bash
.\.venv\Scripts\python.exe -m engine.stress_benchmark
```

The fixed-seed scenario has 300 products and 320 locations. It makes 40 non-special-handling SKUs too large for medium locations (65 × 55 × 50 cm), while only 50 of the nearest locations are large enough. ABC-Greedy fills the closest feasible bins for higher-demand flexible products first and leaves 40 products unassigned. Hungarian reserves enough large locations for those constrained SKUs and returns a complete feasible plan.

| Strategy | Assigned / products | Weekly pick distance (m) | Feasibility |
|---|---:|---:|---:|
| ABC-Greedy | 260 / 300 | Not comparable: incomplete plan | Incomplete |
| Hungarian | 300 / 300 | 96,823.95 | 100.00% |

The greedy distance is intentionally not reported: it covers only its 260 assigned products and would misleadingly look smaller because it omits 40 products. This stress result demonstrates Hungarian's advantage in producing a complete feasible assignment when size constraints bind; it does not claim a lower distance than a complete greedy plan.

## 5. Illustrative Relocation Payback

Using the Hungarian standard result against the baseline:

- **Weekly walking distance avoided:** 93,814.40 m.
- **Daily walking distance avoided:** 18,762.88 m over 5 operating days.
- **Illustrative daily labor value:** ₹562.89 at ₹0.03/m.
- **Relocation estimate:** ₹3,600 (300 moves × ₹12).
- **Illustrative payback:** 6.4 operating days.

This estimate is assumption-sensitive. It treats every avoided meter as labor value at a constant rate and does not include route interactions, implementation disruption, or measured wage data; it is not a guaranteed saving.

## 6. Limitations and Next Steps

- The stress case models one SKU per slot; the separate ILP prototype handles multi-item capacity only on a bounded subset.
- Manhattan distance assumes direct rectilinear travel and omits aisle topology, picker routing, congestion, and one-way traffic.
- Validate the synthetic results against a warehouse's actual layout, order history, labor cost, and relocation effort before making financial claims.
- Future work includes picker-route-aware optimization and evaluating affinity/forecast outcomes on held-out real order data.
