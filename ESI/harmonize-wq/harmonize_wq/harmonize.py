# -*- coding: utf-8 -*-
"""
Created on Tue Sep  7 14:08:08 2021

Functions for harmonizing and tidying data retrieved from WQP
Notes: non-numeric examples: '', '*Not Reported', 'Not Reported', '*Non-detect'

@author: jbousqui
"""
from math import sqrt
from types import SimpleNamespace
from warnings import warn
import pandas
import geopandas
import pint
from pyproj import Transformer
from shapely.geometry import shape
from numpy import nan
from package import domains
from package import basis
from package import convert
#from package import wrangle


class WQCharData():
    """
    A class to represent Water Quality Portal results for a specifc
    characteristic

    Attributes
    ----------
    df : pandas.DataFrame
        DataFrame with results for the specific characteristic
    c_mask : pandas.Series
        Row conditional (bool) mask to limit df rows to only those for the
        specific characteristic
    col : SimpleNamespace
        Standrad df column names for unit_in, unit_out, and measure
    out_col : str
        Column name in df for results, set using char_val
    ureg = pint.UnitRegistry()
        Pint unit registry, starts set to standard unit registry
    units: str
        Units all results in out_col will be converted into. Default units are
        returned from domains.OUT_UNITS[out_col].

    Methods
    -------
    coerce_measure()
        Identifies bad measure values, and flags them. Copies measure
        values to out_col, with bad measures as NaN.
    check_units()
    convert_units()
    replace_unit_by_str()
    replace_unit_by_dict()
    update_ureg()
    update_units()
    char_val()
    """
    def __init__(self, df_in, char_val):
        """
        Create class based off rows of dataframe for characteristic.

        Parameters
        ----------
        df_in : pandas.DataFrame
            DataFrame that will be updated.
        char_val : string
            Expected characteristicName.
        """
        df_out = df_in.copy()
        #self.check_df(df)
        df_checks(df_out)
        c_mask = df_out['CharacteristicName'] == char_val
        self.c_mask = c_mask
        # Deal with units: set out = in
        cols = {'unit_in': 'ResultMeasure/MeasureUnitCode',
                'unit_out': 'Units',
                'measure': 'ResultMeasureValue',
                'basis': 'Speciation',}
        self.col = SimpleNamespace(**cols)
        df_out.loc[c_mask, self.col.unit_out] = df_out.loc[c_mask,
                                                           self.col.unit_in]
        self.df = df_out
        # Deal with values: set out_col = in
        self.out_col = domains.out_col_lookup()[char_val]
        self.coerce_measure()
        self.ureg = pint.UnitRegistry()  # Add standard unit registry
        self.units = domains.OUT_UNITS[self.out_col]

    def coerce_measure(self):
        """ Identifies bad measure values, and flags them. Copies measure
            values to out_col, with bad measures as NaN.
        """
        df_out = self.df
        c_mask = self.c_mask
        meas_col = self.col.measure

        # Coerce bad measues in series to NaN
        meas_s = pandas.to_numeric(df_out.loc[c_mask, meas_col],
                                   errors='coerce')
        # Create a list of the bad measures in the series
        bad_measures = [df_out.loc[i, meas_col] for i in meas_s[meas_s.isna()].index]
        for bad_meas in pandas.unique(bad_measures):
            # Flag each unique bad measure one measure (not row) at a time
            if pandas.isna(bad_meas):
                flag = '{}: missing (NaN) result'.format(meas_col)
                cond = (c_mask & (df_out[meas_col].isna()))
            else:
                flag = '{}: "{}" result cannot be used'.format(meas_col,
                                                               bad_meas)
                cond = (c_mask & (df_out[meas_col] == bad_meas))
            # Flag bad measures
            df_out = add_qa_flag(df_out, cond, flag)
        df_out[self.out_col] = meas_s  # Return coerced results

        self.df = df_out

    def check_units(self, flag_col=None):
        """
        Checks for bad units that are missing (assumes default_unit) or
        unrecoginzed as valid by unit registry (ureg). Does not check for units
        in the correct dimensions, or a mistaken identity (e.g. 'deg F'
        recognized as 'degree * farad').

        Parameters
        ----------
        flag_col : string, optional
            Column to reference in QA_flags.
            The default None uses unit_col instead.
        """
        # Replace unit by dict using domain
        self.replace_unit_by_dict(domains.UNITS_REPLACE[self.out_col])

        # Deal with optional args
        if flag_col is None:
            flag_col = self.col.unit_in
        unit_col = self.col.unit_out
        self.infer_units(unit_col, flag_col)

        df_out = self.df

        # Check each unique unit is valid in ureg
        for unit in list(set(df_out.loc[self.c_mask, unit_col])):
            try:
                self.ureg(unit)
            except pint.UndefinedUnitError:
                #WARNING: Does not catch '%' or bad units in ureg (eg deg F)
                # If bad, flag and replace
                problem = "'{}' UNDEFINED UNIT".format(unit)
                warn("WARNING: " + problem)
                flag = unit_qa_flag(unit_col, problem, self.units, flag_col)
                # New mask for bad units
                u_mask = self.unit_mask(unit)
                # Assign flag to bad units
                df_out = add_qa_flag(df_out, u_mask, flag)
                df_out.loc[u_mask, unit_col] = self.units  # Replace w/ default
        self.df = df_out

    def infer_units(self, unit_col, flag_col=None):
        """
        Replace missing units with desired unit and add QA_flag about it in df.

        Parameters
        ----------
        unit_col : string
            Unit column in df_in.
        flag_col : string, optional
            Column to reference in QA_flags.
            The default None uses unit_col instead.
        """
        # QA flag for missing units
        flag = unit_qa_flag(unit_col, 'MISSING', self.units, flag_col)
        # Update mask for missing units
        unit_mask = self.c_mask & self.df[unit_col].isna()
        self.df = add_qa_flag(self.df, unit_mask, flag)  # Assign flag
        # Update with infered unit
        self.df.loc[unit_mask, unit_col] = self.units
        #Note: .fillna(self.units) is slightly faster but hits datatype issues

    def check_basis(self, basis_col='MethodSpecificationName'):
        """
        Determine speciation (basis) for measure.

        Parameters
        ----------
        basis_col : str, optional
            Basis column name. Default is 'MethodSpecificationName' which is
            replaced by 'Speciation', others are updated in place.
        """
        c_mask = self.c_mask

        # Check for Method Specification column
        df_checks(self.df, [basis_col])

        # Basis from MethodSpecificationName
        if basis_col == 'MethodSpecificationName':
            self.df[c_mask] = basis.basis_from_methodSpec(self.df[c_mask])

            # Basis from unit
            try:
                basis_dict = basis.unit_basis_dict(self.out_col)
                self.df[c_mask] = basis.basis_from_unit(self.df[c_mask],
                                                        basis_dict,
                                                        self.col.unit_out)
            except KeyError:
                pass
            # Finish by filling any NAs with char_val based default
            col = self.col.basis
            if col not in self.df.columns:
                self.df[col] = nan  # If col wasn't created above it is here
            char_val = self.char_val()
            self.df.loc[c_mask, col] = self.df.loc[c_mask, col].fillna(char_val)

            # Drop instances of 'as '
            self.df.loc[c_mask, col] = [bas[3:]
                                        if bas.startswith('as ') else bas
                                        for bas in self.df.loc[c_mask, col]]

        else:
            self.df[c_mask] = basis.update_result_basis(self.df[c_mask],
                                                        basis_col,
                                                        self.col.unit_out)

    def update_ureg(self):
        """Update class unit registry to define units based on out_col"""
        for definition in domains.registry_adds_list(self.out_col):
            self.ureg.define(definition)

    def update_units(self, units_out):
        """
        Update object units attribute to convert everything into.
        Parameters
        ----------
        units_out : str
            Units to convert results into.
        """
        self.units = units_out

    def measure_mask(self, col=None):
        """
        Get mask that is characteristic specific (c_mask) and only has valid
        col measures (Non-NA).
        Parameters
        ----------
        col : str, optional
            DataFrame column name to use. Default None uses self.out_col
        """
        if col:
            return self.c_mask & self.df[col].notna()
        return self.c_mask & self.df[self.out_col].notna()

    def unit_mask(self, unit, col=None):
        """
        Get mask that is characteristic specific (c_mask) and has the
        specified units.
        """
        if col:
            return self.measure_mask() & (self.df[col]==unit)
        return self.measure_mask() & (self.df[self.col.unit_out]==unit)

    def char_val(self):
        """"Returns built-in char_val based on out_col attribute"""
        c_dict = domains.out_col_lookup()
        return list(c_dict.keys())[list(c_dict.values()).index(self.out_col)]

    def convert_units(self, default_unit=None, errors='raise'):
        """
        Update object dataframe's out-col to convert from old units to
        default_unit.

        Parameters
        ----------
        default_unit : str, optional
            Units to convert values to. Default None uses units attribute.
        errors : string, optional
            Values of ‘ignore’, ‘raise’, or ‘skip’. The default is ‘raise’.
            If ‘raise’, invalid dimension conversions will raise an exception.
            If ‘skip’, invalid dimension conversions will not be converted.
            If ‘ignore’, invalid dimension conversions will be NaN.
        """
        if default_unit:
            self.units = default_unit
        df_out = self.df
        m_mask = self.measure_mask()

        params = {'quantity_series': df_out.loc[m_mask, self.out_col],
                  'unit_series': df_out.loc[m_mask, self.col.unit_out],
                  'units': self.units,
                  'ureg': self.ureg,
                  'errors': errors}
        df_out.loc[m_mask, self.out_col] = convert_unit_series(**params)
        self.df = df_out

    def apply_conversion(self, convert_fun, unit, u_mask=None):
        """
        Apply special dimension changing conversions using functions in convert
        module and applying them across all cases of current unit.

        Parameters
        ----------
        convert_fun : function
            Conversion function to apply.
        unit : string
            Current unit.
        u_mask : pandas.Series, optional
            Mask to use to identify what is being converted.
            The default is None, creating a unit mask based on unit.
        """
        #TODO: QA flag inexact conversions?
        df_out = self.df
        if u_mask is None:
            u_mask = self.unit_mask(unit)
        unit = self.ureg.Quantity(unit)  # Pint quantity object from unit
        old_vals = df_out.loc[u_mask, self.out_col]
        try:
            new_quants = [convert_fun(x*unit) for x in old_vals]
        except ValueError:
            #print(old_vals.iloc[0]*unit)
            # string to avoid altered ureg issues
            new_quants = [convert_fun(str(x*unit)) for x in old_vals]
        #1run=6505.62ms (may be slower) vs apply (5888.43ms)
        #new_vals = old_vals.apply(lambda x: convert_fun(x*unit).magnitude)
        new_vals = [quant.magnitude for quant in new_quants]
        df_out.loc[u_mask, self.out_col] = new_vals
        df_out.loc[u_mask, self.col.unit_out] = str(new_quants[0].units)
        #self.units <- was used previously, sus when units is not default

        self.df = df_out

    def dimensions_list(self, m_mask=None):
        """
        Use character object to retrieve list of unique dimensions.

        Parameters
        ----------
        m_mask : pandas.Series, optional
            Conditional mask to limit rows.
            The default None, uses measure_mask().

        Returns
        -------
        list
            List of units with mis-matched dimensions.

        """
        if m_mask is None:
            m_mask = self.measure_mask()
        return units_dimension(self.df.loc[m_mask, self.col.unit_out],
                               self.units,
                               self.ureg)

    def replace_unit_by_str(self, old, new):
        """
        Simple way to replace all instances of old str with new str in units.

        Parameters
        ----------
        old : str
            sub-string to find and replace
        new : str
            sub-string to replace old sub-string
        """
        df_out = self.df
        c_mask = self.c_mask
        unit_col = self.col.unit_out
        df_out.loc[c_mask, unit_col] = df_out.loc[c_mask, unit_col].str.replace(old, new)
        self.df = df_out

    def replace_unit_by_dict(self, val_dict, mask=None):
        """
        A simple way to do multiple replace_in_col() replacements of val_dict key
        with val_dict value.

        Parameters
        ----------
        val_dict : dictionary
            Occurrences of key in the unit column are replaced with the value.
        mask : pandas.Series, optional
            Conditional mask to limit rows.
            The default None, uses the c_mask attribute.
        """
        col = self.col.unit_out
        if mask is None:
            mask = self.c_mask
        for item in val_dict.items():
            replace_in_col(self.df, col, item[0], item[1], mask)

    def fraction(self, frac_dict=None, suffix=None,
                   fract_col='ResultSampleFractionText'):
        """
        Create columns for sample fractions, use frac_dict to set their names.

        Parameters
        ----------
        frac_dict : dictionary, optional
            Dictionary where {fraction_name : new_col}.
            The default None starts with an empty dictionary.
        suffix : string, optional
            String to add to the end of any new column name.
            The default None, uses out_col attribute.
        fract_col : string, optional
            Column name where sample fraction is defined.
            The default is 'ResultSampleFractionText'.

        Returns
        -------
        frac_dict : dictionary
            frac_dict updated to include any frac_col not already defined.
        """
        c_mask = self.c_mask
        if frac_dict is None:
            frac_dict = {}
        if suffix is None:
            suffix = self.out_col

        # Check for sample fraction column
        df_checks(self.df, ['ResultSampleFractionText'])
        # Replace bad sample fraction w/ nan
        self.df = replace_in_col(self.df, fract_col, ' ', nan, c_mask)

        df_out = self.df
        # Make column for any unexpected Sample Fraction values, loudly
        for s_f in set(df_out[fract_col].dropna()):
            if s_f not in frac_dict.values():
                char = '{}_{}'.format(s_f.replace(' ', '_'), suffix)
                frac_dict[char] = s_f
                prob = '"{}" column for {}, may be error'.format(char, s_f)
                warn('Warning: ' + prob)
        # Test we didn't skip any SampleFraction
        for s_f in set(df_out[fract_col].dropna()):
            assert s_f in frac_dict.values(), '{} check in {}'.format(s_f,
                                                                      fract_col)

        # Create out columns for each sample fraction
        for frac in frac_dict.items():
            col = frac[0]  # New column name
            if frac[1] in set(df_out.loc[c_mask, fract_col].dropna()):
                # New subset mask for sample frac
                f_mask = (c_mask & (df_out[fract_col]==frac[1]))
                df_out[col] = nan  # Add column
                # Copy measure to new col (new col name from char_list)
                df_out.loc[f_mask, col] = df_out.loc[f_mask, suffix]
            elif frac[1] == '':
                # Values where sample fraction missing
                if df_out.loc[c_mask, fract_col].isnull().values.any():
                    # New subset mask
                    f_mask = (c_mask & (df_out[fract_col].isnull()))
                    df_out[col] = nan  # Add column
                    # Copy measure to new col
                    df_out.loc[f_mask, col] = df_out.loc[f_mask, suffix]
        self.df = df_out

        return frac_dict

    def handle_dimensions(self):
        """
        Input/output for dimension handling.

        Note: this is done one dimension at a time, except for mole
        conversions which are further divided by basis (one at a time)

        Returns
        -------
        dimension_dict : dictionary
            Dictionary with old_unit:new_unit.
        mol_list : list
            List of Mole (substance) units.

        """
        dimension_dict = {}  # Empty dict to update to
        mol_list = []  # Empty list to append to

        # If converting to/from moles has extra steps
        if self.ureg(self.units).check({'[substance]': 1}):
            # Convert everything to MOLES!!!
            # Must consider the different speciation for each
            #TODO: This could be problematic given umol/l
            warn('This feature is not available yet')
            return {}, []
        for unit in self.dimensions_list():
            if self.ureg(unit).check({'[substance]': 1}):
                mol_params = {'ureg': self.ureg,
                              'Q_': self.ureg.Quantity(1, unit),}
                # Moles need to be further split by basis
                basis_lst = list(set(self.df.loc[self.c_mask, self.col.basis]))
                for speciation in basis_lst:
                    mol_params['basis'] = speciation
                    quant = str(convert.moles_to_mass(**mol_params))
                    dim_tup = dimension_handling(unit,
                                                 self.units,
                                                 quant,
                                                 self.ureg)
                    dimension_dict.update(dim_tup[0])
                    mol_list+= dim_tup[1]
            else:
                dim_tup = dimension_handling(unit,
                                             self.units,
                                             ureg = self.ureg)
                dimension_dict.update(dim_tup[0])
        return dimension_dict, mol_list

    def moles_convert(self, mol_list):
        """
        Update out_col with moles converted and reduce unit_col to units

        Parameters
        ----------
        mol_list : list
            List of Mole (substance) units.
        """
        # Variables from WQP
        df_out = self.df
        unit_col = self.col.unit_out
        ureg = self.ureg
        out_col = self.out_col

        for quant in mol_list:
            mol_mask = self.unit_mask(quant)
            df_out.loc[mol_mask, out_col] = ureg.Quantity(quant) * df_out[out_col]
            df_out.loc[mol_mask, unit_col] = str(ureg.Quantity(quant).units)

        self.df = df_out
        self.ureg = ureg


def df_checks(df_in, columns=None):
    """
    Checks pandas.DataFrame for columns

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame that will be checked.
    columns : list, optional
        List of strings for column names. Default None, uses:
        'ResultMeasure/MeasureUnitCode','ResultMeasureValue','CharacteristicName'
    """
    if columns is None:
        # Assign defaults
        columns = ('ResultMeasure/MeasureUnitCode',
                   'ResultMeasureValue',
                   'CharacteristicName')
    for col in columns:
        assert col in df_in.columns, '{} not in DataFrame'.format(col)


def replace_in_col(df_in, col, old_val, new_val, mask):
    """
    Simple string replacement for a column at rows filtered by mask

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    col : string
        Column of DataFrame to update old_val to _new_val.
    old_val : string
        Old value to replace.
    new_val : string
        New value to use.
    mask : pandas.Series
        Row conditional mask to only update a sub-set of rows.

    Returns
    -------
    df_in : pandas.DataFrame
        Updated DataFrame.

    """
    # Note: Timing is just as fast as long as df isn't copied
    #       Timing for replace vs set unkown
    mask_old = (mask & (df_in[col]==old_val))
    #str.replace did not work for short str to long str (over-replaces)
    #df.loc[mask, col] = df.loc[mask, col].str.replace(old_val, new_val)
    df_in.loc[mask_old, col] = new_val  # This should be more explicit

    return df_in


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
    """
    Convert list of quantities (quantity_list), each with a specified old unit,
    to a quantity in units using pint constructor method.

    Parameters
    ----------
    quantity_series : pandas.Series
        List of quantities. Values should be numeric, must not include NaN.
    unit_series : pandas.Series
        List of units for each quantity in quantity_series. Values should be
        string, must not include NaN.
    units : string
        Desired units.
    ureg : pint.UnitRegistry, optional
        Unit Registry Object with any custom units defined. The default is None
    errors : string, optional
        Values of ‘ignore’, ‘raise’, or ‘skip’. The default is ‘raise’.
        If ‘raise’, invalid dimension conversions will raise an exception.
        If ‘skip’, invalid dimension conversions will not be converted.
        If ‘ignore’, invalid dimension conversions will return the NaN.

    Returns
    -------
    pandas.Series
        Converted values from quantity_series in units with original index.

    """
    if quantity_series.dtype=='O':
        quantity_series = pandas.to_numeric(quantity_series)
    # Initialize classes from pint
    if ureg is None:
        ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    out_series = pandas.Series(dtype='object')
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
                    warn("WARNING: '{}' not converted".format(unit))
                elif errors=='ignore':
                    result_list = [nan for val in result_list]
                else:
                    # errors=='raise', or anything else just in case
                    raise exception
        # Re-index
        result_series = pandas.Series(result_list, index=f_quant_series.index)
        out_series = out_series.append(result_series)  # Append to full series
    return out_series


def add_qa_flag(df_in, mask, flag):
    """
    Adds flag to "QA_field" column in df_in

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    mask : pandas.Series
        Row conditional mask to limit rows.
    flag : string
        Text to populate the new flag with.

    Returns
    -------
    df_out : pandas.DataFrame
        Updated copy of df_in.

    """
    df_out = df_in.copy()
    if 'QA_flag' not in list(df_out.columns):
        df_out['QA_flag'] = nan

    # Append flag where QA_flag is not nan
    cond_notna = mask & (df_out['QA_flag'].notna())  # Mask cond and not NA
    existing_flags = df_out.loc[cond_notna, 'QA_flag']  # Current QA flags
    df_out.loc[cond_notna, 'QA_flag'] = ['{}; {}'.format(txt, flag) for
                                     txt in existing_flags]
    # Equals flag where QA_flag is nan
    df_out.loc[mask & (df_out['QA_flag'].isna()), 'QA_flag'] = flag

    return df_out


def unit_qa_flag(unit_col, trouble, unit, flag_col=None):
    """
    Generates a QA_flag flag string for the units column. If unit_col is a copy
    flag_col can specify the original column name for the flag.

    Parameters
    ----------
    unit_col : string
        Column currently being checked. Used in string when flag_col is None
    trouble : string
        Unit problem encountered (e.g., missing).
    unit : string
        The default unit that replaced the problem unit.
    flag_col : string, optional
        String to use when refering to the unit_col. If None, unit_col is used.
        The default is None.

    Returns
    -------
    string
        Flag to use in QA_flag column.

    """
    if flag_col:
        return '{}: {} UNITS, {} assumed'.format(flag_col, trouble, unit)
    return '{}: {} UNITS, {} assumed'.format(unit_col, trouble, unit)


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
        c_mask = df_out[crs_col]==bad_crs_val  # Mask for bad CRS value
    else:
        # QA flag for missing CRS
        flag = '{}: MISSING datum, EPSG:{} assumed'.format(crs_col, out_EPSG)
        c_mask = df_out[crs_col].isna()  # Mask for missing units
    df_out = add_qa_flag(df_out, c_mask, flag)  # Assign flag
    df_out.loc[c_mask, out_col] = out_EPSG  # Update with infered unit

    return df_out


def units_dimension(series_in, units, ureg=None):
    """
    List of unique units not in desired units dimension

    Parameters
    ----------
    series_in : pandas.Series
        Series of units.
    units : string
        Desired units.
    ureg : pint.UnitRegistry, optional
        Unit Registry Object with any custom units defined. The default is None

    Returns
    -------
    dim_list : list
        List of units with mis-matched dimensions.

    """
    if ureg is None:
        ureg = pint.UnitRegistry()
    dim_list = []  # List for units with mis-matched dimensions
    dimension = ureg(units).dimensionality  # units dimension
    # Loop over list of unique units
    for unit in list(set(series_in)):
        q_ = ureg(unit)
        if not q_.check(dimension):
            dim_list.append(unit)
    return dim_list


def dimension_handling(unit, units, quant=None, ureg=None):
    """

    Parameters
    ----------
    unit : str
        Current unit.
    units : str
        Desired units.
    quant : pint.quantity, optional
        Required for conversions to/from moles
    ureg : pint.UnitRegistry, optional
        Unit Registry Object with any custom units defined. The default is None

    Returns
    -------
    dict
        Dictionary with old_unit:new_unit.
    list
        List of Mole (substance) units.

    """
    if ureg is None:
        ureg = pint.UnitRegistry()

    # Conversion to moles performed a level up from here (class method)
    if ureg(units).check({'[length]': -3, '[mass]': 1}):
        # Convert to density, e.g., '%' -> 'mg/l'
        if ureg(unit).check({'[substance]': 1}):
            if quant:
                # Moles -> mg/l; dim = ' / l'
                return {unit: quant + ' / l'}, [quant + ' / l']
            raise ValueError("Pint Quantity required for moles conversions")
        # Else assume it is dimensionless (e.g. unit = 'g/kg')
        return {unit: unit + ' * H2O'}, []
    if ureg(units).dimensionless:
        # Convert to dimensionless, e.g., 'mg/l' -> '%'
        if ureg(unit).check({'[substance]': 1}):
            if quant:
                # Moles -> g/kg; dim = ' / l / H2O'
                return {unit: quant + ' / l / H2O'}, [quant + ' / l / H2O']
            raise ValueError("Pint Quantity required for moles conversions")
        # Else assume it is density (e.g. unit = 'mg/l')
        return {unit: unit + ' / H2O'}, []
    warn('WARNING: Unexpected dimensionality')
    return {}, []


def get_bounding_box(shp, idx=0):
    """
    Return bounding box for shp.

    Parameters
    ----------
    shp : spatial file
        Any geometry that is readable by geopandas.
    idx : integer, optional
        Index for geometry to get bounding box for.
        The default is 0 to return the first bounding box.

    Returns
    -------
        Coordinates for bounding box as string and seperated by ', '.
    """
    shp = as_gdf(shp)

    xmin = shp.bounds['minx'][idx]
    xmax = shp.bounds['maxx'][idx]
    ymin = shp.bounds['miny'][idx]
    ymax = shp.bounds['maxy'][idx]

    return ','.join(map(str, [xmin, ymin, xmax, ymax]))


def as_gdf(shp):
    """
    Returns a geodataframe for shp if shp is not already a geodataframe.

    Parameters
    ----------
    shp : string
        Filename for something that needs to be a geodataframe.

    Returns
    -------
    shp : geopandas.GeoDataFrame
        GeoDataFrame for shp if it isn't already a geodataframe.
    """
    if not isinstance(shp, geopandas.geodataframe.GeoDataFrame):
        shp = geopandas.read_file(shp, driver='ESRI Shapefile')
    return shp


def clip_stations(aoi_gdf, stations_gdf):
    """
    Clip it to area of interest. aoi_gdf is first transformed to stations_gdf
    projection.

    Parameters
    ----------
    aoi_gdf : pandas.DataFrame
        Polygon representing the area of interest.
    stations_gdf : pandas.DataFrame
        Points representing the stations.

    Returns
    -------
    pandas.DataFrame
        stations_gdf points clipped to the aoi_gdf.
    """
    stations_gdf = as_gdf(stations_gdf)  # Ensure it is geodataframe
    aoi_gdf = as_gdf(aoi_gdf)  # Ensure it is geodataframe
    # Transform aoi to stations CRS (should be 4326)
    aoi_prj = aoi_gdf.to_crs(stations_gdf.crs)
    return geopandas.clip(stations_gdf, aoi_prj)  # Return clipped geodataframe


# Harmonization functions
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
        GeoDataFrame representation of df_in with coordinates in out_EPSG datum.

    """
    df2 = df_in.copy()

    # Default columns
    crs_col = kwargs.get('crs_col',
                         "HorizontalCoordinateReferenceSystemDatumName")
    lat_col = kwargs.get('lat_col', 'LatitudeMeasure')
    lon_col = kwargs.get('lon_col', 'LongitudeMeasure')

    df_checks(df2, [crs_col, lat_col, lon_col]) # Check columns are in df

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
    d_mask = df_in['EPSG']==datum  # Mask for datum in subset
    points = df_in.loc[d_mask, 'geom_orig']  # Points series
    # List of transformed point geometries
    new_geoms = [transformer.transform(pnt[0], pnt[1]) for pnt in points]
    # Assign list to df.geom using Index from mask to re-index list
    df_in.loc[d_mask, 'geom'] = pandas.Series(new_geoms,
                                              index=df_in.loc[d_mask].index)
    return df_in


def dissolved_oxygen(wqp):
    """
    Standardizes 'Dissolved oxygen (DO)' characteristic using and returning
    the WQP Characteristic Info Object.

    Parameters
    ----------
    wqp : WQCharData Object
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : WQP Characteristic Info Object.
        WQP Characteristic Info Object with updated attributes
    """
    # Replace know problem units, fix and flag missing units
    wqp.check_units()

    # Check/fix dimensionality issues
    for unit in wqp.dimensions_list():
        if wqp.ureg(wqp.units).check({'[length]': -3, '[mass]': 1}):
            # Convert to density, e.g., % or ppm -> mg/l (assumes STP for now)
            wqp.apply_conversion(convert.DO_saturation, unit)
        elif wqp.ureg(wqp.units).dimensionless:
            # Convert to dimensionless, e.g., mg/l -> % or ppm
            wqp.apply_conversion(convert.DO_concentration, unit)
            warn('Need % saturation equation for {}'.format(unit))

    return wqp


def salinity(wqp):
    """
    Standardizes 'Salinity' characteristic using and returning
    the WQP Characteristic Info Object.
    Note: 'ppt' is picopint in pint so it is changed to 'ppth'

    Parameters
    ----------
    wqp : WQCharData Object
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : WQP Characteristic Info Object.
        WQP Characteristic Info Object with updated attributes
    """
    #Units = '0/00', 'PSS', 'mg/mL @25C', nan, 'ppt', 'ppth'
    wqp.check_basis(basis_col='ResultTemperatureBasisText')  # Moves '@25C' out
    # Replace know problem units, fix and flag missing units
    wqp.check_units()

    # Check/fix dimensionality issues
    for unit in wqp.dimensions_list():
        if wqp.ureg(wqp.units).dimensionless:
            # Convert to dimensionless, e.g., 'mg/l' -> 'PSU'/'PSS'/'ppth'
            wqp.apply_conversion(convert.density_to_PSU, unit)
        elif wqp.ureg(wqp.units).check({'[length]': -3, '[mass]': 1}):
            # Convert to density, e.g., PSU -> 'mg/l'
            wqp.apply_conversion(convert.PSU_to_density, unit)

    return wqp


def turbidity(wqp):
    """
    Standardizes 'Turbidity' characteristic using and returning
    the WQP Characteristic Info Object.

    Special units: 'NTU' - 400-680nm (EPA 180.1)
                   'NTRU' -
                   'FNU' - 780-900nm (ISO 7027)
                   'JTU' - candle instead of formazin standard
    Conversions: 1.267 NTU = FNU Gohin (2011) Ocean Sci., 7, 705–732
                                 https://doi.org/10.5194/os-7-705-2011
                 cm <-> NTU see convert.cm_to_NTU()
                 1-3 mg/l = NTU
                 JTU = NTU @40 but has different bounds
                 NTRU = NTU

    Parameters
    ----------
    wqp : WQCharData Object
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : WQP Characteristic Info Object.
        WQP Characteristic Info Object with updated attributes
    """
    #units = ['cm', 'mg/l SiO2', 'JTU', 'NTU', 'NTRU']
    #counts = [3, 36, 3481, 127358, 135]

    #TODO: These units exist but have not been encountered yet
    #nephelometric turbidity multibeam unit (NTMU);
    #formazin nephelometric multibeam unit (FNMU);
    #formazin nephelometric ratio unit (FNRU); formazin backscatter unit (FBU);
    #backscatter units (BU); attenuation units (AU)

    # Replace know problem units, fix and flag missing units
    wqp.check_units()

    # Custom dimensionality conversion
    for unit in wqp.dimensions_list():
        if wqp.units in ['NTU', 'NTRU', 'mg/l']:
            wqp.apply_conversion(convert.cm_to_NTU, unit)
        elif wqp.ureg(wqp.units).check({'[length]': 1}):
            wqp.apply_conversion(convert.NTU_to_cm, unit)

    return wqp


def sediment(wqp):
    """
    Standardizes 'Sediment' characteristic using and returning
    the WQP Characteristic Info Object.

    Parameters
    ----------
    wqp : WQCharData Object
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : WQP Characteristic Info Object.
        WQP Characteristic Info Object with updated attributes
    """
    #TODO: ParticleSizeBasis to check_basis?
    #wqp.check_basis(basis_col='ResultParticleSizeBasisText)

    #units = ['%', 'kg/ha', 'g', 'mg/L', 'g/l', 'tons/day', 'mg/l', 'ton/d/ft']

    # Replace know problem units, fix and flag missing units
    wqp.check_units()

    # Check/fix dimensionality issues
    # Convert mg/l <-> dimensionless Premiss: 1 liter water ~ 1 kg mass)
    wqp.replace_unit_by_dict(wqp.handle_dimensions()[0], wqp.measure_mask())

    # un-fixable dimensions: mass/area (kg/ha), mass (g),
    #                        mass/time (ton/day), mass/length/time (ton/day/ft)

    return wqp


def harmonize_all(df_in, errors='raise'):
    """
    Run harmonization on characteristicNames in table with existing functions.
    All results are standardized to default units. Intermediate columns are
    not retained.

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the expected columns.
    errors : string, optional
        Values of ‘ignore’, ‘raise’, or ‘skip’. The default is ‘raise’.
        If ‘raise’, invalid dimension conversions will raise an exception.
        If ‘skip’, invalid dimension conversions will not be converted.
        If ‘ignore’, invalid dimension conversions will return the NaN.

    Returns
    -------
    df : pandas.DataFrame
        Updated copy of df_in
    """
    df_out = df_in.copy()
    char_vals = list(set(df_out['CharacteristicName']))

    for char_val in char_vals:
        df_out = harmonize_generic(df_out, char_val, errors=errors)
    return df_out


def harmonize_generic(df_in, char_val, units_out=None, errors='raise',
                      intermediate_columns=False, report=False):
    """
    Harmonize a given char_val using the appropriate function

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame with the expected activity date time columns.
    char_val : string
        Expected characteristicName.
    units_out : string, optional
        Desired units to convert values into. The default is None.
    errors : string, optional
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
        Updated copy of df_in
    """
    # Check/retrieve standard attributes and df columns as object
    wqp = WQCharData(df_in, char_val)
    out_col = wqp.out_col  # domains.out_col_lookup()[char_val]

    if units_out:
        wqp.update_units(units_out)
    else:
        units_out = domains.OUT_UNITS[out_col]

    #TODO: this may need a try/except
    unit_col = 'Units'
    unit_flag = wqp.col.unit_in
    c_mask = wqp.c_mask
    # Update local units registry to define characteristic specific units
    wqp.update_ureg()

    harmonize_map = {'DO': dissolved_oxygen,
                     'Salinity': salinity,
                     'Turbidity':  turbidity,
                     'Sediment': sediment,
                     }
    # Use out_col to dictate function
    if out_col in ['pH', 'Secchi']:
        wqp.check_units()  # Fix and flag missing units
        # NOTE: pH undefined units ('std units', 'None', etc.) -> units,
        # TODO: replace above pH units to quiet warnings?
    elif out_col in ['Conductivity', 'Chlorophyll']:
        # Replace know problem units, fix and flag missing units
        wqp.check_units()
    elif out_col in ['Fecal_Coliform', 'E_coli']:
        # NOTE: Ecoli ['cfu/100ml', 'MPN/100ml', '#/100ml']
        # NOTE: feca ['CFU', 'MPN/100ml', 'cfu/100ml', 'MPN/100 ml', '#/100ml']
        # Replace known unit problems ('#' count; assume CFU/MPN is /100ml)
        wqp.replace_unit_by_dict(domains.UNITS_REPLACE[out_col])
        #TODO: figure out why the above must be done before replace_unit_by_str
        # Replace all instances in results column
        wqp.replace_unit_by_str('/100ml', '/(100ml)')
        wqp.replace_unit_by_str('/100 ml', '/(100ml)')
        wqp.check_units()  # Fix and flag missing units
    elif out_col in ['Carbon', 'Phosphorus', 'Nitrogen']:
        # Set Basis from unit and MethodSpec column
        wqp.check_basis()
        # Replace know problem units, fix and flag missing units (wet/dry?)
        wqp.check_units()
        # Convert dimensionality issues, e.g., mg/l <-> dimensionless (H2O)
        dimension_dict, mol_list = wqp.handle_dimensions()
        # Replace units by dictionary
        wqp.replace_unit_by_dict(dimension_dict, wqp.measure_mask())
        wqp.moles_convert(mol_list)  # Fix up units/measures where moles
    elif out_col == 'Temperature':
        # Remove spaces from units for pint ('deg C' == degree coulomb)
        wqp.update_units(wqp.units.replace(' ', ''))  # No spaces in units_out
        wqp.replace_unit_by_str(' ', '')  # Replace in results column
        wqp.check_units()  # Fix and flag missing units
    else:
        wqp = harmonize_map[out_col](wqp)
    #TODO: this may need a try/except
    #warn("WARNING: '{}' not available yet.".format(out_col))

    # Update values in out_col with standard units
    wqp.convert_units(errors=errors)

    # Speciation: Parse Sample Fraction, moving measure to new column
    # Note: just phosphorus right now
    # Total is TP (digested) from the whole water sample (vs total dissolved)
    # Dissolved is TDP (total) filtered water digested (vs undigested DIP)
    if out_col == 'Phosphorus':
        frac_dict = {'TP_Phosphorus': 'Total',
                     'TDP_Phosphorus': 'Dissolved',
                     'Other_Phosphorus': '',}
        # Make columns for Sample Fractions, loudly if unexpected (not in dict)
        frac_dict = wqp.fraction(frac_dict)  # Run sample fraction on WQP

    df_out = wqp.df
    #TODO: Add detection limits - wrangle.add_detection(df, char_val)
    #TODO: add activities? Quality filters?

    # Functionality only available w/ generic
    if report:
        print_report(df_out.loc[c_mask], out_col, unit_flag)
    if not intermediate_columns:
        df_out = df_out.drop([unit_col], axis=1)  # Drop intermediate columns
    return df_out


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
        #TODO: Default mean +/-1 standard deviation works here but generally 6
        threshold = {'min': 0.0,
                     'max': results_s.mean() + (6 * results_s.std())}
    inside = results_s[(results_s<=threshold['max']) &
                       (results_s>=threshold['min'])]
    print('Results outside threshold ({} to {}): {}'.format(threshold['min'],
                                                            threshold['max'],
                                                            len(results) - len(inside)))

    # Graphic representation of stats
    inside.hist(bins=int(sqrt(inside.count())))
    #TODO: two histograms overlaid?
    #inferred_s = pandas.Series([x.magnitude for x in inferred])
    #pandas.Series([x.magnitude for x in inferred]).hist()
