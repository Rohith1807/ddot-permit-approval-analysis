"""
Explores available permit classifications after establishing the overall
approval baseline. Identifies overlapping work categories and detailed
activities to inform a defensible segmentation strategy.
"""

from pathlib import Path
from collections import Counter
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

df = pd.read_parquet(
    ROOT / "data/processed/fy2026_permit_approval_analysis.parquet"
)

OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)

assert df["PermitNumber"].is_unique

print("=" * 55)
print("PERMIT CATEGORY EXPLORATION")
print("=" * 55)

# 1. Existing type descriptions
for col in [
    "PermitTypeDescription",
    "TypeDetailNames"
]:
    print(f"\n1. {col}: Top 15 values")
    print(
        df[col].fillna("<MISSING>")
        .value_counts()
        .head(15)
        .to_string()
    )

# 2. Identify broad categories from activity names
category_counter = Counter()
activity_counter = Counter()
permit_category_count = Counter()

for value in df["TypeDetailNames"].dropna():
    activities = [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]

    categories = set()

    for activity in activities:
        activity_counter[activity] += 1

        if ";" in activity:
            category = activity.split(";", 1)[0].strip()
        else:
            category = "Unclassified"

        categories.add(category)

    for category in categories:
        category_counter[category] += 1

    permit_category_count[len(categories)] += 1

print("\n2. BROAD ACTIVITY CATEGORIES")
for category, count in category_counter.most_common():
    print(f"{category}: {count:,}")

print("\n3. CATEGORIES PER PERMIT")
for number, count in sorted(permit_category_count.items()):
    print(f"{number} categories: {count:,} permits")

print("\n4. TOP 20 DETAILED ACTIVITIES")
for activity, count in activity_counter.most_common(20):
    print(f"{count:,} | {activity}")

# 5. Identify permit-type indicator fields
indicator_fields = [
    col for col in df.columns
    if col.startswith("Is")
]

print("\n5. AVAILABLE PERMIT INDICATOR FIELDS")
for col in indicator_fields:
    print(f"\n{col}")
    print(
        df[col].value_counts(dropna=False)
        .head(10)
        .to_string()
    )

# Save profiles
pd.DataFrame(
    category_counter.items(),
    columns=["Category", "PermitCount"]
).sort_values(
    "PermitCount", ascending=False
).to_csv(
    OUTPUTS / "broad_category_profile.csv",
    index=False
)

pd.DataFrame(
    activity_counter.items(),
    columns=["Activity", "Count"]
).sort_values(
    "Count", ascending=False
).to_csv(
    OUTPUTS / "detailed_activity_profile.csv",
    index=False
)

print("\nCategory exploration completed.")
