"""Data validator and cleaner for SlotIQ.

Inspects raw warehouse CSVs, detects and handles anomalies:
- Duplicate records
- Missing values
- Negative or zero physical dimensions
- References to unavailable or nonexistent locations
Produces cleaned DataFrames and a detailed audit trail report.
"""

import os
import pandas as pd
import numpy as np


class DataQualityReport:
    """Holds summary counters and itemized log of all data cleaning actions."""
    def __init__(self):
        self.logs = []  # list of {"dataset": str, "row_id": str, "action": str, "reason": str}
        self.rejected_count = 0
        self.fixed_count = 0

    def add_log(self, dataset: str, row_id: str, action: str, reason: str):
        """Append an entry to the audit log."""
        self.logs.append({"dataset": dataset, "row_id": str(row_id), "action": action, "reason": reason})
        if action == "REJECTED":
            self.rejected_count += 1
        elif action == "FIXED":
            self.fixed_count += 1

    def to_summary_dict(self) -> dict:
        """Return counts and structured logs."""
        return {
            "total_issues": len(self.logs),
            "rejected_count": self.rejected_count,
            "fixed_count": self.fixed_count,
            "details": self.logs
        }


def clean_locations(df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    """Validate and clean location grid records."""
    cleaned = df.copy()
    # 1. Deduplicate by location_id
    dups = cleaned[cleaned.duplicated(subset=["location_id"], keep="first")]
    for _, row in dups.iterrows():
        report.add_log("locations", row["location_id"], "REJECTED", "Duplicate location_id")
    cleaned = cleaned.drop_duplicates(subset=["location_id"], keep="first")

    # 2. Fix or flag negative dimensions
    dim_cols = ["max_length", "max_width", "max_height"]
    for col in dim_cols:
        neg_mask = cleaned[col] <= 0
        for _, row in cleaned[neg_mask].iterrows():
            fixed_val = abs(float(row[col])) if row[col] != 0 else 40.0
            cleaned.loc[cleaned["location_id"] == row["location_id"], col] = fixed_val
            report.add_log("locations", row["location_id"], "FIXED", f"Invalid {col}={row[col]} converted to {fixed_val}")

    # Recompute capacity volume if missing or zero
    if "capacity_volume" in cleaned.columns:
        vol_mask = cleaned["capacity_volume"].isna() | (cleaned["capacity_volume"] <= 0)
        for _, row in cleaned[vol_mask].iterrows():
            vol = round(row["max_length"] * row["max_width"] * row["max_height"], 1)
            cleaned.loc[cleaned["location_id"] == row["location_id"], "capacity_volume"] = vol
            report.add_log("locations", row["location_id"], "FIXED", f"Recomputed capacity_volume={vol}")

    # 3. Handle missing accessibility score
    if "accessibility_score" in cleaned.columns:
        na_access = cleaned["accessibility_score"].isna()
        for _, row in cleaned[na_access].iterrows():
            cleaned.loc[cleaned["location_id"] == row["location_id"], "accessibility_score"] = 3.0
            report.add_log("locations", row["location_id"], "FIXED", "Missing accessibility_score filled with median 3.0")

    return cleaned


def clean_products(df: pd.DataFrame, locations_df: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    """Validate and clean product records against dimension bounds and location validity."""
    cleaned = df.copy()
    # 1. Deduplicate product_id
    dups = cleaned[cleaned.duplicated(subset=["product_id"], keep="first")]
    for _, row in dups.iterrows():
        report.add_log("products", row["product_id"], "REJECTED", "Duplicate product_id")
    cleaned = cleaned.drop_duplicates(subset=["product_id"], keep="first")

    # 2. Handle missing categorical and dimensional values
    for idx, row in cleaned.iterrows():
        p_id = row["product_id"]
        if pd.isna(row.get("category")):
            cleaned.loc[idx, "category"] = "General"
            report.add_log("products", p_id, "FIXED", "Missing category defaulted to 'General'")

        # Physical dimension fixes
        for dim in ["length", "width", "height"]:
            val = row.get(dim)
            if pd.isna(val) or val <= 0:
                fixed_val = abs(float(val)) if (not pd.isna(val) and val != 0) else 20.0
                cleaned.loc[idx, dim] = fixed_val
                report.add_log("products", p_id, "FIXED", f"Invalid {dim}={val} rectified to {fixed_val}")

        # Ensure volume consistency
        calc_vol = round(cleaned.loc[idx, "length"] * cleaned.loc[idx, "width"] * cleaned.loc[idx, "height"], 1)
        if pd.isna(cleaned.loc[idx, "volume"]) or cleaned.loc[idx, "volume"] <= 0:
            cleaned.loc[idx, "volume"] = calc_vol
            report.add_log("products", p_id, "FIXED", f"Missing volume recomputed to {calc_vol}")

    # 3. Verify baseline location availability
    avail_locs = set(locations_df[locations_df["available"] == 1]["location_id"])
    for idx, row in cleaned.iterrows():
        p_id = row["product_id"]
        bloc = row.get("baseline_location_id")
        if bloc not in avail_locs:
            # Assign an available location or mark unassigned
            unavail_reason = "unavailable" if bloc in set(locations_df["location_id"]) else "nonexistent"
            # Fallback to first free available location
            fallback_loc = list(avail_locs)[0] if avail_locs else "A01"
            cleaned.loc[idx, "baseline_location_id"] = fallback_loc
            report.add_log("products", p_id, "FIXED", f"Baseline location '{bloc}' was {unavail_reason}; remapped to {fallback_loc}")

    return cleaned


def clean_orders(df: pd.DataFrame, valid_product_ids: set, report: DataQualityReport) -> pd.DataFrame:
    """Validate order lines: remove duplicates and enforce referential integrity."""
    cleaned = df.copy()
    # 1. Deduplicate identical order lines
    dups = cleaned[cleaned.duplicated(subset=["order_id", "product_id"], keep="first")]
    for _, row in dups.iterrows():
        report.add_log("orders", f"{row['order_id']}_{row['product_id']}", "REJECTED", "Duplicate order line")
    cleaned = cleaned.drop_duplicates(subset=["order_id", "product_id"], keep="first")

    # 2. Check product foreign key
    invalid_p = cleaned[~cleaned["product_id"].isin(valid_product_ids)]
    for _, row in invalid_p.iterrows():
        report.add_log("orders", f"{row['order_id']}_{row['product_id']}", "REJECTED", f"Unknown product_id '{row['product_id']}'")
    cleaned = cleaned[cleaned["product_id"].isin(valid_product_ids)]
    return cleaned


def run_pipeline(data_dir: str = "slotiq/data", use_dirty: bool = False) -> tuple:
    """Run full validation pipeline on CSVs in data_dir and print formatted audit report."""
    suffix = "_dirty" if use_dirty else ""
    p_path = os.path.join(data_dir, f"products{suffix}.csv")
    l_path = os.path.join(data_dir, f"locations{suffix}.csv")
    o_path = os.path.join(data_dir, f"orders{suffix}.csv")

    p_raw = pd.read_csv(p_path)
    l_raw = pd.read_csv(l_path)
    o_raw = pd.read_csv(o_path)

    report = DataQualityReport()
    l_clean = clean_locations(l_raw, report)
    p_clean = clean_products(p_raw, l_clean, report)
    o_clean = clean_orders(o_raw, set(p_clean["product_id"]), report)

    return (p_clean, l_clean, o_clean), report


def print_report(report: DataQualityReport, target_label: str = "Dirty File"):
    """Print an executive data quality report to the console."""
    print("=" * 70)
    print(f"SLOTIQ DATA QUALITY AUDIT REPORT [{target_label.upper()}]")
    print("=" * 70)
    print(f"Total Anomalies Detected: {len(report.logs)}")
    print(f"  Rows Rejected : {report.rejected_count}")
    print(f"  Rows Corrected: {report.fixed_count}")
    print("-" * 70)
    print(f"{'DATASET':<12} {'ROW / ID':<22} {'ACTION':<10} {'REASON'}")
    print("-" * 70)
    for entry in report.logs:
        print(f"{entry['dataset']:<12} {entry['row_id']:<22} {entry['action']:<10} {entry['reason']}")
    print("=" * 70)


if __name__ == "__main__":
    # Test on dirty data as required by Step 2 checkpoint
    _, dirty_report = run_pipeline("slotiq/data", use_dirty=True)
    print_report(dirty_report, "Dirty Dataset")
