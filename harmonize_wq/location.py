# -*- coding: utf-8 -*-
"""
Created on Mon Jun 27 15:34:30 2022

This module contains functions to clean/correct location data.

@author: jbousqui
"""
from pyproj import Transformer
from shapely.geometry import shape
import geopandas
import pandas
import dataretrieval.wqp as wqp
from harmonize_wq import harmonize
from harmonize_wq import domains
from harmonize_wq import wrangle


def infer_CRS(df_in,
              out_EPSG,
              out_col='EPSG',
              bad_crs_val=None,
              crs_col='HorizontalCoordinateReferenceSystemDatumName'):
    """
    Replace missing or unrecognized Coordinate Reference System (CRS) with
    desired CRS and add QA_flag about it.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    out_EPSG : string
        Desired CRS to use.
    out_col : string, optional
        Column in df to write out_EPSG to. The default is 'EPSG'.
    bad_crs_val : string, optional
        Bad Coordinate Reference System (CRS) datum name value to replace.
        The default is None for missing datum.
    crs_col : string, optional
        Datum column in df_in. The default is
        'HorizontalCoordinateReferenceSystemDatumName'.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in

    """
    df_out = df_in.copy()
    if bad_crs_val:
        # QA flag for bad CRS based on bad_crs_val
        flag = '{}: Bad datum {}, EPSG:{} assumed'.format(crs_col,
                                                          bad_crs_val,
                                                          out_EPSG)
        c_mask = df_out[crs_col] == bad_crs_val  # Mask for bad CRS value
    else:
        # QA flag for missing CRS
        flag = '{}: MISSING datum, EPSG:{} assumed'.format(crs_col, out_EPSG)
        c_mask = df_out[crs_col].isna()  # Mask for missing units
    df_out = harmonize.add_qa_flag(df_out, c_mask, flag)  # Assign flag
    df_out.loc[c_mask, out_col] = out_EPSG  # Update with infered unit

    return df_out


def harmonize_locations(df_in, out_EPSG=4326,
                        intermediate_columns=False, **kwargs):
    """
    Takes a DataFrame with lat/lon in multiple Coordinate Reference Systems,
    transforms them to outCRS and converts to GeoDataFrame

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the required columns to be converted to GeoDataFrame.
    out_EPSG : Integer, optional
        EPSG factory code for desired output Coordinate Reference System datum.
        The default is 4326, for the WGS84 Datum used by WQP queries.
    intermediate_columns : Boolean, optional
        Return intermediate columns. Default 'False' does not return these.
    Keyword Arguments:
    crs_col : string, optional
        Name of column in DataFrame with the Coordinate Reference System datum.
        The default is 'HorizontalCoordinateReferenceSystemDatumName'.
    lat_col : string, optional
        Name of column in DataFrame with the lattitude coordinate.
        The default is 'LatitudeMeasure'.
    lon_col : string, optional
        Name of column in DataFrame with the longitude coordinate.
        The default is 'LongitudeMeasure'.

    Returns
    -------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame of df_in with coordinates in out_EPSG datum.

    """
    df2 = df_in.copy()

    # Default columns
    crs_col = kwargs.get('crs_col',
                         "HorizontalCoordinateReferenceSystemDatumName")
    lat_col = kwargs.get('lat_col', 'LatitudeMeasure')
    lon_col = kwargs.get('lon_col', 'LongitudeMeasure')

    # Check columns are in df
    harmonize.df_checks(df2, [crs_col, lat_col, lon_col])

    # Create tuple column
    df2['geom_orig'] = list(zip(df2[lon_col], df2[lat_col]))

    # Create/populate EPSG column
    crs_mask = df2[crs_col].isin(domains.xy_datum().keys())  # w/ known datum
    df2.loc[crs_mask, 'EPSG'] = [domains.xy_datum()[crs]['EPSG'] for crs
                                 in df2.loc[crs_mask, crs_col]]

    # Fix/flag missing
    df2 = infer_CRS(df2, out_EPSG, crs_col=crs_col)

    # Fix/Flag un-recognized CRS
    for crs in set(df2.loc[~crs_mask, crs_col]):
        df2 = infer_CRS(df2, out_EPSG, bad_crs_val=crs, crs_col=crs_col)

    # Transform points by vector (sub-set by datum)
    for datum in set(df2['EPSG'].astype(int)):
        df2 = transform_vector_of_points(df2, datum, out_EPSG)

    # Convert geom to shape object to use with geopandas
    df2['geom'] = [shape({'type': 'Point', 'coordinates': pnt})
                   for pnt in list(df2['geom'])]
    gdf = geopandas.GeoDataFrame(df2, geometry=df2['geom'], crs=out_EPSG)
    if not intermediate_columns:
        # Drop intermediate columns
        gdf = gdf.drop(['geom', 'geom_orig', 'EPSG'], axis=1)

    return gdf


def transform_vector_of_points(df_in, datum, out_EPSG):
    """
    Transform points by vector (sub-set by datum)

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    datum : TYPE
        DESCRIPTION.
    out_EPSG : Integer
        EPSG factory code for desired output Coordinate Reference System datum.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in
    """
    # Create transform object for input datum (EPSG colum) and out_EPSG
    transformer = Transformer.from_crs(datum, out_EPSG)
    d_mask = df_in['EPSG'] == datum  # Mask for datum in subset
    points = df_in.loc[d_mask, 'geom_orig']  # Points series
    # List of transformed point geometries
    new_geoms = [transformer.transform(pnt[0], pnt[1]) for pnt in points]
    # Assign list to df.geom using Index from mask to re-index list
    df_in.loc[d_mask, 'geom'] = pandas.Series(new_geoms,
                                              index=df_in.loc[d_mask].index)
    return df_in


def get_harmonized_stations(query, aoi=None):
    """
    Queries the Water Quality Portal (https://waterquality.data.us) for staions
    with data matching the query, harmonizes those stations location
    information and clips it to the Area Of Interest (aoi) if specified.

    See www.waterqualitydata.us/webservices_documentation for API reference

    Parameters
    ----------
    query : dict
        Water Quality Portal query as dictionary
    aoi : geopandas.GeoDataFrame, optional
        Area of interest to clip stations to.
        The default None returns all stations in the query extent.

    Returns
    -------
    stations_gdf : geopandas.GeoDataFrame
        Harmonized stations.
    stations : pandas.DataFrame
        Raw station results from WQP.
    site_md : TYPE
        WQP query metadata.

    """
    # TODO: **kwargs instead of query dict?

    # Query stations (can be slow)
    if 'dataProfile' in query.keys():
        query.pop('dataProfile')  # TODO: this changes query arg (mutable)
    stations, site_md = wqp.what_sites(**query)

    # Harmonize stations
    stations_gdf = harmonize_locations(stations)

    if aoi is not None:
        # Clip Stations to area of interest
        stations_gdf = wrangle.clip_stations(aoi, stations_gdf)

    return stations_gdf, stations, site_md
