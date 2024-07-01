import pytest
from sqlmodel import Sequence
from datetime import datetime, UTC, timedelta
from ewxpwsdb.station_readings import StationReadings #type: ignore
from ewxpwsdb.db.models import WeatherStation, Reading #type: ignore

from ewxpwsdb.collector import Collector #type: ignore
from ewxpwsdb.time_intervals import UTCInterval #type: ignore

# do this only once
@pytest.fixture(scope = 'module')
def db_with_readings(db_with_data, weather_station):
    """insert readings into our test database for the station type sent"""
    test_collector = Collector(station = weather_station, engine = db_with_data)
    yesterday_interval = UTCInterval.one_day_interval()
    earlier_interval = UTCInterval(start = yesterday_interval.start - timedelta(days=3), end =  yesterday_interval.end - timedelta(days=3))

    x = test_collector.request_and_store_weather_data_utc(earlier_interval)
    x = test_collector.request_and_store_weather_data_utc(yesterday_interval)
    test_collector.close()
    del(test_collector)

    return db_with_data
    
    # TODO: code is not setup for this but eventually, design so it can roll back inserts
    # and use a yield here to remove the data.  this is not essential but good testing 
    # hygiene to leave the database the way we found it

@pytest.fixture(scope = "module")
def test_station_readings(weather_station, db_with_readings):
    return StationReadings(station = weather_station, engine=db_with_readings)
        
def test_instantiate_station_readings_from_code(test_station_code, db_with_readings):
    station_readings = StationReadings.from_station_code(station_code=test_station_code, engine=db_with_readings)
    assert isinstance(station_readings, StationReadings)
    assert isinstance(station_readings.station, WeatherStation)
    assert station_readings.station.station_code == test_station_code


def test_instantiate_station_readings(weather_station, db_with_readings):
    station_readings = StationReadings(station = weather_station, engine=db_with_readings)
    assert isinstance(station_readings, StationReadings)
    assert isinstance(station_readings.station, WeatherStation)
    assert station_readings.station.station_code == weather_station.station_code

def test_station_readings_has_readings(test_station_readings):
    assert test_station_readings.has_readings()

def test_station_readings_latest_reading(test_station_readings):
    reading = test_station_readings.latest_reading()
    assert isinstance(reading, Reading)
    assert reading.id is not None
    assert reading.atmp is not None
    assert isinstance( reading.atmp, float)
    assert isinstance( reading.data_datetime, datetime)
    from ewxpwsdb.time_intervals import is_utc
    assert is_utc(reading.data_datetime)
    
    # recent reading may not be the same date as today if run around midnight UTC 
    # because recent weather data is at least 15 minutes delayed, 
    # so just check that date of most recent reading is today or yesterday
   
    assert reading.data_datetime.date() - datetime.now(UTC).date() <= timedelta(days = 1)


def test_station_readings_recent_readings(test_station_readings):
    readings = test_station_readings.recent_readings(n = 5)
    assert isinstance(readings, list)
    assert len(readings) > 0
    reading = readings[0]
    assert isinstance(reading, Reading)
    assert reading.id is not None
    assert reading.atmp is not None
    assert isinstance( reading.atmp, float)

def test_station_readings_first_reading_datetime(test_station_readings):
    dt = test_station_readings.first_reading_date()  
    assert isinstance(dt, datetime)
    # see comment above about checking dates
    assert dt.date() - datetime.now(UTC).date() <= timedelta(days = 1)

def test_station_readings_by_interval(test_station_readings):
    test_interval = UTCInterval.previous_interval(delta_mins=60)
    readings = test_station_readings.readings_by_interval_utc(test_interval)
    assert isinstance(readings, list)
    assert len(readings) > 0 # stations that read every 30 minutes should have at least 1
    assert isinstance(readings[0], Reading)
    # the interval starts at most 29 minutes before hand, and asked for 60 minutes of readings, 
    # so at most a reading would be 100 minutes ago
    assert ( readings[0].data_datetime - datetime.now(UTC) ) < timedelta(minutes = 100)
    
def test_station_readings_gap_intervals(test_station_readings):
    """ this essentially tests that this summary will even run.  
    Because it uses the UTCInterval class, start > end and both guaranted to be UTC datetimes
    """
    missing_readings_intervals = test_station_readings.missing_summary(
                        start_datetime = datetime.fromisoformat('2024-03-01T00:00+00:00'),
                        end_datetime= datetime.now(UTC)
                        )

    assert isinstance(missing_readings_intervals, list)    
    assert len(missing_readings_intervals) > 0 
    assert isinstance(missing_readings_intervals[0], UTCInterval)

        
            




