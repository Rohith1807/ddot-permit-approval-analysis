"""
Examines the extracted records to establish which permits qualify as new.
Validates renewal classifications, permit statuses, and date consistency
before defining the eligible analysis population.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/raw/fy2026_candidate_permits.parquet"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(DATA_PATH)

print("=" * 60)
print("STEP 2: PERMIT ELIGIBILITY VALIDATION")
print("=" * 60)

# 1. Cross-tabulate permit type and renewal classification
cross_tab = pd.crosstab(
    df["PermitTypeDescription"].fillna("<MISSING>"),
    df["RenewalDescription"].fillna("<MISSING>"),
    margins=True
)

print("\n1. PERMIT TYPE VS RENEWAL CLASSIFICATION")
print(cross_tab.to_string())

cross_tab.to_csv(
    OUTPUT_DIR / "permit_classification_crosstab.csv"
)

# 2. Examine renewal codes
renewal_codes = pd.crosstab(
    df["Renewal"].fillna(-1),
    df["RenewalDescription"].fillna("<MISSING>"),
    margins=True
)

print("\n2. RENEWAL CODE MAPPING")
print(renewal_codes.to_string())

# 3. Examine status of new permits
new_df = df[
    df["RenewalDescription"]
    .astype("string")
    .str.strip()
    .str.casefold()
    .eq("new")
    .fillna(False)
].copy()

print("\n3. STATUS OF NEW PERMITS")
print(
    new_df["StatusDescription"]
    .fillna("<MISSING>")
    .value_counts()
    .to_string()
)

# 4. Date validation
date_checks = {
    "New permit records": len(new_df),
    "Missing application dates":
        int(new_df["ApplicationDate"].isna().sum()),
    "Missing approval dates":
        int(new_df["LastApprovalDate"].isna().sum()),
    "Missing issuance dates":
        int(new_df["IssueDate"].isna().sum()),
    "Approval before application":
        int((
            new_df["LastApprovalDate"]
            < new_df["ApplicationDate"]
        ).sum()),
    "Approval after issuance":
        int((
            new_df["LastApprovalDate"]
            > new_df["IssueDate"]
        ).sum()),
    "Issuance before application":
        int((
            new_df["IssueDate"]
            < new_df["ApplicationDate"]
        ).sum())
}

print("\n4. DATE QUALITY CHECKS")
for name, value in date_checks.items():
    print(f"{name}: {value:,}")

# 5. Save any anomalous records for review
anomaly_mask = (
    new_df["LastApprovalDate"].isna()
    | (new_df["LastApprovalDate"] < new_df["ApplicationDate"])
    | (new_df["LastApprovalDate"] > new_df["IssueDate"])
    | (new_df["IssueDate"] < new_df["ApplicationDate"])
)

anomalies = new_df.loc[anomaly_mask]

anomalies.to_csv(
    OUTPUT_DIR / "date_anomalies_review.csv",
    index=False
)

print(f"\nRecords requiring date review: {len(anomalies):,}")
print("\nValidation report generated.")
