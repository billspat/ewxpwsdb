
"""data models for hourly and daily statistics generated from the EWX PWS database.   Models classes include the sql to generate the statistics"""
from pydantic import BaseModel, Field
from datetime import date    
from sqlmodel import Session   
from typing import Self

from datetime import tzinfo
from zoneinfo import ZoneInfo
from ewxpwsdb.time_intervals import DateInterval

class HourlySummary(BaseModel):
    """data model for the hourly summary statistics from EWX PWS database, 
    and the sql that can create this data from the database. 
    """

    station_code:str
    year:int
    day:int|str|None|date
    represented_date:date = Field(examples = ['2024-06-25'], description = "date of the reading for the station's timezone")
    represented_hour:int
    record_count: int

    atmp_count: int
    atmp_avg_hourly: float | None 
    atmp_max_hourly: float | None
    atmp_min_hourly: float | None
    atmp_max_max_hourly: float | None
    atmp_min_min_hourly:  float | None
    
    relh_avg_hourly: float | None
    
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
    def sql_str(cls, station_id:int, local_start_date:date, local_end_date:date)->str:
        """create the postgresql-compatible SQL for summarizing data in the database.   
        This method exists as it was easier to write as SQLModel documentation is lacking
        and SQLAlchemy is hard to learn and debug. 
        
        The inputs are in local time, not UTC, for user convenience.   
                
        
        This is hear to be near to the dataclass-type model itself so the fields correspond.
        
        Args:
            station_id (int): database id number of a station, 
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
                SUM(CASE when atmp is not null then 1 else 0 end) as atmp_count,
                ROUND(AVG(atmp)::NUMERIC,2) as atmp_avg_hourly,
                MAX(atmp) as atmp_max_hourly,
                MIN(atmp) as atmp_min_hourly,
                MAX(atmp_max) as atmp_max_max_hourly,
                MIN(atmp_min) as atmp_min_min_hourly,
                
                ROUND(AVG(relh)::NUMERIC, 2) as relh_avg_hourly,
                
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
                ROUND(MAX(wspd_max)::numeric, 2) as wspd_max_hourly,
                
                COUNT(*) as record_count
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
                
                WHERE reading.weatherstation_id = {station_id} and
                    (reading.data_datetime at time zone weatherstation.timezone)::date >= '{start_date_str}'  and
                    (reading.data_datetime at time zone weatherstation.timezone)::date <= '{end_date_str}' 
                
                ORDER BY reading.weatherstation_id, local_date, local_hour, reading.data_datetime
                )
                AS readings_local_time
            GROUP BY station_code, local_date, local_hour
            ORDER BY station_code, local_date, local_hour
        """

        return sql_str
    
    @classmethod
    def select_hourly_summaries(cls, engine, station_id, local_start_date=None, local_end_date=None)->list[Self]:
        
        sql_str = cls.sql_str(station_id=station_id, local_start_date= local_start_date, 
                                        local_end_date = local_end_date)
        
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
    
    atmp_count: int
    atmp_avg_daily: float | None 
    atmp_max_daily: float | None
    atmp_min_daily: float | None
    atmp_max_max_daily: float | None
    atmp_min_min_daily:  float | None
    
    pcpn_count:  int
    pcpn_total_daily:  float | None

    lws_count: int
    lws_daily:  float | None


    @classmethod
    def sql_str(cls, station_id:int, local_start_date:date, local_end_date:date)->str:
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


        #TODO cast counts and hour number as ::int

        sql_str = f"""
            SELECT 
                station_code,
                local_date as represented_date, 
                SUM(CASE when atmp is not null then 1 else 0 end) as atmp_count,
                ROUND(AVG(atmp)::NUMERIC,2) as atmp_avg_daily,
                MAX(atmp) as atmp_max_daily,
                MIN(atmp) as atmp_min_daily,
                MAX(atmp_max) as atmp_max_max_daily,
                MIN(atmp_min) as atmp_min_min_daily,
                SUM(CASE when pcpn is not null then 1 else 0 end) as pcpn_count,
                SUM(pcpn) as pcpn_total_daily,
                SUM(CASE when lws is not null then 1 else 0 end) as lws_count,
                SUM(lws)/SUM(CASE when lws is not null then 1 else 0 end) as lws_daily,
                COUNT(*) as record_count
            FROM (
                SELECT
                    (reading.data_datetime at time zone weatherstation.timezone)::date as local_date,
                    EXTRACT(HOUR FROM reading.data_datetime at time zone weatherstation.timezone) as local_hour,

    
                    date_trunc('year', reading.data_datetime at time zone weatherstation.timezone) as `year`,
                    reading.*,
                    weatherstation.station_code as station_code

                FROM reading inner join weatherstation
                    ON reading.weatherstation_id = weatherstation.id
                
                WHERE reading.weatherstation_id = {station_id} and
                    (reading.data_datetime at time zone weatherstation.timezone')::date >= '{start_date_str}'  and
                    (reading.data_datetime at time zone weatherstation.timezone)::date <= '{end_date_str}' 
                ORDER BY reading.weatherstation_id, local_date, reading.data_datetime
                )
                AS readings_local_time
            GROUP BY station_code, local_date
            ORDER BY station_code, local_date
        """
        
        #date_trunc('day', reading.data_datetime at time zone '{pg_timezone}')::date as local_date,

        return sql_str


