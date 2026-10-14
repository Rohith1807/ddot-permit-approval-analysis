"""
Prepares the validated analysis for Tableau using separate permit-level
and excavation activity datasets. Reconciles key metrics to ensure the
dashboard reproduces the Python results without unintended double-counting.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/fy2026_permit_categorized.parquet"
TABLEAU = ROOT / "data" / "tableau"

TABLEAU.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(SOURCE)

assert len(df) == 2997
assert df["PermitNumber"].is_unique
assert df["BusinessDaysToApproval"].notna().sum() == 2992

# -----------------------------
# 1. Permit-level Tableau data
# -----------------------------

master = df[[
    "PermitNumber",
    "TrackingNumber",
    "ApplicationDate",
    "LastApprovalDate",
    "IssueDate",
    "StatusDescription",
    "PermitCategory",
    "TypeDetailNames",
    "WorkLocationWard",
    "WardCount",
    "WardList",
    "BusinessDaysToApproval",
    "SourceRowCount"
]].copy()

# Use explicit date-only fields for Tableau
for col in [
    "ApplicationDate",
    "LastApprovalDate",
    "IssueDate"
]:
    master[col] = master[col].dt.strftime("%Y-%m-%d")

master["ApplicationMonth"] = pd.to_datetime(
    master["ApplicationDate"]
).dt.strftime("%Y-%m")

master["IssueMonth"] = pd.to_datetime(
    master["IssueDate"]
).dt.strftime("%Y-%m")

master["ApprovalDateAvailable"] = (
    master["BusinessDaysToApproval"].notna()
)

master["ZeroBusinessDays"] = (
    master["BusinessDaysToApproval"] == 0
)

master.to_csv(
    TABLEAU / "fy2026_permit_master.csv",
    index=False
)

# -----------------------------
# 2. Excavation activity table
# -----------------------------

exc = df[
    df["PermitCategory"] == "Excavation"
].copy()

records = []

for _, row in exc.iterrows():
    if pd.isna(row["TypeDetailNames"]):
        continue

    activities = {
        part.strip().split(";", 1)[1].strip()
        for part in str(row["TypeDetailNames"]).split(",")
        if part.strip().startswith("Excavation;")
    }

    for activity in activities:
        records.append({
            "PermitNumber": row["PermitNumber"],
            "ExcavationActivity": activity,
            "BusinessDaysToApproval": row["BusinessDaysToApproval"]
        })

activity_df = pd.DataFrame(records)

assert not activity_df.duplicated(
    ["PermitNumber", "ExcavationActivity"]
).any()

assert activity_df["PermitNumber"].nunique() == 2689
assert len(activity_df) == 4443

activity_df.to_csv(
    TABLEAU / "fy2026_excavation_activities.csv",
    index=False
)

# -----------------------------
# 3. Final reconciliation
# -----------------------------

print("TABLEAU DATA VALIDATION")
print("=" * 45)

print("Master rows:", len(master))
print("Unique permits:", master["PermitNumber"].nunique())
print(
    "Valid approvals:",
    master["BusinessDaysToApproval"].notna().sum()
)
print(
    "Overall average:",
    round(master["BusinessDaysToApproval"].mean(), 2)
)

print("\nActivity rows:", len(activity_df))
print(
    "Unique excavation permits:",
    activity_df["PermitNumber"].nunique()
)

assert round(master["BusinessDaysToApproval"].mean(), 2) == 22.23

print("\nTableau exports generated successfully.")
