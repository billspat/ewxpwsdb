from typing import Optional
from datetime import datetime, date

from sqlmodel import SQLModel, Field, text
from pydantic import field_validator

# eventually add validation here 
# from ewxpwsdb.time_intervals import is_valid_timezone, TimeZoneStr
# from ewxpwsdb.weatherstations import STATION_TYPE
# create a type for 'coordinates that enforces correct number of decimal places 

class Reading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    station_id: int
    reading_datetime: datetime
    atmp: float


class WeatherStation(SQLModel, table=True): 
    id: Optional[int] = Field(default=None, primary_key=True)
    station_code: str = Field(unique=True) # use annotated to limit number of chars in this field 
    station_type : str # add validation from the weatSTATION_TYPE
    install_date: date 
    timezone: str # TimeZoneStr = Field(default = 'US/Eastern', description="string that can be turned into ZoneInfo object created using IANA Timezone key https://en.wikipedia.org/wiki/List_of_tz_database_time_zones")  
    ewx_user_id: str # owner of the station, a valid EWX user ID.  (email or other)
    lat: float  #TODO: use decimal and specify the exact precision Decimal = Field(default=0, max_digits=5, decimal_places=3)
    lon: float
    location_description: Optional[str] = None
    api_config: Optional[str] = Field(description="JSON holding configuration to access the vendor cloud api")
    
class StationType(SQLModel, table = True):
    station_type: str = Field(primary_key=True)
    

    # @field_validator('timezone')
    # @classmethod
    # def must_be_valid_timezone_key(cls,v: str) -> str:
    #     """ ensure timezone key is valid"""
    #     if is_valid_timezone(v):
    #         return(v)
    #     else:
    #         raise ValueError(f"timezone_key v is not a valid IANA timezone e.g. US/Eastern")

### add here models that are in weatherstations models and turn into DB tables as needed
    
# WeatherReadings 
