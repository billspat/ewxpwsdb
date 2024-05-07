"""
Subclass of WeatherAPI for the Onset type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.
"""

import json
from requests import get, post, Response 
from datetime import datetime, timezone

from pydantic import Field


from . import STATION_TYPE
from ewxpwsdb.weather_apis.weather_api import WeatherAPIConfig, WeatherAPI
from ewxpwsdb.db.models import WeatherStation


### Onset Notes

# response.content  format
# {
    # "max_results": true,
    # "message": "",
    # "observation_list": []
# }
    
# message example: "message":"OK: Found: 0 results."
# "message":"OK: Found: 21 results."

class OnsetAPIConfig(WeatherAPIConfig):
    _station_type : STATION_TYPE  = 'ONSET'
    sn : str  = Field(description="The serial number of the device")
    client_id : str = Field(description="client specific value provided by Onset")
    client_secret : str = Field(description="client specific value provided by Onset")
    ret_form : str = Field(description="The format data should be returned in. Currently only JSON is supported.")
    user_id : str = Field(description="alphanumeric ID of the user account This can be pulled from the HOBOlink URL: www.hobolink.com/users/<user_id>")
    sensor_sn : dict[str,str] = Field(description="a dict of sensor alphanumeric serial numbers keyed on sensor type, e.g. {'atmp':'21079936-1'}") 

class OnsetAPI(WeatherAPI):
    
    
    APIConfigClass: type[OnsetAPIConfig] = OnsetAPIConfig
    _station_type: STATION_TYPE = 'ONSET'
    _sampling_interval = interval_min = 5
    _lws_threshold = 50
    supported_variables = ['atmp', 'dwpt', 'lws', 'pcpn', 'relh', 'wdir', 'wspd']

    def __init__(self, weather_station:WeatherStation):    
        """ create class from config Type"""
        self._access_token = None
        super().__init__(weather_station)
        # cast api config to correct type for static type checking
        self.api_config: OnsetAPIConfig = self.api_config


    def _check_config(self):
        # TODO implement 
        return(True)
    
    def _get_auth(self):
        """
        uses the api to generate an access token required by Onset API
        adds 'access_token' field to the config dictionary  ( will that affect the type?)

        note that this must be done immediately before the request, as it can 
        otherwise cause a race condition with
        Raises Exception If the return code is not 200.
        """

        # pull from cache/store if present
        if self._access_token:
            return self._access_token
        
        response = post(url='https://webservice.hobolink.com/ws/auth/token',
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded'},
                            data={'grant_type': 'client_credentials',
                                'client_id': self.api_config.client_id,
                                'client_secret': self.api_config.client_secret
                                }
                            )
        
        if response.status_code != 200:
            raise Exception(
                'Get Auth request failed with \'{}\' status code and \'{}\' message.'.format(response.status_code,
                                                                                    response.text))
        response = response.json()
        # store this in the object
        self._access_token = response['access_token']
        return self._access_token    

    def _get_readings(self,start_datetime:datetime,end_datetime:datetime) ->list[Response] :
        """ use Onset API to pull data from this station for times between start and end.  Called by the parent 
        class method get_readings().   
        
        parameters:
            start_datetime: datetime object in UTC timezone.  
            end_datetime: datetime object in UTC timezone.  
        """
    

        access_token = self._get_auth() 
            
        start_datetime_str = self._format_time(start_datetime)
        end_datetime_str = self._format_time(end_datetime)

        response = get( url=f"https://webservice.hobolink.com/ws/data/file/{self.api_config.ret_form}/user/{self.api_config.user_id}",
                        headers={'Authorization': "Bearer " + access_token},
                        params={
                            'loggers': self.api_config.sn,
                            'start_date_time': start_datetime_str,
                            'end_date_time': end_datetime_str
                            }
                        )

        return([response])
    
    def _data_present_in_response(self, response_data:dict)->bool:
        """check for presence of data in response

        Args:
            response_data (dict): data loaded from response JSON

        Returns:
            bool: True if data is present in any of the records in the response, else False
        """

        if 'observation_list' not in response_data.keys():
            return False
        
        for reading in response_data["observation_list"]:
            # any data found anywhere, return True
            if 'si_value' in reading.keys() and reading['si_value']:
                return True
            
        return False

    def _transform(self, response_data):
        """
        Tranform data from Onset API to EWX database values. 

        Readings are in a flatnames space under 'observation list, on reading per sensor per timestamp. 
        
        Weather Variables in "sensor_measurement_type" field are named as follows:

        - Battery
        - Dew Point
        - Gust Speed
        - Rain
        - RH
        - Solar Radiation
        - Temperature
        - Wetness
        - Wind Direction
        - Wind Speed

        """

        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        if 'observation_list' not in response_data.keys():
            return None
        
        readings = {}

        for sensor_reading in response_data["observation_list"]:

            ts = sensor_reading["timestamp"]

            # Remove Z's from ends of timestamps, which occur in Onset data
            ts = ts.replace('Z', '')
            
            # Create new entry if time hasn't been encountered yet
            if ts not in readings.keys():
                readings[ts] = {"data_datetime" : self.dt_utc_from_str(ts) }
            
            # readings[ts]["data_datetime"] =  self# datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').astimezone(timezone.utc)
            
            # Set entries to contain proper data
            match sensor_reading["sensor_measurement_type"]:
                case 'Dew Point':
                    readings[ts]['dwpt'] = sensor_reading["si_value"]
                case 'Rain':
                    readings[ts]['pcpn'] = sensor_reading["si_value"]
                case 'RH':
                    readings[ts]['relh'] = sensor_reading["si_value"]
                case 'Solar Radiation':
                    readings[ts]['srad'] = sensor_reading["si_value"]
                case 'Temperature':
                    readings[ts]['atmp'] = sensor_reading["si_value"]
                case 'Wetness':
                    readings[ts]['lws']  = self.wetness_transform(sensor_reading["si_value"])  # %
                case 'Wind Direction':
                    readings[ts]['wdir'] = sensor_reading["si_value"]
                case 'Wind Speed':
                    readings[ts]['wspd'] = sensor_reading["si_value"]  # meters/sec
                    
        return list(readings.values())
        

    def wetness_transform(self, w):
        return 1 if w >= self._lws_threshold else 0
    

    def _transform_by_sensor_serial(self, response_data):
        """transform of response.text to list of dict
        Use the sensor serial numbers as retrieved by former method. 

       The latest api includes a key "sensor_measurement_type" in the response data so this is obsolete.  
       See _tranform() method above
        """
        

        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        if 'observation_list' not in response_data.keys():
            return None
        
        readings = {}
        sensor_sns = self.api_config.sensor_sn
        atmp_key = sensor_sns['atmp']
        pcpn_key = sensor_sns['pcpn']
        relh_key = sensor_sns['relh']
        # station_sn = response_data["observation_list"][0]["logger_sn"]

        # Gathering each reading into an easily formattable manner
        for reading in response_data["observation_list"]:
            # Remove Z's from ends of timestamps
            ts = reading["timestamp"]
            if reading["timestamp"][-1].lower() == 'z':
                    ts = ts[:-1]
            # Create new entry if time hasn't been encountered yet
            if ts not in readings.keys():
                readings[ts] = {}
            
            readings[ts]["data_datetime"] =  datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').astimezone(timezone.utc)
            
            # Set entries to contain proper data
            if reading["sensor_sn"] == atmp_key:
                readings[ts]["atmp"] = round(float(reading['si_value']), 2)
            elif reading["sensor_sn"] == pcpn_key:
                readings[ts]["pcpn"] = round(float(reading['si_value']), 2)
            elif reading["sensor_sn"] == relh_key:
                readings[ts]["relh"] = round(float(reading['si_value']), 2)

        # convert to list
        readings = [r for r in readings.values()]

        return readings
        

    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass
