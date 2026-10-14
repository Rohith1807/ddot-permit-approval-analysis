"""
Calculates approval duration for each unique permit using validated dates.
Excludes weekends and observed DC holidays, tests calculation accuracy,
and establishes the overall approval-performance baseline.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

PROCESSED.mkdir(parents=True, exist_ok=True)
OUTPUTS.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(
    PROCESSED / "fy2026_new_permit_master.parquet"
)

# Official observed DC government holidays in FY2026
HOLIDAYS = [
    "2025-10-13",
    "2025-11-11",
    "2025-11-27",
    "2025-12-25",
    "2026-01-01",
    "2026-01-19",
    "2026-02-16",
    "2026-04-16",
    "2026-05-25",
    "2026-06-19",
    "2026-07-03",
    "2026-09-07",
]

calendar = np.busdaycalendar(
    weekmask="1111100",
    holidays=np.array(HOLIDAYS, dtype="datetime64[D]")
)

# Protect against double-counting and missing dates
assert df["PermitNumber"].is_unique
assert len(df) == 2997

df["BusinessDaysToApproval"] = np.nan

valid = (
    df["ApplicationDate"].notna()
    & df["LastApprovalDate"].notna()
    & (df["LastApprovalDate"] >= df["ApplicationDate"])
)

# Convert Eastern timestamps to calendar dates.
start = np.array(
    [
        d.date().isoformat()
        for d in df.loc[valid, "ApplicationDate"]
    ],
    dtype="datetime64[D]"
)

end = np.array(
    [
        d.date().isoformat()
        for d in df.loc[valid, "LastApprovalDate"]
    ],
    dtype="datetime64[D]"
)

# Exclude application day; include approval day.
business_days = np.busday_count(
    start + np.timedelta64(1, "D"),
    end + np.timedelta64(1, "D"),
    busdaycal=calendar
)

df.loc[valid, "BusinessDaysToApproval"] = business_days

# Independent spot-checks of calculation logic
def business_day_test(start_date, end_date):
    return int(np.busday_count(
        np.datetime64(start_date) + np.timedelta64(1, "D"),
        np.datetime64(end_date) + np.timedelta64(1, "D"),
        busdaycal=calendar
    ))

assert business_day_test("2026-03-02", "2026-03-02") == 0
assert business_day_test("2026-03-06", "2026-03-09") == 1
assert business_day_test("2026-04-15", "2026-04-17") == 1
assert business_day_test("2026-07-02", "2026-07-06") == 1
assert business_day_test("2026-03-02", "2026-03-04") == 2

# Data integrity checks
assert df["BusinessDaysToApproval"].notna().sum() == valid.sum()
assert (df.loc[valid, "BusinessDaysToApproval"] >= 0).all()
assert df["BusinessDaysToApproval"].isna().sum() == 5

# Save analysis dataset
df.to_parquet(
    PROCESSED / "fy2026_permit_approval_analysis.parquet",
    index=False
)

# Save an auditable holiday reference table
pd.DataFrame({"HolidayDate": HOLIDAYS}).to_csv(
    OUTPUTS / "dc_fy2026_holidays.csv",
    index=False
)

print("=" * 55)
print("BUSINESS-DAY APPROVAL VALIDATION")
print("=" * 55)

print(f"Total unique permits: {len(df):,}")
print(f"Valid approval durations: {valid.sum():,}")
print(
    "Missing approval durations: "
    f"{df['BusinessDaysToApproval'].isna().sum():,}"
)
print(
    "Average business days: "
    f"{df['BusinessDaysToApproval'].mean():.2f}"
)
print(
    "Median business days: "
    f"{df['BusinessDaysToApproval'].median():.2f}"
)
print(
    "Minimum business days: "
    f"{df['BusinessDaysToApproval'].min():.0f}"
)
print(
    "Maximum business days: "
    f"{df['BusinessDaysToApproval'].max():.0f}"
)
print(
    "90th percentile: "
    f"{df['BusinessDaysToApproval'].quantile(.90):.2f}"
)
print(
    "Same-day approvals: "
    f"{(df['BusinessDaysToApproval'] == 0).sum():,}"
)
print("\nAll validation tests passed.")
