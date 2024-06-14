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

from ewxpwsdb.time_intervals import UTCInterval
from ewxpwsdb.station_readings import StationReadings
from ewxpwsdb.station import Station


def create_interval(start:str|None, end:str|None)->UTCInterval:
    """parse params into datetimes and create UTC interval. Strings must have timezone.
     
    When start, end, or both are missing, create a 60 minute interval to work with
    using what was sent 
    """

    try:
        start_datetime = parse(start) if start else None # type: ignore
        end_datetime = parse(end) if end else None       # type: ignore
    except Exception as e:
        raise ValueError(f"error parsing start={start} or end={end}: {e}")
    
    if start_datetime is None and end_datetime is None:
        # no times: create interval of previous 60 minutes
        interval =  UTCInterval.previous_interval(delta_mins=60)

    elif start_datetime is None:
        # no start: create 60 minute interval that ends at end time sent
        interval =  UTCInterval.previous_interval(dtm = end_datetime - timedelta(minutes=60), delta_mins=60)

    elif end_datetime is None:
        # no end: create 60 minute interval that starts at start time sent
        interval =  UTCInterval.previous_interval(dtm = start_datetime, delta_mins=60)

    else:
        try:
            interval = UTCInterval(start = start_datetime, end = end_datetime)
        except Exception as e:
            raise ValueError(f"error creating time interval from start={start} to end={end}: {e}")

    return interval


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
            output = "\n".join(station_codes)
        except Exception as e:
            return("Error getting stations from db: {e}")
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

    interval = create_interval(start, end)

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
    try:
        start_datetime = parse(start) if start else None # type: ignore
        end_datetime = parse(end) if end else None       # type: ignore
    except Exception as e:
        return f"error with start={start} or end={end}: {e}"

    # note if start/end are None, then "get_readings()" gets current weather    
    try:
        api_responses = collector.weather_api.get_readings(start_datetime=start_datetime, end_datetime=end_datetime)
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
    """ pull readings from the database"""
    engine = database.get_engine(db_url)
    station_readings = StationReadings.from_station_code(station_code, engine)
    interval = create_interval(start, end)
    readings = station_readings.readings_by_interval_utc(interval)
    readings_dict = [reading.model_dump() for reading in readings]
    return(json.dumps(readings_dict, indent = 4, sort_keys=True, default=str)) 


def main()->int:
    """Console script for ewx_pws."""
    parser = argparse.ArgumentParser(prog='ewxpwsdb')

    subparsers = parser.add_subparsers(dest='command', required=True, help="Personal weather stations database operations")

    # all commands require a station code and a database connection to work
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument('station_code', help="station code that matches a record in the STATION table in the database.  If not given all stations codes are output")
    common_args.add_argument('-d','--db_url', help="optional sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws.  if none given, reads env var $EWXPWSDB_URL")


    station_parser = subparsers.add_parser("station", parents=[common_args], help="list station info for station code. Send station code 'list' to list all stations")
    # station_parser.set_defaults(command=show_stations)


    weather_parser = subparsers.add_parser("weather", parents=[common_args], help="show weather conditions for specified station and times")
    weather_parser.add_argument('--show_response', action="store_true", help="optional flag to also show the raw API  response data")
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