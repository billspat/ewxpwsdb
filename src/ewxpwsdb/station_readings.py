"""Station and StationReadings class for pulling data from the database"""

import logging
from datetime import datetime, date, timezone
from sqlmodel import select, Session, text
from typing import Self, Sequence
from zoneinfo import ZoneInfo
from sqlalchemy.exc import NoResultFound

from ewxpwsdb.db.models import Reading, WeatherStation, APIResponse
from ewxpwsdb.db.summary_models import HourlySummary, DailySummary, MissingDataSummary, LatestWeatherSummary
from ewxpwsdb.db.database import Engine
from ewxpwsdb.time_intervals import UTCInterval, is_utc, DateInterval

from ewxpwsdb.station import Station
from ewxpwsdb.weather_apis import API_CLASS_TYPES

from ewxpwsdb.weather_apis.weather_api import WeatherAPI

# Configure logger for this module
logger = logging.getLogger(__name__)

class StationReadings():
    """Methods for interacting (read/write) with reading table for a specific 
    weather station
    """

    def __init__(self, station : WeatherStation, engine:Engine):    
        """create StationReadings object given station and db engine

        Args:
            station (WeatherStation): _description_
            engine (Engine): _description_

        Raises:
            ValueError: _description_
        """
        if not station.id:
            raise ValueError("weather station must be saved in the database and have an ID value")
        
        self.station:WeatherStation = station
        self.weather_api:WeatherAPI = API_CLASS_TYPES[station.station_type](station)
        self._engine:Engine = engine

        #TODO find or write converter from Python timezone to PG timezones 
        # until that's done, put the timezone for all of our stations here
        self.postgtres_friendly_timezone = 'est'

        logger.info(f"Initialized StationReadings for station ID {station.id}")

    @classmethod
    def from_station_id(cls, station_id:int, engine:Engine) -> Self:
        """Create StationReadings object given a valid weather station ID number from the database.   

        Args:
            station_id (int): database ID of station
            engine (Engine): sqlalchemy engine object with working connection to an EWX database
        
        """

        try:
            station:Station = Station.from_station_id(station_id, engine)
        except NoResultFound:
            logger.error(f"No result found for station ID {station_id}")
            raise NoResultFound(f"No station found with ID {station_id}")
        logger.info(f"Created StationReadings from station ID {station_id}")
        return(cls(station = station.weather_station, engine = engine))
    

    @classmethod
    def from_station_code(cls, station_code:str, engine:Engine) -> Self:
        """Create StationReadings object given a valid weather station ID number from the database.   

        Args:
            station_id (int): database ID of station
            engine (Engine): sqlalchemy engine object with working connection to an EWX database
        
        """
        try:
            station:Station = Station.from_station_code(station_code, engine)
        except NoResultFound:
            logger.error(f"No station found with code {station_code}")
            raise NoResultFound(f"No station found with code {station_code}")
        logger.info(f"Created StationReadings from station code {station_code}")
        return cls(station = station.weather_station, engine = engine)

    
    @property
    def zone_info(self):
        return(ZoneInfo(self.station.timezone))
    
            
    def recent_readings(self, n:int=1)->Sequence[Reading]:
        """get some readings from the DB for this station
        
        Args:
            n (int): number of records to pull, defaults to 1

        Returns:
            list of Reading objects 
        """

        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).order_by(Reading.data_datetime.desc()).limit(n) #type: ignore
        
        with Session(self._engine) as session:
            readings = session.exec(stmt).fetchall()

        logger.info(f"Retrieved {len(readings)} recent readings for station ID {self.station.id}")
        return(readings)


    def has_readings(self):
        """Check if there are readings for this station in the database currently, or none

        Args:
            station_id (int): valid id of a station in the database, e.g. station.id

        Returns:
            bool: True if any readings in table with this stations id.  
        """
        has_readings = True if self.recent_readings(n = 1) else False
        logger.info(f"Station ID {self.station.id} has readings: {has_readings}")
        return has_readings


    def latest_reading(self)->Reading|None:
        """convenience function to pull one reading, most recent by date"""
        # readings = self.recent_readings(n = 1)
        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).order_by(Reading.data_datetime.desc()).limit(1) #type: ignore
        with Session(self._engine) as session:
            reading:Reading|None = session.exec(stmt).first()
        
        logger.info(f"Latest reading for station ID {self.station.id}: {reading}")
        return reading

    def earliest_reading(self)->Reading | None:        
        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).order_by(Reading.data_datetime.asc()).limit(1) #type: ignore
        with Session(self._engine) as session:
            reading:Reading |None  = session.exec(stmt).first()

        logger.info(f"Earliest reading for station ID {self.station.id}: {reading}")
        return reading

        
    def first_reading_datetime_local(self)->datetime|None:
        """convenience function to return the date of the first reading in the db for this station, mostly to get the date pull one reading ordered by date
        
        Returns:
            datetime of the first reading in the db, which was inserted as UTC but does not have a timezone component
        """

        reading = self.earliest_reading()
        first_reading_datetime_local = ( reading.data_datetime.astimezone(self.zone_info) if reading else None )
        logger.info(f"First reading datetime local for station ID {self.station.id}: {first_reading_datetime_local}")
        return first_reading_datetime_local
                

    def first_reading_date(self)->datetime|None:
        """convenience function to return the date of the first reading in the db for this station, mostly to get the date pull one reading ordered by date
        
        Returns:
            datetime of the first reading in the db, which was inserted as UTC but does not have a timezone component
        """

        reading = self.earliest_reading()
        first_reading_date = ( reading.data_datetime if reading else None )
        logger.info(f"First reading date for station ID {self.station.id}: {first_reading_date}")
        return first_reading_date

        
    def readings_by_interval_utc(self, interval:UTCInterval, order_by:str='desc')->list[Reading|None]:
        """get some readings from the DB for this station
        
        Args:
            interval: UTCInterval
            order:Optional[str] default desc for descending but must desc or asc to match python sqlalchemy order by clauses

        Returns:
            Sequence of Reading objects to be looped through
        """
        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).where(Reading.data_datetime >= interval.start).where(Reading.data_datetime <= interval.end).order_by(Reading.data_datetime) #type:ignore       

        with Session(self._engine) as session:
            readings = session.exec(stmt).fetchall()
    
        logger.info(f"Retrieved {len(readings)} readings for station ID {self.station.id} within interval {interval}")
        if readings:
            return [reading for reading in readings]
        else:
            return []
        
    
    def readings_by_date_interval_local(self, dates: DateInterval)->list[Reading|None]:    
        """get some readings from the DB for this station during the times that occur within the dates (local time)
        
        Args:
            dates (DateInterval): object with start and end dates in local time, start > end
            
            order Optional[str] default desc for descending but must desc or asc to match python sqlalchemy order by clauses

        Returns:
            list[Reading]: list of reading records that occur on or after the start date (date 00:00 ) up to be not including end date (e.g. day before, 23:59),
                for the timezone of the station
        """
        
        
        # just in case, let's fix the timezone to be the timezone for the station
        
        #  convert to a UTC interval
        interval = dates.to_utc_datetime_interval(local_timezone=self.station.timezone)
        
        # get all data same as for UTCInterval
        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).where(Reading.data_datetime >= interval.start).where(Reading.data_datetime <= interval.end).order_by(Reading.data_datetime) #type:ignore       

        with Session(self._engine) as session:
            readings = session.exec(stmt).fetchall()
    
        logger.info(f"Retrieved {len(readings)} readings for station ID {self.station.id} within local date interval {dates}")
        if readings:
            return [reading for reading in readings]
        else:
            return []
        
    
    def api_responses_by_interval_utc(self, interval:UTCInterval)->list[APIResponse]:
        """get the set of responses that covers all readings in an interval.  
        The time ranges of these responses may overlap if data was pulled f
        or overlapping dates repeatedly.  This does not get api responses that may have
        been supercede by later api requests, only those response that account for current
        readings in this interval (linked by reading.apiresponse_id)

        Args:
            interval (UTCInterval): range of reading data_datetimes (inclusive)   

        Returns:
            list[APIResponse]: all APIResponse records linked by readings apiresponse_ids
        """
        
        sql_str = f"""
        select 
            distinct apiresponse.* 
        from 
            reading inner join apiresponse on reading.apiresponse_id = apiresponse.id
        where 
	        reading.data_datetime >= '{interval.start.isoformat()}'::timestamp with time zone
	        and 
            reading.data_datetime <= '{interval.end.isoformat()}'::timestamp with time zone
            and reading.weatherstation_id = {self.station.id};
        """          
        print(sql_str)
        
        with Session(self._engine) as session:
            result = session.exec(text(sql_str))   #type: ignore
            apiresponses = [APIResponse(**dict(r._asdict())) for r in result.all()]
            
        logger.info(f"Retrieved {len(apiresponses)} API responses for station ID {self.station.id} within interval {interval}")
        return apiresponses
        
    
    def missing_summary(self, start_datetime:datetime|None=None, end_datetime:date = date.today())->list[UTCInterval]:
        
        if self.station.id is None:
            raise RuntimeError("this station must be in the database and have an ID")
        else:
            station_id:int = self.station.id
            
        interval = UTCInterval.init_from_local(local_start = start_datetime, local_end = end_datetime, local_timezone=self.station.timezone)
        
        missing_summary_sql = MissingDataSummary.missing_summary_sql(station_id = self.station.id, 
                                                                     sampling_interval = self.weather_api._sampling_interval, 
                                                                     start_datetime = interval.start, 
                                                                     end_datetime = interval.end) 
        
        missing_data_intervals = []   
        # sometimes the start/end are blank as an artifact of the sql, so have to handle each case 
        with Session(self._engine) as session:
            result = session.exec(text(missing_summary_sql))   #type: ignore
            for r in result.all():
                if r.start is None and r.end is None:
                    pass
                else:
                    missing_data_intervals.append ( UTCInterval(
                                start= r.start if r.start is not None else r.end, 
                                end  = r.end   if r.end   is not None else r.start
                                                                )
                                                   ) 
            
        return(missing_data_intervals)
         
         
    def hourly_summary(self, local_start_date:date, local_end_date:date)->list[HourlySummary]:
        """submits SQL to calculate hourly summaries of readings for this station, for whole days in the date interval, local time. 
        Will eventually use the timezone of the station, but needs to convert from Python timezone strings to postgresql timezone strings
        so this version uses just one timezone: est since that is what is used.  Not sure what will happen when it's EDT 

        Args:
            local_date_interval (DateInterval): a date interval (start < end ), not times but whole days, for local time

        Raises:
            RuntimeError: the station of this object must  have a database record (inserted and saved in the db)

        Returns:
            list[HourlySummary]: list of summaries of weather reading values, 1 per hour, with the hour number in station local times.  See HourlySummary class for details. 
        """
        
        if self.station.id is None:
            raise RuntimeError("this station must be in the database and have an ID")
        else:
            station_id:int = self.station.id
         
        if local_start_date > local_end_date:
            raise ValueError("end date must come after start date")
        
        sql_str = HourlySummary.sql_str(station_id=station_id, local_start_date= local_start_date, 
                                        local_end_date = local_end_date)
                
        with Session(self._engine) as session: 
            result = session.exec(text(sql_str))   #type: ignore
            hourly_summaries:list[HourlySummary] =  [HourlySummary(**r._asdict()) for r in result.all()]

        logger.info(f"Retrieved hourly summaries for station ID {self.station.id} from {local_start_date} to {local_end_date}")
        return hourly_summaries


    def daily_summary(self, local_start_date:date, local_end_date:date)->list[DailySummary]:
        """submits SQL to calculate daily summaries of readings for this station, for whole days in the date interval, local time. 
        Will eventually use the timezone of the station, but needs to convert from Python timezone strings to postgresql timezone strings
        so this version uses just one timezone: est since that is what is used.  Not sure what will happen when it's EDT 

        Args:
            local_date_interval (DateInterval): a date interval (start < end ), not times but whole days, for local time

        Raises:
            RuntimeError: the station of this object must  have a database record (inserted and saved in the db)

        Returns:
            list[HourlySummary]: list of summaries of weather reading values, 1 per hour, with the hour number in station local times.  See HourlySummary class for details. 
        """
        
        if self.station.id is None:
            raise RuntimeError("this station must be in the database and have an ID")
        else:
            station_id:int = self.station.id
         
        if local_start_date > local_end_date:
            raise ValueError("end date must come after start date")
        
        sql_str = DailySummary.sql_str(station_id=station_id, local_start_date= local_start_date, 
                                        local_end_date = local_end_date)
                
        with Session(self._engine) as session: 
            result = session.exec(text(sql_str))   #type: ignore
            daily_summaries:list[DailySummary] =  [DailySummary(**r._asdict()) for r in result.all()]

        logger.info(f"Retrieved daily summaries for station ID {self.station.id} from {local_start_date} to {local_end_date}")
        return daily_summaries


    def latest_weather(self)->LatestWeatherSummary:
        """gets a single row of readings that is the latest reading for use by 
        the API. This is different from 'latest_reading()' above because it 
        uses the Pydantic class model for the output, which is in turn used 
        in the API for documentation.   

        Returns:
            LatestWeatherSummary: a single records that is the most recent 
            (latest) reading record with some added
            metadata from the station.   See summary_models.py for details
        """
        if self.station.id is None:
            raise RuntimeError("this station must be in the database and have an ID")
        else:
            station_id:int = self.station.id
            
        sql_str:str = LatestWeatherSummary.latest_weather_sql(station_id = station_id)

        with Session(self._engine) as session: 
            # this should be one row
            result = session.exec(text(sql_str))   #type: ignore
            r = result.fetchone()
            
        latest_weather:LatestWeatherSummary =  LatestWeatherSummary(**r._asdict())
        return(latest_weather)
        
        
    