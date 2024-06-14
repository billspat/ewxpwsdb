import json
from sqlmodel import select
from typing import Self

from ewxpwsdb.db.models import WeatherStation
from ewxpwsdb.db.database import Session, Engine, check_engine


class Station():
    """convenience functions to read from database and output in various formats"""

    def __init__(self, weather_station:WeatherStation)->None:

        self.station_code:str = weather_station.station_code
        self.weather_station = weather_station


    @classmethod 
    def from_station_code(cls, station_code:str, engine:Engine)->Self:
        if not check_engine(engine):
            raise ValueError("invalid engine/connection string: {engine}")

        try:
            with Session(engine) as session:            
                stmt = select(WeatherStation).where(WeatherStation.station_code == station_code)
                station_record:WeatherStation= session.exec(stmt).one()                
        except Exception as e:
            raise RuntimeError(f"could not get station {station_code} from database engine {engine}")
        
        if station_record:
            return cls(weather_station = station_record)
        else:
            raise ValueError(f"no station record found with id {station_code}")
        


    @classmethod
    def from_station_id(cls, station_id:int, engine:Engine) -> Self:
        if not check_engine(engine):
            raise ValueError("invalid engine/connection string: {engine}")
        
        with Session(engine) as session:
            # note this is SQLModel syntax, not SQLAlchemy
            try:
                station_record:WeatherStation|None = session.get(WeatherStation, station_id)                
            except Exception as e:
                raise RuntimeError(f"database error retrieving station record with id {station_id}: {e}")

            if station_record:
                return cls(weather_station = station_record)
            else:
                raise ValueError(f"no station record found with id {station_id}")


    @classmethod
    def all_station_codes(cls,engine:Engine):
        with Session(engine) as session:            
            station_codes = session.exec(select(WeatherStation.station_code)).fetchall()
        # make it a list for real
        # station_codes =  [station.station_code for station in stations]
        return station_codes




    def as_dict(self):
        """ dump model but do not include the config that may contain api secrets"""
        station_dict = self.weather_station.model_dump(exclude={'api_config'})  # typing note: 'exclude' param requires a 'set' type
        return station_dict


    def as_json(self):
        """output string version but without config that may contain api secrets"""
        station_dict = self.as_dict()
        station_str = json.dumps(station_dict, indent = 4,sort_keys=True, default=str)
        return station_str