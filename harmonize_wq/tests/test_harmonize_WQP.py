# -*- coding: utf-8 -*-
"""
This will import when run from CI because sys.path[0] == cur_dir
DIRPATH = r'D:\D_code\HWBI_update\ESI\harmonize-wq\harmonize_wq\tests'

This script doesn't test query/download of the data using dataretrieval,
instead the script is focused on processing, tidying and harmonizing data
results from a query read from a ?csv. The exception is the bounding box query
used to construct the query.

@author: jbousqui
"""
import os
import pytest
import geopandas
import pandas
from harmonize_wq import location
from harmonize_wq import harmonize
from harmonize_wq import convert
from harmonize_wq import wrangle
from harmonize_wq import clean

# CI
DIRPATH = os.path.dirname(os.path.realpath(__file__))

# Test datasets
test_dir = os.path.join(DIRPATH, 'data')

AOI = geopandas.read_file(r'https://github.com/USEPA/Coastal_Ecological_Indicators/raw/master/DGGS_Coastal/temperature_data/TampaBay.geojson')
# results for dataretrieval.wqp.what_sites(**query)
STATIONS = pandas.read_csv(os.path.join(test_dir, 'wqp_sites.txt'))
# These are split by parameter sets of 2 to keep them small but not mono-param
# 'Phosphorus' & 'Temperature, water'
NARROW_RESULTS = pandas.read_csv(os.path.join(test_dir, 'wqp_results.txt'))
ACTIVITIES = pandas.read_csv(os.path.join(test_dir, 'wqp_activities.txt'))
# 'Depth, Secchi disk depth' & Dissolved Oxygen
NARROW_RESULTS1 = pandas.read_csv(os.path.join(test_dir, 'wqp_results1.txt'))
# pH & Salinity
NARROW_RESULTS2 = pandas.read_csv(os.path.join(test_dir, 'wqp_results2.txt'))
# Nitrogen & Conductivity
NARROW_RESULTS3 = pandas.read_csv(os.path.join(test_dir, 'wqp_results3.txt'))
# Chlorophyll_a & Organic_carbon
NARROW_RESULTS4 = pandas.read_csv(os.path.join(test_dir, 'wqp_results4.txt'))
# Turbidity & Sediment
NARROW_RESULTS5 = pandas.read_csv(os.path.join(test_dir, 'wqp_results5.txt'))
# Nutrients and sediment additional characteristics
# NARROW_RESULTS6 = pandas.read_csv(os.path.join(test_dir, 'wqp_results6.txt'))
# Fecal Coliform and Ecoli
NARROW_RESULTS7 = pandas.read_csv(os.path.join(test_dir, 'wqp_results7.txt'))

# fixture to eventually test output writing (.shp)
# @pytest.fixture(scope="session")
# def out_dir(tmp_path_factory):
#     #return tmp_path_factory.mktemp("data") / "roads.shp"
#     temporary_dir = tmp_path_factory.mktemp("data")
#     yield temporary_dir
#     #shutil.rmtree(str(temporary_dir))  # Cleanup


def test_get_bounding_box():
    """
    Retrieve bounding box for GeoDataFrame

    Global Constants
    ----------
    AOI : geopandas.GeoDataFrame
        Geodataframe for Tampa Bay read from github
    """
    expected = ['-82.76095952246396',
                '27.47487752677648',
                '-82.37480995151799',
                '28.12535740372124']
    actual = wrangle.get_bounding_box(AOI).split(',')
    assert actual == expected


# def test_infer_CRS():
#     """
#     Test it infers where missing (not tested in test_harmonize_sites)
#     """
#     actual = infer_CRS(df_in, 4269, out_col='test_EPSG')
#     expected_flag = ''
#     assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
#     #assert actual.size
#     assert 'test_EPSG' in actual.columns


# def test_add_QA_flag():
#     """
#     Test it appends when QA_flag exists (not  in test_harmonize_sites)
#     """
#     actual = test_add_QA_flag(df_in, cond, flag)
@pytest.fixture(scope='session')
def merged_tables():
    """
    Merge narrow_results and activities tables. This fixture is used in some
    of the other harmonization functions that rely on wet/dry definitions.

    Returns
    -------
    merged_tables : pandas.DataFrame
        'Phosphorus' & 'Temperature, water' results merged with activities
    """
    df1 = NARROW_RESULTS
    df2 = ACTIVITIES
    # Fields to get (all for test instead?)
    df2_cols = ['ActivityTypeCode',
                'ActivityMediaName',
                'ActivityMediaSubdivisionName',
                'ActivityEndDate',
                'ActivityEndTime/Time',
                'ActivityEndTime/TimeZoneCode']
    return wrangle.merge_tables(df1, df2, df2_cols=df2_cols)


@pytest.fixture(scope='session')
def harmonized_tables():
    """
    Harmonize Nitrogen and Conductivity results in NARROW_RESULTS3. This
    fixture is used in some of the other tests.

    Returns
    -------
    df3_harmonized : pandas.DataFrame
        Harmonized results for Nitrogen and Conductivity.

    """
    harmonized_table = harmonize.harmonize_generic(NARROW_RESULTS3, 'Nitrogen')
    harmonized_table = harmonize.harmonize_generic(harmonized_table,
                                                   'Conductivity')
    return harmonized_table


def test_harmonize_all(harmonized_tables):
    """
    Test results from harmonize_all are same as individually run results

    Global Constants
    ----------
    NARROW_RESULTS3 : pandas.DataFrame
        Read from data/wqp_results3.txt.
    """
    actual = harmonize.harmonize_all(NARROW_RESULTS3)
    assert actual.size == harmonized_tables.size


def test_harmonize_depth():
    """
    Test function standardizes depth results correctly

    Global Constants
    ----------
    NARROW_RESULTS1 : pandas.DataFrame
        Read from data/wqp_results1.txt.
    """
    actual = clean.harmonize_depth(NARROW_RESULTS1)
    assert len(actual['Depth'].dropna()) == 13
    expected_unit = 'meter'
    assert str(actual.iloc[135227]['Depth'].units) == expected_unit


def test_harmonize_locations():
    """
    Test functions standardizes the sites correctly

    Global Constants
    ----------
    STATIONS : pandas.DataFrame
        Read from data/wqp_sites.txt.
    """
    actual = location.harmonize_locations(STATIONS)

    crs_col = 'HorizontalCoordinateReferenceSystemDatumName'
    expected_flag = crs_col + ': Bad datum OTHER, EPSG:4326 assumed'

    assert isinstance(actual, geopandas.geodataframe.GeoDataFrame)  # Test type
    assert actual.crs.name == 'WGS 84'  # Test for expected CRS
    assert actual.size == 1063506
    # TODO: confirm original fields un-altered
    # Test for expected columns
    for col in ['QA_flag', 'geometry']:
        assert col in actual.columns
    # Test new fields have expected dtype
    assert actual['geometry'].dtype == 'geometry'
    # assert actual['EPSG'].dtype == 'float64'  # Converted to int() later
    # Test flag & fix when un-recognized CRS (test on row[CRS]=='OTHER')
    # assert actual.iloc[3522]['EPSG'] == 4326.0  # Test fixed in new col
    assert actual.iloc[3522]['QA_flag'] == expected_flag  # Test flag
    # No changes not changes
    # Converted converted
    # Missing unit infered
    # Check QA_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_phosphorus(merged_tables):
    """
    Test function standardizes Phosphorus results correctly

    Global Constants
    ----------
    NARROW_RESULTS : pandas.DataFrame
        Read from data/wqp_results.txt.
    """
    # TODO: Test for expected dimensionalityError with NARROW_RESULTS?
    actual = harmonize.harmonize_generic(merged_tables, 'Phosphorus')  # mg/l
    # TODO: test conversion to moles and other non-standard units
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 16896735  # 17256240  # Test size
    # Test for expected columns
    for col in ['TP_Phosphorus', 'TDP_Phosphorus', 'Other_Phosphorus']:
        assert col in actual.columns
    # Number of results in each col
    assert len(actual['TP_Phosphorus'].dropna()) == 11243
    assert len(actual['TDP_Phosphorus'].dropna()) == 601
    assert len(actual['Other_Phosphorus'].dropna()) == 12968  # 1075 NAN

    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(merged_tables[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(merged_tables[orig_unit_col])

    # Inspect specific results
    expected_unit = 'milligram / liter'  # Desired units
    # TP
    out_col = 'TP_Phosphorus'
    actual.loc[((actual['CharacteristicName'] == 'Phosphorus') &
                (actual['ResultSampleFractionText'] == 'Total') &
                (actual[out_col].notna())), out_col]
    # Inspect specific result - where units are not converted
    assert actual.iloc[2866][orig_unit_col] == 'mg/l'  # Confirm orig unit
    assert str(actual.iloc[2866][out_col].units) == expected_unit
    expected_val = actual.iloc[2866][orig_val_col]  # Original value
    assert actual.iloc[2866][out_col].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    # Basis in units 'mg/l as P'
    # Confirm original unit
    assert actual.iloc[134674][orig_unit_col] == 'mg/l as P'
    assert str(actual.iloc[134674][out_col].units) == expected_unit
    # Confirm original measure
    assert actual.iloc[134674][orig_val_col] == 0.29
    assert actual.iloc[134674][out_col].magnitude == 0.29
    # Basis in units 'mg/l PO4'
    assert actual.iloc[142482][orig_unit_col] == 'mg/l PO4'  # Confirm orig unit
    assert str(actual.iloc[142482][out_col].units) == expected_unit
    # TODO: None with different units that get converted
    # Inspect specific result - where units missing
    assert str(actual.iloc[9738][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, mg/l assumed'
    assert actual.iloc[9738]['QA_flag'] == expected_flag
    # Check value unchanged for missing units
    expected_val = float(actual.iloc[9738][orig_val_col])  # Original value
    assert actual.iloc[9738][out_col].magnitude == expected_val  # Unchanged
    # Inspect specific result - where value missing
    assert str(actual.iloc[134943][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    actual_flags = actual.iloc[134943]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[19902][orig_val_col] == '*Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "*Not Reported" result cannot be used'
    actual_flags = actual.iloc[19902]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag

    # TDP
    out_col = 'TDP_Phosphorus'
    actual.loc[((actual['CharacteristicName'] == 'Phosphorus') &
                (actual['ResultSampleFractionText'] == 'Dissolved') &
                (actual[out_col].notna())), out_col]
    # Inspect specific result - where units are not converted
    assert actual.iloc[673][orig_unit_col] == 'mg/l'  # Confirm orig unit
    assert str(actual.iloc[673][out_col].units) == expected_unit
    expected_val = actual.iloc[673][orig_val_col]  # Original value
    assert actual.iloc[673][out_col].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    # Basis in units 'mg/l as P'
    idx = 134696
    assert actual.iloc[idx][orig_unit_col] == 'mg/l as P'  # Confirm orig unit
    assert str(actual.iloc[idx][out_col].units) == expected_unit
    assert actual.iloc[idx][orig_val_col] == 0.38  # Confirm original measure
    assert actual.iloc[idx][out_col].magnitude == 0.38
    # TODO: None with different units that get converted
    # Inspect specific result - where units missing
    # TODO: None missing units w/ value
    # Inspect specific result - where value missing
    assert str(actual.iloc[138475][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    actual_flags = actual.iloc[138475]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    # TODO: no bad value

    # Other
    out_col = 'Other_Phosphorus'
    # NOTE: these are neither labled 'Total' nor 'Dissolved'
    actual.loc[((actual['CharacteristicName'] == 'Phosphorus') &
                (actual['ResultSampleFractionText'].isna()) &
                (actual[out_col].notna())), out_col]
    # Inspect specific result - where units are not converted
    assert actual.iloc[19665][orig_unit_col] == 'mg/l'  # Confirm orig unit
    assert str(actual.iloc[19665][out_col].units) == expected_unit
    expected_val = float(actual.iloc[19665][orig_val_col])  # Original value
    assert actual.iloc[19665][out_col].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    # TODO: None with different units that get converted
    # Inspect specific result - where units missing
    # TODO: None missing units w/ value
    # Inspect specific result - where value missing
    assert str(actual.iloc[177611][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    actual_flags = actual.iloc[177611]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    # TODO: no bad value


#@pytest.mark.skip(reason="no change")
def test_harmonize_temperature():
    """
    Test function standardizes Temperature results correctly

    Global Constants
    ----------
    NARROW_RESULTS : pandas.DataFrame
        Read from data/wqp_results.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS, 'Temperature, water')
    actual2 = harmonize.harmonize_generic(NARROW_RESULTS.iloc[0:10],
                                          'Temperature, water',
                                          units_out='deg F')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 13301685  # Test size #14784040
    assert 'Temperature' in actual.columns  # Check for column
    assert len(actual['Temperature'].dropna()) == 346210  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[0][orig_unit_col] == 'deg C'  # Confirm orig unit
    expected_unit = 'degree_Celsius'  # Desired units
    assert str(actual.iloc[0]['Temperature'].units) == expected_unit
    expected_val = actual.iloc[0][orig_val_col]  # Original value
    assert actual.iloc[0]['Temperature'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[55013][orig_unit_col] == 'deg F'  # Confirm orig unit
    assert str(actual.iloc[55013]['Temperature'].units) == expected_unit
    assert actual.iloc[55013][orig_val_col] == '87'  # Confirm original measure
    assert actual.iloc[55013]['Temperature'].magnitude == 30.5555555555556
    # Inspect specific result - where units missing
    assert str(actual.iloc[143765][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, degC assumed'
    actual_flags = actual.iloc[143765]['QA_flag'].split('; ')
    assert actual_flags[1] == expected_flag  # Should be assessed 1st (flag 0)
    # Check value unchagned for missing units
    # TODO: values would stay the same (no conversion), but this example is nan

    # Inspect specific result - where value missing
    assert str(actual.iloc[143765][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual_flags[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[359504][orig_val_col] == 'Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "Not Reported" result cannot be used'
    assert actual.iloc[359504]['QA_flag'] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_secchi():
    """
    Test function standardizes Seccchi results correctly

    Global Constants
    ----------
    NARROW_RESULTS1 : pandas.DataFrame
        Read from data/wqp_results1.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS1,
                                         'Depth, Secchi disk depth')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 11818094  # Test size
    assert 'Secchi' in actual.columns  # Check for column
    assert len(actual['Secchi'].dropna()) == 69144  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS1[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS1[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[1][orig_unit_col] == 'm'  # Confirm orig unit
    expected_unit = 'meter'  # Desired units
    assert str(actual.iloc[1]['Secchi'].units) == expected_unit
    expected_val = float(actual.iloc[1][orig_val_col])  # Original value
    assert actual.iloc[1]['Secchi'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[369][orig_unit_col] == 'ft'  # Confirm orig unit
    assert str(actual.iloc[369]['Secchi'].units) == expected_unit
    assert actual.iloc[369][orig_val_col] == '1.5'  # Confirm original measure
    assert actual.iloc[369]['Secchi'].magnitude == 0.45719999999999994
    # Inspect specific result - where units missing
    assert str(actual.iloc[347590][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, m assumed'
    actual_flags = actual.iloc[347590]['QA_flag'].split('; ')
    assert actual_flags[1] == expected_flag  # Should be assessed 1st (flag 0)
    # Check value unchanged for missing units
    # TODO: values would stay the same (no conversion), but this example is nan

    # Inspect specific result - where value missing
    assert str(actual.iloc[347590][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual_flags[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[347589][orig_val_col] == 'Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "Not Reported" result cannot be used'
    assert actual.iloc[347589]['QA_flag'] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_DO():
    """
    Test function standardizes Dissolved oxygen (DO) results correctly

    Global Constants
    ----------
    NARROW_RESULTS1 : pandas.DataFrame
        Read from data/wqp_results1.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS1,
                                         'Dissolved oxygen (DO)')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 11818094  # Test size
    assert 'DO' in actual.columns  # Check for column
    assert len(actual['DO'].dropna()) == 278395  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS1[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS1[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[0][orig_unit_col] == 'mg/l'  # Confirm orig unit
    expected_unit = 'milligram / liter'  # Desired units
    assert str(actual.iloc[0]['DO'].units) == expected_unit
    expected_val = float(actual.iloc[0][orig_val_col])  # Original value
    assert actual.iloc[0]['DO'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[4][orig_unit_col] == '%'  # Confirm orig unit
    assert str(actual.iloc[4]['DO'].units) == expected_unit
    assert actual.iloc[4][orig_val_col] == '68.7'  # Confirm original measure
    assert actual.iloc[4]['DO'].magnitude == 5.676222371166
    # TODO: add tests for 99637 in ppm? Currently ppm == mg/l
    # Inspect specific result - where units missing
    assert str(actual.iloc[6816][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, mg/l assumed'
    actual_flags = actual.iloc[6816]['QA_flag'].split('; ')
    assert actual_flags[1] == expected_flag
    # Check value unchagned for missing units
    # TODO: values would stay the same (no conversion), but this example is '*Not Reported'

    # Inspect specific result - where value missing
    assert str(actual.iloc[130784][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[130784]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[6816][orig_val_col] == '*Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "*Not Reported" result cannot be used'
    assert actual.iloc[6816]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_salinity():
    """
    Test function standardizes Salinity results correctly

    Units in test data: '0/00', 'PSS', 'mg/mL @25C', nan, 'ppt', 'ppth'

    Global Constants
    ----------
    NARROW_RESULTS2 : pandas.DataFrame
        Read from data/wqp_results2.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS2, 'Salinity',
                                         units_out='PSS')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 12181392  # Test size
    assert 'Salinity' in actual.columns  # Check for column
    assert len(actual['Salinity'].dropna()) == 185562  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS2[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS2[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[3][orig_unit_col] == 'PSS'  # Confirm orig unit
    expected_unit = 'Practical_Salinity_Units'  # Desired units
    assert str(actual.iloc[3]['Salinity'].units) == expected_unit
    expected_val = float(actual.iloc[3][orig_val_col])  # Original value
    assert actual.iloc[3]['Salinity'].magnitude == expected_val  # Unchanged

    # Inspect specific result - where units converted (ptth)
    assert actual.iloc[0][orig_unit_col] == 'ppth'  # Confirm orig unit
    assert str(actual.iloc[0]['Salinity'].units) == expected_unit
    assert actual.iloc[0][orig_val_col] == '40'  # Confirm original measure
    assert actual.iloc[0]['Salinity'].magnitude == 40
    # Inspect specific result - where units converted (mg/ml)
    # TODO: need a different test value (something weird here)
    assert actual.iloc[335435][orig_unit_col] == 'mg/mL @25C'  # Confirm unit
    assert str(actual.iloc[335435]['Salinity'].units)
    assert actual.iloc[335435][orig_val_col] == 120.0  # Confirm measure
    assert actual.iloc[335435]['Salinity'].magnitude == 125.28127999999992
    # 157.1; 4.014
    print(actual.iloc[335435]['Salinity'].magnitude)

    # Inspect specific result - where units missing
    assert str(actual.iloc[21277][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, PSS assumed'
    actual_flags = actual.iloc[21277]['QA_flag'].split('; ')
    assert actual_flags[1] == expected_flag
    # Check value unchagned for missing units
    # TODO: values would stay the same (no conversion), but this example is '*Not Reported'

    # Inspect specific result - where value missing
    assert str(actual.iloc[69781][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[69781]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[21277][orig_val_col] == '*Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "*Not Reported" result cannot be used'
    assert actual.iloc[21277]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_pH():
    """
    Test function standardizes pH results correctly

    Global Constants
    ----------
    NARROW_RESULTS2 : pandas.DataFrame
        Read from data/wqp_results2.txt.
    """
    # actual1 = harmonize.harmonize_pH(NARROW_RESULTS2, units='dimensionless')
    actual = harmonize.harmonize_generic(NARROW_RESULTS2, 'pH')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 12181392  # Test size
    assert 'pH' in actual.columns  # Check for column
    assert len(actual['pH'].dropna()) == 152314  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS2[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS2[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[1][orig_unit_col] == 'None'  # Confirm orig unit
    expected_unit = 'dimensionless'  # Desired units
    assert str(actual.iloc[1]['pH'].units) == expected_unit
    expected_val = float(actual.iloc[1][orig_val_col])  # Original value
    assert actual.iloc[1]['pH'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[1][orig_unit_col] == 'None'  # Confirm orig unit
    assert str(actual.iloc[1]['pH'].units) == expected_unit
    assert actual.iloc[1][orig_val_col] == '8.18'  # Confirm original measure
    assert actual.iloc[1]['pH'].magnitude == 8.18
    # Inspect specific result - where units missing
    assert str(actual.iloc[195644][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, dimensionless assumed'
    actual_flags = actual.iloc[195644]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag
    # Check value unchanged for missing units
    expected_val = float(actual.iloc[195644][orig_val_col])  # Original value
    assert actual.iloc[195644]['pH'].magnitude == expected_val  # Unchanged

    # Inspect specific result - where value missing
    assert str(actual.iloc[77966][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[77966]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[2641][orig_val_col] == '*Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "*Not Reported" result cannot be used'
    assert actual.iloc[2641]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_nitrogen():
    """
    Test function standardizes Nitrogen results correctly

    Global Constants
    ----------
    NARROW_RESULTS3 : pandas.DataFrame
        Read from data/wqp_results3.txt.
    """
    # actual1 = harmonize.harmonize_Nitrogen(NARROW_RESULTS3, units='mg/l')
    actual = harmonize.harmonize_generic(NARROW_RESULTS3, 'Nitrogen')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size ==  16482  # Test size
    assert 'Nitrogen' in actual.columns  # Check for column
    assert len(actual['Nitrogen'].dropna()) == 182  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS3[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS3[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[55][orig_unit_col] == 'mg/l'  # Confirm orig unit
    expected_unit = 'milligram / liter'  # Desired units
    assert str(actual.iloc[55]['Nitrogen'].units) == expected_unit
    expected_val = float(actual.iloc[55][orig_val_col])  # Original value
    assert actual.iloc[55]['Nitrogen'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[245][orig_unit_col] == 'g/m**3'  # Confirm orig unit
    assert str(actual.iloc[245]['Nitrogen'].units) == expected_unit
    assert actual.iloc[245][orig_val_col] == '1'  # Confirm original measure
    assert actual.iloc[245]['Nitrogen'].magnitude == 1.0000000000000002
    # Inspect specific result - where units missing
    assert str(actual.iloc[211][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, mg/l assumed'
    actual_flags = actual.iloc[211]['QA_flag'].split('; ')
    assert actual_flags[1] == expected_flag
    # Check value unchagned for missing units
    # TODO: values would stay the same (no conversion), but this example is nan

    # Inspect specific result - where value missing
    assert str(actual.iloc[211][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[211]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[240][orig_val_col] == 'Not reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "Not reported" result cannot be used'
    assert actual.iloc[240]['QA_flag'].split('; ')[0] == expected_flag

    # TODO: add test case where 'g/kg'
    # TODO: add test case where 'cm3/g @STP'
    # TODO: add test case where 'cm3/g STP'


#@pytest.mark.skip(reason="no change")
def test_harmonize_conductivity():
    """
    Test function standardizes Conductivity results correctly

    Global Constants
    ----------
    NARROW_RESULTS3 : pandas.DataFrame
        Read from data/wqp_results3.txt.
    """
    #actual1 = harmonize.harmonize_Conductivity(NARROW_RESULTS3, units='uS/cm')
    actual = harmonize.harmonize_generic(NARROW_RESULTS3, 'Conductivity')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 16236  # Test size
    assert 'Conductivity' in actual.columns  # Check for column
    assert len(actual['Conductivity'].dropna()) == 59  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS3[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS3[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[79][orig_unit_col] == 'uS/cm'  # Confirm orig unit
    expected_unit = 'microsiemens / centimeter'  # Desired units
    assert str(actual.iloc[79]['Conductivity'].units) == expected_unit
    expected_val = float(actual.iloc[79][orig_val_col])  # Original value
    assert actual.iloc[79]['Conductivity'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[244][orig_unit_col] == 'mS/cm'  # Confirm orig unit
    assert str(actual.iloc[244]['Conductivity'].units) == expected_unit
    assert actual.iloc[244][orig_val_col] == '1'  # Confirm original measure
    assert actual.iloc[244]['Conductivity'].magnitude == 1000.0
    # Inspect specific result - where units missing
    assert str(actual.iloc[241][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, uS/cm assumed'
    actual_flags = actual.iloc[241]['QA_flag']
    assert actual_flags == expected_flag
    # Check value unchagned for missing units
    expected_val = float(actual.iloc[241][orig_val_col])  # Original value
    assert actual.iloc[241]['Conductivity'].magnitude == expected_val  # Unchanged

    # Inspect specific result - where value missing
    assert str(actual.iloc[242][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[242]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[243][orig_val_col] == 'Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "Not Reported" result cannot be used'
    assert actual.iloc[243]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_carbon_organic():
    """
    Test function standardizes Organic carbon results correctly

    Global Constants
    ----------
    NARROW_RESULTS4 : pandas.DataFrame
        Read from data/wqp_results4.txt.
    """
    #actual1 = harmonize.harmonize_Carbon_organic(NARROW_RESULTS4, units='mg/l')
    #actual2 = harmonize.harmonize_Carbon_organic(NARROW_RESULTS4, units='g/kg')
    actual = harmonize.harmonize_generic(NARROW_RESULTS4, 'Organic carbon')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 6906695  # Test size
    assert 'Carbon' in actual.columns  # Check for column
    assert len(actual['Carbon'].dropna()) == 30631  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS4[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS4[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[1][orig_unit_col] == 'mg/l'  # Confirm orig unit
    expected_unit = 'milligram / liter'  # Desired units
    assert str(actual.iloc[1]['Carbon'].units) == expected_unit
    expected_val = float(actual.iloc[1][orig_val_col])  # Original value
    assert actual.iloc[1]['Carbon'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[355][orig_unit_col] == '%'  # Confirm orig unit
    assert str(actual.iloc[355]['Carbon'].units) == expected_unit
    assert actual.iloc[355][orig_val_col] == '0.1'  # Confirm original measure
    assert actual.iloc[355]['Carbon'].magnitude == 1000.0
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, mg/l assumed'
    actual_flags = actual.iloc[103082]['QA_flag']
    assert actual_flags == expected_flag
    # Check value unchagned for missing units
    expected_val = float(actual.iloc[103082][orig_val_col])  # Original value
    assert actual.iloc[103082]['Carbon'].magnitude == expected_val  # Unchanged

    # Inspect specific result - where value missing
    assert str(actual.iloc[22044][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[22044]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[0][orig_val_col] == '*Non-detect'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "*Non-detect" result cannot be used'
    assert actual.iloc[0]['QA_flag'].split('; ')[0] == expected_flag
    # Moles test
    assert actual.iloc[103084][orig_unit_col] == 'umol'  # Confirm orig unit
    float(actual.iloc[103084][orig_val_col])  # Confirm original value
    assert str(actual.iloc[103084]['Carbon'].units) == expected_unit
    assert actual.iloc[103084]['Carbon'].magnitude == 0.0477424


#@pytest.mark.skip(reason="no change")
def test_harmonize_chlorophyll_a():
    """
    Test function standardizes Chlorophyll a results correctly

    Global Constants
    ----------
    NARROW_RESULTS4 : pandas.DataFrame
        Read from data/wqp_results4.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS4, 'Chlorophyll a')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 6803610  # Test size
    assert 'Chlorophyll' in actual.columns  # Check for column
    assert len(actual['Chlorophyll'].dropna()) == 68201  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS4[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS4[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[47190][orig_unit_col] == 'mg/l'  # Confirm orig unit
    expected_unit = 'milligram / liter'  # Desired units
    assert str(actual.iloc[47190]['Chlorophyll'].units) == expected_unit
    expected_val = float(actual.iloc[47190][orig_val_col])  # Original value
    assert actual.iloc[47190]['Chlorophyll'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[345][orig_unit_col] == 'ug/l'  # Confirm orig unit
    assert str(actual.iloc[345]['Chlorophyll'].units) == expected_unit
    assert actual.iloc[345][orig_val_col] == '2.28'  # Confirm original measure
    assert actual.iloc[345]['Chlorophyll'].magnitude == 0.00228
    # Inspect specific result - where units missing
    assert str(actual.iloc[12618][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, mg/l assumed'
    actual_flags = actual.iloc[12618]['QA_flag']
    assert actual_flags == expected_flag
    # Check value unchagned for missing units
    expected_val = float(actual.iloc[12618][orig_val_col])  # Original value
    assert actual.iloc[12618]['Chlorophyll'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where value missing
    assert str(actual.iloc[947][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[947]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[103081][orig_val_col] == "Not Reported"
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "Not Reported" result cannot be used'
    assert actual.iloc[103081]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_turbidity():
    """
    Test function standardizes Turbidity results correctly

    Units in test data: 'cm', 'mg/l SiO2', 'JTU', 'NTU', 'NTRU'

    Global Constants
    ----------
    NARROW_RESULTS5 : pandas.DataFrame
        Read from data/wqp_results5.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS5, 'Turbidity')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 8628100  # Test size
    assert 'Turbidity' in actual.columns  # Check for column
    assert len(actual['Turbidity'].dropna()) == 131013  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS5[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS5[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[1][orig_unit_col] == 'NTU'  # Confirm orig unit
    expected_unit = 'Nephelometric_Turbidity_Units'  # Desired units
    assert str(actual.iloc[1]['Turbidity'].units) == expected_unit
    expected_val = float(actual.iloc[1][orig_val_col])  # Original value
    assert actual.iloc[1]['Turbidity'].magnitude == expected_val  # Unchanged

    # Inspect specific result - where units converted
    assert actual.iloc[58433][orig_unit_col] == 'cm'  # Confirm orig unit
    assert str(actual.iloc[58433]['Turbidity'].units) == expected_unit
    assert actual.iloc[58433][orig_val_col] == '60'  # Confirm original measure
    assert actual.iloc[58433]['Turbidity'].magnitude == 8.17455929421168  #16.046015096322353
    # JTU -> NTU
    assert actual.iloc[100158][orig_unit_col] == 'JTU'  # Confirm orig unit
    assert str(actual.iloc[100158]['Turbidity'].units) == expected_unit
    assert actual.iloc[100158][orig_val_col] == 5.0  # Confirm original measure
    assert actual.iloc[100158]['Turbidity'].magnitude == 95.0773
    # mg/l SiO2 -> NTU
    assert actual.iloc[126494][orig_unit_col] == 'mg/l SiO2'  # Original unit
    assert str(actual.iloc[126494]['Turbidity'].units) == expected_unit
    assert actual.iloc[126494][orig_val_col] == '4.0'  # Confirm original measure
    assert actual.iloc[126494]['Turbidity'].magnitude == 30.378500000000003
    # NTRU == NTU
    assert actual.iloc[124849][orig_unit_col] == 'NTRU'  # Confirm orig unit
    assert str(actual.iloc[124849]['Turbidity'].units) == expected_unit
    assert actual.iloc[124849][orig_val_col] == '0.7'  # Confirm original measure
    assert actual.iloc[124849]['Turbidity'].magnitude == 0.7

    # Inspect specific result - where units missing
    assert str(actual.iloc[132736][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, NTU assumed'
    actual_flags = actual.iloc[132736]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag
    # Check value unchagned for missing units
    expected_val = float(actual.iloc[132736][orig_val_col])  # Original value
    assert actual.iloc[132736]['Turbidity'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where value missing
    assert str(actual.iloc[19988][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[19988]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[42][orig_val_col] == '*Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "*Not Reported" result cannot be used'
    assert actual.iloc[42]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_sediment():
    """
    Test function standardizes Sediment results correctly

    Units in test data: '%', mg/L', 'g/l', ''mg/l',

    Un-fixabl units in test data: mass/area (kg/ha),
                                  mass (g),
                                  mass/time (ton/day),
                                  mass/length/time (ton/day/ft)

    Global Constants
    ----------
    NARROW_RESULTS5 : pandas.DataFrame
        Read from data/wqp_results5.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS5,
                                         char_val='Sediment',
                                         units_out='g/kg')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 8628100  # Test size
    assert 'Sediment' in actual.columns  # Check for column
    assert len(actual['Sediment'].dropna()) == 37  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS5[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS5[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[132737][orig_unit_col] == 'g/kg'  # Confirm orig unit
    expected_unit = 'gram / kilogram'  # Desired units
    assert str(actual.iloc[132737]['Sediment'].units) == expected_unit
    expected_val = float(actual.iloc[132737][orig_val_col])  # Original value
    assert actual.iloc[132737]['Sediment'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[128909][orig_unit_col] == '%'  # Confirm orig unit
    assert str(actual.iloc[128909]['Sediment'].units) == expected_unit
    assert actual.iloc[128909][orig_val_col] == '17'  # Confirm original measure
    assert actual.iloc[128909]['Sediment'].magnitude == 170.0
    # Inspect specific result - where units missing
    assert str(actual.iloc[132738][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, g/kg assumed'
    actual_flags = actual.iloc[132738]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag
    # Check value unchagned for missing units
    expected_val = float(actual.iloc[132738][orig_val_col])  # Original value
    assert actual.iloc[132738]['Sediment'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where value missing
    assert str(actual.iloc[126342][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing value
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[126342]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[132739][orig_val_col] == 'Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "Not Reported" result cannot be used'
    assert actual.iloc[132739]['QA_flag'].split('; ')[0] == expected_flag
    # TODO: add units mg/l


#@pytest.mark.skip(reason="not implemented")
def test_harmonize_phosphorus_plus():
    """
    Test function standardizes varied Phosphorus results correctly

    Global Constants
    ----------
    NARROW_RESULTS6 : pandas.DataFrame
        Read from data/wqp_results6.txt.
    """

#@pytest.mark.skip(reason="not implemented")
def test_harmonize_nitrogen_plus():
    """
    Test function standardizes varied Nitrogen results correctly

    Global Constants
    ----------
    NARROW_RESULTS6 : pandas.DataFrame
        Read from data/wqp_results6.txt.
    """

#@pytest.mark.skip(reason="not implemented")
def test_harmonize_sediment_plus():
    """
    Test function standardizes varied Sediment results correctly

    Global Constants
    ----------
    NARROW_RESULTS6 : pandas.DataFrame
        Read from data/wqp_results6.txt.
    """


#@pytest.mark.skip(reason="no change")
def test_harmonize_fecal_coliform():
    """
    Test function standardizes Fecal Coliform results correctly

    Global Constants
    ----------
    NARROW_RESULTS7 : pandas.DataFrame
        Read from data/wqp_results7.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS7, 'Fecal Coliform')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 8778720  # Test size
    assert 'Fecal_Coliform' in actual.columns  # Check for column
    assert len(actual['Fecal_Coliform'].dropna()) == 68264  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS7[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS7[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[3][orig_unit_col] == 'cfu/100ml'  # Confirm orig unit
    expected_unit = 'Colony_Forming_Units / milliliter'  # Desired units
    assert str(actual.iloc[3]['Fecal_Coliform'].units) == expected_unit
    expected_val = float(actual.iloc[3][orig_val_col])  # Original value
    assert actual.iloc[3]['Fecal_Coliform'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[0][orig_unit_col] == '#/100ml'  # Confirm orig unit
    assert str(actual.iloc[0]['Fecal_Coliform'].units) == expected_unit
    assert actual.iloc[0][orig_val_col] == '2'  # Confirm original measure
    assert actual.iloc[0]['Fecal_Coliform'].magnitude == 2.0
    # Inspect specific result - where units missing
    assert str(actual.iloc[1][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasure/MeasureUnitCode: MISSING UNITS, CFU/(100ml) assumed'
    actual_flags = actual.iloc[1]['QA_flag'].split('; ')
    assert actual_flags[1] == expected_flag
    # Check value unchagned for missing units
    expected_val = float(actual.iloc[3][orig_val_col])  # Original value
    assert actual.iloc[3]['Fecal_Coliform'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where value missing
    assert str(actual.iloc[1][orig_val_col]) == '*Non-detect'  # Confirm missing
    # Confirm expected flag - for missing value
    expected_flag = 'ResultMeasureValue: "*Non-detect" result cannot be used; ResultMeasure/MeasureUnitCode: MISSING UNITS, CFU/(100ml) assumed'
    assert actual.iloc[1]['QA_flag'] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[75305][orig_val_col] == 'Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "Not Reported" result cannot be used'
    assert actual.iloc[75305]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_harmonize_E_Coli():
    """
    Test function standardizes Escherichia Coliform (E. Coli) results correctly

    Global Constants
    ----------
    NARROW_RESULTS7 : pandas.DataFrame
        Read from data/wqp_results7.txt.
    """
    actual = harmonize.harmonize_generic(NARROW_RESULTS7, 'Escherichia coli')
    # Test that the dataframe has expected type, size, cols, and rows
    assert isinstance(actual, pandas.core.frame.DataFrame)  # Test type
    assert actual.size == 8778720  # Test size
    assert 'E_coli' in actual.columns  # Check for column
    assert len(actual['E_coli'].dropna()) == 7205  # Number of results
    # Confirm orginal data was not altered
    orig_val_col = 'ResultMeasureValue'  # Values
    assert actual[orig_val_col].equals(NARROW_RESULTS7[orig_val_col])
    orig_unit_col = 'ResultMeasure/MeasureUnitCode'  # Units
    assert actual[orig_unit_col].equals(NARROW_RESULTS7[orig_unit_col])
    # Inspect specific result - where units are not converted
    assert actual.iloc[59267][orig_unit_col] == 'cfu/100ml'  # Confirm orig unit
    expected_unit = 'Colony_Forming_Units / milliliter'   # Desired units
    assert str(actual.iloc[59267]['E_coli'].units) == expected_unit
    expected_val = float(actual.iloc[59267][orig_val_col])  # Original value
    assert actual.iloc[59267]['E_coli'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where units converted
    assert actual.iloc[28804][orig_unit_col] == 'MPN/100ml'  # Confirm orig unit
    assert str(actual.iloc[28804]['E_coli'].units) == expected_unit
    assert actual.iloc[28804][orig_val_col] == '7.3'  # Confirm original measure
    assert actual.iloc[28804]['E_coli'].magnitude == 7.3
    # Inspect specific result - where units missing
    assert str(actual.iloc[108916][orig_unit_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered units
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    actual_flags = actual.iloc[108916]['QA_flag'].split('; ')
    assert actual_flags[0] == expected_flag
    # Check value unchagned for missing units
    expected_val = float(actual.iloc[59267][orig_val_col])  # Original value
    assert actual.iloc[59267]['E_coli'].magnitude == expected_val  # Unchanged
    # Inspect specific result - where value missing
    assert str(actual.iloc[28805][orig_val_col]) == 'nan'  # Confirm missing
    # Confirm expected flag - for missing/infered values
    expected_flag = 'ResultMeasureValue: missing (NaN) result'
    assert actual.iloc[28805]['QA_flag'].split('; ')[0] == expected_flag
    # Inspect specific result - un-usable non-numeric values
    assert actual.iloc[69168 ][orig_val_col] == '*Not Reported'
    # Confirm expected flag - for un-usable value
    expected_flag = 'ResultMeasureValue: "*Not Reported" result cannot be used'
    assert actual.iloc[69168 ]['QA_flag'].split('; ')[0] == expected_flag


#@pytest.mark.skip(reason="no change")
def test_conductivity_to_PSU(harmonized_tables):
    conductivity_series = harmonized_tables['Conductivity'].dropna()
    # With wrapper it should have to be converted to string first
    conductivity_series_str = conductivity_series.apply(str)
    actual = conductivity_series_str.apply(convert.conductivity_to_PSU)
    # No loss of rows
    assert len(actual) == len(conductivity_series)
    # Check it is dimensionless
    assert str(actual[0].units) == 'dimensionless'
    # Check conversion was accurate
    assert conductivity_series[0].magnitude == 111.0
    assert actual[0].magnitude == 0.057
    assert conductivity_series[244].magnitude == 1000.0
    assert actual[244].magnitude == 0.493


#@pytest.mark.skip(reason="no change")
def test_accept_methods(merged_tables):
    actual = clean.methods_check(merged_tables, 'Phosphorus')
    actual.sort()  # Order is inconsistent so it's sorted
    expected = ['365.1', '365.3', '365.4', '4500-P-E', '4500-P-F']
    assert actual == expected


#@pytest.mark.skip(reason="no change")
def test_datetime(harmonized_tables):
    # Testit
    actual = clean.datetime(harmonized_tables)
    # Check for dropped fields
    drop_fields = ['ActivityStartDate',
                   'ActivityStartTime/Time',
                   'ActivityStartTime/TimeZoneCode']
    for field in drop_fields:
        assert field not in actual.columns
    # Type for date field (not formated, just str)
    #actual['StartDate']
    # Type for time field
    assert isinstance(actual['Activity_datetime'][0],
                      pandas._libs.tslibs.timestamps.Timestamp)


#@pytest.mark.skip(reason="no change")
def test_split_col(harmonized_tables):
    # Testit with default QA
    actual_QA = wrangle.split_col(harmonized_tables)
    # Check for expected columns
    assert 'QA_Nitrogen' in actual_QA.columns
    assert 'QA_Conductivity' in actual_QA.columns
    assert 'QA_flag' not in actual_QA.columns

    # Testit with non-default column
    col = 'ResultAnalyticalMethod/MethodIdentifier'
    actual_methods = wrangle.split_col(harmonized_tables, col, 'MethodID')
    assert 'MethodID_Nitrogen' in actual_methods.columns
    assert 'MethodID_Conductivity' in actual_methods.columns
    assert col not in actual_methods.columns

    # TODO: test when out_col is list (i.e., Phosphorus)


#@pytest.mark.skip(reason="no change")
def test_split_table(harmonized_tables):
    # Note: it will do datetime() as well
    actual_main, actual_chars = wrangle.split_table(harmonized_tables)
    # Check rows stayed same
    assert len(actual_main) == len(harmonized_tables)
    assert len(actual_chars) == len(harmonized_tables)
    # Check columns expected
    expected = ['OrganizationIdentifier', 'OrganizationFormalName',
                'ActivityIdentifier', 'ProjectIdentifier',
                'MonitoringLocationIdentifier',
                'DetectionQuantitationLimitTypeName',
                'DetectionQuantitationLimitMeasure/MeasureValue',
                'DetectionQuantitationLimitMeasure/MeasureUnitCode',
                'ProviderName', 'QA_flag', 'Nitrogen', 'Speciation',
                'Conductivity', 'StartDate', 'Activity_datetime', 'Depth']
    assert list(actual_main.columns) == expected
    expected = ['ResultDetectionConditionText',
                'MethodSpecificationName', 'CharacteristicName',
                'ResultSampleFractionText', 'ResultMeasureValue',
                'ResultMeasure/MeasureUnitCode', 'MeasureQualifierCode',
                'ResultStatusIdentifier', 'StatisticalBaseCode',
                'ResultValueTypeName', 'ResultWeightBasisText',
                'ResultTimeBasisText', 'ResultTemperatureBasisText',
                'ResultParticleSizeBasisText', 'PrecisionValue',
                'ResultCommentText', 'USGSPCode',
                'ResultDepthHeightMeasure/MeasureValue',
                'ResultDepthHeightMeasure/MeasureUnitCode',
                'ResultDepthAltitudeReferencePointText',
                'SubjectTaxonomicName', 'SampleTissueAnatomyName',
                'ResultAnalyticalMethod/MethodIdentifier',
                'ResultAnalyticalMethod/MethodIdentifierContext',
                'ResultAnalyticalMethod/MethodName',
                'MethodDescriptionText', 'LaboratoryName',
                'AnalysisStartDate', 'ResultLaboratoryCommentText',
                'ActivityTypeCode', 'ActivityMediaName',
                'ActivityMediaSubdivisionName', 'ActivityEndDate',
                'ActivityEndTime/Time', 'ActivityEndTime/TimeZoneCode',
                'ActivityDepthHeightMeasure/MeasureValue',
                'ActivityDepthHeightMeasure/MeasureUnitCode',
                'ActivityDepthAltitudeReferencePointText',
                'ActivityTopDepthHeightMeasure/MeasureValue',
                'ActivityTopDepthHeightMeasure/MeasureUnitCode',
                'ActivityBottomDepthHeightMeasure/MeasureValue',
                'ActivityBottomDepthHeightMeasure/MeasureUnitCode',
                'ActivityConductingOrganizationText',
                'ActivityCommentText', 'SampleAquifer',
                'HydrologicCondition', 'HydrologicEvent',
                'SampleCollectionMethod/MethodIdentifier',
                'SampleCollectionMethod/MethodIdentifierContext',
                'SampleCollectionMethod/MethodName',
                'SampleCollectionEquipmentName', 'PreparationStartDate', ]
    assert list(actual_chars.columns) == expected
