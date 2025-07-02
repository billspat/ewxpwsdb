import pytest
from sqlalchemy import Engine
from sqlmodel import Sequence
from datetime import datetime, UTC, timedelta

from typing import Any

from ewxpwsdb.station_readings import StationReadings #type: ignore
from ewxpwsdb.db.models import WeatherStation, Reading #type: ignore
from ewxpwsdb.collector import Collector #type: ignore
from ewxpwsdb.time_intervals import UTCInterval #type: ignore
from ewxpwsdb.db.summary_models import HourlySummary, DailySummary

from datetime import date, timedelta
from logging import getLogger
logger = getLogger()
    
# do this only once
@pytest.fixture(scope = 'module')
def db_with_readings(db_with_data: Engine, weather_station: WeatherStation ):
    """insert readings into our test database for the station type sent
    
    the station API must be on line and have tree days data"""
    # NOTE THIS CAN FAIL IF WE ARE PAST MIDNIGHT UTC BECAUSE YESTERDAY IS TODAY
    collector = Collector(station = weather_station, engine = db_with_data)
    
    yesterday = date.today() - timedelta(days = 2)
    
    try:
        x = collector.request_and_store_weather_data_utc(UTCInterval.one_day_interval(yesterday))            
        x = collector.request_and_store_weather_data_utc(UTCInterval.one_day_interval(yesterday - timedelta(days = 1)))
        x = collector.request_and_store_weather_data_utc(UTCInterval.one_day_interval(yesterday - timedelta(days = 2)))
    except Exception as e:
        raise RuntimeError(f"Error getting 3 days of data from {weather_station.station_code} API:{e}")

    collector.close()
    del(collector)

    return db_with_data
    
    # TODO: code is not setup for this but eventually, design so it can roll back inserts
    # and use a yield here to remove the data.  this is not essential but good testing 
    # hygiene to leave the database the way we found it

@pytest.fixture(scope = "module")
def station_readings(weather_station: WeatherStation, db_with_readings: Any):
    return StationReadings(station = weather_station, engine=db_with_readings)

def test_hourly_summary_can_make_a_list(station_readings: StationReadings):
    """test if the daily summary function create a list of that model

    Args:
        station_readings (StationReadings): fixture of StationReadings class
        with some actual readings in it
    """
    yesterday = date.today() - timedelta(days = 2)

    hourly_summaries:list[HourlySummary] = station_readings.hourly_summary(
                                                local_end_date=yesterday, 
                                                local_start_date=yesterday
                                                )
    
    assert  isinstance(  hourly_summaries, list)
    assert len(hourly_summaries) > 0  

def test_hourly_summary_record_counts(station_readings: StationReadings):
    
    yesterday:date = date.today() - timedelta(days = 2)
    
    hourly_summaries:list[HourlySummary] = station_readings.hourly_summary(
                                                local_end_date=yesterday, 
                                                local_start_date=yesterday
                                                )
    
    assert isinstance( hourly_summaries[0], HourlySummary)
    hs:HourlySummary = hourly_summaries[0]
    assert 'api_hourly_frequency' in hs.model_fields
    assert hs.api_hourly_frequency == station_readings.weather_api.expected_hourly_frequency
    assert hs.record_count > 0
    assert hs.record_count <= station_readings.weather_api.expected_hourly_frequency
    
    
    
def test_daily_summary_can_make_a_list(station_readings: StationReadings):
    """test if the daily summary function create a list of that model

    Args:
        station_readings (StationReadings): fixture of StationReadings class
        with some actual readings in it
    """
    two_days_ago = date.today() - timedelta(days = 2)
    yesterday = date.today() - timedelta(days = 1)

    daily_summaries:list[DailySummary] = station_readings.daily_summary(
                                                local_end_date=two_days_ago, 
                                                local_start_date=two_days_ago
                                                )
    
    assert  isinstance(  daily_summaries, list)
    assert len(daily_summaries) > 0  

def test_hourly_summary_fields(station_readings: StationReadings):
    """test that the hourly sql is running and model is getting 
    fields.  The pydantic model already checks for types so no need to add specific
    type checks here.  Just check that the fields are there and not None.
    
    We don't test if individual sensors counts > 0 because some stations
    don't have all sensors and some sensors may not have data for a given day.

    Args:
        station_readings (StationReadings): _description_
    """
    yesterday:date = date.today() - timedelta(days = 2)
    
    hourly_summaries:list[HourlySummary] = station_readings.hourly_summary(
                                                local_end_date=yesterday, 
                                                local_start_date=yesterday
                                                )
    
    assert isinstance( hourly_summaries[0], HourlySummary)
    hs:HourlySummary = hourly_summaries[0]
    
    def check_hourly_summary_field(hs:HourlySummary, field_name: str):
        logger.debug(f"Checking hourly summary field: {field_name}")
        
        assert field_name in hs.model_fields
        field_value = getattr(hs, field_name, None)
        assert field_value is not None
        assert isinstance(field_value, (int, float))
        
    for field in [                
                'atmp_count', 
                'atmp_avg_hourly', 
                'atmp_max_hourly', 
                'atmp_min_hourly', 
                'relh_max_hourly', 
                'relh_avg_hourly', 
                'relh_min_hourly', 
                'pcpn_count', 
                'pcpn_total_hourly', 
                'lws_count', 
                'lws_wet_hourly', 
                'lws_pwet_hourly', 
                'wdir_avg_hourly', 
                'wdir_sdv_hourly', 
                'wspd_avg_hourly', 
                'wspd_max_hourly'
                ]:
        # summarie fields are named like 'atmp_avg_hourly' so we can get the sensor name
        # from the field name.  
        sensor_name = field.split('_')[0]
        if sensor_name in station_readings.weather_api.supported_variables:
            check_hourly_summary_field(hs, field)
                
    assert hs.api_hourly_frequency == station_readings.weather_api.expected_hourly_frequency

    
        
def test_daily_summary_fields(station_readings: StationReadings):
    """test that the daily sql is running and model is getting 
    fields.  The pydantic model already checks for types so no need to add specific
    type checks here.  Just check that the fields are there and not None.
    
    We don't test if individual sensors counts > 0 because some stations
    don't have all sensors and some sensors may not have data for a given day.

    Args:
        station_readings (StationReadings): _description_
    """
    two_days_ago = date.today() - timedelta(days = 2)
    yesterday:date = date.today() - timedelta(days = 2)
    
    daily_summaries:list[DailySummary] = station_readings.daily_summary(
                                                local_end_date=two_days_ago, 
                                                local_start_date=two_days_ago
                                                )
    
    assert isinstance( daily_summaries[0], DailySummary)
    ds:DailySummary = daily_summaries[0]
    
    def check_daily_summary_field(ds:DailySummary, field_name: str):
        logger.debug(f"Checking daily summary field: {field_name}")
        
        assert field_name in ds.model_fields
        field_value = getattr(ds, field_name, None)
        assert field_value is not None
        assert isinstance(field_value, (int, float))
        
    for field in ['atmp_avg_daily', 
                  'relh_avg_daily', 
                  'atmp_count', 
                  'relh_count', 
                  'pcpn_total_daily', 
                  'pcpn_count',
                  'lws_daily', 
                  'lws_count',
                  'wspd_avg_daily',
                  'wspd_count']:
        sensor_name = field.split('_')[0]
        if sensor_name in station_readings.weather_api.supported_variables:            
            check_daily_summary_field(ds, field)
    
    assert ds.api_daily_frequency == station_readings.weather_api.expected_daily_frequency
    assert ds.record_count > 0
    assert ds.record_count <= station_readings.weather_api.expected_daily_frequency    