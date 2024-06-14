"""Station and StationReadings class for pulling data from the database"""

import json
from datetime import datetime
from sqlmodel import select, Session
from typing import Self, Sequence

from ewxpwsdb.db.models import Reading, WeatherStation
from ewxpwsdb.db.database import Engine, check_engine
from ewxpwsdb.time_intervals import UTCInterval
from ewxpwsdb.station import Station

class StationReadings():
    """Methods for interacting (read/write) with reading table for a specific weather station
    """

    def __init__(self, station:WeatherStation, engine:Engine):    
        """create StationReadings object given station and db engine

        Args:
            station (WeatherStation): _description_
            engine (Engine): _description_

        Raises:
            ValueError: _description_
        """
        if not station.id:
            raise ValueError("weather station must be saved in the database and have an ID value")
        
        self.station = station
        self._engine = engine

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

    def _exec(self, stmt):
        """convenience function to exec a statement on the db engine.   """
        # try
        with Session(self._engine) as session:
            result = session.exec(stmt)

        return result
    

    def _select(self,stmt)->Sequence:
        result = self._exec(stmt)
        records:Sequence = result.fetchall()
        return(records)

    def recent_readings(self, n:int=1)->Sequence[Reading]:
        """get some readings from the DB for this station
        
        Args:
            n: int number of records to pull, defaults to 1

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
            station_id:int valid id of a station in the database, e.g. station.id

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
            
    
    def first_reading_date(self)->datetime|None:
        """convenience function to return the date of the first reading in the db for this station, mostly to get the date pull one reading ordered by date
        
        Returns:
            datetime of the first reading in the db, which was inserted as UTC but does not have a timezone component
        """

        reading = self.latest_reading()
        return ( reading.data_datetime if reading else None )

        
    def readings_by_interval_utc(self, interval:UTCInterval, order_by:str='desc')->Sequence:
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
        
        return readings
    



