---
title: 'harmonize-wq: Standardize, clean and wrangle Water Quality Portal data into more analytic-ready formats'
tags:
- Python
- water quality
- data set analysis
authors:
  - name: Justin Bousquin
    orcid: 0000-0001-5797-4322
    affiliation: 1
  - name: Cristina A. Mullin
    orcid: 0000-0002-0615-6087
    affiliation: 2
affiliations:
 - name: U.S. Environmental Protection Agency, Gulf Ecosystem Measurement and Modeling Division, Gulf Breeze, FL 32561
   index: 1
 - name: U.S. Environmental Protection Agency, Watershed Restoration, Assessment and Protection Division, Washington, D.C. 20460
   index: 2
date: 20 December 2023
bibliography: paper.bib
---

# Summary

The U.S. EPA’s Water Quality Exchange (WQX) allows state environmental agencies, the EPA, other federal agencies, universities, private citizens, and other organizations to provide water quality, biological, and physical data [@Read_2017]. The Water Quality Portal (WQP) is a data warehouse that facilitates access to data stored in large water quality databases, including WQX, in a common format. WQP has become an essential resource with tools to facilitate both data publishing [@USEPA_2018; @USEPA_2020] and data retrieval [@De_Cicco_2022; @Hodson_2023]. However, given the variety of data originators and methods, using the data in analysis often requires cleaning to ensure it meets required quality standards and wrangling to get it in a more analytic-ready format. Although there are many examples where this data cleaning or wrangling has been performed [@Bousquin_2021;  @Evans_2021; @Manning_2020; @Ross_2019; @Shen_2020], standardized tools to perform this task will make it less time-intensive, more standardized, and more reproducible. More standardized data cleansing and wrangling allows easier integration of outputs into other tools in the water quality data pipeline, e.g., for integration into hydrologic analysis [@Chegini_2021], dashboards for visualization [@Beck_2021] or decision support tools [@Booth_2011].

# Statement of need

Due to the diversity of data originators metadata quality varies and can pose significant challenges preventing WQP from being used as an analysis-ready data set [@Sprague_2017; @Shaughnessy_2019]. Recognizing the definition of 'analysis-ready' varies depending on the analysis, our goal with harmonize-wq is to provide a robust, flexible, water quality specific framework that will help the data analyst identify differences in data units, sampling or analytic methods, and resolve data errors using transparent assumptions. Domain experts must decide what data meets their quality standards for data comparability and any thresholds for acceptance or rejection.

# Current Functionality

WQP is intended to be flexible in how data providers structure their data, what data they provide, and what metadata is associated with the data. The harmonize-wq package does not identify results for rejection, but it does flag those that were altered in a QA column. The package uses the metadata available to clean characteristic data into usable, comparable measures. Four data characteristics are the focus for cleaning the data:

* Measure – If missing (NAN) or not the correct data type, e.g., non-numeric and non-categorical, it cannot be used in analysis.
* Sample Fraction – A measure for a given WQP characteristic, e.g., Phosphorous, may have differences in the analyzed samples, e.g., filtered, dissolved, organic, inorganic, etc. Where these may make measures incomparable to one another results are split into sample fraction specific columns.
* Speciation/Basis/Standards - A measure for a given WQP characteristic, e.g., Nitrogen, may have differences in the molecular basis measured, e.g., ‘as NO3’ vs. ‘as N’. Likewise, some measures will differ depending on sample conditions, such as temperature and pressure. Since these differences will alter the comparability of results they are moved to the appropriate column for consideration in conversions and analyst decisions.
* Units - Units of measure are converted using Pint [@Grecco_2021]. To facilitate this, harmonize-wq defines new units, e.g., ‘NTU’ for turbidity, and updates WQP units for recognition by Pint, e.g., ‘deg C’ for water temperature is updated to ‘degC.’ Where units are missing (NAN) or unrecognized, an attempt is made to assume standard or user-specified units and a flag is added to the QA column. Pint contexts are used to change dimensionality of units, e.g., from mg/l (mass/volume) to g/kg of water (dimensionless), before final conversion. Some additional custom conversions were added, e.g., dissolved oxygen percent saturation to concentration in mg/l. When a unit is falsely recognized, e.g., ‘deg c’ recognized as degree * speed of light, it will typically result in a dimensionality error during conversion. The default is for conversion issues to error, but the user has the option to suppress that error, replacing the results with the un-converted units or as NAN.

In addition to cleaning characteristic results, the package also harmonizes metadata defining the observation. These metadata include site location – where geopandas [@Jordahl_2021] transforms points to a consistent datum, and time of observation – where dataRetrieval [@Hodson_2023] interprets timezone.

Data wrangling involves reducing the complexity of the data to make it more accessible and reshaping the data for use in analysis. The WQP data format is complex, with each row corresponding to a specific result for a specific characteristic and many columns for metadata specific to that result. The harmonize-wq package reshapes the table to loosely adhere to tidy principles [@Wickham_2014], where each variable forms a column (i.e., one characteristic per column) and each observation forms a row (i.e., one row per site and time stamp). Given the number of result specific WQP metadata columns, to avoid conflicts during reshaping the package has functions to differentiate these based on the original characteristic, e.g., ‘QA’ becoming ‘QA_Nitrogen’. Once the data has been cleansed and result specific columns differentiated many of the original columns can be reduced. The package also has resources for entity resolution, both for deduplication when one source has duplicate results during reshaping (e.g., quality control or calibration sample) and when the same result is reported by different sources after the table is reshaped.

# Disclaimer

The views expressed in this article are those of the authors and do not necessarily represent the views or policies of the U.S. Environmental Protection Agency. Any mention of trade names, products, or services does not imply endorsement by the U.S. Government or the U.S. Environmental Protection Agency. The EPA does not endorse any commercial products, services, or enterprises.

This contribution is identified by tracking number ORD-056806 of the U.S. Environmental Protection Agency, Office of Research and Development, Center for Environmental Measurement and Modeling, Gulf Ecosystem Measurement and Modeling Division.

# Acknowledgments

Many people have contributed in various ways to the development of harmonize-wq. We are grateful to Rosmin Ennis, Farnaz Nojavan Asghari, Marc Weber, Catherine Birney, Lisa M. Smith and Elizabeth George for their early reviews of this paper.

# References