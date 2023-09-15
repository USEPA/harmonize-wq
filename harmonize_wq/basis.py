# -*- coding: utf-8 -*-
"""
    Functions to process characteristic basis or return basis dictionary.
"""
from warnings import warn
from numpy import nan
from harmonize_wq import harmonize


def unit_basis_dict(out_col):
    """
    Characteristic specific basis dictionary to define basis from units.

    Parameters
    ----------
    out_col : str
        Column name where results are written (char_val derived)

    Returns
    -------
     dict
         Dictionary with logic for determining basis from units string and
         standard pint units to replace those with.
         The structure is {Basis: {standard units: [unit strings with basis]}}.
 
    Examples
    --------
    Get dictionary for Phosphorus and subset for 'as P':
    
    >>> from harmonize_wq import basis
    >>> basis.unit_basis_dict('Phosphorus')['as P']
    {'mg/l': ['mg/l as P', 'mg/l P'], 'mg/kg': ['mg/kg as P', 'mg/kg P']}
    """
    dictionary = {'Phosphorus': {'as P': {'mg/l': ['mg/l as P', 'mg/l P'],
                                          'mg/kg': ['mg/kg as P', 'mg/kg P']},
                                 'as PO4': {'mg/l': ['mg/l as PO4',
                                                     'mg/l PO4'],
                                            'mg/kg': ['mg/kg as PO4',
                                                      'mg/kg PO4']}},
                  'Nitrogen': {'as N': {'mg/l': ['mg/l as N', 'mg/l N']}},
                  'Carbon': {},
                  }
    return dictionary[out_col]


def basis_conversion():
    """ Dictionary for converting basis/speciation (e.g., as PO4 -> as P)
    
    Returns
    -------
     dict
         Dictionary with structure {basis: conversion factor}
         
    See Also
    --------
    convert.moles_to_mass()
    
    Originally from Table 1 in Best Practices for Submitting Nutrient Data to
    the Water Quality eXchange (WQX):
    www.epa.gov/sites/default/files/2017-06/documents/wqx_nutrient_best_practices_guide.pdf
    """
    return {'NH3': 0.822,
            'NH4': 0.776,
            'NO2': 0.304,
            'NO3': 0.225,
            'PO4': 0.326}


def stp_dict():
    """
    Standard temperature and pressure dictionary to define basis from units.

    Notes
    -----
        This needs to be updated to include pressure or needs to be renamed.
        
    Returns
    -------
    dict
        Dictionary with {'standard temp' : {'units': [values to replace]}}

    Examples
    --------
    Get dictionary for taking temperature basis our of units:
    
    >>> from harmonize_wq import basis
    >>> basis.stp_dict()
    {'@25C': {'mg/mL': ['mg/mL @25C']}}
    """
    return {'@25C': {'mg/mL': ['mg/mL @25C']}}


def basis_from_unit(df_in, basis_dict, unit_col, basis_col='Speciation'):
    """
    Creates a standardized Basis column in DataFrame from units column and
    standardizes units in units column based on basis_dict. Units column is updated in place, it
    should not be original 'ResultMeasure/MeasureUnitCode' to maintain data integrity.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    basis_dict : dictionary
        Dictionary with structure {basis:{new_unit:[old_units]}}.
    unit_col : str
        string for the column name in df to be used.
    basis_col : str, optional
        string for the basis column name in df to be used.
        The default is 'Speciation'.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in

    Examples
    --------
    Build dataFrame for example:
    
    >>> from pandas import DataFrame
    >>> df = DataFrame({'CharacteristicName': ['Phosphorus', 'Phosphorus',],
    ...                 'ResultMeasure/MeasureUnitCode': ['mg/l as P', 'mg/kg as P'],
    ...                 'Units':  ['mg/l as P', 'mg/kg as P'],
    ...                 })
    >>> df
      CharacteristicName ResultMeasure/MeasureUnitCode       Units
    0         Phosphorus                     mg/l as P   mg/l as P
    1         Phosphorus                    mg/kg as P  mg/kg as P

    >>> from harmonize_wq import basis
    >>> basis_dict = basis.unit_basis_dict('Phosphorus')
    >>> unit_col = 'Units'
    >>> basis.basis_from_unit(df, basis_dict, unit_col)
      CharacteristicName ResultMeasure/MeasureUnitCode  Units Speciation
    0         Phosphorus                     mg/l as P   mg/l       as P
    1         Phosphorus                    mg/kg as P  mg/kg       as P
    
    If an existing basis_col value is different a warning is issued when it is 
    updated and a QA_flag is assigned
    
    >>> from numpy import nan
    >>> df['Speciation'] = [nan, 'as PO4']
    >>> df_speciation_change = basis.basis_from_unit(df, basis_dict, unit_col)
    UserWarning: Mismatched Speciation: updated from as PO4 to as P (units)
    >>> df_speciation_change[['Speciation', 'QA_flag']]
      Speciation                                          QA_flag
    0       as P                                              NaN
    1       as P  Speciation: updated from as PO4 to as P (units)
    """
    df = df_in.copy()
    for base in basis_dict.keys():
        for (new_unit, old_units) in basis_dict[base].items():
            for old_unit in old_units:
                # TODO: Time test if old_unit in unit_col first?
                mask = df[unit_col] == old_unit  # Update mask
                if basis_col in df.columns:
                    # Add flags anywhere the values are updated
                    flag1 = '{}: updated from '.format(basis_col)
                    # List of unique basis values
                    basis_list = list(set(df.loc[mask, basis_col].dropna()))
                    # Loop over existing values in basis field
                    for old_basis in basis_list:
                        flag = '{}{} to {} (units)'.format(flag1, old_basis,
                                                           base)
                        if old_basis != base:
                            qa_mask = mask & (df[basis_col] == old_basis)
                            warn('Mismatched {}'.format(flag))
                            df = harmonize.add_qa_flag(df, qa_mask, flag)
                # Add/update basis from unit
                df = set_basis(df, mask, base, basis_col)
                df[unit_col] = [new_unit if x == old_unit else x
                                for x in df[unit_col]]
    return df


def basis_from_methodSpec(df_in):
    """
    Copy speciation from 'MethodSpecificationName' column to new 'Speciation'
    Column

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in.

    Examples
    --------
    Build dataFrame for example:
    
    >>> from pandas import DataFrame
    >>> from numpy import nan
    >>> df = DataFrame({'CharacteristicName': ['Phosphorus', 'Phosphorus',],
    ...                 'MethodSpecificationName': ['as P', nan],
    ...                 'ProviderName': ['NWIS', 'NWIS',],
    ...                 })
    >>> df
      CharacteristicName MethodSpecificationName ProviderName
    0         Phosphorus                    as P         NWIS
    1         Phosphorus                     NaN         NWIS

    >>> from harmonize_wq import basis    
    >>> basis.basis_from_methodSpec(df)
      CharacteristicName MethodSpecificationName ProviderName Speciation
    0         Phosphorus                    as P         NWIS       as P
    1         Phosphorus                     NaN         NWIS        NaN
    """

    # Basis from MethodSpecificationName
    old_col = 'MethodSpecificationName'
    df = df_in.copy()
    # TODO: this seems overly-complex to do a pop from one column to another,
    # consider _coerce_basis()
    # List unique basis
    basis_list = list(set(df[old_col].dropna()))
    for base in basis_list:
        mask = df[old_col] == base
        df = set_basis(df, mask, base)
        # Remove basis from MethodSpecificationName
        #TODO: why update old field?
        #df[old_col] = [nan if x == base else x for x in df[old_col]]
    # Test we didn't miss any methodSpec
    #assert set(df[old_col].dropna()) == set(), (set(df[old_col].dropna()))

    return df


def update_result_basis(df_in, basis_col, unit_col):
    """
    Basis from result col that is not moved to a new col

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    basis_col : str
        Column in df_in with result basis to update. Expected values are
        'ResultTemperatureBasisText'
    unit_col : str
        Column in df_in with units that may contain basis.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in.

    Examples
    --------
    
    Build dataFrame for example:
    Note: 'Units' is used to preserve 'ResultMeasure/MeasureUnitCode'
    
    >>> from pandas import DataFrame
    >>> from numpy import nan
    >>> df = DataFrame({'CharacteristicName': ['Salinity', 'Salinity',],
    ...                 'ResultTemperatureBasisText': ['25 deg C', nan,],
    ...                 'Units':  ['mg/mL @25C', 'mg/mL @25C'],
    ...                 })
    >>> df
      CharacteristicName ResultTemperatureBasisText       Units
    0           Salinity                   25 deg C  mg/mL @25C
    1           Salinity                        NaN  mg/mL @25C

    >>> from harmonize_wq import basis    
    >>> df_temp_basis = basis.update_result_basis(df,
    ...                                           'ResultTemperatureBasisText',
    ...                                           'Units')
    UserWarning: Mismatched ResultTemperatureBasisText: updated from 25 deg C to @25C (units)
    >>> df_temp_basis[['Units']]
       Units
    0  mg/mL
    1  mg/mL
    >>> df_temp_basis[['ResultTemperatureBasisText', 'QA_flag']]
      ResultTemperatureBasisText                                            QA_flag
    0                       @25C  ResultTemperatureBasisText: updated from 25 de...
    1                       @25C                                                NaN
    """
    # TODO: make these columns units aware?
    # df = df_in.copy()

    # Basis from unit
    if basis_col == 'ResultTemperatureBasisText':
        df_out = basis_from_unit(df_in.copy(), stp_dict(), unit_col, basis_col)
        # NOTE: in the test case 25 deg C -> @25C
    elif basis_col == 'ResultParticleSizeBasisText':
        # NOTE: These are normally 'less than x mm', no errors so far to fix
        df_out = df_in.copy()
    elif basis_col == 'ResultWeightBasisText':
        df_out = df_in.copy()
    elif basis_col == 'ResultTimeBasisText':
        df_out = df_in.copy()
    else:
        raise ValueError('{} not recognized basis column'.format(basis_col))

    return df_out


def set_basis(df_in, mask, basis, basis_col='Speciation'):
    """
    Update DataFrame.basis_col to basis where DataFrame.col is expected_val.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    mask : pandas.Series
        Row conditional mask to limit rows (e.g. to specific unit/speciation).
    basis : str
        The string to use for basis.
    basis_col : str, optional
        The new or existing column for basis string.
        The default is 'Speciation'.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in

    """
    df_out = df_in.copy()
    # Add Basis column if it doesn't exist
    if basis_col not in df_out.columns:
        df_out[basis_col] = nan
    # Populate Basis column where expected value with basis
    df_out.loc[mask, basis_col] = basis
    return df_out


def basis_qa_flag(trouble, basis, spec_col='MethodSpecificationName'):
    """
    NOTE: Deprecate - not currently in use anywhere
    
    Generates a QA_flag string for the MethodsSpeciation column if different
    from the basis specified in units.

    Parameters
    ----------
    trouble : str
        Problem encountered (e.g., unit_basis != speciation).
    basis : str
        The basis from the unit that replaced the original speciation.
    spec_col : str, optional
        Column currently being checked. Default is 'MethodSpecificationName'

    Returns
    -------
    string
        Flag to use in QA_flag column.

    Examples
    --------
    
    Formats QA_Flag
    
    >>> from harmonize_wq import basis
    >>> basis.basis_qa_flag('(units)',
    ...                     'updated from 25 deg C to @25C',
    ...                     'ResultTemperatureBasisText')
    'ResultTemperatureBasisText: updated from 25 deg C to @25C (units)'
    """
    return '{}: {} {}'.format(spec_col, basis, trouble)
