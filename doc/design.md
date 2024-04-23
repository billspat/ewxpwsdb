## EWX Personal Weather Stations version Next: 

**Combine Pydantic, SQL models, API, Collector with efficient code**

This is an adaptation of the previous ewx pws efforts which build object classes for pulling data from a vendor APIs.  This new system 
does not conflate a "weather station" from a "weather station company api."

weather stations and api outputs (readings) are stored in database, but API code is part of a separate system now. 

**this doc is to collection work plan to be moved into gitlab issues and/or trello**

### *things to do/fix*
this is a running list of things to get working for this sprint: 


### database functions
- [X] init/session management and other common chores in a database.py file, 
- [X] models for tabls in models.py
- [X] use Postgresql as well as sqlite db
- [X] work with an existing db URL rather than create it every time
    - [X] OR create one as needed e.g. for testing

- [X] return True/False from initdb , test for success
- [X] convert all to tests
- [x] better session management? get the 'get_session' working instead of instantiating a Session directly to capture tha function in one place 
    - [X] better way to specify the db file to work depending on context, one for dev, prod, testing like Rails?   for testing currently uses cli param
    - [X] don't use globals! middle ground - use params with globals as defaults but overridable
    - [ ] figure out how to use yield properly for 'get_session'

*In progress:*

- [x] move previous pydantic models for readings and requests into SQLmodel
- [x] change data structures of response and readings to fit sql
- [x] re-work "weather station" classes from previoius versions to new API-focused design
    - [x] Base classes
    - [x] constants
- [x] edit station API and transform methods for new db models
    - [x] Davis
        - [x] API
        - [x] transform
    - [x] Spectrum
        - [x] API
        - [x] transform
    - [x] Onset
        - [x] API
        - [x] transform    
    - [x] Zentra
        - [x] API
        - [x] transform
    - [x] Rainwise
        - [x] API
        - [x] transform
    - [x] Locomoos
        - [x] API
        - [x] transform



- [x] debug components get transform working 
    - [x] Spectrum
    - [x] others

- [x] Davis API has changed and errors with stale time stamp. add tests for timezone conversion code 

- [x] create a collector class to combine weather stations, api, and save readings to db
    - [x] tests


 *future fixes*

 - [ ] rename WeatherStation to just Station throughout the code to make it easier to work with.  
 
 - [ ] for db/models.py: use pydantic validation for input/output data for a robust system.  here are some reminders...
 
```Python
from pydantic import field_validator
from ewxpwsdb.time_intervals import is_valid_timezone, TimeZoneStr
from ewxpwsdb.weatherstations import STATION_TYPE
# create a type for 'coordinates that enforces correct number of decimal places 
# validation on sampling_interval to be 5, 15, or 30 minutes only
```

example code to validate timezone
```Python
@field_validator('timezone')
@classmethod
def must_be_valid_timezone_key(cls,v: str) -> str:
    """ ensure timezone key is valid"""
    if is_valid_timezone(v):
        return(v)
    else:
        raise ValueError(f"timezone_key v is not a valid IANA timezone e.g. US/Eastern")

```

- [x] apply `mypy` typing validator

*documentation*

- [ ] create a diagram for the python object/class system for other developers
- [ ] create a diagram indicating data flow 


### Misc. design notes saved as we work 

**principle: can add attributes and methods that are not db-specific.   However this assumes the class _always_ works with a db.**


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



## models  # database models

    WeatherStation - physical station info, station type,  
    
    + api connect deets.  same for all station types
        consider adding 'auth_token' a per-station token needed to write any aspect of the station

    WeatherStationConfig  : 1-1 table just be a single string fields to store JSON to keep it flex. the methods for handling this config could be contained in this class
    
- [ ]WeatherAPI: 
- [ ] Readings: sensor readings by timestamp and station id, linked to 
    
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

    

## Database

- [ ] move db into aws for shared access


## Orchestration

use Prefect, looks great  https://www.prefect.io/opensource 

### local

- [ ] install on laptop to fill up db (local and or cloud)
- [ ] run jobs for few days, use 'catch-up' method to get latest data 
- [ ] run orchestrator local, database remote for shared access

### cloud
- [ ] try prefect cloud and see if free version is ok
- [ ] move to a cheap aws EC2 instance for whole pipeline ($)
- [ ] 
- [ ] upgrade EC2 as needed
- [ ] if need to scale, move to kubernetes EKS

### MSU option using ICER data machine?

this would be proof of concept only, as during maintenance 
there is no data updated for PWS, which means models can't be run effectively.  
if there is a weather event where a grower needs a model for a day, can't tolerate 8-12 hour downtime during business hours

1. n  day recurring job (n = 5, 7?)

 - [ ] run ‘server’ inside a job on a node on the data machine, runs web server
 - [ ] run a dask cluster for worker pool
 - [ ] run tasks on cluster workers.  
 - [ ] run postgresql in separate job

