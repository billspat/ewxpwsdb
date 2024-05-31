# Enviroweather (EWX) Personal Weather Station (PWS) Database (DB): ewxpwsdb

This package is to support the Personal Weather Station project of the https://enviroweather.msu.edu project.  

This is v2 or reconfiguration of previous packages to better combine classes to collect and harmonize data from diverse weather station vendor APIs, 
SQL database of weather stations and readings, data collection orchestration/workflow, and an API wrapper around all of these function with type-checked code.  

This package is under heavy development and in transition from previous version. 

More details about how to use the package as well as how to contribute to it's development is coming. 

## Developers

The package uses Python 'poetry' rather than standard setup tools.  Poetry suggests installing in a virtual environment, however it already creates a virtual environment for this package. 

### Using with Poetry

Instructions TBD.  Requires installing pipx as recommend by https://python-poetry.org  which may or may not work on Windows


### Developing with PIP/setup tools

There is a requirements.txt file that could work to develop with this package.   
This method worked for me on MacOS using terminal 

change into the top directory of this project.  (e.g. `cd /path/to/ewxpwsdb`)

Create a virtual environment.  For using virtualenv, use 

`virtualenv -p 3.11 .venv` or similar.  Could also use Conda environments. the method doesn't matter.   However Poetry and pipx have their own way of using environments. 

activate the environment. With virtualenv, use `.venv/bin/activate`

install using pip

`pip install -r requirements.txt`

install this package (it may be that the above it not needed when installing the package)

`pip install .`

### Getting test data

There is a test bed of weather stations for which you can access the API with passwords/creentials.   It is not stored in this repository. 

Current the tests etc assume the file is `data/test_stations.tsv` and must be in Tab-separated values format due to a bug in python 3.11 `dictreader()`

Get a copy of this file and place it in that location as above.    You can override this location from most tests and programs.  

### running tests

once the package and dependencies are instasll with either poetry or pip...

When using poetry, enter the poetry 'shell' (bash environment that loads the virtual environment) with `poetry shell`

from the top folder of the project, run tests from the command line with 

`pytest tests`

Since the system is designed for Postgresql (due to requiring datetimes with timezones), testing requires access to a Postgresql Server.   This tests currently assume you are running a server
on localhost that does not require a password (e.g. [Postgres.app](https://postgresapp.com )).   If that is running, the tests create a temporary SQLite database for running tests and deletes that file when they are done.  


By default the tests only run for one station type, **SPECTRUM**.  To test against other station types, use the option 

`--station_type=STATION_TYPE`
                    
for example 

`pytest --station_type=ZENTRA tests`

To run one test

`pytest --station_type=ZENTRA tests/test_collector.py`


Custom options:

-  `--dburl=DBURL`         sqlalchemy postgresql db url for test.  This is required for the files `test_db_checks.py` but currently not properly used
-  `--file=FILE`           full path to a tsv file to use for test stations data and login credentials
-  `--no-import`           use this to skip importing data (assumes test db already has data)
- `--station_type=STATION_TYPE` mentioned above; station type in all capsTo run against other types use the following syntax


### ABOUT ZENTRA API

You will notice the terminal seems like it's frozen when working with Zentra API, e.g. when running tests.  This is annoying but expected. 

the API from the company "Meter Group" that works with the Zentra weather stations has a speed limit on the api and only allows requests once every 60s.  
That means when testing, if you want to get another reading for aonther test, you have to wait until 60s is up.  The output from the API has the number 
of seconds you have to wait, and this code has a feature to extract that and wait until it's ready.  






