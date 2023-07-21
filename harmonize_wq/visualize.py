# -*- coding: utf-8 -*-
"""
    Functions to help visualize data.
"""
import pandas
import geopandas
from math import sqrt
from harmonize_wq import wrangle


def print_report(results_in, out_col, unit_col_in, threshold=None):
    """
    Prints a standardized report of changes made

    Parameters
    ----------
    results_in : pandas.Dataframe
        DataFrame with subset of results.
    out_col : string
        Name of column in results_in with final result.
    unit_col_in : string
        Name of column with original units.
    threshold : dict, optional
        Dictionary with min and max keys. The default is None.

    Returns
    -------
    None.

    """
    # Series with just usable results.
    results = results_in[out_col].dropna()
    # Series with infered units
    inferred = results_in.loc[((results_in[out_col].notna()) &
                               (results_in[unit_col_in].isna()))]
    # Series with just magnitude
    results_s = pandas.Series([x.magnitude for x in results])
    # Number of usable results
    print('-Usable results-\n{}'.format(results_s.describe()))
    # Number measures unused
    print('Unusable results: {}'.format(len(results_in)-len(results)))
    # Number of infered result units
    print('Usable results with inferred units: {}'.format(len(inferred)))
    # Results outside thresholds
    if not threshold:
        # TODO: Default mean +/-1 standard deviation works here but generally 6
        threshold = {'min': 0.0,
                     'max': results_s.mean() + (6 * results_s.std())}
    inside = results_s[(results_s <= threshold['max']) &
                       (results_s >= threshold['min'])]
    diff = len(results) - len(inside)
    print('Results outside threshold ({} to {}): {}'.format(threshold['min'],
                                                            threshold['max'],
                                                            diff))

    # Graphic representation of stats
    inside.hist(bins=int(sqrt(inside.count())))
    # TODO: two histograms overlaid?
    # inferred_s = pandas.Series([x.magnitude for x in inferred])
    # pandas.Series([x.magnitude for x in inferred]).hist()


def map_counts(df_in, gdf, col=None):
    """
    Return GeoDataFrame summarized by count of results for each station

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with subset of results.
    gdf : geopandas.GeoDataFrame
        GeoDataFrame with monitoring locations.

    Examples
    --------
    Return a GeoDataFrame summarized by counts and plot it::
        
        cnt_gdf = harmonize.visualize.map_counts(df, stations_clipped)
        cnt_gdf.plot(column='cnt', cmap='Blues', legend=True)

    Returns
    -------
    geopandas.GeoDataFrame
    """
    # Column for station
    loc_id = 'MonitoringLocationIdentifier'
    # TODO: col is going to be used to restrict results, if none use all
    if col is not None:
        cols = [loc_id, col]
        df_in = df_in.loc[df_in[col].notna(), cols].copy()
        # TODO: cols needed?
    # Map counts of all results
    df_cnt = df_in.groupby(loc_id).size().to_frame('cnt')
    df_cnt.reset_index(inplace=True)

    # Join it to geometry
    merge_cols = ['MonitoringLocationIdentifier']
    gdf_cols = ['geometry', 'QA_flag']
    results_df = wrangle.merge_tables(df_cnt, gdf, gdf_cols, merge_cols)
    return geopandas.GeoDataFrame(results_df, geometry='geometry')


def map_measure(df_in, gdf, col):
    """
    Return GeoDataFrame summarized by average of results for each station

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with subset of results.
    gdf : geopandas.GeoDataFrame
        GeoDataFrame with monitoring locations.
    col : string
        Column name in df_in to aggregate results for.

    Returns
    -------
    geopandas.GeoDataFrame

    """
    merge_cols = ['MonitoringLocationIdentifier']

    if merge_cols[0] not in df_in.columns:
        df_temp = df_in.reset_index()  # May be part of index already
    else:
        df_temp = df_in.copy()

    df_agg = station_summary(df_temp, col)

    # Join it to geometry
    gdf_cols = ['geometry', 'QA_flag']
    results_df = wrangle.merge_tables(df_agg, gdf, gdf_cols, merge_cols)

    return geopandas.GeoDataFrame(results_df, geometry='geometry')


def station_summary(df_in, col):
    """
    Return summary table with rows for each station, count and column average

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with subset of results.
    col : string
        Column name in df_in to summarize results for.

    Returns
    -------
    pandas.DataFrame

    """
    # Column for station
    loc_id = 'MonitoringLocationIdentifier'
    # Aggregate data by station to look at results spatially
    cols = [loc_id, col]
    df = df_in.loc[df_in[col].notna(), cols].copy()
    # Col w/ magnitude seperate from unit
    avg = [x.magnitude for x in df[col]]
    df['magnitude'] = pandas.Series(avg, index=df[col].index)
    df_agg = df.groupby(loc_id).size().to_frame('cnt')
    cols = [loc_id, 'magnitude']
    df_agg['mean'] = df[cols].groupby(loc_id).mean()
    df_agg.reset_index(inplace=True)

    return df_agg
