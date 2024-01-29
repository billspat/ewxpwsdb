# design principle: can add attributes and methods that are not db-specific.   However this assumes the class _always_ works with a db. 


can of course pull data from stations at any time, and can read/write from database, but struggling on structure to get these things to work together properly 


## main functions:
- setup database
- read/write database 
- validate inputs and put structure on data (pydantic)
- validate configuration / connection to API
- collect data from API per station type, manage data formatting, time zones, etc
    - convert api response to standarized readings

- handle errors when reading from API and indicate problems in readings data
- retry/backfill errors when possible, 
    - estimated data 


## steps to bring life, first notebook, then tests
- db connection and table creationg
    - sqlite
    - postgresql

- import stations from csv into DB, e.g. seed ata

## database  #functions
    init/session management
    async query etc
    common chores



## models  # database models

    WeatherStation - physical station info, station type,  + api connect deets.  same for all station types
        consider adding 'auth_token' a per-station token needed to write any aspect of the station

    WeatherStationConfig  : 1-1 table just be a single string fields to store JSON to keep it flex. the methods for handling this config could be contained in this class
    Readings
        sensor readings by timestamp and station id, linked to 
    
    Requests # reading_events, accesses to APIs, timestamps, unprocessed response data

    Users # method for mimicing EWX usesr accounts 

    Notifications


## weatherstations == vendor api access

    # this folder is all about working with the station vendor cloud apis per station type

    weather_station_api_config - NOT a db table, just pydantic model
        reads and validates from json in weatherstation table
        subclassed by station type  davis_config, etc
        methods for validation and testing

    readings - this should be almost exactly the same as the db folder readings, but that's a lot of duplication.  maybe could just use the same 

    weather_api # _not_ a station, but an API
        parameters:  weather_station

## api

    # methods for reading from database
    app.py # models_and_routes, can be brokenup later.   This is how others get data from here and update station list

## collector

    ewxpws.py 

## lib

    time_intervals
    notification 

    






WeatherStation Table?
    = db table, fields common to all stations, physical attributes
    id (db, 
    station_type
    location lat, lon
    location_description
    station_name

    station_id (uniqu assigned code)
    owner_id
    install_date
    updated
    previous_station_id
    record_created
    record_updated
    notes:text
    last_known_status: string
    api_config_json: string, valid json

    table_name: weather_stations


    parse_config(self):
        station_config_type = ConfigTypes[self.station_type]
        api_config_dict = 
        config_dict = station_config_type.load(self.api_config_json)


WeatherStationAPI
    all the current methods in weather station class to get API data
    assigned to a weather station, but it's NOT A DB FIELD, it's a collection of methods

DavisStation -inherits from weather station




