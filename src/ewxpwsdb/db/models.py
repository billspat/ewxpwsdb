from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field, UniqueConstraint, Column, DateTime
from uuid import uuid4
from sqlalchemy import DateTime
from pydantic import AwareDatetime


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
    background_place: str
    api_config: str = Field(default = "{}", description="JSON holding configuration to access the vendor cloud api")

class APIResponse(SQLModel, table=True):
    """log of request events made from the various vendor APIs for the station, including metadata of request and the response data exactly as received prior to transform
    
    Request / Response data may contain many readings. 
    records in the Reading table have a link to apirequest, but tere is no guarantee requests do not overlap in time, or that there is an associated reading"""

    id: Optional[int] = Field(default=None, primary_key=True, description="unique id of this request")
    request_id: Optional[str] = Field(default = str(uuid4()), unique= True, description="manually generated link to reading records generated from this API response")

    # metadata
    weatherstation_id: int = Field(foreign_key="weatherstation.id", description="link to the weather station that this readng from ")
    request_datetime : AwareDatetime = Field(description="Timestamp in UTC of when the request was made of the API", sa_column = Column(DateTime(timezone=True)))  #type: ignore

    # timezone-aware datetimes
    data_start_datetime: AwareDatetime  = Field(description="Timestamp in UTC of the beginning of the period in ", sa_column = Column(DateTime(timezone=True))) #type: ignore
    data_end_datetime: AwareDatetime  = Field(description="Timestamp in UTC of ", sa_column = Column(DateTime(timezone=True)))  #type: ignore

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

    __table_args__ = (
        UniqueConstraint("data_datetime", "weatherstation_id", name="constraint_one_reading_per_timestamp_per_station"),
    )

    # meta data fields
    id: Optional[int] = Field(default=None, primary_key=True, description="database assigned id number")

    apiresponse_id: int = Field(foreign_key="apiresponse.id",description = "unique ID of the request event to link with raw api output")
    
    # data_datetime: datetime
    data_datetime: AwareDatetime = Field(description = "timezone-aware timestamp of start time for this reading, in UTC", sa_column = Column(DateTime(timezone=True)))    #type: ignore
    
    request_id: str = Field(description = "code generated ID for ensuring linkage")
    
    weatherstation_id: int = Field(foreign_key="weatherstation.id", description="link to the weather station that generated this reading ")
    
    station_sampling_interval: int = Field(description = "number of minutes for sampling interval for this station, 5, 15 or 30.")

    # sensor fields, see doc/weather_variables.md for details
    atmp  : Optional[float] = Field(default=None, description="air temperature, celsius") 
    dwpt  : Optional[float] = Field(default=None, description="dew point, celsius")
    lws   : Optional[float] = Field(default=None, description="this is an nominal reading or 0 or 1 (wet / not wet)")  
    pcpn  : Optional[float] = Field(default=None, description="precipitation, mm, > 0")   
    relh  : Optional[float] = Field(default=None, description="relative humdity, percent")
    rpet  : Optional[float] = Field(default=None, description="Reference Potential Evapotranspiration")
    smst  : Optional[float] = Field(default=None, description="soil moisture")
    srad  : Optional[float] = Field(default=None, description="solar radiation")
    wdir  : Optional[float] = Field(default=None, description="wind direction, deg from North")
    wspd  : Optional[float] = Field(default=None, description="wind speed, kph")



    @classmethod
    def model_validate_from_station(cls, sensor_data:dict, api_response: APIResponse, database = True):
        """ create reading from a list of sensor data from the `transform()` method of WeatherAPI, and add required metadata to dict of transformed weather data.   If the APIResponse record has not been stored 
        in the database already, then it won't have an ID and validation will fail.  set the flag 'database' = False to allow validation.   

        Args:
            sensor_data (list): list of sensor values extracted from APIResponse using the 'transform' method of Weather API
            api_response (APIResponse): object from _get_readings method of APIResponse that contains meta data for where the sensor values come from 
            database (bool, optional): Flag to allow non-database APIResponse objects to be used to make readings.  Set to false to allow using an APIResponse that is not in the database.   Ignored if APIResponse has an id.   Defaults to True.

        Raises:
            ValidationError: If the APIResponse object does not have an ID (e.g. not in the database), and the 'database' flag is not set to False

         Returns:
            Reading: Reading object. sensor values with metadata.   If database=False and APIResponse do not have an id, apireaponse_id==0    
        """
        r:dict = sensor_data # start with this dict and add meta data, r == reading

        from pydantic import ValidationError

        if not api_response.id:
            if database:
                raise ValidationError("Reading can't be created from APIResponse without database id, unless add flag 'database=False'")
            else:
                # this allows the transform to proceed but these reading records can't be inserted into the database
                r['apiresponse_id']  = 0
        else:
            r['apiresponse_id'] = api_response.id
            
        # redundant columns to reduce the need for joins
        r['request_id']          = api_response.request_id
        r['weatherstation_id']   = api_response.weatherstation_id
        r['station_sampling_interval']   = api_response.station_sampling_interval
        return(cls.model_validate(r))

