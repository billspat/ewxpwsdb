""" test of getting data via API, transform to readings and saving to the database"""

import pytest, json
import logging
from datetime import datetime

import pytest, json
from datetime import datetime, timedelta
from ewxpwsdb.time_intervals import tomorrow_utc, previous_fourteen_minute_period, previous_fourteen_minute_interval, UTCInterval, is_utc

from sqlmodel import select

from ewxpwsdb.db.models import WeatherStation, Reading
from ewxpwsdb.weather_apis import API_CLASS_TYPES
from ewxpwsdb.weather_apis.weather_api import WeatherAPI

@pytest.fixture()
def station(station_type, db_with_data_session):
    statement = select(WeatherStation).where(WeatherStation.station_type == station_type)
    results = db_with_data_session.exec(statement)
    weather_station = results.first()
    yield weather_station



def test_creating_wapi(station):
    wapi = API_CLASS_TYPES[station.station_type](station)
    assert wapi.station_type == station.station_type
    assert wapi.id == station.id
    assert isinstance(wapi.id, int)
    
    # check that configuration class is instantiated with same data in database
    api_config = wapi.APIConfigClass.model_validate_json_str(wapi.weather_station.api_config)
    assert api_config == wapi.api_config



def test_get_responses_and_transform(station_type, db_with_data_session):
    """comprehensive test given a database and a station model from that database, 
    go through all steps to get data from api, transform it, and save to db
    """
    
    statement = select(WeatherStation).where(WeatherStation.station_type == station_type)
    results = db_with_data_session.exec(statement)
    station = results.first()

    # create api object for this station
    wapi = API_CLASS_TYPES[station.station_type](station)
    # make api request
    # TODO also test that the internally stored wapi.current_api_response_records also works for this

    if station_type == 'RAINWISE':
        # rainwise goes down, so get 
        from ewxpwsdb.time_intervals import previous_fourteen_minute_period
        from datetime import UTC
        datetime_rainwise_was_working = datetime(year=2024, month=2, day=19, hour=12, minute=0, second=0, tzinfo=UTC)
        s,e = previous_fourteen_minute_period(datetime_rainwise_was_working)
        api_response_records = wapi.get_readings(s,e)
    else:
        interval = UTCInterval.previous_interval(delta_mins= 70)
        api_response_records = wapi.get_readings(interval.start, interval.end)

    # check that there is some weather data, and 200 status
    assert isinstance(api_response_records[0].response_text, str)

    

    # save response(s) to database
    for response in api_response_records:
        assert wapi.data_present_in_response(response)
        db_with_data_session.add(response)
        db_with_data_session.commit()

    # check that they were saved
    for response in api_response_records:
        assert response.id is not None
        assert isinstance(response.id, int)
        assert response.weatherstation_id == station.id
    
        # low level tests that are present in the function data_present_in_response
        assert response.response_status_code == '200'
        assert isinstance(response.response_text,str)
        response_data = json.loads(response.response_text)
        assert isinstance(response_data, dict)
        assert wapi._data_present_in_response(response_data)

        # this is a re-test of the above statements but ensures this function works
        assert wapi.data_present_in_response(response)


    # check the first response record to see if it has what we need to make some readings
    response_data = api_response_records[0].response_text
    response_data = json.loads(response_data)

    if station_type == 'ZENTRA':
        assert 'data' in response_data.keys()
        sensor_count = 0
        for sensor in response_data['data']:
            if sensor in wapi.sensor_transforms:
                sensor_count += 1
        assert sensor_count > 0 

    # attempt transform  for this station type
    # the Readings model also validates the data        
    readings = wapi.transform(api_response_records)
    assert isinstance(readings, list)
    assert len(readings) > 0
    
    assert isinstance(readings[0], Reading)
    for reading in readings:
        assert isinstance(reading, Reading)
        assert isinstance(reading.data_datetime, datetime)
        #TODO test that the datetime is close (within an hour?) to current UTC time datetime.utcnow()  
        #TODO test that the datetime is closer (within an 30 minutes) to time of the api request

    # save readings to database
    for reading in readings:
        db_with_data_session.add(reading)    
        db_with_data_session.commit()
    
    # check all the readings
    for reading in readings:
        # does it have an id => proxy for that is was saved in the db
        assert reading.id  is not None


        # check that the attribute is defined _and_ the that value is float or nothing
        # this is here to ensure the Reading model fields/attributes don't get update without also updating tests
        assert isinstance(reading.atmp, float|None)
        assert isinstance(reading.atmp_min, float|None)  
        assert isinstance(reading.atmp_max, float|None)
        assert isinstance(reading.dwpt, float|None)  
        assert isinstance(reading.lws , float|None)  
        assert isinstance(reading.pcpn, float|None)  
        assert isinstance(reading.relh, float|None)  
        assert isinstance(reading.rpet, float|None)  
        assert isinstance(reading.smst, float|None) 
        assert isinstance(reading.stmp, float|None) 
        assert isinstance(reading.srad, float|None)  
        assert isinstance(reading.wdir, float|None)  
        assert isinstance(reading.wspd, float|None)  
        assert isinstance(reading.wspd_max, float|None)  

        # check that we definitely have working float values for sensors that _should_ be present
        # note this test will fail if the weather station is down

        # STATION BY STATION TYPE test of transformed variables
        # TODO create station specific test files


        if station_type == 'DAVIS':
            assert isinstance(reading.atmp, float)
            assert isinstance(reading.atmp_min, float)
            assert isinstance(reading.atmp_max, float)
            assert isinstance(reading.dwpt, float)
            assert isinstance(reading.lws , float)
            assert isinstance(reading.pcpn, float)  
            assert isinstance(reading.srad, float)  
            assert isinstance(reading.stmp, float)
            assert isinstance(reading.smst, float)
            assert isinstance(reading.wdir, float)
            assert isinstance(reading.wspd, float)
            assert isinstance(reading.wspd_max, float)

        if station_type == 'LOCOMOS':
            assert isinstance(reading.atmp, float)
            assert isinstance(reading.relh , float)

        if station_type == 'ONSET':
            assert isinstance(reading.atmp, float)
            assert isinstance(reading.dwpt, float)
            assert isinstance(reading.lws, float) 
            assert isinstance(reading.pcpn, float)
            assert isinstance(reading.relh, float)
            assert isinstance(reading.srad, float)
            assert isinstance(reading.wdir, float)
            assert isinstance(reading.wspd, float)
            assert isinstance(reading.wspd_max, float)

        if station_type == 'RAINWISE':
            assert isinstance(reading.atmp, float)
            assert isinstance(reading.atmp_min, float)
            assert isinstance(reading.atmp_max, float)
            assert isinstance(reading.dwpt, float)
            assert isinstance(reading.lws,  float)
            assert isinstance(reading.pcpn, float)
            assert isinstance(reading.relh, float)
            assert isinstance(reading.stmp, float)
            assert isinstance(reading.srad, float)
            assert isinstance(reading.wdir, float)
            assert isinstance(reading.wspd, float)
            assert isinstance(reading.wspd_max, float)

        if station_type == 'SPECTRUM':
            assert isinstance(reading.atmp, float)
            assert isinstance(reading.lws,  float)
            assert isinstance(reading.pcpn, float)
            assert isinstance(reading.relh, float)
            assert isinstance(reading.wdir, float)
            assert isinstance(reading.wspd, float)
            assert isinstance(reading.wspd_max, float)

        if station_type == 'ZENTRA':
            assert isinstance(reading.atmp, float)
            assert isinstance(reading.lws , float)
            assert isinstance(reading.pcpn, float)    
            assert isinstance(reading.srad, float)  
            assert isinstance(reading.stmp, float)
            assert isinstance(reading.wdir, float)  
            assert isinstance(reading.wspd, float)
            assert isinstance(reading.wspd_max, float)


    # try to get the readings from the database and test them. 
    stmt = select(Reading, WeatherStation).join(WeatherStation).where(WeatherStation.id  == station.id)
    reading_records = db_with_data_session.exec(stmt).all()

    # there must be at least as many records in db as we just put in
    # TODO use the IDs in the api_response_records to limit the readings pulled to match we just made
    assert len(reading_records) >= len(readings)
    
    
    for reading_record in reading_records:
        reading = reading_record.Reading
        
        assert isinstance(reading.data_datetime, datetime)
        assert is_utc(reading.data_datetime)

        assert isinstance(reading.atmp, float)
        if station_type != 'LOCOMOS':
            assert isinstance(reading.pcpn , float)
        assert isinstance(reading.relh , float)

        # leaf wetness is only on some stations, but we don't have a way to tell which sensors are present yet
        # assert isinstance(reading.lws , float)



def test_response_errors(station):
    """ tests when getting api response we know is erroneous (future or distant past), checks for good data fail"""
    
    WAPIClass = API_CLASS_TYPES[station.station_type]
    wapi = WAPIClass(station)
    

    # attempt to get data in the future and test that we detect no data
    interval = UTCInterval.previous_interval(delta_mins=70)
    
    # add 1 day to put this interval in the future
    future_end_datetime = interval.end + timedelta(days=1)
    future_start_datetime = interval.start + timedelta(days=1)

    # The `responses_of_future` variable is storing the API response data obtained by making a request
    # to the API for a future time interval. In the test scenario, the test is attempting to get data
    # for a time interval that is in the future relative to the current time. The purpose of this test
    # is to check how the system handles such scenarios where data for future time intervals is
    # requested. The test then checks whether the API response contains valid data or if it correctly
    # detects that there is no data available for the future time interval.
    responses_of_future = wapi.get_readings(start_datetime=future_start_datetime, end_datetime=future_end_datetime)
    assert wapi.data_present_in_response(responses_of_future[0]) == False

    # try from ten years ago
    distant_past_start_datetime = interval.start - timedelta(days = 3650)
    distant_past_end_datetime = interval.end - timedelta(days = 3650)
    
    responses_of_distant_past = wapi.get_readings(start_datetime=distant_past_start_datetime, end_datetime=distant_past_end_datetime)
    assert wapi.data_present_in_response(responses_of_distant_past[0]) == False
    
