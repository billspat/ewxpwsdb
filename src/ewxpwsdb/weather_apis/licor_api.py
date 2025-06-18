"""
Subclass of WeatherAPI for the Licor (Onset) type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.

timestamps are localtime with no timezone.  
Readings are in a flatnames space under 'data' key, on reading per sensor per timestamp. 

Weather Variables in "sensor_measurement_type" field are named as follows:

- Battery "V"
- Dew Point "°C"
- Gust Speed "m/s"
- Rain "mm"
- RH "%"
- Solar Radiation "W/m²"
- Temperature "°C"
- Wetness  "%"
- Wind Direction "°
- Wind Speed "m/s"

"""

import json
from requests import get, Response
from requests.utils import quote
from datetime import datetime, timezone, UTC
import logging

from pydantic import Field


from . import STATION_TYPE
from ewxpwsdb.weather_apis.weather_api import WeatherAPIConfig, WeatherAPI
from ewxpwsdb.db.models import WeatherStation


# Initialize the logger
logger = logging.getLogger(__name__)


class LicorAPIConfig(WeatherAPIConfig):
    _station_type : STATION_TYPE  = 'LICOR'
    sn : str  = Field(description="The serial number of the device")
    api_token: str = Field(description="API key obtained from the portal")

class LicorAPI(WeatherAPI):
    APIConfigClass: type[LicorAPIConfig] = LicorAPIConfig
    _station_type: STATION_TYPE = 'LICOR'
    _sampling_interval = interval_min = 5
    _lws_threshold = 0.5
    # supported_variables = ['atmp', 'dwpt', 'lws', 'pcpn', 'relh', 'srad', 'wdir', 'wspd', 'wspd_max']
    # lws sensor down since May 31, 2024.  removing completely from the variables here. 
    supported_variables = ['atmp', 'dwpt', 'pcpn', 'relh', 'srad', 'wdir', 'wspd', 'wspd_max']

    def __init__(self, weather_station:WeatherStation):    
        """ create class from config Type"""
        self._access_token = None
        super().__init__(weather_station)
        # cast api config to correct type for static type checking
        self.api_config: LicorAPIConfig = self.api_config
        logger.info("Initialized LicorAPI for station %s", weather_station.station_code)

    def _check_config(self):
        # TODO implement 
        return(True)
            
    def _get_readings(self,start_datetime:datetime,end_datetime:datetime) ->list[Response] :
        """ use Licor API to pull data from this station for times between start and end.  Called by the parent 
        class method get_readings().   
        
        parameters:
            start_datetime: datetime object in UTC timezone.  
            end_datetime: datetime object in UTC timezone.  
        """
 
        start_datetime_str = self._format_time(start_datetime)
        end_datetime_str = self._format_time(end_datetime)
        logger.debug(f"converted datetimes form {start_datetime} to {start_datetime_str}")

        # example working Licor API URL.  Notice the separator for date/time query 
        # parameter is a space or %20. 
        # https://api.licor.cloud/v1/data?loggers=99999999&start_date_time=2025-06-01%2012%3A45%3A00&end_date_time=2025-06-01%2013%3A45%3A00 
        # the python requests lib will encode a "+" for space automatically
        # so have to encode with the 'quote' function AND can't use that function
        # in the requests.get() params - have to build the URL with the query 
        # string params ourselves.  This is a limit of requests.get
        # unlike the predecessor API (Onset/hobolink), date times are UTC in and out
        url_with_params = f"https://api.licor.cloud/v1/data?loggers={self.api_config.sn}&start_date_time={quote(start_datetime_str)}&end_date_time={quote(end_datetime_str)}"
        try:
            response = get( url=url_with_params,
                            headers={'Authorization': "Bearer " + 
                                     self.api_config.api_token},
                            )
            
            response.raise_for_status()
            
        except Exception as e:
            logger.error("Failed to retrieve data from %s API for interval %s - %s: %s", 
                         self._station_type, start_datetime, end_datetime, e)
            return []

        return([response])    
    
    def _data_present_in_response(self, response_data:dict)->bool:
        """check for presence of data in response

        Args:
            response_data (dict): data loaded from response JSON

        Returns:
            bool: True if data is present in any of the records in 
                  the response, else False
        """

        if 'data' not in response_data.keys():
            return False
        
        for reading in response_data["data"]:
            # any data found anywhere, return True
            if 'value' in reading.keys() and reading.get('value'):
                return True
            
        return False

    def _transform(self, response_data)->list[dict]:
        """
        Tranform data from Licor API to EWX database values. 
        timestamps are localtime with no timezone.  
        Readings are in a flatnames space under 'data' key, on reading per sensor per timestamp. 
        
        Weather Variables in "sensor_measurement_type" field are named as follows:

        - Battery "V"
        - Dew Point "°C"
        - Gust Speed "m/s"
        - Rain "mm"
        - RH "%"
        - Solar Radiation "W/m²"
        - Temperature "°C"
        - Wetness  "%"
        - Wind Direction "°"
        - Wind Speed "m/s"
        
        Args:
            response_data: the text of the response object, either JSON str, 
            in which case it's loaded, or the list of readings already loaded
            from JSON
            
        Returns:
            list of reading records (dict) 

        """

        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        if not self._data_present_in_response(response_data):
            return None
        
        readings = {}
    
        for sensor_reading in response_data["data"]:
            
            ts = sensor_reading["timestamp"]  
            
            # timestamp is actually UTC, not localtime, convert to UTC, but has no timezone info
            # ts = local_datetime_to_utc_datetime(local_datetime = ts, local_timezone = self.weather_station.timezone) 
            
            # Create new entry if time hasn't been encountered yet
            if ts not in readings.keys():                
                readings[ts] = {"data_datetime" : datetime.fromisoformat(ts) }
                        
            match sensor_reading["sensor_measurement_type"]:
                case 'Dew Point':
                    readings[ts]['dwpt'] = sensor_reading["value"]
                case 'Rain':
                    readings[ts]['pcpn'] = sensor_reading["value"]
                case 'RH':
                    readings[ts]['relh'] = sensor_reading["value"]
                case 'Solar Radiation':
                    readings[ts]['srad'] = sensor_reading["value"]
                case 'Temperature':
                    readings[ts]['atmp'] = sensor_reading["value"]
                case 'Wetness':
                    readings[ts]['lws']  = self.wetness_transform(sensor_reading["value"])  # %
                case 'Wind Direction':
                    readings[ts]['wdir'] = sensor_reading["value"]
                case 'Wind Speed':
                    readings[ts]['wspd'] = sensor_reading["value"]  
                case 'Gust Speed':
                    readings[ts]['wspd_max'] = sensor_reading["value"]  

        transformed_readings = list(readings.values())
        from ewxpwsdb.db.models import Reading
        return transformed_readings
        

    def wetness_transform(self, w):
        return 1 if w >= self._lws_threshold else 0
            

    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass
