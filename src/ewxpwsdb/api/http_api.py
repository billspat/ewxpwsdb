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

from ewxpwsdb.db.models import WeatherStation, Reading
from ewxpwsdb.db.summary_models import HourlySummary
from ewxpwsdb.station_readings import StationReadings
from ewxpwsdb.station import Station
from ewxpwsdb.collector import Collector

from ewxpwsdb.db.database import get_engine, check_engine
from ewxpwsdb.time_intervals import str_to_interval, UTCInterval, DateInterval


_version = 0.1

# set the db url in environment when not running with main, see db.database.py for details
# this is overwritten by args -- see below
engine = get_engine()

app = FastAPI()

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
def station_info(station_code:str)->WeatherStation:
    try:
        station_obj = Station.from_station_code(station_code, engine)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="station_code not found")
    except Exception as e:
        raise HTTPException(status_code=503, detail="error with connection {e}")
    
    return(station_obj.as_dict())


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
    
    
if __name__ == "__main__":
    
    # used in the help strings
    from ewxpwsdb.db.database import _EWXPWSDB_URL_VAR as default_db_env_var_name
    
    """starts the recommended http server with arguments """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default=8000, help="server port")
    parser.add_argument('--host', default='0.0.0.0', help="server host")
    parser.add_argument('-d','--db_url', default=None, help=f"sqlaclchemy URL for connecting to Postgresql, if none given, reads env var ${default_db_env_var_name}")

    args = parser.parse_args()

    engine = get_engine(db_url=args.db_url)
    if not check_engine(engine):
        raise RuntimeError(f"invalid database connection for engine {engine}")
    
    uvicorn.run(app, 
                host=(args.host or '0.0.0.0'), 
                port=(args.port or 8000)
                )




