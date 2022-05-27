# -*- coding: utf-8 -*-
"""
Created on Fri Aug 13 06:58:16 2021

Source files for domain lists with all potential values (to filter on)

For small or frequently utilized domains I've hard coded dictionaries and
have a url method to update.

@author: jbousqui
"""
from zipfile import ZipFile
from io import BytesIO
import requests
import pandas
#from numpy import nan


BASE_URL = 'https://cdx.epa.gov/wqx/download/DomainValues/'

UNITS_REPLACE = {'Secchi': {},
                 'DO': {'%': 'percent'},
                 'Temperature': {},
                 'Salinity': {'ppt': 'ppth',
                              '0/00': 'ppth',},
                 'pH': {'None': 'dimensionless',
                        'std units': 'dimensionless'},
                 'Nitrogen': {'cm3/g @STP': 'cm3/g',
                              'cm3/g STP': 'cm3/g',
                              '%': 'percent',},
                 'Conductivity': {'uS': 'uS/cm',
                                  'umho': 'umho/cm',},
                 'Carbon': {'% by wt': '%',
                            '%': 'percent',},
                 'Chlorophyll': {'mg/cm3': 'mg/cm**3',
                                 'mg/m3': 'mg/m**3',
                                 'mg/m2': 'mg/m**3',
                                 'ug/cm3': 'ug/cm**3'},
                 'Turbidity': {'mg/l SiO2': 'SiO2',
                               'ppm SiO2': 'SiO2'},
                 'Sediment': {'%': 'percent'},
                 'Fecal_Coliform': {'#/100ml': 'CFU/(100ml)',
                                    'CFU': 'CFU/(100ml)',
                                    'MPN': 'MPN/(100ml)',},
                 'E_coli': {'#/100ml': 'CFU/(100ml)',
                            'CFU': 'CFU/(100ml)',
                            'MPN': 'MPN/(100ml)',},
                 'Phosphorus': {'%': 'percent'},
                 }

OUT_UNITS = {'Secchi': 'm',
             'DO': 'mg/l',
             'Temperature': 'degC',
             'Salinity': 'PSU',
             'pH': 'dimensionless',
             'Nitrogen': 'mg/l',
             'Conductivity': 'uS/cm',
             'Carbon': 'mg/l',
             'Chlorophyll': 'mg/l',
             'Turbidity': 'NTU',
             'Sediment': 'g/kg',
             'Fecal_Coliform': 'CFU/(100ml)',
             'E_coli': 'CFU/(100ml)',
             'Phosphorus': 'mg/l'
             }


def registry_adds_list(out_col):
    #TODO: 'PSU' = 'PSS' ~ ppth/1.004715

    # define is 1% (0.08s) slower than replacement (ppm->mg/l) but more robust
    # Standard pint unit registry additions for dimensionless portions
    pct_list = ['fraction = [] = frac',
                'percent = 1e-2 frac',
                'parts_per_thousand = 1e-3 = ppth',
                'parts_per_million = 1e-6 fraction = ppm',
                ]
    # Standard pint unit registry additions for dimensionless bacteria units
    bacteria_list = ['Colony_Forming_Units = [] = CFU = cfu',
                     'Most_Probable_Number = CFU = MPN = mpn',
                     ]
    # characteristic based dict
    ureg_adds = {'Secchi': [],
                 'DO': pct_list,
                 'Temperature': [],
                 'Salinity': pct_list +
                             ['Practical_Salinity_Units = ppth = PSU = PSS'],
                 'pH': [],
                 'Nitrogen': [],
                 'Conductivity': [],
                 'Carbon': pct_list,
                 'Chlorophyll': [],
                 'Turbidity': ['Nephelometric_Turbidity_Units = [turbidity] = NTU',
                               'Nephelometric_Turbidity_Ratio_Units = NTU = NTRU',
                               'Nephelometric_Turbidity_Multibeam_Units = NTU = NTMU',
                               'Formazin_Nephelometric_Units = NTU = FNU',
                               'Formazin_Nephelometric_Ratio_Units = FNRU = FNU',
                               'Formazin_Turbidity_Units = FNU = FTU = FAU',
                               'Jackson_Turbidity_Units = [] = JTU',
                               'SiO2 = []'],
                 'Sediment': pct_list,
                 'Fecal_Coliform': bacteria_list,
                 'E_coli': bacteria_list,
                 'Phosphorus': [],
                 }
    return ureg_adds[out_col]


def bacteria_reg(ureg=None):
    """
    Generate standard pint unit registry with bacteria units defined.

    Parameters
    ----------
    ureg : pint.UnitRegistry, optional
        Unit Registry Object with any custom units defined. Default None
        starts with new unit registry

    Returns
    -------
    unit_registry : pint.UnitRegistry
        Unit registry with dimensionless bacteria units defined.
    """
    if ureg is None:
        ureg = pint.UnitRegistry()

    return ureg


def out_col_lookup():
    """

    Returns
    -------
    dict
        {WQP CharacteristicName:Column Name}.

    """
    #TODO: something special for phosphorus? Currently return suffix.
    #'Phosphorus' -> ['TP_Phosphorus', 'TDP_Phosphorus', 'Other_Phosphorus']
    return {'Depth, Secchi disk depth': 'Secchi',
            'Dissolved oxygen (DO)': 'DO',
            'Temperature, water': 'Temperature',
            'Salinity': 'Salinity',
            'pH': 'pH',
            'Nitrogen': 'Nitrogen',
            'Conductivity': 'Conductivity',
            'Organic carbon': 'Carbon',
            'Chlorophyll a': 'Chlorophyll',
            'Turbidity': 'Turbidity',
            'Sediment': 'Sediment',
            'Fecal Coliform': 'Fecal_Coliform',
            'Escherichia coli': 'E_coli',
            'Phosphorus': 'Phosphorus',
            }


def characteristic_cols(category=None):
    """
    Return characteristic specific columns, can subset those by category.

    Parameters
    ----------
    categoy : string, optional
        Subset results: 'Basis', 'Bio', 'Depth', 'QA', 'activity', 'analysis',
        'depth', 'measure', 'sample'.
        The default is None.

    Returns
    -------
    col_list : list
        List of columns.

    """
    cols = {'ActivityStartDate': 'activity',
            'ActivityStartTime/Time': 'activity',
            'ActivityStartTime/TimeZoneCode': 'activity',
            'DataLoggerLine': 'measure',
            'ResultDetectionConditionText': 'QA',
            'MethodSpecificationName': 'measure',
            'CharacteristicName': 'measure',
            'ResultSampleFractionText': 'measure',
            'ResultMeasureValue': 'measure',
            'ResultMeasure/MeasureUnitCode': 'measure',
            'MeasureQualifierCode': 'measure',
            'ResultStatusIdentifier': 'QA',
            'StatisticalBaseCode': 'measure',
            'ResultValueTypeName': 'measure',
            'ResultWeightBasisText': 'Basis',
            'ResultTimeBasisText': 'Basis',
            'ResultTemperatureBasisText': 'Basis',
            'ResultParticleSizeBasisText': 'Basis',
            'PrecisionValue': 'QA',
            'DataQuality/BiasValue': 'QA',
            'ConfidenceIntervalValue': 'QA',
            'UpperConfidenceLimitValue': 'QA',
            'LowerConfidenceLimitValue': 'QA',
            'ResultCommentText': 'QA',
            'USGSPCode': 'measure',
            'ResultDepthHeightMeasure/MeasureValue': 'Depth',
            'ResultDepthHeightMeasure/MeasureUnitCode': 'Depth',
            'ResultDepthAltitudeReferencePointText': 'Depth',
            'ResultSamplingPointName': 'QA',
            'BiologicalIntentName': 'Bio',
            'BiologicalIndividualIdentifier': 'BIO',
            'SubjectTaxonomicName': 'Bio',
            'UnidentifiedSpeciesIdentifier': 'BIO',
            'SampleTissueAnatomyName': 'Bio',
            'GroupSummaryCountWeight/MeasureValue': 'Bio',
            'GroupSummaryCountWeight/MeasureUnitCode': 'Bio',
            'CellFormName': 'Bio',
            'CellShapeName': 'Bio',
            'HabitName': 'Bio',
            'VoltismName': 'Bio',
            'TaxonomicPollutionTolerance': 'Bio',
            'TaxonomicPollutionToleranceScaleText': 'Bio',
            'TrophicLevelName': 'Bio',
            'FunctionalFeedingGroupName': 'Bio',
            'TaxonomicDetailsCitation/ResourceTitleName': 'Bio',
            'TaxonomicDetailsCitation/ResourceCreatorName': 'Bio',
            'TaxonomicDetailsCitation/ResourceSubjectText': 'Bio',
            'TaxonomicDetailsCitation/ResourcePublisherName': 'Bio',
            'TaxonomicDetailsCitation/ResourceDate': 'Bio',
            'TaxonomicDetailsCitation/ResourceIdentifier': 'Bio',
            'FrequencyClassInformationUrl': 'Bio',
            'ResultAnalyticalMethod/MethodIdentifier': 'measure',
            'ResultAnalyticalMethod/MethodIdentifierContext': 'measure',
            'ResultAnalyticalMethod/MethodName': 'measure',
            'ResultAnalyticalMethod/MethodUrl': 'measure',
            'ResultAnalyticalMethod/MethodQualifierTypeName': 'measure',
            'MethodDescriptionText': 'measure',
            'LaboratoryName': 'analysis',
            'AnalysisStartDate': 'analysis',
            'AnalysisStartTime/Time': 'analysis',
            'AnalysisStartTime/TimeZoneCode': 'analysis',
            'AnalysisEndDate': 'analysis',
            'AnalysisEndTime/Time': 'analysis',
            'AnalysisEndTime/TimeZoneCode': 'analysis',
            'ResultLaboratoryCommentCode': 'analysis',
            'ResultLaboratoryCommentText': 'analysis',
            'ResultDetectionQuantitationLimitUrl': 'QA',
            'LaboratoryAccreditationIndicator': 'analysis',
            'LaboratoryAccreditationAuthorityName': 'analysis',
            'TaxonomistAccreditationIndicator': 'analysis',
            'TaxonomistAccreditationAuthorityName': 'analysis',
            'LabSamplePreparationUrl': 'analysis',
            'ActivityTypeCode': 'activity',
            'ActivityMediaName': 'activity',
            'ActivityMediaSubdivisionName': 'activity',
            'ActivityEndDate': 'activity',
            'ActivityEndTime/Time': 'activity',
            'ActivityEndTime/TimeZoneCode': 'activity',
            'ActivityRelativeDepthName': 'depth',
            'ActivityDepthHeightMeasure/MeasureValue': 'depth',
            'ActivityDepthHeightMeasure/MeasureUnitCode': 'depth',
            'ActivityDepthAltitudeReferencePointText': 'depth',
            'ActivityTopDepthHeightMeasure/MeasureValue': 'depth',
            'ActivityTopDepthHeightMeasure/MeasureUnitCode': 'depth',
            'ActivityBottomDepthHeightMeasure/MeasureValue': 'depth',
            'ActivityBottomDepthHeightMeasure/MeasureUnitCode': 'depth',
            'ActivityConductingOrganizationText': 'activity',
            'ActivityCommentText': 'activity',
            'SampleAquifer': 'activity',
            'HydrologicCondition': 'activity',
            'HydrologicEvent': 'activity',
            'ActivityLocation/LatitudeMeasure': 'activity',
            'ActivityLocation/LongitudeMeasure': 'activity',
            'ActivityLocation/SourceMapScaleNumeric': 'activity',
            'ActivityLocation/HorizontalAccuracyMeasure/MeasureValue': 'activity',
            'ActivityLocation/HorizontalAccuracyMeasure/MeasureUnitCode': 'activity',
            'ActivityLocation/HorizontalCollectionMethodName': 'activity',
            'ActivityLocation/HorizontalCoordinateReferenceSystemDatumName': 'activity',
            'AssemblageSampledName': 'sample',
            'CollectionDuration/MeasureValue': 'sample',
            'CollectionDuration/MeasureUnitCode': 'sample',
            'SamplingComponentName': 'sample',
            'SamplingComponentPlaceInSeriesNumeric': 'sample',
            'ReachLengthMeasure/MeasureValue': 'sample',
            'ReachLengthMeasure/MeasureUnitCode': 'sample',
            'ReachWidthMeasure/MeasureValue': 'sample',
            'ReachWidthMeasure/MeasureUnitCode': 'sample',
            'PassCount': 'sample',
            'NetTypeName': 'sample',
            'NetSurfaceAreaMeasure/MeasureValue': 'sample',
            'NetSurfaceAreaMeasure/MeasureUnitCode': 'sample',
            'NetMeshSizeMeasure/MeasureValue': 'sample',
            'NetMeshSizeMeasure/MeasureUnitCode': 'sample',
            'BoatSpeedMeasure/MeasureValue': 'sample',
            'BoatSpeedMeasure/MeasureUnitCode': 'sample',
            'CurrentSpeedMeasure/MeasureValue': 'sample',
            'CurrentSpeedMeasure/MeasureUnitCode': 'sample',
            'ToxicityTestType': 'analysis',
            'SampleCollectionMethod/MethodIdentifier': 'sample',
            'SampleCollectionMethod/MethodIdentifierContext': 'sample',
            'SampleCollectionMethod/MethodName': 'sample',
            'SampleCollectionMethod/MethodQualifierTypeName': 'sample',
            'SampleCollectionMethod/MethodDescriptionText': 'sample',
            'SampleCollectionEquipmentName': 'sample',
            'SampleCollectionMethod/SampleCollectionEquipmentCommentText': 'sample',
            'SamplePreparationMethod/MethodIdentifier': 'sample',
            'SamplePreparationMethod/MethodIdentifierContext': 'sample',
            'SamplePreparationMethod/MethodName': 'sample',
            'SamplePreparationMethod/MethodQualifierTypeName': 'sample',
            'SamplePreparationMethod/MethodDescriptionText': 'sample',
            'SampleContainerTypeName': 'sample',
            'SampleContainerColorName': 'sample',
            'ChemicalPreservativeUsedName': 'analysis',
            'ThermalPreservativeUsedName': 'analysis',
            'SampleTransportStorageDescription': 'analysis',
            'ActivityMetricUrl': 'activity',
            'PreparationStartDate': 'analysis',}
    if category:
        # List of key where value is category
        col_list = [key for key, value in cols.items() if value==category]
    else:
        col_list = list(cols.keys())  # All keys/cols
    return col_list


def get_ResultValueTypeName():
    """
    Get dictionary of possible values (key) and their descriptions (values).
    url = '{}ResultValueType_CSV.zip'.format(BASE_URL)

    Returns
    -------
    dict: dictionary
        Dictionary where exhaustive {ResultValueTypeName: Description}
    """

    return {"Actual": "	Existing now; present; current:",
            "Blank Corrected Calc": "The data were blank corrected using the recommended procedure detailed in the analytical method.",
            "Calculated": "To ascertain by computation or determined by mathematical calculation, evaluating, and reasoning.",
            "Control Adjusted": "Requirements are determined from the control test data",
            "Estimated": "Approximation, educated guess, or projection of a quantity based on experience and/or information available at the time, and the cheapest (and least accurate) type of modeling.",
            }


def xy_datum():
    """
    Get dictionary of possible values (key) and dictionary values for their
    "Description" (string, Not currently used) or EPSG code (int).
    source url:
        '{}HorizontalCoordinateReferenceSystemDatum_CSV.zip'.format(BASE_URL)

    NOTES:
    -------
    Aything not in dict will be nan (must be int), i.e.:
        "OTHER": {"Description": 'Other',
                  "EPSG": nan},
        "UNKWN": {"Description": 'Unknown',
                  "EPSG": nan},

    Returns
    -------
    dict
        Dictionary where exhaustive:
            {HorizontalCoordinateReferenceSystemDatumName: {Description:str,
                                                            EPSG:int}}
    """
    return {"NAD27": {"Description": 'North American Datum 1927',
                      "EPSG": 4267},
            "NAD83": {"Description": 'North American Datum 1983',
                      "EPSG": 4269},
            "AMSMA": {"Description": 'American Samoa Datum',
                      "EPSG": 4169},
            "ASTRO": {"Description": 'Midway Astro 1961',
                      "EPSG": 4727},
            "GUAM": {"Description": 'Guam 1963',
                      "EPSG": 4675},
            "JHNSN": {"Description": 'Johnson Island 1961',
                      "EPSG": 4725},
            "OLDHI": {"Description": 'Old Hawaiian Datum',
                      "EPSG": 4135},
            "PR": {"Description": 'Puerto Rico Datum',
                      "EPSG": 6139},
            "SGEOR": {"Description": 'St. George Island Datum',
                      "EPSG": 4138},
            "SLAWR": {"Description": 'St. Lawrence Island Datum',
                      "EPSG": 4136},
            "SPAUL": {"Description": 'St. Paul Island Datum',
                      "EPSG": 4137},
            "WAKE": {"Description": 'Wake-Eniwetok 1960',
                      "EPSG": 6732},
            "WGS72": {"Description": 'World Geodetic System 1972',
                      "EPSG": 6322},
            "WGS84": {"Description": 'World Geodetic System 1984',
                      "EPSG": 4326},
            "HARN": {"Description": 'High Accuracy Reference Network for NAD83',
                      "EPSG": 4152},
            }


def get_ActivityMediaName():
    """
    Get dictionary of possible values (key) and their descriptions (values).
    url = '{}ActivityMedia_CSV.zip'.format(BASE_URL)

    Returns
    -------
    dict
        Dictionary where exhaustive {ActivityMediaName:Description}

    """
    return {'Air': "the invisible gaseous substance surrounding the earth, a mixture of nitrogen, oxygen, and minute amounts of other gases that forms earth's atmosphere",
            'Biological': 'relating to biology or living organisms',
            'Habitat': 'the natural home or environment of an animal, plant, or other organism.',
            'Other': 'other; the area or natural environment in which an organism or substance is found',
            'Sediment': "matter that settles to the bottom of a liquid; dregs; Geology Solid fragmented material, such as silt, sand, gravel, chemical precipitates, and fossil fragments, that is transported and deposited by water, ice, or wind or that accumulates through chemical precipitation or secretion by organisms, and that forms layers on the Earth's surface.",
            'Soil': "the loose top layer of the Earth's surface, a black or dark brown material consisting of rock and mineral particles mixed with decayed organic matter (humus), and capable of retaining water, providing nutrients for plants, and supporting a wide range of biotic communities.",
            'Tissue': 'an aggregate of cells usually of a particular kind together with their intercellular substance that form one of the structural materials of a plant or an animal',
            'Water': 'a colorless, transparent, odorless, tasteless liquid that forms the seas, lakes, rivers, and rain and is the basis of the fluids of living organisms.'
            }


def get_ActivityMediaSubdivisionName():
    """
    Get dictionary of possible values (key) and their descriptions (values).
    url = '{}ActivityMediaSubdivision_CSV.zip'.format(BASE_URL)

    Returns
    -------
    dict
        Dictionary where exhaustive {ActivityMediaSubdivisionName:Description}

    """
    return {'Air moisture': 'Water present in air in a gaseous form. Air moisture plays a significant role in weather when it changes from one state to another. These changes include condensation (cloud, fog, dew, and frost) and precipitation (rainfall and snowfall).',
            'Ambient Air': 'refers to any unconfined portion of the atmosphere or outdoor air. basically the natural state of air in the outdoor environment',
            'Borehole cuttings': 'Unconsolidated material removed from a pipe or casing during a drilling (coring) operation',
            'Borrow Soil, Waste Rock, and Protore material': 'material (usually soil, gravel or sand) has been dug for use at another location.soil or Rock may contain sub-economic material from which economic mineral deposits may form by geologic concentration processes such as supergene enrichment.',
            'Bottom material': 'A mixture of mineral and organic matter that compose the top bed deposits (usually the first few inches) underlying a body of water. Bottom material consists of living and non-living, organic and inorganic material of varying physical, chemical, and biological composition that has been transported by water, ice, and wind and deposited in aquatic systems.\r',
            'Bulk Deposition': 'the sum of. wet-only deposition and of sedimenting (dry) particles to. a sample collector in ambient air. The fluent delivery of a stream of separate loose pieces onto a receiving surface. The relative size of the pieces is not significant, rather it is the manner in which they are handled, as a mass or stream rather than each particle being individually manipulated.',
            'Canopy water': 'Water dripping off tree-leaf canopies or running down the trunks of trees.',
            'Const. Material': 'any material which is used for construction purposes. Many naturally occurring substances, such as clay, rocks, sand, and wood, even twigs and leaves, have been used to construct buildings',
            'Core material': 'Consolidated or unconsolidated material removed from a pipe or casing during a drilling (coring) operation.',
            'Deionized Water': 'Water that has had almost all of its mineral ions removed, such as cations like sodium, calcium, iron, and copper, and anions such as chloride and sulfate.',
            'Domestic Sewage': 'Domestic sewage means sewage that consists of water and human excretions or other waterborne wastes incidental to the occupancy of a residential building. Domestic sewage carries used water from houses and apartments; it is also called sanitary sewage.',
            'Drinking Water': 'known as potable water or improved drinking water, is water that is safe to drink or to use for food preparation, without risk of health problems.',
            'Dry Fall Material': 'material formulated so that when applied at specified conditions, their droplets or overspray rapidly dry into a dust-like state before reaching a certain distance',
            'Elutriate': 'A process by which a mixture of an unconsolidated solid medium (usually soil) and a liquid medium (usually water) has been agitated for a given period of time to dissolve materials from the solid. The solid/liquid mixture is finally separated and the resulting solution is analyzed for materials dissolved during the elutriation process. separate (lighter and heavier particles in a mixture) by suspension in an upward flow of liquid or gas. purify by straining.',
            'Filter Residue': 'the solid mass remaining on a filter after the liquid that contained it has passed through; specifically :the residue of impurities filtered from clarified juice of sugarcane that is used as a fertilizer',
            'Finished Water': 'water that is introduced into the distribution system of a public water system and is intended for distribution and consumption without further treatment',
            'Foam': 'a mass of small bubbles formed on or in liquid, typically by agitation or fermentation.',
            'Groundwater': "Water below the surface of the Earth contained in the saturated zone. It does not include soil moisture or interstitial water. Water that collects or flows beneath the Earth's surface, filling the porous spaces in soil, sediment, and rocks.",
            'Hyporheic zone': 'Near-stream subsurface environment where mixing occurs between subsurface water and surface water. Water flows not only in the open stream channel, but also through the interstices of stream-channel and bank sediments, thus creating a mixing zone with subsurface water. There is not a precise separation between groundwater and surface water, thus the hyporheic zone is not precisely defined.',
            'Indoor Air': 'refers to the air quality within and around buildings and structures, especially as it relates to the health and comfort of building occupants.',
            'Industrial Effluent': 'Liquid waste flowing out of a factory, farm, commercial establishment',
            'Industrial Waste': 'waste produced by industrial activity which includes any material that is rendered useless during a manufacturing process such as that of factories, industries, mills, and mining operations',
            'Interstitial Water': '(pore water), subterranean water in the pores of rocks, soils, and bottom sediments of oceans, seas, and lakes.',
            'Lake Sediment': 'the accumulation of sand and dirt that settles in the bottom of lakes.',
            'Landfill effluent': 'A liquid material (usually water) that is drained or pumped from a landfill. It usually is a liquid that has percolated through solid landfill material to become a transport medium for materials dissolved from the landfill.',
            'Leachate': "A solution obtained by passing a liquid (usually aqueous) through an unconsolidated solid medium, thereby dissolving materials (from the solid medium) which become a part of the solution. It also contains those precipitates that are the result of the solution process and subsequent chemical or biological reactions. any liquid that, in the course of passing through matter. the liquid that drains or 'leaches' from a landfill.",
            'Manure, green': 'In agriculture, green manure is created by leaving uprooted or sown crop parts to wither on a field so that they serve as a mulch and soil amendment.[1] The plants used for green manure are often cover crops grown primarily for this purpose. Typically, they are ploughed under and incorporated into the soil while green or shortly after flowering.',
            'Manure, liquid': 'Liquid manure is manure in a liquid form. Manure is changed into a liquid form by mixing the manure with water.',
            'Manure, solid': 'Manure is organic matter, mostly derived from animal feces except in the case of green manure, which can be used as organic fertilizer in agriculture. Manures contribute to the fertility of the soil by adding organic matter and nutrients, such as nitrogen, that are utilised by bacteria, fungi and other organisms in the soil.',
            'Mine Tailings Pond': 'Tailing ponds are areas of refused mining tailings where the waterborne refuse material is pumped into a pond to allow the sedimentation (meaning separation) of solids from the water. The pond is generally impounded with a dam, and known as tailings impoundments or tailings dams.',
            'Mixing Zone': 'A mixing zone is an area of a lake or river where pollutants from a point source discharge are mixed, usually by natural means, with cleaner water. In the mixing zone, the level of toxic pollutants is allowed to be higher than the acceptable concentration for the general water body.',
            'Mixing Zone, Zone of Initial Dilution': 'A zone of initial dilution or ZID is defined as a small area in the immediate vicinity of an outfall structure in which turbulence from the eflhtent velocity is high and causes rapid mixing with the surrounding water. Turbulence for rapid mixing can be provided in three ways. The most common way is with the use of an effluent diffuser. This method assures adequate velocities and mixing if it is properly designed for the discharge area.',
            'Municipal Sewage Effluent': 'Sewage treatment is the process of removing contaminants from wastewater, primarily from household sewage. It includes physical, chemical, and biological processes to remove these contaminants and produce environmentally safer treated wastewater (or treated effluent).',
            'Municipal Waste': 'waste from households, and other waste that, because of its nature or composition, is similar to waste from households.',
            'Ocean Water': "Seawater, or salt water, is water from a sea or ocean. On average, seawater in the world's oceans has a salinity of about 3.5% (35 g/L, 599 mM) ",
            'Oil/Oily Sludge': 'Any sludge and/or float generated from the physical and/or chemical separation of oil/water/solids in process wastewaters and oily cooling wastewaters from petroleum refineries.',
            'Pore water': "water contained in pores in soil or rock. Water beneath the earth's surface, often between saturated soil and rock, that supplies wells and springs.",
            'Rainwater': 'water that has fallen as or been obtained from rain.',
            'Rock/Cobbles/Gravel': 'Particle size, also called grain size, refers to the diameter of individual grains of sediment, or the lithified particles in clastic rocks. ... Granular material can range from very small colloidal particles, through clay, silt, sand, gravel, and cobbles, to boulders.',
            'Septic Effluent': 'collect sewage from residences and businesses, and the effluent that comes out of the tank is sent to either a centralized sewage treatment plant or a distributed treatment system',
            'Sieved Sediment': 'characterizing the particle size distribution of a sediment sample thru a device for separating wanted elements from unwanted material ',
            'Sludge': 'thick, soft, wet mud or a similar viscous mixture of liquid and solid components, especially the product of an industrial or refining process',
            'Snowmelt': 'the melting of fallen snow',
            'Soil Gas': 'the gases found in the air space between soil components. The primary natural soil gases include nitrogen, carbon dioxide and oxygen. The oxygen is critical because it allows for respiration of both plant roots and soil organisms. Other natural soil gases are atmospheric methane and radon.',
            'Soil moisture': 'Water occupying voids between loose soil particles within the aerated root zone. The water is held in place by surface tension, capillary and hydroscopic forces in opposition to the pull of gravitational forces.',
            'Solids': 'Unconsolidated materials that may be soils, cores, borehole cuttings, sediments, matter suspended in water or wastewater, street sweepings, other particulate matter, or the total array of materials that are collected as part of a "clean sweep"',
            'Stack Gases': 'combustion product gases called flue gases are exhausted to the outside air.',
            'Stormwater': 'surface water in abnormal quantity resulting from heavy falls of rain or snow.',
            'Subsurface Soil/Sediment': 'relating to, or situated in an area beneath a surface, especially the surface of the earth or of a body of wate, soil or sediment',
            'Surface Soil/Sediment': 'relating to or occurring on the upper or outer part of something.soil or sediment',
            'Surface Water': 'Water on the surface of the Earth stored or transported in rivers, streams, estuaries, lakes, ponds, swamps, glaciers, or other aquatic areas. It also may refer to water in urban drains and storm-sewer systems. water that collects on the surface of the ground. water on the surface of the planet such as in a river, lake, wetland, or ocean.',
            'Surface Water Sediment': 'Sediments are most often transported by water (fluvial processes), but also wind (aeolian processes) and glaciers. Beach sands and river channel deposits are examples of fluvial transport and deposition, though sediment also often settles out of slow-moving or standing water in lakes and oceans.',
            'Treated water supply': 'Water after being processed for some particular use(s)',
            'Unknown': 'Unknown',
            'UnSieved Sediment': 'preserved characterized particle size distribution of a sediment sample',
            'Untreated water supply': 'Untreated water supply from a blend of surface and ground waters or from unknown sources.',
            'USGS Standard Reference Sample': 'Samples provided by the USGS for quality assurance testing',
            'Waste Gas': 'Waste Gas is meant to represent landfill gas. Waste gas means a natural gas that contains a greater percentage of gaseous chemical impurities than the percentage of methane. For purposes of this definition, gaseous chemical impurities may include carbon dioxide, nitrogen, helium, or hydrogen sulfide.',
            'Wastewater Treatment Plant Effluent': 'the final product of all earlier treatment processes, and it can be discharged to a stream, river, bay, lagoon or wetland. Sometimes effluent ',
            'Wastewater Treatment Plant Influent': 'Influent is water, waste water or other liquid flowing into a reservoir, basin or treatment plant.',
            'Water-Vadose Zone': 'The vadose zone, also termed the unsaturated zone, is the part of Earth between the land surface and the top of the phreatic zone, the position at which the groundwater (the water in the soil\'s pores) is at atmospheric pressure ("vadose" is from the Latin for "shallow")',
            'Wet Fall Material': 'material formulated so that when applied at specified conditions, formings a droplets-like state before reaching a certain distance',
            'Wipe': 'a disposable cloth for wiping things clean',
            }


def get_domain_list(field):
    """
    Queries for domain list and extracts as dictionary

    Parameters
    ----------
    field : string
        Name of field in returned results

    Returns
    -------
    dictionary
        Dictionary where {Name: Description}

    """
    # ActivityMediaSubdivisionName -> ActivityMediaSubdivision
    # ActivityMediaName -> ActivityMedia
    url = '{}{}_CSV.zip'.format(BASE_URL, field)

    if requests.get(url).status_code != 200:
        status_code = requests.get(url).status_code
        print("{} web service response {}".format(url, status_code))
    res = requests.get(url)
    if not res.ok:
        # Use requests lib to print url server request
        req_str = requests.Request('GET', url, params={}).prepare().url
        print("Problem with response from {}".format(req_str))
        print('Try running the query using this url in your browser')
        print(res.headers['Warning'], 1)
        # Will typically break with key error

    # zipfile object from response content bytes
    archive = ZipFile(BytesIO(res.content))
    item1 = archive.namelist()[0]  # Name of first file
    cols = ['\tName', '\tDescription']
    df = pandas.read_csv(archive.open(item1), usecols=cols, low_memory=False)
    # Drop tabs from values
    for col in cols:
        df[col] = [val.replace('\t', '') for val in df[col]]
    # Drop tabs from column names
    df.columns = df.columns.str.replace('\t', '')
    df = df.set_index('Name')  # Set index to cols1
    # Return key = col for dict by col1
    return df.to_dict()['Description']


def stations_rename():
#     Default field mapping writes full name to alias but a short name to field
    """
    ESRI places a length restriction on shapefile field names. This returns a
    dictionary with the original water quality portal field name (as key) and
    shortend column name for writing as shp. We suggest using the longer
    original name as the field alias when writing as .shp.

    Returns
    -------
    field_mapping : dictionary
        dictionary where key = WQP field name and value = short name for shp.

    """
    return {'OrganizationIdentifier': 'org_ID',
            'OrganizationFormalName': 'org_name',
            'MonitoringLocationIdentifier': 'loc_ID',
            'MonitoringLocationName': 'loc_name',
            'MonitoringLocationTypeName': 'loc_type',
            'MonitoringLocationDescriptionText': 'loc_desc',
            'HUCEightDigitCode': 'HUC08_code',
            'DrainageAreaMeasure/MeasureValue':'DA_val',
            'DrainageAreaMeasure/MeasureUnitCode': 'DA_unit',
            'ContributingDrainageAreaMeasure/MeasureValue': 'CA_val',
            'ContributingDrainageAreaMeasure/MeasureUnitCode': 'CA_unit',
            'LatitudeMeasure': 'Latitude',
            'LongitudeMeasure': 'Longitude',
            'SourceMapScaleNumeric': 'SRC_Scale',
            'HorizontalAccuracyMeasure/MeasureValue': 'xy_acc',
            'HorizontalAccuracyMeasure/MeasureUnitCode': 'xy_accUnit',
            'HorizontalCollectionMethodName': 'xy_method',
            'HorizontalCoordinateReferenceSystemDatumName': 'xy_datum',
            'VerticalMeasure/MeasureValue': 'z',
            'VerticalMeasure/MeasureUnitCode': 'z_unit',
            'VerticalAccuracyMeasure/MeasureValue': 'z_acc',
            'VerticalAccuracyMeasure/MeasureUnitCode': 'z_accUnit',
            'VerticalCollectionMethodName': 'z_method',
            'VerticalCoordinateReferenceSystemDatumName': 'z_datum',
            'CountryCode': 'country',
            'StateCode': 'state',
            'CountyCode': 'county',
            'AquiferName': 'aquifer',
            'FormationTypeText': 'form_type',
            'AquiferTypeName': 'aquiferType',
            'ConstructionDateText': 'constrDate',
            'WellDepthMeasure/MeasureValue': 'well_depth',
            'WellDepthMeasure/MeasureUnitCode': 'well_unit',
            'WellHoleDepthMeasure/MeasureValue': 'wellhole',
            'WellHoleDepthMeasure/MeasureUnitCode': 'wellHole_unit',
            'ProviderName': 'provider',
            'ActivityIdentifier': 'activity_ID',
            'ResultIdentifier': 'result_ID',
            }

def accepted_methods():
    """
    Accepted methods for each characteristic.

    Note: Source should be in 'ResultAnalyticalMethod/MethodIdentifierContext'

    Returns
    -------
    dict
        Dictionary where key is characteristic column name and value is list of
        dictionaries each with Source and Method keys.

    """
    return {'Secchi': [{'Source': 'APHA', 'Method': '2320-B'},
                       {'Source': 'ASTM', 'Method': 'D1889'},
                       {'Source': 'USEPA', 'Method': 'NRSA09 W QUAL (BOAT)'},
                       {'Source': 'USEPA', 'Method': '841-B-11-003'},],
            'DO': [{'Source': 'USEPA', 'Method': '360.2',},
                   {'Source': 'USEPA', 'Method': '130.1',},
                   {'Source': 'APHA', 'Method': '4500-O-G',},
                   {'Source': 'USEPA', 'Method': '160.3',},
                   {'Source': 'AOAC', 'Method': '973.45',},
                   {'Source': 'USDOI/USGS', 'Method': 'I-1576-78',},
                   {'Source': 'USDOI/USGS', 'Method': 'NFM 6.2.1-LUM',},
                   {'Source': 'ASTM', 'Method': 'D888(B)',},
                   {'Source': 'HACH', 'Method': '8157',},
                   {'Source': 'HACH', 'Method': '10360',},
                   {'Source': 'ASTM', 'Method': 'D3858',},
                   {'Source': 'ASTM', 'Method': 'D888(C)',},
                   {'Source': 'APHA', 'Method': '	4500-O-C',},
                   {'Source': 'USEPA', 'Method': '1002-8-2009',},
                   {'Source': 'APHA', 'Method': '2550',},
                   {'Source': 'USEPA', 'Method': '360.1',},
                   {'Source': 'USEPA', 'Method': '841-B-11-003',},
                   {'Source': 'ASTM', 'Method': 'D888-12',},
                   {'Source': 'YSI', 'Method': 'EXO WQ SONDE',},],
            'Temperature': [{'Source': 'USEPA', 'Method': '170.1'},
                            {'Source': 'USEPA', 'Method': '130.1'},
                            {'Source': 'USEPA', 'Method': '841-B-11-003'},
                            {'Source': 'APHA', 'Method': '2550'},
                            {'Source': 'YSI', 'Method': 'EXO WQ SONDE'},
                            {'Source': 'APHA', 'Method': '2550 B'},],
            'Salinity': [{'Source': 'YSI', 'Method': 'EXO WQ SONDE'},
                         {'Source': 'HACH', 'Method': '8160'},
                         {'Source': 'APHA', 'Method': '2520-B'},
                         {'Source': 'APHA', 'Method': '2130'},
                         {'Source': 'APHA', 'Method': '3.2-B'},
                         {'Source': 'APHA', 'Method': '2520-C'},],
            'pH': [{'Source': 'ASTM', 'Method': 'D1293(B)'},
                   {'Source': 'YSI', 'Method': 'EXO WQ SONDE'},
                   {'Source': 'USEPA', 'Method': '360.2'},
                   {'Source': 'USEPA', 'Method': '130.1'},
                   {'Source': 'USDOI/USGS', 'Method': 'I1586'},
                   {'Source': 'USDOI/USGS', 'Method': 'I-2587-85'},
                   {'Source': 'APHA', 'Method': '3.2-B'},
                   {'Source': 'HACH', 'Method': '8219'},
                   {'Source': 'AOAC', 'Method': '973.41'},
                   {'Source': 'APHA', 'Method': '4500-H'},
                   {'Source': 'APHA', 'Method': '2320'},
                   {'Source': 'USEPA', 'Method': '150.2'},
                   {'Source': 'USEPA', 'Method': '150.1'},
                   {'Source': 'USDOI/USGS', 'Method': 'I-1586-85'},
                   {'Source': 'USEPA', 'Method': '9040B'},
                   {'Source': 'HACH', 'Method': '8156'},
                   {'Source': 'ASTM', 'Method': 'D1293(A)'},
                   {'Source': 'APHA', 'Method': '4500-H+B'},],
            'Nitrogen': [{'Source': 'USEPA', 'Method': '353.1'},
                         {'Source': 'USEPA', 'Method': '353.2'},
                         {'Source': 'USEPA', 'Method': '353.2_M'},
                         {'Source': 'USEPA', 'Method': '353.3'},
                         {'Source': 'USEPA', 'Method': '6020'},
                         {'Source': 'USEPA', 'Method': '200.7'},
                         {'Source': 'USEPA', 'Method': '8321'},
                         {'Source': 'USEPA', 'Method': '365.1'},
                         {'Source': 'USEPA', 'Method': '365.3'},
                         {'Source': 'USEPA', 'Method': '300'},
                         {'Source': 'USEPA', 'Method': '300(A)'},
                         {'Source': 'USEPA', 'Method': '350.1'},
                         {'Source': 'USEPA', 'Method': '350.3'},
                         {'Source': 'USEPA', 'Method': '351.1'},
                         {'Source': 'USEPA', 'Method': '351.2'},
                         {'Source': 'USEPA', 'Method': '351.3 (TITRATION)'},
                         {'Source': 'USEPA', 'Method': '440'},
                         {'Source': 'USEPA', 'Method': '440(W)'},
                         {'Source': 'USEPA', 'Method': '440(S)'},
                         {'Source': 'AOAC', 'Method': '973.48'},
                         {'Source': 'USDOI/USGS', 'Method': 'I-4650-03'},
                         {'Source': 'USDOI/USGS', 'Method': 'I-2650-03'},
                         {'Source': 'USDOI/USGS', 'Method': 'I-4540-85'},
                         {'Source': 'ASTM', 'Method': 'D8083-16'},
                         {'Source': 'ASTM', 'Method': 'D5176'},
                         {'Source': 'ASTM', 'Method': 'D888(B)'},
                         {'Source': 'ASTM', 'Method': 'D3590(B)'},
                         {'Source': 'HACH', 'Method': '10208'},
                         {'Source': 'HACH', 'Method': '10071'},
                         {'Source': 'HACH', 'Method': '10072'},
                         {'Source': 'HACH', 'Method': '10242'},
                         {'Source': 'USDOE/ASD', 'Method': 'MS100'},
                         {'Source': 'LACHAT', 'Method': '31-107-04-3-A'},
                         {'Source': 'LACHAT', 'Method': '31-107-04-4-A'},
                         {'Source': 'BL', 'Method': '818-87T'},
                         {'Source': 'APHA_SM20ED', 'Method': '4500-N-C'},
                         {'Source': 'APHA_SM21ED', 'Method': '4500-N-B'},
                         {'Source': 'APHA', 'Method': '4500-N D'},
                         {'Source': 'APHA', 'Method': '4500-N'},
                         {'Source': 'APHA', 'Method': '4500-NOR(C)'},
                         {'Source': 'APHA', 'Method': '4500-NH3 B'},
                         {'Source': 'APHA', 'Method': '4500-NH3 D'},
                         {'Source': 'APHA', 'Method': '4500-NH3(G)'},
                         {'Source': 'APHA', 'Method': '4500-NH3(H)'},
                         {'Source': 'APHA', 'Method': '4500-NO3(C)'},
                         {'Source': 'APHA', 'Method': '4500-NO3(B)'},
                         {'Source': 'APHA', 'Method': '4500-NO3(E)'},
                         {'Source': 'APHA', 'Method': '4500-NO3(I)'},
                         {'Source': 'APHA', 'Method': '4500-NO3(F)'},
                         {'Source': 'APHA', 'Method': '4500-NOR(B)'},
                         {'Source': 'APHA', 'Method': '4500-NORGB'},
                         {'Source': 'APHA', 'Method': '4500-NORG D'},
                         {'Source': 'APHA', 'Method': '4500-CL(E)'},
                         {'Source': 'APHA', 'Method': '5310-B'},
                         {'Source': 'APHA', 'Method': '4500-P-J'},
                         {'Source': 'APHA', 'Method': '4500-N-C'},],
            'Conductivity': [{'Source': 'ASTM', 'Method': 'D1125(A)'},
                             {'Source': 'APHA', 'Method': '2510'},
                             {'Source': 'USEPA', 'Method': '9050A'},
                             {'Source': 'USEPA', 'Method': '360.2'},
                             {'Source': 'USEPA', 'Method': '130.1'},
                             {'Source': 'USEPA', 'Method': '9050'},
                             {'Source': 'APHA', 'Method': '2510B'},
                             {'Source': 'APHA', 'Method': '2550'},
                             {'Source': 'HACH', 'Method': '8160'},
                             {'Source': 'USEPA', 'Method': '120.1'},
                             {'Source': 'USEPA', 'Method': '841-B-11-003'},
                             {'Source': 'YSI', 'Method': 'EXO WQ SONDE'},],
            'Carbon': [{'Source': 'USEPA', 'Method': '9060'},
                       {'Source': 'APHA_SM20ED', 'Method': '5310-B'},
                       {'Source': 'APHA', 'Method': '5310C'},
                       {'Source': 'APHA', 'Method': '5310-C'},
                       {'Source': 'USEPA', 'Method': '9060A'},
                       {'Source': 'AOAC', 'Method': '973.47'},
                       {'Source': 'USDOI/USGS', 'Method': 'O-1122-92'},
                       {'Source': 'USDOI/USGS', 'Method': 'O3100'},
                       {'Source': 'APHA', 'Method': '5310-D'},
                       {'Source': 'APHA (2011)', 'Method': '5310-C'},
                       {'Source': 'USEPA', 'Method': '415.1'},
                       {'Source': 'USEPA', 'Method': '415.3'},
                       {'Source': 'USEPA', 'Method': '502.1'},
                       {'Source': 'APHA', 'Method': '9222B'},
                       {'Source': 'USEPA', 'Method': '415.2'},
                       {'Source': 'APHA', 'Method': '5310-B'},
                       {'Source': 'APHA', 'Method': '4500-H+B'},],
            'Chlorophyll': [{'Source': 'YSI', 'Method': 'EXO WQ SONDE'},
                            {'Source': 'USEPA', 'Method': '446'},
                            {'Source': 'USEPA', 'Method': '170.1'},
                            {'Source': 'USEPA', 'Method': '445'},
                            {'Source': 'APHA', 'Method': '10200H(3)'},
                            {'Source': 'APHA', 'Method': '10200-H'},
                            {'Source': 'USEPA', 'Method': '353.2'},
                            {'Source': 'USEPA', 'Method': '447'},
                            {'Source': 'APHA', 'Method': '10200H(2)'},
                            {'Source': 'APHA', 'Method': '9222B'},
                            {'Source': 'APHA', 'Method': '5310-C'},],
            'Turbidity': [{'Source': 'USEPA', 'Method': '160.2_M'},
                          {'Source': 'USDOI/USGS', 'Method': 'I3860'},
                          {'Source': 'USEPA', 'Method': '180.1'},
                          {'Source': 'USEPA', 'Method': '360.2'},
                          {'Source': 'USEPA', 'Method': '130.1'},
                          {'Source': 'APHA', 'Method': '2130'},
                          {'Source': 'APHA', 'Method': '2310 B'},
                          {'Source': 'APHA', 'Method': '2130-B'},
                          {'Source': 'HACH', 'Method': '8195'},
                          {'Source': 'LECK MITCHELL', 'Method': 'M5331'},
                          {'Source': 'ASTM', 'Method': 'D1889'},],
            'Sediment': [],
            'Fecal_Coliform': [{'Source': 'IDEXX', 'Method': 'COLILERT-18'},
                               {'Source': 'APHA_SM22ED', 'Method': '9222D'},
                               {'Source': 'APHA', 'Method': '9221-E'},
                               {'Source': 'AOAC', 'Method': '978.23'},
                               {'Source': 'NIOSH', 'Method': '600'},
                               {'Source': 'HACH', 'Method': '8001(A2)'},
                               {'Source': 'HACH', 'Method': '8074(A)'},
                               {'Source': 'APHA', 'Method': '9230-D'},
                               {'Source': 'USEPA', 'Method': '1103.1'},
                               {'Source': 'APHA', 'Method': '9222D'},
                               {'Source': 'APHA', 'Method': '9222A'},
                               {'Source': 'APHA', 'Method': '3.2-B'},
                               {'Source': 'APHA', 'Method': '10200-G'},
                               {'Source': 'APHA', 'Method': '9222-E'},
                               {'Source': 'APHA', 'Method': '9221-B'},],
            'E_coli': [{'Source': 'APHA', 'Method': '9221A-B-C-F'},
                       {'Source': 'IDEXX', 'Method': 'COLILERT/2000'},
                       {'Source': 'MICROLOGY LABS', 'Method': 'EASYGEL'},
                       {'Source': 'IDEXX', 'Method': 'COLILERT'},
                       {'Source': 'IDEXX', 'Method': 'COLISURE'},
                       {'Source': 'USEPA', 'Method': '360.2'},
                       {'Source': 'APHA_SM22ED', 'Method': '9223-B'},
                       {'Source': 'IDEXX', 'Method': 'COLILERT-18'},
                       {'Source': 'IDEXX', 'Method': 'COLILERT-182000'},
                       {'Source': 'USEPA', 'Method': '130.1'},
                       {'Source': 'USEPA', 'Method': '1103.1 (MODIFIED)'},
                       {'Source': 'MICROLOGY LABS', 'Method': 'COLISCAN'},
                       {'Source': 'APHA', 'Method': '9222D'},
                       {'Source': 'APHA', 'Method': '9213-D'},
                       {'Source': 'HACH', 'Method': '10029'},
                       {'Source': 'APHA', 'Method': '9222G'},
                       {'Source': 'CDC',
                        'Method':'CDC - E. coli and Shigella'},
                       {'Source': 'CDC', 'Method': 'E. COLI AND SHIGELLA'},
                       {'Source': 'USEPA', 'Method': '1603'},
                       {'Source': 'APHA', 'Method': '9213D'},
                       {'Source': 'USEPA', 'Method': '1103.1'},
                       {'Source': 'USEPA', 'Method': '1604'},
                       {'Source': 'APHA', 'Method': '9223-B'},
                       {'Source': 'APHA', 'Method': '9223-B-04'},
                       {'Source': 'APHA', 'Method': '9222B,G'},
                       {'Source': 'USEPA', 'Method': '600-R-00-013'},
                       {'Source': 'APHA', 'Method': '9221-F'},
                       {'Source': 'USDOI/USGS', 'Method': '10029'},
                       {'Source': 'NIOSH', 'Method': '1604'},
                       {'Source': 'APHA', 'Method': '"9222B	G"'},
                       {'Source': 'APHA', 'Method': '9223B'},
                       {'Source': 'MODIFIED COLITAG',
                        'Method': 'ATP D05-0035'},
                       {'Source': 'ASTM', 'Method': 'D5392'},
                       {'Source': 'HACH', 'Method': '10018'},
                       {'Source': 'USEPA', 'Method': '1600'},],
            'Phosphorus': [{'Source': 'APHA', 'Method': '3125'},
                           {'Source': 'APHA', 'Method': '4500-P-C'},
                           {'Source': 'USEPA', 'Method': 'IO-3.3'},
                           {'Source': 'USEPA', 'Method': '200.7_M'},
                           {'Source': 'USEPA', 'Method': '200.9'},
                           {'Source': 'USEPA', 'Method': '200.7(S)'},
                           {'Source': 'LACHAT', 'Method': '10-115-01-1-F'},
                           {'Source': 'APHA_SM21ED', 'Method': '4500-P-G'},
                           {'Source': 'USEPA', 'Method': '351.3(C)'},
                           {'Source': 'LACHAT', 'Method': '10-115-01-4-B'},
                           {'Source': 'USEPA', 'Method': '365.2'},
                           {'Source': 'ASA(2ND ED.)', 'Method': '24-5.4'},
                           {'Source': 'USEPA', 'Method': '300.1'},
                           {'Source': 'USEPA', 'Method': '365_M'},
                           {'Source': 'USEPA', 'Method': '365.1'},
                           {'Source': 'APHA', 'Method': '4500-NH3(C)'},
                           {'Source': 'USEPA', 'Method': '300'},
                           {'Source': 'APHA', 'Method': '4500-NO2(B)'},
                           {'Source': 'APHA', 'Method': '4500-P-H'},
                           {'Source': 'USEPA', 'Method': '300(A)'},
                           {'Source': 'USEPA', 'Method': '350.1'},
                           {'Source': 'USEPA', 'Method': '200.7(W)'},
                           {'Source': 'USEPA', 'Method': '351.2'},
                           {'Source': 'USEPA', 'Method': '365.3'},
                           {'Source': 'USDOI/USGS', 'Method': 'I2600(W)'},
                           {'Source': 'USDOI/USGS', 'Method': 'I2601'},
                           {'Source': 'APHA', 'Method': '4500-P B'},
                           {'Source': 'USEPA', 'Method': '6010B'},
                           {'Source': 'USEPA', 'Method': 'ICP-AES'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-4610-91'},
                           {'Source': 'APHA', 'Method': '3030 E'},
                           {'Source': 'APHA', 'Method': '10200-F'},
                           {'Source': 'ASTM', 'Method': 'D3977'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-4650-03'},
                           {'Source': 'USEPA', 'Method': '440(S)'},
                           {'Source': 'USEPA', 'Method': '200.8(W)'},
                           {'Source': 'USDOI/USGS', 'Method': 'I1602'},
                           {'Source': 'APHA', 'Method': '4500-P-E'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-2650-03'},
                           {'Source': 'APHA', 'Method': '4500-NOR(C)'},
                           {'Source': 'APHA', 'Method': '4500-P'},
                           {'Source': 'ASTM', 'Method': 'D888(B)'},
                           {'Source': 'ASTM', 'Method': 'D515(A)'},
                           {'Source': 'HACH', 'Method': '10210'},
                           {'Source': 'HACH', 'Method': '8190'},
                           {'Source': 'HACH', 'Method': '10242'},
                           {'Source': 'USDOE/ASD', 'Method': 'MS100'},
                           {'Source': 'USEPA', 'Method': '6010A'},
                           {'Source': 'APHA', 'Method': '4500-F-E'},
                           {'Source': 'USEPA', 'Method': '200.7'},
                           {'Source': 'APHA', 'Method': '2540-D'},
                           {'Source': 'APHA', 'Method': '4500-P-F'},
                           {'Source': 'USEPA', 'Method': '8321'},
                           {'Source': 'USEPA', 'Method': '200.15'},
                           {'Source': 'USEPA', 'Method': '353.2'},
                           {'Source': 'USEPA', 'Method': '6020A'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-1601-85'},
                           {'Source': 'USEPA', 'Method': '200.2'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-4600-85'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-4607'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-4602'},
                           {'Source': 'APHA (1999)', 'Method': '4500-P-E'},
                           {'Source': 'APHA', 'Method': '4500-H'},
                           {'Source': 'USEPA', 'Method': '6010C'},
                           {'Source': 'USEPA', 'Method': '365.4'},
                           {'Source': 'USDOI/USGS', 'Method': 'I6600'},
                           {'Source': 'USEPA', 'Method': '200.8'},
                           {'Source': 'USEPA', 'Method': '351.1'},
                           {'Source': 'HACH', 'Method': '10209'},
                           {'Source': 'USEPA	', 'Method': '6020'},
                           {'Source': 'ASTM', 'Method': 'D515(B)'},
                           {'Source': 'USEPA', 'Method': '624'},
                           {'Source': 'APHA', 'Method': '2340B'},
                           {'Source': 'APHA', 'Method': '9222B'},
                           {'Source': 'USEPA', 'Method': '440'},
                           {'Source': 'APHA', 'Method': '2540-C'},
                           {'Source': 'USEPA', 'Method': '353.2_M'},
                           {'Source': 'APHA', 'Method': '4500-P-J'},
                           {'Source': 'APHA', 'Method': '9223-B'},
                           {'Source': 'APHA', 'Method': '4500-P-I'},
                           {'Source': 'USEPA', 'Method': '610'},
                           {'Source': 'APHA', 'Method': '4500-N-C'},
                           {'Source': 'APHA', 'Method': '4500-P-D'},
                           {'Source': 'APHA', 'Method': '4500-P E'},
                           {'Source': 'APHA', 'Method': '4500-P F'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-2610-91'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-2607'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-2606'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-2601-90'},
                           {'Source': 'USDOI/USGS', 'Method': 'I-6600-88'},
                           {'Source': 'ASTM', 'Method': 'D515'},],
            }
