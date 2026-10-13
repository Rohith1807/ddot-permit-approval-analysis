
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(
    ROOT / "data/raw/fy2026_candidate_permits.parquet"
)

new_permits = df[df["Renewal"] == 1].copy()

missing = new_permits[
    new_permits["LastApprovalDate"].isna()
]

columns = [
    "OBJECTID",
    "TrackingNumber",
    "PermitNumber",
    "StatusDescription",
    "ApplicationDate",
    "IssueDate",
    "LastApprovalDate"
]

available = [c for c in columns if c in missing.columns]

print(missing[available].to_string(index=False))

print("\nStatus distribution:")
print(missing["StatusDescription"].value_counts(dropna=False))
