# ONSET ###################

import json, logging
from requests import get, post  # Session, Request
from datetime import datetime, timezone

from pydantic import Field

from . import STATION_TYPE
from oldstations.models import WeatherStationConfig
from oldstations.weather_station import WeatherStation

### Onset Notes

# response.content  format
# {
    # "max_results": true,
    # "message": "",
    # "observation_list": []
# }
    
# message example: "message":"OK: Found: 0 results."
# "message":"OK: Found: 21 results."

class OnsetConfig(WeatherStationConfig):
    station_type : STATION_TYPE  = 'ONSET'
    sn : str  = Field(description="The serial number of the device")
    client_id : str = Field(description="client specific value provided by Onset")
    client_secret : str = Field(description="client specific value provided by Onset")
    ret_form : str = Field(description="The format data should be returned in. Currently only JSON is supported.")
    user_id : str = Field(description="alphanumeric ID of the user account This can be pulled from the HOBOlink URL: www.hobolink.com/users/<user_id>")
    sensor_sn : dict[str,str] = Field(description="a dict of sensor alphanumeric serial numbers keyed on sensor type, e.g. {'atemp':'21079936-1'}") 

class OnsetStation(WeatherStation):
    StationConfigClass = OnsetConfig
    station_type = 'ONSET'

    
    # time between readings in minutes for this station type
    interval_min = 5

    """ config is OnsetConfig type """
    @classmethod
    def init_from_dict(cls, config:dict):
        """ accept a dictionary to create this class, rather than the Type class"""

        # this will raise error if config dictionary is not correct
        station_config = OnsetConfig.model_validate(config)
        return(cls(station_config))
        
    def __init__(self,config: OnsetConfig):
        """ create class from config Type"""
        self.access_token = None
        super().__init__(config)

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
        # debug logging - enabling will spill secrets in the log! 
        # logging.debug('client_id: \"{}\"'.format(self.config.client_id))
        # logging.debug('client_secret: \"{}\"'.format(self.client_secret))

        response = post(url='https://webservice.hobolink.com/ws/auth/token',
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded'},
                            data={'grant_type': 'client_credentials',
                                'client_id': self.config.client_id,
                                'client_secret': self.config.client_secret
                                }
                            )
        
        if response.status_code != 200:
            raise Exception(
                'Get Auth request failed with \'{}\' status code and \'{}\' message.'.format(response.status_code,
                                                                                    response.text))
        response = response.json()
        # store this in the object
        self.access_token = response['access_token']
        return self.access_token    

    def _get_readings(self,start_datetime:datetime,end_datetime:datetime):
        """ use Onset API to pull data from this station for times between start and end.  Called by the parent 
        class method get_readings().   
        
        parameters:
            start_datetime: datetime object in UTC timezone.  
            end_datetime: datetime object in UTC timezone.  
        """
    
        access_token = self._get_auth() 
            
        start_datetime_str = self._format_time(start_datetime)
        end_datetime_str = self._format_time(end_datetime)

        response = get( url=f"https://webservice.hobolink.com/ws/data/file/{self.config.ret_form}/user/{self.config.user_id}",
                        headers={'Authorization': "Bearer " + access_token},
                        params={
                            'loggers': self.config.sn,
                            'start_date_time': start_datetime_str,
                            'end_date_time': end_datetime_str
                            }
                        )

        return(response)
   
    def _transform(self, response_data):
        """transform of response.text to list of dict
        only handle response.text (sensor values) and nothing else
        """
        # if we can't decide to load JSON or not
        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        if 'observation_list' not in response_data.keys():
            return None
        
        readings = {}
        sensor_sns = self.config.sensor_sn
        atemp_key = sensor_sns['atemp']
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
            if reading["sensor_sn"] == atemp_key:
                readings[ts]["atemp"] = round(float(reading['si_value']), 2)
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
