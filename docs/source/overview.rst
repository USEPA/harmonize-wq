.. _overview:

Overview
========

US EPA’s `Water Quality Portal (WQP) <https://www.waterqualitydata.us/>`_ aggregates water quality, biological, and physical data provided by many organizations and has become an essential resource with tools to query and retrieve data using `python <https://github.com/USGS-python/dataretrieval>`_ or `R <https://github.com/USGS-R/dataRetrieval>`_. Given the variety of data and data originators, using the data in analysis often requires cleaning to ensure it meets required quality standards and wrangling to get it in a more analytic-ready format.  Recognizing the definition of analysis-ready varies depending on the analysis, the harmonize_wq package is intended to be a flexible water quality specific framework to help:

* Identify differences in data units (including speciation and basis)
* Identify differences in sampling or analytic methods
* Resolve data errors using transparent assumptions
* Transform data from long to wide format

Domain experts must decide what data meets their quality standards for data comparability and any thresholds for acceptance or rejection.

For more complete tutorial information, see: `demos <https://github.com/USEPA/harmonize-wq/tree/main/demos>`_