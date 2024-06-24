"""Enviroweather Personal Weatherstation Database API"""
# saved notes about dates and datetimes
#
# while in dev, some routes may require a timezone aware datetime ojbect
# the parameter would look like
# http://localhost:8000/weather/EWXDAVIS01/readings?start=2024-06-10T12:00:00Z&end=2024-06-14T12:00:00Z
# currently in progress is providing only full-day output
# 

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Depends
from datetime import date, datetime
from typing import Annotated, Any

from ewxpwsdb.db.models import Reading
from ewxpwsdb.db.summary_models import HourlySummary, DailySummary
from ewxpwsdb.station_readings import StationReadings
from ewxpwsdb.station import Station, WeatherStationDetail
from ewxpwsdb.collector import Collector
from ewxpwsdb.db.database import get_engine, check_engine,default_db_env_var_name, get_db_url
from ewxpwsdb.time_intervals import str_to_interval, UTCInterval, DateInterval


# set the db url in environment when not running with main, see db.database.py for details
# this is overwritten by args -- see below

_version = 0.1
global engine
engine = get_engine(get_db_url())
if not check_engine(engine):
    raise RuntimeError(f"invalid database connection for engine {engine}")

app = FastAPI(title="EWX PWS DB", description="Read-only access to Enviroweather Personal Weather Station data", version='0.1')

from .ewxpws_ssl import *
    
def version():
    return(_version)

def date_pattern()->str:
    return "^20[0-9][0-9]-[0-9]{1,2}-[0-9]{1,2}$"

@app.get("/")
def home():
    return(f"Personal Weather Station Project, {_version}")


@app.get("/stations/")
def station_list():
    try:
        station_codes = Station.all_station_codes(engine)
        return({'station_codes': station_codes})
    except Exception as e:
        raise HTTPException(status_code = 503, detail = f"connection error {e}")


@app.get("/stations/{station_code}")
def station_info(station_code:str)->WeatherStationDetail:
    try:
        station = Station.from_station_code(station_code, engine)
        if station:
            station_dict_with_detail = station.station_dict_with_detail(engine)
        else:
            raise HTTPException(status_code=404, detail="station_code not found")   
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail="station_code not found")
    except Exception as e:
        raise HTTPException(status_code=503, detail="error with connection {e}")
    
    return WeatherStationDetail(**station_dict_with_detail)


# TODO: do not require timezones, and add the timezone for the station, and then convert to UTC
@app.get("/weather/{station_code}/api")
def station_api_weather(station_code:str, 
                        start:Annotated[str|None, 
                                        Query(description="earliest timestamp to include, must be full timestamps with a UTC timezone indicator",
                                              examples=['2024-05-01T06:00+05:00']
                                              )
                                        ]=None, 
                        end:Annotated[str|None, 
                                        Query(description="start/end must be full timestamps with a UTC timezone indicator",
                                              examples=['2024-05-01T10:00+05:00']
                                              )
                                        ]=None, 
                        ) -> list[Reading|None]:
    """get weather data directly from the cloud API of the station's cloud data source, transformed to EWX PWS format.  
    Does not store anything in the database, simply pulls from the station vendor's cloud API, transforms, and presents it here.  
    ID values are 'null' because these are not database records. 
    
    start/end must be full timestamps with a timezone indicator: 2024-05-01T06:00+05:00)
    """
    
    try:
        collector = Collector.from_station_code(station_code, engine = engine)
    except Exception as e:
        raise HTTPException(status_code=404, detail="fcould not work with station code {station_code}: error {e}"   )
    
    try:        
        # this function uses some default timestamps if none are given        
        utc_interval =  str_to_interval(start = start, end = end)
    except ValueError as e: 
        raise HTTPException(status_code=400, detail = "incorrectly formatted start or end parameters: {e}".format(e=e))

    try:
        api_responses = collector.weather_api.get_readings(start_datetime=utc_interval.start, end_datetime=utc_interval.end)
    except Exception as e:
        time_params_as_str = f"for {start} to {end}" if (start or end) else "for current time"
        raise HTTPException(status_code=404, detail= f"error getting response from {station_code} {time_params_as_str} ")
        
    readings = collector.weather_api.transform(api_responses,database = False)
    
    if not readings:
        time_params_as_str = f"for {start} to {end}" if (start or end) else "for current time"
        raise HTTPException(status_code=404, detail= f"no readings for {station_code} {time_params_as_str} ")
    else:
        return(readings) 


# TODO: input param formats and requirements of UTCInterval are incompatible  date -> datetime w/timezone.  
@app.get("/weather/{station_code}/readings")
def station_db_weather(station_code:str, 
                        start : Annotated[date, 
                                Query(
                                description="first day in range, in YYYY-MM-DD format")], 
                         end : Annotated[date, 
                                Query(
                                description="end of range day past end of range ( not inclusive), in YYYY-MM-DD format")], 
                       ) -> list[Reading|None]:
    """Get weather readings (unsummarized) for this station from the PWS database during the date range specified.  The time returned is UTC timezone.
    """

    try:
        station_readings = StationReadings.from_station_code(station_code, engine)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="station_code not found {e}".format(e = e))
    except Exception as e:
        raise HTTPException(status_code=503, detail="error with connection {e}".format(e = e))

    # convert string input into a date interval
    try:
        date_interval:DateInterval = DateInterval(start = start, end = end)
        #(s) start, end)
    except ValueError as e: 
        raise HTTPException(status_code=400, detail = "incorrectly formatted start or end parameters: {e}".format(e=e))
    
    try:
        readings = station_readings.readings_by_date_interval_local(dates = date_interval)  
    except Exception as e:
        raise HTTPException(status_code=503, detail="couldn't get readings from {station_code} for {start}-{end}.format(station_code = station_code, start=start,end=end)")
    
    if not readings:
        raise HTTPException(status_code=400, detail="no readings available for those dates")
    else:
        return readings


@app.get("/weather/{station_code}/hourly")
def station_hourly_weather(station_code:str, 
                       start : Annotated[date, 
                                         Query(
                                            title=" Beginning date to include",
                                            description="first day in range, local time, in YYYY-MM-DD format")] = None, 
                         end : Annotated[date, 
                                         Query(                                            
                                            title="Stop date",
                                            description="last day in range (and it's not included), local time.  For 1 day of readings, send start + 1 in YYYY-MM-DD format")] = None, 
                       ) -> list[HourlySummary]:

    """Results of the 'Hourly Summary' query of the database for the station and days provided.  In the output, the date is for the timezone of the station,
    and hour number is a cardinal number, e.g. hour 1 is summary of time 00:00 to 00:59 for that date"""
    
    try:
        station_readings = StationReadings.from_station_code(station_code, engine)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="station_code not found")
    except Exception as e:
        raise HTTPException(status_code=503, detail="error with connection {e}".format(e=e))

    try:
        date_interval = DateInterval(start = start, end = end)
    except ValueError as e: 
        raise HTTPException(status_code=400, detail = "incorrectly formatted start or end parameters: {e}".format(e=e))
    
    try:
        hourly_summaries = station_readings.hourly_summary(local_start_date=date_interval.start, local_end_date=date_interval.end)        
    except Exception as e:
        raise HTTPException(status_code=503, detail="couldn't get summary from {station_code} for {start}-{end}.format(station_code = station_code, start=start,end=end)")
    
    if not hourly_summaries:
        raise HTTPException(status_code=400, detail="no readings available for those dates")
    else:
        return hourly_summaries

from datetime import date, timedelta

date.today() 
@app.get("/weather/{station_code}/daily")
def station_daily_weather(station_code:str, 
                       start : Annotated[date, 
                                         Query(
                                            title=" Beginning date to include",
                                            description="first day in range, local time, in YYYY-MM-DD format",
                                            examples=['2024-06-01'])] = (date.today() - timedelta(days = 1)), 
                         end : Annotated[date, 
                                         Query(                                            
                                            title="Stop date",
                                            description="last day in range (and it's not included), local time.  For 1 day of readings, send start + 1 in YYYY-MM-DD format",
                                            examplles = ['2024-06-02'])] = date.today() , 
                       ) -> list[DailySummary]:

    try:
        station_readings = StationReadings.from_station_code(station_code, engine)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="station_code not found")
    except Exception as e:
        raise HTTPException(status_code=503, detail="error with connection {e}".format(e=e))

    try:
        date_interval = DateInterval(start = start, end = end)
    except ValueError as e: 
        raise HTTPException(status_code=400, detail = "incorrectly formatted start or end parameters: {e}".format(e=e))
    
    try:
        hourly_summaries = station_readings.daily_summary(local_start_date=date_interval.start, local_end_date=date_interval.end)        
    except Exception as e:
        raise HTTPException(status_code=503, detail="couldn't get summary from {station_code} for {start}-{end}:{e}".format(station_code = station_code, start=start,end=end, e = e))
    
    if not hourly_summaries:
        raise HTTPException(status_code=400, detail="no readings available for those dates")
    else:
        return hourly_summaries


def start_server(db_url:str, host:str|None = '0.0.0.0', port:int|str|None = '8080', use_ssl=False):
    """Run a uvicorn server to host the FastAPI on host:port.  Attempts to get the files for https (see ewxpws_ssl.py) and 
    if there is a problem, run http (non-secure) version only.

    Args:
        db_url (str): SQLAlchemy URL to access database, passed from 
        host (str, optional): _description_. Defaults to '0.0.0.0'.
        port (str, optional): _description_. Defaults to '8080'.

    Raises:
        RuntimeError: _description_
    """
    # this test will set the OS Environ with the value db_url if one is set
    # we run this here to be able to set the URL from the command line. 
    # otherwise the import server_api below will automatically attempt to create an engine and fail if there is no .env
    db_url = get_db_url(db_url)
    
    if not db_url:
        print(f"No database: You must either send database url with '--db_url', set the variable {default_db_env_var_name()}, or create a '.env' file (see readme)")
    else:
        try:
            engine = get_engine(db_url)
        except Exception as e:
            print(f"error connecting to database: {e}")
            
    if not check_engine(engine):
        raise RuntimeError(f"invalid database connection for engine {engine}")

    if not port:
        port_number = 8000
    elif isinstance(port, str):
        port_number:int = int(port)  
    else:
        port_number:int = port
        
    if host is None:
        host:str = '0.0.0.0'
        
    import uvicorn
    from .ewxpws_ssl import get_ssl_files
    
    if use_ssl:
        try:
            (cert_file_path, key_file_path) = get_ssl_files()
            uvicorn.run(app="ewxpwsdb.api.http_api:app", host=host, port=port_number, ssl_keyfile=key_file_path, ssl_certfile=cert_file_path)
            return True
        except Exception as e:
            from warnings import warn
            warn(f"SSL files not available, running without SSL:{e}")
    
    uvicorn.run("ewxpwsdb.api.http_api:app", host=host, port=port_number)
    return True

    






