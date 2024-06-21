#!/usr/bin/env python3

# cli.py: CLI for the ewxpwsdb package.  See readme for how to use

import argparse
import sys, json
from sqlmodel import select
from ewxpwsdb.collector import Collector
from ewxpwsdb.db import database
from typing import Any
from dateutil.parser import parse # type: ignore
from datetime import timedelta
from zoneinfo import ZoneInfo

from ewxpwsdb.time_intervals import UTCInterval, str_to_interval
from ewxpwsdb.station_readings import StationReadings
from ewxpwsdb.station import Station

import os.path
from dotenv import load_dotenv

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
        return(f"error when initializing database: {e}")


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
            return(f"Error getting stations from db: {e}")
    else:
        try:
            station_obj = Station.from_station_code(station_code, engine)
        except Exception as e:
            return(f"Error getting station with code '{station_code}' from db")
        
        output = station_obj.as_json()

    return(output)


def collect(db_url:str, station_code:str, start: str|None = None, end: str|None = None, show_response: bool=False)->str:
    """this will insert weather for station {station_code} for start, end dates or just current weather"""    

    engine = database.get_engine(db_url)

    try:
        collector = Collector.from_station_code(station_code, engine)
    except Exception as e:
        return f"error creating a colllector for station {station_code}: {e}"

    interval = str_to_interval(start, end)

    try:
        response_ids = collector.request_and_store_weather_data_utc(interval = interval)
        n_readings = len(collector.current_reading_ids)
        return f"stored {n_readings} readings for {station_code}"
    except Exception as e:
        return(f"error collecting weather from {station_code}:{e}")


def catchup(db_url:str, station_code:str)->str:
    """this will insert records to catch up station by station_code"""

    engine = database.get_engine(db_url)

    try:
        collector = Collector.from_station_code(station_code, engine)
    except Exception as e:
        return f"error creating a colllector for station {station_code}: {e}"
    
    try:
        response_ids = collector.catch_up()
        n_readings = len(collector.current_reading_ids)
        return f"store {n_readings} readings for {station_code}"
    except Exception as e:
        return f"error on catch-up process for station {station_code}: {e}"


def weather(db_url:str, station_code:str, start:str|None = None, end:str|None = None, show_response:bool=False)->str:
    """pull weather from api and save database. """
    
    try:
        engine = database.get_engine(db_url)
    except Exception as e:
        return f"error connecting to database: {e}"
        
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
        return f"error getting weather from {station_code} with params start={start}, end = {end}: {e}"
    
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


def hourly(db_url:str, station_code:str, start_date:str|None = None, end_date:str|None = None):
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
        
    
def main()->int:
    """Console script for ewx_pws."""
    parser = argparse.ArgumentParser(prog='ewxpws')

    subparsers = parser.add_subparsers(dest='command', required=True, help="Personal weather stations database operations")

    # all commands require a station code and a database connection to work
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument('station_code', help="station code that matches a record in the STATION table in the database.  For station command, send 'list' to list all stations")
    common_args.add_argument('-d','--db_url', help="optional sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws.  if none given, reads env var $EWXPWSDB_URL")


    initdb_parser = subparsers.add_parser("initdb", help="initialize an empty database provided with the db_url")
    initdb_parser.add_argument('-d','--db_url', help="optional sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws." )
    initdb_parser.add_argument('-f', '--station-file', default=None, help="path to a station file to import, tsv format")
    
    station_parser = subparsers.add_parser("station", parents=[common_args], help="list station info for station code. Send station code 'list' to list all stations")

    weather_parser = subparsers.add_parser("weather", parents=[common_args], help="show weather conditions for specified station and times")
    weather_parser.add_argument('--showresponse', action="store_true", help="optional flag to also show the raw API  response data")
    weather_parser.add_argument('-s', '--start', default=None, help="start time UTC in format ")
    weather_parser.add_argument('-e', '--end', default=None, help="end time UTC in format ")
    # weather_parser.set_defaults(command=show_weather)


    store_parser = subparsers.add_parser("collect", parents=[common_args], help="get data and save to database for time internval, or current time ")
    store_parser.add_argument('-s', '--start', nargs='?', help="optional start time, UTC timezone in format TBD, if omitted uses near current time")
    store_parser.add_argument('-e', '--end',nargs='?', help="optional end time, UTC timezone in format TBD, if omitted uses near current time")
    # store_parser.set_defaults(command=collect_weather)

    catchup_parser = subparsers.add_parser("catchup", parents=[common_args], help="get all data from last record to current time and save to database")
    # catchup_parser.set_defaults(command=catchup_weather)

    readings_parser = subparsers.add_parser("readings", parents=[common_args], help="retrieve weather data from database, if it's there")
    readings_parser.add_argument('-s', '--start', default=None, help="start time UTC in format ")
    readings_parser.add_argument('-e', '--end', default=None, help="end time UTC in format ")
    
    readings_parser = subparsers.add_parser("hourly", parents=[common_args], help="retriev hourly summaries from from database")
    readings_parser.add_argument('-s', '--start_date', default=None, help="start date, local time ")
    readings_parser.add_argument('-e', '--end_date', default=None, help="end date, localtime ")


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