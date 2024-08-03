# -*- coding: utf-8 -*-
"""Functions to clean/correct additional columns in subset/entire dataset."""

# from warnings import warn
import dataretrieval.utils
from numpy import nan

from harmonize_wq.convert import convert_unit_series
from harmonize_wq.domains import accepted_methods

# from harmonize_wq.wrangle import add_activities_to_df


def datetime(df_in):
    """Format time using :mod:`dataretrieval` and 'ActivityStart' columns.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the expected activity date, time and timezone columns.

    Returns
    -------
    df_out : pandas.DataFrame
        DataFrame with the converted datetime column.

    Examples
    --------
    Build pandas DataFrame for example:

    >>> from pandas import DataFrame
    >>> from numpy import nan
    >>> df = DataFrame({'ActivityStartDate': ['2004-09-01', '2004-07-01',],
    ...                 'ActivityStartTime/Time': ['10:01:00', nan,],
    ...                 'ActivityStartTime/TimeZoneCode':  ['EST', nan],
    ...                 })
    >>> df
      ActivityStartDate ActivityStartTime/Time ActivityStartTime/TimeZoneCode
    0        2004-09-01               10:01:00                            EST
    1        2004-07-01                    NaN                            NaN
    >>> from harmonize_wq import clean
    >>> clean.datetime(df)
      ActivityStartDate  ...         Activity_datetime
    0        2004-09-01  ... 2004-09-01 15:01:00+00:00
    1        2004-07-01  ...                       NaT
    <BLANKLINE>
    [2 rows x 4 columns]
    """
    # Expected columns
    date, time, tz = (
        "ActivityStartDate",
        "ActivityStartTime/Time",
        "ActivityStartTime/TimeZoneCode",
    )
    df_out = df_in.copy()
    # NOTE: even if date, if time is NA datetime is NaT
    df_out = dataretrieval.utils.format_datetime(df_out, date, time, tz)
    df_out = df_out.rename(columns={"datetime": "Activity_datetime"})

    return df_out


def harmonize_depth(df_in, units="meter"):
    """Create 'Depth' column with result depth values in consistent units.

    New column combines values from the 'ResultDepthHeightMeasure/MeasureValue' column
    with units from the 'ResultDepthHeightMeasure/MeasureUnitCode' column.

    Notes
    -----
    Currently unit registry (ureg) updates or errors are not passed back.
    In the future activity depth columns may be considered if result depth missing.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the required 'ResultDepthHeight' columns.
    units : str, optional
        Desired units. The default is 'meter'.

    Returns
    -------
    df_out : pandas.DataFrame
        DataFrame with new Depth column replacing 'ResultDepthHeight' columns.

    Examples
    --------
    Build pandas DataFrame for example:

    >>> from pandas import DataFrame
    >>> from numpy import nan
    >>> df = DataFrame({'ResultDepthHeightMeasure/MeasureValue': ['3.0', nan, 10],
    ...                 'ResultDepthHeightMeasure/MeasureUnitCode': ['m', nan, 'ft'],
    ...                 })
    >>> df
      ResultDepthHeightMeasure/MeasureValue ResultDepthHeightMeasure/MeasureUnitCode
    0                                   3.0                                        m
    1                                   NaN                                      NaN
    2                                    10                                       ft

    Get clean 'Depth' column:

    >>> from harmonize_wq import clean
    >>> clean.harmonize_depth(df)[['ResultDepthHeightMeasure/MeasureValue',
    ...                            'Depth']]
      ResultDepthHeightMeasure/MeasureValue                     Depth
    0                                   3.0                 3.0 meter
    1                                   NaN                       NaN
    2                                    10  3.0479999999999996 meter
    """
    df_out = df_in.copy()
    # Default columns
    meas_col = "ResultDepthHeightMeasure/MeasureValue"
    unit_col = "ResultDepthHeightMeasure/MeasureUnitCode"
    # Note: there are also 'Activity' cols for both of these & top/bottom depth

    df_checks(df_out, [meas_col, unit_col])  # Confirm columns in df
    na_mask = df_out[meas_col].notna()  # Mask NA to speed up processing
    # TODO: if units missing?
    params = {
        "quantity_series": df_out.loc[na_mask, meas_col],
        "unit_series": df_out.loc[na_mask, unit_col],
        "units": units,
    }
    df_out.loc[na_mask, "Depth"] = convert_unit_series(**params)

    # TODO: where result depth is missing use activity depth?

    return df_out


def df_checks(df_in, columns=None):
    """Check :class:`pandas.DataFrame` for columns.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be checked.
    columns : list, optional
        List of strings for column names. Default None, uses:
        'ResultMeasure/MeasureUnitCode','ResultMeasureValue','CharacteristicName'.

    Examples
    --------
    Build pandas DataFrame for example:

    >>> from pandas import DataFrame
    >>> df = DataFrame({'CharacteristicName': ['Phosphorus'],})
    >>> df
      CharacteristicName
    0         Phosphorus

    Check for existing column:

    >>> from harmonize_wq import clean
    >>> clean.df_checks(df, columns=['CharacteristicName'])

    If column is not in DataFrame it throws an AssertionError:

    >>> clean.df_checks(df, columns=['ResultMeasureValue'])
    Traceback (most recent call last):
        ...
    AssertionError: ResultMeasureValue not in DataFrame

    """
    if columns is None:
        # Assign defaults
        columns = (
            "ResultMeasure/MeasureUnitCode",
            "ResultMeasureValue",
            "CharacteristicName",
        )
    for col in columns:
        assert col in df_in.columns, f"{col} not in DataFrame"


def check_precision(df_in, col, limit=3):
    """Add QA_flag if value in column has precision lower than limit.

    Notes
    -----
    Be cautious of float type and real vs representable precision.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the required 'ResultDepthHeight' columns.
    unit_col : str
        Desired column in df_in.
    limit : int, optional
        Number of decimal places under which to detect. The default is 3.

    Returns
    -------
    df_out : pandas.DataFrame
        DataFrame with the quality assurance flag for precision.

    """
    df_out = df_in.copy()
    # Create T/F mask based on len of everything after the decimal
    c_mask = [len(str(x).split(".")[1]) < limit for x in df_out[col]]
    flag = f"{col}: Imprecise: lessthan{limit}decimaldigits"
    df_out = add_qa_flag(df_out, c_mask, flag)  # Assign flags
    return df_out


def methods_check(df_in, char_val, methods=None):
    """Check methods against list of accepted methods.

    Notes
    -----
    This is not fully implemented.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    char_val : str
        Characteristic name.
    methods : dict, optional
        Dictionary where key is characteristic column name and value is list of
        dictionaries each with Source and Method keys. This allows updated
        methods dictionaries to be used. The default None uses the built-in
        :meth:`domains.accepted_methods`.

    Returns
    -------
    accept : list
        List of values from 'ResultAnalyticalMethod/MethodIdentifier' column in methods.

    """
    if methods is None:
        methods = accepted_methods
    method_col = "ResultAnalyticalMethod/MethodIdentifier"
    df2 = df_in.copy()
    # TODO: check df for method_col
    char_mask = df2["CharacteristicName"] == char_val
    methods = [item["Method"] for item in methods[char_val]]
    methods_used = list(set(df2.loc[char_mask, method_col].dropna()))
    accept = [method for method in methods_used if method in methods]
    # reject = [method for method in methods_used if method not in methods]
    # TODO: think about how this would be best implemented
    return accept
    # Originally planned to loop over entire list of characteristics
    # else:
    #     char_vals = list(set(df_out['CharacteristicName'].dropna()))
    #     for char_val in char_vals:
    #         methods_check(df_in, char_val)


def wet_dry_checks(df_in, mask=None):
    """Fix suspected errors in 'ActivityMediaName' column.

    Uses the 'ResultWeightBasisText' and 'ResultSampleFractionText' columns to
    switch if the media is wet/dry where appropriate.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    mask : pandas.Series
        Row conditional (bool) mask to limit df rows to check/fix. The default is None.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated DataFrame.

    """
    df_out = df_in.copy()
    media_col = "ActivityMediaName"
    # Check columns are in df
    df_checks(df_out, [media_col, "ResultSampleFractionText", "ResultWeightBasisText"])
    # QA - Sample Media, fix assigned 'Water' that are actually 'Sediment'
    qa_flag = f"{media_col}: Water changed to Sediment"
    # Create mask for bad data
    media_mask = (
        (df_out["ResultSampleFractionText"] == "Bed Sediment")
        & (df_out["ResultWeightBasisText"] == "Dry")
        & (df_out["ActivityMediaName"] == "Water")
    )
    # Use mask if user specified, else run on all rows
    if mask:
        media_mask = mask & (media_mask)
    # Assign QA flag where data was bad
    df_out = add_qa_flag(df_out, media_mask, qa_flag)
    # Fix the data
    df_out.loc[media_mask, "ActivityMediaName"] = "Sediment"

    return df_out


def add_qa_flag(df_in, mask, flag):
    """Add flag to 'QA_flag' column in df_in.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    mask : pandas.Series
        Row conditional mask to limit rows.
    flag : str
        Text to populate the new flag with.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in.

    Examples
    --------
    Build pandas DataFrame to use as input:

    >>> from pandas import DataFrame
    >>> df = DataFrame({'CharacteristicName': ['Carbon', 'Phosphorus', 'Carbon',],
    ...                 'ResultMeasureValue': ['1.0', '0.265', '2.1'],})
    >>> df
      CharacteristicName ResultMeasureValue
    0             Carbon                1.0
    1         Phosphorus              0.265
    2             Carbon                2.1

    Assign simple flag string and mask to assign flag only to Carbon:

    >>> flag = 'words'
    >>> mask = df['CharacteristicName']=='Carbon'

    >>> from harmonize_wq import clean
    >>> clean.add_qa_flag(df, mask, flag)
      CharacteristicName ResultMeasureValue QA_flag
    0             Carbon                1.0   words
    1         Phosphorus              0.265     NaN
    2             Carbon                2.1   words
    """
    df_out = df_in.copy()
    if "QA_flag" not in list(df_out.columns):
        df_out["QA_flag"] = nan

    # Append flag where QA_flag is not nan
    cond_notna = mask & (df_out["QA_flag"].notna())  # Mask cond and not NA
    existing_flags = df_out.loc[cond_notna, "QA_flag"]  # Current QA flags
    df_out.loc[cond_notna, "QA_flag"] = [f"{txt}; {flag}" for txt in existing_flags]
    # Equals flag where QA_flag is nan
    df_out.loc[mask & (df_out["QA_flag"].isna()), "QA_flag"] = flag

    return df_out


def wet_dry_drop(df_in, wet_dry="wet", char_val=None):
    """Restrict to only water or only sediment samples.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    wet_dry : str, optional
        Which values (Water/Sediment) to keep. The default is 'wet' (Water).
    char_val : str, optional
        Apply to specific characteristic name. The default is None (for all).

    Returns
    -------
    df2 : pandas.DataFrame
        Updated copy of df_in.
    """
    df2 = df_in.copy()
    if char_val:
        # Set characteristic mask
        c_mask = df2["CharacteristicName"] == char_val
        # Adding activities fails on len(df)==0, a do-nothing, end it early
        if len(df2[c_mask]) == 0:
            return df2

    # Set variables for columns and check they're in df
    media_col = "ActivityMediaName"
    #    try:
    df_checks(df2, media_col)
    #    except AssertionError:
    #        warn(f'Warning: {media_col} missing, querying from activities...')
    # Try query/join
    #        if char_val:
    #            df2 = add_activities_to_df(df2, c_mask)
    #        else:
    #            df2 = add_activities_to_df(df2)  # no mask, runs on all
    #        df_checks(df2, [media_col])  # Check it's been added
    # if ERROR?
    # print('Query and join activities first')

    # Fix wet/dry columns
    df2 = wet_dry_checks(df2)  # Changed from df_in?

    # Filter wet/dry rows
    if wet_dry == "wet":
        media_mask = df2[media_col] == "Water"
    elif wet_dry == "dry":
        media_mask = df2[media_col] == "Sediment"

    # Filter characteristic rows
    if char_val:
        media_mask = media_mask & c_mask

    return df2.drop(media_mask.index)
