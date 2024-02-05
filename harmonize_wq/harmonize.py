# -*- coding: utf-8 -*-
"""Functions to harmonize data retrieved from EPA's Water Quality Portal."""
from warnings import warn
import pandas
import pint
from numpy import nan
from harmonize_wq.wq_data import WQCharData
from harmonize_wq import domains
from harmonize_wq import convert
from harmonize_wq import visualize as viz


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

    >>> from harmonize_wq import harmonize
    >>> harmonize.df_checks(df, columns=['CharacteristicName'])
    
    If column is not in DataFrame it throws an AssertionError:
        
    >>> harmonize.df_checks(df, columns=['ResultMeasureValue'])
    Traceback (most recent call last):
        ...
    AssertionError: ResultMeasureValue not in DataFrame
    
    """
    if columns is None:
        # Assign defaults
        columns = ('ResultMeasure/MeasureUnitCode',
                   'ResultMeasureValue',
                   'CharacteristicName')
    for col in columns:
        assert col in df_in.columns, f'{col} not in DataFrame'


#timeit: 159.17
# def convert_unit_series(quantity_series, unit_series, units, ureg=None):
#     # Convert quantities to float if they aren't already (should be)
#     if quantity_series.dtype=='O':
#         quantity_series = pandas.to_numeric(quantity_series)
#     # Initialize classes from pint
#     if ureg is None:
#         ureg = pint.UnitRegistry()
#     Q_ = ureg.Quantity
#     # Create list of Quantity objects
#     val_list = [Q_(q, ureg(unit)) for q, unit in zip(quantity_series,
#                                                      unit_series)]
#     # Convert Quantity objects to new unit
#     out_list = [val.to(ureg(units)) for val in val_list]
#     # Re-index to return series
#     return pandas.Series(out_list, index=quantity_series.index)
#timeit: 27.08
def convert_unit_series(quantity_series, unit_series, units, ureg=None, errors='raise'):
    """Convert quantities to consistent units.

    Convert list of quantities (quantity_list), each with a specified old unit,
    to a quantity in units using :mod:`pint` constructor method.

    Parameters
    ----------
    quantity_series : pandas.Series
        List of quantities. Values should be numeric, must not include NaN.
    unit_series : pandas.Series
        List of units for each quantity in quantity_series. Values should be
        string, must not include NaN.
    units : str
        Desired units.
    ureg : pint.UnitRegistry, optional
        Unit Registry Object with any custom units defined. The default is None.
    errors : str, optional
        Values of ‘ignore’, ‘raise’, or ‘skip’. The default is ‘raise’.
        If ‘raise’, invalid dimension conversions will raise an exception.
        If ‘skip’, invalid dimension conversions will not be converted.
        If ‘ignore’, invalid dimension conversions will return the NaN.

    Returns
    -------
    pandas.Series
        Converted values from quantity_series in units with original index.

    Examples
    --------
    Build series to use as input:
    
    >>> from pandas import Series
    >>> quantity_series = Series([1, 10])
    >>> unit_series = Series(['mg/l', 'mg/ml',])

    Convert series to series of pint Quantity objects in 'mg/l':
    
    >>> from harmonize_wq import harmonize
    >>> harmonize.convert_unit_series(quantity_series, unit_series, units = 'mg/l')
    0                   1.0 milligram / liter
    1    10000.000000000002 milligram / liter
    dtype: object
    """
    if quantity_series.dtype=='O':
        quantity_series = pandas.to_numeric(quantity_series)
    # Initialize classes from pint
    if ureg is None:
        ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    lst_series = [pandas.Series(dtype='object')]
    # Note: set of series does not preservce order and must be sorted at end
    for unit in list(set(unit_series)):
        # Filter quantity_series by unit_series where == unit
        f_quant_series = quantity_series.where(unit_series==unit).dropna()
        unit_ = ureg(unit)  # Set unit once per unit
        result_list = [Q_(q, unit_) for q in f_quant_series]
        if unit != units:
            # Convert (units are all same so if one fails all will fail)
            try:
                result_list = [val.to(ureg(units)) for val in result_list]
            except pint.DimensionalityError as exception:
                if errors=='skip':
                    # do nothing, leave result_list unconverted
                    warn(f"WARNING: '{unit}' not converted")
                elif errors=='ignore':
                    # convert to NaN
                    result_list = [nan for val in result_list]
                    warn(f"WARNING: '{unit}' converted to NaN")
                else:
                    # errors=='raise', or anything else just in case
                    raise exception
        # Re-index and add series to list
        lst_series.append(pandas.Series(result_list, index=f_quant_series.index))
    return pandas.concat(lst_series).sort_index()


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
    
    >>> from harmonize_wq import harmonize
    >>> harmonize.add_qa_flag(df, mask, flag)
      CharacteristicName ResultMeasureValue QA_flag
    0             Carbon                1.0   words
    1         Phosphorus              0.265     NaN
    2             Carbon                2.1   words
    """
    df_out = df_in.copy()
    if 'QA_flag' not in list(df_out.columns):
        df_out['QA_flag'] = nan

    # Append flag where QA_flag is not nan
    cond_notna = mask & (df_out['QA_flag'].notna())  # Mask cond and not NA
    existing_flags = df_out.loc[cond_notna, 'QA_flag']  # Current QA flags
    df_out.loc[cond_notna, 'QA_flag'] = [f'{txt}; {flag}' for
                                         txt in existing_flags]
    # Equals flag where QA_flag is nan
    df_out.loc[mask & (df_out['QA_flag'].isna()), 'QA_flag'] = flag

    return df_out


def units_dimension(series_in, units, ureg=None):
    """List unique units not in desired units dimension.

    Parameters
    ----------
    series_in : pandas.Series
        Series of units.
    units : str
        Desired units.
    ureg : pint.UnitRegistry, optional
        Unit Registry Object with any custom units defined.
        The default is None.

    Returns
    -------
    dim_list : list
        List of units with mismatched dimensions.

    Examples
    --------
    Build series to use as input:
    
    >>> from pandas import Series
    >>> unit_series = Series(['mg/l', 'mg/ml', 'g/kg'])
    >>> unit_series
    0     mg/l
    1    mg/ml
    2     g/kg
    dtype: object

    Get list of unique units not in desired units dimension 'mg/l':
    
    >>> from harmonize_wq import harmonize
    >>> harmonize.units_dimension(unit_series, units='mg/l')
    ['g/kg']
    """
    if ureg is None:
        ureg = pint.UnitRegistry()
    dim_list = []  # List for units with mismatched dimensions
    dimension = ureg(units).dimensionality  # units dimension
    # Loop over list of unique units
    for unit in list(set(series_in)):
        q_ = ureg(unit)
        if not q_.check(dimension):
            dim_list.append(unit)
    return dim_list


def dissolved_oxygen(wqp):
    """Standardize 'Dissolved Oxygen (DO)' characteristic.
    
    Uses :class:`wq_data.WQCharData` to check units, check unit
    dimensionality and perform appropriate unit conversions.

    Parameters
    ----------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object to check units, check unit
        dimensionality and perform appropriate unit conversions.

    Returns
    -------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object with updated attributes.
    """
    wqp.check_units()  # Replace know problem units, fix and flag missing units

    # Check/fix dimensionality issues (Type III)
    for unit in wqp.dimensions_list():
        if wqp.ureg(wqp.units).check({'[length]': -3, '[mass]': 1}):
            # Convert to density, e.g., % or ppm -> mg/l (assumes STP for now)
            wqp.apply_conversion(convert.DO_saturation, unit)
        elif wqp.ureg(wqp.units).dimensionless:
            # Convert to dimensionless, e.g., mg/l -> % or ppm
            wqp.apply_conversion(convert.DO_concentration, unit)
            warn(f'Need % saturation equation for {unit}')

    return wqp


def salinity(wqp):
    """Standardize 'Salinity' characteristic.
    
    Uses :class:`wq_data.WQCharData` to check basis, check units, check unit
    dimensionality and perform appropriate unit conversions.
    
    Notes
    -----
    PSU=PSS=ppth and 'ppt' is picopint in :mod:`pint` so it is changed to
    'ppth'.

    Parameters
    ----------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object with updated attributes.
    """
    wqp.check_basis(basis_col='ResultTemperatureBasisText')  # Moves '@25C' out
    wqp.check_units()  # Replace know problem units, fix and flag missing units

    # Check/fix dimensionality issues (Type III)
    for unit in wqp.dimensions_list():
        if wqp.ureg(wqp.units).dimensionless:
            # Convert to dimensionless
            if wqp.ureg(unit).check({'[length]': -3, '[mass]': 1}):
                # Density, e.g., 'mg/l' -> 'PSU'/'PSS'/'ppth'
                wqp.apply_conversion(convert.density_to_PSU, unit)
            else:
                # Will cause dimensionality error, kick it there for handling
                continue
        elif wqp.ureg(wqp.units).check({'[length]': -3, '[mass]': 1}):
            # Convert to density, e.g., PSU -> 'mg/l'
            wqp.apply_conversion(convert.PSU_to_density, unit)

    return wqp


def turbidity(wqp):
    """Standardize 'Turbidity' characteristic.
    
    Uses :class:`wq_data.WQCharData` to check units, check unit
    dimensionality and perform appropriate unit conversions

    Notes
    -----
    See `USGS Report Chapter A6. Section 6.7. Turbidity
    <https://pubs.usgs.gov/twri/twri9a6/twri9a67/twri9a_Section6.7_v2.1.pdf>`_
    See ASTM D\315-17 for equivalent unit definitions:
    'NTU'  - 400-680nm (EPA 180.1), range 0.0-40.
    'NTRU' - 400-680nm (2130B), range 0-10,000.
    'NTMU' - 400-680nm.
    'FNU'  - 780-900nm (ISO 7027), range 0-1000.
    'FNRU' - 780-900nm (ISO 7027), range 0-10,000.
    'FAU'  - 780-900nm, range 20-1000.
    Older methods:
    'FTU' - lacks instrumentation specificity
    'SiO2' (ppm or mg/l) - concentration of calibration standard (=JTU)
    'JTU' - candle instead of formazin standard, near 40 NTU these may be
    equivalent, but highly variable.
    Conversions used: cm <-> NTU see :func:`convert.cm_to_NTU` from
    `USU <https://extension.usu.edu/utahwaterwatch/monitoring/field-instructions/>`_.

    Alternative conversions available but not currently used by default:
    :func:`convert.FNU_to_NTU` from Gohin (2011) Ocean Sci., 7, 705–732
    `<https://doi.org/10.5194/os-7-705-2011>`_.
    :func:`convert.SiO2_to_NTU` linear relation from Otilia et al. 2013.
    :func:`convert.JTU_to_NTU` linear relation from Otilia et al. 2013.
        
    Otilia, Rusănescu Carmen, Rusănescu Marin, and Stoica Dorel.
    MONITORING OF PHYSICAL INDICATORS IN WATER SAMPLES.
    `<https://hidraulica.fluidas.ro/2013/nr_2/84_89.pdf>`_.

    Parameters
    ----------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object with updated attributes.
    """
    #These units exist but have not been encountered yet
    #formazin nephelometric multibeam unit (FNMU);
    #formazin backscatter unit (FBU);
    #backscatter units (BU); attenuation units (AU)

    wqp.check_units()  # Replace know problem units, fix and flag missing units

    # Check/fix dimensionality issues (Type III)
    for unit in wqp.dimensions_list():
        if wqp.ureg(wqp.units).check({'[turbidity]': 1}):
            if wqp.ureg(unit).dimensionless:
                if unit=='JTU':
                    wqp.apply_conversion(convert.JTU_to_NTU, unit)
                elif unit=='SiO2':
                    wqp.apply_conversion(convert.SiO2_to_NTU, unit)
                else:
                    #raise ValueError('Bad Turbidity unit: {}'.format(unit))
                    warn(f'Bad Turbidity unit: {unit}')
            elif wqp.ureg(unit).check({'[length]': 1}):
                wqp.apply_conversion(convert.cm_to_NTU, unit)
            else:
                #raise ValueError('Bad Turbidity unit: {}'.format(unit))
                warn(f'Bad Turbidity unit: {unit}')
        elif wqp.ureg(wqp.units).check({'[length]': 1}):
            wqp.apply_conversion(convert.NTU_to_cm, unit)
        else:
            #raise ValueError('Bad Turbidity unit: {}'.format(wqp.units))
            warn(f'Bad Turbidity unit: {unit}')
    return wqp


def sediment(wqp):
    """Standardize 'Sediment' characteristic.
    
    Uses :class:`wq_data.WQCharData` to check basis, check units, and check
    unit dimensionality.

    Parameters
    ----------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : wq_data.WQCharData
        WQP Characteristic Info Object with updated attributes.
    """
    #'< 0.0625 mm', < 0.125 mm, < 0.25 mm, < 0.5 mm, < 1 mm, < 2 mm, < 4 mm
    wqp.check_basis(basis_col='ResultParticleSizeBasisText')

    wqp.check_units()  # Replace know problem units, fix and flag missing units

    # Check/fix dimensionality issues (Type I)
    # Convert mg/l <-> dimensionless Premiss: 1 liter water ~ 1 kg mass)
    wqp.replace_unit_by_dict(wqp.dimension_fixes()[0], wqp.measure_mask())

    # un-fixable dimensions: mass/area (kg/ha), mass (g),
    #                        mass/time (ton/day), mass/length/time (ton/day/ft)

    return wqp


def harmonize_all(df_in, errors='raise'):
    """Harmonizes all 'CharacteristicNames' column values with methods.
    
    All results are standardized to default units. Intermediate columns are
    not retained. See :func:`domains.out_col_lookup` for list of values with
    methods.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the expected columns (changes based on values in
        'CharacteristicNames' column).
    errors : str, optional
        Values of ‘ignore’, ‘raise’, or ‘skip’. The default is ‘raise’.
        If ‘raise’, invalid dimension conversions will raise an exception.
        If ‘skip’, invalid dimension conversions will not be converted.
        If ‘ignore’, invalid dimension conversions will return the NaN.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in.
    
    Examples
    --------
    Build example df_in table from harmonize_wq tests to use in place of Water
    Quality Portal query response, this table has 'Temperature, water' and 
    'Phosphorous' results:
    
    >>> import pandas
    >>> tests_url = 'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests'
    >>> df1 = pandas.read_csv(tests_url + '/data/wqp_results.txt')
    >>> df1.shape
    (359505, 35)
    
    When running the function there may be read outs or warnings, as things are 
    encountered such as unexpected nutrient sample fractions:
        
    >>> from harmonize_wq import harmonize
    >>> df_result_all = harmonize.harmonize_all(df1)
    1 Phosphorus sample fractions not in frac_dict
    1 Phosphorus sample fractions not in frac_dict found in expected domains, mapped to "Other_Phosphorus"
    
    >>> df_result_all
           OrganizationIdentifier  ...           Temperature
    0                21FLHILL_WQX  ...  29.93 degree_Celsius
    1                21FLHILL_WQX  ...  17.82 degree_Celsius
    2                  21FLGW_WQX  ...  22.42 degree_Celsius
    3                21FLMANA_WQX  ...   30.0 degree_Celsius
    4                21FLHILL_WQX  ...  30.37 degree_Celsius
    ...                       ...  ...                   ...
    359500           21FLHILL_WQX  ...  28.75 degree_Celsius
    359501           21FLHILL_WQX  ...  23.01 degree_Celsius
    359502            21FLTBW_WQX  ...  29.97 degree_Celsius
    359503           21FLPDEM_WQX  ...  32.01 degree_Celsius
    359504           21FLSMRC_WQX  ...                   NaN
    <BLANKLINE>
    [grows x 42 columns]
    
    List columns that were added:
    
    >>> sorted(list(df_result_all.columns[-7:]))
    ... # doctest: +NORMALIZE_WHITESPACE
    ['Other_Phosphorus', 'Phosphorus', 'QA_flag', 'Speciation',
     'TDP_Phosphorus', 'TP_Phosphorus', 'Temperature']
    
    See Also
    --------
    See any of the 'Simple' notebooks found in 
    'demos<https://github.com/USEPA/harmonize-wq/tree/main/demos>' for
    examples of how this function is used to standardize, clean, and wrangle a
    Water Quality Portal query response.
    
    """
    df_out = df_in.copy()
    char_vals = list(set(df_out['CharacteristicName']))
    char_vals.sort()

    for char_val in char_vals:
        df_out = harmonize(df_out, char_val, errors=errors)
    return df_out


def harmonize(df_in, char_val, units_out=None, errors='raise',
              intermediate_columns=False, report=False):
    """Harmonize char_val rows based methods specific to that char_val.

    All rows where the value in the 'CharacteristicName' column matches
    char_val will have their results harmonized based on available methods for
    that char_val.
    
    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the expected columns (change based on char_val).
    char_val : str
        Target value in 'CharacteristicName' column.
    units_out : str, optional
        Desired units to convert results into.
        The default None, uses the constant domains.OUT_UNITS.
    errors : str, optional
        Values of ‘ignore’, ‘raise’, or ‘skip’. The default is ‘raise’.
        If ‘raise’, then invalid dimension conversions will raise an exception.
        If ‘skip’, then invalid dimension conversions will not be converted.
        If ‘ignore’, then invalid dimension conversions will return the NaN.
    intermediate_columns : Boolean, optional
        Return intermediate columns. Default 'False' does not return these.
    report : bool, optional
        Print a change summary report. The default is False.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in.

    Examples
    --------
    Build example df_in table from harmonize_wq tests to use in place of Water
    Quality Portal query response, this table has 'Temperature, water' and 
    'Phosphorous' results:
        
    >>> import pandas
    >>> tests_url = 'https://raw.githubusercontent.com/USEPA/harmonize-wq/main/harmonize_wq/tests'
    >>> df1 = pandas.read_csv(tests_url + '/data/wqp_results.txt')
    >>> df1.shape
    (359505, 35)
    
    >>> from harmonize_wq import harmonize
    >>> df_result = harmonize.harmonize(df1, 'Temperature, water')
    >>> df_result
           OrganizationIdentifier  ...           Temperature
    0                21FLHILL_WQX  ...  29.93 degree_Celsius
    1                21FLHILL_WQX  ...  17.82 degree_Celsius
    2                  21FLGW_WQX  ...  22.42 degree_Celsius
    3                21FLMANA_WQX  ...   30.0 degree_Celsius
    4                21FLHILL_WQX  ...  30.37 degree_Celsius
    ...                       ...  ...                   ...
    359500           21FLHILL_WQX  ...  28.75 degree_Celsius
    359501           21FLHILL_WQX  ...  23.01 degree_Celsius
    359502            21FLTBW_WQX  ...  29.97 degree_Celsius
    359503           21FLPDEM_WQX  ...  32.01 degree_Celsius
    359504           21FLSMRC_WQX  ...                   NaN
    <BLANKLINE>
    [359505 rows x 37 columns]
    
    List columns that were added:
    
    >>> df_result.columns[-2:]
    Index(['QA_flag', 'Temperature'], dtype='object')
    
    See Also
    --------
    See any of the 'Detailed' notebooks found in 
    'demos<https://github.com/USEPA/harmonize-wq/tree/main/demos>' for examples
    of how this function is used to standardize, clean, and wrangle a Water
    Quality Portal query response, one 'CharacteristicName' value at a time.
    """
    # Check/retrieve standard attributes and df columns as object
    wqp = WQCharData(df_in, char_val)
    out_col = wqp.out_col  # domains.out_col_lookup()[char_val]

    if units_out:
        wqp.update_units(units_out)
    else:
        units_out = domains.OUT_UNITS[out_col]

    # Update local units registry to define characteristic specific units
    wqp.update_ureg()  # This is done based on out_col/char_val

    # Use out_col to dictate function
    if out_col in ['pH', 'Secchi']:
        wqp.check_units()  # Fix and flag missing units
        # NOTE: pH undefined units -> NAN -> units,
    elif out_col in ['Conductivity', 'Chlorophyll']:
        # Replace know problem units, fix and flag missing units
        wqp.check_units()
    elif out_col in ['Fecal_Coliform', 'E_coli']:
        # NOTE: Ecoli ['cfu/100ml', 'MPN/100ml', '#/100ml']
        # NOTE: feca ['CFU', 'MPN/100ml', 'cfu/100ml', 'MPN/100 ml', '#/100ml']
        # Replace known special character in unit ('#' count assumed as CFU)
        wqp.replace_unit_str('#', 'CFU')
        # Replace known unit problems (e.g., assume CFU/MPN is /100ml)
        wqp.replace_unit_by_dict(domains.UNITS_REPLACE[out_col])
        #TODO: figure out why the above must be done before replace_unit_str
        # Replace all instances in results column
        wqp.replace_unit_str('/100ml', '/(100ml)')
        wqp.replace_unit_str('/100 ml', '/(100ml)')
        wqp.check_units()  # Fix and flag missing units
    elif out_col in ['Carbon', 'Phosphorus', 'Nitrogen']:
        # Set Basis from unit and MethodSpec column
        wqp.check_basis()
        # Replace know problem units, fix and flag missing units (wet/dry?)
        wqp.check_units()
        # Convert dimensionality issues, e.g., mg/l <-> dimensionless (H2O)
        dimension_dict, mol_list = wqp.dimension_fixes()
        # Replace units by dictionary
        wqp.replace_unit_by_dict(dimension_dict, wqp.measure_mask())
        wqp.moles_convert(mol_list)  # Fix up units/measures where moles
    elif out_col == 'Temperature':
        # Remove spaces from units for pint ('deg C' == degree coulomb)
        wqp.update_units(wqp.units.replace(' ', ''))  # No spaces in units_out
        wqp.replace_unit_str(' ', '')  # Replace in results column
        wqp.check_units()  # Fix and flag missing units
    else:
        harmonize_map = {'DO': dissolved_oxygen,
                         'Salinity': salinity,
                         'Turbidity':  turbidity,
                         'Sediment': sediment,
                         }
        try:
            wqp = harmonize_map[out_col](wqp)
        except KeyError:
            # out_col not recognized
            warn(f"WARNING: '{out_col}' not available yet.")
            raise

    # Update values in out_col with standard units
    wqp.convert_units(errors=errors)

    # Speciation: Parse Sample Fraction, moving measure to new column
    # Note: just phosphorus right now
    # Total is TP (digested) from the whole water sample (vs total dissolved)
    # Dissolved is TDP (total) filtered water digested (vs undigested DIP)
    if out_col in ['Phosphorus', 'Nitrogen']:
        # NOTE: only top level fractions, while TADA has lower for:
        #'Chlorophyll a', 'Turbidity', 'Fecal Coliform', 'Escherichia coli'
        if out_col=='Phosphorus':
            frac_dict = {'TP_Phosphorus': ['Total'],
                         'TDP_Phosphorus': ['Dissolved'],
                         'Other_Phosphorus': ['', nan],}
        else:
            frac_dict = 'TADA'
        frac_dict = wqp.fraction(frac_dict)  # Run sample fraction on WQP
        

    df_out = wqp.df

    # TODO: add activities/detection limits and filter on quality? e.g., cols:
    # 'ResultStatusIdentifier' = ['Historical', 'Accepted', 'Final']
    # 'ResultValueTypeName' = ['Actual', 'Estimated', 'Calculated']
    # 'ResultDetectionConditionText' = ['*Non-detect', '*Present <QL', '*Not Reported', 'Not Detected']
    # df_out = wrangle.add_activities_to_df(df_out, wqp.c_mask)
    # df_out = wrangle.add_detection(df_out, char_val)

    # Functionality only available w/ generic
    if report:
        viz.print_report(df_out.loc[wqp.c_mask], out_col, wqp.col.unit_in)
    if not intermediate_columns:
        df_out = df_out.drop(['Units'], axis=1)  # Drop intermediate columns
    return df_out
