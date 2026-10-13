
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/fy2026_candidate_permits.parquet"
PROCESSED = ROOT / "data/processed"
OUTPUTS = ROOT / "outputs"

PROCESSED.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(RAW)

# Filter to new permits
new = df.loc[df["Renewal"] == 1].copy()

# Ensure permit identifiers are usable
assert new["PermitNumber"].notna().all()
assert new["PermitNumber"].astype(str).str.strip().ne("").all()

# Fields that must be consistent within a permit
consistent_fields = [
    "TrackingNumber",
    "ApplicationDate",
    "LastApprovalDate",
    "IssueDate",
    "Renewal",
    "RenewalDescription",
    "StatusDescription",
    "TypeDetailNames"
]

for field in consistent_fields:
    conflicting = (
        new.groupby("PermitNumber")[field]
        .nunique(dropna=False)
        .gt(1)
    )
    if conflicting.any():
        raise ValueError(
            f"Inconsistent {field} for "
            f"{conflicting.sum()} permits"
        )

# Explicit one-permit-per-row selection
# OBJECTID determines a reproducible representative record
permit_master = (
    new.sort_values("OBJECTID")
    .drop_duplicates(subset="PermitNumber", keep="first")
    .copy()
)

# Retain original number of source rows for auditing
row_counts = (
    new.groupby("PermitNumber")
    .size()
    .rename("SourceRowCount")
)

permit_master = permit_master.merge(
    row_counts,
    on="PermitNumber",
    how="left",
    validate="one_to_one"
)

# Clean permit-to-ward relationship
ward_links = new[
    ["PermitNumber", "WorkLocationWard"]
].copy()

ward_links["WorkLocationWard"] = (
    ward_links["WorkLocationWard"]
    .astype("string")
    .str.strip()
)

ward_links = (
    ward_links[
        ward_links["WorkLocationWard"].notna()
        & ward_links["WorkLocationWard"].ne("")
    ]
    .drop_duplicates()
)

# Summarize ward coverage for each permit
ward_summary = (
    ward_links.groupby("PermitNumber")["WorkLocationWard"]
    .agg(
        WardCount="nunique",
        WardList=lambda x: "; ".join(sorted(x.unique()))
    )
    .reset_index()
)

permit_master = permit_master.merge(
    ward_summary,
    on="PermitNumber",
    how="left",
    validate="one_to_one"
)

permit_master["WardCount"] = (
    permit_master["WardCount"].fillna(0).astype(int)
)

permit_master["WardList"] = (
    permit_master["WardList"].fillna("Unknown")
)

# Flag missing approval dates, do not impute them
permit_master["MissingApprovalDate"] = (
    permit_master["LastApprovalDate"].isna()
)

# Validate output
assert len(permit_master) == new["PermitNumber"].nunique()
assert permit_master["PermitNumber"].is_unique
assert permit_master["SourceRowCount"].sum() == len(new)

# Write outputs
permit_master.to_parquet(
    PROCESSED / "fy2026_new_permit_master.parquet",
    index=False
)

ward_links.to_csv(
    PROCESSED / "permit_ward_bridge.csv",
    index=False
)

print("=" * 55)
print("PERMIT MASTER VALIDATION")
print("=" * 55)
print(f"Original new-permit rows: {len(new):,}")
print(f"Unique permits: {len(permit_master):,}")
print(
    "Source rows reconciled: "
    f"{permit_master['SourceRowCount'].sum():,}"
)
print(
    "Permits missing approval date: "
    f"{permit_master['MissingApprovalDate'].sum():,}"
)
print(
    "Permits covering multiple wards: "
    f"{permit_master['WardCount'].gt(1).sum():,}"
)
print(
    "Permits without a known ward: "
    f"{permit_master['WardCount'].eq(0).sum():,}"
)
print(f"Distinct permit-ward links: {len(ward_links):,}")

print("\nPermit statuses:")
print(permit_master["StatusDescription"].value_counts())

print("\nPermit-level dataset saved successfully.")
