# -*- coding: utf-8 -*-
"""Functions to help re-shape the WQP pandas DataFrame."""

import geopandas
import pandas
from dataretrieval import wqp

from harmonize_wq import domains
from harmonize_wq.clean import datetime, df_checks, harmonize_depth


def split_table(df_in):
    """Split DataFrame columns axis into main and characteristic based.

    Splits :class:`pandas.DataFrame` in two, one with main results columns and
    one with Characteristic based metadata.

    Notes
    -----
    Runs :func:`clean.datetime` and :func:`clean.harmonize_depth` if expected
    columns ('Activity_datetime' and 'Depth') are missing.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be used to generate results.

    Returns
    -------
    main_df : pandas.DataFrame
        DataFrame with main results.
    chars_df : pandas.DataFrame
        DataFrame with Characteristic based metadata.

    Examples
    --------
    See any of the 'Simple' notebooks found in
    `demos <https://github.com/USEPA/harmonize-wq/tree/main/demos>`_ for
    examples of how this function is used to divide the table into columns of
    interest (main_df) and characteristic specific metadata (chars_df).

    """
    # Run datetime on activity fields if not already done
    if "Activity_datetime" not in list(df_in.columns):
        df_out = datetime(df_in)
    else:
        df_out = df_in.copy()
    # Run depth if not already done
    if "Depth" not in list(df_in.columns):
        df_out = harmonize_depth(df_out)

    chars_cols = domains.characteristic_cols()  # Characteristic columns list
    chars_df = df_out.filter(items=chars_cols)  # Characteristic table
    main_cols = [x for x in df_out.columns if x not in chars_cols]
    main_df = df_out.filter(items=main_cols)
    return main_df, chars_df


def split_col(df_in, result_col="QA_flag", col_prefix="QA"):
    """Move each row value from a column to a characteristic specific column.

    Values are moved from the result_col in df_in to a new column where the
    column name is col_prefix + characteristic.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    result_col : str, optional
        Column name with results to split. The default is 'QA_flag'.
    col_prefix : str, optional
        Prefix to be added to new result column names. The default is 'QA'.

    Returns
    -------
    df : pandas.DataFrame
        Updated DataFrame.

    Examples
    --------
    See any of the 'Simple' notebooks found in
    `demos <https://github.com/USEPA/harmonize-wq/tree/main/demos>`_ for
    examples of how this function is used to split the QA column into multiple
    characteristic specific QA columns.

    """
    # TODO: is this function doing too much?
    df_out = df_in.copy()
    char_list = list(set(df_out["CharacteristicName"]))

    # TODO: try/catch on key error
    col_list = [domains.out_col_lookup[char_name] for char_name in char_list]

    # TODO: generalize to multi-characteristics other than phosphorus
    char = "Phosphorus"
    if char in char_list:
        i = char_list.index(char)
        suffix = "_" + domains.out_col_lookup[char]
        col_list[i] = [col for col in df_out.columns if col.endswith(suffix)]

    # Drop rows where result na
    for i, char in enumerate(char_list):
        mask = df_out["CharacteristicName"] == char
        if isinstance(col_list[i], list):
            # All columns with that suffix must be nan
            for col in col_list[i]:
                mask = mask & (df_out[col].isna())
        else:
            # TODO: catch KeyError where characteristic not harmonized
            mask = mask & (df_out[col_list[i]].isna())
        df_out = df_out.drop(df_out[mask].index)

    for out_col in col_list:
        # TODO: variable names (out_col vs col_out) could be better
        # Currently written to drop NaN qa flags, to keep them filter on char
        if isinstance(out_col, list):
            for col_out in out_col:
                new_col = col_prefix + "_" + col_out
                mask = df_out[col_out].notna()
                df_out.loc[mask, new_col] = df_out.loc[mask, result_col]
        else:
            mask = df_out[out_col].notna()
            new_col = col_prefix + "_" + out_col
            # Create characteristic specific QA field
            df_out.loc[mask, new_col] = df_out.loc[mask, result_col]

    # Drop column, it has been replaced
    df_out = df_out.drop(columns=[result_col])

    return df_out


# def split_unit(series):
# If results are being written to another format that does not support
# pint objects the units must be recorded. If in the standard ureg it seems
# to write them as string, otherwise it errors. Ideally we'd either
# transfer the units to within the column name or in a seperate column (not
# preffered, only is multiple units).
#    return series


def collapse_results(df_in, cols=None):
    """Group rows/results that seems like the same sample.

    Default columns are organization, activity, location, and datetime.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    cols : list, optional
        Columns to consider. The default is None.

    Returns
    -------
    df_indexed : pandas.DataFrame
        Updated DataFrame.

    Examples
    --------
    See any of the 'Simple' notebooks found in
    `demos <https://github.com/USEPA/harmonize-wq/tree/main/demos>`_ for
    examples of how this function is used to combine rows with the same sample
    organization, activity, location, and datetime.

    """
    df = df_in.copy()

    # Drop obvious duplicates (doesn't tend to eliminate many)
    df = df.drop_duplicates()

    # TODO: use date instead of datetime if na?   (date_idx)
    if not cols:
        cols = [
            "MonitoringLocationIdentifier",
            "Activity_datetime",
            "ActivityIdentifier",
            "OrganizationIdentifier",
        ]
    df_indexed = df.groupby(by=cols, dropna=False).first()
    # TODO: warn about multi-lines with values (only returns first)
    problems = df.groupby(by=cols, dropna=False).first(min_count=2)
    problems = problems.dropna(axis=1, how="all")
    return df_indexed


# def combine_results(df_in):
#     """
#     NOT IN USE

#     Parameters
#     ----------
#     df_in : TYPE
#         DESCRIPTION.

#     Returns
#     -------
#     df_passing : TYPE
#         DESCRIPTION.
#     df_fails : TYPE
#         DESCRIPTION.
#     """
#     df = df_in.copy()


#     # 'date_idx': datetime column to use as index
#     if 'Activity_datetime' not in df.columns:
#         df = datetime(df)
#     nat_mask = df['Activity_datetime'].isna()  # No valid time
#     df['date_idx'] = df['Activity_datetime']
#     df.loc[nat_mask, 'date_idx'] = df.loc[nat_mask, 'StartDate']  # Fill nat

#     # Multi-index group
#     by_columns = ['MonitoringLocationIdentifier',
#                   'date_idx',
#                   'ActivityIdentifier',
#                   'OrganizationIdentifier']
#     # Columns to skip in this table (NOTE: ResultIdentifier is Char unique)
#    ignore_cols = ['StartDate', 'Activity_datetime', 'OrganizationFormalName',
#                    'ProviderName', 'QA_flag', 'ResultIdentifier']
#     df_sm = df.drop(columns=ignore_cols, errors='ignore')
#  # Note: determine when there are duplicates - e.g, diff ResultIdentifiers?
#     df_sm = df_sm.drop_duplicates()  # This doesn't tend to eliminate many

#     # Group by multi-index
#     df_indexed = df_sm.groupby(by=by_columns, dropna=False)
#     # Note: nunique much slower, do count first?
#         #df_counts = df_indexed.count()
#     df_unique = df_indexed.nunique()  # Won't count duplicate values
#     # Columns of concern! (where any col > 1)
#     fails = df_unique[df_unique.gt(1).any(axis=1)]
#     # Note: don't need fields from fails...
#     df_fails = df.merge(fails.reset_index(), on=by_columns)

#     passing_idx = df_unique[df_unique.le(1).all(axis=1)].index
#     # Note: subset this table based on pass/fail
#     df_first = df_indexed.first()  #First non-nan, else None
#     df_passing = df_first.loc[passing_idx]

#     # Quick read out about pass/fails
#     print('{} groups had multiple unique values, {} rows'.format(len(fails),
#                                                              len(df_fails)))
#     # Note: df_first replace None w/ nan?
#     return df_passing, df_fails


def get_activities_by_loc(characteristic_names, locations):
    """Segment batch what_activities.

    Warning this is not fully implemented and may not stay. Retrieves in batch
    using :func:`dataretrieval.what_activities`.

    Parameters
    ----------
    characteristic_names : list
        List of characteristic names to retrieve activities for.
    locations : list
        List of location IDs to retrieve activities for.

    Returns
    -------
    activities : pandas.DataFrame
        Combined activities for locations.

    Examples
    --------
    See :func:`wrangle.add_activities_to_df`
    """
    # Split loc_list as query by list may cause the query url to be too long
    seg = 200  # Max length of each segment
    activities_list, md_list = [], []
    for loc_que in [locations[x : x + seg] for x in range(0, len(locations), seg)]:
        query = {"characteristicName": characteristic_names, "siteid": loc_que}
        res = wqp.what_activities(**query)
        activities_list.append(res[0])  # Query response DataFrame
        md_list.append(res[1])  # Query response metadata
    # Combine the dataframe results
    activities = pandas.concat(activities_list).drop_duplicates()
    return activities


def add_activities_to_df(df_in, mask=None):
    """Add activities to DataFrame.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    mask : pandas.Series
        Row conditional mask to sub-set rows to get activities for.
        The default None, uses the entire set.

    Returns
    -------
    df_merged : pandas.DataFrame
        Table with added info from activities table by location id.

    Examples
    --------
    Build example df_in table from harmonize_wq tests to use in place of Water
    Quality Portal query response, this table has 'Temperature, water' and
    'Phosphorous' results:

    >>> import pandas
    >>> tests_url = 'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests'
    >>> df1 = pandas.read_csv(tests_url + '/data/wqp_results.txt')
    >>> df1.shape
    (359505, 35)

    Run on the first 1000 results:

    >>> df2 = df1[:1000]

    >>> from harmonize_wq import wrangle
    >>> df_activities = wrangle.add_activities_to_df(df2)
    >>> df_activities.shape
    (1000, 100)

    Look at the columns added:

    >>> df_activities.columns[-65:]
    Index(['ActivityTypeCode', 'ActivityMediaName', 'ActivityMediaSubdivisionName',
           'ActivityEndDate', 'ActivityEndTime/Time',
           'ActivityEndTime/TimeZoneCode', 'ActivityRelativeDepthName',
           'ActivityDepthHeightMeasure/MeasureValue',
           'ActivityDepthHeightMeasure/MeasureUnitCode',
           'ActivityDepthAltitudeReferencePointText',
           'ActivityTopDepthHeightMeasure/MeasureValue',
           'ActivityTopDepthHeightMeasure/MeasureUnitCode',
           'ActivityBottomDepthHeightMeasure/MeasureValue',
           'ActivityBottomDepthHeightMeasure/MeasureUnitCode', 'ProjectIdentifier',
           'ActivityConductingOrganizationText', 'ActivityCommentText',
           'SampleAquifer', 'HydrologicCondition', 'HydrologicEvent',
           'ActivityLocation/LatitudeMeasure', 'ActivityLocation/LongitudeMeasure',
           'ActivityLocation/SourceMapScaleNumeric',
           'ActivityLocation/HorizontalAccuracyMeasure/MeasureValue',
           'ActivityLocation/HorizontalAccuracyMeasure/MeasureUnitCode',
           'ActivityLocation/HorizontalCollectionMethodName',
           'ActivityLocation/HorizontalCoordinateReferenceSystemDatumName',
           'AssemblageSampledName', 'CollectionDuration/MeasureValue',
           'CollectionDuration/MeasureUnitCode', 'SamplingComponentName',
           'SamplingComponentPlaceInSeriesNumeric',
           'ReachLengthMeasure/MeasureValue', 'ReachLengthMeasure/MeasureUnitCode',
           'ReachWidthMeasure/MeasureValue', 'ReachWidthMeasure/MeasureUnitCode',
           'PassCount', 'NetTypeName', 'NetSurfaceAreaMeasure/MeasureValue',
           'NetSurfaceAreaMeasure/MeasureUnitCode',
           'NetMeshSizeMeasure/MeasureValue', 'NetMeshSizeMeasure/MeasureUnitCode',
           'BoatSpeedMeasure/MeasureValue', 'BoatSpeedMeasure/MeasureUnitCode',
           'CurrentSpeedMeasure/MeasureValue',
           'CurrentSpeedMeasure/MeasureUnitCode', 'ToxicityTestType',
           'SampleCollectionMethod/MethodIdentifier',
           'SampleCollectionMethod/MethodIdentifierContext',
           'SampleCollectionMethod/MethodName',
           'SampleCollectionMethod/MethodQualifierTypeName',
           'SampleCollectionMethod/MethodDescriptionText',
           'SampleCollectionEquipmentName',
           'SampleCollectionMethod/SampleCollectionEquipmentCommentText',
           'SamplePreparationMethod/MethodIdentifier',
           'SamplePreparationMethod/MethodIdentifierContext',
           'SamplePreparationMethod/MethodName',
           'SamplePreparationMethod/MethodQualifierTypeName',
           'SamplePreparationMethod/MethodDescriptionText',
           'SampleContainerTypeName', 'SampleContainerColorName',
           'ChemicalPreservativeUsedName', 'ThermalPreservativeUsedName',
           'SampleTransportStorageDescription', 'ActivityMetricUrl'],
          dtype='object')
    """
    df_out = df_in.copy()
    # Check df for loc_field
    loc_col = "MonitoringLocationIdentifier"
    df_checks(df_out, [loc_col])
    # List of unique sites and characteristicNames
    if mask:
        loc_list = list(set(df_out.loc[mask, loc_col].dropna()))
        char_vals = list(set(df_out.loc[mask, "CharacteristicName"].dropna()))
    else:
        # Get all
        loc_list = list(set(df_out[loc_col].dropna()))
        char_vals = list(set(df_out["CharacteristicName"].dropna()))
    # Get results
    act_df = get_activities_by_loc(char_vals, loc_list)
    # Merge results
    df_merged = merge_tables(df_out, act_df)
    return df_merged


def add_detection(df_in, char_val):
    """
    Add detection quantitation information for results where available.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    char_val : str
        Specific characteristic name to apply to.

    Returns
    -------
    df_merged : pandas.DataFrame
        Table with added info from detection quantitation table columns.

    Examples
    --------
    Build example df_in table from harmonize_wq tests to use in place of Water
    Quality Portal query response, this table has 'Temperature, water' and
    'Phosphorous' results:

    >>> import pandas
    >>> tests_url = 'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests'
    >>> df1 = pandas.read_csv(tests_url + '/data/wqp_results.txt')
    >>> df1.shape
    (359505, 35)

    Run on the 1000 results to speed it up:

    >>> df2 = df1[19000:20000]
    >>> df2.shape
    (1000, 35)

    >>> from harmonize_wq import wrangle
    >>> df_detects = wrangle.add_detection(df2, 'Phosphorus')
    >>> df_detects.shape
    (1001, 38)

    Note: the additional rows are due to one result being able to be assigned
    multiple detection results. This is not the case for e.g., df1[:1000]

    Look at the columns added:

    >>> df_detects.columns[-3:]
    Index(['DetectionQuantitationLimitTypeName',
           'DetectionQuantitationLimitMeasure/MeasureValue',
           'DetectionQuantitationLimitMeasure/MeasureUnitCode'],
          dtype='object')
    """
    df_out = df_in.copy()
    # Check df for loc_field
    loc_col = "MonitoringLocationIdentifier"
    res_id = "ResultIdentifier"
    df_checks(df_out, [loc_col, res_id])
    c_mask = df_out["CharacteristicName"] == char_val  # Mask to limit rows
    loc_series = df_out.loc[c_mask, loc_col]  # Location Series
    res_series = df_out.loc[c_mask, res_id]  # Location Series
    # Get results
    detect_df = get_detection_by_loc(loc_series, res_series, char_val)
    # Merge results to table
    df_merged = merge_tables(df_out, detect_df, merge_cols="all")
    return df_merged


def get_detection_by_loc(loc_series, result_id_series, char_val=None):
    """Get detection quantitation by location and characteristic (optional).

    Retrieves detection quantitation results by location and characteristic
    name (optional). ResultIdentifier can not be used to search. Instead
    location id from loc_series is used and then results are limited by
    ResultIdentifiers from result_id_series.

    Notes
    -----
    There can be multiple Result Detection Quantitation limits / result.
    A result may have a ResultIdentifier without any corresponding data in the
    Detection Quantitation limits table (NaN in return).

    Parameters
    ----------
    loc_series : pandas.Series
        Series of location IDs to retrieve detection limits for.
    result_id_series : pandas.Series
        Series of result IDs to limit retrieved data.
    char_val : str, optional.
        Specific characteristic name to retrieve detection limits for.
        The default None, uses all 'CharacteristicName' values returned.

    Returns
    -------
    df_out  : pandas.DataFrame
        Detection Quantitation limits table corresponding to input arguments.
    """
    # TODO: implement fully
    # DetectionQuantitationLimitTypeName
    # DetectionQuantitationLimitMeasure/MeasureValue
    # DetectionQuantitationLimitMeasure/MeasureUnitCode
    result_idx = list(set(result_id_series.dropna()))  # List of result IDs
    id_list = list(set(loc_series.dropna()))  # List of unique location IDs
    # Split list - query by full list may cause the query url to be too long
    seg = 200  # Max length of each segment
    detection_list, md_list = [], []
    for id_que in [id_list[x : x + seg] for x in range(0, len(id_list), seg)]:
        query = {"siteid": id_que}
        if char_val:
            query["characteristicName"] = char_val
        res = wqp.what_detection_limits(**query)
        detection_list.append(res[0])  # Query response DataFrame
        md_list.append(res[1])  # Query response metadata
    # Combine the dataframe results in the list
    detection_df = pandas.concat(detection_list).drop_duplicates()
    # Filter on resultID
    df_out = detection_df[detection_df["ResultIdentifier"].isin(result_idx)]
    return df_out


def merge_tables(df1, df2, df2_cols="all", merge_cols="activity"):
    """Merge df1 and df2.

    Merge tables(df1 and df2), adding df2_cols to df1 where merge_cols match.

    Parameters
    ----------
    df1 : pandas.DataFrame
        DataFrame that will be updated.
    df2 : pandas.DataFrame
        DataFrame with new columns (df2_cols) that will be added to df1.
    df2_cols : str, optional
        Columns in df2 to add to df1. The default is 'all', for all columns
        not already in df1.
    merge_cols : str, optional
        Columns in both DataFrames to use in join.
        The default is 'activity', for a subset of columns in the activity df2.

    Returns
    -------
    merged_results : pandas.DataFrame
        Updated copy of df1.

    Examples
    --------
    Build example table from harmonize_wq tests to use in place of Water
    Quality Portal query responses:

    >>> import pandas
    >>> tests_url = 'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests'
    >>> df1 = pandas.read_csv(tests_url + '/data/wqp_results.txt')
    >>> df1.shape
    (359505, 35)

    >>> df2 = pandas.read_csv(tests_url + '/data/wqp_activities.txt')
    >>> df2.shape
    (353911, 40)

    >>> from harmonize_wq import wrangle
    >>> merged = wrangle.merge_tables(df1, df2)
    >>> merged.shape
    (359505, 67)
    """
    # TODO: change merge_cols default to all?
    col2_list = list(df2.columns)

    test = merge_cols == "activity"  # Special activity test = true/false

    if merge_cols == "activity":
        # ActivityIdentifiers are non-unique. More cols for one-to-one match.
        merge_cols = [
            "ActivityIdentifier",
            "ActivityStartDate",
            "ActivityStartTime/Time",
            "ActivityStartTime/TimeZoneCode",
            "MonitoringLocationIdentifier",
        ]
    elif merge_cols == "all":
        # Use ALL shared columns. For activity this is +=
        # 'OrganizationIdentifier', 'OrganizationFormalName', 'ProviderName'
        merge_cols = [x for x in list(df1.columns) if x in col2_list]
    else:
        # Check columns in both tables
        shared = [x for x in list(df1.columns) if x in col2_list]
        for col in merge_cols:
            assert col in shared, f"{col} not in both DataFrames"
    # Columns to add from df2
    if df2_cols == "all":
        # All columns not in df1
        df2_cols = [x for x in col2_list if x not in list(df1.columns)]
    else:
        for col in df2_cols:
            assert col in col2_list, f"{col} not in DataFrame"

    # Merge activity columns to narrow results
    df2 = df2[merge_cols + df2_cols]  # Limit df2 to columns we want
    df2 = df2.drop_duplicates()  # Reduces many to one joins

    # Merge activity columns to narrow results
    merged_results = pandas.merge(df1, df2, how="left", on=merge_cols)
    if test:
        # Many df2 to one df1 gets multiple rows, test for extra activities
        # TODO: Throw more descriptive error?
        assert len(merged_results) == len(df1), len(merged_results) - len(df1)

    return merged_results


def as_gdf(shp):
    """Get a GeoDataFrame for shp if shp is not already a GeoDataFrame.

    Parameters
    ----------
    shp : str
        Filename for something that needs to be a GeoDataFrame.

    Returns
    -------
    shp : geopandas.GeoDataFrame
        GeoDataFrame for shp if it isn't already a GeoDataFrame.

    Examples
    --------
    Use area of interest GeoJSON for Pensacola and Perdido Bays, FL from
    harmonize_wq tests:

    >>> from harmonize_wq import wrangle
    >>> aoi_url = r'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests/data/PPBays_NCCA.geojson'
    >>> type(wrangle.as_gdf(aoi_url))
    <class 'geopandas.geodataframe.GeoDataFrame'>
    """
    if not isinstance(shp, geopandas.geodataframe.GeoDataFrame):
        shp = geopandas.read_file(shp)
    return shp


def get_bounding_box(shp, idx=None):
    """Get bounding box for spatial file (shp).

    Parameters
    ----------
    shp : spatial file
        Any geometry that is readable by geopandas.
    idx : int, optional
        Index for geometry to get bounding box for.
        The default is None to return the total extent bounding box.

    Returns
    -------
        Coordinates for bounding box as string and separated by ', '.

    Examples
    --------
    Use area of interest GeoJSON for Pensacola and Perdido Bays, FL from
    harmonize_wq tests:

    >>> from harmonize_wq import wrangle
    >>> aoi_url = r'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests/data/PPBays_NCCA.geojson'
    >>> wrangle.get_bounding_box(aoi_url)
    '-87.72443263367131,30.27180869902194,-86.58972642899643,30.654976858733534'
    """
    shp = as_gdf(shp)

    if idx is None:
        bbox = shp.total_bounds
    else:
        xmin = shp.bounds["minx"][idx]
        xmax = shp.bounds["maxx"][idx]
        ymin = shp.bounds["miny"][idx]
        ymax = shp.bounds["maxy"][idx]
        bbox = [xmin, ymin, xmax, ymax]

    return ",".join(map(str, bbox))


def clip_stations(stations, aoi):
    """Clip stations to area of interest (aoi).

    Locations and results are queried by extent rather than the exact geometry.
    Clipping by the exact geometry helps reduce the size of the results.

    Notes
    -----
    aoi is first transformed to CRS of stations.

    Parameters
    ----------
    stations : geopandas.GeoDataFrame
        Points representing the stations.
    aoi : geopandas.GeoDataFrame
        Polygon representing the area of interest.

    Returns
    -------
    pandas.DataFrame
        stations_gdf points clipped to the aoi_gdf.

    Examples
    --------
    Build example geopandas GeoDataFrame of locations for stations:

    >>> import geopandas
    >>> from shapely.geometry import Point
    >>> from numpy import nan
    >>> d = {'MonitoringLocationIdentifier': ['In', 'Out'],
    ...      'geometry': [Point (-87.1250, 30.50000),
    ...                   Point (-87.5000, 30.50000),]}
    >>> stations_gdf = geopandas.GeoDataFrame(d, crs="EPSG:4326")
    >>> stations_gdf
      MonitoringLocationIdentifier                    geometry
    0                           In  POINT (-87.12500 30.50000)
    1                          Out  POINT (-87.50000 30.50000)

    Use area of interest GeoJSON for Pensacola and Perdido Bays, FL from
    harmonize_wq tests:

    >>> aoi_url = r'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests/data/PPBays_NCCA.geojson'

    >>> stations_in_aoi = harmonize_wq.wrangle.clip_stations(stations_gdf, aoi_url)
    >>> stations_in_aoi
      MonitoringLocationIdentifier                    geometry
    0                           In  POINT (-87.12500 30.50000)
    """
    stations_gdf = as_gdf(stations)  # Ensure it is geodataframe
    aoi_gdf = as_gdf(aoi)  # Ensure it is geodataframe
    # Transform aoi to stations CRS (should be 4326)
    aoi_prj = aoi_gdf.to_crs(stations_gdf.crs)
    return geopandas.clip(stations_gdf, aoi_prj)  # Return clipped geodataframe


def to_simple_shape(gdf, out_shp):
    """Simplify GeoDataFrame for better export to shapefile.

    Adopts and adapts 'Simple' from `NWQMC/pywqp <github.com/NWQMC/pywqp>`_
    See :func:`domains.stations_rename` for renaming of columns.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        The GeoDataFrame to be exported to shapefile.

    shp_out: str
        Shapefile directory and file name to be written.

    Examples
    --------
    Build example geopandas GeoDataFrame of locations for stations:

    >>> import geopandas
    >>> from shapely.geometry import Point
    >>> from numpy import nan
    >>> d = {'MonitoringLocationIdentifier': ['In', 'Out'],
    ...      'geometry': [Point (-87.1250, 30.50000),
    ...                   Point (-87.5000, 30.50000),]}
    >>> gdf = geopandas.GeoDataFrame(d, crs="EPSG:4326")
    >>> gdf
      MonitoringLocationIdentifier                    geometry
    0                           In  POINT (-87.12500 30.50000)
    1                          Out  POINT (-87.50000 30.50000)

    Add datetime column

    >>> gdf['ActivityStartDate'] = ['2004-09-01', '2004-02-18']
    >>> gdf['ActivityStartTime/Time'] = ['10:01:00', '15:39:00']
    >>> gdf['ActivityStartTime/TimeZoneCode'] = ['EST', 'EST']
    >>> from harmonize_wq import clean
    >>> gdf = clean.datetime(gdf)
    >>> gdf
      MonitoringLocationIdentifier  ...         Activity_datetime
    0                           In  ... 2004-09-01 15:01:00+00:00
    1                          Out  ... 2004-02-18 20:39:00+00:00
    <BLANKLINE>
    [2 rows x 6 columns]

    >>> from harmonize_wq import wrangle
    >>> wrangle.to_simple_shape(gdf, 'dataframe.shp')
    """
    cols = gdf.columns  # List of current column names
    names_dict = domains.stations_rename  # Dict of column names to update
    # Rename non-results columns that are too long for shp field names
    renaming_list = [col for col in cols if col in names_dict]
    renaming_dict = {old_col: names_dict[old_col] for old_col in renaming_list}
    # Identify possible results columns before renaming columns
    possible_results = [col for col in cols if col not in names_dict]
    gdf = gdf.rename(columns=renaming_dict)  # Rename columns
    # TODO: old_field should be assigned to alias if output driver allows
    # field_map1...

    # Results columns need to be str not pint (.astype(str))
    # Narrow based on out_col lookup dictionary
    results_cols = [
        col for col in possible_results if col in domains.out_col_lookup.values()
    ]
    # TODO: check based on suffix: e.g. Phosphorus
    # Rename each column w/ units and write results as str
    for col in results_cols:
        gdf[col] = gdf[col].astype(str)
    # Drop dateime
    gdf = gdf.drop(columns=["Activity_datetime"])
    # date yyyy-mm-dd (shp)
    # schema = geopandas.io.file.infer_schema(gdf)
    # schema['properties']['StartDate'] = 'date'
    # schema['properties']['Activity_datetime'] = 'str'
    # warnings.warn(schema)
    gdf.to_file(out_shp)
