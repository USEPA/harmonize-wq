# -*- coding: utf-8 -*-
"""Functions to return domain lists with all potential values.

These are mainly for use as filters. Small or frequently utilized domains may
be hard-coded. A URL based method can be used to get the most up to date domain
list.

Attributes
----------
accepted_methods : dict
  Get accepted methods for each characteristic. Dictionary where key is
  characteristic column name and value is list of dictionaries each with Source
  and Method keys.

  Notes
  -----
  Source should be in 'ResultAnalyticalMethod/MethodIdentifierContext'
  column. This is not fully implemented.

stations_rename : dict
  Get shortened column names for shapefile (.shp) fields.

  Dictionary where key = WQP field name and value = short name for .shp.

  ESRI places a length restriction on shapefile (.shp) field names. This
  returns a dictionary with the original water quality portal field name (as
  key) and shortened column name for writing as .shp. We suggest using the
  longer original name as the field alias when writing as .shp.

  Examples
  --------
  Although running the function returns the full dictionary of Key:Value
  pairs, here we show how the current name can be used as a key to get the
  new name:

  >>> domains.stations_rename['OrganizationIdentifier']
  'org_ID'

xy_datum : dict

  Get dictionary of expected horizontal datums, where exhaustive:
          {HorizontalCoordinateReferenceSystemDatumName: {Description:str,
          EPSG:int}}

  The structure has {key as expected string: value as {"Description": string
  and "EPSG": integer (4-digit code)}.

  Notes
  -----
  source WQP: HorizontalCoordinateReferenceSystemDatum_CSV.zip

  Anything not in dict will be NaN, and non-integer EPSG will be missing:
  "OTHER": {"Description": 'Other', "EPSG": nan},
  "UNKWN": {"Description": 'Unknown', "EPSG": nan}

  Examples
  --------
  Running the function returns the full dictionary with {abbreviation:
  {'Description':values, 'EPSG':values}}. The abbreviation key can be used to
  get the EPSG code:

  >>> domains.xy_datum['NAD83']
  {'Description': 'North American Datum 1983', 'EPSG': 4269}
  >>> domains.xy_datum['NAD83']['EPSG']
  4269
"""

import pandas
import requests

BASE_URL = "https://cdx.epa.gov/wqx/download/DomainValues/"
TADA_DATA_URL = "https://raw.githubusercontent.com/USEPA/EPATADA/"

UNITS_REPLACE = {
    "Secchi": {},
    "DO": {"%": "percent"},
    "Temperature": {},
    "Salinity": {"ppt": "ppth", "0/00": "ppth"},
    "pH": {"None": "dimensionless", "std units": "dimensionless"},
    "Nitrogen": {"cm3/g @STP": "cm3/g", "cm3/g STP": "cm3/g", "%": "percent"},
    "Conductivity": {"uS": "uS/cm", "umho": "umho/cm"},
    "Carbon": {"% by wt": "%", "%": "percent"},
    "Chlorophyll": {
        "mg/cm3": "mg/cm**3",
        "mg/m3": "mg/m**3",
        "mg/m2": "mg/m**3",
        "ug/cm3": "ug/cm**3",
    },
    "Turbidity": {"mg/l SiO2": "SiO2", "ppm SiO2": "SiO2"},
    "Sediment": {"%": "percent"},
    "Fecal_Coliform": {
        "#/100ml": "CFU/(100ml)",
        "CFU": "CFU/(100ml)",
        "MPN": "MPN/(100ml)",
    },
    "E_coli": {"#/100ml": "CFU/(100ml)", "CFU": "CFU/(100ml)", "MPN": "MPN/(100ml)"},
    "Phosphorus": {"%": "percent"},
}

OUT_UNITS = {
    "Secchi": "m",
    "DO": "mg/l",
    "Temperature": "degC",
    "Salinity": "PSU",
    "pH": "dimensionless",
    "Nitrogen": "mg/l",
    "Conductivity": "uS/cm",
    "Carbon": "mg/l",
    "Chlorophyll": "mg/l",
    "Turbidity": "NTU",
    "Sediment": "g/kg",
    "Fecal_Coliform": "CFU/(100ml)",
    "E_coli": "CFU/(100ml)",
    "Phosphorus": "mg/l",
}

# Temporary (these are confirmed)
domain_tables = {
    "ActivityMedia": "ActivityMedia_CSV",
    "SampleFraction": "ResultSampleFraction_CSV",
    "ActivityMediaSubdivision": "ActivityMediaSubdivision_CSV",
    "ResultValueType": "ResultValueType_CSV",
}
# Replaces:
# get_ActivityMediaName():
# get_SampleFraction():
# get_ActivityMediaSubdivisionName():
# get_ResultValueTypeName():
# get_domain_list(field):


def get_domain_dict(table, cols=None):
    """Get domain values for specified table.

    Parameters
    ----------
    table : str
        csv table name (without extension).
    cols : list, optional
        Columns to use as {key, value}.
        The default is None, ['Name', 'Description'].

    Returns
    -------
    dict
        Dictionary where {cols[0]: cols[1]}

    Examples
    --------
    Return dictionary for domain from WQP table (e.g., 'ResultSampleFraction'),
    The default keys ('Name') are shown as values ('Description') are long:

    >>> from harmonize_wq import domains
    >>> domains.get_domain_dict('ResultSampleFraction').keys() # doctest: +NORMALIZE_WHITESPACE
    dict_keys(['Acid Soluble', 'Bed Sediment', 'Bedload', 'Bioavailable', 'Comb Available',
               'Dissolved', 'Extractable', 'Extractable, CaCO3-bound', 'Extractable, exchangeable',
               'Extractable, organic-bnd', 'Extractable, other', 'Extractable, oxide-bound',
               'Extractable, residual', 'Field***', 'Filter/sieve residue', 'Filterable',
               'Filtered field and/or lab', 'Filtered, field', 'Filtered, lab',
               'Fixed', 'Free Available', 'Inorganic', 'Leachable', 'Net (Hot)',
               'Non-Filterable (Particle)', 'Non-settleable', 'Non-volatile',
               'None', 'Organic', 'Pot. Dissolved', 'Semivolatile', 'Settleable',
               'Sieved', 'Strong Acid Diss', 'Supernate', 'Suspended', 'Total',
               'Total Recoverable', 'Total Residual', 'Total Soluble',
               'Unfiltered', 'Unfiltered, field', 'Vapor', 'Volatile',
               'Weak Acid Diss', 'Yield', 'non-linear function'])
    """  # noqa: E501
    if cols is None:
        cols = ["Name", "Description"]
    if not table.endswith("_CSV"):
        table += "_CSV"
    url = f"{BASE_URL}{table}.zip"
    # Very limited url handling
    if requests.get(url).status_code != 200:
        status_code = requests.get(url).status_code
        print(f"{url} web service response {status_code}")
    df = pandas.read_csv(url, usecols=cols)
    return dict(df.values)


def harmonize_TADA_dict():
    """Get structured dictionary from TADA HarmonizationTemplate csv.

    Based on target column names and sample fractions.

    Returns
    -------
    full_dict : dict
        {'TADA.CharacteristicName':
         {Target.TADA.CharacteristicName:
          {Target.TADA.ResultSampleFractionText :
           [Target.TADA.ResultSampleFractionText]}}}
    """
    # Note: too nested for refactor into single function w/ char_tbl_TADA

    # Read from github
    csv = f"{TADA_DATA_URL}develop/inst/extdata/HarmonizationTemplate.csv"
    df = pandas.read_csv(csv)  # Read csv url to DataFrame
    full_dict = {}  # Setup results dict
    # Build dict one unique characteristicName at a time
    for char, sub_df in df.groupby("TADA.CharacteristicName"):
        full_dict[char] = char_tbl_TADA(sub_df, char)  # Build dictionary

    # Domains to check agaisnt
    domain_list = list(get_domain_dict("ResultSampleFraction").keys())

    # Update in/out with expected sample Fraction case
    for k_char, v_char in full_dict.items():
        for k_target, v_target in v_char.items():
            new_target = {}
            for k_sf, v_sf in v_target.items():
                # re-case new keys
                new_k_sf = re_case(k_sf, domain_list)
                # re-case old values
                new_v_sf = [re_case(x, domain_list) for x in v_sf]
                new_target[new_k_sf] = new_v_sf
            # Replace old smaple fraction dict with new using keys
            full_dict[k_char][k_target] = new_target

    return full_dict


def re_case(word, domain_list):
    """Change instance of word in domain_list to UPPERCASE.

    Parameters
    ----------
    word : str
        Word to alter in domain_list.
    domain_list : list
        List including word.

    Returns
    -------
    str
        Word from domain_list in UPPERCASE.
    """
    domain_list_upper = [x.upper() for x in domain_list]
    try:
        idx = domain_list_upper.index(word)
    except ValueError:
        return word
    return domain_list[idx]


def char_tbl_TADA(df, char):
    """Get structured dictionary for TADA.CharacteristicName from TADA df.

    Parameters
    ----------
    df : pandas.DataFrame
        Table from TADA for specific characteristic.
    char : str
        CharacteristicName.

    Returns
    -------
    new_char_dict : dict
        Returned dictionary follows general structure:
            {
                "Target.TADA.CharacteristicName": {
                    "Target.TADA.ResultSampleFractionText": [
                        "Target.TADA.ResultSampleFractionText"
                    ]
                }
            }
    """
    cols = [
        "Target.TADA.CharacteristicName",
        "TADA.ResultSampleFractionText",
        "Target.TADA.ResultSampleFractionText",
    ]
    sub_df = df[cols].drop_duplicates()  # TODO: superfluous?

    # Update Output/target columns
    sub_df[cols[0]] = sub_df[cols[0]].fillna(char)  # new_char
    sub_df[cols[2]] = sub_df[cols[2]].fillna(sub_df[cols[1]])  # new_fract

    sub_df.drop_duplicates(inplace=True)

    # loop over new chars, getting {new_fract: [old fracts]}
    new_char_dict = {}
    for new_char in sub_df[cols[0]].unique():
        new_char_df = sub_df[sub_df[cols[0]] == new_char]  # Mask by new_char
        new_fract_dict = {}
        for new_fract in new_char_df[cols[2]].unique():
            # TODO: {nan: []}? Doesn't break but needs handling later
            # Mask by new_fract
            new_fract_df = new_char_df[new_char_df[cols[2]] == new_fract]
            # Add a list of possible old_fract for new_fract key
            new_fract_dict[new_fract] = new_fract_df[cols[1]].unique()
        new_char_dict[new_char] = new_fract_dict

    return new_char_dict


def registry_adds_list(out_col):
    """Get units to add to :mod:`pint` unit registry by out_col column.

    Typically out_col refers back to column used for a value from the
    'CharacteristicName' column.

    Parameters
    ----------
    out_col : str
        The result column a unit registry is being built for.

    Returns
    -------
    list
        List of strings with unit additions in expected format.

    Examples
    --------
    Generate a new pint unit registry object for e.g., Sediment:

    >>> from harmonize_wq import domains
    >>> domains.registry_adds_list('Sediment')  # doctest: +NORMALIZE_WHITESPACE
    ['fraction = [] = frac',
     'percent = 1e-2 frac',
     'parts_per_thousand = 1e-3 = ppth',
     'parts_per_million = 1e-6 fraction = ppm']
    """
    # TODO: 'PSU' = 'PSS' ~ ppth/1.004715

    # define is 1% (0.08s) slower than replacement (ppm->mg/l) but more robust
    # Standard pint unit registry additions for dimensionless portions
    pct_list = [
        "fraction = [] = frac",
        "percent = 1e-2 frac",
        "parts_per_thousand = 1e-3 = ppth",
        "parts_per_million = 1e-6 fraction = ppm",
    ]
    # Standard pint unit registry additions for dimensionless bacteria units
    bacteria_list = [
        "Colony_Forming_Units = [] = CFU = cfu",
        "Most_Probable_Number = CFU = MPN = mpn",
    ]
    # characteristic based dict
    ureg_adds = {
        "Secchi": [],
        "DO": pct_list,
        "Temperature": [],
        "Salinity": pct_list + ["Practical_Salinity_Units = ppth = PSU = PSS"],
        "pH": [],
        "Nitrogen": [],
        "Conductivity": [],
        "Carbon": pct_list,
        "Chlorophyll": [],
        "Turbidity": [
            "Nephelometric_Turbidity_Units = [turbidity] = NTU",
            "Nephelometric_Turbidity_Ratio_Units = NTU = NTRU",
            "Nephelometric_Turbidity_Multibeam_Units = NTU = NTMU",
            "Formazin_Nephelometric_Units = NTU = FNU",
            "Formazin_Nephelometric_Ratio_Units = FNRU = FNU",
            "Formazin_Turbidity_Units = NTU = FNU = FTU = FAU",
            "Jackson_Turbidity_Units = [] = JTU",
            "SiO2 = []",
        ],
        "Sediment": pct_list,
        "Fecal_Coliform": bacteria_list,
        "E_coli": bacteria_list,
        "Phosphorus": [],
    }
    return ureg_adds[out_col]


"""Get {CharacteristicName: out_column_name}.

This is often subset and used to write results to a new column from the
'CharacteristicName' column.

Returns
-------
dict
    {WQP CharacteristicName:Column Name}.

Examples
--------
The function returns the full dictionary {CharacteristicName: out_column_name}.
It can be subset by a 'CharactisticName' column value to get the name of
the column for results:

>>> domains.out_col_lookup['Escherichia coli']
'E_coli'
"""
# TODO: something special for phosphorus? Currently return suffix.
# 'Phosphorus' -> ['TP_Phosphorus', 'TDP_Phosphorus', 'Other_Phosphorus']
out_col_lookup = {
    "Depth, Secchi disk depth": "Secchi",
    "Dissolved oxygen (DO)": "DO",
    "Temperature, water": "Temperature",
    "Salinity": "Salinity",
    "pH": "pH",
    "Nitrogen": "Nitrogen",
    "Conductivity": "Conductivity",
    "Organic carbon": "Carbon",
    "Chlorophyll a": "Chlorophyll",
    "Turbidity": "Turbidity",
    "Sediment": "Sediment",
    "Fecal Coliform": "Fecal_Coliform",
    "Escherichia coli": "E_coli",
    "Phosphorus": "Phosphorus",
}


def characteristic_cols(category=None):
    """Get characteristic specific columns list, can subset those by category.

    Parameters
    ----------
    category : str, optional
        Subset results: 'Basis', 'Bio', 'Depth', 'QA', 'activity', 'analysis',
        'depth', 'measure', 'sample'.
        The default is None.

    Returns
    -------
    col_list : list
        List of columns.

    Examples
    --------
    Running the function without a category returns the full list of column
    names, including a category returns only the columns in that category:

    >>> domains.characteristic_cols('QA')  # doctest: +NORMALIZE_WHITESPACE
    ['ResultDetectionConditionText', 'ResultStatusIdentifier', 'PrecisionValue',
     'DataQuality/BiasValue', 'ConfidenceIntervalValue', 'UpperConfidenceLimitValue',
     'LowerConfidenceLimitValue', 'ResultCommentText', 'ResultSamplingPointName',
     'ResultDetectionQuantitationLimitUrl']
    """
    cols = {
        "ActivityStartDate": "activity",
        "ActivityStartTime/Time": "activity",
        "ActivityStartTime/TimeZoneCode": "activity",
        "DataLoggerLine": "measure",
        "ResultDetectionConditionText": "QA",
        "MethodSpecificationName": "measure",
        "CharacteristicName": "measure",
        "ResultSampleFractionText": "measure",
        "ResultMeasureValue": "measure",
        "ResultMeasure/MeasureUnitCode": "measure",
        "MeasureQualifierCode": "measure",
        "ResultStatusIdentifier": "QA",
        "ResultIdentifier": "measure",
        "StatisticalBaseCode": "measure",
        "ResultValueTypeName": "measure",
        "ResultWeightBasisText": "Basis",
        "ResultTimeBasisText": "Basis",
        "ResultTemperatureBasisText": "Basis",
        "ResultParticleSizeBasisText": "Basis",
        "PrecisionValue": "QA",
        "DataQuality/BiasValue": "QA",
        "ConfidenceIntervalValue": "QA",
        "UpperConfidenceLimitValue": "QA",
        "LowerConfidenceLimitValue": "QA",
        "ResultCommentText": "QA",
        "USGSPCode": "measure",
        "ResultDepthHeightMeasure/MeasureValue": "Depth",
        "ResultDepthHeightMeasure/MeasureUnitCode": "Depth",
        "ResultDepthAltitudeReferencePointText": "Depth",
        "ResultSamplingPointName": "QA",
        "BiologicalIntentName": "Bio",
        "BiologicalIndividualIdentifier": "BIO",
        "SubjectTaxonomicName": "Bio",
        "UnidentifiedSpeciesIdentifier": "BIO",
        "SampleTissueAnatomyName": "Bio",
        "GroupSummaryCountWeight/MeasureValue": "Bio",
        "GroupSummaryCountWeight/MeasureUnitCode": "Bio",
        "CellFormName": "Bio",
        "CellShapeName": "Bio",
        "HabitName": "Bio",
        "VoltismName": "Bio",
        "TaxonomicPollutionTolerance": "Bio",
        "TaxonomicPollutionToleranceScaleText": "Bio",
        "TrophicLevelName": "Bio",
        "FunctionalFeedingGroupName": "Bio",
        "TaxonomicDetailsCitation/ResourceTitleName": "Bio",
        "TaxonomicDetailsCitation/ResourceCreatorName": "Bio",
        "TaxonomicDetailsCitation/ResourceSubjectText": "Bio",
        "TaxonomicDetailsCitation/ResourcePublisherName": "Bio",
        "TaxonomicDetailsCitation/ResourceDate": "Bio",
        "TaxonomicDetailsCitation/ResourceIdentifier": "Bio",
        "FrequencyClassInformationUrl": "Bio",
        "ResultAnalyticalMethod/MethodIdentifier": "measure",
        "ResultAnalyticalMethod/MethodIdentifierContext": "measure",
        "ResultAnalyticalMethod/MethodName": "measure",
        "ResultAnalyticalMethod/MethodUrl": "measure",
        "ResultAnalyticalMethod/MethodQualifierTypeName": "measure",
        "MethodDescriptionText": "measure",
        "LaboratoryName": "analysis",
        "AnalysisStartDate": "analysis",
        "AnalysisStartTime/Time": "analysis",
        "AnalysisStartTime/TimeZoneCode": "analysis",
        "AnalysisEndDate": "analysis",
        "AnalysisEndTime/Time": "analysis",
        "AnalysisEndTime/TimeZoneCode": "analysis",
        "ResultLaboratoryCommentCode": "analysis",
        "ResultLaboratoryCommentText": "analysis",
        "ResultDetectionQuantitationLimitUrl": "QA",
        "LaboratoryAccreditationIndicator": "analysis",
        "LaboratoryAccreditationAuthorityName": "analysis",
        "TaxonomistAccreditationIndicator": "analysis",
        "TaxonomistAccreditationAuthorityName": "analysis",
        "LabSamplePreparationUrl": "analysis",
        "ActivityTypeCode": "activity",
        "ActivityMediaName": "activity",
        "ActivityMediaSubdivisionName": "activity",
        "ActivityEndDate": "activity",
        "ActivityEndTime/Time": "activity",
        "ActivityEndTime/TimeZoneCode": "activity",
        "ActivityRelativeDepthName": "depth",
        "ActivityDepthHeightMeasure/MeasureValue": "depth",
        "ActivityDepthHeightMeasure/MeasureUnitCode": "depth",
        "ActivityDepthAltitudeReferencePointText": "depth",
        "ActivityTopDepthHeightMeasure/MeasureValue": "depth",
        "ActivityTopDepthHeightMeasure/MeasureUnitCode": "depth",
        "ActivityBottomDepthHeightMeasure/MeasureValue": "depth",
        "ActivityBottomDepthHeightMeasure/MeasureUnitCode": "depth",
        "ActivityConductingOrganizationText": "activity",
        "ActivityCommentText": "activity",
        "SampleAquifer": "activity",
        "HydrologicCondition": "activity",
        "HydrologicEvent": "activity",
        "ActivityLocation/LatitudeMeasure": "activity",
        "ActivityLocation/LongitudeMeasure": "activity",
        "ActivityLocation/SourceMapScaleNumeric": "activity",
        "ActivityLocation/HorizontalAccuracyMeasure/MeasureValue": "activity",
        "ActivityLocation/HorizontalAccuracyMeasure/MeasureUnitCode": "activity",
        "ActivityLocation/HorizontalCollectionMethodName": "activity",
        "ActivityLocation/HorizontalCoordinateReferenceSystemDatumName": "activity",
        "AssemblageSampledName": "sample",
        "CollectionDuration/MeasureValue": "sample",
        "CollectionDuration/MeasureUnitCode": "sample",
        "SamplingComponentName": "sample",
        "SamplingComponentPlaceInSeriesNumeric": "sample",
        "ReachLengthMeasure/MeasureValue": "sample",
        "ReachLengthMeasure/MeasureUnitCode": "sample",
        "ReachWidthMeasure/MeasureValue": "sample",
        "ReachWidthMeasure/MeasureUnitCode": "sample",
        "PassCount": "sample",
        "NetTypeName": "sample",
        "NetSurfaceAreaMeasure/MeasureValue": "sample",
        "NetSurfaceAreaMeasure/MeasureUnitCode": "sample",
        "NetMeshSizeMeasure/MeasureValue": "sample",
        "NetMeshSizeMeasure/MeasureUnitCode": "sample",
        "BoatSpeedMeasure/MeasureValue": "sample",
        "BoatSpeedMeasure/MeasureUnitCode": "sample",
        "CurrentSpeedMeasure/MeasureValue": "sample",
        "CurrentSpeedMeasure/MeasureUnitCode": "sample",
        "ToxicityTestType": "analysis",
        "SampleCollectionMethod/MethodIdentifier": "sample",
        "SampleCollectionMethod/MethodIdentifierContext": "sample",
        "SampleCollectionMethod/MethodName": "sample",
        "SampleCollectionMethod/MethodQualifierTypeName": "sample",
        "SampleCollectionMethod/MethodDescriptionText": "sample",
        "SampleCollectionEquipmentName": "sample",
        "SampleCollectionMethod/SampleCollectionEquipmentCommentText": "sample",
        "SamplePreparationMethod/MethodIdentifier": "sample",
        "SamplePreparationMethod/MethodIdentifierContext": "sample",
        "SamplePreparationMethod/MethodName": "sample",
        "SamplePreparationMethod/MethodQualifierTypeName": "sample",
        "SamplePreparationMethod/MethodDescriptionText": "sample",
        "SampleContainerTypeName": "sample",
        "SampleContainerColorName": "sample",
        "ChemicalPreservativeUsedName": "analysis",
        "ThermalPreservativeUsedName": "analysis",
        "SampleTransportStorageDescription": "analysis",
        "ActivityMetricUrl": "activity",
        "PreparationStartDate": "analysis",
    }
    if category:
        # List of key where value is category
        col_list = [key for key, value in cols.items() if value == category]
    else:
        col_list = list(cols.keys())  # All keys/cols
    return col_list


xy_datum = {
    "NAD27": {"Description": "North American Datum 1927", "EPSG": 4267},
    "NAD83": {"Description": "North American Datum 1983", "EPSG": 4269},
    "AMSMA": {"Description": "American Samoa Datum", "EPSG": 4169},
    "ASTRO": {"Description": "Midway Astro 1961", "EPSG": 4727},
    "GUAM": {"Description": "Guam 1963", "EPSG": 4675},
    "JHNSN": {"Description": "Johnson Island 1961", "EPSG": 4725},
    "OLDHI": {"Description": "Old Hawaiian Datum", "EPSG": 4135},
    "PR": {"Description": "Puerto Rico Datum", "EPSG": 6139},
    "SGEOR": {"Description": "St. George Island Datum", "EPSG": 4138},
    "SLAWR": {"Description": "St. Lawrence Island Datum", "EPSG": 4136},
    "SPAUL": {"Description": "St. Paul Island Datum", "EPSG": 4137},
    "WAKE": {"Description": "Wake-Eniwetok 1960", "EPSG": 6732},
    "WGS72": {"Description": "World Geodetic System 1972", "EPSG": 6322},
    "WGS84": {"Description": "World Geodetic System 1984", "EPSG": 4326},
    "HARN": {
        "Description": "High Accuracy Reference Network for NAD83",
        "EPSG": 4152,
    },
}

#     Default field mapping writes full name to alias but a short name to field
stations_rename = {
    "OrganizationIdentifier": "org_ID",
    "OrganizationFormalName": "org_name",
    "MonitoringLocationIdentifier": "loc_ID",
    "MonitoringLocationName": "loc_name",
    "MonitoringLocationTypeName": "loc_type",
    "MonitoringLocationDescriptionText": "loc_desc",
    "HUCEightDigitCode": "HUC08_code",
    "DrainageAreaMeasure/MeasureValue": "DA_val",
    "DrainageAreaMeasure/MeasureUnitCode": "DA_unit",
    "ContributingDrainageAreaMeasure/MeasureValue": "CA_val",
    "ContributingDrainageAreaMeasure/MeasureUnitCode": "CA_unit",
    "LatitudeMeasure": "Latitude",
    "LongitudeMeasure": "Longitude",
    "SourceMapScaleNumeric": "SRC_Scale",
    "HorizontalAccuracyMeasure/MeasureValue": "xy_acc",
    "HorizontalAccuracyMeasure/MeasureUnitCode": "xy_accUnit",
    "HorizontalCollectionMethodName": "xy_method",
    "HorizontalCoordinateReferenceSystemDatumName": "xy_datum",
    "VerticalMeasure/MeasureValue": "z",
    "VerticalMeasure/MeasureUnitCode": "z_unit",
    "VerticalAccuracyMeasure/MeasureValue": "z_acc",
    "VerticalAccuracyMeasure/MeasureUnitCode": "z_accUnit",
    "VerticalCollectionMethodName": "z_method",
    "VerticalCoordinateReferenceSystemDatumName": "z_datum",
    "CountryCode": "country",
    "StateCode": "state",
    "CountyCode": "county",
    "AquiferName": "aquifer",
    "FormationTypeText": "form_type",
    "AquiferTypeName": "aquiferType",
    "ConstructionDateText": "constrDate",
    "WellDepthMeasure/MeasureValue": "well_depth",
    "WellDepthMeasure/MeasureUnitCode": "well_unit",
    "WellHoleDepthMeasure/MeasureValue": "wellhole",
    "WellHoleDepthMeasure/MeasureUnitCode": "wellHole_unit",
    "ProviderName": "provider",
    "ActivityIdentifier": "activity_ID",
    "ResultIdentifier": "result_ID",
}

accepted_methods = {
    "Secchi": [
        {"Source": "APHA", "Method": "2320-B"},
        {"Source": "ASTM", "Method": "D1889"},
        {"Source": "USEPA", "Method": "NRSA09 W QUAL (BOAT)"},
        {"Source": "USEPA", "Method": "841-B-11-003"},
    ],
    "DO": [
        {"Source": "USEPA", "Method": "360.2"},
        {"Source": "USEPA", "Method": "130.1"},
        {"Source": "APHA", "Method": "4500-O-G"},
        {"Source": "USEPA", "Method": "160.3"},
        {"Source": "AOAC", "Method": "973.45"},
        {"Source": "USDOI/USGS", "Method": "I-1576-78"},
        {"Source": "USDOI/USGS", "Method": "NFM 6.2.1-LUM"},
        {"Source": "ASTM", "Method": "D888(B)"},
        {"Source": "HACH", "Method": "8157"},
        {"Source": "HACH", "Method": "10360"},
        {"Source": "ASTM", "Method": "D3858"},
        {"Source": "ASTM", "Method": "D888(C)"},
        {"Source": "APHA", "Method": "	4500-O-C"},
        {"Source": "USEPA", "Method": "1002-8-2009"},
        {"Source": "APHA", "Method": "2550"},
        {"Source": "USEPA", "Method": "360.1"},
        {"Source": "USEPA", "Method": "841-B-11-003"},
        {"Source": "ASTM", "Method": "D888-12"},
        {"Source": "YSI", "Method": "EXO WQ SONDE"},
    ],
    "Temperature": [
        {"Source": "USEPA", "Method": "170.1"},
        {"Source": "USEPA", "Method": "130.1"},
        {"Source": "USEPA", "Method": "841-B-11-003"},
        {"Source": "APHA", "Method": "2550"},
        {"Source": "YSI", "Method": "EXO WQ SONDE"},
        {"Source": "APHA", "Method": "2550 B"},
    ],
    "Salinity": [
        {"Source": "YSI", "Method": "EXO WQ SONDE"},
        {"Source": "HACH", "Method": "8160"},
        {"Source": "APHA", "Method": "2520-B"},
        {"Source": "APHA", "Method": "2130"},
        {"Source": "APHA", "Method": "3.2-B"},
        {"Source": "APHA", "Method": "2520-C"},
    ],
    "pH": [
        {"Source": "ASTM", "Method": "D1293(B)"},
        {"Source": "YSI", "Method": "EXO WQ SONDE"},
        {"Source": "USEPA", "Method": "360.2"},
        {"Source": "USEPA", "Method": "130.1"},
        {"Source": "USDOI/USGS", "Method": "I1586"},
        {"Source": "USDOI/USGS", "Method": "I-2587-85"},
        {"Source": "APHA", "Method": "3.2-B"},
        {"Source": "HACH", "Method": "8219"},
        {"Source": "AOAC", "Method": "973.41"},
        {"Source": "APHA", "Method": "4500-H"},
        {"Source": "APHA", "Method": "2320"},
        {"Source": "USEPA", "Method": "150.2"},
        {"Source": "USEPA", "Method": "150.1"},
        {"Source": "USDOI/USGS", "Method": "I-1586-85"},
        {"Source": "USEPA", "Method": "9040B"},
        {"Source": "HACH", "Method": "8156"},
        {"Source": "ASTM", "Method": "D1293(A)"},
        {"Source": "APHA", "Method": "4500-H+B"},
    ],
    "Nitrogen": [
        {"Source": "USEPA", "Method": "353.1"},
        {"Source": "USEPA", "Method": "353.2"},
        {"Source": "USEPA", "Method": "353.2_M"},
        {"Source": "USEPA", "Method": "353.3"},
        {"Source": "USEPA", "Method": "6020"},
        {"Source": "USEPA", "Method": "200.7"},
        {"Source": "USEPA", "Method": "8321"},
        {"Source": "USEPA", "Method": "365.1"},
        {"Source": "USEPA", "Method": "365.3"},
        {"Source": "USEPA", "Method": "300"},
        {"Source": "USEPA", "Method": "300(A)"},
        {"Source": "USEPA", "Method": "350.1"},
        {"Source": "USEPA", "Method": "350.3"},
        {"Source": "USEPA", "Method": "351.1"},
        {"Source": "USEPA", "Method": "351.2"},
        {"Source": "USEPA", "Method": "351.3 (TITRATION)"},
        {"Source": "USEPA", "Method": "440"},
        {"Source": "USEPA", "Method": "440(W)"},
        {"Source": "USEPA", "Method": "440(S)"},
        {"Source": "AOAC", "Method": "973.48"},
        {"Source": "USDOI/USGS", "Method": "I-4650-03"},
        {"Source": "USDOI/USGS", "Method": "I-2650-03"},
        {"Source": "USDOI/USGS", "Method": "I-4540-85"},
        {"Source": "ASTM", "Method": "D8083-16"},
        {"Source": "ASTM", "Method": "D5176"},
        {"Source": "ASTM", "Method": "D888(B)"},
        {"Source": "ASTM", "Method": "D3590(B)"},
        {"Source": "HACH", "Method": "10208"},
        {"Source": "HACH", "Method": "10071"},
        {"Source": "HACH", "Method": "10072"},
        {"Source": "HACH", "Method": "10242"},
        {"Source": "USDOE/ASD", "Method": "MS100"},
        {"Source": "LACHAT", "Method": "31-107-04-3-A"},
        {"Source": "LACHAT", "Method": "31-107-04-4-A"},
        {"Source": "BL", "Method": "818-87T"},
        {"Source": "APHA_SM20ED", "Method": "4500-N-C"},
        {"Source": "APHA_SM21ED", "Method": "4500-N-B"},
        {"Source": "APHA", "Method": "4500-N D"},
        {"Source": "APHA", "Method": "4500-N"},
        {"Source": "APHA", "Method": "4500-NOR(C)"},
        {"Source": "APHA", "Method": "4500-NH3 B"},
        {"Source": "APHA", "Method": "4500-NH3 D"},
        {"Source": "APHA", "Method": "4500-NH3(G)"},
        {"Source": "APHA", "Method": "4500-NH3(H)"},
        {"Source": "APHA", "Method": "4500-NO3(C)"},
        {"Source": "APHA", "Method": "4500-NO3(B)"},
        {"Source": "APHA", "Method": "4500-NO3(E)"},
        {"Source": "APHA", "Method": "4500-NO3(I)"},
        {"Source": "APHA", "Method": "4500-NO3(F)"},
        {"Source": "APHA", "Method": "4500-NOR(B)"},
        {"Source": "APHA", "Method": "4500-NORGB"},
        {"Source": "APHA", "Method": "4500-NORG D"},
        {"Source": "APHA", "Method": "4500-CL(E)"},
        {"Source": "APHA", "Method": "5310-B"},
        {"Source": "APHA", "Method": "4500-P-J"},
        {"Source": "APHA", "Method": "4500-N-C"},
    ],
    "Conductivity": [
        {"Source": "ASTM", "Method": "D1125(A)"},
        {"Source": "APHA", "Method": "2510"},
        {"Source": "USEPA", "Method": "9050A"},
        {"Source": "USEPA", "Method": "360.2"},
        {"Source": "USEPA", "Method": "130.1"},
        {"Source": "USEPA", "Method": "9050"},
        {"Source": "APHA", "Method": "2510B"},
        {"Source": "APHA", "Method": "2550"},
        {"Source": "HACH", "Method": "8160"},
        {"Source": "USEPA", "Method": "120.1"},
        {"Source": "USEPA", "Method": "841-B-11-003"},
        {"Source": "YSI", "Method": "EXO WQ SONDE"},
    ],
    "Carbon": [
        {"Source": "USEPA", "Method": "9060"},
        {"Source": "APHA_SM20ED", "Method": "5310-B"},
        {"Source": "APHA", "Method": "5310C"},
        {"Source": "APHA", "Method": "5310-C"},
        {"Source": "USEPA", "Method": "9060A"},
        {"Source": "AOAC", "Method": "973.47"},
        {"Source": "USDOI/USGS", "Method": "O-1122-92"},
        {"Source": "USDOI/USGS", "Method": "O3100"},
        {"Source": "APHA", "Method": "5310-D"},
        {"Source": "APHA (2011)", "Method": "5310-C"},
        {"Source": "USEPA", "Method": "415.1"},
        {"Source": "USEPA", "Method": "415.3"},
        {"Source": "USEPA", "Method": "502.1"},
        {"Source": "APHA", "Method": "9222B"},
        {"Source": "USEPA", "Method": "415.2"},
        {"Source": "APHA", "Method": "5310-B"},
        {"Source": "APHA", "Method": "4500-H+B"},
    ],
    "Chlorophyll": [
        {"Source": "YSI", "Method": "EXO WQ SONDE"},
        {"Source": "USEPA", "Method": "446"},
        {"Source": "USEPA", "Method": "170.1"},
        {"Source": "USEPA", "Method": "445"},
        {"Source": "APHA", "Method": "10200H(3)"},
        {"Source": "APHA", "Method": "10200-H"},
        {"Source": "USEPA", "Method": "353.2"},
        {"Source": "USEPA", "Method": "447"},
        {"Source": "APHA", "Method": "10200H(2)"},
        {"Source": "APHA", "Method": "9222B"},
        {"Source": "APHA", "Method": "5310-C"},
    ],
    "Turbidity": [
        {"Source": "USEPA", "Method": "160.2_M"},
        {"Source": "USDOI/USGS", "Method": "I3860"},
        {"Source": "USEPA", "Method": "180.1"},
        {"Source": "USEPA", "Method": "360.2"},
        {"Source": "USEPA", "Method": "130.1"},
        {"Source": "APHA", "Method": "2130"},
        {"Source": "APHA", "Method": "2310 B"},
        {"Source": "APHA", "Method": "2130-B"},
        {"Source": "HACH", "Method": "8195"},
        {"Source": "LECK MITCHELL", "Method": "M5331"},
        {"Source": "ASTM", "Method": "D1889"},
    ],
    "Sediment": [],
    "Fecal_Coliform": [
        {"Source": "IDEXX", "Method": "COLILERT-18"},
        {"Source": "APHA_SM22ED", "Method": "9222D"},
        {"Source": "APHA", "Method": "9221-E"},
        {"Source": "AOAC", "Method": "978.23"},
        {"Source": "NIOSH", "Method": "600"},
        {"Source": "HACH", "Method": "8001(A2)"},
        {"Source": "HACH", "Method": "8074(A)"},
        {"Source": "APHA", "Method": "9230-D"},
        {"Source": "USEPA", "Method": "1103.1"},
        {"Source": "APHA", "Method": "9222D"},
        {"Source": "APHA", "Method": "9222A"},
        {"Source": "APHA", "Method": "3.2-B"},
        {"Source": "APHA", "Method": "10200-G"},
        {"Source": "APHA", "Method": "9222-E"},
        {"Source": "APHA", "Method": "9221-B"},
    ],
    "E_coli": [
        {"Source": "APHA", "Method": "9221A-B-C-F"},
        {"Source": "IDEXX", "Method": "COLILERT/2000"},
        {"Source": "MICROLOGY LABS", "Method": "EASYGEL"},
        {"Source": "IDEXX", "Method": "COLILERT"},
        {"Source": "IDEXX", "Method": "COLISURE"},
        {"Source": "USEPA", "Method": "360.2"},
        {"Source": "APHA_SM22ED", "Method": "9223-B"},
        {"Source": "IDEXX", "Method": "COLILERT-18"},
        {"Source": "IDEXX", "Method": "COLILERT-182000"},
        {"Source": "USEPA", "Method": "130.1"},
        {"Source": "USEPA", "Method": "1103.1 (MODIFIED)"},
        {"Source": "MICROLOGY LABS", "Method": "COLISCAN"},
        {"Source": "APHA", "Method": "9222D"},
        {"Source": "APHA", "Method": "9213-D"},
        {"Source": "HACH", "Method": "10029"},
        {"Source": "APHA", "Method": "9222G"},
        {"Source": "CDC", "Method": "CDC - E. coli and Shigella"},
        {"Source": "CDC", "Method": "E. COLI AND SHIGELLA"},
        {"Source": "USEPA", "Method": "1603"},
        {"Source": "APHA", "Method": "9213D"},
        {"Source": "USEPA", "Method": "1103.1"},
        {"Source": "USEPA", "Method": "1604"},
        {"Source": "APHA", "Method": "9223-B"},
        {"Source": "APHA", "Method": "9223-B-04"},
        {"Source": "APHA", "Method": "9222B,G"},
        {"Source": "USEPA", "Method": "600-R-00-013"},
        {"Source": "APHA", "Method": "9221-F"},
        {"Source": "USDOI/USGS", "Method": "10029"},
        {"Source": "NIOSH", "Method": "1604"},
        {"Source": "APHA", "Method": '"9222B	G"'},
        {"Source": "APHA", "Method": "9223B"},
        {"Source": "MODIFIED COLITAG", "Method": "ATP D05-0035"},
        {"Source": "ASTM", "Method": "D5392"},
        {"Source": "HACH", "Method": "10018"},
        {"Source": "USEPA", "Method": "1600"},
    ],
    "Phosphorus": [
        {"Source": "APHA", "Method": "3125"},
        {"Source": "APHA", "Method": "4500-P-C"},
        {"Source": "USEPA", "Method": "IO-3.3"},
        {"Source": "USEPA", "Method": "200.7_M"},
        {"Source": "USEPA", "Method": "200.9"},
        {"Source": "USEPA", "Method": "200.7(S)"},
        {"Source": "LACHAT", "Method": "10-115-01-1-F"},
        {"Source": "APHA_SM21ED", "Method": "4500-P-G"},
        {"Source": "USEPA", "Method": "351.3(C)"},
        {"Source": "LACHAT", "Method": "10-115-01-4-B"},
        {"Source": "USEPA", "Method": "365.2"},
        {"Source": "ASA(2ND ED.)", "Method": "24-5.4"},
        {"Source": "USEPA", "Method": "300.1"},
        {"Source": "USEPA", "Method": "365_M"},
        {"Source": "USEPA", "Method": "365.1"},
        {"Source": "APHA", "Method": "4500-NH3(C)"},
        {"Source": "USEPA", "Method": "300"},
        {"Source": "APHA", "Method": "4500-NO2(B)"},
        {"Source": "APHA", "Method": "4500-P-H"},
        {"Source": "USEPA", "Method": "300(A)"},
        {"Source": "USEPA", "Method": "350.1"},
        {"Source": "USEPA", "Method": "200.7(W)"},
        {"Source": "USEPA", "Method": "351.2"},
        {"Source": "USEPA", "Method": "365.3"},
        {"Source": "USDOI/USGS", "Method": "I2600(W)"},
        {"Source": "USDOI/USGS", "Method": "I2601"},
        {"Source": "APHA", "Method": "4500-P B"},
        {"Source": "USEPA", "Method": "6010B"},
        {"Source": "USEPA", "Method": "ICP-AES"},
        {"Source": "USDOI/USGS", "Method": "I-4610-91"},
        {"Source": "APHA", "Method": "3030 E"},
        {"Source": "APHA", "Method": "10200-F"},
        {"Source": "ASTM", "Method": "D3977"},
        {"Source": "USDOI/USGS", "Method": "I-4650-03"},
        {"Source": "USEPA", "Method": "440(S)"},
        {"Source": "USEPA", "Method": "200.8(W)"},
        {"Source": "USDOI/USGS", "Method": "I1602"},
        {"Source": "APHA", "Method": "4500-P-E"},
        {"Source": "USDOI/USGS", "Method": "I-2650-03"},
        {"Source": "APHA", "Method": "4500-NOR(C)"},
        {"Source": "APHA", "Method": "4500-P"},
        {"Source": "ASTM", "Method": "D888(B)"},
        {"Source": "ASTM", "Method": "D515(A)"},
        {"Source": "HACH", "Method": "10210"},
        {"Source": "HACH", "Method": "8190"},
        {"Source": "HACH", "Method": "10242"},
        {"Source": "USDOE/ASD", "Method": "MS100"},
        {"Source": "USEPA", "Method": "6010A"},
        {"Source": "APHA", "Method": "4500-F-E"},
        {"Source": "USEPA", "Method": "200.7"},
        {"Source": "APHA", "Method": "2540-D"},
        {"Source": "APHA", "Method": "4500-P-F"},
        {"Source": "USEPA", "Method": "8321"},
        {"Source": "USEPA", "Method": "200.15"},
        {"Source": "USEPA", "Method": "353.2"},
        {"Source": "USEPA", "Method": "6020A"},
        {"Source": "USDOI/USGS", "Method": "I-1601-85"},
        {"Source": "USEPA", "Method": "200.2"},
        {"Source": "USDOI/USGS", "Method": "I-4600-85"},
        {"Source": "USDOI/USGS", "Method": "I-4607"},
        {"Source": "USDOI/USGS", "Method": "I-4602"},
        {"Source": "APHA (1999)", "Method": "4500-P-E"},
        {"Source": "APHA", "Method": "4500-H"},
        {"Source": "USEPA", "Method": "6010C"},
        {"Source": "USEPA", "Method": "365.4"},
        {"Source": "USDOI/USGS", "Method": "I6600"},
        {"Source": "USEPA", "Method": "200.8"},
        {"Source": "USEPA", "Method": "351.1"},
        {"Source": "HACH", "Method": "10209"},
        {"Source": "USEPA	", "Method": "6020"},
        {"Source": "ASTM", "Method": "D515(B)"},
        {"Source": "USEPA", "Method": "624"},
        {"Source": "APHA", "Method": "2340B"},
        {"Source": "APHA", "Method": "9222B"},
        {"Source": "USEPA", "Method": "440"},
        {"Source": "APHA", "Method": "2540-C"},
        {"Source": "USEPA", "Method": "353.2_M"},
        {"Source": "APHA", "Method": "4500-P-J"},
        {"Source": "APHA", "Method": "9223-B"},
        {"Source": "APHA", "Method": "4500-P-I"},
        {"Source": "USEPA", "Method": "610"},
        {"Source": "APHA", "Method": "4500-N-C"},
        {"Source": "APHA", "Method": "4500-P-D"},
        {"Source": "APHA", "Method": "4500-P E"},
        {"Source": "APHA", "Method": "4500-P F"},
        {"Source": "USDOI/USGS", "Method": "I-2610-91"},
        {"Source": "USDOI/USGS", "Method": "I-2607"},
        {"Source": "USDOI/USGS", "Method": "I-2606"},
        {"Source": "USDOI/USGS", "Method": "I-2601-90"},
        {"Source": "USDOI/USGS", "Method": "I-6600-88"},
        {"Source": "ASTM", "Method": "D515"},
    ],
}
