# -*- coding: utf-8 -*-
"""Functions to help visualize data."""

from math import sqrt

import geopandas
import pandas

from harmonize_wq.wrangle import merge_tables


def print_report(results_in, out_col, unit_col_in, threshold=None):
    """Print a standardized report of changes made.

    Parameters
    ----------
    results_in : pandas.DataFrame
        DataFrame with subset of results.
    out_col : str
        Name of column in results_in with final result.
    unit_col_in : str
        Name of column with original units.
    threshold : dict, optional
        Dictionary with min and max keys. The default is None.

    Returns
    -------
    None.

    See Also
    --------
    See any of the 'Detailed' notebooks found in
    `demos <https://github.com/USEPA/harmonize-wq/tree/main/demos>`_ for
    examples of how this function is leveraged by the
    :func:`harmonize.harmonize_generic` report argument.

    """
    # Series with just usable results.
    results = results_in[out_col].dropna()
    # Series with infered units
    inferred = results_in.loc[
        ((results_in[out_col].notna()) & (results_in[unit_col_in].isna()))
    ]
    # Series with just magnitude
    results_s = pandas.Series([x.magnitude for x in results])
    # Number of usable results
    print(f"-Usable results-\n{results_s.describe()}")
    # Number measures unused
    print(f"Unusable results: {len(results_in)-len(results)}")
    # Number of infered result units
    print(f"Usable results with inferred units: {len(inferred)}")
    # Results outside thresholds
    if not threshold:
        # TODO: Default mean +/-1 standard deviation works here but generally 6
        threshold = {"min": 0.0, "max": results_s.mean() + (6 * results_s.std())}
    inside = results_s[
        (results_s <= threshold["max"]) & (results_s >= threshold["min"])
    ]
    diff = len(results) - len(inside)
    threshold_range = f"{threshold['min']} to {threshold['max']}"
    print(f"Results outside threshold ({threshold_range}): {diff}")

    # Graphic representation of stats
    inside.hist(bins=int(sqrt(inside.count())))
    # TODO: two histograms overlaid?
    # inferred_s = pandas.Series([x.magnitude for x in inferred])
    # pandas.Series([x.magnitude for x in inferred]).hist()


def map_counts(df_in, gdf, col=None):
    """Get GeoDataFrame summarized by count of results for each station.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with subset of results.
    gdf : geopandas.GeoDataFrame
        GeoDataFrame with monitoring locations.
    col : str, optional
        Column in df_in to aggregate results to in addition to location.
        The default is None, where results are only aggregated on location.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with count of results for each station

    Examples
    --------
    Build example DataFrame of results:

    >>> from pandas import DataFrame
    >>> df_in = DataFrame({'ResultMeasureValue': [5.1, 1.2, 8.7],
    ...                    'MonitoringLocationIdentifier': ['ID1', 'ID2', 'ID1']
    ...                           })
    >>> df_in
       ResultMeasureValue MonitoringLocationIdentifier
    0                 5.1                          ID1
    1                 1.2                          ID2
    2                 8.7                          ID1

    Build example GeoDataFrame of monitoring locations:

    >>> import geopandas
    >>> from shapely.geometry import Point
    >>> from numpy import nan
    >>> d = {'MonitoringLocationIdentifier': ['ID1', 'ID2'],
    ...      'QA_flag': [nan, nan],
    ...      'geometry': [Point(1, 2), Point(2, 1)]}
    >>> gdf = geopandas.GeoDataFrame(d, crs="EPSG:4326")
    >>> gdf
      MonitoringLocationIdentifier  QA_flag                 geometry
    0                          ID1      NaN  POINT (1.00000 2.00000)
    1                          ID2      NaN  POINT (2.00000 1.00000)

    Combine these to get an aggregation of results per station:

    >>> import harmonize_wq
    >>> cnt_gdf = harmonize_wq.visualize.map_counts(df_in, gdf)
    >>> cnt_gdf
      MonitoringLocationIdentifier  cnt                 geometry  QA_flag
    0                          ID1    2  POINT (1.00000 2.00000)      NaN
    1                          ID2    1  POINT (2.00000 1.00000)      NaN

    These aggregate results can then be plotted:

    >>> cnt_gdf.plot(column='cnt', cmap='Blues', legend=True)
    <Axes: >
    """
    # Column for station
    loc_id = "MonitoringLocationIdentifier"
    # TODO: col is going to be used to restrict results, if none use all
    if col is not None:
        cols = [loc_id, col]
        df_in = df_in.loc[df_in[col].notna(), cols].copy()
        # TODO: cols needed?
    # Map counts of all results
    df_cnt = df_in.groupby(loc_id).size().to_frame("cnt")
    df_cnt.reset_index(inplace=True)

    # Join it to geometry
    merge_cols = ["MonitoringLocationIdentifier"]
    gdf_cols = ["geometry", "QA_flag"]
    results_df = merge_tables(df_cnt, gdf, gdf_cols, merge_cols)
    return geopandas.GeoDataFrame(results_df, geometry="geometry")


def map_measure(df_in, gdf, col):
    """Get GeoDataFrame summarized by average of results for each station.

    :class:`geopandas.GeoDataFrame` will have new column 'mean' with the
    average of col values for that location.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with subset of results.
    gdf : geopandas.GeoDataFrame
        GeoDataFrame with monitoring locations.
    col : str
        Column name in df_in to aggregate results for.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with average value of results for each station.

    Examples
    --------
    Build array of pint Quantity for Temperature:

    >>> from pint import Quantity
    >>> u = 'degree_Celsius'
    >>> temperatures = [Quantity(5.1, u), Quantity(1.2, u), Quantity(8.7, u)]

    Build example pandas DataFrame of results:

    >>> from pandas import DataFrame
    >>> df_in = DataFrame({'Temperature': temperatures,
    ...                    'MonitoringLocationIdentifier': ['ID1', 'ID2', 'ID1']
    ...                    })
    >>> df_in
              Temperature MonitoringLocationIdentifier
    0  5.1 degree_Celsius                          ID1
    1  1.2 degree_Celsius                          ID2
    2  8.7 degree_Celsius                          ID1

    Build example geopandas GeoDataFrame of monitoring locations:

    >>> import geopandas
    >>> from shapely.geometry import Point
    >>> from numpy import nan
    >>> d = {'MonitoringLocationIdentifier': ['ID1', 'ID2'],
    ...      'QA_flag': [nan, nan],
    ...      'geometry': [Point(1, 2), Point(2, 1)]}
    >>> gdf = geopandas.GeoDataFrame(d, crs="EPSG:4326")
    >>> gdf
      MonitoringLocationIdentifier  QA_flag                 geometry
    0                          ID1      NaN  POINT (1.00000 2.00000)
    1                          ID2      NaN  POINT (2.00000 1.00000)

    Combine these to get an aggregation of results per station:

    >>> from harmonize_wq import visualize
    >>> avg_temp = visualize.map_measure(df_in, gdf, 'Temperature')
    >>> avg_temp
      MonitoringLocationIdentifier  cnt  mean                 geometry  QA_flag
    0                          ID1    2   6.9  POINT (1.00000 2.00000)      NaN
    1                          ID2    1   1.2  POINT (2.00000 1.00000)      NaN

    These aggregate results can then be plotted:

    >>> avg_temp.plot(column='mean', cmap='Blues', legend=True)
    <Axes: >
    """
    merge_cols = ["MonitoringLocationIdentifier"]

    if merge_cols[0] not in df_in.columns:
        df_temp = df_in.reset_index()  # May be part of index already
    else:
        df_temp = df_in.copy()

    df_agg = station_summary(df_temp, col)

    # Join it to geometry
    gdf_cols = ["geometry", "QA_flag"]
    results_df = merge_tables(df_agg, gdf, gdf_cols, merge_cols)

    return geopandas.GeoDataFrame(results_df, geometry="geometry")


def station_summary(df_in, col):
    """Get summary table for stations.

    Summary table as :class:`~pandas.DataFrame` with rows for each
    station, count, and column average.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with results to summarize.
    col : str
        Column name in df_in to summarize results for.

    Returns
    -------
    pandas.DataFrame
        Table with result count and average summarized by station.
    """
    # Column for station
    loc_id = "MonitoringLocationIdentifier"
    # Aggregate data by station to look at results spatially
    cols = [loc_id, col]
    df = df_in.loc[df_in[col].notna(), cols].copy()
    # Col w/ magnitude seperate from unit
    avg = [x.magnitude for x in df[col]]
    df["magnitude"] = pandas.Series(avg, index=df[col].index)
    df_agg = df.groupby(loc_id).size().to_frame("cnt")
    cols = [loc_id, "magnitude"]
    df_agg["mean"] = df[cols].groupby(loc_id).mean()
    df_agg.reset_index(inplace=True)

    return df_agg
