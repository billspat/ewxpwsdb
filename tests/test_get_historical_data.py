import pytest
from sqlmodel import select, Session

from ewxpwsdb.db.database import Session
from ewxpwsdb.db.models import WeatherStation, APIResponse, Reading
from ewxpwsdb.collector import Collector
# from ewxpwsdb.db.models import WeatherStationStation
from ewxpwsdb.weather_apis.weather_api import WeatherAPI
from ewxpwsdb.time_intervals import previous_fourteen_minute_interval


@pytest.fixture(scope='module')
def station(station_type, db_with_data):
    with Session(db_with_data) as session:
        statement = select(WeatherStation).where(WeatherStation.station_type == station_type)
        results = session.exec(statement)
        weather_station = results.first()


    return(weather_station)


def test_get_historical_data(station, db_with_data):
    """Test collecting historical data as if the station was just added to the db
    this test should start with a db with only stations in it and no readings (scope is module for fixture)
    """
    if station.station_type == 'RAINWISE':
        pytest.fail("sorry testing historical data for RAINWISE is not working yet since it does not have current data")

    collector = Collector(station, engine=db_with_data)

    # there should be no readings in the db for this station
    some_readings = collector.get_readings(n=1)
    assert some_readings == []

    # fillr up! Don't allow overwrite to ensure that check is working
    # limit the number of days so the test doesn't take for-ever
    collector.get_historic_data(overwrite=False, days_limit=5)
    
    some_readings = collector.get_readings(n=10)
    print(f"example reading: {some_readings[0]}")
    assert some_readings != []
    assert len(some_readings) == 10

    # this should fail
    with pytest.raises(RuntimeError):
        collector.get_historic_data(overwrite=False, days_limit=1)

    collector.close()

    

    
