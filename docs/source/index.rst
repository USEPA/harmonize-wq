.. harmonize_wq documentation master file, created by
   sphinx-quickstart on Mon Jul  3 14:48:49 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

harmonize_wq: 
=============
Standardize, clean, and wrangle Water Quality Portal data into more analytic-ready formats
------------------------------------------------------------------------------------------
**Useful links**:
`Code Repository <https://github.com/USEPA/harmonize-wq>`__ |
`Issues <https://github.com/USEPA/harmonize-wq/issues>`__ 

.. toctree::
    :maxdepth: 2
    :caption: Getting Started
    overview
    example workflow

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

.. _installing:

Installing harmonize_wq
=======================

harmonize_wq can be installed using pip:

.. code-block:: python3
   
    pip install harmonize-wq



To install the latest development version of harmonize_wq using pip:

.. code-block:: python3
   
    pip install git+https://github.com/USEPA/harmonize-wq.git

.. toctree::
    :maxdepth: 1
    :caption: Tutorial Notebooks

    notebooks/Harmonize_Pensacola_Simple
    notebooks/Harmonize_Pensacola_Detailed
    notebooks/Harmonize_Tampa_Simple
    notebooks/Harmonize_Tampa_Detailed
    notebooks/Harmonize_CapeCod_Simple
    notebooks/Harmonize_CapeCod_Detailed
    notebooks/Harmonize_GOM

.. toctree::
    :maxdepth: 1
    :caption: Reference Documentation

    modules

.. toctree::
    :maxdepth: 2
    :hidden:
    :caption: Development

    contributing
    Code of Conduct

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Disclaimer
==========
The United States Environmental Protection Agency (EPA) GitHub project code is provided on an “as is” basis and the user assumes responsibility for its use. EPA has relinquished control of the information and no longer has responsibility to protect the integrity , confidentiality, or availability of the information. Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation or favoring by EPA. The EPA seal and logo shall not be used in any manner to imply endorsement of any commercial product or activity by EPA or the United States Government.