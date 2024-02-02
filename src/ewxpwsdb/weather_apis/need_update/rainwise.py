# RAINWISE ###################

import json
from requests import get
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  


from oldstations import STATION_TYPE
from oldstations.models import WeatherStationConfig
from oldstations.weather_station import WeatherStation

class RainwiseConfig(WeatherStationConfig):
        station_type   : STATION_TYPE = 'RAINWISE'
        username       : str = None
        sid            : str # Site id, assigned by Rainwise.
        pid            : str # Password id, assigned by Rainwise.
        mac            : str # MAC of the weather station. Must be in the group assigned to username.
        ret_form       : str # Values xml or json; returns the data as JSON or XML.

class RainwiseStation(WeatherStation):
    """ WeatherStation subclass for Rainwise API http://api.rainwise.net """
    StationConfigClass = RainwiseConfig
    station_type = 'RAINWISE'

    # time between readings in minutes for this station type
    interval_min = 15

    @classmethod
    def init_from_dict(cls, config:dict):
        """ accept a dictionary to create this class, rather than the Type class"""

        # this will raise error if config dictionary is not correct
        station_config = RainwiseConfig.model_validate(config)
        return(cls(station_config))

    def __init__(self,config: RainwiseConfig):
        """ create class from config Type"""
        super().__init__(config)

    def _check_config(self):
        # TODO implement 
        return(True)
    
    def _get_readings(self, start_datetime:datetime, end_datetime:datetime, 
                      interval:int = 5):
        """
        Params 
            start time start of time interval in UTC (station requires local time and it's converted here)
            end time: UTC data time object
            interval = the number of minutes per reading per docs.  Readings are taken every 15 minutes. 

            Returns api response in a list with metadata
        """

        # note start/end times in station timezone
        response = get( url='http://api.rainwise.net/main/v1.5/registered/get-historical.php',
                        params={'username': self.config.username,
                                'sid': self.config.sid,
                                'pid': self.config.pid,
                                'mac': self.config.mac,
                                'format': self.config.ret_form,
                                'interval': interval,
                                'sdate': start_datetime.astimezone(tz=self.station_tz),
                                'edate': end_datetime.astimezone(tz=self.station_tz)
                                }
                        )

        return response


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

