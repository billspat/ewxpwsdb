"""
Subclass of WeatherAPI for the Zentra type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.
"""

import json, logging, time
from requests import get, Response
from datetime import datetime,timezone, timedelta
from typing import Self
from math import ceil

# from pydantic import Field
from . import STATION_TYPE
from .weather_api import WeatherAPI, WeatherAPIConfig

from ewxpwsdb.db.models import WeatherStation

class ZentraAPIConfig(WeatherAPIConfig):
        _station_type   : STATION_TYPE = 'ZENTRA'
        sn             : str #  The serial number of the device.
        token          : str # The user's access token.


class ZentraAPI(WeatherAPI):
    """Subclass of WeatherAPI with methods specific to Zentra weather stations from the Meter Group.  
    This API allows one call per 60s, so this includes code to determine if it must wait and delays returning for that long """

    APIConfigClass = ZentraAPIConfig    # type: ignore[assignment]
    _station_type = 'ZENTRA'
    _sampling_interval = interval_min = 5

    _MAX_READINGS_PER_PAGE:int = 2000


    # sensor names that appear in response data and equiv EWX fields.  
    # Update this to add more types of sensors.  assumes there is no transform of these values needed
    _sensor_transforms = {
        'Air Temperature':'atmp', 
        'Precipitation':'pcpn',
        'Relative Humidity':'relh',
        'Leaf Wetness':'lws'
        }
    
    def __init__(self, weather_station:WeatherStation, max_retries: int = 2):
        self._max_retries : int = max_retries
        super().__init__(weather_station)  
        # cast api config to Zentra type for static type checking
        self.api_config: ZentraAPIConfig = self.api_config


    @property
    def max_retries(self) -> int:
        return self._max_retries

    @max_retries.setter
    def max_retries(self, value: int):
        self._max_retries = value

    @property
    def sampling_interval(self)->int:
        return self._sampling_interval
    
    @property
    def sensor_transforms(self)->dict[str,str]:
        return self._sensor_transforms
    
    def _expected_page_count(self,start_datetime:datetime, end_datetime:datetime, page_len:int|None = None)->int:
        """given a number of readings per page, determine the total number of readings based on the start and end times

        Args:
            start_datetime (datetime): beginning of time interval sent to get_readings
            end_datetime (datetime): end of time interval sent to get_readings
            page_len (int, optional): number of readings per page, Defaults to Meter group max of 2000.

        Returns:
            int: number of pages expected to be returned for get_readings to loop through
        """

        if not page_len:
            page_len = self._MAX_READINGS_PER_PAGE

        delta_seconds:float = (end_datetime - start_datetime).total_seconds()
        minutes_delta:int = ceil(delta_seconds/60.0)
        expected_reading_count:int = ceil(minutes_delta/self._sampling_interval)
        expected_page_count:int = ceil(expected_reading_count/page_len)
    
        return expected_page_count
        

    def _get_readings(self, start_datetime:datetime, end_datetime:datetime)->list[Response]:
        """ Builds, sends, and stores raw response from Zentra API
        start_datetime, end_datetime : timezone aware datetimes in UTC, zentra converts to station-local time
        """
        
        url = "https://zentracloud.com/api/v4/get_readings/"
        token =  f"Token {self.api_config.token}" # "Token {TOKEN}".format(TOKEN="your_ZENTRACLOUD_API_token")
        headers = {'content-type': 'application/json', 'Authorization': token}
        params: dict[str,int|str] = {'device_sn' : self.api_config.sn, 
                  'start_date': self._format_time(self.dt_local_from_utc(start_datetime)), 
                  'end_date'  : self._format_time(self.dt_local_from_utc(end_datetime)), 
                  'per_page'  : self._MAX_READINGS_PER_PAGE }
        
        responses = []
        expected_page_count:int = self._expected_page_count(start_datetime, end_datetime, page_len = self._MAX_READINGS_PER_PAGE)
        
        for page_num in range(expected_page_count):
            params['page_num'] = page_num+1  # zero-based languages are annoying
            response = get(url, params=params, headers=headers) 

            # Handles the 1 request/60 second throttling error
            retry_counter = 0
            while response.status_code == 429 and self.max_retries > 0:
                retry_counter += 1
                if retry_counter > self.max_retries:
                    err_message = f"Zentra timed out {self.max_retries} times"
                    raise RuntimeError(err_message) 

                lockout = int(response.text[response.text.find("Lock out expires in ")+20:response.text.find("Lock out expires in ")+22])
                logging.warning(f"Zentra station {self.weather_station.station_code} API too-frequent request throttle, retrying in {lockout+1} seconds...")
                time.sleep(lockout + 1)

                response = get(url, params=params, headers=headers)
            
            responses.append(response)

        return(responses)


    def _data_present_in_response(self, response_data:dict)->bool:
        """check for presence of data in response

        Args:
            response_data (dict): data loaded from response JSON

        Returns:
            bool: True if data is present in any of the records in the response, else False
        """
        
        if 'data' not in response_data.keys():
            return False
        
        for sensor in response_data['data']: # response_data['data'].keys()
            if sensor in self._sensor_transforms:
                for zentra_reading in response_data['data'][sensor][0]['readings']:
                    if zentra_reading.get('value'):
                        return True

        return False


    def _transform(self, response_data)->list:
        """
        Transforms response text from Zentra API into a standardized format 
        params:
            response_data : JSON string from response.text or dict 
        returns:
            list of dict for each sensor reading
        """
        
        if isinstance(response_data, str):
            response_data = json.loads(response_data)

        # Return an empty list if there is no data contained in the response, this covers error 429
        # print(response_data)

        # if 'data' not in response_data.keys():
        #     logging.error("data element not found in response_data (returning empty):")
        #     logging.debug(response_data)
        #     return []
        # else:
        #     logging.debug("Zentra readings found")
        

        # Build a ZentraReading object for each and put it into the readings_list
        # the readings are sensor-wise, not timestamp-wise, so we need to collect all the timestamps from 
        # the first reading, then build our list sensor wise. 

        # a dict of dict keyed on timestamp
        readings_by_timestamp = {}

        for sensor in response_data['data']: # response_data['data'].keys()
            if sensor in self._sensor_transforms: # only include those sensors that we have transforms for
                # loop through the readings of this sensor, build up timestamp-keyed dict of dict
                for zentra_reading in response_data['data'][sensor][0]['readings']:

                    timestamp = zentra_reading['timestamp_utc']
                    # if we haven't seen this timestamp before, create a new entry in our readings dict
                    if timestamp not in readings_by_timestamp:
                        # add the datetime which would be the same for all readings with this time stamp
                        reading_datetime = datetime.fromtimestamp(timestamp).astimezone(timezone.utc)
                        readings_by_timestamp[timestamp] = {'data_datetime': reading_datetime}
                    
                    # add this sensor value to our ewx reading dict
                    ewx_field_name = self._sensor_transforms[sensor]
                    readings_by_timestamp[timestamp][ewx_field_name] = zentra_reading['value']

        # no longer need the timestamp keys, and calling program is expecting a list ()
        return list(readings_by_timestamp.values())
    
    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass
