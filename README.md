[![PyPi](https://img.shields.io/pypi/v/harmonize-wq.svg)](https://pypi.python.org/pypi/harmonize-wq)
[![Documentation Status](https://github.com/USEPA/harmonize-wq/actions/workflows/documentation_deploy.yaml/badge.svg)](https://github.com/USEPA/harmonize-wq/actions/workflows/documentation_deploy.yaml)
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![test](https://github.com/USEPA/harmonize-wq/actions/workflows/test.yml/badge.svg)](https://github.com/USEPA/harmonize-wq/actions/workflows/test.yml)
[![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/USEPA/harmonize-wq/main/pyproject.toml)](https://www.python.org/downloads/)
[![pyOpenSci Peer-Reviewed](https://pyopensci.org/badges/peer-reviewed.svg)](https://github.com/pyOpenSci/software-review/issues/157)

# harmonize-wq
Standardize, clean, and wrangle Water Quality Portal data into more analytic-ready formats

US EPA’s [Water Quality Portal (WQP)](https://www.waterqualitydata.us/) aggregates water quality, biological, and physical data provided by many organizations and has become an essential resource with tools to query and retrieval data using [python](https://github.com/USGS-python/dataretrieval) or [R](https://github.com/USGS-R/dataRetrieval).
Given the variety of data and variety of data originators, using the data in analysis often requires data cleaning to ensure it meets the required quality standards and data wrangling to get it in a more analytic-ready format.
Recognizing the definition of analysis-ready varies depending on the analysis, the harmonize_wq package is intended to be a flexible water quality specific framework to help:

- Identify differences in data units (including speciation and basis)
- Identify differences in sampling or analytic methods
- Resolve data errors using transparent assumptions
- Transform data from long to wide format

Domain experts must decide what data meets their quality standards for data comparability and any thresholds for acceptance or rejection.

For complete documentation see [docs](https://usepa.github.io/harmonize-wq/index.html). For more complete tutorial information see: [demos](https://github.com/USEPA/harmonize-wq/tree/main/demos)

## Quick Start

harmonize_wq can be installed using pip:
```bash
python3 -m pip install harmonize-wq
```

To install the latest development version of harmonize_wq using pip:

```bash
pip install git+https://github.com/USEPA/harmonize-wq.git
```

## Example Workflow
### dataretrieval Query for a geojson

```python
import dataretrieval.wqp as wqp
from harmonize_wq import wrangle

# File for area of interest
aoi_url = r'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests/data/PPBays_NCCA.geojson'

# Build query
query = {'characteristicName': ['Temperature, water',
                                'Depth, Secchi disk depth',
                                ]}
query['bBox'] = wrangle.get_bounding_box(aoi_url)
query['dataProfile'] = 'narrowResult'

# Run query
res_narrow, md_narrow = wqp.get_results(**query)

# dataframe of downloaded results
res_narrow
```

### Harmonize results

```python
from harmonize_wq import harmonize

# Harmonize all results
df_harmonized = harmonize.harmonize_all(res_narrow, errors='raise')
df_harmonized
```

### Clean results

```python
from harmonize_wq import clean

# Clean up other columns of data
df_cleaned = clean.datetime(df_harmonized)  # datetime
df_cleaned = clean.harmonize_depth(df_cleaned)  # Sample depth
df_cleaned
```

### Transform results from long to wide format
There are many columns in the dataframe that are characteristic specific, that is they have different values for the same sample depending on the characteristic.
To ensure one result for each sample after the transformation of the data these columns must either be split, generating a new column for each characteristic with values, or moved out from the table if not being used.

```python
from harmonize_wq import wrangle

# Split QA column into multiple characteristic specific QA columns
df_full = wrangle.split_col(df_cleaned)

# Divide table into columns of interest (main_df) and characteristic specific metadata (chars_df)
main_df, chars_df = wrangle.split_table(df_full)

# Combine rows with the same sample organization, activity, location, and datetime
df_wide = wrangle.collapse_results(main_df)

```

The number of columns in the resulting table is greatly reduced

Output Column | Type | Source | Changes
--- | --- | --- | ---
MonitoringLocationIdentifier | Defines row | MonitoringLocationIdentifier | NA 
Activity_datetime | Defines row | ActivityStartDate, ActivityStartTime/Time, ActivityStartTime/TimeZoneCode | Combined and UTC
ActivityIdentifier | Defines row | ActivityIdentifier | NA
OrganizationIdentifier | Defines row | OrganizationIdentifier | NA 
OrganizationFormalName | Metadata| OrganizationFormalName | NA
ProviderName | Metadata | ProviderName | NA
StartDate | Metadata | ActivityStartDate | Preserves date where time NAT
Depth | Metadata | ResultDepthHeightMeasure/MeasureValue, ResultDepthHeightMeasure/MeasureUnitCode | standardized to meters
Secchi | Result | ResultMeasureValue, ResultMeasure/MeasureUnitCode | standardized to meters
QA_Secchi | QA | NA | harmonization processing quality issues
Temperature | Result | ResultMeasureValue, ResultMeasure/MeasureUnitCode | standardized to degrees Celcius
QA_Temperature | QA | NA | harmonization processing quality issues

## Issue Tracker
harmonize_wq is under development. Please report any bugs and enhancement ideas using [issues](https://github.com/USEPA/harmonize-wq/issues)


## Disclaimer
The United States Environmental Protection Agency (EPA) GitHub project code is provided on an "as is" basis and the user assumes responsibility for its use.
EPA has relinquished control of the information and no longer has responsibility to protect the integrity, confidentiality, or availability of the information. Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation or favoring by EPA.
The EPA seal and logo shall not be used in any manner to imply endorsement of any commercial product or activity by EPA or the United States Government.
