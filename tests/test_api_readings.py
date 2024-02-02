""" test of getting data via API, transform to readings and saving to the database"""

import pytest
from datetime import datetime


from sqlmodel import Session, select

from ewxpwsdb.time_intervals import is_utc
from ewxpwsdb.db.models import WeatherStation, Reading
from ewxpwsdb.weather_apis import API_CLASS_TYPES

def test_creating_wapi(station):
    wapi = API_CLASS_TYPES[station.station_type](station)
    assert wapi.station_type == station.station_type
    assert wapi.id == station.id
    assert isinstance(wapi.id, int)
    
    # check that configuration class is instantiated with same data in database
    api_config = wapi.APIConfigClass.model_validate_json_str(wapi.weather_station.api_config)
    assert api_config == wapi.api_config


def test_get_responses_and_transform(station_type, db_with_data):
    """comprehensive test given a database and a station model from that database, 
    go through all steps to get data from api, transform it, and save to db
    """
    
    session = Session(db_with_data)
    statement = select(WeatherStation).where(WeatherStation.station_type == station_type)
    results = session.exec(statement)
    station = results.first()

    # create api object for this station
    wapi = API_CLASS_TYPES[station.station_type](station)
    # make api request
    # TODO also test that the internally stored wapi.current_api_response_records also works for this
    api_response_records = wapi.get_readings()
    # check that there is some weather data, and 200 status
    assert isinstance(api_response_records[0].response_text, str)

    # save response(s) to database
    session = Session(db_with_data)
    for response in api_response_records:
        session.add(response)
        session.commit()

    for response in api_response_records:
        assert response.id is not None
        assert isinstance(response.id, int)
        assert response.weatherstation_id == station.id

    # attempt transform for this station type
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

    # save to database
    for reading in readings:
        session.add(reading)    
        session.commit()
    
    # check all the readings
    for reading in readings:
        # does it have an id now?
        assert reading.id  is not None
        # TODO not all stations will have all sensors, so may need to tailor this list depending on station type
        assert isinstance(reading.atemp, float)
        assert isinstance(reading.pcpn , float)
        assert isinstance(reading.relh , float)
        assert isinstance(reading.lws0 , float)

    # try to get the readings from the database and test them. 
    stmt = select(Reading, WeatherStation).join(WeatherStation).where(WeatherStation.id  == station.id)
    reading_records = session.exec(stmt).all()

    # there must be at least as many records in db as we just put in
    # TODO use the IDs in the api_response_records to limit the readings pulled to match we just made
    assert len(reading_records) >= len(readings)
    
    for reading_record in reading_records:
        reading = reading_record.Reading
        assert isinstance(reading.data_datetime, datetime)
        assert isinstance(reading.atemp, float)
        assert isinstance(reading.pcpn , float)
        assert isinstance(reading.relh , float)
        assert isinstance(reading.lws0 , float)
