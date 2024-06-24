import json
from sqlmodel import select
from typing import Self
from datetime import datetime, date
from pydantic import BaseModel, SecretStr, AwareDatetime
from sqlalchemy.sql import text


from ewxpwsdb.db.models import WeatherStation, Reading
from ewxpwsdb.db.database import Session, Engine, check_engine
from ewxpwsdb.weather_apis import API_CLASS_TYPES
from ewxpwsdb.time_intervals import DateInterval


    
#     def weather_api(self):
#         return (API_CLASS_TYPES[self.station_type](self))
        
#     def connectable(self):
#         can_connect:bool = self.weather_api().get_test_readings()
#         return(can_connect)
    
    
#     def station_with_dates_sql(weatherstation_id, timezone='est')->str:
#         return """
#         select 
#             min(reading.data_datetime at time zone '{pg_timezone}') first_reading_datetime, 
#             min(reading.data_datetime) as first_reading_datetime_utc,
#             max(reading.data_datetime at time zone '{pg_timezone}') as latest_reading_datetime, 
#             max(reading.data_datetime) as latest_reading_datetime_utc,
#             weatherstation.* 
#         from 
#             weatherstation inner join reading on weatherstation.id = reading.weatherstation_id 
#         where 
#             weatherstation.id = 2 
#         group by 
#             weatherstation.id
#         """
    
#     @classmethod 
#     def from_id(cls, weatherstation_id:int, engine:Engine)->Self:
#         if not check_engine(engine):
#             raise ValueError("invalid engine/connection string: {engine}")
#         try:
#             with Session(engine) as session: 
#                 sql_str = cls.station_with_dates_sql(weatherstation_id=weatherstation_id, timezone = 'est')
#                 result = session.exec(text(sql_str)).one()   #type: ignore
#                 station_response  = cls(**result._asdict()) 

#             return station_response
                              
#         except Exception as e:
#             raise RuntimeError(f"could not get station {weatherstation_id} from database")


class WeatherStationDetail(BaseModel):
    """WeatherStation database table with additional status information"""
    
    id: int
    station_code: str
    station_type: str
    install_date: date
    timezone: str
    ewx_user_id: str
    lat: float
    lon: float
    location_description: str
    background_place: str
    api_config: SecretStr
    
    first_reading_datetime: datetime
    first_reading_datetime_utc: AwareDatetime
    latest_reading_datetime: datetime
    latest_reading_datetime_utc: AwareDatetime
    supported_variables: list[str]

    
class Station():
    """convenience functions to create WeatherStation models from database and output in various formats.   
    Similar to the Collector class but does not pull any data"""

    def __init__(self, weather_station:WeatherStation)->None:

        self.station_code:str = weather_station.station_code
        self.weather_station = weather_station
        self.weather_api = API_CLASS_TYPES[weather_station.station_type](weather_station)
        # to do function that converts any US timezone to 3-letter code version
        self.pg_timezone = 'est'
        

    def can_connect(self):
        if self.weather_api().get_test_readings():
            return True
        else:
            return False
    

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
    def all_station_codes(cls,engine:Engine)->list[str]:
        with Session(engine) as session:            
            station_codes = session.exec(select(WeatherStation.station_code)).fetchall()
        # make it a list for real
        station_codes =  [station_code for station_code in station_codes]
        return station_codes

    @classmethod
    def valid_station_code(cls, station_code:str, engine:Engine)->bool:
        try:
            s = cls.from_station_code(station_code, engine)
            if s:
                return True
            else:
                return False
        except Exception as e:
            return False
    
    
    def station_with_dates_sql(self)->str:
        return f"""select 
            min(reading.data_datetime at time zone '{self.pg_timezone}') first_reading_datetime, 
            min(reading.data_datetime) as first_reading_datetime_utc,
            max(reading.data_datetime at time zone '{self.pg_timezone}') as latest_reading_datetime, 
            max(reading.data_datetime) as latest_reading_datetime_utc,
            weatherstation.* 
        from 
            weatherstation inner join reading on weatherstation.id = reading.weatherstation_id 
        where 
            weatherstation.id = {self.weather_station.id}
        group by 
            weatherstation.id
        """

    def station_dict_with_detail(self, engine)->dict:
        """ add info to a WeatherStation model for API output"""
        if not check_engine(engine):
            raise ValueError("invalid engine/connection string: {engine}")
        
        with Session(engine) as session:             
            result = session.exec(text(self.station_with_dates_sql())).one()   #type: ignore
            weatherstation_plus = result._asdict()
            
        weatherstation_plus['supported_variables'] = self.weather_api.supported_variables
            
        return weatherstation_plus 
                              

    def as_dict(self):
        """ dump model but do not include the config that may contain api secrets"""
        station_dict = self.weather_station.model_dump(exclude={'api_config'})  # typing note: 'exclude' param requires a 'set' type
        return station_dict


    def as_json(self):
        """output string version but without config that may contain api secrets"""
        station_dict = self.as_dict()
        station_str = json.dumps(station_dict, indent = 4,sort_keys=True, default=str)
        return station_str