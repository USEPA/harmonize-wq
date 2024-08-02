# -*- coding: utf-8 -*-
"""Functions to convert from one unit to another, at times using :mod:`pint` decorators.

Contains several unit conversion functions not in :mod:`pint`.
"""

import math
from warnings import warn

import pandas
import pint
from numpy import nan

from harmonize_wq.domains import registry_adds_list

# TODO: does this constant belong here or in domains?
PERIODIC_MW = {
    "Organic carbon": 180.16,
    "C6H12O6": 180.16,
    "Phosphorus": 30.97,
    "P": 30.97,
    "PO4": 94.97,
    "Nitrogen": 14.01,
    "N": 14.01,
    "NO3": 62.01,
    "NO2": 46.01,
    "NH4": 18.04,
    "NH3": 17.03,
    "SiO3": 76.08,
}
# Molecular weight assumptions: Organic carbon = C6H12O6
# NOTE: for a more complete handling of MW: CalebBell/chemicals

u_reg = pint.UnitRegistry()  # For use in wrappers
# TODO: find more elegant way to do this with all definitions
for definition in registry_adds_list("Turbidity"):
    u_reg.define(definition)
for definition in registry_adds_list("Salinity"):
    u_reg.define(definition)


# timeit: 159.17
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
# timeit: 27.08
def convert_unit_series(quantity_series, unit_series, units, ureg=None, errors="raise"):
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

    >>> from harmonize_wq import convert
    >>> convert.convert_unit_series(quantity_series, unit_series, units = 'mg/l')
    0                   1.0 milligram / liter
    1    10000.000000000002 milligram / liter
    dtype: object
    """
    if quantity_series.dtype == "O":
        quantity_series = pandas.to_numeric(quantity_series)
    # Initialize classes from pint
    if ureg is None:
        ureg = pint.UnitRegistry()
    Q_ = ureg.Quantity

    lst_series = [pandas.Series(dtype="object")]
    # Note: set of series does not preservce order and must be sorted at end
    for unit in list(set(unit_series)):
        # Filter quantity_series by unit_series where == unit
        f_quant_series = quantity_series.where(unit_series == unit).dropna()
        unit_ = ureg(unit)  # Set unit once per unit
        result_list = [Q_(q, unit_) for q in f_quant_series]
        if unit != units:
            # Convert (units are all same so if one fails all will fail)
            try:
                result_list = [val.to(ureg(units)) for val in result_list]
            except pint.DimensionalityError as exception:
                if errors == "skip":
                    # do nothing, leave result_list unconverted
                    warn(f"WARNING: '{unit}' not converted")
                elif errors == "ignore":
                    # convert to NaN
                    result_list = [nan for val in result_list]
                    warn(f"WARNING: '{unit}' converted to NaN")
                else:
                    # errors=='raise', or anything else just in case
                    raise exception
        # Re-index and add series to list
        lst_series.append(pandas.Series(result_list, index=f_quant_series.index))
    return pandas.concat(lst_series).sort_index()


def mass_to_moles(ureg, char_val, Q_):
    """Convert a mass to moles substance.

    Parameters
    ----------
    ureg : pint.UnitRegistry
        Unit Registry Object with any custom units defined.
    char_val : str
        Characteristic name to use to find corresponding molecular weight.
    Q_ : pint.Quantity
        Mass to convert to moles.

    Returns
    -------
    pint.Quantity
        Value in moles of substance.

    Examples
    --------
    Build standard pint unit registry:

    >>> import pint
    >>> ureg = pint.UnitRegistry()

    Build pint quantity:

    >>> Q_ = 1 * ureg('g')

    >>> from harmonize_wq import convert
    >>> str(convert.mass_to_moles(ureg, 'Phosphorus', Q_))
    '0.03228931223764934 mole'
    """
    # TODO: Not used yet
    m_w = PERIODIC_MW[char_val]
    return Q_.to("moles", "chemistry", mw=m_w * ureg("g/mol"))


def moles_to_mass(ureg, Q_, basis=None, char_val=None):
    """Convert moles substance to mass.

    Either basis or char_val must have a non-default value.

    Parameters
    ----------
    ureg : pint.UnitRegistry
        Unit Registry Object with any custom units defined.
    Q_ : ureg.Quantity
        Quantity (measure and units).
    basis : str, optional
        Speciation (basis) of measure to determine molecular weight.
        Default is None.
    char_val : str, optional
        Characteristic Name to use when converting moles substance to mass.
        Default is None.

    Returns
    -------
    pint.Quantity
        Value in mass (g).

    Examples
    --------
    Build standard pint unit registry:

    >>> import pint
    >>> ureg = pint.UnitRegistry()

    Build quantity:

    >>> Q_ = 0.265 * ureg('umol')

    >>> from harmonize_wq import convert
    >>> str(convert.moles_to_mass(ureg, Q_, basis='as P'))
    '8.20705e-06 gram'
    """
    if basis:
        # Clean-up basis
        # print(basis)
        if basis.startswith("as "):
            basis = basis[3:]
        m_w = PERIODIC_MW[basis]
    elif char_val:
        m_w = PERIODIC_MW[char_val]
    else:
        raise ValueError("Characteristic Name or basis (Speciation) required")
    return Q_.to("g", "chemistry", mw=m_w / ureg("mol/g"))


@u_reg.wraps(u_reg.NTU, u_reg.centimeter)
def cm_to_NTU(val):
    """Convert turbidity measured in centimeters to NTU.

    Parameters
    ----------
    val : pint.Quantity
        The turbidity value in centimeters.

    Returns
    -------
    pint.Quantity
        The turbidity value in NTU.

    Examples
    --------
    Build standard pint unit registry:

    >>> import pint
    >>> ureg = pint.UnitRegistry()

    Build cm units aware pint Quantity (already in standard unit registry):

    >>> turbidity = ureg.Quantity('cm')
    >>> str(turbidity)
    '1 centimeter'
    >>> type(turbidity)
    <class 'pint.Quantity'>

    Convert to cm:

    >>> from harmonize_wq import convert
    >>> str(convert.cm_to_NTU(str(turbidity)))
    '3941.8 Nephelometric_Turbidity_Units'
    >>> type(convert.cm_to_NTU(str(turbidity)))
    <class 'pint.Quantity'>
    """
    # TODO: Currently exports None since NTU is not defined in u_reg
    # https://extension.usu.edu/utahwaterwatch/monitoring/field-instructions/
    # turbidity/turbiditytube/turbiditytubeconversionchart
    # Graphaed table conversions (average for each bound) and
    # used exponential curve (R2>.99)
    return 3941.8 * (val**-1.509)


@u_reg.wraps(u_reg.centimeter, u_reg.NTU)
def NTU_to_cm(val):
    """Convert turbidity in NTU (Nephelometric Turbidity Units) to centimeters.

    Parameters
    ----------
    val : pint.Quantity
        The turbidity value in NTU.

    Returns
    -------
    pint.Quantity
        The turbidity value in centimeters.

    Examples
    --------
    NTU is not a standard pint unit and must be added to a unit registry first
    (normally done by WQCharData.update_ureg() method):

    >>> import pint
    >>> ureg = pint.UnitRegistry()
    >>> from harmonize_wq import domains
    >>> for definition in domains.registry_adds_list('Turbidity'):
    ...     ureg.define(definition)

    Build NTU aware pint pint Quantity:

    >>> turbidity = ureg.Quantity('NTU')
    >>> str(turbidity)
    '1 Nephelometric_Turbidity_Units'
    >>> type(turbidity)
    <class 'pint.Quantity'>

    Convert to cm:

    >>> from harmonize_wq import convert
    >>> str(convert.NTU_to_cm('1 NTU'))
    '241.27 centimeter'
    >>> type(convert.NTU_to_cm('1 NTU'))
    <class 'pint.Quantity'>
    """
    # TODO: add wrapper
    # https://extension.usu.edu/utahwaterwatch/monitoring/field-instructions/
    # turbidity/turbiditytube/turbiditytubeconversionchart
    # Graphaed table conversions (average for each bound) and
    # used exponential curve (R2>.99)
    return 241.27 * (val**-0.662)


@u_reg.wraps(u_reg.NTU, u_reg.dimensionless)
def JTU_to_NTU(val):
    """Convert turbidity units from JTU (Jackson Turbidity Units) to NTU.

    Notes
    -----
    This is based on linear relationship: 1 -> 19, 0.053 -> 1, 0.4 -> 7.5

    Parameters
    ----------
    val : pint.Quantity
        The turbidity value in JTU (dimensionless).

    Returns
    -------
    NTU : pint.Quantity
        The turbidity value in dimensionless NTU.

    Examples
    --------
    JTU is not a standard pint unit and must be added to a unit registry first
    (normally done by WQCharData.update_ureg() method):

    >>> import pint
    >>> ureg = pint.UnitRegistry()
    >>> from harmonize_wq import domains
    >>> for definition in domains.registry_adds_list('Turbidity'):
    ...     ureg.define(definition)

    Build JTU units aware pint Quantity:

    >>> turbidity = ureg.Quantity('JTU')
    >>> str(turbidity)
    '1 Jackson_Turbidity_Units'
    >>> type(turbidity)
    <class 'pint.Quantity'>

    Convert to NTU:

    >>> from harmonize_wq import convert
    >>> str(convert.JTU_to_NTU(str(turbidity)))
    '18.9773 Nephelometric_Turbidity_Units'
    >>> type(convert.JTU_to_NTU(str(turbidity)))
    <class 'pint.Quantity'>
    """
    # Alternative relation (Macneina 1990): NTU = JTU **0.943
    # from Maceina, M. J., & Soballe, D. M. (1990).
    #      Wind-related limnological variation in Lake Okeechobee, Florida.
    #      Lake and Reservoir Management, 6(1), 93-100.
    return 19.025 * val - 0.0477


@u_reg.wraps(u_reg.NTU, u_reg.dimensionless)
def SiO2_to_NTU(val):
    """Convert turbidity units from SiO2 (silicon dioxide) to NTU.

    Notes
    -----
    This is based on a linear relationship: 0.13 -> 1, 1 -> 7.5, 2.5 -> 19

    Parameters
    ----------
    val : pint.Quantity.build_quantity_class
        The turbidity value in SiO2 units (dimensionless).

    Returns
    -------
    NTU : pint.Quantity.build_quantity_class
        The turbidity value in dimensionless NTU.

    Examples
    --------
    SiO2 is not a standard pint unit and must be added to a unit registry first
    (normally done using WQCharData.update_ureg() method):

    >>> import pint
    >>> ureg = pint.UnitRegistry()
    >>> from harmonize_wq import domains
    >>> for definition in domains.registry_adds_list('Turbidity'):
    ...     ureg.define(definition)

    Build SiO2 units aware pint Quantity:

    >>> turbidity = ureg.Quantity('SiO2')
    >>> str(turbidity)
    '1 SiO2'
    >>> type(turbidity)
    <class 'pint.Quantity'>

    Convert to NTU:

    >>> from harmonize_wq import convert
    >>> str(convert.SiO2_to_NTU(str(turbidity)))
    '7.5701 Nephelometric_Turbidity_Units'
    >>> type(convert.SiO2_to_NTU(str(turbidity)))
    <class 'pint.Quantity'>
    """
    return 7.6028 * val - 0.0327


def FNU_to_NTU(val):
    """Convert turbidity units from FNU (Formazin Nephelometric Units) to NTU.

    Parameters
    ----------
    val : float
        The turbidity magnitude (FNU is dimensionless).

    Returns
    -------
    NTU : float
        The turbidity magnitude (NTU is dimensionless).

    Examples
    --------
    Convert to NTU:

    >>> from harmonize_wq import convert
    >>> convert.FNU_to_NTU(8)
    10.136

    """
    return val * 1.267


@u_reg.wraps(
    u_reg.gram / u_reg.kilogram,
    (u_reg.gram / u_reg.liter, u_reg.standard_atmosphere, u_reg.degree_Celsius),
)
def density_to_PSU(
    val, pressure=1 * u_reg("atm"), temperature=u_reg.Quantity(25, u_reg("degC"))
):
    """Convert salinity as density (mass/volume) to Practical Salinity Units.

    Parameters
    ----------
    val : pint.Quantity.build_quantity_class
        The salinity value in density units.
    pressure : pint.Quantity.build_quantity_class, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : pint.Quantity.build_quantity_class, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    PSU : pint.Quantity.build_quantity_class
        The salinity value in dimensionless PSU.

    Examples
    --------
    PSU (Practical Salinity Units) is not a standard pint unit and must be added to a
    unit registry first (normally done by WQCharData.update_ureg() method):

    >>> import pint
    >>> ureg = pint.UnitRegistry()
    >>> from harmonize_wq import domains
    >>> for definition in domains.registry_adds_list('Salinity'):
    ...     ureg.define(definition)

    Build units aware pint Quantity, as string:

    >>> input_density = '1000 milligram / milliliter'

    Convert to Practical Salinity Units:

    >>> from harmonize_wq import convert
    >>> convert.density_to_PSU(input_density)
    <Quantity(4.71542857, 'gram / kilogram')>
    """
    # Standard Reference Value
    ref = 35.16504 / 35.0
    # density of pure water is ~1000 mg/mL
    if val > 1000:
        PSU = (float(val) * ref) - 1000
    else:
        PSU = ((float(val) + 1000) * ref) - 1000
    # print('{} mg/ml == {} ppth'.format(val, PSU))
    # multiply by 33.45 @26C, 33.44 @25C

    return PSU


@u_reg.wraps(
    u_reg.milligram / u_reg.milliliter,
    (u_reg.dimensionless, u_reg.standard_atmosphere, u_reg.degree_Celsius),
)
def PSU_to_density(
    val, pressure=1 * u_reg("atm"), temperature=u_reg.Quantity(25, u_reg("degC"))
):
    """Convert salinity as Practical Salinity Units (PSU) to density.

    Dimensionality changes from dimensionless Practical Salinity Units (PSU) to
    mass/volume density.

    Parameters
    ----------
    val : pint.Quantity
        The salinity value in dimensionless PSU.
    pressure : pint.Quantity, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : pint.Quantity, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    density : pint.Quantity.build_quantity_class
        The salinity value in density units (mg/ml).

    Examples
    --------
    PSU is not a standard pint unit and must be added to a unit registry first.
    This can be done using the WQCharData.update_ureg method:

    >>> import pint
    >>> ureg = pint.UnitRegistry()
    >>> from harmonize_wq import domains
    >>> for definition in domains.registry_adds_list('Salinity'):
    ...     ureg.define(definition)

    Build units aware pint Quantity, as string because it is an altered unit
    registry:

    >>> unit = ureg.Quantity('PSU')
    >>> unit
    <Quantity(1, 'Practical_Salinity_Units')>

    >>> type(unit)
    <class 'pint.Quantity'>

    >>> input_psu = str(8*unit)
    >>> input_psu
    '8 Practical_Salinity_Units'

    Convert to density:

    >>> from harmonize_wq import convert
    >>> str(convert.PSU_to_density(input_psu))
    '997.0540284772519 milligram / milliliter'
    """
    _p, t = pressure, temperature

    # Pure water density (see SMOW, Craig 1961)
    x = [
        999.842594,
        6.793952e-2 * t,
        -9.095290e-3 * t**2,
        1.001685e-4 * t**3,
        -1.120083e-6 * t**4,
        6.536336e-9 * t**5,
    ]
    pure_water = sum(x)

    # Constants
    a0 = [
        -4.0899e-3 * t,
        7.6438e-5 * (t**2),
        -8.2467e-7 * (t**3),
        5.3875e-9 * (t**4),
    ]
    a = 8.24493e-1 + sum(a0)

    b0 = [-5.72466e-3, 1.0227e-4 * t, -1.6546e-6 * (t**2)]
    b = sum(b0)

    density = pure_water + a * val + b * (val ** (3 / 2)) + 4.8314e-4 * (val**2)

    # # UNESCO 1983 Eqn.(13) p17.

    # s, t
    # T68 = T68conv(t)
    # T68 = T * 1.00024;

    # b = (8.24493e-1, -4.0899e-3, 7.6438e-5, -8.2467e-7, 5.3875e-9)
    # c = (-5.72466e-3, 1.0227e-4, -1.6546e-6)
    # d = 4.8314e-4
    # return (smow(t) + (b[0] + (b[1] + (b[2] + (b[3] + b[4] * T68) * T68) *
    #         T68) * T68) * s + (c[0] + (c[1] + c[2] * T68) * T68) * s *
    #       s ** 0.5 + d * s ** 2)
    return density


@u_reg.wraps(
    u_reg.milligram / u_reg.liter,
    (None, u_reg.standard_atmosphere, u_reg.degree_Celsius),
)
def DO_saturation(
    val, pressure=1 * u_reg("atm"), temperature=u_reg.Quantity(25, u_reg("degC"))
):
    """Convert Dissolved Oxygen (DO) from saturation (%) to concentration (mg/l).

    Defaults assume STP where pressure is 1 atmosphere and temperature 25C.

    Parameters
    ----------
    val : pint.Quantity.build_quantity_class
        The DO saturation value in dimensionless percent.
    pressure : pint.Quantity, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : pint.Quantity, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    pint.Quantity
        DO value in mg/l.

    Examples
    --------
    >>> from harmonize_wq import convert
    >>> convert.DO_saturation(70)
    <Quantity(5.78363269, 'milligram / liter')>

    At 2 atm (10m depth)
    >>> convert.DO_saturation(70, ('2 standard_atmosphere'))
    ￼￼11.746159340060716 milligram / liter
    """
    p, t = pressure, temperature
    if p == 1 & (t == 25):
        cP = 8.262332418
    else:
        cP = _DO_concentration_eq(p, t)
    return float(val) / 100 * cP  # Divide by 100?


@u_reg.wraps(
    None,
    (u_reg.milligram / u_reg.liter, u_reg.standard_atmosphere, u_reg.degree_Celsius),
)
def DO_concentration(
    val, pressure=1 * u_reg("atm"), temperature=u_reg.Quantity(25, u_reg("degC"))
):
    """Convert Dissolved Oxygen (DO) from concentration (mg/l) to saturation (%).

    Parameters
    ----------
    val : pint.Quantity.build_quantity_class
        The DO value (converted to mg/L).
    pressure : pint.Quantity, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : pint.Quantity, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    float
        Dissolved Oxygen (DO) as saturation (dimensionless).

    Examples
    --------
    Build units aware pint Quantity, as string:

    >>> input_DO = '578 mg/l'

    >>> from harmonize_wq import convert
    >>> convert.DO_concentration(input_DO)
    6995.603308586222
    """
    p, t = pressure, temperature
    if p == 1 & (t == 25):
        cP = 8.262332418
    else:
        cP = _DO_concentration_eq(p, t)
    return 100 * val / cP


def _DO_concentration_eq(p, t):
    """Equilibrium oxygen concentration at non-standard"""
    # https://www.waterontheweb.org/under/waterquality/oxygen.html#:~:
    # text=Oxygen%20saturation%20is%20calculated%20as,
    # concentration%20at%20100%25%20saturation%20decreases.
    tk = t + 273.15  # t in kelvin (t is in C)
    standard = 0.000975 - (1.426e-05 * t) + (6.436e-08 * (t**2))  # Theta
    # partial pressure of water vapor, atm
    Pwv = math.exp(11.8571 - (3840.7 / tk) - (216961 / (tk**2)))
    # equilibrium oxygen concentration at std pres of 1 atm
    cStar = math.exp(7.7117 - 1.31403 * math.log(t + 45.93))
    numerator = (1 - Pwv / p) * (1 - (standard * p))
    denominator = (1 - Pwv) * (1 - standard)

    return cStar * p * (numerator / denominator)


@u_reg.wraps(
    u_reg.dimensionless,
    (
        u_reg.microsiemens / u_reg.centimeter,
        u_reg.standard_atmosphere,
        u_reg.degree_Celsius,
    ),
)
def conductivity_to_PSU(
    val, pressure=0 * u_reg("atm"), temperature=u_reg.Quantity(25, u_reg("degC"))
):
    """Estimate salinity (PSU) from conductivity.

    Parameters
    ----------
    val : pint.Quantity.build_quantity_class
        The conductivity value (converted to microsiemens / centimeter).
    pressure : pint.Quantity, optional
        The pressure value. The default is 0*ureg("atm").
    temperature : pint.Quantity, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    pint.Quantity
        Estimated salinity (PSU).

    Notes
    -----
    Conductivity to salinity conversion PSS 1978 method.
    c-numeric conductivity in uS (microsiemens).
    t-numeric Celsius temperature (defaults to 25).
    P-numeric optional pressure (defaults to 0).

    References
    ----------
    IOC, SCOR and IAPSO, 2010: The international thermodynamic equation of
    seawater – 2010: Calculation and use of thermodynamic properties.
    Intergovernmental Oceanographic Commission, Manuals and Guides No. 56,
    UNESCO (English), 196 pp.

    Alan D. Jassby and James E. Cloern (2015). wq: Some
    tools for  exploring water quality monitoring data. R package v0.4.4.
    See the ec2pss function.

    Adapted from R `cond2sal_shiny
    <https://github.com/jsta/cond2sal_shiny/blob/master/helpers.R>`_

    Examples
    --------
    PSU (Practical Salinity Units) is not a standard pint unit and must be
    added to a unit registry first:

    >>> import pint
    >>> ureg = pint.UnitRegistry()
    >>> from harmonize_wq import domains
    >>> for definition in domains.registry_adds_list('Salinity'):
    ...     ureg.define(definition)

    Build units aware pint Quantity, as string:

    >>> input_conductivity = '111.0 uS/cm'

    Convert to Practical Salinity Units:

    >>> from harmonize_wq import convert
    >>> convert.conductivity_to_PSU(input_conductivity)
    <Quantity(0.057, 'dimensionless')>
    """
    # Units wrapper returns magnitude only (faster)
    p, t = pressure, temperature

    a = [0.008, -0.1692, 25.3851, 14.0941, -7.0261, 2.7081]
    b = [5e-04, -0.0056, -0.0066, -0.0375, 0.0636, -0.0144]
    c = [0.6766097, 0.0200564, 0.0001104, -6.9698e-07, 1.0031e-09]
    D = [0.03426, 0.0004464, 0.4215, -0.003107]
    e = [0.000207, -6.37e-08, 3.989e-12]

    # Csw = 42.914
    K = 0.0162
    Ct = round(val * (1 + 0.0191 * (t - 25)), 0)
    R = (Ct / 1000) / 42.914
    # Was rt
    c = c[0] + (c[1] * t) + (c[2] * t**2) + (c[3] * t**3) + (c[4] * t**4)

    Rp = 1 + (p * e[0] + e[1] * p**2 + e[2] * p**3) / (
        1 + D[0] * t + D[1] * t**2 + (D[2] + D[3] * t) * R
    )
    Rt1 = R / (Rp * c)
    dS = (
        (
            b[0]
            + b[1] * Rt1 ** (1 / 2)
            + b[2] * Rt1 ** (2 / 2)
            + b[3] * Rt1 ** (3 / 2)
            + b[4] * Rt1 ** (4 / 2)
            + b[5] * Rt1 ** (5 / 2)
        )
        * (t - 15)
        / (1 + K * (t - 15))
    )
    S = (
        a[0]
        + a[1] * Rt1 ** (1 / 2)
        + a[2] * Rt1 ** (2 / 2)
        + a[3] * Rt1 ** (3 / 2)
        + a[4] * Rt1 ** (4 / 2)
        + a[5] * Rt1 ** (5 / 2)
        + dS
    )

    # TODO: implement these two lines? Shouldn't encounter NaN.
    # S[is.na(S<0)]<-NA  # if <0 or NA set as nan
    # S[S<2 & !is.na(S)]<- S[S<2 & !is.na(S)] - a[0]/(1 + 1.5 * (400 * Rt1) +
    # (400 * Rt1)**2) - (b[0] * (t - 15)/(1 + K * (t - 15)))/
    # (1 + (100 * Rt1)**(1/2) + (100 * Rt1)**(3/2))
    # S = S - a[0]/(1 + 1.5 * (400 * Rt1) + (400 * Rt1)**2) - (b[0] * (t - 15)/
    # (1 + K * (t - 15)))/(1 + (100 * Rt1)**(1/2) + (100 * Rt1)**(3/2))

    return round(S, 3)
