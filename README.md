# FY2026 Public Space Construction Permit Approval Analysis

**District of Columbia | Public Space Division**  
**Deliverable:** Tableau Packaged Workbook (`.twbx`)  
**Tools:** Python, Pandas, NumPy, ArcGIS REST API, Tableau  
**Reporting Period:** FY2026 (October 1, 2025 – September 30, 2026)

## 1. Project Overview

This analysis addresses a request from the Associate Director of Public Space Division to evaluate average business days required to approve new Public Space Construction Permits issued during FY2026.

The objective was to assess overall approval performance, compare permit categories, and identify meaningful differences across additional permit segments to inform future operational investigation.

Data was extracted from the [DDOT ArcGIS REST Service](https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_APPS/DDOT_TOPS/MapServer/23), processed and validated using Python, and presented through an executive-facing Tableau dashboard.

## 2. Key Findings

**Overall Approval Performance**

- **22.23 business days** was the average application-to-approval duration.
- **2,997 unique new permits** were identified, of which **2,992** had valid approval dates.

**Permit Category Differences**

- Mixed Work Types averaged **51.03 business days** across 112 permits, compared with **20.15 days** for Excavation-only permits (2,684 valid permits).
- These differences identify areas for further review but do not establish the causes of longer approval times.

**Excavation Activity Differences**

- Boring Test Pit (Single) averaged **46.28 days** across 716 valid permits, while Repair Gas Main Line averaged **1.62 days** across 507 permits.
- Some excavation activities occur together on the same permit. For example, 677 permits involved both Boring Test Pit (Single) and Repair Water Service Lateral.

**Recommended Next Step:** Further examine the approval workflows and histories of mixed-work permits and longer-duration excavation activity combinations to understand where additional investigation may be valuable.

## 3. Methodology

### Data Selection and Validation

The analysis includes permits with application dates on or after October 1, 2025, issued between October 1, 2025, and September 30, 2026.

New permits were identified using `Renewal = 1`, verified against the source's renewal descriptions.

The source dataset contained multiple geographic records per permit. To avoid double counting, records were consolidated into a unique permit-level dataset after validating the consistency of application, approval, and issuance dates.

| Processing Stage | Records |
|---|---:|
| FY2026 candidate records | 29,889 |
| New-permit source records | 12,429 |
| Unique new permits | 2,997 |
| Permits with valid approval dates | 2,992 |

### Business-Day Calculation

Approval duration was calculated from `ApplicationDate` to `LastApprovalDate`, excluding the application date, weekends, and observed District of Columbia government holidays.

Five unique permits with missing approval dates were excluded from duration calculations.

The calculation was implemented using NumPy's `busday_count` with a custom DC holiday calendar.

### Segmentation

- **Permit categories:** Mutually exclusive classifications derived from work descriptions and validated against available permit-type indicators.
- **Excavation activities:** Additional activity-level segmentation for Excavation-only permits, retaining overlapping activity associations.
- **Sample sizes:** Permit counts were included to support interpretation of differences, particularly for smaller categories.

## 4. Tableau Deliverable

The packaged Tableau workbook contains an executive dashboard and supporting worksheets covering:

1. Overall average business days to approval and permit counts.
2. Average approval duration by permit category.
3. Average approval duration by excavation activity.
4. Key findings and methodology notes to support management interpretation.

**Workbook:** `tableau/DDOT_FY2026_Permit_Approval_Analysis.twbx`

The dashboard uses validated permit-level metrics and identifies differences in approval duration without attempting to explain their underlying causes.

![alt text](<Screenshot 2026-11-12 120638.png>)

## 5. Reproducibility

The repository contains the Python scripts used for data extraction, validation, transformation, and Tableau dataset preparation.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Execute the numbered scripts in the `scripts/` directory in sequence, beginning with `01_extract_permits.py` and ending with `05_prepare_tableau_data.py`. Supporting validation scripts are included between these stages.

The resulting Tableau-ready datasets are saved to `data/tableau/`.

The source is a live REST service; subsequent extractions may differ as permit records are updated.

## 6. Assumptions and Limitations

- Approval time represents elapsed business days from application to the **last recorded approval**, not exclusively agency processing time.
- Five permits without approval dates were excluded from duration averages.
- Permits with multiple geographic records were counted once in overall and permit-category calculations.
- Excavation activities may overlap; their counts should not be added together.
- Small permit categories should be interpreted cautiously.
- This is a descriptive analysis. No statistical modeling or causal attribution was performed.
