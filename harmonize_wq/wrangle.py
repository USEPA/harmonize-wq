# -*- coding: utf-8 -*-
"""
    Functions to help re-shape the WQP DataFrame
"""
import pandas
import geopandas
from harmonize_wq import domains
from harmonize_wq import harmonize
from harmonize_wq.clean import datetime, harmonize_depth
import dataretrieval.wqp as wqp


def split_table(df_in):
    """
    Splits DataFrame in two, one with main results columns and one with
    Characteristic based metadata.

    Note: runs datetime() and harmonize_depth() if expected columns are missing

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

    """
    # Run datetime on activity fields if not already done
    if 'Activity_datetime' not in list(df_in.columns):
        df_out = datetime(df_in)
    else:
        df_out = df_in.copy()
    # Run depth if not already done
    if 'Depth' not in list(df_in.columns):
        df_out = harmonize_depth(df_out)

    chars_cols = domains.characteristic_cols()  # Characteristic columns list
    chars_df = df_out.filter(items=chars_cols)  # Characteristic table
    main_cols = [x for x in df_out.columns if x not in chars_cols]
    main_df = df_out.filter(items=main_cols)
    return main_df, chars_df


def split_col(df_in, result_col='QA_flag', col_prefix='QA'):
    """
    Splits column so that each value is in a characteristic specific column

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    result_col : string, optional
        Column name with results to split. The default is 'QA_flag'.
    col_prefix : string, optional
        Prefix to be added to new result column names. The default is 'QA'.

    Returns
    -------
    df : pandas.DataFrame
        Updated DataFrame.

    """
    # TODO: is this function doing too much?
    df_out = df_in.copy()
    char_list = list(set(df_out['CharacteristicName']))

    # TODO: try/catch on key error
    col_list = [domains.out_col_lookup()[char_name] for char_name in char_list]

    # TODO: generalize to multi-characteristics other than phosphorus
    char = 'Phosphorus'
    if char in char_list:
        i = char_list.index(char)
        suffix = '_' + domains.out_col_lookup()[char]
        col_list[i] = [col for col in df_out.columns if col.endswith(suffix)]

    # Drop rows where result na
    for i, char in enumerate(char_list):
        mask = (df_out['CharacteristicName'] == char)
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
                new_col = col_prefix + '_' + col_out
                mask = df_out[col_out].notna()
                df_out.loc[mask, new_col] = df_out.loc[mask, result_col]
        else:
            mask = df_out[out_col].notna()
            new_col = col_prefix + '_' + out_col
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
    df = df_in.copy()

    # Drop obvious duplicates (doesn't tend to eliminate many)
    df = df.drop_duplicates()

    # TODO: use date instead of datetime if na?   (date_idx)
    idx_cols = ['MonitoringLocationIdentifier',
                'Activity_datetime',
                'ActivityIdentifier',
                'OrganizationIdentifier']
    df_indexed = df.groupby(by=idx_cols, dropna=False).first()
    # TODO: warn about multi-lines with values (only returns first)
    problems = df.groupby(by=idx_cols, dropna=False).first(min_count=2)
    problems = problems.dropna(axis=1, how='all')
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
    """
    Quick attempt to segment batch what_activities - may not stay

    Parameters
    ----------
    characteristic_names : list
        List of characteristic names to retrieve activities for.
    locations : list
        List of location IDs to retrieve activities for.

    Returns
    -------
    activities : pandas.DataFrame
        DataFrame from dataRetrieval.what_activities().
    """
    # Split loc_list as query by list may cause the query url to be too long
    seg = 200  # Max length of each segment
    activities_list = []
    for loc_que in [locations[x:x+seg] for x in range(0, len(locations), seg)]:
        query = {'characteristicName': characteristic_names,
                 'siteid': loc_que}
        activities_list.append(wqp.what_activities(**query))
    # Combine the dataframe results
    activities = pandas.concat(activities_list).drop_duplicates()
    return activities


def add_activities_to_df(df_in, mask=None):
    """
    Add activities to DataFrame

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    mask : pandas.Series
        Row conditional mask to sub-set rows to get activities for

    Returns
    -------
    df_merged : pandas.DataFrame
        Table with added info from activities table by location id.

    """
    df_out = df_in.copy()
    # Check df for loc_field
    loc_col = 'MonitoringLocationIdentifier'
    harmonize.df_checks(df_out, [loc_col])
    # List of unique sites and characteristicNames
    if mask:
        loc_list = list(set(df_out.loc[mask, loc_col].dropna()))
        char_vals = list(set(df_out.loc[mask, 'CharacteristicName'].dropna()))
    else:
        # Get all
        loc_list = list(set(df_out[loc_col].dropna()))
        char_vals = list(set(df_out['CharacteristicName'].dropna()))
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
    char_val : string
        Specific characteristic name to apply to

    Returns
    -------
    df_merged : pandas.DataFrame
        Table with added info from detection quantitation table columns.

    """
    df_out = df_in.copy()
    # Check df for loc_field
    loc_col = 'MonitoringLocationIdentifier'
    res_id = 'ResultIdentifier'
    harmonize.df_checks(df_out, [loc_col, res_id])
    c_mask = df_out['CharacteristicName'] == char_val  # Mask to limit rows
    loc_series = df_out.loc[c_mask, loc_col]  # Location Series
    res_series = df_out.loc[c_mask, res_id]  # Location Series
    # Get results
    detect_df = get_detection_by_loc(loc_series, res_series, char_val)
    # Merge results to table
    df_merged = merge_tables(df_out, detect_df, merge_cols='all')
    return df_merged


def get_detection_by_loc(loc_series, result_id_series, char_val=None):
    """
    Retrieve detection quantitation results by location, and characteristic
    name (Optional). ResultIdentifier can not be used to search, location id is
    used instead and then results are limited by ResultIdentifiers.

    NOTES: There can be multiple Result Detection Quantitation limits / result
           A result may have a resultid without any corresponding data in the
           Detection Quantitation limits table (nan in full result table).

    Parameters
    ----------
    loc_series : pandas.Series
        Series of location IDs to retrieve detection limits for.
    result_id_series : pandas.Series
        Series of result IDs to limit retrieved data.
    char_val : string, optional.
        Specific characteristic name to retrieve detection limits for.
        The default None, uses all CharacteristicNames

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
    detection_list = []
    for id_que in [id_list[x:x+seg] for x in range(0, len(id_list), seg)]:
        query = {'siteid': id_que}
        if char_val:
            query['characteristicName'] = char_val
        detection_list.append(wqp.what_detection_limits(**query))
    # Combine the dataframe results in the list
    detection_df = pandas.concat(detection_list).drop_duplicates()
    # Filter on resultID
    df_out = detection_df[detection_df['ResultIdentifier'].isin(result_idx)]
    return df_out


def merge_tables(df1, df2, df2_cols='all', merge_cols='activity'):
    """
    Merges two tables (df1 & df2), adding df2_cols to df1 where merge_cols
    match.

    Parameters
    ----------
    df1 : pandas.DataFrame
        DataFrame that will be updated.
    df2 : pandas.DataFrame
        DataFrame with new columns (df2_cols) that will be added to df_in.
    df2_cols : string, optional
        Columns in df2 to add to df1. The default is 'all', for all columns
        not already in df1.
    merge_cols : string, optional
        Columns in both DataFrames to use in join.
        The default is 'activity', for a subset of columns in the activity df2.

    Returns
    -------
    merged_results : pandas.DataFrame
        Updated copy of df_in.

    """
    # TODO: change merge_cols default to all?
    col2_list = list(df2.columns)

    test = merge_cols == 'activity'  # Special activity test = true/false

    if merge_cols == 'activity':
        # ActivityIdentifiers are non-unique. More cols for one-to-one match.
        merge_cols = ['ActivityIdentifier',
                      'ActivityStartDate',
                      'ActivityStartTime/Time',
                      'ActivityStartTime/TimeZoneCode',
                      'MonitoringLocationIdentifier',
                      ]
    elif merge_cols == 'all':
        # Use ALL shared columns. For activity this is +=
        # 'OrganizationIdentifier', 'OrganizationFormalName', 'ProviderName'
        merge_cols = [x for x in list(df1.columns) if x in col2_list]
    else:
        # Check columns in both tables
        shared = [x for x in list(df1.columns) if x in col2_list]
        for col in merge_cols:
            assert col in shared, '{} not in both DataFrames'.format(col)
    # Columns to add from df2
    if df2_cols == 'all':
        # All columns not in df1
        df2_cols = [x for x in col2_list if x not in list(df1.columns)]
    else:
        for col in df2_cols:
            assert col in col2_list, '{} not in DataFrame'.format(col)

    # Merge activity columns to narrow results
    df2 = df2[merge_cols + df2_cols]  # Limit df2 to columns we want
    df2 = df2.drop_duplicates()  # Reduces many to one joins

    # Merge activity columns to narrow results
    merged_results = pandas.merge(df1, df2, how='left', on=merge_cols)
    if test:
        # Many df2 to one df1 gets multiple rows, test for extra activities
        # TODO: Throw more descriptive error?
        assert len(merged_results) == len(df1), len(merged_results) - len(df1)

    return merged_results


def as_gdf(shp):
    """
    Returns a GeoDataFrame for shp if shp is not already a GeoDataFrame.

    Parameters
    ----------
    shp : string
        Filename for something that needs to be a GeoDataFrame.

    Returns
    -------
    shp : geopandas.GeoDataFrame
        GeoDataFrame for shp if it isn't already a GeoDataFrame.
    """
    if not isinstance(shp, geopandas.geodataframe.GeoDataFrame):
        shp = geopandas.read_file(shp)
    return shp


def get_bounding_box(shp, idx=None):
    """
    Return bounding box for shp.

    Parameters
    ----------
    shp : spatial file
        Any geometry that is readable by geopandas.
    idx : integer, optional
        Index for geometry to get bounding box for.
        The default is None to return the total extent bounding box.

    Returns
    -------
        Coordinates for bounding box as string and seperated by ', '.
    """
    shp = as_gdf(shp)

    if idx is None:
        bBox = shp.total_bounds
    else:
        xmin = shp.bounds['minx'][idx]
        xmax = shp.bounds['maxx'][idx]
        ymin = shp.bounds['miny'][idx]
        ymax = shp.bounds['maxy'][idx]
        bBox = [xmin, ymin, xmax, ymax]

    return ','.join(map(str, bBox))


def clip_stations(stations, aoi):
    """
    Clip stations to area of interest (aoi).
    
    Notes
    -----
    aoi is first transformed to stations CRS.

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
    """
    stations_gdf = as_gdf(stations)  # Ensure it is geodataframe
    aoi_gdf = as_gdf(aoi)  # Ensure it is geodataframe
    # Transform aoi to stations CRS (should be 4326)
    aoi_prj = aoi_gdf.to_crs(stations_gdf.crs)
    return geopandas.clip(stations_gdf, aoi_prj)  # Return clipped geodataframe


def to_simple_shape(gdf, out_shp):
    """
    Simplifies GeoDataFrame for better export to shapefile. Adopts and adapts
    'Simple' from NWQMC/pywqp.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        The GeoDataFrame to be exported to shapefile.

    shp_out: string
        Shapefile directory and file name to be written.
    """
    cols = gdf.columns  # List of current column names
    names_dict = domains.stations_rename()  # Dict of column names to update
    # Rename non-results columns that are too long for shp field names
    renaming_list = [col for col in cols if col in names_dict.keys()]
    renaming_dict = {old_col: names_dict[old_col] for old_col in renaming_list}
    # Identify possible results columns before renaming columns
    possible_results = [col for col in cols if col not in names_dict.keys()]
    gdf = gdf.rename(columns=renaming_dict)  # Rename columns
    # TODO: old_field should be assigned to alias
    # field_map1...

    # Results columns need to be str not pint (.astype(str))
    # Narrow based on out_col lookup dictionary
    results_cols = [col for col in possible_results if col in domains.out_col_lookup().values()]
    # TODO: check based on suffix: e.g. Phosphorus
    # Rename each column w/ units and write results as str
    for col in results_cols:
        gdf[col] = gdf[col].astype(str)
    # Drop dateime
    gdf = gdf.drop(columns=['Activity_datetime'])
    # date yyyy-mm-dd (shp)
    # schema = geopandas.io.file.infer_schema(gdf)
    # schema['properties']['StartDate'] = 'date'
    # schema['properties']['Activity_datetime'] = 'str'
    # warnings.warn(schema)
    gdf.to_file(out_shp)
