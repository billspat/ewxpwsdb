"""
Subclass of WeatherAPI for the Davis type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.

The list of variables available from Davis are (not in sensor order): 
 - abs_press
 - air_density
 - arch_int
 - bar_alt
 - bar_trend_3_hr
 - bar
 - deg_days_cool
 - deg_days_heat
 - dew_point_out
 - emc
 - et
 - heat_index_out
 - hum_out
 - moist_soil_last
 - night_cloud_cover
 - pressure_last
 - rain_rate_hi_clicks
 - rain_rate_hi_in
 - rain_rate_hi_mm
 - rainfall_clicks
 - rainfall_in
 - rainfall_mm
 - solar_energy
 - solar_rad_avg
 - solar_rad_hi
 - temp_last
 - temp_out_hi
 - temp_out_lo
 - temp_out
 - thsw_index
 - thw_index
 - uv_dose
 - uv_index_avg
 - uv_index_hi
 - wet_bulb
 - wetness_hi_at
 - wetness_hi
 - wetness_last
 - wetness_lo_at
 - wetness_lo
 - wetness_secs
 - wind_chill
 - wind_dir_of_hi
 - wind_dir_of_prevail
 - wind_num_samples
 - wind_run
 - wind_speed_avg
 - wind_speed_hi


"""

import hashlib, hmac
import json
from requests import Session, Request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging

# from pydantic import Field
from . import STATION_TYPE
from .weather_api import WeatherAPI, Response, WeatherAPIConfig

# only used for type checking
from ewxpwsdb.db.models import WeatherStation

class DavisAPIConfig(WeatherAPIConfig):
        _station_type   : STATION_TYPE = 'DAVIS'
        sn             : str #  The serial number of the device.
        apikey         : str # The user's API access key. 
        apisec         : str # API security that is used to compute the hash.


class DavisAPI(WeatherAPI):
    """Station class for Davis type stations"""
    APIConfigClass: type[DavisAPIConfig] = DavisAPIConfig
    _station_type = 'DAVIS'
    _sampling_interval = interval_min = 15
    supported_variables = ['atmp', 'dwpt', 'lws', 'pcpn', 'relh', 'srad', 'smst', 'stmp']

    
    def __init__(self, weather_station:WeatherStation):
        self.apisig  = ""
        super().__init__(weather_station)
        # cast api config to correct type for static type checking
        self.api_config: DavisAPIConfig = self.api_config
 
        

    
    def get_intervals(self, start_datetime:datetime, end_datetime:datetime):
        """
        Public for viewing of what potential time intervals would look like
        Pass in start_datetime and end_datetime, if they're above 24hr apart,
        get nice splits that Davis can handle well in an array of tuples.
        """
        secondsdiff = (end_datetime - start_datetime).total_seconds()
        curr_start_date = start_datetime
        splits = []

        # 86400 seconds per interval
        while secondsdiff > 0:
            if secondsdiff > 86400:
                splits.append((curr_start_date, curr_start_date + timedelta(seconds=86400)))
                curr_start_date += timedelta(seconds=86400)
                secondsdiff -= 86400
            elif secondsdiff < 300:
                # Makes sure there aren't any intervals too small for Davis which result in errors.
                break
            else:
                splits.append((curr_start_date, curr_start_date + timedelta(seconds=secondsdiff)))
                secondsdiff -= secondsdiff
        return splits
    
    def _get_readings(self,start_datetime:datetime, end_datetime:datetime)->list[Response]:
        """ 
        Builds, sends, and stores raw response from Davis API
        The Davis stations will only collect data for at most 24 hrs. 
        If a multi-day request is made, would have to return a list of responses for each daily request
        So this _always_ returns a list of responses
        """
        tsplits = self.get_intervals(start_datetime=start_datetime, end_datetime=end_datetime)
        
        response_list = []
        for tsplit in tsplits:
            start_datetime = tsplit[0]
            end_datetime = tsplit[1]
            now = self.dt_local_from_utc(datetime.now(timezone.utc))
            now_timestamp_integer = int(now.timestamp())

            start_timestamp=int(start_datetime.timestamp())
            end_timestamp=int(end_datetime.timestamp())


            apisig = self._compute_signature(timestamp_integer=now_timestamp_integer, start_timestamp=start_timestamp, end_timestamp=end_timestamp)
            self.current_api_request = Request('GET',
                                url='https://api.weatherlink.com/v2/historic/' + self.api_config.sn,
                                params={'api-key': self.api_config.apikey,
                                        't': now_timestamp_integer,
                                        'start-timestamp': start_timestamp,
                                        'end-timestamp': end_timestamp,
                                        'api-signature': apisig}).prepare()
            
            response = Session().send(self.current_api_request)
            response_list.append(response)

        return response_list

    def _compute_signature(self, timestamp_integer:int, start_timestamp:int, end_timestamp:int) -> str:
        """
        This method computes the API signature used to call the Davis API historic endpoint.
        NOTE: datetimes should be in unix timestamp format already
        More info on this process can be found at https://weatherlink.github.io/v2-api/api-signature-calculator
        """

        msg = "api-key{}end-timestamp{}start-timestamp{}station-id{}t{}".format(self.api_config.apikey,
                                                                                end_timestamp,
                                                                                start_timestamp,
                                                                                self.api_config.sn,
                                                                                timestamp_integer)
        
        self.apisig = hmac.new(
            self.api_config.apisec.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256).hexdigest()
        
        return self.apisig

    def _data_present_in_response(self, response_data:dict)->bool:
        """check for presence of data in response

        Args:
            response_data (dict): data loaded from response JSON

        Returns:
            bool: True if data is present in any of the records in the response, else False
        """

        if 'sensors' not in response_data:
            return False
        
        for lsid in response_data['sensors']:
            if 'data' not in lsid.keys():
                 return False
            
            for record in lsid['data']:    
                if 'temp_out' in record.keys():
                        # if any data in any record, true
                        if  record['ts'] or record['rainfall_mm'] or record['hum_out']:
                            return True
        
        return False
        
    def _transform(self, response_data)->list:
        """
        Transforms data into a standardized format and returns it as a WeatherStationReadings object.
        data param if left to default tries for self.response_data processing

        Based on sample from test station, the sensor IDs (which groups the readings) are as follows:

        weather array (air temp, etc): 2
        soil probe: 205
        leaf wetness: 104
        station health: 501
        network connection: 502
        atmos pressure: 3

        """
        # convert to JSON if it isn't already 
        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        if 'sensors' not in response_data.keys():
            ## no data
            return []


        readings_by_datetime = {}

        for sensor in response_data['sensors']:
            if sensor['sensor_type'] == 2:  # weather array
                for record in sensor['data']:
                    record_datetime = self.dt_utc_from_ts(record['ts'])
                    if record_datetime not in readings_by_datetime:
                        readings_by_datetime[record_datetime] = {'data_datetime': record_datetime}

                    ## TODO confirm transforms esp for hum_out solar rad
                    sensor2_data = {                        
                        'atmp': round(self.f_to_c(record['temp_out']),2),
                        'dwpt': round(self.f_to_c(record['dew_point_out']),2),
                        'pcpn': record['rainfall_mm'],
                        'relh': record['hum_out'],
                        'srad': record['solar_rad_avg']
                        }

                    readings_by_datetime[record_datetime].update(sensor2_data)

            elif sensor['sensor_type'] == 205:  # soil
                for record in sensor['data']:
                    record_datetime = self.dt_utc_from_ts(record['ts'])
                    if record_datetime not in readings_by_datetime:
                        readings_by_datetime[record_datetime] = {'data_datetime': record_datetime}
                    
                    soil_sensor_data = {
                        'smst' : record['moist_soil_last'],
                        'stmp' : round(self.f_to_c(record['temp_last']),2)
                    }
                    readings_by_datetime[record_datetime].update(soil_sensor_data)

            elif sensor['sensor_type'] == 104:  # leaf wetness
                for record in sensor['data']:
                    record_datetime = self.dt_utc_from_ts(record['ts'])
                    if record_datetime not in readings_by_datetime:
                        readings_by_datetime[record_datetime] = {'data_datetime': record_datetime}
                    # TODO confirm leaf wetness transform
                    lws:int =  1 if record['wetness_hi'] >= 0.5 else 0
                    wetness_sensor_data = {'lws':lws  }
                    
                    readings_by_datetime[record_datetime].update(wetness_sensor_data)

        # convert from dictionary of dictionaries back to a list of dictionaries as expected
        readings:list[dict] = list(readings_by_datetime.values())

        return readings
    

    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass


