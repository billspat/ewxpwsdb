"""utils for editing time stamps"""

from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, model_validator, field_validator # validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal, Annotated
from pydantic import WrapValidator


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
    
    if not dt.tzinfo == timezone.utc:
        return False
    
    return True


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
    
    model_config = {'allow_reuse': True}
    
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
    def previous_fifteen_minutes(cls):
        s,e = previous_fifteen_minute_period()
        return( cls(start = s, end = e))
    
    @classmethod
    def previous_interval(cls, dtm = datetime.now(timezone.utc), delta_mins:int=15):
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
        

    def duration(self):
        return(self.end-self.start)
    

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


# def previous_interval(dtm:datetime=datetime.now(timezone.utc), delta_mins:int=15)->UTCInterval:
#     """ returns  that is on the quarter hour and inclusive. 
#     input datetime object with timezone , e.g. 03:10:15+00
#     output: tuple of two datetime objects, e.g (02:45:00, 03:00:00)
    
#     if called successively every 15 minutes, times will overlap , e.g. 
#     (02:45:00, 03:00:00), (03:00:00, 3:15:00),(3:15:00, 03:30:00), etc

#     set arbitrary delta (15 minutes, 14 minutes, 30 minutes, etc)
    
#     """
#     # starter time - 
#     dtm_utc = dtm

#     # quarter hour prior to starter (11:55 ->  11:45, etc)
#     end_datetime_utc = fifteen_minute_mark(dtm_utc.datetime)
#     # time previous to that for delta
#     start_datetime_utc = end_datetime_utc - timedelta(minutes=delta_mins)
    
#     try:
#         dti = UTCInterval(start = start_datetime_utc, end = end_datetime_utc )
#     except ValueError as e:
#         raise(ValueError)
        
#     return(dti)

def previous_fourteen_minute_interval(dtm:datetime=datetime.now(timezone.utc))->UTCInterval:
    """ convenience method for using previous interval above for 14 intervals, 
    which are non-overlapping ranges of an hour
    00:00 - 00:14, 00:15 - 00:29, 00:30 - 00:44, 00:45 - 00:59
    """
    dti = UTCInterval.previous_interval(dtm, delta_mins=14)
    return(dti)



