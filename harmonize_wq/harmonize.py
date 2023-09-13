# -*- coding: utf-8 -*-
"""
    Class and functions for harmonizing data retrieved from EPA's Water Quality
    Portal (WQP)
"""
from types import SimpleNamespace
from warnings import warn
import pandas
import pint
from numpy import nan
from harmonize_wq import domains
from harmonize_wq import basis
from harmonize_wq import convert
from harmonize_wq import visualize as viz


class WQCharData():
    """
    A class to represent Water Quality Portal results for a specific
    characteristic

    Parameters
    ----------
    df_in : pandas.DataFrame
        DataFrame that will be updated.
    char_val : string
        Expected characteristicName.

    Attributes
    ----------
    df : pandas.DataFrame
        DataFrame with results for the specific characteristic
    c_mask : pandas.Series
        Row conditional (bool) mask to limit df rows to only those for the
        specific characteristic
    col : SimpleNamespace
        Standard df column names for unit_in, unit_out, and measure
    out_col : str
        Column name in df for results, set using char_val
    ureg = pint.UnitRegistry()
        Pint unit registry, starts set to standard unit registry
    units: str
        Units all results in out_col will be converted into. Default units are
        returned from domains.OUT_UNITS[out_col].
    
    Examples
    --------
    Build dataframe to use as input:
    
    >>> import pandas
    >>> from numpy import nan
    >>> df = pandas.DataFrame({'CharacteristicName': ['Phosphorus',
                                                      'Temperature, water',],
    ...                        'ResultMeasure/MeasureUnitCode': [nan, nan],
    ...                        'ResultMeasureValue': ['1.0', '10.0',],
    ...                        })
    >>> df
       CharacteristicName  ResultMeasure/MeasureUnitCode ResultMeasureValue
    0          Phosphorus                            NaN                1.0
    1  Temperature, water                            NaN               10.0
    
    >>> wq = harmonize.WQCharData(df, 'Phosphorus')
    >>> wq.df
       CharacteristicName  ResultMeasure/MeasureUnitCode  ... Units  Phosphorus
    0          Phosphorus                            NaN  ...   NaN         1.0
    1  Temperature, water                            NaN  ...   NaN         NaN
    
    [2 rows x 5 columns]
    >>> wq.df.columns
    Index(['CharacteristicName', 'ResultMeasure/MeasureUnitCode',
           'ResultMeasureValue', 'Units', 'Phosphorus'],
          dtype='object')
    """

    def __init__(self, df_in, char_val):
        df_out = df_in.copy()
        # self.check_df(df)
        df_checks(df_out)
        c_mask = df_out['CharacteristicName'] == char_val
        self.c_mask = c_mask
        # Deal with units: set out = in
        cols = {'unit_in': 'ResultMeasure/MeasureUnitCode',
                'unit_out': 'Units',
                'measure': 'ResultMeasureValue',
                'basis': 'Speciation', }
        self.col = SimpleNamespace(**cols)
        df_out.loc[c_mask, self.col.unit_out] = df_out.loc[c_mask,
                                                           self.col.unit_in]
        self.df = df_out
        # Deal with values: set out_col = in
        self.out_col = domains.out_col_lookup()[char_val]
        self._coerce_measure()
        self.ureg = pint.UnitRegistry()  # Add standard unit registry
        self.units = domains.OUT_UNITS[self.out_col]

    def _coerce_measure(self):
        """ Identifies bad measure values, and flags them. Copies measure
            values to out_col, with bad measures as NaN.
        """
        df_out = self.df
        c_mask = self.c_mask
        meas_col = self.col.measure

        # Coerce bad measures in series to NaN
        meas_s = pandas.to_numeric(df_out.loc[c_mask, meas_col],
                                   errors='coerce')
        # Create a list of the bad measures in the series
        bad_measures = [df_out.iloc[i][meas_col] for i in meas_s[meas_s.isna()].index]
        for bad_meas in pandas.unique(bad_measures):
            # Flag each unique bad measure one measure (not row) at a time
            if pandas.isna(bad_meas):
                flag = '{}: missing (NaN) result'.format(meas_col)
                cond = c_mask & (df_out[meas_col].isna())
            else:
                flag = '{}: "{}" result cannot be used'.format(meas_col,
                                                               bad_meas)
                cond = c_mask & (df_out[meas_col] == bad_meas)
            # Flag bad measures
            df_out = add_qa_flag(df_out, cond, flag)
        df_out[self.out_col] = meas_s  # Return coerced results

        self.df = df_out

    def _unit_mask(self, unit, column=None):
        """Get mask that is characteristic specific (c_mask) and has required
        units.
        """
        if column:
            # TODO: column for in vs out col, not being used, remove?
            return self.measure_mask() & (self.df[column] == unit)
        return self.measure_mask() & (self.df[self.col.unit_out] == unit)

    def _infer_units(self, flag_col=None):
        """
        Replace missing units with desired unit and add QA_flag about it in df.

        Parameters
        ----------
        flag_col : string, optional
            Column to reference in QA_flags. The default None uses self.col.unit_out instead.
        """
        # QA flag for missing units
        flag = unit_qa_flag(self.col.unit_out, 'MISSING', self.units, flag_col)
        # Update mask for missing units
        units_mask = self.c_mask & self.df[self.col.unit_out].isna()
        self.df = add_qa_flag(self.df, units_mask, flag)  # Assign flag
        # Update with infered unit
        self.df.loc[units_mask, self.col.unit_out] = self.units
        # Note: .fillna(self.units) is slightly faster but hits datatype issues
        
        def _replace_in_col(self, col, old_val, new_val, mask=None):
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
                The default None uses 'CharacteristicName' mask instead.
        
            Returns
            -------
            df_in : pandas.DataFrame
                Updated DataFrame.
        
            """
            if mask is None:
                mask = self.c_mask
            df_in = self.df
            # Note: Timing is just as fast as long as df isn't copied
            #       Timing for replace vs set unkown
            mask_old = mask & (df_in[col]==old_val)
            #str.replace did not work for short str to long str (over-replaces)
            #df.loc[mask, col] = df.loc[mask, col].str.replace(old_val, new_val)
            df_in.loc[mask_old, col] = new_val  # This should be more explicit
        
            return df_in


    def check_units(self, flag_col=None):
        """
        Checks for bad units that are missing (assumes default_unit) or
        unrecognized as valid by unit registry (ureg). Does not check for units
        in the correct dimensions, or a mistaken identity (e.g. 'deg F'
        recognized as 'degree * farad').

        Parameters
        ----------
        flag_col : string, optional
            Column to reference in QA_flags.
            The default None uses unit_col instead.
            
        Examples
        --------
        Build DataFrame to use as input:
        
        >>> import pandas
        >>> from numpy import nan
        >>> df = pandas.DataFrame({'CharacteristicName': ['Phosphorus',
        ...                                               'Temperature, water',
        ...                                               'Phosphorus',],
        ...                        'ResultMeasure/MeasureUnitCode': [nan, nan, 'Unknown',],
        ...                        'ResultMeasureValue': ['1.0', '67.0', '10',],
        ...                        })
        >>> df
           CharacteristicName ResultMeasure/MeasureUnitCode ResultMeasureValue
        0          Phosphorus                           NaN                1.0
        1  Temperature, water                           NaN               67.0
        2          Phosphorus                       Unknown                 10
        
        Build WQ Characteristic Data object from DataFrame:
        
        >>> wq = harmonize.WQCharData(df, 'Phosphorus')
        >>> wq.df.Units
        0        NaN
        1        NaN
        2    Unknown
        
        Run check_units method to replace bad or missing units for phosphorus:
    
        >>> wq.check_units()
        UserWarning: WARNING: 'Unknown' UNDEFINED UNIT for Phosphorus
        
        >>> wq.df[['CharacteristicName', 'Units']]
           CharacteristicName Units                                            QA_flag
        0          Phosphorus  mg/l  ResultMeasure/MeasureUnitCode: MISSING UNITS, ...
        1  Temperature, water   NaN                                                NaN
        2          Phosphorus  mg/l  ResultMeasure/MeasureUnitCode: 'Unknown' UNDEF...
        
        Note: it didn't infer units for 'Temperature, water' because wq is Phosphorus specific
        """
        # Replace unit by dict using domain
        self.replace_unit_by_dict(domains.UNITS_REPLACE[self.out_col])

        # Deal with optional args
        if flag_col is None:
            flag_col = self.col.unit_in
        self._infer_units(flag_col=flag_col)

        df_out = self.df

        # Check each unique unit is valid in ureg
        for unit in list(set(df_out.loc[self.c_mask, self.col.unit_out])):
            try:
                self.ureg(unit)
            except pint.UndefinedUnitError:
                # WARNING: Does not catch '%' or bad units in ureg (eg deg F)
                # If bad, flag and replace
                problem = "'{}' UNDEFINED UNIT for {}".format(unit, self.out_col)
                warn("WARNING: " + problem)
                flag = unit_qa_flag(self.col.unit_out, problem, self.units, flag_col)
                # New mask for bad units
                u_mask = self._unit_mask(unit)
                # Assign flag to bad units
                df_out = add_qa_flag(df_out, u_mask, flag)
                df_out.loc[u_mask, self.col.unit_out] = self.units  # Replace w/ default
        self.df = df_out

    def check_basis(self, basis_col='MethodSpecificationName'):
        """
        Determine speciation (basis) for measure.

        Parameters
        ----------
        basis_col : str, optional
            Basis column name. Default is 'MethodSpecificationName' which is
            replaced by 'Speciation', others are updated in place.
        
        Examples
        --------
        Build DataFrame to use as input:
        
        >>> import pandas
        >>> from numpy import nan
        >>> df = pandas.DataFrame({'CharacteristicName': ['Phosphorus',
        ...                                               'Temperature, water',
        ...                                               'Phosphorus',],
        ...                        'ResultMeasure/MeasureUnitCode': ['mg/l as P', nan, 'mg/l',],
        ...                        'ResultMeasureValue': ['1.0', '67.0', '10',],
        ...                        'MethodSpecificationName': [nan, nan, 'as PO4',],        
        ...                        })
        >>> df
           CharacteristicName  ... MethodSpecificationName
        0          Phosphorus  ...                     NaN
        1  Temperature, water  ...                     NaN
        2          Phosphorus  ...                  as PO4
        
        [3 rows x 4 columns]
        
        Build WQ Characteristic Data object from DataFrame:
        
        >>> wq = harmonize.WQCharData(df, 'Phosphorus')
        >>> wq.df.columns
        Index(['CharacteristicName', 'ResultMeasure/MeasureUnitCode',
               'MethodSpecificationName', 'ResultMeasureValue', 'Units', 'Phosphorus'],
              dtype='object')
        
        Run check_basis method to speciation for phosphorus:
        
        >>> wq.check_basis()
        >>> wq.df[['MethodSpecificationName', 'Speciation']]
          MethodSpecificationName  Speciation
        0                     NaN           P
        1                     NaN         NaN
        2                     NaN         PO4
        
        Note where basis was part of ResultMeasure/MeasureUnitCode it has been removed in Units:

        >>> wq.df.iloc[0]
        CharacteristicName               Phosphorus
        ResultMeasure/MeasureUnitCode     mg/l as P
        ResultMeasureValue                      1.0
        MethodSpecificationName                 NaN
        Units                                  mg/l
        Phosphorus                              1.0
        Speciation                                P
        Name: 0, dtype: object
        """
        c_mask = self.c_mask

        # Check for Method Specification column
        df_checks(self.df, [basis_col])

        # Basis from MethodSpecificationName
        if basis_col == 'MethodSpecificationName':
            
            # Add basis out column (i.e., 'Speciation') if it doesn't exist
            if self.col.basis not in self.df.columns:
                self.df[self.col.basis] = nan
            
            # Mask to characteristic
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

            # Get built-in char_val based on out_col attribute
            char_keys, char_vals = zip(*domains.out_col_lookup().items())
            char_val = list(char_keys)[list(char_vals).index(self.out_col)]

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
        Update object units attribute to convert everything into. Does not do
        the conversion.
        
        Parameters
        ----------
        units_out : str
            Units to convert results into.

        Examples
        --------
        >>> wq = harmonize.WQCharData(df, 'Phosphorus')
        >>> wq.units
        'mg/l'
        
        >>> wq.update_units('mg/kg')
        >>> wq.units
        'mg/kg'
        """
        self.units = units_out

    def measure_mask(self, column=None):
        """
        Get mask that is characteristic specific (c_mask) and only has valid
        col measures (Non-NA).
        
        Parameters
        ----------
        column : str, optional
            DataFrame column name to use. Default None uses self.out_col

        Examples
        --------
        >>> wq = harmonize.WQCharData(df, 'Phosphorus')
        >>> wq.measure_mask()
        0     True
        1    False
        2     True
        dtype: bool
        """
        if column:
            return self.c_mask & self.df[column].notna()
        return self.c_mask & self.df[self.out_col].notna()

    def convert_units(self, default_unit=None, errors='raise'):
        """
        Update object DataFrame's out-col to convert from old units to
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

        Examples
        --------
        Build dataframe to use as input:
        
        >>> import pandas
        >>> df = pandas.DataFrame({'CharacteristicName': ['Phosphorus',
        ...                                               'Temperature, water',
        ...                                               ],
        ...                        'ResultMeasure/MeasureUnitCode': ['mg/ml',
        ...                                                          'deg C'],
        ...                        'ResultMeasureValue': ['1.0', '10.0',],
        ...                        })
        >>> df
           CharacteristicName ResultMeasure/MeasureUnitCode ResultMeasureValue
        0          Phosphorus                         mg/ml                1.0
        1  Temperature, water                         deg C               10.0
        
        Build WQ Characteristic Data object from DataFrame:
            
        >>> wq = harmonize.WQCharData(df, 'Phosphorus')
        
        >>> wq.convert_units()
        >>> wq.df
           CharacteristicName  ...                            Phosphorus
        0          Phosphorus  ...  1000.0000000000001 milligram / liter
        1  Temperature, water  ...                                   NaN
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

        Examples
        --------
        Build dataframe to use as input:
        
        >>> import pandas
        >>> df = pandas.DataFrame({'CharacteristicName': ['Dissolved oxygen (DO)',
        ...                                               'Dissolved oxygen (DO)',
        ...                                               ],
        ...                        'ResultMeasure/MeasureUnitCode': ['mg/l',
        ...                                                          '%'],
        ...                        'ResultMeasureValue': ['1.0', '10.0',],
        ...                        })
        >>> df
              CharacteristicName ResultMeasure/MeasureUnitCode ResultMeasureValue
        0  Dissolved oxygen (DO)                          mg/l                1.0
        1  Dissolved oxygen (DO)                             %               10.0
        
        Build WQ Characteristic Data object from DataFrame:
            
        >>> wq = harmonize.WQCharData(df, 'Dissolved oxygen (DO)')        
        >>> wq.apply_conversion(convert.DO_saturation, '%')
        >>> wq.df[['Units', 'DO']]
        """
        # TODO: QA flag inexact conversions?
        df_out = self.df
        if u_mask is None:
            u_mask = self._unit_mask(unit)
        unit = self.ureg.Quantity(unit)  # Pint quantity object from unit
        old_vals = df_out.loc[u_mask, self.out_col]
        try:
            new_quants = [convert_fun(x*unit) for x in old_vals]
        except ValueError:
            #print(old_vals.iloc[0]*unit)
            # string to avoid altered ureg issues
            new_quants = [convert_fun(str(x*unit)) for x in old_vals]
        # 1run=6505.62ms (may be slower) vs apply (5888.43ms)
        #new_vals = old_vals.apply(lambda x: convert_fun(x*unit).magnitude)
        new_vals = [quant.magnitude for quant in new_quants]
        df_out.loc[u_mask, self.out_col] = new_vals
        df_out.loc[u_mask, self.col.unit_out] = str(new_quants[0].units)
        # self.units <- was used previously, sus when units is not default

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
        A simple way to do multiple replace_in_col() replacements of val_dict
        key with val_dict value.

        Parameters
        ----------
        val_dict : dictionary
            Occurrences of key in the unit column are replaced with the value.
        mask : pandas.Series, optional
            Conditional mask to limit rows.
            The default None, uses the c_mask attribute.
        """
        col = self.col.unit_out
        for item in val_dict.items():
            self._replace_in_col(self.df, col, item[0], item[1], mask)

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
        if suffix is None:
            suffix = self.out_col

        catch_all = 'Other_{}'.format(suffix)
        if frac_dict is None:
            frac_dict = {catch_all: ''}
        else:
            if catch_all not in frac_dict.keys():
                frac_dict[catch_all] = ['']
        if not isinstance(frac_dict[catch_all], list):
            frac_dict[catch_all] = [frac_dict[catch_all]]
        # Get all domain values
        #accepted_fracs = list(domains.get_domain_dict('ResultSampleFraction').keys())
        for key in domains.get_domain_dict('ResultSampleFraction').keys():
            # Check against expected fractions and add others to catch_all
            if key not in [x for v in frac_dict.values() for x in v]:
                frac_dict[catch_all] += [key]
        # Flatten for some uses
        samp_fract_set = sorted({x for v in frac_dict.values() for x in v})

        # Check for sample fraction column
        df_checks(self.df, [fract_col])
        # Replace bad sample fraction w/ nan
        self.df = self._replace_in_col(self.df, fract_col, ' ', nan, c_mask)

        df_out = self.df

        # Make column for any unexpected Sample Fraction values, loudly
        for s_f in set(df_out[c_mask][fract_col].dropna()):
            if s_f not in samp_fract_set:
                char = '{}_{}'.format(s_f.replace(' ', '_'), suffix)
                frac_dict[char] = s_f
                prob = '"{}" column for {}, may be error'.format(char, s_f)
                warn('Warning: ' + prob)
        # Test we didn't skip any SampleFraction
        samp_fract_set = sorted({x for v in frac_dict.values() for x in v})
        for s_f in set(df_out[c_mask][fract_col].dropna()):
            assert s_f in samp_fract_set, '{} check in {}'.format(s_f,
                                                                      fract_col)
        # Create out columns for each sample fraction
        for frac in frac_dict.items():
            col = frac[0]  # New column name
            for smp_frac in frac[1]:
                if smp_frac in set(df_out.loc[c_mask, fract_col].dropna()):
                    # New subset mask for sample frac
                    f_mask = c_mask & (df_out[fract_col]==smp_frac)
                    # Copy measure to new col (new col name from char_list)
                    df_out.loc[f_mask, col] = df_out.loc[f_mask, suffix]
                elif smp_frac == '':
                    # Values where sample fraction missing go to catch all
                    if df_out.loc[c_mask, fract_col].isnull().values.any():
                        # New subset mask
                        f_mask = c_mask & (df_out[fract_col].isnull())
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
            mol_mask = self._unit_mask(quant)
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
        
    Examples
    --------
    
    Check dataframe for column:
    
    >>> import pandas
    >>> df = pandas.DataFrame({'CharacteristicName': ['Phosphorus'],})
    >>> df
      CharacteristicName
    0         Phosphorus
    
    Check for existing column:

    >>> harmonize.df_checks(df, columns=['CharacteristicName'])
    
    If column is not in df it throws an assertionError:
        
    >>> harmonize.df_checks(df, columns=['ResultMeasureValue'])
    AssertionError: ResultMeasureValue not in DataFrame
    """
    if columns is None:
        # Assign defaults
        columns = ('ResultMeasure/MeasureUnitCode',
                   'ResultMeasureValue',
                   'CharacteristicName')
    for col in columns:
        assert col in df_in.columns, '{} not in DataFrame'.format(col)


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

    lst_series = [pandas.Series(dtype='object')]
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
                    # convert to NaN
                    result_list = [nan for val in result_list]
                    warn("WARNING: '{}' converted to NaN".format(unit))
                else:
                    # errors=='raise', or anything else just in case
                    raise exception
        # Re-index and add series to list
        lst_series.append(pandas.Series(result_list, index=f_quant_series.index))
    return pandas.concat(lst_series)


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
        String to use when referring to the unit_col. If None, unit_col is used.
        The default is None.

    Returns
    -------
    string
        Flag to use in QA_flag column.

    """
    if flag_col:
        return '{}: {} UNITS, {} assumed'.format(flag_col, trouble, unit)
    return '{}: {} UNITS, {} assumed'.format(unit_col, trouble, unit)


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
    Handles and routes common dimension conversions/contexts

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
    wqp.check_units()  # Replace know problem units, fix and flag missing units

    # Check/fix dimensionality issues (Type III)
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
    Standardizes 'Salinity' characteristic using and returning the WQP
    Characteristic Info Object.
    Note: PSU=PSS=ppth
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
    """
    Standardizes 'Turbidity' characteristic using and returning
    the WQP Characteristic Info Object.

    See USGS Report Chapter A6. Section 6.7. Turbidity
        https://pubs.usgs.gov/twri/twri9a6/twri9a67/twri9a_Section6.7_v2.1.pdf
    See ASTM D\315-17 for equivalent unit definitions:
        'NTU'  - 400-680nm (EPA 180.1), range 0.0-40
        'NTRU' - 400-680nm (2130B), range 0-10,000
        'NTMU' - 400-680nm
        'FNU'  - 780-900nm (ISO 7027), range 0-1000
        'FNRU' - 780-900nm (ISO 7027), range 0-10,000
        'FAU'  - 780-900nm, range 20-1000
    Older methods:
        'FTU' - lacks instrumentation specificity
        'SiO2' (ppm or mg/l) - concentration of calibration standard (=JTU)
        'JTU' - candle instead of formazin standard, near 40 NTU these may be
        equivalent, but highly variable
    Conversions used:
        cm <-> NTU see convert.cm_to_NTU()
        https://extension.usu.edu/utahwaterwatch/monitoring/field-instructions/

    Alternative conversions not currently used by default:
        convert.FNU_to_NTU from Gohin (2011) Ocean Sci., 7, 705–732
        https://doi.org/10.5194/os-7-705-2011
        convert.SiO2_to_NTU linear relation from Otilia et al. 2013
        convert.JTU_to_NTU linear relation from Otilia et al. 2013
        Otilia, Rusănescu Carmen, Rusănescu Marin, and Stoica Dorel.
        "MONITORING OF PHYSICAL INDICATORS IN WATER SAMPLES."
        https://hidraulica.fluidas.ro/2013/nr_2/84_89.pdf

    Parameters
    ----------
    wqp : WQCharData Object
        WQP Characteristic Info Object.

    Returns
    -------
    wqp : WQP Characteristic Info Object.
        WQP Characteristic Info Object with updated attributes
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
                    warn('Bad Turbidity unit: {}'.format(unit))
            elif wqp.ureg(unit).check({'[length]': 1}):
                wqp.apply_conversion(convert.cm_to_NTU, unit)
            else:
                #raise ValueError('Bad Turbidity unit: {}'.format(unit))
                warn('Bad Turbidity unit: {}'.format(unit))
        elif wqp.ureg(wqp.units).check({'[length]': 1}):
            wqp.apply_conversion(convert.NTU_to_cm, unit)
        else:
            #raise ValueError('Bad Turbidity unit: {}'.format(wqp.units))
            warn('Bad Turbidity unit: {}'.format(unit))
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
    #'< 0.0625 mm', < 0.125 mm, < 0.25 mm, < 0.5 mm, < 1 mm, < 2 mm, < 4 mm
    wqp.check_basis(basis_col='ResultParticleSizeBasisText')

    wqp.check_units()  # Replace know problem units, fix and flag missing units

    # Check/fix dimensionality issues (Type I)
    # Convert mg/l <-> dimensionless Premiss: 1 liter water ~ 1 kg mass)
    wqp.replace_unit_by_dict(wqp.handle_dimensions()[0], wqp.measure_mask())

    # un-fixable dimensions: mass/area (kg/ha), mass (g),
    #                        mass/time (ton/day), mass/length/time (ton/day/ft)

    return wqp


def harmonize_all(df_in, errors='raise'):
    """
    Run harmonization on 'CharacteristicNames' in table with existing functions.
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
    
    See also
    --------
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
        Expected 'CharacteristicName'.
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
    
    See also
    --------
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
        wqp.replace_unit_by_str('#', 'CFU')
        # Replace known unit problems (e.g., assume CFU/MPN is /100ml)
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
        harmonize_map = {'DO': dissolved_oxygen,
                         'Salinity': salinity,
                         'Turbidity':  turbidity,
                         'Sediment': sediment,
                         }
        try:
            wqp = harmonize_map[out_col](wqp)
        except KeyError:
            # out_col not recognized
            warn("WARNING: '{}' not available yet.".format(out_col))
            raise

    # Update values in out_col with standard units
    wqp.convert_units(errors=errors)

    # Speciation: Parse Sample Fraction, moving measure to new column
    # Note: just phosphorus right now
    # Total is TP (digested) from the whole water sample (vs total dissolved)
    # Dissolved is TDP (total) filtered water digested (vs undigested DIP)
    if out_col == 'Phosphorus':
        frac_dict = {'TP_Phosphorus': ['Total'],
                     'TDP_Phosphorus': ['Dissolved'],
                     'Other_Phosphorus': [''],}
        # Make columns for Sample Fractions, loudly if unexpected (not in dict)
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
