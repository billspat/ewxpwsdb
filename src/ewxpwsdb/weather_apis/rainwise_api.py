"""
Subclass of WeatherAPI for the Rainwise type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.

The following variables are availabe from the Rainwise API: 

 - times local time
 - temp C if units=metric
 - temp_lo NOT USED always 0F or -18C
 - temp_hi NOT USED always 0F or -18C
 - itemp   NOT USED always 0F or -18C
 - itemp_lo  NOT USED always 0F or -18C
 - itemp_hi  NOT USED always 0F or -18C
 - hum percent
 - hum_lo NOT USED always 0
 - hum_hi NOT USED always 0
 - pressure
 - pressure_lo NOT USED always 0
 - pressure_hi NOT USED always 0
 - windchill
 - dewpoint
 - wind  assuming kph
 - wind_gust assuming kph
 - wind_dir
 - leaf_wetness = number of minutes wet cumulative for the day
 - heat_index
 - precip
 - solar_radiation
 - temperature_1  alternative temp sensor
 - temperature_1_lo NOT USED always 0F or -18C
 - temperature_1_hi NOT USED always 0F or -18C
 - soil_tension  
 - soil_temperature NOT USED always 0F or -18C


"""
#####  REQUIRES UPDATE TO WORK WITH CURRENT SYSTEM


import json
from requests import get, Response
from datetime import datetime
import logging

from . import STATION_TYPE
from ewxpwsdb.weather_apis.weather_api import WeatherAPIConfig, WeatherAPI
from ewxpwsdb.db.models import WeatherStation, APIResponse

# Initialize the logger
logger = logging.getLogger(__name__)

class RainwiseAPIConfig(WeatherAPIConfig):
        _station_type   : STATION_TYPE = 'RAINWISE'
        username       : str # user name, quoted integer
        sid            : str # Site id, assigned by Rainwise.
        pid            : str # Password id, assigned by Rainwise.
        mac            : str # MAC of the weather station. Must be in the group assigned to username.
        ret_form       : str # Values xml or json; returns the data as JSON or XML.


class RainwiseAPI(WeatherAPI):
    """ WeatherStation subclass for Rainwise API http://api.rainwise.net """

    APIConfigClass: type[RainwiseAPIConfig] = RainwiseAPIConfig
    _station_type: STATION_TYPE = 'RAINWISE'
    _sampling_interval = interval_min = 15
    _lws_threshold = 0.50 # percent minutes wet
    supported_variables = ['atmp', 'lws', 'pcpn', 'relh', 'srad', 'smst', 'wspd', 'wdir', 'wspd_max']
    standard_time_interval_minutes = 44 # this should get 3 readings
    
    # rainwise only, used for leaf wetness transform
    # previous_minutes_wet_cumulative = None


    def __init__(self, weather_station:WeatherStation):

        super().__init__(weather_station)  
        # cast api config to correct type for static type checking
        self.api_config: RainwiseAPIConfig = self.api_config
        logger.info("Initialized RainwiseAPI for station %s", weather_station.station_code)


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
        
        from datetime import timedelta
        start_local_time_early = self._format_time(self.dt_local_from_utc( start_datetime ) - timedelta(minutes=16) )
        end_local_time = self._format_time(self.dt_local_from_utc( end_datetime ))
        
        url = 'http://api.rainwise.net/main/v1.5/registered/get-historical.php'
        params: dict[str,int|str] = {
                                'username': self.api_config.username,
                                'sid': self.api_config.sid,
                                'pid': self.api_config.pid,
                                'mac': self.api_config.mac,
                                'format': self.api_config.ret_form,
                                'interval': interval,
                                'sdate': start_local_time_early,
                                'edate': end_local_time,
                                'units':'metric' 
                                }
        
        try:
            response = get(url= url, params=params)
            response.raise_for_status()
            logger.info("Successfully retrieved data for interval %s - %s", start_datetime, end_datetime)
        except Exception as e:
            logger.error("Failed to retrieve data for interval %s - %s: %s", start_datetime, end_datetime, e)
            return []

        # response should have 1 extra previous reading
        return [response]

    
    def _get_readings_current(self) -> Response:
        """ use the Rainwse public api to get 'current' data.  This has different output format than the historical data"""
        current_data_url = f"http://api.rainwise.net/main/v1.5/get-data.php?mac={self.api_config.mac}&format=json"
        response = get(url= current_data_url)
        return response
    

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
    
    
    def _lws_convert(self, lws_value:int, obs_datetime:datetime)->float:
        """handles rainwise leaf wetness which is stored as cumulative minutes wet for the day, resets at 00:00 """        
        
        # call it like it is
        minutes_wet_cumulative = int(lws_value)        
        
        if obs_datetime.hour == 0:
            # the minutes web so far today resets at 00:00    
            if minutes_wet_cumulative != 0:
                Warning("Rainwise Transform issue: at 0 hour the cumulative minutes wet was not 0 for time {t}".format(t = obs_datetime))
            minutes_wet_for_this_interval = 0            
            
        else: 
            if hasattr(self, 'previous_minutes_wet_cumulative'):
                minutes_wet_for_this_interval = minutes_wet_cumulative - self.previous_minutes_wet_cumulative

        percent_wet = minutes_wet_for_this_interval/self.interval_min
        # set the new cumulative value. save in the class
        
        self.previous_minutes_wet_cumulative = minutes_wet_cumulative 
        
        return 1 if  percent_wet >= self._lws_threshold else 0

   
    def _transform(self, response_data):
        """
        Transforms data into a standardized format and returns it as a WeatherStationReadings object.
        data param if left to default tries for self.response_data processing

        Values in JSON are quoted and are read as string, so need to convert using 'float()' 

        Assumes the parameter 'units' was sent as 'metric' (RainwiseAPI has option for 'english' or 'metric' )

        note that even though there are some variables with values in the API response, they are not actual measurements
        and are not converted here.  for example temp_hi and temp_lo are always 0F or -17.8C
        for historical data API endpoint in our tests

        Args:
            response_data = content of response, or 'text' attribute of a python Requests Response object
        
        Returns:
            list of dictionary: readings variables to be used to build a Readings object.  Does not include the metadata, only 
            the timestamp of the observation and transformed values available from this station
        
        """

        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        # Return an empty list if there is no data contained in the response, this covers error 429
        if 'station_id' not in response_data.keys():
            return []

        readings = []
        
        first_data_key = list(response_data['times'].keys())[0]
        # leaf wetness is cumulative, so need save initial value to get the delta
        self.previous_minutes_wet_cumulative = int(response_data['leaf_wetness'][first_data_key])
            
        # when rainwise "get"s data, it gets one extra previous time at the beginning to do this percent_wet calc
        all_but_first_key  = list(response_data['times'].keys())[1:]
        
        for key in all_but_first_key:  # response_data['times']:
            #TODO confirm  wspd, srad transforms for this station
            data_datetime = self.dt_utc_from_str(response_data['times'][key])
            reading = {
                    'data_datetime' : data_datetime,
                    'atmp' : float(response_data['temp'][key]),
                    #'atmp_min' : float(response_data['temp_lo'][key]),   # this is reported but always 0F
                    #'atmp_max' : float(response_data['temp_hi'][key]),   # this is reported but always 0F
                    'dwpt' : float(response_data['dewpoint'][key]),
                    'lws'  : self._lws_convert( int(response_data['leaf_wetness'][key]), data_datetime ),
                    'pcpn' : float(response_data['precip'][key]) * 25.4,
                    'relh' : float(response_data['hum'][key]),
                    'smst' : float(response_data['soil_tension'][key]),  # units are 'CB' = ?
                    # 'stmp' : round(self.f_to_c(float(response_data['soil_temperature'][key])), 2),  this is always 0F
                    'srad' : float(response_data['solar_radiation'][key]),
                    'wdir' : float(response_data['wind_dir'][key]),
                    'wspd' : self.kph_to_ms(float(response_data['wind'][key])),  
                    'wspd_max' : self.kph_to_ms(float(response_data['wind_gust'][key]))
                    
            }
            
            readings.append(reading)
        
        # return object to previous state
        delattr(self, "previous_minutes_wet_cumulative")
        
        logger.debug("Transformed readings: %s", readings)
        return readings

    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass

