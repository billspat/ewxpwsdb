# Enviroweather Personal Weather Stations Database (ewxpwsdb)

## Instructions for developers

Requirements: 

- Python 3.10 or higher installed 
- Python Poetry Package manager: https://python-poetry.org. You may have to install this for your system rather than in an virtual environment
- A local copy or access to a remote Postgresql Database server.   This has been tested with version 15 but earlier or later versions should work
- File with our test-bed weather stations information and API access secrets.  

1. Get a database server running or accessible

Install Postgresql server on your computer.  The there are functions for creating new temporary database instances. 
To install...

  - On Mac, the easiestversion for local testing https://postgresapp.com 
  - On Windows, a version for local testing, this is often e version from EDB: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
  - There are free cloud services for small database you can also try 

  For now, the code assumes this database server is running on port 5432 (the default) and that the test URL has full 
  admin access (to be able to create new, empty, temporary database instances, or schemas in postgresql terms)

  Optionally you can install any number of database SQL Gui applications.   I use beekeeper studio as it's lightweight and free.  

1. create a database instance in the server

    inside the server, create a database to hold weather readings.   This is not necessary for the tests (which create temporary db and deletes it), but useful for building a larger and persistent database.   

    To create a database in postgresql, in the terminal run

    `psql` 

    For most local, developer database installed (e.g. Postgres.app), you don't need to specify username. 

    `create database ewxpws;`

    Any database name will work (pws-testing, ewx-temp-db) but use all lower case.  Remember this db name for later. 

    Once done, exit the psql shell with  `\q`  

1. Install Poetry

   - on Mac, we use homebrew works brew install python; brew install poetry.   
   - Windows... ?
    
    you can run   poetry --help  to see if it's installed

1. clone the repo after you've been given access 

    `git clone git@gitlab.msu.edu:Enviroweather/ewxpwsdb.git`

    optionally specify a new folder 

    `git clone git@gitlab.msu.edu:Enviroweather/ewspwsdb.git ewxpwsdb_project`  # or whatever folder you like

1. go to the code directory 

   The poetry commands should be run in the project folder <br>
   `cd ewxpwsdb`  # replace if you used a different directory name

1. create a settings file for database access

    The details for accessing the database must be put into a configuration file the code can read.  A 
    standard way to do this in Python is called 'dot-env'  
     - create a new blank file at the top level direction named `.env`  (start with a dot)
     - in this file there is one line that has the Python SQLAlchemy database 'URL' for access.  
     - There is an example to view in `doc/example_dot_env.txt`  with a Postgresql URL that works with postgresql.app.   Note if the 
     database is installed to use the default username as an admin (your logged-in user name), you don't need to specify a password.   However if you are using a remote server, you will to include those things. 

     This URL includes a database name, use the same name as you used in the step "create a database instance in the server."   
     
     An example URL and variable setting in .env is `EWXPWSDB_URL=postgresql+psycopg2://localhost:5432/ewxpws` which works with Postgres.app where there is no password needed. 

     See the [PostgreSQL dialect page for SQLAlchemy](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html) for details on how to write a Postgresql URL.  The package uses the psycopg2 library to connect. 

1. use poetry to create an enviroment with all the dependencies installed

   do this in the root directory of the project

    '--no-root' means: don't also install the package itself -- not super critical but let's try it this way.   See `poetry install --help` for more info

    `poetry install --no-root`

1. get the station data

    If you are working with the Enviroweather project, contact the main devs to get a copy of the file with weather station information and secrets, which is a tab-separated value file (TSV).  Note that is must be TSV, not CSV, format due to some quoting issues and python.   There is an example in the the `/data` folder with secrets removed. 

    - copy the station csv file into the `/data` folder of this project.  
    - the default name used by the tests is `test_stations.tsv`, but there is a way to use a different name


1. to work in the terminal with the poetry virtual env, use this command 

    `poetry shell`

    this gives you a new prompt and uses the env that poetry just created.  This is very similar to virtualenv `source venv/bin/activate`

1. now you can run tests inside this shell

    `pytest tests`
    
    This will test for one type of station (SPECTRUM type by default)

    You can run tests for different station types using a command line parameter: 

    `pytest tests --station_type=DAVIS

    The station type names are defined in the file `src/ewxpwsdb/weather_apis/__init__.py`

    There is not an option to test all station types at once, but you could use the zsh shell command: 

    ```shell
    for st in 'ZENTRA', 'ONSET', 'DAVIS', 'RAINWISE', 'SPECTRUM', 'LOCOMOS'; do pytest tests --station_type=$st; done
    ```

    Note that some stations throttle access (especially Zentra/Meter group), so some tests take a veyr long time to complete

    There are other options for the tests, for example the db url to use and the location of the test station info.  You can get these 
    options using `pytest -h` in the top level directory (but this also outputs many other options for pytest)

    ```
    Custom options:
    --dburl=DBURL               sqlalchemy db url for test.  otherwise the tests create a temporary db.  Note the tests will add data
    --file=FILE                 tsv file to use for test data
    --no-import                 use this to skip importing data (assumes test db already has data)
    --echo                      enable SQL echo-ing
    --station_type=STATION_TYPE station type in all caps
    ```



1. Build the package 

    The command for installing things with Poetry will also install the package.  If you make changes to the code, you can rebuild the package with `poetry build` in the top level directory. 

1. Using VS Code

    After opening this folder in vscode, select the environment that poetry created (with the install command), by using the command prompt (on mac is shift+command+p)  and search for  "python select interpreter..."

    it should pick the poetry env for you, but if not, you can identify poetry environments by the folder, which are somewhere in your home directory, but inside a folder that looks like `pypoetry/virtualenvs/ewxpwsdb....`

    Note that you can use the terminal in VS Code to run python

1. Explore the python notebooks

    in the `/doc` folder are several notebooks (`.ipynb` files) that can be opened with VS Code that demonstrate and walk through some code to work with this package, step by step.    Please see if those will work.  

1. Installing package from git

    There is a public mirror of this repo on github which is mostly up-to-date.  If you need to `pip install` this package for use in another system (not for testing or dev work), use 

    `pip install ewxpwsdb@git+https://github.com/billspat/ewxpwsdb`

    