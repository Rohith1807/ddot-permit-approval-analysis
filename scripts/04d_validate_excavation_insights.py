
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/fy2026_permit_categorized.parquet"
OUTPUTS = ROOT / "outputs"

df = pd.read_parquet(DATA)
exc = df[df["PermitCategory"] == "Excavation"].copy()

# 1. Review zero business-day approvals
valid = df[df["BusinessDaysToApproval"].notna()].copy()
zero = valid[valid["BusinessDaysToApproval"] == 0].copy()

same_calendar_day = (
    zero["ApplicationDate"].dt.date
    == zero["LastApprovalDate"].dt.date
)

print("1. ZERO BUSINESS-DAY APPROVALS")
print(f"Zero business-day permits: {len(zero):,}")
print(f"Same-calendar-day: {same_calendar_day.sum():,}")
print(f"Different-calendar-day: {(~same_calendar_day).sum():,}")

# 2. Examine activity overlap
ACTIVITIES = {
    "Water Service Repair": "Repair Water Service Lateral",
    "Single Test Pit": "Boring Test Pit (Single)",
    "Additional Test Pit": "Boring Test Pit (Each Add'l)",
    "Gas Main Repair": "Repair Gas Main Line",
    "Gas Connection": "Gas Connection (Trench)"
}

def activity_set(value):
    if pd.isna(value):
        return set()
    return {
        part.strip().split(";", 1)[1].strip()
        for part in str(value).split(",")
        if part.strip().startswith("Excavation;")
    }

exc["ActivitySet"] = exc["TypeDetailNames"].apply(activity_set)

print("\n2. SELECTED ACTIVITY OVERLAPS")

for label_a, activity_a in ACTIVITIES.items():
    for label_b, activity_b in ACTIVITIES.items():
        if label_a >= label_b:
            continue

        overlap = exc["ActivitySet"].apply(
            lambda s: activity_a in s and activity_b in s
        ).sum()

        if overlap:
            print(f"{label_a} + {label_b}: {overlap:,}")

# 3. Export permits with zero business days for inspection
zero[[
    "PermitNumber",
    "ApplicationDate",
    "LastApprovalDate",
    "BusinessDaysToApproval",
    "PermitCategory"
]].to_csv(
    OUTPUTS / "zero_business_day_review.csv",
    index=False
)

print("\nValidation completed.")
