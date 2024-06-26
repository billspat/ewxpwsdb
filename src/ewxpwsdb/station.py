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
    
    sampling_interval: int
    expected_readings_day: int
    expected_readings_hour: int
    first_reading_datetime: datetime
    first_reading_datetime_utc: AwareDatetime
    latest_reading_datetime: datetime
    latest_reading_datetime_utc: AwareDatetime
    supported_variables: str
    
    @classmethod
    def weatherstation_plus_sql(cls, station_code)->str:
        return f"""select 
            weatherstation.*,
            stationtype.sampling_interval,
            stationtype.supported_variables,
            min(reading.data_datetime at time zone weatherstation.timezone) first_reading_datetime, 
            min(reading.data_datetime) as first_reading_datetime_utc,
            max(reading.data_datetime at time zone weatherstation.timezone) as latest_reading_datetime, 
            max(reading.data_datetime) as latest_reading_datetime_utc,
            60/stationtype.sampling_interval::int as expected_readings_hour,
            (24*60)/stationtype.sampling_interval::int as expected_readings_day
        from 
            weatherstation inner join stationtype on weatherstation.station_type = stationtype.station_type
            inner join reading on weatherstation.id = reading.weatherstation_id 
        where 
            weatherstation.station_code = '{station_code}'
        group by 
            weatherstation.id, stationtype.sampling_interval, stationtype.supported_variables
        """
        
    @classmethod
    def with_detail(cls, station_code, engine)->Self:
        """ add info to a WeatherStation model"""
        
        if not check_engine(engine):
            raise ValueError("invalid engine/connection string: {engine}")
        with Session(engine) as session:             
            result = session.exec(text(cls.weatherstation_plus_sql(station_code))).one()   #type: ignore
        
        return cls(**result._asdict())
    
    
class Station():
    """convenience functions to create WeatherStation models from database and output in various formats.   
    Similar to the Collector class but does not pull any data"""

    def __init__(self, weather_station:WeatherStation)->None:

        self.station_code:str = weather_station.station_code
        self.weather_station = weather_station
        self.weather_api = API_CLASS_TYPES[weather_station.station_type](weather_station)

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
    
    
    def weatherstation_plus_sql(self)->str:
        return f"""select 
            weatherstation.*,
            stationtype.sampling_interval,
            stationtype.supported_variables,
            min(reading.data_datetime at time zone weatherstation.timezone) first_reading_datetime, 
            min(reading.data_datetime) as first_reading_datetime_utc,
            max(reading.data_datetime at time zone weatherstation.timezone) as latest_reading_datetime, 
            max(reading.data_datetime) as latest_reading_datetime_utc,
            60/stationtype.sampling_interval::int as expected_readings_hour,
            (24*60)/stationtype.sampling_interval::int as expected_readings_day
        from 
            weatherstation inner join stationtype on weatherstation.station_type = stationtype.station_type
            inner join reading on weatherstation.id = reading.weatherstation_id 
        where 
            weatherstation.id = {self.weather_station.id}
        group by 
            weatherstation.id, stationtype.sampling_interval, stationtype.supported_variables
        """


    def station_with_detail(self, engine)->WeatherStationDetail:
        """ add info to a WeatherStation model for API output"""
        if not check_engine(engine):
            raise ValueError("invalid engine/connection string: {engine}")
        
        with Session(engine) as session:             
            result = session.exec(text(self.weatherstation_plus_sql())).one()   #type: ignore
            weatherstation_plus = result._asdict()
        
        return WeatherStationDetail(**weatherstation_plus)
                              

    def as_dict(self):
        """ dump model but do not include the config that may contain api secrets"""
        station_dict = self.weather_station.model_dump(exclude={'api_config'})  # typing note: 'exclude' param requires a 'set' type
        return station_dict


    def as_json(self):
        """output string version but without config that may contain api secrets"""
        station_dict = self.as_dict()
        station_str = json.dumps(station_dict, indent = 4,sort_keys=True, default=str)
        return station_str