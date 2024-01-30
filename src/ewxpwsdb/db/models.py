from typing import Optional
from datetime import datetime, date

from sqlmodel import SQLModel, Field, text

# TODO use pydantic validation for some fields.  here are reminders...
# from pydantic import field_validator
# from ewxpwsdb.time_intervals import is_valid_timezone, TimeZoneStr
# from ewxpwsdb.weatherstations import STATION_TYPE
# create a type for 'coordinates that enforces correct number of decimal places 

class StationType(SQLModel, table = True):
    """code representing the type of station, which dictates which class to use for API connecting and decoding """
    station_type: str = Field(primary_key=True)
    reporting_duration: Optional[int] = Field(description="period for which each reading covers in minutes, one of 5, 15, 30")

class WeatherStation(SQLModel, table=True): 
    id: Optional[int] = Field(default=None, primary_key=True)
    station_code: str = Field(unique=True) # use annotated to limit number of chars in this field 
    station_type : str = Field(foreign_key="stationtype.station_type") # add validation from the weatSTATION_TYPE
    install_date: date 
    timezone: str # TimeZoneStr = Field(default = 'US/Eastern', description="string that can be turned into ZoneInfo object created using IANA Timezone key https://en.wikipedia.org/wiki/List_of_tz_database_time_zones")  
    ewx_user_id: str # owner of the station, a valid EWX user ID.  (email or other)
    lat: float  #TODO: use decimal and specify the exact precision Decimal = Field(default=0, max_digits=5, decimal_places=3)
    lon: float
    location_description: Optional[str] = None
    api_config: Optional[str] = Field(description="JSON holding configuration to access the vendor cloud api")

    # TODO validate timezone
    # @field_validator('timezone')
    # @classmethod
    # def must_be_valid_timezone_key(cls,v: str) -> str:
    #     """ ensure timezone key is valid"""
    #     if is_valid_timezone(v):
    #         return(v)
    #     else:
    #         raise ValueError(f"timezone_key v is not a valid IANA timezone e.g. US/Eastern")

class Reading(SQLModel, table=True):
    """a reading of a weather stations sensors, as reported by the API and harmonized to EWX standard"""
    id: Optional[int] = Field(default=None, primary_key=True, description="database assigned id number")
    weatherstation_id: int = Field(foreign_key="weatherstation.id", description="link to the weather station that this readng from ")
    
    reading_datetime: datetime = Field(description = "timestamp of start time for this reading")
    reading_duration: int = Field(description = "number of minutes for time interval for this station, 5, 15 or 30.")
    
    # link to 'raw' api data
    apirequest_id : str = Field(description = "unique ID of the request event to link with raw api output")

    # sensors    
    atemp : Optional[float] = Field(default=None, description="air temperature, celsius") 
    pcpn  : Optional[float] = Field(default=None, description="precipitation, mm, > 0")   
    relh  : Optional[float] = Field(default=None, description="relative humdity, percent")
    lws0  : Optional[float] = Field(default=None, description="this is an nominal reading or 0 or 1 (wet / not wet)")  

    # optional fields that _maybe_ valuable
    # weatherstation_code: str = Field(foreign_key="weatherstation.station_code", description="link to the weather station that this readng from via human assigned code")
    # data_datetime : datetime  # this is now redundant with reading_datetime
    # time_interval: UTCInterval can't store this in a database...

    # TODO 
    # error status if any
    # 
    
class APIRequest(SQLModel, table=True):
    """log of request events made from the various vendor APIs for the station, the along wiht output (response) data exactly as received prior to transform"""
    id: Optional[int] = Field(default=None, primary_key=True, description="database assigned id number")
    weatherstation_id: int = Field(foreign_key="weatherstation.id", description="link to the weather station that this readng from ")
    # weatherstation_code: str = Field(foreign_key="weatherstation.station_code", description="link to the weather station that this readng from via human assigned code")
    request_datetime : datetime
    request_json : str = Field(description='what was sent to the API')
    response_json : str = Field(description='json that was sent beack as a reponse')  ### needs to be an array of responses! 

