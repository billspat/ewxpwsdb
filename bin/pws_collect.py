#!/usr/bin/env python
"""Console script for enviroweather personal weather station database to pull or view data. 

Example run from the command line:  
python bin/pws_collect.py EWXDAVIS01

This requires a python environment with all requirements installed """
import argparse
import sys, os, logging
from ewxpwsdb.collector import Collector
from ewxpwsdb.db import database # import engine, get_engine

def main()->int:
    """Console script for ewx_pws."""
    parser = argparse.ArgumentParser()
    parser.add_argument('station_code', help="station code that matches a record in the STATION table in the database")
    parser.add_argument('-d','--dburl', help="optional valid sqlaclchemy URL for connecting to Postgresql, eg. postgresql+psycopg2://localhost:5432/ewxpws.  if none given, reads from .env")
    
    # possible future arguments, for now just getting current weather data and displaying it
    # parser.add_argument('command', help="optional command, defaults to getting recent weather from last 15 minutes ")
    # parser.add_argument('-s', '--start', help="start time UTC in format ")
    # parser.add_argument('-e', '--end',help="end time UTC in format ")
    # parser.add_argument('-c', '--catchup', help="get the latest weather data from station")

    # parser.add_argument('_', nargs='*')
    args = parser.parse_args()

    # create sqlalchemy engine from url or from env
    if args.dburl:
        engine = database.get_engine(args.dburl)
    else:
        engine = database.engine

    # try db connection
    try:
        engine.connect()
    except Exception as e:
        print(f"could not connect engine to db url sent as param, EWXPWSDB_URL, or from local file .env: {e} ")
        return 1
    

    # create collector object which reads station info from database
    # just get a weather API object
    try:
        collector = Collector.from_station_code(args.station_code)
    except ValueError as e:
        print("could not work with station code {station_code}: error {e}")
        return 1
    
    # get  most recent data and print it (for now) 

    api_response = collector.weather_api.get_readings()
    weather_data = collector.weather_api.transform(api_response,database = False)
    for reading in weather_data:
        print(reading)

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
