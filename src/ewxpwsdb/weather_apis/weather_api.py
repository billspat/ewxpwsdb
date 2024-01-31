"""
classes and types to support data acquisition from weather station vendor web APIs. 
"""

# #TODO see some code in models.py that should be here that is a new way to organize the data classes for validation and loading
# #TODO get rid of madeup 2-character timezones - just use the standard IANA timezones used by python (and Operating systems) in ZoneInfo/tzdata packages
# #   see models.py for example

from pydantic import BaseModel, ConfigDict
from typing import Optional
import json, warnings, logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from abc import ABC, abstractmethod
from uuid import uuid4
from requests import Response


from ewxpwsdb import __version__ # from importlib.metadata import version didn't work
from ewxpwsdb.time_intervals import is_tz_aware, UTCInterval
from ewxpwsdb.db.models import WeatherStation, Reading, APIResponse
from . import STATION_TYPE 


# TODO can we use ABC here?
class WeatherAPIConfig(BaseModel):
    """Base API configuration model to validate configuration values for connecting to various vendor APIs.  
    API configs are stored in the Stations table using a single string field that is intended for JSONified dictionary of config values 
    This is a generic class that must be Sub-classed for each type of API, adding fields specific to their configuration.  
    """

    # there are no common fields, this class is not meant to be instantiated

    model_config = ConfigDict(frozen=True) # don't allow adding extra attribs for security

    @property
    def station_type(self) -> STATION_TYPE: 
        """ return station class, override for each type"""
        return(self._station_type)

    ### unserializer/serializers for db/record storage that accommodate fields in subclasses consistently
    @classmethod
    def model_validate_json_str(cls, api_config_str: str):
        """ create config obj from our standard serialization format (from disk/db/etc.  In the serialization format, additional station-specific
        fields are stored as a JSON dictionary in the 'station_config. """
        
        # station-type-specific config is held as JSON in a special field (station config). 
        # This unpacks and loads any items from that 'station_config' field up into the class
        api_config_dict = json.loads(api_config_str) 
        return(cls.model_validate(api_config_dict))


 
#################################################################################
class GenericAPIConfig(WeatherAPIConfig):
    """This dummy configuration is used for abstract base class of the API and for testing"""
    _station_type : str = 'GENERIC'
    secret : Optional[str] = "abracabra"


#################################################################################
class WeatherAPI(ABC):
    """abstract base class for a weather station to access it's API and retrieve and transform data. """
    
    #override with config class per vendor, e.g. DavisAPIConfig
    APIConfigClass = WeatherAPIConfig  
    _station_type = None
    _sampling_interval = 0 
    empty_response = ['{}']


    #### constructor
    def __init__(self, weather_station:WeatherStation):
        """
        create weather api object to collect data from external station vendor weather api
        
        params: 
            weather_station: instance of a WeatherStation model class that contains api config as str """    

        #TODO add run-time validation of weather_station object
        
        if weather_station.station_type != self.station_type:
            raise ValueError(f"weather station type does not match {self.station_type}")
        
        self.weather_station = weather_station
        self.api_config = self.APIConfigClass.model_validate_json_str(weather_station.api_config)

        # store latest resp object as returned from request
        self.current_responses = [] # None # list[APIResponse]
        self.current_api_response_records = []


    #### convenience/hiding methods
    @property
    def sampling_interval(self):
        """interval between weather readings in minutes.   Hourly frequency is sampling_interval/60 """
        return(self._sampling_interval)

    @property
    def station_type(self):
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

    def _format_time(self, dt:datetime)->str:
        """
        format date/time parameters for specific API request, convert to 
        UTC or local as needed.  The generic converter simply converts to ISO.  
        """
        
        return(dt.strftime('%Y-%m-%d %H:%M:%S'))
    

    #### primary class interfaces
    def get_readings(self, start_datetime : datetime = None, end_datetime : datetime = None)->list[APIResponse]:
        """prepare start/end times and other params generically and then call station-specific method with that.

        parameters:
            start_datetime: optional, date time in UTC time zone that the readings start. Defaults to current time - station sampling interval 
            end_datetime: date time in UTC time zone.  If start_datetime is empty this is ignored, defaults to start_datetime + station sampling interval (5, 10, 15 minutes)
        
        returns:
            WeatherAPIData object containing request metadata and dict of responses
        """
        
        if end_datetime and start_datetime:
            interval = UTCInterval(start = start_datetime, end = end_datetime)

        elif end_datetime and not start_datetime:
            interval = UTCInterval.previous_interval(end_datetime)
        
        elif not end_datetime and start_datetime: 
            interval = UTCInterval.previous_interval(start_datetime + timedelta(minutes= 14),delta_mins=14)
        
        else : # both are null
            interval = UTCInterval.previous_fifteen_minutes()
       
        ###### call the sub-class to pull data from the station vendor API
        # save the response object in this object
        try:
            # get the request timestamp right away, save in object only if request was successful
            request_datetime = datetime.utcnow().astimezone(timezone.utc)
            responses = self._get_readings(
                    start_datetime = interval.start,
                    end_datetime = interval.end
            )

        except Exception as e:
            logging.error(f"Error getting reading from station {self.id}: {e}")
            raise e

        # ensure what is returned is _always_ a list of responses
        if not isinstance(responses, list):
            responses = [responses]
            # list of requests.response obj

        self.current_request_datetime = request_datetime
        self.current_responses = responses

        # convert each to our serializer model 

        # TODO fix the end data time may not be correct if it spans multiple days!!!!
        self.current_api_response_records = [self._add_response_metadata(r, start_datetime, end_datetime, request_datetime) for r in responses]

        return(self.current_api_response_records)


    def _add_response_metadata(self, response:Response, start_datetime:datetime, end_datetime:datetime, request_datetime:datetime = datetime.utcnow().astimezone(timezone.utc) )->APIResponse:
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



    def transform(self, api_response_records:list[APIResponse] = None)->list[Reading]:
        """
        Transforms data and return it in a standardized format. 
        data: optional input used to load in data if transform of existing data dictionary is required.
        Usage from stored data
        dict_api_record = db.get_by_data(something) or get_by_req_id(request_id)
        api_response = optional WeatherAPIData (object or dict)
        """

        # if no data was sent, use data stored from latest request
        api_response_records = api_response_records or self.current_api_response_records

        readings = []
        # run-time conversion and validation to allow for list of dictionaries for example
        try:
            for api_response_record in api_response_records:
                if not isinstance(api_response_record, APIResponse):
                    api_response_record = APIResponse.model_validate(api_response_record)

                    # call station subclass to interpret response content into a list
                    # TODO create class to hold sensor data, currently just a dictionary
                    sensor_data =  self._transform(api_response_record.response_text)
                    if sensor_data is not None:
                        logging.debug(f"transformed_reading type {type(sensor_data)}: {sensor_data}")
                        

                        reading = Reading.new_from_transform(sensor_data, api_response_record)
                        
                        readings.append(reading)
                        ### TODO create READING OBJECT FROM THIS AND THE METADATA
                    else:
                        logging.debug(f"could not transform {api_response_record.response_text}")
  
        
        except Exception as e:
            print(f'could not transform: {e}')
            return []
        

        self.current_readings =readings

        
        return readings
        
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
    

