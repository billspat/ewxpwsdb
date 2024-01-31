
from ewxpwsdb.db.models import WeatherStation, Reading, StationType, APIResponse

from ewxpwsdb.weather_apis import API_CLASS_TYPES
from ewxpwsdb.weather_apis.weather_api import WeatherAPI, Response

from ewxpwsdb.db.importdata import read_station_table
import pytest, json, os

# from conftest import not_raises

@pytest.fixture(scope = 'module')
def station_file():
    test_file = 'data/test_stations.tsv'
    return(test_file)

@pytest.fixture(scope = 'module')
def weather_stations(station_file):
    """ non database method for creating list of stations.  requires data file """
    stations = read_station_table(station_file)
    return(stations)

@pytest.fixture()
def stype():
    return 'SPECTRUM'

@pytest.fixture()
def weather_station_of_type(weather_stations, stype):
    one_station_data = list(filter(lambda x: (x['station_type']==stype), weather_stations))[0]
    station = WeatherStation.model_validate(one_station_data) 
    yield(station)

@pytest.fixture()
def wapi(weather_station_of_type):
    return (API_CLASS_TYPES[weather_station_of_type.station_type](weather_station_of_type))


def test_can_create_station_from_file(station_file):
    assert(os.path.exists(station_file))

    stations = read_station_table(station_file)
    assert stations is not None
    assert isinstance(stations, list)
    station_data = stations[0]
    station = WeatherStation.model_validate(station_data) 
    assert isinstance(station, WeatherStation)
    assert isinstance(station.station_type, str)
    assert isinstance(station.api_config, str)

    try:
        api_config_dict = json.loads(station.api_config)
    except ValueError:
        pytest.fail("Unexpected Value error when jsonifying api_config string")
        
    assert isinstance(api_config_dict, dict)
    
def test_can_create_weather_api_object(weather_station_of_type, stype):
    wapi = API_CLASS_TYPES[weather_station_of_type.station_type](weather_station_of_type)
    assert wapi.station_type == stype
    assert isinstance(wapi, WeatherAPI)

def test_weather_api_get_get_response(wapi):

    print(f"getting request of recent data from {wapi.weather_station.station_code} type {wapi.station_type}")
    responses = wapi.get_readings()
    assert isinstance(responses, list)
    assert isinstance(responses[0], APIResponse)
    assert isinstance(responses[0].response_text, str)

    try: 
        response_dict = json.loads(responses[0].response_text)
    except ValueError:
        pytest.fail("could not read response text JSON")

    readings = wapi.transform(responses)

    assert isinstance(readings, list)


    assert len(readings) > 0
    assert isinstance(readings[0], Reading)





