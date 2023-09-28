.. _example workflow:

Example Workflow
================

dataretrieval Query for a GeoJSON
*********************************

.. code-block:: python3

    import dataretrieval.wqp as wqp
    from harmonize_wq import wrangle

    # File for area of interest
    aoi_url = r'https://github.com/USEPA/harmonize-wq/raw/master/harmonize_wq/tests/data/PPBays_NCCA.geojson'

    # Build query
    query = {'characteristicName': ['Temperature, water',
                                    'Depth, Secchi disk depth',
                                    ]}
    query['bBox'] = wrangle.get_bounding_box(aoi_url)
    query['dataProfile'] = 'narrowResult'

    # Run query
    res_narrow, md_narrow = wqp.get_results(**query)

    # DataFrame of downloaded results
    res_narrow


Harmonize results
*****************

.. code-block:: python3

    from harmonize_wq import harmonize
    
    # Harmonize all results
    df_harmonized = harmonize.harmonize_all(res_narrow, errors='raise')
    df_harmonized


Clean results
*************

.. code-block:: python3

    from harmonize_wq import clean

    # Clean up other columns of data
    df_cleaned = clean.datetime(df_harmonized)  # datetime
    df_cleaned = clean.harmonize_depth(df_cleaned)  # Sample depth
    df_cleaned


Transform results from long to wide format
******************************************
There are many columns in the pandas.DataFrame that are characteristic specific, that is they have different values for the same sample depending on the characteristic. To ensure one result for each sample after the transformation of the data these columns must either be split, generating a new column for each characteristic with values, or moved out from the table if not being used.

.. code-block:: python3

    from harmonize_wq import wrangle

    # Split QA column into multiple characteristic specific QA columns
    df_full = wrangle.split_col(df_cleaned)

    # Divide table into columns of interest (main_df) and characteristic specific metadata (chars_df)
    main_df, chars_df = wrangle.split_table(df_full)

    # Combine rows with the same sample organization, activity, location, and datetime
    df_wide = wrangle.collapse_results(main_df)

The number of columns in the resulting table is greatly reduced

+----------------------------+-------------+----------------------------------------+-------------------------------+
|        Output Column       |     Type    |               Source                   |           Changes             |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|MonitoringLocationIdentifier| Defines row |MonitoringLocationIdentifier            |NA                             |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|Activity_datetime           | Defines row |ActivityStartDate                       |Combined and UTC               |
|                            |             |ActivityStartTime/Time                  |                               |
|                            |             |ActivityStartTime/TimeZoneCode          |                               |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|ActivityIdentifier          | Defines row |ActivityIdentifier                      |NA                             |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|OrganizationIdentifier      | Defines row |OrganizationIdentifier                  |NA                             |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|OrganizationFormalName      | Metadata    |OrganizationFormalName                  |NA                             |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|ProviderName                | Metadata    |ProviderName                            |NA                             |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|StartDate                   | Metadata    |ActivityStartDate                       |Preserves date where time NAT  |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|Depth                       | Metadata    |ResultDepthHeightMeasure/MeasureValue   |Standardized to meters         |
|                            |             |ResultDepthHeightMeasure/MeasureUnitCode|                               |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|Secchi                      | Result      |ResultMeasureValue                      |Standardized to meters         |
|                            |             |ResultMeasure/MeasureUnitCode           |                               |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|QA_Secchi                   | QA          |NA                                      |Harmonization quality issues   |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|Temperature                 | Result      |ResultMeasureValue                      |Standardized to degrees Celsius|
|                            |             |ResultMeasure/MeasureUnitCode           |                               |
+----------------------------+-------------+----------------------------------------+-------------------------------+
|QA_Temperature              | QA          |NA                                      |Harmonization quality issues   |
+----------------------------+-------------+----------------------------------------+-------------------------------+

For more complete tutorial information, see: `demos <https://github.com/USEPA/harmonize-wq/tree/main/demos>`_