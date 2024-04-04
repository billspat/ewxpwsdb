
# get a database with stations via fixtures
# get a station class via type
# pull data and store in database
# check that the data is in the db like we think it should

import pytest
from sqlmodel import select, Session

from ewxpwsdb.db.database import Session
from ewxpwsdb.db.models import WeatherStation, APIResponse, Reading
from ewxpwsdb.collector import Collector
# from ewxpwsdb.db.models import WeatherStationStation
from ewxpwsdb.weather_apis.weather_api import WeatherAPI
from ewxpwsdb.time_intervals import UTCInterval, previous_fourteen_minute_interval


@pytest.fixture()
def sample_interval():
    interval = UTCInterval.previous_interval(delta_mins=70)
    return interval


#TODO start with a literal list of types, but copy the technique from ewx_pws package to loop through all types
@pytest.fixture(scope='module')
def station(station_type, db_with_data):
    with Session(db_with_data) as session:
        statement = select(WeatherStation).where(WeatherStation.station_type == station_type)
        results = session.exec(statement)
        weather_station = results.first()
    return(weather_station)


def test_collector_class(station, db_with_data):
    # we are using a station instead of just an id so we can test the Collector class can get a station

    station_id = station.id
    collector = Collector.from_station_id(station_id=station_id, engine=db_with_data)
    
    # can we instantiate the class?
    assert isinstance(collector, Collector)
    # is the station we sent the same one the collector pulled from the db
    assert collector.station.station_code == station.station_code

    assert isinstance(collector.weather_api, WeatherAPI)    
    assert collector.current_api_response_record_ids == []
    assert collector.current_reading_ids == []
    assert isinstance(collector.id, int)
    collector.close()


def test_collect_request(station,db_with_data):
    
    collector = Collector.from_station_id(station_id=station.id, engine=db_with_data)

    # temporary adjustment for this down station, use 
    if station.station_type == 'RAINWISE':
        # rainwise goes down, so set the period for when the station was up and there is data
        from datetime import datetime, UTC
        datetime_rainwise_was_working = datetime(year=2024, month=2, day=19, hour=12, minute=0, second=0, tzinfo=UTC)
        interval = previous_fourteen_minute_interval(datetime_rainwise_was_working)
    else:
        interval = UTCInterval.previous_interval(delta_mins=70)
    
    s,e = (interval.start, interval.end)

    # get weather data    
    try:
        collector.request_and_store_weather_data(start_datetime = s, end_datetime = e)
    except Exception as e:
        pytest.fail(f"raised exception on request: {e}")

    # test results
    assert isinstance(collector.current_api_response_record_ids, list)
    assert collector.current_api_response_record_ids[0] is not None

    example_response_id = collector.current_api_response_record_ids[0]

    assert isinstance(example_response_id, int)
    engine = db_with_data
    with Session(engine) as session:
        response_from_db = session.get(APIResponse, example_response_id)
        assert response_from_db.id == example_response_id
        assert isinstance(response_from_db, APIResponse)

    assert isinstance(collector.current_reading_ids, list)
    assert len(collector.current_reading_ids) > 0 
    assert isinstance(collector.current_reading_ids[0], int)
    example_reading_id = collector.current_reading_ids[0]
    
    
    with Session(engine) as session:    
        reading_from_db = session.get(Reading, example_reading_id)
        assert reading_from_db.id == example_reading_id
        assert isinstance(reading_from_db, Reading)


    responses = collector.current_responses
    assert isinstance(responses, list)
    response = responses[0]
    assert isinstance(response, APIResponse)
    assert isinstance(response.id, int)
    print(response.request_datetime)
    
    import datetime
    assert isinstance(response.request_datetime, datetime.datetime)
    assert response.request_datetime.date() == datetime.datetime.now(datetime.timezone.utc).date()


    readings = collector.current_readings
    assert isinstance(readings, list)
    # this assumes there is actually data here
    assert isinstance(readings[0], Reading)
    reading = readings[0]
    assert isinstance(reading.atemp, float)

    #this depends on the ordering of the requests/responses and may or may not be true
    # change to look for this manually created id in the request_id's for all responses
    assert reading.request_id == response.request_id
    # check database foreign key in reading is in one of the current response ids
    assert reading.apiresponse_id in collector.current_api_response_record_ids

    # re-get one of the response from the database
    with Session(engine) as session:
        response_from_db = session.get(APIResponse, example_response_id)

    # attempt to save the same readings again and see if it fails
    with pytest.raises(Exception) as e_info:
        collector.save_readings_from_responses(api_responses = response_from_db)
    
    collector.close()

