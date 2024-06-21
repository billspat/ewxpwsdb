
from pydantic import BaseModel
from datetime import date    
    

class HourlySummary(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_

    Returns:
        _type_: _description_
    """

    station_code:str
    local_date:date
    local_hour:int

    record_count: int

    atmp_count: int
    atmp_avg_hourly: float | None 
    atmp_max_hourly: float | None
    atmp_min_hourly: float | None
    atmp_max_max_hourly: float | None
    atmp_min_min_hourly:  float | None
    
    pcpn_count:  int
    pcpn_total_hourly:  float | None

    lws_count: int
    lws_hourly:  float | None


    @classmethod
    def sql_str(cls, station_id:int, local_start_date:date, local_end_date:date, pg_timezone:str = 'est')->str:
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
            pg_timezone (str): Postgresql timezone, which are not the same as Python timezones, but are lowercase 3-letter abbreviations

        Returns:
            str: valid SQL for the schema created from the tables in this system, with ids and dates inserted, with timezone adjustments for UTC data
        """
        
        start_date_str = local_start_date.strftime("%Y-%m-%d")
        end_date_str = local_end_date.strftime("%Y-%m-%d")


        #TODO cast counts and hour number as ::int

        sql_str = f"""
            SELECT 
                station_code,
                local_date, 
                local_hour+1 as local_hour,
                SUM(CASE when atmp is not null then 1 else 0 end) as atmp_count,
                ROUND(AVG(atmp)::NUMERIC,2) as atmp_avg_hourly,
                MAX(atmp) as atmp_max_hourly,
                MIN(atmp) as atmp_min_hourly,
                MAX(atmp_max) as atmp_max_max_hourly,
                MIN(atmp_min) as atmp_min_min_hourly,
                SUM(CASE when pcpn is not null then 1 else 0 end) as pcpn_count,
                SUM(pcpn) as pcpn_total_hourly,
                SUM(CASE when lws is not null then 1 else 0 end) as lws_count,
                SUM(lws)/SUM(CASE when lws is not null then 1 else 0 end) as lws_hourly,
                COUNT(*) as record_count
            FROM (
                SELECT
                    date_trunc('day', reading.data_datetime at time zone '{pg_timezone}')::date as local_date,
                    EXTRACT(HOUR FROM reading.data_datetime at time zone '{pg_timezone}') as local_hour,
                    reading.*,
                    weatherstation.station_code as station_code

                FROM reading inner join weatherstation
                    ON reading.weatherstation_id = weatherstation.id
                
                WHERE reading.weatherstation_id = {station_id} and
                    reading.data_datetime >= timestamp '{start_date_str}' at time zone '{pg_timezone}' and
                    reading.data_datetime < timestamp '{end_date_str}' at time zone '{pg_timezone}'
                ORDER BY reading.weatherstation_id, local_date, local_hour, reading.data_datetime
                )
                AS readings_local_time
            GROUP BY station_code, local_date, local_hour
            ORDER BY station_code, local_date, local_hour
        """

        return sql_str
    
    
    
    
    
    # f"""
    #         SELECT 
    #             station_code,
    #             local_date, 
    #             local_hour+1 as local_hour,
    #             SUM(CASE when atmp is not null then 1 else 0 end) as atmp_count,
    #             ROUND(AVG(atmp)::NUMERIC,2) as atmp_avg_hourly,
    #             MAX(atmp) as atmp_max_hourly,
    #             MIN(atmp) as atmp_min_hourly,
    #             MAX(atmp_max) as atmp_max_max_hourly,
    #             MIN(atmp_min) as atmp_min_min_hourly,
    #             SUM(CASE when pcpn is not null then 1 else 0 end) as pcpn_count,
    #             SUM(pcpn) as pcpn_total_hourly,
    #             SUM(lws)/SUM(CASE when lws is not null then 1 else 0 end) as lws_0_hourly,
    #             COUNT(*) as record_count


    #         FROM (
    #             SELECT
    #                 date_trunc('day', reading.data_datetime at time zone '{pg_timezone}')::date as local_date,
    #                 EXTRACT(HOUR FROM reading.data_datetime at time zone '{pg_timezone}') as local_hour,
    #                 reading.*,
    #                 weatherstation.station_code as station_code

    #             FROM reading inner join weatherstation
    #                 ON reading.weatherstation_id = weatherstation.id
                
    #             WHERE reading.weatherstation_id = {station_id} and
    #                 reading.data_datetime >= timestamp '{start_date}' at time zone '{pg_timezone}' and
    #                 reading.data_datetime < timestamp '{end_date}' at time zone '{pg_timezone}'
    #             ORDER BY reading.weatherstation_id, local_date, local_hour, reading.data_datetime
    #             )
    #             AS readings_local_time
    #         GROUP BY station_code, local_date, local_hour
    #         ORDER BY station_code, local_date, local_hour
    #     """

