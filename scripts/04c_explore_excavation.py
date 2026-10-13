
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/fy2026_permit_categorized.parquet"
OUTPUTS = ROOT / "outputs"

df = pd.read_parquet(DATA)
assert df["PermitNumber"].is_unique

# Use excavation-only permits for a clean comparison
exc = df[df["PermitCategory"] == "Excavation"].copy()

records = []

for _, row in exc.iterrows():
    raw = row["TypeDetailNames"]

    if pd.isna(raw):
        continue

    # Each activity is recorded as Category; Detail
    activities = {
        x.strip()
        for x in str(raw).split(",")
        if x.strip().startswith("Excavation;")
    }

    for activity in activities:
        records.append({
            "PermitNumber": row["PermitNumber"],
            "Activity": activity.split(";", 1)[1].strip(),
            "BusinessDays": row["BusinessDaysToApproval"]
        })

activity_df = pd.DataFrame(records)

assert not activity_df.duplicated(
    ["PermitNumber", "Activity"]
).any()

summary = (
    activity_df.groupby("Activity")
    .agg(
        TotalPermits=("PermitNumber", "nunique"),
        ValidApprovals=("BusinessDays", "count"),
        AverageDays=("BusinessDays", "mean"),
        MedianDays=("BusinessDays", "median"),
        P90Days=("BusinessDays", lambda x: x.quantile(.90)),
        SameDay=("BusinessDays", lambda x: (x == 0).sum())
    )
    .reset_index()
)

# Minimum sample size for initial exploration
summary = summary[
    summary["ValidApprovals"] >= 30
].sort_values("TotalPermits", ascending=False)

summary.to_csv(
    OUTPUTS / "excavation_activity_performance.csv",
    index=False
)

print("EXCAVATION ACTIVITY PERFORMANCE")
print(summary.round(2).to_string(index=False))

print("\nVALIDATION")
print("Excavation-only permits:", len(exc))
print("Distinct permits in activity table:",
      activity_df["PermitNumber"].nunique())
print("Permit-activity relationships:", len(activity_df))
print("Activities with 30+ valid approvals:", len(summary))
print(
    "Permits assigned multiple activities:",
    activity_df.groupby("PermitNumber").size().gt(1).sum()
)
