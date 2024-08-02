# -*- coding: utf-8 -*-
"""Functions to clean/correct location data."""

import geopandas
import pandas
from dataretrieval import wqp
from pyproj import Transformer
from shapely.geometry import shape

from harmonize_wq.clean import add_qa_flag, check_precision, df_checks
from harmonize_wq.domains import xy_datum
from harmonize_wq.wrangle import clip_stations


def infer_CRS(
    df_in,
    out_EPSG,
    out_col="EPSG",
    bad_crs_val=None,
    crs_col="HorizontalCoordinateReferenceSystemDatumName",
):
    """Replace missing or unrecognized Coordinate Reference System (CRS).

    Replaces with desired CRS and notes it was missing in 'QA_flag' column.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    out_EPSG : str
        Desired CRS to use.
    out_col : str, optional
        Column in df to write out_EPSG to. The default is 'EPSG'.
    bad_crs_val : str, optional
        Bad Coordinate Reference System (CRS) datum name value to replace.
        The default is None for missing datum.
    crs_col : str, optional
        Datum column in df_in. The default is
        'HorizontalCoordinateReferenceSystemDatumName'.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in.

    Examples
    --------
    Build pandas DataFrame to use in example, where crs_col name is 'Datum'
    rather than default 'HorizontalCoordinateReferenceSystemDatumName':

    >>> from numpy import nan
    >>> df_in = pandas.DataFrame({'Datum': ['NAD83', 'WGS84', '', None, nan]})
    >>> df_in  # doctest: +NORMALIZE_WHITESPACE
       Datum
    0  NAD83
    1  WGS84
    2
    3   None
    4    NaN

    >>> from harmonize_wq import location
    >>> location.infer_CRS(df_in, out_EPSG=4326, crs_col='Datum')
    ... # doctest: +NORMALIZE_WHITESPACE
       Datum                                  QA_flag    EPSG
    0  NAD83                                      NaN     NaN
    1  WGS84                                      NaN     NaN
    2                                             NaN     NaN
    3   None  Datum: MISSING datum, EPSG:4326 assumed  4326.0
    4    NaN  Datum: MISSING datum, EPSG:4326 assumed  4326.0

    NOTE: missing (NaN) and bad CRS values (bad_crs_val=None) are given an EPSG
    and noted in QA_flag' columns.
    """
    df_out = df_in.copy()
    if bad_crs_val:
        # QA flag for bad CRS based on bad_crs_val
        flag = f"{crs_col}: Bad datum {bad_crs_val}, EPSG:{out_EPSG} assumed"
        c_mask = df_out[crs_col] == bad_crs_val  # Mask for bad CRS value
    else:
        # QA flag for missing CRS
        flag = f"{crs_col}: MISSING datum, EPSG:{out_EPSG} assumed"
        c_mask = df_out[crs_col].isna()  # Mask for missing units
    df_out = add_qa_flag(df_out, c_mask, flag)  # Assign flag
    df_out.loc[c_mask, out_col] = out_EPSG  # Update with infered unit

    return df_out


def harmonize_locations(df_in, out_EPSG=4326, intermediate_columns=False, **kwargs):
    """Create harmonized geopandas GeoDataframe from pandas DataFrame.

    Takes a :class:`~pandas.DataFrame` with lat/lon in multiple Coordinate
    Reference Systems (CRS), transforms them to out_EPSG CRS, and converts to
    :class:`geopandas.GeoDataFrame`. A 'QA_flag' column is added to the result
    and populated for any row that has location based problems like limited
    decimal precision or an unknown input CRS.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the required columns (see kwargs for expected defaults)
        to be converted to GeoDataFrame.
    out_EPSG : int, optional
        EPSG factory code for desired output Coordinate Reference System datum.
        The default is 4326, for the WGS84 Datum used by WQP queries.
    intermediate_columns : Boolean, optional
        Return intermediate columns. Default 'False' does not return these.
    **kwargs: optional
       Accepts crs_col, lat_col, and lon_col parameters if non-default:
    crs_col : str, optional
        Name of column in DataFrame with the Coordinate Reference System datum.
        The default is 'HorizontalCoordinateReferenceSystemDatumName'.
    lat_col : str, optional
        Name of column in DataFrame with the latitude coordinate.
        The default is 'LatitudeMeasure'.
    lon_col : str, optional
        Name of column in DataFrame with the longitude coordinate.
        The default is 'LongitudeMeasure'.

    Returns
    -------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame of df_in with coordinates in out_EPSG datum.

    Examples
    --------
    Build pandas DataFrame to use in example:

    >>> df_in = pandas.DataFrame(
    ...     {
    ...         "LatitudeMeasure": [27.5950355, 27.52183, 28.0661111],
    ...         "LongitudeMeasure": [-82.0300865, -82.64476, -82.3775],
    ...         "HorizontalCoordinateReferenceSystemDatumName":
    ...             ["NAD83", "WGS84", "NAD27"],
    ...     }
    ... )
    >>> df_in
       LatitudeMeasure  ...  HorizontalCoordinateReferenceSystemDatumName
    0        27.595036  ...                                         NAD83
    1        27.521830  ...                                         WGS84
    2        28.066111  ...                                         NAD27
    <BLANKLINE>
    [3 rows x 3 columns]

    >>> from harmonize_wq import location
    >>> location.harmonize_locations(df_in)
       LatitudeMeasure  LongitudeMeasure  ... QA_flag                    geometry
    0        27.595036        -82.030086  ...     NaN  POINT (-82.03009 27.59504)
    1        27.521830        -82.644760  ...     NaN  POINT (-82.64476 27.52183)
    2        28.066111        -82.377500  ...     NaN  POINT (-82.37750 28.06611)
    <BLANKLINE>
    [3 rows x 5 columns]
    """
    df2 = df_in.copy()

    # Default columns
    crs_col = kwargs.get("crs_col", "HorizontalCoordinateReferenceSystemDatumName")
    lat_col = kwargs.get("lat_col", "LatitudeMeasure")
    lon_col = kwargs.get("lon_col", "LongitudeMeasure")

    # Check columns are in df
    df_checks(df2, [crs_col, lat_col, lon_col])

    # Check location precision
    df2 = check_precision(df2, lat_col)
    df2 = check_precision(df2, lon_col)

    # Create tuple column
    df2["geom_orig"] = list(zip(df2[lon_col], df2[lat_col]))

    # Create/populate EPSG column
    crs_mask = df2[crs_col].isin(xy_datum.keys())  # w/ known datum
    df2.loc[crs_mask, "EPSG"] = [
        xy_datum[crs]["EPSG"] for crs in df2.loc[crs_mask, crs_col]
    ]

    # Fix/flag missing
    df2 = infer_CRS(df2, out_EPSG, crs_col=crs_col)

    # Fix/Flag un-recognized CRS
    for crs in set(df2.loc[~crs_mask, crs_col]):
        df2 = infer_CRS(df2, out_EPSG, bad_crs_val=crs, crs_col=crs_col)

    # Transform points by vector (sub-set by datum)
    for datum in set(df2["EPSG"].astype(int)):
        df2 = transform_vector_of_points(df2, datum, out_EPSG)

    # Convert geom to shape object to use with geopandas
    df2["geom"] = [
        shape({"type": "Point", "coordinates": pnt}) for pnt in list(df2["geom"])
    ]
    gdf = geopandas.GeoDataFrame(df2, geometry=df2["geom"], crs=out_EPSG)
    if not intermediate_columns:
        # Drop intermediate columns
        gdf = gdf.drop(["geom", "geom_orig", "EPSG"], axis=1)

    return gdf


def transform_vector_of_points(df_in, datum, out_EPSG):
    """Transform points by vector (sub-sets points by EPSG==datum).

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    datum : int
        Current datum (EPSG code) to transform.
    out_EPSG : int
        EPSG factory code for desired output Coordinate Reference System datum.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in.
    """
    # Create transform object for input datum (EPSG colum) and out_EPSG
    transformer = Transformer.from_crs(datum, out_EPSG)
    d_mask = df_in["EPSG"] == datum  # Mask for datum in subset
    points = df_in.loc[d_mask, "geom_orig"]  # Points series
    # List of transformed point geometries
    new_geoms = [transformer.transform(pnt[0], pnt[1]) for pnt in points]
    # Assign list to df.geom using Index from mask to re-index list
    df_in.loc[d_mask, "geom"] = pandas.Series(new_geoms, index=df_in.loc[d_mask].index)
    return df_in


def get_harmonized_stations(query, aoi=None):
    """Query, harmonize and clip stations.

    Queries the `Water Quality Portal <https://waterquality.data.us>`_ for
    stations with data matching the query, harmonizes those stations' location
    information, and clips it to the area of interest (aoi) if specified.

    See `<www.waterqualitydata.us/webservices_documentation>`_ for API
    reference.

    Parameters
    ----------
    query : dict
        Water Quality Portal query as dictionary.
    aoi : geopandas.GeoDataFrame, optional
        Area of interest to clip stations to.
        The default None returns all stations in the query extent.

    Returns
    -------
    stations_gdf : ``geopandas.GeoDataFrame``
        Harmonized stations.
    stations : ``pandas.DataFrame``
        Raw station results from WQP.
    site_md : ``dataretrieval.utils.Metadata``
        Custom ``dataretrieval`` metadata object pertaining to the WQP query.

    Examples
    --------
    See any of the 'Simple' notebooks found in
    'demos<https://github.com/USEPA/harmonize-wq/tree/main/demos>'_ for
    examples of how this function is used to query and harmonize stations.

    """
    # TODO: **kwargs instead of query dict?

    # Query stations (can be slow)
    if "dataProfile" in query.keys():
        query.pop("dataProfile")  # TODO: this changes query arg (mutable)
    stations, site_md = wqp.what_sites(**query)

    # Harmonize stations
    stations_gdf = harmonize_locations(stations)

    if aoi is not None:
        # Clip Stations to area of interest
        stations_gdf = clip_stations(stations_gdf, aoi)

    return stations_gdf, stations, site_md
