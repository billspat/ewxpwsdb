import pytest

from zoneinfo import ZoneInfo
from datetime import date, datetime
from ewxpwsdb.time_intervals import DateInterval, UTCInterval, is_utc  # type: ignore

from pydantic import ValidationError

@pytest.fixture(scope="module")
def test_tz_str():
    return "America/Detroit"

def test_date_interval():
    start = date(2024, 6, 10)
    end =   date(2024, 6, 11)

    di = DateInterval(start = start, end = end)
    assert isinstance(di, DateInterval)

    assert isinstance(di.start, date)
    assert isinstance(di.end, date)
    with pytest.raises(ValidationError):
        di = DateInterval(start = end, end = start )

def test_date_interval_conversion(test_tz_str):
    start = date(2024, 6, 10)
    end =   date(2024, 6, 11)

    di = DateInterval(start = start, end = end )
    assert is_utc(di.start_date_to_utc_datetime(local_timezone=test_tz_str))
    assert is_utc(di.end_date_to_utc_datetime(local_timezone=test_tz_str))

    try:
        utc_interval =  di.to_utc_datetime_interval(local_timezone=test_tz_str)
    except ValidationError as e:
        pytest.fail(f"raised exception  {e}")

    assert isinstance(utc_interval, UTCInterval)

def test_date_interval_from_string():
    month = 6
    start = "2024-6-10"
    end =   "2024-6-11"
    
    try:
        di = DateInterval.from_string(start = start, end = end )
    except ValidationError as e:
        pytest.fail(f"raised exception on request: {e}")
    
    assert isinstance(di, DateInterval)
    assert di.start.month == 6

    

    