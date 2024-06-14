
import pytest
import json
from ewxpwsdb.db.models import WeatherStation
from ewxpwsdb.station import Station

def test_instantiate_station(test_station_code, db_with_data):
    test_station_object = Station.from_station_code(station_code = test_station_code, engine=db_with_data)    
    assert isinstance(test_station_object, Station)
    assert isinstance(test_station_object.weather_station, WeatherStation)
    assert test_station_object.weather_station.station_code == test_station_code


def test_station_object_methods(test_station_code, db_with_data):
    test_station_object = Station.from_station_code(station_code = test_station_code, engine=db_with_data)
    station_json = test_station_object.as_json()
    assert len(station_json) > 0
    assert isinstance(station_json, str)

    try: 
        station_dict = json.loads(station_json)
    except ValueError:
        pytest.fail("could not read response text JSON")

    assert station_dict['station_code'] == test_station_code

def test_station_object_can_create_collector(test_station_code, db_with_data):
    from ewxpwsdb.collector import Collector

    test_station_object = Station.from_station_code(station_code = test_station_code, engine=db_with_data)
    test_collector = Collector(station = test_station_object.weather_station, engine = db_with_data)
    assert isinstance(test_collector, Collector)
    assert test_collector.station_code == test_station_code
    # this depends on the station being on-line
    assert test_collector.weather_api.get_test_reading()
    


    