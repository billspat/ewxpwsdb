#!/usr/bin/env python3

# ewxpwsdb.py: CLI for the ewxpwsdb package

from prettytable import PrettyTable

import argparse
import sys, os, logging, json
from sqlmodel import select
from ewxpwsdb.collector import Collector
from ewxpwsdb.db import database # import engine, get_engine
from ewxpwsdb.db.models import WeatherStation
from pprint import pprint, pformat

from dateutil.parser import parse
from dateutil import tz

from datetime import datetime



def get_station(engine, station_code:str):
    
    with database.Session(engine) as session:            
        stmt = select(WeatherStation).where(WeatherStation.station_code == station_code)
        station_record = session.exec(stmt).one()
    
    return(station_record)


def get_station_codes(engine):
    with database.Session(engine) as session:            
        stmt = select(WeatherStation)
        stations = session.exec(stmt).fetchall()
    
    # using select for only some fields in SQLAlchemy is dumb so get all fields and filter them out here
    station_codes =  [station.station_code for station in stations]
    return station_codes


def show_stations(db_url, station_code=None):
    engine = database.get_engine(db_url)
    if not station_code or station_code.upper() == 'LIST':
        try:
            stations = get_station_codes(engine)
            output = "\n".join(stations)
        except Exception as e:
            return("Error getting stations from db")
    else:
        try:
            station = get_station(engine, station_code)
            
        except Exception as e:
            return(f"Error getting station '{station_code}' from db")

        
        station_dict = station.model_dump(exclude='api_config')
        output = json.dumps(station_dict, indent = 4,sort_keys=True, default=str)
    
    return(output)


def collect_weather(db_url, station_code, start = None, end = None, show_response=False):
    return(f"this will insert weather for station {station_code} for start, end dates or just current weather")


def catchup_weather(db_url, station_code):
    return(f"this will insert records to catch up station {station_code}")


def show_weather(db_url, station_code, start = None, end = None, show_response=False)->str:
    
    try:
        engine = database.get_engine(db_url)
    except Exception as e:
        print(f"error connecting to database: {e}")

        
    try:
        collector = Collector.from_station_code(station_code, engine = engine)
    except Exception as e:
        print(f"could not work with station code {station_code}: error {e}")
        return ""
    
    output = []

    start_datetime = parse(start) if start else None
    end_datetime = parse(end) if end else None

    # note if start/end are None, then gets current weather    
    api_responses = collector.weather_api.get_readings(start_datetime=start_datetime, end_datetime=end_datetime)
    
    if show_response:
        for resp in api_responses:
            json_response = json.loads(resp.response_text)
            output.append(pformat(json_response))

    weather_data = collector.weather_api.transform(api_responses,database = False)
    if not weather_data:
        output.append(f"no data for {station_code}")

    for reading in weather_data:
        reading_dict = reading.model_dump()
        output.append(json.dumps(reading_dict, indent = 4,sort_keys=True, default=str))

    return ",\n".join(output)


def main()->int:
    """Console script for ewx_pws."""
    parser = argparse.ArgumentParser(prog='ewxpwsdb')
    subparsers = parser.add_subparsers(title="subcommands", help="Personal weather stations database operations")

    # all commands require a station code and a database connection to work
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument('station_code', help="station code that matches a record in the STATION table in the database.  If not given all stations codes are output")
    common_args.add_argument('-d','--db_url', help="optional sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws.  if none given, reads env var $EWXPWSDB_URL")


    station_parser = subparsers.add_parser("station", parents=[common_args], help="list station info for station code. Send station code 'list' to list all stations")
    station_parser.set_defaults(func=show_stations)


    weather_parser = subparsers.add_parser("weather", parents=[common_args], help="show weather conditions for specified station and times")
    weather_parser.add_argument('--show_response', action="store_true", help="optional flag to also show the raw API  response data")
    weather_parser.add_argument('-s', '--start', default=None, help="start time UTC in format ")
    weather_parser.add_argument('-e', '--end', default=None, help="end time UTC in format ")
    weather_parser.set_defaults(func=show_weather)


    store_parser = subparsers.add_parser("collect", parents=[common_args], help="get data and save to database for time internval, or current time ")
    store_parser.add_argument('-s', '--start', nargs='?', help="optional start time, UTC timezone in format TBD, if omitted uses near current time")
    store_parser.add_argument('-e', '--end',nargs='?', help="optional end time, UTC timezone in format TBD, if omitted uses near current time")
    store_parser.set_defaults(func=collect_weather)

    catchup_parser = subparsers.add_parser("catchup", parents=[common_args], help="get all data from last record to current time and save to database")
    catchup_parser.set_defaults(func=catchup_weather)

    
    args = parser.parse_args()
    clifunc = args.func
    params = vars(args)
    del params['func']
    output = clifunc(**params)
    if output:
        print(output)

    return 0




if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover