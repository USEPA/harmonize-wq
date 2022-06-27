# harmonize-wq
Standardize, clean and wrangle Water Quality Portal data into more analytic-ready formats

US EPA’s [Water Quality Portal (WQP)](https://www.waterqualitydata.us/) aggregates water quality, biological, and physical data provided many organizations and has become an essential resource with tools to query and retrieval data using [python](https://github.com/USGS-python/dataretrieval) or [R](https://github.com/USGS-R/dataRetrieval). Given the variety of data and variety of data originators, using the data in analysis often requires data cleaning to ensure it meets the required quality standards and data wrangling to get it in a more analytic-ready format.  Recognizing the definition of analysis-ready varies depending on the analysis, the harmonixe_wq package is intended to be a flexible water quality specific framework to help:
- Identify differences in data units (including speciation and basis)
- Identify differences in sampling or analytic methods
- Resolve data errors using transparent assumptions
- Transform data from long to wide format

Domain experts must decide what data meets their quality standards for data comparability and any thresholds for acceptance or rejection.

For more complete tutorial information, see:
https://github.com/USEPA/harmonize-wq/tree/main/demos

## Quick Start
harmonize_wq can be installed from git using pip:
```python
pip install git+git://github.com/USEPA/harmonize-wq.git
```

## Issue Tracker
harmonize_wq is under development. Please report any bugs and enhancement ideas using the issue track:
https://github.com/USEPA/harmonize-wq/issues


## Disclaimer
The United States Environmental Protection Agency (EPA) GitHub project code is provided on an "as is" basis and the user assumes responsibility for its use.  EPA has relinquished control of the information and no longer has responsibility to protect the integrity , confidentiality, or availability of the information.  Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation or favoring by EPA.  The EPA seal and logo shall not be used in any manner to imply endorsement of any commercial product or activity by EPA or the United States Government.
