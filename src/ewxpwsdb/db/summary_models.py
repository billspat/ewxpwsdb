
"""data models for hourly and daily statistics generated from the EWX PWS database.   Models classes include the sql to generate the statistics"""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Self
import logging
from ewxpwsdb.weather_apis.weather_api import WeatherAPI

# Set up logging
logger = logging.getLogger(__name__)

from ewxpwsdb.time_intervals import UTCInterval

class HourlySummary(BaseModel):
    """data model for the hourly summary statistics from EWX PWS database, 
    and the sql that can create this data from the database. 
    """

    station_code:str
    year:int
    day:int|str|None|date
    represented_date:date = Field(examples = ['2024-06-25'], description = "date of the reading for the station's timezone")
    represented_hour:int
    record_count: int = Field(description = "number of readings from the database used to calculate this hours summary")
    api_hourly_frequency: int = Field(description = "expected number of readings per hour from this API")

    atmp_count: int
    atmp_avg_hourly: float | None 
    atmp_max_hourly: float | None
    atmp_min_hourly: float | None
    atmp_max_max_hourly: float | None
    atmp_min_min_hourly:  float | None
    
    relh_max_hourly: float | None
    relh_avg_hourly: float | None
    relh_min_hourly: float | None
    
    pcpn_count:  int
    pcpn_total_hourly:  float | None

    lws_count: int
    lws_wet_hourly: int | None
    lws_pwet_hourly: float | None
    
    wdir_avg_hourly: float | None
    wdir_sdv_hourly: float | None
    wdir_null_avg_hourly: float | None
    wdir_null_sdv_hourly: float | None
    wspd_avg_hourly: float | None
    wspd_max_hourly: float | None


    @classmethod
    def sql_str(cls, weather_api:WeatherAPI, local_start_date:date, local_end_date:date)->str:
        """create the postgresql-compatible SQL for summarizing data in the database.   
        This method exists as it was easier to write as SQLModel documentation is lacking
        and SQLAlchemy is hard to learn and debug. 
        
        The inputs are in local time, not UTC, for user convenience.   
                
        
        This is hear to be near to the dataclass-type model itself so the fields correspond.
        
        Args:
            weather_api(WeatherAPI): weatherAPI object for the station
            start_date (date): date at beginning of interval, inclusive (i.e. >=)  to pull readings from, in local time  
            end_date (date): date at end of interval, excluding  (i.e. <)  to pull readings from, in local time.   to pull one day, make this 1 day after start_date 
            station_timezone (str): station timezone as a str

        Returns:
            str: valid SQL for the schema created from the tables in this system, with ids and dates inserted, with timezone adjustments for UTC data
        """
              
        start_date_str = local_start_date.strftime("%Y-%m-%d")
        end_date_str = local_end_date.strftime("%Y-%m-%d")


        sql_str = f"""
            SELECT 
                station_code,
                EXTRACT(YEAR FROM local_date)::integer as "year",
                EXTRACT(DOY FROM local_date) as "day",
                ' ' as rpt_time,
                local_date as represented_date, 
                local_hour represented_hour,
                COUNT(*) as record_count,
                {weather_api.expected_hourly_frequency} as api_hourly_frequency,
                
                SUM(CASE when atmp is not null then 1 else 0 end) as atmp_count,
                ROUND(AVG(atmp)::NUMERIC,2) as atmp_avg_hourly,
                MAX(atmp) as atmp_max_hourly,
                MIN(atmp) as atmp_min_hourly,
                MAX(atmp_max) as atmp_max_max_hourly,
                MIN(atmp_min) as atmp_min_min_hourly,
                
                ROUND(MIN(relh)::NUMERIC,2) as relh_min_hourly,
                ROUND(AVG(relh)::NUMERIC,2) as relh_avg_hourly,
                ROUND(MAX(relh)::NUMERIC,2) as relh_max_hourly,
                
                SUM(CASE when pcpn is not null then 1 else 0 end) as pcpn_count,
                SUM(pcpn) as pcpn_total_hourly,
                
                SUM(CASE when lws is not null then 1 else 0 end) as lws_count,
                SUM(CASE when lws is not null then ( CASE when lws > 0 then 1 else 0 end) else null end) as lws_wet_hourly,
                ROUND( (SUM(lws)/SUM(CASE when lws is not null then 1 else 0 end )) ::NUMERIC,2) as lws_pwet_hourly,            
        
                ROUND(AVG(wdir)::numeric,2) as wdir_avg_hourly,
                ROUND(STDDEV_POP(wdir)::numeric,2) as wdir_sdv_hourly,
                ROUND(AVG(wdir_null)::numeric,2) as wdir_null_avg_hourly,
                ROUND(STDDEV_POP(wdir_null)::numeric,2) as wdir_null_sdv_hourly,

                ROUND(AVG(wspd)::numeric,2) as wspd_avg_hourly, 
                ROUND(MAX(wspd_max)::numeric, 2) as wspd_max_hourly
                

            FROM (
                SELECT
                    (reading.data_datetime at time zone weatherstation.timezone)::timestamp as local_datetime,
                    date_trunc('day', (reading.data_datetime at time zone weatherstation.timezone))::date as local_date,
                    EXTRACT('hour' FROM (reading.data_datetime at time zone weatherstation.timezone))+1 as local_hour,
                    reading.*,
                    (CASE WHEN reading.wdir=0 THEN NULL ELSE reading.wdir END) AS wdir_null,

                    weatherstation.station_code as station_code

                FROM weatherstation 
                inner join reading ON reading.weatherstation_id = weatherstation.id
                
                WHERE reading.weatherstation_id = {weather_api.id} and
                    (reading.data_datetime at time zone weatherstation.timezone)::date >= '{start_date_str}'  and
                    (reading.data_datetime at time zone weatherstation.timezone)::date <= '{end_date_str}' 
                
                ORDER BY reading.weatherstation_id, local_date, local_hour, reading.data_datetime
                )
                AS readings_local_time
            GROUP BY station_code, local_date, local_hour
            ORDER BY station_code, local_date, local_hour
        """

        logger.debug(f"Generated SQL for hourly summary: {sql_str}")
        return sql_str
    
    @classmethod
    def select_hourly_summaries(cls, engine, weather_api:WeatherAPI, local_start_date:date, local_end_date:date)->list[Self]:
        """convenience method to generated a list of hourly summaries from the
        class. This is currently unused and hourly summaries are genereated using 
        method `StationReadings.daily_summary()` which already has an engine property

        Args:
            engine (Engine): sql_model (SQLAlchemy) enginge from which a session
                            can be creatd
            weather_api (WeatherAPI): instance of weatherapi for the station to query
            local_start_date (_type_, optional): _description_. Defaults to None.
            local_end_date (_type_, optional): _description_. Defaults to None.

        Returns:
            list[Self]: _description_
        """
        
        sql_str = cls.sql_str(weather_api= weather_api, local_start_date=local_start_date, local_end_date=local_end_date)
        logger.debug(f"Selecting hourly summaries for station {weather_api.id} from {local_start_date} to {local_end_date}")
        
        from sqlmodel import Session          
        with Session(engine) as session:
            result = session.exec(text(sql_str))   #type: ignore
            hourly_summaries =  [cls(**r._asdict()) for r in result.all()]
            
        return hourly_summaries

#############################################################################     

class DailySummary(BaseModel):
    """data model for the daily summary statistics from EWX PWS database, 
    and the sql that can create this data from the database. 
    """

    station_code:str
    represented_date:date
    
    record_count: int
    api_daily_frequency: int
    
    atmp_count: int
    atmp_avg_daily: float | None 
    atmp_max_daily: float | None
    atmp_min_daily: float | None
    atmp_max_max_daily: float | None
    atmp_min_min_daily:  float | None
   
    relh_count: int
    relh_min_daily: float | None
    relh_avg_daily: float | None
    relh_max_daily: float | None
    
    pcpn_count:  int
    pcpn_total_daily:  float | None

    lws_count: int
    lws_daily:  float | None
    
    wspd_count: int
    wspd_avg_daily: float | None
    wspd_max_daily: float | None


    @classmethod
    def sql_str(cls,  weather_api:WeatherAPI, local_start_date:date, local_end_date:date)->str:
        """create the postgresql-compatible SQL for summarizing data in the database.   
        This method exists as it was easier to write as SQLModel documentation is lacking
        and SQLAlchemy is hard to learn and debug. 
        
        The inputs are in local time, not UTC, for user convenience.   
        The Postgresql SQL includes timezone conversion based on pg_timezone. 
        
        
        
        This is hear to be near to the dataclass-type model itself so the fields correspond.
        
        Args:
            station_id (int): database id number of a station, 
            start_date (date): date at beginning of interval, inclusive (i.e. >=)  to pull readings from, in local time  
            end_date (date): date at end of interval, excluding  (i.e. <)  to pull readings from, in local time.   to pull one day, make this 1 day after start_date 
            station_timezone (str): weatherstation timezone string eg. 'America/Detroit'

        Returns:
            str: valid SQL for the schema created from the tables in this system, with ids and dates inserted, with timezone adjustments for UTC data
        """
    
        start_date_str = local_start_date.strftime("%Y-%m-%d")
        end_date_str = local_end_date.strftime("%Y-%m-%d")


        sql_str = f"""
            SELECT 
                station_code,
                local_date as represented_date, 
                COUNT(*)::int  as record_count,
                {weather_api.expected_daily_frequency}::int as api_daily_frequency,
                SUM(CASE when atmp is not null then 1 else 0 end) as atmp_count,
                
                ROUND(AVG(atmp)::NUMERIC,2) as atmp_avg_daily,
                MAX(atmp) as atmp_max_daily,
                MIN(atmp) as atmp_min_daily,
                MAX(atmp_max) as atmp_max_max_daily,
                MIN(atmp_min) as atmp_min_min_daily,
                
                SUM(CASE when relh is not null then 1 else 0 end) as relh_count,                
                ROUND(AVG(relh)::NUMERIC,2) as relh_avg_daily,
                ROUND(MIN(relh)::NUMERIC,2) as relh_min_daily,
                ROUND(MAX(relh)::NUMERIC,2) as relh_max_daily,
                
                SUM(CASE when pcpn is not null then 1 else 0 end) as pcpn_count,
                SUM(pcpn) as pcpn_total_daily,
                
                SUM(CASE when lws is not null then 1 else 0 end) as lws_count,
                SUM(lws)/SUM(CASE when lws is not null then 1 else 0 end) as lws_daily,
                
                SUM(CASE when wspd is not null then 1 else 0 end) as wspd_count,
                ROUND(AVG(wspd)::numeric,2) as wspd_avg_daily,
                ROUND(MAX(wspd)::numeric,2) as wspd_max_daily

            FROM (
                SELECT
                    (reading.data_datetime at time zone weatherstation.timezone)::date as local_date,
                    EXTRACT(HOUR FROM reading.data_datetime at time zone weatherstation.timezone) as local_hour,

    
                    date_trunc('year', reading.data_datetime at time zone weatherstation.timezone) as "year",
                    reading.*,
                    weatherstation.station_code as station_code

                FROM reading inner join weatherstation
                    ON reading.weatherstation_id = weatherstation.id
                
                WHERE reading.weatherstation_id = {weather_api.id} and
                    (reading.data_datetime at time zone weatherstation.timezone)::date >= '{start_date_str}'  and
                    (reading.data_datetime at time zone weatherstation.timezone)::date <= '{end_date_str}' 
                ORDER BY reading.weatherstation_id, local_date, reading.data_datetime
                )
                AS readings_local_time
            GROUP BY station_code, local_date
            ORDER BY station_code, local_date
        """
        
        #date_trunc('day', reading.data_datetime at time zone '{pg_timezone}')::date as local_date,

        logger.debug(f"Generated SQL for daily summary: {sql_str}")
        return sql_str


#############################################################################     

class LatestWeatherSummary(BaseModel):
    station_code: str
    local_datetime: datetime
    local_date: date
    minutes_since_latest_reading: int
    id: int
    apiresponse_id: int
    data_datetime: datetime
    request_id: str
    weatherstation_id: int
    station_sampling_interval: int
    atmp: float | None
    atmp_min: float | None
    atmp_max: float | None
    dwpt: float | None
    lws: float | None
    pcpn: float | None
    relh: float | None
    rpet: float | None
    smst: float | None
    stmp: float | None
    srad: float | None
    wdir: float | None
    wspd: float | None
    wspd_max: float | None
    
    @classmethod
    def latest_weather_sql(cls, station_id:int):
        
        sql_str = f"""
            SELECT
                weatherstation.station_code,
                reading.data_datetime at time zone weatherstation.timezone as local_datetime,
                (reading.data_datetime at time zone weatherstation.timezone)::date as local_date,
                ROUND(  (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP	- reading.data_datetime) ))/60 ,  0 ) AS minutes_since_latest_reading,
                reading.*
            FROM
                reading inner join weatherstation ON weatherstation.id = reading.weatherstation_id
            WHERE 
                reading.weatherstation_id = {station_id}
            ORDER BY
                reading.data_datetime DESC
            LIMIT 1;
        """
        
        logger.debug(f"Generated SQL for latest weather summary: {sql_str}")

        return(sql_str)





############################################################################# 

class MissingDataSummary(BaseModel):
    missing_data_intervals: list[UTCInterval]
    
    @classmethod
    def missing_summary_sql(cls, station_id:int, sampling_interval, start_datetime:datetime|None=None, end_datetime:date = date.today())-> str: 
          

        utc_interval = UTCInterval(start = start_datetime, end = end_datetime) # type: ignore
        
               
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
                ( tick - lag(tick)  over (order by clock.tick) ) > interval '{sampling_interval} minutes' as gap_start,
                ( tick - lead(tick) over (order by clock.tick) )* -1 > interval '{sampling_interval} minutes' as gap_end

            FROM
        
                (SELECT
                    generate_series( 
                        '{utc_interval.start.isoformat()}'::timestamp with time zone, 
                        '{utc_interval.end.isoformat()}'::timestamp with time zone, 
                        '{sampling_interval} minutes') 
                    as tick) 
                as clock 
            
                left outer join 
                (SELECT 
                    data_datetime 
                FROM reading 
                WHERE reading.weatherstation_id = {station_id}
                ) 
                as station_readings
                    on clock.tick = station_readings.data_datetime

            WHERE data_datetime is null

            ) as gap_finder
  
        WHERE  ( gap_end = true or gap_start = true)
        """
        logger.debug(f"Generated SQL for missing data summary: {sql_str}")
        return(sql_str)


