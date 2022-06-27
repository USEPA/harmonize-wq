# -*- coding: utf-8 -*-
"""
Created on Mon May  9 11:43:25 2022

This module contains functions that can be applied to the entire dataset or
subsets of the dataset to clean/correct additional columns.

@author: jbousqui
"""
#import pandas
from warnings import warn
import dataretrieval.utils
from harmonize_wq import harmonize
from harmonize_wq import domains
from harmonize_wq import wrangle

def datetime(df_in):
    """
    Format time using dataretrieval and ActivityStart

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the expected activity date time columns.

    Returns
    -------
    df_out : pandas.DataFrame
        Dataframe with the converted date and datetime columns.

    """
    df_out = df_in.copy()
    # Backup date (if time is NA datetime is NaT)
    df_out['StartDate'] = df_out['ActivityStartDate']
    df_out = dataretrieval.utils.format_datetime(df_out,
                                             'ActivityStartDate',
                                             'ActivityStartTime/Time',
                                             'ActivityStartTime/TimeZoneCode')
    df_out = df_out.rename(columns={'datetime': 'Activity_datetime'})

    return df_out


def harmonize_depth(df_in, units='meter'):
    """
    Note - doesn't currently pass errors or ureg

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the required ResultDepthHeight columns.
    units : string, optional
        Desired units. The default is 'meter'.

    Returns
    -------
    df_out : pandas.DataFrame
        DataFrame with new Depth colummn replacing ResultDepthHeight columns.

    """
    df_out = df_in.copy()
    # Default columns
    meas_col = 'ResultDepthHeightMeasure/MeasureValue'
    unit_col = 'ResultDepthHeightMeasure/MeasureUnitCode'
    # Note: there are also 'Activity' cols for both of these & top/bottom depth

    harmonize.df_checks(df_out, [meas_col, unit_col]) # Check columns are in df
    na_mask = df_out[meas_col].notna()  # Mask NA to speed up processing
    #TODO: if units missing?
    params = {'quantity_series': df_out.loc[na_mask, meas_col],
              'unit_series': df_out.loc[na_mask, unit_col],
              'units': units,}
    df_out.loc[na_mask, "Depth"] = harmonize.convert_unit_series(**params)

    #TODO: where result depth is missing use activity depth?
    #TODO: drop old cols like datetime does (.pop them)

    return df_out


def methods_check(df_in, char_val, methods=None):
    """
    Check methods against list of accepted methods.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    char_val : string
        Characteristic name.
    methods : dictionary, optional
        Dictionary where key is characteristic column name and value is list of
        dictionaries each with Source and Method keys. This allows updated
        methods dictionaries to be used. The default None, uses the built-in
        domains.accepted_methods().

    Returns
    -------
    None.

    """
    if methods is None:
        methods = domains.accepted_methods()
    method_col = 'ResultAnalyticalMethod/MethodIdentifier'
    #if char_val:
    df2 = df_in.copy()
    #TODO: check df for method_col
    char_mask = df2['CharacteristicName']==char_val
    methods = [item['Method'] for item in methods[char_val]]
    methods_used = list(set(df2.loc[char_mask, method_col].dropna()))
    accept = [method for method in methods_used if method in methods]
    #reject = [method for method in methods_used if method not in methods]
    #TODO: think about how this would be best implemented
    return accept
    # Originally planned to loop over entire list of characteristics
    # else:
    #     char_vals = list(set(df_out['CharacteristicName'].dropna()))
    #     for char_val in char_vals:
    #         methods_check(df_in, char_val)


def wet_dry_checks(df_in, mask=None):
    """
    Fix known errors in MediaName based on WeightBasis and SampleFraction
    columns.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    mask : pandas.Series
        Row conditional (bool) mask to limit df rows to check/fix

    Returns
    -------
    df_out : pandas.DataFrame
        Updated DataFrame

    """
    df_out = df_in.copy()
    media_col = 'ActivityMediaName'
    # Check columns are in df
    harmonize.df_checks(df_out, [media_col,
                                 'ResultSampleFractionText',
                                 'ResultWeightBasisText'])
    # QA - Sample Media, fix assigned 'Water' that are actually 'Sediment'
    qa_flag = '{}: Water changed to Sediment'.format(media_col)
    # Create mask for bad data
    media_mask = ((df_out['ResultSampleFractionText']=='Bed Sediment') &
                  (df_out['ResultWeightBasisText']=='Dry') &
                  (df_out['ActivityMediaName']=='Water'))
    # Use mask if user specified, else run on all rows
    if mask:
        media_mask = mask & (media_mask)
    # Assign QA flag where data was bad
    df_out = harmonize.add_qa_flag(df_out, media_mask, qa_flag)
    # Fix the data
    df_out.loc[media_mask, 'ActivityMediaName'] = 'Sediment'

    return df_out


def wet_dry_drop(df_in, wet_dry='wet', char_val=None):
    """
    Restrict to only water or only sediment samples

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    wet_dry : string, optional
        Which values (Water/Sediment) to keep. The default is 'wet' (Water)
    char_val : string, optional
        Apply to specific characteristic name. The default is None (for all).

    Returns
    -------
    df2 : pandas.DataFrame
        Updated copy of df_in
    """
    df2 = df_in.copy()
    if char_val:
        # Set characteristic mask
        c_mask = df2['CharacteristicName'] == char_val
        # Adding activities fails on len(df)==0, a do-nothing, end it early
        if len(df2[c_mask])==0:
            return df2

    # Set variables for columns and check they're in df
    media_col = 'ActivityMediaName'
    try:
        harmonize.df_checks(df2, media_col)
    except AssertionError:
        problem = "{} missing, querying from activities...".format(media_col)
        warn('Warning: ' + problem)
        # Try query/join
        if char_val:
            df2 = wrangle.add_activities_to_df(df2, c_mask)
        else:
            df2 = wrangle.add_activities_to_df(df2)  # no mask, runs on all
        harmonize.df_checks(df2, [media_col])  # Check it's been added
        # if ERROR?
        #print('Query and join activities first')

    # Fix wet/dry columns
    df2 = wet_dry_checks(df2)  # Changed from df_in?

    # Filter wet/dry rows
    if wet_dry == 'wet':
        media_mask = df2[media_col]=='Water'
    elif wet_dry == 'dry':
        media_mask = df2[media_col]=='Sediment'

    # Filter characteristic rows
    if char_val:
        media_mask = media_mask & c_mask

    return df2.drop(media_mask.index)
