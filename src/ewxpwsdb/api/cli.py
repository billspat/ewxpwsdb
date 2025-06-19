#!/usr/bin/env python3

# cli.py: CLI for the ewxpwsdb package.  See readme for how to use

import argparse
import sys, json
from sqlmodel import select
from ewxpwsdb.collector import Collector
from ewxpwsdb.db import database

from typing import Any
from dateutil.parser import parse # type: ignore
from datetime import timedelta, datetime, timezone
from zoneinfo import ZoneInfo

from ewxpwsdb.time_intervals import UTCInterval, str_to_interval
from ewxpwsdb.station_readings import StationReadings
from ewxpwsdb.station import Station, WeatherStationDetail


import os.path
from dotenv import load_dotenv

# Set up logging
import logging
logger = logging.getLogger(__name__)

load_dotenv()

def initdb(db_url:str, station_file:str|None=None):
    """run the init_db method, which includes importing station files, on the databas at the url. 
    Requires a databas to exist.   See the documentation for init_db() for details.

    Args:
        db_url (str): sqlalchemy database URL 
        station_file (str | None, optional): path to a file containing station info.  See . Defaults to None.

    Raises:
        FileExistsError: if station file is given but doesn't exist
    """
    
    engine = database.get_engine(db_url)
    if station_file and not os.path.exists(station_file):
        raise FileExistsError(f"can't find station file {station_file}")
    
    try:
        database.init_db(engine, station_tsv_file=station_file)
        return("database initialized")
    except Exception as e:
        raise RuntimeError(f"error when initializing database: {e}")


def station(db_url:str, station_code:str)->str:
    """pull a station record and output to JSON for a station code, excluding 
    the API connection info which may contain secrets. 
    If string is "list" sent, then return all stations as a column of station codes, 
    which may be used in a zsh or bash shell loop 
    for station in `ewxpws station list`; do ewxpws station $station; done

    Args:
        db_url (str): connection string for database
        station_code (str): unique station code for a station record, or 'list'  
            

    Returns:
        str: JSON formatted station data or column of station codes for use in shell loop
    """
    engine = database.get_engine(db_url)
    
    if station_code.upper() == 'LIST':
        try:
            station_codes = Station.all_station_codes(engine)
            # all_station_readings = [StationReadings.from_station_code(station_code, engine=engine) for station_code in station_codes]
            # station_codes_with_dates = [f"{sr.station.station_code}: {sr.first_reading_date()}" for sr in all_station_readings ]
            output = "\n".join( station_codes )
        except Exception as e:
            raise RuntimeError(f"Error getting stations from db: {e}")

    elif station_code.upper() in ['TYPE', 'TYPES']:
        from ewxpwsdb.weather_apis import STATION_TYPE_LIST as station_types
        return('\n'.join(station_types))
            
    else:
        try:
            weather_station_detail:WeatherStationDetail = WeatherStationDetail.with_detail(station_code, engine)            
            # weather_station_detail:WeatherStationDetail = station.station_with_detail(engine)
            output = weather_station_detail.model_dump_json(indent=4)
        except Exception as e:
            raise RuntimeError(f"Error getting station with code '{station_code}' from db: {e}")

    return(output)


def collect(db_url:str, station_code:str, start: str|None = None, end: str|None = None, show_response: bool=False)->str:
    """this will insert weather for station {station_code} for start, end dates or just current weather"""    

    engine = database.get_engine(db_url)

    try:
        collector = Collector.from_station_code(station_code, engine)
    except Exception as e:
        raise RuntimeError(f"error creating a collector for station {station_code}: {e}")

    interval = str_to_interval(start, end)

    try:
        response_ids = collector.request_and_store_weather_data_utc(interval = interval)
        n_readings = len(collector.current_reading_ids)
        return f"stored {n_readings} readings for {station_code}"
    except Exception as e:
        raise RuntimeError(f"error collecting weather from {station_code}: {e}")


def catchup(db_url:str, station_code:str)->str:
    """this will insert records to catch up station by station_code"""

    engine = database.get_engine(db_url)

    try:
        collector = Collector.from_station_code(station_code, engine)
    except Exception as e:
        raise RuntimeError(f"error creating a collector for station {station_code}: {e}")

    try:
        response_ids = collector.catch_up()
        n_readings = len(collector.current_reading_ids)
        return f"store {n_readings} readings for {station_code}"
    except Exception as e:
        raise RuntimeError(f"error on catch-up process for station {station_code}: {e}")


def weather(db_url:str, station_code:str, start:str|None = None, end:str|None = None, show_response:bool=False)->str:
    """pull weather from api and save database. """
    
    try:
        engine = database.get_engine(db_url)
    except Exception as e:
        raise RuntimeError(f"error connecting to database: {e}")

    try:
        collector = Collector.from_station_code(station_code, engine = engine)
    except Exception as e:
        return f"could not work with station code {station_code}: error {e}"        
    
    weather_api_output:dict[str, Any] = {}

    # parse datetimes using dateutil, not guaranteed and must have a timezone that is
    utc_interval = str_to_interval(start, end)

    try:
        api_responses = collector.weather_api.get_readings(start_datetime=utc_interval.start, end_datetime=utc_interval.end)
    except Exception as e:
        raise RuntimeError(f"error getting weather from {station_code} with params start={start}, end={end}: {e}")

    if show_response:
        responses_text = [ json.loads(resp.response_text) for resp in api_responses]
        weather_api_output['response'] = responses_text

    readings = collector.weather_api.transform(api_responses,database = False)
    if not readings:
       time_params_as_str = f"for {start} to {end}" if (start or end) else "for current time"
       return(f"no readings for {station_code} {time_params_as_str} ")

    weather_api_output['readings'] = [reading.model_dump() for reading in readings]

    return(json.dumps(weather_api_output, indent = 4, sort_keys=True, default=str)) 


def readings(db_url:str, station_code:str, start:str|None = None, end:str|None = None):
    """ pull readings from the database
    example usage: 
    ewxpws readings -s 2024-06-10T00:00+00 -e 2024-06-10T23:59+00 EWXSPECTRUM01
    """
    engine = database.get_engine(db_url)
    station_readings = StationReadings.from_station_code(station_code, engine)
    utc_interval = str_to_interval(start, end)
    readings = station_readings.readings_by_interval_utc(utc_interval)
    if readings:
        readings_dict = [reading.model_dump() for reading in readings if reading is not None]
        return(json.dumps(readings_dict, indent = 4, sort_keys=True, default=str)) 


def hourly(db_url:str, station_code:str, start_date:str|None, end_date:str|None):
    """pull hourly summary readings by date. 
       Example usage: 
       ewxpws hourly -s 2024-06-10 -e 2024-06-11 EWXSPECTRUM01
    """
    
    from datetime import date
    from ewxpwsdb.time_intervals import DateInterval
    
    engine = database.get_engine(db_url)
    station_readings = StationReadings.from_station_code(station_code, engine)
    if start_date is None and end_date is None:  
        date_interval= DateInterval(start = date.today()- timedelta(days =1), end = date.today())
    else:
        date_interval= DateInterval.from_string(start = start_date, end = end_date)  
    
    readings = station_readings.hourly_summary(local_start_date=date_interval.start, 
                                                local_end_date =date_interval.end)
    
    if readings:
        readings_dict = [reading.model_dump() for reading in readings if reading is not None]
        return(json.dumps(readings_dict, indent = 4, sort_keys=False, default=str)) 


def daily(db_url:str, station_code:str, start_date:str, end_date:str):
    """pull hourly summary readings by date. 
       Example usage: 
       ewxpws hourly -s 2024-06-10 -e 2024-06-11 EWXSPECTRUM01
    """
    
    from datetime import date
    from ewxpwsdb.time_intervals import DateInterval
    
    engine = database.get_engine(db_url)
    station_readings = StationReadings.from_station_code(station_code, engine)
    if start_date is None and end_date is None:  
        date_interval= DateInterval(start = date.today()- timedelta(days =1), end = date.today())
    else:
        date_interval= DateInterval.from_string(start = start_date, end = end_date)  
    
    readings = station_readings.daily_summary(local_start_date=date_interval.start, 
                                                local_end_date =date_interval.end)
    
    if readings:
        readings_dict = [reading.model_dump() for reading in readings if reading is not None]
        return(json.dumps(readings_dict, indent = 4, sort_keys=False, default=str))  
    
           
def startapi(db_url, host:str|None=None, port:str|None=None, ssl=False):
    """Run a uvicorn server to host the FastAPI on host:port.  Attempts to get the files for https (see ewxpws_ssl.py) and 
    if there is a problem, run http (non-secure) version only.  

    Args:
        db_url (str): SQLAlchemy URL to access database
        host (str, optional): Host IP Address passed from CLI args defaults to None which uses defaults set in start_server
        port (str, optional): port number passed from CLI args, defaults to None which uses defaults set in start_server

    """
    
    from .http_api import start_server
    start_server(db_url, host, port, use_ssl=ssl)
    return None


def main()->int:
    """Console script for ewx_pws."""
    parser = argparse.ArgumentParser(prog='ewxpws')
    
    from importlib.metadata import version
    parser.add_argument('-v', '--version', action='version', version=version('ewxpwsdb'), help="show version and exit") 

    subparsers = parser.add_subparsers(dest='command', required=True, help="Personal weather stations database operations")
    
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument('station_code', help="station code in the database STATION table. ('station list' lists stations, 'station types' list types)")
    common_args.add_argument('-d','--db_url', help="optional sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws.  if none given, reads env var $EWXPWSDB_URL")

    # To add a new command, create a function above with the command name, then add new subparser with first argument being that function name

    initdb_parser = subparsers.add_parser("initdb", help="initialize an empty database provided with the db_url")
    initdb_parser.add_argument('-d','--db_url', help="optional sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws." )
    initdb_parser.add_argument('-f', '--station-file', default=None, help="path to a station file to import, tsv format")
    
    station_parser = subparsers.add_parser("station", parents=[common_args], help="lookup station by code.  'station list' lists stations, 'station types' list types")

    weather_parser = subparsers.add_parser("weather", parents=[common_args], help="show weather conditions for specified station and times")
    weather_parser.add_argument('--show_response', action="store_true", help="optional flag to also show the raw API  response data")
    weather_parser.add_argument('-s', '--start', default=None, help="start time UTC in format YYYY-MM-DDTHH:MM:SS+ZZ example 2024-01-01T13:00:00+00")
    weather_parser.add_argument('-e', '--end', default=None, help="end time UTC in format YYYY-MM-DDTHH:MM:SS+ZZ example 2024-01-31T13:00:00+00")


    store_parser = subparsers.add_parser("collect", parents=[common_args], help="get data and save to database for time internval, or current time ")
    store_parser.add_argument('-s', '--start', nargs='?', help="optional start time, UTC timezone in format YYYY-MM-DDTHH:MM:SS+ZZ example 2024-01-31T13:00:00+00, if omitted uses near current time")
    store_parser.add_argument('-e', '--end',nargs='?', help="optional end time, UTC timezone in format YYYY-MM-DDTHH:MM:SS+ZZ example 2024-02-28T13:00:00+00, if omitted uses near current time")

    catchup_parser = subparsers.add_parser("catchup", parents=[common_args], help="get all data from last record to current time and save to database")

    readings_parser = subparsers.add_parser("readings", parents=[common_args], help="retrieve weather data from database, if it's there")
    readings_parser.add_argument('-s', '--start', default=None, help="start time UTC in format YYYY-MM-DDTHH:MM:SS+ZZ example 2024-01-31T13:00:00+00")
    readings_parser.add_argument('-e', '--end', default=None, help="end time UTC in format YYYY-MM-DDTHH:MM:SS+ZZ example 2024-02-28T13:00:00+00,")
    
    hourly_parser = subparsers.add_parser("hourly", parents=[common_args], help="retriev hourly summaries from from database")
    hourly_parser.add_argument('-s', '--start_date', default=None, help="start date, local time, ISO format YYYY-MM-DD ")
    hourly_parser.add_argument('-e', '--end_date', default=None, help="end date, localtime ISO format YYYY-MM-DD ")

    daily_parser = subparsers.add_parser("daily", parents=[common_args], help="retriev hourly summaries from from database")
    daily_parser.add_argument('-s', '--start_date', default=None, help="start date, local time ISO format YYYY-MM-DD ")
    daily_parser.add_argument('-e', '--end_date', default=None, help="end date, localtime ISO format YYYY-MM-DD")
    
    api_parser = subparsers.add_parser("startapi", help="start the API server")
    api_parser.add_argument('--port', default=8000, help="server port")
    api_parser.add_argument('--host', default='0.0.0.0', help="server host")
    api_parser.add_argument('--ssl', action=argparse.BooleanOptionalAction, default=False, help="attempt to start server with ssl, will fall back to http if SSL not configured")
    api_parser.add_argument('-d','--db_url', default=None, help=f"sqlaclchemy URL for connecting to Postgresql, if none given, reads env var ${database.default_db_env_var_name()}")


    args = parser.parse_args()
    clifunc = eval(args.command)
    params = vars(args)
    del params['command']
    output = clifunc(**params)
    if output:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
