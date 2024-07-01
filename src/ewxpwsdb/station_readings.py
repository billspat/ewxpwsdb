"""Station and StationReadings class for pulling data from the database"""

from datetime import datetime, date
from sqlmodel import select, Session, text
from typing import Self, Sequence

from ewxpwsdb.db.models import Reading, WeatherStation
from ewxpwsdb.db.summary_models import HourlySummary, DailySummary
from ewxpwsdb.db.database import Engine
from ewxpwsdb.time_intervals import UTCInterval, is_utc
from ewxpwsdb.station import Station
from ewxpwsdb.weather_apis import API_CLASS_TYPES

from ewxpwsdb.weather_apis.weather_api import WeatherAPI

from zoneinfo import ZoneInfo

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

    @classmethod
    def from_station_id(cls, station_id:int, engine:Engine) -> Self:
        """Create StationReadings object given a valid weather station ID number from the database.   

        Args:
            station_id (int): database ID of station
            engine (Engine): sqlalchemy engine object with working connection to an EWX database
        
        """

        station:Station = Station.from_station_id(station_id, engine)
        return(cls(station = station.weather_station, engine = engine))
    

    @classmethod
    def from_station_code(cls, station_code:str, engine:Engine) -> Self:
        """Create StationReadings object given a valid weather station ID number from the database.   

        Args:
            station_id (int): database ID of station
            engine (Engine): sqlalchemy engine object with working connection to an EWX database
        
        """
        station:Station = Station.from_station_code(station_code, engine)
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

        return(readings)


    def has_readings(self):
        """Check if there are readings for this station in the database currently, or none

        Args:
            station_id (int): valid id of a station in the database, e.g. station.id

        Returns:
            bool: True if any readings in table with this stations id.  
        """
        return True if self.recent_readings(n = 1) else False


    def latest_reading(self)->Reading|None:
        """convenience function to pull one reading, most recent by date"""
        # readings = self.recent_readings(n = 1)
        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).order_by(Reading.data_datetime.desc()).limit(1) #type: ignore
        with Session(self._engine) as session:
            reading:Reading|None = session.exec(stmt).first()
        
        return reading

    def earliest_reading(self)->Reading | None:        
        stmt = select(Reading).where(Reading.weatherstation_id == self.station.id).order_by(Reading.data_datetime.asc()).limit(1) #type: ignore
        with Session(self._engine) as session:
            reading:Reading |None  = session.exec(stmt).first()

        return reading

        
    def first_reading_datetime_local(self)->datetime|None:
        """convenience function to return the date of the first reading in the db for this station, mostly to get the date pull one reading ordered by date
        
        Returns:
            datetime of the first reading in the db, which was inserted as UTC but does not have a timezone component
        """

        reading = self.earliest_reading()
        return ( reading.data_datetime.astimezone(self.zone_info) if reading else None )
                

    def first_reading_date(self)->datetime|None:
        """convenience function to return the date of the first reading in the db for this station, mostly to get the date pull one reading ordered by date
        
        Returns:
            datetime of the first reading in the db, which was inserted as UTC but does not have a timezone component
        """

        reading = self.earliest_reading()
        return ( reading.data_datetime if reading else None )

        
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
    
        if readings:
            return [reading for reading in readings]
        else:
            return []
        
    from ewxpwsdb.time_intervals import DateInterval
    
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
    
        if readings:
            return [reading for reading in readings]
        else:
            return []
        
       
    def missing_summary(self, start_datetime:datetime|None=None, end_datetime:date = date.today())->list[UTCInterval]:
        """Identify gaps in the reading record for this station"""   
        
        assert(start_datetime) is not None
        
        if start_datetime is None:
            start_datetime = self.first_reading_date()
                    
        elif not is_utc(start_datetime):
            start_datetime = start_datetime.astimezone(timezone.utc)  # type: ignore
        
        if not end_datetime:
            end_datetime = self.latest_reading().data_datetime # type: ignore

        if not is_utc(end_datetime): # type: ignore
            end_datetime = end_datetime.astimezone(timezone.utc) # type: ignore
        
        
        utc_interval = UTCInterval(start = start_datetime, end = end_datetime).model_dump_iso() # type: ignore
        
               
        sql_str = f"""
        SELECT DISTINCT
            CASE
            when gap_start =true and gap_end = true then missing_datetime
            when gap_start = false and gap_end = true then LAG(missing_datetime, 1) OVER ( ORDER BY missing_datetime ) 
            when gap_start = true and gap_end = false then missing_datetime
            when gap_start = false and gap_end = false then Null
            END start, 
            CASE
            when gap_start =true and gap_end = true then missing_datetime
            when gap_start = false and gap_end = true then missing_datetime
            when gap_start = true and gap_end = false then LEAD(missing_datetime, 1) OVER ( ORDER BY missing_datetime )
            when gap_start = false and gap_end = false then Null
            END end
            -- ,
            -- missing_datetime as actual_missing_datetime, gap_start, gap_end 
        FROM 
            ( SELECT 
                clock.tick as missing_datetime, 
                data_datetime,
                ( tick - lag(tick)  over (order by clock.tick) ) > interval '{self.weather_api._sampling_interval} minutes' as gap_start,
                ( tick - lead(tick) over (order by clock.tick) )* -1 > interval '{self.weather_api.sampling_interval} minutes' as gap_end

            FROM
        
                (SELECT
                    generate_series( 
                        '{utc_interval['start']}'::timestamp with time zone, 
                        '{utc_interval['end']}'::timestamp with time zone, 
                        '{self.weather_api._sampling_interval} minutes') 
                    as tick) 
                as clock 
            
                left outer join 
                (SELECT 
                    data_datetime 
                FROM reading 
                WHERE reading.weatherstation_id = {self.station.id}
                ) 
                as station_readings
                    on clock.tick = station_readings.data_datetime

            WHERE data_datetime is null

            ) as gap_finder
  
        WHERE  ( gap_end = true or gap_start = true)
        """
        
        print(sql_str)
        
        with Session(self._engine) as session:
            result = session.exec(text(sql_str))   #type: ignore

            missing_data_intervals:list[UTCInterval] =  [
                    UTCInterval(start= r.start if r.start is not None else r.end, 
                                end  = r.end   if r.end   is not None else r.start) 
                    for r in result.all()
                    ]
        
        print(missing_data_intervals)
        
        return missing_data_intervals
    
        
         
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

        return daily_summaries
