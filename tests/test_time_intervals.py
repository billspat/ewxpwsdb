#!/usr/bin/env python

import pytest
from pydantic import ValidationError

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ewxpwsdb.time_intervals import fifteen_minute_mark, previous_fifteen_minute_period, \
    previous_fourteen_minute_period, is_utc, UTCInterval, datetimeUTC


@pytest.fixture
def test_timestamp():
    """return a random timestamp, but just now for now"""
    return datetime.now(timezone.utc)

@pytest.fixture()
def just_past_two():
    return(datetime(datetime.now().year,1,1,hour=2, minute=1, second=0))

def test_15minutemark(test_timestamp):
    """test that we get something always on 15 minutes"""

    # no args
    dtm = fifteen_minute_mark()
    assert dtm.minute % 15 == 0

    # with args
    dtm = fifteen_minute_mark(test_timestamp)
    assert dtm.minute % 15 == 0

    just_past_two = datetime(2022,1,1,hour=2, minute=1, second=0)
    two = datetime(2022,1,1,hour=2, minute=0, second=0)
    assert fifteen_minute_mark(just_past_two) == two

    time_with_seconds  = datetime(2022,1,1,hour=2, minute=1, second=10)
    assert fifteen_minute_mark(time_with_seconds) == two
    


def test_previous_fifteen_minute_period():
    
    pfmp = previous_fifteen_minute_period()
    assert len(pfmp) == 2
    assert pfmp[1] > pfmp[0]
    assert pfmp[0].minute % 15 == 0
    assert pfmp[1].minute % 15 == 0
    start_minute = pfmp[0].minute
    end_minute = pfmp[1].minute
    # if the end minute is at top of clock, call it 60 minutes instead of 0
    if end_minute == 0: end_minute = 60
    assert  abs(end_minute - start_minute) == 15

    now = datetime.utcnow()
    pfmp = previous_fifteen_minute_period(now)
    assert pfmp[1] <= now
    assert now - pfmp[0] > timedelta(minutes=15)
    
    #TODO test that it's ac
    
    sample_dt = datetime(2022,1,1,hour=2, minute=10, second=0)
    pfmp = previous_fifteen_minute_period(sample_dt)
    assert pfmp[1] == datetime(2022,1,1,hour=2, minute=0, second=0)
    assert pfmp[0] == datetime(2022,1,1,hour=1, minute=45, second=0)

def test_previous_fourteen_minute_period():
    pfmp = previous_fourteen_minute_period()
        # check that the interval is really 14 minutes
    assert len(pfmp) == 2
    assert (pfmp[1] - pfmp[0]).seconds == 14 * 60

def test_is_utc(just_past_two):
    nowish = datetime.now(timezone.utc)
    assert is_utc(nowish)

    assert not is_utc(datetime.now())

    assert not is_utc(datetime(month=1, day=1, year=1900))
    assert not is_utc(datetime.now(tz = ZoneInfo("America/Detroit")))


def test_utcinterval():
    start, end = previous_fifteen_minute_period()

    interval = UTCInterval(start=start,end=end)

    assert isinstance(interval.start, datetime)
    assert isinstance(interval.end, datetime)
    assert is_utc(interval.start)
    assert is_utc(interval.end)
    # note not "less than or equal" - don't allow zero intervals
    assert interval.start < interval.end 

def test_utcinterval_methods():
    interval = UTCInterval.previous_fifteen_minutes()
    assert isinstance(interval.start, datetime)
    assert isinstance(interval.end, datetime)
    assert is_utc(interval.start)
    assert is_utc(interval.end)
    # note not "less than or equal" - don't allow zero intervals
    assert interval.start < interval.end 

    assert (interval.end - interval.start).seconds == 15 * 60

def test_previous_interval():
    dtm = datetime(2023, 1,1, hour=12, minute=0).astimezone(timezone.utc)
    interval = UTCInterval.previous_interval(dtm = dtm )

    assert isinstance(interval.start, datetime)
    assert isinstance(interval.end, datetime)
    assert is_utc(interval.start)
    assert is_utc(interval.end)
    # note not "less than or equal" - don't allow zero intervals
    assert interval.start < interval.end 

def test_utc_datetimes():
    assert datetimeUTC(value=datetime(2022,10,10,15,25,0,tzinfo=timezone.utc))
    with pytest.raises(ValidationError):
        est = datetimeUTC(value=datetime(2022,10,10,15,25,0,tzinfo=ZoneInfo('US/Eastern')))
    with pytest.raises(ValidationError):
        naive = datetimeUTC(value=datetime(2022,10,10,15,25,0))

# def test_datetimeutc():
#     assert just_past_two.tzinfo is None
#     with pytest.raises(ValidationError):
#         DatetimeUTC(datetime = just_past_two)

#     # add a tz and check again  
    
#     dt_with_tz = just_past_two.astimezone(ZoneInfo('US/Eastern'))  
#     dtu = DatetimeUTC(datetime = dt_with_tz)
#     assert isinstance(dtu.datetime, datetime)
#     assert dtu.datetime.tzinfo == timezone.utc
