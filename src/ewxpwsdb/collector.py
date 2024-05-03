"""weather data collection class"""

from datetime import datetime, timedelta, timezone


from sqlmodel import SQLModel, select, update
from sqlalchemy import Engine, asc, desc
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError

from typing import Sequence

from ewxpwsdb.db.database import Session, engine
from ewxpwsdb.db.models import WeatherStation, APIResponse, Reading
from ewxpwsdb.weather_apis import API_CLASS_TYPES
from ewxpwsdb.time_intervals import one_day_interval, UTCInterval, is_utc, previous_fourteen_minute_interval, fifteen_minute_mark


class Collector():
    """class to enable collecting data from station apis and store in a database.  
    This class connects the components of the system to be invoked by a workflow manager.    """

    current_reading_ids: list[int] = []
    current_api_response_record_ids: list[int] = []
    current_api_response: APIResponse|None = None

    @classmethod
    def from_station_code(cls, station_code:str, engine:Engine = engine):
        """Create collector object from a valid station_code

        Args:
            station_code (str): valid station table station_code
            engine (Engine, optional):   Defaults to engine created from imported database module

        Raises:
            ValueError: if not station is found matching station code, or multiple stations match

        Returns:
            Collector: collector object for the station with that station code 
        """

        with Session(engine) as session:
            stmt = select(WeatherStation).where(WeatherStation.station_code == station_code)
            records = session.exec(stmt).fetchall()

            if len(records) > 1:
                raise ValueError(f"collector.from_station_code value error: station_code {station_code} returned multiple records")

            if len(records) == 1:
                station:WeatherStation = records[0]
                return cls(station = station, engine=engine)
            else:
                raise ValueError(f"collector class value error: no station record with station_code {station_code} found")
            
    @classmethod
    def from_station_id(cls, station_id:int, engine:Engine = engine):
        """Create collector object from a valid database id for the station table

        Args:
            station_id (int): valid station table id value
            engine (Engine, optional):   Defaults to engine created from imported database module

        Raises:
            ValueError: if not station is found with id

        Returns:
            Collector: collector object for the station with id = stationid
        """
        with Session(engine) as session:
            station = session.get(WeatherStation, station_id)
            if station:
                return cls(station, engine)
            else:
                raise ValueError(f"collector class value error: no station record with id {station_id} found")

    def __init__(self, station:WeatherStation, engine:Engine = engine):
        """create a collector object for pulling for an API specific to a station type.  
        This creates a database session open for the life of this object.   Use collector.close() when operations are complete.  

        Args:
            station_id (int): Database ID (primary key) of a weather station record
            engine (Engine, optional): Engine connection for existing EWX PWS database that data is read/written to.  Defaults to global engine from database.py. 
        """

        self._engine = engine
        self._session = Session(engine)
        self.station = station
        # instatiate API class for this station to collect data         
        self.weather_api = API_CLASS_TYPES[self.station.station_type](self.station)


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
    
    @property
    def current_responses(self)->list|list[APIResponse]:
        """get database records of responses from this session for the ids store from previous API request, if any"""
        responses = []
        for response_id in self.current_api_response_record_ids:

            responses.append(self._session.get(APIResponse, response_id)) 
        
        return(responses)

    @property
    def current_readings(self)->list|list[Reading]:
        """get database records of readings from this session for the ids store from previous API request, if any"""
        readings = []
        for reading_id in self.current_reading_ids:
            readings.append(self._session.get(Reading, reading_id)) 

        return(readings)

    #########################
    # primary methods

    def request_and_store_weather_data_utc(self, interval:UTCInterval):
        return(self.request_and_store_weather_data(interval.start, interval.end))


    def request_and_store_weather_data(self, start_datetime:datetime, end_datetime:datetime):
        """use API class to request data for a range of UTC timestamps.  
         Stores the data from the request/response internally and in the database
         
        Args:
            start_datetime (datetime): start of interval, timezone aware datetime in UTC
            end_datetime (datetime): end of interval, timezone aware datetime in UTC
             
        Returns:
            this object for method chaining
        """

        if not is_utc(start_datetime):
            raise ValueError(f"start datetime is not UTC timezone {start_datetime}")
    
        if not is_utc(end_datetime):
            raise ValueError(f"end datetime is not UTC timezone: {end_datetime}")
        
        # call station vendor web API
        responses = self.weather_api.get_readings(start_datetime = start_datetime,  end_datetime = end_datetime)


        if responses:
            # there is some kind of response, so clear out current "recent data" to fill as these are saved to db
            saved_responses = []
            self.current_api_response_record_ids = []
            self.current_reading_ids = []

            for response in responses:
                if not self.weather_api.data_present_in_response(response):    
                    self.api_error_handler(start_datetime, end_datetime, response)
                    
                self.current_api_response = response
                self._session.add(response)
                self._session.commit()

                if response.id:
                    # transform this response and save readings
                    saved_responses.append(response.id)
                    reading_ids = self.save_readings_from_responses(response)

                    self.current_reading_ids.extend(reading_ids)
                else:
                    self.api_error_handler(start_datetime, end_datetime, responses)
                
            self.current_api_response_record_ids = saved_responses

            return(self.current_api_response_record_ids)

        else:
            self.api_error_handler(start_datetime, end_datetime)
            return None
            
    def request_current_weather_data(self):
        """call request weather method with no dates, so API class gets most recent 
        complete 15 minute period.   Stores the data from the request/response internally and in the database"""

        nowish = previous_fourteen_minute_interval()
        result = self.request_and_store_weather_data(start_datetime = nowish.start, end_datetime=nowish.end)
        return(result)

    def api_error_handler(self,start_datetime, end_datetime, responses=None):
        """error handling stub, currently raise exception"""
        if responses:
            raise RuntimeError(f"no data present in response for station for {self.station.id} for interval {start_datetime} to {end_datetime}: {responses}")
        else:
            raise RuntimeError(f"no response from station for {self.station.id} for interval {start_datetime} to {end_datetime}")
        

    # TODO move these to station_readings class since will almost always be selecting/inserting for one station at atime
    def reading_by_time_and_station(self, data_datetime, weatherstation_id):
        with Session(self._engine) as session:
            stmt = select(Reading).where(Reading.data_datetime == data_datetime).where(Reading.weatherstation_id == weatherstation_id)
            reading:Reading = session.exec(stmt).first()

        return(reading)
    
    def insert_or_update_reading(self, new_reading:Reading):
        """inserts the reading data into the database.   If there is a conflict with existing record (e.g. in same time and station), 
        (see Reading model, but currently this is a unique constractin on [data_datetime, weatherstation_id]), instead of throwing a
        SQL error, is uses the SQLAlchemy + Postgresql special 'upsert' feature. 

        This preserves t, data_datetime, and weatherstation_id fields but 
        updates all the other data from the reading sent (ostensibly  transformed from a current APIResponse)

        Args:
            reading: Reading a reading object with data for inserting

        Returns:
            Reading: reading model as retrieved from the db after inserting 

        """

        ## note about this code.   It would be great to use Postgresl upsert function, for example this mostly works
        # reading_data = dict(reading)
        # reading_data.pop('id') 
        # from sqlalchemy.dialects.postgresql import insert as pg_insert
        # stmt = pg_insert(Reading).values(reading_data).returning(Reading.__table__.c.id)
        # upsert_stmt = stmt.on_conflict_do_update(constraint="timeplaceconstraint",set_=stmt.excluded)
        # with Session(self._engine) as session:
        #   r = session.exec(upsert_stmt)
        #   session.commit()
        
        # but because we are looking for conflict on timestamp and station id and _not_ the primary key, you have to take out the null ID
        # and then the id serial pk gets updated +1 every time, which 
        # can break relations etc.   solution would be to use a compound primary key timestamp + stationid
        # however this code _could_ cause race conditions because if the same record is read in another process right beore it gets updated, it may be the old data

        existing_reading = self.reading_by_time_and_station(new_reading.data_datetime, new_reading.weatherstation_id)
        
        if existing_reading:
            # update
            record_id = existing_reading.id

            reading_data = dict(new_reading)
            reading_data.pop('id')
            reading_data.pop('data_datetime')
            reading_data.pop('weatherstation_id')
    
            
            with Session(self._engine) as session:
                stmt = update(Reading).where(Reading.id == record_id).values(reading_data) # .returning(Reading.__table__.c.id)
                session.exec(stmt)
                session.commit()
        else:
            # insert
            with Session(self._engine) as session:
                session.add(new_reading)
                session.commit()
                record_id = new_reading.id

        return record_id
    

    def save_readings_from_responses(self, api_responses:APIResponse|list[APIResponse])->list[int]:
        """transform api response and save to the database, handling errors etc"""

        # allow for single record as parameter, just turn it into a list 
        if not isinstance(api_responses, list):
            api_responses = [api_responses]

        saved_reading_ids = []

        # transform expects list of responses
        readings = self.weather_api.transform(api_responses)
        if readings:
            for reading in readings:
                new_id = self.insert_or_update_reading(new_reading = reading)
                if new_id:
                    saved_reading_ids.append(new_id)
                else:
                    raise RuntimeError(f"could not insert PWS API response record into database")
        else: 
            raise RuntimeError(f"no reading data extracted from responses {api_responses}")
        
        return(saved_reading_ids)    


    def readings_in_db(self):
        """Check if there are readings for this station in the database currently, or none

        Returns:
            bool: True if any readings in table with this stations id.  
        """
        if self.get_readings(n = 1):
            return True
        
        return False
    

    # Typing Notes: 
    ## MyPy type checker 
    ##  - fails on the sqlalchemy.desc() and .asc() which expect strings, or esoteric SQLAlchemy types.  However the sql runs just fine
    ##  - fails with this syntax order_by(Reading.data_datetime.desc()) since the output type (datetime ) doesn't have desc attribute, but sqlmodel/sqlalchemy use tricks to make this work
    ##  one fix it converting the datetime value to string, but do that efficiently using the SQL function to_char allows the type checker to pass, and the SQL to runs correctly, but doesnt work in sqlite
    ##    eg.  order_by( desc(func.to_char( Reading.data_datetime, '%Y%m%d-%H%M%S' ) ) ) 
    ## so instead I'm just ignoring the type warnings on these statements 
    
    def get_readings(self, n:int=1, order_by:str='desc')->Sequence[Reading]:
        """get some readings from the DB for this station
        
        Args:
            n: int number of records to pull, defaults to 1
            order:Optional[str] default desc for descending but must desc or asc to match python sqlalchemy order by clauses

        Returns:
            list of Reading objects 
        """

        if order_by == 'asc':
            stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).order_by(Reading.data_datetime).limit(n) #type: ignore
        elif order_by == 'desc':
            stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).order_by(Reading.data_datetime.desc()).limit(n) #type: ignore
        else:
            raise ValueError(f"order_by argument must be either  'asc' or 'desc', got {order_by}")
        
        result = self._session.exec(stmt)        
        return(result.fetchall())   
    
    def get_readings_by_date(self, interval:UTCInterval, order_by:str='desc')->Sequence[Reading]:
        """get some readings from the DB for this station
        
        Args:
            interval: UTCInterval
            order:Optional[str] default desc for descending but must desc or asc to match python sqlalchemy order by clauses

        Returns:
            list of Reading objects 
        """
        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).where(Reading.data_datetime >= interval.start).where(Reading.data_datetime <= interval.end).order_by(Reading.data_datetime) #type:ignore       
        result = self._session.exec(stmt)
        return(result.fetchall())   

    def get_latest_reading(self)->Reading|None:
        """convenience function to pull one reading ordered by date"""
        readings = self.get_readings(n=1, order_by='desc')
        if len(readings)>0:
            return(readings[0])
        else:
            return(None)
        
    
    def get_first_reading_date(self)->datetime:
        """convenience function to return the date of the first reading in the db for this station, mostly to get the date pull one reading ordered by date
        
        Returns:
            datetime of the first reading in the db, which was inserted as UTC but does not have a timezone component
        """

        readings = self.get_readings(n=1, order_by='asc')
        if len(readings)>0:
            first_reading_datetime = readings[0].data_datetime
            return(first_reading_datetime)
        else:
            return(None)
        

    def get_historic_data(self, overwrite: bool=False, days_limit:int=365)->list[int]:
        """        pull all previous data for this old station starting from right now
        If there is any data already in the db, this will this will not overwrite 
        
        check if there are any readings at all in db for this station, if so, only overwrite if we have permission


        Args:
            overwrite (bool, optional): only overwrite if we have permission.  If False and any readings are present for this station, cancel. Defaults to False.
            days_limit (int, optional): Days to go back. Defaults to 365.

        Raises:
            RuntimeError: if overwrite is not True and there are records, raise an exception

        Returns:
            list[int]: list of all record ids inserted into the reading table
        """

        if self.get_readings(n = 1):
            # already some stuff in the db, probably should use catch up instead
            if not overwrite:
                raise RuntimeError(f"data for station {self.station.id} already present, cancelling get historic data procedure")
            
        collected_reading_ids = []

        # start -- get and save readings for today
        today = datetime.now(timezone.utc).date()
        api_data = self.request_and_store_weather_data_utc(one_day_interval(today))
        
        # get all the remaining tomorrows data, up to the imposed limit (1 yr default)
        day_offset = 1
        while api_data and day_offset <= days_limit:            
            date_to_fetch = today - timedelta(days = day_offset)
            print(f"fetching data for {self.station.station_code} for {day_offset} days ago")
            api_data = self.request_and_store_weather_data_utc(one_day_interval(date_to_fetch))
            collected_reading_ids.extend(self.current_reading_ids)
            day_offset += 1 

        return collected_reading_ids


    def catch_up(self):
        """determines the most recent timestamp of weather data, and attempts to request all data missing and stores in the database= """

        # look in database to get most recent reading (e.g. sort by data descending limit 1)
        # get the datetime for this reading
        # if no reading, raise an exception
        # use that as the starttime and previous 15 mark as end time
        # get readings, transform, and store in the database
        # if there is a problem, don't try to catch the exception let the caller catch, but -some- data may be written 
        
        reading = self.get_latest_reading()
        if not reading:
            # if there are no readings at all (e.g. new station, have to run the get historic data first)
           raise RuntimeError(f"attempting to 'catchup' weather data for station {self.station.station_code} but there is no data at all, cancelling catchup process")
       
        interval_since_last_reading = UTCInterval(start = reading.data_datetime + timedelta(minutes = 1), end  = fifteen_minute_mark() )
        # this has the side effect of storing in the database, we don't keep the api data at all
        # this can raise an exception sometime in the middle, for example if the station is turned off and there is no data
        saved_api_data = self.request_and_store_weather_data_utc(interval= interval_since_last_reading)
        return self.current_reading_ids
        
        
    def close(self):
        """closes the session opened for this collector"""
        self._session.close()
        self._engine.dispose()
