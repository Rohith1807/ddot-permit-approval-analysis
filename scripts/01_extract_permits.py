"""
Extracts FY2026 candidate construction permit records from the DDOT ArcGIS REST API.
Retrieves records in batches and validates completeness before beginning analysis.
"""


from pathlib import Path
from datetime import datetime, timezone
import json
import time

import pandas as pd
import requests

# -----------------------------
# 1. Project configuration
# -----------------------------

BASE_URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_APPS/DDOT_TOPS/MapServer/23"
)
QUERY_URL = f"{BASE_URL}/query"

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "outputs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Candidate population only.
WHERE = (
    "ApplicationDate >= TIMESTAMP '2025-10-01 00:00:00' "
    "AND IssueDate >= TIMESTAMP '2025-10-01 00:00:00' "
    "AND IssueDate < TIMESTAMP '2026-10-01 00:00:00'"
)

BATCH_SIZE = 100
session = requests.Session()


# -----------------------------
# 2. API helper with retries
# -----------------------------


def api_request(url, params, attempts=6, use_post=False):
    for attempt in range(attempts):
        try:
            if use_post:
                response = session.post(
                    url, data=params, timeout=120
                )
            else:
                response = session.get(
                    url, params=params, timeout=120
                )

            response.raise_for_status()
            payload = response.json()

            if "error" in payload:
                raise RuntimeError(
                    f"ArcGIS error: {payload['error']}"
                )

            return payload

        except (requests.RequestException, ValueError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError(
                    f"API failed after {attempts} attempts"
                ) from exc

            wait = min(2 ** attempt, 30)
            print(
                f"Request failed ({type(exc).__name__}). "
                f"Retrying in {wait}s..."
            )
            time.sleep(wait)

    raise RuntimeError("API request failed")



# -----------------------------
# 3. Get layer metadata
# -----------------------------

metadata = api_request(BASE_URL, {"f": "json"})

field_definitions = metadata["fields"]
field_names = [f["name"] for f in field_definitions]

oid_field = next(
    f["name"]
    for f in field_definitions
    if f["type"] == "esriFieldTypeOID"
)

date_fields = [
    f["name"]
    for f in field_definitions
    if f["type"] == "esriFieldTypeDate"
]

with open(
    RAW_DIR / "layer_metadata.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(metadata, file, indent=2)


# -----------------------------
# 4. Count candidate permits
# -----------------------------

count_result = api_request(
    QUERY_URL,
    {
        "where": WHERE,
        "returnCountOnly": "true",
        "f": "json"
    }
)

expected_count = count_result["count"]

print(f"API candidate permit count: {expected_count:,}")


# -----------------------------
# 5. Retrieve matching IDs
# -----------------------------

id_result = api_request(
    QUERY_URL,
    {
        "where": WHERE,
        "returnIdsOnly": "true",
        "f": "json"
    }
)

object_ids = sorted(id_result.get("objectIds") or [])

assert len(object_ids) == len(set(object_ids)), (
    "Duplicate object IDs returned by API"
)

if len(object_ids) != expected_count:
    raise RuntimeError(
        f"ID count {len(object_ids)} does not "
        f"match API count {expected_count}"
    )

print(f"Retrieved {len(object_ids):,} unique IDs")


# -----------------------------
# 6. Download in batches
# -----------------------------

all_records = []

for start in range(0, len(object_ids), BATCH_SIZE):
    batch_ids = object_ids[start:start + BATCH_SIZE]

    payload = api_request(
        QUERY_URL,
        {
            "objectIds": ",".join(map(str, batch_ids)),
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json"
        },
        use_post=True
    )

    records = [
        feature["attributes"]
        for feature in payload.get("features", [])
    ]

    returned_ids = {r[oid_field] for r in records}
    missing_ids = set(batch_ids) - returned_ids

    if missing_ids:
        raise RuntimeError(
            f"Missing records in batch: {missing_ids}"
        )

    if len(records) != len(batch_ids):
        raise RuntimeError(
            "Batch returned an unexpected record count"
        )

    all_records.extend(records)

    print(
        f"Downloaded {len(all_records):,} / "
        f"{expected_count:,}"
    )


# -----------------------------
# 7. Build DataFrame
# -----------------------------

df = pd.DataFrame(
    all_records,
    columns=field_names
)

if len(df) != expected_count:
    raise RuntimeError("Final record count mismatch")

if df[oid_field].duplicated().any():
    raise RuntimeError("Duplicate OBJECTIDs found")


# -----------------------------
# 8. Convert ArcGIS dates
# -----------------------------

# ArcGIS dates are epoch milliseconds.
# Convert from UTC to the layer's Eastern time.
# Keep time-zone-aware timestamps.
for col in date_fields:
    df[col] = (
        pd.to_datetime(
            df[col],
            unit="ms",
            utc=True,
            errors="coerce"
        )
        .dt.tz_convert("America/New_York")
    )


# -----------------------------
# 9. Validate date boundaries
# -----------------------------

application_dates = df["ApplicationDate"].dt.date
issue_dates = df["IssueDate"].dt.date

valid_dates = (
    (application_dates >= datetime(2025, 10, 1).date())
    & (issue_dates >= datetime(2025, 10, 1).date())
    & (issue_dates < datetime(2026, 10, 1).date())
)

if not valid_dates.all():
    raise RuntimeError(
        f"{(~valid_dates).sum()} records outside "
        "required candidate date boundaries"
    )


# -----------------------------
# 10. Save raw candidate data
# -----------------------------

output_file = RAW_DIR / "fy2026_candidate_permits.parquet"

df.to_parquet(output_file, index=False)

# Field dictionary from available metadata
field_dictionary = pd.DataFrame([
    {
        "field": f["name"],
        "alias": f.get("alias"),
        "type": f["type"],
        "missing_count": int(df[f["name"]].isna().sum()),
        "missing_pct": round(
            df[f["name"]].isna().mean() * 100, 2
        )
    }
    for f in field_definitions
])

field_dictionary.to_csv(
    OUTPUT_DIR / "field_profile.csv",
    index=False
)


# -----------------------------
# 11. Initial category profiles
# -----------------------------

profile_columns = [
    "StatusDescription",
    "PermitTypeDescription",
    "Renewal",
    "RenewalDescription",
    "TypeDetailNames",
    "WorkLocationWard"
]

for col in profile_columns:
    if col in df.columns:
        profile = (
            df[col]
            .fillna("<MISSING>")
            .astype(str)
            .value_counts(dropna=False)
            .rename_axis(col)
            .reset_index(name="permit_count")
        )

        profile.to_csv(
            OUTPUT_DIR / f"profile_{col}.csv",
            index=False
        )

        print(f"\n{col}")
        print(profile.head(15).to_string(index=False))


# -----------------------------
# 12. Final summary
# -----------------------------

print("\n" + "=" * 50)
print("EXTRACTION SUMMARY")
print("=" * 50)
print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns)}")
print(f"Duplicate IDs: {df[oid_field].duplicated().sum()}")

for col in [
    "ApplicationDate",
    "IssueDate",
    "LastApprovalDate"
]:
    if col in df.columns:
        print(
            f"{col}: "
            f"{df[col].min()} to {df[col].max()}"
        )
        print(
            f"  Missing: {df[col].isna().sum():,}"
        )

print(f"\nSaved data: {output_file}")
print("Step 1 extraction completed successfully.")
