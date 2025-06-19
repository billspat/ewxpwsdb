"""
Subclass of WeatherAPI for the Onset type weather stations with methods for 
requesting data (_get_readings) and transforming data (_transform) called by 
methods in the parent class.
"""

import json
from requests import post, Session, Request, Response
from datetime import datetime, timezone
import logging

from . import STATION_TYPE
from ewxpwsdb.weather_apis.weather_api import WeatherAPIConfig, WeatherAPI
from ewxpwsdb.db.models import WeatherStation

# Initialize the logger
logger = logging.getLogger(__name__)

## CONSTANT
# LOCOMOS stations output leaf wetness in average millivolts.  
# The UBIDOTS/api calculates an hourly value of count/wet per hour, using the threshold constant below
# API readings only ouptut mVolts so we need to convert to wet yes/no coded as 1/0 here so it can be averaged per hour.  
# two readings per hour
# (0,0), (1,0) or (0,1) or (1,1).   sum(readings)/2.0 = percent wet (0, .5 or 1.0)
LOCOMOS_LWS_THRESHOLD = 460

class LocomosAPIConfig(WeatherAPIConfig):
        _station_type   : STATION_TYPE = 'LOCOMOS'
        token          : str # Device token
        id             : str # ID field on device webpage


class LocomosAPI(WeatherAPI):
    """Sub class for  MSU BAE LOCOMOS weather stations used for TOMCAST model"""

    APIConfigClass: type[LocomosAPIConfig] = LocomosAPIConfig
    _station_type: STATION_TYPE = 'LOCOMOS'
    _sampling_interval = interval_min = 30
    # this list of supported vars is for 2024 test station only

    supported_variables = ['atmp', 'lws', 'relh']
    standard_time_interval_minutes = 60
    
    
    # object variable may be overridden per station if necessary #TODO create a property

    # LOCOMOS uses variable names to identify sensors, and this dict maps to PWS database names
    # var names must be assigned manual when the station is added to Ubidots, so may change 
    # 2023 variables - saved for reference
    # ewx_var_mapping = {
    #     # LOCOMOS: EWX
    #     'rh':'relh',
    #     'temp':'atmp',
    #     'prep':'pcpn',
    #     'lws1':'lws',   # this is not percent wet, but wet y/n -> 0/1
    # }

    # 2024 variables
    # ewx_var_mapping = {
    #     # LOCOMOS: EWX
    #     'humid':'relh',
    #     'temp':'atmp',
    #     'precip':'pcpn',
    #     'lws1':'lws',  
    # }
        
    # 2025 variables
    ewx_var_mapping = {
        'humidity':'relh',
        'temperature':'atmp',
        'precip':'pcpn',
        'lws':'lws', 
    }


    def __init__(self, weather_station:WeatherStation, lws_threshold:int = LOCOMOS_LWS_THRESHOLD):    

        self.lws_threshold = lws_threshold
        self.variables: dict[str,str]|None = None
        super().__init__(weather_station)
        
        # re-cast api config to correct type for static type checking
        self.api_config: LocomosAPIConfig = self.api_config
        logger.debug("Initialized LocomosAPI for station %s", weather_station.station_code)


    def _get_variables(self) -> dict[str,str]:
        """load ubidots variable list
        
        gets the list of variables and their IDS for this Ubidots device via the Ubidots API. 
        Ubidots is flexible and allows for multiple sensors or 'variables' each with it's own label and ID. 

        when the LOCOMOS station is set-up, sensors are defined with standardized labels.  
        Those labels are used to transform the data to EWX standard naming

        If this object already has a non-empty variable list, does not make the request a second time

        returns : dictionary keyed on serial id and values are common names (label)
        """
        if self.variables is None or len(self.variables) == 0:
            # object member is empty, load and save list of variables from API
            variables_request = Request(method='GET',
                    url=f"https://industrial.api.ubidots.com/api/v2.0/devices/{self.api_config.id}/variables/", 
                    headers={'X-Auth-Token': self.api_config.token}, 
                    params={'page_size':'ALL'}).prepare()
            
            response = Session().send(variables_request)

            if response.status_code != 200:
                logger.error("Failed to get variable list from LOCOMOS API")
                return {}

            variable_response = json.loads(response.content)
            if 'results' not in variable_response.keys():
                logger.error("LOCOMOS API did not return variable content as expected (no result key)")
                return {}

            variables = {}
            for result in variable_response['results']:
                variables[result['id']] = result['label']
            logger.debug("Loaded variables: %s", variables)
            self.variables = variables
        
        return(self.variables)
    
        
    def _get_readings(self, start_datetime:datetime, end_datetime:datetime)->list[Response]:
        """
        Pull "data raw series" from UBIDOTS api.  Note they use POST rather than get.  
        See Ubidots doc : https://docs.ubidots.com/v1.6/reference/data-raw-series
        Params are start time, end time in UTC
        Returns api response in a list with metadata
        Example Curl command 
        # curl -X POST 'https://industrial.api.ubidots.com/api/v1.6/data/raw/series' \
        #     -H 'Content-Type: application/json' \
        #     -H "X-Auth-Token: $TOKEN" \
        #     -d '{"variables": ["6410e8564a53ce000ec46e46"], "columns": ["variable.name","value.value", "timestamp"], "join_dataframes": false, "start": 1679202000000, "end":1679203800000}'
        """
        
        start_milliseconds=int(start_datetime.timestamp() * 1000)
        end_milliseconds=int(end_datetime.timestamp() * 1000)
  
        request_headers = {
            'Content-Type': 'application/json',
            'X-Auth-Token': self.api_config.token,
        }

        variables = self._get_variables()
        logger.debug(f"locomos variables: {variables}")
        if isinstance(variables, dict) and len(variables) > 0: 
            variable_ids = list(variables.keys())
        else:
            logger.error("LOCOMOS station %s could not get variable list", self.id)
            return []

        response_columns = [
            'timestamp', 
            'device.name', 
            'device.label', 
            'variable.id', 
            'variable.name', 
            'value.value'
            ]
        
        request_params = {
                'variables': variable_ids,
                'columns': response_columns,
                'join_dataframes': False,
                'start': start_milliseconds,
                'end': end_milliseconds,
        }            
        
        try:
            response = post(url='https://industrial.api.ubidots.com/api/v1.6/data/raw/series',
                            headers=request_headers,
                            json=request_params)
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

        # must have a results key
        if not('results' in response_data):
             return False
        
        # results array must have more than one element
        if len(response_data['results']) == 0:
            return False
        
        # the first results element should be non-zero len (it's an array of arrays)
        if len(response_data['results'][0]) > 0:
            return True
        
        return False
    

    def _lws_convert(self, lws_value:float)->float:
        """ convert leaf wetness value to EWX standard wet/not wet.
        params lws_value : mVolt value as storedd in the API
        output : integer 0 or 1
        """
        # this is here mostly to be explicit and document where this conversion happens
        return 1.0 if lws_value > self.lws_threshold else 0.0


    def _transform(self, response_data)->list[dict]:
        """transform LOCOMOS api response to ewx variables, which uses the UBIDOTs api. 

        Ubidots returns a variable ID which maps to a variable name in the Ubidots portal.    The response data has a differenet 
        
        The Ubidots output has results key and columns key, and columns indicates what the column contains for each row. 
        This version has hard-coded column numbers embedded in it as the columns haven't changed yet.   Ubidots has a more flexible API than 
        is needed for this application

        Args:
            response_data (_type_): dictionary from API response 

        Returns:
            list[dict]: list of readings records for inserting to database
        """

        # this is the order of the columns from the 'results' array from the API
        colnumber = {
            "timestamp":0,
            "device.name":1,
            "device.label":2,
            "variable.id":3,
            "variable.name":4,
            "value.value":5
        }        

        # the variables and IDs we are interested in
        variables:dict[str,str] = self._get_variables()
        readings:dict[int, dict[str,any]] = {}

        if isinstance(response_data,str):
            response_data = json.loads(response_data)

        # records are grouped by time, with one record per sensor
        for timestamped_records in response_data['results']: 
            for sensor_record in timestamped_records:
                timestamp = sensor_record[colnumber['timestamp']]
                if timestamp not in readings.keys():
                    data_datetime = datetime.fromtimestamp(timestamp/ 1000).astimezone(timezone.utc)
                    readings[timestamp] =  {'data_datetime': data_datetime}

                # convert this record's variable from an id to it's name 
                this_variable_id = sensor_record[colnumber["variable.id"]]
                this_variable_name = variables[this_variable_id]

                # we are not interested in all the values in the data, only those in our list of self.variables
                if this_variable_name in self.ewx_var_mapping.keys():
                    ewx_variable_name = self.ewx_var_mapping[this_variable_name]
                    if ewx_variable_name == 'lws':
                        readings[timestamp][ewx_variable_name] = self._lws_convert(sensor_record[colnumber["value.value"]])
                    else:
                        readings[timestamp][ewx_variable_name] = sensor_record[colnumber["value.value"]]

        reading_list:list[dict] = list(readings.values())

        return(reading_list)


    # this will be removed after extensive testing of simplified transform above
    # def _transform_old_version(self, response_data)->list:
    #     """ station specific transform
    #     params response_data: the value of 'text' from the response object e.g. JSON

    #     PREVIOUS VERSION THAT ACCOMMODATED FOR UNKNOW COLUMN ORDER IN OUTPUT
        
    #     returns: list of readings keyed on date/teim"""
    #     def rm_dev_id(colname, delim = "."):
    #         if(delim in colname):
    #             colname = delim.join(colname.split('.')[1:])
    #         return(colname) 

    #     import re
    #     def variable_id_from_columns(columns):
    #         """ some, but not all, column names are prepended with a variable id, 
    #         like this: 649ded97c607eb000ea8777d.value.value
    #         this finds the first matching colname and extracts the variable id"""
    #         pattern_col_with_id =  r"^[0-9a-z]+\.[a-z\.]+$"
    #         for colname in columns:
    #             if re.match(pattern_col_with_id, colname):
    #                 variable_id_for_this_result =  colname.split('.')[0]
    #                 return(variable_id_for_this_result)

    #     if isinstance(response_data,str):
    #         response_data = json.loads(response_data)

    #     results = response_data['results']
    #     columns = response_data['columns']

    #     var_by_id = dict( [(var_id,self.ewx_var_mapping[var_name]) for var_id,var_name in self._get_variables().items() if var_name in self.ewx_var_mapping.keys() ] ) 
        
    #     # readings dict, keyed on timestamp
    #     readings:dict[dict] = {}

    #     # print(var_dict)
    #     for j in range(1, len(columns)):
    #         # is there data? 
    #         if len(results[j]) == 0:
    #             continue

    #         var_id = variable_id_from_columns(columns[j])
    #         # is this var one we want? 
    #         if var_id not in var_by_id.keys():
    #             continue
    #         else:
    #             var_name = var_by_id[var_id]
    #             print(var_name)
                
    #         # results are a list inside list element, one item for each reading/time interval
    #         # and just one sensor per result
    #         for result in results[j]:
    #             # result is list of one reading (timestamp) for one variable, but does not have varnames 
    #             # add the var/column names to make it easy
    #             simple_var_names = [ rm_dev_id(c) for c in columns[j]]
    #             result_dict = dict(zip(simple_var_names,result ))
                
    #             if result_dict['variable.id'] != var_id:
    #                 raise ValueError(f"named variable.id not the same as var_id: {var_id} != {result_dict['variable.id']}")
                
    #             # add this sensor result / value to the readings list
    #             # to accumlate the sensors from different readings into single diction, 
    #             # key it on timestamp, and build up the dict as sensor values come in. 
    #             # first insert a new readings dict if that timestamp is not yet present, start with data_datetime
    #             if result_dict['timestamp'] not in readings.keys():
    #                 data_datetime = datetime.fromtimestamp(result_dict['timestamp']/ 1000).astimezone(timezone.utc)
    #                 readings[result_dict['timestamp']] =  {'data_datetime': data_datetime}
                
    #             # add sensor reading to reading dict for this timestamp
    #             if var_name == "lws":
    #                 readings[result_dict['timestamp']][var_name] = self._lws_convert(result_dict['value.value'])
    #             else:
    #                 readings[result_dict['timestamp']][var_name] = result_dict['value.value']
                
    #             # end result _should_ be readings[per_timestamp] = {'temp':999, 'rh':999, 'lws1':999}

    #     return(list(readings.values()))    


    def _handle_error(self):
        """ place holder to remind that we need to add err handling to each class"""
        pass

