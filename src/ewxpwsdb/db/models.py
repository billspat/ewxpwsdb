from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field, text
from uuid import uuid4


from ewxpwsdb import __version__
class StationType(SQLModel, table = True):
    """code representing the type of station, which dictates which class to use for API connecting and decoding """
    station_type: str = Field(primary_key=True)
    sampling_interval: Optional[int] = Field(description="period for which each reading covers in minutes, one of 5, 15, 30")

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

class APIResponse(SQLModel, table=True):
    """log of request events made from the various vendor APIs for the station, including metadata of request and the response data exactly as received prior to transform
    
    Request / Response data may contain many readings. 
    records in the Reading table have a link to apirequest, but tere is no guarantee requests do not overlap in time, or that there is an associated reading"""

    id: Optional[int] = Field(default=None, primary_key=True, description="unique id of this request")
    request_id: Optional[str] = Field(default = str(uuid4()), unique= True, description="manually generated link to reading records generated from this API response")

    # metadata
    weatherstation_id: int = Field(foreign_key="weatherstation.id", description="link to the weather station that this readng from ")
    request_datetime : datetime = Field(description="Timestamp in UTC of when the request was made of the API")
    data_start_datetime: datetime  = Field(description="Timestamp in UTC of the beginning of the period in ")
    data_end_datetime: datetime  = Field(description="Timestamp in UTC of ")
    package_version: str  = __version__ # version('ewxpwsdb')
    station_sampling_interval: int = Field(description='5,10,15 minutes frequency of sampling for this station, propagated to reading')
    
    # response data
    request_url : str =  Field(description='response.request.url')
    response_status_code : str = Field(description='(response.status_code)')
    response_reason : str = Field(description='response.reason')
    response_text : str = Field(description='response.text')
    response_content : str = Field(description='response.content') 

    #TODO redundant fields, enable later?
    # weatherstation_code: str = Field(foreign_key="weatherstation.station_code", description="backup link to the weather station that this readng from via human assigned code")
    # weatherstation_type: str 


class Reading(SQLModel, table=True):
    """a reading of a weather stations sensors, as reported by the API and harmonized to EWX standard"""
    id: Optional[int] = Field(default=None, primary_key=True, description="database assigned id number")
    apiresponse_id: int = Field(foreign_key="apiresponse.id",description = "unique ID of the request event to link with raw api output")
    
    request_id: str = Field(description = "code generated ID for ensuring linkage")
    # metadata
    weatherstation_id: int = Field(foreign_key="weatherstation.id", description="link to the weather station that generated this reading ")
    station_sampling_interval: int = Field(description = "number of minutes for sampling interval for this station, 5, 15 or 30.")

    reading_datetime: datetime = Field(description = "timestamp of start time for this reading")
    

    # sensors
    # TODO use decimal for accuracy    
    atemp : Optional[float] = Field(default=None, description="air temperature, celsius") 
    pcpn  : Optional[float] = Field(default=None, description="precipitation, mm, > 0")   
    relh  : Optional[float] = Field(default=None, description="relative humdity, percent")
    lws0  : Optional[float] = Field(default=None, description="this is an nominal reading or 0 or 1 (wet / not wet)")  

    # optional fields that might be valuable
    # weatherstation_code: str = Field(foreign_key="weatherstation.station_code", description="link to the weather station that this readng from via human assigned code")

    @classmethod
    def model_validate_from_station(cls, sensor_data, api_response: APIResponse):
        """ add required metadata to dict of transformed weather data"""
        r = sensor_data # start with this dict and add meta data
        r['apiresponse_id']      = api_response.id
        # redundant columns to reduce the need for joins
        r['request_id']          = api_response.request_id
        r['weatherstation_id']   = api_response.weatherstation_id
        r['station_sampling_interval']   = api_response.station_sampling_interval

        return(cls.model_validate(r))

