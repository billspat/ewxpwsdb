#!/usr/bin/env python
"""Console script for enviroweather personal weather station database to pull or view data. 

Example run from the command line:  
python bin/pws_collect.py EWXDAVIS01

This requires a python environment with all requirements installed """
import argparse
import sys, os, logging
from sqlmodel import select
from ewxpwsdb.collector import Collector
from ewxpwsdb.db import database # import engine, get_engine
from ewxpwsdb.db.models import WeatherStation

from pprint import pprint, pformat

def main()->int:
    """Console script for ewx_pws."""
    parser = argparse.ArgumentParser()
    parser.add_argument('station_code', nargs='?', help="station code that matches a record in the STATION table in the database.  If not given all stations codes are output")
    parser.add_argument('-d','--dburl', help="optional valid sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws.  if none given, reads from .env")
    parser.add_argument('--show_response', action="store_true", help="optional flag to also show the raw API  response data")
    
    # possible future arguments, for now just getting current weather data and displaying it
    # parser.add_argument('-s', '--start', help="start time UTC in format ")
    # parser.add_argument('-e', '--end',help="end time UTC in format ")
    # parser.add_argument('-c', '--catchup', help="get the latest weather data from station")

    # parser.add_argument('_', nargs='*')
    args = parser.parse_args()

    # create sqlalchemy engine from url or from env
    if args.dburl:
        engine = database.get_engine(args.dburl)
    else:
        engine = database.get_engine()

    # try db connection
    try:
        engine.connect()
    except Exception as e:
        print(f"could not connect engine to db url sent as param, EWXPWSDB_URL, or from local file .env: {e} ")
        return 1
    
    if not args.station_code:
        print("list of station ids:")
        print("\n".join(get_stations(engine)))
        return 0
    
    output = print_weather(station_code = args.station_code, engine = engine, show_response = args.show_response)
    if output:
        print(output)
        return 0
    else:
        return 1

def get_stations(engine):
    
    with database.Session(engine) as session:            
        stmt = select(WeatherStation)
        stations = session.exec(stmt).fetchall()
    
    # using select for only some fields in SQLAlchemy is dumb so get all fields and filter them out here
    station_codes =  [station.station_code for station in stations]
    return station_codes

def print_weather(station_code, engine, show_response=False)->str:
    import json
    from pprint import pformat
    try:
        collector = Collector.from_station_code(station_code, engine = engine)
    except ValueError as e:
        print(f"could not work with station code {station_code}: error {e}")
        return ""
    
    # get  most recent data and print it (for now) 
    output = ""
    api_responses = collector.weather_api.get_readings()
    if show_response:
        for resp in api_responses:
            json_response = json.loads(resp.response_text)
            output += pformat(json_response)

    weather_data = collector.weather_api.transform(api_responses,database = False)
    for reading in weather_data:
        output += pformat(reading)

    return output





if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
