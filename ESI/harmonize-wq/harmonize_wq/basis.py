# -*- coding: utf-8 -*-
"""
Created on Fri Oct 22 10:01:10 2021

Module with basis dictionaries and functions

@author: jbousqui
"""
from warnings import warn
from numpy import nan
from harmonize_wq import harmonize


def unit_basis_dict(out_col):
    """
    Characteristic specific basis dictionary to define basis from units.

    Parameters
    ----------
    out_col : string
        Column name where results are written (char_val derived)

    Returns
    -------
     dict
         Dictionary with logic for determining basis from units string and
         standard pint units to replace those with.
         The structure is {Basis: {standard units: [unit strings with basis]}}.
    """
    dictionary = {'Phosphorus': {'as P': {'mg/l': ['mg/l as P', 'mg/l P'],
                                     'mg/kg': ['mg/kg as P', 'mg/kg P'],},
                            'as PO4': {'mg/l': ['mg/l as PO4',
                                                'mg/l PO4'],
                                       'mg/kg': ['mg/kg as PO4', 'mg/kg PO4'],}
                            },
             'Nitrogen': {'as N': {'mg/l': ['mg/l as N', 'mg/l N'],}},
             'Carbon': {},
             }
    return dictionary[out_col]


def stp_dict():
    """
    Standard temperature and pressure dictionary to define basis from units.

    Returns
    -------
    dict
        DESCRIPTION.

    """
    return {'@25C': {'mg/mL': ['mg/mL @25C'],}}


def basis_from_unit(df_in, basis_dict, unit_col, basis_col='Speciation'):
    """
    Creates a standardized Basis column in DataFrame from units column and
    standardizes units in units column based on basis_dict

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

    """
    df = df_in.copy()
    for base in basis_dict.keys():
        for (new_unit, old_units) in basis_dict[base].items():
            for old_unit in old_units:
                # TODO: Test if old_unit in unit_col first?
                mask = df[unit_col]==old_unit  # Update mask
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
                            qa_mask = mask & (df[basis_col]==old_basis)
                            warn('Mismatched {}'.format(flag))
                            df = harmonize.add_qa_flag(df, qa_mask, flag)
                # Add/update basis from unit
                set_basis(df, mask, base, basis_col)
                df[unit_col] = [new_unit if x==old_unit else x
                                for x in df[unit_col]]
    return df


def basis_from_methodSpec(df_in):
    """
    Moves speciation from 'MethodSpecificationName' column to new 'Speciation'
    Column

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in.

    """
    # Basis from MethodSpecificationName
    old_col = 'MethodSpecificationName'
    df = df_in.copy()
    #TODO: this seems overly-complex to do a pop from one column to another
    # List unique basis
    basis_list = list(set(df[old_col].dropna()))
    for base in basis_list:
        mask = df[old_col]==base
        df = set_basis(df, mask, base)
        # Remove basis from MethodSpecificationName
        df[old_col] = [nan if x==base else x for x in df[old_col]]
    # Test we didn't miss any methodSpec
    assert set(df[old_col].dropna())==set(), (set(df[old_col].dropna()))

    return df


def update_result_basis(df_in, basis_col, unit_col):
    """
    Basis from result col that is not moved to a new col

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    basis_col : string
        Column in df_in with result basis to update. Expected values are
        'ResultTemperatureBasisText'
    unit_col : string
        Column in df_in with units that may contain basis.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in.

    """
    # TODO: make these columns units aware?
    #df = df_in.copy()

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
    basis : string
        The string to use for basis.
    basis_col : string, optional
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

    """
    return '{}: {} {}'.format(spec_col, basis, trouble)
