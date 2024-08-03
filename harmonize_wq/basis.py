# -*- coding: utf-8 -*-
"""Functions to process characteristic basis or return basis dictionary.

Attributes
----------
unit_basis_dict : dict
  Characteristic specific basis dictionary to define basis from units.

  Notes
  -----
  Dictionary with logic for determining basis from units string and
  standard :mod:`pint` units to replace those with.
  The structure is {Basis: {standard units: [unit strings with basis]}}.

  The out_col is often derived from :attr:`WQCharData.char_val`. The desired
  basis can be used as a key to subset result.

  Examples
  --------
  Get dictionary for Phosphorus and subset for 'as P':

  >>> from harmonize_wq import basis
  >>> basis.unit_basis_dict['Phosphorus']['as P']
  {'mg/l': ['mg/l as P', 'mg/l P'], 'mg/kg': ['mg/kg as P', 'mg/kg P']}

basis_conversion : dict
  Get dictionary of conversion factors to convert basis/speciation.
  For example, this is used to convert 'as PO4' to 'as P'.
  Dictionary structure {basis: conversion factor}.

  See Also
  --------
  :func:`convert.moles_to_mass`

  `Best Practices for Submitting Nutrient Data to the Water Quality eXchange
  <www.epa.gov/sites/default/files/2017-06/documents/wqx_nutrient_best_practices_guide.pdf>`_

stp_dict : dict
  Get standard temperature and pressure to define basis from units.
  Dictionary structure {'standard temp' : {'units': [values to replace]}}.

  Notes
  -----
  This needs to be updated to include pressure or needs to be renamed.
"""

from warnings import warn

import numpy

from harmonize_wq.clean import add_qa_flag

unit_basis_dict = {
    "Phosphorus": {
        "as P": {"mg/l": ["mg/l as P", "mg/l P"], "mg/kg": ["mg/kg as P", "mg/kg P"]},
        "as PO4": {
            "mg/l": ["mg/l as PO4", "mg/l PO4"],
            "mg/kg": ["mg/kg as PO4", "mg/kg PO4"],
        },
    },
    "Nitrogen": {"as N": {"mg/l": ["mg/l as N", "mg/l N"]}},
    "Carbon": {},
}

basis_conversion = {
    "NH3": 0.822,
    "NH4": 0.776,
    "NO2": 0.304,
    "NO3": 0.225,
    "PO4": 0.326,
}

stp_dict = {"@25C": {"mg/mL": ["mg/mL @25C"]}}


def basis_from_unit(df_in, basis_dict, unit_col="Units", basis_col="Speciation"):
    """Move basis from units to basis column in :class:`pandas.DataFrame`.

    Move basis information from units in unit_col column to basis in basis_col
    column based on basis_dict. If basis_col does not exist in df_in it will be
    created. The unit_col column is updated in place. To maintain data
    integrity unit_col should not be the original
    'ResultMeasure/MeasureUnitCode' column.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    basis_dict : dict
        Dictionary with structure {basis:{new_unit:[old_units]}}.
    unit_col : str, optional
        String for the units column name in df_in to use.
        The default is 'Units'.
    basis_col : str, optional
        String for the basis column name in df_in to use.
        The default is 'Speciation'.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in.

    Examples
    --------
    Build pandas DataFrame for example:

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
    >>> basis_dict = basis.unit_basis_dict['Phosphorus']
    >>> unit_col = 'Units'
    >>> basis.basis_from_unit(df, basis_dict, unit_col)
      CharacteristicName ResultMeasure/MeasureUnitCode  Units Speciation
    0         Phosphorus                     mg/l as P   mg/l       as P
    1         Phosphorus                    mg/kg as P  mg/kg       as P

    If an existing basis_col value is different, a warning is issued when it is
    updated and a QA_flag is assigned:

    >>> from numpy import nan
    >>> df['Speciation'] = [nan, 'as PO4']
    >>> df_speciation_change = basis.basis_from_unit(df, basis_dict, unit_col)
    ... # doctest: +IGNORE_RESULT
    UserWarning: Mismatched Speciation: updated from as PO4 to as P (units)
    >>> df_speciation_change[['Speciation', 'QA_flag']]
      Speciation                                          QA_flag
    0       as P                                              NaN
    1       as P  Speciation: updated from as PO4 to as P (units)
    """
    df = df_in.copy()
    for base in basis_dict.keys():
        for new_unit, old_units in basis_dict[base].items():
            for old_unit in old_units:
                # TODO: Time test if old_unit in unit_col first?
                mask = df[unit_col] == old_unit  # Update mask
                if basis_col in df.columns:
                    # Add flags anywhere the values are updated
                    flag1 = f"{basis_col}: updated from "
                    # List of unique basis values
                    basis_list = df.loc[mask, basis_col].dropna().unique()
                    # Loop over existing values in basis field
                    for old_basis in basis_list:
                        flag = f"{flag1}{old_basis} to {base} (units)"
                        if old_basis != base:
                            qa_mask = mask & (df[basis_col] == old_basis)
                            warn(f"Mismatched {flag}", UserWarning)
                            df = add_qa_flag(df, qa_mask, flag)
                # Add/update basis from unit
                df = set_basis(df, mask, base, basis_col)
                df[unit_col] = [new_unit if x == old_unit else x for x in df[unit_col]]
    return df


def basis_from_method_spec(df_in):
    """Copy speciation from MethodSpecificationName to new 'Speciation' column.

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
    Build pandas DataFrame for example:

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
    >>> basis.basis_from_method_spec(df)
      CharacteristicName MethodSpecificationName ProviderName Speciation
    0         Phosphorus                    as P         NWIS       as P
    1         Phosphorus                     NaN         NWIS        NaN
    """
    # Basis from MethodSpecificationName
    old_col = "MethodSpecificationName"
    df = df_in.copy()
    # TODO: this seems overly-complex to do a pop from one column to another,
    # consider _coerce_basis()
    # List unique basis
    basis_list = list(set(df[old_col].dropna()))
    for base in basis_list:
        mask = df[old_col] == base
        df = set_basis(df, mask, base)
        # Remove basis from MethodSpecificationName
        # TODO: why update old field?
        # df[old_col] = [nan if x == base else x for x in df[old_col]]
    # Test we didn't miss any methodSpec
    # assert set(df[old_col].dropna()) == set(), (set(df[old_col].dropna()))

    return df


def update_result_basis(df_in, basis_col, unit_col):
    """Move basis from unit_col column to basis_col column.

    This is usually used in place of basis_from_unit when the basis_col is not
    'ResultMeasure/MeasureUnitCode' (i.e., not speciation).

    Notes
    -----
    Currently overwrites the original basis_col values rather than create many new empty
    columns. The original values are noted in the QA_flag.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    basis_col : str
        Column in df_in with result basis to update. Expected values are
        'ResultTemperatureBasisText'.
    unit_col : str
        Column in df_in with units that may contain basis.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in.

    Examples
    --------
    Build pandas DataFrame for example:

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
    ... # doctest: +IGNORE_RESULT
    UserWarning: Mismatched ResultTemperatureBasisText: updated from 25 deg C to @25C
    (units)
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
    if basis_col == "ResultTemperatureBasisText":
        df_out = basis_from_unit(df_in.copy(), stp_dict, unit_col, basis_col)
        # NOTE: in the test case 25 deg C -> @25C
    elif basis_col == "ResultParticleSizeBasisText":
        # NOTE: These are normally 'less than x mm', no errors so far to fix
        df_out = df_in.copy()
    elif basis_col == "ResultWeightBasisText":
        df_out = df_in.copy()
    elif basis_col == "ResultTimeBasisText":
        df_out = df_in.copy()
    else:
        raise ValueError(f"{basis_col} not recognized basis column")

    return df_out


def set_basis(df_in, mask, basis, basis_col="Speciation"):
    """Update or create basis_col with basis as value.

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
        Updated copy of df_in.

    Examples
    --------
    Build pandas DataFrame for example:

    >>> from pandas import DataFrame
    >>> df = DataFrame({'CharacteristicName': ['Phosphorus',
    ...                                        'Phosphorus',
    ...                                        'Salinity'],
    ...                 'MethodSpecificationName': ['as P', 'as PO4', ''],
    ...                 })
    >>> df  # doctest: +NORMALIZE_WHITESPACE
      CharacteristicName MethodSpecificationName
    0         Phosphorus                    as P
    1         Phosphorus                  as PO4
    2           Salinity

    Build mask for example:

    >>> mask = df['CharacteristicName']=='Phosphorus'

    >>> from harmonize_wq import basis
    >>> basis.set_basis(df, mask, basis='as P')
      CharacteristicName MethodSpecificationName Speciation
    0         Phosphorus                    as P       as P
    1         Phosphorus                  as PO4       as P
    2           Salinity                                NaN
    """
    df_out = df_in.copy()
    if basis_col not in df_out.columns:
        df_out[basis_col] = numpy.nan
    # Otherwise don't mess with existing values that are not part of mask
    df_out.loc[mask, basis_col] = basis
    return df_out
