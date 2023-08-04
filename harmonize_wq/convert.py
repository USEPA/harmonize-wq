# -*- coding: utf-8 -*-
"""
Created on Tue Feb  1 16:41:35 2022

Module with functions to convert from one unit to another, sometimes using
pint decorators. Contains several unit conversions functions not in Pint.

@author: jbousqui
"""
import pint

# TODO: does this constant belong here or in domains?
PERIODIC_MW = {'Organic carbon': 180.16,
               'C6H12O6': 180.16,
               'Phosphorus': 30.97,
               'P': 30.97,
               'PO4': 94.97,
               'Nitrogen': 14.01,
               'N': 14.01,
               'NO3': 62.01,
               'NO2': 46.01,
               'NH4': 18.04,
               'NH3': 17.03,
               'SiO3': 76.08,
               }
# Molecular weight assumptions: Organic carbon = C6H12O6
# NOTE: for a more complete handling of MW: CalebBell/chemicals

u_reg = pint.UnitRegistry()  # For use in wrappers
# TODO: find more elegant way to do this with all definitions
u_reg.define('NTU = [turbidity]')
u_reg.define('Jackson_Turbidity_Units = [] = JTU')
u_reg.define('SiO2 = []')


def mass_to_moles(ureg, char_val, Q_):
    """
    Converts a mass to moles substance.

    Parameters
    ----------
    ureg : pint.UnitRegistry
        Unit Registry Object with any custom units defined.
    char_val : TYPE
        DESCRIPTION.
    Q_ : TYPE
        DESCRIPTION.

    Returns
    -------
    pint.Quantity
        Value in moles of substance.

    """
    # TODO: Not used yet
    m_w = PERIODIC_MW[char_val]
    return Q_.to('moles', 'chemistry', mw=m_w * ureg('g/mol'))


def moles_to_mass(ureg, Q_, basis=None, char_val=None):
    """
    Converts moles substance to mass.

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

    """
    if basis:
        # Clean-up basis
        # print(basis)
        if basis.startswith('as '):
            basis = basis[3:]
        m_w = PERIODIC_MW[basis]
    elif char_val:
        m_w = PERIODIC_MW[char_val]
    else:
        raise ValueError("Characteristic Name or basis (Speciation) required")
    return Q_.to('g', 'chemistry', mw=m_w / ureg('mol/g'))


@u_reg.wraps(u_reg.NTU, u_reg.centimeter)
def cm_to_NTU(val):
    """
    Convert Turbidity measured in centimeters to NTU

    Parameters
    ----------
    val : pint.Quanitity
        The turbidity value in centimeters.

    Returns
    -------
        The turbidity value in NTU.

    """
    # TODO: Currently exports None since NTU is not defined in u_reg
    # https://extension.usu.edu/utahwaterwatch/monitoring/field-instructions/
    # turbidity/turbiditytube/turbiditytubeconversionchart
    # Graphaed table conversions (average for each bound) and
    # used exponential curve (R2>.99)
    return 3941.8 * (val**-1.509)


@u_reg.wraps(u_reg.centimeter, u_reg.NTU)
def NTU_to_cm(val):
    """
    Convert Turbidity measured in NTU to centimeters

    Parameters
    ----------
    val : pint.Quanitity
        The turbidity value in NTU.

    Returns
    -------
        The turbidity value in centimeters.

    """
    # TODO: add wrapper
    # https://extension.usu.edu/utahwaterwatch/monitoring/field-instructions/
    # turbidity/turbiditytube/turbiditytubeconversionchart
    # Graphaed table conversions (average for each bound) and
    # used exponential curve (R2>.99)
    return 241.27 * (val**-0.662)


@u_reg.wraps(u_reg.NTU, u_reg.dimensionless)
def JTU_to_NTU(val):
    """Linear relationship, 1 -> 19, 0.053 -> 1, 0.4 -> 7.5 """
    # Alternative relation (Macneina 1990): NTU = JTU **0.943
    # from Maceina, M. J., & Soballe, D. M. (1990).
    #      Wind-related limnological variation in Lake Okeechobee, Florida.
    #      Lake and Reservoir Management, 6(1), 93-100.
    return 19.025*val - 0.0477


@u_reg.wraps(u_reg.NTU, u_reg.dimensionless)
def SiO2_to_NTU(val):
    """Linear relationship, 2.5 -> 19, 0.13 -> 1, 1 -> 7.5"""
    return 7.6028 * val - 0.0327


def FNU_to_NTU(val):
    return val * 1.267


@u_reg.wraps(u_reg.gram/u_reg.kilogram, (u_reg.gram/u_reg.liter,
                                         u_reg.standard_atmosphere,
                                         u_reg.degree_Celsius))
def density_to_PSU(val,
                   pressure=1*u_reg("atm"),
                   temperature=u_reg.Quantity(25, u_reg("degC"))):
    """
    Convert absolute salinity as density (mass/volume) to Practical Salinity
    Units

    Parameters
    ----------
    val : pint.quantity.build_quantity_class
        The salinty value in density units.
    pressure : pint.quantity.build_quantity_class, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : pint.quantity.build_quantity_class, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    PSU : pint.quantity.build_quantity_class
        The salinity value in dimensionless PSU.

    """
    # Standard Reference Value
    ref = 35.16504/35.0
    # density of pure water is ~1000 mg/mL
    if val > 1000:
        PSU = (float(val)*ref)-1000
    else:
        PSU = ((float(val)+1000)*ref)-1000
    # print('{} mg/ml == {} ppth'.format(val, PSU))
    # multiply by 33.45 @26C, 33.44 @25C

    return PSU


@u_reg.wraps(u_reg.milligram/u_reg.milliliter, (u_reg.dimensionless,
                                                u_reg.standard_atmosphere,
                                                u_reg.degree_Celsius))
def PSU_to_density(val,
                   pressure=1*u_reg("atm"),
                   temperature=u_reg.Quantity(25, u_reg("degC"))):
    """
    Convert salinity as Practical Salinity Units to density (mass/volume)


    Parameters
    ----------
    val : pint.Quanitity
        The salinty value in dimensionless PSU.
    pressure : pint.Quanitity, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : pint.Quanitity, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    density : pint.quantity.build_quantity_class
        The salinity value in density units (mg/ml).

    """
    p, t = pressure, temperature

    # Pure water density (see SMOW, Craig 1961)
    x = [999.842594,
         6.793952e-2 * t,
         -9.095290e-3 * t**2,
         1.001685e-4 * t**3,
         -1.120083e-6 * t**4,
         6.536336e-9 * t**5]
    pure_water = sum(x)

    # Constants
    a0 = [-4.0899e-3*t, 7.6438e-5*(t**2), -8.2467e-7*(t**3), 5.3875e-9*(t**4)]
    a = 8.24493e-1 + sum(a0)

    b0 = [-5.72466e-3, 1.0227e-4*t, -1.6546e-6*(t**2)]
    b = sum(b0)

    density = pure_water + a*val + b*(val**(3/2)) + 4.8314e-4*(val**2)

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


@u_reg.wraps(u_reg.milligram/u_reg.liter, (None,
                                           u_reg.standard_atmosphere,
                                           u_reg.degree_Celsius))
def DO_saturation(val,
                  pressure=1*u_reg("atm"),
                  temperature=u_reg.Quantity(25, u_reg("degC"))):
    """
    Convert Dissolved Oxygen as percent saturation (%) to mg/l concentration.
    Defaults assume STP where pressure is 1 atmosphere and temperature 25C.

    Parameters
    ----------
    val : pint.quantity.build_quantity_class
        The Dissolved Oxygen saturation value in dimensionless percent.
    pressure : pint.Quanitity, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : pint.Quanitity, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    pint.Quantity
        Value in mg/l.

    """
    p, t = pressure, temperature
    if p == 1 & (t == 25):
        Cp = 8.262332418
    else:
        Pwv = 11.8571-(3840.7/(t+273.15))-(216961/((t+273.15)**2))
    # CP =((EXP(7.7117-1.31403*LN(t+45.93)))* P *
    #      (1-EXP(Pwv)/p) *
    #      (1-(0.000975-(0.00001426*t)+(0.00000006436*(t**2)))*p)) /
    #     (1-EXP(Pwv))/(1-(0.000975-(0.00001426*t)+(0.00000006436*(t**2))))
    return float(val) * Cp  # Divide by 100?


@u_reg.wraps(None, (u_reg.milligram/u_reg.liter,
                    u_reg.standard_atmosphere,
                    u_reg.degree_Celsius))
def DO_concentration(val,
                     pressure=1*u_reg("atm"),
                     temperature=u_reg.Quantity(25, u_reg("degC"))):
    """
    Convert Dissolved Oxygen from concentration (e.g., mg/ml) to saturation (%)

    Parameters
    ----------
    val : pint.quantity.build_quantity_class
        The DO value (converted to mg/L)
    pressure : pint.Quanitity, optional
        The pressure value. The default is 1*ureg("atm").
    temperature : TYPE, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    float
        Dissolved Oxygen as saturation (dimensionless).

    """
    # TODO: switch to kelvin?
    # https://www.waterontheweb.org/under/waterquality/oxygen.html#:~:
    # text=Oxygen%20saturation%20is%20calculated%20as,
    # concentration%20at%20100%25%20saturation%20decreases.
    p, t = pressure, temperature
    standard = 0.000975 - (0.00001426*t) + (0.00000006436*(t**2))
    numerator = ((1-Pwv)/p)*(1-(standard*p))
    denominator = (1-Pwv)*(1-standard)
    Cp = C0*p(numerator/denominator)
    return (100*val)/Cp


@u_reg.wraps(u_reg.dimensionless, (u_reg.microsiemens / u_reg.centimeter,
                                   u_reg.standard_atmosphere,
                                   u_reg.degree_Celsius))
def conductivity_to_PSU(val,
                        pressure=0*u_reg("atm"),
                        temperature=u_reg.Quantity(25, u_reg("degC"))):
    """
    Estimate salinity (PSU) from conductivity

    Parameters
    ----------
    val : pint.quantity.build_quantity_class
        The conductivity value (converted to microsiemens / centimeter)
    pressure : pint.Quanitity, optional
        The pressure value. The default is 0*ureg("atm").
    temperature : TYPE, optional
        The temperature value. The default is ureg.Quantity(25, ureg("degC")).

    Returns
    -------
    pint.Quantity
        Estimated salinity (PSU).

    Additional Notes:
    Conductivity to salinity conversion PSS 1978 method
    c-numeric conducitivity in uS (microseimens).
    t-numeric celcius temperature (defauls to 25)
    P-numeric optional pressure (defaults to 0)

    References:
    IOC, SCOR and IAPSO, 2010: The international thermodynamic
        equation of seawater – 2010: Calculation and use of thermodynamic
        properties. Intergovernmental Oceanographic Commission, Manuals
        and Guides No. 56, UNESCO (English), 196 pp

    code: Alan D. Jassby and James E. Cloern (2015). wq: Some tools for
                exploring water quality monitoring data. R package v0.4.4.
                See the wq::ec2pss function.
    Function: https://github.com/jsta/cond2sal_shiny/blob/master/helpers.R
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
    R = (Ct/1000)/42.914
    # Was rt
    c = c[0] + (c[1] * t) + (c[2] * t**2) + (c[3] * t**3) + (c[4] * t**4)

    Rp = (1 + (p * e[0] + e[1] * p**2 + e[2] * p**3) /
          (1 + D[0] * t + D[1] * t**2 + (D[2] + D[3] * t) * R))
    Rt1 = R/(Rp * c)
    dS = ((b[0] + b[1] * Rt1**(1/2) +
           b[2] * Rt1**(2/2) +
           b[3] * Rt1**(3/2) +
           b[4] * Rt1**(4/2) +
           b[5] * Rt1**(5/2)) *
          (t - 15)/(1 + K * (t - 15)))
    S = (a[0] + a[1] * Rt1**(1/2) +
         a[2] * Rt1**(2/2) + a[3] * Rt1**(3/2) +
         a[4] * Rt1**(4/2) + a[5] * Rt1**(5/2) + dS)

    # TODO: implement these two lines? Shouldn't encounter NaN.
    # S[is.na(S<0)]<-NA  # if <0 or NA set as nan
    # S[S<2 & !is.na(S)]<- S[S<2 & !is.na(S)] - a[0]/(1 + 1.5 * (400 * Rt1) +
    # (400 * Rt1)**2) - (b[0] * (t - 15)/(1 + K * (t - 15)))/
    # (1 + (100 * Rt1)**(1/2) + (100 * Rt1)**(3/2))
    # S = S - a[0]/(1 + 1.5 * (400 * Rt1) + (400 * Rt1)**2) - (b[0] * (t - 15)/
    # (1 + K * (t - 15)))/(1 + (100 * Rt1)**(1/2) + (100 * Rt1)**(3/2))

    return round(S, 3)
