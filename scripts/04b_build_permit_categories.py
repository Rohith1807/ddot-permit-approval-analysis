
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

df = pd.read_parquet(
    PROCESSED / "fy2026_permit_approval_analysis.parquet"
)

# Known broad permit categories
KNOWN_CATEGORIES = {
    "Excavation",
    "Fixture",
    "Paving",
    "Over Head Work",
    "Projections",
    "Mega Projects",
    "Landscaping"
}

def extract_categories(value):
    if pd.isna(value) or not str(value).strip():
        return set()

    categories = set()

    for activity in str(value).split(","):
        activity = activity.strip()

        if not activity:
            continue

        if ";" not in activity:
            categories.add("Unclassified")
            continue

        category = activity.split(";", 1)[0].strip()

        if category in KNOWN_CATEGORIES:
            categories.add(category)
        else:
            categories.add("Unclassified")

    return categories


def assign_category(value):
    categories = extract_categories(value)
    known = categories - {"Unclassified"}

    if len(known) > 1:
        return "Mixed Work Types"

    # Do not silently combine unknown with known categories.
    if "Unclassified" in categories and known:
        return "Mixed / Unclassified"

    if len(known) == 1:
        return next(iter(known))

    return "Unclassified"


df["PermitCategory"] = (
    df["TypeDetailNames"].apply(assign_category)
)

# Check classification against available binary flags
FLAG_MAPPING = {
    "Excavation": "IsExcavation",
    "Fixture": "IsFixture",
    "Paving": "IsPaving",
    "Over Head Work": "IsOverHeadWork",
    "Projections": "IsProjections",
    "Landscaping": "IsLandscaping"
}

print("CATEGORY VS INDICATOR VALIDATION")

for category, flag in FLAG_MAPPING.items():
    if flag not in df.columns:
        continue

    parsed = df["TypeDetailNames"].apply(
        lambda x: category in extract_categories(x)
    )

    flagged = (
        pd.to_numeric(df[flag], errors="coerce")
        .eq(1)
    )

    disagreements = int((parsed != flagged).sum())

    print(f"{category}: {disagreements} disagreements")


# Validate one row per permit
assert df["PermitNumber"].is_unique
assert df["PermitCategory"].notna().all()
assert len(df) == 2997

# Save enriched dataset
df.to_parquet(
    PROCESSED / "fy2026_permit_categorized.parquet",
    index=False
)

# Summary statistics by category
summary = (
    df.groupby("PermitCategory", dropna=False)
    .agg(
        TotalPermits=("PermitNumber", "nunique"),
        ValidApprovals=("BusinessDaysToApproval", "count"),
        AverageDays=("BusinessDaysToApproval", "mean"),
        MedianDays=("BusinessDaysToApproval", "median"),
        P90Days=(
            "BusinessDaysToApproval",
            lambda x: x.quantile(.90)
        ),
        SameDayApprovals=(
            "BusinessDaysToApproval",
            lambda x: (x == 0).sum()
        )
    )
    .reset_index()
)

summary["MissingApprovals"] = (
    summary["TotalPermits"] - summary["ValidApprovals"]
)

summary = summary.sort_values(
    "TotalPermits", ascending=False
)

summary.to_csv(
    OUTPUTS / "permit_category_performance.csv",
    index=False
)

print("\nPERMIT CATEGORY PERFORMANCE")
print(summary.round(2).to_string(index=False))

print("\nVALIDATION")
print("Total permits:", summary["TotalPermits"].sum())
print("Valid approvals:", summary["ValidApprovals"].sum())
print("Missing approvals:", summary["MissingApprovals"].sum())

assert summary["TotalPermits"].sum() == 2997
assert summary["ValidApprovals"].sum() == 2992
assert summary["MissingApprovals"].sum() == 5

print("\nAll population reconciliation checks passed.")
