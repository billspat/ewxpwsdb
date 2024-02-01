
import json
from requests import get
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

# from pydantic import Field
from . import STATION_TYPE
from .weather_api import WeatherAPI, WeatherAPIConfig


class SpectrumAPIConfig(WeatherAPIConfig):
        _station_type   : STATION_TYPE = 'SPECTRUM'
        sn             : str #  The station identifier. 
        apikey         : str #  The user's API access key.  

class SpectrumAPI(WeatherAPI):
    """Subclass of WeatherAPI with methods specific to specconnect.net for Spectrum weather stations"""

    APIConfigClass = SpectrumAPIConfig
    _station_type = 'SPECTRUM'
    _sampling_interval = interval_min = 5

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
    
    def _get_readings(self,start_datetime:datetime, end_datetime:datetime):
        """ request weather data from the specconnect API for a range of dates
        
        parameters:
            start_datetime: datetime object in UTC timezone.  
            end_datetime: datetime object in UTC timezone.  
        """
        start_datetime_str = self._format_time(start_datetime)
        end_datetime_str = self._format_time(end_datetime)
        
        response = get( url='https://api.specconnect.net:6703/api/Customer/GetDataInDateTimeRange',
                        params={'customerApiKey': self.api_config.apikey, 
                                'serialNumber': self.api_config.sn,
                                'startDate': start_datetime_str, 
                                'endDate': end_datetime_str}
                        )
        
        return(response)

    def _transform(self, response_data):
        """
        Transforms data into a standardized format and returns it as a WeatherStationReadings object.
        data param if left to default tries for self.response_data processing
        """
        
        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        if 'EquipmentRecords' not in response_data.keys():
            return []
        
        readings = []
        for record in response_data['EquipmentRecords']:
            reading = { 'data_datetime': self.dt_utc_from_str(record['TimeStamp']),
                        'atemp': round((record['SensorData'][1]["DecimalValue"] - 32) * 5 / 9, 2),
                        'pcpn' : round(record['SensorData'][0]["DecimalValue"] * 25.4, 2),
                        'relh' : round(record['SensorData'][2]["DecimalValue"], 2)
            }

            readings.append(reading)

        return readings

    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass

