"""
Investigates repeated permit numbers discovered during data validation.
Determines the true unit of analysis and checks whether repeated records
contain conflicting information before permit-level consolidation.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(
    ROOT / "data/raw/fy2026_candidate_permits.parquet"
)

new_df = df[df["Renewal"] == 1].copy()

print("=" * 55)
print("PERMIT-LEVEL GRANULARITY AUDIT")
print("=" * 55)

# Check identifier completeness
print("\n1. IDENTIFIER QUALITY")
for col in ["PermitNumber", "TrackingNumber"]:
    print(f"{col} missing: {new_df[col].isna().sum():,}")

# Count unique permits
counts = new_df.groupby(
    "PermitNumber", dropna=False
).size().sort_values(ascending=False)

print("\n2. RECORD COUNTS")
print(f"Total rows: {len(new_df):,}")
print(f"Unique permit numbers: {counts.size:,}")
print(f"Permits with multiple rows: {(counts > 1).sum():,}")
print(f"Extra rows beyond one per permit: {len(new_df) - counts.size:,}")

print("\n3. ROWS PER PERMIT DISTRIBUTION")
print(
    counts.value_counts()
    .sort_index()
    .rename_axis("rows_per_permit")
    .to_string()
)

# Check if repeated permits have conflicting values
fields = [
    "TrackingNumber",
    "ApplicationDate",
    "LastApprovalDate",
    "IssueDate",
    "RenewalDescription",
    "StatusDescription",
    "TypeDetailNames",
    "WorkLocationWard"
]

print("\n4. CONFLICTING VALUES WITHIN PERMITS")
for field in fields:
    if field in new_df.columns:
        distinct = new_df.groupby(
            "PermitNumber", dropna=False
        )[field].nunique(dropna=False)

        conflicts = (
            (counts > 1) & (distinct > 1)
        ).sum()

        print(f"{field}: {conflicts:,} permits")

# Example permits with repeated rows
repeated = counts[counts > 1].head(5).index

example_columns = [
    "OBJECTID",
    "PermitNumber",
    "TrackingNumber",
    "ApplicationDate",
    "LastApprovalDate",
    "IssueDate",
    "TypeDetailNames"
]

print("\n5. EXAMPLE REPEATED PERMITS")
print(
    new_df[
        new_df["PermitNumber"].isin(repeated)
    ][example_columns]
    .sort_values(["PermitNumber", "OBJECTID"])
    .to_string(index=False)
)

print("\nAudit complete.")
