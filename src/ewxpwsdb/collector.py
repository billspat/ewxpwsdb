"""weather data collection class"""

from datetime import datetime

from sqlalchemy import Engine
from sqlmodel import select
from ewxpwsdb.db.importdata import import_station_file, read_station_table
from ewxpwsdb.db.database import Session, init_db, engine, get_engine
from ewxpwsdb.db.models import WeatherStation, APIResponse
from ewxpwsdb.weather_apis import API_CLASS_TYPES


class Collector():
    """class to enable collecting data from station apis and store in a database.  
    This class connects the components of the system to be invoked by a workflow manager.    """

    def __init__(self, station_id:int, engine:Engine = engine,  *args, **kwargs):
        """create a collector object for pulling for an API specific to a station type.  
        This creates a database session open for the life of this object.   Use collector.close() when operations are complete.  

        Args:
            station_id (int): Database ID (primary key) of a weather station record
            engine (Engine, optional): Engine connection for existing EWX PWS database that data is read/written to.  Defaults to global engine from database.py. 
        """

        self._engine = engine
        self._session = Session(engine)
        self.station_id = station_id
                      
        self.station = self._session.get(WeatherStation, station_id)
        
        self.APIClass = API_CLASS_TYPES[self.station.station_type]
        self.weather_api = self.APIClass(self.station)


    @property
    def id(self):
        """convenience method, identify this collector by the station id, which is core element"""
        return self.station.id
    
    @property
    def station_type(self):
        """convenience method to get the type of station this is working with"""
        return self.station.station_type

    @property
    def station_code(self):
        """convenience method to get the human-readable station code/id for use in logging/debug"""
        return self.station.station_code

    #########################
    # primary methods

    def request_weather_data(self, start_datetime:datetime, end_datetime:datetime):
        """use API class to request data for a range of UTC timestamps.  
         Stores the data from the request/response internally and in the database
         
        Args:
            start_datetime (datetime): start of interval, timezone aware datetime in UTC
            end_datetime (datetime): end of interval, timezone aware datetime in UTC
             
        Returns:
            this object for method chaining
        """
        
        self.current_api_response_records = self.weather_api.get_readings(start_datetime = start_datetime,  end_datetime = end_datetime)

        # we have _new_ batch of response(s), so clear existing current readings in anticipation of new transform
        if self.current_api_response_records and self.current_readings:
            self.current_readings = []

        # store reponses in database
        for response in self.current_api_response_records:
            self._session.add(response)
            self._session.commit() # TODO determine if this commit affects any other pending transactions?  
        
        # TODO error handling to allow for rollback of these records

        # TODO check if returning self works; this is an experiment for method chaining
        return(self)


    def request_current_weather_data(self):
        """call request weather method with no dates, so API class gets most recent 
        complete 15 minute period.   Stores the data from the request/response internally and in the database"""

        self.request_weather_data(start_datetime = None, end_datetime=None)
        
        # TODO check if returning self works; this is an experiment for method chaining
        return(self)


    def transform_current_weather_data(self):
        """transform data in API response to database record format, and store in database"""

        #TODO error handling!
        self.current_readings = self.weather_api.transform(self.current_api_response_records)

        #TODO check for real data here, error handling.  IF readings are blank do we store blank readings?
        #TODO handling of duplicate readings.  Currently stores repeat data

        # store records.   
        for reading in self.current_readings:
            self._session.add(reading)    
            self._session.commit()

        # TODO check if returning self works; this is an experiment for method chaining
        return(self)    

    def close(self):
        """closes the session opened for this collector"""
        self._session.close()
        self._engine.dispose()
