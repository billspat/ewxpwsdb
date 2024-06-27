
import pytest
import json
from ewxpwsdb.db.models import WeatherStation
from ewxpwsdb.station import Station, WeatherStationDetail
from ewxpwsdb.collector import Collector


def test_instantiate_station(test_station_code, db_with_data):
    test_station_object = Station.from_station_code(station_code = test_station_code, engine=db_with_data)    
    assert isinstance(test_station_object, Station)
    assert isinstance(test_station_object.weather_station, WeatherStation)
    ws = test_station_object.weather_station
    assert test_station_object.weather_station.station_code == test_station_code
    assert isinstance(ws.active, bool)
    assert ws.active == True



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

    test_station_object = Station.from_station_code(station_code = test_station_code, engine=db_with_data)
    test_collector = Collector(station = test_station_object.weather_station, engine = db_with_data)
    assert isinstance(test_collector, Collector)
    assert test_collector.station_code == test_station_code
    # this depends on the station being on-line
    assert test_collector.weather_api.get_test_reading()
    
def test_weatherstation_detail(test_station_code, db_with_data):
    
    # get some data in there    
    collector = Collector.from_station_code(station_code=test_station_code, engine= db_with_data)
    collector.request_current_weather_data()

    ws = WeatherStationDetail.with_detail(engine = db_with_data, station_code = test_station_code)

    assert isinstance(ws, WeatherStationDetail)
    assert isinstance(ws.expected_readings_day, int)
    assert ws.expected_readings_hour in [60/5, 60/15, 60/30]
    assert ws.first_reading_datetime is not None
    
    


    