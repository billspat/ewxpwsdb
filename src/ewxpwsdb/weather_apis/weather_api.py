"""
parent classes and types to support data acquisition from weather station vendor web APIs. 
The class WeatherAPI is abstract and must be sub-classed and is not used directly. 
"""

# #TODO see some code in models.py that should be here that is a new way to organize the data classes for validation and loading
# #TODO get rid of madeup 2-character timezones - just use the standard IANA timezones used by python (and Operating systems) in ZoneInfo/tzdata packages
# #   see models.py for example

from pydantic import BaseModel, ConfigDict
from typing import get_args, Self
import json, warnings, logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from abc import ABC, abstractmethod
from uuid import uuid4
from requests import Response


from ewxpwsdb import __version__ # from importlib.metadata import version didn't work
from ewxpwsdb.time_intervals import is_tz_aware, UTCInterval, is_utc
from ewxpwsdb.db.models import WeatherStation, Reading, APIResponse
from . import STATION_TYPE 

#################################################################################
class WeatherAPIConfig(BaseModel):
    """Base API configuration model to validate configuration values for connecting to various vendor APIs.  
    API configs are stored in the Stations table using a single string field that is intended for JSONified dictionary of config values 
    This is a generic class that must be Sub-classed for each type of API, adding fields specific to their configuration.  
    """

    _station_type: STATION_TYPE = None
    # there are no common fields, this class is not meant to be instantiated

    model_config = ConfigDict(frozen=True) # don't allow adding extra attribs for security

    @property
    def station_type(self) -> STATION_TYPE: 
        """ return station class, override for each type"""

        # note this syntax passes mypy but allows us to use str class attribute for easy reading
        return  self._station_type
        

    ### unserializer/serializers for db/record storage that accommodate fields in subclasses consistently
    @classmethod
    def model_validate_json_str(cls, api_config_str: str) ->Self:
        """ create config obj from our standard serialization format (from disk/db/etc.  In the serialization format, additional station-specific
        fields are stored as a JSON dictionary in the 'station_config. """
        
        # station-type-specific config is held as JSON in a special field (station config). 
        # This unpacks and loads any items from that 'station_config' field up into the class
        api_config_dict = json.loads(api_config_str) 
        return(cls.model_validate(api_config_dict))


 
#################################################################################
class WeatherAPI(ABC):
    """abstract base class for a weather station to access it's API and retrieve and transform data. """
    
    #override with config class per vendor, e.g. DavisAPIConfig
    APIConfigClass = WeatherAPIConfig  
    # station type must be one of STATION_TYPE type, reset this in 
    _station_type: STATION_TYPE = None
    _sampling_interval = 0 
    standard_time_interval_minutes:int = 14

    supported_variables:list[str] = ['atmp', 'atmp_min', 'atmp_max', 'lws', 'pcpn', 'relh', 'srad', 'smst', 'stmp', 'wspd', 'wsp_max', 'wdir']
    empty_response = ['{}']


    #### constructor
    def __init__(self, weather_station:WeatherStation):
        """
        create weather api object to collect data from external station vendor weather api
        
        params: 
            weather_station: instance of a WeatherStation model class that contains api config as str """    

    
        # ensure the subclass is using a valid station type    
        assert self.station_type in get_args(STATION_TYPE)

        # ensure the data record has the same station type as this class
        if weather_station.station_type != self.station_type:
            raise ValueError(f"weather station type does not match {self.station_type}")
        
        self.weather_station = weather_station
        self.api_config: WeatherAPIConfig = self.APIConfigClass.model_validate_json_str(weather_station.api_config)

        # store latest resp object as returned from request but don't need to declare them here
        # self.current_responses = [] # type: ignore
        # self.current_api_response_records = []  # type: ignore

    #### convenience/hiding methods
    @property
    def sampling_interval(self):
        """interval between weather readings in minutes.   Hourly frequency is sampling_interval/60 """
        return(self._sampling_interval)

    @property
    def station_type(self)->STATION_TYPE:
        """interval between weather readings in minutes.   Hourly frequency is sampling_interval/60 """
        return(self._station_type)
    
    @property
    def id(self):
        return self.weather_station.id
    

    #### abstract methods to be implemented in subclass
    # @abstractmethod
    # def _check_config(self)->bool:
    #     return(True)        

    @abstractmethod
    def _transform(self, response_data):
        """transforms a response into a json to be exported"""
        return None
    
    @abstractmethod
    def _get_readings(self,start_datetime:datetime, end_datetime:datetime)->list[Response]:
        """create API request and return str of json

        params:
            start_datetime: timezone aware datetime in UTC
            end_datetime: timezone aware datetime in UTC

        returns: list of Response object,   #TODO add the dates???
        """
        pass

    @abstractmethod
    def _data_present_in_response(self, response_data:dict)->bool:
        return True


    def _format_time(self, dt:datetime)->str:
        """
        format date/time parameters for specific API request, convert to 
        UTC or local as needed.  The generic converter simply converts to ISO.  
        """
        
        return(dt.strftime('%Y-%m-%d %H:%M:%S'))
    

    #### primary class interface
    def get_readings(self, start_datetime : datetime|None = None, end_datetime : datetime|None = None)->list[APIResponse]:
        """prepare start/end times and other params generically and then call station-specific method with that.

        args:
            start_datetime: optional, timezone-aware datetime in UTC that the readings start. Defaults to current time - station sampling interval 
            end_datetime: date time in UTC time zone.  If start_datetime is empty this is ignored, defaults to start_datetime + station sampling interval (5, 10, 15 minutes)
        
        returns:
            WeatherAPIData object containing request metadata and dict of responses
        """
        
        if end_datetime and start_datetime:
            interval = UTCInterval(start = start_datetime, end = end_datetime)

        elif end_datetime and not start_datetime:
            interval = UTCInterval.previous_interval(end_datetime)
        
        elif not end_datetime and start_datetime: 
            interval = UTCInterval.previous_interval(start_datetime + timedelta(minutes= self.standard_time_interval_minutes),delta_mins=self.standard_time_interval_minutes)
        
        else : # both are null
            # let UTCInterval class pick endtime, startime standard interval minutes before that. 
            interval = UTCInterval.previous_interval(delta_mins=self.standard_time_interval_minutes)
    
       
        ###### call the sub-class to pull data from the station vendor API
        # save the response object in this object
        try:
            # get the request timestamp right away, save in object only if request was successful, in UTC
            request_datetime = datetime.now(timezone.utc)
            responses = self._get_readings(
                    start_datetime = interval.start,
                    end_datetime = interval.end
            )

        except Exception as e:
            logging.error(f"Error getting reading from station {self.id}: {e}")
            raise e

        # ensure what is returned is _always_ a list
        if not isinstance(responses, list):
            responses = [responses]

        self.current_request_datetime = request_datetime
        self.current_responses = responses

        # convert each to our serializer model 

        self.current_api_response_records = [self._add_response_metadata(r, interval.start, interval.end, request_datetime) for r in responses]

        # print("DEBUG CURRENT RESPONSES IN API CLASS")
        # print(self.current_api_response_records)
        # print("---------")
        return(self.current_api_response_records)


    def _add_response_metadata(self, response: Response, start_datetime: datetime, end_datetime: datetime, request_datetime: datetime = datetime.now(timezone.utc)) -> APIResponse:
        """combine a response object with metadata from this station, etc
        
        parameters
            response: a single response object
            start_datetime: datetime for start of time span of weather data
            end_datetime: datetime for end of time span of weather data
            request_datatime: a datetime timestamp assumed to be UTC
            
        returns
            APIResponse model object
        """
        
        api_response_record = APIResponse(
            request_id = str(uuid4()),  # locally generate a unique key for this response 
            weatherstation_id = self.weather_station.id,
            station_sampling_interval = self.sampling_interval,
            request_datetime = request_datetime, 
            data_start_datetime = start_datetime, 
            data_end_datetime =  end_datetime,
            package_version = __version__, # version('ewxpwsdb')? 
            # response data
            request_url =  response.request.url,
            response_status_code  = response.status_code,
            response_reason = response.reason,
            response_text = response.text,
            response_content  = response.content,

            )
    
        return(api_response_record)


    def data_present_in_response(self, api_response:APIResponse)-> bool:
        """test if the response from the api contains sensor data.  Data is not validated, it just needs to be present. 
        Given diversity of response forms, and some may even return status code 200 'OK' but there may not be data available.  
        This calls a private method to be overridden by each station type similar to _transform methods

        Args:
            api_response (APIResponse): a single response record to check.  Note that since get_reading returns a list of APIResponse, use a map to examine those

        Returns:
            bool: True if there is sensor data into the response, False if not. 
        """
        # if we don't get a 200, there is an error of some kind for all station types
        # assume this is a string but in case it's an int, convert to str to be safe
        if str(api_response.response_status_code) != '200':
            return False
        
        response_text:str = api_response.response_text

        # check if JSON
        if isinstance(response_text,str):
            try:
                response_data:dict = json.loads(response_text)
            except Exception as e:
                return False
        
        return self._data_present_in_response(response_data)


    def transform(self, api_response_records:list[APIResponse]|None = None, database:bool = True)->list[Reading]:
        """
        Transforms data and return it in a standardized format. 
        data: optional input used to load in data if transform of existing data dictionary is required.
        Usage from stored data
        dict_api_record = db.get_by_data(something) or get_by_req_id(request_id)
        Args:
            api_response_records (list[APIResponse], optional):

        Args:
            api_response_records (list[APIResponse] | None, optional):  APIresponse model objects, not simple Response. see models.py
            database (bool, optional): Flag to allow non-database APIResponse objects to be used to make readings.  Set to false to allow Reading object to be created from  APIResponse that is not in the database.   Ignored if APIResponse has an ID.  Defaults to True.

        Returns:
            list[Reading]: List of Reading records with metadata.   If database=False and APIResponse do not have an id, readings will have id==0
        """
        
        
        # if no data was sent, use data stored from latest request
        api_response_records = api_response_records or self.current_api_response_records
        
        all_response_readings = []
        # run-time conversion and validation to allow for list of dictionaries for example
        for api_response_record in api_response_records:
            # call station subclass private method to convert response content into a list of sensor readings
            # TODO create class to hold sensor data, currently just a dictionary
            sensor_data =  self._transform(api_response_record.response_text)
            
            # ensure sensor_data is always a list for uniform processing
            if not isinstance(sensor_data, list):
                sensor_data = [sensor_data]

            # convert those to Reading model objects with meta data
            readings = [Reading.model_validate_from_station(data, api_response_record, database) for data in sensor_data]
            all_response_readings.extend(readings)

        self.current_readings = all_response_readings

        return self.current_readings
        
    #### station class utilities
    def dt_utc_from_str(self, datetime_str: str)->datetime:
        """ To enable converting timestamp strings from api responses that 
            1) are in in station local time
            2) don't have a timezone info in the string (most don't)
            use the station's config timezone to convert to a timestamp str
            to a UTC timezone aware datateime
        """
        
        dt = datetime.fromisoformat(datetime_str)
        #
        if not is_tz_aware(dt):            
            dt = dt.replace(tzinfo = ZoneInfo(self.weather_station.timezone))
        else:
            # the string already has a timezone, could be anytimezone
            # should that be an error condition?

            pass

        return(dt.astimezone(timezone.utc))
    
    def dt_utc_from_ts(self,ts:int)->datetime:
        """convert numeric timestamp into utc timezone aware datetime

        Args:
            ts (int): UTC timestamp

        Returns:
            datetime:  utc timezone aware datetime object
        """

        dt:datetime = datetime.utcfromtimestamp(ts).astimezone(timezone.utc)
        return(dt)
    
    def dt_local_from_utc(self, dt:datetime)->datetime:
        """given a timezone-aware datetime in UTC, convert to station local time.
        
        Args:
            dt (datetime): datetime in UTC format
        
        Returns:
            datetime: datatime in timezone to the station attribute of this object
        """
        
        if not is_utc(dt):
            raise ValueError("datetime must be timezone aware and UTC")
        
        return(dt.astimezone(tz=ZoneInfo(self.weather_station.timezone)))

    def f_to_c(self,f:float)->float:
        """utility to convert Fahrenheit to centigrade for transform functions

        Args:
            f (float): temp in F

        Returns:
            float: temperature in Celsius/centigrade
        """
        c:float = (f - 32.0) * (5.0 / 9.0)
        return(c)
    
    def mph_to_ms(self, mph:float) -> float:  
        """convert mile per hour to meters per second   

        Args:
            mph (float): floating point value of mile per hour

        Returns:
            float: equiv value in meters per second
        """

        m_per_s:float = mph * 0.44704

        return(m_per_s)
    
    def kph_to_ms(self, kph:float) ->float:
        """convert kilometers per hour to meters per second

        Args:
            kph (float): kilometers per hour value

        Returns:
            float: converted value in meters/sec
        """
        conversion = 1000.0 / (60*60) 
        meters_per_second = round(kph * conversion, 2)
        return(meters_per_second)
    
    def get_test_reading(self):
        """ test that current config is working and station is online
        returns:
        True: station is on-line and configuration correct
        False: station is either off-line OR configuration incorrect
        """

        try:
            r = self.get_readings()
        except Exception as e:
            warnings.warn(f"error when testing api for station {self.id}: {e}")
            return(False)

        if r is not None:  # ensure that an empty reading is actually None
            return True
        else:
            warnings.warn("empty response when testing api for station {self.id}")
            return False
    

