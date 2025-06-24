# Enviroweather (EWX) Personal Weather Station (PWS) Database (DB): ewxpwsdb

This package is to support the Personal Weather Station project of the https://enviroweather.msu.edu project.  

This is v2 or reconfiguration of previous packages to better combine classes to collect and harmonize data from diverse weather station vendor APIs, 
SQL database of weather stations and readings, data collection orchestration/workflow, and an API wrapper around all of these function with type-checked code.  

This package is under heavy development and in transition from previous version. 

More details about how to use the package as well as how to contribute to it's development is coming. 

## Developers

The package uses Python 'poetry' rather than standard setup tools.  Poetry suggests installing in a virtual environment, however it already creates a virtual environment for this package. 

### Using with Poetry

Poetry is a great package-development system  for adding/removing dependencies, dev/test, running commands and building multiple architectures targets.  
this project has chosen Poetry as the development system, and most of the insructions below assume you have it installed.  

To use poetry it must be available system-wide (e.g. run on your computer without starting a new environment) but it's extremely important that you use environments for 
this and other python projects on your computer.  

A recommend way is to install with `pipx`, which won't affect the python your system uses and sometimes requires (MacOS, Linux).  See https://python-poetry.org  

However this may mean installing an Operating system package manager - yet another install!   On MacOS , Homebrew is highly recommended and that works well with poetry. 

Command Line instructions:

1. install the OS package manager:  MacOS:  homebrew; Windows: [scoop](https://scoop.sh/), Linux: none needed
2. install pipx: see https://pipx.pypa.io/stable/
3. install poetry: `pipx install poetry`  https://python-poetry.org/docs/

#### Alternative Install of Poetry: 

 see https://python-poetry.org/docs/#installing-with-the-official-installer : but on windows requires using the [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) 


### Developing with PIP/setup tools

~~There is a requirements.txt file that could work to develop with this package.~~
~~This method worked for me on MacOS using terminal~~ 

~~change into the top directory of this project.  (e.g. `cd /path/to/ewxpwsdb`)~~

~~Create a virtual environment.  For using virtualenv, use ~~

~~`virtualenv -p 3.11 .venv` or similar.  Could also use Conda environments. the method doesn't matter. However Poetry and pipx have their own way of using environments. ~~

~~activate the environment. With virtualenv, use `.venv/bin/activate`~~

~~install using pip~~

~~`pip install -r requirements.txt`~~

~~install this package (it may be that the above it not needed when installing the package)~~

~~`pip install .`~~

### Install dependencies for dev

- cd to the folder with this project `cd path/to/ewxpwsdb` if you aren't in the top directory already 
- `poetry install`



### Install Postgresql

Because not all databases allow the use of timezones, and this system requires timezones, we have opted to use Postgresql.   
You must have a Postgresql db server with a database in it for which you have the priv. of creating databases for the tests to work.  

On Mac, [Postgres.app](https://postgres.app) is a super easy way to install.   Once you start the db and create a database, say, `ewxpws` for the 
database name, your database URL is EWXPWSDB_URL=postgresql+psycopg2://localhost:5432/ewxpws

On Windows etc you can isntall using the default postgresql installer.   Create  user, password and new database, maybe named `ewxpws` 

### Setting the environment

You can use a file to set the database URL so you don't type passwords on the command line.   

create a new file named `.env` in the top directory of this project.  Python will look for and read this file for environment variables.   

see the file `example-dot-env` for what should go in into it.   Currently the default environment variable uses is set in the module 
`ewxpwsdb.database._EWXPWSDB_URL_VAR, currently "EWXPWSDB_URL" but most functions
and cli will take a `db_url` parameters will override that  (e.g. for a test URL or a dev URL)

## Testing

### Getting test data

There is a test bed of weather stations for which you can access the API with passwords/creentials.   It is not stored in this repository since it contains
passwords and secrets to access the stations' APIs.  

Current the tests etc assume the file is `data/test_stations.tsv` and must be in Tab-separated values format due to a bug in python 3.11 `dictreader()`

Get a copy of this file and place it in that location as above.    You can override this location from most tests and programs.  

There is a function in `init_db()` in `database.py` that will create a new blank databas and load the test stations into it.  

### running tests

once the package and dependencies, database and files are all in place, you can now run tests.   

`poetry run pytest tests`

When using poetry, you can also enter the poetry 'shell' (bash environment that loads the virtual environment) with `poetry shell`, 
akin to activating an environment.   If you do that, from the top folder of the project, run tests from the command line with 

`pytest tests`

Note that these tests, by default, will use the Postgresql URL to access the database server, but then will create a new, temporary database
on that server and fill with test data.   When the tests complete the test database is deleted. 
on localhost that does not require a password (e.g. [Postgres.app](https://postgresapp.com )).   If that is running, the tests create a temporary SQLite database for running tests and deletes that file when they are done.  

By default the tests only run for one station type, **SPECTRUM**.  To test against other station types, use the option 

`--station_type=STATION_TYPE`
                    
for example 

`pytest --station_type=ZENTRA tests`

To run one test:

`pytest --station_type=ZENTRA tests/test_collector.py`

To run all tests for all station types, use the CLI (see below):

```
poetry shell
for TYPE in `ewxpws station types`; do 
   pytest tests --station_type=$TYPE
done
```


#### Test options.  

Run  `pytest tests -h` and see the **Custom options** section in the output for lastest options and details. 

-  `--dburl=DBURL`         sqlalchemy postgresql db url for test.  If you send a URL like this, it will not create a temporary database 
-  `--file=FILE`           full path to a tsv file to use for test stations data and login credentials
-  `--no-import`           use this to skip importing data (assumes test db already has data)
- `--station_type=STATION_TYPE` mentioned above; station type in all caps.  If there is more than one station of that type in the db, picks the first one. 


#### Problems reading environment (Windows) 

There are times when the test system (and the CLI) are not reading the .env file or the environment and the tests will not run with a database not found problem. 

As a work around, use the command line above to specify a database and an admin user  (does not have to be 'postgres' ). 
In addition, you may have to use poetry shell to run them.  When using a dbURL it will use the database you suggest 

1. create a new database on your db host (e.g. local host) and record the admin user id and password 
2. optionally create a new database to use for testing, for example ewxpwstest May or may not have data in it.  

example run: 

poetry run pytest tests --dburl="postgresql+psycopg2://adminuser:adminpassword@localhost/ewxpwstest



### About API Throttling

You will notice the terminal seems like it's frozen when working with Zentra API, e.g. when running tests.  This is annoying but expected. 

the API from the company "Meter Group" that works with the Zentra weather stations has a speed limit on the api and only allows requests once every 60s.  
That means when testing, if you want to get another reading for aonther test, you have to wait until 60s is up.  The output from the API has the number 
of seconds you have to wait, and this code has a feature to extract that and wait until it's ready. 

The DAVIS api is also a little slow and will only allow getting data for 24 at a time

## Installing a test package

If you would to test how this package would install using pip, you can do the following

from the top directory: 

1. poetry build
2. pip install -e .

Then the CLI described below can be used on your system without starting Poetry first

## Using the CLI

There is a command line interface for working with the database and APIs using the terminal/command.exe.    

Until the package is actually installable via PIP, you have to use `poetry` to use the cli.   For all the following examples, you must be in
the top directory of this project (e.g. first `cd path/to/ewxpws` if you aren't already).  

The cli command is `ewxpws` 

- get help/information about the arguments:   `poetry run ewxpws -h`
- get details about a sub command `poetry run ewxpws station -h`
- list all stations `poetry run ewxpws station list`
- get current weather details, directly from API `poetry run ewxpws weather {station code}`
- get recent hourly weather summary from database `poetry run ewxpws hourly {station code}`

For many of these commands there are options for `--start` and `--stop` to get a range of data. For hourly data these are dates in form Y-M-D `2024-04-30`

## API

There is a Web API (not necessarily REST but read-only) as well. 

## Starting

To start the API server on your local computer you can use the command line script

`poetry run ewxpws startapi -d <database_url>`

which runs on host address http://0.0.0.0:8000 but the host IP and the port address can be overrided.  
The server can be run using ssl using local cert and key files,  with `--ssl` option (off by default). 

To use `https` SSL, you must create cert and key file, place them on disk where the server has access, and add the files paths 
to the `.env` file.  See the `example_dot_env` file at the top of this repository for the names of the variables.   If you use self-signed   

This does not run as a dev server with reload, see below for that. 

If you have set up the .env file as described above, you don't need the `-d` parameter but may use it to override .env settings

### Starting a dev api server

Those used to developing with FastAPI can start a FastAPI dev server, set the database variable in .env, and run

`poetry run fastapi dev src/ewxpwsdb/api/http_api.py`  

this will auto-reload as code changes.  

To run with a different database for example on a different server, add the URL to the environment (different for Mac/Windows). 
For example if you set the environment variable `EWXPWSDB_AWS_URL` to the URL for a database on AWS, to use that databas, run 

```shell
source .env
EWXPWSDB_URL=$EWXPWSDB_AWS_URL; poetry run fastapi dev src/ewxpwsdb/api/http_api.py
```

### Using the API

Once the server is running, the default local parameters for the API server host and port, browse to http://0.0.0.0:8000/docs for documentation about the api.  

There are several other routes available.  For example `http://0.0.0.0:8000/stations` is a list of station codes.  All data is output in JSON format.  



## Docker

This includes a simplistic `Dockerfile` to run the API server for giving out the data.  It 
copies all files (including `/data` which is not needed except to init the db).  

### Building

To build a new image (which has the architecture of the CPU on your computer, e.g. Intel for windows and ARM aka aarch for Mac), use

`TAG=v0; docker buildx build -t ewxpwsdb:$TAG .`

see the command below to run the api server using the container.  You can't use a db url with 'localhost' since that's not local to docke.   And change the TAG (v0) to the tag used to build the container

### Running Docker

The dockerfile does run but currently the server ("uvicorn") has a logging error and does not log properly (6/2024) 
One the server, or locally, create a new .env file to support docker with an exteral db url and cert locations, for example docker.env 

`docker run -d --env-file=docker.env -p 80:80 ewxpwsdb:v0`

The command attempts to use ssl.  If you've create .pem files for SSL and included them into the docker build, then open 
then in your browser open https://localhost/docs to see the API docs, otherwise use `http`


If you would like to use a different URL than the database usd for dev/test, add it to the .env file, for example

*example .env contents:*

```shell
EWXPWSDB_URL=postgresql+psycopg2://localhost:5432/ewxpws
EWXPWSDB_DOCKER_URL=postgresql+psycopg2://ewxuser:****nTgoX****@ewxpwsdev-db.etc.us-east-1.rds.amazonaws.com:5432/ewxpws
```

Three ways to use environment variables.  Source file to environment and explicitly 
set with `-e`, or with a local .env file like this with `--end-file=`

```shell
source .env; docker run -d --env-file=docker.env  -e EWXPWSDB_URL=$EWXPWSDB_DOCKER_URL  -p 80:80 ewxpwsdb:v0
```

On a Linux server, store the env file where it's accessible by systemd, for example

```shell
export TAG=0.1.2
docker run --rm --name testapiserver --env-file=/etc/.pwsapienv -p 8000:8000 ewxpwsdb:$TAG startapi --port 8000 --no-ssl
```

# Weather Station record fields and format

See [# Enviroweather Personal Weather Station API output variable definitions](./doc/ewx_pws_api_variables.md)





