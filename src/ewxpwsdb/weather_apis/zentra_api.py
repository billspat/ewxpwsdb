"""
Subclass of WeatherAPI for the Zentra type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.

Variables available from the Zentra API: 

- Air Temperature
- Atmospheric Pressure
- Battery Percent
- Battery Voltage
- Gust Speed (m/s)
- Leaf Wetness
- Lightning Activity
- Lightning Distance
- Logger Temperature
- Max Precip Rate (mm/h)
- Precipitation (mm)
- RH Sensor Temp
- Reference Pressure
- Relative Humidity
- Soil Temperature
- Solar Radiation
- VPD
- Water Content
- Wetness Level (unit less)
- Leaf Wetness (min)
- Leaf Wetness (high) (min)
- Wind Direction
- Wind Speed (m/s)

Unit strings: 
- 'Atmospheric Pressure' : ' kPa'
- 'Air Temperature' : ' °C'
- 'Gust Speed' : ' km/h'
- 'Precipitation' : ' in'
- 'Soil Temperature' : ' °C'
- 'Solar Radiation' : ' W/m²'
- 'Wind Direction' : '°'
- 'Wind Speed' : ' km/h'

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

# Initialize the logger
logger = logging.getLogger(__name__)

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
    _lws_threshold = 450


    _MAX_READINGS_PER_PAGE:int = 2000
    supported_variables = ['atmp', 'lws', 'pcpn', 'relh', 'srad', 'smst', 'stmp', 'wspd', 'wdir', 'wspd_max']


    # sensor names that appear in response data and equiv EWX fields.  
    # used to tell if data is present, etc.  For transforms, 
    # see  _lookup_sensor_transform()
    _sensor_fieldnames = {
        'Air Temperature':'atmp', 
        'Wetness Level':'lws',
        'Precipitation':'pcpn',
        'Relative Humidity':'relh',
        'Soil Temperature': 'stmp',
        'Solar Radiation':'srad',
        'Wind Speed':'wspd',
        'Wind Direction':'wdir',
        'Gust Speed':'wspd_max',
        
        }
    
    def _lookup_sensor_transform(self, sensor_name:str, sensor_units:str)->tuple[str,callable]:
        """given the name the weather station uses for the sensor, and the units
        provide by the api response, get the database field name and a function
        to convert/transform the value sent. If the station's sensor is not 
        one we store, return a blank string for field name.  If the units are 
        already how we store them, don't use a transform 
        (for example degrees Celsius) so we send the 
        'identity' function which doesn't alter the value
        TODO: this function assumes if units are not metric they must be 
        imperial.  Re-code to check for either units and fail if neither

        Args:
            sensor_name (str): sensor name in the JSON response data
            sensor_units (str): string decribing units in JSON response data, 
                    for example ' \\u00b0C' which is ' °C'

        Returns:
            tuple[str,callable]: the ewx db field name, or blank for sensors
            we don't sort ( "") and a transform to use.  
        """
        
        # set defaults here so that 
        sensor_transform = self.identity
        ewx_field_name = ""
        match sensor_name:
            case 'Air Temperature':
                if sensor_units != ' \\u00b0C':
                    sensor_transform = self.f_to_c
                ewx_field_name = 'atmp'
                
            case 'Wetness Level':
                sensor_transform = self._zentra_leaf_wetness_transform
                ewx_field_name = 'lws'

            case 'Precipitation':
                if sensor_units == ' in':
                    sensor_transform = self.in_to_mm 
                ewx_field_name = 'pcpn'
                
            case 'Relative Humidity':
                ewx_field_name = 'relh'
                
            case 'Soil Temperature':
                if sensor_units != ' \\u00b0C':
                    sensor_transform = self.f_to_c
                ewx_field_name =  'stmp'
                
            case 'Solar Radiation':
                ewx_field_name = 'srad'
                
            case 'Wind Speed':
                if sensor_units != ' km/h':
                    sensor_transform = self.mph_to_ms
                else:
                    sensor_transform = self.kph_to_ms 
                ewx_field_name = 'wspd'
                
            case 'Wind Direction':
                ewx_field_name = 'wdir'
                
            case 'Gust Speed':
                if sensor_units != ' km/h':
                    sensor_transform = self.mph_to_ms
                else:
                    sensor_transform = self.kph_to_ms 
                ewx_field_name = 'wspd_max'
            
            case other:
                # sensor is not one we transform, send defaults
                # the caller will have to check for empty field name
                ewx_field_name = ""            
        
        return(ewx_field_name, sensor_transform)

        
    def _zentra_leaf_wetness_transform(self, lws_value):
        """Convert data from Meter group PHYTOS 31 sensor to 1=wet, 0=not wet
        using the 'Wetness Level' of the last minute.   This also has a "Leaf Wetness(min) which is (n minutes > 450) / minutes """
        return 1 if lws_value >= self._lws_threshold else 0
    
    def __init__(self, weather_station:WeatherStation, max_retries: int = 3):
        self._max_retries : int = max_retries
        super().__init__(weather_station)  
        # cast api config to Zentra type for static type checking
        self.api_config: ZentraAPIConfig = self.api_config
        logger.debug("Initialized ZentraAPI for station %s", weather_station.station_code)

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
    def sensor_fieldnames(self)->dict[str,str]:
        return self._sensor_fieldnames
    
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
        
        #TODO near this point, call API to determine the units being used
        
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
                    logger.error(err_message)
                    raise RuntimeError(err_message) 

                lockout = int(response.text[response.text.find("Lock out expires in ")+20:response.text.find("Lock out expires in ")+22])
                logger.warning(f"Zentra station {self.weather_station.station_code} API too-frequent request throttle, retrying in {lockout+1} seconds...")
                time.sleep(lockout + 1)

                response = get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                logger.error("Failed to retrieve data for page %s: %s", page_num+1, response.text)

            responses.append(response)

        logger.debug("Successfully retrieved data for interval %s - %s", start_datetime, end_datetime)
        return responses


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
            if sensor in self._sensor_fieldnames:
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
            list of dict for each sensor reading to be stored in db
        """
        
        if isinstance(response_data, str):
            response_data = json.loads(response_data)

        # Return an empty list if there is no data contained in the response, this covers error 429
        # print(response_data)
        if 'data' not in response_data.keys():
             logging.error("data element not found in Zentra response_data (returning empty):")
             logging.debug(response_data)
             return []

        # Build a ZentraReading object for each and put it into the readings_list
        # the readings are sensor-wise, not timestamp-wise, so we need to 
        # collect all the timestamps to build a timestamp-wise list to store
        # each sensor has a list

        # a dict of dict keyed on timestamp to be filled
        readings_by_timestamp = {}

        # loop through the keys of the 'data' dictionary, the sensor names
        for sensor in response_data.get('data'): 
            
            # if not a sensor we store, skip it
            if sensor not in self._sensor_fieldnames:
                continue

            # zentra returns a list of data, usually just one element, but
            # maybe broken into chunks in case the units were changed 
            # loop through list of entries under this sensor            
            for sensor_data in response_data['data'][sensor]:
                # using subclass method, determine the field name & transform                
                sensor_units = sensor_data['metadata']['units'] 
                ewx_field_name, this_sensor_transform = self._lookup_sensor_transform(sensor, sensor_units)
            
                # double check, if not a sensor we transform, skip it
                if ewx_field_name == "":  
                    continue 
                
                # loop through the readings of this sensor, build up timestamp-keyed dict of dict
                for zentra_reading in sensor_data['readings']:                    
                    timestamp = zentra_reading['timestamp_utc']

                    # if we haven't seen this timestamp before, create a new entry in our readings dict
                    if timestamp not in readings_by_timestamp:
                        # add the datetime which would be the same for all readings with this time stamp
                        reading_datetime = datetime.fromtimestamp(timestamp).astimezone(timezone.utc)
                        readings_by_timestamp[timestamp] = {'data_datetime': reading_datetime}

                    # add the transformed reading to the db for that field name                    
                    readings_by_timestamp[timestamp][ewx_field_name] = this_sensor_transform(zentra_reading['value'])

        readings = list(readings_by_timestamp.values())
        
        return readings
        
    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass
