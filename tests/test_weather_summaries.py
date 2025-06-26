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
    
def test_daily_summary_fields(station_readings: StationReadings):
    
    two_days_ago = date.today() - timedelta(days = 2)
    yesterday:date = date.today() - timedelta(days = 2)
    
    daily_summaries:list[DailySummary] = station_readings.daily_summary(
                                                local_end_date=two_days_ago, 
                                                local_start_date=two_days_ago
                                                )
    
    assert isinstance( daily_summaries[0], DailySummary)
    ds:DailySummary = daily_summaries[0]
    assert 'atmp_avg_daily' in ds.model_fields
    assert isinstance(ds.atmp_avg_daily, float)
    assert ds.api_daily_frequency == station_readings.weather_api.expected_daily_frequency
    assert ds.record_count > 0
    assert ds.record_count <= station_readings.weather_api.expected_daily_frequency
    