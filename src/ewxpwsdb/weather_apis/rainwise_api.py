"""
Subclass of WeatherAPI for the Rainwise type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.
"""
#####  REQUIRES UPDATE TO WORK WITH CURRENT SYSTEM


import json
from requests import get, Response
from datetime import datetime

from . import STATION_TYPE
from ewxpwsdb.weather_apis.weather_api import WeatherAPIConfig, WeatherAPI
from ewxpwsdb.db.models import WeatherStation, APIResponse


class RainwiseAPIConfig(WeatherAPIConfig):
        _station_type   : STATION_TYPE = 'RAINWISE'
        username       : str|None = None
        sid            : str # Site id, assigned by Rainwise.
        pid            : str # Password id, assigned by Rainwise.
        mac            : str # MAC of the weather station. Must be in the group assigned to username.
        ret_form       : str # Values xml or json; returns the data as JSON or XML.


class RainwiseAPI(WeatherAPI):
    """ WeatherStation subclass for Rainwise API http://api.rainwise.net """

    APIConfigClass: type[RainwiseAPIConfig] = RainwiseAPIConfig
    _station_type: STATION_TYPE = 'RAINWISE'
    _sampling_interval = interval_min = 15


    def __init__(self, weather_station:WeatherStation):

        super().__init__(weather_station)  
        # cast api config to correct type for static type checking
        self.api_config: RainwiseAPIConfig = self.api_config


    def _get_readings(self, start_datetime:datetime, end_datetime:datetime, 
                      interval:int = 5) -> list[Response]:
        """
        Args: 
            start time start of time interval in UTC (station requires local time and it's converted here)
            end time: UTC data time object
            interval = the number of minutes per reading per docs.  Readings are taken every 15 minutes. 

        Returns:
            api response in a list with metadata (uses a list for compatibility with other station types)
        """

        # note start/end times in station timezone
        response = get( url='http://api.rainwise.net/main/v1.5/registered/get-historical.php',
                        params={'username': self.api_config.username,
                                'sid': self.api_config.sid,
                                'pid': self.api_config.pid,
                                'mac': self.api_config.mac,
                                'format': self.api_config.ret_form,
                                'interval': interval,
                                'sdate': self.dt_local_from_utc( start_datetime ), 
                                'edate': self.dt_local_from_utc( end_datetime )
                                }
                        )

        return [response]


    def _data_present_in_response(self, response_data:dict)->bool:
        """check for presence of data in response

        Args:
            response_data (dict): data loaded from response JSON

        Returns:
            bool: True if data is present in any of the records in the response, else False
        """  

        if 'station_id' not in response_data.keys():
            return False
     
        for key in response_data['times']:
            # if we see any non-empty data at all here, return true
            if response_data['temp'][key] or response_data['precip'][key] or response_data['hum'][key]:
                return True
            
        return False
    
    def _transform(self, response_data):
        """
        Transforms data into a standardized format and returns it as a WeatherStationReadings object.
        data param if left to default tries for self.response_data processing
        """

        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        # Return an empty list if there is no data contained in the response, this covers error 429
        if 'station_id' not in response_data.keys():
            return []

        readings = []        
        for key in response_data['times']:
            reading = {
                    'data_datetime' : self.dt_utc_from_str(response_data['times'][key]),
                    'atemp': round((float(response_data['temp'][key]) - 32) * 5/9, 2),
                    'pcpn' : round(float(response_data['precip'][key]) * 25.4, 2),
                    'relh' : round(float(response_data['hum'][key]), 2)
                    }
            
            readings.append(reading)
            
        return readings

    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass

