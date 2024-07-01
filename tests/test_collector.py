
# get a database with stations via fixtures
# get a station class via type
# pull data and store in database
# check that the data is in the db like we think it should

import pytest
from sqlmodel import Session
from datetime import datetime, timedelta, timezone

# from ewxpwsdb.db.database import Session
from ewxpwsdb.db.models import APIResponse, Reading
from ewxpwsdb.collector import Collector
# from ewxpwsdb.db.models import WeatherStationStation
from ewxpwsdb.weather_apis.weather_api import WeatherAPI
from ewxpwsdb.time_intervals import UTCInterval, previous_fourteen_minute_interval


@pytest.fixture()
def sample_interval():
    interval = UTCInterval.previous_interval(delta_mins=70)
    return interval


@pytest.fixture(scope='module')
def viable_interval(station_type):
    duration_min = 70

    # temporary adjustment for this down station, use 
    # if station_type == 'RAINWISE':
    #     # rainwise goes down, so set the period for when the station was up and there is data
    #     from datetime import datetime, UTC
    #     datetime_rainwise_was_working = datetime(year=2024, month=2, day=19, hour=12, minute=0, second=0, tzinfo=UTC)
    #     interval = UTCInterval.previous_interval(dtm = datetime_rainwise_was_working, delta_mins=duration_min) # previous_fourteen_minute_interval(datetime_rainwise_was_working)
    # else:
    interval = UTCInterval.previous_interval(delta_mins=duration_min)
    
    return(interval)

def test_collector_class(weather_station, db_with_data):
    """can we instantiate a collector object given a station table id?

    assumes station param is object is from the db  
    """
    # we are using a station instead of just an id so we can test the Collector class can get a station

    station_id = weather_station.id
    collector = Collector.from_station_id(station_id=station_id, engine=db_with_data)
    
    # can we instantiate the class?
    assert isinstance(collector, Collector)
    # is the station we sent the same one the collector pulled from the db
    assert collector.station.station_code == weather_station.station_code

    assert isinstance(collector.weather_api, WeatherAPI)    
    assert collector.current_api_response_record_ids == []
    assert collector.current_reading_ids == []
    assert isinstance(collector.id, int)
    collector.close()

def test_collector_class_from_station_code(test_station_code, db_with_data):
    """can we instantiate a collector object given a station code?
    
    assumes station param is object is from the db
    """
    collector = Collector.from_station_code(station_code=test_station_code, engine=db_with_data)
    
    # did we instantiate the class?
    assert isinstance(collector, Collector)
    # is the station we sent the same one the collector pulled from the db
    assert collector.station.station_code == test_station_code

    assert isinstance(collector.weather_api, WeatherAPI)    
    assert collector.current_api_response_record_ids == []
    assert collector.current_reading_ids == []
    assert isinstance(collector.id, int)
    collector.close()
    

@pytest.fixture(scope='module')
def station_collector(test_station_code, db_with_data):
    collector = Collector.from_station_code(station_code = test_station_code, engine=db_with_data)
    yield(collector)
    collector.close()

def test_collect_request(weather_station,db_with_data, station_collector):
    
    collector = station_collector

    # temporary adjustment for this down station, use 
    if weather_station.station_type == 'RAINWISE':
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
        session.close()

    assert isinstance(collector.current_reading_ids, list)
    assert len(collector.current_reading_ids) > 0 
    assert isinstance(collector.current_reading_ids[0], int)
    example_reading_id = collector.current_reading_ids[0]    
    
    with Session(engine) as session:    
        reading_from_db = session.get(Reading, example_reading_id)
        assert reading_from_db.id == example_reading_id
        assert isinstance(reading_from_db, Reading)
        session.close()


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
    assert isinstance(reading.atmp, float)

    #this depends on the ordering of the requests/responses and may or may not be true
    # change to look for this manually created id in the request_id's for all responses
    assert reading.request_id == response.request_id
    # check database foreign key in reading is in one of the current response ids
    assert reading.apiresponse_id in collector.current_api_response_record_ids

    # re-get one of the response from the database
    with Session(engine) as session:
        response_from_db = session.get(APIResponse, example_response_id)
        session.close()

    # attempt to save the same readings again and see if it fails
    # it should not, just re-insert the data!   

    current_reading_ids = collector.current_reading_ids
    resaved_reading_ids = collector.save_readings_from_responses(api_responses = response_from_db)

    assert current_reading_ids == resaved_reading_ids

    # with pytest.raises(Exception) as e_info:
    #     collector.save_readings_from_responses(api_responses = response_from_db)
    
    collector.close()


def test_collector_readings_api(viable_interval, db_with_data,station_collector):
    # must run after putting readings into the db
    today_interval = UTCInterval.one_day_interval()  # this defaults to getting the time range from midnight to now
    two_day_interval = UTCInterval(start = (today_interval.start - timedelta(days = 1)), end = today_interval.end)

    response_ids = station_collector.request_and_store_weather_data_utc(two_day_interval)
    assert len(response_ids) > 0 

    some_time_yesterday = UTCInterval(start=viable_interval.start - timedelta(days = 1), 
                           end = viable_interval.end - timedelta(days = 1)
                           )
    
    readings = station_collector.get_readings_by_date(some_time_yesterday)
    assert isinstance(readings, list)
    assert len(readings) > 0 
    assert isinstance(readings[0], Reading)
    assert readings[0].weatherstation_id == station_collector.station.id
    print(db_with_data)

    dt = station_collector.get_first_reading_date()
    assert isinstance(dt, datetime)
    assert dt.year == datetime.today().year

    reading = station_collector.get_latest_reading()
    
    assert isinstance(reading, Reading)
    assert (datetime.now(timezone.utc) - reading.data_datetime) < timedelta(minutes=21)

    readings = station_collector.get_readings(n = 4)
    assert len(readings) == 4
    assert isinstance(readings[0], Reading)

    # test api parameter for sorting
    readings = station_collector.get_readings(n =4, order_by ='desc')
    assert len(readings) == 4
    assert isinstance(readings[0], Reading)
    assert readings[0].weatherstation_id == station_collector.station.id
    
    readings = station_collector.get_readings(n =4, order_by ='asc')
    assert len(readings) == 4
    assert isinstance(readings[0], Reading)
    assert readings[0].weatherstation_id == station_collector.station.id
    station_collector.close()

def test_collector_retransform(viable_interval, db_with_data,station_collector):
    # get some data 
    n = 4
    readings = station_collector.get_readings(n =n, order_by ='asc')
    assert len(readings ) == n
    readings_interval = UTCInterval(start = readings[0].data_datetime, end = readings[-1].data_datetime)
    
    retransform_results = station_collector.retransform( readings_interval)
    assert isinstance(retransform_results, list)
    assert len(retransform_results) > 0

    # the API reqs that cover these readings will have many more readings than selected above    
    assert len(retransform_results) > n
    


    


    


