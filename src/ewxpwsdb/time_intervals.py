"""utils for editing time stamps"""

from datetime import datetime, timedelta, date, UTC, time, tzinfo, timezone 

from dateutil import tz
from dateutil.parser import parse # type: ignore
from pydantic import BaseModel, model_validator, field_validator # validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal, Annotated
from pydantic import WrapValidator, ConfigDict, Field
from typing import Self


def is_valid_timezone(tz:str) -> bool:
    """Simple test if a string is also a valid python timezone library timezone, e.t. "US/Eastern"

    Args:
        tz (str): a string purporting to be a timezone     

    Returns:
        bool: True if valid, false if not
    """
    try:
        x = ZoneInfo(tz)
        return(True)
    except ZoneInfoNotFoundError as e: 
        return(False)
        # raise ValueError("timezone_key string must be valid IANA timezone e.g. US/Eastern")

TimeZoneStr = Annotated[str, WrapValidator(is_valid_timezone)]


def is_tz_aware(dt:datetime)->bool:
    """ based on documentation, test if a datetime is timezone aware (T) or naive (F)
    see https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    input dt a datetime object
    returns True if is aware (not naive) False if not tz aware (naive)"""
    if dt.tzinfo is not None:
        if dt.tzinfo.utcoffset(dt) is not None:
            return True
    return False
  
def is_utc(dt:datetime)->bool:
    if not is_tz_aware(dt):
        return False
    
    # detect dateutil's timezone format
    if dt.tzinfo == tz.tzutc():
        return True
        
    # detect python standard lib timezone format
    if dt.tzinfo == timezone.utc:
        return True
    
    return False

        
def str_to_timezone(timezone_str:str):
    if is_valid_timezone(timezone_str):
        local_timezone = ZoneInfo(timezone_str)
        return(local_timezone)
    else:
        raise ValueError(f"could not set timezone - invalide timezone {timezone_str}")


def local_date_to_utc_datetime(local_date:date, boundary:str,  local_timezone:tzinfo|str = ZoneInfo('America/Detroit'))->datetime:
    """convert the local time start date to a UTC start time, given the start of the sttart day is midnight"""
    
    if boundary.upper() not in ['START', 'END']:
        raise ValueError(f"boundary param must be 'start' or 'end', got {boundary}")
    
    if not isinstance(local_timezone, timezone):
        local_tzinfo:tzinfo = str_to_timezone(timezone_str = str(local_timezone))
    else:
        local_tzinfo = local_timezone

    datetime_parts:dict = {
                        'year'  : local_date.year, 
                        'month' : local_date.month, 
                        'day'   : local_date.day, 
                        'tzinfo': local_tzinfo
                       }                    
                        
    if boundary.upper() == 'START':        
        datetime_parts.update({'hour': 0, 'minute': 0, 'second':0 })
        
    elif boundary.upper() == 'END':        
        datetime_parts.update({'hour':23, 'minute':59, 'second':59 })
        
    else:
        raise ValueError(f"boundary param must be 'start' or 'end', got {boundary}")
    
    dt_local = datetime(**datetime_parts)
    
    return dt_local.astimezone(UTC)


class datetimeUTC(BaseModel):
    """a datetime object guaranteed to be UTC tz aware"""
    value: datetime 
    @field_validator('value')
    def check_datetime_utc(cls, value):
        assert is_utc(value)
        return value
 
   
class UTCInterval(BaseModel):
    """ datetime interval that requires user to supply UTC datetimes.  
    Useful for passing start and end times into functions"""
        
    start: datetime
    end: datetime
    
    @field_validator('start', 'end')
    @classmethod
    def check_datetime_utc(cls, v):
        """ ensure datetime value is utc"""
        if is_utc(v):
            return v
        raise ValueError("datetime must have a timezone and must be UTC")
    
    # this is a pre-validation step
    @model_validator(mode='after')
    def validate_utc_interval(self):
        """ensure that start is before end"""

        if self.start <= self.end:
            return self
        
        raise ValueError('end date-time must come after start date-time')

        
    @classmethod
    def init_from_local(cls, local_start:datetime, local_end:datetime, local_timezone:str)->Self:
        """create UTC interval given a start and stop in non-UTC timezone (or with no timezones)
        Args:
            local_start (datetime): start datetime assumed to be 'local' time, with or with out timezone.  if does not have a timezone, the timezone arg is used
            local_end (datetime): end datetime assumed to be 'local' time, with or with out timezone.  if does not have a timezone, the timezone arg is used
            timezone (str): timezone of these
            
        Returns:
            UTCInterval
        """
       
        local_tz:ZoneInfo = ZoneInfo(local_timezone)  if not isinstance(local_timezone, ZoneInfo) else local_timezone
        
        if not is_tz_aware(local_start):
            local_start = local_start.astimezone(local_tz)
        
        if not is_tz_aware(local_end):
            local_end = local_end.astimezone(local_tz)
            
        return(cls(start = local_start.astimezone(UTC), end = local_end.astimezone(UTC)))
        
        
    @classmethod
    def previous_fifteen_minutes(cls):
        s,e = previous_fifteen_minute_period()
        return( cls(start = s, end = e))
    
    @classmethod
    def previous_interval(cls, dtm = datetime.now(timezone.utc), delta_mins:int=14):
        """ returns  that is on the quarter hour and inclusive. 
        input datetime object with timezone , e.g. 03:10:15+00
        output: tuple of two datetime objects, e.g (02:45:00, 03:00:00)
        
        if called successively every 15 minutes, times will overlap , e.g. 
        (02:45:00, 03:00:00), (03:00:00, 3:15:00),(3:15:00, 03:30:00), etc

        set arbitrary delta (15 minutes, 14 minutes, 30 minutes, etc)
        
        """
        # starter time - 
        if not is_utc(dtm):
            raise ValueError("input dtm must be a timezone aware value in UTC")
        else:
            dtm_utc = dtm

        # quarter hour prior to starter (11:55 ->  11:45, etc)
        end_datetime_utc = fifteen_minute_mark(dtm_utc)
        # time previous to that for delta
        start_datetime_utc = end_datetime_utc - timedelta(minutes=delta_mins)
        
        return cls(start = start_datetime_utc, end = end_datetime_utc )
        
    @classmethod
    def one_day_interval(cls, d:date = datetime.now(timezone.utc).date() ):
        """Create a time interval for the date in question, in UTC

        Args:
            d (date): a date object, today or day in the past, default is current UTC date

        Returns:
            UTCInterval: interval for the date, starting 00:00 to  21:59 unless the date is today, when it ends at the more recent 15 minute mark 
        """

        if not isinstance(d,date):
            raise ValueError("value sent was not a date object")
        
        todays_date:date = datetime.now(UTC).date()
        
        if d > todays_date:
            raise ValueError("date sent was in the future and this is for historic dates")
        
        # start the day as minimum time for date d
        beginning_of_day = datetime.combine(date=d, time=time(hour=0, minute=0, second=0)).replace(tzinfo=UTC)
        
        # end date different depending on today or some yesterday
        if d == todays_date:
            end_of_day =  fifteen_minute_mark()
        else:
            end_of_day =  datetime.combine(date=d, time=time(hour=23, minute=59, second=0)).replace(tzinfo=UTC) # datetime.combine(d, datetime.max.time())
        
        return cls(start = beginning_of_day , end = end_of_day )

    def model_dump_iso(self)->dict[str, str]:
        """dump to a dictionary of string iso format dates, suitable for sql"""
        return {'start': self.start.isoformat(), 'end':self.end.isoformat()}
        
    def duration(self):
        """time delta object difference start and end"""
        return(self.end-self.start)
    

class DateInterval(BaseModel):
    """ ordered dates and the time zone that does with them.   Time Zone is required to convert to UTC.  
    
    usage example: 
        from zoneinfo import ZoneInfo
        from datetime import date
        di = DateInterval(start = date(2024, 6, 10), end = date(2024, 6, 11) )
        di
    
    """

    model_config = ConfigDict(arbitrary_types_allowed=True) 

    start: date = Field(description="first day in range, in YYYY-MM-DD format")
    end: date = Field(description="day past end of range ( not inclusive), in YYYY-MM-DD format")

    @model_validator(mode='after')
    def validate_date_interval(self):
        """ensure that start is before end"""

        if self.start <= self.end:
            return self
        
        raise ValueError('end date must be equal to or come after start date')
    
    @classmethod
    def from_string(cls, start:str, end:str)->Self: 
        if not start or not end:
            raise ValueError(f"invalid arguments for start={start} and end={end}, can't create a data interval")

        start_date:date = parse(start).date()
        end_date:date = parse(end).date()
        
        return(cls(start = start_date, end = end_date))
    
    
    def date_to_utc_datetime(self, local_timezone:tzinfo|str)->datetime:
        """convert the local time start date to a UTC start time, given the start of the sttart day is 00:00"""

        return local_date_to_utc_datetime(self.start, 'start', local_timezone)
            
    
    def start_date_to_utc_datetime(self, local_timezone:tzinfo|str)->datetime:
        """convert the local time start date to a UTC start time, given the start of the sttart day is 00:00"""
        
        return local_date_to_utc_datetime(self.start, 'start', local_timezone)

                            
    def end_date_to_utc_datetime(self,local_timezone:tzinfo|str)->datetime:  
        """convert the local time end date to a UTC end time, given the end time  of the end day is 23:59""" 
        return local_date_to_utc_datetime(self.end, 'end', local_timezone)
    


    def to_utc_datetime_interval(self,local_timezone:tzinfo|str )->UTCInterval:
        """convert this date interval in local time to UTC time interval given the hour offset.  For example for eastern time, 
        starting January 1, 2020 EST is December 31, 2019 19:00:00 UTC
        """
        
        return UTCInterval(
                start = self.start_date_to_utc_datetime(local_timezone),
                end = self.end_date_to_utc_datetime(local_timezone)
                           )


def fifteen_minute_mark(dtm:datetime=datetime.now(timezone.utc))->datetime:
    """return the nearest previous 15 minute mark.  e.g. 10:49 -> 10:45, preserves timezone if any. 
    parameter dtm = optional datetime, default is 'now' using utc timezone """
    dtm -= timedelta(minutes=dtm.minute % 15,
                     seconds=dtm.second,
                     microseconds=dtm.microsecond)
    return(dtm)

def fifteen_minute_mark_utc(dtm:datetime=datetime.now(timezone.utc))->datetime:
    """return the nearest previous 15 minute mark.  e.g. 10:49 -> 10:45, preserves timezone if any. 
    parameter dtm = optional datetime, default is 'now' using utc timezone """

    if not is_utc(dtm):
        raise ValueError("dtm must have timezone set to UTC")
    
    dtm -= timedelta(minutes=dtm.minute % 15,
                     seconds=dtm.second,
                     microseconds=dtm.microsecond)
    return(dtm)

def previous_fifteen_minute_period(dtm:datetime=datetime.now(timezone.utc))->tuple[datetime, datetime]:
    """ returns tuple of start/end times that is on the quarter hour and inclusive. 
    input datetime object with timezone , e.g. 03:10:15+00
    output: tuple of two datetime objects, e.g (02:45:00, 03:00:00)
    
    if called successively every 15 minutes, times will overlap , e.g. 
    (02:45:00, 03:00:00), (03:00:00, 3:15:00),(3:15:00, 03:30:00), etc
    
    """
    end_datetime = fifteen_minute_mark(dtm)
    start_datetime = end_datetime - timedelta(minutes=15)
    return((start_datetime, end_datetime))


def previous_fourteen_minute_period( dtm:datetime = datetime.now(timezone.utc) )->tuple[datetime, datetime]:
    """ returns tuple of start/end times that is on the quarter hour and not inclusive.   
    input datetime object with timezone , e.g. 03:10:15+00
    output: tuple of two datetime objects, e.g (02:46:00, 03:00:00)

    it's not inclusive so that if called successviely every 15 minutes, it will not overlap
    (02:46:00, 03:00:00), (03:01:00, 3:15:00),(3:16:00, 03:30:00), etc
    """
    end_datetime = fifteen_minute_mark(dtm)
    start_datetime =  end_datetime - timedelta(minutes=14)
    return( (start_datetime, end_datetime) )


def today_utc()->date:
    """return a date object representing todays date in the UTC timezone.   
    For example in Eastern time if it were 10pm, it would be the next day since UTC is 5 hrs ahead
    
    Returns:
        date object in UTC time zone

    """
    return(datetime.now(UTC).date())

    
def one_day_interval_utc(local_date, local_timezone)-> UTCInterval:
    
    return UTCInterval(
        start = local_date_to_utc_datetime(local_date, boundary='start', local_timezone=local_timezone),
        end =   local_date_to_utc_datetime(local_date, boundary = 'end', local_timezone=local_timezone)
    )
        
    
def one_day_interval(d:date = datetime.now(timezone.utc).date() )->UTCInterval:
    """Create a time interval for the date in question, in UTC

    Args:
        d (date): a date object, today or day in the past, default is current UTC date

    Returns:
        UTCInterval: interval for the date, starting 00:00 to  21:59 unless the date is today, when it ends at the more recent 15 minute mark 
    """

    if not isinstance(d,date):
        raise ValueError("value sent was not a date object")
    
    todays_date:date = datetime.now(UTC).date()
    
    if d > todays_date:
        raise ValueError("date sent was in the future and this is for historic dates")
    
    # start the day as minimum time for date d
    beginning_of_day = datetime.combine(date=d, time=time(hour=0, minute=0, second=0)).replace(tzinfo=UTC)
    
    # end date different depending on today or some yesterday
    if d == todays_date:
        end_of_day =  fifteen_minute_mark()
    else:
        end_of_day =  datetime.combine(date=d, time=time(hour=23, minute=59, second=0)).replace(tzinfo=UTC) # datetime.combine(d, datetime.max.time())
    
    return UTCInterval(start = beginning_of_day , end = end_of_day )


def tomorrow_utc()->datetime:
    """convenience method used primarily for testing"""
    return datetime.now(UTC)+ timedelta(days=1)


def previous_fourteen_minute_interval(dtm:datetime=datetime.now(timezone.utc))->UTCInterval:
    """ convenience method for using previous interval above for 14 intervals, 
    which are non-overlapping ranges of an hour
    00:00 - 00:14, 00:15 - 00:29, 00:30 - 00:44, 00:45 - 00:59
    """
    dti = UTCInterval.previous_interval(dtm, delta_mins=14)
    return(dti)


def parse_and_validate(dt:str)->datetime:
    """given a timestamp string, attempt to parse and ensure it has a timezone

    Args:
        dt (str): string representation of datetime with timezone   

    Raises:
        ValueError: if can't be parse or does not have a timezone
        
    Returns:
        datetime: datetime (timestamp) in UTC timezone
    """
    try:
        a_datetime:datetime = parse(dt)
    except Exception as e:
        raise ValueError(f"error parsing start={dt}: {e}")
    if not is_tz_aware(a_datetime):
        raise ValueError(f"{dt} string must have a timezone")
    
    return(a_datetime.astimezone(UTC))


def str_to_interval(start:str|None=None, end:str|None=None)->UTCInterval:
    """parse params into datetimes and create UTC interval. Strings must have timezone.
     
    When start, end, or both are missing, create a 60 minute interval to work with
    using what was sent 
    """
        
    if start is None and end is None:
        # no times: create interval of previous 60 minutes
        interval =  UTCInterval.previous_interval(delta_mins=60)

    elif start is None:
        # no start: create 60 minute interval that ends at end time sent
        end_datetime = parse_and_validate(end)
        interval =  UTCInterval.previous_interval(dtm = end_datetime - timedelta(minutes=60), delta_mins=60)

    elif end is None:
        # no end: create 60 minute interval that starts at start time sent
        start_datetime = parse_and_validate(start)
        interval =  UTCInterval.previous_interval(dtm = start_datetime, delta_mins=60)

    else:
        end_datetime = parse_and_validate(end)
        start_datetime = parse_and_validate(start)
        try:            
            interval = UTCInterval(start = start_datetime, end = end_datetime)
        except Exception as e:
            raise ValueError(f"error creating time interval from start={start} to end={end}: {e}")

    return interval



