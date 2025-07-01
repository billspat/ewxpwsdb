"""
Subclass of WeatherAPI for the Spectrum type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.

Spectrum Sensor Names: 
- Leaf Wetness
- Rainfall
- Relative Humidity
- Solar Radiation Light
- Temperature
- Wind Direction
- Wind Gust
- Wind Speed
"""

import json
from requests import get, Response
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import logging

from typing import Any

from . import STATION_TYPE
from .weather_api import WeatherAPI, WeatherAPIConfig
from ewxpwsdb.db.models import WeatherStation, APIResponse

# Initialize the logger
logger = logging.getLogger(__name__)

class SpectrumAPIConfig(WeatherAPIConfig):
        _station_type   : STATION_TYPE = 'SPECTRUM'
        sn             : str #  The station identifier. 
        apikey         : str #  The user's API access key.  

class SpectrumAPI(WeatherAPI):
    """Subclass of WeatherAPI with methods specific to specconnect.net for Spectrum weather stations"""

    APIConfigClass: type[SpectrumAPIConfig] = SpectrumAPIConfig
    _station_type: STATION_TYPE = 'SPECTRUM'
    _sampling_interval = interval_min = 5
    _lws_threshold = 7  # any value over 6 is considered wet -- spectrum manual


    supported_variables = ['atmp', 'lws', 'pcpn', 'relh', 'srad', 'wspd', 'wdir', 'wspd_max']


    def __init__(self, weather_station:WeatherStation):

        super().__init__(weather_station)  
        # cast api config to correct type for static type checking
        self.api_config: SpectrumAPIConfig = self.api_config
        logger.debug("Initialized SpectrumAPI for station %s", weather_station.station_code)

    def _format_time(self, dt:datetime)->str:
        """
        format date/time parameter for specconnect API request
        Spectrum API expects local time (zone) of the station's location for its `startDate` and `endDate`

        '%m-%d-%Y %H:%M'
        """
        
        # convert UTC date to timezone of station for request
        # use the converter in config obj to get python-friendly tz string
        dt = self.dt_local_from_utc(dt) # .replace(tzinfo=timezone.utc).astimezone(tz=ZoneInfo(self.weather_station.timezone))
        return(dt.strftime('%m-%d-%Y %H:%M'))
    
    def _get_readings(self,start_datetime:datetime, end_datetime:datetime)->list[Response]:
        """ request weather data from the specconnect API for a range of dates
        
        parameters:
            start_datetime: datetime object in UTC timezone.  
            end_datetime: datetime object in UTC timezone.  
        """
        start_datetime_str = self._format_time(start_datetime)
        end_datetime_str = self._format_time(end_datetime)
        
        try:
            response = get( url='https://api.specconnect.net:6703/api/Customer/GetDataInDateTimeRange',
                            params={'customerApiKey': self.api_config.apikey, 
                                    'serialNumber': self.api_config.sn,
                                    'startDate': start_datetime_str, 
                                    'endDate': end_datetime_str}
                          )
            response.raise_for_status()
            logger.debug("Successfully retrieved data for interval %s - %s", start_datetime, end_datetime)
        except Exception as e:
            logger.error("Failed to retrieve data for interval %s - %s: %s", start_datetime, end_datetime, e)
            return []

        return [response]


    def _data_present_in_response(self, response_data:dict)->bool:
        """check for presence of data in response

        Args:
            response_data (dict): data loaded from response JSON

        Returns:
            bool: True if data is present in any of the records in the response, else False
        """
        
        if  'EquipmentRecords' not in response_data.keys():
            return False
        
        if response_data['EquipmentRecords'] == []:
            return False
        
        if response_data['ApiCallStatus'] == "NoDataFound: No Data Found for Equipment":
            return False
        
        # any of the records has data, the 'OR' logic will set it to be 
        # true forever 
        has_data_state = False        
        for record in response_data['EquipmentRecords']:
            if not 'SensorData' in record.keys():
                has_data_state = (has_data_state or False)
            
            # if any one of these sensors have non-empty data, make it true
            if record['SensorData'][0]["DecimalValue"] or \
                record['SensorData'][1]["DecimalValue"] or \
                record['SensorData'][2]["DecimalValue"]:
                has_data_state = (has_data_state or True)

        return has_data_state 
    
        
    def _wetness_transform(self, w):
        return 1 if w >= self._lws_threshold else 0
    
    
    def _transform(self, response_data)->list[dict[str,Any]]:
        """
        Transforms data into a standardized format and returns it as a WeatherStationReadings object.
        data param if left to default tries for self.response_data processing

        """
        
        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        if 'EquipmentRecords' not in response_data.keys():
            return []
        
        readings:list[dict] = []
        for record in response_data['EquipmentRecords']:
            reading:dict[str,Any] = { 'data_datetime': self.dt_utc_from_str(record['TimeStamp'])}
            for sensor in record['SensorData']:
                match sensor['SensorType']:
                    case 'Temperature':
                        reading['atmp'] = round(self.f_to_c(sensor["DecimalValue"]), 2)
                    case 'Leaf Wetness':
                        reading['lws'] = self._wetness_transform(sensor["DecimalValue"])
                    case 'Rainfall':
                        reading['pcpn'] = sensor["DecimalValue"]  * 25.4
                    case 'Relative Humidity':
                        reading['relh'] = sensor["DecimalValue"]
                    case 'Solar Radiation Light':
                        reading['srad'] = sensor["DecimalValue"]
                    case 'Wind Direction':
                        reading['wdir'] = sensor["DecimalValue"]
                    case 'Wind Speed':
                        reading['wspd'] =  self.mph_to_ms(sensor["DecimalValue"])
                    case 'Wind Gust':
                        reading['wspd_max'] = self.mph_to_ms(sensor["DecimalValue"])
                    case _:
                        # we are only collecting the sensors above
                        pass

            readings.append(reading)

        
        logger.debug("Transformed readings: %s", readings)
        return readings
    
    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass

