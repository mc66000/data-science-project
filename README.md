# Macau Public Toilets — Distribution & Accessibility Analysis

## Problem / Research Question
How are public toilets distributed across Macau's three districts, and how
well does that network serve visitors and people with accessibility needs?
Specifically: Where are the gaps in barrier-free access, parent-child
facilities, and whole-day (24-hour) availability?

## Dataset — Source and Usage Permissions
- **Source:** Macau Open Data Portal (data.gov.mo), published by the
  Municipal Affairs Bureau (IAM / Instituto para os Assuntos Municipais).
- **File:** `macau_toilets.csv` (198 public toilet records).
- **Permissions:** Open government data released for public reuse. No
  personal or restricted data is included. Attribution to IAM / data.gov.mo
  is retained. Map tiles are © OpenStreetMap contributors.

## Methods and Tools
- **Language:** Python 3
- **Libraries:** pandas, numpy, matplotlib (core);
  geopandas + contextily (real OpenStreetMap basemap);
  folium (interactive map).
- **Pipeline:** load and clean the CSV (BOM/whitespace/title-row handling),
  classify each toilet into a district from its facility-code prefix,
  parse `location` into latitude/longitude, and flag whole-day opening
  with a regular expression. Results are aggregated per district and
  rendered as four static charts plus one interactive HTML map.

## Key Findings
- **198 toilets total:** Macau Peninsula 136, Taipa 30, Coloane 32.
- **Barrier-free (DWC) 65.2% overall**, but uneven — Taipa 83.3% vs
  Peninsula 62.5% and Coloane 59.4%.
- **Parent-child (FWC) only 11.6%**, the clearest service gap citywide.
- **Whole-day open 55.6%**, yet the tourist-heavy Peninsula sits lowest at
  50.7%, meaning roughly half its toilets are unavailable at night.

## Limitation
The dataset provides no "temporarily closed" field, so real-time
availability cannot be assessed; one record (GM13) is also missing
coordinates and is excluded from the maps. Findings therefore reflect
listed facilities, not live status.

## How to Run
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place the dataset at ./Datasets/macau_toilets.csv

# 3. Run the analysis
python analysis.py