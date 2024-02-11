
# get a database with stations via fixtures
# get a station class via type
# pull data and store in database
# check that the data is in the db like we think it should

import pytest
from sqlmodel import select, Session

from ewxpwsdb.db.database import Session
from ewxpwsdb.db.models import WeatherStation, APIResponse

#TODO start with a literal list of types, but copy the technique from ewx_pws package to loop through all types
@pytest.fixture()
def station(station_type, db_with_data):
    with Session(db_with_data) as session:
        statement = select(WeatherStation).where(WeatherStation.station_type == station_type)
        results = session.exec(statement)
        weather_station = results.first()
    return(weather_station)


from ewxpwsdb.collector import Collector
# from ewxpwsdb.db.models import WeatherStationStation
from ewxpwsdb.weather_apis.weather_api import WeatherAPI

def test_collector_class(station, db_with_data):
    # we are using a station instead of just an id so we can test the Collector class can get a station

    station_id = station.id
    collector = Collector(station_id=station_id, engine=db_with_data)
    
    # can we instantiate the class?
    assert isinstance(collector, Collector)
    # is the station we sent the same one the collector pulled from the db
    assert collector.station.station_code == station.station_code

    assert isinstance(collector.weather_api, WeatherAPI)    
    assert collector.current_api_response_records == []
    assert collector.current_readings == []
    assert isinstance(collector.id, int)
    collector.close()


def test_collect_request(station,db_with_data):
    
    collector = Collector(station_id=station.id, engine=db_with_data)

    try:
        collector.request_current_weather_data()
    except Exception as e:
        pytest.fail(f"raised exception on request: {e}")

    assert collector.current_api_response_records[0].id is not None

    saved_id = collector.current_api_response_records[0].id

    assert isinstance(saved_id, int)

    with Session(db_with_data) as session:
        response_from_db = session.get(APIResponse, saved_id)
        assert response_from_db.id == saved_id
        assert isinstance(response_from_db, APIResponse)


    collector.transform_current_weather_data()
    assert isinstance(collector.current_readings, list)
    assert len(collector.current_readings) > 0 


    collector.close()





