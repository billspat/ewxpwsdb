
from ewxpwsdb.db.models import WeatherStation, Reading, StationType, APIResponse

from ewxpwsdb.weather_apis import API_CLASS_TYPES
from ewxpwsdb.weather_apis.weather_api import WeatherAPI, Response

from datetime import datetime, timezone

from ewxpwsdb.db.importdata import read_station_table
import pytest, json, os, re

@pytest.fixture(scope = 'module')
def weather_stations(station_file):
    """ non database method for creating list of stations.  requires data file """
    stations = read_station_table(station_file)
    return(stations)

@pytest.fixture()
def weather_station_of_type(weather_stations, station_type):
    one_station_data = list(filter(lambda x: (x['station_type']==station_type), weather_stations))[0]
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
    
def test_can_create_weather_api_object(weather_station_of_type, station_type):


    wapi = API_CLASS_TYPES[weather_station_of_type.station_type](weather_station_of_type)
    assert wapi.station_type == station_type
    assert isinstance(wapi, WeatherAPI)
    assert wapi.sampling_interval in [5,15,30,60]

    utc_datetime = datetime.now(timezone.utc)

    assert isinstance(wapi._format_time(utc_datetime), str)

    assert isinstance(wapi.dt_local_from_utc(utc_datetime), datetime)

def test_weather_api_get_get_response(wapi):

    print(f"getting request of recent data from {wapi.weather_station.station_code} type {wapi.station_type}")
    responses = wapi.get_readings()
    assert isinstance(responses, list)
    assert len(responses) > 0 

    response = responses[0]
    assert isinstance(responses, list)
    assert len(responses ) > 0 
    assert isinstance(response, APIResponse)
    assert isinstance(response.response_text, str)

    try: 
        response_dict = json.loads(response.response_text)
    except ValueError:
        pytest.fail("could not read response text JSON")


    assert response.response_status_code == 200
    assert re.match("^http", response.request_url)







