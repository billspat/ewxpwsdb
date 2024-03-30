import pytest
from sqlmodel import select, Session
from ewxpwsdb.db.models import WeatherStation
from ewxpwsdb.weather_apis import ZentraAPI
from ewxpwsdb.time_intervals import previous_fourteen_minute_interval
from datetime import datetime, timedelta


@pytest.fixture(scope='module')
def zentra_station(station_type, db_with_data)->None|ZentraAPI:

    if station_type !='ZENTRA':
        return None
    
    with Session(db_with_data) as session:
        statement = select(WeatherStation).where(WeatherStation.station_type == 'ZENTRA')
        results = session.exec(statement)
        weather_station = results.first()

    return(weather_station)


def test_zentra_page_count_math(zentra_station):

    if zentra_station:
        
        assert isinstance(zentra_station, WeatherStation)
        assert zentra_station.station_type == 'ZENTRA'
        zapi = ZentraAPI(zentra_station)

        # ensure the constant is set
        assert isinstance(zapi._MAX_READINGS_PER_PAGE, int)
        # this should fail if we ever change this max 
        assert zapi._MAX_READINGS_PER_PAGE == 2000
        assert zapi._sampling_interval == 5 # minutes
        # short time period, 1 page    
        interval = previous_fourteen_minute_interval()
        
        assert isinstance(interval.start, datetime)
        assert zapi._expected_page_count(interval.start,interval.end) == 1
        assert zapi._expected_page_count(interval.start,interval.end, page_len=zapi._MAX_READINGS_PER_PAGE) == 1
        # should still work using default page_len
        assert zapi._expected_page_count(interval.start,interval.end) == 1

        
        
        
        # this is kind of tautological since this math is already in the session
        # number of days per page = 2000 readings/page divided by 60 min/hour / 5 minute interval * 24 hours per day 
        days_per_page = zapi._MAX_READINGS_PER_PAGE / ( ( 60/zapi._sampling_interval ) * 24 )
        assert days_per_page > 6 and days_per_page < 7

        interval = previous_fourteen_minute_interval()
        interval.start = interval.start - timedelta(days= 6)
        assert zapi._expected_page_count(interval.start,interval.end, page_len=zapi._MAX_READINGS_PER_PAGE) == 1

        interval.start = interval.start - timedelta(days= 7)
        assert zapi._expected_page_count(interval.start,interval.end, page_len = zapi._MAX_READINGS_PER_PAGE) > 1
        assert zapi._expected_page_count(interval.start,interval.end, page_len = zapi._MAX_READINGS_PER_PAGE) == 2

        interval = previous_fourteen_minute_interval()
        interval.start = interval.start - timedelta(days= 15)
        assert zapi._expected_page_count(interval.start,interval.end, page_len = zapi._MAX_READINGS_PER_PAGE) == 3
        



        

# def test_zentra_page_count_works(zentra_station):

#     if zentra_station:
#         zapi = ZentraAPI(zentra_station)
#         interval = previous_fourteen_minute_interval()

#         responses = zapi.get_readings(interval.start,interval.end)




        



    